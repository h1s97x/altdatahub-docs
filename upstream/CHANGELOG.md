# Changelog

本文件记录面向使用者的变更。版本号以 `pyproject.toml` 的 `version` 为准；
**0.1.0 已发布到 CNB PyPI 制品库 `h1s97x/pypi`**（未发布到 PyPI 官方），
更早的历史变更以提交记录为准。

## [Unreleased]

### 新增

- `service/console_cli.py`：纯标准库交互式联调 CLI，问答填 4 个必填业务参数，支持
  **网关探针**（直连 EDS 网关、原始响应落盘 0600、打印信封结构摘要）与**能力服务**两种模式；
  不依赖 `src/altdatahub`，宿主机只需这一个文件 + 本地 `.env`。10 项不联网回归用例。
- `.gitignore`：忽略 `service/probe/` 与根 `/probe/`，防止含真实响应的探针产物误提交。

### 变更

- P0 编排：`service/compose.yml` / `service/compose.arm64.yml` 的 `SERVICE_AUTH_TOKEN` 改为
  `${...:?}` 必填（容器内监听 `0.0.0.0`，空 Token 会让服务按设计退出码 2 并反复重启）；
  `.env.example` 与 `service/README.md` 同步澄清该约束。
- `service/README.md`：补 v1 `docker-compose`（连字符）兼容写法、门户 4 必填 + 2 选填业务参数表、
  `--env-file` 位置说明、纯 `docker run` 兜底，以及联调 CLI 用法。
- `service/probe.py` 与 `service/compose.arm64.yml`：探针示例参数从 `{}` / 单个 `entName`
  补齐为 `entName` / `idNum` / `idType` / `queryReason` 必填集（按示例代码推断，待截图核对字段名）。

### 已确认的联调证据（2026-11-13，内网 aarch64 机器）

- 真实错误响应：顶层 `code` / `msg` / `data`，业务错误走 HTTP 200；`code:"3000"`（无权限）
  被 `check_error` 正确判为 `EdsBizError` / authentication / 不重试，与错误码表和契约向量一致。
  请求侧 8 个 `eds_*` 公共参数 + 业务参数同层平铺、`eds_validday` 数字 0 被网关接受。
- 门户「服务验证」成功响应截图：`code:"0000"`（成功码，不在四个错误码内）、`msg`、
  `data` 为数组且产品数据行在内层 `data[].data`；当前 `DATA_PATHS` 五个候选均取不到，
  会把外层对象当数据行、业务字段静默降级为 `None`。**这是待修的行为缺陷，尚未改代码。**
- 上述结论只记录结构，不含凭据、账号、企业名与证件号；原始探针产物与 `.env` 留在内网机器，
  已被 `.gitignore` 忽略、不入库，也不出网。后续联调只依据截图人工转写结构，
  不要求回传原始报文。

## [0.1.0] - 2026-11-13

### 新增

**架构与契约治理（S0 / S1）**

- `docs/architecture.md`：固化已确认的最终架构（两仓职责、规划目录树、真源→派生映射、阶段顺序），
  作为后续实施的唯一基准；`AGENTS.md` 必读顺序与 `todo.md` 只链到它，不复制内容。
- `tools/verify.py`：契约/文档统一门禁（生成物一致性、目录校验、向量消费者、链接、脱敏、
  能力派生一致性、文档快照导出）；`ci-contracts` 跑 `verify.py all` 并打包 `docs-snapshot.tar.gz`。
- `catalog/schema.json` + `tools/catalog_model.py`：目录形状、类型枚举、必填键成为唯一规则，
  `extract_catalog.py` / `gen_code.py` / `tests/test_catalog.py` / `verify.py` 共用；
  子结构字段中文名可留空这一分册事实显式写进规则。
- `gen_code.py` 产出第 12 份生成物 `contract/generated.json`（11 个产物 sha256、公开 API 签名摘要、
  生成器 sha256、目录计数），生成前先校验真源；未知类型不再静默降级为 `str`。
- `verify.py catalog` / `diff OLD.json`：目录与英文名映射校验、分册升版语义 diff
  （删产品 / 删字段 / 改类型标红要求人工确认）；升版流程加入「先留旧目录 → diff → 看签名 diff」。
- `contract/vectors.json` 增加 `meta.authority` 与 `meta.consumers`（7 语言）；
  `tests/test_verify.py` 覆盖脱敏、计数、链接、目录校验与向量门禁。
