#!/usr/bin/env python3
"""从 upstream/ 快照生成 MkDocs 派生页（stdlib only）。

    python scripts/build_docs.py            # 生成
    python scripts/build_docs.py --check    # 只校验 manifest / sha256 / 脱敏

`upstream/` 是主仓 CI 推来的唯一真源；`docs/contract/`、`docs/reference/`、
`docs/changelog.md`、`docs/llms*.txt`、`docs/assets/` 全部由本脚本生成，勿手改、不入库。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPSTREAM = ROOT / "upstream"
DOCS = ROOT / "docs"
ASSETS = DOCS / "assets"
GENERATED_DIRS = (DOCS / "contract", DOCS / "reference", ASSETS)
GENERATED_FILES = (DOCS / "changelog.md", DOCS / "llms.txt", DOCS / "llms-full.txt")
HEADER = "<!-- 由 scripts/build_docs.py 从 upstream/ 生成，勿手改 -->\n\n"
# 主仓快照已脱敏；这里是第二道防线，防止脱敏规则失效后把内网地址发布出去。
SENSITIVE = re.compile(r"\b80\.37\.0\.103\b|https?://(?!127\.0\.0\.1|0\.0\.0\.0)\d{1,3}(?:\.\d{1,3}){3}")


def load_manifest() -> dict | None:
    path = UPSTREAM / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def verify(manifest: dict) -> list[str]:
    problems: list[str] = []
    for item in manifest.get("files", []):
        rel = item["path"]
        target = UPSTREAM / rel
        if not target.is_file():
            problems.append(f"快照缺文件：{rel}")
            continue
        content = target.read_text(encoding="utf-8")
        if hashlib.sha256(content.encode("utf-8")).hexdigest() != item["sha256"]:
            problems.append(f"快照 sha256 不一致：{rel}")
        hit = SENSITIVE.search(content)
        if hit:
            problems.append(f"未脱敏内容：{rel} -> {hit.group(0)}")
    return problems


def asset_rel(rel: str) -> str:
    return f"assets/{rel}.txt" if rel.endswith(".md") else f"assets/{rel}"


def render(manifest: dict) -> None:
    for path in GENERATED_DIRS:
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)
    for path in GENERATED_FILES:
        if path.exists():
            path.unlink()

    rows: list[str] = []
    full = ["# altdatahub 文档全文", "", "> 由 scripts/build_docs.py 从 upstream/ 聚合，勿手改。", ""]
    for item in manifest.get("files", []):
        rel = item["path"]
        src = UPSTREAM / rel
        if not src.is_file():
            continue
        content = src.read_text(encoding="utf-8")
        dest = DOCS / asset_rel(rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        rows.append(f"| `{rel}` | [原文](../{asset_rel(rel)}) |")
        if rel.endswith(".md"):
            full.extend([f"## {rel}", "", content, ""])

    (DOCS / "reference" / "index.md").write_text(
        HEADER
        + "# 原始文档镜像\n\n"
        + "主仓 `tools/verify.py export` 产出的脱敏快照原文。`.md` 以 `.txt` 提供，\n"
        + "避免站内相对链接失效；完整聚合见 [llms-full.txt](../llms-full.txt)。\n\n"
        + "| 快照文件 | 原文 |\n|---|---|\n"
        + "\n".join(rows)
        + "\n",
        encoding="utf-8",
    )

    (DOCS / "contract" / "index.md").write_text(
        HEADER
        + "# 数据契约与传输契约\n\n"
        + "| 契约 | 真源 | 说明 |\n|---|---|---|\n"
        + "| 数据契约 | `catalog/products.json` | 分册 PDF 解析产物；51 个 productCode / 557 个顶层字段 / 12 个子结构 |\n"
        + "| 目录速查 | [PRODUCTS.md](../assets/catalog/PRODUCTS.md.txt) | 生成物，勿手改 |\n"
        + "| 传输契约 | [transport.md](../assets/docs/api/transport.md.txt) | 已按示例代码接入，4 项未确认、未与真实网关联调 |\n"
        + "| 解析踩坑 | [catalog.md](../assets/docs/catalog.md.txt) | 真源链、易误判事实、升版流程 |\n"
        + "| 能力级契约 | [service.yaml](../assets/openapi/service.yaml) | 对外 6 条路径，含 `degrade_reason` |\n"
        + "| 跨语言行为 | `contract/vectors.json` | 报文 / 错误码 / 信封的黄金向量（不进公开快照，见主仓） |\n\n"
        + "!!! warning \"响应信封仍未确认\"\n"
        + "    数据行所在层级、错误码字段名、51 个服务号、`eds_validday` 类型注释都未由真实响应钉死；\n"
        + "    SDK 用候选路径试探，联调后需按主仓 `docs/api/transport.md` 收敛。\n",
        encoding="utf-8",
    )

    changelog = UPSTREAM / "CHANGELOG.md"
    (DOCS / "changelog.md").write_text(
        HEADER + (changelog.read_text(encoding="utf-8") if changelog.is_file() else "# 变更记录\n\n等待主仓快照。\n"),
        encoding="utf-8",
    )

    (DOCS / "llms.txt").write_text(
        "# altdatahub 文档\n\n"
        "> 第三方 SDK 文档：离线目录可用；在线查询未与真实网关联调，不伪造数据。\n\n"
        "## 入门\n- [首页](index.md)\n- [安装与离线 CLI](getting-started/install.md)\n"
        "## 指南\n- [Python SDK](guides/python.md)\n- [多语言 SDK](guides/sdks.md)\n"
        "## 契约\n- [契约概览](contract/index.md)\n- [原始文档镜像](reference/index.md)\n"
        "## 其他\n- [变更记录](changelog.md)\n- [全文聚合](llms-full.txt)\n",
        encoding="utf-8",
    )
    (DOCS / "llms-full.txt").write_text("\n".join(full) + "\n", encoding="utf-8")
    print(f"generated {len(rows)} reference assets, contract/index, changelog, llms*.txt")


def main() -> int:
    parser = argparse.ArgumentParser(description="从 upstream/ 生成文档站派生页")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest()
    if manifest is None:
        print("upstream/manifest.json 缺失：等待主仓首次推送快照", file=sys.stderr)
        return 1
    problems = verify(manifest)
    if problems:
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    if args.check:
        print(f"snapshot ok: {len(manifest['files'])} files")
        return 0
    render(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
