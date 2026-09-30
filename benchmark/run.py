"""Local browser-use benchmark. Run --preflight before recording."""
from __future__ import annotations

import argparse
import asyncio
import base64
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = Path(__file__).resolve().parent / 'outputs'
sys.path.insert(0, str(ROOT))


def write_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def append_json(path, value):
    with Path(path).open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + '\n')


def request_json(url, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urlopen(req, timeout=45) as response:
            result = json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'HTTP {exc.code} from {url}: {detail[:2000]}') from exc
    if isinstance(result, dict) and result.get('ok') is False:
        raise RuntimeError(result.get('message') or result.get('error') or 'API failed')
    return result


async def http(url, body=None):
    return await asyncio.to_thread(request_json, url, body)


def normalize_url(raw):
    """Match drive's volatile query/anchor policy for ordinary HTTP URLs."""
    u = urlsplit(raw)
    volatile = re.compile(r'^(?:utm_|_)|^(?:sid|session|sess|token|ts|cb|nonce|csrf|xsrf|v|cache)$', re.I)
    query = sorted(((k, v) for k, v in parse_qsl(u.query, keep_blank_values=True)
                    if not volatile.search(k)), key=lambda item: item[0])
    fragment = u.fragment if re.match(r'^!?/', u.fragment) else ''
    return urlunsplit((u.scheme, u.netloc, u.path or '/', urlencode(query), fragment))


def origin(url):
    u = urlsplit(url)
    return f'{u.scheme}://{u.netloc}'


def trace_quality(folder):
    summaries = []
    for path in (folder / 'trace').rglob('trace.segments.summary.json'):
        summary = json.loads(path.read_text(encoding='utf-8-sig'))
        summaries.append({'path': str(path.relative_to(folder)),
                          **{key: summary.get(key) for key in
                             ('totalSegments', 'failedSegments', 'maxSwitchGapMs', 'dataLossOccurred')}})
    return summaries


class Budget:
    def __init__(self, args):
        self.args = args
        self.started = time.monotonic()
        self.pages = set()
        self.attempts = 0
        self.steps = 0
        self.reason = None

    def check(self):
        if self.reason:
            return self.reason
        if time.monotonic() - self.started >= self.args.max_minutes * 60:
            self.reason = 'time_limit'
        elif len(self.pages) >= self.args.max_pages:
            self.reason = 'page_limit'
        elif self.attempts >= self.args.max_actions:
            self.reason = 'action_limit'
        return self.reason


async def cdp_capture(target, folder):
    """Read-only CDP snapshots; never start Chrome Tracing (tracer owns it)."""
    import websockets
    folder.mkdir(parents=True, exist_ok=True)
    async with websockets.connect(target['webSocketDebuggerUrl'], max_size=64 * 1024 * 1024) as ws:
        sequence = 0

        async def call(method, params=None):
            nonlocal sequence
            sequence += 1
            await ws.send(json.dumps({'id': sequence, 'method': method, 'params': params or {}}))
            while True:
                message = json.loads(await asyncio.wait_for(ws.recv(), 12))
                if message.get('id') == sequence:
                    if 'error' in message:
                        raise RuntimeError(message['error']['message'])
                    return message['result']

        async def document():
            result = await call('Runtime.evaluate', {
                'expression': '({url:location.href,title:document.title,html:document.documentElement.outerHTML})',
                'returnByValue': True})
            return result['result']['value']

        before = await document()
        ax = await call('Accessibility.getFullAXTree')
        png = await call('Page.captureScreenshot', {'format': 'png'})
        after = await document()
        if before['url'] != after['url']:
            raise RuntimeError('Navigation during snapshot; snapshot discarded')
        (folder / 'page.html').write_text(before['html'], encoding='utf-8')
        write_json(folder / 'accessibility.json', ax)
        (folder / 'screenshot.png').write_bytes(base64.b64decode(png['data']))
        meta = {'url': before['url'], 'title': before['title'], 'target_id': target['id'],
                'captured_at': datetime.now(timezone.utc).isoformat()}
        write_json(folder / 'metadata.json', meta)
        return meta