- `todo.md`：文档仓、A 方案跨仓同步、部署与后续阶段的排期。

**跨语言一致性（M1）**

- 20 个 case 加稳定 `id`，`meta.declaration` 定义 consumer 标记规则；7 个语言测试声明
  `PARITY_VECTOR_VERSION` / `PARITY_COVERAGE: all`；`verify.py vectors` 升级为
  case id 唯一性 + 版本/覆盖声明 + 三分组引用的门禁。
- `contract/mock_gateway.py`（stdlib `http.server`）记录真实 HTTP 报文；
  `tests/test_wire_parity.py` 用本地 mock 校验 method/path/header/body 与黄金向量一致
  （含 UTF-8 中文不转义），无需真实 EDS 凭据。
- `tests/test_contract_vectors.py` 增加 case id 与期望值完整性的运行时校验。
- **向量 v2**：补 4 个失败路径/边界 case（码值只出现在描述文本、未知码值不算业务错误、
  `data` 为空对象时报错、多个候选同时存在时按 `DATA_PATHS` 顺序取 `data`），共 24 个 case；
  7 个 consumer 的 PARITY 标记同步升到 2。

**能力编排（M2）**

- `contract/capabilities.json` 成为能力 / 路由 / MCP tool / Skill 命令 / 降级文案的唯一真源；
  错误码仍只从 `src/altdatahub/errors.py` 读，不复制码值。
- `verify.py sync` 校验并生成 `service/capabilities.json`（含 `routes`）、`mcp/tools.json` 与
  Skill 参考的生成块；`all` 纳入只读版 `sync`。
- `service/capabilities.py` 的能力名、`GATEWAY_NOTE`、5 处 `degrade_reason` 与
  `mcp/server.py` 的 tools 定义全部改读生成物；双 transport 不变。
- **M2 收尾**：`service/server.py` 的 `do_GET` / `do_POST` 路径匹配与 `_result` 分派由生成物
  `routes` 装配；`service/tests` 新增端到端用例，证明「只改注册表 + 加一个 handler」即可让
  HTTP 路由自动可见。`tests/test_capabilities.py` 覆盖注册表结构与派生一致性。

**文档仓与 CI**

- 文档站选定 MkDocs Material + 独立仓库；CNB 文档仓 `h1s97x/whccb/altdatahub-docs` 初始化完成
  （`mkdocs.yml` / `requirements.txt` / `scripts/build_docs.py` / 手写指南 / 文档仓 `.cnb.yml`），
  首份脱敏快照 `upstream/` 已推到 `main`；本地与 CI 的 `mkdocs build --strict` 均通过，
  只出 `site/` 构建产物、未上线。
- `ci-contracts` 增加 A 方案推送阶段：`main.push` 用构建内置 `CNB_TOKEN` 把 `contract/snapshot/`
  推到文档仓 `upstream/`，PR 与非 main 分支跳过；提交加 `--no-gpg-sign`。
- M0：`ci-contracts` 第 4 阶段加 `PUBLISH_DOCS_SNAPSHOT` 冻结开关（默认跳过），
  `todo.md` 改为 M0–M5 里程碑与文档站冻结边界。

**P0 联调交付（aarch64）**

- `service/probe.py`：真实网关探针，落盘原始请求/响应（`eds_account` 与主机脱敏、文件 0600），
  并记录 SDK 当前用 `check_error` / `extract_rows` 的解释结果，供回填 `contract/vectors.json`。
- `service/compose.arm64.yml` + `service/Dockerfile`：`linux/arm64` 部署编排，同一镜像可跑
  常驻服务或探针；`.cnb.yml` 的 `build-arm64-image` 在 `cnb:arch:arm64:v8` 原生节点构建并推送
  `docker.cnb.cool/h1s97x/whccb/altdatahub/altdatahub-service:0.1.0-arm64`（镜像不含凭据）。

### 变更

- 文档仓与部署目标确认：CNB 文档仓为权威源（私有、已初始化），GitHub 文档仓
  `h1s97x/altdatahub-docs`（私有）为未来 GitHub Pages 源；部署选 **GitHub Pages**，
  用户确认**暂不上线**、A 方案**推 CNB**。冻结期第 4 阶段由开关默认跳过。
- 凭据纪律：token 只在 CNB 密钥仓库保存、CI 引用变量名；对话中出现的临时凭据
  **未使用、未入库**，仍需在 GitHub 撤销。私有仓与免费版 GitHub Pages 的可见性冲突留到 M5 决策。
