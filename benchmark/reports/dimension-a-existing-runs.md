# 维度 A：现有两份 Shopping trace 的覆盖与证据盘点

日期：2026-09-29  
范围：只分析既有运行，不追加采集。计数来自 `drive-pilot.json`、`browser-use-pilot.json`、原始 run 元数据及 `frontier-audit.json`。

## 结论

在现有两次运行里，**织语 trace 是更适合作为后续共同抽取输入的候选**：它留下了更多不同 URL 和更多页面类型；browser-use 的优势是有购物车页面证据，且分段日志未报告失败。此结论只表示这两次 trace 的证据广度，不证明织语策略普遍更好。运行时长、实际动作和探索停止方式不同，尚未形成严格的同预算策略实验。

| 指标 | 织语 | browser-use |
|---|---:|---:|
| 运行记录的策略步数 | 157 | 25 agent steps / 21 tool attempts |
| 实际 elapsed | 569 秒 | 927 秒探索（931 秒含清理） |
| 已访问不同 URL | 31 | 5 |
| 快照数 | 53 | 26 |
| 快照 URL 数 | 31 | 5 |
| 快照中观察到的页面类型 | 6 类有效类型，另 1 个未知 URL | 5 类 |
| 分段日志 | 39 段，37 完成、2 失败；JSONL 均可解析 | 62 段，62 完成、0 失败；JSONL 均可解析 |
| 数据丢失标记 | `dataLossOccurred=true` | `dataLossOccurred=true` |

页面类型按不同 URL 汇总：

- 织语：商品详情 12、分类列表 14、首页 1、账户登录 1、高级搜索 1、联系页 1；另 1 个 `/dp/...` URL 未归类。一个 snapshot 目录 `screenshots/x` 缺少 `accessibility.json`，不纳入有效页面类型。
- browser-use：首页、分类列表、商品详情、高级搜索、购物车各 1 个不同 URL。其 26 个快照目录都有 HTML、AX 和截图文件。
- 两边共同观察到首页、分类、商品详情和高级搜索。织语独有账户登录与联系页；browser-use 独有购物车。

快照多于 URL 的部分表示同一 URL 被多次取证，不代表重复导航：织语有 22 个额外快照，browser-use 有 21 个。快照是周期记录，不能由此推算重复访问率。AX 内容指纹分别为 53 与 13 个；该指纹会受商品文本、异步内容等影响，不能解释为业务状态数量。

## frontier 与完整性

织语 checkpoint 记录 653 个 pending frontier 链接。这些只是发现但未访问的候选项，不是已核验页面全集，也不能作为覆盖率分母。其扩展方向包括商品/分类候选、分页/筛选参数，以及购物车、比较、账户等路径；这次审计没有访问这些候选页面。

织语的 39 段中有 2 段失败；browser-use 的 62 段都完成。两边段内 JSONL 都没有语法错误，但 summary 都标记 `dataLossOccurred=true`，所以“可解析”不等于事件证据完整。browser-use 的 run 还记录了 LLM 超时、输出截断、JSON 验证失败和一个搜索页正则错误；捕获器本身报告 0 个 capture error，并以 `agent_done` 结束。织语与 browser-use 的页面证据文件总体可读，只有前述一个织语目录缺失 AX 文件。

## 可支持的比较与边界

1. 这两次既有 trace 中，织语实际留下了更广的 URL/页面类型证据；browser-use 补到了购物车类型。
2. 二者都早于 30 分钟结束（约 9.5 分钟与 15.5 分钟），页数也远低于 100 URL；运行的策略步数定义并不相同。因此不能说它们消耗了同等采集预算，也不能把差异归因于策略本身。
3. 两份 trace 都没有可信全站页面/业务状态全集，当前只报告发现数，不报告百分比覆盖率。
4. 这次运行级结果适合选取后续共同输入，不足以得出跨运行的统计结论。按“覆盖较广、证据较完整”挑选，建议先冻结织语 trace；若后续任务特别需要购物车证据，可在同一 trace 中明确增加该页面范围，或另做有相同起点/动作政策的采集。

## 可复算来源

- 织语原始运行：`C:\Users\bulin\appweave\outputs\01-evidence\26_09_28_10_40_34-min`
- browser-use 原始运行：`C:\Users\bulin\browser-use-demo\benchmark\outputs\20260928-160723-422670`
- 统一统计：`archive/pilot-comparison.md`、`reports/drive-pilot.json`、`reports/browser-use-pilot.json`
- 未访问候选链接审计：`reports\frontier-audit.json`
