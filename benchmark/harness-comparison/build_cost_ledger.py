"""Sanitized recorded cost/provenance; no prices estimated, no raw prompts copied."""
import collections,datetime,hashlib,json,pathlib
O=pathlib.Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 at=pathlib.Path(r'C:\Users\bulin\artifacttrace\templates\at-template\tasks\09-21-bu-shopping\.at\run\run_20260928_072333_05a3\trace.jsonl')
 rows=[json.loads(l) for l in at.read_text(encoding='utf-8').splitlines()];completed={r['model_call_id']:r for r in rows if r['event_type']=='model_call_completed'}
 models=collections.Counter(r['tail']['algorithm']['algo_id'] for r in rows if r['event_type']=='model_call_started');tokens=collections.Counter()
 for r in completed.values():tokens.update(r.get('head',{}).get('token_usage',{}))
 started=next(r for r in rows if r['event_type']=='model_call_started')
 bound=any(x.get('data_type')=='user_input' and '260928-145535' in x.get('content','') for x in started['tail']['inputs'])
 aqi={'source_file':str(at),'sha256':sha(at),'bound_to_original_task':bound,'model_routes':dict(models),'wall_seconds':(max(r['timestamp'] for r in rows)-min(r['timestamp'] for r in rows))/1000,'completed_model_calls':len(completed),'recorded_token_usage':dict(tokens),'billing_cost':None,'usage_caveat':'AT event totals; input includes repeated context; cache accounting and billing not verified','event_counts':dict(collections.Counter(r['event_type'] for r in rows))}
 cc=pathlib.Path(r'C:\Users\bulin\.claude\projects\C--Users-bulin-artifacttrace-templates-at-template-tasks-09-21-bu-shopping\a2a8c566-42f8-4fc8-97e5-196fb10d82f7.jsonl')
 active=False;begin=None;end=None;models=collections.Counter();byid={};starts=0
 for line in cc.read_text(encoding='utf-8').splitlines():
  r=json.loads(line);m=r.get('message',{});c=m.get('content',[]) if isinstance(m,dict) else [];text=c if isinstance(c,str) else '\n'.join(x.get('text','') for x in c if isinstance(x,dict) and x.get('type')=='text')
  if r.get('type')=='user' and text.startswith('请读 ') and 'claudecode-original-task' in text:
   active=True;starts+=1
   if begin is None:begin=r['timestamp']
  if not active:continue
  if r.get('type')=='assistant' and m.get('model'):
   models[m['model']]+=1;mid=m.get('id')
   if mid:
    u=m.get('usage',{});rec=byid.setdefault(mid,{})
    for k in ['input_tokens','output_tokens','cache_read_input_tokens','cache_creation_input_tokens']:
     if isinstance(u.get(k),(int,float)):rec[k]=max(rec.get(k,0),u[k])
  if r.get('type')=='assistant' and text.startswith('全部 26 页已完成'):end=r['timestamp'];break
 totals=collections.Counter()
 for u in byid.values():totals.update(u)
 seconds=(datetime.datetime.fromisoformat(end.replace('Z','+00:00'))-datetime.datetime.fromisoformat(begin.replace('Z','+00:00'))).total_seconds()
 claude={'source_file':str(cc),'sha256':sha(cc),'model_message_counts':dict(models),'unique_assistant_message_ids':len(byid),'recorded_token_usage':dict(totals),'first_task_timestamp':begin,'completion_timestamp':end,'wall_seconds':seconds,'explicit_task_prompt_count':starts,'user_reported_seconds':2100,'billing_cost':None,'usage_caveat':'Local message usage deduplicated by message.id, per-field maximum across updates. Not validated as gateway billing; assistant messages are not guaranteed one-to-one HTTP requests. Wall interval includes pauses/retries/compaction.'}
 report={'scope':'Extraction only; do not mix with exploration cost','aqi':aqi,'claudecode':claude,'comparability':'Both logs identify DeepSeek-V4-Flash-0731. Harness context, retries and token/cache reporting differ. No cost or speed winner asserted from incomparable active-time/accounting.'}
 (O/'cost-ledger.v1.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='scope'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
