"""Unauthenticated, cached reads from the GitHub REST API."""

import base64
import json
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener


class WorkbenchError(Exception):
    pass


class ResourceUnavailable(WorkbenchError):
    pass


class RateLimited(WorkbenchError):
    pass


class CacheMiss(WorkbenchError):
    pass


def repo_name(value):
    value = value.removeprefix("https://github.com/").rstrip("/").removesuffix(".git")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", value):
        raise WorkbenchError("仓库须为 owner/repo 或 GitHub 仓库 URL。")
    if value.split("/")[1] in {".", ".."}:
        raise WorkbenchError("仓库名无效。")
    return value


def public_path(value):
    if (
        not value or value.startswith("/") or "\\" in value
        or any(ord(char) < 32 for char in value)
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise WorkbenchError("上游文件路径无效。")
    return value


def blob_link(repo, sha, path, line=None):
    url = f"https://github.com/{repo}/blob/{sha}/{quote(public_path(path), safe='/')}"
    return f"{url}#L{line}" if line else url


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class GitHub:
    def __init__(self, directory: Path, offline=False, refresh=False):
        directory.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(directory / "public.sqlite3")
        self.db.execute("CREATE TABLE IF NOT EXISTS cache (url TEXT PRIMARY KEY, at REAL, body TEXT)")
        self.db.execute("CREATE TABLE IF NOT EXISTS limits (bucket TEXT PRIMARY KEY, until REAL)")
        self.offline = offline
        self.refresh = refresh
        self.opener = build_opener(NoRedirect())

    def get(self, path, params=None, *, ttl=900):
        url = "https://api.github.com" + path
        if params:
            url += "?" + urlencode(sorted(params.items()))
        cached = self.db.execute("SELECT at, body FROM cache WHERE url = ?", (url,)).fetchone()
        if cached and (self.offline or not self.refresh and time.time() - cached[0] < ttl):
            return json.loads(cached[1])
        if self.offline:
            raise CacheMiss("离线模式缺少对应的公开查询缓存。")

        bucket = "search" if path.startswith("/search/") else "core"
        hold = self.db.execute(
            "SELECT max(until) FROM limits WHERE bucket IN (?, 'all')", (bucket,)
        ).fetchone()[0]
        if hold and hold > time.time():
            self.rate_error(hold)
        request = Request(url, method="GET", headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "repo-trail-opensource-workbench",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        try:
            with self.opener.open(request, timeout=25) as response:
                body = json.load(response)
                if response.headers.get("X-RateLimit-Remaining") == "0":
                    self.hold(bucket, response.headers.get("X-RateLimit-Reset"), time.time() + 60)
        except HTTPError as error:
            with error:
                if error.code == 404:
                    raise ResourceUnavailable("GitHub REST 返回 404，公开资源不可用。") from None
                message = error.read(8192).lower()
                retry = error.headers.get("Retry-After")
                primary = error.headers.get("X-RateLimit-Remaining") == "0"
                if error.code in {403, 429} and (retry or primary or b"rate limit" in message or error.code == 429):
                    if retry and retry.isdecimal():
                        until = time.time() + int(retry)
                        self.rate_error(self.hold("all", until, time.time() + 60))
                    if primary:
                        reset = error.headers.get("X-RateLimit-Reset")
                        self.rate_error(self.hold(bucket, reset, time.time() + 60))
                    self.rate_error(self.hold("all", time.time() + 60, time.time() + 60))
                raise WorkbenchError(f"GitHub REST 返回 HTTP {error.code}。") from None
        except (URLError, TimeoutError, ValueError):
            raise WorkbenchError("GitHub REST 请求失败，可检查网络或使用已有离线缓存。") from None
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO cache VALUES (?, ?, ?)", (url, time.time(), json.dumps(body)))
        return body

    def hold(self, bucket, until, fallback):
        try:
            until = float(until)
        except (ValueError, TypeError):
            until = fallback
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO limits VALUES (?, ?)", (bucket, until))
        return until

    @staticmethod
    def rate_error(until):
        stamp = datetime.fromtimestamp(until, timezone.utc).isoformat(timespec="seconds")
        raise RateLimited(f"GitHub REST 已限流，下次可请求时间为 {stamp}。已有查询可用 --offline。")

    def snapshot(self, repo, ref="HEAD"):
        if ref != "HEAD" and not re.fullmatch(r"[0-9a-f]{40}", ref):
            raise WorkbenchError("指定的上游 commit 必须是完整的 40 位 SHA。")
        return Snapshot(self, repo_name(repo), ref)


class Snapshot:
    def __init__(self, api, repo, ref):
        self.api = api
        self.repo = repo
        self.endpoint = f"/repos/{repo}"
        commit = api.get(f"{self.endpoint}/commits/{ref}", ttl=900 if ref == "HEAD" else 31_536_000)
        self.sha = commit["sha"]
        tree_sha = commit["commit"]["tree"]["sha"]
        tree = api.get(f"{self.endpoint}/git/trees/{tree_sha}", {"recursive": 1}, ttl=31_536_000)
        self.incomplete = bool(tree.get("truncated"))
        self.paths = {row["path"] for row in tree["tree"]}
        self.files = {
            row["path"]: row for row in tree["tree"]
            if row["type"] == "blob" and row["mode"] in {"100644", "100755"}
        }

    @property
    def commit_link(self):
        return f"https://github.com/{self.repo}/commit/{self.sha}"

    def link(self, path, line=None):
        return blob_link(self.repo, self.sha, path, line)

    def read(self, path):
        if path not in self.files or self.files[path].get("size", 0) > 262144:
            raise ResourceUnavailable("上游文件不存在、不是普通文件或超过 256 KiB。")
        data = self.api.get(
            f"{self.endpoint}/git/blobs/{self.files[path]['sha']}", ttl=31_536_000
        )
        if data.get("encoding") != "base64":
            raise WorkbenchError("无法识别上游文件编码。")
        return base64.b64decode(data["content"])

    def text(self, path):
        try:
            return self.read(path).decode("utf-8")
        except UnicodeDecodeError:
            raise ResourceUnavailable("第一版仅分析 UTF-8 文本。") from None

    def root_file(self, *names):
        return next((path for path in self.files if path.casefold() in names), None)

    def policy_paths(self):
        result = []
        for path in self.files:
            low = path.casefold()
            name = PurePosixPath(low).name
            if (
                name.split(".")[0] in {"contributing", "agents", "claude", "gemini", "ai_policy", "ai-policy", "llms",
                                        "issue_template", "pull_request_template", "code_of_conduct"}
                or low.startswith((".github/issue_template/", ".github/pull_request_template/"))
                or re.search(r"(?:ai|llm|generative)[_-](?:usage|contributions?|policy|guidelines)", low)
                or low == ".github/copilot-instructions.md"
            ):
                result.append(path)
        readme = self.root_file("readme.md", "readme.rst", "readme")
        return ([readme] if readme else []) + sorted(result)
