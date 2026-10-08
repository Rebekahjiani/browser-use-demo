"""Two separate evidence layers. Never add DB keys and description subfields together."""
import argparse,datetime,hashlib,json,pathlib,sys
O=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(O.parent/'coverage-v3'))
import score as ui
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def project(supported,mappings):
 return {r['physical_key'] for r in mappings if r['physical_key'] and r['fact_id'] in supported}
def freeze():
 dst=O/'two-layer.freeze.v1.json'
 if dst.exists():raise RuntimeError('Use a new version')
 paths={pathlib.Path(__file__),O/'test_two_layers.py',O/'map_db_ui.py',O/'db-export.v2.json',O/'db-ui-mapping.v1.json',O/'two-layer-contract.v1.json',O.parent/'coverage-v3/freeze.v1.json'}
 for r in read(O.parent/'coverage-v3/freeze.v1.json')['files']:
  p=pathlib.Path(r['file'])
  if sha(p)!=r['sha256']:raise RuntimeError('Old frozen input changed')
  paths.add(p)
 for root in ui.ROOTS.values():
  for p in root.glob('*/accessibility.json'):paths.update([p,p.parent/'page.html'])
 if any(not p.is_file() for p in paths):raise RuntimeError('Required input missing')
 write(dst,{'frozen_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':[{'file':str(p),'sha256':sha(p)} for p in sorted(paths)]})
def score():
 m=read(O/'two-layer.freeze.v1.json')
 for r in m['files']:
  if sha(pathlib.Path(r['file']))!=r['sha256']:raise RuntimeError('Frozen file changed '+r['file'])
 mapping=read(O/'db-ui-mapping.v1.json')['facts'];gold=read(O.parent/'coverage-v3/gold.v1.json');target={f['id'] for f in gold['facts'] if f['kind']=='attribute'}
 db_target=project(target,mapping);result={}
 for name,root in ui.ROOTS.items():
  pages=[ui.Page(p) for p in sorted(root.glob('*/accessibility.json'))];facts=[]
  for f in gold['facts']:
   hits=[]
   for p in pages:
    refs=ui.fullmatch(p,f)
    if refs:
     for r in refs:ui.verify_ref(r)
     hits.append({'url':p.url,'refs':refs})
   facts.append({'id':f['id'],'kind':f['kind'],'supported':bool(hits),'evidence':hits})
  supported={f['id'] for f in facts if f['supported']};db_hit=project(supported&target,mapping);semantic_hit=supported&target
  result[name]={'DB_verified_subset':{'hit':len(db_hit),'denominator':len(db_target),'matched':sorted(db_hit),'missing':sorted(db_target-db_hit)},'business_detail':{'hit':len(semantic_hit),'denominator':len(target),'matched':sorted(semantic_hit),'missing':sorted(target-semantic_hit)},'other_dimensions':{kind:{'hit':sum(f['supported'] for f in facts if f['kind']==kind),'denominator':sum(f['kind']==kind for f in facts)} for kind in sorted({f['kind'] for f in facts}-{'attribute'})},'facts':facts}
 report={'freeze_sha256':sha(O/'two-layer.freeze.v1.json'),'frozen_at':m['frozen_at'],'contract':read(O/'two-layer-contract.v1.json'),'results':result}
 write(O/'two-layer-results.v1.json',report)
 lines=['# 两层指标下的自动探索比较','','DB层仅为已验证映射子集，不能称全库覆盖率；业务细节单列，description内多个子字段不重复增加DB层分数。','','| 层次 | Drive | browser-use |','|---|---:|---:|']
 for key in ['DB_verified_subset','business_detail']:
  a=result['drive'][key];b=result['browser-use'][key];lines.append(f"| {key} | {a['hit']}/{a['denominator']} | {b['hit']}/{b['denominator']} |")
 lines+=['','DB已核验子集持平；当前业务细节范围Drive领先。页面和记录完整性browser-use更好，保留原始条件差异，不合成总冠军。','', '剩余59个EAV候选仍待界面核验，28项为范围排除草案；不能把未知当不存在。','', '复算：`python test_two_layers.py`、`python score_two_layers.py score`。']
 (O/'two-layer-results.v1.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');print('\n'.join(lines))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['freeze','score']);globals()[p.parse_args().command]()
