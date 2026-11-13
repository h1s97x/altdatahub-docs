# 能力矩阵与 productCode 坑

服务契约机器版见 `openapi/service.yaml`；产品目录真源是 `catalog/products.json`
（**勿手改**，由 `tools/extract_catalog.py` 生成）。AI 侧只持调用方 Token，
`EDS_*` 公共参数全在服务端。

## 能力 × 入参

| 能力 | 端点 | 必填 | 可选 | 网关 |
|---|---|---|---|---|
| `categories` | `GET /v1/categories` | — | — | 不需要 |
| `catalog` | `GET /v1/catalog` | — | `category`（大类 key） | 不需要 |
| `schema` | `GET /v1/schema/{code}` | `product_code` | — | 不需要 |
| `query` | `POST /v1/query/{code}` | `product_code` | 平铺业务参数 | **需要 `EDS_*`** |
| `ping` | `GET /v1/ping` | — | — | 不需要 |

`query` 的 body 是**业务参数平铺**（如 `{"entName":"贵州茅台","page":"1"}`），
8 个 `eds_*` 公共参数由服务端注入，业务参数含 `eds_` 前缀会被直接拒绝。

## 目录关键事实（别当 bug 修）

- **51 个 productCode、10 个大类**，编码**不连续**（无 S03 / S06），
  编码体系与章节号无关，**不要按规律猜 productCode**，先 `catalog`。
- 字段字典键名：`name`（英文）、`cnName`（中文名）、`type`、`length`、
  `required`、`description`。
- `S1104` 只有 4 个字段、`S1106` 只有 3 个 —— 分册原文如此。
- 只有 `S0206`（年报年份）与 `S1201`（会计年度）带查询参数 `productParameter`。
- `S0101` 字段里有 `legalRep`、`regCapital` 等**字段定义**；
  目录里有这个字段 ≠ 已经查到该企业的真实法定代表人，**不要当成数据**。
- `catalog` 只返回产品摘要（编码/名称/大类/字段数），
  要完整字段字典用 `schema`；别把 557 个顶层字段 + 397 个子结构字段全量贴回对话。

## 在线查询的诚实口径

`docs/api/transport.md` 列了 4 项未确认：

1. 响应信封：数据行在 `data` / `resultData` / `resultData.data` / `data.list` 哪一层
2. 错误码放在哪个字段，信封是否包一层
3. 各产品服务号（前缀 `izxzx`，其余 50 个是否同为 `izxzx<productCode>`）
4. `eds_validday` 的类型注释被截断（当前按示例代码传数字 `0`）

另外 2 项未验证：是否所有产品共用同一 URL；`page`/`pageSize` 是否要求数字。

**服务端没配 `EDS_*` 时**，`query` 返回：

```json
{
  "success": false,
  "error": "缺少 EDS 网关公共参数：…",
  "category": "configuration",
  "retryable": false,
  "degrade_reason": "未配置 EDS 网关公共参数",
  "hint": "在服务端 .env 配置 EDS_BASE_URL / EDS_ACCOUNT / …",
  "note": "EDS 网关尚未与真实响应联调…"
}
```

这是**数据源未接入**，不是「查无记录」，也不是接口故障。必须如实转述，
不能编造企业数据。成功与失败都走 HTTP 200，看 `success` 字段。

## 错误码速查

| 码 / 现象 | 分类 | 重试 | 建议 |
|---|---|---|---|
| `1000` | validation | 否 | 核对服务号与业务参数名 |
| `2000` | validation | **否**（可能重复计费） | 加 `page` / `pageSize` |
| `3000` | authentication | 否 | 核对 `eds_account` 授权与服务号是否开通 |
| `9999` | upstream | 是 | 有界退避重试 |
| `category=configuration` | 配置 | 否 | 服务端补 `EDS_*` |
| `category=contract` | 契约 | 否 | 响应信封未联调，报告待确认 |
| `category=upstream` | 上游 | 看 `retryable` | 按指示退避 |
| HTTP 401 | 鉴权 | 否 | 调用方 Token 无效/被吊销，重新签发 |
| HTTP 403 | 鉴权 / ACL | 否 | scope 不足或来源 IP 不在白名单 |
| HTTP 429 | 限流 | 是 | 稍后重试 |

**一律以响应里的 `retryable` 为准。**

## 权限与大数据纪律

- Token 的 `scopes` 是能力级：`categories` / `catalog` / `schema` / `query`
- 只给 AI 助手授权时，建议**只签前三个离线能力**，不发在线查询权限
- 大结果用 `--output` 落盘，只报告路径与字符数
- 审计日志不落企业名明文与凭据
