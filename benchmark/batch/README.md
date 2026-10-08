# 参数化 Shopping 评测入口

此入口新增版本，不修改任何历史冻结规则、trace 或候选。

## 已验证的能力

`score_runs.py freeze --spec <runs.json> --bundle <新目录>` 接入任意数量的不同 run。
每个 run 提供 `id`、`strategy`、`snapshots`（目录下各快照含 accessibility.json 与 page.html）、可选 `conditions` 和 `artifacts`。
spec 提供 `gold`、`mapping`、`runs` 和可选 `experiment`；相对路径以 spec 所在目录解析。
`historical.mapping-v2.runs.json` 是已复算的两份历史运行示例。

冻结独立复制评分代码、规则和映射，校验源材料 SHA256，包括 DB 导出、映射审查来源和标准答案的独立见证。
使用 bundle 内的评分代码复算旧版本；拒绝变更后的输入、不同规则、重复快照根目录、缺少AX/HTML配对和覆盖不同报告。

```powershell
cd C:\Users\bulin\browser-use-demo\benchmark\batch
python .\bundles\historical-v2\score_runs.py score --bundle .\bundles\historical-v2 --output .\reports\historical-v2
python .\test_score_runs.py
python .\test_readonly_proxy.py
```

输出包括每个 run 的逐事实证据、分维度分数、DB去重子集、按快照顺序的覆盖曲线，以及按策略的均值/样本标准差。
声明的条件不等于实际已对齐；曲线未声称动作归一或完整elapsed time。
规则仍面向 Shopping AX/HTML，不是跨站通用语义裁判，也没有 B 全声明语义精确率。

`bundles/historical-v1` 是开发过程的回归检查点，工具源文件随后已更新，当前使用 `historical-v2`。
历史原 coverage-v3 和 two-layer v1 不变。

## 共用只读请求边界

`readonly_proxy.py` 通过 SSH 将本地7770代理到服务器 Shopping7770。
认证只从 `BENCHMARK_SSH_PASSWORD` 环境变量或交互密码读取，不写入文件；使用已知SSH主机密钥。
只放行 GET/HEAD 的公开商品、分类、搜索、空购物车、静态资源和读取 section 路由；其他路径及写方法拦截为403。
浏览器必须使用此HTTP代理并禁用隐式loopback绕过，使站外请求同样被拒绝。
外部HTTPS CONNECT不支持。白名单不足时先审查并新版本化策略，不直接全放行。

代理测试覆盖搜索允许、写路由拒绝、路径穿越、站外URL与SSH响应流完整读取。
线上只读连通性验证：首页/搜索/购物车200，加购403。

## 采集前提

用户已确认2026-10-08新实验允许只读查询提交，browser-use使用 `sophnet/DeepSeek-V4-Flash-0731`。
旧2026-09-29 browser-use **采集**的 config.json 记录 Pro；B历史**抽取**对照为Flash。新旧采集不混算。

2026-10-08 用户已手动启动专用Chrome；正式6次采集和A评分已经完成。以下命令保留为后续重新启动的入口：

```powershell
& 'C:\Users\bulin\browser-use-demo\benchmark\batch\start-browser.ps1'
```

本次采集产出201份快照，去除同URL、完整树和接口shape均相同的输入后，B有111个状态、两种组合共222份目标结果。
`shopping-readonly.txt` 是新权限下的探索提示词。
新增参考核验与规则需在正式运行前冻结，不能让新候选反向决定评分分母。

## B逐页抽取与留痕补跑

`prepare_b.py` 制作两种组合相同的离线输入；`run_b.py` 是首轮串行队列。
`complete_b.py` 只补缺失页面，保留原始失败与中断，每个attempt记录选中页、此前结果hash及结束状态；校验此前结果与冻结输入不变。单个job失败后继续剩余队列，每次启动最多两次尝试。
Claude Code用关闭的stdin运行，以日志文件句柄和逐页结果监控活动；300秒无活动或单trace超过1小时才终止。Windows文件列表可能暂时显示陈旧长度，不能凭列表中的0字节认定模型没有工作。
补跑提示要求读一页即写一页，避免整批预读；首轮与补跑提示/执行差异会留在attempt账本，不把补跑完成性当作首轮成功率。

`audit_b.py` 检查JSON/schema、页面局部引用和输入hash；`score_b.py` 沿用历史v4的32项核心词表和自身引用支持规则，同时报告输入可见字段分母。
字段label或接口编号可定位不等于值级DB核验或实体归属正确，未定位及范围外声明不自动计错，不报告完整语义precision/F1。
`finalize_b.py` 只在222份结果均存在且schema通过时冻结产物、执行血缘和代码，并验证引用评分JSON逐字节复算一致。

结果入口：`b-runs/controlled-v02/citation-results.md`，逐项证据：同目录`citation-results.json`，原始失败和每次补跑日志：各trace/组合目录。
