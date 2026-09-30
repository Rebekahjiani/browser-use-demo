# 统一页面语义抽取 v1（UI-only）
读取 INDEX.json，逐目录读 inputs/page.json 与 inputs/ui.json，写该目录 output/concepts.json，符合 schema.json。调用工具时按工具 schema 明确提供 path；先列目录再读文件。

只根据本任务包证据抽取 business_entity 与 operation。不得读取 ground-truth、其他策略输出、数据库、历史回答或联网补充。不预设要发现哪些实体。

实体列 canonical_name、description、aliases、attributes、evidence_refs、api_refs、page_refs。属性 name 用证据中的 label/字段名，source_refs 引用本页 U 编号；不得发明字段。实体 page_refs 写本页目录名。不要把商品数据值复制为属性名。导航布局本身不是业务实体。

operation 必须填写 belongs_to_entity、canonical_name、description、evidence_refs、api_refs 和 observation_level。本包只有静态结构证据，observation_level 固定为 visible_control；控件存在不代表执行成功。只看到明确控件才输出动作，不根据实体存在强制补“查询”。

所有 evidence_refs/source_refs 使用本页 ui.json 中真实 U 编号。本轨不提供网络证据，所有 api_refs=[]。不得用 HTML 路径、页面 URL 代替接口证据。

额外输出顶层 relations 数组，每项包括 source_entity、predicate、target_entity、evidence_refs；仅输出证据支持的关系，不按常识补齐。无关系时写 []。所有输出包含 notes 数组记录不确定性。

全部页处理后报告成功、失败页数；无法读取的页记录失败，不能声称完成。不要另写任意格式的 context-model.json。最终由统一收卷工具验证引用与格式后汇总。
