# altdatahub

封装中国人民银行征信中心「**金融信用信息基础数据库替代数据通**」产品的第三方 Python SDK
（**非官方**，与征信中心无隶属关系）—— **10 个产品大类、51 个 `productCode`** 的强类型封装，
外加一份可重放的离线产品目录。

数据契约来自《替代数据通 产品数据分册（V1.0）》（中国人民银行征信中心，2025-12）；
传输契约按《接口规范》示例代码实现（POST + 8 个 `eds_*` 公共参数 + 业务参数平铺，
**无签名**，鉴权靠 `eds_account`）。响应信封与业务错误码仍待真实响应确认 —— 见「诚实口径」。

## 诚实口径

| 能力 | 状态 | 说明 |
|---|---|---|
| 产品目录（51 个 `productCode`、557 个顶层字段、12 个子结构 / 397 个字段） | ✅ 可用 | 由分册 PDF 解析生成，含中文名 / 类型 / 长度 / 非空 |
| 强类型模型（51 + 12 个 dataclass） | ✅ 可用 | 未知字段落 `raw`，前向兼容 |
| 10 个大类方法 + `productCode` 枚举 | ✅ 可用 | 类别与编码不匹配时**本地**报错 |
| 传输层（POST 到 EDS 网关） | ✅ 已实现 | 按《接口规范》示例代码逐字段对齐；**未与真实网关联调** |
| 业务错误码（1000/2000/3000/9999） | ✅ 已实现 | 按值判定，带 `category` / `retryable` / `hint`，OpenAPI 有 `x-error-codes` |
| 响应信封 | ⏳ 未确认 | 数据行位置按候选路径试；错误码字段名按「含 code 的键」找 |
| **能力服务 / MCP / Skill** | ✅ 骨架可用 | 独立部署的 HTTP 服务 + AI 接入层；**离线目录能力完全可用，在线查询仍需 `EDS_*` 凭据与一次真实响应联调**，见下节 |

仍未确认 4 项：响应信封、错误码字段名、各产品服务号、`eds_validday` 类型注释，详见
[`docs/api/transport.md`](docs/api/transport.md)。**没有签名环节** —— 示例代码里鉴权只靠
`eds_account` 授权串，本 SDK 不发明签名字段。

## 安装

本包尚未发布到 PyPI（`pip install altdatahub` 目前不可用），从仓库源码安装：

```bash
pip install .                    # 核心零第三方依赖（stdlib only）
pip install -e ".[dev]"         # 开发：pytest / ruff
pip install -e ".[extract]"     # 只有重新解析分册 PDF 时才需要（pdfplumber）
```

## 快速开始

```bash
altdatahub categories            # 10 个大类
altdatahub products --category judicial    # 某个大类下的 productCode
altdatahub schema S0101          # 某产品的字段字典（名称/类型/长度/非空/中文名）
altdatahub schema S1201 --json   # 机器可读
```

```python
from altdatahub import HubClient, MappingTransport, PRODUCT_CODES

# 离线（把上游响应喂进模型层）
client = HubClient(MappingTransport({"S0101": {"data": [{"entType": "有限责任公司"}]}}))
row = client.enterprise_basic(PRODUCT_CODES.S0101, entName="贵州茅台")[0]
row.entType      # '有限责任公司'
row.raw          # {'entType': '有限责任公司'} —— 分册未覆盖的新字段不会丢

# 真实调用：从 EDS_* 环境变量取网关参数
client = HubClient.from_env()
client.enterprise_basic(PRODUCT_CODES.S0101, entName="贵州茅台", page="1", pageSize="20", queryReason="贷前审查")
```

公共参数（缺任何一个都会在**本地**报错并列出变量名，不回显取值）：

| 环境变量 | 说明 |
|---|---|
| `EDS_BASE_URL` | 网关地址（示例里是内网 `http://<host>:9080/edsservice/api/gateway`） |
| `EDS_ACCOUNT` | 授权字串（凭据，不传或传错将无法查询） |
| `EDS_OPERATE_USER_ID` / `EDS_OPERATE_USER_NAME` | 用户编号 / 查询用户名 |
| `EDS_SCENE` | 来源系统简称（大写英文字母，全行统一） |
| `EDS_ORG_ID` / `EDS_ORG_ID_NAME` | 查询机构编号 / 机构名 |
| `EDS_VALID_DAY` | 选填，数据有效期（0=每次查最新，N=N 天内复用），默认 0 |
| `EDS_TIMEOUT` | 选填，秒，默认 30 |
| `EDS_SERVICE_CODE_PATTERN` | 选填，服务号模板，默认 `izxzx{product_code}` |

## 10 个大类 → 51 个产品

