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

# 2) 容器（只绑宿主机回环；容器内监听 0.0.0.0，SERVICE_AUTH_TOKEN 必填非空）
cp .env.example .env        # 填非空的 SERVICE_AUTH_TOKEN，EDS_* 可选
docker compose -f service/compose.yml --env-file .env up -d --build

# 3) 生产：签发 Token → 不发布端口、只加入调用方网络
python service/issue_token.py --caller backend --scopes '*' --quiet
DUEAGENT_NETWORK=workspace_default \
  docker compose -f service/compose.internal.yml --env-file .env up -d --build
```

容器内 `SERVICE_HOST=0.0.0.0`，空 Token 会让服务按设计拒绝启动；`Container Started` 不等于端口已监听。
先确认 `docker logs altdatahub-service` 出现「能力服务已启动」，再 curl `/v1/ping`（不鉴权）。

## 联调 CLI（交互式）

`service/console_cli.py` 是纯标准库单文件工具：**不需要浏览器、不新增端口、不改服务端、不重建镜像**。
宿主机有 python3，把这一个文件和 `.env` 放到同一台机器上即可：

```bash
python3 service/console_cli.py                       # 交互式，默认读 ./.env
python3 service/console_cli.py --env-file .env --mode probe
```

两种模式：

- **网关探针（默认，替代手写 probe 脚本）**：逐项问答填 4 个必填业务参数（+ 2 个选填），
  从 `.env` 读 7 个 `EDS_*`，连同按 `izxzx<productCode>` 拼出的服务号组成 8 个公共参数，
  直接 POST 网关，把**原始响应**落盘到 `./probe/probe-<label>-<UTC>.json`（权限 0600），
  并打印信封层级摘要。
- **能力服务**：带 `SERVICE_AUTH_TOKEN` 调 `POST /v1/query/{code}`，看结构化结果与耗时。

支持「改一个参数重发」「打印完整响应」「打印可复制的 `--params`」，缺必填项会当场提示。
CLI 不回显 `EDS_*` 与 Token，落盘的请求体里 `eds_account` 脱敏、URL 主机脱敏为 `<EDS_HOST>`；
凭据只读本地 `.env`，不进仓库。它不改变 `src/altdatahub/cli.py` 只做离线元数据的边界。

## aarch64 联调镜像（P0）

CNB 在原生 `cnb:arch:arm64:v8` 节点上构建 `linux/arm64` 镜像并推送到 Docker 制品库，
**镜像内不含任何凭据**：

```bash
docker pull docker.cnb.cool/h1s97x/whccb/altdatahub/altdatahub-service:0.1.0-arm64
```

在 aarch64 机器上准备 `.env`（7 个 `EDS_*` 与非空 `SERVICE_AUTH_TOKEN` 必填，缺任意一个 compose 会直接报错），然后：

```bash
docker compose -f service/compose.arm64.yml --env-file .env up -d
curl http://127.0.0.1:8802/v1/ping

# 采集一份真实成功响应
docker compose -f service/compose.arm64.yml --env-file .env --profile probe \
  run --rm probe --product-code S0101 --params '{"entName":"<企业名称>","idNum":"<身份标识号码>","idType":"01","queryReason":"01"}' --label success

# 采集一份错误响应（换无效 productCode / 服务号）
docker compose -f service/compose.arm64.yml --env-file .env --profile probe \
  run --rm probe --product-code XXXX --params '{}' --label error
```

`--params` 要给全门户「服务验证」表单的必填业务参数，只传 `entName` 会被判参数不全。
按《接口规范》示例代码，S0101 常用键如下（`page` / `pageSize` 选填，可留空）：

| 门户表单 | 参数名 | 必填 |
|---|---|---|
| 企业名称 | `entName` | 是 |
| 企业身份标识号码 | `idNum` | 是 |
| 企业身份标识类型 | `idType` | 是 |
| 查询原因 | `queryReason` | 是 |
| 页数 / 每页大小 | `page` / `pageSize` | 否 |

字段名按《接口规范》示例代码推断，请对照门户测试表单截图核对；分册字段字典里的
`entCertNo` / `entCertType` 出现在响应字段中，请求侧示例代码用的是 `idNum` / `idType`。
内网数据不出网，不需要回传原始请求报文。
公开文档只放占位符，真实测试企业与证件号码只写进本地命令。

`--env-file` 是 **compose 顶层** flag，必须放在 `run` 之前，它给 compose 做变量插值，
不是探针 `python -m service.probe` 的参数（后者只认 `--product-code` / `--params` /
`--label` / `--out`）。

先用 `docker compose version` / `docker-compose version` 确认客户端：内网老机器若只有 v1
独立命令，全部示例改用 `docker-compose`（连字符）；`docker compose`（空格）会落回 docker
顶层 CLI，`-f` / `--env-file` 都可能报 `unknown flag`。v1 < 1.28 不支持 `--env-file` 时
省略即可（它默认读**工作目录**的 `.env`，所以要从仓库根执行）；不支持 `--profile` 时
`run --rm probe` 直接指定服务名即可：

```bash
docker-compose -f service/compose.arm64.yml up -d
docker-compose -f service/compose.arm64.yml run --rm probe \
  --product-code S0101 --params '{"entName":"<企业名称>","idNum":"<身份标识号码>","idType":"01","queryReason":"01"}' --label success
```

若 `docker-compose` 仍有 flag 或 schema 限制，绕开 compose 用 `docker run`（`--env-file` 是
docker 顶层原生 flag，老版本也支持）：

```bash
mkdir -p service/probe
grep -vE '^[[:space:]]*(#|$)' .env > /tmp/ah-probe.env
IMG=docker.cnb.cool/h1s97x/whccb/altdatahub/altdatahub-service:0.1.0-arm64
docker run --rm --env-file /tmp/ah-probe.env \
  -v "$(pwd)/service/probe:/app/probe" \
  --entrypoint python "$IMG" -m service.probe \
  --product-code S0101 --params '{"entName":"<企业名称>","idNum":"<身份标识号码>","idType":"01","queryReason":"01"}' --label success
```

探针把**原始响应体**写到 `service/probe/probe-<label>-<UTC>.json`（权限 0600）：compose 卷
`./probe` 相对 compose 文件所在的 `service/` 目录，不是仓库根，也不是可执行脚本。同时记录
请求 URL（主机脱敏为 `<EDS_HOST>`）、请求体（`eds_account` 脱敏）、HTTP 状态与响应原文，
以及 SDK 当前用 `check_error` / `extract_rows` 得到的解释结果；stdout 只报路径与字节数。

回传样例前请**自行脱敏响应里的业务数据，但保留信封层级与字段名** —— 要靠它钉死
4 项：数据行位置、错误码字段名、51 个服务号、`eds_validday` 类型；另有 2 项
（是否共用 URL、`page/pageSize` 是否要求数字）可用同一探针换参数验证。
本地若只需自建镜像：`docker buildx build --platform linux/arm64 -f service/Dockerfile -t altdatahub-service:arm64 .`。

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
