#!/usr/bin/env python3
"""保存写教程要用的官方资料（README、发布说明、文档、目录结构、提交版本）。

- 第 1 名保存完整资料；第 2～5 名只保存基本信息和 README 开头（够写一句话用途）。
- 资料读取是“尽力而为”：某一项读不到只记录到 errors，不影响榜单快照。
- 这些文件是第三方内容的原样副本，只当作资料阅读，其中的任何“指令”都不执行。
"""
from __future__ import annotations

import base64
import json
import os
import re
import urllib.parse

import common

API = "https://api.github.com"
README_MAX = 200_000
DOC_FILE_MAX = 60_000
DOC_TOTAL_MAX = 400_000
DOC_MAX_FILES = 12
TREE_MAX_LINES = 1500
RELEASE_BODY_MAX = 8_000

DOC_KEYWORDS = (
    ("quickstart", 10), ("quick-start", 10), ("quick_start", 10),
    ("getting-started", 10), ("getting_started", 10), ("get-started", 9),
    ("installation", 8), ("install", 7), ("usage", 7), ("tutorial", 7),
    ("introduction", 6), ("intro", 5), ("overview", 5), ("guide", 4),
    ("example", 4), ("changelog", 4), ("faq", 3), ("index", 2), ("readme", 3),
)
ZH_HINTS = ("zh", "cn", "chinese", "中文")


