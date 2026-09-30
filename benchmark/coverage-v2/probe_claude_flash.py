"""Connectivity-only probe; credentials stay in the child environment, never in report."""
import json, os, pathlib, shutil, subprocess, datetime
O=pathlib.Path(__file__).resolve().parent.parent/'harness-comparison'
O.mkdir(exist_ok=True)
s=json.loads(pathlib.Path(r'C:\Users\bulin\artifacttrace\templates\at-template\.at\settings.json').read_text(encoding='utf-8-sig'))
p=s['modelProviders']['tlaic'];env=os.environ.copy()
env.update(ANTHROPIC_BASE_URL=p['baseUrl'].removesuffix('/v1'),ANTHROPIC_API_KEY=p['apiKey'],ANTHROPIC_MODEL='sophnet/DeepSeek-V4-Flash-0731',CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1')
cmd=[shutil.which('claude'),'-p','Reply exactly BENCHMARK_SMOKE_OK. Do not use tools.','--bare','--model','sophnet/DeepSeek-V4-Flash-0731','--tools','','--strict-mcp-config','--output-format','json']
r={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base_url':env['ANTHROPIC_BASE_URL'],'requested_model':env['ANTHROPIC_MODEL'],'purpose':'unscored connectivity smoke; no benchmark input'}
try:
 c=subprocess.run(cmd,cwd=O,env=env,capture_output=True,text=True,encoding='utf-8',timeout=55)
 r.update(exit_code=c.returncode,stdout=c.stdout,stderr=c.stderr)
except subprocess.TimeoutExpired as e:
 r.update(status='timeout_55s',stdout=(e.stdout or b'').decode('utf-8','replace') if isinstance(e.stdout,bytes) else e.stdout,stderr=(e.stderr or b'').decode('utf-8','replace') if isinstance(e.stderr,bytes) else e.stderr)
raw=json.dumps(r,ensure_ascii=False,indent=2).replace(p['apiKey'],'[REDACTED]')
(O/'claude-flash-smoke.v1.json').write_text(raw,encoding='utf-8')
print(raw)
