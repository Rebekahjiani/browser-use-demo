# Benchmark 对抗式审查与文件入口

## 审查结论

方向仍对准两个问题：A 比较织语与 browser-use 的采集，B 比较同一织语任务的阿器与 Claude Code 抽取。已形成有限核心范围的可复算历史诊断，尚未完成原计划所要求的“全不全、真不真、对不对、成本”完整评测。此前“维度完成”“优先阿器”的措辞过强：A 只支持本轮核心 UI 属性覆盖优势，B 只支持核心声明完整度优势；B 的整体准确性胜者尚未确定。

## 按严重程度排列的问题

### P1：名称召回不约束候选证据，不能用于整体质量排名

`harness-comparison/evaluate_original_task.py` 的 core_recall 调用 normalize 后按 canonical 集合求交集；audit 单独列引用错误，没有将错误引用的声明从命中集合中扣除。对抗检查：构造3个核心实体及32个标准属性，所有 source_refs 都填不存在的 E999999，复用相同 normalize/集合公式仍得3/3、32/32。这是名称召回的固有限制，不意味着真实候选全错。完整 scorer 的引用检查能够报告问题，但没有语义支持门槛。

当前30/32与26/32保留为“声明召回”，不得改称有证据准确率、语义正确率或总体质量分。下一版需要逐条页内证据裁定、支持/矛盾/未知分类，并计算有证据召回及已裁定范围的误报率，保留未知覆盖率。

### P1：原计划B的核心问题“对不对”没有完成

只完成schema、引用存在、字面锚点与少数人工语义例子；未穷举额外实体/属性、错归实体、端点错误归属等。未知额外断言不算错是合理的，但也意味着不能依据召回宣布B总体获胜者。原schema未要求实体间关系，不应事后对未输出关系扣分。

### P1：A的证据质量和成本尚未齐全

Drive有dataLoss和分段失败；browser-use未报丢失不等于全部页面/动作/响应对应关系正确。缺完整忠实度审计。两边耗时有记录，但缺统一模型调用、token、费用和可靠覆盖时间曲线。原生动作计数不同义。只能说现有两策略trace已保存并评分，不能说两份无缺失完整trace已验收。

### P2：答案与规则存在事后偏差

核心词表参考过Drive历史素材/输出，特殊字段核验部分沿用见证URL；不是独立盲标。DB reference/code映射不等于逐字段物理来源已经核实。冻结证明可复算，不能消除选词偏差。现有清单不能替代全站或完整DB可推导答案。

### P2：部分覆盖指标是代理指标

- short_description见证来自高级搜索框，只证明字段暴露，不证明商品有描述值。
- category_lists_product规则为分类标题与Add to Cart共现，不证明实例级归属关系。
- sorted_result检查Sort By选中Price，不核验商品顺序实际正确。
- 所有历史匹配主要来自AX，未命中不意味着完整network中没有。

以上规则在当前结果中有注释，但汇总表仍容易被读成更强的语义，应保留限定或下版细分。

### P2：实验条件不完全一致

A初始购物车、权限、时间预算和输入处理不一致；B的81个任务/输入文件一致，但Claude会话有重复任务和压缩，阿器对应历史模型调用尚未独立核实。Claude本地模型字段已核实Flash。用户35分钟与日志约145分钟墙钟口径不同，不能比较速度胜者。

### P2：打分器尚不是任意候选的一键评测产品

脚本包含固定本机路径与特定候选清单，词表依赖人工别名。A scorer重跑会改报告时间，进而使依赖该报告的已冻结CM输入哈希失效。paired冻结函数用is_file过滤，缺文件不会在冻结阶段直接失败（后续读候选会失败）。依赖版本未完整锁定，补充日志审计不在主冻结清单内。这些不推翻当前数字，但限制可移植性及未来新候选使用。

## 已完成与入口

所有下列路径均相对于 `C:\Users\bulin\browser-use-demo\benchmark`。

| 工作 | 脚本/标准 | 结果 |
|---|---|---|
| 共同只读核心答案与UI覆盖 | coverage-v2/common-readonly.v2.json；score_coverage_v2.py；audit_traces.py | coverage-v2/common-readonly-coverage.v2.json / .md |
| 现有CM共同分母诊断 | coverage-v2/score_existing_cm_v2.py | coverage-v2/existing-cm-common-g.v2.json / .md |
| 两份历史trace内抽取诊断 | extraction/ground-truth/*.v1.json；extraction/score_context_models.py | extraction/reports/existing-trace-scoped.v1.json / .md |
| 同输入阿器/Claude逐页比较 | harness-comparison/evaluate_original_task.py | harness-comparison/paired-original.v1.json / .md |
| 格式修复模拟与Claude日志核验 | harness-comparison/supplementary_audit.py | harness-comparison/supplementary-audit.v1.json |
| A/B结论及当前计划 | APPWEAVE_EVAL_PLAN_V4.md | BENCHMARK_A_CONCLUSION_20260929.md；BENCHMARK_B_CONCLUSION_20260930.md |

每套对应freeze清单与test脚本位于同目录。已有JSON逐项证据比汇总Markdown更细；避免使用被替代的共同CM诊断v1。旧3/4、8/14 vs4/4、12/14仅为事后清单回溯。

原始Drive trace：`C:\Users\bulin\appweave\outputs\01-evidence\26_09_28_10_40_34-min`。

原始browser-use trace：`C:\Users\bulin\browser-use-demo\benchmark\outputs\20260929-115141-231052`。

阿器逐页候选：`C:\Users\bulin\appweave\logs\03-context-model\260928-145535\llm\entity-extract\*/output/concepts.json`。

Claude逐页候选：`harness-comparison/claudecode-original-task/entity-extract/*/output/concepts.json`。

## 是否做偏

曾偏离的/已纠正的步骤：把内部/ingest当重建前置条件；拟用新AX包替代原始B任务；把只统计名称的结果表述成B整体选型。前两项已停止，B已回到用户原始TASK/schema/inputs。本审查收窄第三项结论。保留已有结果，不为掩盖问题修改冻结分数或原始trace。

后续优先补语义精确率/有证据召回、trace忠实度和成本账本；不增加新的探索算法、不恢复用户取消的重复次数、不更换原始任务、不访问购物车写操作。当前审查不自动启动重新采集。
