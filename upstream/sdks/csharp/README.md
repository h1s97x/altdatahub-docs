# altdatahub（C#）

封装中国人民银行征信中心「**金融信用信息基础数据库替代数据通**」产品的第三方 .NET SDK
（**非官方**，与征信中心无隶属关系）。

- **零 NuGet**：JSON 用 `System.Text.Json`、HTTP 用 `HttpClient`，都在 .NET 8 框架里；
  连测试都不用 xunit —— 测试工程是个自跑 console，`dotnet run` 的退出码即结论；
- **模型是生成的**：`Types.cs`（51 个产品 record + 12 个子结构）由 `tools/gen_code.py`
  从 `catalog/products.json` 产出，`gen_code.py --check` 在 CI 里守着，**不许手改**；
- **行为对齐 Python / TypeScript / Java / Go**：五个语言 SDK 读同一份 `contract/vectors.json`。

## 构建与测试

```bash
cd sdks/csharp
dotnet build Altdatahub.sln -c Release
dotnet run --project tests/Altdatahub.Tests -c Release   # 退出码 0 = 全部用例通过
```

## 用法

```csharp
using Altdatahub;

// 离线：把上游响应喂进模型层，不发网络请求
var offline = new HubClient(new MappingTransport(new Dictionary<string, Dictionary<string, object?>>
{
    ["S0101"] = new() { ["data"] = new List<object?> { new Dictionary<string, object?> { ["entType"] = "有限责任公司" } } },
}));

var rows = offline.EnterpriseBasic<S0101BasicProfile>("S0101",
    new Dictionary<string, object?> { ["entName"] = "贵州茅台" });
Console.WriteLine(rows[0].EntType); // 有限责任公司
Console.WriteLine(rows[0].Raw);     // 原始行，分册未覆盖的新字段不会丢

// 真实调用：从 EDS_* 环境变量取网关公共参数
var client = HubClient.FromEnv();
var live = client.EnterpriseBasic<S0101BasicProfile>("S0101",
    new Dictionary<string, object?> { ["entName"] = "贵州茅台", ["page"] = "1" });
```

`HubClient` 提供 10 个大类方法与通用入口 `Query<T>(productCode, parameters)`；
泛型参数由调用方标注，类型与 productCode 不匹配时会在取字段处抛 `InvalidCastException`。

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
| `EDS_TIMEOUT` | 选填，**秒**，默认 30 |
| `EDS_SERVICE_CODE_PATTERN` | 选填，服务号模板，默认 `izxzx{product_code}` |

## 异常

全部继承 `HubException`：

| 异常 | 场景 | 处置 |
|---|---|---|
| `SpecPendingException` | 没配传输（默认 `PendingTransport`） | 部署期问题，不要重试 |
| `ValidationException` | 未知 productCode、类别不匹配、业务参数以 `eds_` 开头 | 改代码，**不花钱** |
| `TransportException` | 网络 / HTTP 失败，带 `Status` 与 `Retryable` | 4xx 改请求，5xx 才退避 |
| `EdsBizException` | 网关业务错误码（1000/2000/3000/9999），带 `Category` / `Retryable` / `Hint` | 见 `Retryable` |
| `ResponseException` | 拿到响应但不是预期结构 | 多半是上游变更，**先别重试** |

## 与 Python 版的对应关系

| Python | C# |
|---|---|
| `client.enterprise_basic("S0101", entName="x")` | `client.EnterpriseBasic<S0101BasicProfile>("S0101", new Dictionary<string, object?> { ["entName"] = "x" })` |
| `client.from_env()` | `HubClient.FromEnv()` |
| `EdsConfig(...)` 的 `org_id` | `EdsConfig.OrgId`（PascalCase） |
| `list[Record]` | `IReadOnlyList<T>` |
| `None`（缺字段） | `null` |

错误码表、重试语义、「先判错再取数据行」的链路顺序与其他语言逐条一致 ——
由 `contract/vectors.json` 里同一批断言守着（`ContractVectorTests`）。

## 未确认项

响应信封（`data[].data`）与错误码字段名（`code` / `msg`）已确认；仍待确认服务号清单、
`eds_validday` 类型原文 —— 与 Python 版共享同一批未知，
详见 [`docs/api/transport.md`](../../docs/api/transport.md)。
