"""Command line for 开源工作台."""

import argparse
import sqlite3
import sys
from pathlib import Path

from platformdirs import user_cache_path

from .contribution import contribution_draft
from .github import GitHub, WorkbenchError
from .reuse import reuse_plan, search


def parser():
    command = argparse.ArgumentParser(prog="python -m workbench", description="开源工作台")
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
    draft.add_argument("--evidence", type=Path, help="公开证据与精确编辑 JSON")
    draft.add_argument("--policy-reviewed", action="store_true", help="人工核对上游规则和外链")
    draft.add_argument("--related-reviewed", action="store_true", help="人工判断列出的 Issue 和 PR 均非重复")
    draft.add_argument("--route", choices=("issue", "direct-pr"), default="issue")
    draft.add_argument("--patch", type=Path, help="本地补丁输出")

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
        output_path(args.out)
        output_path(patch)
        if patch and args.out and patch.resolve() == args.out.resolve():
            raise WorkbenchError("报告和补丁须使用不同的文件路径。")
        if hasattr(args, "project") and not args.project.is_dir():
            raise WorkbenchError("--project 须指向存在的本地目录。")
        if args.action == "reuse-plan" and bool(args.branch) != bool(patch):
            raise WorkbenchError("创建复用审查时须同时提供 --branch 和 --patch。")
        if args.action == "contribution-draft" and args.issue is not None and args.issue < 1:
            raise WorkbenchError("Issue 编号须为正整数。")
        if args.action == "contribution-draft" and args.route == "direct-pr" and not args.policy_reviewed:
            raise WorkbenchError("准备直接 PR 前须人工核对贡献规则和外链。")
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
