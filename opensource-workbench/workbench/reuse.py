"""Repository evidence, dependency-first assessment and guarded reuse reviews."""

import ast
import configparser
import re
import sys
from pathlib import PurePosixPath
from urllib.parse import quote

from .github import RateLimited, ResourceUnavailable, WorkbenchError, public_path
from .local import isolated_review, normalize_package, parse_manifest, project_dependencies

READMES = ("readme.md", "readme.rst", "readme.txt", "readme")
MANIFESTS = ("pyproject.toml", "setup.cfg", "setup.py", "package.json", "cargo.toml",
             "go.mod", "requirements.txt", "gemfile", "pom.xml")
PERMISSIVE = {"MIT", "BSD-2-Clause", "BSD-3-Clause", "ISC"}


def inline(value):
    value = re.sub(r"[\x00-\x1f\x7f]", " ", str(value))
    value = re.sub(r"(?i)(?:github_pat_[a-z0-9_]{16,}|gh[pousr]_[a-z0-9]{16,}|(?<=://)[^/\s:@]+:[^/\s@]+@)", "[已隐藏]", value)
    return "".join(f"&#{ord(ch)};" if ch in "&<>`[]*_!|@\\" else ch for ch in value)


def terms(value):
    if not re.fullmatch(r"[\w.+#-]+(?: +[\w.+#-]+){0,7}", value):
        raise WorkbenchError("公开关键词应为 1–8 个空格分隔的词，请避开限定符和本地资料。")
    if re.search(r"\b(?:github_pat_|gh[pousr]_)", value, re.I):
        raise WorkbenchError("公开关键词疑似包含凭据，查询已停止。")
    return value.split()


def relevant_lines(text, keywords, limit=3):
    result = []
    for index, line in enumerate(text.splitlines(), 1):
        hits = sum(term.casefold() in line.casefold() for term in keywords)
        if hits and line.strip() and not line.lstrip().startswith(("!", "[!", "<", "http", ".. image", ":target:")):
            result.append((hits, index, line.strip()[:200]))
    return [(index, line) for _, index, line in sorted(result, key=lambda row: (-row[0], row[1]))[:limit]]


def entries(snapshot, keywords):
    scores = []
    for path in snapshot.files:
        lower = path.casefold()
        file = PurePosixPath(lower)
        if file.suffix not in {".py", ".rs", ".go", ".ts", ".js", ".java", ".cs", ".c", ".cpp", ".rb", ".php"}:
            continue
        hits = sum(term.casefold() in lower for term in keywords)
        parts = set(file.parts)
        if parts & {"tests", "test", "docs", "examples", ".github"} or file.name.startswith("test"):
            continue
        score = 4 * hits + int(file.name in {"__init__.py", "index.ts", "lib.rs", "main.go"})
        score += 5 * sum(term.casefold() in file.stem for term in keywords)
        if file.name.startswith("__") and file.name != "__init__.py":
            score -= 1
        if score > 0:
            scores.append((-score, len(file.parts), path))
    return [path for _, _, path in sorted(scores)[:4]]


def package(snapshot, manifest):
    if not manifest:
        return None, None, []
    text = snapshot.text(manifest)
    if manifest.casefold() == "pyproject.toml":
        document = parse_manifest(text.encode())
        info = document.get("project") or document.get("tool", {}).get("poetry", {})
        dep = info.get("dependencies", [])
        if isinstance(dep, dict):
            dep = [key for key in dep if key.lower() != "python"]
        if info.get("name") or not (legacy := snapshot.root_file("setup.py", "setup.cfg")):
            return info.get("name"), info.get("version"), dep
        return package(snapshot, legacy)
    if manifest.casefold() in {"setup.py", "setup.cfg"}:
        if manifest.casefold() == "setup.cfg":
            config = configparser.ConfigParser(interpolation=None)
            config.read_string(text)
            return (config.get("metadata", "name", fallback=None),
                    config.get("metadata", "version", fallback=None),
                    config.get("options", "install_requires", fallback="").split())
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return None, None, []
        assignments = literal_assignments(tree)
        about = {}
        if isinstance(assignments.get("package"), str) and "__version__.py" in text:
            path = f"{assignments['package']}/__version__.py"
            if path in snapshot.files:
                try:
                    about = literal_assignments(ast.parse(snapshot.text(path)))
                except SyntaxError:
                    pass
        for call in ast.walk(tree):
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "setup":
                values = {}
                for item in call.keywords:
                    value = item.value
                    if item.arg not in {"name", "version", "install_requires"}:
                        continue
                    if isinstance(value, ast.Name):
                        values[item.arg] = assignments.get(value.id)
                    elif (isinstance(value, ast.Subscript) and isinstance(value.value, ast.Name)
                          and value.value.id == "about" and isinstance(value.slice, ast.Constant)
                          and isinstance(value.slice.value, str)):
                        values[item.arg] = about.get(value.slice.value)
                    else:
                        try:
                            values[item.arg] = ast.literal_eval(value)
                        except (ValueError, TypeError):
                            continue
                return values.get("name"), values.get("version"), values.get("install_requires") or []
    if manifest.casefold() == "package.json":
        import json
        document = json.loads(text)
        return document.get("name"), document.get("version"), list(document.get("dependencies", {}))
    if manifest.casefold() == "requirements.txt":
        return None, None, [line for line in text.splitlines() if line.strip() and not line.startswith(("#", "-"))][:12]
    return None, None, []