- 执行顺序改为「先完成本项目、文档站冻结」（M0–M5 / DoD-1 / DoD-2），随后解除 A 方案冻结：
  `ci-contracts` 第 4 阶段移除 `PUBLISH_DOCS_SNAPSHOT` 开关，`main.push` 正常推送脱敏快照；
  GitHub Pages 上线仍待可见性决策。
- S2 收尾：`vectors.json` v2 已被 7 语言全量参数化消费，各语言自建 HTTP server 的 wire parity
  降级为可选增强（避免重复投入）；真正的缺口是**重试执行器**——SDK 目前只有 `retryable`
  标记与 hint，没有实际重试，超时/传输失败分类则已由 `tests/test_http_transport.py` 覆盖。
- **A 方案已验证**：内置 `CNB_TOKEN` 能推送到 Private 文档仓；主仓 `main.push` 产生
  `docs: sync snapshot <sha>` 提交（作者 `h1s97x <yang1297656998@outlook.com>`），
  文档仓 CI 自动跑通 `mkdocs build --strict`。

**文档站上线（M5）**

- 能力矩阵页：主仓快照纳入 `contract/capabilities.json`，文档仓 `scripts/build_docs.py`
  生成 `contract/capabilities.md`（能力 × 路由 × MCP tool × Skill 命令 × 降级口径）。
- `.github/workflows/pages.yml` 放在 **CNB 文档仓（权威源）**，由 GitHub Actions 构建发布；
  `scripts/ensure_pages.py` 幂等保证 Pages 配置，文档仓 CI 增加 `site/` 产物完整性核对。
- 新增 `guides/service.md`、`guides/ai-integration.md`，`mkdocs.yml` 设置 `site_url`。
- 站点：<https://h1s97x.github.io/altdatahub-docs/>

**文档站增强（第一批）**

- 中文搜索：发现 `theme.language: zh` 会隐式启用 `lang: [zh]`，而 Material 打包的
  `lunr.zh.min.js` 在浏览器端缺 `@node-rs/jieba`、会抛 `e.cut` 错误；改为显式 `lang: [en]`
  + CJK 标点断句，启用 `search.suggest` / `search.highlight` / `search.share` 与关键页 `search.boost`。
- `llms-full.txt` 重写：纳入 6 个手写页、快照原文与派生页，加编号目录（26 章节 / 120 KB），
  修正此前**手写页完全不在 AI 全文里**的问题；新增 `scripts/check_site.py` 校验链接、目录、
  体积、脱敏与中文索引，并接入文档仓 CI 与 GitHub Pages workflow。
- 新增 `guides/troubleshooting.md`（排障 FAQ）与 `guides/contract-governance.md`（契约治理与分册升版）。
- `mike` 暂不启用（单版本 + 与 Actions Pages 部署模式冲突），启用条件写入文档仓 README。
- 砍掉 `parity-results.json` 运行时汇总：静态 PARITY 标记 + 各语言全量参数化 + CI
  已能发现漏接，跨并行 job 传递产物收益不抵复杂度，避免又多一份需同步的生成物。

### 修正

- 统一传输契约口径：`HttpTransport` 已按《接口规范》示例代码接入、无签名；
  默认 `PendingTransport` 是刻意的离线默认值，不代表契约未接入；
  未确认项统一为 4 项（另有 2 项未验证）。
- 统一字段数统计口径：51 个产品 / 557 个顶层字段 / 12 个子结构（397 个字段）/
  2 个查询参数，与 `catalog/PRODUCTS.md` 的合计一致。
- 修正 `AGENTS.md` 中 `SpecPendingError` 的出处，并在项目边界表补全 TypeScript SDK。
- 修正 `tools/extract_catalog.py`、`.cnb.yml`、Rust README 中失效的引用与注释。
- 明确 `pip install altdatahub` 暂不可用（PyPI 官方未发布），安装方式改为
  CNB PyPI 制品库 `h1s97x/pypi` 或仓库源码；说明 `integration` 测试标记目前无用例、
  为真实网关联调预留。
- 发布链路：CNB PyPI 制品库不支持 `twine --skip-existing`，改为「仅在 `pyproject.toml`
  变更时发布」（发新版先 bump 版本号）；`project.license` 改为 SPDX 字符串，
  消除 setuptools 的弃用警告。
