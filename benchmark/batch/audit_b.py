"""Structural/page-local reference audit; does not infer semantic accuracy."""
import collections
import datetime
import json
import pathlib
import re
import jsonschema
import run_b as b


def reference(ref, tree, endpoints, page):
    if not isinstance(ref, str):
        return 'invalid_type'
    if ref.startswith('page.aria.yml:'):
        anchor = ref.split(':', 1)[1].strip()
        if not anchor:
            return 'empty_anchor'
        # Literal, role:name, and role "name" styles are audited separately.
        if anchor in tree:
            return 'literal_match'
        if ':' in anchor:
            role, name = anchor.split(':', 1)
            if re.search(r'-\s+' + re.escape(role) + r'\s+"[^"\n]*' + re.escape(name) + r'[^"\n]*"', tree):
                return 'role_name_match'
        return 'unresolved_anchor'
    if re.fullmatch(r'E\d+', ref):
        return 'endpoint_match' if ref in endpoints else 'unknown_endpoint'
    if ref == page:
        return 'page_match'
    return 'unsupported_syntax'


def audit():
    jobs, all_pages = [], []
    for info in b.read(b.REPORTS / 'experiment.json')['tasks']:
        task = pathlib.Path(info['path'])
        b.verify_task_inputs(task)
        for combination in ['aqi', 'claudecode']:
            root = task / combination / 'entity-extract'
            validator = jsonschema.Draft7Validator(b.read(root / 'schema.json'))
            pages = []
            for page in b.read(root / 'INDEX.json')['pages']:
                directory = root / page['dir']
                output = directory / 'output/concepts.json'
                item = {'trace': info['run'], 'combination': combination, 'page': page['dir'],
                        'output': str(output), 'exists': output.exists(), 'schema_errors': [], 'references': []}
                if output.exists():
                    item['sha256'] = b.sha(output)
                    try:
                        data = b.read(output)
                        item['schema_errors'] = [{'path': list(e.absolute_path), 'message': e.message}
                                                 for e in validator.iter_errors(data)]
                        tree = (directory / 'inputs/page.aria.yml').read_text(encoding='utf-8-sig')
                        lines = (directory / 'inputs/endpoints.jsonl').read_text(encoding='utf-8-sig').splitlines()
                        endpoints = set()
                        for line in lines:
                            entry = json.loads(line)
                            endpoints.update(v for v in entry.values() if isinstance(v, str) and re.fullmatch(r'E\d+', v))
                        for concept in data.get('concepts', []):
                            for field in ['evidence_refs', 'api_refs', 'page_refs']:
                                for ref in concept.get(field, []):
                                    item['references'].append({'concept': concept.get('canonical_name'), 'field': field,
                                         'ref': ref, 'status': reference(ref, tree, endpoints, page['dir'])})
                            for attribute in concept.get('attributes', []):
                                for ref in attribute.get('source_refs', []):
                                    item['references'].append({'concept': concept.get('canonical_name'),
                                         'attribute': attribute.get('name'), 'field': 'source_refs', 'ref': ref,
                                         'status': reference(ref, tree, endpoints, page['dir'])})
                        item['concepts'] = len(data.get('concepts', []))
                        item['attributes'] = sum(len(c.get('attributes', [])) for c in data.get('concepts', []))
                    except (ValueError, TypeError, AttributeError) as exc:
                        item['schema_errors'].append({'path': [], 'message': str(exc)})
                pages.append(item)
            counts = collections.Counter(r['status'] for p in pages for r in p['references'])
            jobs.append({'trace': info['run'], 'combination': combination, 'expected': len(pages),
                         'generated': sum(p['exists'] for p in pages),
                         'schema_valid': sum(p['exists'] and not p['schema_errors'] for p in pages),
                         'reference_status_counts': dict(counts)})
            all_pages.extend(pages)
    result = {'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'totals': {'expected': len(all_pages), 'generated': sum(p['exists'] for p in all_pages),
                         'schema_valid': sum(p['exists'] and not p['schema_errors'] for p in all_pages)},
              'jobs': jobs, 'pages': all_pages,
              'limitations': ['Anchor matches validate page-local text support, not entity ownership or semantics.',
                              'Unresolved references require adjudication; they are not automatically hallucinations.',
                              'Recovery outputs must be reported separately from original attempt success.']}
    b.write(b.REPORTS / 'structural-audit.json', result)
    return result


if __name__ == '__main__':
    print(json.dumps(audit()['totals']))
