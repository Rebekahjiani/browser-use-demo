"""Same AX adapter and evidence matcher for both runs; no website coverage percentages."""
import json,pathlib,re,hashlib,datetime
from collections import Counter
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
BASE=pathlib.Path(__file__).resolve().parent;B=BASE.parent
RUNS={'drive':pathlib.Path(r'C:\Users\bulin\appweave\outputs\01-evidence\26_09_28_10_40_34-min'),'browser-use-20260929':B/'outputs/20260929-115141-231052'}
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def normalize_url(url):
 u=urlsplit(url);query=[(k,v) for k,v in parse_qsl(u.query,keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in ['sid','phpsessid']]
 return urlunsplit((u.scheme.lower(),u.netloc.lower(),u.path or '/',urlencode(sorted(query)),''))
def classify(url,html):
 path=urlsplit(url).path
 if 'catalog-product-view' in html:return 'product_detail'
 if 'catalog-category-view' in html:return 'category_list'
 for key,val in [('catalogsearch/advanced','advanced_search'),('catalogsearch/result','search_results'),('checkout/cart','cart'),('customer/account','account'),('/contact','contact')]:
  if key in path:return val
 if path=='/':return 'home'
 return 'unknown'
def visible_nodes(data):
 return [dict(index=i,node_id=n.get('nodeId'),role=n.get('role',{}).get('value'),name=n.get('name',{}).get('value',''),properties=n.get('properties',[]),value=n.get('value',{}).get('value')) for i,n in enumerate(data['nodes']) if not n.get('ignored') and n.get('name',{}).get('value')]
def matches(page,fact):
 if fact.get('page_types') and page['type'] not in fact['page_types']:return None
 refs=[]
 for clause in fact['clauses']:
  found=[]
  for n in page['nodes']:
   if clause.get('roles') and n['role'] not in clause['roles']:continue
   if fact['id'] in ['product','product.name'] and not any(x.get('name')=='level' and x.get('value',{}).get('value')==1 for x in n['properties']):continue
   if clause.get('value_equals') is not None and n.get('value')!=clause['value_equals']:continue
   if re.search(clause['name_regex'],n['name'],re.I):found.append(n)
  if not found:return None
  n=found[0];refs.append(dict(file=page['ax_file'],pointer=f"/nodes/{n['index']}/name/value",quote=n['name'],node_id=n['node_id'],role=n['role']))
  if clause.get('value_equals') is not None:refs.append(dict(file=page['ax_file'],pointer=f"/nodes/{n['index']}/value/value",quote=n['value']))
 return refs

def main():
 registry=read(BASE/'common-registry.draft.json');out={};used={BASE/'common-registry.draft.json',pathlib.Path(__file__),BASE/'db-candidate-review.json',pathlib.Path(registry['db_reference'])}
 for name,root in RUNS.items():
  folder=root/'drive/screenshots' if name=='drive' else root/'snapshots';obs={}
  if name!='drive':
   p=root/'observations.jsonl';used.add(p)
   for line in p.read_text(encoding='utf-8-sig').splitlines():
    o=json.loads(line);obs[pathlib.Path(o['path']).name]=o['elapsed_s']
  pages=[];errors=[]
  for directory in sorted(folder.iterdir()):
   if not directory.is_dir():continue
   try:
    ax=directory/'accessibility.json';html_file=directory/'page.html';a=read(ax);used.update([ax,html_file]);web=next(n for n in a['nodes'] if n.get('role',{}).get('value')=='RootWebArea');url=next((v['value']['value'] for v in web.get('properties',[]) if v['name']=='url'),'');html=html_file.read_text(encoding='utf-8-sig')
    page=dict(snapshot=directory.name,url=url,normalized_url=normalize_url(url),type=classify(url,html),ax_file=str(ax),html_file=str(html_file),nodes=visible_nodes(a),elapsed_s=obs.get(directory.name),evidence_files={f:(directory/f).is_file() for f in ['accessibility.json','page.html','screenshot.png']})
    pages.append(page)
   except Exception as e:errors.append(dict(directory=str(directory),error=str(e)))
  # No timestamps guessed from file mtime or snapshot ordinal.
  if name=='drive':
   trail_file=next((root/'drive').glob('*-trail.json'));used.add(trail_file);trail=read(trail_file)
   times={normalize_url(url):(node.get('visitedAt')-trail['startedAt'])/1000 for url,node in trail['nodes'] if node.get('visitedAt')}
   visited=[dict(url=url,elapsed_s=t) for url,t in times.items()]
  else:visited=[dict(url=p['normalized_url'],elapsed_s=p['elapsed_s']) for p in pages]
  findings=[]
  for fact in registry['facts']:
   hits=[]
   for page in pages:
    refs=matches(page,fact)
    if refs:hits.append(dict(snapshot=page['snapshot'],url=page['url'],elapsed_s=page['elapsed_s'],evidence_refs=refs))
   findings.append(dict(id=fact['id'],kind=fact['kind'],status='rule_matched_requires_semantic_review' if hits else 'not_observed_in_recorded_AX',first_recorded_elapsed_s=min((h['elapsed_s'] for h in hits if h['elapsed_s'] is not None),default=None),hits=hits,note=fact['note']))
  summary={}
  for kind in sorted({f['kind'] for f in findings}):
   fs=[f for f in findings if f['kind']==kind];summary[kind]=dict(observed=sum(bool(f['hits']) for f in fs),candidate_checklist=len(fs),coverage_rate=None)
  nodes=[]
  for p in pages:nodes.append({k:v for k,v in p.items() if k!='nodes'})
  # Candidate-independent normalized AX input for future identical construction runs.
  run_dir=BASE/'normalized-inputs'/name;run_dir.mkdir(parents=True,exist_ok=True)
  with (run_dir/'observations.jsonl').open('w',encoding='utf-8') as f:
   for p in pages:f.write(json.dumps(p,ensure_ascii=False)+'\n')
  write(run_dir/'manifest.json',dict(adapter='visible-AX-v1',run=name,pages=len(pages),original_root=str(root),input_files=[dict(file=str(p),sha256=sha(p)) for p in sorted({pathlib.Path(x[k]) for x in pages for k in ['ax_file','html_file']})],exclusions=['ignored AX nodes','network not normalized in this draft input profile','screenshots not embedded; original references remain available'],status='prepared_UI_only_profile_not_approved_as_fixed_Weave_pipeline'))
  out[name]=dict(summary=summary,snapshots=len(pages),unique_urls=len({p['normalized_url'] for p in pages}),page_types={t:len({p['normalized_url'] for p in pages if p['type']==t}) for t in sorted({p['type'] for p in pages})},errors=errors,pages=nodes,facts=findings,observed_visits=visited,timing_note='Drive snapshot-to-time mapping unavailable; no semantic time curve or AUC computed. Native URL first-visit timestamps are separate.' if name=='drive' else 'Snapshot elapsed_s is observation time, not exact transition time.')
 # Compare raw source hashes to the already frozen originals for consumed files.
 prior=read(B/'extraction/freeze.v1.json');prior_hashes={str(pathlib.Path(x['file'])):x['sha256'] for x in prior['files']};rows=[]
 for p in sorted(used):
  h=sha(p);old=prior_hashes.get(str(p));
  if old and old!=h:raise RuntimeError('Original input changed: '+str(p))
  rows.append(dict(file=str(p),sha256=h,bytes=p.stat().st_size,matched_previous_freeze=old==h if old else None))
 write(BASE/'offline-audit.inputs.json',dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='audit_input_manifest_not_G_freeze',files=rows))
 report=dict(status='offline_candidate_audit_not_website_coverage_score',runs=out,limitations=['Common registry is draft; no website-level coverage denominator or percentages.','Same AX rules used on both raw snapshot sets; matches require semantic review.','No match means not observed in available AX, not absent from all network evidence or site.','Starting state, exploration permissions, prompts and coverage differ; not a controlled algorithm ranking.','Network provenance, complete transitions and UI reachability await further verification.'])
 write(BASE/'offline-coverage-audit.json',report)
 lines=['# 两份历史 trace 的共同口径离线审计','','这是共同候选清单的证据命中审计，不是网站覆盖率。G 尚未通过独立界面核验，所有比例留空。','','| 观察指标 | Drive | browser-use 2026-09-29 |','|---|---:|---:|']
 for field in ['snapshots','unique_urls']:lines.append(f"| {field} | {out['drive'][field]} | {out['browser-use-20260929'][field]} |")
 for kind in out['drive']['summary']:lines.append(f"| {kind} 候选规则命中数 | {out['drive']['summary'][kind]['observed']} | {out['browser-use-20260929']['summary'][kind]['observed']} |")
 lines+=['','## 候选事实逐项矩阵','','“有”表示同一AX规则有证据命中，仍需语义复核；“未见”只限已记录AX。','', '| 候选事实 | 类型 | Drive | browser-use |','|---|---|---|---|']
 for i,f in enumerate(out['drive']['facts']):lines.append(f"| {f['id']} | {f['kind']} | {'有' if f['hits'] else '未见'} | {'有' if out['browser-use-20260929']['facts'][i]['hits'] else '未见'} |")
 lines+=['','## 限制','']+['- '+s for s in report['limitations']]+['- Drive非空header不能代替cart-line；browser-use空购物车没有金额/条目证据。','- 有控件不等于已执行；暂无完整动作结果评分。','- Drive原生URL时间不能当作snapshot事实首次发现时间，不生成伪精确的语义覆盖曲线。','- 规范化输入是UI-only候选适配器，未冒充织语统一构建流程，也未生成新的CM分数。','','## 复算','','```powershell','python audit_traces.py','```','','输入哈希见 offline-audit.inputs.json；逐项原始AX JSON Pointer与quote见 offline-coverage-audit.json。']
 (BASE/'offline-coverage-audit.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');print(json.dumps({k:{x:v[x] for x in ['summary','snapshots','unique_urls','page_types','errors']} for k,v in out.items()},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
