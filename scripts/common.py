#!/usr/bin/env python3
"""公共工具：路径、北京时间、期号、读写文件、网络请求。

整个项目只用 Python 自带的标准库，不需要安装任何第三方包。
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BEIJING = timezone(timedelta(hours=8))
TRENDING_URL = "https://github.com/trending?since=weekly"
TOP_N = 5
# 通用的客户端标识，不包含任何个人信息。
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) weekly-trending-snapshot/1.0"

KEY_RE = re.compile(r"^(\d{4})-W(\d{2})$")


# ---------- 路径 ----------

def root() -> Path:
    """仓库根目录。测试时可用环境变量 GTS_ROOT 指到临时目录。"""
    env = os.environ.get("GTS_ROOT")
    return Path(env).resolve() if env else Path(__file__).resolve().parent.parent


def weekly_dir() -> Path:
    return root() / "weekly"


def snapshots_dir() -> Path:
    return root() / "data" / "snapshots"


def snapshot_dir(key: str) -> Path:
    return snapshots_dir() / key


def snapshot_path(key: str) -> Path:
    return snapshot_dir(key) / "trending.json"


def materials_dir(key: str) -> Path:
    return snapshot_dir(key) / "materials"


def issue_path(key: str) -> Path:
    return weekly_dir() / f"{key}.md"


def run_log_path() -> Path:
    return root() / "data" / "run-log.json"


def debug_dir() -> Path:
    return root() / "data" / "debug"


# ---------- 时间与期号 ----------

def now_beijing() -> datetime:
    """当前北京时间。测试时可用 GTS_NOW（ISO 格式）固定时间。"""
    fake = os.environ.get("GTS_NOW")
    if fake:
        dt = datetime.fromisoformat(fake)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=BEIJING)
        return dt.astimezone(BEIJING)
    return datetime.now(BEIJING)


def issue_key(dt: datetime) -> str:
    """期号 = 北京时间所在的 ISO 周，例如 2026-W47。同一周内重复运行得到同一个期号。"""
    year, week, _ = dt.astimezone(BEIJING).isocalendar()
    return f"{year}-W{week:02d}"


def week_label(key: str) -> str:
    m = KEY_RE.match(key)
    if not m:
        return key
    return f"{int(m.group(1))} 年第 {int(m.group(2))} 周"


def week_range(key: str) -> str:
    """这一期对应的自然周（周一至周日），例如 11 月 16 日—11 月 22 日。"""
    m = KEY_RE.match(key)
    if not m:
        return ""
    monday = date.fromisocalendar(int(m.group(1)), int(m.group(2)), 1)
    sunday = monday + timedelta(days=6)
    return f"{monday.month} 月 {monday.day} 日—{sunday.month} 月 {sunday.day} 日"


def fmt_bj(dt: datetime) -> str:
    return dt.astimezone(BEIJING).strftime("%Y-%m-%d %H:%M")


def parse_iso(text: str) -> datetime:
    return datetime.fromisoformat(text)


# ---------- 读写文件 ----------

def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def write_text(path: Path, text: str) -> None:
    """先写临时文件再替换，避免写到一半失败时留下残缺文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_json(path: Path, data) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


# ---------- 网络 ----------

def http_get(url: str, headers: dict | None = None, timeout: int = 40):
    """发起一次 GET 请求，返回 (状态码, 内容字节, 响应头)。

    HTTP 错误（404、429、500 等）不抛异常，而是把状态码返回给调用方；
    连不上、超时等网络错误会抛出异常，由调用方决定是否重试。
    """
    merged = {"User-Agent": USER_AGENT}
    merged.update(headers or {})
    req = urllib.request.Request(url, headers=merged)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as err:
        body = b""
        try:
            body = err.read() or b""
        except Exception:
            pass
        return err.code, body, dict(err.headers or {})


def md_cell(text: str | None) -> str:
    """把任意文字变成可以安全放进 Markdown 表格单元格的一行。"""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", str(text)).strip()
    return text.replace("|", "\\|")
