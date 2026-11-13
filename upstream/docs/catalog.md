# 目录（数据契约）说明

## 真源与派生关系

```
《替代数据通 产品数据分册（V1.0）》PDF  （内部资料，*.pdf 不入库）
        │  tools/extract_catalog.py     （坐标解析 + 质量校验，可重放）
        ▼
catalog/products.json                   ← 数据契约真源
catalog/names_en.json                   ← 中文名 → 英文类名的显式映射（缺映射即失败）
        │  tools/gen_code.py            （缺一即 CI 红）
        ▼
src/altdatahub/models.py                  51 个产品 + 12 个子结构的强类型模型
src/altdatahub/_data/products.json        随包分发的目录副本（与仓根必须逐字节一致）
openapi/openapi.yaml                    唯一 POST 入口 + 51 个 schema（0 errors，见 spectral）
catalog/PRODUCTS.md                     人读速查表
```

任何一环都不许手改下游产物：`tests/test_generated.py` 会重跑生成器并比对。

## 分册版本

| 项 | 值 |
|---|---|
| 名称 | 金融信用信息基础数据库替代数据通 产品数据分册 |
| 版本 | V1.0（2025-12 首次发布，中国人民银行征信中心） |
| 篇幅 | 51 页 |
| 解析产物 | 51 个 productCode / 10 个大类 / 557 个顶层字段 + 397 个子结构字段（12 个子结构）/ 2 个查询参数 |

字段数分两层统计：产品顶层 557、子结构 397（合计 954），口径与
`catalog/PRODUCTS.md` 的合计一致；2 个查询参数另计，不并入字段数。

## 解析器踩过的四个坑（改解析器前先读）

1. **水印**：每页铺满「山东省分中心收文 2025-12-17」，字号 15.0/15.4/17.9pt、字体 `STSong-Light`；
   正文 9.0/10.4pt。按字号 `< 13` 过滤。
2. **无框线表格**：`page.extract_tables()` 返回空。列边界靠表头行
   「名称/类型/长度/非空/中文名/说明」的 x 坐标推。
3. **英文名会折行**：`simpleDissolObjConten` + `t` 这种跨行碎片要合并，判据是
   「与上一锚点邻近且该行没有类型/长度/中文名内容」。
4. **一页多个产品 + 参数表在 marker 之前**：`productCode：S0206` 的冒号有时被拆成独立字符；
   `2.1.6.1 产品参数` 出现在 `productCode` 之前，必须暂存再挂到下一个产品
   （早期版本把它挂到了上一个产品，是这批解析里唯一的逻辑性错误）。

## 已确认的目录事实（容易误判，别"修"）

| 现象 | 结论 |
|---|---|
| 编码前缀不连续（无 S03、S06） | 分册如此，产品编码不属于章节号体系；`sectionId` 由章节标题决定，不从编码推 |
| `S1104 海关资质信息` 只有 4 个字段、`S1106` 只有 3 个 | 分册原文如此，不是解析漏字段（曾误报 25 个，是越界收集） |
| `S0206` 下有个叫「产品结构」的子结构 | 是分册里的**容器节点**（年报附加表的总入口），保留原名以保证可回溯 |
| 只有 S0206 / S1201 有「产品参数」 | 分册只给这两类产品定义了查询参数（年报年份 / 会计年度） |
| 所有字段的 `required` 都不阻止解析 | 「非空」是对上游返回的约束；SDK 遇到缺失字段降级为 `None` 并保留 `raw`，不整批失败 |

## 分册升版怎么办

1. 把新 PDF 放本地（不要入库）；
   首次需要 `pip install -e ".[extract]"`（pdfplumber 只在解析期用）；
   **先留一份旧目录**：`cp catalog/products.json /tmp/products-old.json`；
2. `python tools/extract_catalog.py <pdf> -o catalog/products.json --check`；
3. `python tools/verify.py diff /tmp/products-old.json` —— 删产品 / 删字段 / 改类型会标红，
   必须人工确认是「分册真的改了」；新增字段只提示不报错；
4. `python tools/gen_code.py`；
5. `python -m pytest tests/ -q`；
6. 看 `git diff catalog/products.json` 与 `git diff contract/generated.json`。
   只看产物条数变化不够：顶层字段数从 557 掉到 500 可能是新分册精简，也可能是折行合并失效；
   `generated.json` 的 `publicApi` 摘要能看出公开 API 签名是否变了。
