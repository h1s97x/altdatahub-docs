# 传输契约：已接入的部分与仍未知的部分

> 状态：**已接入（基于《接口规范》示例代码）**，但**未对真实网关联调过**。
> 本文只写「有证据的」和「明确没有证据的」两类，不写「按规范实现」这种无法验证的话。

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
- 表里**没有 success 码**——响应里不含上述四码即视为成功。

识别方式是「值判定」：在顶层找**键名含 `code`** 的字段，值命中四个码之一才算业务错误。
这是过渡手段（字段名尚未见到），拿到响应样例后收敛成固定键名，并删掉猜测部分。

## 仍未确认（4 项，都影响联调）

| # | 未知 | 当前处置 | 怎么确认 |
|---|---|---|---|
| 1 | **响应信封形状**：数据行在 `data` / `resultData` / `resultData.data` / `data.list` 哪一层 | `wire.DATA_PATHS` 按顺序试，全部落空才报错并附 400 字符响应片段 | 门户页的「响应报文」栏是空的，仍需一个真实响应 |
| 2 | **错误码放在哪个字段**（`code` / `returnCode` / …）以及信封是否包一层 | 按「键名含 code + 值命中码表」判定，不猜固定键名 | 一个真实错误响应即可定死 |
| 3 | **各产品的服务号**：前缀已确认为 `izxzx`（规范示例里的 `IQY/BXX` 是脱敏值）；其余 50 个是否同为 `izxzx<productCode>` 未确认 | `EdsConfig.service_code_pattern` 默认按 `izxzx{product_code}` 拼装，可用 `EDS_SERVICE_CODE_PATTERN` 覆盖 | 向网关要服务号清单；拿到后改成显式映射表（缺映射即失败，不再拼字符串） |
| 4 | **`eds_validday` 的类型注释被截断**（截图里「注意：数字…」） | 按示例代码传**数字** `0` | 补一张完整截图或原文；若要求字符串，改 `build_payload` 一处 |

另外两点未验证：**是否所有产品共用同一 URL**（示例只有一个地址）；**`page`/`pageSize`
示例传的是 `"demo"` 字符串，真实调用是否要求数字**（当前原样透传，不做类型转换）。

## 安全纪律

- `eds_account` 只在 `EdsConfig` 里，`__repr__` 打码；错误信息只报变量名；
- 内网地址 `<EDS_HOST>` 不外泄到公开文档/日志（本仓文档里只作示例出现）；
- 联调凭据一律走环境变量（`EDS_*`），不写进代码、不写进 `.cnb.yml`。
