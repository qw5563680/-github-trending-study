#!/usr/bin/env python3
"""周报文件的格式约定：状态标记、分块标记，以及“是否真的写完了”的检查规则。

周报文件里有几行网页上看不见的标记（HTML 注释），自动流程靠它们判断状态：
  <!-- gts:status=pending -->   榜单已保存，教程待生成
  <!-- gts:status=complete -->  完整周报
首页只把“标记为 complete 且通过下面全部检查”的周报当作完整周报，
所以空模板、半成品不会被当成已完成。
"""
from __future__ import annotations

import re

STATUS_RE = re.compile(r"<!-- gts:status=(\w+) -->")
COMPLETED_RE = re.compile(r"<!-- gts:completed=([^>]*?) -->")
PENDING_MARK = "<!-- gts:tutorial:pending -->"
VERDICTS = ("值得现在动手", "先收藏", "了解即可")
VERIFY_LABELS = ("实际运行成功", "依据官方文档整理", "尚未验证")

SECTIONS = [
    ("1. 它能做什么？", re.compile(r"^###\s*1[\.、．]\s*.*能做什么", re.M), 200),
    ("2. 我怎么用？", re.compile(r"^###\s*2[\.、．]\s*.*怎么用", re.M), 200),
    ("3. 带我完成一个小练习", re.compile(r"^###\s*3[\.、．]\s*.*练习", re.M), 200),
    ("4. 它为什么能做到？", re.compile(r"^###\s*4[\.、．]\s*.*为什么能做到", re.M), 200),
    ("5. 学习判断", re.compile(r"^###\s*5[\.、．]\s*.*学习判断", re.M), 80),
    ("资料来源与核实状态", re.compile(r"^###\s*资料来源与核实状态", re.M), 80),
]


def marker(name: str, edge: str) -> str:
    return f"<!-- gts:{name}:{edge} -->"


def get_status(text: str) -> str | None:
    m = STATUS_RE.search(text)
    return m.group(1) if m else None


def get_completed(text: str) -> str | None:
    m = COMPLETED_RE.search(text)
    return m.group(1).strip() if m else None


def get_block(text: str, name: str) -> str | None:
    start, end = marker(name, "start"), marker(name, "end")
    i, j = text.find(start), text.find(end)
    if i < 0 or j < 0 or j < i:
        return None
    return text[i + len(start):j]


def set_block(text: str, name: str, content: str) -> str:
    start, end = marker(name, "start"), marker(name, "end")
    i, j = text.find(start), text.find(end)
    if i < 0 or j < 0 or j < i:
        raise ValueError(f"周报文件里找不到 {name} 分块标记")
    return text[: i + len(start)] + "\n" + content.strip("\n") + "\n" + text[j:]


def table_rows(block: str) -> list[list[str]]:
    """解析 Markdown 表格的数据行（跳过表头和分隔线），返回单元格列表。"""
    rows = []
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]]
        if not cells or all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
            continue
        rows.append(cells)
    return rows[1:] if rows else []


def _digits(text) -> str:
    return re.sub(r"\D", "", str(text or ""))


def content_problems(text: str, snapshot: dict | None, source: dict | None = None) -> list[str]:
    """检查一期周报的内容是否完整。返回问题列表；空列表表示通过。"""
    problems = []

    # --- 前 5 名表格必须与快照一致，且每行都有中文一句话用途 ---
    top5 = get_block(text, "top5")
    if top5 is None:
        problems.append("缺少前 5 名表格分块（gts:top5）")
    elif snapshot:
        rows = table_rows(top5)
        items = snapshot["items"][: snapshot.get("top_n", 5)]
        if len(rows) != len(items):
            problems.append(f"前 5 名表格应有 {len(items)} 行，实际 {len(rows)} 行")
        for row, item in zip(rows, items):
            label = f"表格第 {item['rank']} 名"
            if len(row) < 4:
                problems.append(f"{label}：列数不足 4 列")
                continue
            if _digits(row[0]) != str(item["rank"]):
                problems.append(f"{label}：排名与快照不一致")
            if f"]({item['url']})" not in row[1] or item["full_name"] not in row[1]:
                problems.append(f"{label}：项目名称或链接与快照不一致（应为 {item['full_name']}）")
            purpose = row[2]
            if not purpose or "待补充" in purpose:
                problems.append(f"{label}：一句话用途还没写成中文")
            elif not re.search(r"[一-鿿]", purpose):
                problems.append(f"{label}：一句话用途应使用中文")
            if _digits(row[3]) != _digits(item.get("stars_this_week_text")):
                problems.append(f"{label}：本周新增 Star 与快照不一致（取不到应留空，不能自己填）")

    # --- 教程主体 ---
    tut = get_block(text, "tutorial")
    if tut is None:
        problems.append("缺少教程分块（gts:tutorial）")
        return problems
    if PENDING_MARK in tut or "教程：待生成" in tut:
        problems.append("教程仍是“待生成”占位内容")
        return problems

    positions = []
    for title, pattern, _ in SECTIONS:
        m = pattern.search(tut)
        positions.append(m.start() if m else -1)
        if not m:
            problems.append(f"缺少小节标题：### {title}")
    found = [p for p in positions if p >= 0]
    if found != sorted(found):
        problems.append("小节顺序不对，应按 1→2→3→4→5→资料来源 的顺序")

    bodies = {}
    order = sorted((p, idx) for idx, p in enumerate(positions) if p >= 0)
    for n, (pos, idx) in enumerate(order):
        end = order[n + 1][0] if n + 1 < len(order) else len(tut)
        body = tut[pos:end].split("\n", 1)
        bodies[idx] = body[1] if len(body) > 1 else ""
    for idx, (title, _, min_len) in enumerate(SECTIONS):
        if idx in bodies and len(bodies[idx].strip()) < min_len:
            problems.append(f"小节“{title}”内容过短（少于 {min_len} 字），像是没写完")

    if 4 in bodies:
        verdicts = re.findall(
            r"判断[:：]\s*\*{0,2}\s*(" + "|".join(VERDICTS) + r")", bodies[4]
        )
        if len(verdicts) != 1:
            problems.append(
                "“学习判断”小节里必须有且只有一行“判断：值得现在动手／先收藏／了解即可”三选一"
            )
        if "？" not in bodies[4] and "?" not in bodies[4]:
            problems.append("“学习判断”小节缺少一个用来自测的问题")

    if not any(label in tut for label in VERIFY_LABELS):
        problems.append("没有标明核实状态（实际运行成功／依据官方文档整理／尚未验证）")
    if 5 in bodies:
        sha = (source or {}).get("head_sha")
        if sha and sha[:7] not in bodies[5]:
            problems.append(f"“资料来源与核实状态”里没有写参考的提交版本（应包含 {sha[:7]}）")
        if "http" not in bodies[5]:
            problems.append("“资料来源与核实状态”里没有任何官方链接")

    for leftover in ("____", "待生成", "待补充", "TODO"):
        if leftover in tut:
            problems.append(f"教程里还留着未填写的占位内容：{leftover}")
    return problems
