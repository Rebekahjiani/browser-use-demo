"""Provisional, scoped scorer for the already generated drive/browser-use CMs."""
import json, subprocess
import sys
from pathlib import Path
B=Path(__file__).parent
DRIVE=B/'reports'/'drive-context-model.json'
BU=Path(r'C:\Users\bulin\artifacttrace\templates\at-template\tasks\09-21-bu-shopping\outputs\context-model.json')
# Retrospective checklist based on the already-seen outputs. Diagnostic only; not an unbiased frozen oracle.
REF={
 'product':{'names':['产品','商品','Product'],'attrs':{'name':['name','商品名称','Product Name'],'sku':['sku','SKU'],'price':['price','价格','Price'],'image':['image','商品图片'],'quantity_and_stock_status':['availability','In stock（库存状态）','In stock (库存状态)','库存状态']}},
 'category':{'names':['商品分类','分类','Category'],'attrs':{'name':['name','分类名称','Category Name']}},
 'cart':{'names':['购物车','Cart'],'attrs':{'items_count':['itemCount','item_count','数量'],'subtotal':['subtotal','Subtotal','小计'],'grand_total':['grand_total','Grand Total','Order Total','总计']}},
 'cart_item':{'names':['购物车条目','购物车商品','Cart Item'],'attrs':{'name':['name','Item','商品名称'],'sku':['sku','SKU'],'qty':['qty','Qty','数量'],'price':['price','Price','价格'],'row_total':['row_total','Subtotal','小计']}}
}
def norm(s):return ''.join(c.lower() for c in str(s) if c.isalnum())
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def concepts_drive():
    raw=read(DRIVE); return [c for c in raw['concepts'] if c.get('concept_type')=='business_entity']
def concepts_bu():
    raw=read(BU); out=[]
    for e in raw.get('entities',[]):
        out.append({'canonical_name':e.get('name',''),'aliases':e.get('aliases',[]),'concept_type':'business_entity','attributes':e.get('attributes',[])})
    return out
def actual_map(cs):
    out={k:{'names':set(),'attrs':set(),'variants':[]} for k in REF}
    idx={norm(n):k for k,v in REF.items() for n in v['names']}
    for c in cs:
        labels=[c.get('canonical_name',c.get('name',''))]+c.get('aliases',[])
        key=next((idx[norm(x)] for x in labels if norm(x) in idx),None)
        if key is None:continue
        out[key]['names'].update(labels)
        for a in c.get('attributes',[]):
            val=a.get('name','') if isinstance(a,dict) else str(a)
            out[key]['attrs'].add(norm(val)); out[key]['variants'].append(val)
    return out
def score(label,cs,meta):
    actual=actual_map(cs); rows=[]; total=hits=entity_hits=0
    for key,ref in REF.items():
        present=bool(actual[key]['names']); entity_hits+=present
        miss=[]; hit=[]
        for code,aliases in ref['attrs'].items():
            total+=1; acceptable={norm(code),*(norm(a) for a in aliases)}
            found=bool(acceptable & actual[key]['attrs'])
            hits+=found
            (hit if found else miss).append(code)
        rows.append({'entity':key,'entity_found':present,'attributes_hit':hit,'attributes_missed':miss,'attr_recall':round(len(hit)/len(ref['attrs']),4)})
    return {'strategy':label,'source_meta':meta,'entity_recall':round(entity_hits/len(REF),4),'entity_hits':entity_hits,'entity_total':len(REF),'attribute_recall_micro':round(hits/total,4),'attribute_hits':hits,'attribute_total':total,'per_entity':rows,'scope_note':'Recall only. Reference is a small, manually mapped trace-demonstrated subset; precision and site-wide completeness are not measured.'}
