#!/usr/bin/env python3
"""自动流程的测试。运行方式：python3 -m unittest discover -s tests -v

测试用的是手写的仿真榜单页面（tests/fixtures/trending_sample.html）和假的网络响应，
不会真的访问 GitHub，也不会改动仓库里的真实周报。
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

import build_index  # noqa: E402
import common  # noqa: E402
import fetch_trending  # noqa: E402
import finalize_issue  # noqa: E402
import issue_format as fmt  # noqa: E402
import run_weekly  # noqa: E402

FIXTURE = (HERE / "fixtures" / "trending_sample.html").read_text(encoding="utf-8")
SHA = "0123456789abcdef0123456789abcdef01234567"


class FakeNet:
    """假的网络层：按网址返回预设内容。"""

    def __init__(self):
        self.trending = (200, FIXTURE)
        self.calls = []

    def __call__(self, url, headers=None, timeout=40):
        self.calls.append(url)
        if url == common.TRENDING_URL:
            status, body = self.trending
            return status, body.encode("utf-8"), {}
        if url.startswith("https://api.github.com"):
            path = url[len("https://api.github.com"):]
            return self.api(path)
        return 404, b"", {}

    def api(self, path):
        def ok(data):
            body = data if isinstance(data, bytes) else json.dumps(data).encode()
            return 200, body, {}

        if path.endswith("/readme"):
            return ok({
                "path": "README.md", "html_url": "https://example.invalid/readme", "sha": "r1",
                "encoding": "base64",
                "content": base64.b64encode("# Demo\n\nOfficial readme text.\n".encode()).decode(),
            })
        if "/releases" in path:
            return ok([{"tag_name": "v1.2.3", "name": "1.2.3", "published_at": "2026-11-10T00:00:00Z",
                        "html_url": "https://example.invalid/rel", "prerelease": False, "body": "notes"}])
        if "/commits/" in path:
            return ok({"sha": SHA, "html_url": "https://example.invalid/commit",
                       "commit": {"committer": {"date": "2026-11-15T00:00:00Z"}}})
        if "/git/trees/" in path:
            return ok({"truncated": False, "tree": [
                {"path": "README.md", "type": "blob"},
                {"path": "docs/quickstart.md", "type": "blob"},
                {"path": "src/main.py", "type": "blob"},
            ]})
        if "/contents/" in path:
            return ok(b"# Quickstart\n\nRun the demo.\n")
        if path.startswith("/repos/"):
            return ok({"full_name": path[len("/repos/"):], "html_url": "https://example.invalid",
                       "description": "d", "default_branch": "main", "license": {"spdx_id": "MIT"}})
        return 404, b"", {}


def good_tutorial() -> str:
    filler = "这是一段用于测试的说明文字，长度需要足够，才能通过“内容不能太短”的检查。" * 8
    return "\n".join([
        "### 1. 它能做什么？", filler, "",
        "### 2. 我怎么用？", filler, "（依据官方文档整理）", "",
        "### 3. 带我完成一个小练习", filler, "",
        "### 4. 它为什么能做到？", filler, "",
        "### 5. 学习判断", "**判断：先收藏**", filler, "自测问题：你能说出它的输入和输出分别是什么吗？", "",
        "### 资料来源与核实状态",
        f"- 参考版本：提交 `{SHA[:7]}`，见 https://example.invalid/commit",
        "- 核实状态：依据官方文档整理；练习步骤尚未验证。" + filler,
    ])


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gts-test-")
        os.environ["GTS_ROOT"] = self.tmp
        os.environ["GTS_NOW"] = "2026-11-16T09:05:00+08:00"
        self.net = FakeNet()
        self._orig_get = common.http_get
        common.http_get = self.net
        self._orig_snapshot = fetch_trending.get_snapshot
        fetch_trending.get_snapshot = lambda **kw: self._orig_snapshot(sleep=lambda s: None, **kw)

    def tearDown(self):
        common.http_get = self._orig_get
        fetch_trending.get_snapshot = self._orig_snapshot
        os.environ.pop("GTS_ROOT", None)
        os.environ.pop("GTS_NOW", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def readme(self) -> str:
        return (Path(self.tmp) / "README.md").read_text(encoding="utf-8")

    def issue(self, key: str) -> str:
        return common.issue_path(key).read_text(encoding="utf-8")

    def complete(self, key: str):
        text = self.issue(key)
        top5 = fmt.get_block(text, "top5").replace("〔中文说明待补充〕官方简介原文：", "中文说明：")
        text = fmt.set_block(text, "top5", top5)
        text = fmt.set_block(text, "tutorial", good_tutorial())
        common.write_text(common.issue_path(key), text)
        return finalize_issue.main([key])

    # ---- 解析 ----
    def test_parse_keeps_page_order_and_leaves_missing_blank(self):
        parsed = fetch_trending.parse_trending(FIXTURE)
        items = parsed["items"]
        self.assertEqual([i["full_name"] for i in items], [
            "alpha-org/alpha-tool", "beta-dev/beta.js", "gamma/no-description-repo",
            "delta/delta_lib", "epsilon/eps", "zeta/sixth"])
        first = items[0]
        self.assertEqual(first["description"], "Turn any PDF into clean Markdown & structured data | fast")
        self.assertEqual((first["language"], first["total_stars"], first["forks"]), ("Python", 45678, 3210))
        self.assertEqual((first["stars_this_week_text"], first["stars_this_week"]), ("9,876", 9876))
        self.assertIsNone(items[2]["description"])           # 没有简介 → 留空
        self.assertEqual(items[2]["total_stars_text"], "12.3k")
        self.assertIsNone(items[2]["total_stars"])            # 缩写数字不估算
        self.assertIsNone(items[3]["stars_this_week_text"])   # 页面没显示本周新增 → 留空
        self.assertEqual(items[4]["stars_this_week"], 1)      # “1 star this week”

    def test_daily_page_is_rejected(self):
        self.net.trending = (200, FIXTURE.replace("this week", "today"))
        with self.assertRaises(fetch_trending.TrendingError):
            fetch_trending.get_snapshot(attempts=2)

    # ---- 整体流程 ----
    def test_first_run_creates_pending_issue_not_shown_as_complete(self):
        result, key, _ = run_weekly.run()
        build_index.rebuild()
        self.assertEqual((result, key), ("created", "2026-W47"))
        text = self.issue(key)
        self.assertEqual(fmt.get_status(text), "pending")
        self.assertIn("教程：待生成", text)
        self.assertIn("[alpha-org/alpha-tool](https://github.com/alpha-org/alpha-tool)", text)
        self.assertIn("fast | 9,876 |", text)                      # 第 1 名的本周新增
        self.assertIn("structured data \\| fast", text)            # 简介里的竖线已转义
        self.assertNotIn("zeta/sixth", text)                        # 只展示前 5 名
        readme = self.readme()
        self.assertIn("还没有完整周报", readme)
        self.assertIn("本期正在整理：2026 年第 47 周", readme)
        self.assertNotIn("[阅读最新一期", readme)
        mat = common.materials_dir(key) / "1-alpha-org__alpha-tool"
        self.assertTrue((mat / "official-readme.md").exists())
        self.assertTrue((mat / "docs" / "docs__quickstart.md").exists())
        self.assertEqual(common.read_json(mat / "source.json")["head_sha"], SHA)
        self.assertTrue((common.materials_dir(key) / "2-beta-dev__beta.js" / "official-readme-head.md").exists())

    def test_rerun_same_week_does_not_duplicate_or_overwrite(self):
        run_weekly.run()
        key = "2026-W47"
        common.write_text(common.issue_path(key), self.issue(key) + "\n人工补充的一行\n")
        before = self.issue(key)
        calls_before = len(self.net.calls)
        os.environ["GTS_NOW"] = "2026-11-18T15:00:00+08:00"      # 同一周的周三再跑
        result, key2, _ = run_weekly.run()
        self.assertEqual((result, key2), ("exists", key))
        self.assertEqual(self.issue(key), before)
        self.assertEqual(len(list(common.weekly_dir().glob("*.md"))), 1)
        self.assertEqual(len(self.net.calls), calls_before)        # 没有重新抓取

    def test_scheduled_retry_is_silent_when_issue_exists(self):
        run_weekly.main()
        log_before = common.run_log_path().read_text(encoding="utf-8")
        readme_before = self.readme()
        os.environ["GITHUB_EVENT_NAME"] = "schedule"
        os.environ["GTS_NOW"] = "2026-11-16T09:40:00+08:00"
        try:
            self.assertEqual(run_weekly.main(), 0)
        finally:
            os.environ.pop("GITHUB_EVENT_NAME", None)
        self.assertEqual(common.run_log_path().read_text(encoding="utf-8"), log_before)
        self.assertEqual(self.readme(), readme_before)

    def test_finalize_refuses_empty_template(self):
        run_weekly.run()
        key = "2026-W47"
        self.assertEqual(finalize_issue.main([key]), 1)
        self.assertEqual(fmt.get_status(self.issue(key)), "pending")
        # 手动把标记改成 complete 也骗不过首页
        common.write_text(common.issue_path(key),
                          self.issue(key).replace("gts:status=pending", "gts:status=complete"))
        build_index.rebuild()
        self.assertNotIn("[阅读最新一期", self.readme())
        self.assertIn("未通过完整性检查", self.readme())

    def test_complete_then_failure_then_repeat_champion(self):
        run_weekly.run()
        self.assertEqual(self.complete("2026-W47"), 0)
        self.assertEqual(fmt.get_status(self.issue("2026-W47")), "complete")
        self.assertIn("阅读最新一期：2026 年第 47 周｜榜首 alpha-org/alpha-tool", self.readme())
        done = self.issue("2026-W47")

        # 第二周：榜单打不开 → 记录失败、保留上一期、不创建新周报
        os.environ["GTS_NOW"] = "2026-11-23T09:05:00+08:00"
        self.net.trending = (503, "")
        self.assertEqual(run_weekly.main(), 0)
        self.assertFalse(common.issue_path("2026-W48").exists())
        self.assertFalse(common.snapshot_path("2026-W48").exists())
        self.assertEqual(self.issue("2026-W47"), done)
        readme = self.readme()
        self.assertIn("最近一次自动运行没有成功", readme)
        self.assertIn("阅读最新一期：2026 年第 47 周", readme)
        self.assertEqual(common.read_json(common.run_log_path())[-1]["result"], "fetch_failed")

        # 同一周稍后重试成功，榜首与上期相同 → 标明重复并链接往期
        self.net.trending = (200, FIXTURE)
        os.environ["GTS_NOW"] = "2026-11-23T11:00:00+08:00"
        result, key, _ = run_weekly.run()
        build_index.rebuild()
        self.assertEqual((result, key), ("created", "2026-W48"))
        new = self.issue("2026-W48")
        self.assertIn("榜首与往期重复", new)
        self.assertIn("[2026 年第 47 周](2026-W47.md)", new)
        readme = self.readme()
        self.assertIn("阅读最新一期：2026 年第 47 周", readme)       # 最新“完整”周报仍是上一期
        self.assertIn("本期正在整理：2026 年第 48 周", readme)
        self.assertLess(readme.index("weekly/2026-W48.md)"), readme.rindex("weekly/2026-W47.md)"))

    def test_checker_catches_tampered_table_and_missing_parts(self):
        run_weekly.run()
        key = "2026-W47"
        snap = common.read_json(common.snapshot_path(key))
        text = self.issue(key)
        top5 = fmt.get_block(text, "top5").replace("〔中文说明待补充〕官方简介原文：", "中文说明：")
        ok = fmt.set_block(fmt.set_block(text, "top5", top5), "tutorial", good_tutorial())
        self.assertEqual(fmt.content_problems(ok, snap, {"head_sha": SHA}), [])
        swapped = ok.replace("| 9,876 |", "| 99,999 |")
        self.assertTrue(any("本周新增 Star 与快照不一致" in p for p in fmt.content_problems(swapped, snap)))
        two = ok.replace("**判断：先收藏**", "**判断：先收藏**\n判断：了解即可")
        self.assertTrue(any("三选一" in p for p in fmt.content_problems(two, snap)))
        nosec = ok.replace("### 3. 带我完成一个小练习", "### 小练习")
        self.assertTrue(any("缺少小节标题" in p for p in fmt.content_problems(nosec, snap)))
        nosha = ok.replace(SHA[:7], "abcdefg")
        self.assertTrue(any("提交版本" in p for p in fmt.content_problems(nosha, snap, {"head_sha": SHA})))


if __name__ == "__main__":
    unittest.main()
