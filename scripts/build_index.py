#!/usr/bin/env python3
"""重新生成仓库首页 README.md：醒目的“阅读最新一期”+ 按日期倒序的历史周报。

首页严格区分两种状态：
- 最新完整周报：标记为 complete 且通过完整性检查的最新一期；
- 本期正在整理：榜单已保存、教程还没写完的一期（不会被当作“最新一期”）。
"""
from __future__ import annotations

import build_issue
import common
import fetch_materials
import issue_format as fmt

RESULT_TEXT = {
    "created": "✅ 已保存新一期榜单和官方资料（教程待生成）",
    "exists": "✅ 本期已存在，没有重复生成",
    "resumed": "✅ 已补齐本期缺少的资料或初稿",
    "completed": "✅ 本期深度教程已写完",
    "writer_check": "✅ 写作任务发布权限检查通过",
    "fetch_failed": "❌ 榜单抓取失败，已保留上一期",
    "error": "❌ 运行出错，已有周报未受影响",
}


def collect() -> list[dict]:
    """收集每一期的信息，新的在前。"""
    issues = []
    base = common.snapshots_dir()
    keys = set()
    if base.exists():
        keys |= {d.name for d in base.iterdir() if d.is_dir() and common.KEY_RE.match(d.name)}
    if common.weekly_dir().exists():
        keys |= {p.stem for p in common.weekly_dir().glob("*.md") if common.KEY_RE.match(p.stem)}
    for key in sorted(keys, reverse=True):
        snap = common.read_json(common.snapshot_path(key))
        path = common.issue_path(key)
        info = {
            "key": key,
            "snapshot": snap,
            "has_file": path.exists(),
            "champion": snap["items"][0]["full_name"] if snap and snap.get("items") else "",
            "fetched": (snap or {}).get("fetched_at_display", ""),
            "state": "snapshot_only",
            "problems": [],
            "completed": None,
        }
        if path.exists():
            text = path.read_text(encoding="utf-8")
            status = fmt.get_status(text)
            info["completed"] = fmt.get_completed(text)
            if status == "complete":
                source = None
                if snap and snap.get("items"):
                    source = common.read_json(
                        common.materials_dir(key)
                        / fetch_materials.dir_name(1, snap["items"][0]["full_name"])
                        / "source.json"
                    )
                info["problems"] = fmt.content_problems(text, snap, source)
                info["state"] = "complete" if not info["problems"] else "invalid"
            else:
                info["state"] = "pending"
        issues.append(info)
    return issues


