# 复用计划

上游 · [un33k/python-slugify](https://github.com/un33k/python-slugify/commit/f85f9488520148d5f6899b5639199882b605e30a)  
核对 commit · f85f9488520148d5f6899b5639199882b605e30a  
目标平台 · Windows

## 功能与入口

- [README.md 第 1 行](https://github.com/un33k/python-slugify/blob/f85f9488520148d5f6899b5639199882b605e30a/README.md#L1) · # Python Slugify
- [README.md 第 3 行](https://github.com/un33k/python-slugify/blob/f85f9488520148d5f6899b5639199882b605e30a/README.md#L3) · &#42;&#42;A Python slugify application that handles unicode&#42;&#42;.
- [README.md 第 17 行](https://github.com/un33k/python-slugify/blob/f85f9488520148d5f6899b5639199882b605e30a/README.md#L17) · However, there is an alternative decoding package called &#91;Unidecode&#93;(https://github.com/avian2/unidecode) &#95;(GPL)&#95;. It can be installed as &#96;python-slugify&#91;unidecode&#93;&#96; for those who prefer it. &#96;Unidecod
- [slugify/slugify.py](https://github.com/un33k/python-slugify/blob/f85f9488520148d5f6899b5639199882b605e30a/slugify/slugify.py)

## 依赖优先评估

- 上游声明的包名 · **python-slugify**，版本字段 · 8.0.4
- 声明的直接依赖 · text-unidecode&#62;=1.3
- 优先采用发行包。固定版本，核对发行包与来源 commit 的对应关系，在项目现有工具中解析锁文件并检查传递依赖和平台。
- [上游依赖清单](https://github.com/un33k/python-slugify/blob/f85f9488520148d5f6899b5639199882b605e30a/setup.py)
- [GitHub 标签 v8.0.4](https://github.com/un33k/python-slugify/tree/v8.0.4) 指向所核对的 commit。发行包内容仍待核对。

## 许可证与摘取范围

- GitHub 对固定版本的许可证识别 · MIT
- [LICENSE](https://github.com/un33k/python-slugify/blob/f85f9488520148d5f6899b5639199882b605e30a/LICENSE)
- 许可证版权声明 · Copyright (c) Val Neekman &#64; Neekware Inc. http://neekware.com
- 摘取评估以上述源码入口为起点。保留文件内版权声明及适用的许可证和 NOTICE 原文。
- 接入时核对调用边界、错误处理、Python 版本和平台资源；先在目标平台跑最小行为测试。
- 功能入口 [def slugify(](https://github.com/un33k/python-slugify/blob/f85f9488520148d5f6899b5639199882b605e30a/slugify/slugify.py#L75)
- Python 静态导入 · &#95;&#95;future&#95;&#95;、collections、html、re、text&#95;unidecode、unicodedata、unidecode
- 暂停复制 · 发现仓库内、第三方、动态导入或资源引用的可能，需人工追踪传递依赖。

## 本地审查

- 隔离分支 · `workbench/slugify-demo`
- 来源记录与改动已进入隔离分支。审查 diff 单独保存在指定的本地补丁文件。
- 等待人工审查、目标平台验证及合并确认。
