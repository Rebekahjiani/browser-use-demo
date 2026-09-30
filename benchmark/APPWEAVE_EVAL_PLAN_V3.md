# AppWeave Shopping Benchmark 执行计划 v3

更新日期：2026-09-29  
评测站点：WebArena shopping（Magento）  
当前优先任务：已完成两份既有 trace 的核心范围答案与评分契约冻结，完成现有 Context Model 的 trace-scoped 诊断；之后另行冻结维度 B 共同输入，再进入 harness＋基模对照。

本计划取代旧 v2 的过期日期安排和旧版“8实体/57属性已冻结”说法。原始计划保留作历史记录。

## 1. 评测目标

### 维度 A：自动采集策略

比较 drive 与 browser-use 在相同入口、初始状态、权限和预算下采到的页面类型、业务状态和证据质量，并记录时间与成本。

页面发现数与状态覆盖数分开统计。当前没有独立核验的全站页面/状态全集，所以报告发现数量，不声称全站覆盖率。653 个 drive frontier 项是尚未访问的候选链接，不能当作已验证的页面全集。

### 维度 B：实体提取 harness 与模型

固定一份 trace 和完全相同的输入材料，比较 harness＋基模从证据中提取实体及属性的效果、证据支持度、完成率和成本。

维度 A 盘点完成后，建议使用织语 trace 作为 B 的共同输入候选：它覆盖更多已访问 URL 和页面类型。该选择有两段失败日志且有全局数据丢失标记；冻结前必须核实缺口是否影响抽取事实，并保留该限制。browser-use 的购物车页面是额外覆盖，当前不在选定输入中。若把购物车设为 B 的必要范围，需改变共同输入并为两组提供相同证据。

本轮拟比较：

| 组 | Harness | 基模 |
|---|---|---|
| B1 | ArtifactTrace 阿器 | `sophnet/DeepSeek-V4-Flash-0731` |
| B2 | Claude Code | `sophnet/DeepSeek-V4-Flash-0731` |

本实验回答的是：**在选定的这份 trace、这套抽取任务和该模型下，哪个 harness 提取效果更好。**单份 trace 的结果不能证明某 harness 在其他网站、trace 或模型上普遍更优。

## 2. 当前进展与可用材料

### 采集 trace

| 策略 | Trace 目录 | 现有观察 |
|---|---|---|
| drive | `C:\Users\bulin\appweave\outputs\01-evidence\26_09_28_10_40_34-min` | checkpoint 记载 157 steps、31 个 visited URL；另有 653 个 pending 链接。存在 trace 分段失败及 `dataLossOccurred=true`。 |
| browser-use | `C:\Users\bulin\browser-use-demo\benchmark\outputs\20260928-160723-422670` | 25 agent steps、5 个 URL、26 个 snapshot，提前 `agent_done`；Trace 62 segments、0 failed segments，但 `dataLossOccurred=true`。 |

2026-09-29 按相同名义预算追加了一次 browser-use run：`C:\Users\bulin\browser-use-demo\benchmark\outputs\20260929-115141-231052`。该轮从访客空购物车开始，探索期间没有加购、提交搜索或修改购物车；14 agent steps、12次计数工具尝试（其中7次与页面交互相关）、5个不同 URL、14份完整快照，约437秒后以 `agent_done` 结束。Tracer 30/30 分段完成，`dataLossOccurred=false`；发生1次90秒模型调用超时，重试后完成。详细统计见 `reports/browser-use-rerun-20260929.md`。

两份旧 run 曾配置相同的 200轮/100页/30分钟上限，但轮数不是浏览器动作数，且结束原因不同。未执行每种探索策略三次重复；依据用户决定，本版不把重复采集列为当前阻塞项。

653 pending 链接审计在 `reports/frontier-audit.json`。其主要为同源 `.html` 候选，许多是商品/分类及带参数 URL，尚未逐个访问验证；不得把它们算成653种页面。

### 已生成的 Context Model