| 大类方法 | 章节 | 产品数 | 例 |
|---|---|---|---|
| `enterprise_basic` | 1 企业基本信息 | 6 | S0101 基本概况 |
| `market_supervision` | 2 市场监管 | 6 | S0206 年报信息 |
| `judicial` | 3 司法 | 4 | S0401 民事判决 |
| `intellectual_property` | 4 知识产权 | 7 | S0502 商标 |
| `stock` | 5 股票 | 7 | S0701 股票基本信息 |
| `bond` | 6 债券 | 9 | S0801 债券基本信息 |
| `administration` | 7 行政管理 | 4 | S0901 行政许可 |
| `honor` | 8 诚实守信荣誉 | 1 | S1001 荣誉信息 |
| `operation` | 9 经营 | 6 | S1101 招标 |
| `finance` | 10 财务 | 1 | S1201 财务信息（三表） |

完整清单（含每个产品的字段数与子结构）见 [`catalog/PRODUCTS.md`](catalog/PRODUCTS.md)。

## TypeScript SDK

`sdks/typescript/`，零运行时依赖（`fetch` + `node:test`）：

```bash
cd sdks/typescript && npm ci && npm test
```

```ts
import { HubClient, PRODUCT_CODES } from 'altdatahub';

const client = HubClient.fromEnv(); // 或 new HubClient(new MappingTransport({ ... })) 离线跑
const rows = await client.enterpriseBasic(PRODUCT_CODES.S0101, { entName: '贵州茅台' });
```

与 Python 版的差异只有三处：方法名 camelCase、业务参数走对象（TS 没有 `**kwargs`）、
全程 `Promise`。错误码表、重试语义、「先判错再取数据行」的链路顺序两边一致。
`src/types.ts`（51 个产品接口 + 12 个子结构）由同一个生成器产出，`gen_code.py --check` 守着。
详见 [`sdks/typescript/README.md`](sdks/typescript/README.md)。

## Java SDK

`sdks/java/`，Java 17 + `record`，唯一依赖 `jackson-databind`：

```bash
cd sdks/java && mvn verify
```

```java
import com.altdatahub.HubClient;
import com.altdatahub.Types;

import java.util.List;
import java.util.Map;

HubClient client = HubClient.fromEnv(); // 或 new HubClient(new Transport.Mapping(...)) 离线跑
List<Types.S0101BasicProfile> rows = client.enterpriseBasic(Map.of("entName", "贵州茅台"));
rows.get(0).entType();
```

`Types.java`（51 个产品 record + 12 个子结构）同样由 `tools/gen_code.py` 产出，**不许手改**。
错误码表、重试语义、链路顺序与 Python / TypeScript 版一致，三边用同一份
`contract/vectors.json` 断言。详见 [`sdks/java/README.md`](sdks/java/README.md)。

## Go SDK

`sdks/go/`，标准库零依赖（`net/http` + `encoding/json`）：

```bash
cd sdks/go && go vet ./... && go test ./...
```

```go
import altdatahub "github.com/h1s97x/altdatahub"

client, err := altdatahub.FromEnv() // 或 altdatahub.NewHubClient(altdatahub.NewMapping(...)) 离线跑
rows, err := client.EnterpriseBasic("S0101", map[string]any{"entName": "贵州茅台"})
profile := rows[0].(*altdatahub.S0101BasicProfile)
```

`types_gen.go`（51 个产品 struct + 12 个子结构）同样由 `tools/gen_code.py` 产出，**不许手改**。
详见 [`sdks/go/README.md`](sdks/go/README.md)。

## C# SDK

`sdks/csharp/`，.NET 8 零 NuGet（`System.Text.Json` + `HttpClient`）：

```bash
cd sdks/csharp && dotnet build Altdatahub.sln -c Release
dotnet run --project tests/Altdatahub.Tests -c Release
```

```csharp
using Altdatahub;

var client = HubClient.FromEnv(); // 或 new HubClient(new MappingTransport(...)) 离线跑
var rows = client.EnterpriseBasic<S0101BasicProfile>("S0101",
    new Dictionary<string, object?> { ["entName"] = "贵州茅台" });
```

`Types.cs`（51 个产品 record + 12 个子结构）同样由 `tools/gen_code.py` 产出，**不许手改**。
详见 [`sdks/csharp/README.md`](sdks/csharp/README.md)。

## Rust SDK

`sdks/rust/`，`serde_json` + `ureq`（rustls，无系统库依赖，最低工具链 1.88）：

```bash
cd sdks/rust && cargo fmt --check && cargo test
```

