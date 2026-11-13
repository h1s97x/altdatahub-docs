# 安装与离线 CLI

主仓核心**零第三方依赖**（Python 3.10+，仅标准库）。包尚未发布到 PyPI，
`pip install altdatahub` 目前不可用，从仓库源码安装：

```bash
pip install .                    # 或 pip install -e ".[dev]" 做开发
```

## 离线元数据 CLI

CLI 只做离线能力，不发网络请求，无需 `EDS_*` 凭据：

```bash
altdatahub categories                    # 10 个大类
altdatahub products --category judicial  # 某个大类下的 productCode
altdatahub schema S0101                  # 单产品字段字典
altdatahub schema S1201 --json           # 机器可读
```

!!! tip "大数据纪律"
    不要一次把全量目录/字段字典导出给对话或模型；用 `schema <code>` 按需查单产品。

## 在线查询需要什么

在线查询要 8 个 `eds_*` 公共参数（`EDS_BASE_URL` / `EDS_ACCOUNT` /
`EDS_OPERATE_USER_ID` / `EDS_OPERATE_USER_NAME` / `EDS_SCENE` /
`EDS_ORG_ID` / `EDS_ORG_ID_NAME` / `EDS_VALID_DAY`）与一次真实响应联调。
凭据只放服务端环境变量，不写进代码、文档或日志。

当前阶段：SDK 的 `HttpTransport` 已按《接口规范》示例代码实现，但**未与真实网关联调**；
响应信封、错误码字段名、各产品服务号等 4 项仍未确认，详见[契约](../contract/index.md)。
