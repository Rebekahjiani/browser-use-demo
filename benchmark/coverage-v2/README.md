# Coverage v2 当前入口

本目录实现 v4 计划的 Benchmark A 历史审计口径。用户已确认本轮只评全新访客的只读状态，不加购、不修改购物车、不下单。

## 当前冻结范围

`common-readonly.v2.json` 是 55 项有限核心契约：3 个实体、32 个属性、7 个操作入口、1 个关系、6 个业务状态和 6 个页面类型。它由独立访客会话的页面/AX 证据核验，但不是全站或完整数据库答案。

## 评分含义

- `G∩T/G`：共同契约中，某历史 trace 实际有 UI 证据的比例。
- `G∩T∩C/G∩T`：已有证据被统一构建流程提取的比例；当前尚未产生受控结果。
- `G∩T∩C/G`：端到端有证据还原率；当前尚未产生受控结果。

当前 `common-readonly-coverage.v2.*` 只报告第一项，且按实体、属性、操作入口、关系、页面类型、业务状态分开，不合成总分。

现有 CM 的三层诊断见 `existing-cm-common-g.v1.{json,md}`，运行 `python score_existing_cm.py` 复算。

## 复算

```powershell
python test_coverage.py
python score_coverage_v2.py score
```

评分器先校验 `common-readonly.freeze.v2.json` 的全部输入哈希。原始 trace 只读。`prepare_*.py` 是标注辅助脚本，不是复算入口。

## 未完成项

两份现有 Context Model 已经通过各自的 AT harness 与 prompt family 构建完成，可以直接作为当前 A 的历史诊断输入。两套 prompt 的任务语义和证据约束基本一致，但实际输入结构不同：Drive 使用逐页 `page.json + page.aria.yml + endpoints.jsonl`，browser-use 使用 `page.html + accessibility.json + actions/observations/trace`，且没有同构 endpoints 文件。因此报告应称为 prompt-equivalent / trace-scoped 诊断，不能把差异纯粹归因于探索算法。

当前可以直接计算 `G∩T∩C/G∩T` 和 `G∩T∩C/G`；统一重建不是历史比较的前置条件。只有严格 harness 对照时，才需要另行建立统一输入包。此前调用 `context-model /ingest` 不是本任务所需步骤，不作为阻塞依据。任何统一重建结果都新建版本，不修改冻结 v2。
