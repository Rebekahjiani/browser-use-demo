# AppWeave Benchmark 执行计划 v4

更新：2026-09-30。当前入口文件；v3及冻结v1产物保留为历史记录。

2026-10-08推进入口：`PROGRESS_20261008.md`、`batch/README.md`。已新增参数化评分、92项EAV候选分类审查和图片来源映射，DB已核验子集7/7对7/7；其余UI业务细节29/29对16/29。用户确认新采集使用Flash及允许只读查询提交。原历史数字和阶段说明保留，下文未更新的状态以新推进记录和CURRENT_RESULTS为准。旧browser-use采集实际为Pro，Flash是B抽取模型；新A实验单列。

**对照命名更正**：A比较“织语 Drive采集”与“browser-use采集”；B比较“织语 trace / 阿器 + DeepSeek V4 Flash”与“同一织语 trace / Claude Code + DeepSeek V4 Flash”。B固定同一26页任务包，不使用browser-use trace，不混用A/B表头。

**当前评测脚本位置**：

- A两层评分：[C:\Users\bulin\browser-use-demo\benchmark\ground-truth-vnext\score_two_layers.py](C:/Users/bulin/browser-use-demo/benchmark/ground-truth-vnext/score_two_layers.py)。
- A原始UI证据规则：[C:\Users\bulin\browser-use-demo\benchmark\coverage-v3\score.py](C:/Users/bulin/browser-use-demo/benchmark/coverage-v3/score.py)。
- B自身引用支持：[C:\Users\bulin\browser-use-demo\benchmark\harness-comparison\score_citations_v4.py](C:/Users/bulin/browser-use-demo/benchmark/harness-comparison/score_citations_v4.py)。
- B原始声明/schema检查：[C:\Users\bulin\browser-use-demo\benchmark\harness-comparison\evaluate_original_task.py](C:/Users/bulin/browser-use-demo/benchmark/harness-comparison/evaluate_original_task.py)。
- B成本日志：[C:\Users\bulin\browser-use-demo\benchmark\harness-comparison\build_cost_ledger.py](C:/Users/bulin/browser-use-demo/benchmark/harness-comparison/build_cost_ledger.py)。

结果文件及复算命令统一见 [CURRENT_RESULTS.md](C:/Users/bulin/browser-use-demo/benchmark/CURRENT_RESULTS.md)。

统一当前结果入口：`CURRENT_RESULTS.md`。按“两层并列、不合成总分”继续，已冻结并复算A双层结果：已核验DB子集6/6对6/6，业务细节29/29对16/29。B最新自身引用支持诊断为citations-v4：30/32对22/32（不等于完整语义精确率），7项测试通过。已找到阿器对应历史run及Flash模型标识，成本原始日志整理至cost-ledger.v1.json。下文旧阶段状态保留历史，以当前入口为准。

DB核验新增进度：`ground-truth-vnext/PROGRESS_20260930.md`。已获得只读实时schema/EAV及公开商品样本，发现17项UI细节来自同一个description字段。已核验的6个独立DB字段子集两边都命中，不能将coverage-v3的29/29 vs16/29称为DB字段覆盖优势。下一版答案尚未冻结；待确定DB来源覆盖与业务细节覆盖的主次后继续。

下一阶段具体计划：`NEXT_STEPS_20260930.md`。优先补实DB/EAV到界面的来源映射，再冻结有证据评分并重评已有A/B候选；补齐质量/成本，最后整理统一复算入口。当前标准并非本轮直接从数据库导出并核验的全集。

最新A入口：`coverage-v3/README.md`。根据对抗审查修订标准和证据门槛，并完成原始trace重评：实体Drive2/3、browser-use3/3；有值/选项的核心属性29/29、16/29；页面4/6、5/6；状态2/6、1/6。搜索字段与数量控件单列，删除共现关系及重复空状态属性。53项参考事实验证后先冻结171个文件，再评分；12项测试及字节一致复算通过。旧coverage-v2数值仅作历史，不与新分母直接比较。B的名称召回与语义精确率缺口仍未修复。

