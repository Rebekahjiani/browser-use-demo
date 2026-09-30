# browser-use Shopping 重采记录

日期：2026-09-29  
运行目录：`C:\Users\bulin\browser-use-demo\benchmark\outputs\20260929-115141-231052`

## 运行设置与结果

沿用 `shopping.txt` 的只读探索任务。上限设为 200 agent steps、200 browser-use 工具尝试、100 个归一化同源 URL、30 分钟；共用 tracer preset `min`。起始状态记录为访客空购物车，采集期间未加购、提交搜索或修改购物车。

| 指标 | 结果 |
|---|---:|
| 模型 | `sophnet/DeepSeek-V4-Pro-0813` |
| 停止原因 | `agent_done`，agent 报告成功 |
| 实际用时 | 437.1 秒探索；含清理 437.7 秒（约 7.3 分钟） |
| agent steps / 工具尝试 | 14 / 12（另有一次不计数的 `done`） |
| 页面相关工具调用 | click 4、scroll 1、navigate 1、evaluate 1，共 7 次；另有5次文件工具调用 |
| 已访问的不同 URL | 5 |
| 快照 | 14；14 份 HTML、AX、截图文件齐全 |
| 页面类型 | 首页、分类列表、商品详情、高级搜索、购物车，各1个 URL |
| 模型调用错误 | 1 次 90 秒超时，运行仍完成 |
| Tracer | 30/30 分段完成，0 失败；JSONL 无坏行；最大切换间隔 708ms；`dataLossOccurred=false` |
| 快照错误 / 未录制的新标签页 | 0 / 0 |

购物车页面证据是空购物车状态。主要探索内容包括首页商品卡、Grocery & Gourmet Food 分类页筛选/排序/分页、商品详情、Advanced Search 表单和空购物车。Agent 没有提交搜索或操作购物车。

## 和已有运行的关系

- 与旧 browser-use 运行相比，新 trace 仍发现5个 URL，但覆盖了 Grocery 分类、不同商品，并直接采集 `/checkout/cart/` 空状态。旧 trace 的购物车非空。新 trace 的 tracer 完整性更好：旧 run 有 `dataLossOccurred=true`，新 run 为 `false`。
- 与织语现有 trace 相比，织语记录31个 URL、157步、约9.5分钟；新 browser-use 记录5个 URL、14步、约7.3分钟。两者都在30分钟和100页之前自然结束，但内部 step/tool 计数不同。织语 checkpoint 没有明确记录起始购物车状态；本次 browser-use 明确是空购物车。
- 因此本次结果增加了一份证据完整的 browser-use trace，但它没有缩小页面发现数量差距，也不足以宣布策略优劣。动作数不作等价比较；两边起始状态是否相同也未能证实。织语探索器所用模型 ID 尚未从该 run 的记录中核实，本次 browser-use 模型已记录为 DeepSeek V4 Pro。

## 复核文件

- `config.json`：预算、模型、提示词和起始状态
- `result.json`：停止原因、用时、URL、错误及 trace 质量
- `actions.jsonl` / `observations.jsonl`：工具调用和快照记录
- `snapshots/`：14组逐步页面证据
- `trace/`：本次原始 tracer 记录

旧 pilot 报告保留原有 browser-use run，不覆盖；本报告单列本次新运行。
