# 两份历史 trace 的共同口径离线审计

这是共同候选清单的证据命中审计，不是网站覆盖率。G 尚未通过独立界面核验，所有比例留空。

| 观察指标 | Drive | browser-use 2026-09-29 |
|---|---:|---:|
| snapshots | 53 | 14 |
| unique_urls | 31 | 5 |
| attribute 候选规则命中数 | 32 | 19 |
| business_state 候选规则命中数 | 2 | 1 |
| entity 候选规则命中数 | 3 | 3 |
| operation_control 候选规则命中数 | 7 | 7 |
| relation 候选规则命中数 | 1 | 1 |

## 候选事实逐项矩阵

“有”表示同一AX规则有证据命中，仍需语义复核；“未见”只限已记录AX。

| 候选事实 | 类型 | Drive | browser-use |
|---|---|---|---|
| product | entity | 有 | 有 |
| category | entity | 有 | 有 |
| cart | entity | 有 | 有 |
| cart_item | entity | 未见 | 未见 |
| product.name | attribute | 有 | 有 |
| product.sku | attribute | 有 | 有 |
| product.price | attribute | 有 | 有 |
| product.rating | attribute | 有 | 有 |
| product.review_count | attribute | 有 | 有 |
| product.availability | attribute | 有 | 有 |
| product.image | attribute | 有 | 有 |
| product.quantity | attribute | 有 | 有 |
| product.size | attribute | 有 | 有 |
| product.color | attribute | 有 | 未见 |
| product.style | attribute | 有 | 未见 |
| product.description | attribute | 有 | 有 |
| product.short_description | attribute | 有 | 有 |
| product.asin | attribute | 有 | 有 |
| product.dimensions | attribute | 有 | 未见 |
| product.upc | attribute | 有 | 未见 |
| product.manufacturer | attribute | 有 | 有 |
| product.country_of_origin | attribute | 有 | 有 |
| product.package_dimensions | attribute | 有 | 未见 |
| product.item_weight | attribute | 有 | 未见 |
| product.model_number | attribute | 有 | 未见 |
| product.date_first_available | attribute | 有 | 未见 |
| product.batteries | attribute | 有 | 未见 |
| product.discontinued_status | attribute | 有 | 未见 |
| product.domestic_shipping | attribute | 有 | 未见 |
| product.international_shipping | attribute | 有 | 未见 |
| product.department | attribute | 有 | 未见 |
| category.name | attribute | 有 | 有 |
| category.item_count | attribute | 有 | 有 |
| category.subcategories | attribute | 有 | 有 |
| category.price_range | attribute | 有 | 有 |
| cart.empty_state | attribute | 未见 | 有 |
| cart.item_count | attribute | 有 | 未见 |
| cart.subtotal | attribute | 未见 | 未见 |
| cart.grand_total | attribute | 未见 | 未见 |
| cart.coupon_code | attribute | 未见 | 未见 |
| cart.shipping_amount | attribute | 未见 | 未见 |
| cart_item.name | attribute | 未见 | 未见 |
| cart_item.price | attribute | 未见 | 未见 |
| cart_item.quantity | attribute | 未见 | 未见 |
| cart_item.row_total | attribute | 未见 | 未见 |
| search.basic | operation_control | 有 | 有 |
| search.advanced | operation_control | 有 | 有 |
| catalog.filter | operation_control | 有 | 有 |
| catalog.sort | operation_control | 有 | 有 |
| catalog.paginate | operation_control | 有 | 有 |
| cart.add | operation_control | 有 | 有 |
| cart.view | operation_control | 有 | 有 |
| cart.update | operation_control | 未见 | 未见 |
| cart.remove | operation_control | 未见 | 未见 |
| category_lists_product | relation | 有 | 有 |
| cart_contains_item | relation | 未见 | 未见 |
| cart_item_refers_product | relation | 未见 | 未见 |
| cart.empty | business_state | 未见 | 有 |
| cart.nonempty_header | business_state | 有 | 未见 |
| cart.nonempty_page | business_state | 未见 | 未见 |
| product.required_option_error | business_state | 有 | 未见 |
| search.results_nonempty | business_state | 未见 | 未见 |
| search.results_empty | business_state | 未见 | 未见 |

## 限制

- Common registry is draft; no website-level coverage denominator or percentages.
- Same AX rules used on both raw snapshot sets; matches require semantic review.
- No match means not observed in available AX, not absent from all network evidence or site.
- Starting state, exploration permissions, prompts and coverage differ; not a controlled algorithm ranking.
- Network provenance, complete transitions and UI reachability await further verification.
- Drive非空header不能代替cart-line；browser-use空购物车没有金额/条目证据。
- 有控件不等于已执行；暂无完整动作结果评分。
- Drive原生URL时间不能当作snapshot事实首次发现时间，不生成伪精确的语义覆盖曲线。
- 规范化输入是UI-only候选适配器，未冒充织语统一构建流程，也未生成新的CM分数。

## 复算

```powershell
python audit_traces.py
```

输入哈希见 offline-audit.inputs.json；逐项原始AX JSON Pointer与quote见 offline-coverage-audit.json。
