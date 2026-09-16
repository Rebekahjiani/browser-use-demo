import asyncio
import logging
import os
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

os.environ['ANONYMIZED_TELEMETRY'] = 'false'
os.environ['BROWSER_USE_CLOUD_SYNC'] = 'false'
from browser_use import Agent, ActionResult
from human_interaction import HumanInteraction, HumanInputCancelled, wait_for_browser


def fake_agent(result):
    return SimpleNamespace(
        browser_session=object(),
        state=SimpleNamespace(last_result=[result], consecutive_failures=0, n_steps=1),
        history=SimpleNamespace(history=[SimpleNamespace(result=[result.model_copy()])], is_done=lambda: False),
        settings=SimpleNamespace(step_timeout=0.01),
        logger=logging.getLogger('test'), _demo_mode_log=AsyncMock(),
    )


class HumanTests(unittest.IsolatedAsyncioTestCase):
    async def test_wait_outlives_step_timeout_and_reaches_history(self):
        async def confirm(*_):
            await asyncio.sleep(0.05)
        human = HumanInteraction(waiter=confirm)
        agent = fake_agent(ActionResult())
        async def step(_):
            result = await human.tools.registry.execute_action('handoff_browser', {'instructions': '请选择分类'})
            agent.state.last_result = [result]
            agent.history.history[-1].result = [result.model_copy()]
        agent.step = step
        await Agent._execute_step(agent, 0, 5, None, on_step_end=human.on_step_end)
        self.assertEqual(agent.state.consecutive_failures, 0)
        self.assertIn('重新观察', agent.state.last_result[-1].extracted_content)
        self.assertIn('页面点击继续', agent.history.history[-1].result[-1].long_term_memory)
        self.assertIsNone(human.pending)
        self.assertTrue(human.tools.registry.registry.actions['handoff_browser'].terminates_sequence)
        self.assertNotIn('ask_human', human.tools.registry.registry.actions)

    async def test_no_resume_until_confirmation(self):
        ready = asyncio.Event()
        human = HumanInteraction(waiter=lambda *_: ready.wait())
        result = await human.tools.registry.execute_action('handoff_browser', {'instructions': '登录'})
        agent = fake_agent(result)
        task = asyncio.create_task(human.on_step_end(agent))
        await asyncio.sleep(0.02)
        self.assertFalse(task.done())
        self.assertNotIn('页面点击继续', result.extracted_content)
        ready.set()
        await task

    async def test_cancel_does_not_claim_success(self):
        human = HumanInteraction(waiter=AsyncMock(side_effect=HumanInputCancelled('cancel')))
        result = await human.tools.registry.execute_action('handoff_browser', {'instructions': '登录'})
        with self.assertRaises(HumanInputCancelled):
            await human.on_step_end(fake_agent(result))
        self.assertNotIn('页面点击继续', result.extracted_content)

    async def test_navigation_retries_then_confirmation_removes_panel(self):
        page = SimpleNamespace(evaluate=AsyncMock(side_effect=[RuntimeError('context destroyed'), 'continue', '']))
        browser = SimpleNamespace(get_current_page=AsyncMock(return_value=page))
        await wait_for_browser(browser, '请选择')
        self.assertEqual(browser.get_current_page.await_count, 2)
        self.assertIn('remove()', page.evaluate.call_args.args[0])

    async def test_page_cancel_and_browser_close(self):
        page = SimpleNamespace(evaluate=AsyncMock(side_effect=['cancel', '']))
        for current in (page, None):
            browser = SimpleNamespace(get_current_page=AsyncMock(return_value=current))
            with self.assertRaises(HumanInputCancelled):
                await wait_for_browser(browser, '请选择')


if __name__ == '__main__':
    unittest.main()
