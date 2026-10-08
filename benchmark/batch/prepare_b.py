"""Uniform, immutable per-state B packages; no candidate-informed selection."""
import collections
import hashlib
import json
import pathlib
import re
import shutil
from urllib.parse import urlsplit

HERE = pathlib.Path(__file__).resolve().parent
BENCHMARK = HERE.parent
TEMPLATE = pathlib.Path(r'C:\Users\bulin\appweave\logs\03-context-model\260928-145535\llm\entity-extract')


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def tree(raw):
    nodes = raw['nodes']
    by_id = {n['nodeId']: n for n in nodes}
    root = next(n for n in nodes if n.get('role', {}).get('value') == 'RootWebArea')
    seen, lines = set(), []

    def walk(node, depth):
        if node['nodeId'] in seen:
            return
        seen.add(node['nodeId'])
        role = node.get('role', {}).get('value', '')
        name = re.sub(r'\s+', ' ', str(node.get('name', {}).get('value', ''))).strip()
        emit = not node.get('ignored') and role not in {'InlineTextBox', 'LineBreak'}
        if emit:
            properties = {p['name']: p['value'].get('value') for p in node.get('properties', [])}
            label = ' ' + json.dumps(name, ensure_ascii=False) if name else ''
            attrs = ''.join(f' [{key}={json.dumps(properties[key], ensure_ascii=False)}]'
                            for key in ['level', 'checked', 'selected', 'expanded', 'url'] if key in properties)
            value = node.get('value', {}).get('value')
            if value not in (None, '', name):
                attrs += ' [value=' + json.dumps(value, ensure_ascii=False) + ']'
            lines.append('  ' * depth + '- ' + role + label + attrs)
        for child in node.get('childIds', []):
            if child in by_id:
                walk(by_id[child], depth + int(emit))

    walk(root, 0)
    return '\n'.join(lines) + '\n'


