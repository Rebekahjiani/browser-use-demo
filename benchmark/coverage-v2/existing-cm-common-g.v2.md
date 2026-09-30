# 现有 CM 共同核心事实召回 v2

v1 漏映射 Qty、Price 区间、独立价格区间实体及高级搜索。此版替代 v1；两个候选已见后修订映射，属于事后诊断。先冻结规则、候选和证据，再计分。

| 运行 | 维度 | 共同 G | trace T | CM 命中 G | T 与 CM 同时命中 |
|---|---|---:|---:|---:|---:|
| drive | entities | 3 | 3 | 3 | 3 |
| drive | attributes | 32 | 31 | 29 | 29 |
| drive | operations | 7 | 7 | 2 | 2 |
| drive | relations | 1 | 1 | 0 | 0 |
| browser-use-20260929 | entities | 3 | 3 | 3 | 3 |
| browser-use-20260929 | attributes | 32 | 19 | 16 | 16 |
| browser-use-20260929 | operations | 7 | 7 | 6 | 6 |
| browser-use-20260929 | relations | 1 | 1 | 0 | 0 |

属性和关系要求结构化声明；不把实体级引用当作属性级证据。关系没有结构化输出，两边均为零。
价格分面 range 可归一到 category.price_range；分面 itemCount 不等于分类商品总数。高级搜索条件不自动变成商品属性。
同一搜索操作明确写出首页搜索框与 Advanced Search 时分别命中两个控件；控件不代表执行成功。
未映射或分母外声明保留在 JSON，不自动判为错误。此报告不计算精确率，不替代逐断言证据核验，也不用于维度 B 的 harness 排名。

复算：`python test_existing_cm_v2.py`，然后 `python score_existing_cm_v2.py score`。

Manifest SHA256：`edb6115465c004dd76144d13600427be9215565d50f6017a7ee583c6814b2712`。
