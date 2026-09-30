"""Trace-scoped CM diagnostics. Standard library only; score requires verified freeze."""
import argparse, datetime, hashlib, json, pathlib, re
BASE=pathlib.Path(__file__).resolve().parent
SECTIONS=('entities','attributes','operations','relations')
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8-sig'))
def write(p,x):pathlib.Path(p).parent.mkdir(parents=True,exist_ok=True);pathlib.Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def norm(s):return re.sub(r'[\W_]+','',str(s).casefold())
def key(section,x):return x['entity']+'.'+x['id'] if section=='attributes' else x['id']
def aliases(g,section):
 out={}
 for x in g[section]:
  for name in [x['id'],x.get('name',''),*x.get('aliases',[])]:
   if name:out[(x['entity'] if section=='attributes' else '',norm(name))]=key(section,x)
 return out
def validate_ref(r):
 p=pathlib.Path(r['file'])
 if not p.is_file():return False
 if 'line' in r:
  lines=p.read_text(encoding='utf-8-sig').splitlines();return 0<r['line']<=len(lines) and lines[r['line']-1]==r['quote']
 obj=read(p)
 for part in r['pointer'].split('/')[1:]:
  part=part.replace('~1','/').replace('~0','~');obj=obj[int(part)] if isinstance(obj,list) else obj[part]
 return obj==r['quote']
def metric(pred,gold,pending=0):
 tp=len(pred&gold); fp=len(pred-gold); fn=len(gold-pred); p=tp/len(pred) if pred else None;r=tp/len(gold) if gold else None
 return dict(tp=tp,fp=fp,fn=fn,predicted_resolved=len(pred),gold=len(gold),precision=p,recall=r,f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,unresolved=pending,precision_lower=tp/(len(pred)+pending) if len(pred)+pending else None,precision_upper=(tp+pending)/(len(pred)+pending) if len(pred)+pending else None,matched=sorted(pred&gold),missing=sorted(gold-pred),extra_resolved=sorted(pred-gold))
def normalize(cm,g,policy):
 maps={s:aliases(g,s) for s in SECTIONS};claims=[];excluded=[]
 def add(s,k,x,owner=None):claims.append(dict(section=s,canonical=k,original=x,owner=owner))
 entities=cm.get('entities',[]) if 'entities' in cm else [x for x in cm['concepts'] if x.get('concept_type')=='business_entity']
 operations=cm.get('operations',[]) if 'operations' in cm else [x for x in cm.get('concepts',[]) if x.get('concept_type')=='operation']
 ids={}
 for e in entities:
  name=e.get('canonical_name',e.get('name',''));n=norm(name)
  if n in map(norm,policy['facet_entities']):
   for a in e.get('attributes',[]):
    if norm(a['name']) in map(norm,['range','price_range','Price Range']):add('attributes','category.price_range',a,e)
    else:excluded.append(dict(section='attributes',name=name+'.'+a['name'],reason='facet_bucket_count_outside_core_vocabulary'))
   excluded.append(dict(section='entities',name=name,reason='facet entity normalized to category.price_range; not a category entity hit'));continue
  canon=maps['entities'].get(('',n));ids[e.get('id',name)]=canon
  if not canon and n in map(norm,policy['excluded_entities']):
   excluded.append(dict(section='entities',name=name,reason='outside_core_domain',attributes=e.get('attributes',[])));continue
  add('entities',canon or '?'+name,e)
  for a in e.get('attributes',[]):add('attributes',maps['attributes'].get((canon,norm(a['name'])),(canon or '?'+name)+'.?'+a['name']),a,e)
 for o in operations:
  name=o.get('canonical_name',o.get('name',''));canon=maps['operations'].get(('',norm(name)))
  if not canon and norm(name) in map(norm,policy['excluded_operations']):excluded.append(dict(section='operations',name=name,reason='outside_core_operation_contract'));continue
  add('operations',canon or '?'+name,o)
 for r in cm.get('relations',cm.get('relationships',[])):
  canon=maps['relations'].get(('',norm(r.get('id',r.get('name','')))))
  if not canon:
   source=ids.get(r.get('source'),maps['entities'].get(('',norm(r.get('source','')))));target=ids.get(r.get('target'),maps['entities'].get(('',norm(r.get('target','')))))
   for gt in g['relations']:
    if source==gt['source'] and target==gt['target'] and norm(r.get('predicate','')) in map(norm,[gt['predicate'],*gt.get('predicate_aliases',[])]):canon=gt['id']
  add('relations',canon or '?'+json.dumps(r,ensure_ascii=False,sort_keys=True),r)
 return claims,excluded

