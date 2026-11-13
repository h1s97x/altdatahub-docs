# altdatahub-docs

[altdatahub](https://cnb.cool/h1s97x/whccb/altdatahub-docs) 主仓的**独立文档站**，
用 MkDocs Material 构建。主仓零依赖、不放任何站点文件；本仓是唯一放站点配置的地方。

## 职责边界

| 目录 | 谁维护 | 说明 |
|---|---|---|
| `upstream/` | **主仓 CI 自动推送，勿手改** | 脱敏后的文档契约快照 + `manifest.json` |
| `docs/getting-started/`、`docs/guides/` | 手写 | 教程与指南，事实以上游快照为准 |
| `docs/contract/`、`docs/reference/`、`docs/changelog.md`、`docs/llms*.txt`、`docs/assets/` | `scripts/build_docs.py` 生成，勿手改 | 从 `upstream/` 派生 |
| `site/`、`site.tar.gz` | CI 构建产物，不入库 | 当前阶段终点 |

两仓之间只有 `主仓 contract/snapshot/ → 本仓 upstream/` 一条数据通道。

## 本地构建

```bash
python -m pip install -r requirements.txt
python scripts/build_docs.py --check
python scripts/build_docs.py
mkdocs build --strict        # 产物在 site/
```

没有 `upstream/manifest.json` 时，`build_docs.py --check` 会失败；
本地调试可先在主仓跑 `python tools/verify.py export`，把 `contract/snapshot/` 复制到 `upstream/`。

## 栏目结构

导航按三类组织，与同类数据服务文档站对齐：

| 栏目 | 内容 | 页面来源 |
|---|---|---|
| **API 文档** | 总览与鉴权、逐端点参数/curl 示例、数据契约、能力矩阵、原始文档镜像 | `docs/api/index.md` 手写；`api/endpoints.md`、`contract/`、`reference/` 由 `build_docs.py` 生成 |
| **MCP 文档** | 总览、5 个 tool 的 `inputSchema` 与 JSON-RPC 示例、部署与配置 | `docs/mcp/index.md` / `deploy.md` 手写；`mcp/tools.md` 生成 |
| **开发工具** | 安装与 CLI、Python/多语言 SDK、能力服务部署、工具链与生成器、分册升版、排障 FAQ | 全部手写 |

生成页的真源是 `upstream/contract/capabilities.json` 与脱敏快照；手写页与生成页同目录时，
`build_docs.py` 只删指定生成文件，不会误删手写页。`scripts/check_site.py` 校验三大板块关键页。

首页 `docs/index.md` 是产品级介绍落地页（Hero / 数据指标 / 三大板块卡片 / 特性网格 /
快速开始 / 诚实口径横幅），样式在 `docs/stylesheets/landing.css`：纯 CSS、无外部字体与 CDN，
兼容暗色模式与移动端。`build_docs.py` 聚合 `llms-full.txt` 时会剥掉首页的 HTML 标签，
保持 AI 全文可读；`check_site.py` 校验样式文件与首页关键结构都已发布。

**与商业数据文档站的差别（刻意保留）**：本站不提供在线调试台、试用 Token 或可公开调用的
接口 —— 在线链路尚未与真实 EDS 网关联调，做假调试界面等于编造数据。所有在线示例都明确
标注「未联调 / 缺凭据显式降级」。

## 搜索与版本化

- **搜索**：显式声明 `plugins.search.lang: [en]`，`separator` 把全角空白与 CJK 标点作为断句边界；
  Material 启用 `search.suggest` / `search.highlight` / `search.share`；关键页用 front matter
  `search.boost` 提权。`scripts/check_site.py` 校验索引含中文页面、断句配置存在、且未误用 `lang: zh`。
- **为什么不用 `lang: zh`**：`theme.language: zh` 会让 MkDocs 隐式推断成 `lang: [zh]`，而
  Material 打包的 `lunr.zh.min.js` 在浏览器分支不传 `@node-rs/jieba`，worker 调用 `e.cut()`
  会抛错。显式设 `en` 可绕开该语言包，中文内容仍完整进入索引。
- **已知限制**：中文**词典分词**需要 `prebuild_index: node` + `@node-rs/jieba`（需 Node 工具链），
  当前两侧构建只有 Python，所以是「中文标点断句 + 子串/前缀」匹配；
  需要真分词时再在文档仓 CI 与 `pages.yml` 加 `actions/setup-node` 并改为预建索引。
- **版本化 `mike` 暂未启用**：目前只有 `0.1.0` 单版本，且 `mike deploy` 默认推 `gh-pages` 分支，
  与现有 `upload-pages-artifact` + `deploy-pages` 的 Actions 部署模式冲突。出现多版本需求时：
  `requirements.txt` 加 pin 的 `mike` → `mkdocs.yml` 加 `extra.version.provider: mike` →
  把 Pages 源改为 `gh-pages` 分支并用 `mike deploy --push --update-aliases <版本> latest`
  （或保留 Actions 模式、用 `mike build` 生成版本化目录后上传）→ 同步改两侧流水线。

## 诚实口径

- 离线目录能力（产品目录、字段字典）**完全可用**；
- 在线查询**尚未与真实 EDS 网关联调**，缺凭据时服务端显式降级，**不伪造数据**；
- 本仓是**权威源**：`main.push` 由 `.github/workflows/pages.yml` 构建并发布到 GitHub Pages；
  `sync-docs-to-github` 先把本仓 force 同步到 GitHub 文档仓，再由那边的 Actions 部署。
  因此 Pages workflow 必须放在本仓，只写在 GitHub 侧会被同步覆盖。

本项目是第三方实现，非征信中心官方发布，与征信中心无隶属关系。
