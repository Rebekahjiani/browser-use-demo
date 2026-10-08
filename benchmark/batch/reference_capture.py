"""Independent read-only reference snapshots; never count these as explorer runs."""
import argparse
import asyncio
import hashlib
import json
import pathlib
import sys
import time
from urllib.request import urlopen

BENCHMARK = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCHMARK.parent))
from benchmark.run import cdp_capture, write_json


def get_targets(port):
    with urlopen(f'http://127.0.0.1:{port}/json/list', timeout=10) as stream:
        return [t for t in json.load(stream) if t['type'] == 'page']


async def command(ws, counter, method, params=None):
    counter[0] += 1
    sequence = counter[0]
    await ws.send(json.dumps({'id': sequence, 'method': method, 'params': params or {}}))
    while True:
        message = json.loads(await asyncio.wait_for(ws.recv(), 30))
        if message.get('id') == sequence:
            if 'error' in message:
                raise RuntimeError(str(message['error']))
            return message.get('result', {})


async def reset(port):
    import websockets
    pages = get_targets(port)
    if len(pages) != 1:
        raise RuntimeError('Dedicated browser must have exactly one page')
    async with websockets.connect(pages[0]['webSocketDebuggerUrl']) as ws:
        counter = [0]
        await command(ws, counter, 'Page.navigate', {'url': 'about:blank'})
        await command(ws, counter, 'Network.clearBrowserCookies')
        await command(ws, counter, 'Storage.clearDataForOrigin',
                      {'origin': 'http://127.0.0.1:7770', 'storageTypes': 'all'})
    return pages[0]


async def capture(port, output):
    import websockets
    output = pathlib.Path(output).resolve()
    if output.exists():
        raise RuntimeError('Refuse overwrite of reference capture')
    output.mkdir(parents=True)
    target = await reset(port)
    gold = json.loads((BENCHMARK / 'coverage-v3/gold.v1.json').read_text(encoding='utf-8'))
    urls = list(dict.fromkeys([
        'http://127.0.0.1:7770/',
        'http://127.0.0.1:7770/beauty-personal-care.html',
        'http://127.0.0.1:7770/home-kitchen.html?cat=34',
        'http://127.0.0.1:7770/cell-phones-accessories.html?p=2',
        'http://127.0.0.1:7770/beauty-personal-care.html?product_list_order=price',
        'http://127.0.0.1:7770/catalogsearch/result/?q=shoe',
        'http://127.0.0.1:7770/catalogsearch/result/?q=zzzz_no_result_20261008',
        'http://127.0.0.1:7770/catalogsearch/advanced/',
        'http://127.0.0.1:7770/checkout/cart/',
        'http://127.0.0.1:7770/catalog/product/view/id/16/',
    ] + [f['reference_witness']['url'] for f in gold['facts']]))
    results = []
    async with websockets.connect(target['webSocketDebuggerUrl'], max_size=64 * 1024 * 1024) as ws:
        counter = [0]
        for index, url in enumerate(urls):
            folder = output / f'{index:04d}'
            print(f'Reference {index + 1}/{len(urls)}: {url}', flush=True)
            try:
                response = await command(ws, counter, 'Page.navigate', {'url': url})
                if response.get('errorText'):
                    raise RuntimeError(response['errorText'])
                deadline, stable, previous = time.monotonic() + 40, 0, None
                while time.monotonic() < deadline:
                    status = await command(ws, counter, 'Runtime.evaluate', {
                        'expression': '({ready:document.readyState,bytes:document.body?.innerText.length||0,url:location.href})',
                        'returnByValue': True})
                    value = status['result'].get('value', {})
                    stable = stable + 1 if value == previous and value.get('ready') == 'complete' else 0
                    previous = value
                    if stable >= 2 and value.get('bytes', 0) > 50:
                        break
                    await asyncio.sleep(1)
                else:
                    raise RuntimeError('Reference page did not settle')
                meta = await cdp_capture(target, folder)
                results.append({'requested_url': url, 'snapshot': str(folder), 'metadata': meta})
            except Exception as exc:
                results.append({'requested_url': url, 'error': str(exc)})
                print(type(exc).__name__, str(exc), flush=True)
    write_json(output / 'capture.json', {
        'role': 'Independent current UI reference; not automatic exploration or blind annotation',
        'conditions': 'fresh guest cookies/storage; shared read-only proxy; no writes',
        'posthoc_limit': 'Some witness URLs originate in historical gold; not blind',
        'urls': results})
    write_json(output / 'source-hashes.json', {
        'files': [{'file': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                  for p in sorted(output.rglob('*')) if p.is_file()]})
    print(f'Reference captured: {len(results)} attempted, {sum("error" in r for r in results)} failed', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cdp-port', type=int, default=9222)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    asyncio.run(capture(args.cdp_port, args.output))
