#!/usr/bin/env python3
"""抓取 GitHub Trending 周榜（全部语言），按页面顺序解析出项目列表。

原则：
- 只认页面上实际显示的内容；取不到的数字留空（None），绝不猜。
- 打不开或解析不出来时做有限次数重试；仍失败就抛出 TrendingError，由调用方记录原因。
"""
from __future__ import annotations

import html as html_lib
import re
import time

import common

ARTICLE_RE = re.compile(r"<article\b[^>]*>(.*?)</article>", re.S | re.I)
NAME_RE = re.compile(
    r"<h2\b[^>]*>.*?<a\b[^>]*?\bhref=\"/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)\"", re.S | re.I
)
DESC_RE = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S | re.I)
LANG_RE = re.compile(r"itemprop=\"programmingLanguage\"[^>]*>(.*?)<", re.S | re.I)
PERIOD_RE = re.compile(
    r"(\d[\d,\.]*\s*[kKmM]?)\s+stars?\s+(today|this\s+week|this\s+month)", re.I
)
TAG_RE = re.compile(r"<[^>]+>")
MIN_ITEMS = 5


class TrendingError(Exception):
    """榜单抓取或解析失败。"""

    def __init__(self, message: str, last_html: str | None = None):
        super().__init__(message)
        self.last_html = last_html


def _text(fragment: str) -> str:
    """去掉 HTML 标签，还原转义字符，把连续空白压成一个空格。"""
    fragment = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", fragment, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html_lib.unescape(TAG_RE.sub(" ", fragment))).strip()


def _to_int(text: str | None):
    """'12,345' -> 12345；带 k/m 缩写或取不到时返回 None（不估算）。"""
    if not text:
        return None
    cleaned = text.strip()
    if re.fullmatch(r"\d[\d,]*", cleaned):
        return int(cleaned.replace(",", ""))
    return None


def _link_text(block: str, owner: str, repo: str, suffixes: tuple[str, ...]):
    for suffix in suffixes:
        pattern = (
            r"<a\b[^>]*?\bhref=\"/" + re.escape(owner) + "/" + re.escape(repo)
            + re.escape(suffix) + r"\"[^>]*>(.*?)</a>"
        )
        m = re.search(pattern, block, re.S | re.I)
        if m:
            text = _text(m.group(1))
            m2 = re.search(r"\d[\d,\.]*\s*[kKmM]?", text)
            if m2:
                return m2.group(0).strip()
    return None


def parse_trending(page: str) -> dict:
    """解析榜单页面，返回 {'items': [...], 'period_seen': [...], 'excerpt': [...]}。"""
    items = []
    excerpt = []
    periods = set()
    for block in ARTICLE_RE.findall(page):
        m = NAME_RE.search(block)
        if not m:
            continue
        owner, repo = m.group(1), m.group(2)
        full_name = f"{owner}/{repo}"
        if any(it["full_name"].lower() == full_name.lower() for it in items):
            continue
        desc_m = DESC_RE.search(block)
        lang_m = LANG_RE.search(block)
        visible = _text(block)
        period_m = PERIOD_RE.search(visible)
        stars_text = _link_text(block, owner, repo, ("/stargazers",))
        forks_text = _link_text(block, owner, repo, ("/forks", "/network/members"))
        period_text = period_m.group(1).strip() if period_m else None
        period_word = re.sub(r"\s+", " ", period_m.group(2).lower()) if period_m else None
        if period_word:
            periods.add(period_word)
        items.append(
            {
                "rank": len(items) + 1,
                "full_name": full_name,
                "url": f"https://github.com/{full_name}",
                "description": _text(desc_m.group(1)) if desc_m else None,
                "language": _text(lang_m.group(1)) if lang_m else None,
                "total_stars_text": stars_text,
                "total_stars": _to_int(stars_text),
                "forks_text": forks_text,
                "forks": _to_int(forks_text),
                # 只有页面写的是 this week 时才记为“本周新增”，否则留空。
                "stars_this_week_text": period_text if period_word == "this week" else None,
                "stars_this_week": _to_int(period_text) if period_word == "this week" else None,
                "period_label_seen": (
                    f"{period_text} stars {period_word}" if period_m else None
                ),
            }
        )
        if len(excerpt) < 10:
            excerpt.append(f"{len(items)}. {visible[:400]}")
    return {"items": items, "period_seen": sorted(periods), "excerpt": excerpt}


def validate(parsed: dict) -> None:
    items = parsed["items"]
    if len(items) < MIN_ITEMS:
        raise TrendingError(
            f"页面打开了，但只解析出 {len(items)} 个项目（少于 {MIN_ITEMS} 个），"
            "可能是榜单暂时为空或页面结构变了"
        )
    periods = parsed["period_seen"]
    if periods and "this week" not in periods:
        raise TrendingError(
            f"页面显示的统计周期是 {periods}，不是 this week，说明拿到的不是周榜，本次不采用"
        )


def diagnostics(page: str) -> str:
    """解析失败时输出页面的结构线索，方便以后修解析规则。"""
    title = re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I)
    return (
        f"页面长度 {len(page)} 字符；标题：{_text(title.group(1)) if title else '（无）'}；"
        f"<article> 数量 {len(re.findall(r'<article', page, re.I))}；"
        f"'stars this week' 出现 {len(re.findall(r'stars this week', page, re.I))} 次；"
        f"'Box-row' 出现 {page.count('Box-row')} 次"
    )


def get_snapshot(attempts: int = 4, delays=(20, 60, 150), sleep=time.sleep) -> dict:
    """抓取并解析周榜，失败时有限次数重试。成功返回快照字典。"""
    errors = []
    last_html = None
    for i in range(attempts):
        try:
            status, body, _ = common.http_get(
                common.TRENDING_URL,
                headers={
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-US,en;q=0.8",
                },
                timeout=40,
            )
            if status != 200 or not body:
                errors.append(f"第 {i + 1} 次：HTTP 状态码 {status}")
            else:
                last_html = body.decode("utf-8", "replace")
                parsed = parse_trending(last_html)
                try:
                    validate(parsed)
                except TrendingError as err:
                    errors.append(f"第 {i + 1} 次：{err}（{diagnostics(last_html)}）")
                else:
                    fetched = common.now_beijing()
                    warnings = []
                    if not parsed["period_seen"]:
                        warnings.append("页面上没有找到“stars this week”字样，本周新增 Star 留空")
                    return {
                        "issue": common.issue_key(fetched),
                        "source_url": common.TRENDING_URL,
                        "source_label": "GitHub Trending · Repositories · This week · 全部编程语言",
                        "fetched_at_beijing": fetched.isoformat(timespec="seconds"),
                        "fetched_at_display": common.fmt_bj(fetched) + "（北京时间）",
                        "note": "抓取时的周榜快照：记录的是抓取那一刻页面显示的顺序和数字，"
                        "不是上一个自然周的最终排名。",
                        "attempts_used": i + 1,
                        "earlier_errors": errors,
                        "warnings": warnings,
                        "top_n": common.TOP_N,
                        "items": parsed["items"],
                        "page_excerpt": parsed["excerpt"],
                    }
        except Exception as err:  # 网络错误、超时等
            errors.append(f"第 {i + 1} 次：{type(err).__name__}: {err}")
        if i < attempts - 1:
            sleep(delays[min(i, len(delays) - 1)])
    raise TrendingError(
        f"榜单抓取失败，已重试 {attempts} 次。" + "；".join(errors), last_html=last_html
    )


if __name__ == "__main__":
    import json

    snap = get_snapshot()
    print(json.dumps(snap, ensure_ascii=False, indent=2))
