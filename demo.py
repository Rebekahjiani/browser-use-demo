"""Visible browser-use demo. Credentials stay in the existing settings file."""
import argparse
import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')
os.environ.setdefault('ANONYMIZED_TELEMETRY', 'false')
os.environ.setdefault('BROWSER_USE_CLOUD_SYNC', 'false')

from browser_use import Agent, Browser, ChatOpenAI
from human_interaction import HumanInteraction, HumanInputCancelled, wait_for_browser

TASK = (
    '打开 https://books.toscrape.com/ ，通过页面上的 Travel 分类链接进入分类。'
    '比较该分类所有书的价格，打开最便宜的一本的详情页。'
    '用中文报告完整书名、价格、库存数量和详情页链接。不要加入购物车。'
)


def make_llm():
    settings_path = os.getenv('AT_SETTINGS_PATH')
    if settings_path:
        settings = json.loads(Path(settings_path).expanduser().read_text())
        provider_name, model = settings['defaultModel'].split('/', 1)
        provider = settings['modelProviders'][provider_name]
        key, base_url = provider['apiKey'], provider['baseUrl']
    else:
        key = os.getenv('OPENAI_API_KEY')
        base_url = os.getenv('OPENAI_BASE_URL')
        model = os.getenv('MODEL')
    model = os.getenv('MODEL') or model
    if not key or not model:
        raise ValueError('请在 .env 配置 AT_SETTINGS_PATH，或 OPENAI_API_KEY / MODEL。')
    print(f'模型：{model}', flush=True)
    return ChatOpenAI(
        model=model, api_key=key, base_url=base_url,
        temperature=0.2, frequency_penalty=None, reasoning_effort=None,
        timeout=60, max_retries=1,
    )


def make_browser():
    chrome = os.getenv('BROWSER_EXECUTABLE_PATH')
    if not chrome:
        if sys.platform == 'darwin':
            chrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        else:
            chrome = shutil.which('chromium') or shutil.which('google-chrome')
    return Browser(
        executable_path=chrome,
        headless=False, keep_alive=True,
        user_data_dir=str(ROOT / '.browser-profile'),
        window_size={'width': 1280, 'height': 900},
        wait_between_actions=1.0,
        enable_default_extensions=False,
        highlight_elements=True,
    )


async def main(args):
    llm = None if args.smoke else make_llm()
    run_dir = ROOT / 'runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run_dir.mkdir(parents=True)
    browser = make_browser()
    print(f'结果目录：{run_dir}', flush=True)
    success = False
    try:
        await browser.start()
        if args.smoke:
            page = await browser.get_current_page()
            await page.goto('https://books.toscrape.com/')
            for _ in range(40):
                title = await page.evaluate('() => document.title')
                if 'All products' in title:
                    break
                await asyncio.sleep(0.5)
            success = 'All products' in title
            result = {'mode': 'browser-smoke', 'success': success,
                      'url': 'https://books.toscrape.com/', 'title': title}
        else:
            human = HumanInteraction()
            agent = Agent(
                task=args.task, llm=llm, browser=browser, tools=human.tools,
                extend_system_message=(
                    "缺少用户才能提供的信息时调用 handoff_browser，让用户直接在网页填写或选择，不要猜测。"
                    "遇到登录、验证码、密码输入或用户要求亲自操作时，调用 handoff_browser。"
                    "用户通过页面浮层点击继续后，重新观察页面并验证操作结果。"
                    "人工交互动作单独执行；信息已知时可直接填表，无需遇到每个输入框都询问。"
                ),
                use_vision=False, use_judge=False,
                max_failures=3, max_actions_per_step=2,
                llm_timeout=90, step_timeout=150,
                file_system_path=str(run_dir / 'agent-files'),
            )
            history = await agent.run(max_steps=args.max_steps, on_step_end=human.on_step_end)
            history.save_to_file(run_dir / 'history.json')
            success = history.is_successful() is True
            result = {'mode': 'agent', 'success': success,
                      'task': args.task, 'result': history.final_result(),
                      'steps': len(history.history), 'errors': history.errors()}
        await browser.take_screenshot(path=str(run_dir / 'final.png'), full_page=False)
        (run_dir / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
        if not args.no_wait:
            try:
                await wait_for_browser(browser, str(result.get('result') or '演示已结束，请查看当前页面。'), finished=True)
            except HumanInputCancelled as exc:
                print(f'{exc} 已完成的任务结果保留。', flush=True)
    except HumanInputCancelled as exc:
        success = False
        result = {'mode': 'agent', 'success': False, 'cancelled': True, 'reason': str(exc)}
        (run_dir / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(str(exc), flush=True)
    finally:
        await browser.kill()
    return 0 if success else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke', action='store_true', help='只检查浏览器，不调用模型')
    parser.add_argument('--task', default=TASK, help='自然语言演示任务')
    parser.add_argument('--max-steps', type=int, default=15)
    parser.add_argument('--no-wait', action='store_true', help='完成后自动关闭浏览器')
    args = parser.parse_args()
    try:
        sys.exit(asyncio.run(main(args)))
    except KeyboardInterrupt:
        print('\n演示已停止。')
        sys.exit(130)
