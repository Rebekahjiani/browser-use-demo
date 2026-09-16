"""Pause outside the agent step timeout; confirm directly in the visible page."""
import asyncio
from pathlib import Path
import uuid

from browser_use import ActionResult, Tools

PANEL_SCRIPT = Path(__file__).with_name('handoff_panel.js').read_text()


class HumanInputCancelled(Exception):
    pass


async def wait_for_browser(browser, instructions, finished=False):
    token = uuid.uuid4().hex
    failures = 0
    while True:
        try:
            page = await browser.get_current_page()
            if page is None:
                raise HumanInputCancelled('演示浏览器已关闭。')
            response = await page.evaluate(PANEL_SCRIPT, token, instructions, finished)
            failures = 0
        except HumanInputCancelled:
            raise
        except Exception as exc:
            # Navigation briefly destroys the JS context. Reinstall on the new page.
            failures += 1
            if failures >= 10:
                raise HumanInputCancelled('无法连接演示页面，任务已停止。') from exc
            await asyncio.sleep(0.5)
            continue
        if response in ('continue', 'cancel'):
            await page.evaluate("() => document.getElementById('browser-use-handoff')?.remove()")
            if response == 'cancel':
                raise HumanInputCancelled('用户在页面中取消了任务。')
            return
        await asyncio.sleep(0.5)


class HumanInteraction:
    def __init__(self, waiter=wait_for_browser):
        self.waiter = waiter
        self.pending = None
        self.tools = Tools()

        @self.tools.action(
            'Pause and hand the visible browser to the user. Explain what the user should '
            'fill in, select or complete on the website. The user clicks Continue in an '
            'on-page panel when ready. Use for missing information, login and manual steps.',
            terminates_sequence=True,
        )
        async def handoff_browser(instructions: str) -> ActionResult:
            self.pending = instructions
            return ActionResult(extracted_content='Waiting for the user to operate the browser.')

    async def on_step_end(self, agent):
        if self.pending is None:
            return
        await self.waiter(agent.browser_session, self.pending)
        content = '用户已在页面点击继续。请重新观察当前页面，核实人工操作结果后继续，不要沿用旧元素编号。'
        for result in (agent.state.last_result[-1], agent.history.history[-1].result[-1]):
            result.extracted_content = content
            result.long_term_memory = content
        self.pending = None