def credentials():
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    settings_path = os.getenv('AT_SETTINGS_PATH')
    if settings_path:
        settings = json.loads(Path(settings_path).expanduser().read_text(encoding='utf-8-sig'))
        provider, model = settings['defaultModel'].split('/', 1)
        cfg = settings['modelProviders'][provider]
        key, base = cfg['apiKey'], cfg['baseUrl']
    else:
        key, base, model = (os.getenv(k) for k in ('OPENAI_API_KEY', 'OPENAI_BASE_URL', 'MODEL'))
    model = os.getenv('MODEL') or model
    if not key or not model:
        raise ValueError('Configure OPENAI_API_KEY/MODEL or AT_SETTINGS_PATH in the project .env')
    return key, base, model


async def preflight(args):
    version = importlib.metadata.version('browser-use')
    if version != '0.13.10':
        raise RuntimeError(f'This adapter is validated for browser-use 0.13.10; installed: {version}')
    await http(args.tracer_url + '/api/healthz')
    runs = await http(args.tracer_url + '/api/explore')
    if any(r.get('state') in ('running', 'starting', 'stopping') for r in runs.get('runs', [])):
        raise RuntimeError('An exploration is active. Wait until it finishes before benchmarking.')
    targets = await http(f'http://127.0.0.1:{args.cdp_port}/json/list')
    pages = [t for t in targets if t.get('type') == 'page']
    if len(pages) != 1:
        raise RuntimeError('Use a dedicated CDP Chrome with exactly one page tab (blank or target site).')
    if pages[0]['url'] != 'about:blank' and origin(pages[0]['url']) != origin(args.url):
        raise RuntimeError('The CDP page is not blank or on the target origin. Use a dedicated Chrome.')
    # Live status is authoritative; per-profile files can contain stale 'recording' states.
    status = await http(args.tracer_url + '/api/status')
    if status.get('hasActiveProfile') or status.get('activeProfiles'):
        raise RuntimeError('A tracer recording is active. Stop and collect it first.')
    _, _, model = credentials()
    return pages[0], model


