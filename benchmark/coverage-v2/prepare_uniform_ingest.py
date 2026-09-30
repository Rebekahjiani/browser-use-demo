import pathlib,json,urllib.request,urllib.error
O=pathlib.Path(__file__).resolve().parent
roots={'drive':r'C:\Users\bulin\appweave\outputs\01-evidence\26_09_28_10_40_34-min\DE342E97_trace','browser-use-20260929':r'C:\Users\bulin\browser-use-demo\benchmark\outputs\20260929-115141-231052\trace\26_09_29_11_51_42-min\4680CD0D_trace'}
for name,root in roots.items():
 out=O/'uniform-build'/name/'trace_acquire';out.mkdir(parents=True,exist_ok=True)
 body={'session_root':root,'allowed_roots':[r'C:\Users\bulin\appweave\outputs',r'C:\Users\bulin\browser-use-demo\benchmark\outputs'],'generated_at':'2026-09-29T00:00:00Z'}
 req=urllib.request.Request('http://127.0.0.1:14569/ingest',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=180) as r:d=json.load(r)
  for key,file in [('evidence_catalog','evidence_catalog.json'),('session','evidence_session.json')]: (out/file).write_text(json.dumps(d[key],ensure_ascii=False),encoding='utf-8')
  (out/'ingest-metrics.json').write_text(json.dumps(d['metrics']),encoding='utf-8');print(name,'nodes',len(d['evidence_catalog'].get('nodes',[])),'trees',len(d['session'].get('page_trees',[])),d['metrics'],flush=True)
 except urllib.error.HTTPError as e:
  body=e.read().decode();(out/'ingest-error.txt').write_text(body,encoding='utf-8');print(name,'ingest error',e.code,body[:700],flush=True)
