import json, pathlib, hashlib, re, copy
B=pathlib.Path(r'C:\Users\bulin\browser-use-demo\benchmark'); O=B/'extraction'; G=O/'ground-truth'
if (O/'freeze.v1.json').exists(): raise RuntimeError('Frozen v1 exists. Do not regenerate; create a new annotation version.')
D=pathlib.Path(r'C:\Users\bulin\appweave\outputs\01-evidence\26_09_28_10_40_34-min'); U=B/'outputs/20260929-115141-231052'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,x): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def ref(p,ptr,q):return dict(file=str(p.resolve()),pointer=ptr,quote=q)
def dr(page,pattern):
 pages=[B/f'eval-v1/packages/drive/{page}/inputs/ui.json'] if page!='*' else sorted((B/'eval-v1/packages/drive').glob('*/inputs/ui.json'))
 for p in pages:
  for i,x in enumerate(read(p)):
   if re.search(pattern,x['text'],re.I):return ref(p,f'/{i}/text',x['text'])
 raise ValueError((page,pattern))
def bu(page,pattern,role=None):
 p=U/f'snapshots/{page}/accessibility.json'
 for i,n in enumerate(read(p)['nodes']):
  s=n.get('name',{}).get('value','')
  if not n.get('ignored') and (not role or n.get('role',{}).get('value')==role) and re.search(pattern,s,re.I):return ref(p,f'/nodes/{i}/name/value',s)
 raise ValueError((page,pattern,role))
d=read(G/'drive-trace.draft-preserved.json')
patterns={'name':('002','heading.*Belle'),'sku':('002','strong.*SKU'),'asin':('002','rowheader.*ASIN'),'price':('002',r'generic.*\$23.50'),'rating':('002','generic.*Rating:'),'review_count':('002','link.*12 Reviews'),'availability':('002','Availability.*In stock'),'image':('002','img "Image"'),'size':('002','Size \\*'),'quantity':('002','spinbutton.*Qty'),'description':('002','heading.*Product Description'),'dimensions':('002','rowheader.*Product Dimensions'),'upc':('002','rowheader.*UPC'),'manufacturer':('002','rowheader.*Manufacturer'),'country_of_origin':('002','rowheader.*Country of Origin'),'package_dimensions':('*','rowheader.*Package Dimensions'),'item_weight':('*','rowheader.*Item Weight'),'model_number':('*','rowheader.*Item model number'),'date_first_available':('*','rowheader.*Date First Available'),'color':('008','Color \\*'),'style':('012','Style \\*'),'batteries':('*','rowheader "Batteries'),'discontinued_status':('*','rowheader.*Is Discontinued By Manufacturer'),'domestic_shipping':('*','rowheader.*Domestic Shipping'),'international_shipping':('*','rowheader.*International Shipping'),'department':('*','rowheader.*Department')}
for a in d['attributes']:
 if a['entity']=='product':a['evidence_refs']=[dr(*patterns[a['id']])]
 else:
  p={'category.name':('001','heading.*Beauty'),'category.item_count':('001','paragraph.*Items 1-12'),'category.subcategories':('001','heading "Category"'),'category.price_range':('001','heading "Price"'),'cart.item_count':('000','link.*My Cart 3')}[a['entity']+'.'+a['id']];a['evidence_refs']=[dr(*p)]
for e in d['entities']:
 e['aliases']=[a for a in e['aliases'] if a not in ['价格区间','Price Range','价格筛选']]
 e['evidence_refs']=[dr(*{'product':('002','heading.*Belle'),'category':('001','heading.*Beauty'),'cart':('000','link.*My Cart 3')}[e['id']])]
ops={'product_navigation':('002','heading.*Belle'),'search':('004','button "Search"'),'filter':('001','heading "Category"'),'sort':('001','combobox "Sort By"'),'paginate':('001','link.*Page Next'),'add_to_cart':('002','button "Add to Cart"'),'cart_view':('000','link.*My Cart 3')}
for a in d['operations']:
 a['evidence_refs']=[dr(*ops[a['id']])];a['executed']=None;a['execution_status']='not_adjudicated_from_action_log';a['visibility']='visible_control' if a['id']!='product_navigation' else 'observed_page'
 if a['id']=='cart_view':a['aliases']=[x for x in a['aliases'] if x!='购物车-查询']
