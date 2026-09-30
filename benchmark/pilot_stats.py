"""Read-only pilot audit; run with Python. Raw AX snapshots use identical rules."""
import json, hashlib, re
from pathlib import Path
from collections import Counter
from urllib.parse import urlsplit, urlunsplit
ROOT=Path(__file__).parent
D=Path(r'C:\Users\bulin\appweave\outputs\01-evidence\26_09_28_10_40_34-min')
B=ROOT/'outputs'/'20260928-160723-422670'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def classify(url,html):
    path=urlsplit(url).path
    for key,typ in [('catalogsearch/advanced','advanced_search'),('catalogsearch/result','search_results'),('checkout/cart','cart'),('customer/account','account'),('/contact','contact')]:
        if key in path:return typ
    if path=='/':return 'home'
    if 'catalog-product-view' in html:return 'product_detail'
    if 'catalog-category-view' in html:return 'category_list'
    return 'unknown'
def audit(name,root,folder):
    pages=[]; bad=[]
    for d in sorted(folder.iterdir()):
        if not d.is_dir():continue
        try:
            p=d/'accessibility.json'; ax=read(p)['nodes']
            top=next(n for n in ax if n.get('role',{}).get('value')=='RootWebArea')
            url=next((x['value']['value'] for x in top.get('properties',[]) if x['name']=='url'),'')
            if (d/'metadata.json').exists():url=read(d/'metadata.json')['url']
            html=(d/'page.html').read_text(encoding='utf-8-sig')
            signature=[(n.get('role',{}).get('value'),n.get('name',{}).get('value',''),[(v['name'],v.get('value',{}).get('value')) for v in n.get('properties',[]) if v['name'] in ['expanded','selected','checked']]) for n in ax if not n.get('ignored')]
            typ=classify(url,html)
            pages.append({'directory':str(d),'url':url,'type':typ,'ax_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'observed_state_hash':hashlib.sha256(json.dumps([url,signature],ensure_ascii=False).encode()).hexdigest(),'files':{f:(d/f).exists() and (d/f).stat().st_size>0 for f in ['page.html','accessibility.json','screenshot.png']}})
        except Exception as e:bad.append({'path':str(d),'error':str(e)})
    segments=[]
    for p in root.rglob('trace.segment.*.jsonl'):
        count=0; errors=0
        with p.open(encoding='utf-8-sig') as f:
            for line in f:
                if not line.strip():continue
                try:json.loads(line); count+=1
                except ValueError:errors+=1
        segments.append({'path':str(p),'parsed_lines':count,'invalid_lines':errors})
    summaries=[{'path':str(p),'data':read(p)} for p in root.rglob('trace.segments.summary.json')]
    result={'strategy':name,'rule_version':'pilot-v1','snapshots':len(pages),'snapshot_urls':len({p['url'] for p in pages}),'page_types':dict(Counter(p['type'] for p in pages)),'observed_ax_states':len({p['observed_state_hash'] for p in pages}),'business_states':None,'repeat_visit_rate':None,'snapshot_errors':bad,'pages':pages,'trace_segments':segments,'trace_summaries':summaries,'limitations':['AX state hash includes data values; not independent business-state count','Snapshots are samples, not visit events; repeat visits unknown','Parseability does not prove temporal/network completeness']}
    if name=='browser-use':
        result['native_result']=read(root/'result.json')
        actions=[json.loads(s) for s in (root/'actions.jsonl').read_text().splitlines() if s]
        result['tool_attempts_by_name']=dict(Counter(a['tool'] for a in actions if a.get('phase')=='attempt'))
    else:
        trail=read(next((root/'drive').glob('*-trail.json')))
        cp=read(next((root/'drive').glob('*-checkpoint.json')))
        result['native_result']={'steps':cp['stepCount'],'visited_urls':len(cp['visited']),'trail_statuses':dict(Counter(n[1].get('status','unknown') for n in trail['nodes'])),'elapsed_s':(trail['endedAt']-trail['startedAt'])/1000}
    return result
def main():
    out=ROOT/'reports';out.mkdir(exist_ok=True)
    reports=[audit('drive',D,D/'drive'/'screenshots'),audit('browser-use',B,B/'snapshots')]
    for r in reports:(out/(r['strategy']+'-pilot.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 现有两份trace统一盘点（pilot-v1）','','本报告自动生成。页面类型按URL及HTML页面类分类；分类仍需抽样复核。未知项不补猜测。','','|指标|drive|browser-use|','|---|---:|---:|']
    for key in ['snapshots','snapshot_urls','observed_ax_states']:
        lines.append(f"|{key}|{reports[0][key]}|{reports[1][key]}|")
    for r in reports:
        lines+=['',f"## {r['strategy']}",'',f"页面类型（按快照计）：`{json.dumps(r['page_types'],ensure_ascii=False)}`",f"无效快照目录：{len(r['snapshot_errors'])}；分段JSONL文件：{len(r['trace_segments'])}；无效行：{sum(s['invalid_lines'] for s in r['trace_segments'])}",f"缺失/空证据文件：{sum(not v for p in r['pages'] for v in p['files'].values())}"]
    lines+=['','## 解释边界','','- observed_ax_states是URL＋可见AX角色/文本/选中展开状态的哈希数量，商品值或异步文本变化也会增加它，不能直接称为业务独立状态。','- 周期快照不代表访问事件；重复访问率、完整业务状态数本轮不报告。','- 两边都有原始AX文件，可以统一AX观测分析；此前只使用drive ARIA备料并非唯一选择。','- 原生visited计数与有快照证据的URL数分别报告；发现链接不等于访问页面。','- segment可解析不代表无数据丢失；必须结合trace summary中的失败分段与切换缺口。','- 具体页面、源路径、哈希、原生统计和每段解析结果见同目录两个JSON。']
    (out/'pilot-comparison.md').write_text('\n'.join(lines),encoding='utf-8')
    print('\n'.join(lines))
if __name__=='__main__':main()
