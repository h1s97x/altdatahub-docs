# altdatahub（Go）

封装中国人民银行征信中心「**金融信用信息基础数据库替代数据通**」产品的第三方 Go SDK
（**非官方**，与征信中心无隶属关系）。

- **零第三方依赖**：只用标准库（`net/http` + `encoding/json`）;
- **模型是生成的**：`types_gen.go`（51 个产品 struct + 12 个子结构）由 `tools/gen_code.py`
  从 `catalog/products.json` 产出，`gen_code.py --check` 在 CI 里守着，**不许手改**；
- **行为对齐 Python / TypeScript / Java**：四个语言 SDK 的测试读同一份 `contract/vectors.json`。

## 构建与测试

```bash
cd sdks/go
go vet ./...
go test ./...
gofmt -l .      # 必须无输出
```

## 用法

```go
package main

import (
	"fmt"

	altdatahub "github.com/h1s97x/altdatahub"
)

func main() {
	// 离线：把上游响应喂进模型层，不发网络请求
	client := altdatahub.NewHubClient(altdatahub.NewMapping(map[string]map[string]any{
		"S0101": {"data": []any{map[string]any{"entType": "有限责任公司"}}},
	}))

	rows, err := client.EnterpriseBasic("S0101", map[string]any{"entName": "贵州茅台"})
	if err != nil {
		panic(err)
	}
	profile := rows[0].(*altdatahub.S0101BasicProfile)
	fmt.Println(*profile.EntType) // 有限责任公司
	fmt.Println(profile.Raw)      // 原始行，分册未覆盖的新字段不会丢

	// 真实调用：从 EDS_* 环境变量取网关公共参数
	live, err := altdatahub.FromEnv()
	if err != nil {
		panic(err)
	}
	_, _ = live.EnterpriseBasic("S0101", map[string]any{"entName": "贵州茅台", "page": "1"})
}
```

Go 没有默认参数，`productCode` 必填（用 `altdatahub.ProductCodes` 里的常量）。
`HubClient` 提供 10 个大类方法与通用入口 `Query(productCode, params)`；返回值是 `[]any`，
元素是 `types_gen.go` 里的 `*SXXX` 结构，调用方按产品断言。

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

## 错误

用 `errors.As` 判断类型，不要匹配字符串：

| 类型 | 场景 | 处置 |
|---|---|---|
| `*SpecPendingError` | 没配传输（`NewHubClient(nil)`） | 部署期问题，不要重试 |
| `*ValidationError` | 未知 productCode、类别不匹配、业务参数以 `eds_` 开头 | 改代码，**不花钱** |
| `*TransportError` | 网络 / HTTP 失败，带 `Status` 与 `Retryable` | 4xx 改请求，5xx 才退避 |
| `*BizError` | 网关业务错误码（1000/2000/3000/9999），带 `Category` / `Retryable` / `Hint` | 见 `Retryable` |
| `*ResponseError` | 拿到响应但不是预期结构 | 多半是上游变更，**先别重试** |

## 与 Python 版的对应关系

| Python | Go |
|---|---|
| `client.enterprise_basic("S0101", entName="x")` | `client.EnterpriseBasic("S0101", map[string]any{"entName": "x"})` |
| `client.from_env()` | `altdatahub.FromEnv()` |
| `list[Record]` | `[]any`，元素是 `*SXXX` 结构 |
| `None`（缺字段） | `nil`（`*string` / map / slice） |
| `EdsBizError.retryable` | `BizError.Retryable` |

错误码表、重试语义、「先判错再取数据行」的链路顺序与 Python / TypeScript / Java 版逐条一致 ——
由 `contract/vectors.json` 里同一批断言守着（`contract_test.go`）。

## 未确认项

响应信封形状、错误码字段名、部分产品的业务参数 —— 与 Python 版共享同一批未知，
详见 [`docs/api/transport.md`](../../docs/api/transport.md)。
