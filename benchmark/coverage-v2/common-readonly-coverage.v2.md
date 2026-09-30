# 共同只读核心契约：历史 trace 的 UI 证据覆盖

按用户决定，只评全新访客可只读访问的商品、搜索筛选和空购物车。**分母为同一份55项核心契约，不是全站全集。** 各维度分开，不合成总分。

| 维度 | Drive 命中/分母 | browser-use 命中/分母 | Drive recall | browser-use recall |
|---|---:|---:|---:|---:|
| attribute | 31/32 | 19/32 | 96.88% | 59.38% |
| business_state | 2/6 | 1/6 | 33.33% | 16.67% |
| entity | 3/3 | 3/3 | 100.00% | 100.00% |
| operation_control | 7/7 | 7/7 | 100.00% | 100.00% |
| page_type | 4/6 | 5/6 | 66.67% | 83.33% |
| relation | 1/1 | 1/1 | 100.00% | 100.00% |

## 逐项矩阵

| 项目 | Drive | browser-use |
|---|---|---|
| product | 有证据 | 有证据 |
| category | 有证据 | 有证据 |
| cart | 有证据 | 有证据 |
| product.name | 有证据 | 有证据 |
| product.sku | 有证据 | 有证据 |
| product.price | 有证据 | 有证据 |
| product.rating | 有证据 | 有证据 |
| product.review_count | 有证据 | 有证据 |
| product.availability | 有证据 | 有证据 |
| product.image | 有证据 | 有证据 |
| product.quantity | 有证据 | 有证据 |
| product.size | 有证据 | 有证据 |
| product.color | 有证据 | 未见 |
| product.style | 有证据 | 未见 |
| product.description | 有证据 | 有证据 |
| product.short_description | 有证据 | 有证据 |
| product.asin | 有证据 | 有证据 |
| product.dimensions | 有证据 | 未见 |
| product.upc | 有证据 | 未见 |
| product.manufacturer | 有证据 | 有证据 |
| product.country_of_origin | 有证据 | 有证据 |
| product.package_dimensions | 有证据 | 未见 |
| product.item_weight | 有证据 | 未见 |
| product.model_number | 有证据 | 未见 |
| product.date_first_available | 有证据 | 未见 |
| product.batteries | 有证据 | 未见 |
| product.discontinued_status | 有证据 | 未见 |
| product.domestic_shipping | 有证据 | 未见 |
| product.international_shipping | 有证据 | 未见 |
| product.department | 有证据 | 未见 |
| category.name | 有证据 | 有证据 |
| category.item_count | 有证据 | 有证据 |
| category.subcategories | 有证据 | 有证据 |
| category.price_range | 有证据 | 有证据 |
| cart.empty_state | 未见 | 有证据 |
| search.basic | 有证据 | 有证据 |
| search.advanced | 有证据 | 有证据 |
| catalog.filter | 有证据 | 有证据 |
| catalog.sort | 有证据 | 有证据 |
| catalog.paginate | 有证据 | 有证据 |
| cart.add | 有证据 | 有证据 |
| cart.view | 有证据 | 有证据 |
| category_lists_product | 有证据 | 有证据 |
| cart.empty | 未见 | 有证据 |
| search.results_nonempty | 未见 | 未见 |
| search.results_empty | 未见 | 未见 |
| catalog.filtered_result | 有证据 | 未见 |
| catalog.sorted_result | 未见 | 未见 |
| catalog.next_page | 有证据 | 未见 |
| page.home | 有证据 | 有证据 |
| page.category_list | 有证据 | 有证据 |
| page.product_detail | 有证据 | 有证据 |
| page.advanced_search | 有证据 | 有证据 |
| page.search_results | 未见 | 未见 |
| page.cart | 未见 | 有证据 |

## 解释

- Drive的商品字段更丰富；browser-use额外记录空购物车页面和状态。相同分母能描述材料差异，但初始状态/权限不同，不能单独归因于算法。
- Drive有筛选结果和第二页证据，browser-use有空购物车状态；两边均未记录搜索结果或按价格排序的结果。控件可见不等于操作结果。
- Drive非空header只作为历史额外观察，不计空购物车状态，也不推断cart-line。
- 本报告只审计原始UI快照，network/rawbody中可能包含的补充事实没有当作不存在。
- 商品特殊属性由UI字段/值证明，有些只存在于描述表格；DB字段映射尚未全部确认，不能称每一项都是独立物理列。
- 页面类型和状态目录是明确定义的有限目标集，不称全站类型/状态全集。

## 冻结与复算

冻结：2026-09-29T07:02:51.851263+00:00；计分：2026-09-29T07:15:08.783351+00:00。

Manifest SHA256：`773e8dc42a8b66079ef320c289dcc3ac9cdca599ef22520e302f3994f4982e83`。

```powershell
python test_coverage.py
python score_coverage_v2.py score
```

每项原始AX定位与quote见JSON。标准答案的独立网站证据见common-readonly.v2.json；原始历史trace未修改。
