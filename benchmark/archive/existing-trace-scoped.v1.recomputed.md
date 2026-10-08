# 现有运行的 trace-scoped 诊断

冻结时间：2026-09-29T05:57:48.492695+00:00；计分时间：2026-09-29T06:23:25.884589+00:00

Freeze SHA256: `3a28aac1ccbb882adb5f23481d94184e59ac978009993a5d9bcc9e52262b9590`

本报告为事后核心范围诊断。P/R/F1 按名称/结构匹配计分，不代表引用已证明断言。未裁定额外项不判为幻觉；P 是已裁定子集精度，另报保守精度区间。

| 运行 | 指标 | 命中/答案 | 已裁定预测 | P | R | F1 | 未裁定 | P 区间 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| drive | entities | 3/3 | 3 | 100.00% | 100.00% | 100.00% | 0 | 100.00%–100.00% |
| drive | attributes | 30/32 | 30 | 100.00% | 93.75% | 96.77% | 3 | 90.91%–100.00% |
| drive | operations | 3/7 | 3 | 100.00% | 42.86% | 60.00% | 0 | 100.00%–100.00% |
| drive | relations | 0/1 | 0 | N/A | 0.00% | 0.00% | 0 | N/A–N/A |
| browser-use-20260929 | entities | 3/3 | 3 | 100.00% | 100.00% | 100.00% | 0 | 100.00%–100.00% |
| browser-use-20260929 | attributes | 16/19 | 16 | 100.00% | 84.21% | 91.43% | 0 | 100.00%–100.00% |
| browser-use-20260929 | operations | 6/7 | 6 | 100.00% | 85.71% | 92.31% | 0 | 100.00%–100.00% |
| browser-use-20260929 | relations | 0/1 | 0 | N/A | 0.00% | 0.00% | 0 | N/A–N/A |

## 规则与限制

- 核心实体/字段词表为窄范围答案，非完整 trace 或全站标准答案；营养成分、搜索条件对象、账户等未穷举。
- 所有属性答案独立进入召回分母，父实体漏报也不会删分母；canonical 去重，中英文及 snake/camel case 别名归一。
- 价格区间独立实体仅把 range 映射为 category.price_range；不额外记 category 实体命中，facet itemCount 不等于分类总商品数。
- 浏览列表与查看详情合并为 product_navigation；购物车 API 会话加载/查询不等于进入购物车页面，不计 cart_view 命中。
- Description 与 Short Description 分开；Short Description 仅有搜索表单字段证据，证明暴露字段名，不证明商品已填值。
- 未知额外断言进入待裁定队列，不自动记幻觉；精度为已裁定子集 P，并列出把全部未裁定项分别当错/对的界限。结构关系必须有结构化条目，描述中提及不计关系命中。
- 属性不继承父实体页面引用。证据索引仅能补自身 ID 的引用；文件存在、精确定位、语义支持分开，语义支持待人工复核。
- Drive 操作 executed 未经完整动作日志裁定，标为 null，不能把未知标为 false；browser-use 导航由目标页快照支持，其余操作在记录中未执行。
- 答案在现有输出存在且已被查看后标注，属于 post-hoc 核心范围诊断，不是盲标、无偏答案或正式策略/harness 排名。
- 旧 3/4, 8/14 vs 4/4, 12/14 是看过输出后整理14项清单的回溯结果，browser-use 对应2026-09-28旧 trace，禁止称为正式分数。
- 提示词、输入处理不一致；trace 覆盖不同（Drive约31 URL，browser-use 5 URL），每侧独立分母不能作公平胜负比较。
- browser-use 2026-09-29 是访客空购物车，无 cart-line、购物车数量、小计或总计证据；可见 Add to Cart 控件不等于发生加购。
- Drive 非空 cart header 显示3/4 items，但本范围没有 cart-page/cart-line 证据；初始购物车状态未知，不能推断写后成功。
- Drive 有失败分段及 dataLossOccurred=true；browser-use 30/30分段且 dataLossOccurred=false。Drive答案每条已回链至原始 aria.yml 精确行，仍不消除采集缺口。
- DB Context Model 只作字段映射参考，不扩大分母；derived_or_unverified 项未做实时 DB 记录值核验。
- 双方报告为阿器+DeepSeek V4 Flash，但 Drive 成功模型日志尚未定位；运行资源成本/完成页数没有统一可比契约，本轮不补造数据。
- 尚未完成全部候选断言的人工语义支持与额外项裁定；报告的匹配分数不是证据支持度分数。

## drive 逐项诊断


### entities

命中：cart, category, product

遗漏：无

待裁定：无

### attributes

命中：cart.item_count, category.item_count, category.name, category.price_range, product.asin, product.availability, product.batteries, product.color, product.country_of_origin, product.date_first_available, product.department, product.description, product.dimensions, product.discontinued_status, product.domestic_shipping, product.image, product.international_shipping, product.item_weight, product.manufacturer, product.model_number, product.name, product.package_dimensions, product.price, product.quantity, product.rating, product.review_count, product.size, product.sku, product.style, product.upc

遗漏：category.subcategories, product.short_description

