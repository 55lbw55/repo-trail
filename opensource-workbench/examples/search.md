# 公开仓库检索

公开查询词 · slugify  
语言与目标平台 · Python / Windows

从 GitHub 返回的候选中按本地功能、平台和依赖线索排序。平台匹配依据来自公开文档，接入成本为静态估计。

## un33k/python-slugify

- 核对版本 [4b6b5b42f050](https://github.com/un33k/python-slugify/commit/4b6b5b42f050f1ce96899e015247d5e3901cc433)
- GitHub 许可证识别 · MIT
- 公开项目描述 · Returns unicode slugs
- [README.md 第 27 行](https://github.com/un33k/python-slugify/blob/4b6b5b42f050f1ce96899e015247d5e3901cc433/README.md#L27) · assert slugify('影師嗎', allow&#95;unicode=True, algorithm='modern') == '影師嗎'
- [README.md 第 1 行](https://github.com/un33k/python-slugify/blob/4b6b5b42f050f1ce96899e015247d5e3901cc433/README.md#L1) · # Python Slugify
- [README.md 第 3 行](https://github.com/un33k/python-slugify/blob/4b6b5b42f050f1ce96899e015247d5e3901cc433/README.md#L3) · Unicode-aware slug generation for Python, with explicit transliteration choices.
- 相关源码入口 · [slugify/slugify.py](https://github.com/un33k/python-slugify/blob/4b6b5b42f050f1ce96899e015247d5e3901cc433/slugify/slugify.py)、[slugify/&#95;&#95;init&#95;&#95;.py](https://github.com/un33k/python-slugify/blob/4b6b5b42f050f1ce96899e015247d5e3901cc433/slugify/__init__.py)、[slugify/&#95;legacy.py](https://github.com/un33k/python-slugify/blob/4b6b5b42f050f1ce96899e015247d5e3901cc433/slugify/_legacy.py)、[slugify/special.py](https://github.com/un33k/python-slugify/blob/4b6b5b42f050f1ce96899e015247d5e3901cc433/slugify/special.py)
- 依赖入口 [pyproject.toml](https://github.com/un33k/python-slugify/blob/4b6b5b42f050f1ce96899e015247d5e3901cc433/pyproject.toml) · text-unidecode&#62;=1.3
- 优先核对现成依赖 **python-slugify**。接入成本预计较低，待验证包版本、依赖和平台行为。

## mozilla/unicode-slugify

- 核对版本 [74d175dd4c9d](https://github.com/mozilla/unicode-slugify/commit/74d175dd4c9d21b1586842a3909118c7ec58f4ce)
- GitHub 许可证识别 · BSD-3-Clause
- 公开项目描述 · A slugifier that works in unicode
- [README.md 第 1 行](https://github.com/mozilla/unicode-slugify/blob/74d175dd4c9d21b1586842a3909118c7ec58f4ce/README.md#L1) · # Unicode Slugify
- [README.md 第 3 行](https://github.com/mozilla/unicode-slugify/blob/74d175dd4c9d21b1586842a3909118c7ec58f4ce/README.md#L3) · Unicode Slugify is a slugifier that generates unicode slugs.  It was originally
- [README.md 第 12 行](https://github.com/mozilla/unicode-slugify/blob/74d175dd4c9d21b1586842a3909118c7ec58f4ce/README.md#L12) · from slugify import slugify, SLUG&#95;OK
- 相关源码入口 · [slugify/&#95;&#95;init&#95;&#95;.py](https://github.com/mozilla/unicode-slugify/blob/74d175dd4c9d21b1586842a3909118c7ec58f4ce/slugify/__init__.py)
- 依赖入口 [setup.py](https://github.com/mozilla/unicode-slugify/blob/74d175dd4c9d21b1586842a3909118c7ec58f4ce/setup.py) · six、unidecode
- 优先核对现成依赖 **unicode-slugify**。接入成本预计较低，待验证包版本、依赖和平台行为。

## voronind/awesome-slugify

- 核对版本 [a6563949965b](https://github.com/voronind/awesome-slugify/commit/a6563949965bcddd976b7b3fb0babf76e3b490f7)
- GitHub 许可证识别 · UNKNOWN
- 公开项目描述 · Python flexible slugify function
- [README.rst 第 91 行](https://github.com/voronind/awesome-slugify/blob/a6563949965bcddd976b7b3fb0babf76e3b490f7/README.rst#L91) · slugify&#95;unicode = Slugify(translate=None)
- [README.rst 第 112 行](https://github.com/voronind/awesome-slugify/blob/a6563949965bcddd976b7b3fb0babf76e3b490f7/README.rst#L112) · from slugify import Slugify, UniqueSlugify, slugify, slugify&#95;unicode
- [README.rst 第 132 行](https://github.com/voronind/awesome-slugify/blob/a6563949965bcddd976b7b3fb0babf76e3b490f7/README.rst#L132) · slugify&#95;unicode('Я ♥ борщ')                   # Я-борщ      (sanitize only)
- 相关源码入口 · [slugify/&#95;&#95;init&#95;&#95;.py](https://github.com/voronind/awesome-slugify/blob/a6563949965bcddd976b7b3fb0babf76e3b490f7/slugify/__init__.py)、[slugify/alt&#95;translates.py](https://github.com/voronind/awesome-slugify/blob/a6563949965bcddd976b7b3fb0babf76e3b490f7/slugify/alt_translates.py)、[slugify/main.py](https://github.com/voronind/awesome-slugify/blob/a6563949965bcddd976b7b3fb0babf76e3b490f7/slugify/main.py)
- 依赖入口 [setup.py](https://github.com/voronind/awesome-slugify/blob/a6563949965bcddd976b7b3fb0babf76e3b490f7/setup.py) · regex、Unidecode&#62;=0.04.14,&#60;0.05
- 许可未明确，暂停复制。接入前先核对包的许可证和发行状态。
