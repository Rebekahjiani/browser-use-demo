"""Freeze and score arbitrary Shopping AX/HTML runs without changing historical files."""
import argparse
import collections
import hashlib
import importlib.util
import json
import pathlib
import shutil
import statistics

HERE = pathlib.Path(__file__).resolve().parent
BENCHMARK = HERE.parent


def read(path):
    return json.loads(pathlib.Path(path).read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def write(path, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    path = pathlib.Path(path)
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError(f'Refuse to replace different artifact: {path}')
    else:
        path.write_bytes(data)


def engine(path):
    spec = importlib.util.spec_from_file_location('frozen_ui_engine', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def resolve(base, value):
    path = pathlib.Path(value)
    return (path if path.is_absolute() else base / path).resolve()


def validate_runs(spec, base):
    runs = spec.get('runs', [])
    if not runs or len({r['id'] for r in runs}) != len(runs):
        raise ValueError('Nonempty runs with unique IDs required')
    out = []
    roots = set()
    for run in runs:
        root = resolve(base, run['snapshots'])
        if root in roots:
            raise ValueError('Duplicate snapshot root is not an independent run')
        roots.add(root)
        files = sorted(root.glob('*/accessibility.json'))
        if not files:
            raise ValueError(f'No AX snapshots: {root}')
        for path in files:
            if not (path.parent / 'page.html').is_file():
                raise ValueError(f'Missing paired HTML: {path}')
        if not run.get('strategy'):
            raise ValueError('Each run requires strategy')
        out.append({**run, 'snapshots': str(root), 'files': [str(p) for p in files],
                    'artifacts': [str(resolve(base, p)) for p in run.get('artifacts', [])]})
    return out


def freeze(spec_path, output):
    spec_path = pathlib.Path(spec_path).resolve()
    output = pathlib.Path(output).resolve()
    if output.exists():
        raise RuntimeError('Bundle already exists; use a new directory/version')
    spec = read(spec_path)
    runs = validate_runs(spec, spec_path.parent)
    gold_path = resolve(spec_path.parent, spec['gold'])
    mapping_path = resolve(spec_path.parent, spec['mapping'])
    engine_path = resolve(spec_path.parent, spec['engine']) if spec.get('engine') else BENCHMARK / 'coverage-v3/score.py'
    ui = engine(engine_path)
    gold = read(gold_path)
    mapping = read(mapping_path)
    if not gold['facts'] or len({f['id'] for f in gold['facts']}) != len(gold['facts']):
        raise ValueError('Gold must have unique nonempty facts')
    paths = {spec_path, gold_path, mapping_path, engine_path}
    if mapping.get('source_export'):
        source = resolve(mapping_path.parent, mapping['source_export'])
        if digest(source) != mapping['source_sha256']:
            raise RuntimeError('DB source hash disagrees with mapping')
        paths.add(source)
    for item in mapping.get('review_sources', []):
        source = resolve(mapping_path.parent, item['file'])
        if digest(source) != item['sha256']:
            raise RuntimeError('DB review source changed')
        paths.add(source)
    for row in mapping['facts']:
        for ref in row.get('db_refs', []):
            if ref.get('ui_ref'):
                ui.verify_ref(ref['ui_ref'])
                source = pathlib.Path(ref['ui_ref']['file']).resolve()
                paths.update([source, source.parent / 'page.html'])
            if ref.get('file'):
                source = pathlib.Path(ref['file']).resolve()
                obj = read(source)
                for key in ref['pointer'].split('/')[1:]:
                    obj = obj[int(key)] if isinstance(obj, list) else obj[key]
                if 'value' in ref and obj != ref['value']:
                    raise RuntimeError('DB witness mismatch')
                paths.add(source)
    for fact in gold['facts']:
        for ref in fact['reference_witness']['evidence_refs']:
            ui.verify_ref(ref)
            paths.add(pathlib.Path(ref['file']).resolve())
            paths.add(pathlib.Path(ref['file']).resolve().parent / 'page.html')
    for run in runs:
        paths.update(pathlib.Path(p) for p in run['artifacts'])
        for name in run['files']:
            path = pathlib.Path(name)
            ui.Page(path)  # fail closed on malformed snapshots
            paths.update([path, path.parent / 'page.html'])
            metadata = path.parent / 'metadata.json'
            if metadata.exists():
                paths.add(metadata)
    hashes = [{'file': str(p), 'sha256': digest(p)} for p in sorted(paths)]
    output.mkdir(parents=True)
    shutil.copyfile(engine_path, output / 'ui_engine.py')
    shutil.copyfile(gold_path, output / 'gold.json')
    shutil.copyfile(mapping_path, output / 'mapping.json')
    shutil.copyfile(__file__, output / 'score_runs.py')
    write(output / 'runs.json', {'runs': runs, 'experiment': spec.get('experiment', {})})
    local = ['ui_engine.py', 'gold.json', 'mapping.json', 'score_runs.py', 'runs.json']
    write(output / 'freeze.json', {'inputs': hashes,
          'bundle_files': [{'file': p, 'sha256': digest(output / p)} for p in local],
          'scope': gold['scope'], 'status': 'finite witnessed contract; not complete website gold'})
    print(f'Frozen {len(runs)} runs, {len(hashes)} source files: {output}')


def verify(bundle):
    manifest = read(bundle / 'freeze.json')
    for item in manifest['bundle_files']:
        if digest(bundle / item['file']) != item['sha256']:
            raise RuntimeError('Bundle changed: ' + item['file'])
    for item in manifest['inputs']:
        if digest(item['file']) != item['sha256']:
            raise RuntimeError('Frozen input changed: ' + item['file'])
    return manifest


def project(facts, mapping):
    return {r['physical_key'] for r in mapping if r.get('physical_key') and r['fact_id'] in facts}


def evaluate_run(run, gold, mapping, ui):
    pages = [ui.Page(pathlib.Path(p)) for p in run['files']]
    rows = []
    first = {}
    for fact in gold['facts']:
        hits = []
        for index, page in enumerate(pages):
            refs = ui.fullmatch(page, fact)
            if refs:
                for ref in refs:
                    ui.verify_ref(ref)
                first.setdefault(fact['id'], index)
                hits.append({'url': page.url, 'snapshot_index': index, 'refs': refs})
        rows.append({'id': fact['id'], 'kind': fact['kind'], 'supported': bool(hits),
                     'status': 'supported' if hits else 'not_demonstrated', 'evidence': hits})
    target = {f['id'] for f in gold['facts'] if f['kind'] == 'attribute'}
    supported = {r['id'] for r in rows if r['supported']}
    db_target = project(target, mapping)
    db_hit = project(target & supported, mapping)
    metrics = {kind: {'hit': sum(r['supported'] for r in rows if r['kind'] == kind),
                      'denominator': sum(r['kind'] == kind for r in rows)}
               for kind in sorted({r['kind'] for r in rows})}
    metrics['DB_verified_subset'] = {'hit': len(db_hit), 'denominator': len(db_target)}
    curve = []
    for i, page in enumerate(pages):
        metadata = page.path.parent / 'metadata.json'
        curve.append({'snapshot_index': i, 'url': page.url,
                      'captured_at': read(metadata).get('captured_at') if metadata.exists() else None,
                      'attributes_supported': sum(first.get(fid, len(pages)) <= i for fid in target)})
    return {'strategy': run['strategy'], 'conditions': run.get('conditions', {}),
            'snapshots': len(pages), 'unknown_page_types': sum(p.type == 'unknown' for p in pages),
            'metrics': metrics, 'facts': rows, 'coverage_curve': curve,
            'curve_order': 'sorted snapshot paths; no claim of action-normalized elapsed time'}


def summarize(results):
    groups = collections.defaultdict(list)
    for result in results.values():
        groups[result['strategy']].append(result)
    out = {}
    for strategy, runs in groups.items():
        metrics = {}
        for kind in runs[0]['metrics']:
            values = [r['metrics'][kind]['hit'] / r['metrics'][kind]['denominator']
                      for r in runs if r['metrics'][kind]['denominator']]
            metrics[kind] = {'mean': statistics.mean(values) if values else None,
                             'sample_stdev': statistics.stdev(values) if len(values) > 1 else None,
                             'min': min(values) if values else None,
                             'max': max(values) if values else None}
        out[strategy] = {'runs': len(runs), 'metrics': metrics}
    return out


def score(bundle, destination):
    bundle = pathlib.Path(bundle).resolve()
    verify(bundle)
    if digest(__file__) != digest(bundle / 'score_runs.py'):
        raise RuntimeError('Use this bundle\'s frozen score_runs.py to replay its rules')
    ui = engine(bundle / 'ui_engine.py')
    gold = read(bundle / 'gold.json')
    mapping = read(bundle / 'mapping.json')['facts']
    spec = read(bundle / 'runs.json')
    results = {r['id']: evaluate_run(r, gold, mapping, ui) for r in spec['runs']}
    out = {'freeze_sha256': digest(bundle / 'freeze.json'), 'scope': gold['scope'],
           'experiment': spec['experiment'], 'results': results, 'summary': summarize(results),
           'limitations': ['No complete DB denominator, CM precision, or trace fidelity claim.',
                          'Not demonstrated is not false; missing evidence is not website absence.',
                          'Declared conditions do not prove environment reset or budget equivalence.',
                          'Repeated snapshot paths are observations, not independent business states.',
                          'No composite ranking. Historical/post-hoc gold remains diagnostic.']}
    destination = pathlib.Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    write(destination / 'results.json', out)
    lines = ['# Batch Shopping evidence coverage', '', '| Run | Strategy | UI attributes | DB subset |',
             '|---|---|---:|---:|']
    for name, result in results.items():
        a, db = result['metrics']['attribute'], result['metrics']['DB_verified_subset']
        lines.append(f"| {name} | {result['strategy']} | {a['hit']}/{a['denominator']} | {db['hit']}/{db['denominator']} |")
    lines += ['', 'Finite witnessed scope. No complete website, semantic precision or causal ranking.',
              '', 'Freeze SHA256: ' + out['freeze_sha256']]
    report = destination / 'results.md'
    content = '\n'.join(lines) + '\n'
    if report.exists() and report.read_text(encoding='utf-8') != content:
        raise RuntimeError('Refuse to replace different report')
    report.write_text(content, encoding='utf-8')
    print(content)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    f = commands.add_parser('freeze')
    f.add_argument('--spec', required=True)
    f.add_argument('--bundle', required=True)
    s = commands.add_parser('score')
    s.add_argument('--bundle', required=True)
    s.add_argument('--output', required=True)
    args = parser.parse_args()
    if args.command == 'freeze':
        freeze(args.spec, args.bundle)
    else:
        score(args.bundle, args.output)
