# 多语言 SDK

Python SDK 在主仓 `src/altdatahub/`；其余实现在 `sdks/` 下，
均提供 **10 个大类方法 + 51 个生成模型**，并消费同一份
`contract/vectors.json` 断言（报文 / 错误码 / 信封）。

| 语言 | 运行时依赖 | 构建 / 测试 |
|---|---|---|
| TypeScript | 零运行时（`fetch` + `node:test`，Node 20+） | `npm ci && npm test` |
| Java | Java 17 + `jackson-databind` | `mvn verify` |
| Go | 标准库零依赖 | `go vet ./... && go test ./...` |
| C# | .NET 8 零 NuGet | `dotnet build` + 自跑测试 |
| Rust | `serde_json` + `ureq`（1.88+） | `cargo fmt --check && cargo test` |
| C | C11 + libcurl，仓内自研极简 JSON | `make test`（CI 另跑 ASan/UBSan） |
| C++ | C++17 header-only，`extern "C"` 复用 C 库 | `make test` |

## 差异只在这几处

- 方法名按语言习惯（Python `snake_case`、TS/Java `camelCase`、Go 首字母大写）；
- 业务参数形态（`**kwargs` / 对象 / `map[string]any`）；
- 异步模型（TS 全程 `Promise`）；
- C++ 不重写报文 / 错误码 / 信封三层，向量由 C SDK 覆盖。

错误码表、重试语义、「先判错再取数据行」的链路顺序各语言一致。

各 SDK 的完整 README 见[原始文档镜像](../reference/index.md)中的
`sdks/*/README.md`；改行为必须先改主仓 `contract/vectors.json`，否则各语言测试会同时红。