```rust
use altdatahub::{HubClient, S0101BasicProfile};

let client = HubClient::from_env()?;            // 或 HubClient::new(Box::new(MappingTransport::new(..))) 离线跑
let rows: Vec<S0101BasicProfile> = client.enterprise_basic("S0101", params)?;
```

`src/types.rs`（51 个产品 struct + 12 个子结构）同样由 `tools/gen_code.py` 产出，**不许手改**。
详见 [`sdks/rust/README.md`](sdks/rust/README.md)。

## C SDK

`sdks/c/`，C11 标准库 + libcurl，JSON 与模型都在仓内实现（不引第三方 JSON 库）：

```bash
# Debian/Ubuntu 系统依赖
apt-get install -y make gcc pkg-config libcurl4-openssl-dev

cd sdks/c && make test          # 编译静态库 + 自跑测试，退出码即结论
```

```c
#include "altdatahub.h"

ad_config *config = ad_config_from_env(&error);
ad_transport *transport = ad_http_transport_new(config);
ad_client *client = ad_client_new(transport);
ad_rows *rows = ad_client_query_by_code(client, "S0101", params, &error);
```

`include/altdatahub_types.h`（51 + 12 个模型）同样由 `tools/gen_code.py` 产出，**不许手改**。
`tests/test_contract_vectors.c` 与其它六种语言读同一份 `contract/vectors.json`；
CI 里还会跑 ASan/UBSan 构建。详见 [`sdks/c/README.md`](sdks/c/README.md)。

## C++ SDK

`sdks/cpp/` 是 **header-only 薄封装**，用 `extern "C"` 直接复用 C 库，不重复
51+12 个模型、不改 `tools/gen_code.py`：

```cpp
#include "altdatahub.hpp"

auto client = altdatahub::Client::from_env();
altdatahub::Rows rows = client.query("S0101", {{"entName", "贵州茅台"}});
// 失败抛 altdatahub::Error；RAII 管理 config → transport → client 的释放顺序
```

C++17 + 标准库，无需额外安装依赖；`make test` 会自动先构建 C 静态库。
报文 / 错误码 / 信封三组跨语言向量仍由 C SDK 覆盖，CI 的 `ci-cpp-sdk`
会同时跑 C 与 C++ 的测试（含 ASan/UBSan）。详见
[`sdks/cpp/README.md`](sdks/cpp/README.md)。

## 目录结构

```
catalog/
  products.json          数据契约真源（解析产物，勿手改）
  names_en.json          中文名 → 英文类名的显式映射（缺映射生成器直接失败）
  PRODUCTS.md            人读速查表（生成）
src/altdatahub/
  models.py              51 + 12 个模型（生成）
  endpoints.py           10 个大类 + productCode 枚举
  client.py              大类方法 + query，传输可注入
  transport.py           传输协议与 Mock（PendingTransport / MappingTransport）
  http_transport.py      真实传输（stdlib urllib，按示例代码 POST JSON）
  credentials.py         EDS 网关公共参数（8 个 eds_* 字段）
  wire.py                请求体组装 + 响应解包
  records.py             模型基类（payload → 强类型，保留 raw）
  catalog.py             运行时目录访问
  cli.py                 离线元数据 CLI
tools/
  extract_catalog.py     分册 PDF → products.json（坐标解析 + --check 质量门禁）
  gen_code.py            products.json → 模型 / OpenAPI / 速查表
docs/
  catalog.md             解析细节、踩过的坑、易误判事实、升版流程
  api/transport.md       传输契约待补清单
openapi/openapi.yaml     51 个逻辑接口 + 51 对请求/响应 schema（生成；真实端点见 x-gateway-path）
.spectral.yml            OpenAPI 契约校验规则（CI 跑，0 errors）
contract/vectors.json    跨语言契约向量（报文形状 / 错误码判定 / 信封解包，各语言跑同一份）
sdks/typescript/         TypeScript SDK（零运行时依赖；types.ts 由本生成器产出）
sdks/java/               Java SDK（仅 jackson-databind；Types.java 由本生成器产出）
sdks/go/                 Go SDK（标准库零依赖；types_gen.go 由本生成器产出）
sdks/csharp/             C# SDK（.NET 8 零 NuGet；Types.cs 由本生成器产出）
sdks/rust/               Rust SDK（serde_json + ureq；src/types.rs 由本生成器产出）
sdks/c/                  C SDK（C11 + libcurl；include/altdatahub_types.h 由本生成器产出）
  tests/test_contract_vectors.c   与其余六种语言读同一份 contract/vectors.json
sdks/cpp/                C++ SDK（header-only，复用 C 库；不新增生成器产物）
service/                 能力服务：通用查询 + 离线目录 + Token 注册表（纯标准库）
  Dockerfile / compose.yml / compose.internal.yml / README.md
  tests/                  零联网 unittest
mcp/                     MCP stdio + Streamable HTTP 双 transport（纯标准库）
skills/altdatahub-service/   Agent Skill：SKILL.md + 查询脚本 + 目录参考
openapi/service.yaml     调用方视角的能力级契约（与 openapi.yaml 的 51 个逻辑接口不同）
.env.example             服务端环境变量模板
```

