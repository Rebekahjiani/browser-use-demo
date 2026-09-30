# 两次既有 Context Model 回溯诊断（非正式评分）

输出文件：`existing-cm-provisional.json`。下面数字只展示当前合并器和名称映射能否运行。14项检查表是在查看两边输出后才整理的，存在明显的事后选择偏差；不能用来判断哪种策略更好。实体范围为商品、商品分类、购物车、购物车条目；不代表全站真值，也不评精确率。正式评分必须先独立冻结参考答案。

|策略|实体命中|字段命中|相对当前清单召回¹|
|---|---:|---:|---:|
|drive|3/4|8/14|57.1%|
|browser-use|4/4|12/14|85.7%|

## drive

- product: 实体已提取；字段命中 name, sku, price, image, quantity_and_stock_status；遗漏 无。
- category: 实体已提取；字段命中 name；遗漏 无。
- cart: 实体已提取；字段命中 items_count, subtotal；遗漏 grand_total。
- cart_item: 实体遗漏；字段命中 无；遗漏 name, sku, qty, price, row_total。

## browser-use

- product: 实体已提取；字段命中 name, sku, price, quantity_and_stock_status；遗漏 image。
- category: 实体已提取；字段命中 name；遗漏 无。
- cart: 实体已提取；字段命中 subtotal, grand_total；遗漏 items_count。
- cart_item: 实体已提取；字段命中 name, sku, qty, price, row_total；遗漏 无。

¹ 召回以回溯整理的14项清单为分母，因事后选择偏差仅供调试查看。

## 可比性限制

- browser-use 的 AT 运行 trace 明确记录模型 `sophnet/DeepSeek-V4-Flash-0731`；织语评测计划记载使用同一模型，但对应成功运行记录尚未定位。
- 提示词不同：织语使用逐页 `entity-extract/TASK.md`；browser-use 使用专门编写的总任务，直接点名商品、分类、购物车等目标概念。
- 输入准备不同：织语抽取包有26页并附 endpoints 摘要；browser-use最终总结称处理26个 snapshot 目录，但只读取了5个代表页面的 accessibility JSON，并使用部分网络证据。
- 所以当前数字混合了采集、备料、提示词和阿器提取的影响，不能将差异单独归因于采集策略。
- 当前不评 precision、操作和关系，也不声称结果完整。
- 两份 trace 都有 `dataLossOccurred=true` 标记。

## 解释

browser-use 在这个事后清单上命中更多项，但这不是可信的胜负结论。可确认的是：两份结果文件结构已统一读取、跨格式归并和全局召回分母的计算流程可以运行。正式结论需先冻结独立答案，再用同一提示词和备料方式评分。