# 修订后的自动探索评测（2026-09-30）

## 结论

**在本轮 Shopping 只读核心范围，为实体抽取采集更丰富的属性材料，仍优先织语 Drive。browser-use 在购物车页面覆盖和记录完整性上更好。** 不给出全指标总冠军，也不把现有单次、不同起点/权限/预算运行解释为算法因果排名。

这次评的是原始 trace 的 UI 证据，不读取两份 Context Model 的名称，不使用阿器/Claude Code 的抽取成绩替探索器打分。原始 trace、旧标准与冻结文件均保留。

## 标准答案和打分器改了什么

| 旧问题 | 修订 |
|---|---|
| 标签出现就可能命中属性 | 表格属性必须有同一 row 内非空 cell；规格类也可由同一字段容器的选项支持；SKU、评分、图片、描述分别要求值、百分比、资源URL、内容见证 |
| Short Description 搜索框当商品属性 | 移入独立 form_field，不再计入商品属性分母 |
| Qty 输入当持久化属性 | 移入 input_control，并要求输入值 |
| 空购物车既算属性又算状态 | 删除重复属性，只保留空状态 |
| My Cart 菜单等同购物车实体 | 要求实际 cart 页面、Shopping Cart 标题和空状态；header仅作为入口，不推断cart-line |
| 分类标题+加购按钮推断关系 | 删除该关系计分，不用共现冒充结构关系 |
| 选中Price等同排序正确 | 改名price_sort_selected，同时检查URL与控件值，仅证明选择状态 |
| 只看到筛选标题/页码 | 分别要求筛选查询参数与移除筛选入口、p=2参数与第二页范围 |
| 页面分类可被脚本文本误导 | 只读HTML实际body class，不全文件搜类名 |
| 名称召回可刷分 | 本轮A完全绕开CM名称；由冻结原始AX生成指针和原文，再校验指针/原文，不接受名称列表作为证据 |

53项独立网站见证全部通过新规则后，冻结171个规则/输入/证据文件，再计算两边分数。12项对抗测试通过，复算JSON字节一致。冻结SHA256：`d243e0c68d7671d1485b85396b48df5731973f525500e4daf5c6cf221af7981e`。

## 新结果与对比表

| 维度 | 织语 Drive | browser-use | 解读 |
|---|---:|---:|---|
| 有页面证据的核心实体 | 2/3 | 3/3 | Drive未记录实际购物车页；不抹去其header入口证据 |
| 有值/选项支持的核心属性 | 29/29（100%） | 16/29（55.17%） | Drive多13项；有限词表，非网站属性全集 |
| 可见操作入口 | 7/7 | 7/7 | 不计执行成功 |
| 核心页面类型 | 4/6 | 5/6 | browser-use多购物车页 |
| 目标观察状态 | 2/6 | 1/6 | Drive筛选和第二页；browser-use空购物车 |
| 搜索表单字段 | 1/1 | 1/1 | 单列Short Description，不算商品实例值 |
| 数量输入控件 | 1/1 | 1/1 | 不算购物车条目数量 |
| AX/HTML标题一致 | 53/53 | 14/14 | 配对一致性检查，不是完整忠实度证明 |
| recorder完成分段 | 37/39 | 30/30 | Drive失败2段；BU失败0段 |
| recorder数据丢失标记 | true | false | 不推断未报丢失就绝对完整 |
| recorder墙钟区间 | 578.165秒 | 437.167秒 | 同口径stoppedAt-startedAt，含切段/等待；不是有效计算时间 |
| token、模型调用数、账单费用 | 未形成共同可核验账本 | 未形成共同可核验账本 | 未知不记零，不排费用效率名次 |

旧报告约569秒/437秒采用探索耗时口径；此表采用两边均存在的recorder起止区间，不混用为同一指标。browser-use另有exploration_s=437.078、14个agent步骤、12次工具尝试和一次LLM超时，保留在quality-cost JSON；不与Drive原生步数直接比较。

browser-use未证明的13项属性：color、style、dimensions、upc、package_dimensions、item_weight、model_number、date_first_available、batteries、discontinued_status、domestic_shipping、international_shipping、department。逐项AX指针及原文见results JSON。

## 如何理解分数变化

旧31/32与19/32不能直接与新29/29与16/29作升降比较：分母分类变了，并收紧了证据条件。Drive的100%只表示命中当前29项核心属性；它仍缺购物车页及多个目标状态，绝不表示探索全站完成。

## 仍然保留的限制

- 词表受历史trace启发，部分独立核验URL沿用历史见证。新规则消除部分误计，不能事后变成盲标。DB映射仍是参考，不冒充物理来源已经完全核实。
- 完整network语义未纳入；“未证明”只限记录的UI。无新增采集，无购物车写操作。Drive非空header不能证明cart-line；browser-use是空购物车。
- 历史搜索权限、起始购物车、提示词与输入处理、预算不同。固定评分规则能比较材料，不能消除采集条件差异。
- 新规则验证的是页面局部值或选项存在，不保证DB真实性，也不穷举每个属性在全部商品实例上的覆盖。图片资源URL不等于验证图像内容，描述非空不等于完整描述。
- AX/HTML标题相同仅为配对一致性，不验证全部动作与响应的时间因果关系；完整忠实度仍未验收。
- 本轮只重新评A。B的逐声明语义精确率和有证据召回需要单独修订，旧B名称召回不因A更新而变成准确率。

## 文件与复算

- `gold.v1.json`：新标准答案、变更记录、独立网站见证。
- `score.py`：标准准备、冻结及原始证据评分；仅Python标准库。
- `test_score.py`：12项对抗测试。
- `freeze.v1.json`：171个文件哈希，评分前校验；文件缺失/更改即拒绝。
- `results.v1.json` / `.md`：逐项支持证据与汇总，无运行时生成日期，复算稳定。
- `audit_quality_cost.py`、`quality-cost.v1.json`：配对一致性、分段及成本记录，附来源哈希；此附表不改变核心分数。

```powershell
cd C:\Users\bulin\browser-use-demo\benchmark\coverage-v3
python test_score.py
python score.py score
python audit_quality_cost.py
```

不要重跑prepare/freeze覆盖已有版本。新候选或新规则需新版本。当前路径配置仍针对本机这两次历史运行，尚未做成任意trace一键接入工具。
