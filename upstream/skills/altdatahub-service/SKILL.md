---
name: altdatahub-service
version: 0.1.0
description: 查询中国人民银行征信中心「金融信用信息基础数据库替代数据通」的 10 大类 / 51 个 productCode 产品目录、字段字典与数据。通过已部署的 altdatahub 能力服务访问，AI 侧只持调用方 Token，不接触 EDS 网关公共参数。当用户询问某类企业替代数据有哪些产品、某产品有哪些字段、或要按 productCode 查数据时使用。
---

# altdatahub 替代数据通查询（能力服务版）

## 文件地图

```
altdatahub-service/
├── SKILL.md                    # 本文件：触发条件、工作流、降级语义
├── scripts/query.py            # 零依赖执行脚本：HTTP → 解析 → 格式化
└── references/catalog.md       # 能力矩阵、productCode 坑、错误码速查
```

| 文件 | 调用时机 |
|---|---|
| `SKILL.md` | 每次触发全文加载 |
| `scripts/query.py` | 阶段 1 执行 |
| `references/catalog.md` | 不确定产品码 / 参数 / 错误含义时按需引用 |

## 诚实口径（最重要）

**EDS 网关联调未完成**：响应信封与错误码字段名已确认，`docs/api/transport.md` 仍有 2 项
（各产品服务号清单、`eds_validday` 类型）未确认，且账号权限待开通。
`query` 能力在服务端未配置 `EDS_*` 公共参数时返回
`success=false` + `degrade_reason=未配置 EDS 网关公共参数`。

- 目录能力（`categories` / `catalog` / `schema`）**完全可用、纯离线**，不依赖网关
- 在线查询失败时必须如实说「数据源尚未接入 / 网关不可用」，
  **不能说成「查无记录」，更不能编造企业数据**
- 本 Skill 不向用户索要 `EDS_ACCOUNT` 等凭据；那只属于服务端

## 触发场景

- 「替代数据通有哪些产品 / 司法类能查什么」
- 「S0101 有哪些字段，哪些必填」
- 「查一下某企业的工商基本概况 / 民事判决 / 年报信息」
- 需要先确定 `productCode` 再组业务参数的任何场景

## 工作流程

### 阶段 0：检查配置

```bash
python -c "import os; print('OK' if os.getenv('ALTDATAHUB_SERVICE_URL') and os.getenv('ALTDATAHUB_SERVICE_TOKEN') else 'MISSING')"
```

- `OK` → 阶段 1
- `MISSING` → 停止并说明需要能力服务地址与调用方 Token，**不要索要 EDS 凭据、不要复述任何 Token 值**
- 可用 `ping` 能力确认服务可达

### 阶段 1：先查目录，再定产品码

**51 个 productCode 不连续**（无 S03 / S06），编码与章节号无关，不要猜。

1. 用户说业务意图而非产品码时，先列大类：
   ```bash
   python scripts/query.py --capability categories
   ```
2. 按大类取产品清单：
   ```bash
   python scripts/query.py --capability catalog --category judicial
   ```
3. 拿到 `product_code` 后查字段字典，确定业务参数名（如 `entName`）：
   ```bash
   python scripts/query.py --capability schema --product-code S0101
   ```
4. 需要数据时才发在线查询（业务参数平铺，不许 `eds_` 前缀）：
   ```bash
   python scripts/query.py --capability query --product-code S0101 --param entName=贵州茅台
   ```
5. 大结果用 `--output` 落盘，只报告路径与字符数，**不回显全量 JSON**。

### 阶段 2：呈现结果

- `success=true`：按用户语言整理；`row_count` 与 `rows` 一并说明
- `success=true` 但 `row_count=0`：说「未查询到相关记录」，**不是接口故障**
- `success=false`：转述 `error` / `degrade_reason` / `hint`，按错误分类给建议
- 任何响应都带 `note`：EDS 网关信封与服务号待确认，不要把空数据当结论
- 严禁把目录里的**字段定义**（例如 S0101 有 `legalRep` 字段）当成查到的**真实数据**

## 错误分类

| 现象 | 含义 | 处理 |
|---|---|---|
| `degrade_reason=未配置 EDS 网关公共参数` | 服务端缺 `EDS_*` | 说明数据源未接入，不重试 |
| `category=validation` | productCode 或业务参数不合法 | 回 `catalog` / `schema` 核对 |
| `业务参数不许以 eds_ 开头` | 参数会覆盖服务端公共凭据 | 去掉该参数 |
| HTTP 401 | 调用方 Token 无效/被吊销 | 找管理员重签，不重试 |
| HTTP 403 | scope 不足或来源 IP 不在白名单 | 说明权限边界 |
| HTTP 429 | 触发限流 | 稍后重试 |
| `category=contract` | 响应信封未按预期解析 | 核对网关报文结构 |
| `category=upstream` | 网关网络/业务错误 | 看 `retryable` 决定有界重试 |
| `code=2000` | 数据量超阈值 | 加 `page` / `pageSize`，**不要重试同一请求**（可能重复计费） |
| `code=3000` | 账户无该接口权限 | 核对服务号是否开通 |
| `code=9999` | 上游系统错误 | 有界退避重试 |

**重试与否一律以响应里的 `retryable` 为准。**

## 能力边界

| 擅长 | 超出范围 |
|---|---|
| 51 个产品的目录、字段字典、产品码核对 | 实时征信评分、企业信用评级 |
| 按 productCode 查询已开通产品的数据 | 全市场批量扫描 |
| 如实标注数据源未接入 | 绕过 Token 权限直连 EDS 网关 |

## Resources

| 资源 | 路径 |
|---|---|
| 能力矩阵与错误码 | `references/catalog.md` |
| 执行脚本 | `scripts/query.py` |
| 服务契约 | 仓库 `openapi/service.yaml` |
| 未联调清单 | 仓库 `docs/api/transport.md` |
