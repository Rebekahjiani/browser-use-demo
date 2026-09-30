# 标注核验与冻结说明

## 范围

本轮冻结的是两份核心词表答案：商品、商品分类、购物车，以及列出的字段、7类操作、1条分类列出商品关系。它们不是全站或完整 trace 的实体/属性全集。标注时已看过现有候选，存在事后选择偏差；冻结只能防止本次评分过程继续改动标准，不能消除该偏差。

## 核验与裁决

- Drive：3实体、32属性、7操作、1关系。每条事实均有原始 `drive/screenshots/.../aria.yml` 精确行及原文；部分条目同时保留 evidence package 来源。已展开所有通配符及描述性占位引用。
- browser-use 2026-09-29：3实体、19属性、7操作、1关系。使用原始 `accessibility.json` 的 JSON Pointer 与 exact quote。商品详情 Size、图片和描述正文也纳入答案，尽管现有模型未提取这些字段。
- `Short Description` 与 `Description` 分开。前者仅由高级搜索的字段名支持，`support_kind=search_form_field_only`；不声称详情页填有短描述值。
- Drive 的 Batteries 以准确的 `Batteries` 表格行头为准，排除了包含同词的比较表功能标题。
- 分类子分类和价格区间同时核验具体筛选链接。独立“价格区间”实体的 `range` 归一成 `category.price_range`，不把它本身当作 category 实体命中；其 bucket itemCount 不等于 category 总商品数。
- 结构关系要求输出显式 source/predicate/target 或已注册的关系 ID；描述文本提及商品列表不算结构关系命中。
- Drive 购物车仅有非空 header count；不纳入 cart-line、subtotal 或 cart total。输出中这些额外字段进入待裁定清单，不能凭未入 gold 自动宣称幻觉。购物车 API 查询不等于打开购物车页面。
- browser-use 购物车只有 empty_state，不能把缺省数量或金额补为零后得分。加购控件存在，所以 add_to_cart 在操作答案中，但 executed=false。
- Drive 的 executed 未全面核验，使用 null；可见按钮或错误提示均不足以证明加购成功。
- 原 handoff 称 browser-use 有属性级 evidence-index；实查该索引仅有实体/操作级页面引用。scorer 不把父实体引用继承成属性引用。

## 数据库参考

使用本机现存数据库生成模型：

`C:\Users\bulin\.crabvisor_data\sandboxes\sb_d5c9d813\workspace\appweave\eval\ground-truth\shopping.expected-cm.json`

按数据库模型中实际列出的 code 作名称映射；字段没有精确匹配时保留 null 与 derived_or_unverified 状态。没有实时查询记录值，也不使用其 ui_derivable 标记扩大评分分母。此参考文件也进入冻结清单。

## 冻结与复算

`score_context_models.py freeze` 先核验所有 gold 引用原文与定位，再记录 gold、contract、scorer、自查脚本、候选模型、补充索引、DB参考、两个原始 trace 目录全部文件和 Drive 抽取来源目录文件的大小与 SHA256。已有 freeze 文件拒绝覆盖。

`score` 必须先验证整个 manifest；哈希不一致立即停止。JSON 报告记录 manifest 自身 SHA256、冻结时间与评分时间。原始 trace 没有写入或替换操作。

`build_ground_truth.py` 与 `prepare_contract.py` 是标注阶段辅助文件，最终答案还经过精确行回链及人工修订。它们不是评分复算入口，冻结后拒绝覆盖 v1。复算仅运行 `test_scorer.py` 与 `score_context_models.py verify/score`。

## 尚未解决

- 额外断言逐项语义裁定、所有候选引用的人工支持性复核。
- Drive 完整操作执行状态与成功模型日志核验。
- 两侧提示词和素材处理不一致，独立 trace 分母不同。本轮不构成同输入 harness 对照。
- 对完整核心领域乃至全 trace 的系统性补标尚未完成；下一版需另立范围及版本，禁止修改冻结 v1 后冒充原评分。

## 首次计分后的解释补充（不改变冻结规则）

Drive 的高级搜索条件对象含 shortDescription；该对象按冻结契约排除，因此 product.short_description 的缺项表示缺少规范化归属，不表示模型完全没有看见该字段。两侧结构与粒度不同会影响分数，不能把它解释为纯粹的事实发现能力差异。

按范围内原始断言计数，Drive 引用存在率42/42、文件可定位27/42、精确定位27/42；browser-use 为10/26、10/26、0/26。browser-use 16条属性没有自身引用，不能继承实体级引用。这些比率衡量引用形式与定位，不代表事实真实性。
