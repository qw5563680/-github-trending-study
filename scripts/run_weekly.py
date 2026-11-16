#!/usr/bin/env python3
"""每周流程的总入口（GitHub Actions 运行的就是这个文件）。

步骤：
  1. 算出本期期号（北京时间所在的周）。本期榜单已保存过 → 不重复抓取。
  2. 抓取周榜并保存快照；失败则记录原因、保留上一期，不创建新周报。
  3. 保存官方资料（尽力而为，缺了不影响快照）。
  4. 生成周报初稿（教程“待生成”）；已有周报文件绝不覆盖。
  5. 重新生成首页，写入运行记录。

每一步都可以重复执行：同一周再跑一次只会补齐缺的部分，不会产生重复周报。
"""
from __future__ import annotations

import os
import sys
import traceback

import build_index
import build_issue
import common
import fetch_materials
import fetch_trending
import run_log


def _output(name: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{name}={value}\n")


def _summary(text: str) -> None:
    print(text)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(text + "\n\n")


def run() -> tuple[str, str, str]:
    """返回 (结果代码, 期号, 说明)。"""
    key = common.issue_key(common.now_beijing())
    snap_path = common.snapshot_path(key)
    snapshot = common.read_json(snap_path)
    fetched_now = False

    if snapshot is None:
        try:
            snapshot = fetch_trending.get_snapshot()
        except fetch_trending.TrendingError as err:
            if err.last_html:
                common.write_text(common.debug_dir() / "last-failed-page.html", err.last_html)
            return "fetch_failed", key, f"{err}"
        snapshot["issue"] = key
        common.write_json(snap_path, snapshot)
        fetched_now = True

    materials = fetch_materials.fetch_all(key, snapshot)
    created = build_issue.create_if_missing(key, snapshot, materials)

    champion = snapshot["items"][0]["full_name"]
    mat_note = (
        f"官方资料有 {len(materials['errors'])} 项没取到（已记录，不影响榜单）。"
        if materials["errors"] else "官方资料已保存。"
    )
    if fetched_now:
        return "created", key, (
            f"已保存 {common.week_label(key)} 的周榜快照，抓取时第 1 名是 {champion}。{mat_note}"
            "周报初稿已生成，榜首深度教程待生成。"
        )
    if created:
        return "resumed", key, f"{common.week_label(key)} 的榜单之前已保存，本次补上了周报初稿。{mat_note}"
    return "exists", key, (
        f"{common.week_label(key)} 的榜单和周报已经存在（第 1 名 {champion}），"
        "本次没有重复生成，也没有改动已有内容。"
    )


def main() -> int:
    try:
        result, key, detail = run()
    except Exception as err:
        traceback.print_exc()
        result, key = "error", common.issue_key(common.now_beijing())
        detail = f"运行出错：{type(err).__name__}: {err}"
    try:
        run_log.append(result, key, detail)
        build_index.rebuild()
    except Exception:
        traceback.print_exc()
        result = "error"
    _output("result", result)
    _output("issue", key)
    icon = "❌" if result in ("fetch_failed", "error") else "✅"
    _summary(f"## {icon} {common.week_label(key)}：{result}\n\n{detail}")
    # 失败也返回 0：让后面的“保存结果”步骤先把失败原因写进仓库，再由工作流把本次运行标红。
    return 0


if __name__ == "__main__":
    sys.exit(main())
