# 上游贡献草稿

目标 · [Textualize/rich](https://github.com/Textualize/rich/commit/3a109ccdffe5b2d0e30684a304fbd388e99ce57b)  
核对 commit · 3a109ccdffe5b2d0e30684a304fbd388e99ce57b  
类别 · 文档或示例不一致

## 贡献规则

- [README.md](https://github.com/Textualize/rich/blob/3a109ccdffe5b2d0e30684a304fbd388e99ce57b/README.md)
- [.github/ISSUE&#95;TEMPLATE/bug&#95;report.md](https://github.com/Textualize/rich/blob/3a109ccdffe5b2d0e30684a304fbd388e99ce57b/.github/ISSUE_TEMPLATE/bug_report.md)
- [.github/ISSUE&#95;TEMPLATE/feature&#95;request.md](https://github.com/Textualize/rich/blob/3a109ccdffe5b2d0e30684a304fbd388e99ce57b/.github/ISSUE_TEMPLATE/feature_request.md)
- [.github/pull&#95;request&#95;template.md](https://github.com/Textualize/rich/blob/3a109ccdffe5b2d0e30684a304fbd388e99ce57b/.github/pull_request_template.md)
- [AI&#95;POLICY.md](https://github.com/Textualize/rich/blob/3a109ccdffe5b2d0e30684a304fbd388e99ce57b/AI_POLICY.md)
- [CODE&#95;OF&#95;CONDUCT.md](https://github.com/Textualize/rich/blob/3a109ccdffe5b2d0e30684a304fbd388e99ce57b/CODE_OF_CONDUCT.md)
- [CONTRIBUTING.md](https://github.com/Textualize/rich/blob/3a109ccdffe5b2d0e30684a304fbd388e99ce57b/CONTRIBUTING.md)
- AI 政策线索 [.github/pull&#95;request&#95;template.md 第 30 行](https://github.com/Textualize/rich/blob/3a109ccdffe5b2d0e30684a304fbd388e99ce57b/.github/pull_request_template.md#L30) · ## AI?
- AI 政策线索 [.github/pull&#95;request&#95;template.md 第 32 行](https://github.com/Textualize/rich/blob/3a109ccdffe5b2d0e30684a304fbd388e99ce57b/.github/pull_request_template.md#L32) · - &#91; &#93; AI was used to generate this PR
- AI 政策线索 [.github/pull&#95;request&#95;template.md 第 34 行](https://github.com/Textualize/rich/blob/3a109ccdffe5b2d0e30684a304fbd388e99ce57b/.github/pull_request_template.md#L34) · AI generated PRs may be accepted, but only if &#64;willmcgugan has responded on an issue or discussion.
- AI 政策线索 [AI&#95;POLICY.md 第 1 行](https://github.com/Textualize/rich/blob/3a109ccdffe5b2d0e30684a304fbd388e99ce57b/AI_POLICY.md#L1) · This project accepts AI generated Pull Requests, as long as the following guidelines are met.
- AI 政策线索 [AI&#95;POLICY.md 第 4 行](https://github.com/Textualize/rich/blob/3a109ccdffe5b2d0e30684a304fbd388e99ce57b/AI_POLICY.md#L4) · - The Pull Request must identify itself as AI generated, including the name of the agent used.
- AI 政策线索 [AI&#95;POLICY.md 第 5 行](https://github.com/Textualize/rich/blob/3a109ccdffe5b2d0e30684a304fbd388e99ce57b/AI_POLICY.md#L5) · - The Pull Request must link to a issue or discussion where a solution has been approved by a maintainer (&#64;willmcgugan).
- AI 政策线索 [CONTRIBUTING.md 第 9 行](https://github.com/Textualize/rich/blob/3a109ccdffe5b2d0e30684a304fbd388e99ce57b/CONTRIBUTING.md#L9) · See also &#91;AI&#95;POLICY.md&#93;(https://github.com/Textualize/rich/blob/master/AI&#95;POLICY.md) if you will be using AI.

## 已有 Issue 和 PR

- Issue 查询 · `repo:Textualize/rich is:issue log_time_format`，检索命中 13 条，展示 10 条。
  - [#3256 &#91;BUG&#93; Documentation and code disagree about the type of &#96;log&#95;time&#95;format&#96;](https://github.com/Textualize/rich/issues/3256) · open
  - [#3877 &#91;BUG&#93; RichHandler ignores &#96;%z&#96; time zone format specifier](https://github.com/Textualize/rich/issues/3877) · open
  - [#2936 &#91;REQUEST&#93; Print traceback without borders](https://github.com/Textualize/rich/issues/2936) · open
  - [#3225 &#91;BUG&#93; timefmt](https://github.com/Textualize/rich/issues/3225) · open
  - [#3277 &#91;BUG&#93; Rich tracebacks raise another exception when suppressing sys](https://github.com/Textualize/rich/issues/3277) · open
  - [#3529 &#91;BUG&#93; RichHandler breaks Progress bar with multiprocessing](https://github.com/Textualize/rich/issues/3529) · open
  - [#3215 &#91;BUG&#93; &#96;rich&#95;tracebacks&#96; with &#96;rich&#95;tracebacks&#96; not working in notebook](https://github.com/Textualize/rich/issues/3215) · open
  - [#1972 &#91;REQUEST&#93; RichHandler Time Zones](https://github.com/Textualize/rich/issues/1972) · closed
  - [#2334 &#91;REQUEST&#93; Add markup support for &#96;Console.log&#95;time&#95;format&#96;](https://github.com/Textualize/rich/issues/2334) · closed
  - [#2195 &#91;BUG&#93; Enabling &#96;tracebacks&#95;show&#95;locals&#96; in &#96;RichHandler&#96; will cause the program to get stuck](https://github.com/Textualize/rich/issues/2195) · closed
- PR 查询 · `repo:Textualize/rich is:pr log_time_format`，检索命中 3 条，展示 3 条。
  - [#4078 fix: RichHandler now honours %z (and other timezone specifiers) in log&#95;time&#95;format](https://github.com/Textualize/rich/pull/4078) · closed
  - [#3982 Fix RichHandler ignoring %z timezone format specifier](https://github.com/Textualize/rich/pull/3982) · closed
  - [#3574 Add option to pass a timezone into richhandler for log timestamps](https://github.com/Textualize/rich/pull/3574) · closed
- 命中超出本次读取范围或 GitHub 返回不完整结果，继续核对后才能判定是否重复。
- 本次关联 [#3256 &#91;BUG&#93; Documentation and code disagree about the type of &#96;log&#95;time&#95;format&#96;](https://github.com/Textualize/rich/issues/3256) · open。沿用该 Issue 讨论。

## 贡献候选 · Use FormatTimeCallable in the RichHandler docstring

- 影响 · Readers looking up the log&#95;time&#95;format callable type by the name in the parameter documentation are directed to a name that differs from the signature.
- 预期 · The RichHandler parameter documentation names FormatTimeCallable, matching the constructor annotation.
- 实际 · The RichHandler docstring names TimeFormatterCallable, whereas the constructor uses FormatTimeCallable.
- 预期证据 [rich/logging.py 第 94 行](https://github.com/Textualize/rich/blob/3a109ccdffe5b2d0e30684a304fbd388e99ce57b/rich/logging.py#L94)
- 实际证据 [rich/logging.py 第 55 行](https://github.com/Textualize/rich/blob/3a109ccdffe5b2d0e30684a304fbd388e99ce57b/rich/logging.py#L55)

## PR 草稿

### Use FormatTimeCallable in the RichHandler docstring

### Type of changes

- [ ] Bug fix
- [ ] New feature
- [x] Documentation / docstrings
- [ ] Tests
- [ ] Other

### AI?

- [x] AI was used to generate this PR

### Checklist

- [ ] Run Black on new code, if applicable
- [x] Update CHANGELOG.md and CONTRIBUTORS.md where appropriate (changelog updated)
- [ ] Add tests for new code, if applicable
- [ ] Contributor accepts the project's review checklist

### Description

Readers looking up the log&#95;time&#95;format callable type by the name in the parameter documentation are directed to a name that differs from the signature.

Expected behavior after the change: The RichHandler parameter documentation names FormatTimeCallable, matching the constructor annotation.

Related issue: [#3256](https://github.com/Textualize/rich/issues/3256).

### Verification

- Checked the evidence and exact edit anchors against the pinned upstream commit.
- Ran `git apply --check --no-index --whitespace=error` on the upstream files, applied the patch, and compared the result byte for byte.
- Parsed the updated rich/logging.py with Python's AST parser.
- Upstream tests, documentation builds, and runtime checks remain pending.
- Prepared with assistance from OpenAI Codex.

提交条件 · Rich's AI policy requires approval of the proposed solution by &#64;willmcgugan in the linked issue or discussion, disclosure of OpenAI Codex, and completion of the PR template. Maintainer approval is unverified.

在 Chrome 发布前，核对目标、对应 Issue、上游模板与政策、正文和本地补丁。
