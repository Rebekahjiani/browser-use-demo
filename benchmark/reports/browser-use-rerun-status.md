# browser-use 重采状态

日期：2026-09-29

本次已完成，结果目录：`C:\Users\bulin\browser-use-demo\benchmark\outputs\20260929-115141-231052`。

- 按用户确认，以访客空购物车开始；探索期间没有加购、提交搜索或修改购物车。
- 使用既有 `shopping.txt` 只读探索任务，预算为200 agent steps、200 browser-use 工具尝试、100个同源 URL、30分钟。
- 实际运行约437秒，agent 自然结束；采到5个不同 URL、14份完整快照。
- Tracer 30/30 分段完成，`dataLossOccurred=false`；有1次模型调用超时，重试后完成。
- 完整结果及与已有运行的比较见 [browser-use-rerun-20260929.md](./browser-use-rerun-20260929.md)。

本次是单次补充 pilot，不足以单独判定探索策略优劣。织语旧 run 的起始购物车状态未记录，因此两边起始状态是否完全相同仍未证实。