def evidence(claim,run,index):
 x=claim['original'];owner=claim.get('owner') or {};direct=x.get('evidence_refs',[])+x.get('source_refs',[])
 # Entity page refs are valid entity-level citations, never inherited as attribute citations.
 if claim['section']=='entities':direct+=x.get('page_refs',[])
 supplemental=index.get(x.get('id',''),{});direct+=supplemental.get('evidence_refs',[])+supplemental.get('page_refs',[])
 result=[]
 for r in dict.fromkeys(direct):
  status='unresolved';detail=None
  p=pathlib.Path(run['trace'])/r
  if p.is_file():status='file_only';detail=str(p)
  elif p.is_dir():status='directory_only';detail=str(p)
  elif run.get('source_root') and (pathlib.Path(run['source_root'])/r/'inputs/page.aria.yml').is_file():
   status='file_only';detail=str(pathlib.Path(run['source_root'])/r/'inputs/page.aria.yml')
  elif r.startswith('page.aria.yml:'):
   selector=r.split(':',1)[1];parts=selector.split(':');role=parts[0];label=':'.join(parts[1:]);hits=[]
   for page in (owner or x).get('page_refs',[]):
    f=pathlib.Path(run.get('source_root',''))/page/'inputs/page.aria.yml'
    if f.is_file():
     for i,line in enumerate(f.read_text(encoding='utf-8').splitlines(),1):
      if re.search(r'\b'+re.escape(role)+r'\b',line) and label and label in line:hits.append(dict(file=str(f),line=i,quote=line))
   if hits:status='selector_located';detail=hits
  elif re.fullmatch('E[0-9]+',r):
   status='unresolved_local_E_id' # Merged local IDs lack a unique page binding.
  result.append(dict(ref=r,status=status,location=detail,semantic_support='pending_manual_review'))
 return dict(has_assertion_ref=bool(direct),has_file=any(x['status'] in ['file_only','directory_only','selector_located'] for x in result),has_precise_locator=any(x['status']=='selector_located' for x in result),refs=result,semantic_support='pending_manual_review',parent_page_refs=owner.get('page_refs',[]) if claim['section']=='attributes' else [])
def score(cm,g,policy,run,index=None):
 claims,excluded=normalize(cm,g,policy);out={};audit=[]
 for c in claims:
  c['evidence']=evidence(c,run,index or {});audit.append(c)
 for s in SECTIONS:
  unique={c['canonical'] for c in claims if c['section']==s};pending={k for k in unique if '?' in k};pred=unique-pending
  out[s]=metric(pred,{key(s,x) for x in g[s]},len(pending));out[s]['pending_adjudication']=sorted(pending);out[s]['raw_assertions']=sum(c['section']==s for c in claims);out[s]['duplicates_collapsed']=out[s]['raw_assertions']-len(unique)
 execution=[]
 for c in claims:
  if c['section']=='operations':
   gt=next((x for x in g['operations'] if x['id']==c['canonical']),{});expected=gt.get('executed');actual=c['original'].get('executed');execution.append(dict(operation=c['canonical'],candidate=actual,reference=expected,status='not_assessable' if actual is None or expected is None else 'match' if actual==expected else 'mismatch',reference_basis=gt.get('execution_status')))
 n=len(claims)
 return dict(metrics=out,excluded=excluded,assertions=audit,evidence_summary=dict(assertions=n,with_refs=sum(c['evidence']['has_assertion_ref'] for c in claims),with_resolvable_file=sum(c['evidence']['has_file'] for c in claims),with_precise_locator=sum(c['evidence']['has_precise_locator'] for c in claims),semantic_support_verified=0,semantic_support_pending=n),operation_execution=execution,schema=dict(adapter='concepts' if 'concepts' in cm else 'entities_operations',parsed=True,structured_relations_present=bool(cm.get('relations',cm.get('relationships',[]))),note='Adapter validation only; no shared original output schema or comparable completion denominator.'))
def freeze(config,out):
 if out.exists():raise ValueError('Freeze already exists; never overwrite. Create a new version.')
 c=read(config);files={pathlib.Path(__file__).resolve(),config.resolve(),BASE/'test_scorer.py'}
 for run in c['runs']:
  g=read(run['gold'])
  for s in SECTIONS:
   for x in g[s]:
    assert x['evidence_refs'] and all(validate_ref(r) for r in x['evidence_refs']),x
    for r in x['evidence_refs']:
     files.add(pathlib.Path(r['file']))
     if r.get('derived_ref'):files.add(pathlib.Path(r['derived_ref']['file']))
  files.add(pathlib.Path(run['gold']));files.add(pathlib.Path(run['candidate']))
  if run.get('evidence_index'):files.add(pathlib.Path(run['evidence_index']))
  files.add(pathlib.Path(g['meta']['db_reference']))
  for root in [run['trace'],run.get('source_root')]:
   if root:files.update(p for p in pathlib.Path(root).rglob('*') if p.is_file())
 rows=[dict(file=str(p),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(files)]
 write(out,dict(frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),contract='freeze before score; existing candidates predate annotation',config=str(config.resolve()),files=rows))