审查更正：见 `ADVERSARIAL_REVIEW_20260930.md`。当前完成的是核心覆盖与历史产物诊断，完整误报率、trace忠实度及成本尚未验收。B的30/32和26/32是声明召回，不验证候选逐条语义支持，不能据此判定总体准确性胜者；下文“优先阿器”仅限核心信息完整度。冻结文件与原始分数保留。

## 1. 当前目标

首版范围为 Shopping 的商品、搜索筛选、购物车。核心问题是自动探索采到多少可还原业务语义的证据，而不只是访问多少 URL。

- A：先对现有两次探索的原始 UI 证据按同一有限核心答案评分，比较语义覆盖、页面/状态覆盖、完整性与成本，给出本轮选型结论；现有 CM 作为辅助诊断直接使用。
- B：固定同一 trace、用户任务、schema 与模型 DeepSeek-V4-Flash-0731，比较阿器和 Claude Code 的实体、属性及关系抽取质量。
- 不追加三次探索、不要求逐个访问653 pending链接的既有决定继续有效。旧两周版中的模型组合和重复次数不自动恢复。

## 2. 三个集合与评分分母

- G：本轮模块内、DB映射及界面可达性经过独立核验的网站级共同答案。
- T：某次trace实际支持的事实，必须可定位到原始证据。
- C：候选 Context Model 输出的事实；A 使用已有输出，B 使用同一输入下的新候选。

分别按实体、属性和关系计算：

| 指标 | 分子 / 分母 | 用途 |
|---|---|---|
| 探索语义覆盖 | G∩T / G | 比较采集材料包含哪些业务事实 |
| trace内提取召回 | G∩T∩C / G∩T | 区分抽取遗漏 |
| 候选与 trace 共同命中 | G∩T∩C / G | 已有 CM 的辅助诊断；不等于候选逐条引用核验 |

名称匹配不等于证据支持。没有trace支持的C断言另行裁定。未知、未验证不能自动视为不存在。

页面类型、业务状态、有效URL、随时间新增覆盖及重复/失败动作作为解释指标。DB不能直接给出页面/状态全集，不使用DB表数作页面覆盖分母。

## 3. 已完成

- 两次历史探索trace盘点：Drive约31 URL，新browser-use 5 URL。
- 两份事后核心trace-scoped答案、通用scorer和SHA256冻结；原始trace保持不变。
- 现有CM诊断：Drive 3/3实体、30/32属性、3/7操作、0/1关系；新browser-use 3/3、16/19、6/7、0/1。
- scorer八项自查通过；两次复算一致，并验证篡改哈希拒绝计分。

这些分数使用不同trace分母和不同提示词/输入处理，只用于提取诊断，不能用于探索算法排名。旧3/4、8/14 vs 4/4、12/14是另一份事后清单回溯结果，绝非正式分数。

## 4. 当前补齐顺序

1. 从DB参考模型逐项建立三个模块的候选事实清单，记录纳入、排除、待核验及理由。保留两边都没采到的候选，不将两份trace并集冒充网站全集。
2. 独立核验界面/交互可达性，给每项G记录页面、前置状态、证据标准、DB映射。网页派生事实与真实DB字段分开。
3. 统一审计原始trace，输出T及证据索引；对无法证明不存在的项记unknown。界面展示与网络响应可获得性分别记录。
4. 在G冻结后输出同分母覆盖矩阵、交集与独有项、采集遗漏/抽取遗漏清单。
5. 直接接入两份现有 CM，冻结规范化评分并输出辅助诊断；不重新调用 `/ingest`，不要求 A 重建。
6. A 已得出本轮选型结论：以业务属性证据丰富度为主，优先织语；browser-use 在空购物车和 trace 完整性方面更好。当前结果与边界见 `coverage-v3/README.md` 和 `CURRENT_RESULTS.md`；旧结论在 `archive/BENCHMARK_A_CONCLUSION_20260929.md`。
7. B 已按用户决定改为原始 26 页 entity-extract 任务：相同 TASK/schema/inputs，直接比较历史阿器输出和用户执行完成的 Claude Code 输出。81 个输入文件哈希一致；结论见 `BENCHMARK_B_CONCLUSION_20260930.md`，不再把此前独立 CLI 的 Messages 404 当作阻塞。

