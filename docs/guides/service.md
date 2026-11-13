# 能力服务部署

`service/` 把 Python SDK 包成长期运行的 HTTP 进程：调用方只发「能力名 / `productCode` /
业务参数」，不接触 8 个 `eds_*` 公共参数、服务号拼装与网关地址。纯标准库、零第三方依赖。

## 诚实口径

| 能力 | 状态 |
|---|---|
| `categories` / `catalog` / `schema` | **完全可用**，纯离线产品目录，不需要网关 |
| `query` | 代码路径完整，但 **EDS 网关尚未与真实响应联调**；缺 `EDS_*` 时返回 `success=false` + `degrade_reason`，不伪造数据 |

## aarch64 镜像

镜像 `docker.cnb.cool/h1s97x/whccb/altdatahub/altdatahub-service:0.1.0-arm64`
（`linux/arm64`，**不含凭据**）；离线环境也可向维护者要 zip 包（`docker load` 即用）。

```bash
docker pull docker.cnb.cool/h1s97x/whccb/altdatahub/altdatahub-service:0.1.0-arm64
cp .env.example .env && vi .env          # 7 个 EDS_* 必填
docker compose -f service/compose.arm64.yml --env-file .env up -d
curl http://127.0.0.1:8802/v1/ping
```

`EDS_*` 只放服务端环境变量；业务参数禁止以 `eds_` 开头，避免顶掉公共参数。

## 端点

| 端点 | 能力 | 网关 |
|---|---|---|
| `GET /v1/ping` | 健康检查（不鉴权） | 不需要 |
| `GET /v1/categories` | 10 个大类 | 不需要 |
| `GET /v1/catalog?category=judicial` | 51 个产品摘要 | 不需要 |
| `GET /v1/schema/{productCode}` | 单产品字段字典 | 不需要 |
| `POST /v1/query/{productCode}` | 通用在线查询 | **需要 `EDS_*`** |

生产形态用 `service/compose.internal.yml`：**不发布端口**，只加入调用方所在的 compose
网络，配合 `service/issue_token.py` 签发的 Token 注册表（只存 SHA-256 哈希）。

## 联调探针

`service/probe.py` 直连真实网关并落盘原始报文（请求 URL 主机脱敏、请求体
`eds_account` 脱敏、文件权限 0600），stdout 只报路径与字节数：

```bash
docker compose -f service/compose.arm64.yml --env-file .env --profile probe \
  run --rm probe --product-code S0101 --params '{"entName":"示例企业"}' --label success
```

回传样例前请自行脱敏业务数据，但**保留信封层级与字段名** —— 要用它钉死响应信封、
错误码字段名、51 个服务号与 `eds_validday` 类型。

!!! note "大数据纪律"
    `catalog` 只返回摘要；不要一次把 557 个顶层字段 + 397 个子结构字段全量贴回对话，
    用 `schema <code>` 按需查。
