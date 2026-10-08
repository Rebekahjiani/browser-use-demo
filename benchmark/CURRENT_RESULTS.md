# 织语 Benchmark 当前有效结果与复算入口

更新：2026-10-08。本文件是入口；各旧报告保留历史，不将不同分母/不同证据门槛的数字串成进步曲线。

2026-10-08新受控A实验已完成6次采集和评分，共201份快照，详见 `batch/reports/controlled-v02/results.json` / `.md` 和 `quality-summary.json`。Drive业务细节23/29、21/29、20/29；browser-use Flash为15/29、18/29、16/29。业务状态分别1/6、2/6、3/6与4/6、3/6、5/6；页面类型均5/6，DB子集均7/7。6次均有录制间隔告警，其中一次Drive有失败分段；完整忠实度及新B抽取尚未完成。下文原历史A/B表是旧产物诊断，不是本轮三次重复的统计。

最新推进：[PROGRESS_20261008.md](./PROGRESS_20261008.md)。新受控采集使用Flash、允许只读查询提交，用户手动启动Chrome后已完成6次正式运行。全部92个EAV候选已分类审查，UI可达性仍未全部验收。

新B于17:17完成收卷：全部6份trace的111个去重页面状态，两种组合共222份结果，均通过schema；同一trace的两组合输入逐文件一致，原始与准备输入hash核对通过，评分JSON逐字节复算一致。1052文件冻结入口为 `batch/b-runs/controlled-v02/completed.freeze.json`。主引用诊断见同目录`citation-results.md`，事后路径兼容诊断见`path-diagnostic.md`。B包含Drive及browser-use的材料来源，逐trace成对比较；原始失败、中断和补跑结果分别保留。完整语义precision/F1及全trace忠实度尚未验收，不把格式兼容补充诊断称为预注册指标。

## 历史对照对象（下文旧结果的命名）

| 维度 | 对照一 | 对照二 | 固定项 |
|---|---|---|---|
| A：自动探索 | 织语 Drive 采集 | browser-use 采集 | 同一评分标准；沿用两次历史trace |
| B：实体抽取 | 织语 trace → 阿器 + DeepSeek V4 Flash | 同一织语 trace → Claude Code + DeepSeek V4 Flash | 同一26页任务包，81个TASK/schema/inputs文件哈希一致 |

下方历史B表格中的“织语 / 阿器”和“织语 / Claude Code”均表示上述完整组合；历史B未使用browser-use的trace。新B分别对两种采集来源做相同输入的抽取比较。JSON内部`aqi`与`claudecode`键分别对应抽取组合；A的`drive`与`browser-use`键是采集策略。

## A：探索器，两层并列

| 指标 | 织语 Drive 采集 | browser-use 采集（2026-09-29） | 能得出的结论 |
|---|---:|---:|---|
| 已核验的独立DB字段子集（映射v2） | 7/7 | 7/7 | 新增同商品image资源映射；子集持平，不是全库覆盖率 |
| 有值/选项支持的业务细节 | 29/29 | 16/29 | 本轮有限UI业务细节Drive更多 |
| 有页面证据的实体 | 2/3 | 3/3 | browser-use有实际购物车页 |
| 核心页面类型 | 4/6 | 5/6 | browser-use多购物车类型 |
| 目标观察状态 | 2/6 | 1/6 | Drive筛选/第二页，browser-use空购物车 |
| recorder完成分段 | 37/39 | 30/30 | Drive有2段失败和dataLoss |

**当前建议：需要丰富商品业务细节时优先Drive；不再将这个优势表述为独立DB字段覆盖优势。** 两层不加权合成总分，整体算法优胜尚不能从这两次不同起点/权限/预算的历史运行推出。

数据库读核验取得853个相关表列、92个EAV属性、8个公开商品样本，未读取客户/订单/购物车记录。17项UI语义证据来自同一个description字段；独立DB层去重为同一个来源键。2026-10-08新增前台元数据、渲染代码和有界公开样本，全部92个EAV候选已分类为6项已映射、18项导航/关系待审、20项存储值未见而UI默认值待审、40项排除标量范围、8项待同记录UI见证。独立DB来源含非EAV库存键共7项，仍只是已映射子集。旧6/6和59/28分类保留于冻结v1，不与新版本混用。

模型口径更正：2026-09-29 browser-use **采集** config记录 `sophnet/DeepSeek-V4-Pro-0813`；B历史**抽取**对照为Flash。新A运行选择Flash，会单列新实验版本。

### A 文件

- `batch/bundles/historical-v2/`、`batch/reports/historical-v2/results.json` / `.md`：当前7项DB子集及历史UI覆盖的参数化复算。
- `batch/score_runs.py`、`test_score_runs.py`：任意run清单接入、独立规则复制和冻结，6项测试。
- `ground-truth-vnext/db-ui-mapping.v2.json`、`review_candidates_v2.py`：当前92项候选审查与同商品图片资源映射，4项测试。
- `ground-truth-vnext/db-export.v2.json`：只读DB导出、查询、时间。
- `ground-truth-vnext/db-ui-mapping.v1.json`：字段映射、原文/记录定位、全部92项EAV候选状态。
- `ground-truth-vnext/two-layer-contract.v1.json`、`two-layer.freeze.v1.json`：两层规则和冻结。
- `ground-truth-vnext/score_two_layers.py`、`test_two_layers.py`：双层评分与4项测试。
- `ground-truth-vnext/two-layer-results.v1.json` / `.md`：当前A结果。
- `coverage-v3/gold.v1.json`、`score.py`、`test_score.py`：UI层53项有限契约、规则及12项对抗测试。
- `coverage-v3/quality-cost.v1.json`：分段、AX/HTML标题配对和recorder墙钟；不是完整动作响应忠实度。

