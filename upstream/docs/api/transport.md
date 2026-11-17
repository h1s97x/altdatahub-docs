# 传输契约：已接入的部分与仍未知的部分

> 状态：**已接入，且已完成全量在线验证**：2026-11-16 S0101（HTTP 200 / 1 行），
> 2026-11-17 其余 50 个产品也逐条验证，51 个 `productCode` 经能力服务
> `POST /v1/query/{productCode}` 均返回 HTTP 200（部分 0 行为正常空结果）。信封层级、
> 错误码字段名与 `data[].data` 展平均已由真实响应确认，业务参数
> `entName` / `idNum` / `idType` / `queryReason` 平铺可用；默认 `izxzx{productCode}`
> 服务号模板全量可用。本文只写「有证据的」和「明确没有证据的」两类。

## 验证样本（2026-11-16 / 11-17）

用户只回传了部分截图，但明确说明 51 个产品已全部验证可用、部分无数据。下表只列有截图的样本，
不复述企业与证件号码：

| 产品码 | 产品名 | 大类 | 行数 | 结论 |
|---|---|---|---|---|
| `S0101` | 基本概况信息 | 企业基本信息 | 1 | 真实响应已确认信封与展平（2026-11-16） |
| `S0402` | 民事判决信息 | 司法 | 0 | 空结果按成功返回，符合「`data: []` 是正常成功」口径 |
| `S0501` | 专利信息 | 知识产权 | 2 | 业务字段正常返回 |
| `S1101` | 招标信息 | 经营 | 3 | 业务字段正常返回 |

这些调用都以数字 `eds_validday=0` 发出且网关未报参数错误，进一步支持“按数字传”的处置，
但仍不等于拿到被截断的类型原文。截图是能力服务的结构化输出，**不是网关原始报文**。

## 证据来源

《接口规范》Java 示例 `EDSSServiceTest`：

```java
private static final String SERVICE_URL = "http://<EDS_HOST>:9080/edsservice/api/gateway";
HttpPost httpPost = new HttpPost(SERVICE_URL);
httpPost.setHeader("Content-Type", "application/json;charset=utf-8");
httpPost.setHeader("Accept", "application/json");
httpPost.setEntity(new StringEntity(requestJson, Charset.forName("UTF-8")));
```

请求体 = 8 个 `eds_*` 公共参数 + 业务参数，**同层平铺**：

| 字段 | 含义 | 变体 |
|---|---|---|
| `eds_transcode` | 每个服务的唯一服务号，前缀为 `izxzx`（规范示例里的 `IQY/BXX` 是脱敏值） | 如 `izxzxS0101` |
| `eds_operateuserid` | 全行统一的用户编号 | — |
| `eds_operateusername` | 查询用户名 | 示例 `张三`（中文） |
| `eds_account` | 查询系统向外部数据服务申请的授权字串 | **凭据**，不传或传错将无法查询 |
| `eds_scene` | 来源系统简称，大写英文字母，全行统一 | 示例 `EDS` |
| `eds_orgid` | 查询机构编号 | — |
| `eds_orgidname` | 查询人所属机构名 | — |
| `eds_validday` | 数据有效期：0=每次查最新；N=N 天内复用 | **数字**，默认 0 |

**没有签名、没有时间戳、没有 AppKey、没有请求级信封。** 鉴权只靠 `eds_account`。
所以本仓不建 `signature.py`：多加一个签名字段会被网关当成脏参数。

## 接口与实现对照

| 接口 | 实现 | 测试 |
|---|---|---|
| `EdsConfig` / `EdsConfig.from_env()` | `credentials.py` | 缺变量只报变量名、`repr` 脱敏 account |
| 报文组装 `build_payload` | `wire.py` | `test_payload_matches_the_spec_sample`（逐字段对齐示例） |
| POST + JSON | `HttpTransport`（stdlib `urllib`） | 假 opener 断言 URL/方法/头/UTF-8 中文不转义 |
| 响应解包 | `wire.extract_rows` | 候选形状逐条钉住 |

