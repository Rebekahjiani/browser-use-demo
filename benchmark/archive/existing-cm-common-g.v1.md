# 现有 Context Model × 共同只读 G/T 诊断

现有两份 CM 可以直接用于该诊断。两套 prompt 任务语义相近，但输入预处理不同；结果不是严格控制变量的 Benchmark A 排名。

| 运行 | 维度 | G | T | T∩C | G∩T/G | G∩T∩C/G∩T | G∩T∩C/G |
|---|---|---:|---:|---:|---:|---:|---:|
| drive | entities | 3 | 3 | 3 | 100.00% | 100.00% | 100.00% |
| drive | attributes | 32 | 31 | 28 | 96.88% | 90.32% | 87.50% |
| drive | operations | 7 | 7 | 1 | 100.00% | 14.29% | 14.29% |
| drive | relations | 1 | 1 | 0 | 100.00% | 0.00% | 0.00% |
| browser-use-20260929 | entities | 3 | 3 | 3 | 100.00% | 100.00% | 100.00% |
| browser-use-20260929 | attributes | 32 | 19 | 14 | 59.38% | 73.68% | 43.75% |
| browser-use-20260929 | operations | 7 | 7 | 5 | 100.00% | 71.43% | 71.43% |
| browser-use-20260929 | relations | 1 | 1 | 0 | 100.00% | 0.00% | 0.00% |

## 解释

- G 是冻结的共同只读核心契约；T 是该 run 的原始 UI 证据覆盖；C 是现有 Context Model 归一后的命中。
- C 只在 G 内计入；额外断言列在 JSON 中，不自动判为错误。
- 由于 Drive/browser-use 的输入材料和证据预处理不同，这份报告是现有运行的 prompt-equivalent / trace-scoped 诊断。
- 两边原始 trace、购物车状态和采集完整性差异仍然保留。
