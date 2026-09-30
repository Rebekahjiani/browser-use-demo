"""Read-only schema repair simulation and sanitized local Claude log provenance."""
import collections,datetime,hashlib,json,pathlib
import jsonschema
from evaluate_original_task import O,ROOTS,read,write
root=ROOTS['aqi'];validator=jsonschema.Draft7Validator(read(root/'schema.json'))
fields=conflicts=passed=0
for p in root.glob('*/output/concepts.json'):
 obj=read(p)
 for c in obj['concepts']:
  for a in c.get('attributes',[]):
   if 'description' in a:
    fields+=1;conflicts+=int('note' in a);a['note']=a.pop('description')
 passed+=not bool(list(validator.iter_errors(obj)))
sessions=[]
for p in (pathlib.Path.home()/'.claude/projects').glob('*/*.jsonl'):
 raw=p.read_text(encoding='utf-8',errors='replace')
 if 'claudecode-original-task' not in raw:continue
 starts=[];finishes=[];models=collections.Counter();active=False
 for line in raw.splitlines():
  try:r=json.loads(line)
  except ValueError:continue
  m=r.get('message',{});content=m.get('content',[]) if isinstance(m,dict) else []
  text=content if isinstance(content,str) else '\n'.join(x.get('text','') for x in content if isinstance(x,dict) and x.get('type')=='text')
  if r.get('type')=='user' and text.startswith('请读 ') and 'claudecode-original-task' in text:
   starts.append(r.get('timestamp'));active=True
  if active and isinstance(m,dict) and m.get('model'):models[m['model']]+=1
  if active and r.get('type')=='assistant' and text.startswith('全部 26 页已完成'):finishes.append(r.get('timestamp'))
 if starts and finishes:
  seconds=(datetime.datetime.fromisoformat(finishes[-1].replace('Z','+00:00'))-datetime.datetime.fromisoformat(starts[0].replace('Z','+00:00'))).total_seconds()
  sessions.append({'source_file':str(p),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'explicit_task_starts':starts,'completion_messages':finishes,'assistant_model_field_counts_after_first_task':dict(models),'wall_seconds_first_prompt_to_completion':seconds,'interpretation':'Wall interval includes repeated prompts, pauses and compactions; not active inference time. Local assistant model fields corroborate model name, not provider billing proof.'})
write(O/'supplementary-audit.v1.json',{'aqi_schema_repair_simulation':{'method':'in-memory attribute.description rename to attribute.note','fields':fields,'conflicts':conflicts,'schema_pass_pages':passed,'source_outputs_modified':False},'claude_local_log_provenance':sessions,'user_reported_elapsed_seconds':2100})
print(json.dumps({'repaired_schema_pass_pages':passed,'sessions':sessions},ensure_ascii=False,indent=2))
