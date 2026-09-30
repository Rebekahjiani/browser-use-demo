"""Build a shared UI-only extraction package. No ground truth is copied to agents."""
import json, re, hashlib
from pathlib import Path
ROOT = Path(__file__).parent
BU = Path(r'C:\Users\bulin\browser-use-demo\benchmark\outputs\20260928-160723-422670')
DRIVE = Path(r'C:\Users\bulin\appweave\logs\03-context-model\260928-145535\llm\entity-extract')
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2), encoding='utf-8')
def build(name, pages):
    dest=ROOT/'packages'/name
    index=[]
    for i,(url,source,body) in enumerate(pages):
        page=f'{i:03d}'
        lines=[x.strip() for x in body.splitlines() if x.strip()]
        refs=[{'ref':f'U{j:05d}','text':s} for j,s in enumerate(lines)]
        write(dest/page/'inputs'/'page.json',{'url':url,'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
        write(dest/page/'inputs'/'ui.json',refs)
        (dest/page/'output').mkdir(exist_ok=True)
        index.append({'dir':page,'url':url})
    write(dest/'INDEX.json',index)
    for f in ['TASK.md','schema.json']:
        (dest/f).write_bytes((ROOT/f).read_bytes())
    write(dest/'manifest.json',{'track':'ui-only-v1','pages':len(index),'schema_sha256':hashlib.sha256((ROOT/'schema.json').read_bytes()).hexdigest(),'task_sha256':hashlib.sha256((ROOT/'TASK.md').read_bytes()).hexdigest(),'notes':'All captured snapshots retained; repeated URLs are not new page types. Browser-use AX and drive ARIA retain different sensor provenance.'})
    return dest
def main():
    bu=[]
    for d in sorted((BU/'snapshots').iterdir()):
        p=d/'accessibility.json'
        if not p.exists(): continue
        nodes=read(p)['nodes']
        body='\n'.join(str(n.get('role',{}).get('value',''))+': '+str(n.get('name',{}).get('value','')) for n in nodes if not n.get('ignored') and n.get('name',{}).get('value'))
        bu.append((read(d/'metadata.json')['url'],p,body))
    drive=[]
    for d in sorted(DRIVE.iterdir()):
        p=d/'inputs'/'page.json'
        if not p.exists(): continue
        tree=next(iter(list((d/'inputs').glob('page.aria.yml'))+list((d/'inputs').glob('page.axtree.md'))),None)
        if tree: drive.append((read(p)['url'],tree,tree.read_text(encoding='utf-8-sig')))
    for name,rows in [('browser-use',bu),('drive',drive)]: print(build(name,rows))
if __name__=='__main__': main()
