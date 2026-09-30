"""Versioned recall diagnostic. Freeze all inputs before scoring; never infer citations."""
import datetime
import hashlib
import json
import sys
from pathlib import Path
import score_existing_cm as base

O = Path(__file__).resolve().parent
MANIFEST = O / 'existing-cm.freeze.v2.json'

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def normalize(cm):
    # Explicit aliases reviewed against the actual candidate wording.
    base.ATTR.update({'qty数量输入': 'quantity', 'priceshopbyprice区间': 'price_range'})
    base.OP['高级搜索提交'] = 'search.advanced'
    result = base.candidate(cm)
    unmapped = []
    for e in cm.get('entities', []) + [e for e in cm.get('concepts', []) if e.get('concept_type') == 'business_entity']:
        name = e.get('canonical_name', e.get('name', ''))
        ent = base.ENTITY.get(base.n(name))
        for a in e.get('attributes', []):
            attr = a.get('name', '')
            if name == '价格区间' and base.n(attr) == 'range':
                result['attributes'].add('category.price_range')
            elif not ent or base.n(attr) not in base.ATTR:
                unmapped.append({'entity': name, 'attribute': attr})
    for op in cm.get('operations', []) + [e for e in cm.get('concepts', []) if e.get('concept_type') == 'operation']:
        name = op.get('canonical_name', op.get('name', ''))
        desc = op.get('description', '')
        # One operation may describe two separate visible controls, but generic search alone earns neither.
        if base.n(name) in {'商品搜索', '产品搜索', 'search'}:
            result['operations'].discard('search.advanced')
            if 'Advanced Search' in desc:
                result['operations'].add('search.advanced')
            if '首页搜索框' in desc:
                result['operations'].add('search.basic')
        if base.n(name) not in base.OP:
            unmapped.append({'operation': name})
    return result, unmapped

def freeze():
    if MANIFEST.exists():
        raise RuntimeError('Already frozen; use a new version')
    paths = [Path(__file__), O/'score_existing_cm.py', O/'test_existing_cm_v2.py',
             O/'common-readonly.v2.json', O/'common-readonly-coverage.v2.json',
             O/'common-readonly.freeze.v2.json', *base.CM.values()]
    data = {'frozen_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'files': [{'file': str(p), 'sha256': sha(p)} for p in paths]}
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def score():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    for row in manifest['files']:
        if sha(row['file']) != row['sha256']:
            raise RuntimeError('Hash mismatch: '+row['file'])
    evidence = json.loads((O/'common-readonly.freeze.v2.json').read_text(encoding='utf-8'))
    for row in evidence['files']:
        if sha(row['file']) != row['sha256']:
            raise RuntimeError('Evidence hash mismatch: '+row['file'])
    report = {'freeze_sha256': sha(MANIFEST), 'frozen_at': manifest['frozen_at'],
              'scope': 'Existing CM canonical fact recall; T occurrence is not validation of candidate citations. No precision or harness ranking.', 'results': {}}
    lines = ['# 现有 CM 共同核心事实召回 v2', '',
             'v1 漏映射 Qty、Price 区间、独立价格区间实体及高级搜索。此版替代 v1；两个候选已见后修订映射，属于事后诊断。先冻结规则、候选和证据，再计分。', '',
             '| 运行 | 维度 | 共同 G | trace T | CM 命中 G | T 与 CM 同时命中 |',
             '|---|---|---:|---:|---:|---:|']
    for run, path in base.CM.items():
        c, unmapped = normalize(json.loads(path.read_text(encoding='utf-8-sig')))
        rows = {}
        for kind, g in base.gold_sets().items():
            t = {f for f in g if base.observed(run, f)}
            rows[kind] = {'G': len(g), 'T': len(t), 'C_in_G': len(c[kind]&g),
                          'T_and_C': len(t&c[kind]), 'T_missing_from_C': sorted(t-c[kind]),
                          'C_without_G': sorted(c[kind]-g)}
            v = rows[kind]
            lines.append(f"| {run} | {kind} | {v['G']} | {v['T']} | {v['C_in_G']} | {v['T_and_C']} |")
        report['results'][run] = {'metrics': rows, 'canonical': {k: sorted(v) for k,v in c.items()}, 'unmapped_assertions': unmapped}
    lines += ['', '属性和关系要求结构化声明；不把实体级引用当作属性级证据。关系没有结构化输出，两边均为零。',
              '价格分面 range 可归一到 category.price_range；分面 itemCount 不等于分类商品总数。高级搜索条件不自动变成商品属性。',
              '同一搜索操作明确写出首页搜索框与 Advanced Search 时分别命中两个控件；控件不代表执行成功。',
              '未映射或分母外声明保留在 JSON，不自动判为错误。此报告不计算精确率，不替代逐断言证据核验，也不用于维度 B 的 harness 排名。',
              '', '复算：`python test_existing_cm_v2.py`，然后 `python score_existing_cm_v2.py score`。',
              '', 'Manifest SHA256：`'+report['freeze_sha256']+'`。']
    (O/'existing-cm-common-g.v2.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (O/'existing-cm-common-g.v2.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    freeze() if sys.argv[1] == 'freeze' else score()
