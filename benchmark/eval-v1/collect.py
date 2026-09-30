"""Usage: python collect.py packages/browser-use. Validates before collecting."""
import sys
from pathlib import Path
from prepare import read, write
from jsonschema import Draft7Validator
def collect(root):
    schema=read(root/'schema.json'); result={'concepts':[],'relations':[],'pages':[]}
    for page in read(root/'INDEX.json'):
        pid=page['dir']; data=read(root/pid/'output'/'concepts.json')
        Draft7Validator(schema).validate(data)
        refs={r['ref'] for r in read(root/pid/'inputs'/'ui.json')}
        def verify(values):
            if not values or not set(values)<=refs: raise ValueError(f'{pid}: invalid/empty refs {values}')
            return [pid+':'+v for v in values]
        for c in data['concepts']:
            if c['api_refs']: raise ValueError('UI-only requires api_refs=[]')
            c['evidence_refs']=verify(c['evidence_refs'])
            if c['concept_type']=='business_entity' and c['page_refs']!=[pid]: raise ValueError('page_refs must match page')
            for a in c.get('attributes',[]): a['source_refs']=verify(a['source_refs'])
            result['concepts'].append(c)
        for r in data['relations']:
            r['evidence_refs']=verify(r['evidence_refs']); result['relations'].append(r)
        result['pages'].append({'dir':pid,'notes':data['notes']})
    entities={c['canonical_name'] for c in result['concepts'] if c['concept_type']=='business_entity'}
    for c in result['concepts']:
        if c['concept_type']=='operation' and c['belongs_to_entity'] not in entities: raise ValueError('orphan operation')
    for r in result['relations']:
        if r['source_entity'] not in entities or r['target_entity'] not in entities: raise ValueError('orphan relation')
    write(root/'collected.json',result)
    return result
if __name__=='__main__': collect(Path(sys.argv[1]))
