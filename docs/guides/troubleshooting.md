---
search:
  boost: 1.5
---

# 排障 FAQ

先记住一条最重要的口径：**`data: []` 是正常成功**，不是「查无记录」，也不是接口故障。
网关尚未与真实响应联调，空结果不能推出业务结论。

## 在线查询返回 `success: false`

看响应里的 `category` / `degrade_reason`，不要只看 HTTP 状态：

| `category` | 含义 | 处置 |
|---|---|---|
| `configuration` | 服务端未配置 `EDS_*` 公共参数 | 补齐 7 个必填环境变量后重启能力服务 |
| `validation` | 本地参数校验失败 | 用 `catalog` / `schema` 核对 `productCode` 与业务参数名 |
| `contract` | 响应信封未按候选路径解析 | 属**未联调**的已知状态，报告待确认，不要重试或改数据 |
| `transport` | 网关网络/传输失败 | 以 `retryable` 为准；`9999` 用有界退避 |
| `upstream` | 上游/业务错误 | 以 `retryable` 为准 |

## 业务错误码

| 码 | 分类 | 重试 | 建议 |
|---|---|---|---|
| `1000` | validation | 否 | 核对服务号与业务参数名 |
| `2000` | validation | **否**（可能重复计费） | 加 `page` / 调小 `pageSize` |
| `3000` | authentication | 否 | 核对 `eds_account` 授权与服务号是否开通 |
| `9999` | upstream | 是 | 有界退避（建议 3 次、2^n×500ms） |

码表里**没有 success 码**，也**没有「查无数据」码**：响应不含上述四码即视为成功。

## 能力服务 HTTP 状态

| 状态 | 原因 | 处置 |
|---|---|---|
| `401` | 调用方 Token 无效/被吊销 | 用 `service/issue_token.py` 重新签发 |
| `403` | scope 不足或来源 IP 不在白名单 | 检查 `SERVICE_ALLOWED_CIDRS` 与 Token scopes |
| `429` | 触发限流 | 稍后重试；生产可调 `SERVICE_RATE_LIMIT_PER_MIN` |
| `404` | 路径不在能力注册表 | 看 [能力矩阵](../contract/capabilities.md) |

## `productCode` 找不到 / 服务号报错

产品编码**不连续**（没有 `S03`、`S06`），不要按规律猜。顺序固定：
`categories → catalog（定 productCode）→ schema（看字段字典）→ query`。
服务号目前按 `izxzx{productCode}` 模板拼装，51 个逐个核对属 P0 联调项。

## 请求被拒：`eds_` 前缀

业务参数不能以 `eds_` 开头，`build_payload` 会直接拒绝 —— 否则会顶掉 8 个公共参数
（尤其是 `eds_account` 凭据）。

## 容器与工具链

| 现象 | 原因 / 解决 |
|---|---|
| aarch64 机器拉不到镜像 | 用离线 zip 包 `docker load`，或检查制品库权限 |
| C SDK 编译报 `curl/curl.h` 缺失 | 安装 `libcurl4-openssl-dev` |
| .NET 启动报 `Couldn't find a valid ICU package` | 安装 `libicu-dev` |
| `twine upload --skip-existing` 报 `UnsupportedConfiguration` | CNB PyPI 制品库不支持该选项，发布只在 `pyproject.toml` 变更时触发 |
| GitHub Actions 在 `configure-pages` 失败 | Pages 站点未启用；`scripts/ensure_pages.py` 会幂等补齐 |

## 文档快照没更新

A 方案只在**主仓 `main.push` 且快照内容真的变化**时才提交；内容没变会打印
`snapshot unchanged, skip push`。所以没看到新的 `docs: sync snapshot ...` 不一定是故障，
先确认白名单文件是否改了。

## 还解决不了

用 [能力服务部署](service.md) 里的 `service/probe.py` 采集**原始请求/响应**
（凭据与主机已脱敏）。回传样例前请自行脱敏业务数据，但保留信封层级与字段名 ——
响应信封、错误码字段名、服务号、`eds_validday` 类型都要靠它钉死。
