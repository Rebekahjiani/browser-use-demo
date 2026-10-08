"""Parameterized controlled B diagnostic using the unchanged historical v4 rules."""
import datetime
import json
import pathlib
import statistics
import sys
import run_b as b

sys.path.insert(0, str(b.HERE.parent / 'harness-comparison'))
import score_citations_v4 as rules
from audit_b import audit

RULE_FREEZE = b.REPORTS / 'scoring-rules.freeze.json'


def freeze_rules():
    paths = [pathlib.Path(__file__), pathlib.Path(rules.__file__), pathlib.Path(rules.legacy.__file__),
             rules.GOLD, rules.POLICY, b.HERE / 'audit_b.py']
    manifest = {'frozen_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'scope': 'Historical v4 core attribute own-citation support; not full semantic precision.',
                'timing': 'Rules reuse historical v4; this parameterized wrapper was frozen during generation.',
                'source_input_freeze_sha256': b.sha(b.SOURCE / 'freeze.json'),
                'files': [{'file': str(p), 'sha256': b.sha(p)} for p in paths]}
    if RULE_FREEZE.exists():
        raise RuntimeError('Scoring rules already frozen; never overwrite')
    b.write(RULE_FREEZE, manifest)


def score():
    frozen = b.read(RULE_FREEZE)
    for entry in frozen['files']:
        if b.sha(pathlib.Path(entry['file'])) != entry['sha256']:
            raise RuntimeError('Frozen scoring code or rule changed: ' + entry['file'])
    if b.sha(b.SOURCE / 'freeze.json') != frozen['source_input_freeze_sha256']:
        raise RuntimeError('Source input freeze changed')
    structural = audit()
    gold, policy = b.read(rules.GOLD), b.read(rules.POLICY)['policy']
    # Identical aliases already declared by historical v4, not fitted to this batch.
    extra = {'product.name': ['名称'], 'product.model_number': ['型号'], 'product.color': ['颜色'],
             'product.style': ['款式'], 'category.item_count': ['商品数量'], 'product.size': ['尺寸']}
    for attribute in gold['attributes']:
        attribute['aliases'] += extra.get(attribute['entity'] + '.' + attribute['id'], [])
    targets = {rules.legacy.key('attributes', a) for a in gold['attributes']}
    jobs = []
    for info in b.read(b.REPORTS / 'experiment.json')['tasks']:
        task = pathlib.Path(info['path'])
        for combination in ['aqi', 'claudecode']:
            root = task / combination / 'entity-extract'
            claims, pending, opportunities, page_metrics = [], [], set(), []
            for page in b.read(root / 'INDEX.json')['pages']:
                directory = root / page['dir']
                nodes = rules.parse_tree(directory / 'inputs/page.aria.yml')
                endpoints = {r['ref']: r for r in map(json.loads, (directory / 'inputs/endpoints.jsonl').read_text(encoding='utf-8-sig').splitlines())}
                markers = {key: rules.field_markers(key, nodes) for key in targets}
                available = {key for key, value in markers.items() if value}
                opportunities.update(available)
                output = directory / 'output/concepts.json'
                supported_on_page = set()
                if output.exists():
                    try:
                        normalized, excluded = rules.legacy.normalize(b.read(output), gold, policy)
                    except (ValueError, TypeError, KeyError, AttributeError) as exc:
                        pending.append({'page': page['dir'], 'reason': 'unparseable_output', 'error': str(exc)})
                        normalized = []
                    for claim in normalized:
                        if claim['section'] != 'attributes':
                            continue
                        canonical = claim['canonical']
                        if canonical not in targets:
                            pending.append({'page': page['dir'], 'canonical': canonical, 'reason': 'outside_core_or_unmapped'})
                            continue
                        refs = [{'ref': ref, **rules.supported_ref(ref, markers[canonical], nodes, endpoints)}
                                for ref in claim['original'].get('source_refs', [])]
                        supported = any(r['status'] == 'supported' for r in refs)
                        if supported:
                            supported_on_page.add(canonical)
                        claims.append({'page': page['dir'], 'canonical': canonical, 'raw_name': claim['original']['name'],
                                       'status': 'supported_own_citation' if supported else 'unresolved', 'refs': refs,
                                       'field_markers_present': bool(markers[canonical])})
                page_metrics.append({'page': page['dir'], 'available': sorted(available),
                                     'supported': sorted(supported_on_page), 'output_exists': output.exists()})
            supported = {c['canonical'] for c in claims if c['status'] == 'supported_own_citation'}
            structural_job = next(j for j in structural['jobs'] if j['trace'] == info['run'] and j['combination'] == combination)
            jobs.append({'trace': info['run'], 'combination': combination,
                         'expected_pages': structural_job['expected'], 'generated_pages': structural_job['generated'],
                         'schema_valid_pages': structural_job['schema_valid'],
                         'fixed_core_recall': {'hits': len(supported), 'denominator': len(targets),
                                               'ratio': len(supported) / len(targets), 'matched': sorted(supported)},
                         'input_conditioned_marker_recall': {'hits': len(supported & opportunities), 'denominator': len(opportunities),
                                               'ratio': len(supported & opportunities) / len(opportunities) if opportunities else None,
                                               'available': sorted(opportunities)},
                         'page_field_support': {'hits': sum(len(p['supported']) for p in page_metrics),
                                                'denominator': sum(len(p['available']) for p in page_metrics)},
                         'supported_core_assertions': sum(c['status'] == 'supported_own_citation' for c in claims),
                         'unresolved_core_assertions': sum(c['status'] == 'unresolved' for c in claims),
                         'claims': claims, 'outside_core_or_unmapped': pending, 'pages': page_metrics})
    result = {'scoring_rules_freeze_sha256': b.sha(RULE_FREEZE), 'structural_totals': structural['totals'], 'jobs': jobs,
              'interpretation': ['Fixed core is the unchanged 32-field historical vocabulary, distinct from A value coverage.',
                                 'Input-conditioned denominator uses field markers in supplied pages, not whole-site truth.',
                                 'Endpoint-only references stay unresolved without attribute-specific semantic adjudication.',
                                 'Neither unresolved assertions nor out-of-core assertions are automatically false positives.',
                                 'Recovery and original execution success must be reported separately.']}
    b.write(b.REPORTS / 'citation-results.json', result)
    lines = ['# 受控 B 结果：逐页产物及核心属性自身引用支持', '',
             '沿用历史 v4 的 32 项核心词表和引用规则。下表是保守引用支持诊断，不是完整语义准确率或全站覆盖率。', '',
             '| trace | 组合 | 已生成 / 计划 | schema通过 | 固定核心命中 | 输入中可见字段命中 |',
             '|---|---|---:|---:|---:|---:|']
    for job in jobs:
        fixed, conditional = job['fixed_core_recall'], job['input_conditioned_marker_recall']
        lines.append(f"| {job['trace']} | {job['combination']} | {job['generated_pages']}/{job['expected_pages']} | {job['schema_valid_pages']} | {fixed['hits']}/{fixed['denominator']} | {conditional['hits']}/{conditional['denominator']} |")
    lines += ['', '原始失败、超时或中断记录保留在各组合目录；attempt-* 是缺失页补跑，不能把最终完整性写成首轮成功率。',
              '输入可见字段只按既有 marker 规则判定；字段 label 支持不等于值级 DB 核验，接口编号存在不等于字段属于该实体。',
              '未定位引用、非核心属性及实体归属保留待审，不据此计算完整 precision/F1。']
    (b.REPORTS / 'citation-results.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'freeze':
        freeze_rules()
    else:
        print(json.dumps(score()['structural_totals']))
