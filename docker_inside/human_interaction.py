"""Read-only login guard. No injected UI; human waits live outside step_timeout."""
import asyncio
import json
from pathlib import Path
import time
from urllib.parse import urlsplit

from browser_use import ActionResult, Agent, Tools

LOGIN_SCRIPT = Path(__file__).with_name('login_state.js').read_text(encoding='utf-8')


class LoginWaitError(RuntimeError):
    pass


class HumanInteraction:
    def __init__(self, capture_dir, success_selector='', timeout=0, poll_interval=1,
                 stable_seconds=3):
        self.status_path = Path(capture_dir) / 'ape-status.json'
        self.success_selector = success_selector
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.stable_seconds = stable_seconds
        self.pending = False
        self.login_baseline = None
        self.tools = Tools()

        @self.tools.action(
            'Wait for the user to complete login or authentication in the browser. '
            'Do not click register, submit credentials, or change login methods. '
            'No popup is shown; resume automatically after verified login.',
            terminates_sequence=True,
        )
        async def handoff_browser(instructions: str = '', message: str = '', text: str = '') -> ActionResult:
            self.pending = True
            return ActionResult(extracted_content='已暂停，等待用户在浏览器完成登录。')

    def status(self, state, message):
        # Contains no credentials, page text, or URLs with session parameters.
        content = json.dumps({'state': state, 'message': message}, ensure_ascii=False, indent=2)
        temporary = self.status_path.with_suffix('.tmp')
        temporary.write_text(content, encoding='utf-8')
        temporary.replace(self.status_path)
        print(message, flush=True)

    async def inspect(self, browser):
        for attempt in range(10):
            try:
                page = await browser.get_current_page()
                if page is None:
                    raise LoginWaitError('浏览器页面已关闭。')
                state = await page.evaluate(LOGIN_SCRIPT, self.success_selector)
                if isinstance(state, str):
                    state = json.loads(state)
                if not isinstance(state, dict) or not all(
                    type(state.get(k)) is bool for k in ('blocked', 'ready', 'authenticated')
                ):
                    raise ValueError('无效的登录检测结果')
                # Cross-origin login fields cannot be read from the parent DOM.
                # Inspect only iframe targets whose URLs match visible frames on
                # this page; never inspect unrelated tabs or hidden frames.
                if state.get('frameRoutes') and not state['blocked']:
                    from browser_use.actor.page import Page
                    session_id = await page.session_id
                    tree = await browser.cdp_client.send.Page.getFrameTree(session_id=session_id)
                    nodes = list(tree.get('frameTree', {}).get('childFrames', []))
                    while nodes and not state['blocked']:
                        node = nodes.pop()
                        nodes.extend(node.get('childFrames', []))
                        parts = urlsplit(node.get('frame', {}).get('url', ''))
                        route = f'{parts.scheme}://{parts.netloc}{parts.path}'
                        if route not in state['frameRoutes']:
                            continue
                        world = await browser.cdp_client.send.Page.createIsolatedWorld(
                            {'frameId': node['frame']['id'], 'worldName': 'login-guard'}, session_id=session_id)
                        evaluated = await browser.cdp_client.send.Runtime.evaluate(
                            {'expression': f'({LOGIN_SCRIPT})("")', 'contextId': world['executionContextId'],
                             'returnByValue': True}, session_id=session_id)
                        frame_state = evaluated.get('result', {}).get('value', {})
                        if frame_state.get('blocked'):
                            state['blocked'] = True
                            state['authenticated'] = False
                            state['password'] = frame_state.get('password', False)
                    targets = await browser.cdp_client.send.Target.getTargets()
                    for target in targets.get('targetInfos', []):
                        parts = urlsplit(target.get('url', ''))
                        route = f'{parts.scheme}://{parts.netloc}{parts.path}'
                        if target.get('type') != 'iframe' or route not in state['frameRoutes']:
                            continue
                        frame = Page(browser, target['targetId'])
                        frame_state = await frame.evaluate(LOGIN_SCRIPT, '')
                        if isinstance(frame_state, str):
                            frame_state = json.loads(frame_state)
                        if frame_state.get('blocked'):
                            state['blocked'] = True
                            state['authenticated'] = False
                            state['password'] = frame_state.get('password', False)
                            break
                if state['blocked'] and self.login_baseline is None:
                    self.login_baseline = state.copy()
                baseline = self.login_baseline
                if (baseline and not self.success_selector and not state['blocked']
                        and state['ready'] and not state.get('loginControl', False)):
                    route_changed = bool(baseline.get('route') and state.get('route')
                                         and baseline['route'] != state['route'])
                    identity_appeared = state.get('identity') is True and not baseline.get('identity')
                    storage_appeared = state.get('storage') is True and not baseline.get('storage')
                    # Leaving login alone can mean a public page. Require a new
                    # account indicator plus navigation or new session markers.
                    if identity_appeared and (route_changed or storage_appeared):
                        state['authenticated'] = True
                return state
            except LoginWaitError:
                raise
            except Exception as exc:
                if attempt == 9:
                    raise LoginWaitError('无法读取登录状态，已停止自动操作。') from exc
                await asyncio.sleep(self.poll_interval)

    async def on_step_start(self, agent):
        state = await self.inspect(agent.browser_session)
        if not self.pending and not state['blocked']:
            return
        self.pending = True
        if self.login_baseline is None:
            self.login_baseline = state.copy()
        self.status('waiting_for_login', '自动探索已暂停，请在浏览器/noVNC 中完成登录；登录成功后自动继续。')
        started = time.monotonic()
        stable_since = None
        while True:
            if state['authenticated'] and state['ready'] and not state['blocked']:
                if stable_since is None:
                    stable_since = time.monotonic()
                if time.monotonic() - stable_since >= self.stable_seconds:
                    break
            else:
                stable_since = None
            if self.timeout and time.monotonic() - started >= self.timeout:
                raise LoginWaitError('等待用户登录超时，未恢复自动探索。')
            await asyncio.sleep(self.poll_interval)
            state = await self.inspect(agent.browser_session)
        self.pending = False
        self.login_baseline = None
        self.status('running', '已检测到稳定的登录成功状态，重新读取页面并继续探索。')
        content = '用户已完成登录。重新读取当前页面，不要重复登录或沿用旧元素编号。'
        results = list(agent.state.last_result or [])[-1:]
        if agent.history.history:
            results += list(agent.history.history[-1].result or [])[-1:]
        for result in results:
            result.extracted_content = content
            result.long_term_memory = content

    async def on_step_end(self, agent):
        if any(result.is_done for result in (agent.state.last_result or [])):
            return
        await self.on_step_start(agent)


