# B 路径引用兼容诊断（事后补充）

历史v4评分保留。本诊断处理观测到的多角色路径引用；路径带label时必须定位到本页该字段，无label时所有选中节点必须仅定位同一字段。模糊路径不自动得分。

| trace | 组合 | 原v4命中 | 兼容路径后命中 | 输入可见字段 |
|---|---|---:|---:|---:|
| 01-drive | aqi | 20/32 | 20/32 | 24 |
| 01-drive | claudecode | 17/32 | 17/32 | 24 |
| 01-browser-use | aqi | 8/32 | 8/32 | 14 |
| 01-browser-use | claudecode | 6/32 | 7/32 | 14 |
| 02-drive | aqi | 16/32 | 16/32 | 21 |
| 02-drive | claudecode | 3/32 | 12/32 | 21 |
| 02-browser-use | aqi | 0/32 | 9/32 | 18 |
| 02-browser-use | claudecode | 1/32 | 11/32 | 18 |
| 03-drive | aqi | 13/32 | 13/32 | 20 |
| 03-drive | claudecode | 12/32 | 12/32 | 20 |
| 03-browser-use | aqi | 3/32 | 3/32 | 16 |
| 03-browser-use | claudecode | 11/32 | 11/32 | 16 |

这是生成期间针对已观测格式提出并冻结的事后诊断，不是预注册主指标，也不是完整语义准确率。
