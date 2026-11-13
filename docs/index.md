# altdatahub 文档

!!! warning "诚实口径（先读）"
    本项目是**第三方 SDK**，非征信中心官方发布，与征信中心无隶属关系。

    - 离线目录能力（10 大类 / 51 个 `productCode` / 字段字典）**完全可用**，不依赖网关；
    - 在线查询**尚未与真实 EDS 网关联调**：缺 `EDS_*` 凭据时返回
      `success=false` + `degrade_reason`，**不伪造数据**；
    - 本站点当前**只出构建产物，未上线部署**。

## 从哪里开始

| 想做什么 | 去哪里 |
|---|---|
| 安装 / 离线 CLI | [安装与离线 CLI](getting-started/install.md) |
| Python SDK 查询 | [Python SDK](guides/python.md) |
| 其它语言 SDK | [多语言 SDK](guides/sdks.md) |
| 数据 / 传输契约 | [契约](contract/index.md) |
| 主仓原始文档 | [原始文档镜像](reference/index.md) |
| 给 AI 客户端 | [llms.txt](llms.txt) / [llms-full.txt](llms-full.txt) |

## 工作流

先 `categories` → `catalog` 定 `productCode` → `schema` 看字段字典，
最后才发在线查询。产品编码不连续（无 S03 / S06），**不要猜 productCode**。

!!! note "数据源未接入 ≠ 查无记录"
    在线查询失败时必须如实说明「网关未联调 / 未配置凭据」，不能当成空数据，更不能编造记录。