- drive 的逐页抽取输入/输出：`C:\Users\bulin\appweave\logs\03-context-model\260928-145535\llm\entity-extract`
- drive 合并结果：`benchmark/reports/drive-context-model.json`
- 旧 browser-use（2026-09-28）的 AT 合并结果：`C:\Users\bulin\artifacttrace\templates\at-template\tasks\09-21-bu-shopping\outputs\context-model.json`
- 本轮计分的 browser-use（2026-09-29）结果：`C:\Users\bulin\appweave\outputs\02-context-model\browser-use-contextmodel\context-model.json`，补充引用索引位于同目录 `evidence-index.json`（仅实体/操作级引用，非逐属性引用）。
- browser-use AT 输出还包含 `entities.json`、`operations.json`、`evidence-index.json`、`quality-report.json`。

browser-use 成功的 AT 运行记录确认模型为 `sophnet/DeepSeek-V4-Flash-0731`。drive 评测计划记录也写了阿器＋DeepSeek V4 Flash，但对应成功运行日志尚未定位，正式报告应保留此核验状态。

已有回溯诊断见 `reports/existing-cm-provisional.md`。在一份**看过两边输出后才整理的14项清单**上，drive 命中3/4实体、8/14属性，browser-use 命中4/4实体、12/14属性。这份清单有事后选择偏差，提示词和输入处理也不同；数字仅验证读取、归并、映射与召回计算流程，**不能作为策略或 harness 排名**。

## 3. 维度 A 当前结果与下一步

现有两份旧 run 的统一盘点结论见 `reports/dimension-a-existing-runs.md`。织语实际记录31个不同 URL、6类有效页面；旧 browser-use 记录5个 URL、5类页面。新 browser-use 补跑仍记录5个 URL、5类页面，其中包含空购物车；其快照与 tracer 分段完整性优于旧 browser-use trace。两边都在30分钟之前停止，实际动作口径不同；织语旧 run 有数据丢失标记，且其起始购物车状态未知；新 browser-use run 从访客空购物车开始。因此当前可描述为织语现有 trace 发现的 URL 更多，新 browser-use trace 的记录完整性更好，且单独覆盖购物车；不能据此宣布总体策略胜负。

**维度 A 的当前阶段结论：**不追加三次运行，不要求访问653个 pending 链接；已有材料足以完成描述性比较。维度 B 仍可将织语 trace 作为共同输入候选，因为它发现的 URL 和页面类型较多；但它存在数据丢失标记。新 browser-use trace 的完整性较好、页面发现数较少，并含空购物车页面。选择前应先按实际可读证据比较 trace 的抽取适用范围，再冻结 manifest 与 SHA256；若选定输入没有购物车页面，就不把购物车实体/写后状态纳入 B 的评分范围。

完成上述冻结后，再生成该 trace 的 trace-scope 标准答案，数据库仅用于核验属性映射与真实性；只收录原始 trace 支持的实体、属性、操作和关系。然后才运行维度 B。DB 全量 schema/EAV 字段不得直接成为本轮评分分母。

数据库连通性已于 2026-09-29 从 SSH 主机 `218.245.63.97:2286` 经 `sudo docker exec` 验证，目标容器为 `webarena_verified_shopping`，库为 `magentodb`，MariaDB 版本 10.6.12。只读 EAV 目录查询可用；未读取客户、订单或商品记录值。下一阶段须以选定 trace 的可见证据逐字段映射，不能把该数据库结构查询本身当成 UI 可见性证明。

## 4. 后续实验：Harness 对照（维度 B）

### 4.1 固定输入

使用维度 A 选出的织语 trace：

`C:\Users\bulin\appweave\outputs\01-evidence\26_09_28_10_40_34-min`

该 trace 包含首页、多个分类列表、商品详情、高级搜索、账户登录与联系页面。它没有购物车页面或搜索结果页的快照；因此这次提取测试不能声称评估购物车实体/写后状态或搜索结果页。

