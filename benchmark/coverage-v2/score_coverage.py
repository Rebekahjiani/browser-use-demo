"""Freeze and score a closed, independently witnessed read-only UI contract."""
import pathlib,json,sys,datetime,hashlib
from collections import Counter
from audit_traces import read,write,sha,visible_nodes,classify,matches,RUNS
O=pathlib.Path(__file__).resolve().parent

def freeze():
 dst=O/'common-readonly.v1.json';manifest=O/'common-readonly.freeze.v1.json'
 if dst.exists() or manifest.exists():raise RuntimeError('v1 already frozen; create a new version')
 g=read(O/'common-readonly.v1.draft.json');assert not g['unverified'];g['status']='frozen_explicit_core_UI_contract';g['frozen_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 for f in g['facts']:
  for r in f['evidence_refs']:
   value=read(pathlib.Path(r['file']))
   for part in r['pointer'].split('/')[1:]:value=value[int(part)] if isinstance(value,list) else value[part]
   assert value==r['quote']
 write(dst,g);paths={dst,O/'score_coverage.py',O/'audit_traces.py',O/'test_coverage.py',pathlib.Path(g['db_reference'])}
 for root in [O/'site-verification',O/'site-verification-extra']:paths.update(p for p in root.rglob('*') if p.is_file())
 for name,root in RUNS.items():
  folder=root/'drive/screenshots' if name=='drive' else root/'snapshots'
  paths.update(p for p in folder.rglob('*') if p.is_file() and p.name in ['accessibility.json','page.html','metadata.json'])
 rows=[dict(file=str(p),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(paths)]
 write(manifest,dict(frozen_at=g['frozen_at'],files=rows,scope='UI snapshots only; not complete raw network trace semantics'))
 print('frozen',len(rows),'files')

def score():
 mf=O/'common-readonly.freeze.v1.json';m=read(mf)
 for x in m['files']:
  if sha(pathlib.Path(x['file']))!=x['sha256']:raise RuntimeError('Hash mismatch: '+x['file'])
 g=read(O/'common-readonly.v1.json');out={}
 for name,root in RUNS.items():
  folder=root/'drive/screenshots' if name=='drive' else root/'snapshots';pages=[]
  for d in sorted(folder.iterdir()):
   if not d.is_dir() or not (d/'accessibility.json').is_file():continue
   a=read(d/'accessibility.json');web=next(n for n in a['nodes'] if n.get('role',{}).get('value')=='RootWebArea');url=next(x['value']['value'] for x in web['properties'] if x['name']=='url');pages.append(dict(url=url,type=classify(url,(d/'page.html').read_text(encoding='utf-8-sig')),nodes=visible_nodes(a),ax_file=str(d/'accessibility.json')))
  facts=[]
  for f in g['facts']:
   hits=[]
   for p in pages:
    refs=matches(p,f)
    if refs:hits.append(dict(url=p['url'],evidence_refs=refs))
   facts.append(dict(id=f['id'],kind=f['kind'],observed=bool(hits),status='observed_UI_witness' if hits else 'not_observed_in_UI_snapshots',evidence=hits,db_mapping=f.get('db_mapping')))
  metrics={k:dict(observed=sum(f['observed'] for f in facts if f['kind']==k),denominator=sum(f['kind']==k for f in facts)) for k in sorted({f['kind'] for f in facts})}
  for v in metrics.values():v['recall']=v['observed']/v['denominator']
  out[name]=dict(metrics=metrics,facts=facts)
 report=dict(title='共同只读核心契约：历史trace的UI证据覆盖',frozen_at=m['frozen_at'],scored_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),freeze_sha256=sha(mf),results=out,limitations=g['limitations']+['These are UI evidence recalls for a closed core contract, not full website coverage or full trace/API semantic coverage.','Historical runs had different starting cart states, permissions, prompt/input treatment; do not rank algorithm quality causally.','Controls count as observed affordances, not executed transitions. No composite score.','Existing Context Models are not rescored as controlled A outcomes; uniform construction remains pending.'])
 write(O/'common-readonly-coverage.v1.json',report)
 lines=['# 共同只读核心契约：历史 trace 的 UI 证据覆盖','','按用户决定，只评全新访客可只读访问的商品、搜索筛选和空购物车。**分母为同一份55项核心契约，不是全站全集。** 各维度分开，不合成总分。','','| 维度 | Drive 命中/分母 | browser-use 命中/分母 | Drive recall | browser-use recall |','|---|---:|---:|---:|---:|']
 for k,v in out['drive']['metrics'].items():
  u=out['browser-use-20260929']['metrics'][k];lines.append(f"| {k} | {v['observed']}/{v['denominator']} | {u['observed']}/{u['denominator']} | {v['recall']:.2%} | {u['recall']:.2%} |")
 lines+=['','## 逐项矩阵','','| 项目 | Drive | browser-use |','|---|---|---|']
 for i,f in enumerate(out['drive']['facts']):lines.append(f"| {f['id']} | {'有证据' if f['observed'] else '未见'} | {'有证据' if out['browser-use-20260929']['facts'][i]['observed'] else '未见'} |")
 lines+=['','## 解释','','- Drive的商品字段更丰富；browser-use额外记录空购物车页面和状态。相同分母能描述材料差异，但初始状态/权限不同，不能单独归因于算法。','- 两边缺少搜索结果、筛选/排序/翻页结果状态；看到控件不等于覆盖操作结果。','- Drive非空header只作为历史额外观察，不计空购物车状态，也不推断cart-line。','- 本报告只审计原始UI快照，network/rawbody中可能包含的补充事实没有当作不存在。','- 商品特殊属性由UI字段/值证明，有些只存在于描述表格；DB字段映射尚未全部确认，不能称每一项都是独立物理列。','- 页面类型和状态目录是明确定义的有限目标集，不称全站类型/状态全集。','','## 冻结与复算','',f"冻结：{m['frozen_at']}；计分：{report['scored_at']}。",'',f"Manifest SHA256：`{sha(mf)}`。",'','```powershell','python test_coverage.py','python score_coverage.py score','```','','每项原始AX定位与quote见JSON。标准答案的独立网站证据见common-readonly.v1.json；原始历史trace未修改。']
 (O/'common-readonly-coverage.v1.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');print(json.dumps({k:v['metrics'] for k,v in out.items()},ensure_ascii=False,indent=2))
if __name__=='__main__':freeze() if sys.argv[1]=='freeze' else score()
