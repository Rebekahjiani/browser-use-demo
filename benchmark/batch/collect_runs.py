"""Sequential controlled Shopping collection; preserves failed runs and raw budgets."""
import argparse
import asyncio
import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
from urllib.request import Request, urlopen

HERE = pathlib.Path(__file__).resolve().parent
BENCHMARK = HERE.parent
sys.path.insert(0, str(BENCHMARK.parent))
from benchmark.batch.reference_capture import command, get_targets
from benchmark.run import cdp_capture
from benchmark.batch.score_runs import verify


def read(path):
    return json.loads(pathlib.Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    pathlib.Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def api(path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    with urlopen(Request('http://127.0.0.1:14567' + path, data=data,
                         headers={'Content-Type': 'application/json'}), timeout=60) as response:
        value = json.load(response)
    if value.get('ok') is False:
        raise RuntimeError(str(value))
    return value


async def reset_browser(folder):
    import websockets
    status = api('/api/status')
    if status.get('hasActiveProfile') or status.get('activeProfiles'):
        raise RuntimeError('Active recording exists; do not reset it')
    if any(r.get('state') == 'running' for r in api('/api/explore').get('runs', [])):
        raise RuntimeError('Active explorer exists')
    pages = get_targets(9222)
    if not pages:
        raise RuntimeError('No dedicated browser page')
    target = pages[0]
    async with websockets.connect(target['webSocketDebuggerUrl'], max_size=64 * 1024 * 1024) as ws:
        counter = [0]
        for extra in pages[1:]:
            await command(ws, counter, 'Target.closeTarget', {'targetId': extra['id']})
        await command(ws, counter, 'Page.navigate', {'url': 'about:blank'})
        await command(ws, counter, 'Network.clearBrowserCookies')
        await command(ws, counter, 'Storage.clearDataForOrigin',
                      {'origin': 'http://127.0.0.1:7770', 'storageTypes': 'all'})
        await command(ws, counter, 'Page.navigate', {'url': 'http://127.0.0.1:7770/checkout/cart/'})
        for _ in range(30):
            result = await command(ws, counter, 'Runtime.evaluate', {
                'expression': "({url:location.href,empty:document.body?.innerText.includes('You have no items in your shopping cart.'),ready:document.readyState})",
                'returnByValue': True})
            value = result['result'].get('value', {})
            if value.get('empty') and value.get('ready') == 'complete':
                break
            await asyncio.sleep(1)
        else:
            raise RuntimeError('Fresh guest empty cart verification failed')
        await cdp_capture(target, folder / 'initial-state')
        await command(ws, counter, 'Page.navigate', {'url': 'http://127.0.0.1:7770/'})
        await asyncio.sleep(2)
    write(folder / 'reset.json', {'cookies_cleared': True, 'origin_storage_cleared': True,
                                  'empty_cart_verified': True, 'entry_url': 'http://127.0.0.1:7770/',
                                  'reset_at': datetime.datetime.now(datetime.timezone.utc).isoformat()})
    return target


def drive(folder, config, index):
    target = asyncio.run(reset_browser(folder))
    profiles = api('/api/profile/start', {'cdpPort': 9222, 'targetIds': [target['id']],
                   'outputRoot': str(folder / 'trace'), 'tracePreset': 'min', 'captureBefore': True})
    write(folder / 'profiles.json', profiles)
    ids = [p['profileId'] for p in profiles.get('profiles', [])]
    if len(ids) != 1:
        raise RuntimeError('Expected exactly one recording')
    request = {'profileId': ids[0], 'entryUrl': 'http://127.0.0.1:7770/',
               'seed': f'controlled-20261008-{index}', 'maxActions': config['max_actions'],
               'maxDurationMs': int(config['max_minutes'] * 60000), 'maxPages': config['max_pages'],
               'maxDepth': 5, 'saturationLimit': 8, 'allowSubmit': True, 'capturePages': True,
               'autoStop': False, 'allowedOrigins': ['http://127.0.0.1:7770'],
               'blockedPathPatterns': [r'/checkout/(?!cart/?(?:$|\?))', r'/customer/(?!section/load)',
                                       r'/wishlist/', r'/newsletter/', r'/review/product/post'],
               'forms': {'submitAuthForms': False}}
    write(folder / 'config.json', request)
    run_id = None
    try:
        run = api('/api/explore', request)
        run_id = run['exploreId']
        write(folder / 'start.json', run)
        deadline = time.monotonic() + config['max_minutes'] * 60 + 120
        while True:
            state = api(f'/api/explore/{run_id}/status')
            write(folder / 'status.json', state)
            if state.get('state') != 'running':
                break
            if time.monotonic() >= deadline:
                api(f'/api/explore/{run_id}/stop', {})
                raise RuntimeError('Collector hard timeout; stop requested, terminal state must be checked')
            time.sleep(3)
        print(f'Drive {index}: {state.get("state")} {state.get("reason")}', flush=True)
    finally:
        if run_id:
            state = api(f'/api/explore/{run_id}/status')
            if state.get('state') == 'running':
                api(f'/api/explore/{run_id}/stop', {})
        stop = api('/api/profile/stop', {'profileId': ids[0], 'captureAfter': True})
        write(folder / 'stop.json', stop)
    snapshots = sorted(folder.rglob('drive/screenshots'))
    if len(snapshots) != 1:
        raise RuntimeError('Drive snapshots missing or ambiguous')
    return snapshots[0]


def browser_use(folder, config):
    asyncio.run(reset_browser(folder))
    before = {p for p in (BENCHMARK / 'outputs').iterdir() if p.is_dir()}
    environment = {**os.environ, 'MODEL': config['model'], 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}
    cmd = [sys.executable, str(BENCHMARK / 'run.py'), '--max-steps', str(config['max_actions']),
           '--max-actions', str(config['max_actions']), '--max-pages', str(config['max_pages']),
           '--max-minutes', str(config['max_minutes']), '--prompt-file', str(HERE / 'shopping-readonly.txt'),
           '--initial-state', 'verified fresh guest; empty cart; shared read-only query proxy']
    write(folder / 'command.json', {'command': cmd, 'model': config['model']})
    with (folder / 'console.log').open('w', encoding='utf-8') as stream:
        result = subprocess.run(cmd, env=environment, stdout=stream, stderr=subprocess.STDOUT,
                                cwd=BENCHMARK.parent)
    after = {p for p in (BENCHMARK / 'outputs').iterdir() if p.is_dir()}
    created = sorted(after - before)
    write(folder / 'process.json', {'exit_code': result.returncode, 'output_folders': [str(p) for p in created]})
    if len(created) != 1:
        raise RuntimeError('Browser-use output missing or ambiguous')
    summary = read(created[0] / 'result.json')
    write(folder / 'result.json', summary)
    print(f'Browser-use: {summary["stop_reason"]}, {summary["pages_visited"]} URLs, exit={result.returncode}', flush=True)
    if not list((created[0] / 'snapshots').glob('*/accessibility.json')):
        raise RuntimeError('No usable browser-use snapshots; preserve failed run and investigate')
    return created[0] / 'snapshots'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--only', choices=['drive', 'browser-use'])
    args = parser.parse_args()
    config_path = pathlib.Path(args.config).resolve()
    config = read(config_path)
    verify(pathlib.Path(config['contract_bundle']))
    # Require completed gold freeze: independent reference first, candidates later.
    gold = pathlib.Path(config['gold'])
    if hashlib.sha256(gold.read_bytes()).hexdigest() != config['gold_sha256']:
        raise RuntimeError('Experimental gold changed')
    output = pathlib.Path(args.output).resolve()
    if output.exists():
        raise RuntimeError('Experiment directory exists; never overwrite or silently resume')
    output.mkdir(parents=True)
    write(output / 'experiment.json', config)
    runs = []
    for index in range(1, config['repeats'] + 1):
        for strategy in ['drive', 'browser-use']:
            if args.only and strategy != args.only:
                continue
            folder = output / f'{index:02d}-{strategy}'
            folder.mkdir()
            print(f'Starting {index}/{config["repeats"]} {strategy}', flush=True)
            try:
                snapshots = drive(folder, config, index) if strategy == 'drive' else browser_use(folder, config)
                artifacts = [p for p in folder.glob('*.json')]
                if strategy == 'browser-use':
                    artifacts += [snapshots.parent / name for name in
                                  ['config.json', 'prompt.txt', 'result.json', 'history.json',
                                   'actions.jsonl', 'observations.jsonl'] if (snapshots.parent / name).exists()]
                artifacts += list(folder.rglob('trace.segments.summary.json'))
                if strategy == 'browser-use':
                    artifacts += list(snapshots.parent.rglob('trace.segments.summary.json'))
                runs.append({'id': folder.name, 'strategy': strategy, 'snapshots': str(snapshots),
                             'conditions': {**{k: config[k] for k in ['max_actions', 'max_pages', 'max_minutes']},
                                            'model': config['model'] if strategy == 'browser-use' else None,
                                            'permissions': config['permissions']},
                             'artifacts': [str(p) for p in artifacts]})
            except Exception as exc:
                write(folder / 'collector-error.json', {'error': str(exc)})
                raise
            write(output / 'runs.json', {'gold': str(gold), 'mapping': config['mapping'],
                                        'engine': config['engine'], 'experiment': config, 'runs': runs})
    print('Completed collection manifest: ' + str(output / 'runs.json'), flush=True)


if __name__ == '__main__':
    main()