d['relations'][0]['evidence_refs']=[dr('001','heading.*Beauty'),dr('001','link.*JSY Foldable')]
# Search fields establish exposed schema only; do not claim populated values.
d['attributes'].append(dict(entity='product',id='short_description',aliases=['Short Description','shortDescription'],evidence_refs=[dr('004','textbox "Short Description"')],support_kind='search_form_field_only'))
u=copy.deepcopy(d);u['meta']['id']='shopping-browser-use-20260929-v1';u['meta']['trace']=str(U);u['meta']['cart_state']='Guest empty cart only; no cart lines, quantity, subtotal or total.'
bp={'name':('00005','^Greens Egg','heading'),'sku':('00005','^SKU$','StaticText'),'asin':('00005','^ASIN','rowheader'),'price':('00005',r'^\$31.99$','StaticText'),'rating':('00002','^Rating:$','StaticText'),'review_count':('00002','5.*Reviews','link'),'availability':('00005','^IN STOCK$','StaticText'),'image':('00005','^Image$','image'),'size':('00005','^Size$','StaticText'),'quantity':('00005','^Qty$','spinbutton'),'description':('00005','Loved by many','StaticText'),'manufacturer':('00005','^Manufacturer','rowheader'),'country_of_origin':('00005','^Country of Origin','rowheader'),'short_description':('00007','^Short Description$','textbox')}
u['attributes']=[]
for a in d['attributes']:
 if a['entity']=='product' and a['id'] in bp:
  a=copy.deepcopy(a);a['evidence_refs']=[bu(*bp[a['id']])];u['attributes'].append(a)
for ident,args in {'name':('00002','^Grocery.*Items','heading'),'item_count':('00002','^Grocery.*Items','heading'),'subcategories':('00002','Food & Beverage Gifts','link'),'price_range':('00002',r'\$0.00.*999.99','link')}.items():
 a=copy.deepcopy(next(x for x in d['attributes'] if x['entity']=='category' and x['id']==ident));a['evidence_refs']=[bu(*args)];u['attributes'].append(a)
u['attributes'].append(dict(entity='cart',id='empty_state',aliases=['购物车空状态（cart-empty）','cart-empty','empty'],evidence_refs=[bu('00011','You have no items','StaticText')]))
for e in u['entities']:e['evidence_refs']=[bu(*{'product':('00005','^Greens Egg','heading'),'category':('00002','^Grocery.*Items','heading'),'cart':('00011','^Shopping Cart$','heading')}[e['id']])]
bops={'product_navigation':('00005','^Greens Egg','heading'),'search':('00007','^Search$','button'),'filter':('00002','^Category$','heading'),'sort':('00002','^Sort By$','combobox'),'paginate':('00002','Next','link'),'add_to_cart':('00005','^Add to Cart$','button'),'cart_view':('00011','^Shopping Cart$','heading')}
for a in u['operations']:
 a['evidence_refs']=[bu(*bops[a['id']])];a['executed']=a['id'] in ['product_navigation','cart_view'];a['execution_status']='observed_destination_page' if a['executed'] else 'not_executed_in_recorded_run'
u['relations'][0]['evidence_refs']=[bu('00002','^Grocery.*Items','heading'),bu('00002','^Greens Egg','link')]
extra={'availability':['In stock（库存状态）'],'quantity':['Qty（数量输入）'],'subcategories':['子分类（Shop By Category）'],'price_range':['Price（Shop By Price 区间）'],'item_count':['商品计数（items）'],'model_number':['item_model_number'],'discontinued_status':['is_discontinued_by_manufacturer']}
dbpath=pathlib.Path(r'C:\Users\bulin\.crabvisor_data\sandboxes\sb_d5c9d813\workspace\appweave\eval\ground-truth\shopping.expected-cm.json');db=read(dbpath)
for gold in [d,u]:
 gold['meta']['annotation_basis']='Post-hoc core-field annotation reviewed against UI evidence; not blind, exhaustive or a strategy/harness ranking.'
 gold['meta']['scope_policy']='Closed core vocabulary: only listed entities, attributes, operations and relations have recall denominators. Unmapped assertions require adjudication and are excluded from resolved precision; report precision bounds. No site-wide completeness claim.'
 gold['meta']['db_reference']=str(dbpath)
 for a in gold['attributes']:
  a['aliases']+=extra.get(a['id'],[])
  ent={'product':'catalog_product','category':'catalog_category','cart':'quote'}[a['entity']]
  codes={x['code'] for x in db['entities'].get(ent,{}).get('attributes',[]) if 'code' in x}
  a['db_mapping']={'entity':ent,'field':a['id'] if a['id'] in codes else None,'status':'reference_catalog_match_only' if a['id'] in codes else 'derived_or_unverified_no_exact_mapping'}
  a.setdefault('support_kind','visible_UI_field_or_value')
 write(G/('drive-trace.v1.json' if gold is d else 'browser-use-20260929.v1.json'),gold)
print('built',len(d['attributes']),len(u['attributes']))
