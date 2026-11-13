---
search:
  boost: 2
---

# MCP 文档

[Model Context Protocol](https://modelcontextprotocol.io/) 接入层把同一批能力暴露为 tools，
让 AI 客户端按「大类 → 产品 → 字段字典 → 查询」的顺序使用，而**不持有 `EDS_*` 凭据**。

## 5 个 Tools

| Tool | 能力 | 对应 HTTP | 网关 |
|---|---|---|---|
| `altdatahub_categories` | 列出 10 个大类（离线） | `GET /v1/categories` | 不需要 |
| `altdatahub_catalog` | 产品清单，可按大类过滤（离线） | `GET /v1/catalog` | 不需要 |
| `altdatahub_schema` | 单产品字段字典（离线） | `GET /v1/schema/{productCode}` | 不需要 |
| `altdatahub_query` | 按 `productCode` 查询（在线） | `POST /v1/query/{productCode}` | **需要 `EDS_*`** |
| `altdatahub_ping` | 检查能力服务可达（不鉴权） | `GET /v1/ping` | 不需要 |

名称、`description` 与 `inputSchema` 由主仓 `contract/capabilities.json` 派生，
与 [能力矩阵](../contract/capabilities.md) 同源。逐 tool 的 schema 与调用示例见
[Tools 参考](tools.md)。

## 两种 Transport

| 模式 | 启动 | 协议 | 适用 |
|---|---|---|---|
| **stdio** | `python -m mcp` | 一行一个 JSON-RPC 2.0，stdout 只走协议、日志走 stderr | 桌面客户端、本地 Agent |
| **Streamable HTTP** | `python -m mcp --http` | 无状态单端点 `POST /mcp`；notifications 返回 202，`GET /mcp` 405，`/healthz` 不鉴权 | 服务端集成、多客户端共享 |

两种模式共用同一个 `handle_request()`，工具行为一致。HTTP 模式非回环时必须设置
入站 `MCP_AUTH_TOKEN`。配置细节见 [部署与配置](deploy.md)。

## 与能力服务的关系

```
AI 客户端 ──MCP(stdio/HTTP)──> mcp/server.py ──HTTP + Bearer──> service(8802) ──> 离线目录
                                                                    └──EDS 网关（未联调）
```

MCP 层只做 tools 注册与转发：鉴权、缓存、限流、审计与降级都在能力服务里。
因此无论从 API、MCP 还是 Skill 进来，**降级口径完全一致**。

## Agent Skill

`skills/altdatahub-service/` 是零依赖 Skill，工作流固定：

```
categories → catalog（定 productCode）→ schema（看字段字典）→ query
```

参考手册 `references/catalog.md` 的能力矩阵与错误码表由主仓注册表生成。
`productCode` 编码不连续（无 `S03` / `S06`），**不要按规律猜**。

## 诚实口径（必须遵守）

- 网关**尚未与真实响应联调**：缺凭据返回 `success=false` + `degrade_reason`，
  这是「数据源未接入」，**不是「查无记录」**，也不是接口故障；
- **不能编造企业数据**，不能用模拟/静态示例冒充真实结果；
- 重试一律以响应里的 `retryable` 为准；
- 大结果用 `--output` 落盘，只报告路径与字符数；审计日志不落企业名明文与凭据。

!!! warning "字段定义 ≠ 已查到数据"
    `S0101` 的字段字典里有 `legalRep`、`regCapital` 等**字段定义**；
    目录里存在这个字段，不代表已查到该企业的真实法定代表人。

## 下一步

- [Tools 参考](tools.md)：5 个 tool 的 `inputSchema` 与 JSON-RPC 调用示例
- [部署与配置](deploy.md)：环境变量、客户端配置、健康检查
- [API 文档](../api/index.md)：直接调用 HTTP 端点
