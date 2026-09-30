import pathlib,json,sys
from audit_traces import read,write,visible_nodes,classify,matches
O=pathlib.Path(__file__).resolve().parent
r=read(O/'common-registry.draft.json');facts=[];excluded=[]
for f in r['facts']:
 id=f['id']
 if id=='cart_item' or id.startswith('cart_item.') or id in ['cart.item_count','cart.subtotal','cart.grand_total','cart.coupon_code','cart.shipping_amount','cart.update','cart.remove','cart_contains_item','cart_item_refers_product','cart.nonempty_header','cart.nonempty_page','product.required_option_error']:
  excluded.append(dict(id=id,reason='User chose fresh-guest read-only scope; nonempty cart and write-dependent results excluded. Historical occurrences may be retained as extras.'));continue
 if id=='product.batteries':f['clauses']=[dict(name_regex=r'^Batteries[\s\u200f]*$',roles=['rowheader'])]
 if id=='search.results_empty':f['clauses']=[dict(name_regex='^Your search returned no results\\.$',roles=['StaticText'])]
 if id=='category.subcategories':f['clauses'][0]['name_regex']=r'^(?!\$).+\(\s*\d+\s*item\s*\)'
 f['provenance']='Candidate defined before independent site verification; historical trace informed product-field vocabulary. Not blind.';facts.append(f)
for id,clauses in [('catalog.filtered_result',[{'name_regex':'^Now Shopping by$','roles':['heading']}]),('catalog.sorted_result',[{'name_regex':'^Sort By$','roles':['combobox'],'value_equals':'Price'}]),('catalog.next_page',[{'name_regex':r'Items 13-24 of','roles':['heading']}])]:facts.append(dict(id=id,kind='business_state',page_types=['category_list'],clauses=clauses,db_mapping=None,precondition='guest; read-only GET allowed',note='Observed result state; no claim that historical agent executed a specific action.'))
for type in ['home','category_list','product_detail','advanced_search','search_results','cart']:facts.append(dict(id='page.'+type,kind='page_type',page_types=[type],clauses=[dict(name_regex='.+',roles=['RootWebArea'])],db_mapping=None,precondition='guest; read-only',note='URL/body-class classifier plus observed rendered page.'))
pages=[]
for root in [O/'site-verification',O/'site-verification-extra']:
 for d in sorted(root.iterdir()):
  if not d.is_dir():continue
  m=read(d/'metadata.json');p=d/'accessibility.json';pages.append(dict(url=m['url'],type=classify(m['url'],(d/'page.html').read_text(encoding='utf-8')),nodes=visible_nodes(read(p)),ax_file=str(p),directory=str(d)))
missing=[]
for f in facts:
 hits=[(p,matches(p,f)) for p in pages];hits=[(p,refs) for p,refs in hits if refs]
 if not hits:missing.append(f['id']);continue
 p,refs=hits[0];f['independent_site_verification']='rendered_UI_witness_verified';f['evidence_refs']=refs;f['verification_url']=p['url'];f['verification_metadata']=str(pathlib.Path(p['directory'])/'metadata.json')
 print(f['id'],[x['quote'] for x in refs])
print('MISSING',missing)
write(O/'common-readonly.v1.draft.json',dict(status='ready_for_review_before_freeze' if not missing else 'incomplete',scope='Explicit core vocabulary; fresh guest; read-only catalog/search/empty cart. Not exhaustive site or DB schema.',user_decision='2026-09-29: 本轮只评只读可达状态，不加购或修改购物车',facts=facts,excluded=excluded,unverified=missing,db_reference=r['db_reference'],limitations=['Candidate vocabulary was informed by historical trace; independent verification is fresh evidence, not blind annotation.','DB mapping is a reference schema/code mapping, not verified row-level provenance. UI-derived attributes are separately labeled.','G is the explicit core contract; unselected DB candidates remain outside this version, not declared invisible.','Read-only search is allowed in reference verification but was forbidden in browser-use historical prompt; no causal strategy ranking.']))
