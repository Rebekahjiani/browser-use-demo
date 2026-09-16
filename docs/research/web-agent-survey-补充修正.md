# 对 web-agent-survey.md 的补充与修正

核验日期：2026-09-14。以下针对部署决策与关键结论补充，不是对原报告所有数字的完整复审。

## 已确认需要修正

1. **browser-use 的 max_steps 位置**：本机实装 0.13.10 的 `Agent.run` 签名为 `run(max_steps=500, ...)`。示例应使用 `await agent.run(max_steps=50)`；`Agent(...)` 配置 `max_failures` 等。
2. **CDP 直连与 Playwright 后端混用**：本次版本的浏览器执行层通过 CDP 控制 Chrome。使用 Playwright 镜像提供浏览器依赖，不等于 browser-use 调用 Playwright Python API。现成镜像还要核对浏览器路径、依赖、版本和显示服务；只有两行 Dockerfile 不能验收有头演示。[源码](https://github.com/browser-use/browser-use/blob/main/browser_use/browser/session.py)
3. **有头模式不等于窗口自动出现在宿主桌面**：容器有头模式需要显示服务器。远程演示常用 Xvfb + VNC/noVNC；本机 macOS 则可直接弹出 Chrome。
4. **WebVoyager 并非没有步数上限**：官方 `run.py` 定义 `--max_iter`（代码默认 5），主循环检查 `while it < args.max_iter`。原报告“无步数上限”及据此得出的“browser-use 唯一有多层约束”需要改写。其他项目应逐一检查外层 runner，未核验不能写“无”。[官方 run.py](https://github.com/MinorJerry/WebVoyager/blob/main/run.py)
5. **AWorld 的公开实现边界**：VisualWebArena README 明确是 Recon-Act 的 Action Team 推理示例；论文描述 Level 3，保留人工参与。不能直接写成完整开源、自动探索并生成站点工具的无人值守流水线。示例还列出 max_steps、parsing_failure_th、repeating_action_failure_th，不能将其概括成完全没有步数/失败限制。[README](https://github.com/inclusionAI/AWorld/blob/main/examples/visualwebarena/README.md)、[论文](https://arxiv.org/html/2509.21072v1)

## 建议调整的推论

- 有限动作集合不保证有限执行；回溯也不自动保证终止。网页状态还可能随数据、输入和时间不断变化，需要明确 visited 判等、预算和停止条件。
- DOM 压缩减少输入规模，不是全局收敛保证。
- 不同模型、数据集和评测设置之间的成功率差距，不能直接归因给某一个模块，例如仅归因于任务分解或视觉。
- `WebArena SR` 列不应混放 VisualWebArena、WebVoyager 和 SeeAct 在线结果。建议分列数据集、模型、任务数、版本、结果来源；无明确来源的 browser-use 40–60% 应先标为未核验。
- “全球第一”“最完善”“唯一”“商业产品持续领先”等结论应限定日期、范围和同条件证据。Stars 应作为有日期的关注度快照，不用于证明可靠性。

## 自动探索还应补充的项目

| 项目 | 相关性 | 已核验边界 |
|---|---|---|
| [Go-Browse](https://github.com/ApGa/Go-Browse) | 全局页面图、探索任务、到达路径与恢复 | Graph 按 URL 去重，默认 FIFO；同 URL 多状态要补处理 |
| [Crawljax](https://github.com/crawljax/crawljax) | 交互状态图与候选事件探索 | 默认状态类按 stripped DOM 判等；需要业务语义提炼 |
| [Explorer](https://github.com/OSU-NLP-Group/Explorer) | 从探索生成与验证轨迹 | 适合训练数据，不直接等于全站覆盖 |

如果目标是部署任务型 webagent 演示，本次 browser-use 方案足够作为起点；如果目标是无人指定任务的站点功能探索，还要加探索队列、状态图和知识输出。

## 本次实测部署结论

browser-use 0.13.10 + Python 3.12.12 + 本机 Google Chrome + 用户已有 DeepSeek 网关，已在 macOS 有头模式完成一个真实模型演示。4 个 agent 步骤找到 Travel 分类最低价书，并读取 £23.21 与库存 3，本次网页复核一致。此结果仅是部署验收，不是 benchmark 成绩。

使用与迁移说明见 [项目 README](../../README.md)。
