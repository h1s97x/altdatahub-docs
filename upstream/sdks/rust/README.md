# altdatahub（Rust）

封装中国人民银行征信中心「**金融信用信息基础数据库替代数据通**」产品的第三方 Rust SDK
（**非官方**，与征信中心无隶属关系）。

- **只有两个依赖**：`serde_json`（JSON）+ `ureq`（HTTP，rustls，无系统库依赖，CI 不用装 libcurl）；
- **模型是生成的**：`src/types.rs`（51 个产品 struct + 12 个子结构）由 `tools/gen_code.py`
  从 `catalog/products.json` 产出，`gen_code.py --check` 在 CI 里守着，**不许手改**；
- **反序列化不苛求**：字段一律 `Option`，上游漏字段降级为 `None`、多出来的字段进 `raw`，
  字符串字段还能接受 number（上游常把 ID 报成数字）；
- **行为对齐其余五个语言**：六边读同一份 `contract/vectors.json`。

## 构建与测试

```bash
cd sdks/rust
cargo fmt --check
cargo test
```

最低工具链 **1.88**（`icu` 系列依赖的 MSRV）。CI 用 `rust:1.88` 镜像；仓库未入库
`Cargo.lock`，依赖版本不锁定，如需可复现构建请显式提交 lockfile。

## 用法

```rust
use altdatahub::{HubClient, S0101BasicProfile};
use serde_json::{Map, Value};

// 真实调用：从 EDS_* 环境变量取网关公共参数
let client = HubClient::from_env()?;
let params: Map<String, Value> =
    serde_json::from_str(r#"{"entName": "贵州茅台", "page": "1"}"#)?;
let rows: Vec<S0101BasicProfile> = client.enterprise_basic("S0101", params)?;

println!("{:?}", rows[0].ent_type);
println!("{:?}", rows[0].raw); // 分册未覆盖的新字段不会丢
# Ok::<(), Box<dyn std::error::Error>>(())
```

离线跑（把上游响应喂进模型层，不发网络请求）：

```rust
use altdatahub::{HubClient, MappingTransport, S0101BasicProfile};
use std::collections::HashMap;

let mut responses = HashMap::new();
responses.insert("S0101".to_string(), serde_json::json!({"data": [{"entType": "有限责任公司"}]})
    .as_object().unwrap().clone());

let client = HubClient::new(Box::new(MappingTransport::new(responses)));
let rows: Vec<S0101BasicProfile> = client.enterprise_basic("S0101", Default::default())?;
# Ok::<(), Box<dyn std::error::Error>>(())
```

`HubClient` 提供 10 个大类方法与通用入口 `query::<T>(product_code, params)`；
泛型 `T` 由调用方标注，反序列化失败会变成 `HubError::Response` 而不是 panic。

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

统一是 `HubError` 枚举，用 `match` 或 `code()` / `category()` / `retryable()` / `hint()` 读：

| 变体 | 场景 | 处置 |
|---|---|---|
| `SpecPending` | 没配传输（`HubClient::pending()`） | 部署期问题，不要重试 |
| `Validation` | 未知 productCode、类别不匹配、业务参数以 `eds_` 开头 | 改代码，**不花钱** |
| `Transport { status, retryable }` | 网络 / HTTP 失败 | 4xx 改请求，5xx 才退避 |
| `Biz { code, category, retryable, hint }` | 网关业务错误码（1000/2000/3000/9999） | 见 `retryable` |
| `Response` | 拿到响应但不是预期结构 | 多半是上游变更，**先别重试** |

## 与 Python 版的对应关系

| Python | Rust |
|---|---|
| `client.enterprise_basic("S0101", entName="x")` | `client.enterprise_basic::<S0101BasicProfile>("S0101", params)` |
| `client.from_env()` | `HubClient::from_env()` |
| `EdsConfig(...)` 的 `org_id` | `EdsConfig.org_id`（snake_case） |
| `list[Record]` | `Vec<T>` |
| `None`（缺字段） | `Option::None` |

## 未确认项

响应信封形状、错误码字段名、部分产品的业务参数 —— 与 Python 版共享同一批未知，
详见 [`docs/api/transport.md`](../../docs/api/transport.md)。
