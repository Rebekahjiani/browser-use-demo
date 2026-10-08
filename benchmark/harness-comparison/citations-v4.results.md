# B：属性自身引用支持的核心召回

这是保守引用支持诊断：字段在本页存在且自身source_refs可定位到该字段才命中；范围外与未定位保留待核验，不当错。不是完整准确率。

| 指标 | 阿器 | Claude Code |
|---|---:|---:|
| own_citation_core_recall | 30/32 | 22/32 |
| core_assertions | 202 | 191 |
| supported_core_assertions | 186 | 149 |
| unresolved_core_assertions | 16 | 42 |
| incorrect_refs | 0 | 0 |

表格容器引用如table:ASIN可通过其子行头定位；泛指“商品标题”等非原文锚点不自动修补。无引用或伪造E编号不能获得自身引用命中。

原任务允许字段label与record_key；本诊断沿用32项任务核心词表，与A的29项有值属性分母不同。短描述搜索框与Qty仅为字段暴露，不证明DB商品值。

v4承认同字段容器内radio选项值、评分值及有结构依据的商品卡名称/子分类链接引用。v3修复ARIA冒号后引号字符串解析。v2/v3保留历史，以v4为当前入口。

复算：`python test_citations_v4.py`、`python score_citations_v4.py score`。