## 5. 限制与当前阻塞

- Drive存在分段失败/dataLoss标记；起始购物车状态未知。已标注header的3/4 items不能替代cart-line证据。
- 新browser-use为访客空购物车，无cart-line、金额、修改购物车或搜索提交的证据。搜索与写操作权限不同需保留。
- DB生成模型的ui_derivable标签尚未逐项通过前台核验，不能直接用546项作分母。
- Shopping http://127.0.0.1:7770/ 已恢复可访问，已用隔离访客浏览器完成只读核验；SSH BatchMode仍不可用，本轮DB只使用冻结参考模型。
- 已冻结55项只读核心UI契约。它是明确的有限范围，不是全站/全DB答案；完整network语义不在本轮已完成的UI覆盖结论内。统一输入构建属于 B，不阻塞 A。

## 6. 文件

- 历史计划：`archive/APPWEAVE_EVAL_PLAN_V3.md`
- 已冻结提取诊断：extraction/reports/existing-trace-scoped.v1.{json,md}
- 新的共同标准与A审计：coverage-v2/
- 原始需求参考：`archive/appweave-eval-plan-reference-20260920.md`

本文件随实际进度更新。任何新冻结使用新版本，禁止覆写extraction/freeze.v1.json及其纳入文件。

## 7. 本轮新增进度（用户已确认只读范围）

用户决定：只评只读可达状态，不加购或修改购物车。独立核验使用全新访客会话，不使用现有购物车、不下单。非空购物车、条目、金额和写后状态不进入此次分母；可见加购入口仅作控件观察。

- DB候选清单：260个字段逐项记录，原有ui_derivable标记不直接当真值；未选字段不宣称不可见。
- 独立只读核验：现场采集商品/分类/高级搜索/空购物车/搜索结果及无结果/筛选/排序/第二页等证据。部分特殊商品字段使用历史见证URL重新访问，明确非盲标。
- 冻结共同核心契约：3实体、32属性、7操作入口、1关系、6业务状态、6页面类型，共55项。每项有新核验快照JSON Pointer与原文。
- 两边均使用同一个AX适配器与匹配规则。八项自查通过（隐藏节点、URL参数、空搜索误判、Batteries混淆、排序值等）。

| 指标 | Drive | browser-use 2026-09-29 |
|---|---:|---:|
| 核心实体 | 3/3 | 3/3 |
| 核心属性 | 31/32 | 19/32 |
| 操作入口 | 7/7 | 7/7 |
| 核心关系 | 1/1 | 1/1 |
| 页面类型 | 4/6 | 5/6 |
| 业务状态 | 2/6 | 1/6 |

Drive具有分类筛选结果（home-kitchen.html?cat=34，Now Shopping by）与第二页（cell-phones-accessories.html?p=2，Items 13–24）的原始AX证据。此前“没有筛选/翻页结果”的泛化说法不再沿用；仍不直接推断完整操作链。

此表是共同有限核心契约下的UI证据覆盖，不是CM分数，也不是全站覆盖率或完整UI+API语义覆盖。Drive未见空购物车；browser-use未见部分商品详情字段。初始购物车、任务权限和采集缺口不同，不能据此作算法因果排名。

### 当前产物入口

- coverage-v2/common-readonly.v2.json：最新共同答案
- coverage-v2/common-readonly.freeze.v2.json：冻结清单
- coverage-v2/common-readonly-coverage.v2.md / .json：最新报告
- coverage-v2/db-candidate-review.json：DB候选审阅记录
- coverage-v2/site-verification/、site-verification-extra/：独立核验证据
- coverage-v2/normalized-inputs/：两份原始trace的统一AX输入候选包
- coverage-v2/test_coverage.py、score_coverage_v2.py：自查及评分入口

