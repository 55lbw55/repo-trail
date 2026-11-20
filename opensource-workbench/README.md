# 开源工作台

在本地检索公开 GitHub 仓库、评估代码复用，并为单个上游问题准备证据、草稿和补丁。需要 Python 3.11+ 和 Git，运行时只用 Python 标准库。以下命令在本目录运行，示例使用 PowerShell 7。

## 演示

```powershell
./examples/demo.ps1
# 使用已有缓存复跑，请指定一个新的输出目录
./examples/demo.ps1 -Offline -OutputDirectory review-offline
```

脚本创建临时 Git 项目，生成报告和补丁，并打印项目位置与分支 diff 的文件统计。目标仓库是 [55lbw55/repo-trail](https://github.com/55lbw55/repo-trail)，CLI 位于其本地工作区内的独立子目录。

| 流程 | 实际演示产物 |
| --- | --- |
| 检索 Unicode 标题转 slug | [检索报告](examples/search.md) |
| 优先采用 `python-slugify` 的发行包 | [复用计划](examples/reuse-plan.md) · [隔离分支导出的 diff](examples/reuse.patch) |
| 修正 Rich 的 `RichHandler` docstring | [贡献报告与 PR 草稿](examples/contribution-draft.md) · [补丁](examples/rich-docstring.patch) · [可复用的证据输入](examples/rich-evidence.json) |

复用演示先检索默认分支，在计划与隔离分支中固定到 `v8.0.4` 对应的 commit。该版本用于复现演示。GitHub 标签、源码版本、许可证和依赖声明均已核对。发行包字节、锁文件、目标平台行为和完整依赖许可仍待实际接入时验证。

贡献演示关联已有的 [Rich #3256](https://github.com/Textualize/rich/issues/3256)。补丁改正类型名称，并按上游要求补充变更记录。已在 API 取得的固定版本文件上完成 `git apply --check`、实际应用、字节比对和 Python 语法解析。Rich 的政策要求维护者先在关联 Issue 或 Discussion 中认可方案才能提交 AI 辅助 PR。草稿中的模板核对、维护者认可及上游运行检查仍需完成。

## 三条命令

**检索。** 功能描述用于本地排序。请用 `--keywords` 单独提供可公开的 GitHub 搜索词。项目路径用于本地检查 PEP 621 依赖声明。

```powershell
python -m workbench search --feature '把包含 Unicode 的标题转换成网址 slug' --language Python --platform Windows --project . --keywords slugify --limit 3
```

**复用。** 默认生成计划。指定候选源码路径与核对过的完整 commit 后，可复现同一份证据。

```powershell
python -m workbench reuse-plan --repo un33k/python-slugify --ref f85f9488520148d5f6899b5639199882b605e30a --release-tag v8.0.4 --file slugify/slugify.py --keywords slugify --platform Windows --project .
```

选定候选并核对许可后，添加 `--license-reviewed --branch workbench/slugify-demo --patch reuse.patch`。依赖方案还需提供 `--requirement 'python-slugify==8.0.4'`。版本字段需能在固定快照中静态读出，或通过 `--version-file slugify/__version__.py --version-evidence "__version__ = '8.0.4'"` 指明精确行。目标项目须有 Git 基础 commit、Git 身份和可写入的 PEP 621 清单。用 `git diff HEAD workbench/slugify-demo` 审查分支，再自行确认合并。分支从当前 `HEAD` 建立，临时 Git 索引用于写入分支上的单个 commit。

`--strategy vendor` 支持一个独立 Python 模块。复制前先核对许可证及目标项目兼容性。CLI 同时检查固定版本的许可证文本、文件 SPDX 标记、静态导入和明显的动态加载线索。发现外部、相对或同名仓库导入、多重许可材料、许可缺失或许可不明确时，报告列出阻塞项。获准摘取时保留原文件字节、适用的根目录许可材料和来源记录。静态导入结果只覆盖可解析的导入，隐式资源、平台模块和运行时依赖仍需人工核对。

**贡献。** 第一遍用 `--keywords` 查询已有 Issue 和 PR 并读取常见贡献规则、模板和 AI 政策文件。可用 `--kind good-first` 选出一个带维护者标签的未认领 Issue，或用 `--kind docs` / `--kind platform` 查找文档与普通跨平台问题。精确的预期、实际行为和编辑锚点由使用者在证据 JSON 中指定。CLI 对照固定 commit 核验锚点。

```powershell
python -m workbench contribution-draft --repo Textualize/rich --ref 3a109ccdffe5b2d0e30684a304fbd388e99ce57b --kind docs --keywords log_time_format --issue 3256 --evidence examples/rich-evidence.json
```

确认已有 Issue 对应同一问题时，用 `--issue` 关联。如果搜索只命中无关条目，审查后用 `--related-reviewed` 准备新 Issue 草稿。上游规则允许直接 PR 时，可显式使用 `--route direct-pr --policy-reviewed`。核对政策和外链后加上 `--policy-reviewed --patch rich-docstring.patch` 生成可审查补丁。证据范例中每个 claim 有 `path` 与精确的 `text`。每个 edit 有 `path`、`before` 和 `after`。补丁最多支持四处精确文本编辑。可用 `pr_checklists` 提供上游模板勾选项，用 `assistance` 记录准备草稿时实际使用的工具。

发布 Issue、推送分支和创建 PR 由你审核目标、正文与 diff 后在 Chrome 完成。CLI 没有 GitHub 写接口，也不访问浏览器会话。

## 缓存、数据与验证边界

- 加 `--out 新文件.md` 输出 UTF-8 Markdown，默认输出到终端。补丁单独写入指定文件。复用补丁可能包含目标项目的清单 diff，应留在本地审查。
- 公开数据通过 `api.github.com` 的 REST GET 匿名访问。公开查询和固定版本对象缓存到 SQLite，可在子命令前用 `--cache-dir` 指定位置、用 `--offline` 离线、用 `--refresh` 重新查询。按 GitHub 的限流响应暂停相应请求；查询会在额度耗尽时给出可重试时间。 [GitHub REST 限流说明](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
- 功能原文、本地目录名、项目清单内容和 Git 身份不会写入 Markdown 或发送给 GitHub。关键词与证据文件是显式的公开输入，只填写可公开资料。公开仓库文本作为资料读取；CLI 不执行第三方安装、构建、测试、仓库指令或 Git hooks。
- 搜索依据为公开索引、README、源码路径及静态读取的清单。目标平台和依赖锁定由接入方实际验证。贡献草稿由已确认的精确证据驱动，政策语义、问题重复性与维护者许可由人确认。
