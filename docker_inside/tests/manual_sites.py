"""Visible, read-only login transition test for QQ Mail and Feishu."""
import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'docker_inside'))
os.environ['ANONYMIZED_TELEMETRY'] = 'false'
os.environ['BROWSER_USE_CLOUD_SYNC'] = 'false'
from browser_use import Browser
from human_interaction import LOGIN_SCRIPT


async def main():
    site = sys.argv[1] if len(sys.argv) > 1 else 'qq'
    url = {'qq': 'https://mail.qq.com/', 'feishu': 'https://www.feishu.cn/messenger/'}[site]
    folder = ROOT / 'runs' / (site + '-manual-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    folder.mkdir(parents=True)
    browser = Browser(headless=False, keep_alive=True,
                      executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                      user_data_dir=str(folder / 'profile'), enable_default_extensions=False)
    await browser.start()
    page = await browser.get_current_page()
    await page.goto(url)
    print(f'OPEN: {site}; report directory: {folder}', flush=True)
    previous = None
    for _ in range(600):
        try:
            page = await browser.get_current_page()
            # Reload the detector so fixes can be checked without another login.
            state = json.loads(await page.evaluate((ROOT / 'docker_inside/login_state.js').read_text(encoding='utf-8'), ''))
            state['frames'] = json.loads(await page.evaluate('''() => [...document.querySelectorAll('iframe')].filter(e => e.getClientRects().length).map(e => { const u = new URL(e.src || 'about:blank', location.href); return {origin:u.origin,path:u.pathname,title:e.title}; })'''))
            if state != previous:
                (folder / 'state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
                print(json.dumps(state, ensure_ascii=False), flush=True)
                previous = state
        except Exception as exc:
            print(type(exc).__name__, flush=True)
        await asyncio.sleep(2)


if __name__ == '__main__':
    asyncio.run(main())
