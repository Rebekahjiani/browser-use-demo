# 现有两份trace统一盘点（pilot-v1）

本报告自动生成。页面类型按URL及HTML页面类分类；分类仍需抽样复核。未知项不补猜测。

|指标|drive|browser-use|
|---|---:|---:|
|snapshots|53|26|
|snapshot_urls|31|5|
|observed_ax_states|53|13|

## drive

页面类型（按快照计）：`{"home": 3, "product_detail": 16, "category_list": 25, "account": 5, "unknown": 1, "contact": 2, "advanced_search": 1}`
无效快照目录：1；分段JSONL文件：37；无效行：0
缺失/空证据文件：0

## browser-use

页面类型（按快照计）：`{"home": 4, "category_list": 10, "product_detail": 3, "advanced_search": 3, "cart": 6}`
无效快照目录：0；分段JSONL文件：62；无效行：0
缺失/空证据文件：0

## 解释边界

- observed_ax_states是URL＋可见AX角色/文本/选中展开状态的哈希数量，商品值或异步文本变化也会增加它，不能直接称为业务独立状态。
- 周期快照不代表访问事件；重复访问率、完整业务状态数本轮不报告。
- 两边都有原始AX文件，可以统一AX观测分析；此前只使用drive ARIA备料并非唯一选择。
- 原生visited计数与有快照证据的URL数分别报告；发现链接不等于访问页面。
- segment可解析不代表无数据丢失；必须结合trace summary中的失败分段与切换缺口。
- 具体页面、源路径、哈希、原生统计和每段解析结果见同目录两个JSON。