def main():
    dmeta=read(DRIVE).get('meta',{})
    bq=read(BU.parent/'quality-report.json')
    drive=score('drive',concepts_drive(),{'merged_entities':dmeta.get('merged_business_entity'),'source_pages':dmeta.get('files'),'source':str(DRIVE)})
    bu=score('browser-use',concepts_bu(),{'entities':bq.get('summary',{}).get('entities_count'),'operations':bq.get('summary',{}).get('operations_count'),'snapshot_dirs_processed':bq.get('summary',{}).get('snapshot_dirs_processed'),'accessibility_json_read':bq.get('inputs',{}).get('accessibility_json_read'),'source':str(BU)})
    report={'title':'Existing CM retrospective diagnostic (not a benchmark result)','reference':REF,'reference_bias':'This 14-item checklist was authored after inspecting both generated Context Models and their traces. It overlaps observed outputs by construction and must not be used to claim either strategy is superior. Freeze an independently authored oracle before formal scoring.','results':[drive,bu],'comparability':{'model':'DeepSeek-V4-Flash-0731 confirmed in browser-use AT run trace; drive AT run not located in saved task history. Eval plan says drive extraction used same model, so treat as provisionally reported, not independently verified.','prompt':'Different task text. Drive used page-wise entity-extract TASK.md; browser-use received a broad custom Context Model prompt naming the target concepts.','inputs':'Drive extraction had 26 page packages with endpoint summaries and ARIA; browser AT report says it read AX for 5 page groups, plus selective network evidence. Not same evidence volume/type.','claim':'Scores describe these two end-to-end historical runs only; they do not isolate the crawler algorithm.'}}
    p=B/'reports'/'existing-cm-provisional.json';p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    md=['# 两次既有 Context Model 回溯诊断（非正式评分）','','输出文件：`existing-cm-provisional.json`。下面数字只展示当前合并器和名称映射能否运行。14项检查表是在查看两边输出后才整理的，存在明显的事后选择偏差；不能用来判断哪种策略更好。实体范围为商品、商品分类、购物车、购物车条目；不代表全站真值，也不评精确率。正式评分必须先独立冻结参考答案。','','|策略|实体命中|字段命中|相对当前清单召回¹|','|---|---:|---:|---:|']
    for x in (drive,bu):md.append(f"|{x['strategy']}|{x['entity_hits']}/{x['entity_total']}|{x['attribute_hits']}/{x['attribute_total']}|{x['attribute_recall_micro']:.1%}|")
    for x in (drive,bu):
        md+=['',f"## {x['strategy']}",'']
        for r in x['per_entity']:md.append(f"- {r['entity']}: {'实体已提取' if r['entity_found'] else '实体遗漏'}；字段命中 {', '.join(r['attributes_hit']) or '无'}；遗漏 {', '.join(r['attributes_missed']) or '无'}。")
    md+=['','¹ 召回以回溯整理的14项清单为分母，因事后选择偏差仅供调试查看。','','## 可比性限制','','- browser-use 的 AT 运行 trace 明确记录模型 `sophnet/DeepSeek-V4-Flash-0731`；织语评测计划记载使用同一模型，但对应成功运行记录尚未定位。','- 提示词不同：织语使用逐页 `entity-extract/TASK.md`；browser-use 使用专门编写的总任务，直接点名商品、分类、购物车等目标概念。','- 输入准备不同：织语抽取包有26页并附 endpoints 摘要；browser-use最终总结称处理26个 snapshot 目录，但只读取了5个代表页面的 accessibility JSON，并使用部分网络证据。','- 所以当前数字混合了采集、备料、提示词和阿器提取的影响，不能将差异单独归因于采集策略。','- 当前不评 precision、操作和关系，也不声称结果完整。','- 两份 trace 都有 `dataLossOccurred=true` 标记。','','## 解释','','browser-use 在这个事后清单上命中更多项，但这不是可信的胜负结论。可确认的是：两份结果文件结构已统一读取、跨格式归并和全局召回分母的计算流程可以运行。正式结论需先冻结独立答案，再用同一提示词和备料方式评分。']
    (B/'reports'/'existing-cm-provisional.md').write_text('\n'.join(md),encoding='utf-8')
    print('\n'.join(md[:10]))
if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    main()

