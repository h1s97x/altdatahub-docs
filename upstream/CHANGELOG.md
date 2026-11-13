# Changelog

本文件记录面向使用者的变更。版本号以 `pyproject.toml` 的 `version` 为准；
**0.1.0 尚未发布到 PyPI**，在此之前历史变更以提交记录为准。

## [Unreleased]

### 新增

- `docs/architecture.md`：固化用户已确认的最终架构（两仓职责、规划目录树、真源→派生映射、阶段顺序），
  作为后续实施的唯一基准；`AGENTS.md` 必读顺序与 `todo.md` 只链到它，不复制内容。
- **S1 契约治理**：新增 `catalog/schema.json` + `tools/catalog_model.py`，目录形状、类型枚举、
  必填键成为唯一规则，`extract_catalog.py` / `gen_code.py` / `tests/test_catalog.py` / `verify.py` 共用；
  子结构字段中文名可留空这一分册事实显式写进规则。
- `gen_code.py` 产出第 12 份生成物 `contract/generated.json`（11 个产物 sha256、公开 API 签名摘要、
  生成器 sha256、目录计数），生成前先校验真源；未知类型不再静默降级为 `str`。
- `verify.py` 新增 `catalog` / `diff OLD.json` 子命令：目录校验、英文名映射校验与分册升版语义 diff
  （删产品 / 删字段 / 改类型标红要求人工确认）；`all` 已纳入 `catalog`。
- 分册升版流程加入「先留旧目录 → `verify.py diff` → 看 `generated.json` 签名 diff」。
- `tools/verify.py`：契约/文档统一门禁（生成物一致性、向量消费者、链接、脱敏、文档快照导出），
  新增 `ci-contracts` job 跑该门禁并把快照打包成 `docs-snapshot.tar.gz` 构建产物。
- `contract/vectors.json` 增加 `meta.authority` 与 `meta.consumers`（7 语言），
  `tests/test_verify.py` 覆盖脱敏、计数、链接与向量门禁。
- `todo.md`：文档仓、A 方案跨仓同步、部署与 S1–S3 / P0 的后续排期。
- 文档站选定 MkDocs Material + 独立仓库；主仓只产脱敏文档快照，当前阶段不部署。

### 变更

- 明确凭据纪律：GitHub 文档仓为 **Private**，token 只在 CNB 密钥仓库保存、CI 引用变量名；
  临时明文凭据须轮换后才启用 A 方案推送。私有仓与免费版 GitHub Pages 的可见性冲突待决策，
  决策前不写 `pages.yml`、不部署。

- 确认文档仓与部署目标：CNB `h1s97x/whccb/altdatahub-docs`（已创建、私有、空仓）、
  GitHub `h1s97x/altdatahub-docs`（可见性待确认），部署选 **GitHub Pages**；
  `docs/architecture.md` 与 `todo.md` 已同步。A 方案推送待 token 授权范围确认后启用。

### 修正

- 统一传输契约口径：`HttpTransport` 已按《接口规范》示例代码接入、无签名；
  默认 `PendingTransport` 是刻意的离线默认值，不代表契约未接入；
  未确认项统一为 4 项（另有 2 项未验证）。
- 统一字段数统计口径：51 个产品 / 557 个顶层字段 / 12 个子结构（397 个字段）/
  2 个查询参数，与 `catalog/PRODUCTS.md` 的合计一致。
- 修正 `AGENTS.md` 中 `SpecPendingError` 的出处，并在项目边界表补全 TypeScript SDK。
- 修正 `tools/extract_catalog.py`、`.cnb.yml`、Rust README 中失效的引用与注释。
- 明确 `pip install altdatahub` 暂不可用，安装方式改为从仓库源码；
  说明 `integration` 测试标记目前无用例、为真实网关联调预留。
