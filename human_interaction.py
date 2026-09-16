"""Human input is awaited in on_step_end, outside browser-use's step timeout."""
import asyncio
import sys

from browser_use import ActionResult, Tools


class HumanInputCancelled(Exception):
    pass


async def read_terminal(prompt):
    """Cancellable terminal input for macOS/Linux, without a blocked input thread."""
    if not sys.stdin.isatty():
        raise HumanInputCancelled('人工交互需要终端；请直接运行或使用 docker exec -it。')
    print(prompt, end='', flush=True)
    loop = asyncio.get_running_loop()
    answer = loop.create_future()
    fd = sys.stdin.fileno()

    def ready():
        line = sys.stdin.readline()
        if not answer.done():
            if line:
                answer.set_result(line.rstrip('\n'))
            else:
                answer.set_exception(HumanInputCancelled('终端输入已关闭。'))

    loop.add_reader(fd, ready)
    try:
        return await answer
    finally:
        loop.remove_reader(fd)


class HumanInteraction:
    def __init__(self, reader=read_terminal):
        self.reader = reader
        self.pending = None
        self.tools = Tools()

        @self.tools.action(
            'Ask the user for missing non-sensitive information. Do not ask for passwords or codes; '
            'use handoff_browser for those. Stops this action sequence and waits for a terminal reply.',
            terminates_sequence=True,
        )
        async def ask_human(question: str) -> ActionResult:
            self.pending = ('question', question)
            return ActionResult(extracted_content='Waiting for the user to answer.')

        @self.tools.action(
            'Let the user operate the visible browser for login, verification codes or other manual steps. '
            'Explain what to do. Stops this action sequence until the user confirms in the terminal.',
            terminates_sequence=True,
        )
        async def handoff_browser(instructions: str) -> ActionResult:
            self.pending = ('browser', instructions)
            return ActionResult(extracted_content='Waiting for the user to operate the browser.')

    async def on_step_end(self, agent):
        if self.pending is None:
            return
        kind, prompt = self.pending
        print(f'\n【{"需要你回答" if kind == "question" else "浏览器已交给你"}】{prompt}', flush=True)
        while True:
            label = ('请输入答复（/cancel 取消）：' if kind == 'question' else
                     '请在浏览器完成操作，再回此处按 Enter（/cancel 取消）：')
            answer = (await self.reader(label)).strip()
            if answer.lower() == '/cancel':
                self.pending = None
                raise HumanInputCancelled('用户取消了人工交互。')
            if kind == 'browser' or answer:
                break
            print('答复不能为空；请输入信息或 /cancel。', flush=True)
        if kind == 'question':
            content = f'用户回答：{answer}'
        else:
            content = '用户已确认完成人工操作。请重新观察当前页面，核实结果后继续，不要沿用旧元素编号。'
        # The next prompt consumes state.last_result; persist the same answer in history.
        for result in (agent.state.last_result[-1], agent.history.history[-1].result[-1]):
            result.extracted_content = content
            result.long_term_memory = content
        self.pending = None
        print('【继续执行】\n', flush=True)
