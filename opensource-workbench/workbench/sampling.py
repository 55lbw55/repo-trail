"""Budgeted sampling of static evidence in public documentation."""

import posixpath
import re
import shlex
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from hashlib import sha256
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

from .github import CacheMiss, RateLimited, ResourceUnavailable, WorkbenchError, public_path
from .reuse import inline

DOCS = {".md", ".mdx", ".markdown"}
EXCLUDED = {"node_modules", "vendor", "third_party", "testdata", "__snapshots__", "_build"}
LINK = re.compile(r"(?<![!\\])\[[^\[\]\n]*\]\(<?([^\s()<>]+)>?(?:\s+\"[^\"]*\")?\)")
FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})\s*([\w+-]*)")
CONFIG_KEY = re.compile(r"^\s+([A-Za-z][\w-]*)\s*:")
GO_TAG = re.compile(r'\bmapstructure:"([A-Za-z][\w-]*)(?:,[^"]*)?"')
GO_IMPORT = re.compile(r'^\s*(?:import\s+)?(?:(\w+)\s+)?"(github\.com/[^"]+)"', re.M)
GO_SQUASH = re.compile(r'^\s*(?:\w+\s+)?\*?(\w+)\.(\w+)\s+`[^`]*mapstructure:",squash"', re.M)
COBRA_COMMAND = re.compile(r'^\s*(\w+)\s*:?=\s*&cobra\.Command\{([^{}]*)', re.M)
COBRA_USE = re.compile(r'\bUse:\s*"(\w[\w-]*)\s+([A-Z][A-Z0-9_-]*)"')
COBRA_FLAG = re.compile(r'\b(\w+)\.Flags\(\)\.(String|StringSlice|Int|Bool)(P)?\("([\w-]+)"(?:,\s*"([\w-]+)")?')


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    before: str
    after: str
    reference: str
    reference_line: int | None = None


def document(path, row):
    file = PurePosixPath(path)
    return file.suffix.lower() in DOCS and row.get("size", 0) <= 262144 and not EXCLUDED.intersection(file.parts)


def scale(file_count, doc_count):
    if file_count >= 1000 or doc_count >= 200:
        return "大型"
    return "中型" if file_count >= 200 or doc_count >= 40 else "小型"


def sample_order(paths, keywords, sha):
    lowered = [word.casefold() for word in keywords]

    def rank(path):
        folded = path.casefold()
        hits = sum(word in folded for word in lowered)
        digest = sha256(f"{sha}\0{path}".encode()).digest()
        return (-hits, digest)

    return sorted(paths, key=rank)


def markdown_parts(source):
    fence = None
    body = []
    paragraph = []
    examples = []
    for number, line in enumerate(source.splitlines(), 1):
        marker = FENCE.match(line)
        if marker and fence is None:
            fence = marker.groups()
        elif marker and marker[1][0] == fence[0][0] and len(marker[1]) >= len(fence[0]) and not marker[2]:
            examples.append((fence[1].lower(), body))
            fence, body = None, []
        elif fence:
            body.append((number, line))
        else:
            paragraph.append((number, re.sub(r"`+[^`\n]*`+", "", line)))
    return paragraph, examples


def link_finding(path, paragraph, all_paths, by_name):
    for number, line in paragraph:
        for match in LINK.finditer(line):
            target = match[1]
            try:
                url = urlsplit(target)
            except ValueError:
                continue
            relative = unquote(url.path)
            if url.scheme or url.netloc or not relative or relative.startswith("/") or url.query or "\\" in relative:
                continue
            destination = posixpath.normpath(posixpath.join(posixpath.dirname(path), relative))
            if destination in all_paths or destination.startswith("../"):
                continue
            choices = by_name.get(posixpath.basename(relative).casefold(), [])
            if len(choices) == 1 and choices[0] != path:
                replacement = posixpath.relpath(choices[0], posixpath.dirname(path) or ".")
                if re.fullmatch(r"[A-Za-z0-9._/-]+", replacement):
                    suffix = f"#{url.fragment}" if url.fragment else ""
                    return Finding(path, number, target, replacement + suffix, choices[0])
    return None


