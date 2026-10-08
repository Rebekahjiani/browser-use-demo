"""Freeze and replay the completed controlled B diagnostic, including attempt lineage."""
import datetime
import json
import pathlib
import faulthandler
faulthandler.dump_traceback_later(30, repeat=True)
import run_b as b
from score_b import score, RULE_FREEZE
from b_cost_ledger import build as build_cost
from b_boundary_audit import audit as audit_boundary
from b_path_diagnostic import diagnostic as path_diagnostic, FREEZE as PATH_FREEZE


def finalize():
    print('Verifying raw and prepared input hashes', flush=True)
    source = b.read(b.SOURCE / 'freeze.json')
    for entry in source['source_files']:
        if b.sha(pathlib.Path(entry['file'])) != entry['sha256']:
            raise RuntimeError('Raw B source changed: ' + entry['file'])
    for entry in source['input_files']:
        if b.sha(b.SOURCE / entry['file']) != entry['sha256']:
            raise RuntimeError('Prepared B input changed: ' + entry['file'])
    result = score()
    print('Scored all pages', result['structural_totals'], flush=True)
    if result['structural_totals']['generated'] != result['structural_totals']['expected']:
        raise RuntimeError('Missing outputs remain; do not mark benchmark complete')
    if result['structural_totals']['schema_valid'] != result['structural_totals']['expected']:
        raise RuntimeError('Schema-invalid outputs remain; preserve them and adjudicate')
    paths = {RULE_FREEZE, b.SOURCE / 'freeze.json', b.REPORTS / 'experiment.json',
             pathlib.Path(__file__), b.HERE / 'run_b.py', b.HERE / 'complete_b.py'}
    for entry in b.read(RULE_FREEZE)['files']:
        paths.add(pathlib.Path(entry['file']))
    lineage = []
    for info in b.read(b.REPORTS / 'experiment.json')['tasks']:
        task = pathlib.Path(info['path'])
        paths.add(task / 'input-freeze.json')
        for entry in b.read(task / 'input-freeze.json')['files']:
            paths.add(task / entry['file'])
        for combination in ['aqi', 'claudecode']:
            paths.update((task / combination / 'entity-extract').glob('*/output/concepts.json'))
            directory = b.REPORTS / info['run'] / combination
            records = []
            for filename in ['process.json', 'error.json', 'interruption.json']:
                if (directory / filename).exists():
                    records.append({'kind': filename, 'data': b.read(directory / filename)})
            if (directory / 'latest-run.json').exists():
                run = b.read(directory / 'latest-run.json')
                records.append({'kind': 'at_original_status', 'data': {'id': run.get('id'), 'status': run.get('status')}})
            for attempt in sorted(directory.glob('attempt-*/attempt.json')):
                record = {'kind': 'attempt', 'data': b.read(attempt)}
                for extra in ['interruption.json', 'error.json', 'process.json']:
                    if (attempt.parent / extra).exists():
                        record[extra] = b.read(attempt.parent / extra)
                if (attempt.parent / 'latest-run.json').exists():
                    run = b.read(attempt.parent / 'latest-run.json')
                    record['at_status'] = {'id': run.get('id'), 'status': run.get('status')}
                records.append(record)
            paths.update(p for p in directory.rglob('*') if p.is_file())
            lineage.append({'trace': info['run'], 'combination': combination, 'records': records})
    if (b.REPORTS / 'recovery-ledger.json').exists():
        paths.add(b.REPORTS / 'recovery-ledger.json')
    before = (b.REPORTS / 'citation-results.json').read_bytes()
    score()
    print('Score replay finished', flush=True)
    if (b.REPORTS / 'citation-results.json').read_bytes() != before:
        raise RuntimeError('Citation score replay differs')
    b.write(b.REPORTS / 'execution-lineage.json', lineage)
    paths.add(b.REPORTS / 'execution-lineage.json')
    build_cost()
    print('Cost ledger finished', flush=True)
    paths.add(b.REPORTS / 'cost-ledger.json')
    paths.add(b.HERE / 'b_cost_ledger.py')
    audit_boundary()
    print('Boundary audit finished', flush=True)
    paths.add(b.REPORTS / 'boundary-audit.json')
    paths.add(b.HERE / 'b_boundary_audit.py')
    path_diagnostic()
    print('Path diagnostic finished', flush=True)
    for filename in ['path-diagnostic.json', 'path-diagnostic.md']:
        paths.add(b.REPORTS / filename)
    paths.add(PATH_FREEZE)
    for item in b.read(PATH_FREEZE)['files']:
        paths.add(pathlib.Path(item['file']))
    for filename in ['citation-results.json', 'citation-results.md', 'structural-audit.json']:
        paths.add(b.REPORTS / filename)
    manifest = {'frozen_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'totals': result['structural_totals'], 'citation_replay': 'byte-identical',
                'files': [{'file': str(p), 'sha256': b.sha(p)} for p in sorted(paths)],
                'limitations': result['interpretation']}
    destination = b.REPORTS / 'completed.freeze.json'
    if destination.exists():
        raise RuntimeError('Completed freeze already exists; do not overwrite')
    b.write(destination, manifest)
    faulthandler.cancel_dump_traceback_later()
    print(json.dumps({'totals': manifest['totals'], 'files': len(paths), 'replay': 'byte-identical'}))


if __name__ == '__main__':
    finalize()