def verify(manifest):
 m=read(manifest)
 for x in m['files']:
  p=pathlib.Path(x['file']);assert p.is_file() and p.stat().st_size==x['bytes'] and sha(p)==x['sha256'],'Hash mismatch: '+str(p)
 return m

def main():
 p=argparse.ArgumentParser();p.add_argument('command',choices=['freeze','score','verify']);p.add_argument('--config',type=pathlib.Path,default=BASE/'scoring-contract.v1.json');p.add_argument('--manifest',type=pathlib.Path,default=BASE/'freeze.v1.json');p.add_argument('--output',type=pathlib.Path,default=BASE/'reports/existing-trace-scoped.v1.json');a=p.parse_args()
 if a.command=='freeze':freeze(a.config,a.manifest);print('Frozen',a.manifest);return
 m=verify(a.manifest)
 if a.command=='verify':print('Verified',len(m['files']),'files');return
 c=read(m['config']);results={}
 for run in c['runs']:
  index=read(run['evidence_index']).get('evidence_index',{}) if run.get('evidence_index') else {}
  results[run['id']]=score(read(run['candidate']),read(run['gold']),c['policy'],run,index)
 report=dict(title='现有运行的 trace-scoped 诊断',scored_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),freeze_sha256=sha(a.manifest),frozen_at=m['frozen_at'],manifest=str(a.manifest.resolve()),limitations=c['limitations'],rules=c['rules'],results=results)
 write(a.output,report)
 lines=['# 现有运行的 trace-scoped 诊断','',f"冻结时间：{m['frozen_at']}；计分时间：{report['scored_at']}",'',f'Freeze SHA256: `{sha(a.manifest)}`','','本报告为事后核心范围诊断。P/R/F1 按名称/结构匹配计分，不代表引用已证明断言。未裁定额外项不判为幻觉；P 是已裁定子集精度，另报保守精度区间。','', '| 运行 | 指标 | 命中/答案 | 已裁定预测 | P | R | F1 | 未裁定 | P 区间 |','|---|---|---:|---:|---:|---:|---:|---:|---|']
 def pct(v):return 'N/A' if v is None else f'{100*v:.2f}%'
 for name,r in results.items():
  for s,v in r['metrics'].items():lines.append(f"| {name} | {s} | {v['tp']}/{v['gold']} | {v['predicted_resolved']} | {pct(v['precision'])} | {pct(v['recall'])} | {pct(v['f1'])} | {v['unresolved']} | {pct(v['precision_lower'])}–{pct(v['precision_upper'])} |")
 lines+=['','## 规则与限制','']+['- '+x for x in c['rules']+c['limitations']]
 for name,r in results.items():
  lines+=['',f'## {name} 逐项诊断','']
  for s,v in r['metrics'].items():lines+=['',f"### {s}",'','命中：'+(', '.join(v['matched']) or '无'),'','遗漏：'+(', '.join(v['missing']) or '无'),'','待裁定：'+(', '.join(v['pending_adjudication']) or '无')]
  e=r['evidence_summary'];lines+=['','### 引用与执行','',f"在 {e['assertions']} 条范围内原始断言中，带自身引用 {e['with_refs']}，可定位到文件/目录 {e['with_resolvable_file']}，可定位到节点/行 {e['with_precise_locator']}。语义支持仍需人工复核，不能由命中或引用存在率代替。",'', '```json',json.dumps(r['operation_execution'],ensure_ascii=False,indent=2),'```','','排除项（不作为错误）：']+['- '+x['name']+'：'+x['reason'] for x in r['excluded']]
 lines+=['','## 复算','', '在 benchmark/extraction 目录运行：','','```powershell','python test_scorer.py','python score_context_models.py verify','python score_context_models.py score','```','','评分前校验 manifest 内所有文件哈希；任一变化即拒绝评分。JSON 保存每项断言、归一结果、遗漏、排除、待裁定和引用检查结果。原始 trace 只读，完整文件清单包含于 freeze.v1.json。']
 a.output.with_suffix('.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');print(json.dumps({k:v['metrics'] for k,v in results.items()},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