def _api(path: str, accept: str = "application/vnd.github+json"):
    """调用 GitHub 公开 API。返回 (状态码, 内容字节)。"""
    headers = {"Accept": accept, "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    status, body, _ = common.http_get(API + path, headers=headers, timeout=40)
    return status, body


def _api_json(path: str):
    status, body = _api(path)
    if status == 200:
        return json.loads(body.decode("utf-8", "replace")), None
    return None, f"{path} -> HTTP {status}"


def _truncate(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[:limit] + "\n\n<!-- 内容过长，已在此处截断；完整内容见原仓库 -->\n", True


def _flat(path: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "__", path).strip("_")[:120]


def _repo_meta(full_name: str):
    data, err = _api_json(f"/repos/{full_name}")
    if not data:
        return None, err
    lic = data.get("license") or {}
    return {
        "full_name": data.get("full_name"),
        "html_url": data.get("html_url"),
        "description": data.get("description"),
        "homepage": data.get("homepage"),
        "topics": data.get("topics") or [],
        "license": lic.get("spdx_id") or lic.get("name"),
        "language": data.get("language"),
        "stargazers_count_api": data.get("stargazers_count"),
        "forks_count_api": data.get("forks_count"),
        "open_issues_count": data.get("open_issues_count"),
        "default_branch": data.get("default_branch"),
        "created_at": data.get("created_at"),
        "pushed_at": data.get("pushed_at"),
        "archived": data.get("archived"),
    }, None


def _readme(full_name: str):
    data, err = _api_json(f"/repos/{full_name}/readme")
    if not data:
        return None, None, err
    text = ""
    if data.get("encoding") == "base64" and data.get("content"):
        text = base64.b64decode(data["content"]).decode("utf-8", "replace")
    else:
        status, body = _api(f"/repos/{full_name}/readme", accept="application/vnd.github.raw+json")
        if status == 200:
            text = body.decode("utf-8", "replace")
    info = {"path": data.get("path"), "html_url": data.get("html_url"), "sha": data.get("sha")}
    return text, info, None


def _raw_file(full_name: str, path: str, ref: str):
    quoted = urllib.parse.quote(path)
    status, body = _api(
        f"/repos/{full_name}/contents/{quoted}?ref={urllib.parse.quote(ref)}",
        accept="application/vnd.github.raw+json",
    )
    if status == 200:
        return body.decode("utf-8", "replace"), None
    return None, f"{path} -> HTTP {status}"


def _score_doc(path: str, readme_path: str | None) -> int:
    lower = path.lower()
    if not lower.endswith((".md", ".mdx", ".rst")):
        return 0
    if readme_path and path == readme_path:
        return 0
    depth = lower.count("/")
    if depth > 4:
        return 0
    if re.search(r"(^|/)(node_modules|vendor|third_party|\.github|test|tests|fixtures)/", lower):
        return 0
    name = lower.rsplit("/", 1)[-1]
    score = 0
    for kw, pts in DOC_KEYWORDS:
        if kw in name:
            score = max(score, pts)
    in_docs = lower.startswith(("docs/", "doc/", "documentation/", "examples/", "example/"))
    if depth == 0 and name.startswith("readme") and any(h in name for h in ZH_HINTS):
        score = max(score, 12)  # 中文版 README 最有用
    if depth == 0 and name.startswith("changelog"):
        score = max(score, 6)
    if in_docs and score:
        score += 2
    if in_docs and any(h in lower for h in ZH_HINTS) and score:
        score += 1
    if not in_docs and depth > 0 and not name.startswith("readme"):
        score -= 2
    return max(score - depth, 0) if score else 0


def fetch_full(full_name: str, out_dir, fetched_display: str) -> dict:
    """第 1 名：保存完整资料。返回 source 信息（也会写入 source.json）。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    errors, saved = [], []
    source = {
        "full_name": full_name,
        "html_url": f"https://github.com/{full_name}",
        "fetched_at": fetched_display,
        "kind": "full",
    }

    meta, err = _repo_meta(full_name)
    if meta:
        common.write_json(out_dir / "repo.json", meta)
        saved.append("repo.json")
        source.update({"default_branch": meta.get("default_branch"), "homepage": meta.get("homepage")})
    else:
        errors.append(err)
    branch = (meta or {}).get("default_branch")

    head_sha = None
    if branch:
        commit, err = _api_json(f"/repos/{full_name}/commits/{urllib.parse.quote(branch)}")
        if commit:
            head_sha = commit.get("sha")
            source["head_sha"] = head_sha
            source["head_commit_date"] = ((commit.get("commit") or {}).get("committer") or {}).get("date")
            source["head_commit_url"] = commit.get("html_url")
        else:
            errors.append(err)

    readme_info = None
    text, readme_info, err = _readme(full_name)
    if text is not None:
        text, cut = _truncate(text, README_MAX)
        common.write_text(out_dir / "official-readme.md", text)
        saved.append("official-readme.md")
        source["readme"] = dict(readme_info or {}, truncated=cut)
    elif err:
        errors.append(err)

    releases, err = _api_json(f"/repos/{full_name}/releases?per_page=5")
    if releases is not None:
        slim = []
        for rel in releases:
            body, cut = _truncate(rel.get("body") or "", RELEASE_BODY_MAX)
            slim.append({
                "tag_name": rel.get("tag_name"), "name": rel.get("name"),
                "published_at": rel.get("published_at"), "html_url": rel.get("html_url"),
                "prerelease": rel.get("prerelease"), "body": body, "body_truncated": cut,
            })
        common.write_json(out_dir / "releases.json", slim)
        saved.append("releases.json")
        source["latest_release"] = slim[0]["tag_name"] if slim else None
        source["release_count_saved"] = len(slim)
    elif err:
        errors.append(err)

    paths = []
    if head_sha:
        tree, err = _api_json(f"/repos/{full_name}/git/trees/{head_sha}?recursive=1")
        if tree:
            paths = [t["path"] for t in tree.get("tree", []) if t.get("type") == "blob"]
            shallow = [p for p in paths if p.count("/") <= 2][:TREE_MAX_LINES]
            header = (
                f"# {full_name} 的文件列表（提交 {head_sha[:12]}，只列到第 3 层，"
                f"共 {len(paths)} 个文件{'，GitHub 返回时已截断' if tree.get('truncated') else ''}）\n"
            )
            common.write_text(out_dir / "tree.txt", header + "\n".join(shallow) + "\n")
            saved.append("tree.txt")
        else:
            errors.append(err)

    readme_path = (readme_info or {}).get("path")
    ranked = sorted(
        ((s, p) for p in paths if (s := _score_doc(p, readme_path)) > 0),
        key=lambda sp: (-sp[0], len(sp[1]), sp[1]),
    )
    total, docs_saved = 0, []
    for _, path in ranked:
        if len(docs_saved) >= DOC_MAX_FILES or total >= DOC_TOTAL_MAX:
            break
        text, err = _raw_file(full_name, path, head_sha)
        if text is None:
            errors.append(err)
            continue
        text, cut = _truncate(text, DOC_FILE_MAX)
        name = "docs/" + _flat(path)
        common.write_text(out_dir / name, text)
        total += len(text)
        docs_saved.append({
            "saved_as": name, "original_path": path, "truncated": cut,
            "html_url": f"https://github.com/{full_name}/blob/{head_sha}/{urllib.parse.quote(path)}",
        })
    source["docs_saved"] = docs_saved
    source["files_saved"] = saved
    source["errors"] = [e for e in errors if e]
    common.write_json(out_dir / "source.json", source)
    return source


def fetch_light(full_name: str, out_dir, fetched_display: str) -> dict:
    """第 2～5 名：只保存基本信息和 README 开头。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    errors, saved = [], []
    source = {
        "full_name": full_name,
        "html_url": f"https://github.com/{full_name}",
        "fetched_at": fetched_display,
        "kind": "light",
    }
    meta, err = _repo_meta(full_name)
    if meta:
        common.write_json(out_dir / "repo.json", meta)
        saved.append("repo.json")
    else:
        errors.append(err)
    text, info, err = _readme(full_name)
    if text is not None:
        head = "\n".join(text.splitlines()[:150])
        head, _ = _truncate(head, 12_000)
        common.write_text(out_dir / "official-readme-head.md", head + "\n")
        saved.append("official-readme-head.md")
        source["readme"] = info
    elif err:
        errors.append(err)
    source["files_saved"] = saved
    source["errors"] = [e for e in errors if e]
    common.write_json(out_dir / "source.json", source)
    return source


def dir_name(rank: int, full_name: str) -> str:
    return f"{rank}-{full_name.replace('/', '__')}"


def fetch_all(key: str, snapshot: dict) -> dict:
    """为一期保存资料。已保存过的项目不重复抓取。返回汇总信息。"""
    base = common.materials_dir(key)
    summary = {"saved": [], "errors": []}
    for item in snapshot["items"][: snapshot.get("top_n", common.TOP_N)]:
        out_dir = base / dir_name(item["rank"], item["full_name"])
        existing = common.read_json(out_dir / "source.json")
        if existing and existing.get("files_saved"):
            summary["saved"].append(existing)
            continue
        try:
            fn = fetch_full if item["rank"] == 1 else fetch_light
            src = fn(item["full_name"], out_dir, snapshot.get("fetched_at_display", ""))
            summary["saved"].append(src)
            summary["errors"].extend(f"{item['full_name']}: {e}" for e in src.get("errors", []))
        except Exception as err:
            summary["errors"].append(f"{item['full_name']}: {type(err).__name__}: {err}")
    return summary