待裁定：cart.?cart, cart.?messages, cart.?subtotal

### operations

命中：add_to_cart, product_navigation, search

遗漏：cart_view, filter, paginate, sort

待裁定：无

### relations

命中：无

遗漏：category_lists_product

待裁定：无

### 引用与执行

在 42 条范围内原始断言中，带自身引用 42，可定位到文件/目录 27，可定位到节点/行 27。语义支持仍需人工复核，不能由命中或引用存在率代替。

```json
[
  {
    "operation": "product_navigation",
    "candidate": null,
    "reference": null,
    "status": "not_assessable",
    "reference_basis": "not_adjudicated_from_action_log"
  },
  {
    "operation": "add_to_cart",
    "candidate": null,
    "reference": null,
    "status": "not_assessable",
    "reference_basis": "not_adjudicated_from_action_log"
  },
  {
    "operation": "search",
    "candidate": null,
    "reference": null,
    "status": "not_assessable",
    "reference_basis": "not_adjudicated_from_action_log"
  }
]
```

排除项（不作为错误）：
- 商品比较清单：outside_core_domain
- 新闻订阅：outside_core_domain
- 价格区间.itemCount：facet_bucket_count_outside_core_vocabulary
- 价格区间：facet entity normalized to category.price_range; not a category entity hit
- 心愿单：outside_core_domain
- 商品评论：outside_core_domain
- 高级搜索条件：outside_core_domain
- 联系请求：outside_core_domain
- 客户账户：outside_core_domain
- 客户会话：outside_core_domain
- 产品-加入比较：outside_core_operation_contract
- 产品-加入心愿单：outside_core_operation_contract
- 商品比较清单-查询：outside_core_operation_contract
- 新闻订阅-提交：outside_core_operation_contract
- 商品比较清单-移除：outside_core_operation_contract
- 商品比较清单-清空：outside_core_operation_contract
- 产品-写评论：outside_core_operation_contract
- 购物车-查询：outside_core_operation_contract
- 联系请求-提交：outside_core_operation_contract
- 新闻订阅-订阅：outside_core_operation_contract
- 商品评论-查询：outside_core_operation_contract
- 客户账户-登录提交：outside_core_operation_contract
- 客户账户-会话加载：outside_core_operation_contract
- 客户账户-注册：outside_core_operation_contract
- 客户账户-忘记密码：outside_core_operation_contract
- 商品比较清单-比较：outside_core_operation_contract
- 商品比较清单-移除商品：outside_core_operation_contract
- 购物车-会话加载：outside_core_operation_contract
- 客户会话-加载：outside_core_operation_contract
- 商品评论-写评论：outside_core_operation_contract
- 商品比较清单-会话加载：outside_core_operation_contract

## browser-use-20260929 逐项诊断


### entities

命中：cart, category, product

遗漏：无

待裁定：无

### attributes

命中：cart.empty_state, category.item_count, category.name, category.price_range, category.subcategories, product.asin, product.availability, product.country_of_origin, product.manufacturer, product.name, product.price, product.quantity, product.rating, product.review_count, product.short_description, product.sku

遗漏：product.description, product.image, product.size

待裁定：无

### operations

命中：cart_view, filter, paginate, product_navigation, search, sort

遗漏：add_to_cart

待裁定：无

### relations

命中：无

遗漏：category_lists_product

待裁定：无

### 引用与执行

在 26 条范围内原始断言中，带自身引用 10，可定位到文件/目录 10，可定位到节点/行 0。语义支持仍需人工复核，不能由命中或引用存在率代替。

```json
[
  {
    "operation": "product_navigation",
    "candidate": true,
    "reference": true,
    "status": "match",
    "reference_basis": "observed_destination_page"
  },
  {
    "operation": "product_navigation",
    "candidate": true,
    "reference": true,
    "status": "match",
    "reference_basis": "observed_destination_page"
  },
  {
    "operation": "search",
    "candidate": false,
    "reference": false,
    "status": "match",
    "reference_basis": "not_executed_in_recorded_run"
  },
  {
    "operation": "filter",
    "candidate": false,
    "reference": false,
    "status": "match",
    "reference_basis": "not_executed_in_recorded_run"
  },
  {
    "operation": "sort",
    "candidate": false,
    "reference": false,
    "status": "match",
    "reference_basis": "not_executed_in_recorded_run"
  },
  {
    "operation": "paginate",
    "candidate": false,
    "reference": false,
    "status": "match",
    "reference_basis": "not_executed_in_recorded_run"
  },
  {
    "operation": "cart_view",
    "candidate": true,
    "reference": true,
    "status": "match",
    "reference_basis": "observed_destination_page"
  }
]
```

排除项（不作为错误）：

## 复算

在 benchmark/extraction 目录运行：

```powershell
python test_scorer.py
python score_context_models.py verify
python score_context_models.py score
```

评分前校验 manifest 内所有文件哈希；任一变化即拒绝评分。JSON 保存每项断言、归一结果、遗漏、排除、待裁定和引用检查结果。原始 trace 只读，完整文件清单包含于 freeze.v1.json。
