"""Core attribute citation support, page-local, conservative. Not complete semantic precision."""
import datetime,hashlib,json,pathlib,re,sys,unicodedata
O=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(O.parent/'extraction'))
import score_context_models as legacy
from evaluate_original_task import ROOTS,GOLD,POLICY
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def clean(s):return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',s).replace('\u200f','').replace('\u200e','')).strip().casefold()
def parse_tree(path):
 out=[];stack=[]
 for line_no,line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(),1):
  m=re.match(r'^(\s*)- ([\w]+)(?:\s|:|$)',line)
  if not m:continue
  depth=len(m[1]);role=m[2]
  while stack and stack[-1]['depth']>=depth:stack.pop()
  rest=line[m.end():];q=re.match(r'"((?:\\.|[^"\\])*)"',rest)
  name=q[1].replace('\\"','"') if q else re.sub(r'\[.*?\]','',rest).lstrip(': ').strip()
  item={'line':line_no,'quote':line,'role':role,'name':name,'depth':depth,'parents':[x['line'] for x in stack]};out.append(item);stack.append(item)
 return out
def supported_ref(ref,markers,nodes,endpoints):
 if re.fullmatch('E[0-9]+',ref):
  return {'status':'incorrect_reference','reason':'missing page-local endpoint'} if ref not in endpoints else {'status':'unresolved','reason':'endpoint exists but attribute-specific response-field support requires separate review'}
 if not ref.startswith('page.aria.yml:'):return {'status':'unresolved','reason':'unsupported locator syntax'}
 role,sep,label=ref[len('page.aria.yml:'):].partition(':')
 if not sep or not clean(label):return {'status':'unresolved','reason':'missing selector label'}
 for marker in markers:
  # A broad container may locate its named descendant, but its label must identify THIS field.
  if clean(label) not in clean(marker['name']):continue
  containers=[n for n in nodes if n['role']==role and (n['line']==marker['line'] or n['line'] in marker['parents'])]
  if containers:return {'status':'supported','marker':marker,'container':containers[-1],'reason':'reference role plus named descendant locates the same field in this page'}
 return {'status':'unresolved','reason':'no matching field-specific marker under cited role; not automatically a hallucination'}
def field_markers(canonical,nodes):
 field=canonical.split('.',1)[-1];entity=canonical.split('.',1)[0]
 labels={'sku':'SKU','asin':'ASIN','dimensions':'Product Dimensions','upc':'UPC','manufacturer':'Manufacturer','country_of_origin':'Country of Origin','package_dimensions':'Package Dimensions','item_weight':'Item Weight','model_number':'Item model number','date_first_available':'Date First Available','batteries':'Batteries','discontinued_status':'Is Discontinued By Manufacturer','domestic_shipping':'Domestic Shipping','international_shipping':'International Shipping','department':'Department'}
 found=[]
 for n in nodes:
  name=clean(n['name']);role=n['role'];q=n['quote']
  if field in labels:
   ok=name==clean(labels[field]) and role in (['strong','generic'] if field=='sku' else ['rowheader'])
  elif field=='name':ok=(role=='heading' and '[level=1]' in q) if entity=='product' else role=='heading' and bool(re.search(r'Items\s+\d+-\d+\s+of',n['name']))
  elif field=='price':ok=bool(re.fullmatch(r'\$[\d,.]+',name)) or name=='price'
  elif field=='rating':ok=name=='rating:'
  elif field=='review_count':ok=role in ['link','tab'] and bool(re.search(r'\d+\s*reviews?|reviews?\s*\(\d+\)',name))
  elif field=='availability':ok=name in ['availability','in stock','out of stock']
  elif field=='image':ok=role in ['img','image'] and name=='image'
  elif field=='quantity':ok=role in ['spinbutton','textbox'] and name=='qty'
  elif field in ['size','color','style']:ok=name.rstrip(' *')==field and role in ['generic','rowheader','radio','combobox']
  elif field=='description':ok=role in ['heading','tabpanel'] and name in ['product description','details']
  elif field=='short_description':ok=role=='textbox' and name=='short description'
  elif field=='item_count':ok=(role=='link' and 'my cart' in name and bool(re.search(r'\d+.*items?',name))) if entity=='cart' else bool(re.search(r'items\s+\d+-\d+\s+of\s*\d+',name))
  elif field=='subcategories':ok=role=='link' and not name.startswith('$') and bool(re.search(r'\(\s*\d+\s*item',name))
  elif field=='price_range':ok=role=='link' and bool(re.search(r'\$[\d,.]+\s*(-|and above)',name))
  else:ok=False
  if ok:found.append(n)
 return found
