#!/usr/bin/env python3
"""站点产物复核（在 `mkdocs build --strict` 之后运行）。

检查：三大板块关键页、llms.txt 链接目标、llms-full.txt 目录/体积/脱敏/关键内容、
search_index.json 中文页面与搜索配置。任何一项失败都返回非 0，由 CI 拦下。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DOCS = ROOT / "docs"
MAX_LLMS_FULL_BYTES = 512 * 1024
LINK_RE = re.compile(r"^- \[[^\]]+\]\(([^)]+)\)", re.MULTILINE)
SECTION_RE = re.compile(r"^## (\[\d{2}\] .+)$", re.MULTILINE)
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
SENSITIVE = re.compile(r"\b80\.37\.0\.103\b|https?://(?!127\.0\.0\.1|0\.0\.0\.0)\d{1,3}(?:\.\d{1,3}){3}")
REQUIRED_PAGES = (
    "api/index.html",
    "api/endpoints/index.html",
    "mcp/index.html",
    "mcp/tools/index.html",
    "mcp/deploy/index.html",
    "guides/toolchain/index.html",
    "contract/capabilities/index.html",
)


def check_pages() -> list[str]:
    return [f"site/{rel} 缺失" for rel in REQUIRED_PAGES if not (SITE / rel).is_file()]


def check_llms_txt() -> list[str]:
    path = SITE / "llms.txt"
    if not path.is_file():
        return ["site/llms.txt 缺失"]
    problems: list[str] = []
    for target in LINK_RE.findall(path.read_text(encoding="utf-8")):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        rel = target.split("#", 1)[0]
        if not (SITE / rel).is_file() and not (DOCS / rel).is_file():
            problems.append(f"llms.txt 链接目标不存在：{target}")
    return problems


def check_llms_full() -> list[str]:
    path = SITE / "llms-full.txt"
    if not path.is_file():
        return ["site/llms-full.txt 缺失"]
    text = path.read_text(encoding="utf-8")
    problems: list[str] = []
    size = len(text.encode("utf-8"))
    if size > MAX_LLMS_FULL_BYTES:
        problems.append(f"llms-full.txt 超过 {MAX_LLMS_FULL_BYTES} 字节：{size}")
    if "## 目录" not in text:
        problems.append("llms-full.txt 缺目录段")
        return problems

    toc_block = text.split("## 目录", 1)[1].split("\n## ", 1)[0]
    sections = SECTION_RE.findall(text)
    if not sections:
        problems.append("llms-full.txt 没有编号章节")
    for title in sections:
        if title not in toc_block:
            problems.append(f"目录缺章节：{title}")
    if len(sections) != len(set(sections)):
        problems.append("llms-full.txt 章节编号重复")
    for word in ("端点参考", "MCP Tools 参考", "工具链与生成器", "排障 FAQ", "快照原文：README.md"):
        if word not in text:
            problems.append(f"llms-full.txt 缺关键内容：{word}")
    hit = SENSITIVE.search(text)
    if hit:
        problems.append(f"llms-full.txt 含未脱敏地址：{hit.group(0)}")
    print(f"  llms-full.txt: {size} bytes, {len(sections)} sections")
    return problems


def check_search_index() -> list[str]:
    path = SITE / "search" / "search_index.json"
    if not path.is_file():
        return ["site/search/search_index.json 缺失"]
    data = json.loads(path.read_text(encoding="utf-8"))
    blob = json.dumps(data, ensure_ascii=False)
    problems: list[str] = []
    if not CJK_RE.search(blob):
        problems.append("search_index.json 不含中文内容")
    for word in ("端点参考", "MCP Tools 参考", "工具链与生成器", "能力矩阵"):
        if word not in blob:
            problems.append(f"search_index.json 未索引：{word}")
    config = data.get("config", {}) if isinstance(data, dict) else {}
    lang = config.get("lang") or []
    if "zh" in lang:
        problems.append("搜索语言含 zh：lunr.zh.js 在浏览器端缺 nodejieba 会报错，应改用 lang: [en]")
    if "u3000" not in config.get("separator", ""):
        problems.append("搜索未配置中文标点断句（separator 缺 CJK 标点范围）")
    docs = data.get("docs", []) if isinstance(data, dict) else []
    print(f"  search_index.json: {len(docs)} docs, lang={lang or 'inferred'}")
    return problems


def main() -> int:
    problems = check_pages() + check_llms_txt() + check_llms_full() + check_search_index()
    for problem in problems:
        print(f"  - {problem}", file=sys.stderr)
    if problems:
        return 1
    print("site content ok: 三大板块页面 / llms.txt / llms-full.txt / search_index.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
