"""Audit discovered links; path categories are candidates, not visited page types."""
from pilot_stats import D, ROOT, read
from urllib.parse import urlsplit, parse_qsl
from collections import Counter
import json
def main():
    trail=read(next((D/'drive').glob('*-trail.json')))
    rows=[]
    for url,node in trail['nodes']:
        if node.get('status')!='pending':continue
        u=urlsplit(url); p=u.path
        if 'product_compare' in p:kind='compare'
        elif '/checkout/' in p:kind='cart_or_checkout'
        elif '/customer/' in p:kind='account'
        elif '/catalogsearch/' in p:kind='search'
        elif p.endswith('.html'):kind='html_product_or_category_unverified'
        elif p=='/':kind='home_or_home_parameters'
        else:kind='other_unverified'
        rows.append({'url':url,'candidate':kind,'query_keys':[k for k,v in parse_qsl(u.query)],'origin':u.netloc})
    result={'pending_count':len(rows),'exact_unique_urls':len({r['url'] for r in rows}),'candidate_groups':dict(Counter(r['candidate'] for r in rows)),'origins':dict(Counter(r['origin'] for r in rows)),'with_query':sum(bool(r['query_keys']) for r in rows),'nodes':rows,'limitation':'Discovered links only. No endpoint was visited by this audit. Candidate path classification is not verified page coverage.'}
    out=ROOT/'reports'/'frontier-audit.json'
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='nodes'},ensure_ascii=True,indent=2))
if __name__=='__main__':main()
