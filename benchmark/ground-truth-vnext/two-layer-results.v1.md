# 两层指标下的自动探索比较

DB层仅为已验证映射子集，不能称全库覆盖率；业务细节单列，description内多个子字段不重复增加DB层分数。

| 层次 | Drive | browser-use |
|---|---:|---:|
| DB_verified_subset | 6/6 | 6/6 |
| business_detail | 29/29 | 16/29 |

DB已核验子集持平；当前业务细节范围Drive领先。页面和记录完整性browser-use更好，保留原始条件差异，不合成总冠军。

剩余59个EAV候选仍待界面核验，28项为范围排除草案；不能把未知当不存在。

复算：`python test_two_layers.py`、`python score_two_layers.py score`。
