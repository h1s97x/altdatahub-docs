# MCP 与 Agent Skill

AI 接入层有两条路径，都复用同一个能力服务，**不持有 `EDS_*` 凭据**。

## MCP Server

`mcp/` 暴露 5 个 tools（名称与 inputSchema 由主仓 `contract/capabilities.json` 派生）：

| Tool | 作用 |
|---|---|
| `altdatahub_categories` | 列出 10 个产品大类（离线） |
| `altdatahub_catalog` | 产品清单，可按 `category` 过滤（离线） |
| `altdatahub_schema` | 单个 `productCode` 的字段字典（离线） |
| `altdatahub_query` | 按 `productCode` 查询数据（在线，需服务端 `EDS_*`） |
| `altdatahub_ping` | 检查能力服务可达（不鉴权） |

两种 transport 共用 `handle_request()`：

- **stdio**：`python -m mcp`，一行一个 JSON-RPC 2.0 消息，stdout 只走协议、日志走 stderr；
- **Streamable HTTP**：`python -m mcp --http`，无状态单端点 `POST /mcp`，notifications
  返回 202，`GET /mcp` 405，`/healthz` 不鉴权。

关键配置：`ALTDATAHUB_SERVICE_URL`、`ALTDATAHUB_SERVICE_TOKEN`、HTTP 模式的入站
`MCP_AUTH_TOKEN`（非回环必填）、`MCP_HOST` / `MCP_PORT`、`MCP_MAX_CHARS`（结果字符上限）。

## Agent Skill

`skills/altdatahub-service/` 是零依赖 Skill，工作流固定：

```
categories → catalog（定 productCode）→ schema（看字段字典）→ query
```

参考手册 `references/catalog.md` 的能力矩阵与错误码表由主仓注册表生成（勿手改）。
`productCode` 编码不连续（无 S03 / S06），**不要按规律猜**，先 `catalog`。

## 诚实口径（必须遵守）

- 网关**尚未与真实响应联调**：缺凭据返回 `success=false` + `degrade_reason`，
  这是「数据源未接入」，**不是「查无记录」**，也不是接口故障；
- **不能编造企业数据**，也不能用模拟/静态示例冒充真实结果；
- 重试一律以响应里的 `retryable` 为准（`1000/2000/3000` 不重试，`9999` 有界退避）；
- 大结果用 `--output` 落盘，只报告路径与字符数；审计日志不落企业名明文与凭据。

!!! warning "字段定义 ≠ 已查到数据"
    `S0101` 的字段字典里有 `legalRep`、`regCapital` 等**字段定义**；
    目录里存在这个字段，不代表已查到该企业的真实法定代表人。
