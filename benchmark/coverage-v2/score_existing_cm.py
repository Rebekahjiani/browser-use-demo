import json, re, datetime
from pathlib import Path

O = Path(__file__).resolve().parent
G = json.loads((O / "common-readonly.v2.json").read_text(encoding="utf-8"))
T = json.loads((O / "common-readonly-coverage.v2.json").read_text(encoding="utf-8"))

CM = {
    "drive": Path(r"C:\Users\bulin\browser-use-demo\benchmark\reports\drive-context-model.json"),
    "browser-use-20260929": Path(r"C:\Users\bulin\appweave\outputs\02-context-model\browser-use-contextmodel\context-model.json"),
}

def n(x): return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", str(x).casefold())

ENTITY = {n("商品"): "product", n("产品"): "product", n("商品分类"): "category", n("分类"): "category", n("购物车"): "cart"}
ATTR = {
    "name":"name", "商品名称":"name", "title":"name", "productname":"name",
    "sku":"sku", "asin":"asin", "price":"price", "价格":"price", "rating":"rating",
    "reviews":"review_count", "review_count":"review_count", "reviewcount":"review_count",
    "availability":"availability", "instock库存状态":"availability", "image":"image",
    "size":"size", "qty":"quantity", "quantity":"quantity", "数量输入":"quantity",
    "description":"description", "productdescription":"description", "shortdescription":"short_description",
    "manufacturer":"manufacturer", "countryoforigin":"country_of_origin", "dimensions":"dimensions",
    "productdimensions":"dimensions", "upc":"upc", "packagedimensions":"package_dimensions",
    "itemweight":"item_weight", "modelnumber":"model_number", "itemmodelnumber":"model_number",
    "datefirstavailable":"date_first_available", "color":"color", "style":"style", "batteries":"batteries",
    "isdiscontinuedbymanufacturer":"discontinued_status", "domesticshipping":"domestic_shipping",
    "internationalshipping":"international_shipping", "department":"department",
    "分类名称":"name", "itemcount":"item_count", "商品计数items":"item_count", "subcategories":"subcategories",
    "子分类shopbycategory":"subcategories", "range":"price_range", "pricefacet":"price_range",
    "price区间":"price_range", "购物车空状态cartempty":"empty_state",
}
OP = {"productnavigation":"product_navigation", "商品查看":"product_navigation", "产品查看":"product_navigation",
      "productquery":"product_navigation", "商品查询浏览列表":"product_navigation", "产品查询":"product_navigation",
      "商品搜索":"search.advanced", "产品搜索":"search.advanced", "search":"search.advanced", "商品筛选":"catalog.filter", "产品筛选":"catalog.filter",
      "商品排序":"catalog.sort", "产品排序":"catalog.sort", "商品分页浏览":"catalog.paginate", "产品分页":"catalog.paginate",
      "商品加入购物车":"cart.add", "产品加入购物车":"cart.add", "购物车查看":"cart.view"}

def candidate(cm):
    es, ats, ops = set(), set(), set()
    entities = cm.get("entities", []) + [x for x in cm.get("concepts", []) if x.get("concept_type") == "business_entity"]
    operations = cm.get("operations", []) + [x for x in cm.get("concepts", []) if x.get("concept_type") == "operation"]
    for e in entities:
        raw = e.get("canonical_name", e.get("name", "")); ent = ENTITY.get(n(raw))
        if not ent: continue
        es.add(ent)
        for a in e.get("attributes", []):
            raw_a = a.get("name", "")
            aid = ATTR.get(n(raw_a))
            if aid: ats.add(ent + "." + aid)
    for o in operations:
        raw = o.get("canonical_name", o.get("name", "")); oid = OP.get(n(raw))
        if oid: ops.add(oid)
    return {"entities":es, "attributes":ats, "operations":ops, "relations":set()}

def gold_sets():
    out = {k:set() for k in ["entities","attributes","operations","relations"]}
    for f in G["facts"]:
        if f["kind"] == "entity": out["entities"].add(f["id"])
        elif f["kind"] == "attribute": out["attributes"].add(f["id"])
        elif f["kind"] == "operation_control": out["operations"].add(f["id"])
        elif f["kind"] == "relation": out["relations"].add(f["id"])
    return out

def observed(run, fact_id):
    for f in T["results"][run]["facts"]:
        if f["id"] == fact_id: return bool(f["observed"])
    return False

def main():
    gs = gold_sets(); report = {"title":"Existing Context Models against common read-only G/T","generated_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"interpretation":"prompt-equivalent / trace-scoped diagnostic; not controlled A ranking","results":{}}
    for run,p in CM.items():
        c = candidate(json.loads(p.read_text(encoding="utf-8-sig"))); rows={}
        for kind in gs:
            g=gs[kind]; t={x for x in g if observed(run,x)}; cm=c[kind]; both=t&cm
            rows[kind]={"G":len(g),"T":len(t),"C":len(cm&g),"T_and_C":len(both),"exploration_G_recall":len(t)/len(g) if g else None,"trace_extraction_recall":len(both)/len(t) if t else None,"end_to_end_G_recall":len(both)/len(g) if g else None,"G_missing_from_T":sorted(g-t),"T_missing_from_C":sorted(t-cm),"C_without_G":sorted(cm-g)}
        report["results"][run]={"metrics":rows,"candidate_canonical":{k:sorted(v) for k,v in c.items()},"source":str(p)}
    (O/"existing-cm-common-g.v1.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=["# 现有 Context Model × 共同只读 G/T 诊断","", "现有两份 CM 可以直接用于该诊断。两套 prompt 任务语义相近，但输入预处理不同；结果不是严格控制变量的 Benchmark A 排名。", "", "| 运行 | 维度 | G | T | T∩C | G∩T/G | G∩T∩C/G∩T | G∩T∩C/G |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for run,r in report["results"].items():
        for k,v in r["metrics"].items(): lines.append(f"| {run} | {k} | {v['G']} | {v['T']} | {v['T_and_C']} | {v['exploration_G_recall']:.2%} | {v['trace_extraction_recall'] if v['trace_extraction_recall'] is not None else float('nan'):.2%} | {v['end_to_end_G_recall']:.2%} |")
    lines += ["", "## 解释", "", "- G 是冻结的共同只读核心契约；T 是该 run 的原始 UI 证据覆盖；C 是现有 Context Model 归一后的命中。", "- C 只在 G 内计入；额外断言列在 JSON 中，不自动判为错误。", "- 由于 Drive/browser-use 的输入材料和证据预处理不同，这份报告是现有运行的 prompt-equivalent / trace-scoped 诊断。", "- 两边原始 trace、购物车状态和采集完整性差异仍然保留。"]
    (O/"existing-cm-common-g.v1.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps(report["results"],ensure_ascii=False,indent=2))
if __name__ == "__main__": main()
