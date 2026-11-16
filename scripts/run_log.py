#!/usr/bin/env python3
"""运行记录：每次自动/手动运行的时间、结果和原因，保存在 data/run-log.json（只留最近 60 条）。"""
from __future__ import annotations

import os

import common

KEEP = 60


def run_url() -> str | None:
    server = os.environ.get("GITHUB_SERVER_URL")
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if server and repo and run_id:
        return f"{server}/{repo}/actions/runs/{run_id}"
    return None


def trigger() -> str:
    event = os.environ.get("GITHUB_EVENT_NAME")
    return {
        "schedule": "定时（每周一）",
        "workflow_dispatch": "手动运行",
    }.get(event or "", event or "本地/Claude 会话")


def append(result: str, issue: str, detail: str) -> dict:
    entry = {
        "time_beijing": common.fmt_bj(common.now_beijing()),
        "issue": issue,
        "trigger": trigger(),
        "result": result,
        "detail": detail,
        "run_url": run_url(),
    }
    log = common.read_json(common.run_log_path(), default=[]) or []
    log.append(entry)
    common.write_json(common.run_log_path(), log[-KEEP:])
    return entry
