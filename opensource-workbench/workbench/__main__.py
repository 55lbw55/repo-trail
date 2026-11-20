"""Command line for 开源工作台."""

import argparse
import sqlite3
import sys
from pathlib import Path

from platformdirs import user_cache_path

from . import __version__
from .contribution import contribution_draft
from .github import GitHub, WorkbenchError
from .reuse import reuse_plan, search


def parser():
    command = argparse.ArgumentParser(prog="python -m workbench", description="开源工作台")
    command.add_argument("--version", action="version", version=__version__)
    command.add_argument("--cache-dir", type=Path, help="覆盖平台默认的用户缓存目录")
    cache_mode = command.add_mutually_exclusive_group()
    cache_mode.add_argument("--offline", action="store_true", help="仅用已有公开缓存")
    cache_mode.add_argument("--refresh", action="store_true", help="重新查询 GitHub REST")
    actions = command.add_subparsers(dest="action", required=True)

    find = actions.add_parser("search", help="检索最多五个公开仓库")
    find.add_argument("--feature", required=True, help="功能描述，仅用于本地评估")
    find.add_argument("--language", required=True)
    find.add_argument("--limit", choices=range(1, 6), type=int, default=5)
    plan = actions.add_parser("reuse-plan", help="核对复用计划或创建本地审查分支")
    plan.add_argument("--repo", required=True)
    plan.add_argument("--ref", default="HEAD", help="HEAD 或完整 SHA")
    plan.add_argument("--file", action="append", default=[], help="候选文件，可重复")
    plan.add_argument("--strategy", choices=("dependency", "vendor"), default="dependency")
    plan.add_argument("--license-reviewed", action="store_true", help="人工确认许可范围和兼容性")
    plan.add_argument("--branch", help="显式创建 workbench/… 隔离分支")
    plan.add_argument("--requirement", help="显式指定 package==version")
    plan.add_argument("--version-file", help="上游版本声明文件")
    plan.add_argument("--version-evidence", help="上游版本赋值原文")
    plan.add_argument("--release-tag", help="核对与 commit 对应的 GitHub 发行标签")
    plan.add_argument("--patch", type=Path, help="本地审查补丁输出")
    for action in (find, plan):
        action.add_argument("--platform", required=True)
        action.add_argument("--project", required=True, type=Path)

    draft = actions.add_parser("contribution-draft", help="核对并准备单个本地贡献草稿")
    draft.add_argument("--repo", required=True)
    draft.add_argument("--ref", default="HEAD", help="HEAD 或完整 SHA")
    draft.add_argument("--kind", choices=("docs", "platform", "good-first"), default="docs")
    draft.add_argument("--issue", type=int, help="人工核对过的现有 Issue 编号")
    draft.add_argument("--related-pr", type=int, help="已有覆盖此变更的 PR 编号，仅生成本地验证材料")
    draft.add_argument("--evidence", type=Path, help="公开证据与精确编辑 JSON")
    draft.add_argument("--policy-reviewed", action="store_true", help="人工核对上游规则和外链")
    draft.add_argument("--human-pr-body", action="store_true", help="仅生成补丁和证据，正文由贡献者填写")
    draft.add_argument("--related-reviewed", action="store_true", help="人工判断列出的 Issue 和 PR 均非重复")
    draft.add_argument("--route", choices=("issue", "direct-pr"), default="issue")
    draft.add_argument("--patch", type=Path, help="本地补丁输出")
    draft.add_argument("--publish", choices=("issue", "pr"), help="生成可交接给 Chrome 的发布审查稿")
    draft.add_argument("--publish-out", type=Path, help="单独输出将进入 GitHub 表单的标题和正文")
    draft.add_argument("--open-chrome", action="store_true", help="打开表单，最后的提交按钮留给审核后的操作")
    draft.add_argument("--pr-base", help="GitHub 上游目标分支")
    draft.add_argument("--pr-head", help="已推送并审查的 GitHub 分支，格式 owner:branch")
    draft.add_argument("--pr-head-sha", help="已核对的远端 head 完整 SHA")
    draft.add_argument("--scan", action="store_true", help="按项目规模抽查 Markdown，以单个线索为上限")
    draft.add_argument("--scope", help="抽查目录或文件，相对仓库根目录")
    draft.add_argument("--reference", help="可选 Go 文件，用 mapstructure 或 Cobra 定义对照示例")
    draft.add_argument("--local-repo", type=Path, help="从已在本地的 Git 对象读取固定版本")
    draft.add_argument("--scan-rounds", type=int, choices=range(1, 11), default=2, metavar="1–10")
    draft.add_argument("--scan-max-files", type=int, choices=range(1, 61), default=25, metavar="1–60")

    for action in (find, plan, draft):
        action.add_argument("--keywords", required=True, help="可发送给 GitHub 的公开关键词")
        action.add_argument("--out", type=Path, help="Markdown 输出，默认标准输出")
    return command


