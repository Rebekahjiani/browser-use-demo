import asyncio
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['ANONYMIZED_TELEMETRY'] = 'false'
os.environ['BROWSER_USE_CLOUD_SYNC'] = 'false'
from browser_use import ActionResult, Agent
from human_interaction import HumanInteraction, LoginGuardAgent, LoginWaitError

LOGIN = {'blocked': True, 'ready': True, 'authenticated': False}
PUBLIC = {'blocked': False, 'ready': True, 'authenticated': False}
BLANK = {'blocked': False, 'ready': False, 'authenticated': False}
HOME = {'blocked': False, 'ready': True, 'authenticated': True}


class LoginTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.human = HumanInteraction(self.directory.name, poll_interval=.001, stable_seconds=.003)
        self.page = SimpleNamespace(evaluate=AsyncMock(return_value=LOGIN))
        self.agent = SimpleNamespace(
            browser_session=SimpleNamespace(get_current_page=AsyncMock(return_value=self.page)),
            state=SimpleNamespace(last_result=[ActionResult()]),
            history=SimpleNamespace(history=[]),
        )

    async def test_wait_until_positive_stable_login(self):
        task = asyncio.create_task(self.human.on_step_start(self.agent))
        try:
            for state in (LOGIN, PUBLIC, BLANK, LOGIN):
                self.page.evaluate.return_value = state
                await asyncio.sleep(.01)
                self.assertFalse(task.done())
            self.page.evaluate.return_value = HOME
            await asyncio.wait_for(task, 1)
            self.assertFalse(self.human.pending)
            self.assertIn('重新读取', self.agent.state.last_result[0].extracted_content)
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    async def test_transient_success_does_not_resume(self):
        self.page.evaluate.side_effect = [LOGIN, HOME, LOGIN, PUBLIC, HOME, HOME, HOME, HOME, HOME]
        await self.human.on_step_start(self.agent)
        self.assertGreaterEqual(self.page.evaluate.await_count, 6)

    async def test_public_page_is_not_blocked_before_login(self):
        self.page.evaluate.return_value = PUBLIC
        await self.human.on_step_start(self.agent)
        self.assertFalse(self.human.pending)

    async def test_model_fallback_waits_even_on_unrecognized_login(self):
        self.page.evaluate.return_value = PUBLIC
        await self.human.tools.registry.execute_action('handoff_browser', {'instructions': '扫码登录'})
        self.human.timeout = .005
        with self.assertRaises(LoginWaitError):
            await self.human.on_step_end(self.agent)
        self.assertTrue(self.human.pending)

    async def test_wait_outside_agent_step_timeout(self):
        self.agent.settings = SimpleNamespace(step_timeout=.001)
        self.agent._demo_mode_log = AsyncMock()
        self.agent.logger = SimpleNamespace(debug=lambda *_: None)
        self.agent.step = AsyncMock()
        self.agent.history.is_done = lambda: False
        async def login_later():
            await asyncio.sleep(.02)
            self.page.evaluate.return_value = HOME
        await asyncio.gather(login_later(), Agent._execute_step(
            self.agent, 0, 5, None, on_step_start=self.human.on_step_start))
        self.agent.step.assert_awaited_once()

    async def test_block_registration_after_model_inference(self):
        self.agent.human = self.human
        with patch.object(Agent, 'multi_act', new_callable=AsyncMock) as execute:
            results = await LoginGuardAgent.multi_act(self.agent, ['register', 'click'])
            execute.assert_not_awaited()
        self.assertTrue(self.human.pending)
        self.assertIn('拦截', results[0].extracted_content)

    async def test_real_agent_drops_second_queued_action(self):
        # Exercise the actual subclass (super() requires an instance).
        agent = object.__new__(LoginGuardAgent)
        agent.human = self.human
        agent.browser_session = self.agent.browser_session
        self.page.evaluate.return_value = PUBLIC
        with patch.object(Agent, 'multi_act', new_callable=AsyncMock, return_value=[]) as execute:
            await agent.multi_act(['navigate', 'register'])
            execute.assert_awaited_once_with(['navigate'])

    async def test_navigation_errors_retry_but_never_unlock(self):
        self.page.evaluate.side_effect = [RuntimeError('navigation'), LOGIN]
        self.assertEqual(await self.human.inspect(self.agent.browser_session), LOGIN)
        self.page.evaluate.side_effect = RuntimeError('disconnected')
        with self.assertRaises(LoginWaitError):
            await self.human.inspect(self.agent.browser_session)

    async def test_browser_closed_stops(self):
        self.agent.browser_session.get_current_page.return_value = None
        with self.assertRaises(LoginWaitError):
            await self.human.on_step_start(self.agent)

    async def test_browser_use_json_string_result(self):
        import json
        self.page.evaluate.return_value = json.dumps(LOGIN)
        self.assertEqual(await self.human.inspect(self.agent.browser_session), LOGIN)

    async def test_string_booleans_do_not_unlock(self):
        self.page.evaluate.return_value = {'blocked': False, 'ready': True, 'authenticated': 'false'}
        with self.assertRaises(LoginWaitError):
            await self.human.inspect(self.agent.browser_session)

    async def test_resume_preserves_earlier_action_results(self):
        earlier = ActionResult(extracted_content='Previously collected page data')
        self.agent.state.last_result.insert(0, earlier)
        self.human.pending = True
        self.page.evaluate.return_value = HOME
        await self.human.on_step_start(self.agent)
        self.assertEqual(earlier.extracted_content, 'Previously collected page data')

    async def test_generic_login_transition(self):
        self.page.evaluate.return_value = dict(LOGIN, route='https://new.test/login', identity=False, storage=False)
        await self.human.inspect(self.agent.browser_session)
        for changes, expected in [
            ({'route': 'https://new.test/home'}, False),
            ({'route': 'https://new.test/home', 'storage': True}, False),
            ({'route': 'https://new.test/home', 'identity': True}, True),
            ({'route': 'https://new.test/login', 'identity': True, 'storage': True}, True),
            ({'route': 'https://new.test/home', 'identity': True, 'loginControl': True}, False),
        ]:
            self.page.evaluate.return_value = dict(PUBLIC, **changes)
            self.assertEqual((await self.human.inspect(self.agent.browser_session))['authenticated'], expected)

    async def test_generic_rule_does_not_override_selector(self):
        self.human.success_selector = '#required'
        self.human.login_baseline = dict(LOGIN, route='/login')
        self.page.evaluate.return_value = dict(PUBLIC, route='/home', identity=True)
        self.assertFalse((await self.human.inspect(self.agent.browser_session))['authenticated'])

    async def test_done_is_not_blocked_by_login(self):
        agent = object.__new__(LoginGuardAgent)
        agent.human = self.human
        agent.browser_session = self.agent.browser_session
        done = SimpleNamespace(done={'text': '完成', 'success': True})
        with patch.object(Agent, 'multi_act', new_callable=AsyncMock, return_value=[]) as execute:
            await agent.multi_act([done])
            execute.assert_awaited_once_with([done])
        self.page.evaluate.assert_not_awaited()

    async def test_done_does_not_wait_in_end_hook(self):
        self.agent.state.last_result = [ActionResult(is_done=True, success=True, extracted_content='完成')]
        await self.human.on_step_end(self.agent)
        self.page.evaluate.assert_not_awaited()

    async def test_blank_page_allows_navigation_but_not_click(self):
        agent = object.__new__(LoginGuardAgent)
        agent.human = self.human
        agent.browser_session = self.agent.browser_session
        self.page.evaluate.return_value = dict(BLANK, blank=True)
        navigate = SimpleNamespace(navigate={'url': 'https://example.com'})
        click = SimpleNamespace(click={'index': 1})
        with patch.object(Agent, 'multi_act', new_callable=AsyncMock, return_value=[]) as execute:
            await agent.multi_act([navigate])
            execute.assert_awaited_once_with([navigate])
            execute.reset_mock()
            await agent.multi_act([click])
            execute.assert_not_awaited()

    async def test_visible_cross_origin_frame_blocks_login(self):
        route = 'https://auth.example.test/embedded'
        self.page.evaluate.return_value = dict(PUBLIC, frameRoutes=[route])
        # Page.session_id is an awaitable property in browser-use.
        session = asyncio.Future()
        session.set_result('session')
        self.page.session_id = session
        cdp = SimpleNamespace(
            Page=SimpleNamespace(
                getFrameTree=AsyncMock(return_value={'frameTree': {'childFrames': [
                    {'frame': {'id': 'child', 'url': route}}]}}),
                createIsolatedWorld=AsyncMock(return_value={'executionContextId': 1})),
            Runtime=SimpleNamespace(evaluate=AsyncMock(return_value={'result': {'value': dict(LOGIN, password=True)}})),
            Target=SimpleNamespace(getTargets=AsyncMock(return_value={'targetInfos': []})),
        )
        self.agent.browser_session.cdp_client = SimpleNamespace(send=cdp)
        result = await self.human.inspect(self.agent.browser_session)
        self.assertTrue(result['blocked'])
        self.assertFalse(result['authenticated'])
        self.assertTrue(result['password'])

    async def test_stale_snapshot_does_not_handoff_loaded_account_page(self):
        agent = object.__new__(LoginGuardAgent)
        agent.human = self.human
        agent.browser_session = self.agent.browser_session
        self.page.evaluate.return_value = dict(PUBLIC, identity=True, storage=True, loginControl=False)
        action = SimpleNamespace(handoff_browser={'instructions': 'login'})
        with patch.object(Agent, 'multi_act', new_callable=AsyncMock) as execute:
            result = await agent.multi_act([action])
            execute.assert_not_awaited()
        self.assertIn('重新观察', result[0].extracted_content)
        self.assertFalse(self.human.pending)


if __name__ == '__main__':
    unittest.main()