def shape(value, depth=0):
    if depth >= 4:
        return 'nested'
    if isinstance(value, dict):
        return {k: shape(v, depth + 1) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return {'type': 'array', 'sample_shape': shape(value[0], depth + 1) if value else None}
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'boolean'
    if isinstance(value, (int, float)):
        return 'number'
    return 'string'


def pair_network(rows):
    """Without request IDs, accept only a single outstanding exact-URL request."""
    pending = collections.defaultdict(list)
    ambiguous_urls = set()
    pairs = []
    for line, row in enumerate(rows, 1):
        url = row.get('url')
        if row.get('type') == 'request':
            pending[url].append((line, row))
            if len(pending[url]) > 1:
                ambiguous_urls.add(url)
        elif row.get('type') == 'response':
            candidates = pending.pop(url, [])
            if len(candidates) == 1 and url not in ambiguous_urls:
                pairs.append((candidates[0], (line, row)))
            ambiguous_urls.discard(url)
    return pairs


def endpoints_for_run(run):
    source_root = pathlib.Path(run['snapshots'])
    if run['strategy'] == 'drive':
        roots = [source_root.parent.parent]
    else:
        roots = list((source_root.parent / 'trace').iterdir())
    by_page = collections.defaultdict(list)
    sources = set()
    diagnostics = {'candidate_JSON_responses': 0, 'accepted_pairs': 0, 'unreadable_bodies': 0}
    for root in roots:
        for network in root.glob('*_trace/network.jsonl'):
            sources.add(network)
            rows = [json.loads(line) for line in network.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
            diagnostics['candidate_JSON_responses'] += sum(r.get('type') == 'response' and 'json' in r.get('contentType', '') for r in rows)
            for (req_line, request), (resp_line, response) in pair_network(rows):
                parts = urlsplit(request['url'])
                if parts.path.startswith(('/static/', '/media/')) or 'json' not in response.get('contentType', ''):
                    continue
                if request.get('method') != 'GET' or response.get('status') != 200 or not request.get('page_url'):
                    continue
                body_name = response.get('bodyPath')
                if not body_name:
                    continue
                body = (network.parent / body_name).resolve()
                if not body.is_relative_to(network.parent.resolve()):
                    raise ValueError('Body path escapes recorded profile')
                try:
                    payload = read(body)
                except (OSError, ValueError):
                    diagnostics['unreadable_bodies'] += 1
                    continue
                sources.add(body)
                by_page[request['page_url']].append({
                    'method': request['method'], 'path': parts.path, 'status': response['status'],
                    'content_type': response['contentType'], 'digest': {'shape': shape(payload)},
                    'record_shape': shape(payload),
                    'association': 'one outstanding exact-URL request; recorded page_url; no request-ID proof',
                    'source': {'network': str(network), 'request_line': req_line, 'response_line': resp_line,
                               'body': str(body), 'sha256_body': sha(body)}})
                diagnostics['accepted_pairs'] += 1
    return by_page, sources, diagnostics


def main():
    spec = read(HERE / 'experiments/20261008/controlled-v02/runs.json')
    output = HERE / 'b-inputs/controlled-v02'
    if output.exists():
        raise RuntimeError('B inputs already exist; use a new version')
    output.mkdir(parents=True)
    summary = {}
    all_sources = {pathlib.Path(__file__).resolve(), TEMPLATE / 'TASK.md', TEMPLATE / 'schema.json'}
    for run in spec['runs']:
        directory = output / run['id']
        directory.mkdir()
        shutil.copyfile(TEMPLATE / 'TASK.md', directory / 'TASK.md')
        shutil.copyfile(TEMPLATE / 'schema.json', directory / 'schema.json')
        with (directory / 'TASK.md').open('a', encoding='utf-8') as stream:
            stream.write('\n## 本轮材料边界\n每个目录是一个独立页面状态，允许同URL多个状态。'
                         '树由完整AX确定性转换，没有深度/数量/字段名截断。'
                         '不打开网页，不回溯原始trace。API引用只用本页endpoints中实际存在的E编号；'
                         'shape只证明响应结构，不证明实体数据归属；未知来源留空。'
                         '不要读取评分gold或其他构建组合的输出。\n')
        by_page, network_sources, diagnostics = endpoints_for_run(run)
        all_sources.update(network_sources)
        seen = {}
        pages = []
        for ax in sorted(pathlib.Path(run['snapshots']).glob('*/accessibility.json')):
            raw = read(ax)
            web = next(n for n in raw['nodes'] if n.get('role', {}).get('value') == 'RootWebArea')
            url = next(p['value']['value'] for p in web['properties'] if p['name'] == 'url')
            text = tree(raw)
            endpoints = by_page.get(url, [])
            # Same URL + exact normalized tree + response shapes only. Never merge distinct states by URL.
            signature = hashlib.sha256(json.dumps([url, text, [{k: e[k] for k in ['method', 'path', 'status', 'digest']} for e in endpoints]],
                                                  ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            all_sources.update([ax, ax.parent / 'page.html'])
            if signature in seen:
                pages[seen[signature]]['duplicate_snapshots'].append(str(ax.parent))
                continue
            name = f'{len(pages):03d}_state'
            seen[signature] = len(pages)
            inputs = directory / name / 'inputs'
            inputs.mkdir(parents=True)
            (directory / name / 'output').mkdir()
            (inputs / 'page.aria.yml').write_text(text, encoding='utf-8')
            write(inputs / 'page.json', {'url': url, 'title': web['name']['value'], 'route': urlsplit(url).path,
                                       'sources': {'accessibility': str(ax), 'sha256_AX': sha(ax)},
                                       'material_scope': 'recorded UI and conservatively associated JSON responses'})
            unique = {}
            for endpoint in endpoints:
                key = json.dumps({k: endpoint[k] for k in ['method', 'path', 'status', 'digest']}, sort_keys=True)
                unique.setdefault(key, endpoint)
            items = [{'ref': f'E{i + 1:03d}', **e} for i, e in enumerate(unique.values())]
            (inputs / 'endpoints.jsonl').write_text(''.join(json.dumps(e, ensure_ascii=False) + '\n' for e in items), encoding='utf-8')
            pages.append({'dir': name, 'url': url, 'title': web['name']['value'], 'snapshot': str(ax.parent),
                          'duplicate_snapshots': [], 'signature': signature, 'endpoint_count': len(items)})
        write(directory / 'INDEX.json', {'pages': pages, 'deduplication': 'exact prepared input signature within run; no URL-only merging'})
        summary[run['id']] = {'states': len(pages), 'raw_snapshots': sum(1 + len(p['duplicate_snapshots']) for p in pages),
                              'network_diagnostics': diagnostics}
    inputs = [p for p in output.rglob('*') if p.is_file()]
    write(output / 'freeze.json', {'source_files': [{'file': str(p), 'sha256': sha(p)} for p in sorted(all_sources)],
                                 'input_files': [{'file': str(p.relative_to(output)), 'sha256': sha(p)} for p in sorted(inputs)],
                                 'summary': summary, 'scope': 'prospective paired B task packages; not full semantic gold',
                                 'limitations': ['No request IDs in network rows; association remains conservative evidence, not complete causality.',
                                                 'Each combination must receive byte-identical copies; output dirs excluded from input hash.']})
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