def config_finding(path, examples, tags):
    for language, block in examples:
        if language not in {"yaml", "yml"}:
            continue
        keys = [(line, match[1]) for line, source in block if (match := CONFIG_KEY.match(source))]
        if not any(key in tags for _, key in keys):
            continue
        for line, key in keys:
            if key in tags or len(key) < 4:
                continue
            scores = sorted(
                ((SequenceMatcher(None, key, tag).ratio(), tag) for tag in tags),
                reverse=True,
            )
            if not scores:
                continue
            score, tag = scores[0]
            if score >= 0.65 and (min(len(key), len(tag)) >= 5 or tag.startswith(key)) and (
                len(scores) == 1 or score - scores[1][0] >= 0.12
            ):
                tag_path, tag_line = tags[tag]
                return Finding(path, line, f"{key}:", f"{tag}:", tag_path, tag_line)
    return None


def config_tags(snapshot, reference, source):
    files = [(reference, source)]
    root = f"github.com/{snapshot.repo}/"
    imports = {
        alias or posixpath.basename(module): module[len(root):] for alias, module in GO_IMPORT.findall(source)
        if module.startswith(root) and all(part not in {"", ".", ".."} for part in module[len(root):].split("/"))
    }
    dependencies = {}
    for alias, type_name in GO_SQUASH.findall(source):
        if alias in imports:
            path = posixpath.join(imports[alias], "config.go")
            if path != reference and path in snapshot.files:
                dependencies.setdefault(path, set()).add(type_name)
    for path, type_names in list(dependencies.items())[:3]:
        shared = snapshot.text(path)
        lines = shared.splitlines(keepends=True)
        selected = set()
        for index, line in enumerate(lines):
            if any(re.match(rf"^type\s+{re.escape(name)}\s+struct\s*{{", line) for name in type_names):
                for number in range(index + 1, len(lines)):
                    if lines[number].startswith("}"):
                        break
                    selected.add(number)
        files.append((path, "".join(line if i in selected else "\n" for i, line in enumerate(lines))))
    return {
        match[1]: (path, line) for path, contents in reversed(files)
        for line, text in enumerate(contents.splitlines(), 1) for match in GO_TAG.finditer(text)
    }


def cobra_commands(source):
    flags = defaultdict(dict)
    for variable, kind, short_form, long, short in COBRA_FLAG.findall(source):
        flags[variable]["--" + long] = kind != "Bool"
        if short_form and short:
            flags[variable]["-" + short] = kind != "Bool"
    commands = {}
    ambiguous = set()
    for match in COBRA_COMMAND.finditer(source):
        variable, block = match.groups()
        usage = COBRA_USE.search(block)
        if not usage or not re.search(r"\bArgs:\s*cobra\.ExactArgs\(1\)", block):
            continue
        name, argument = usage.groups()
        if name in commands:
            ambiguous.add(name)
        line = source.count("\n", 0, match.start(2) + usage.start()) + 1
        commands[name] = (argument, line, flags[variable])
    return {name: value for name, value in commands.items() if name not in ambiguous}


def positional_count(tokens, flags):
    remaining = iter(tokens)
    count = 0
    for token in remaining:
        if token == "--":
            return count + sum(1 for _ in remaining)
        if not token.startswith("-"):
            count += 1
            continue
        name, separator, value = token.partition("=")
        if name not in flags:
            return None
        if flags[name] and not separator:
            value = next(remaining, "")
            if not value or value.startswith("-"):
                return None
    return count


def command_finding(path, examples, reference, program, commands):
    for language, block in examples:
        if language not in {"", "bash", "sh", "shell", "zsh"}:
            continue
        for line, source in block:
            if not source.lstrip().startswith(program + " ") or re.search(r"[|;&<>`$]", source) or source.rstrip().endswith("\\"):
                continue
            try:
                tokens = shlex.split(source, comments=True)
            except ValueError:
                continue
            if len(tokens) < 2 or tokens[1] not in commands:
                continue
            argument, code_line, flags = commands[tokens[1]]
            if positional_count(tokens[2:], flags) == 0:
                return Finding(path, line, source.strip()[:180], f"{tokens[1]} {argument} · cobra.ExactArgs(1)",
                               reference, code_line)
    return None


