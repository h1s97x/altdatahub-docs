# altdatahub 能力服务

把 `src/altdatahub/` SDK 包装成**长期运行的 HTTP 进程**，让调用方只发
「能力名 / productCode / 业务参数」，不接触 8 个 `eds_*` 公共参数、服务号拼装
或 EDS 网关地址。**纯标准库，无需 pip install**（同仓 SDK 核心也是零依赖）。

## 诚实口径（先读）

| 能力 | 状态 |
|---|---|
| `/v1/categories`、`/v1/catalog`、`/v1/schema/{code}` | ✅ **完全可用**，纯离线产品目录，不需要网关 |
| `/v1/query/{code}` | ⚠️ 代码路径完整，但 **EDS 网关尚未与真实响应联调** |

仓库 `docs/api/transport.md` 列了 4 项未确认：响应信封（数据行在哪一层）、
错误码字段名、51 个产品的服务号、`eds_validday` 类型。**没有 `EDS_*` 凭据时，
在线查询返回 `success=false` + `degrade_reason`，不会伪造数据**；拿到凭据后
仍需一次真实响应才能把信封/服务号钉死。

## 启动

```bash
# 1) 直接跑（回环、无鉴权调试）
PYTHONPATH=src python -m service
curl http://127.0.0.1:8802/v1/ping

# 2) 容器（只绑回环）
cp .env.example .env        # 填 EDS_*（可选）+ SERVICE_AUTH_TOKEN
docker compose -f service/compose.yml --env-file .env up -d --build

# 3) 生产：签发 Token → 不发布端口、只加入调用方网络
python service/issue_token.py --caller backend --scopes '*' --quiet
DUEAGENT_NETWORK=workspace_default \
  docker compose -f service/compose.internal.yml --env-file .env up -d --build
```

## 对外契约（能力级，不是 51 个 `/products/{code}`）

机器版见 `openapi/service.yaml`。

| 端点 | 能力名 | 网关 | 说明 |
|---|---|---|---|
| `GET /v1/ping`、`/healthz` | — | 不需要 | 不鉴权，返回能力清单与 `gateway_contract_status` |
| `GET /v1/categories` | `categories` | 不需要 | 10 大类、每类产品数 |
| `GET /v1/catalog?category=judicial` | `catalog` | 不需要 | 51 产品摘要（不倒全量字段字典：557 个顶层 + 397 个子结构） |
| `GET /v1/schema/S0101` | `schema` | 不需要 | 单产品字段字典（中文名/类型/长度/非空） |
| `POST /v1/query/S0101` | `query` | **需要** | body 是平铺业务参数，如 `{"entName":"贵州茅台"}` |

所有 `/v1/*`（除 ping）都要 `Authorization: Bearer <调用方 Token>`。
查询成功与失败**都返回 HTTP 200**，靠 `success` 区分；失败信封带
`category` / `retryable` / `degrade_reason` / `hint` / `note`，便于下游如实降级。

业务参数**不许以 `eds_` 开头**（会覆盖服务端公共参数），服务层会先拒绝。
参数名只允许标识符字符，值必须是标量（网关要求平铺），最多 40 个 / 8000 字符；
`productCode` 由 `catalog` 白名单校验，`category` 由 10 个大类 key 白名单校验。
缺 `EDS_*` 时按 `credentials.ENV_MAP`（SDK 真源）列出**变量名**，不回显取值。

## 调用示例

```bash
TOKEN=$(grep '^SERVICE_AUTH_TOKEN=' .env | cut -d= -f2-)
curl -s http://127.0.0.1:8802/v1/categories -H "Authorization: Bearer $TOKEN"
curl -s 'http://127.0.0.1:8802/v1/catalog?category=judicial' -H "Authorization: Bearer $TOKEN"
curl -s http://127.0.0.1:8802/v1/schema/S0101 -H "Authorization: Bearer $TOKEN"
curl -s -X POST http://127.0.0.1:8802/v1/query/S0101 \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"entName":"贵州茅台"}'
```

## 调用方 Token（推荐）

`service/auth.py` + `service/issue_token.py`：注册表只存 SHA-256 哈希、
权限 600、已 gitignore；每个调用方独立 `scopes`（`categories` / `catalog` /
`schema` / `query`）、可选过期、可单独吊销。

```bash
python service/issue_token.py --caller analyst --scopes categories,catalog,schema --quiet
python service/issue_token.py --list      # 只显示哈希前缀
python service/issue_token.py --revoke analyst
```

签发脚本**原地覆写**保持 inode 不变：注册表是单文件 bind mount，
换 inode 会让容器永远看到旧内容（新 Token 静默 401、吊销不生效）。

无注册表时回落到 `SERVICE_AUTH_TOKEN` 单一静态 Token；两者都没有且监听
非回环地址时**拒绝启动**。

## 安全与行为约定

- `SERVICE_ALLOWED_CIDRS` 来源 IP 白名单（配置写错时 fail closed）、
  `SERVICE_RATE_LIMIT_PER_MIN` 全局限流
- 审计只记 `caller` / 能力名 / 参数哈希 / 响应大小 / 耗时，不落企业名明文与凭据
- TTL 缓存仅缓存 `success=true`，失败不缓存（避免把故障固化）
- 大响应渐进式结构化裁剪（≤30000 字符），始终返回合法 JSON
- 健康检查不返回凭据配置状态，避免被外部探测

## 环境变量

见仓库根 `.env.example`。`EDS_*` 只在服务端；调用方只需服务地址 + 调用方 Token。

## 测试

```bash
PYTHONPATH=src python -m unittest discover -s service/tests -v
```
