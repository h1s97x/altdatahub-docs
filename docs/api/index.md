---
search:
  boost: 2
---

# API 文档

能力服务把 51 个产品、557 个顶层字段与 8 个 `eds_*` 公共参数，收敛成 **5 个能力级端点**。
调用方只发「能力名 / `productCode` / 业务参数」，不接触网关地址、服务号拼装或凭据。

## 诚实口径（先读）

| 能力 | 状态 |
|---|---|
| `ping` / `categories` / `catalog` / `schema` | ✅ **完全可用**，纯离线产品目录，不需要网关 |
| `query` | ⚠️ 代码路径完整，但 **EDS 网关尚未与真实响应联调**；缺凭据时显式降级，不伪造数据 |
| 在线调试台 / 公开可调用 API | ❌ **不提供** —— 在线链路未联调，不做假调试界面，也不编造返回数据 |

!!! warning "本项目不是实时行情服务"
    文档里的 `Base URL` 指向**你自己部署**的能力服务（本机或内网 compose 网络）。
    本站不托管任何可公开调用的接口，也不提供试用 Token；响应信封、错误码字段名、
    51 个服务号与 `eds_validday` 类型仍待 P0 联调钉死。

## 三步跑通离线部分

```bash
PYTHONPATH=src python -m service                 # 或 docker compose -f service/compose.yml up -d
curl http://127.0.0.1:8802/v1/ping              # 不鉴权
curl -H "Authorization: Bearer $TOKEN" \
     http://127.0.0.1:8802/v1/categories
```

安装与部署细节见 [能力服务部署](../guides/service.md) 与 [安装与 CLI](../getting-started/install.md)。

## Base URL 与鉴权

| 形态 | Base URL | 说明 |
|---|---|---|
| 本机调试 | `http://127.0.0.1:8802` | compose 只绑宿主机回环 |
| 内网生产 | `http://altdatahub-service:8802` | `compose.internal.yml`，不发布端口，只加入调用方网络 |

除 `/v1/ping` 与 `/healthz` 外，所有端点需要 `Authorization: Bearer <token>`：

```bash
python service/issue_token.py --caller backend --scopes '*' --quiet
```

Token 注册表只存 SHA-256 哈希；`scope` 与能力一一对应（`categories` / `catalog` /
`schema` / `query`）。HTTP 401 表示 Token 无效或吊销，403 表示 scope 不足或来源 IP 不在白名单。

## 统一响应

成功（离线目录能力）：

```json
{"success": true, "data": {"count": 10, "categories": []}}
```

在线能力未就绪时是**结构化降级**，不是错误也不是「查无记录」：

```json
{
  "success": false,
  "error": "缺少 EDS 网关公共参数",
  "category": "configuration",
  "retryable": false,
  "degrade_reason": "未配置 EDS 网关公共参数"
}
```

`data: []` 是**正常成功**（码表里没有「查无数据」）；不能把空数组改写成「未查到」。

## 错误处置

| 现象 | 分类 | 重试 | 建议 |
|---|---|---|---|
| `1000` / `2000` / `3000` | validation / authentication | 否 | 核对参数、服务号与 `eds_account` |
| `9999` | upstream | 是 | 有界退避（建议 3 次、2^n×500ms） |
| HTTP 401 / 403 | 鉴权 / ACL | 否 | 重新签发 Token / 检查白名单 |
| HTTP 429 | 限流 | 是 | 稍后重试 |

**一律以响应里的 `retryable` 为准。** 完整策略见 [端点参考](endpoints.md)，
业务错误码见 [数据契约](../contract/index.md)。

## 端点速查

| 端点 | 能力 | 网关 |
|---|---|---|
| `GET /v1/ping` | 健康检查（不鉴权） | 不需要 |
| `GET /v1/categories` | 10 个大类 | 不需要 |
| `GET /v1/catalog` | 51 个产品摘要 | 不需要 |
| `GET /v1/schema/{productCode}` | 单产品字段字典 | 不需要 |
| `POST /v1/query/{productCode}` | 通用在线查询 | **需要 `EDS_*`** |

逐端点的参数表与 curl 示例见 [端点参考](endpoints.md)，机器版契约见
[openapi/service.yaml](../assets/openapi/service.yaml)。

## 限流、缓存、审计

`SERVICE_RATE_LIMIT_PER_MIN`（默认 120）、`SERVICE_CACHE_TTL`（默认 600 秒）与
`SERVICE_ALLOWED_CIDRS` 由服务端配置；审计日志不落企业名明文与 `EDS_*` 凭据，
大结果会被有界裁剪。

## 下一步

- [MCP 文档](../mcp/index.md)：把同样的 5 个能力暴露给 AI 客户端
- [开发工具](../guides/toolchain.md)：CLI、7 语言 SDK、生成器与联调镜像
- [排障 FAQ](../guides/troubleshooting.md)
