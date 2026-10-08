"""Build auditable mappings, keeping description subfields separate from physical attributes."""
import collections,hashlib,html,json,pathlib,re,unicodedata
from html.parser import HTMLParser
from urllib.parse import urlsplit
O=pathlib.Path(__file__).resolve().parent;B=O.parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def norm(s):return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',html.unescape(str(s))).replace('\u200f','')).strip().casefold()
class Text(HTMLParser):
 def __init__(self,s):super().__init__();self.parts=[];self.feed(s)
 def handle_data(self,s):self.parts.append(s)
def plain(s):return norm(' '.join(Text(s).parts))
def main():
 export=read(O/'db-export.v2.json');d=export['data'];gold=read(B/'coverage-v3/gold.v1.json');rows=[]
 urls={u['request_path']:(u['entity_type'],u['entity_id']) for u in d['urls']}
 eavs={(r['entity_type_code'],r['attribute_code']):(i,r) for i,r in enumerate(d['eav'])}
 direct={'product.name':('product_varchar','name','catalog_product_entity_varchar.value'),'product.sku':('products','sku','catalog_product_entity.sku'),'product.price':('product_decimal','price','catalog_product_entity_decimal.value'),'category.name':('category_varchar','name','catalog_category_entity_varchar.value')}
 for f in gold['facts']:
  witness=f['reference_witness'];url=witness['url'];identity=urls.get(urlsplit(url).path.lstrip('/'));quotes=[r['quote'] for r in witness['evidence_refs']];mapping={'fact_id':f['id'],'kind':f['kind'],'ui_witness':witness,'status':'UI_derived_or_unverified','physical_key':None,'db_refs':[]}
  if f['id'] in direct and identity:
   group,code,col=direct[f['id']]
   for i,r in enumerate(d[group]):
    value=r.get(code) if group=='products' else r.get('value')
    if r.get('entity_id')!=identity[1] or (group!='products' and r['attribute_code']!=code):continue
    def agrees(q):
     if code=='price':
      try:return float(str(q).replace('$','').replace(',',''))==float(value)
      except ValueError:return False
     return norm(value) in norm(q) and bool(norm(value))
    if any(agrees(q) for q in quotes):mapping.update(status='matched_public_record_value',physical_key=identity[0]+'.'+code,storage=col);mapping['db_refs'].append({'pointer':f'/data/{group}/{i}','value':r})
  if f['id']=='product.availability' and identity:
   for i,r in enumerate(d['stock']):
    if r['product_id']==identity[1] and int(r['is_in_stock'])==1 and any(norm(q)=='in stock' for q in quotes):mapping.update(status='matched_public_record_value',physical_key='stock.is_in_stock',storage='cataloginventory_stock_item.is_in_stock');mapping['db_refs'].append({'pointer':f'/data/stock/{i}','value':r})
  if f['kind']=='attribute' and identity and identity[0]=='product' and mapping['physical_key'] is None:
   for i,r in enumerate(d['product_text']):
    if r['entity_id']!=identity[1] or r['attribute_code']!='description':continue
    text=plain(r['value']);content=[q for q in quotes if str(q).strip() and norm(q) not in ['details','image']]
    # Both label and value required where available. The contract's description is content-only.
    matched=bool(content) and all(norm(q) in text for q in content)
    if matched:mapping.update(status='matched_embedded_description',physical_key='product.description',storage='catalog_product_entity_text.value / description',note='UI semantic subfield of one HTML description, not a separate DB attribute');mapping['db_refs'].append({'pointer':f'/data/product_text/{i}','entity_id':r['entity_id'],'store_id':r['store_id'],'matched_quotes':content})
  rows.append(mapping)
 candidates=[]
 for i,r in enumerate(d['eav']):
  ent=r['entity_type_code'];code=r['attribute_code'];key=('product' if ent=='catalog_product' else 'category')+'.'+code
  facts=[x['fact_id'] for x in rows if x['physical_key']==key]
  admin=code.startswith(('meta_','custom_','use_config_')) or code in ['page_layout','display_mode','is_anchor','cost','status','visibility','created_at','updated_at']
  candidates.append({'entity':ent,'attribute':code,'db_pointer':f'/data/eav/{i}','metadata':r,'disposition':'verified_UI_mapping' if facts else 'excluded_frontend_readonly_scope' if admin else 'pending_UI_verification','fact_ids':facts,'reason':'Has same-record rendered witness' if facts else 'Admin/configuration or audit field; presence cannot be inferred from storefront absence' if admin else 'DB metadata exists; UI reachability/value witness not established; do not count as invisible'})
 result={'source_export':'db-export.v2.json','source_sha256':hashlib.sha256((O/'db-export.v2.json').read_bytes()).hexdigest(),'scope':'Front-end read-only public catalog and empty cart; no customer/order/cart record export','facts':rows,'eav_candidates':candidates,'limitations':['DB sampled 2026-09-30; UI witnesses captured earlier. Matching values support mapping, not complete historical DB snapshot identity.','No attribute-id or backend-table assumptions turn into proven application dataflow.','Unverified UI-derived quantities remain separate; no claim of complete DB-denominator coverage.']}
 write(O/'db-ui-mapping.v1.json',result)
 old=read(B/'coverage-v3/results.v1.json');scores={}
 verified={r['fact_id']:r['physical_key'] for r in rows if r['physical_key']};denom=set(verified.values())
 for run,result in old['results'].items():
  hits={verified[f['id']] for f in result['facts'] if f['supported'] and f['id'] in verified};scores[run]={'matched_distinct_DB_keys':sorted(hits),'denominator_keys':sorted(denom),'hits':len(hits),'denominator':len(denom),'warning':'Only the verified mapped subset; not complete DB coverage. Many UI fields collapse to description.'}
 write(O/'mapped-subset-diagnostic.v1.json',scores)
 print(json.dumps({'mapping_status':dict(collections.Counter(r['status'] for r in rows)),'candidate_status':dict(collections.Counter(r['disposition'] for r in candidates)),'mapped_subset':scores},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