def output_path(path):
    if path:
        if path.exists() or path.is_symlink() or not path.parent.is_dir():
            raise WorkbenchError("输出须使用位于已有目录中的新文件路径。")


def cache_directory(explicit, offline):
    if explicit is not None:
        return explicit
    default = user_cache_path("repo-trail", appauthor=False)
    if offline and not (default / "public.sqlite3").is_file():
        legacy = Path.cwd() / ".workbench-cache"
        if (legacy / "public.sqlite3").is_file():
            return legacy
    return default


def main():
    args = parser().parse_args()
    api = None
    try:
        patch = getattr(args, "patch", None)
        publish_out = getattr(args, "publish_out", None)
        paths = [path for path in (args.out, patch, publish_out) if path is not None]
        for path in paths:
            output_path(path)
        if len({path.resolve() for path in paths}) != len(paths):
            raise WorkbenchError("报告、补丁、发布审查稿须使用不同的文件路径。")
        if hasattr(args, "project") and not args.project.is_dir():
            raise WorkbenchError("--project 须指向存在的本地目录。")
        if args.action == "reuse-plan" and bool(args.branch) != bool(patch):
            raise WorkbenchError("创建复用审查时须同时提供 --branch 和 --patch。")
        if args.action == "contribution-draft" and args.issue is not None and args.issue < 1:
            raise WorkbenchError("Issue 编号须为正整数。")
        if args.action == "contribution-draft" and args.related_pr is not None and args.related_pr < 1:
            raise WorkbenchError("PR 编号须为正整数。")
        if args.action == "contribution-draft" and args.scan and (args.evidence or patch or args.issue or args.related_pr):
            raise WorkbenchError("请先用 --scan 发现候选，再用证据与 Issue 编号单独准备草稿。")
        if args.action == "contribution-draft" and args.scan and args.kind == "good-first":
            raise WorkbenchError("good-first 使用维护者标签检索，请省略 --scan。")
        if args.action == "contribution-draft" and not args.scan and (args.scope or args.reference):
            raise WorkbenchError("--scope 和 --reference 仅用于 --scan。")
        if args.action == "contribution-draft" and args.route == "direct-pr" and not args.policy_reviewed:
            raise WorkbenchError("准备直接 PR 前须人工核对贡献规则和外链。")
        if args.action == "contribution-draft":
            if args.publish and (args.offline or args.scan or not args.evidence or not args.policy_reviewed or not publish_out):
                raise WorkbenchError("发布审查需要联网、证据、--policy-reviewed 和 --publish-out。")
            if not args.publish and (publish_out or args.open_chrome):
                raise WorkbenchError("--publish-out 和 --open-chrome 必须与 --publish 一起使用。")
            if args.publish == "pr" and (not patch or not args.pr_base or not args.pr_head or not args.pr_head_sha):
                raise WorkbenchError("PR 发布审查需要 --patch、--pr-base、--pr-head 和 --pr-head-sha。")
            if args.publish != "pr" and (args.pr_base or args.pr_head or args.pr_head_sha):
                raise WorkbenchError("PR 分支参数仅用于 --publish pr。")
        api = GitHub(cache_directory(args.cache_dir, args.offline), args.offline, args.refresh)
        handler = {"search": search, "reuse-plan": reuse_plan, "contribution-draft": contribution_draft}
        content = "\n".join(handler[args.action](api, args)).rstrip() + "\n"
        if args.out:
            with args.out.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
        else:
            print(content, end="")
        return 0
    except WorkbenchError as error:
        print(f"开源工作台 · {error}", file=sys.stderr)
        return 1
    except (OSError, sqlite3.Error):
        print("开源工作台 · 无法读写本地文件或公开缓存。", file=sys.stderr)
        return 1
    finally:
        if api:
            api.db.close()


if __name__ == "__main__":
    raise SystemExit(main())
