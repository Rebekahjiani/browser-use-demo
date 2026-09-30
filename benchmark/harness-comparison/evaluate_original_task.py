"""Paired historical outputs: freeze first, then recall and page-local citation audit."""
import collections, datetime, hashlib, json, pathlib, re, sys
import jsonschema
O=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(O.parent/'extraction'))
import score_context_models as legacy
ROOTS={'aqi':pathlib.Path(r'C:\Users\bulin\appweave\logs\03-context-model\260928-145535\llm\entity-extract'), 'claudecode':O/'claudecode-original-task/entity-extract'}
GOLD=O.parent/'extraction/ground-truth/drive-trace.v1.json'
POLICY=O.parent/'extraction/scoring-contract.v1.json'
MANIFEST=O/'paired-original.freeze.v1.json'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def freeze():
 if MANIFEST.exists():raise RuntimeError('Already frozen')
 paths={pathlib.Path(__file__),O/'test_paired.py',GOLD,POLICY,O.parent/'extraction/score_context_models.py',O/'claudecode-original-task/input-manifest.json'}
 for root in ROOTS.values():
  paths.update(root/name for name in ['TASK.md','INDEX.json','schema.json'])
  for page in read(root/'INDEX.json')['pages']:
   paths.update((root/page['dir']/'inputs').rglob('*'))
   paths.add(root/page['dir']/'output/concepts.json')
 for section in ['entities','attributes','operations','relations']:
  for fact in read(GOLD)[section]:
   paths.update(pathlib.Path(r['file']) for r in fact['evidence_refs'])
 write(MANIFEST,{'frozen_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'design':'post-hoc paired historical outputs; frozen before numerical scoring, not before generation','files':[{'file':str(p),'sha256':sha(p)} for p in sorted(paths) if p.is_file()]})

def locate(ref,root,page,endpoints):
 if re.fullmatch(r'E\d+',ref):
  e=endpoints.get(ref)
  return {'status':'endpoint_exists' if e else 'missing_endpoint','endpoint':e}
 if ref.startswith('page.aria.yml:'):
  selector=ref[len('page.aria.yml:'):];role,sep,label=selector.partition(':')
  hits=[]
  for i,line in enumerate((root/page/'inputs/page.aria.yml').read_text(encoding='utf-8-sig').splitlines(),1):
   if sep and label and re.search(r'^\s*-\s*'+re.escape(role)+r'(?:\s|:|$)',line) and label in line:
    hits.append({'line':i,'quote':line})
  return {'status':'literal_tree_anchor_found' if hits else 'tree_anchor_not_literal','hits':hits}
 return {'status':'unsupported_reference_syntax'}

def audit(root):
 schema=read(root/'schema.json');validator=jsonschema.Draft7Validator(schema)
 pages=read(root/'INDEX.json')['pages'];allconcepts=[];rows=[];refs=[]
 for page in pages:
  name=page['dir'];p=root/name/'output/concepts.json';cm=read(p);concepts=cm['concepts'];allconcepts.extend(concepts)
  endpoints={e['ref']:e for e in map(json.loads,(root/name/'inputs/endpoints.jsonl').read_text(encoding='utf-8-sig').splitlines())}
  row={'page':name,'schema_errors':[{'pointer':'/'+ '/'.join(map(str,e.absolute_path)),'message':e.message} for e in validator.iter_errors(cm)],'contract_issues':[]}
  for i,c in enumerate(concepts):
   entity=c['concept_type']=='business_entity';owner=c.get('belongs_to_entity') or c['canonical_name'].split('-',1)[0]
   if 'api_refs' not in c:row['contract_issues'].append(f'{i}: missing api_refs')
   if entity and c.get('page_refs')!=[name]:row['contract_issues'].append(f'{i}: page_refs not current page')
   if not entity and 'page_refs' in c:row['contract_issues'].append(f'{i}: operation has page_refs')
   if not entity and not c.get('belongs_to_entity') and '-' not in c['canonical_name']:row['contract_issues'].append(f'{i}: no entity association')
   for field in ['api_refs','evidence_refs']:
    for ref in c.get(field,[]):
     r={'page':name,'pointer':f'/concepts/{i}/{field}','concept':c['canonical_name'],'field':field,'ref':ref,**locate(ref,root,name,endpoints)}
     if field=='api_refs':r['static_template']=r.get('endpoint',{}).get('path','').startswith('/static/') if r.get('endpoint') else False
     refs.append(r)
   for j,a in enumerate(c.get('attributes',[])):
    for ref in a.get('source_refs',[]):refs.append({'page':name,'pointer':f'/concepts/{i}/attributes/{j}/source_refs','concept':c['canonical_name'],'attribute':a['name'],'field':'source_refs','ref':ref,**locate(ref,root,name,endpoints)})
  rows.append(row)
 names={c['canonical_name'] for c in allconcepts if c['concept_type']=='business_entity'}
 associations=[{'operation':c['canonical_name'],'owner':c.get('belongs_to_entity') or c['canonical_name'].split('-',1)[0]} for c in allconcepts if c['concept_type']=='operation']
 missing=[x for x in associations if x['owner'] not in names]
 return {'pages':rows,'schema_pass':sum(not r['schema_errors'] for r in rows),'page_count':len(rows),'concept_count':len(allconcepts),'attribute_assertions':sum(len(c.get('attributes',[])) for c in allconcepts),'reference_counts':dict(collections.Counter(r['status'] for r in refs)),'static_api_refs':sum(r.get('static_template',False) for r in refs),'unresolved_entity_associations':missing,'references':refs}, {'concepts':allconcepts}

def score():
 for row in read(MANIFEST)['files']:
  if sha(pathlib.Path(row['file']))!=row['sha256']:raise RuntimeError('Frozen hash mismatch: '+row['file'])
 copy=read(O/'claudecode-original-task/input-manifest.json')
 for row in copy['files']:
  for root in ROOTS.values():
   if sha(root/row['path'])!=row['sha256']:raise RuntimeError('Inputs changed')
 g=read(GOLD);policy=read(POLICY)['policy']
 # Symmetric, explicit Chinese translations. Ambiguous size/dimensions remains pending.
 extra={'product.name':['名称'],'product.model_number':['型号'],'product.color':['颜色'],'product.style':['款式'],'category.item_count':['商品数量']}
 for a in g['attributes']:a['aliases']+=extra.get(a['entity']+'.'+a['id'],[])
 witnesses={}
 for kind in ['entities','attributes']:
  for fact in g[kind]:
   hits=[]
   for p in ROOTS['claudecode'].glob('*/inputs/page.aria.yml'):
    for i,line in enumerate(p.read_text(encoding='utf-8-sig').splitlines(),1):
     if any(r['quote'].strip()==line.strip() for r in fact['evidence_refs']):hits.append({'file':str(p.relative_to(ROOTS['claudecode'])),'line':i,'quote':line})
   if not hits:raise RuntimeError('Gold fact lacks prepared-input witness: '+legacy.key(kind,fact))
   witnesses[legacy.key(kind,fact)]=hits
 results={}
 for run,root in ROOTS.items():
  audit_result,cm=audit(root);claims,excluded=legacy.normalize(cm,g,policy)
  metrics={}
  for kind in ['entities','attributes']:
   target={legacy.key(kind,x) for x in g[kind]};pred={c['canonical'] for c in claims if c['section']==kind and '?' not in c['canonical']}
   metrics[kind]={'matched':sorted(pred&target),'missing':sorted(target-pred),'hits':len(pred&target),'denominator':len(target),'recall':len(pred&target)/len(target)}
  pending=[{'section':c['section'],'canonical':c['canonical']} for c in claims if '?' in c['canonical']]
  results[run]={'core_recall':metrics,'audit':audit_result,'pending_mapping':pending,'excluded':excluded}
 report={'frozen_at':read(MANIFEST)['frozen_at'],'freeze_sha256':sha(MANIFEST),'input_files_identical':True,'pages':copy['pages'],'scope':'Paired original 26-page outputs; core fact recall + literal citation audit. Literal absence is not semantic falsity. No full precision or relation penalty: schema never requested entity-entity relations.','model_provenance':'User reports both DeepSeek V4 Flash; not independently confirmed from both run logs.','elapsed_seconds':{'claudecode':{'value':2100,'source':'user approximate 35 minutes'},'aqi':None},'results':results}
 report['gold_witnesses_in_identical_inputs']=witnesses
 write(O/'paired-original.v1.json',report)
 lines=['# 阿器 vs Claude Code：相同织语素材的实体抽取核验','', '两边均为原始 26 页任务，81 个输入/任务文件哈希相同。以下为事后历史输出评估；评分在查看候选后冻结，不冒充预注册实验。','', '| 指标 | 阿器 | Claude Code |','|---|---:|---:|']
 for kind in ['entities','attributes']:
  a=results['aqi']['core_recall'][kind];b=results['claudecode']['core_recall'][kind];lines.append(f"| 核心 {kind} 声明召回 | {a['hits']}/{a['denominator']} | {b['hits']}/{b['denominator']} |")
 for key,label in [('schema_pass','schema 合格页'),('concept_count','逐页概念声明数（未去重）'),('attribute_assertions','逐页属性声明数（未去重）'),('static_api_refs','静态模板 api_refs 次数')]:lines.append(f"| {label} | {results['aqi']['audit'][key]} | {results['claudecode']['audit'][key]} |")
 for status in sorted(set(results['aqi']['audit']['reference_counts'])|set(results['claudecode']['audit']['reference_counts'])):lines.append(f"| 引用定位：{status} | {results['aqi']['audit']['reference_counts'].get(status,0)} | {results['claudecode']['audit']['reference_counts'].get(status,0)} |")
 lines+=['','## 解释与限制','','- 实体/属性按既有核心答案与对称别名去重，不用输出数量衡量质量。未映射和范围外概念在 JSON 保留，不自动判错；未计算完整精确率。','- 树锚点按原文 role 和 label 定位；未命中可能是概括性标签，不自动等同幻觉。E 编号存在只说明可定位，不能证明支持业务声明。','- 两边 schema 均只要求实体和操作，未要求实体间关系；不给双方未输出关系扣分。操作归属另审计。','- 分母来自既有 Drive trace 核心答案；逐项输入可见性和语义证据另见人工复核记录，不能拿全站答案给这 26 页直接扣分。','- 模型一致性目前据用户说明，尚无双方服务端运行日志核实；Claude Code 约35分钟由用户报告，阿器耗时未知，不比较速度胜负。','', '复算：`python evaluate_original_task.py score`（依赖 jsonschema）。','',f"冻结 SHA256：`{report['freeze_sha256']}`。"]
 (O/'paired-original.v1.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print('\n'.join(lines))
if __name__=='__main__':freeze() if sys.argv[1]=='freeze' else score()
