# ArtifactTrace Context Model 生成任务：browser-use trace

请使用当前 ArtifactTrace 的 ContextModelGenerator 流程，根据下面指定的 browser-use trace 生成 Context Model。

## 唯一输入

本次 trace 根目录是：

`C:\Users\bulin\browser-use-demo\benchmark\outputs\20260929-115141-231052`

以后使用新的 browser-use trace 时，只替换上面这一行的目录地址，其他提示词保持不变。

## 文件读取规则（必须遵守）

1. 先读取 trace 根目录下的 `result.json`、`config.json`、`observations.jsonl`、`actions.jsonl`、`history.json` 和 `prompt.txt`（文件存在才读）。
2. 读取 `snapshots`、`trace`、`agent-files` 的目录清单时，必须给目录列表工具传入完整的 `path` 参数。
3. 读取具体文件时，必须给文件读取工具传入完整的 `path` 参数。示例：

   ```json
   {"path":"C:\\Users\\bulin\\browser-use-demo\\benchmark\\outputs\\20260928-160723-422670\\result.json"}
   ```

4. 禁止调用空参数的文件读取工具；禁止把目录路径直接传给只接受文件路径的 `read_file` 工具。
5. 不要一次性猜测或拼接不存在的文件名。先列目录，再对返回的具体文件逐个读取。
6. 截图只作辅助证据；优先使用 `metadata.json`、`page.html`、`accessibility.json`、actions、observations 和 trace 事件。
7. 不要读取或混入其他 browser-use 运行、织语运行或其他任务目录的素材。

## 工作步骤

1. 根据 `result.json`、`actions.jsonl`、`observations.jsonl` 和 `history.json` 建立实际访问页面、动作和运行状态清单。
2. 逐个读取 `snapshots/` 下每个 snapshot 的 `metadata.json`、`page.html`、`accessibility.json`（存在才读）。
3. 逐个读取 `trace/` 下可解析的 segment、事件和网络/API 摘要；无法解析的文件记录在质量报告中，继续处理其他文件。
4. 以真实素材为唯一依据生成模型，不要根据 URL、常识、模型总结或页面名称臆造未出现的实体、字段、接口或动作。
5. 逐页完成抽取后，再做跨页去重和实体/操作关联。

## 建模范围

目标是生成 shopping 站点的业务 Context Model，至少检查以下对象和动作是否有证据：

- 商品、商品分类、商品详情；
- 商品名称、SKU、价格、库存、分类等属性；
- 搜索、高级搜索、搜索条件；
- 筛选、排序、分页；
- 购物车、购物车条目、数量、小计、运费、总计；
- 查看商品、查询商品、搜索商品、筛选商品、排序商品、分页浏览、查看购物车。

只输出证据支持的概念。页眉、导航栏、菜单、通用布局和纯 UI 控件不要单独建模为业务实体。

## 概念类型

概念必须分为以下两类，且互斥：

### `business_entity`

具有稳定业务身份、可持续展示或可持久化的对象，例如“商品”“商品分类”“购物车”“购物车条目”。

### `operation`

针对实体的原子动作，例如“商品-查看”“商品-查询”“商品-搜索”“商品-筛选”“购物车-查看”。

每个 operation 必须通过 `belongs_to_entity` 关联一个已有实体；无法合理关联的动作不要输出。实体存在页面加载或明确接口证据时，至少考虑一个“实体-查看”或“实体-查询” operation。

## 引用规则

- `evidence_refs`：只能引用本次 trace 中真实存在的 snapshot、HTML、AXTree、action、observation、trace segment 或事件文件。
- `page_refs`：只用于 `business_entity`，写实体实际出现的页面/snapshot 标识。
- `api_refs`：只有 trace 明确记录 API URL、请求、响应或 endpoint 标识时才填写；仅凭 HTML、URL、页面加载或常识推测时必须写 `[]`。
- 属性名只能来自 HTML、可访问性树或接口响应中真实出现的字段、列名或 label。
- 不要把商品实际名称、价格、SKU 或数量等具体值写成属性名。
- 没有执行的动作不能写成已发生事实。例如未提交搜索、未加入购物车、未删除条目、未结算，只能记为“未覆盖”或“可见操作”。
- 禁止跨运行目录引用，禁止发明 API、字段、页面或事件编号。

## 输出目录

所有结果固定写入：

`C:\Users\bulin\appweave\outputs\02-context-model\browser-use-contextmodel`

创建或更新以下文件：

- `README.md`：建模范围、输入 trace 地址、页面清单、覆盖缺口和质量问题；
- `entities.json`：business_entity 及其属性；
- `operations.json`：operation、所属实体和证据引用；
- `context-model.json`：合并后的最终 Context Model；
- `evidence-index.json`：概念到具体 snapshot/action/observation/trace 文件的引用索引；
- `quality-report.json`：输入文件数、页面数、实体数、operation 数、API 引用数、跳过/无法解析素材、数据丢失和模型错误。

如果 ContextModelGenerator 已定义固定 schema 或文件名，优先遵循模板 schema，同时把等价结果写入上述 `C:\Users\bulin\appweave\outputs\02-context-model\browser-use-contextmodel` 目录。不得修改或覆盖原始 trace。

## 质量检查

完成前必须检查：

1. 所有 JSON 文件都能解析；
2. 每个 operation 都关联一个已有实体；
3. 每个引用都能定位到本次 trace 的真实素材；
4. `api_refs` 没有任何猜测性引用；
5. 未执行动作没有被写成已执行事实；
6. 记录 trace 中的 `dataLossOccurred`、模型超时、输出截断、JSON 格式错误、页面读取失败等问题；
7. 逐页处理完成后汇报总页数、成功页数、跳过页数、实体数、operation 数、API 引用数和剩余缺口。

全部完成后，告诉我已经完成，并列出 `C:\Users\bulin\appweave\outputs\02-context-model\browser-use-contextmodel` 下实际生成的文件。



