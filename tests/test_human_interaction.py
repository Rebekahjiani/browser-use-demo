import asyncio
import logging
import os
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

os.environ['ANONYMIZED_TELEMETRY'] = 'false'
os.environ['BROWSER_USE_CLOUD_SYNC'] = 'false'
from browser_use import Agent, ActionResult
from human_interaction import HumanInteraction, HumanInputCancelled


def fake_agent(result):
    return SimpleNamespace(
        state=SimpleNamespace(last_result=[result], consecutive_failures=0, n_steps=1),
        history=SimpleNamespace(history=[SimpleNamespace(result=[result.model_copy()])], is_done=lambda: False),
        settings=SimpleNamespace(step_timeout=0.01),
        logger=logging.getLogger('test'), _demo_mode_log=AsyncMock(),
    )


class HumanTests(unittest.IsolatedAsyncioTestCase):
    async def test_answer_outlives_real_step_timeout_and_reaches_history(self):
        async def reply(_):
            await asyncio.sleep(0.05)
            return 'Travel'
        human = HumanInteraction(reader=reply)
        agent = fake_agent(ActionResult())

        async def step(_):
            result = await human.tools.registry.execute_action('ask_human', {'question': '哪个分类？'})
            agent.state.last_result = [result]
            agent.history.history[-1].result = [result.model_copy()]
        agent.step = step
        # Use the installed library's actual step wrapper, with a 10ms timeout.
        await Agent._execute_step(agent, 0, 5, None, on_step_end=human.on_step_end)
        self.assertEqual(agent.state.consecutive_failures, 0)
        self.assertIn('Travel', agent.state.last_result[-1].extracted_content)
        self.assertIn('Travel', agent.history.history[-1].result[-1].long_term_memory)
        self.assertIsNone(human.pending)

    async def test_handoff_requires_confirmation_and_ends_action_sequence(self):
        human = HumanInteraction(reader=AsyncMock(return_value=''))
        result = await human.tools.registry.execute_action('handoff_browser', {'instructions': '请手动登录'})
        agent = fake_agent(result)
        await human.on_step_end(agent)
        self.assertIn('重新观察', agent.state.last_result[-1].extracted_content)
        for name in ('ask_human', 'handoff_browser'):
            self.assertTrue(human.tools.registry.registry.actions[name].terminates_sequence)

    async def test_empty_answer_reprompts(self):
        reader = AsyncMock(side_effect=['  ', '北京'])
        human = HumanInteraction(reader=reader)
        result = await human.tools.registry.execute_action('ask_human', {'question': '城市？'})
        agent = fake_agent(result)
        await human.on_step_end(agent)
        self.assertEqual(reader.await_count, 2)
        self.assertIn('北京', agent.state.last_result[-1].extracted_content)

    async def test_cancel_and_eof_do_not_claim_manual_success(self):
        for reader in (AsyncMock(return_value='/cancel'),
                       AsyncMock(side_effect=HumanInputCancelled('EOF'))):
            human = HumanInteraction(reader=reader)
            result = await human.tools.registry.execute_action('handoff_browser', {'instructions': '登录'})
            agent = fake_agent(result)
            with self.assertRaises(HumanInputCancelled):
                await human.on_step_end(agent)
            self.assertNotIn('已确认', agent.state.last_result[-1].extracted_content)


if __name__ == '__main__':
    unittest.main()
