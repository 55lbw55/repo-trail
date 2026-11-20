"""Build reviewable Chrome handoffs without writing to GitHub."""

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlencode

from .github import WorkbenchError
from .reuse import inline

BRANCH = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_./-]{0,239}")
OWNER = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}")


@dataclass(frozen=True)
class Handoff:
    kind: str
    title: str
    body: str
    url: str
    prefill: bool = True
    head_sha: str | None = None

    def chrome_url(self):
        if not self.prefill:
            return self.url
        sep = "&" if "?" in self.url else "?"
        url = self.url + sep + urlencode({"title": self.title, "body": self.body})
        return url if len(url) <= 5000 else self.url

    def review(self, snapshot):
        lines = [
            f"# {self.kind} 发布审查", "",
            f"- 目标仓库 · {inline(snapshot.repo)}",
            f"- 核对过的 commit · [{snapshot.sha}]({snapshot.commit_link})",
            f"- [打开 GitHub 页面]({self.url})",
        ]
        if self.head_sha:
            lines += [f"- 远端 head · `{self.head_sha}`。提交前在比较页核对完整 diff 和分支。"]
        lines += [
            "", "先审核目标、标题和正文。GitHub 页面上的提交按钮是最后一步。",
            "", "## 标题", "", self.title, "", "## 正文", "", self.body,
        ]
        return "\n".join(lines).rstrip() + "\n"


def public_text(value):
    if re.search(r"(?i)github_pat_|\bgh[pousr]_[a-z0-9]|://[^/\s:@]+:[^/\s@]+@", value):
        raise WorkbenchError("发布正文疑似含凭据。")
    return value.strip()


def branch_ref(value):
    if (not BRANCH.fullmatch(value or "") or ".." in value or "//" in value or value.endswith(("/", "."))
        or any(part.startswith(".") or part.endswith(".lock") for part in value.split("/"))):
        raise WorkbenchError("GitHub 分支名称无效。")
    return value


def prepare_handoff(api, snapshot, args, spec, evidence, issue, syntax_checked):
    title = " ".join(public_text(spec["title"]).split())
    if not title or len(title) > 256:
        raise WorkbenchError("发布标题须为 1–256 个字符。")
    expected_path, expected_line, actual_path, actual_line = evidence
    expected_link = snapshot.link(expected_path, expected_line)
    actual_link = snapshot.link(actual_path, actual_line)
    support = (
        f"- [Observed behavior]({actual_link})\n"
        f"- [Expected behavior reference]({expected_link})"
    )
    if args.publish == "issue":
        meta = api.get(snapshot.endpoint, ttl=300)
        if not meta.get("has_issues") or meta.get("archived") or meta.get("disabled"):
            raise WorkbenchError("目标仓库当前不接收 Issue。")
        templates = bool(any(
            "issue_template" in path.casefold() for path in snapshot.policy_paths()
        ))
        url = f"https://github.com/{snapshot.repo}/issues/new" + ("/choose" if templates else "")
        body = (
            f"### Summary\n\n{spec['impact']}\n\n"
            f"### Actual behavior\n\n{spec['actual_behavior']}\n\n"
            f"### Expected behavior\n\n{spec['expected_behavior']}\n\n"
            f"### Evidence\n\n{support}"
        )
        if spec.get("assistance"):
            body += f"\n\nPrepared with assistance from {spec['assistance']}."
        return Handoff("Issue", title, public_text(body), url, prefill=not templates)

    owner, separator, head = (args.pr_head or "").partition(":")
    if not separator or not OWNER.fullmatch(owner):
        raise WorkbenchError("PR 需要 --pr-head owner:branch。")
    base = branch_ref(args.pr_base)
    head = branch_ref(head)
    compare = f"{quote(base, safe='')}...{owner}:{quote(head, safe='')}"
    response = api.get(f"{snapshot.endpoint}/compare/{compare}", {"per_page": 100}, ttl=60)
    base_sha = response.get("base_commit", {}).get("sha")
    commits = response.get("commits", [])
    head_sha = commits[-1].get("sha") if commits else None
    if (response.get("status") != "ahead" or base_sha != snapshot.sha
        or response.get("total_commits") != len(commits) or not re.fullmatch("[0-9a-f]{40}", head_sha or "")):
        raise WorkbenchError("远端比较结果与所审查的基础 commit 不符，或比较结果不完整。")
    expected_paths = {edit["path"] for edit in spec["edits"]}
    remote_paths = {file["filename"] for file in response.get("files", [])}
    if remote_paths != expected_paths:
        raise WorkbenchError("远端比较页的修改文件与审查补丁不符。")
    if args.pr_head_sha != head_sha:
        raise WorkbenchError("远端 head 与显式核对的 --pr-head-sha 不符。")
    body = (
        f"### Summary\n\n{spec['impact']}\n\n{spec['expected_behavior']}\n\n"
        f"### Evidence\n\n{support}\n\n"
        "### Verification\n\n"
        "- Checked the evidence and exact edit anchors at the base commit.\n"
        "- Checked and applied the local patch to the base files and compared the result byte for byte."
    )
    if syntax_checked:
        body += "\n- Parsed the edited Python files with Python's AST parser."
    if issue:
        body += f"\n\nRelated issue: #{issue['number']}."
    if spec.get("assistance"):
        body += f"\n\nPrepared with assistance from {spec['assistance']}."
    url = f"https://github.com/{snapshot.repo}/compare/{compare}?quick_pull=1"
    templates = any("pull_request_template" in path.casefold() for path in snapshot.policy_paths())
    return Handoff("PR", title, public_text(body), url, prefill=not templates, head_sha=head_sha)


def open_chrome(handoff):
    chrome = shutil.which("chrome") or shutil.which("google-chrome") or shutil.which("google-chrome-stable")
    if not chrome and os.name == "nt":
        for name in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
            directory = os.environ.get(name)
            if directory:
                candidate = Path(directory) / "Google" / "Chrome" / "Application" / "chrome.exe"
                if candidate.is_file():
                    chrome = candidate
                    break
    if not chrome:
        raise WorkbenchError("找不到 Chrome，可使用已生成的发布审查文件打开目标页面。")
    try:
        subprocess.Popen([chrome, handoff.chrome_url()])
    except OSError:
        raise WorkbenchError("无法启动 Chrome，发布审查文件仍可使用。") from None
