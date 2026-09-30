"""Read-only snapshot pairing and recorded capture/cost metadata; not full replay fidelity."""
import html,json,re,pathlib
from score import O,ROOTS,Page,read,write,sha
def main():
 result={};sources={pathlib.Path(__file__)}
 for run,root in ROOTS.items():
  rows=[]
  for ax in sorted(root.glob('*/accessibility.json')):
   p=Page(ax);h=ax.parent/'page.html';sources.update([ax,h]);text=h.read_text(encoding='utf-8-sig');m=re.search(r'<title[^>]*>(.*?)</title>',text,re.S|re.I)
   title=html.unescape(m.group(1)).strip() if m else None
   ax_title=next(n['name']['value'] for n in p.nodes if n.get('role',{}).get('value')=='RootWebArea')
   rows.append({'snapshot':ax.parent.name,'url':p.url,'html_title':title,'ax_title':ax_title,'titles_agree':title==ax_title,'screenshot_exists':any(ax.parent.glob('*.png'))})
  trace=root.parent.parent if run=='drive' else root.parent/'trace/26_09_29_11_51_42-min'
  summary=trace/'trace.segments.summary.json';sources.add(summary);capture=read(summary)
  cost={'capture_wall_seconds':(capture['stoppedAt']-capture['startedAt'])/1000,'capture_wall_definition':'recorder stoppedAt minus startedAt; not agent execution time','token_usage':None,'billed_cost':None,'llm_calls':None,'unknown_reason':'No common verified usage/billing ledger; missing is not zero'}
  if run=='browser-use':
   rp=root.parent/'result.json';sources.add(rp);r=read(rp);cost.update(exploration_seconds=r['exploration_s'],agent_steps=r['steps'],tool_attempts=r['tool_attempts'],errors=r['errors'])
  result[run]={'snapshot_pairs':rows,'title_pairs_agree':sum(r['titles_agree'] for r in rows),'snapshot_count':len(rows),'capture_summary':capture,'cost':cost}
 report={'scope':'Recorded segment health, AX/HTML title agreement, wall time; not complete action-response fidelity or efficiency ranking','sources':[{'file':str(p),'sha256':sha(p)} for p in sorted(sources)],'results':result}
 write(O/'quality-cost.v1.json',report)
 print(json.dumps({k:{'title_pairs_agree':v['title_pairs_agree'],'snapshot_count':v['snapshot_count'],'capture_wall_seconds':v['cost']['capture_wall_seconds']} for k,v in result.items()},indent=2))
if __name__=='__main__':main()
