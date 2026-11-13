# 工具链与生成器

「开发工具」栏目汇总本地可用的命令行入口。所有命令都在**主仓**执行；文档仓只消费
`upstream/` 快照，不重新解析分册。

## CLI

```bash
altdatahub categories                     # 10 个大类
altdatahub products --category judicial   # 某个大类下的 productCode
altdatahub schema S0101                   # 单产品字段字典（名称/类型/长度/非空/中文名）
altdatahub schema S1201 --json            # 机器可读
```

离线目录能力不需要任何凭据。安装方式见 [安装与 CLI](../getting-started/install.md)。

## 7 语言 SDK

| 语言 | 测试命令 | 说明 |
|---|---|---|
| Python | `pytest tests/ -q` | 核心 SDK + 门禁自检 |
| TypeScript | `cd sdks/typescript && npm ci && npm test` | 向量全量参数化 |
| Java | `cd sdks/java && mvn test` | JDK 17+ |
| Go | `cd sdks/go && go test ./...` | |
| C# | `cd sdks/csharp && dotnet run --project tests/Altdatahub.Tests -c Release` | .NET 8 |
| Rust | `cd sdks/rust && cargo test` | |
| C / C++ | `cd sdks/c && make test`、`cd ../cpp && make test` | 需 libcurl 开发头 |

C++ 复用 C 的静态库与向量，不单独建向量。各语言测试读同一份
`contract/vectors.json`，新增 case 需升 `version` 并同步 7 个 PARITY 标记。

## 统一门禁

```bash
python tools/verify.py all                 # 生成物 / 目录 / 向量 / 能力派生 / 链接 / 脱敏 / 快照
python tools/verify.py catalog             # schema.json 校验目录与英文名映射
python tools/verify.py diff OLD.json       # 分册升版语义 diff
python tools/verify.py sync --write        # 由能力注册表重生成派生文件
python tools/verify.py vectors             # case id 与跨语言 PARITY 门禁
python tools/verify.py export              # 导出脱敏文档快照（本站数据源）
python tools/gen_code.py                   # 由 products.json 生成 11+1 份产物
python tools/gen_code.py --check           # 校验生成物未漂移
```

`contract/generated.json` 记录 11 个产物 sha256、公开 API 签名摘要、生成器 sha256
与目录计数，用来区分「只改了生成器」和「真源变了」。详见
[契约治理与分册升版](contract-governance.md)。

## 容器与联调镜像

| 产物 | 用途 |
|---|---|
| `docker.cnb.cool/h1s97x/whccb/altdatahub/altdatahub-service:0.1.0-arm64` | `linux/arm64` 能力服务镜像，不含凭据 |
| 离线 zip 包 | 内含镜像 tar + `compose.yml` + `.env` 模板 + 一键脚本，离线 `docker load` 即用 |
| `service/probe.py` | 采集真实网关原始请求/响应，凭据与主机脱敏，产物 0600 |
| `contract/mock_gateway.py` | 本地 stdlib HTTP mock，用于 wire parity 测试，无需凭据 |

部署与探针用法见 [能力服务部署](service.md)；P0 联调需要的样例说明也在那页。

## Token 与凭据

```bash
python service/issue_token.py --caller backend --scopes '*' --quiet
```

Token 注册表 `service/tokens.json` 只存哈希、不入库。`EDS_*` 只放能力服务端环境变量；
**任何 token 不写入仓库、CI 脚本、命令或对话**，只在 CNB 密钥仓库维护、CI 用 `imports`
引用变量名。

## 大数据纪律

`catalog` 只给产品摘要，`schema <code>` 按需查单产品；不要把 557 个顶层字段 +
397 个子结构字段一次倒进对话。大结果落盘后只报路径与字符数。