## 业务错误码（已确认）

自助门户「错误码管理」页原文四条，`errors.EDS_ERROR_CODES` 与 OpenAPI 的 `x-error-codes`
都由这一处生成：

| 错误码 | 原文说明 | category | 可重试 | 处理 |
|---|---|---|---|---|
| `1000` | 请求参数无效，请重新确认！ | validation | ❌ | 核对服务号与业务参数名 |
| `2000` | 数据量返回超出阈值，请使用分页参数查询！ | validation | ❌ | 加 page / 调小 pageSize，别重试同一请求 |
| `3000` | 该账户无查询此接口权限！ | authentication | ❌ | 核对 `eds_account` 与服务号是否开通 |
| `9999` | 系统错误！ | upstream | ✅ | 有界退避（3 次、2^n×500ms） |

两条口径：

- 表里**没有「查无数据」**——`data: []` 是正常成功；
- 表里**没有 success 码**——响应里不含上述四码即视为成功（`code:"0000"` 是成功码，不在表内）。

字段名已由真实错误响应确认：顶层 **`code`**（字符串值），描述在 **`msg`**，数据位 `data`；
业务错误走 HTTP 200。判定仍保留「键名含 `code` + 值命中码表」的容错，兼容 `returnCode`
等历史字段名；真实响应 `code:"3000"` 被正确判为 authentication / 不重试。

## 已确认的响应信封（2026-11-13）

真实错误响应（探针落盘原文）：`{"msg":"...","code":"3000","data":""}`。
门户「服务验证」成功响应：`msg` / `code:"0000"` / `data` 是**主体数组**，每个主体含
`idType`、`entName` 和内层 `data` 数组；**产品数据行在内层 `data[].data`**，字段名与
`altdatahub schema S0101` 一致；多主体时按顺序展平为一个行数组。

7 语言 `extract_rows` 已按此实现（展平优先，取不到嵌套层时回退旧候选 `DATA_PATHS`），
`contract/vectors.json` v3 的 `extract-12/13/14` 用占位值固化了单主体、多主体、空结果三种形状。
各语言客户端同样先把展平结果写回 `data`，避免把主体外壳当数据行、业务字段静默为 `None`。

## 仍未确认（1 项）

| # | 未知 | 当前处置 | 怎么确认 |
|---|---|---|---|
| 1 | **`eds_validday` 的类型注释被截断**（截图里「注意：数字…」） | 按示例代码传**数字** `0`；51 个产品的真实请求均以数字发出且网关未报参数错误 | 补一张完整截图或原文；若要求字符串，改 `build_payload` 一处 |

服务号层面：默认 `izxzx{product_code}` 已由 51 个产品的真实查询全量验证，且所有产品共用同一
网关 URL；但尚未取得官方书面清单，因此模板仍保留 `EDS_SERVICE_CODE_PATTERN` 可覆盖，
拿到清单后应改为显式映射表（缺映射即失败，不再拼字符串）。

另外一项未验证：**`page`/`pageSize` 示例传的是 `"demo"` 字符串，真实调用是否要求数字**
（当前原样透传，不做类型转换）。

> 门户成功响应来自截图（非原始报文）；2026-11-16 / 11-17 经能力服务的多次真实在线查询中，
> `rows` 里直接是业务字段（非主体外壳），与 `data[].data` 展平口径一致。
> 原始报文留在内网机器、不出网；服务层仍按结构化降级如实返回，不把空数据当作「确无记录」。

## 安全纪律

- `eds_account` 只在 `EdsConfig` 里，`__repr__` 打码；错误信息只报变量名；
- 内网地址 `<EDS_HOST>` 不外泄到公开文档/日志（本仓文档里只作示例出现）；
- 联调凭据一律走环境变量（`EDS_*`），不写进代码、不写进 `.cnb.yml`。
