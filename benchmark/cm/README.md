# Context Model — shopping 站点（browser-use trace）

## 建模范围

- 输入 trace 根目录：`C:\Users\bulin\browser-use-demo\benchmark\outputs\20260928-160723-422670`
- 目标：基于真实 trace 素材，为 shopping（Magento 风格 demo 商城，127.0.0.1:7770）抽取业务 Context Model。
- 只输出证据支持的概念。页眉、页脚、导航栏、菜单、通用布局与纯 UI 控件不建模为业务实体。
- 概念分为互斥两类：`business_entity`（商品、商品分类、购物车、购物车条目）与 `operation`（查看/查询/搜索/筛选/排序/分页/查看购物车/运费估算/金额合计）。
- 未执行的动作（提交搜索、加入购物车、删除/更新条目、结算）不写成已发生事实，仅记录为“表单/控件可见、未覆盖”。

## 输入 trace 页面清单

| 页面组 | snapshot | URL | 说明 |
|--------|----------|-----|------|
| 首页 | 00001–00004 | http://127.0.0.1:7770/ | 商品网格 12 个、搜索框、Advanced Search 链接、分类导航、minicart |
| Beauty & Personal Care 分类页 | 00005–00014 | /beauty-personal-care.html（含分页参数） | Sort By、Shop By、分页、limiter、21796 总商品数、Add to Cart disabled |
| SureThik 商品详情页 | 00015–00017 | /surethik-b09c6l71ys.html 类 | h1、SKU、价格、In stock、Qty、Add to Cart disabled、Details/Reviews |
| Advanced Search | 00018–00020 | /catalogsearch/advanced/ | 表单字段：Product Name、SKU、Description、Short Description、Price From/To（USD） |
| Shopping Cart | 00021–00026 | /checkout/cart/ | 4 个条目、Summary 区、Estimate Shipping and Tax、Proceed to Checkout |

## 运行状态

- `agent_done`；25 步、21 次工具尝试、5 个唯一页面 URL、26 个 snapshot。
- `dataLossOccurred=true`（见 result.json）。

## 覆盖缺口

1. **搜索未提交**：首页搜索框与 Advanced Search 表单可见（00001、00018），actions.jsonl 中无搜索提交动作；未产生搜索结果页。
2. **未加购**：所有 Add to Cart 按钮在页面中均为 disabled，未发生 add-to-cart 请求或动作。
3. **未改购物车**：Qty 未修改、条目未删除/更新（无 update/delete 动作）。
4. **未结算**：Proceed to Checkout 可见但未点击。
5. **购物车 API 证据来自页面加载时自动触发的 POST**（estimate-shipping-methods、totals-information），非用户显式操作。
6. **Reviews 表单**（Rating、Nickname、Summary、Review）在详情页可见，但未提交任何评论。

## 质量问题（详见 quality-report.json）

- `dataLossOccurred=true`、`maxSwitchGapMs=2660`。
- step 5 `search_page` 正则无效（Invalid group），步骤报错。
- LLM 90 秒超时、输出截断（max_completion_tokens=4096）、AgentOutput JSON 校验失败（result.json 记录）。
- `network.jsonl` 约 1.55MB 超单次读取上限，改为 search_file 定位后读取，未整读。
- trace 大量 segment 仅含 Chrome loading 事件，无业务字段；已跳过并记录。
- 00015 page.html 中嵌入 JSON（product id=6520、type=simple 等）与 AXTree 均确认存在，未发现 URL/标题/树冲突。

## 输出文件

- entities.json / operations.json / context-model.json / evidence-index.json / quality-report.json