async def run(args):
    target, model = await preflight(args)
    print(f'Preflight OK: CDP {args.cdp_port}, tracer reachable, model={model}', flush=True)
    if args.preflight:
        return 0

    from benchmark.driver import make_llm, start_browser, disconnect_browser, COMPLETION_RULE
    from benchmark.login_guard import HumanInteraction, LoginGuardAgent
    from browser_use import ActionResult

    prompt_path = Path(args.prompt_file)
    task = prompt_path.read_text(encoding='utf-8-sig').replace('{url}', args.url).strip()
    if not task:
        raise ValueError('Empty prompt')
    task += COMPLETION_RULE
    folder = OUTPUTS / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    (folder / 'prompt.txt').write_text(task, encoding='utf-8')
    write_json(folder / 'config.json', {
        **vars(args), 'model': model, 'browser_use_version': importlib.metadata.version('browser-use'),
        'max_actions_per_step': 1, 'temperature': 0.2, 'use_vision': False,
        'action_counting': 'non-done/non-handoff tool attempts, not DOM event count',
        'page_counting': 'normalized same-origin URLs observed at step boundaries',
        'initial_state': args.initial_state,
    })
    print(f'Output: {folder}', flush=True)
    browser = agent = budget = None
    profile_ids = []
    errors = []
    reason = 'setup_error'
    snapshot_index = 0
    capture_errors = 0
    unattached_targets = set()
    exploration_seconds = 0
    ignored_initial_targets = set()

    async def observe():
        nonlocal snapshot_index, capture_errors
        targets = await http(f'http://127.0.0.1:{args.cdp_port}/json/list')
        pages = [t for t in targets if t.get('type') == 'page' and origin(t['url']) == origin(args.url)
                 and t['id'] not in ignored_initial_targets]
        # New tabs need a recording of their own; flag them rather than silently claiming completeness.
        for t in pages:
            if t['id'] != target['id']:
                unattached_targets.add(t['id'])
            budget.pages.add(normalize_url(t['url']))
            snapshot_index += 1
            dest = folder / 'snapshots' / f'{snapshot_index:05d}'
            event = {'step': budget.steps, 'elapsed_s': time.monotonic() - budget.started,
                     'target_id': t['id'], 'path': str(dest.relative_to(folder)),
                     'tracer_attached': t['id'] == target['id']}
            try:
                event.update(await asyncio.wait_for(cdp_capture(t, dest), 35))
                budget.pages.add(normalize_url(event['url']))
            except Exception as exc:
                capture_errors += 1
                event['error'] = str(exc)
            append_json(folder / 'observations.jsonl', event)

    class BenchmarkAgent(LoginGuardAgent):
        async def multi_act(self, actions):
            if budget.check():
                self.stop()
                return [ActionResult(error=budget.reason)]
            selected = actions[:1]
            name = next(iter(selected[0].model_dump(exclude_none=True)), 'unknown') if selected else 'none'
            counted = name not in ('done', 'handoff_browser', 'none')
            if counted:
                budget.attempts += 1
            event = {'step': budget.steps, 'tool': name, 'counted': counted,
                     'elapsed_s': time.monotonic() - budget.started}
            append_json(folder / 'actions.jsonl', {**event, 'phase': 'attempt'})
            try:
                result = await super().multi_act(selected)
                append_json(folder / 'actions.jsonl', {**event, 'phase': 'return',
                    'errors': [r.error for r in result if r.error]})
                return result
            except BaseException:
                append_json(folder / 'actions.jsonl', {**event, 'phase': 'interrupted_or_failed'})
                raise

    try:
        browser = await start_browser(args.cdp_port, 3, 1)
        # Browser-use may create a new tab while attaching. Record the actual
        # actor target, not the tab that happened to exist before connection.
        actor_page = await browser.get_current_page()
        if actor_page is None:
            raise RuntimeError('Browser-use has no active page')
        actor_target = actor_page._target_id  # pinned browser-use 0.13.10 API
        await actor_page.goto(args.url)
        connected_targets = await http(f'http://127.0.0.1:{args.cdp_port}/json/list')
        target = next(t for t in connected_targets if t['id'] == actor_target)
        ignored_initial_targets = {t['id'] for t in connected_targets
                                   if t.get('type') == 'page' and t['id'] != actor_target}
        response = await http(args.tracer_url + '/api/profile/start', {
            'cdpPort': args.cdp_port, 'targetIds': [target['id']],
            'outputRoot': str(folder / 'trace'), 'tracePreset': args.trace_preset,
            'captureBefore': True,
        })
        profile_ids = [p['profileId'] for p in response.get('profiles', [])]
        if not profile_ids:
            raise RuntimeError('Tracer returned no profile IDs')
        write_json(folder / 'tracer-profiles.json', response)
        budget = Budget(args)
        human = HumanInteraction(folder, args.login_success_selector, timeout=120)
        key, base, model = credentials()
        agent = BenchmarkAgent(human=human, task=task, llm=make_llm(key, base, model),
            browser=browser, tools=human.tools, use_vision=False, use_judge=False,
            directly_open_url=False,
            max_failures=3, max_actions_per_step=1, llm_timeout=90, step_timeout=150,
            file_system_path=str(folder / 'agent-files'),
            extend_system_message='Stay on the entry origin and in the current tab. '
                'Do not open new tabs. On login use handoff_browser; do not enter credentials. '
                'Do not read local files or use external sources as website evidence. '
                'Return exactly one valid JSON object matching the provided AgentOutput schema. '
                'Put thinking inside the JSON thinking string. Do not output XML tags such as '
                '<thinking> or <action>, markdown fences, or text outside the JSON object.')

        async def step_start(current):
            if budget.check():
                current.stop()
                return
            await human.on_step_start(current)

        async def step_end(current):
            budget.steps += 1
            current.save_history(str(folder / 'history.json'))
            await observe()
            if budget.check():
                current.stop()

        async def explore():
            page = await browser.get_current_page()
            await page.goto(args.url)
            await observe()
            if not budget.check():
                await agent.run(max_steps=args.max_steps, on_step_start=step_start, on_step_end=step_end)

        try:
            await asyncio.wait_for(explore(), args.max_minutes * 60)
            reason = budget.reason or ('agent_done' if agent.history.is_done() else
                     'step_limit' if budget.steps >= args.max_steps else 'agent_stopped')
        except asyncio.TimeoutError:
            reason = budget.reason = 'time_limit'
        except asyncio.CancelledError:
            reason = 'interrupted'
        except Exception as exc:
            reason = 'error'
            errors.append(str(exc))
    except asyncio.CancelledError:
        reason = 'interrupted'
    except Exception as exc:
        errors.append(str(exc))
    finally:
        exploration_seconds = time.monotonic() - budget.started if budget else 0
        # Persist history even on timeout; cleanup time is outside the exploration budget.
        if agent is not None:
            try:
                agent.save_history(str(folder / 'history.json'))
                history_errors = [str(e) for e in agent.history.errors() if e]
                errors.extend(history_errors)
                if history_errors and reason == 'agent_stopped':
                    reason = 'agent_error'
            except Exception as exc:
                errors.append(f'history: {exc}')
        for pid in profile_ids:
            try:
                result = await http(args.tracer_url + '/api/profile/stop', {'profileId': pid, 'captureAfter': True})
                write_json(folder / f'tracer-stop-{pid}.json', result)
            except Exception as exc:
                errors.append(f'tracer stop {pid}: {exc}')
        if browser is not None:
            await disconnect_browser(browser)
        try:
            trace_summaries = trace_quality(folder)
        except Exception as exc:
            trace_summaries = []
            errors.append(f'trace quality: {exc}')
        trace_incomplete = not trace_summaries or any(
            s.get('dataLossOccurred') or s.get('failedSegments') for s in trace_summaries)
        summary = {
            'stop_reason': reason, 'errors': errors, 'profile_ids': profile_ids,
            'steps': budget.steps if budget else 0,
            'tool_attempts': budget.attempts if budget else 0,
            'pages_visited': len(budget.pages) if budget else 0,
            'visited_urls': sorted(budget.pages) if budget else [],
            'elapsed_including_cleanup_s': time.monotonic() - budget.started if budget else 0,
            'exploration_s': exploration_seconds,
            'capture_errors': capture_errors, 'unattached_targets': sorted(unattached_targets),
            'trace_quality': trace_summaries,
            'evidence_needs_review': bool(capture_errors or unattached_targets or errors
                                         or trace_incomplete or reason == 'interrupted' or snapshot_index == 0),
            'agent_claimed_success': agent.history.is_successful() if agent else None,
            'finished_at': datetime.now(timezone.utc).isoformat(),
        }
        write_json(folder / 'result.json', summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 1 if errors or reason in ('error', 'setup_error', 'interrupted') else 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:7770/')
    parser.add_argument('--cdp-port', type=int, default=9222)
    parser.add_argument('--tracer-url', default='http://127.0.0.1:14567')
    parser.add_argument('--max-steps', type=int, default=200, help='Agent round limit; distinct from tool attempts')
    parser.add_argument('--max-actions', type=int, default=200, help='Non-done/non-handoff tool attempt limit')
    parser.add_argument('--max-pages', type=int, default=100)
    parser.add_argument('--max-minutes', type=float, default=30)
    parser.add_argument('--prompt-file', default=str(Path(__file__).with_name('shopping.txt')))
    parser.add_argument('--initial-state', default='unspecified', help='Describe login/cart state for comparison')
    parser.add_argument('--login-success-selector', default='')
    parser.add_argument('--trace-preset', default='min', help='Use the same tracer preset as drive')
    parser.add_argument('--preflight', action='store_true', help='Read-only checks; no model calls/recording')
    args = parser.parse_args(argv)
    import math
    if min(args.max_steps, args.max_actions, args.max_pages) < 1 or not math.isfinite(args.max_minutes) or args.max_minutes <= 0:
        parser.error('Budgets must be positive and finite')
    if not 1 <= args.cdp_port <= 65535:
        parser.error('Invalid CDP port')
    if urlsplit(args.url).scheme not in ('http', 'https'):
        parser.error('Entry must be HTTP(S)')
    args.tracer_url = args.tracer_url.rstrip('/')
    return args


if __name__ == '__main__':
    try:
        sys.exit(asyncio.run(run(parse_args())))
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as exc:
        print(f'Benchmark failed: {exc}', file=sys.stderr)
        sys.exit(1)
