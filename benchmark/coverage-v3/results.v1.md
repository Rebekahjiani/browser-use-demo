# 修订后自动探索 UI 证据覆盖

同一冻结规则直接审计原始AX与页面类型；不读取CM名称。只读核心有限范围，不是全站覆盖率。

| 维度 | Drive | browser-use |
|---|---:|---:|
| affordance | 7/7 | 7/7 |
| attribute | 29/29 | 16/29 |
| business_state | 2/6 | 1/6 |
| entity | 2/3 | 3/3 |
| form_field | 1/1 | 1/1 |
| input_control | 1/1 | 1/1 |
| page_type | 4/6 | 5/6 |

## 逐项证据支持

| 事实 | Drive | browser-use |
|---|---|---|
| product | 支持 | 支持 |
| category | 支持 | 支持 |
| cart | 未证明 | 支持 |
| product.name | 支持 | 支持 |
| product.sku | 支持 | 支持 |
| product.price | 支持 | 支持 |
| product.rating | 支持 | 支持 |
| product.review_count | 支持 | 支持 |
| product.availability | 支持 | 支持 |
| product.image | 支持 | 支持 |
| control.product.quantity | 支持 | 支持 |
| product.size | 支持 | 支持 |
| product.color | 支持 | 未证明 |
| product.style | 支持 | 未证明 |
| product.description | 支持 | 支持 |
| form.search.short_description | 支持 | 支持 |
| product.asin | 支持 | 支持 |
| product.dimensions | 支持 | 未证明 |
| product.upc | 支持 | 未证明 |
| product.manufacturer | 支持 | 支持 |
| product.country_of_origin | 支持 | 支持 |
| product.package_dimensions | 支持 | 未证明 |
| product.item_weight | 支持 | 未证明 |
| product.model_number | 支持 | 未证明 |
| product.date_first_available | 支持 | 未证明 |
| product.batteries | 支持 | 未证明 |
| product.discontinued_status | 支持 | 未证明 |
| product.domestic_shipping | 支持 | 未证明 |
| product.international_shipping | 支持 | 未证明 |
| product.department | 支持 | 未证明 |
| category.name | 支持 | 支持 |
| category.item_count | 支持 | 支持 |
| category.subcategories | 支持 | 支持 |
| category.price_range | 支持 | 支持 |
| search.basic | 支持 | 支持 |
| search.advanced | 支持 | 支持 |
| catalog.filter | 支持 | 支持 |
| catalog.sort | 支持 | 支持 |
| catalog.paginate | 支持 | 支持 |
| cart.add | 支持 | 支持 |
| cart.view | 支持 | 支持 |
| cart.empty | 未证明 | 支持 |
| search.results_nonempty | 未证明 | 未证明 |
| search.results_empty | 未证明 | 未证明 |
| catalog.filtered_result | 支持 | 未证明 |
| catalog.price_sort_selected | 未证明 | 未证明 |
| catalog.next_page | 支持 | 未证明 |
| page.home | 支持 | 支持 |
| page.category_list | 支持 | 支持 |
| page.product_detail | 支持 | 支持 |
| page.advanced_search | 支持 | 支持 |
| page.search_results | 未证明 | 未证明 |
| page.cart | 未证明 | 支持 |

未证明仅限已记录UI。完整trace忠实度、DB来源和成本不由本表推出。页面控件、输入、状态分别计分，不合成总分。

冻结：`d243e0c68d7671d1485b85396b48df5731973f525500e4daf5c6cf221af7981e`

复算：`python test_score.py`，`python score.py score`。输出无变化时间字段，同输入可逐字节复算。