def render(issues: list[dict], run_log: list[dict]) -> str:
    complete = [i for i in issues if i["state"] == "complete"]
    latest = complete[0] if complete else None
    in_progress = [i for i in issues if i["state"] != "complete" and (not latest or i["key"] > latest["key"])]

    out = [
        "# 📚 GitHub 热门项目学习周报",
        "",
        "每周一自动抓取 [GitHub Trending 周榜（全部语言）](https://github.com/trending?since=weekly)，"
        "用中文大白话讲清榜首项目的三件事：**它能帮我做什么 → 我怎样用它完成一件具体的事 → "
        "我怎么知道自己用成功了**。直接在这个网页上点开阅读，不用下载任何东西。",
        "",
    ]

    if latest:
        out += [
            f"## 👉 [阅读最新一期：{common.week_label(latest['key'])}｜榜首 {latest['champion']}](weekly/{latest['key']}.md)",
            "",
            f"榜单抓取于 {latest['fetched']}"
            + (f"；教程完成于 {latest['completed']}（北京时间）" if latest["completed"] else "")
            + "。",
            "",
        ]
    else:
        out += ["## 👉 还没有完整周报", "", "第一期正在整理中，写完后这里会出现“阅读最新一期”的链接。", ""]

    for item in in_progress[:3]:
        if item["state"] == "invalid":
            why = "已标记完成但没有通过完整性检查（" + "；".join(item["problems"][:3]) + "）"
        elif item["state"] == "snapshot_only":
            why = "榜单已保存，周报文件还没生成（下次自动运行会补上）"
        else:
            why = "榜单和官方资料已保存，榜首深度教程还没写完"
        target = (
            f"weekly/{item['key']}.md" if item["has_file"] else f"data/snapshots/{item['key']}/trending.json"
        )
        out += [
            f"> ⏳ **本期正在整理：{common.week_label(item['key'])}**（榜首 {item['champion'] or '未知'}）—— {why}。"
            f"[先看榜单快照]({target})。"
            + ("上面的“最新一期”仍指向上一期完整周报。" if latest else ""),
            "",
        ]

    actions = f"https://github.com/{build_issue.repo_slug()}/actions"
    last = run_log[-1] if run_log else None
    if last and last.get("result") in ("fetch_failed", "error"):
        out += [
            f"> ⚠️ **最近一次自动运行没有成功**（{last.get('time_beijing', '')}）："
            f"{last.get('detail', '')} 已有周报没有被改动，下面仍是之前的内容；没有用猜测或别的榜单顶替。",
            "",
        ]

    out += [
        "## 历史周报（新的在前）",
        "",
    ]
    if issues:
        out += [
            "| 期数 | 榜单抓取时间（北京时间） | 抓取时的第 1 名 | 状态 |",
            "|---|---|---|---|",
        ]
        for item in issues:
            state = {
                "complete": "✅ 完整周报",
                "pending": "⏳ 教程待生成",
                "invalid": "⏳ 整理中（未通过完整性检查）",
                "snapshot_only": "⏳ 仅有榜单快照",
            }[item["state"]]
            title = f"{common.week_label(item['key'])}（{common.week_range(item['key'])}）"
            link = (
                f"[{title}](weekly/{item['key']}.md)" if item["has_file"]
                else f"[{title}](data/snapshots/{item['key']}/trending.json)"
            )
            champ = (
                f"[{item['champion']}](https://github.com/{item['champion']})" if item["champion"] else ""
            )
            out.append(
                f"| {link} | {item['fetched'].replace('（北京时间）', '')} | {champ} | {state} |"
            )
        out.append("")
    else:
        out += ["还没有任何一期。", ""]

    out += ["## 自动更新状态", ""]
    if last:
        line = (
            f"- 最近一次运行：{last.get('time_beijing', '')}（北京时间）· "
            f"{RESULT_TEXT.get(last.get('result'), last.get('result'))}"
        )
        if last.get("run_url"):
            line += f" · [运行记录]({last['run_url']})"
        out.append(line)
    out += [
        "- 时间表：每周一北京时间 09:00，GitHub Actions 自动抓取榜单并保存官方资料"
        "（GitHub 的定时任务有时会晚几分钟到几十分钟；09:35 会自动补跑一次）；"
        "10:10 起由 Claude Code 云端定时任务写中文深度教程（16:10 再检查一次有没有漏写的）。",
        f"- 全部运行记录：[Actions 页面]({actions}) · 想立刻手动跑一次："
        f"[打开这个页面]({actions}/workflows/weekly.yml)，点右侧 **Run workflow**。",
        "- 同一周重复运行不会生成重复周报；抓取或写作失败不会改动已有周报。",
        "",
        "## 关于这个仓库",
        "",
        "- [使用说明与常见问题](docs/使用说明.md)：它是怎么运作的、出问题时怎么办、费用说明。",
        "- [写作规范](WRITING_GUIDE.md)：每期周报按什么标准写（给 Claude 看的，你也可以改）。",
        "",
        "<sub>本页由 `scripts/build_index.py` 自动生成，请不要手动编辑；要改措辞请改脚本。</sub>",
        "",
    ]
    return "\n".join(out)


def rebuild() -> list[dict]:
    issues = collect()
    run_log = common.read_json(common.run_log_path(), default=[]) or []
    common.write_text(common.root() / "README.md", render(issues, run_log))
    return issues


if __name__ == "__main__":
    for it in rebuild():
        print(it["key"], it["state"], "；".join(it["problems"]))