coverage-v2的v1数值/逐项矩阵与v2一致；v1自动报告有一句错误概括了Drive状态缺口，v2已修正文字。保留v1，v2为当前入口。extraction下此前冻结的v1不变。

共同契约冻结时间：`2026-09-29T07:02:51.851263+00:00`；计分时间：`2026-09-29T07:02:53.441053+00:00`；manifest SHA256：`773e8dc42a8b66079ef320c289dcc3ac9cdca599ef22520e302f3994f4982e83`。

## 8. Context Model 构建状态（更正）

两份 trace 和对应 Context Model 都已经分别采集/构建完成。现有 Context Model 是通过各自的 AT harness 与提示词流程生成的候选结果；本轮不需要、也不应为了评分再次把原始 trace 喂给 `/ingest`。此前尝试调用 `/ingest` 是把织语内部的确定性 ingest/build 管线误当成现有 AT 构建流程，已撤销该阻塞结论。

两套 prompt 的任务语义和证据约束基本一致，可以把现有 CM 直接接入 A 的历史诊断与覆盖矩阵。保留输入预处理和证据材料差异：Drive 实际使用逐页 `page.json + page.aria.yml + endpoints.jsonl` 和阿器目录化收卷，browser-use 使用 `page.html + accessibility.json + actions/observations/trace`，且没有同构的 endpoints 文件。不能把 CM 差异纯粹归因于探索算法，也不要求重建才允许比较原始采集覆盖。

这不阻塞当前 A：可直接计算 `G∩T/G`、`G∩T∩C/G∩T` 和 `G∩T∩C/G`，并标记为现有运行诊断。只有在需要严格控制构建输入、进行独立 harness 对照时，才需要保留两份 trace 后重新统一输入包和收卷；这一步属于可选的受控复实验，不是当前历史比较的前置条件。

本轮已经完成的共同 UI 证据覆盖仍然有效：共同只读契约 v2 已冻结，8项覆盖自查通过。现有 CM 可直接接入候选诊断；统一受控重建是后续工作，不影响共同契约或原始 trace。

现有 CM 已直接接入共同 G/T 诊断，当前结果见 `coverage-v2/existing-cm-common-g.v2.md` / `.json`。v1 因漏映射部分别名已被替代，历史文件保留。v2 属性共同命中为 Drive 29/32、browser-use 16/32；相对自身 trace 属性为 29/31、16/19。操作入口声明为 2/7、6/7，关系声明均为 0/1。分母外及未映射断言单独保留，不自动算错。事实同时出现不等于逐条引用已经语义核验。

评分规则、候选和证据已先冻结后计分：`coverage-v2/existing-cm.freeze.v2.json`；5 项映射测试通过。复算入口 `python score_existing_cm_v2.py score`。不得覆写冻结输入报告；更新必须新建版本。

## 9. 当前交付与下一步

- A 结论：`coverage-v3/README.md`。当前业务属性采集目标下优先织语，保留 browser-use 的页面覆盖及完整性优势；不合成总分、不泛化为全站或所有网站算法结论。旧结论保存在 `archive/BENCHMARK_A_CONCLUSION_20260929.md`。
- B 已完成现有产物的核心召回与格式/引用审计：阿器实体3/3、属性30/32，Claude Code实体2/3、属性26/32；原始 schema 合格页分别7/26与26/26。阿器204处 description→note 的内存修复模拟可使26页全通过，原件未修改。以信息完整度为主优先阿器，未经适配的格式可靠性则Claude Code更好。完整语义精确率尚未逐条裁定，不能宣称全指标胜出。
- 当前报告：`BENCHMARK_B_CONCLUSION_20260930.md`；可复算数据与冻结：`harness-comparison/paired-original.v1.json`、`paired-original.freeze.v1.json`。两边对应运行日志均记录 `DeepSeek-V4-Flash-0731`；这不等于供应商底层权重的独立证明。35分钟为用户口径，日志墙钟约145分钟包含暂停/重复提示/压缩，不作速度排名。
- 原始 trace、原始 CM、extraction 冻结 v1、coverage 冻结 v1/v2 均不修改。旧清单回溯数值不称正式分数。