## B：原始26页任务的候选比较

| 指标 | 织语 / 阿器 | 织语 / Claude Code |
|---|---:|---:|
| 原始核心属性声明召回 | 30/32 | 26/32 |
| 自身引用支持的核心属性召回（当前v4） | 30/32 | 22/32 |
| 已自动支持的逐页核心属性声明 | 186/202 | 149/191 |
| 尚未自动支持的逐页核心属性声明 | 16 | 42 |
| 原始schema合格页 | 7/26 | 26/26 |

自身引用支持意味着：该候选属性自己的source_refs指向本页相应字段/值，或可定位的包含该字段的容器。支持表格容器子行头、同字段容器radio选项值、商品卡名称和子分类名称。未定位不自动判为错误；缺少/伪造引用不能得分。原任务允许字段label，B沿用32项任务词表，不与A的29项有值属性混用。

v2诊断遗漏ARIA冒号后引号字符串解析；v3遗漏合法选项值/实例引用。两者保留历史，以v4为准。修正都有回归测试，规则先冻结再计分；候选已经被看过，仍是事后诊断而非盲标。

**本轮核心完整度与自身引用支持，阿器更好；原始格式合规，Claude Code更好。** 阿器204个属性description→note的机械修复模拟可使26页合格，原件未修改。引用诊断不穷举实体/操作说明中的语义错误，不能称完整精确率或整体准确性胜负。

### B 模型及成本日志

已定位阿器实际任务run，原始提示词指向同一TASK目录，89次调用记录的模型为`sophnet/DeepSeek-V4-Flash-0731`。Claude本地任务消息记录为`DeepSeek-V4-Flash-0731`。此前“阿器历史模型未核验”现已由实际run日志补足，但不是两边供应商底层权重的独立证明。

| 日志记录 | 织语 / 阿器 | 织语 / Claude Code |
|---|---:|---:|
| 任务墙钟区间 | 880.637秒（约14.7分钟） | 8704.49秒（约145.1分钟） |
| 完成模型调用/消息 | 89次完成调用 | 171个去重assistant message ID（不冒充HTTP调用数） |
| input记录 | 4,436,609 | 9,321,045 |
| output记录 | 75,951 | 201,974 |
| cache_read_input记录 | 未给独立字段 | 10,190,848 |
| 账单费用 | 未知 | 未知 |

Claude另有用户报告约35分钟。日志区间含两次明确任务提示、暂停/压缩/重试；不能把墙钟等同活跃推理时间。双方token/cache字段语义未与网关账单对齐，不将缓存字段直接相加估费，不据此给费用效率排名。input包含重复上下文，非唯一输入材料长度。

### B 文件

- `harness-comparison/score_citations_v4.py`、`test_citations_v4.py`：自身引用支持评分和7项测试。
- `harness-comparison/citations-v4.freeze.json`、`citations-v4.results.json` / `.md`：当前引用诊断。
- `harness-comparison/evaluate_original_task.py`、`paired-original.v1.json`：原始声明/schema逐页检查，保留原口径。
- `harness-comparison/build_cost_ledger.py`、`cost-ledger.v1.json`：脱敏日志来源、模型、调用与token字段。

## 复算

### 评测脚本完整路径

| 用途 | 脚本 |
|---|---|
| A：DB来源与业务细节两层评分 | [score_two_layers.py](C:/Users/bulin/browser-use-demo/benchmark/ground-truth-vnext/score_two_layers.py) |
| A：原始UI证据匹配 | [score.py](C:/Users/bulin/browser-use-demo/benchmark/coverage-v3/score.py) |
| A：采集质量与成本记录 | [audit_quality_cost.py](C:/Users/bulin/browser-use-demo/benchmark/coverage-v3/audit_quality_cost.py) |
| B：同一织语任务包的自身引用支持评分 | [score_citations_v4.py](C:/Users/bulin/browser-use-demo/benchmark/harness-comparison/score_citations_v4.py) |
| B：原始声明召回、schema及引用检查 | [evaluate_original_task.py](C:/Users/bulin/browser-use-demo/benchmark/harness-comparison/evaluate_original_task.py) |
| B：模型及成本日志整理 | [build_cost_ledger.py](C:/Users/bulin/browser-use-demo/benchmark/harness-comparison/build_cost_ledger.py) |

Python依赖版本见 `requirements-evaluation.txt`。UI和A双层评分只需标准库；B使用jsonschema；数据库导出另需paramiko，复算不需要重新导出。

```powershell
cd C:\Users\bulin\browser-use-demo\benchmark\ground-truth-vnext
python test_two_layers.py
python score_two_layers.py score

cd C:\Users\bulin\browser-use-demo\benchmark\harness-comparison
python test_citations_v4.py
python score_citations_v4.py score
```

A、B均已通过JSON字节一致复算。评分先校验冻结哈希，不修改原始trace、任务输入或候选。目录仍含本机绝对路径，尚未实现异机一键移植。

## 尚未完成的验收

1. 映射v2中18项导航/关系、20项默认值、8项同记录UI见证的进一步核验，不能宣称完整数据库分母已完成；40项标量范围排除不等于界面不可见。
2. B所有声明（含实体/操作/API来源和范围外属性）的逐条语义精确率；当前16/42条核心引用待裁定，额外声明也未自动判错。
3. 完整动作—页面—响应忠实度、丢失段影响与统一账单费用。已补齐日志能确认的指标，缺失不记零。

保留只读范围：不加购、不修改购物车、不下单。Drive非空header无cart-line证据；browser-use空购物车。旧3/4、8/14 vs4/4、12/14始终仅为事后清单回溯。
