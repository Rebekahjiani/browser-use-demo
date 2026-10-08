# 维度 A：自动采集比较结论

历史版本：2026-09-30已按对抗审查收紧标准并重新评测。当前入口为 `coverage-v3/README.md` 与 `coverage-v3/results.v1.json`；本文件原数值保留，不作为最新成绩。

## 选型结论

**本轮 Shopping 只读核心范围，以给 Context Model 提供更丰富的实体属性证据为目标，优先采用织语 Drive。** browser-use 在空购物车页面覆盖和 trace 完整性上有优势。当前结果支持本轮工程选型；单次历史运行、起始状态及预算不一致，尚不足以证明任意网站、相同预算下织语算法都更好。

## 同一分母上的结果

分母是独立界面核验后冻结的 55 项核心契约，覆盖商品、搜索筛选、空购物车。不是全站或完整数据库全集。下表直接评价原始 UI 采集证据，不受后续实体抽取输出多少的影响。

| 指标 | 织语 Drive | browser-use 2026-09-29 | 解读 |
|---|---:|---:|---|
| 实体覆盖 | 3/3 | 3/3 | 持平 |
| 属性覆盖 | 31/32（96.88%） | 19/32（59.38%） | 织语多覆盖 12 项，领先 37.50 个百分点 |
| 可见操作入口 | 7/7 | 7/7 | 持平；不表示执行过操作 |
| 分类包含商品的 UI 证据 | 1/1 | 1/1 | 持平；不表示 CM 已输出结构化关系 |
| 核心页面类型 | 4/6 | 5/6 | browser-use 多覆盖购物车页；两边均未见搜索结果页 |
| 目标业务状态 | 2/6 | 1/6 | 织语有筛选结果和第二页；browser-use 有空购物车 |
| 可读 UI 快照 | 53 | 14 | 采样次数，不等于独立页面数 |
| 已记录唯一 URL | 31 | 5 | 保留业务查询参数；不当作全站覆盖率 |
| 历史采集耗时 | 约 569 秒 | 约 437 秒 | 织语更长；不是相同时间预算实验 |
| trace 完整性 | 存在 dataLoss / 分段失败 | dataLoss=false，tracer 30/30 | browser-use 本次记录更完整 |

不用加权总分掩盖属性、页面类型和完整性的取舍。原生 Drive 步数和 browser-use agent/tool 步数定义不同，不直接相除比较效率；缺少一致成本账单和可靠的两边覆盖时间曲线，不下 token 成本或同预算效率结论。

## 现有 Context Model 的辅助诊断

直接使用已经由 AT 生成的两份 CM，无需重新调用 `/ingest`。同一核心属性分母下，织语现有 CM 命中 29/32，browser-use 命中 16/32；相对于各自采集到的属性，为 29/31 和 16/19。这里仅表示规范化声明与原始 trace 事实同时出现，尚不是每条候选引用都通过了语义核验。

操作入口的结构化声明是 2/7 与 6/7，结构化关系均为 0/1。它说明已有输出的抽取粒度不同，不能据此改变原始采集控件覆盖均为 7/7 的结论，也不能据此选出阿器与 Claude Code 的胜者。

共同 CM 诊断 v1 遗漏别名映射，已由 v2 替代并保留历史文件。v2 在计分前冻结规则、两份候选及输入，5 项映射测试通过；映射在看过候选后修订，因此属于事后诊断。原先不同 trace 分母的冻结诊断仍保留。更早的 `3/4、8/14 vs 4/4、12/14` 仅为事后清单回溯，禁止称为正式分数。

## 结论边界

- 本轮仅只读可达状态，不加购、不改购物车、不下单。Drive header 的 3/4 items 不能证明存在 cart-line 证据；browser-use 为访客空购物车，两个起始状态不一致。
- 提示词基于同一 AT 任务，但输入处理不同：Drive 为逐页 page/ARIA/endpoints，browser-use 为 HTML/AX/actions/observations/trace。现有 CM 差异不能全部归因于采集算法。
- Drive 的数据丢失、两边任务权限及搜索提交差异仍保留。完整网络响应语义未逐项审计；“UI 未见”不等于“全部 trace 不含”。
- 部分独立核验 URL 来自历史见证，不是盲标。DB 参考字段只作候选及语义映射，未把全部 ui_derivable 标记直接当作答案。
- 只比较已有两次运行，不新增探索复跑。后续若要证明一般算法优劣，需统一起点、权限和预算，跨网站重复实验；它不作为当前交付的前置要求。

## 可复算产物

- UI 答案与逐项原始证据：`coverage-v2/common-readonly.v2.json`、`common-readonly-coverage.v2.json`。
- UI 冻结：`coverage-v2/common-readonly.freeze.v2.json`，SHA256 `773e8dc42a8b66079ef320c289dcc3ac9cdca599ef22520e302f3994f4982e83`。
- CM 诊断：`coverage-v2/existing-cm-common-g.v2.json` / `.md`。
- CM 冻结：`coverage-v2/existing-cm.freeze.v2.json`，SHA256 `edb6115465c004dd76144d13600427be9215565d50f6017a7ee583c6814b2712`。

在 `benchmark/coverage-v2` 下运行：

```powershell
python test_coverage.py
python test_existing_cm_v2.py
python score_existing_cm_v2.py score
```

CM scorer 同时校验 UI 冻结证据哈希。若需要重跑 UI scorer，请先把原报告另存，因其生成时间变化会改变已冻结 CM 输入报告的哈希；不要覆盖已冻结输入。
