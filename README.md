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

## 诚实口径

- 离线目录能力（产品目录、字段字典）**完全可用**；
- 在线查询**尚未与真实 EDS 网关联调**，缺凭据时服务端显式降级，**不伪造数据**；
- 本仓当前**只出构建产物，不部署上线**；GitHub Pages 配置留待后续决定。

本项目是第三方实现，非征信中心官方发布，与征信中心无隶属关系。
