# 给 ArtifactTrace 的 browser-use Context Model 生成任务

请使用 ContextModelGenerator 流程，读取 browser-use 本次 shopping 探索的完整 trace 素材：

`C:\Users\bulin\browser-use-demo\benchmark\outputs\20260928-160723-422670`

这是一次与织语采用相同预算的探索（动作上限 200、页面上限 100、时间上限 30 分钟）。请把它作为独立证据源处理，不要混入织语的 trace 或其他运行结果。

## 输入读取顺序

1. 先读 `result.json`、`config.json`、`observations.jsonl`、`actions.jsonl` 和 `history.json`，建立本次运行的页面和动作清单。
2. 逐个读取 `snapshots/` 下的全部页面素材：`metadata.json`、`page.html`、`accessibility.json` 和截图（截图只作辅助）。
3. 读取 `trace/` 下可解析的 segment、事件和网络/API 摘要；如果某个 segment 无法解析，记录原因并继续处理其他 segment。
4. 以实际素材为准，不要根据页面 URL、常识或模型总结臆造不存在的页面、实体、字段、接口或动作。

## 生成目标

请生成 browser-use shopping 站点的 Context Model，至少覆盖：

- 商品（商品列表、商品详情、SKU、价格、库存等页面证据）；
- 商品分类；
- 搜索与高级搜索；
- 筛选、排序、分页等列表操作；
- 购物车及购物车条目；
- 查看商品、查询商品、搜索商品、筛选商品、排序商品、分页浏览、查看购物车等 operation。

只输出证据支持的概念。页面导航、页眉、菜单和通用布局不要单独建模为业务实体。

## 概念约束

识别两类互斥概念：

1. `business_entity`：具有稳定业务身份、可持续展示或持久化的对象。
2. `operation`：针对实体的原子动作。

每个 operation 必须通过 `belongs_to_entity` 关联一个实体；如果无法合理关联则不要输出。实体有页面加载或明确接口证据时，至少考虑一个“实体-查看”或“实体-查询” operation。

## 证据和 API 约束

- `evidence_refs` 只能引用本次 browser-use 输出中真实存在的文件、snapshot、action、observation、trace segment 或明确事件标识。
- `page_refs` 只写实体实际出现的 snapshot/page 目录或页面标识。
- `api_refs` 只有在 trace 中明确记录了接口 URL、请求、响应或 endpoint 标识时才填写；仅凭 HTML、URL、页面加载或猜测不得填写，使用 `[]`。
- 属性名只能来自 HTML、可访问性树或接口响应中实际出现的字段/列名/label；不要把具体商品值写成属性名。
- 不要把此次探索中“没有执行”的搜索提交、加入购物车、删除条目、结算等动作写成已发生事实。可以在 notes 或覆盖缺口中说明。

## 输出位置

将最终 browser-use Context Model 输出到：

`C:\Users\bulin\browser-use-demo\benchmark\cm\`

请创建并写入：

- `cm/README.md`：范围、输入运行目录、页面清单、覆盖缺口和质量问题；
- `cm/entities.json`：实体及属性；
- `cm/operations.json`：动作、所属实体、证据引用；
- `cm/context-model.json`：合并后的最终 Context Model；
- `cm/evidence-index.json`：概念到 snapshot/action/trace 文件的引用索引；
- `cm/quality-report.json`：输入页数、实体数、operation 数、API 引用数、无法解析的素材、数据丢失和证据缺口。

如果 ContextModelGenerator 模板已有固定 schema 或文件名，优先遵循模板 schema，同时把等价结果写入上述目录；不要覆盖原始 trace。

## 质量检查

完成前检查：

1. 所有 JSON 都可解析；
2. 每个 operation 都关联实体；
3. 每个引用都能定位到本次运行的真实素材；
4. 没有发明 API、字段或未执行的动作；
5. 明确记录本次运行的 `dataLossOccurred=true`、模型超时/截断/JSON 格式错误等质量问题；
6. 逐页处理完成后汇报：总页面数、成功处理页数、跳过页数、实体数、operation 数、API 引用数和剩余缺口。

全部完成后告诉我，并给出 `C:\Users\bulin\browser-use-demo\benchmark\cm\` 下实际生成文件的清单。
