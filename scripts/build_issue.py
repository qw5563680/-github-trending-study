#!/usr/bin/env python3
"""根据榜单快照生成一期周报的初稿：前 5 名表格 + 快照明细 + “教程待生成”占位。

只在这一期的周报文件还不存在时才创建，绝不覆盖已有内容。
"""
from __future__ import annotations

import os
import re
import subprocess

import common
import fetch_materials
import issue_format as fmt

DEFAULT_REPO = "qw5563680/-github-trending-study"


def repo_slug() -> str:
    """本仓库的“所有者/仓库名”。优先用 GitHub Actions 提供的值，其次读 git 远程地址。

    这样以后即使给仓库改名，下次运行时首页和周报里的链接也会自动跟着变。
    """
    env = os.environ.get("GITHUB_REPOSITORY")
    if env:
        return env
    try:
        url = subprocess.run(
            ["git", "-C", str(common.root()), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        m = re.search(r"github\.com[:/]+([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", url)
        if m:
            return f"{m.group(1)}/{m.group(2)}"
    except Exception:
        pass
    return DEFAULT_REPO


def fill_instruction(key: str) -> str:
    return (
        f"请打开仓库 {repo_slug()}，先完整阅读 WRITING_GUIDE.md，然后补全 weekly/{key}.md "
        "这一期的榜首深度教程；按指南自检通过后运行收尾脚本、更新首页，并推送到 main 分支。"
    )


def previous_champions(key: str, champion: str) -> list[str]:
    """找出往期里同样把这个项目排在第 1 名的期号（从新到旧）。"""
    found = []
    base = common.snapshots_dir()
    if not base.exists():
        return found
    for d in sorted(base.iterdir(), reverse=True):
        if not d.is_dir() or d.name >= key or not common.KEY_RE.match(d.name):
            continue
        snap = common.read_json(d / "trending.json")
        if snap and snap.get("items") and snap["items"][0]["full_name"].lower() == champion.lower():
            found.append(d.name)
    return found


def top5_table(snapshot: dict) -> str:
    lines = [
        "| 排名 | 项目名称及链接 | 一句话用途 | 本周新增 Star |",
        "|:---:|---|---|---:|",
    ]
    for item in snapshot["items"][: snapshot.get("top_n", common.TOP_N)]:
        desc = common.md_cell(item.get("description")) or "（页面上没有简介）"
        lines.append(
            f"| {item['rank']} | [{item['full_name']}]({item['url']}) "
            f"| 〔中文说明待补充〕官方简介原文：{desc} "
            f"| {item.get('stars_this_week_text') or ''} |"
        )
    return "\n".join(lines)


def detail_table(snapshot: dict) -> str:
    lines = [
        "| 名次 | 仓库地址 | 主要语言 | 累计 Star（页面显示） | 本周新增 Star（页面显示） |",
        "|:---:|---|---|---:|---:|",
    ]
    for item in snapshot["items"][: snapshot.get("top_n", common.TOP_N)]:
        lines.append(
            f"| {item['rank']} | <{item['url']}> | {common.md_cell(item.get('language'))} "
            f"| {item.get('total_stars_text') or ''} | {item.get('stars_this_week_text') or ''} |"
        )
    return "\n".join(lines)


def render_pending(key: str, snapshot: dict, materials: dict | None) -> str:
    champion = snapshot["items"][0]
    mat_dir = f"data/snapshots/{key}/materials/{fetch_materials.dir_name(1, champion['full_name'])}"
    repeats = previous_champions(key, champion["full_name"])
    out = [
        f"<!-- gts:issue={key} -->",
        "<!-- gts:status=pending -->",
        "",
        f"# GitHub 热门项目学习周报｜{common.week_label(key)}",
        "",
        fmt.marker("banner", "start"),
        "> ⏳ **本期正在整理**：榜单快照和官方资料已自动保存，**榜首深度教程待生成**。",
        "> 这还不是完整周报。[← 回首页看最新完整周报](../README.md)",
        fmt.marker("banner", "end"),
        "",
        "## 本周前 5 名（抓取时的周榜快照）",
        "",
        fmt.marker("top5", "start"),
        top5_table(snapshot),
        fmt.marker("top5", "end"),
        "",
        f"- **榜单来源**：[{snapshot['source_label']}]({snapshot['source_url']})",
        f"- **实际抓取时间**：{snapshot['fetched_at_display']}",
        "- **怎么理解这张表**：这是**抓取那一刻**页面显示的顺序和数字，之后还会变；"
        "它不是上一个自然周的最终排名。排名按页面顺序原样保留，没有按 Star 数重排。",
        "",
        "<details>",
        "<summary>快照明细：名次、仓库地址、累计 Star、本周新增 Star（点击展开）</summary>",
        "",
        detail_table(snapshot),
        "",
        "累计 Star 和本周新增 Star 是两个不同的数字：前者是项目至今收到的总数，"
        "后者是页面标注的“stars this week”。页面上取不到的数字留空。"
        f"完整原始记录见 [`data/snapshots/{key}/trending.json`](../data/snapshots/{key}/trending.json)。",
        "",
        "</details>",
        "",
        f"## 本周榜首深度教程：{champion['full_name']}",
        "",
    ]
    if repeats:
        links = "、".join(f"[{common.week_label(k)}]({k}.md)" for k in repeats[:5])
        out += [
            fmt.marker("repeat", "start"),
            f"> 🔁 **榜首与往期重复**：`{champion['full_name']}` 本周仍是第 1 名，"
            f"它在 {links} 也是榜首。**入门教程请看往期**；"
            "本期只讲已核实的新变化，或换一个以前没讲过的实用案例，不重复同样的内容。",
            fmt.marker("repeat", "end"),
            "",
        ]
    warn = ""
    if materials and materials.get("errors"):
        warn = (
            "> ⚠️ 保存官方资料时有部分内容没取到（详见该目录下的 `source.json`），"
            "写教程时需要到项目官方页面补看。\n>\n"
        )
    out += [
        fmt.marker("tutorial", "start"),
        fmt.PENDING_MARK,
        "> **教程：待生成**",
        ">",
        f"> 榜单和官方资料已保存在 [`{mat_dir}`](../{mat_dir})，但这一期的中文教程还没有写。",
        ">",
        warn + "> 正常情况下，Claude Code 的云端定时任务会在周一上午自动补全。"
        "如果过了大半天这里仍是“待生成”，",
        "> 打开 <https://claude.ai/code> 新建一个会话，把下面这句话原样发过去即可：",
        ">",
        "> ```text",
        f"> {fill_instruction(key)}",
        "> ```",
        fmt.marker("tutorial", "end"),
        "",
    ]
    return "\n".join(out)


def create_if_missing(key: str, snapshot: dict, materials: dict | None) -> bool:
    """周报文件不存在时创建初稿，返回 True；已存在则原样保留，返回 False。"""
    path = common.issue_path(key)
    if path.exists():
        return False
    common.write_text(path, render_pending(key, snapshot, materials))
    return True
