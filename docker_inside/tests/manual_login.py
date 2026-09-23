"""Open Juhaokai and exercise the production login wait, without an LLM."""
import asyncio
from datetime import datetime
import os
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'docker_inside'))
os.environ['ANONYMIZED_TELEMETRY'] = 'false'
os.environ['BROWSER_USE_CLOUD_SYNC'] = 'false'

from dotenv import load_dotenv
from browser_use import Browser
from human_interaction import HumanInteraction


async def main():
    load_dotenv(ROOT / '.env')
    folder = ROOT / 'runs' / ('jhk-login-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    folder.mkdir(parents=True)
    browser = Browser(
        executable_path=os.getenv('BROWSER_EXECUTABLE_PATH') or
        (r'C:\Program Files\Google\Chrome\Application\chrome.exe' if sys.platform == 'win32' else None),
        headless=False, keep_alive=True,
        user_data_dir=str(ROOT / '.browser-profile-jhk-test'),
        enable_default_extensions=False,
    )
    await browser.start()
    page = await browser.get_current_page()
    await page.goto('https://jhk.juhaokai.cn:10003')
    human = HumanInteraction(folder, timeout=600)
    # Explicitly wait even if navigation has not yet rendered the login form.
    human.pending = True
    agent = SimpleNamespace(browser_session=browser,
                            state=SimpleNamespace(last_result=[]),
                            history=SimpleNamespace(history=[]))
    print(f'Login test status: {folder / "ape-status.json"}', flush=True)
    await human.on_step_start(agent)
    # Reaching this statement proves the actual production wait has returned.
    print('PASS: login wait returned; the next agent step can execute.', flush=True)
    print('Browser stays open for inspection.', flush=True)


if __name__ == '__main__':
    asyncio.run(main())
