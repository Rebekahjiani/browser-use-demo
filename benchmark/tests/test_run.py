import argparse
import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import AsyncMock, patch

spec = importlib.util.spec_from_file_location('benchmark_runner', Path(__file__).parents[1] / 'run.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class BudgetTests(unittest.TestCase):
    def test_url_preserves_business_query_and_router(self):
        self.assertEqual(runner.normalize_url('http://host/?p=2&utm_source=x&sort=price#reviews'),
                         'http://host/?p=2&sort=price')
        self.assertEqual(runner.normalize_url('http://host/#/cart'), 'http://host/#/cart')
        self.assertNotEqual(runner.normalize_url('http://host/?p=1'), runner.normalize_url('http://host/?p=2'))

    def test_each_budget_can_stop_independently(self):
        args = argparse.Namespace(max_minutes=30, max_pages=100, max_actions=200)
        for field, value, reason in [('attempts', 200, 'action_limit'),
                                     ('pages', set(range(100)), 'page_limit'),
                                     ('started', runner.time.monotonic() - 1801, 'time_limit')]:
            budget = runner.Budget(args)
            setattr(budget, field, value)
            self.assertEqual(budget.check(), reason)

    def test_invalid_budget(self):
        for args in [['--max-minutes', 'nan'], ['--max-pages', '0']]:
            with self.assertRaises(SystemExit):
                runner.parse_args(args)


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_preflight_uses_live_recording_state(self):
        args = runner.parse_args(['--preflight'])
        async def api(url, body=None):
            if url.endswith('/api/healthz'): return {'ok': True}
            if url.endswith('/api/explore'): return {'runs': []}
            if url.endswith('/json/list'): return [{'type': 'page', 'id': 'tab', 'url': args.url}]
            if url.endswith('/api/status'): return {'hasActiveProfile': False, 'activeProfiles': []}
            raise AssertionError('Unexpected API (must not trust historical status files): ' + url)
        with patch.object(runner, 'http', api), patch.object(runner, 'credentials', return_value=('secret', '', 'model')):
            target, model = await runner.preflight(args)
            self.assertEqual(target['id'], 'tab')
            self.assertEqual(model, 'model')

    async def test_preflight_rejects_active_exploration(self):
        async def api(url, body=None):
            if url.endswith('/api/healthz'): return {'ok': True}
            return {'runs': [{'state': 'running'}]}
        with patch.object(runner, 'http', api):
            with self.assertRaisesRegex(RuntimeError, 'exploration is active'):
                await runner.preflight(runner.parse_args([]))

    async def simulate(self, mode):
        calls = []
        disconnected = AsyncMock()
        page = types.SimpleNamespace(goto=AsyncMock(), _target_id='actor-target')
        browser = types.SimpleNamespace(get_current_page=AsyncMock(return_value=page))

        class History:
            def errors(self): return ['Gateway quota exceeded'] if mode == 'quota' else []
            def is_done(self): return mode == 'done'
            def is_successful(self): return mode == 'done'

        class FakeAgent:
            def __init__(self, **kwargs):
                assert kwargs['directly_open_url'] is False
                self.history = History()
            def save_history(self, path): runner.write_json(path, {'partial': True})
            def stop(self): pass
            async def run(self, **kwargs):
                if mode == 'timeout':
                    await asyncio.sleep(10)
                if mode == 'cancel':
                    raise asyncio.CancelledError()
                if mode == 'error':
                    raise RuntimeError('simulated model failure')
                await kwargs['on_step_end'](self)

        async def fake_http(url, body=None):
            calls.append((url, body))
            if url.endswith('/api/profile/start'):
                return {'ok': True, 'profiles': [{'profileId': 'owned-profile'}]}
            if url.endswith('/api/profile/stop'):
                return {'ok': True}
            if url.endswith('/json/list'):
                return [{'id': 'actor-target', 'type': 'page', 'url': 'about:blank'},
                        {'id': 'target', 'type': 'page', 'url': args.url}]
            raise AssertionError(url)

        modules = {
            'benchmark.driver': types.SimpleNamespace(make_llm=lambda *a: object(),
                start_browser=AsyncMock(return_value=browser), disconnect_browser=disconnected, COMPLETION_RULE=''),
            'benchmark.login_guard': types.SimpleNamespace(LoginGuardAgent=FakeAgent,
                HumanInteraction=lambda *a, **k: types.SimpleNamespace(tools=[], on_step_start=AsyncMock())),
            'browser_use': types.SimpleNamespace(ActionResult=object),
        }
        args = runner.parse_args(['--max-minutes', '0.001' if mode == 'timeout' else '30'])
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(runner, 'OUTPUTS', Path(tmp)), \
             patch.object(runner, 'preflight', AsyncMock(return_value=({'id': 'target'}, 'test-model'))), \
             patch.object(runner, 'credentials', return_value=('secret', 'http://gateway', 'test-model')), \
             patch.object(runner, 'http', fake_http), patch.dict(sys.modules, modules):
            code = await runner.run(args)
            folder = next(Path(tmp).iterdir())
            result = json.loads((folder / 'result.json').read_text())
            self.assertTrue((folder / 'history.json').exists())
            self.assertNotIn('secret', (folder / 'config.json').read_text())
            stop_calls = [b for u, b in calls if u.endswith('/api/profile/stop')]
            start_calls = [b for u, b in calls if u.endswith('/api/profile/start')]
            self.assertEqual(start_calls[0]['targetIds'], ['actor-target'])
            self.assertEqual(stop_calls, [{'profileId': 'owned-profile', 'captureAfter': True}])
            disconnected.assert_awaited_once_with(browser)
            return code, result

    async def test_timeout_keeps_history_and_collects_owned_profile(self):
        code, result = await self.simulate('timeout')
        self.assertEqual(result['stop_reason'], 'time_limit')
        self.assertEqual(code, 0)

    async def test_cancellation_keeps_history_and_collects_owned_profile(self):
        code, result = await self.simulate('cancel')
        self.assertEqual(result['stop_reason'], 'interrupted')
        self.assertEqual(code, 1)

    async def test_model_error_keeps_partial_result(self):
        code, result = await self.simulate('error')
        self.assertEqual(result['stop_reason'], 'error')
        self.assertEqual(code, 1)

    async def test_swallowed_model_failure_is_not_reported_as_clean_run(self):
        code, result = await self.simulate('quota')
        self.assertEqual(result['stop_reason'], 'agent_error')
        self.assertEqual(result['errors'], ['Gateway quota exceeded'])
        self.assertTrue(result['evidence_needs_review'])
        self.assertEqual(code, 1)

    async def test_normal_end_collects(self):
        code, result = await self.simulate('done')
        self.assertEqual(result['stop_reason'], 'agent_done')
        self.assertEqual(result['steps'], 1)
        self.assertEqual(code, 0)


if __name__ == '__main__':
    unittest.main()
