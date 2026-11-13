---
search:
  boost: 1.2
---

# 契约治理与分册升版

本页面向维护者：说明哪些文件是**真源**、哪些是**生成物**、改事实该动哪里。
日常使用请看 [Python SDK](python.md) 与 [快速开始](../getting-started/install.md)。

## 真源 → 派生

| 真源 | 派生（勿手改） | 生成/校验 |
|---|---|---|
| `catalog/products.json` | `src/altdatahub/models.py`、`_data/products.json`、`openapi/openapi.yaml`、`catalog/PRODUCTS.md`、各语言类型文件、11 份生成物 | `tools/gen_code.py` / `gen_code.py --check` |
| `catalog/schema.json` | 目录形状、类型枚举、必填键规则 | `tools/catalog_model.py`（解析器 / 生成器 / 测试 / 门禁共用） |
| `contract/capabilities.json` | `service/capabilities.json`（含 `routes`）、`mcp/tools.json`、Skill 参考生成块、**本站能力矩阵页** | `tools/verify.py sync --write` |
| `contract/vectors.json` | 7 个语言 SDK 的向量测试 | `tools/verify.py vectors` |
| `src/altdatahub/errors.py:EDS_ERROR_CODES` | 错误码表（注册表与文档都不复制码值） | `tools/verify.py sync` |
| 白名单文档 | 本站 `upstream/` 脱敏快照 | `tools/verify.py export` |

`contract/generated.json` 记录 11 个产物的 sha256、公开 API 签名摘要、生成器 sha256 与目录计数，
用来判断「只改了生成器」还是「真源变了」。

## 常用门禁

```bash
python tools/verify.py all              # 生成物 / 目录 / 向量 / 能力派生 / 链接 / 脱敏 / 快照
python tools/verify.py catalog          # schema.json 校验 products.json 与 names_en.json
python tools/verify.py diff OLD.json    # 分册升版语义 diff
python tools/verify.py sync --write     # 从能力注册表重生成派生文件
python tools/verify.py vectors          # case id / 7 语言 PARITY 标记门禁
python tools/verify.py export           # 导出脱敏文档快照
```

## 分册升版六步

1. **先留旧目录**：`cp catalog/products.json /tmp/products-old.json`；
2. `python tools/extract_catalog.py <new.pdf> -o catalog/products.json --check`；
3. `python tools/verify.py diff /tmp/products-old.json` —— 删产品 / 删字段 / 改类型会标红，
   必须人工确认是「分册真的改了」；
4. `python tools/gen_code.py`；
5. `python -m pytest tests/ -q`；
6. 看 `git diff catalog/products.json` 与 `git diff contract/generated.json`。

只看条数变化不够：顶层字段数从 557 掉到 500 可能是新分册精简，也可能是折行合并失效。

## 新增一个能力

只改 `contract/capabilities.json`（加 `id` / 路由 / `handler` / `argKind` / MCP tool / scope），
在 `service/capabilities.py` 加同名 handler，然后 `verify.py sync --write` 重生成。
HTTP 路由、MCP `tools/list`、Skill 参考与本站能力矩阵会自动可见；`verify.py sync` 会抓手写漂移。

## 新增一个向量 case

1. 在 `contract/vectors.json` 的 `payload` / `errors` / `extract` 组加带稳定 `id` 的 case；
2. **升 `version`**，并同步 7 个 consumer 的 `PARITY_VECTOR_VERSION` 标记；
3. 跑 `verify.py vectors` 与 7 语言测试 —— 各语言测试是全量参数化，新 case 自动被消费。

## 不做什么

不引入 Smithy / OpenAPI Generator 作为构建依赖，不把 `products.json` 换成 IDL，
不手写生成物，不在 P0 联调前把响应信封假设写成事实。
