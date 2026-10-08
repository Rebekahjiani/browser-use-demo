"""Evidence-gated historical UI exploration benchmark, standard library only."""
import argparse,collections,copy,datetime,hashlib,json,pathlib,re
from urllib.parse import urlsplit,parse_qs
O=pathlib.Path(__file__).resolve().parent
OLD=O.parent/'coverage-v2'
ROOTS={'drive':pathlib.Path(r'C:\Users\bulin\appweave\outputs\01-evidence\26_09_28_10_40_34-min\drive\screenshots'), 'browser-use':O.parent/'outputs/20260929-115141-231052/snapshots'}
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def val(n,k):return n.get(k,{}).get('value','')
def prop(n,k):return next((p['value'].get('value') for p in n.get('properties',[]) if p['name']==k),None)

class Page:
 def __init__(self,path):
  self.path=path;self.raw=read(path);self.nodes=self.raw['nodes'];self.ids={n['nodeId']:n for n in self.nodes};self.indices={n['nodeId']:i for i,n in enumerate(self.nodes)}
  root=next(n for n in self.nodes if val(n,'role')=='RootWebArea');self.url=prop(root,'url');self.query=parse_qs(urlsplit(self.url).query)
  html=(path.parent/'page.html').read_text(encoding='utf-8-sig');body=re.search(r'<body\b[^>]*class=["\']([^"\']+)',html,re.I);classes=body.group(1).split() if body else []
  self.type=next((t for c,t in [('catalog-product-view','product_detail'),('catalog-category-view','category_list'),('catalogsearch-advanced-index','advanced_search'),('catalogsearch-result-index','search_results'),('checkout-cart-index','cart'),('cms-index-index','home')] if c in classes),'unknown')
 def visible(self,n):return not n.get('ignored',False)
 def find(self,regex,roles=None):return [n for n in self.nodes if self.visible(n) and (not roles or val(n,'role') in roles) and re.search(regex,str(val(n,'name')),re.I)]
 def descendants(self,n):
  todo=list(n.get('childIds',[]));seen=set();out=[]
  while todo:
   k=todo.pop()
   if k in seen:continue
   seen.add(k);c=self.ids.get(k)
   if c:out.append(c);todo.extend(c.get('childIds',[]))
  return out
 def parent(self,n):return self.ids.get(n.get('parentId'),{})
 def ref(self,n,field='name'):
  return {'file':str(self.path),'pointer':f"/nodes/{self.indices[n['nodeId']]}/{field}/value",'quote':val(n,field)}
 def refs(self,ns):return [self.ref(n) for n in ns]

