# altdatahub（Java）

封装中国人民银行征信中心「**金融信用信息基础数据库替代数据通**」产品的第三方 Java SDK
（**非官方**，与征信中心无隶属关系）。

- **只有一个依赖**：`jackson-databind`（JSON），不引入 Web 框架 / 注解处理器；
- **Java 17**：用 `record` 承载模型、`switch` 表达式做分派；
- **模型是生成的**：`Types.java`（51 个产品 record + 12 个子结构）由 `tools/gen_code.py`
  从 `catalog/products.json` 产出，`gen_code.py --check` 在 CI 里守着，**不许手改**；
- **行为对齐 Python / TypeScript**：三个语言 SDK 的测试读同一份 `contract/vectors.json`。

## 构建与测试

```bash
cd sdks/java
mvn verify      # compile + JUnit 5（67 个用例，离线可跑，不发真实请求）
```

## 用法

```java
import com.altdatahub.HubClient;
import com.altdatahub.Transport;
import com.altdatahub.Types;

import java.util.List;
import java.util.Map;

// 离线：把上游响应喂进模型层，不发网络请求
Transport transport = new Transport.Mapping(Map.of(
        "S0101", Map.of("data", List.of(Map.of("entType", "有限责任公司")))));
HubClient offline = new HubClient(transport);

List<Types.S0101BasicProfile> rows = offline.enterpriseBasic(Map.of("entName", "贵州茅台"));
rows.get(0).entType(); // "有限责任公司"
rows.get(0).raw();     // 原始行，分册未覆盖的新字段不会丢

// 真实调用：从 EDS_* 环境变量取网关公共参数
HubClient client = HubClient.fromEnv();
List<Types.S0101BasicProfile> live = client.enterpriseBasic(Map.of(
        "entName", "贵州茅台",
        "page", "1",
        "pageSize", "20"));
```

`HubClient` 提供 10 个大类方法（`enterpriseBasic` / `marketSupervision` / `judicial` /
`intellectualProperty` / `stock` / `bond` / `administration` / `honor` / `operation` / `finance`）
与通用入口 `query(productCode, params)`。

**泛型是「按赋值目标推断」的**：`List<T>` 的 `T` 由调用方声明决定，类型不匹配不会在查询时
报错，而会在取字段时抛 `ClassCastException`。想让编译器帮忙，就显式写目标类型（如上）。

## 公共参数（环境变量）

缺任何一个都会在**本地**报错并列出变量名，不回显取值。

| 环境变量 | 说明 |
|---|---|
| `EDS_BASE_URL` | 网关地址 |
| `EDS_ACCOUNT` | 授权字串（凭据） |
| `EDS_OPERATE_USER_ID` / `EDS_OPERATE_USER_NAME` | 用户编号 / 查询用户名 |
| `EDS_SCENE` | 来源系统简称（大写英文字母） |
| `EDS_ORG_ID` / `EDS_ORG_ID_NAME` | 查询机构编号 / 机构名 |
| `EDS_VALID_DAY` | 选填，数据有效期（0=每次查最新），默认 0 |
| `EDS_TIMEOUT` | 选填，**秒**（内部换算成毫秒），默认 30 |
| `EDS_SERVICE_CODE_PATTERN` | 选填，服务号模板，默认 `izxzx{product_code}` |

## 异常

全部继承 `Errors.HubException`（均为 `RuntimeException`），按「调用方该怎么处理」命名：

| 异常 | 场景 | 处置 |
|---|---|---|
| `SpecPendingException` | 没配传输（默认 `Transport.Pending`） | 部署期问题，不要重试 |
| `ValidationException` | 未知 productCode、类别不匹配、业务参数以 `eds_` 开头 | 改代码，**不花钱** |
| `TransportException` | 网络 / HTTP 失败，带 `getStatus()` 与 `isRetryable()` | 4xx 改请求，5xx 才退避 |
| `EdsBizException` | 网关业务错误码（1000/2000/3000/9999），带 `getCategory()` / `isRetryable()` / `getHint()` | 见 `retryable` |
| `ResponseException` | 拿到响应但不是预期结构 | 多半是上游变更，**先别重试** |

## 与 Python 版的对应关系

| Python | Java |
|---|---|
| `client.enterprise_basic(code, entName="x")` | `client.enterpriseBasic(code, Map.of("entName", "x"))` |
| `client.from_env()` | `HubClient.fromEnv()` |
| `EdsConfig(...)` 的 `org_id` | `EdsConfig.Builder.orgId(...)` |
| `list[Record]` | `List<Types.XXX>`，可空字段为 `null` |
| `EdsBizError.retryable` | `EdsBizException.isRetryable()` |

错误码表、重试语义、「先判错再取数据行」的链路顺序与 Python / TypeScript 版逐条一致 ——
由 `contract/vectors.json` 里同一批断言守着（`ContractVectorsTest`）。

## 未确认项

响应信封形状、错误码字段名、部分产品的业务参数 —— 与 Python 版共享同一批未知，
详见 [`docs/api/transport.md`](../../docs/api/transport.md)。
