# 任务：browser-use shopping trace 实体抽取（entity-extract）

请读取本次 browser-use 运行导出的 trace 素材，逐页目录读取 `inputs/` 下的全部材料，生成每页的 `output/concepts.json`。页面清单以本任务目录中的 `INDEX.json` 为准；不要跳过已有素材的页面。全部页完成后再汇总检查，并告诉我完成情况。

## 工作方式

1. 读取 `INDEX.json`，把每个页面目录作为任务清单。
2. 对每个页面目录读取 `inputs/` 下全部文件，再写 `output/concepts.json`。
3. 扫描 `*/output/concepts.json` 做进度自查；文件存在且 JSON 合法才算该页完成。
4. 某页素材不足或解析失败时，跳过该页并在该页 `notes` 中说明原因，不要卡死整个任务。

## browser-use 素材

优先读取页面目录中实际存在的文件，常见文件包括：

- `page.json` 或 `metadata.json`：URL、标题、路由、时间和页面身份；
- `page.html`：页面可见文本、表单、按钮、表格、价格和商品字段；
- `accessibility.json`、AXTree 或 aria snapshot：角色、名称、列头、控件和导航结构；
- `endpoints.jsonl`、network 或 trace 摘要（如果存在）：接口、请求方法、响应字段和数据结构；
- 截图只用于辅助确认页面状态，不能单独作为 API 引用来源。

browser-use trace 可能没有织语的 `endpoints.jsonl`。没有接口证据时，`api_refs` 必须写空数组 `[]`；不要根据 URL、HTML 或常识臆造 API 编号。

## 抽取两类概念

两类概念互斥，导航栏、菜单、布局控件本身不要输出为概念：

1. `business_entity`：有稳定业务身份、可持久化或可反复展示的对象，例如商品、商品分类、购物车、购物车条目、订单摘要、搜索结果。
2. `operation`：针对实体的原子动作，例如商品-查看、商品-搜索、商品-筛选、商品-排序、购物车-查看、购物车-修改数量、购物车-删除条目、结算-开始。

实体尽量列出页面或接口证据中出现的字段，例如商品名称、SKU、价格、库存状态、分类、数量、小计；不得抄录具体数据行的值。

每个 operation 必须关联实体：优先写 `belongs_to_entity`，值为该页或跨页最终采用的实体 `canonical_name`；也可以使用“实体名-动词”的 canonical_name。实体有 GET 或页面加载证据时，至少考虑产出一个“X-查询”或“X-查看” operation。没有合理所属实体的动作不要输出。

## 引用规则

- `evidence_refs`：只引用本页实际存在的证据标识、文件路径或 DOM/AXTree 锚点。
- `api_refs`：只引用本页素材中明确存在的 API/endpoint 标识；没有明确 API 证据就写 `[]`。页面加载也只有在存在接口证据时才能算 API 来源。
- `page_refs`：仅用于 `business_entity`，写本页目录名；operation 不需要此字段。
- 禁止跨页发明引用，禁止把商品实际名称、价格或 SKU 的值当作字段名或引用。

## 输出格式

每页写 `output/concepts.json`：

```json
{
  "concepts": [
    {
      "canonical_name": "商品",
      "concept_type": "business_entity",
      "description": "可在商品列表和详情页中展示的商品对象",
      "aliases": [],
      "attributes": [
        {"name": "name", "note": "商品名称", "source_refs": ["page.html"]},
        {"name": "price", "note": "商品价格", "source_refs": ["page.html"]}
      ],
      "evidence_refs": ["page.html"],
      "api_refs": [],
      "page_refs": ["页面目录名"]
    },
    {
      "canonical_name": "商品-查看",
      "concept_type": "operation",
      "description": "打开商品详情并查看商品信息",
      "belongs_to_entity": "商品",
      "evidence_refs": ["page.html"],
      "api_refs": []
    }
  ],
  "notes": []
}
```

输出前检查：JSON 合法；`concept_type` 只能是 `business_entity` 或 `operation`；每个 operation 都能关联实体；每个字段和引用都能在本页素材中找到；没有接口证据时不得填写 `api_refs`。

## 完成汇报

全部页面处理后，汇报页面总数、成功写入的 `concepts.json` 数量、跳过页面及原因，并指出哪些 browser-use trace 页面因缺少 endpoint/API 素材而只能依据 HTML/可访问性树抽取。
