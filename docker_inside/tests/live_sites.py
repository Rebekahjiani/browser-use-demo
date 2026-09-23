"""Read-only live-site audit. Does not log in, submit forms, or call an LLM."""
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
from human_interaction import HumanInteraction

SITES = [
    ('qq_mail', 'https://mail.qq.com/', True),
    ('163_mail', 'https://mail.163.com/', True),
    ('outlook', 'https://outlook.live.com/mail/0/', None),
    ('feishu', 'https://accounts.feishu.cn/accounts/page/login', True),
    ('github', 'https://github.com/login', True),
    ('books', 'https://books.toscrape.com/', False),
    ('feishu_public', 'https://www.feishu.cn/', False),
]


async def main():
    folder = ROOT / 'runs' / ('live-sites-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    folder.mkdir(parents=True)
    browser = Browser(headless=True,
                      executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe' if sys.platform == 'win32' else None,
                      user_data_dir=str(folder / 'profile'), enable_default_extensions=False)
    results = []
    try:
        await browser.start()
        page = await browser.get_current_page()
        for name, url, expected in SITES:
            if len(sys.argv) > 1 and name not in sys.argv[1:]:
                continue
            row = dict(site=name, url=url, expected_blocked=expected, authenticated_flow='not_tested')
            try:
                await asyncio.wait_for(page.goto(url), 40)
                human = HumanInteraction(folder)
                states = []
                for _ in range(3):
                    await asyncio.sleep(3)
                    state = await asyncio.wait_for(human.inspect(browser), 20)
                    states.append(state)
                row['samples'] = states
                row['title'] = await page.evaluate('() => document.title')
                row['loading'] = await page.evaluate('() => ({readyState:document.readyState, textLength:document.body?.innerText.length || 0})')
                row['frames'] = json.loads(await page.evaluate('''() => [...document.querySelectorAll('iframe')].filter(e => e.getClientRects().length).map(e => { const u = new URL(e.src || 'about:blank', location.href); return {origin:u.origin,path:u.pathname,title:e.title}; })'''))
                row['pass'] = states[-1]['ready'] and (expected is None or states[-1]['blocked'] == expected) and not states[-1]['authenticated']
                await browser.take_screenshot(path=str(folder / f'{name}.png'), full_page=False)
            except Exception as exc:
                row['error'] = f'{type(exc).__name__}: {str(exc)[:300]}'
                row['pass'] = False
            results.append(row)
            (folder / 'report.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps(row, ensure_ascii=False), flush=True)
        print(f'REPORT: {folder / "report.json"}', flush=True)
    finally:
        await browser.kill()


if __name__ == '__main__':
    asyncio.run(main())