def literal_assignments(tree):
    result = {}
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
            try:
                result[statement.targets[0].id] = ast.literal_eval(statement.value)
            except (ValueError, TypeError):
                continue
    return result


def manifest_for(snapshot):
    return next((path for name in MANIFESTS if (path := snapshot.root_file(name))), None)


def license_id(metadata):
    return (metadata.get("license") or {}).get("spdx_id") or "UNKNOWN"


def notices(snapshot):
    return sorted(path for path in snapshot.files if re.match(
        r"^(?:licen[cs]e|copying|copyright|notice)(?:[._-]|$)", PurePosixPath(path).name, re.I
    ))


def evidence(snapshot, keywords, platform):
    readme = snapshot.root_file(*READMES)
    lines = []
    if readme:
        source = snapshot.text(readme)
        lines.extend(f"- [{inline(readme)} 第 {i} 行]({snapshot.link(readme, i)}) · {inline(line)}"
                     for i, line in relevant_lines(source, keywords))
        platform_hints = relevant_lines(source, [platform], 1)
        if platform_hints:
            line, content = platform_hints[0]
            lines.append(f"- 平台资料 [{inline(readme)} 第 {line} 行]({snapshot.link(readme, line)}) · {inline(content)}")
    return lines


def search(api, args):
    keywords = terms(args.keywords)
    local_deps = project_dependencies(args.project)
    feature_hints = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", args.feature)[:8]
    if not re.fullmatch(r"[A-Za-z0-9+#. -]{1,30}", args.language):
        raise WorkbenchError("语言应为 GitHub 支持的公开语言名称。")
    listings = api.get("/search/repositories", {
        "q": f'{args.keywords} language:"{args.language}" is:public archived:false',
        "per_page": args.limit,
    })
    report = [
        "# 公开仓库检索", "",
        f"公开查询词 · {inline(args.keywords)}  ",
        f"语言与目标平台 · {inline(args.language)} / {inline(args.platform)}", "",
        "从 GitHub 返回的候选中按本地功能、平台和依赖线索排序。平台匹配依据来自公开文档，接入成本为静态估计。", "",
    ]
    if listings.get("incomplete_results"):
        report += ["GitHub 标记本次搜索结果不完整。", ""]
    if not listings["items"]:
        report += ["没有符合查询的公开仓库。", ""]
    def priority(item):
        description = (item.get("description") or "").casefold()
        familiar = normalize_package(item["name"]) in local_deps
        return (-sum(hint.casefold() in description for hint in feature_hints),
                -(args.platform.casefold() in description), -int(familiar))

    for item in sorted(listings["items"], key=priority):
        if item.get("private"):
            continue
        snap = api.snapshot(item["full_name"])
        paths = entries(snap, keywords)
        manifest = manifest_for(snap)
        try:
            name, _, deps = package(snap, manifest)
        except RateLimited:
            raise
        except (ValueError, configparser.Error, WorkbenchError):
            name, deps = None, []
        report += [
            f"## {inline(snap.repo)}", "",
            f"- 核对版本 [{snap.sha[:12]}]({snap.commit_link})",
            f"- GitHub 许可证识别 · {inline(license_id(item))}",
            f"- 公开项目描述 · {inline(item.get('description') or '未提供')}",
        ]
        try:
            matches = evidence(snap, list(dict.fromkeys(keywords + feature_hints)), args.platform)
        except ResourceUnavailable:
            matches = []
        report += matches or ["- 当前读取范围内未找到 README 关键词证据。"]
        if paths:
            report += ["- 相关源码入口 · " + "、".join(f"[{inline(path)}]({snap.link(path)})" for path in paths)]
        else:
            report += ["- 当前文件索引未识别到相关源码入口。"]
        if manifest:
            declared = "、".join(inline(dep) for dep in list(deps)[:12]) or "未能静态识别，或清单未声明"
            report += [f"- 依赖入口 [{inline(manifest)}]({snap.link(manifest)}) · {declared}"]
        else:
            report += ["- 当前文件索引未识别到根目录依赖清单。"]
        report += [
            "- 许可未明确，暂停复制。接入前先核对包的许可证和发行状态。"
            if license_id(item) in {"NONE", "UNKNOWN", "NOASSERTION", "OTHER"} else
            f"- 优先核对现成依赖 **{inline(name)}**。接入成本预计较低，待验证包版本、依赖和平台行为。"
            if isinstance(name, str) else
            "- 接入成本待核定。先人工检查发布方式、公开 API 和运行依赖。",
            "",
        ]
    return report


