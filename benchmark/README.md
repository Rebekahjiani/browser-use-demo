# 本地 browser-use 预评测

## 文档入口

- [文档总入口](./BENCHMARK_PLAN.md)
- [当前计划](./APPWEAVE_EVAL_PLAN_V4.md)
- [当前结果与复算](./CURRENT_RESULTS.md)
- [下一步](./NEXT_STEPS_20260930.md)
- [本周周报](./WEEKLY_REPORT_2026-09-30.md)
- [历史文档](./archive/README.md)

模型初始化、CDP 连接和登录保护最初基于提交 `fa45a5e` 的容器驱动复制，现独立维护在本目录的 `driver.py`、`login_guard.py` 和 `login_state.js`。运行时不导入或修改 `docker_inside`。使用项目现有 `.venv`、`.env`，无须部署容器。入口适配固定的 `browser-use==0.13.10`。

## 启动前

1. 等待织语探索结束，并确认录制已停止收带。本入口遇到运行中的探索或录制会拒绝启动，不会停止别人的会话。
2. 保持本地 tracer API（默认 `14567`）和 shopping SSH 转发运行。
3. 准备专门的 CDP Chrome，只保留一个标签页，打开空白页或 shopping 同源地址。CDP 默认 `9222`，可用 `--cdp-port` 指定。不要使用有其他任务的浏览器。本入口连接已有 Chrome，不负责启动或清理浏览器配置。
4. 恢复与 drive 相同的登录、购物车和网站状态。入口不自动清空 Cookie 或重置数据库。
5. 项目 `.env` 配置 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`MODEL`；也支持 `AT_SETTINGS_PATH`。设置后者时先读取该配置中的 provider，`MODEL` 可覆盖模型名。不会把密钥写入运行配置。

## 命令

在 PowerShell 中先做只读预检（不调用模型、不导航、不创建录制）：

```powershell
cd C:\Users\bulin\browser-use-demo
.\.venv\Scripts\python.exe .\benchmark\run.py --preflight
```

建议先跑 5 步短程联调。下面命令会调用 `.env` 中的模型，并将浏览器页面内容发送给该模型：

```powershell
.\.venv\Scripts\python.exe .\benchmark\run.py --max-steps 5 --max-actions 5 --max-pages 10 --max-minutes 5 --initial-state "guest; empty cart"
```

确认 trace 和 snapshots 中有相应页面证据后，恢复初始状态，再运行：

```powershell
.\.venv\Scripts\python.exe .\benchmark\run.py --url http://127.0.0.1:7770/ --max-steps 200 --max-actions 200 --max-pages 100 --max-minutes 30 --initial-state "guest; empty cart"
```

无需手动在织语点击“开始录制”。本入口通过 tracer API 开始录制，结束时只收集本次创建的 profile，保持 Chrome 开启。收带失败时，`result.json` 保留 profile ID 和错误，需到 tracer 检查该会话。Ctrl+C 尽力保存和收带；强杀进程、关机不能保证清理。

所有运行产物固定放在 `benchmark/outputs/<时间戳>/`，不会写入 appweave 的 `outputs/01-evidence`。tracer 服务必须运行在本机，才能正确解释这个本地输出路径。

## 预算口径

- `--max-steps`：agent 轮次，默认 200。与 drive 的循环预算近似对应，但两者的内部操作不同。
- `--max-actions`：非 `done` / `handoff_browser` 工具尝试次数，默认 200。包括读取/文件工具以及被登录保护拦截的尝试，不是成功的浏览器动作数。`actions.jsonl` 保存工具类型与尝试/返回事件，后续比较需按统一分类统计。
- `--max-pages`：在步骤边界观察到的同源去重 URL，默认 100。使用与 drive 相同的易变参数/锚点过滤原则；不是页面类型或业务状态数。不统计瞬时重定向的每个中间 URL。
- `--max-minutes`：录制建立后探索的总时限，默认 30 分钟；含初始导航、模型等待、登录等待和快照耗时，不含连接准备与最终收带。达到时限取消当前探索，尽力保存历史。
- 任一上限达到即停止。页面限制在步骤边界检查，单次动作新开多页可能造成少量超出。模型主动结束、连续错误等也可能更早结束；`agent_done` 不代表全站已探索完。

当前 `shopping.txt` 默认只浏览/填写，不提交表单或修改购物车，目的是先接近 drive 的 `allowSubmit=false` 配置。这只是提示词约束，并不等同于 drive 的执行层护栏；不能据此宣称权限已严格对齐。需要测试购物车变更时，另存提示词文件，通过 `--prompt-file` 指定，并在两种策略中统一实际允许的操作。不要只改一方。

## 产物

| 文件 | 内容 |
| --- | --- |
| `config.json` / `prompt.txt` | 参数、模型、版本、计数口径、初始状态说明、完整探索任务 |
| `history.json` | 每步覆盖保存及结束时保存的 browser-use 历史，包含可用的 usage 信息 |
| `actions.jsonl` | 工具尝试和返回记录，失败/中断也保留尝试 |
| `observations.jsonl` | 步骤、时间、快照路径、目标标签页及快照错误 |
| `snapshots/` | 初始页面及每步后的 HTML、完整 AXTree、视口截图、URL 元数据 |
| `trace/` | tracer 原生录制产物 |
| `tracer-profiles.json` / `tracer-stop-*.json` | 本次录制会话及收带响应 |
| `result.json` | 停止原因、轮次、工具尝试数、页面数、探索耗时及证据告警 |

中间快照是独立 CDP 读取，不启动 Chrome Tracing，避免与 tracer 抢占。页面在读取期间发生 URL 跳转时丢弃该次快照并记错误；同 URL 的动态内容不保证原子一致。按步保存快照，不用它冒充 drive 的 `statesDiscovered`。

提示词要求保持当前标签页，但不作执行层强制。若 agent 新开标签页，快照会采集同源标签页，`unattached_targets` 会标记没有 tracer 网络录制的新页，该轮必须检查后才能用于正式比较。此版本没有自动扩展 tracer 到新标签页。

## 与 drive 比较

先用短程联调核对搜索/点击/导航的动作和网络记录是否齐全，确认页面证据能够进入同一构建流程。本入口尚未替你完成这个真实模型联调，也未实现评分器或自动转换为 drive trail 格式。

对比固定的入口、初始状态、实际权限、trace preset 和预算；保留各自实际停止原因。查看实体/属性证据、页面类型、模型 token、耗时、失败动作，而非只比 URL 数。未消耗相同动作数时，不能声称是等动作预算比较。第一批作为预实验，随后冻结配置，各独立运行 3 次，并用同一构建组合与标准答案评分。

## 无模型测试

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s benchmark/tests -v
```

登录规则回归：`node benchmark/tests/test_login_state.cjs`。规则调整仅影响 benchmark。

### 2026-09-28 联调补充

- 入口先打开目标站，再启动 tracer；录制绑定 browser-use 连接后的实际标签页。
- 关闭 browser-use 从任务文本自动提取 URL 的额外导航，避免中文标点被拼进网址。
- 输出格式明确要求 AgentOutput JSON，模型格式错误仍保留在历史和结果中，不用猜测修复替代模型输出。
- `result.json` 汇总 agent 历史错误和 tracer 分段质量。`dataLossOccurred` 是 tracer 的缺口告警：分段失败或切换间隔超过 1 秒都会触发，不能直接解释为所有页面证据丢失。
- benchmark 的 `.env` 与 AT 配置独立，修改 AT 的 key 不会自动改变 benchmark。
