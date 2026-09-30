# Handoff：冻结 trace 级 Context Model 答案并评分

更新时间：2026-09-29（Asia/Shanghai）

## 用户目标

继续 AppWeave Shopping benchmark：先为织语 trace 和最新 browser-use trace 冻结各自有 trace 证据支持的标准答案与评分器，再给两边现有 Context Model 打分。需要把数据库生成的 Context Model 用作名称/数据库字段映射参考，但不能把数据库中未被 trace 展示的字段算入标准答案。

## 当前结论

- 维度 A 已有描述性统计：织语 trace 发现约31个不同 URL；browser-use 2026-09-29 新 trace 发现5个 URL。新 browser-use trace 分段记录完整度较好（30/30、`dataLossOccurred=false`），织语 trace 有分段失败/数据丢失标记。两者目前不能据此作普遍策略排名。
- 旧表 `drive 3/4 entities, 8/14 attrs; browser-use 4/4, 12/14` 是回溯诊断，不是有效正式成绩。browser-use 分数来自 2026-09-28 的旧 trace（非空购物车）；14项清单在看过模型输出后才整理。
- 最新 browser-use Context Model 针对 2026-09-29 trace，访客空购物车；文件在 `C:\Users\bulin\appweave\outputs\02-context-model\browser-use-contextmodel\`。其 `context-model.json` 有3实体、7操作，没有结构化实体关系；属性级证据主要在 `evidence-index.json`。
- 织语 Context Model 在 `benchmark/reports/drive-context-model.json`，合并12实体、24操作；来源是 `C:\Users\bulin\appweave\logs\03-context-model\260928-145535\llm\entity-extract`。
- 两次抽取均被报告为阿器＋DeepSeek V4 Flash，但提示词/素材处理方式不同。因此本次分数是现有结果的 trace-scoped 抽取诊断，不能单独归因于采集策略或 harness。

## 当前检查过的文件

- `benchmark/reports/drive-context-model.json`
- `benchmark/eval-v1/packages/drive/INDEX.json` 与 `000`、`001`、`002`、`004` 等页面证据包
- 最新 browser-use 的 `benchmark/outputs/20260929-115141-231052/`：14 snapshots、5 URL
- 最新 browser-use Context Model 的 `entities.json`、`operations.json`、`context-model.json`、`evidence-index.json`、`quality-report.json`
- 旧评分代码 `benchmark/score_existing.py` 和旧答案 `benchmark/eval-v1/ground-truth/shopping.ui-core.v1.json`；两者不能直接用于新结果

## 已开始但尚未完成

已新增：`benchmark/extraction/ground-truth/drive-trace.v1.json`。

该文件拟定了窄范围：商品、商品分类、购物车；核心商品/分类/购物车属性；搜索、筛选、排序、分页、加购、查看购物车等操作；分类列出商品的关系。它仍须：

1. 校验 JSON 可解析。
2. 核对每项证据引用及字段是否真实出现在对应页面证据中；当前若干带 `*` 的引用是待展开的宽泛定位符。
3. 明确 scope 是否应保留这组核心实体与属性，避免把不完整答案误称为全面标准答案。

**尚未创建** browser-use trace 的 gold、ground-truth hash manifest、评分器、评分报告；没有完成任何新一轮实际评分。

## 推荐续做顺序

1. 先读 `benchmark/extraction/ground-truth/drive-trace.v1.json` 并修复/验证，给每个目标事实加准确可定位的 trace refs。记录这是基于 trace 的 post-hoc 人工标注；避免称盲标或无偏答案。
2. 新建 `benchmark/extraction/ground-truth/browser-use-20260929.v1.json`，仅纳入新 trace 可见的事实。其购物车只能标空状态，不能标购物车条目、数量、小计或总计。主要快照 URL：`00001` 首页、`00002` Grocery 分类、`00005` 商品详情、`00007` Advanced Search、`00011` 空购物车。相关报告：`benchmark/reports/browser-use-rerun-20260929.md`。
3. 设计统一 canonical 名称映射（含中英别名、snake/camel case、review_count/reviews 等）。GT 文件中记录每项实体、属性、操作、关系及精确 `evidence_refs`；数据库映射仅作为备注字段，不增加 trace-scoped 召回分母。
4. 写通用评分器读取两种输出格式：织语 `{concepts:[...]}` 与 browser-use `{entities:[...], operations:[...]}`。按各自 trace 的答案算 entity / attribute / operation / structured relation 的 precision、recall、F1；属性召回分母不能因父实体漏掉而消失。报告 evidence-ref 存在率/可定位性与 operation executed 状态；无法自动判语义支持的引用标为待人工复核。
5. 明确范围映射：织语把 `价格区间` 单列实体，而 browser-use 把 Price facet 记为分类属性；可通过标注映射统一为 category.price_range，并在报告公开该归一规则。不得悄悄把不同粒度当作完全相同。
6. Gold 完成后冻结文件 SHA256 manifest，再运行评分器，输出 JSON + Markdown 报告。结果应同时给原始计数（如实体 x/y）和 P/R/F1。
7. 报告标题注明“现有运行的 trace-scoped 诊断”；单份 trace 和不同提示词/素材处理不能证明采集策略或 harness 普遍优劣。
8. 更新 `benchmark/APPWEAVE_EVAL_PLAN_V3.md`，将评分数据、可比性限制、未解决项和下一步记录进去。

## 可直接粘贴到新对话的继续指令

请先阅读 `C:\Users\bulin\browser-use-demo\benchmark\HANDOFF_CM_TRACE_SCORING_20260929.md`，然后继续完成 handoff 中的目标：核验并冻结两份 trace-scoped ground truth，创建通用 Context Model scorer，先冻结哈希再给织语和 2026-09-29 browser-use 两个现有 Context Model 打分，生成可复算的 JSON/Markdown 报告并更新评测计划。注意旧 `3/4, 8/14 vs 4/4, 12/14` 是事后清单回溯结果；禁止称为正式分数。保留提示词/输入处理不一致、trace 覆盖不同、browser-use 空购物车、Drive 非空 cart header 但无 cart-line 证据等限制。不要覆盖原始 trace。
