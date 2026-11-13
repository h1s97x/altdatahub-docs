# altdatahub MCP Server

把 [能力服务](../service/README.md) 包装成 [Model Context Protocol](https://modelcontextprotocol.io)
工具，让 AI 客户端（Claude Desktop、CodeBuddy、Cursor、Cline 等）查询
**51 个 productCode 的产品目录、字段字典与数据**。纯标准库、零 pip install。

| transport | 启动 | 适用 |
|---|---|---|
| `stdio` | `python -m mcp` | AI 客户端与代码在同一台机器 |
| **Streamable HTTP** | `python -m mcp --http` → `POST /mcp` | 远程 AI 客户端、容器化部署 |

两种 transport 共用同一套 5 个 tools 与 `handle_request()`。

## Tools

| 工具 | 入参 | 网关 |
|---|---|---|
| `altdatahub_categories` | 无 | 不需要（离线） |
| `altdatahub_catalog` | `category?` | 不需要（离线） |
| `altdatahub_schema` | `product_code` | 不需要（离线） |
| `altdatahub_query` | `product_code`, `params?` | 需要 `EDS_*` |
| `altdatahub_ping` | 无 | 不需要 |

**离线三件套完全可用**：AI 可以先 `categories` → `catalog` → `schema` 搞清
「查什么、有哪些字段、怎么组参数」，再决定要不要发在线查询。

## 诚实口径

EDS 网关**尚未与真实响应联调**：`docs/api/transport.md` 列的 4 项
（响应信封 / 错误码字段名 / 服务号 / `eds_validday` 类型）未确认。
`altdatahub_query` 在未配置 `EDS_*` 时返回 `isError=true` 的**文本结果**，
内容含 `degrade_reason: 未配置 EDS 网关公共参数` 与 `note`，模型应如实告知
用户「数据源未接入」，**不能把降级当空数据，更不能编造记录**。

## 1. stdio（本机）

```bash
export ALTDATAHUB_SERVICE_URL=http://127.0.0.1:8802
export ALTDATAHUB_SERVICE_TOKEN=<调用方 Token>
```
```json
{
  "mcpServers": {
    "altdatahub": {
      "command": "python3",
      "args": ["-m", "mcp"],
      "cwd": "/path/to/altdatahub",
      "env": {
        "ALTDATAHUB_SERVICE_URL": "http://127.0.0.1:8802",
        "ALTDATAHUB_SERVICE_TOKEN": "<调用方 Token>"
      }
    }
  }
}
```

手动冒烟：

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"altdatahub_categories","arguments":{}}}' \
  | python -m mcp
```

## 2. Streamable HTTP（远程）

```bash
python service/issue_token.py --caller mcp-gateway \
  --scopes categories,catalog,schema,query --quiet   # 明文只输出一次
# 写入 .env：ALTDATAHUB_SERVICE_TOKEN=<上面的值>、MCP_AUTH_TOKEN=$(openssl rand -hex 32)

DUEAGENT_NETWORK=workspace_default \
  docker compose -f mcp/compose.yml --env-file .env up -d --build
```

客户端：

```json
{
  "mcpServers": {
    "altdatahub": {
      "url": "https://mcp.internal.example/mcp",
      "headers": { "Authorization": "Bearer <MCP_AUTH_TOKEN>" }
    }
  }
}
```

curl 冒烟：

```bash
TOKEN=$(grep '^MCP_AUTH_TOKEN=' .env | cut -d= -f2-)
curl -s http://127.0.0.1:8803/healthz
curl -s -X POST http://127.0.0.1:8803/mcp \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

**协议**：单端点 `POST /mcp`、无状态；`notifications/*` → 202 空体；
支持 JSON-RPC 批处理；`GET /mcp` → 405；`GET /healthz` 不鉴权。

**安全默认**：只绑 `127.0.0.1:8803`；`MCP_AUTH_TOKEN` 为空且非回环监听时拒绝启动；
可选 `MCP_ALLOWED_CIDRS`、`MCP_RATE_LIMIT_PER_MIN`。跨主机不要直接改成 `0.0.0.0`，
应前置带 TLS/mTLS 的反向代理。

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `ALTDATAHUB_SERVICE_URL` | `http://127.0.0.1:8802` | 能力服务地址 |
| `ALTDATAHUB_SERVICE_TOKEN` | 空 | 出站调用方 Token（不是 EDS 凭据） |
| `MCP_AUTH_TOKEN` | 空 | HTTP 入站 Token；非回环必填 |
| `MCP_HOST` / `MCP_PORT` | `127.0.0.1` / `8803` | HTTP 监听 |
| `MCP_MAX_CHARS` | 40000 | 结果上限；超限返回结构化摘要，不回传半截 JSON |
| `MCP_ALLOWED_CIDRS` | 空 | 来源 IP 白名单（配错 fail closed） |
| `MCP_RATE_LIMIT_PER_MIN` | 0 | 全局限流 |

## 测试

```bash
python -m unittest discover -s mcp/tests -v
```