当前 trace 带有 `dataLossOccurred=true`。运行对照前先固定实际可读取文件清单、大小与 SHA256，并确认两个 harness 访问到同一份材料。丢失标记及已知缺口写入实验报告；不得只给某一组补充材料。

建议把只读素材做成冻结输入包，例如：

`benchmark/extraction/drive-20260928-frozen/`

输入清单应覆盖 `result.json`、`config.json`、`prompt.txt`、actions、observations、全部 snapshots、trace metadata/summary 及这次决定纳入的网络证据。将文件清单与 hashes 保存为 manifest。原始 trace 保持不变。

### 4.2 同一抽取任务

两组收到完全相同的用户任务、素材目录、输出 schema、时间/输出预算和完成要求。任务要求逐页提取有证据支持的业务实体及属性，带可定位的证据引用；不要提供预期实体名称、DB ground-truth、旧 Context Model 或另一组结果。

两边可保留 harness 自带系统规则与工具，但需记录版本和实际系统提示。Harness 自带能力差异是本轮被测因素；不得通过定制一侧的任务提示来补偿另一侧。

输出统一为同一个机器可校验 schema，最低包含：

- entity canonical name 与 aliases；
- attributes（字段名及证据引用）；
- 页面/素材引用；
- notes / uncertainty；
- 不要求本轮输出完整 operations、关系或 API Context Model。

实体名称及字段使用评测方单独维护的别名映射做评分。别名表和标准答案不向 harness 暴露。

### 4.3 变量控制

唯一计划内变化为 harness：阿器 vs Claude Code。

固定 DeepSeek V4 Flash 的确切模型 ID、API endpoint/provider、temperature（若接口支持）、上下文与输出 token 限额、任务文字、输入文件 hashes、JSON schema、截止时间和重试上限。记录每组成功/失败调用、token、耗时和工具调用。

开始正式计分前先各做一次**不计分的连接/格式 smoke run**，验证两边实际请求都路由到 `sophnet/DeepSeek-V4-Flash-0731`，都能读到冻结输入并写出合法 JSON。Smoke run 只用简单无关的小材料，不能让一组提前看到评测答案。

如果 Claude Code 无法通过配置确认使用同一个 DeepSeek 模型，停止 B1/B2 比较并报告阻塞；不要把 Claude 自身模型的结果标成 Claude Code＋DeepSeek。

建议每个 harness 做3次独立抽取，使用相同输入与设置，报告每次结果、中位数和范围。运行次序交错或随机化，保留失败和部分结果。若成本限制导致只能各做一次，结果标为单次探索性试验。

### 4.4 标准答案和评分

在看两组新输出之前，由评测方基于冻结 trace 标注实体/属性答案；每项记录证据文件/节点/API 来源、业务 canonical name、DB mapping（有则填写）和同义词。DB 只作映射与真实性核验，trace 没有支持的属性不列入本次召回分母。

标注过程不得以旧模型输出作为唯一依据。先逐页审阅原始证据建立候选集，再交叉核对 DB 和范围；将歧义、排除项及裁决理由写入 notes。答案和别名映射冻结并计算 SHA256 后才运行计分。

至少报告：

- entity precision / recall / F1；
- entity-attribute pair precision / recall / F1；属性召回分母包含未命中实体的全部标准属性；
- 每个断言的证据引用有效率、证据是否实际支持断言；
- schema 通过率、完成页数、遗漏与多报的逐项清单；
- token、模型调用、工具调用、运行时间及失败重试。

不能映射的额外项先人工裁定是合法扩展、名称差异还是错误，不自动判成幻觉。重复页面上重复抽到的实体在收卷后按 canonical name 与别名合并，不能重复得分。

### 4.5 Harness 对照完成条件

- 两组实际模型 ID 均有运行日志证据，确认为同一 DeepSeek V4 Flash；
- 输入目录 hashes、任务文本、schema、预算和输出校验规则一致；
- 冻结答案在两组新输出前完成；
- 所有运行（包括失败）均保留，至少提供可复算的逐项差异报告；
- 结论只适用于这份选定 trace、当前提示任务和 DeepSeek V4 Flash。