def scan(snapshot, args, keywords):
    paths = [path for path, row in snapshot.files.items() if document(path, row)]
    size = scale(len(snapshot.files), len(paths))
    scope = public_path(args.scope.rstrip("/")) if args.scope else None
    if scope:
        paths = [path for path in paths if path == scope or path.startswith(scope + "/")]
    if not paths:
        raise WorkbenchError("抽查范围内没有符合条件的 Markdown 文件。")
    ordered = sample_order(paths, keywords, snapshot.sha)
    round_size = min(len(paths), 12) if size == "小型" else (len(paths) + 19) // 20
    budget = min(len(paths), args.scan_max_files, round_size * args.scan_rounds)
    strategy = "小型项目每轮最多 12 个" if size == "小型" else "每轮约 5%，向上取整，至少 1 个"
    report = [
        "# 贡献抽查", "",
        f"目标 · [{inline(snapshot.repo)}]({snapshot.commit_link})",
        f"证据来源 · {'本地 Git 对象' if args.local_repo else 'GitHub REST 文件树与 blob'}",
        f"规模 · {size}（文件树列出 {len(snapshot.files)} 个普通文件）",
        f"抽查范围 · {inline(scope or '整个仓库')} · {len(paths)} 个符合条件的 Markdown 文件",
        f"计划 · {strategy}。每轮最多 {round_size} 个，最多 {args.scan_rounds} 轮，本次最多读取 {budget} 个文档。",
        "依据路径关键词优先，分数相同时按固定 commit 的散列排序。命中首个候选即停止。",
        "",
    ]
    if snapshot.incomplete:
        report += ["GitHub 返回的文件树不完整，已暂停基于路径缺失的抽查。"]
        return report
    by_name = defaultdict(list)
    for path in snapshot.files:
        if PurePosixPath(path).suffix.lower() in DOCS:
            by_name[posixpath.basename(path).casefold()].append(path)
    tags = {}
    commands = {}
    reference = None
    if args.reference:
        reference = public_path(args.reference)
        if not reference.endswith(".go"):
            raise WorkbenchError("源码对照目前支持含 mapstructure 或 Cobra 命令定义的 Go 文件。")
        try:
            source = snapshot.text(reference)
            tags = config_tags(snapshot, reference, source)
        except (RateLimited, CacheMiss) as error:
            return report + [f"源码对照待完成。{error}"]
        commands = cobra_commands(source)
        if not tags and not commands:
            raise WorkbenchError("指定的 Go 文件没有可识别的 mapstructure 或 Cobra 命令定义。")
        report += [f"源码对照 · [{inline(reference)}]({snapshot.link(reference)})", ""]
    result = None
    reads = 0
    stopped = False
    for turn, offset in enumerate(range(0, budget, round_size), 1):
        batch = ordered[offset:min(offset + round_size, budget)]
        checked = []
        skipped = []
        for path in batch:
            try:
                text = snapshot.text(path)
            except (RateLimited, CacheMiss) as error:
                report += [str(error)]
                stopped = True
                break
            except ResourceUnavailable:
                skipped.append(path)
                continue
            reads += 1
            checked.append(path)
            paragraph, examples = markdown_parts(text)
            result = config_finding(path, examples, tags) if tags else None
            if not result and commands:
                result = command_finding(path, examples, reference, snapshot.repo.split("/")[-1], commands)
            result = result or link_finding(path, paragraph, snapshot.paths, by_name)
            if result:
                break
        report += [f"## 第 {turn} 轮", "", f"实际检查 {len(checked)} / 本轮计划 {len(batch)} 个文件。"]
        report += [f"- [{inline(path)}]({snapshot.link(path)})" for path in checked]
        report += [f"- 跳过不可读文件 [{inline(path)}]({snapshot.link(path)})" for path in skipped]
        report += [""]
        if result or stopped:
            break
    report += [f"累计覆盖 · {reads}/{len(paths)}（{reads / len(paths):.1%}）。", ""]
    if result:
        report += [
            "## 单个待核对线索", "",
            f"- 实际 [{inline(result.path)} 第 {result.line} 行]({snapshot.link(result.path, result.line)}) · {inline(result.before)}",
            f"- 对照 [{inline(result.reference)}]({snapshot.link(result.reference, result.reference_line)}) · {inline(result.after)}",
            "- 用该线索核对上游规则、已有 Issue/PR 和实际影响，再准备草稿与补丁。",
        ]
    elif not stopped:
        report += ["本次抽查未发现支持的线索。覆盖范围以报告为准。"]
    return report
