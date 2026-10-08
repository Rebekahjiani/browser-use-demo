"""Resume authorized B queue with immutable previous outputs and explicit attempts."""
import datetime
import json
import pathlib
import time
import run_b as b


def missing(task, combination):
    root = task / combination / 'entity-extract'
    return [p['dir'] for p in b.read(root / 'INDEX.json')['pages']
            if not (root / p['dir'] / 'output/concepts.json').exists()]


def main():
    experiment = b.read(b.REPORTS / 'experiment.json')
    ledger_path = b.REPORTS / 'recovery-ledger.json'
    ledger = b.read(ledger_path) if ledger_path.exists() else []
    for info in experiment['tasks']:
        task = pathlib.Path(info['path'])
        b.verify_task_inputs(task)
        for combination in ['aqi', 'claudecode']:
            for _ in range(2):
                pending = missing(task, combination)
                if not pending:
                    break
                previous = {str(p): b.sha(p) for p in
                            (task / combination / 'entity-extract').glob('*/output/concepts.json')}
                parent = b.REPORTS / info['run'] / combination
                parent.mkdir(parents=True, exist_ok=True)
                out = parent / ('attempt-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
                out.mkdir()
                item = {'trace': info['run'], 'combination': combination, 'directory': str(out),
                        'selected_pages': pending, 'previous_outputs': previous,
                        'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
                b.write(out / 'attempt.json', item)
                print('Starting', info['run'], combination, len(pending), 'missing pages', flush=True)
                try:
                    if combination == 'aqi':
                        b.run_aqi(info['task_id'], task, out, pending)
                    else:
                        b.run_claude(task, out, pending)
                    item['status'] = 'completed'
                except Exception as exc:
                    item['status'] = 'failed'
                    item['error'] = str(exc)
                    b.write(out / 'error.json', {'error': str(exc)})
                b.verify_task_inputs(task)
                for filename, digest in previous.items():
                    if b.sha(pathlib.Path(filename)) != digest:
                        raise RuntimeError('Recovery modified previous output: ' + filename)
                item['remaining_pages'] = missing(task, combination)
                item['ended_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                b.write(out / 'attempt.json', item)
                b.write(out / 'output-hashes.json', {'files': [{'file': str(p), 'sha256': b.sha(p)} for p in
                        sorted((task / combination / 'entity-extract').glob('*/output/concepts.json'))]})
                ledger.append(item)
                b.write(b.REPORTS / 'recovery-ledger.json', ledger)
                print(item['status'], info['run'], combination, 'missing', len(item['remaining_pages']), flush=True)
    from audit_b import audit
    result = audit()
    print('Queue finished', result['totals'], flush=True)


if __name__ == '__main__':
    main()