def freeze():
 dst=O/'citations-v2.freeze.json'
 if dst.exists():raise RuntimeError('Already frozen')
 prior=read(O/'paired-original.freeze.v1.json');paths={pathlib.Path(__file__),O/'test_citations_v2.py',O/'evaluate_original_task.py',O/'paired-original.freeze.v1.json'}
 for r in prior['files']:
  p=pathlib.Path(r['file'])
  if sha(p)!=r['sha256']:raise RuntimeError('Previous frozen input changed')
  paths.add(p)
 write(dst,{'frozen_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Core attribute own-citation support. No precision claim for unresolved or out-of-scope assertions.','files':[{'file':str(p),'sha256':sha(p)} for p in sorted(paths)]})
def score():
 m=read(O/'citations-v2.freeze.json')
 for r in m['files']:
  if sha(pathlib.Path(r['file']))!=r['sha256']:raise RuntimeError('Frozen input changed')
 g=read(GOLD);policy=read(POLICY)['policy'];extra={'product.name':['名称'],'product.model_number':['型号'],'product.color':['颜色'],'product.style':['款式'],'category.item_count':['商品数量'],'product.size':['尺寸']}
 for a in g['attributes']:a['aliases']+=extra.get(a['entity']+'.'+a['id'],[])
 targets={legacy.key('attributes',a) for a in g['attributes']};out={}
 for run,root in ROOTS.items():
  claims=[];pending=[]
  for page in read(root/'INDEX.json')['pages']:
   directory=root/page['dir'];nodes=parse_tree(directory/'inputs/page.aria.yml');endpoints={r['ref']:r for r in map(json.loads,(directory/'inputs/endpoints.jsonl').read_text(encoding='utf-8-sig').splitlines())}
   normalized,excluded=legacy.normalize(read(directory/'output/concepts.json'),g,policy)
   for c in normalized:
    if c['section']!='attributes':continue
    if c['canonical'] not in targets:pending.append({'page':page['dir'],'canonical':c['canonical'],'reason':'outside evaluated core or unmapped'});continue
    markers=field_markers(c['canonical'],nodes);refs=[{'ref':ref,**supported_ref(ref,markers,nodes,endpoints)} for ref in c['original'].get('source_refs',[])]
    supported=any(r['status']=='supported' for r in refs)
    claims.append({'page':page['dir'],'canonical':c['canonical'],'raw_name':c['original']['name'],'source_file':str(directory/'inputs/page.aria.yml'),'status':'supported_own_citation' if supported else 'unresolved','refs':refs,'field_markers_present':bool(markers)})
  supported={c['canonical'] for c in claims if c['status']=='supported_own_citation'}
  out[run]={'own_citation_core_recall':{'hits':len(supported),'denominator':len(targets),'matched':sorted(supported),'not_yet_supported':sorted(targets-supported)},'core_assertions':len(claims),'supported_core_assertions':sum(c['status']=='supported_own_citation' for c in claims),'unresolved_core_assertions':sum(c['status']=='unresolved' for c in claims),'incorrect_refs':sum(r['status']=='incorrect_reference' for c in claims for r in c['refs']),'assertions':claims,'outside_core_or_unmapped':pending}
 write(O/'citations-v2.results.json',{'freeze_sha256':sha(O/'citations-v2.freeze.json'),'frozen_at':m['frozen_at'],'interpretation':'A conservative citation-support diagnostic, not complete semantic accuracy. Missing literal anchors stay unknown. Label support is allowed by original extraction task; this is different from A value-level coverage.','results':out})
 lines=['# B：属性自身引用支持的核心召回','','这是保守引用支持诊断：字段在本页存在且自身source_refs可定位到该字段才命中；范围外与未定位保留待核验，不当错。不是完整准确率。','','| 指标 | 阿器 | Claude Code |','|---|---:|---:|']
 for key in ['own_citation_core_recall','core_assertions','supported_core_assertions','unresolved_core_assertions','incorrect_refs']:
  values=[str(out[k][key]) if key!='own_citation_core_recall' else f"{out[k][key]['hits']}/{out[k][key]['denominator']}" for k in ['aqi','claudecode']];lines.append('| '+key+' | '+' | '.join(values)+' |')
 lines+=['','表格容器引用如table:ASIN可通过其子行头定位；泛指“商品标题”等非原文锚点不自动修补。无引用或伪造E编号不能获得自身引用命中。','', '原任务允许字段label与record_key；本诊断沿用32项任务核心词表，与A的29项有值属性分母不同。短描述搜索框与Qty仅为字段暴露，不证明DB商品值。','', '复算：`python test_citations_v2.py`、`python score_citations_v2.py score`。']
 (O/'citations-v2.results.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');print('\n'.join(lines))
if __name__=='__main__':freeze() if sys.argv[1]=='freeze' else score()
