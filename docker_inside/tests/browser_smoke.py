"""Optional real Chrome DOM smoke check, no LLM or account required."""
import asyncio
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import quote
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['ANONYMIZED_TELEMETRY'] = 'false'
os.environ['BROWSER_USE_CLOUD_SYNC'] = 'false'
from browser_use import Browser
from human_interaction import HumanInteraction


async def main():
    chrome = os.getenv('BROWSER_EXECUTABLE_PATH')
    if not chrome and sys.platform == 'win32':
        chrome = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    with tempfile.TemporaryDirectory() as folder:
        browser = Browser(headless=True, executable_path=chrome,
                          user_data_dir=str(Path(folder) / 'profile'),
                          enable_default_extensions=False)
        try:
            await browser.start()
            page = await browser.get_current_page()
            human = HumanInteraction(folder)
            fixtures = [
                ('<h1>Login</h1><input type="password"><button>Register</button>', True, False),
                ('<h1>Welcome to the public marketing website</h1><a>Login</a>', False, False),
                ('<h1>Welcome to your authenticated dashboard</h1><button>Logout</button>', False, True),
                ('<button>Logout</button>', False, True),
                ('<h1>Login failed, please try again with your credentials</h1><input type="password">', True, False),
                ('<h1>已登录的工作台，可以搜索查看各项业务功能</h1><input type="text"><button>退出登录</button>', False, True),
                ('<h1>已登入的工作台，可以搜尋查看各項業務功能</h1><input type="text"><a>退出登錄</a>', False, True),
                ('<h1>Session expired, please log in again</h1><input type="password"><button>Logout</button>', True, False),
                ('<h1>请输入短信验证码后登录您的企业协作平台</h1><input type="text"><button>登录</button>', True, False),
            ]
            for html, blocked, authenticated in fixtures:
                await page.goto('data:text/html;charset=utf-8,' + quote(html))
                state = await human.inspect(browser)
                assert state['blocked'] == blocked, state
                assert state['authenticated'] == authenticated, state
            # Unknown site / same-URL SPA: a new account UI plus session marker
            # must release the production wait without a visible logout button.
            await page.goto('https://example.com')
            await page.evaluate('() => { document.body.innerHTML = \'<h1>Login</h1><input type="password">\'; localStorage.removeItem("auth-test-session"); }')
            generic = HumanInteraction(folder, poll_interval=.1, stable_seconds=.2)
            assert (await generic.inspect(browser))['blocked']
            await page.evaluate('() => { document.body.innerHTML = \'<header><span class="user-name">Test user</span></header><main>Dashboard</main>\'; localStorage.setItem("auth-test-session", "fixture"); }')
            generic_state = await generic.inspect(browser)
            assert generic_state['authenticated'], generic_state
            await page.evaluate('() => localStorage.removeItem("auth-test-session")')
            # Real DOM -> wait loop -> manual page change -> automatic resume.
            await page.goto('data:text/html;charset=utf-8,' + quote(fixtures[0][0]))
            human.poll_interval = .05
            human.stable_seconds = .15
            agent = SimpleNamespace(browser_session=browser,
                                    state=SimpleNamespace(last_result=[]),
                                    history=SimpleNamespace(history=[]))
            # Let the page simulate the user's SPA login, avoiding concurrent
            # CDP page.goto and inspect calls from two Python tasks.
            await page.evaluate("""() => {
                setTimeout(() => {
                    document.body.innerHTML = '<h1>已登录的工作台，可以搜索查看各项业务功能</h1><input type="text"><button>退出登录</button>';
                }, 1500);
            }""")
            waiting = asyncio.create_task(human.on_step_start(agent))
            try:
                await asyncio.sleep(.25)
                assert not waiting.done(), 'Agent must wait on the login form'
                await asyncio.wait_for(waiting, 30)
                assert not human.pending, 'Signed-in search page must release the wait'
            finally:
                if not waiting.done():
                    waiting.cancel()
                    await asyncio.gather(waiting, return_exceptions=True)
            await page.goto('https://www.iquicker.com.cn/login/')
            assert (await human.inspect(browser))['blocked']
            print(f'PASS: {len(fixtures)} real DOM fixtures, login wait/resume, and live iQuicker login route')
        finally:
            await browser.kill()


if __name__ == '__main__':
    asyncio.run(main())
