"""Post-hoc compatibility diagnostic for observed chained AX references."""
import datetime
import json
import pathlib
import sys
import run_b as b
sys.path.insert(0, str(b.HERE.parent / 'harness-comparison'))
import score_citations_v4 as rules

FREEZE = b.REPORTS / 'path-diagnostic.rules.freeze.json'


def has_chain(node, roles, byline):
    ancestors = [byline[line]['role'] for line in node['parents']] + [node['role']]
    if not roles or ancestors[-1] != roles[-1]:
        return False
    cursor = 0
    for role in ancestors[:-1]:
        if cursor < len(roles) - 1 and role == roles[cursor]:
            cursor += 1
    return cursor == len(roles) - 1


def support(ref, markers, nodes):
    if not isinstance(ref, str) or not ref.startswith('page.aria.yml:') or not markers:
        return {'status': 'unresolved'}
    tokens = ref[len('page.aria.yml:'):].split(':')
    known_roles = {node['role'] for node in nodes}
    roles = []
    while tokens and tokens[0] in known_roles:
        roles.append(tokens.pop(0))
    if len(roles) < 2:
        return {'status': 'unresolved'}
    label = ':'.join(tokens).strip()
    byline = {node['line']: node for node in nodes}
    containers = [node for node in nodes if has_chain(node, roles, byline)]
    if not containers:
        return {'status': 'unresolved'}
    if label:
        for marker in markers:
            if rules.clean(label) not in rules.clean(marker['name']):
                continue
            for container in containers:
                if container['line'] == marker['line'] or container['line'] in marker['parents']:
                    return {'status': 'supported_chain_with_label', 'marker': marker, 'container': container,
                            'reason': 'Ordered ancestor roles and literal field label locate this field on this page.'}
    else:
        # A label-free selector is supported only if EVERY selected node locates
        # this same field. A broad StaticText selector cannot borrow a price hit.
        if all(any(container['line'] == marker['line'] or container['line'] in marker['parents']
                   for marker in markers) for container in containers):
            return {'status': 'supported_field_specific_role_path', 'containers': containers,
                    'reason': 'All nodes selected by this role path locate this field; no unrelated selected nodes.'}
    return {'status': 'unresolved'}


def freeze():
    if FREEZE.exists():
        raise RuntimeError('Compatibility rules already frozen')
    paths = [pathlib.Path(__file__), b.HERE / 'test_b_path.py', pathlib.Path(rules.__file__)]
    b.write(FREEZE, {'frozen_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    'timing': 'Post-hoc diagnostic motivated by observed chained references; not preregistered.',
                    'files': [{'file': str(path), 'sha256': b.sha(path)} for path in paths]})


def diagnostic():
    for item in b.read(FREEZE)['files']:
        if b.sha(pathlib.Path(item['file'])) != item['sha256']:
            raise RuntimeError('Frozen compatibility rule changed')
    primary = b.read(b.REPORTS / 'citation-results.json')
    tasks = {task['run']: pathlib.Path(task['path']) for task in b.read(b.REPORTS / 'experiment.json')['tasks']}
    jobs = []
    for job in primary['jobs']:
        root = tasks[job['trace']] / job['combination'] / 'entity-extract'
        cache, assertions = {}, []
        for claim in job['claims']:
            page = claim['page']
            if page not in cache:
                cache[page] = rules.parse_tree(root / page / 'inputs/page.aria.yml')
            nodes = cache[page]
            markers = rules.field_markers(claim['canonical'], nodes)
            refs = [{'ref': ref['ref'], **support(ref['ref'], markers, nodes)} for ref in claim['refs']]
            supported = claim['status'] == 'supported_own_citation' or any(ref['status'].startswith('supported_') for ref in refs)
            assertions.append({'page': page, 'canonical': claim['canonical'], 'primary_status': claim['status'],
                               'compatible_supported': supported, 'supplementary_refs': refs})
        matched = {claim['canonical'] for claim in assertions if claim['compatible_supported']}
        available = set(job['input_conditioned_marker_recall']['available'])
        jobs.append({'trace': job['trace'], 'combination': job['combination'], 'primary_hits': job['fixed_core_recall']['hits'],
                     'compatible_hits': len(matched), 'fixed_denominator': job['fixed_core_recall']['denominator'],
                     'available_denominator': len(available), 'matched': sorted(matched), 'assertions': assertions})
    result = {'primary_results_sha256': b.sha(b.REPORTS / 'citation-results.json'),
              'compatibility_rule_freeze_sha256': b.sha(FREEZE), 'jobs': jobs,
              'limitations': ['Post-hoc format compatibility diagnostic; original v4 scores remain unchanged.',
                             'No precision claim, no response-field ownership inference, no repair of generated references.']}
    b.write(b.REPORTS / 'path-diagnostic.json', result)
    lines = ['# B 路径引用兼容诊断（事后补充）', '',
             '历史v4评分保留。本诊断处理观测到的多角色路径引用；路径带label时必须定位到本页该字段，无label时所有选中节点必须仅定位同一字段。模糊路径不自动得分。', '',
             '| trace | 组合 | 原v4命中 | 兼容路径后命中 | 输入可见字段 |', '|---|---|---:|---:|---:|']
    for job in jobs:
        lines.append(f"| {job['trace']} | {job['combination']} | {job['primary_hits']}/{job['fixed_denominator']} | {job['compatible_hits']}/{job['fixed_denominator']} | {job['available_denominator']} |")
    lines += ['', '这是生成期间针对已观测格式提出并冻结的事后诊断，不是预注册主指标，也不是完整语义准确率。']
    (b.REPORTS / 'path-diagnostic.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'freeze':
        freeze()
    else:
        print(json.dumps({'jobs': len(diagnostic()['jobs'])}))
