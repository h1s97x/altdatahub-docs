# 部署与配置

## 前置

- Python 3.10+（MCP 层零第三方依赖，核心 SDK 也是 stdlib only）
- 能力服务已启动并可达（默认 `http://127.0.0.1:8802`），见 [能力服务部署](../guides/service.md)
- 一个有效 Token：`python service/issue_token.py --caller mcp --scopes '*' --quiet`

## stdio 模式

```bash
PYTHONPATH=src python -m mcp
```

一行一个 JSON-RPC 2.0 消息。stdout **只走协议**，日志一律走 stderr，否则会污染协议流。
桌面客户端通常在配置里声明 command + args，例如：

```json
{
  "mcpServers": {
    "altdatahub": {
      "command": "python",
      "args": ["-m", "mcp"],
      "env": {
        "PYTHONPATH": "/path/to/altdatahub/src",
        "ALTDATAHUB_SERVICE_URL": "http://127.0.0.1:8802",
        "ALTDATAHUB_SERVICE_TOKEN": "<调用方 Token>"
      }
    }
  }
}
```

具体字段以你使用的客户端为准；路径与 Token 请替换成自己的值，**不要写进仓库**。

## Streamable HTTP 模式

```bash
PYTHONPATH=src python -m mcp --http
```

| 路由 | 行为 |
|---|---|
| `POST /mcp` | 无状态单端点，处理 JSON-RPC 请求 |
| `GET /mcp` | 405（不接受 GET） |
| notifications | 202，无响应体 |
| `/healthz` | 健康检查，不鉴权 |

非回环监听时**必须**设置 `MCP_AUTH_TOKEN`，否则按设计拒绝启动。

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `ALTDATAHUB_SERVICE_URL` | `http://127.0.0.1:8802` | 能力服务地址 |
| `ALTDATAHUB_SERVICE_TOKEN` | — | 调用能力服务的 Bearer Token（scope 需覆盖所用工具） |
| `MCP_AUTH_TOKEN` | — | HTTP 模式的入站 Token；非回环必填 |
| `MCP_HOST` / `MCP_PORT` | `127.0.0.1` / `8803` | HTTP 监听地址与端口 |
| `MCP_MAX_CHARS` | 有界默认值 | 单次结果字符上限，超出裁剪 |

`EDS_*` **不在这里配置** —— 凭据只在能力服务端，MCP 层不接触。

## 验证

```bash
curl http://127.0.0.1:8803/healthz
curl -X POST http://127.0.0.1:8803/mcp \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $MCP_AUTH_TOKEN" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

`tools/list` 应返回 5 个 tool，名称与 `inputSchema` 与 [Tools 参考](tools.md) 一致。

## 常见问题

| 现象 | 原因 / 处置 |
|---|---|
| 客户端报协议解析错误 | stdio 模式有日志打到 stdout；把日志重定向到 stderr |
| `tools/list` 返回空 | 能力服务不可达或 Token scope 不足；先看 `/healthz` 与 `401/403` |
| 非回环启动即退出 | 未设置 `MCP_AUTH_TOKEN`（刻意的安全约束） |
| 结果被截断 | `MCP_MAX_CHARS` 生效，改用 `schema`/`catalog` 缩小范围 |
| 在线查询返回 `success=false` | 属未联调/缺凭据的结构化降级，见 [MCP 总览](index.md) 诚实口径 |

更多排障见 [排障 FAQ](../guides/troubleshooting.md)。