## 5. 维度 A 补充说明与限制

已完成两份旧 trace 的统一盘点脚本和 frontier 清单初审，维度 A 的描述性比较报告位于：

- `benchmark/reports/dimension-a-existing-runs.md`
- `benchmark/reports/pilot-comparison.md`
- `benchmark/reports/drive-pilot.json`
- `benchmark/reports/browser-use-pilot.json`
- `benchmark/reports/frontier-audit.json`

报告区分 snapshot、唯一 URL、AX 指纹、native visited/pending 与分段解析。AX 指纹不等同业务状态，周期 snapshot 也无法还原重复访问率。当前数据可用于试跑分析，不能给出正式页面覆盖率排名。

按用户决定，当前不执行“drive 与 browser-use 各追加三次全新采集”的步骤。653 个候选链接也不要求两边逐个访问；自主探索比较应从同一起点独立探索。

如果之后恢复维度 A 正式重复实验，再单独冻结初始状态、登录和权限、轮/动作定义、停止条件与重复运行安排。当前这次 browser-use 按用户决定未做购物车种子，使用访客空购物车，采集期间只读；织语旧 run 的购物车初始状态未知，报告中保留此限制。若产品搜索任务必须提交 GET 搜索，需先核对执行器安全策略再统一开放。当前 browser-use prompt 禁止提交搜索，因此未采搜索结果页。

## 6. Ground-truth 与旧评分器状态

沙箱 DB ground-truth `shopping.expected-cm.json` 适合作数据库结构与字段映射的来源，但其中实体/属性 UI 可见性有争议；文件的每实体计数有21处未同步，相关 notes 也有旧统计。因此不把它整体直接当作本次 trace 的标准答案。

旧计划中的“8实体/57属性已冻结”与目前 ground-truth 文件内容不一致，不能沿用。当前 ground-truth 版本列出24实体、812去重属性、546个 `ui_derivable=true`，但仍含 storefront/admin口径混杂及待人工复核项。

`eval-v1/ground-truth/shopping.ui-core.v1.json` 的3实体/8属性是联调核心，也不是正式标准答案。`reports/existing-cm-provisional.json` 的14项检查表有事后偏差，不可用于排名。

`compare-cm.ts` / `compare-cm.js` 旧版不能直接承担正式评分：历史版本的格式/别名映射及实体未命中时属性召回分母等问题须先确认修复。正式打分器需以新冻结的 trace-level 标注契约为准，并在正式结果前完成手工正例/漏项/重复/别名/伪造引用自查。

## 7. 文件与报告约定

- 本计划：`benchmark/APPWEAVE_EVAL_PLAN_V3.md`
- 当前 trace pilot：`benchmark/reports/`
- harness 冻结输入、manifest 和各次运行：`benchmark/extraction/`
- harness 评测答案、打分器和报告：`benchmark/extraction/reports/`

正式结论同时提供输入哈希、任务提示、harness/模型版本、评分标准和逐项 evidence refs，便于复算。

## 8. 2026-09-29：现有运行的 trace-scoped 诊断（已冻结并计分）

已核验并冻结两份核心范围答案、别名/范围规则和通用 scorer，再给既有 Context Model 计分。冻结不等于盲标：候选此前已存在且已被查看，答案为 post-hoc 标注。本轮不是维度 B 的同输入 harness 实验，也不是策略排名。

| 运行 | 核心实体命中 | 属性命中 | 操作命中 | 结构关系命中 |
|---|---:|---:|---:|---:|
| Drive / 织语 | 3/3 | 30/32 | 3/7 | 0/1 |
| browser-use 2026-09-29 | 3/3 | 16/19 | 6/7 | 0/1 |