class LoginGuardAgent(Agent):
    def __init__(self, *args, human, **kwargs):
        super().__init__(*args, **kwargs)
        self.human = human

    async def multi_act(self, actions):
        # Reporting completion does not operate the page. Do not block done on
        # a login page, a blank page, or a browser closed after data collection.
        if actions and getattr(actions[0], 'done', None) is not None:
            return await super().multi_act(actions[:1])
        # A redirect may arrive while the LLM is thinking. Drop that stale action.
        state = await self.human.inspect(self.browser_session)
        if self.human.pending or state['blocked']:
            self.human.pending = True
            return [ActionResult(extracted_content='登录页动作已拦截，等待人工登录。')]
        if (actions and getattr(actions[0], 'handoff_browser', None) is not None
                and not self.human.success_selector and state['ready']
                and state.get('identity') and state.get('storage')
                and not state.get('loginControl')):
            # A stale/empty model snapshot is not evidence of a login challenge.
            # Do not claim authentication; ask the model to read the live page.
            return [ActionResult(extracted_content=(
                '实时页面已就绪，存在账号界面与会话标记，未检测到登录阻碍。'
                '不要仅凭先前的空白快照要求重新登录；请用 evaluate 只读检查导航或重新观察页面。'))]
        if not state['ready']:
            if state.get('blank') and actions and getattr(actions[0], 'navigate', None) is not None:
                return await super().multi_act(actions[:1])
            return [ActionResult(extracted_content='页面尚未加载完成，请重新观察后再执行动作。')]
        # Enforce even if the model returns more actions than configured.
        return await super().multi_act(actions[:1])
