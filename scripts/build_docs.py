#!/usr/bin/env python3
"""从 upstream/ 快照生成 MkDocs 派生页（stdlib only）。

    python scripts/build_docs.py            # 生成
    python scripts/build_docs.py --check    # 只校验 manifest / sha256 / 脱敏

`upstream/` 是主仓 CI 推来的唯一真源；`docs/api/endpoints.md`、`docs/mcp/tools.md`、
`docs/contract/`、`docs/reference/`、`docs/changelog.md`、`docs/llms*.txt`、`docs/assets/`
全部由本脚本生成，勿手改、不入库。
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
# 整目录都是生成物，可安全重建
GENERATED_DIRS = (DOCS / "contract", DOCS / "reference", ASSETS)
# api/ 与 mcp/ 含手写总览页，只补目录、不整目录删除
GENERATED_DIRS_KEEP = (DOCS / "api", DOCS / "mcp")
GENERATED_FILES = (
    DOCS / "changelog.md",
    DOCS / "llms.txt",
    DOCS / "llms-full.txt",
    DOCS / "api" / "endpoints.md",
    DOCS / "mcp" / "tools.md",
)
GENERATED_TOP_DIRS = {"contract", "reference", "assets"}
GENERATED_FILE_SET = {path.resolve() for path in GENERATED_FILES if path.suffix == ".md"}
HEADER = "<!-- 由 scripts/build_docs.py 从 upstream/ 生成，勿手改 -->\n\n"
CAPABILITIES_REL = "contract/capabilities.json"
# 主仓快照已脱敏；这里是第二道防线，防止脱敏规则失效后把内网地址发布出去。
SENSITIVE = re.compile(r"\b80\.37\.0\.103\b|https?://(?!127\.0\.0\.1|0\.0\.0\.0)\d{1,3}(?:\.\d{1,3}){3}")


def load_manifest() -> dict | None:
    path = UPSTREAM / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def load_registry() -> dict:
    path = UPSTREAM / CAPABILITIES_REL
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"capabilities": []}


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
        if rel == CAPABILITIES_REL:
            try:
                registry = json.loads(content)
                if "capabilities" not in registry:
                    problems.append(f"{rel} 缺少 capabilities 段")
            except json.JSONDecodeError as exc:
                problems.append(f"{rel} 不是合法 JSON：{exc}")
    return problems


def asset_rel(rel: str) -> str:
    return f"assets/{rel}.txt" if rel.endswith(".md") else f"assets/{rel}"


def handwritten_pages() -> list[Path]:
    """站点手写页（非生成物），按路径排序，供 llms-full 全文聚合。"""
    return sorted(
        path
        for path in DOCS.rglob("*.md")
        if path.relative_to(DOCS).parts[0] not in GENERATED_TOP_DIRS
        and path.resolve() not in GENERATED_FILE_SET
    )


def page_text(path: Path) -> str:
    """llms-full 用的纯文本：去 front matter；首页是 HTML 落地页，剥标签后可读性更好。"""
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"\A---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)
    if path == DOCS / "index.md":
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def render_capabilities(registry: dict) -> str:
    """由能力注册表生成能力矩阵页；快照尚无该文件时给占位页，保证 strict 不断链。"""
    if not registry["capabilities"]:
        return HEADER + "# 能力矩阵\n\n等待主仓快照包含 `contract/capabilities.json`。\n"

    lines = [
        HEADER,
        "# 能力矩阵",
        "",
        "> 真源：主仓 `contract/capabilities.json`。能力服务的路由、MCP tools、Skill 命令与",
        "> 降级文案均由它派生；本页是生成物，勿手改。",
        "",
        "## 能力 × 路由 × 入口",
        "",
        "| 能力 | HTTP | MCP tool | Skill 命令 | 网关 | scope |",
        "|---|---|---|---|---|---|",
    ]
    for item in registry["capabilities"]:
        gateway = "**需要 `EDS_*`**" if item["requiresGateway"] else "不需要"
        scope = f"`{item['scope']}`" if item["scope"] else "免鉴权"
        lines.append(
            f"| `{item['id']}` | `{item['method']} {item['pathTemplate']}` "
            f"| `{item['mcpTool']}` | `{item['skillCommand']}` | {gateway} | {scope} |"
        )

    lines += ["", "## 降级口径（各入口共用）", "", "| key | 文案 |", "|---|---|"]
    for key, text in registry.get("degradeReasons", {}).items():
        lines.append(f"| `{key}` | {text} |")

    lines += ["", "## 错误处置策略", "", "| 现象 | 分类 | 重试 | 建议 |", "|---|---|---|---|"]
    for row in registry.get("policyRows", []):
        lines.append(f"| `{row['label']}` | {row['category']} | {row['retryable']} | {row['hint']} |")

    lines += [
        "",
        f"> 业务错误码不在此复制，真源是 `{registry['errorCodeSource']}`；一律以响应里的 `retryable` 为准。",
        "",
        '!!! warning "在线查询未与真实网关联调"',
        f"    {registry['gatewayNote']}",
        "",
    ]
    return "\n".join(lines)


def curl_example(item: dict) -> str:
    base = "http://127.0.0.1:8802"
    auth = '-H "Authorization: Bearer $TOKEN" '
    routes = {
        "ping": f"curl {base}/v1/ping",
        "categories": f"curl {auth}{base}/v1/categories",
        "catalog": f'curl {auth}"{base}/v1/catalog?category=judicial"',
        "schema": f"curl {auth}{base}/v1/schema/S0101",
        "query": (
            f"curl -X POST {auth}-H 'Content-Type: application/json' \\\n"
            f"  -d '{{\"entName\":\"示例企业\"}}' {base}/v1/query/S0101"
        ),
    }
    return routes.get(item["id"], f"curl {auth}{base}{item['path']}")


def render_api_endpoints(registry: dict) -> str:
    """API 文档 · 端点参考：由能力注册表生成，保证与运行时路由同源。"""
    caps = registry["capabilities"]
    if not caps:
        return HEADER + "# 端点参考\n\n等待主仓快照包含 `contract/capabilities.json`。\n"

    lines = [
        HEADER,
        "# 端点参考",
        "",
        "> 本页由 `contract/capabilities.json` 生成；路由、鉴权 scope、网关依赖与参数同源。",
        "> 详见 [API 总览](index.md) 与 [能力矩阵](../contract/capabilities.md)。",
        "",
        "## 通用约定",
        "",
        "| 项 | 说明 |",
        "|---|---|",
        "| Base URL | `http://127.0.0.1:8802`（本机）/ `http://altdatahub-service:8802`（内网 compose） |",
        "| 鉴权 | `Authorization: Bearer <token>`；`/v1/ping`、`/healthz` 不鉴权 |",
        "| 响应 | JSON，`success` + `data`；失败时带 `category` / `retryable` / `degrade_reason` |",
        "| 在线查询 | 需服务端 `EDS_*`；**未与真实网关联调**，失败显式降级、不伪造数据 |",
        "",
        "## 端点清单",
        "",
        "| 端点 | 能力 | 鉴权 scope | 网关 |",
        "|---|---|---|---|",
    ]
    for item in caps:
        scope = f"`{item['scope']}`" if item["scope"] else "免鉴权"
        lines.append(
            f"| `{item['method']} {item['pathTemplate']}` | `{item['id']}` | {scope} | {item['gatewayLabel']} |"
        )

    lines += ["", "## 逐端点说明", ""]
    for item in caps:
        lines += [f"### `{item['method']} {item['pathTemplate']}`", "", item["summary"] + "。", ""]
        schema = item["mcpInputSchema"]
        props = schema.get("properties", {})
        required = schema.get("required", [])
        if props:
            lines += ["| 参数 | 位置 | 必填 | 说明 |", "|---|---|---|---|"]
            for name, spec in props.items():
                if name == "product_code":
                    location = "path"
                elif item["argKind"] == "category":
                    location = "query"
                else:
                    location = "body"
                lines.append(
                    f"| `{name}` | {location} | {'是' if name in required else '否'} | {spec.get('description', '—')} |"
                )
            lines.append("")
        lines += ["```bash", curl_example(item), "```", ""]
        if item["requiresGateway"]:
            lines += [
                '!!! warning "在线能力未联调"',
                "    该端点依赖 EDS 网关。缺凭据或未联调时返回 `success=false` + `degrade_reason`，",
                "    这是「数据源未接入」，**不是「查无记录」**；`data: []` 才是正常成功。",
                "",
            ]

    lines += ["## 错误处置", "", "| 现象 | 分类 | 重试 | 建议 |", "|---|---|---|---|"]
    for row in registry.get("policyRows", []):
        lines.append(f"| `{row['label']}` | {row['category']} | {row['retryable']} | {row['hint']} |")
    lines += [
        "",
        "> 业务错误码（`1000/2000/3000/9999`）见 [数据契约](../contract/index.md)，",
        "> 一律以响应里的 `retryable` 为准。",
        "",
    ]
    return "\n".join(lines)


def tool_arguments(item: dict) -> dict:
    props = item["mcpInputSchema"].get("properties", {})
    examples = {
        "product_code": "S0101",
        "category": "judicial",
        "params": {"entName": "示例企业"},
    }
    return {key: examples[key] for key in props if key in examples}


def render_mcp_tools(registry: dict) -> str:
    """MCP 文档 · Tools 参考：inputSchema 与 tools/list 返回保持一致。"""
    caps = registry["capabilities"]
    if not caps:
        return HEADER + "# MCP Tools 参考\n\n等待主仓快照包含 `contract/capabilities.json`。\n"

    lines = [
        HEADER,
        "# MCP Tools 参考",
        "",
        "> 本页由 `contract/capabilities.json` 生成；`tools/list` 返回的 `inputSchema` 与本页一致。",
        "> 启动与配置见 [部署与配置](deploy.md)，概念见 [MCP 总览](index.md)。",
        "",
        "## Tools 一览",
        "",
        "| Tool | 能力 | 对应 HTTP | 网关 |",
        "|---|---|---|---|",
    ]
    for item in caps:
        lines.append(
            f"| `{item['mcpTool']}` | `{item['id']}` | `{item['method']} {item['pathTemplate']}` "
            f"| {item['gatewayLabel']} |"
        )

    lines += ["", "## 逐 Tool 说明", ""]
    for item in caps:
        lines += [
            f"### `{item['mcpTool']}`",
            "",
            item["mcpDescription"] + "。",
            "",
            f"- 对应能力：`{item['id']}` · scope `{item['scope'] or '免鉴权'}`",
            f"- Skill 命令：`{item['skillCommand']}`",
            "",
            "**inputSchema**",
            "",
            "```json",
            json.dumps(item["mcpInputSchema"], ensure_ascii=False, indent=2),
            "```",
            "",
            "**调用示例（JSON-RPC 2.0）**",
            "",
            "```json",
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": item["mcpTool"], "arguments": tool_arguments(item)},
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
            "",
        ]
        if item["requiresGateway"]:
            lines += [
                '!!! warning "不得伪造数据"',
                "    未联调或缺 `EDS_*` 时返回结构化降级；不能把 `success=false` 说成「未查到」，",
                "    也不能用示例数据冒充真实结果。",
                "",
            ]

    lines += [
        "## 通用返回结构",
        "",
        "```json",
        json.dumps(
            {"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": "{\"success\":true,...}"}]}},
            ensure_ascii=False,
            indent=2,
        ),
        "```",
        "",
        "大结果受 `MCP_MAX_CHARS` 裁剪；审计日志不落企业名明文与凭据。",
        "",
    ]
    return "\n".join(lines)


def render(manifest: dict) -> None:
    for path in GENERATED_DIRS:
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)
    for path in GENERATED_DIRS_KEEP:
        path.mkdir(parents=True, exist_ok=True)
    for path in GENERATED_FILES:
        if path.exists():
            path.unlink()

    rows: list[str] = []
    snapshot_sections: list[tuple[str, str]] = []
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
            snapshot_sections.append((f"快照原文：{rel}", content))

    registry = load_registry()
    capabilities_md = render_capabilities(registry)
    api_md = render_api_endpoints(registry)
    mcp_md = render_mcp_tools(registry)
    (DOCS / "contract" / "capabilities.md").write_text(capabilities_md, encoding="utf-8")
    (DOCS / "api" / "endpoints.md").write_text(api_md, encoding="utf-8")
    (DOCS / "mcp" / "tools.md").write_text(mcp_md, encoding="utf-8")

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
        + "| 能力矩阵 | [capabilities.md](capabilities.md) | [生成] 由 `contract/capabilities.json` 派生 |\n"
        + "| 端点参考 | [endpoints.md](../api/endpoints.md) | [生成] 路由、参数、示例 |\n"
        + "| 契约治理 | [分册升版](../guides/contract-governance.md) | 真源→派生、升版六步 |\n"
        + "| 能力级契约 | [service.yaml](../assets/openapi/service.yaml) | 对外 6 条路径，含 `degrade_reason` |\n"
        + "| 跨语言行为 | `contract/vectors.json` | 报文 / 错误码 / 信封的黄金向量（不进公开快照，见主仓） |\n\n"
        + "!!! warning \"响应信封仍未确认\"\n"
        + "    数据行所在层级、错误码字段名、51 个服务号、`eds_validday` 类型注释都未由真实响应钉死；\n"
        + "    SDK 用候选路径试探，联调后需按主仓 `docs/api/transport.md` 收敛。\n",
        encoding="utf-8",
    )

    changelog = UPSTREAM / "CHANGELOG.md"
    changelog_md = HEADER + (
        changelog.read_text(encoding="utf-8") if changelog.is_file() else "# 变更记录\n\n等待主仓快照。\n"
    )
    (DOCS / "changelog.md").write_text(changelog_md, encoding="utf-8")

    (DOCS / "llms.txt").write_text(
        "# altdatahub 文档\n\n"
        "> 第三方 SDK 文档：离线目录可用；在线查询未与真实网关联调，不伪造数据。\n\n"
        "## API 文档\n- [总览与鉴权](api/index.md)\n- [端点参考](api/endpoints.md)\n"
        "- [数据契约](contract/index.md)\n- [能力矩阵](contract/capabilities.md)\n"
        "- [原始文档镜像](reference/index.md)\n"
        "## MCP 文档\n- [总览](mcp/index.md)\n- [Tools 参考](mcp/tools.md)\n"
        "- [部署与配置](mcp/deploy.md)\n"
        "## 开发工具\n- [安装与 CLI](getting-started/install.md)\n- [Python SDK](guides/python.md)\n"
        "- [多语言 SDK](guides/sdks.md)\n- [能力服务部署](guides/service.md)\n"
        "- [工具链与生成器](guides/toolchain.md)\n- [契约治理与分册升版](guides/contract-governance.md)\n"
        "- [排障 FAQ](guides/troubleshooting.md)\n"
        "## 入门 / 其他\n- [首页](index.md)\n- [变更记录](changelog.md)\n- [全文聚合](llms-full.txt)\n",
        encoding="utf-8",
    )

    # llms-full：手写页 + 快照原文 + 关键派生页，带编号目录，避免原文内部 ## 标题混淆层级。
    site_sections = [
        (f"站点页面：{path.relative_to(DOCS).as_posix()}", page_text(path))
        for path in handwritten_pages()
    ]
    derived_sections = [
        ("派生页：api/endpoints.md", api_md),
        ("派生页：mcp/tools.md", mcp_md),
        ("派生页：contract/capabilities.md", capabilities_md),
        ("派生页：changelog.md", changelog_md),
    ]
    sections = site_sections + snapshot_sections + derived_sections
    # [NN] 前缀保证章节标题唯一，不会被快照原文里恰好以数字开头的 ## 标题冒充。
    titles = [f"[{index:02d}] {title}" for index, (title, _) in enumerate(sections, 1)]
    full = [
        "# altdatahub 文档全文",
        "",
        "> 由 scripts/build_docs.py 从本站手写页与 upstream/ 快照聚合，勿手改。",
        "> 章节按「站点页面 / 快照原文 / 派生页」分组并编号；原文内部的 `##` 标题不列入目录。",
        "",
        "## 目录",
        "",
        *[f"- {title}" for title in titles],
        "",
    ]
    for title, (_, content) in zip(titles, sections):
        full.extend([f"## {title}", "", content, ""])
    (DOCS / "llms-full.txt").write_text("\n".join(full) + "\n", encoding="utf-8")
    print(
        f"generated {len(rows)} reference assets, api/mcp/contract pages, changelog, "
        f"llms*.txt ({len(sections)} sections)"
    )


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
