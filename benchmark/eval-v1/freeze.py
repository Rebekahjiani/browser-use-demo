"""Freeze a conservative, evidence-backed minimum reference, not site completeness."""
from prepare import ROOT, read, write, BU
import hashlib
BASE=__import__('pathlib').Path(r'C:\Users\bulin\.crabos_data\file\workspace\default\eval')
def main():
    schema=read(BASE/'entity-extract-schema.json')
    concept=schema['definitions']['concept']
    concept['properties']['observation_level']={'enum':['visible_control']}
    concept['required'] += ['evidence_refs','api_refs']
    concept['allOf']=[{'if':{'properties':{'concept_type':{'const':'operation'}}},'then':{'required':['belongs_to_entity','observation_level']}},{'if':{'properties':{'concept_type':{'const':'business_entity'}}},'then':{'required':['attributes','page_refs']}}]
    schema['properties']['relations']={'type':'array','items':{'type':'object','required':['source_entity','predicate','target_entity','evidence_refs'],'properties':{k:{'type':'string'} for k in ['source_entity','predicate','target_entity']}|{'evidence_refs':{'type':'array','minItems':1,'items':{'type':'string'}}},'additionalProperties':False}}
    schema['required']=['concepts','relations','notes']
    write(ROOT/'schema.json',schema)
    pages=[]
    for d in sorted((BU/'snapshots').iterdir()):
        p=d/'accessibility.json'
        if p.exists(): pages.append((d,read(d/'metadata.json')['url'],read(p)['nodes']))
    def evidence(route,label):
        for d,url,nodes in pages:
            if route not in url: continue
            for n in nodes:
                name=str(n.get('name',{}).get('value',''))
                if not n.get('ignored') and label.lower() in name.lower():
                    return {'file':str(d/'accessibility.json'),'node_id':n['nodeId'],'label':name,'url':url,'precondition':'本次已捕获页面状态；购物车为非空','verification':'snapshot_verified'}
        raise ValueError((route,label))
    specs=[('product','商品',['catalog_product','产品','Product'],'.html',[('sku','SKU','catalog_product.sku'),('price','Price','catalog_product.price'),('availability','In stock','cataloginventory_stock_item.is_in_stock')]),('cart','购物车',['quote','Shopping Cart'],'/checkout/cart/',[('subtotal','Subtotal','quote.subtotal'),('grand_total','Order Total','quote.grand_total')]),('cart_item','购物车条目',['quote_item','购物车项','Cart Item'],'/checkout/cart/',[('qty','Qty','quote_item.qty'),('price','Price','quote_item.price'),('row_total','Subtotal','quote_item.row_total')])]
    entities=[]
    for eid,name,aliases,route,attrs in specs:
        aa=[]
        for code,label,db in attrs:
            aa.append({'name':code,'aliases':[label,{'sku':'商品编号','price':'价格','availability':'库存状态','subtotal':'小计','grand_total':'总计','qty':'数量','row_total':'行小计'}[code]],'db_mapping':db,'visibility':evidence(route,label)})
        entities.append({'id':eid,'name':name,'aliases':aliases,'attributes':aa,'scope':'minimum_confirmed_core'})
    ops=[]
    for eid,name,route,label in [('product','搜索','/catalogsearch/advanced/','Search'),('product','排序','beauty-personal-care.html','Sort By'),('product','翻页','beauty-personal-care.html','Next'),('cart_item','编辑','/checkout/cart/','Edit'),('cart_item','删除','/checkout/cart/','Remove item'),('cart','更新','/checkout/cart/','Update Shopping Cart')]:
        ops.append({'id':eid+'.'+name,'name':name,'belongs_to_entity':eid,'observation_level':'visible_control','visibility':evidence(route,label),'execution_verified':False})
    gt={'meta':{'version':'shopping-ui-core-v1','frozen':True,'freeze_date':'2026-09-29','scope':'商品、搜索筛选、购物车的已证实最小核心；不是三个模块全集','reference_selection':'既有 browser-use 快照辅助核验，存在选择偏差；只供试评，不足以给探索器正式排名','source_db_sha256':hashlib.sha256((BASE/'ground-truth'/'shopping.expected-cm.json').read_bytes()).hexdigest(),'exclude':['后台','订单支付','未知可见性字段','动作执行成功率','API覆盖率']},'entities':entities,'operations':ops,'relations':[{'source_entity':'cart','predicate':'contains','target_entity':'cart_item','visibility':evidence('/checkout/cart/','Qty')},{'source_entity':'cart_item','predicate':'references','target_entity':'product','visibility':evidence('/checkout/cart/','ZOSI')}],'pending':['分类名称/层级及商品分类关系需独立参考采集','搜索有/无结果、筛选后状态需独立验证','购物车空状态、数量修改/删除结果需独立验证','商品名称、描述、特殊价格等需字段级证据和映射补全']}
    write(ROOT/'ground-truth'/'shopping.ui-core.v1.json',gt)
    p=ROOT/'ground-truth'/'shopping.ui-core.v1.json'
    (p.parent/'SHA256.txt').write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name,encoding='utf-8')
if __name__=='__main__': main()