Python SDK 在根目录（`src/`），其余语言在 `sdks/`，服务层在 `service/`。

## 服务化与 AI 接入

SDK 是库，不会自己监听端口。若要把替代数据通接给主系统或 AI 客户端，用
`service/`（与 SDK 同仓、零第三方依赖）：

```bash
cp .env.example .env                     # 填 EDS_* 与调用方 Token（.env 已 gitignore）
PYTHONPATH=src python -m service        # 或直接跑，回环 8802
docker compose -f service/compose.yml --env-file .env up -d --build   # 只绑回环
```

| 层 | 入口 | 说明 |
|---|---|---|
| 能力服务 | `service/README.md` | `GET /v1/categories`、`/v1/catalog`、`/v1/schema/{code}`（**离线可用**）；`POST /v1/query/{code}`（在线，需 `EDS_*`） |
| MCP | `mcp/README.md` | `python -m mcp`（stdio）或 `python -m mcp --http`（`POST /mcp`） |
| Agent Skill | `skills/altdatahub-service/SKILL.md` | 先查目录定 productCode，再查字段字典，最后才发在线查询 |

**在线查询仍是显式降级**：EDS 网关尚未与真实响应联调，服务端没配 `EDS_*`
时返回 `success=false` + `degrade_reason=未配置 EDS 网关公共参数`，不伪造数据。
拿到凭据与一份真实响应后，需按 `docs/api/transport.md` 把信封 / 服务号钉死。
调用方只持服务地址 + 调用方 Token，`EDS_ACCOUNT` 等 8 个公共参数只在服务端。

生产形态用 `service/compose.internal.yml`（不发布端口，只加入调用方网络）；
AI 客户端可另起 `mcp/compose.yml`。三者都由 `.ci-service` 进 CI。

## 文档站

文档站（MkDocs Material）在**独立仓库**，主仓不放站点文件、不加第三方依赖。
两仓之间只传「脱敏后的文档契约快照」：

```bash
python tools/verify.py all       # 统一门禁：生成物 / 向量 / 链接 / 脱敏 / 快照
python tools/verify.py export    # 只产快照：contract/snapshot/（含 manifest.json）
```

CI 的 `ci-contracts` 把快照打成 `docs-snapshot.tar.gz` 作为构建产物；
**当前阶段只出产物、不部署**。文档仓地址、跨仓同步（方式 A）与 Pages 上线
等事项见 [`todo.md`](todo.md)。

## 开发

```bash
python -m pytest tests/ -q --cov=altdatahub   # 覆盖率门禁 95%（CI 强制）
python -m ruff check src/ tests/ tools/
python tools/gen_code.py --check              # 生成物必须与目录一致（CI 也跑）
cd sdks/java && mvn verify                    # 改生成器后 Java 侧也要跑（67 个用例）
cd sdks/go && gofmt -l . && go test ./...     # Go 侧（79 个用例）
cd sdks/csharp && dotnet run --project tests/Altdatahub.Tests -c Release   # C# 侧（56 个用例）
cd sdks/rust && cargo fmt --check && cargo test                           # Rust 侧（36 个用例）
```

CI 在 CNB（`.cnb.yml`）：push / PR 按改动的目录分别跑 Python（ruff + pytest + 生成物一致性）、
TypeScript（`npm run build` + `node --test`）、Java（`mvn verify`）、Go（`gofmt` 门禁 + `go test`）、C#（`dotnet build` + 自跑测试）、Rust（`cargo fmt --check` + `cargo test`）；
`ci-contracts` 单独跑 `tools/verify.py all` 并把脱敏快照打成 `docs-snapshot.tar.gz`
构建产物（当前不部署，见 `todo.md`）；每周一跑 Python 3.10 / 3.12 全量。

## 数据来源与合规

- 本项目是**第三方实现**，非征信中心官方发布，与征信中心无隶属关系；产品名
  「金融信用信息基础数据库替代数据通」仅用于说明封装对象，不代表官方背书；
- 分册 PDF **不入库**（`*.pdf` 已 gitignore），入库的是解析产物 `catalog/products.json`；
- 目录只含产品结构定义，**不含任何真实企业数据**；
- 分册升版流程见 [`docs/catalog.md`](docs/catalog.md)。

## License

MIT，见 [LICENSE](LICENSE)。
