"""Prepare prospective finite Shopping contract using independent current witnesses."""
import copy
import hashlib
import json
import pathlib
import score

ROOT = pathlib.Path(__file__).resolve().parent
B = ROOT.parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    gold = copy.deepcopy(read(B / 'coverage-v3/gold.v1.json'))
    mapping = copy.deepcopy(read(B / 'ground-truth-vnext/db-ui-mapping.v2.json'))
    pages = [score.Page(p) for p in sorted((B / 'ground-truth-vnext/site-verification-20261008').glob('*/accessibility.json'))]
    for fact in gold['facts']:
        old_url = fact['reference_witness']['url']
        matched = next((p for p in pages if p.url == old_url and score.fullmatch(p, fact)), None)
        if matched is None:
            raise RuntimeError('Same-page independent witness missing: ' + fact['id'])
        refs = score.fullmatch(matched, fact)
        for ref in refs:
            score.verify_ref(ref)
        fact['reference_witness'] = {'url': matched.url, 'evidence_refs': refs}
        fact['precondition'] = 'fresh guest; read-only query submission allowed; no cart writes'
        for row in mapping['facts']:
            if row['fact_id'] == fact['id']:
                row['ui_witness'] = fact['reference_witness']
    relation = {'id': 'category_lists_product', 'kind': 'relation', 'rule': 'product_card_relation',
                'page_types': ['category_list'], 'clauses': [],
                'precondition': 'fresh guest; read-only category browse',
                'interpretation': 'Explicit product-card target under a category listing; no navigation co-occurrence credit'}
    page = next(p for p in pages if p.url == 'http://127.0.0.1:7770/beauty-personal-care.html')
    refs = score.fullmatch(page, relation)
    db_path = B / 'ground-truth-vnext/db-category-witness.20261008.json'
    physical = read(db_path)['rows']
    if not refs or not any(any(str(ref['quote']).endswith('/' + r['request_path']) for ref in refs) for r in physical):
        raise RuntimeError('Relation requires matching DB membership and explicit UI link')
    relation['reference_witness'] = {'url': page.url, 'evidence_refs': refs}
    relation['db_witness'] = {'file': str(db_path), 'pointer': '/rows/0', 'value': physical[0]}
    gold['facts'].append(relation)
    mapping['facts'].append({'fact_id': relation['id'], 'kind': 'relation',
                            'ui_witness': relation['reference_witness'], 'physical_key': None,
                            'status': 'verified_category_product_relation',
                            'storage': 'catalog_category_product.category_id + product_id',
                            'db_refs': [relation['db_witness']]})
    mapping['review_sources'].append({'file': db_path.name, 'sha256': hashlib.sha256(db_path.read_bytes()).hexdigest()})
    gold['scope'] = 'Shopping finite public read-only contract v0.2: 54 facts; not whole website or complete DB'
    gold['changes'].append({'id': relation['id'], 'change': 'explicit structural relation with DB membership witness',
                            'reason': 'Product card link is stronger than page co-occurrence'})
    gold['limitations'] += ['Current independent witnesses captured 2026-10-08 before new explorer candidates.',
                           'Vocabulary inherited from historical analysis: not blind or exhaustive.',
                           'No full DB/website denominator; unresolved EAV defaults, media aliases and graph fields remain outside this finite contract.']
    mapping['limitations'].append('v3 refreshes UI witnesses and adds relation; not complete application dataflow or current DB snapshot audit.')
    for path, value in [(ROOT / 'gold.v1.json', gold), (B / 'ground-truth-vnext/db-ui-mapping.v3.json', mapping)]:
        if path.exists():
            raise RuntimeError('Refuse overwrite: ' + str(path))
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Prepared 54 independent witnessed facts; no new explorer scores read')


if __name__ == '__main__':
    main()
