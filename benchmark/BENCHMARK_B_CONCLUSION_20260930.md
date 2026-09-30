# 维度 B：同一织语素材，阿器与 Claude Code 的抽取比较

## 当前选型

**以核心业务信息完整度为首要目标，本轮优先选阿器，并在收卷阶段加确定性的 schema 校验与格式修复。Claude Code 的原始输出格式更可靠，但遗漏的核心信息更多。** 这是两份历史产出的工程选型结论；尚未完成所有声明的语义精确率裁定，不能表述为阿器在正确性、速度等所有指标上都胜出。

此次确实在比较相同的织语素材：TASK.md、INDEX.json、schema.json 与 26 页 inputs/ 共 81 个文件逐一校验 SHA256 相同。双方原始逐页输出都保留，未重新构建或改写。原始任务包含页面树和 endpoints，未换成另外一套 AX 任务。

## 同分母结果

| 指标 | 阿器 | Claude Code | 解读 |
|---|---:|---:|---|
| 26 页输出齐全 | 26/26 | 26/26 | 均完成 |
| 核心实体声明召回 | 3/3 | 2/3 | Claude Code 缺购物车实体 |
| 核心属性声明召回 | 30/32（93.75%） | 26/32（81.25%） | 阿器高 12.5 个百分点 |
| 原始输出符合原 schema | 7/26 | 26/26 | Claude Code 更好 |
| 操作可关联到已声明实体 | 全部 | 全部 | 按明确归属或实体名前缀校验 |
| E### 引用存在于本页 | 全部 | 全部 | 只表示可定位，不证明语义正确 |
| api_refs 引用静态模板 | 0 次 | 0 次 | 双方均未出现；属性引用模板另论 |

32 个属性及 3 个实体都已找到**相同 inputs/ 内的原文见证**，证据文件、行号、原文写入 JSON。没有把只在完整原始 trace、却不在抽取输入中的事实拿来扣分。按概念去重，不把阿器更多的逐页输出条数作为得分。

### 缺失项

- 阿器：分类子分类、商品 short_description。后者在“高级搜索条件”对象中有提及，但没有建模为商品属性；按共同结构化词表记为未命中，不称完全没读到。
- Claude Code：购物车商品数量、分类价格区间、分类子分类、商品图片、Domestic Shipping、International Shipping。
- Claude Code 有商品 short_description 声明，阿器有其余多个独有字段，因此不是一方输出简单包含另一方。

核心答案不是完整实体全集。账户、联系表单、评论、营养标签等范围外信息不自动算错。Claude Code 的“尺寸”在部分页明确指 Size 选项，已由其他页的“规格”命中同一 size 概念，不影响当前去重召回；不把它混成 Product Dimensions。

## 格式与内容分开看

阿器 19 页不符合 schema，共 204 个属性使用了 `description`，而原 schema 只允许 `name`、`note`、`source_refs`。它们不是 204 个事实错误。

只在内存里把属性 `description` 改名为 `note`，无字段冲突，26/26 页全部通过 schema。这个机械修复不补充任何事实；原始结果未改。若系统要求未经任何适配即可直接入库，Claude Code 的本次交付更好；若允许收卷适配，阿器的覆盖优势仍然保留。

原始任务要求 business_entity、operation 及操作归属，没有要求实体间关系数组。因此不沿用前一轮“双方关系 0/1”作为本次扣分项，也不临时提高输出要求。

## 证据正确性复核：不能直接采信自检

以下例子可在两边 `000_root/output/concepts.json` 和相同 `000_root/inputs/` 复查：

1. Claude Code 的“商品-查询”仅以 E018 为 api_refs，说明为加载购物车/对比/消息。E018 的摘要只有 `compare-products` 和 `messages`，不能证明商品记录或购物车数据来源。阿器“产品-查询”也包含 E018，同时另有商品页 GET 引用；两边这个 E018 关联都应收紧。
2. Claude Code 商品“名称”的引用是 `page.aria.yml:strong:Product Showcases`。该锚点即使能定位，也指向展示区标题，不能直接证明商品名称字段。不能把锚点命中率当作语义正确率。
3. 阿器购物车 `subtotal` 的 source_refs 为 E013，指向静态 minicart 模板；输入只给端点摘要，不能据此确认当前购物车有小计值。它不在核心计分分母内，保留为待裁定声明。
4. 阿器使用 `page.aria.yml:strong:link:商品标题` 等概括性锚点，无法按原文直接定位。Claude Code 也有 `radio:Size *` 等难以按原文 role/label 定位的锚点。它们需要更精确的引用，但不能仅据此宣布对应属性是幻觉。

完整引用审计在 JSON 中逐项保留：阿器 472 次原文树锚点命中、62 次未按字面命中；Claude Code 为 177 次和 46 次。由于重复引用与声明数不同，不以绝对数量判断谁更好。所有语义声明的精确率尚未逐条裁定，本报告不提供虚假的完整 P/F1。

## 模型、时间和实验边界

- Claude Code 对应本地会话的 assistant.model 字段记录为 `DeepSeek-V4-Flash-0731`（任务开始后 295 条消息记录，不等于295次独立请求）。阿器历史模型目前依据用户说明和当前 agent 配置，尚未找到对应运行的服务端模型记录。
- Claude Code 运行在 AT 外部 agent 集成会话中，日志有任务重复提示和多次压缩，不能称全新空会话、相同预算的严格单次对照。未据此否定现有产物比较。
- 用户报告 Claude Code 约35分钟；日志首次明确提示 2026-09-29 09:04:16 UTC，完成 11:29:21 UTC，墙钟区间约145.1分钟。包括暂停、重试与压缩的区间不是有效推理耗时。两种口径分别记录，阿器对应耗时未知，暂不排速度名次。
- 原始任务/输入一致，harness 自身提示词、工具和会话处理不同，这正是比较因素；模型调用参数、上下文历史和预算未完全控制。
- 答案继承事后 Drive 核心标注，见过阿器历史输出；本次别名与评估规则也在候选存在后确定。先冻结再复算可保证重现，不能消除事后选词偏差。
- Drive dataLoss、非空 cart header 但无 cart-line 的事实仍成立；本次不加购、不改购物车，不把模板、header 推断成购物车明细。旧 `3/4、8/14 vs 4/4、12/14` 仍仅是事后清单回溯，不是正式分数。

## 产物与复算

- `harness-comparison/paired-original.v1.json`：逐项命中/遗漏、全部 schema 错误、引用与输入见证。
- `harness-comparison/paired-original.v1.md`：自动生成的核心指标摘要。模型日志补充以本文件及 `supplementary-audit.v1.json` 为准。
- `harness-comparison/paired-original.freeze.v1.json`：评分代码、双方候选、输入及答案的 SHA256 清单。冻结值 `650f4b72e839a43d397bab33f1ba931571bc050d2c6645e31782a2aedff12d8e`。
- `harness-comparison/supplementary-audit.v1.json`：机械修复模拟、脱敏模型日志元数据及时间区间。

在 `benchmark/harness-comparison` 运行：

```powershell
python test_paired.py
python evaluate_original_task.py score
python supplementary_audit.py
```

依赖 Python jsonschema。3 项定位测试通过；评分程序校验冻结文件以及全部输入哈希后才能计分；两次评分 JSON 字节一致。原始素材和候选输出未改动。