属性召回分别为93.75%与84.21%；已裁定子集属性 F1 为96.77%与91.43%。Drive 另有3项 cart 属性（cart、messages、subtotal）待裁定，属性精度保守区间为90.91%–100%，不能把已裁定子集的100% precision称为全部输出正确。完整 P/R/F1、分母、去重、排除和未知项见报告。

- Drive 遗漏 category.subcategories 和 product.short_description；后者在单独“高级搜索条件”对象中有相近字段，但本次固定结构契约未将该对象重归属商品，不能解释为完全没有读到该文字。
- browser-use 遗漏 product.description、product.image、product.size，以及 add_to_cart 操作；可见加购按钮仅证明操作入口，未发生加购。
- 两侧均没有结构化 category_lists_product 关系条目；描述中提及列表不计结构关系命中。
- 价格区间实体的 range 公开归一为 category.price_range，其 itemCount 不当作分类总商品数。浏览列表/商品详情合并为一个 navigation 操作，购物车 API 会话查询不等于进入购物车页面。
- browser-use 为空购物车，仅评分 empty_state；Drive 为非空 cart header，但无本范围内 cart-line/完整购物车页证据。不得补造购物车金额或写后成功状态。
- Drive 每条 gold 引用已回链至原始 aria.yml 精确行；browser-use 使用原始 accessibility JSON Pointer。原始 trace 保持不变。
- 原 handoff 对 evidence-index 的属性级证据描述不准确：实际仅实体/操作级引用，scorer 不将其继承为属性级引用。引用存在、可定位与语义支持分开报告；语义支持仍待人工复核。
- 保留提示词/输入处理不一致、trace 覆盖不同、Drive数据丢失标记、Drive成功模型日志未定位等限制。不能据独立分母比较策略或 harness 胜负。
- 旧 `3/4, 8/14 vs 4/4, 12/14` 仍只指事后14项清单回溯诊断；其 browser-use 为2026-09-28旧 run，绝不是本轮正式分数。

### 冻结产物与复算

- 答案：`extraction/ground-truth/drive-trace.v1.json`、`extraction/ground-truth/browser-use-20260929.v1.json`
- 评分契约：`extraction/scoring-contract.v1.json`
- 通用 scorer / 自查：`extraction/score_context_models.py`、`extraction/test_scorer.py`（8项通过）
- 标注审计：`extraction/ANNOTATION_AUDIT_V1.md`
- 冻结清单：`extraction/freeze.v1.json`（15,634文件，437,010,033字节）
- 报告：`extraction/reports/existing-trace-scoped.v1.json` 和 `.md`

冻结时间：`2026-09-29T05:57:48.492695+00:00`；首次计分时间：`2026-09-29T06:02:05.056371+00:00`。manifest SHA256：`3a28aac1ccbb882adb5f23481d94184e59ac978009993a5d9bcc9e52262b9590`。

复算：在 `benchmark/extraction` 运行 `python test_scorer.py`，然后 `python score_context_models.py score`。scorer 自动验证冻结清单的全部文件，任何哈希变化即停止。JSON 含每个候选断言、原始引用、映射、遗漏、排除及执行状态。核心范围答案不是全面标准答案；DB模型仅核验名字/code映射，不扩大分母。

### 下一步

1. 人工裁定额外 cart 字段和全部候选引用的语义支持；若调整答案、映射或评分规则，新建版本并重新冻结，不覆盖 v1。
2. 若需更广范围，先逐页补标而非从现有输出补分母，单独冻结新版范围。
3. 维度 B 仍需固定共同输入包、同一任务、schema、模型路由与预算并完成 smoke run；本轮各自 trace 的哈希清单不代替同输入控制。

复算核验：第二次运行与首次 JSON 除 scored_at 外完全一致；另用临时输入验证哈希篡改会被拒绝。核验记录见 `extraction/reports/verification.v1.json`。

## 后续执行入口
2026-09-29：根据原始两周版目标重新校准A/B口径，后续进度见 APPWEAVE_EVAL_PLAN_V4.md。本文件及冻结提取诊断保留，不作为探索排名。