def fullmatch(p,f):
 """Return precise evidence only when every additional semantic gate passes."""
 if f.get('page_types') and p.type not in f['page_types']:return []
 groups=[]
 for clause in f['clauses']:
  ns=p.find(clause['name_regex'],clause.get('roles'))
  if clause.get('value_equals') is not None:ns=[n for n in ns if val(n,'value')==clause['value_equals']]
  if not ns:return []
  groups.append(ns)
 ns=groups[0];rule=f['rule'];fid=f['id']
 if rule=='heading_identity':
  ns=[n for n in ns if prop(n,'level')==1]
  return p.refs(ns[:1])
 if rule=='cart_page':
  h=p.find(r'^Shopping Cart$',['heading']);empty=p.find(r'^You have no items in your shopping cart\.$',['StaticText'])
  return p.refs(h[:1]+empty[:1]) if h and empty else []
 if rule=='row_value_or_option':
  for n in ns:
   if val(n,'role')=='rowheader':
    parent=p.parent(n)
    cells=[c for c in p.descendants(parent) if p.visible(c) and val(c,'role')=='cell' and str(val(c,'name')).strip() and val(c,'name')!=val(n,'name')]
    if val(parent,'role')=='row' and cells:return p.refs([n,cells[0]])
   # Option must be in the label's local field container, not elsewhere on the page.
   parent=p.parent(p.parent(n))
   options=[c for c in p.descendants(parent) if p.visible(c) and val(c,'role') in ['radio','option','combobox'] and str(val(c,'name')).strip() and val(c,'name')!=val(n,'name')]
   if fid in ['product.size','product.color','product.style'] and options:return p.refs([n,options[0]])
  return []
 if rule=='sku_value':
  for n in ns:
   container=p.parent(p.parent(n));values=[c for c in p.descendants(container) if p.visible(c) and val(c,'role')=='StaticText' and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{2,}',str(val(c,'name'))) and val(c,'name')!='SKU']
   if values:return p.refs([n,values[0]])
  return []
 if rule=='rating_value':
  for n in ns:
   values=[c for c in p.descendants(p.parent(p.parent(n))) if p.visible(c) and re.fullmatch(r'\d+(?:\.\d+)?%',str(val(c,'name')))]
   if values:return p.refs([n,values[0]])
  return []
 if rule=='description_content':
  for n in ns:
   texts=[c for c in p.descendants(n) if p.visible(c) and val(c,'role')=='StaticText' and len(str(val(c,'name')).strip())>=30]
   if texts:return p.refs([n,texts[0]])
  return []
 if rule=='image_resource':
  for n in ns:
   url=prop(n,'url')
   if url and re.match(r'https?://',url):
    i=next(i for i,x in enumerate(n['properties']) if x['name']=='url');return p.refs([n])+[{'file':str(p.path),'pointer':f"/nodes/{p.indices[n['nodeId']]}/properties/{i}/value/value",'quote':url}]
  return []
 if rule=='filter_result':
  if not ({'cat','price'} & set(p.query)):return []
  remove=p.find(r'Remove This Item',['link']);return p.refs([ns[0],remove[0]]) if remove else []
 if rule=='page2_result':
  return p.refs([ns[0]]) if p.query.get('p')==['2'] else []
 if rule=='sort_selection':
  if p.query.get('product_list_order')!=['price']:return []
  return p.refs([ns[0]])+[p.ref(ns[0],'value')]
 if rule=='search_result':
  if not p.query.get('q'):return []
  cards=p.find(r'.+',['link']);cards=[n for n in cards if prop(n,'url') and '.html' in prop(n,'url')]
  return p.refs([ns[0],cards[0]]) if cards else []
 if rule=='numeric_input':
  return p.refs([ns[0]])+[p.ref(ns[0],'value')] if str(val(ns[0],'value')).strip() else []
 if rule=='link_target':
  targets=[n for n in ns if prop(n,'url') and (f.get('target_contains','') in prop(n,'url'))]
  return p.refs(targets[:1])
 if rule=='visible_control':
  # Non-interactive headings alone do not establish filter controls.
  if fid=='catalog.filter':
   links=p.find(r'\(\s*\d+\s*item\s*\)',['link']);links=[n for n in links if prop(n,'url') and any(k in parse_qs(urlsplit(prop(n,'url')).query) for k in ['cat','price'])]
   return p.refs([ns[0],links[0]]) if links else []
  return p.refs([g[0] for g in groups])
 if rule=='literal_value':return p.refs([g[0] for g in groups])
 raise ValueError(rule)

def verify_ref(r):
 obj=read(pathlib.Path(r['file']))
 for k in r['pointer'].split('/')[1:]:obj=obj[int(k)] if isinstance(obj,list) else obj[k]
 if obj!=r['quote']:raise ValueError('Evidence quote mismatch')

def prepare():
 if (O/'gold.v1.json').exists():raise RuntimeError('Gold already exists; use a new version')
 old=read(OLD/'common-readonly.v2.json');facts=[];changes=[]
 for original in old['facts']:
  f=copy.deepcopy(original);i=f['id'];f.pop('evidence_refs',None);f.pop('verification_metadata',None);f.pop('verification_url',None);f['rule']='literal_value'
  if i in ['category_lists_product','cart.empty_state']:
   changes.append({'id':i,'change':'removed','reason':'co-occurrence does not prove relation' if i=='category_lists_product' else 'duplicate of cart.empty state'});continue
  if i=='product.short_description':f.update(id='form.search.short_description',kind='form_field',rule='visible_control');changes.append({'id':i,'change':'form field, not product attribute value'})
  elif i=='product.quantity':f.update(id='control.product.quantity',kind='input_control',rule='numeric_input');changes.append({'id':i,'change':'purchase input, not persistent entity attribute'})
  elif i=='cart':f.update(page_types=['cart'],rule='cart_page');changes.append({'id':i,'change':'require cart page heading and empty state; menu link insufficient'})
  elif i in ['product','product.name','category','category.name']:f['rule']='heading_identity'
  elif i=='product.sku':f['rule']='sku_value'
  elif i=='product.rating':f['rule']='rating_value'
  elif i=='product.description':f.update(rule='description_content',clauses=[{'name_regex':'^Details$','roles':['tabpanel']}])
  elif i=='product.image':f['rule']='image_resource'
  elif i.startswith('product.') and i not in ['product.price','product.review_count','product.availability']:
   f['rule']='row_value_or_option'
   if f['clauses'][0]['roles']==['rowheader']:f['clauses'][0]['name_regex']=f['clauses'][0]['name_regex'].rstrip('$')+r'[\s\u200f]*$'
  elif i=='catalog.sorted_result':f.update(id='catalog.price_sort_selected',rule='sort_selection');changes.append({'id':i,'change':'selection state only; no sorted-order correctness claim'})
  elif i=='catalog.filtered_result':f['rule']='filter_result'
  elif i=='catalog.next_page':f['rule']='page2_result'
  elif i=='search.results_nonempty':f['rule']='search_result'
  elif f['kind']=='operation_control':f.update(kind='affordance',rule='visible_control')
  if i=='cart.view':f.update(rule='link_target',target_contains='/checkout/cart')
  if i=='catalog.paginate':f.update(rule='link_target',target_contains='p=')
  f['interpretation']='Observed UI evidence only; no automatic claim about execution or database provenance.'
  facts.append(f)
 pages=[Page(p) for folder in ['site-verification','site-verification-extra'] for p in sorted((OLD/folder).glob('*/accessibility.json'))]
 missing=[]
 for f in facts:
  hits=[{'url':p.url,'evidence_refs':fullmatch(p,f)} for p in pages];hits=[h for h in hits if h['evidence_refs']]
  if not hits:missing.append(f['id'])
  else:f['reference_witness']=hits[0]
 if missing:raise RuntimeError('New gold rule lacks independent witness: '+str(missing))
 write(O/'gold.v1.json',{'scope':'Historical Shopping read-only core UI, explicitly not whole website/DB or full network trace','facts':facts,'changes':changes,'limitations':old['limitations'],'excluded':old['excluded']})
 print('Prepared',len(facts),'independently witnessed facts; no candidate scores computed')

def freeze():
 dst=O/'freeze.v1.json'
 if dst.exists():raise RuntimeError('Already frozen')
 paths={O/'gold.v1.json',O/'score.py',O/'test_score.py'}
 for folder in ROOTS.values():
  for p in folder.glob('*/accessibility.json'):paths.update([p,p.parent/'page.html'])
 for f in read(O/'gold.v1.json')['facts']:
  for r in f['reference_witness']['evidence_refs']:verify_ref(r);paths.add(pathlib.Path(r['file']));paths.add(pathlib.Path(r['file']).parent/'page.html')
 if any(not p.is_file() for p in paths):raise RuntimeError('Required file missing')
 write(dst,{'frozen_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':[{'file':str(p),'sha256':sha(p)} for p in sorted(paths)]})

def score():
 m=read(O/'freeze.v1.json')
 for r in m['files']:
  if sha(pathlib.Path(r['file']))!=r['sha256']:raise RuntimeError('Frozen file changed: '+r['file'])
 g=read(O/'gold.v1.json');results={}
 for run,root in ROOTS.items():
  pages=[Page(p) for p in sorted(root.glob('*/accessibility.json'))];rows=[]
  for f in g['facts']:
   hits=[]
   for p in pages:
    refs=fullmatch(p,f)
    if refs:
     for r in refs:verify_ref(r)
     hits.append({'url':p.url,'snapshot':p.path.parent.name,'evidence_refs':refs})
   rows.append({'id':f['id'],'kind':f['kind'],'supported':bool(hits),'status':'supported_in_recorded_UI' if hits else 'not_demonstrated_in_recorded_UI','evidence':hits})
  metrics={kind:{'supported':sum(r['supported'] for r in rows if r['kind']==kind),'denominator':sum(r['kind']==kind for r in rows)} for kind in sorted({r['kind'] for r in rows})}
  results[run]={'snapshots':len(pages),'metrics':metrics,'facts':rows}
 out={'freeze_sha256':sha(O/'freeze.v1.json'),'frozen_at':m['frozen_at'],'results':results,'limitations':g['limitations']+['No CM candidate names are used. Absent UI support does not prove absence in network.','No full trace fidelity, cost-efficiency, or causal algorithm ranking. No composite score.']}
 write(O/'results.v1.json',out)
 lines=['# 修订后自动探索 UI 证据覆盖','','同一冻结规则直接审计原始AX与页面类型；不读取CM名称。只读核心有限范围，不是全站覆盖率。','','| 维度 | Drive | browser-use |','|---|---:|---:|']
 for kind,v in results['drive']['metrics'].items():
  b=results['browser-use']['metrics'][kind];lines.append(f"| {kind} | {v['supported']}/{v['denominator']} | {b['supported']}/{b['denominator']} |")
 lines+=['','## 逐项证据支持','','| 事实 | Drive | browser-use |','|---|---|---|']
 for a,b in zip(results['drive']['facts'],results['browser-use']['facts']):lines.append(f"| {a['id']} | {'支持' if a['supported'] else '未证明'} | {'支持' if b['supported'] else '未证明'} |")
 lines+=['','未证明仅限已记录UI。完整trace忠实度、DB来源和成本不由本表推出。页面控件、输入、状态分别计分，不合成总分。', '',f"冻结：`{out['freeze_sha256']}`",'', '复算：`python test_score.py`，`python score.py score`。输出无变化时间字段，同输入可逐字节复算。']
 (O/'results.v1.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');print(json.dumps({k:v['metrics'] for k,v in results.items()},ensure_ascii=False,indent=2))

# v4 adds a structurally bound category -> product-card relation.
from html.parser import HTMLParser

class ProductCards(HTMLParser):
 def __init__(self, html):
  super().__init__();self.stack=[];self.links=set();self.feed(html)
 def handle_starttag(self, tag, attrs):
  attrs=dict(attrs);classes=attrs.get('class','').split()
  if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:
   self.stack.append((tag,'product-item' in classes))
  if tag=='a' and 'product-item-link' in classes and any(card for _,card in self.stack):
   self.links.add(attrs.get('href',''))
 def handle_endtag(self, tag):
  for i in range(len(self.stack)-1,-1,-1):
   if self.stack[i][0]==tag:
    del self.stack[i:];break

original_fullmatch=fullmatch

def fullmatch(p,f):
 if f.get('rule')!='product_card_relation':return original_fullmatch(p,f)
 if p.type!='category_list':return []
 heading=p.find(r'Items.*of',['heading'])
 if not heading:return []
 html=(p.path.parent/'page.html').read_text(encoding='utf-8-sig')
 cards=ProductCards(html).links
 for n in p.nodes:
  target=prop(n,'url')
  if not p.visible(n) or val(n,'role')!='link' or not str(val(n,'name')).strip() or val(n,'name')=='Image' or target not in cards:continue
  if urlsplit(target).netloc!=urlsplit(p.url).netloc or not urlsplit(target).path.endswith('.html'):continue
  i=next(i for i,x in enumerate(n['properties']) if x['name']=='url')
  return p.refs([heading[0],n])+[{'file':str(p.path),'pointer':f"/nodes/{p.indices[n['nodeId']]}/properties/{i}/value/value",'quote':target}]
 return []