def module_imports(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        raise WorkbenchError("当前 Python 版本无法静态解析该文件。") from None
    modules = set()
    dynamic = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.add("." * node.level + (node.module or "").split(".")[0])
        elif isinstance(node, ast.Name) and node.id in {"__import__", "eval", "exec", "__file__"}:
            dynamic = True
        elif isinstance(node, ast.Attribute) and node.attr in {"import_module", "exec_module", "get_data"}:
            dynamic = True
    return sorted(modules), dynamic


def reuse_plan(api, args):
    keywords = terms(args.keywords)
    current_deps = project_dependencies(args.project)
    snap = api.snapshot(args.repo, args.ref)
    manifest = manifest_for(snap)
    name, version, deps = package(snap, manifest)
    legal = notices(snap)
    root_license = snap.root_file("license", "license.md", "license.txt", "copying", "copying.txt")
    root_text = snap.text(root_license) if root_license else ""
    try:
        detected = api.get(f"{snap.endpoint}/license", {"ref": snap.sha}, ttl=31_536_000) if root_license else {}
    except ResourceUnavailable:
        detected = {}
    spdx = license_id(detected)
    if detected.get("sha") != snap.files.get(root_license, {}).get("sha"):
        spdx = "UNKNOWN"
    tag_link = None
    if args.release_tag:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,59}", args.release_tag):
            raise WorkbenchError("发行标签格式无效。")
        tag = quote(args.release_tag, safe="")
        commit = api.get(f"{snap.endpoint}/commits/{tag}")
        if commit["sha"] != snap.sha:
            raise WorkbenchError("发行标签未指向核对的 commit。")
        tag_link = f"https://github.com/{snap.repo}/tree/{tag}"
    paths = list(dict.fromkeys(public_path(path) for path in args.file)) or entries(snap, keywords)[:2]
    if any(path not in snap.files for path in paths):
        raise WorkbenchError("指定的上游文件不在核对的 commit 中。")
    report = [
        "# 复用计划", "",
        f"上游 · [{inline(snap.repo)}]({snap.commit_link})  ",
        f"核对 commit · {snap.sha}  ",
        f"目标平台 · {inline(args.platform)}", "",
        "## 功能与入口", "",
        *evidence(snap, keywords, args.platform),
        *[f"- [{inline(path)}]({snap.link(path)})" for path in paths],
        "", "## 依赖优先评估", "",
    ]
    if isinstance(name, str):
        report += [
            f"- 上游声明的包名 · **{inline(name)}**"
            + (f"，版本字段 · {inline(version)}" if version else "，版本需单独核对。"),
            "- 声明的直接依赖 · " + ("、".join(inline(dep) for dep in list(deps)[:20]) if deps else "清单无可静态确认的条目。"),
            "- 优先采用发行包。固定版本，核对发行包与来源 commit 的对应关系，"
            "在项目现有工具中解析锁文件并检查传递依赖和平台。",
        ]
    else:
        report += ["- 未识别到可直接采用的公开包名。先核对上游发行物和清单。"]
    if manifest:
        report += [f"- [上游依赖清单]({snap.link(manifest)})"]
    if tag_link:
        report += [f"- [GitHub 标签 {inline(args.release_tag)}]({tag_link}) 指向所核对的 commit。发行包内容仍待核对。"]
    report += ["", "## 许可证与摘取范围", "", f"- GitHub 对固定版本的许可证识别 · {inline(spdx)}"]
    report += [f"- [{inline(path)}]({snap.link(path)})" for path in legal[:20]]
    headers = [line.strip() for line in root_text.splitlines() if re.match(r"\s*(?:copyright\s*(?:\(c\)|©|\d)|©)", line, re.I)][:4]
    report += [f"- 许可证版权声明 · {inline(line[:180])}" for line in headers]
    report += [
        "- 摘取评估以上述源码入口为起点。保留文件内版权声明及适用的许可证和 NOTICE 原文。",
        "- 接入时核对调用边界、错误处理、Python 版本和平台资源；先在目标平台跑最小行为测试。",
    ]
    blockers = []
    if spdx not in PERMISSIVE or not root_text or not args.license_reviewed or snap.incomplete:
        blockers.append("许可证文本、兼容性确认或完整文件树不足。")
    copy = None
    if len(paths) == 1 and paths[0].endswith(".py"):
        source = snap.text(paths[0])
        definitions = [(i, line.strip()) for i, line in enumerate(source.splitlines(), 1)
                       if re.match(r"^(?:async )?def ", line) and any(word.casefold() in line.casefold() for word in keywords)]
        report += [f"- 功能入口 [{inline(line[:120])}]({snap.link(paths[0], i)})" for i, line in definitions[:3]]
        imported, dynamic = module_imports(source)
        report += ["- Python 静态导入 · " + ("、".join(inline(item) for item in imported) or "无")]
        report += [f"- 源文件版权标记 · {inline(line.strip()[:180])}"
                   for line in source.splitlines() if re.search(r"copyright|©|SPDX-License-Identifier", line, re.I)][:6]
        off_tree = set(imported) - sys.stdlib_module_names
        public_stdlib = set(imported) & sys.stdlib_module_names
        shadowed = any(PurePosixPath(path).stem in public_stdlib for path in snap.files if path.endswith(".py"))
        if off_tree or dynamic or shadowed:
            blockers.append("发现仓库内、第三方、动态导入或资源引用的可能，需人工追踪传递依赖。")
        if any(tag.strip() != spdx for tag in re.findall(r"SPDX-License-Identifier:\s*([^\r\n]+)", source)):
            blockers.append("文件 SPDX 标记与仓库许可证不一致。")
        if any("/" in path for path in legal) or len([p for p in legal if re.match(r"licen[cs]e|copying", p, re.I)]) != 1:
            blockers.append("检测到多份或目录级许可材料，需人工确认适用范围。")
        copy = paths[0]
    else:
        blockers.append("自动摘取的最小范围限于一个独立 Python 模块。")
    report += [f"- 暂停复制 · {reason}" for reason in blockers]
    if not blockers:
        report += ["- 静态检查通过；写入时保留源码原字节与根目录许可证、NOTICE 和版权文件。"]

    if not args.branch:
        return report
    source_record = ("# 上游来源\n\n" + f"- 仓库 [{snap.repo}]({snap.commit_link})\n"
                     + f"- Commit {snap.sha}\n- GitHub 识别的许可证 {inline(spdx)}\n")
    if tag_link:
        source_record += f"- [核对的 GitHub 标签 {inline(args.release_tag)}]({tag_link})\n"
    if args.strategy == "dependency":
        requirement = args.requirement
        if not requirement or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*==[0-9][A-Za-z0-9.]*", requirement):
            raise WorkbenchError("依赖写入需要简单精确版本，例如 package==1.2.3。")
        expected_name = normalize_package(requirement.split("==")[0])
        if not isinstance(name, str) or expected_name != normalize_package(name):
            raise WorkbenchError("指定的包名与核对 commit 中的声明不符。")
        if expected_name in current_deps:
            raise WorkbenchError("当前工作树已声明同名依赖，请先复用现有声明。")
        if version != requirement.split("==")[1] or args.version_file or args.version_evidence:
            if not args.version_file or not args.version_evidence:
                raise WorkbenchError("请提供该 commit 的版本文件和精确版本声明。")
            version_source = snap.text(public_path(args.version_file))
            wanted = requirement.split("==")[1]
            if (args.version_evidence not in version_source.splitlines()
                or not re.fullmatch(r"\s*(?:__version__|VERSION|version)\s*=\s*(['\"])"
                                    + re.escape(wanted) + r"\1\s*", args.version_evidence)):
                raise WorkbenchError("指定版本声明与文件或依赖版本不符。")
            source_record += f"- [版本声明]({snap.link(args.version_file)})\n"
        if not args.license_reviewed or spdx in {"NONE", "UNKNOWN", "NOASSERTION", "OTHER"} or not root_text:
            raise WorkbenchError("生成依赖分支前须核对上游许可证与目标项目的兼容性。")
        source_record += f"- 依赖 `{requirement}` · [包声明]({snap.link(manifest)})\n"
        changes = {f"third_party/workbench-{expected_name}.md": source_record.encode()}
        isolated_review(args.project, args.branch, changes, args.patch, requirement)
    else:
        if blockers or not copy:
            return report + ["", "未创建摘取分支，需先解决上述阻塞项。"]
        slug = snap.repo.lower().replace("/", "-")
        folder = f"third_party/workbench-{slug}"
        source_record += f"- [摘取文件]({snap.link(copy)})\n"
        for path in legal:
            source_record += f"- [许可材料]({snap.link(path)})\n"
        changes = {f"{folder}/upstream.py": snap.read(copy), f"{folder}/ORIGIN.md": source_record.encode()}
        changes.update({f"{folder}/{path}": snap.read(path) for path in legal})
        isolated_review(args.project, args.branch, changes, args.patch)
    return report + ["", "## 本地审查", "",
                     f"- 隔离分支 · `{args.branch}`",
                     "- 来源记录与改动已进入隔离分支。审查 diff 单独保存在指定的本地补丁文件。",
                     "- 等待人工审查、目标平台验证及合并确认。"]
