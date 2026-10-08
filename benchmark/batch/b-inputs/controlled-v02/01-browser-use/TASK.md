# 任务：实体抽取（entity-extract）

你是企业业务语义建模助手。本目录（entity-extract/）下每个 `{seq}_{page_url_short}/` 子目录
是一个页面的全部证据。逐目录完成抽取。

## 工作方式
1. 读 INDEX.json 拿页面清单（这就是你的任务清单）
2. 对每个页目录：读 inputs/ 下全部材料 → 抽取 → 写 output/concepts.json
3. 进度自查：扫 `*/output/concepts.json`，存在且符合 schema.json 即该页完成
4. 某页失败/存疑 → 跳过并在该页 notes 里标注，不要卡死在一页上

## 输入（每个页目录的 inputs/，共 3 个文件）
- `page.json`         素材清单：页面身份（url/title/route）+ 素材来源路径（sources.*）
- `page.aria.yml` 或 `page.axtree.md`
                      页面结构树（表单 label / 表格列头 / 按钮 / 菜单，中文业务名）。
                      两种格式等价：page.aria.yml 是 playwright ariaSnapshot；
                      page.axtree.md 是 CDP AXTree 的确定性精简（role: name 缩进树）。
                      有哪个读哪个
- `endpoints.jsonl`   API 端点 + 响应结构摘要：每行含 digest（shape/record_keys/key_enums）
                      与 record_shape（字段名 → 类型指纹，如 `assetCode: string(12)`、
                      `useStatus: enum(已入库,领用中)`、`createTime: datetime`）

## 要做什么（每页）
识别两类概念（互斥；导航/菜单不是概念，不要输出）：
1. `business_entity` 有稳定业务身份、可持久化的对象（如"资产"），**必须尽量列 attributes**
2. `operation`       对实体的原子动作（动词性）。canonical_name 用"实体名-动词"约定
   （如"资产报废-提交"），或加 belongs_to_entity 字段写实体名；**实体有 API 证据
   （含 GET 数据加载）时至少产出一个"X-查询"类 operation**

## 关联引用规则（entity 与 operation 都要写 api_refs）
三类引用语义不同，别混：
- `evidence_refs` 概念**存在的依据**（可含树锚点，如 `["E001", "page.axtree.md:table:资产编码"]`）
- `api_refs` 数据/行为的**接口来源**：实体数据从哪个接口来、操作触发哪个接口
  （该页 endpoints.jsonl 里存在的 E###；GET 数据加载也算；字典/配置类接口不算数据来源，别写）
- `page_refs` 实体**呈现于哪些页**：entity 专写，值=**本页目录名**（如 `"001_ams_asset_storage_wm_to_manage"`）；
  operation 不需要（经宿主实体 + 接口所在页推导）

硬约束：只用本页存在的值，禁跨页引用、禁发明；页面看不出数据来源（纯静态展示/
纯树锚点）就留空 `[]`——宁缺勿错。

## attributes 规则
- 字段名只能来自 endpoints.jsonl 的 record_keys / record_shape 的字段、或页面树的列头/label，禁止发明
- 每个 attribute 带 source_refs（如 `["E001"]` 或 `["page.axtree.md:table:资产编码"]`）

## 硬约束
- 只依据各页目录内的证据；不引入百科知识；不编造引用
- 不得把任何数据行的值抄进输出（字段名/枚举/业务判断可以）
- evidence_refs 只用该页 inputs/endpoints.jsonl 里存在的 ref（E001 起）
- 无树的页照样抽取（只凭 endpoints）；无端点的页也照样（只凭树）

## 输出契约（每页）
写 `{page}/output/concepts.json`，**必须符合本目录 schema.json**：

```json
{
  "concepts": [
    {
      "canonical_name": "新购资产",
      "concept_type": "business_entity",
      "description": "…",
      "aliases": [],
      "attributes": [{"name": "assetCode", "note": "资产编码", "source_refs": ["E001"]}],
      "evidence_refs": ["E001"],
      "api_refs": ["E001"],
      "page_refs": ["000_ams_asset_storage_om_scrap_manage"]
    },
    {
      "canonical_name": "新购资产-提交",
      "concept_type": "operation",
      "description": "…",
      "belongs_to_entity": "新购资产",
      "evidence_refs": ["E002"],
      "api_refs": ["E002"]
    }
  ],
  "notes": []
}
```

**operation 必须关联实体**：每个 operation 用 `belongs_to_entity` 写所属实体的
canonical_name（推荐，明确无歧义）；或名字用"实体名-动词"约定。关联不上的动作
（找不到合理实体）不要输出为 operation。

写完自查：JSON 合法、schema 通过、引用存在、两类归类无误、每个 operation 都能对上实体。

## stage-2（本任务第二阶段，用户详细分析时才启用）
以上是 stage-1：只看少量脱敏材料，单次完成。若需深入（用户发起），
按该页 `stage2/index.json` 的指引多轮读取全量数据，产出写 `output/concepts.stage2.json`，
**不得覆盖 concepts.json**。详见 stage2/index.json 内的指南。

## 本轮材料边界
每个目录是一个独立页面状态，允许同URL多个状态。树由完整AX确定性转换，没有深度/数量/字段名截断。不打开网页，不回溯原始trace。API引用只用本页endpoints中实际存在的E编号；shape只证明响应结构，不证明实体数据归属；未知来源留空。不要读取评分gold或其他构建组合的输出。
