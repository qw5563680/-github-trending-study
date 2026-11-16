#!/usr/bin/env python3
"""写完教程后的收尾脚本：先检查内容是否完整，通过了才把这一期标记为“完整周报”。

用法：
    python3 scripts/finalize_issue.py 2026-W47            # 检查 + 标记完成 + 更新首页
    python3 scripts/finalize_issue.py 2026-W47 --check    # 只检查，不改任何文件

检查不通过时不会修改周报状态，首页仍显示“本期正在整理”。
"""
from __future__ import annotations

import sys

import build_index
import common
import fetch_materials
import issue_format as fmt
import run_log

COMPLETE_BANNER = (
    "> ✅ **完整周报**｜[← 回首页看全部周报](../README.md)"
)


def load(key: str):
    path = common.issue_path(key)
    if not path.exists():
        raise SystemExit(f"找不到周报文件：{path}")
    snap = common.read_json(common.snapshot_path(key))
    source = None
    if snap and snap.get("items"):
        source = common.read_json(
            common.materials_dir(key)
            / fetch_materials.dir_name(1, snap["items"][0]["full_name"])
            / "source.json"
        )
    return path, path.read_text(encoding="utf-8"), snap, source


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    check_only = "--check" in argv
    if len(args) != 1 or not common.KEY_RE.match(args[0]):
        print(__doc__)
        return 2
    key = args[0]
    path, text, snap, source = load(key)
    if snap is None:
        print(f"✗ 找不到这一期的榜单快照：{common.snapshot_path(key)}")
        return 1
    problems = fmt.content_problems(text, snap, source)
    if problems:
        print(f"✗ {key} 还不能标记为完成，发现 {len(problems)} 个问题：")
        for p in problems:
            print(f"  - {p}")
        return 1
    if check_only:
        print(f"✓ {key} 内容检查通过（未修改任何文件）")
        return 0

    already = fmt.get_status(text) == "complete"
    if not already:
        now = common.fmt_bj(common.now_beijing())
        text = fmt.STATUS_RE.sub("<!-- gts:status=complete -->", text, count=1)
        if fmt.get_completed(text) is None:
            text = text.replace(
                "<!-- gts:status=complete -->",
                f"<!-- gts:status=complete -->\n<!-- gts:completed={now} -->",
                1,
            )
        text = fmt.set_block(text, "banner", COMPLETE_BANNER)
        common.write_text(path, text)
        run_log.append("completed", key, f"{common.week_label(key)} 的榜首深度教程已写完并通过检查。")
    build_index.rebuild()
    print(f"✓ {key} 已标记为完整周报，首页已更新" + ("（之前已是完成状态）" if already else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
