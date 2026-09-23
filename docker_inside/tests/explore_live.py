"""Manual login followed by a bounded read-only model exploration."""
import argparse
import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import subprocess
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'docker_inside'))
from dotenv import load_dotenv
from browser_ape import (COMPLETION_RULE, disconnect_browser, make_llm,
                          start_browser)
from browser_use import Browser
from human_interaction import HumanInteraction, LoginGuardAgent


async def launch_chrome(folder, headless, user_data_dir=None):
    """Match Docker's external-Chrome/CDP lifecycle; no asyncio child pipes."""
    chrome = os.getenv('BROWSER_EXECUTABLE_PATH') or r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    profile = Path(user_data_dir) if user_data_dir else folder / 'profile'
    profile.mkdir(parents=True, exist_ok=True)
    command = [chrome, '--remote-debugging-port=0', '--remote-debugging-address=127.0.0.1',
               f'--user-data-dir={profile}', '--no-first-run', '--no-default-browser-check',
               '--disable-extensions', '--new-window']
    if headless:
        command.append('--headless=new')
    command.append('about:blank')
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        port_file = profile / 'DevToolsActivePort'
        if port_file.exists():
            lines = port_file.read_text().splitlines()
            if lines:
                port = int(lines[0])
                try:
                    with urlopen(f'http://127.0.0.1:{port}/json/version', timeout=1) as response:
                        if response.status == 200:
                            return process, port
                except OSError:
                    pass
        if process.poll() is not None:
            raise RuntimeError('Chrome 启动失败')
        await asyncio.sleep(.2)
    process.terminate()
    raise TimeoutError('Chrome CDP 启动超时')


def acquire_profile_lock(profile):
    lock_path = Path(profile) / '.explore_live.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            handle = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(handle, str(os.getpid()).encode('ascii'))
            os.close(handle)
            return lock_path
        except FileExistsError:
            try:
                owner = int(lock_path.read_text(encoding='ascii').strip())
                os.kill(owner, 0)
            except (OSError, ValueError):
                lock_path.unlink(missing_ok=True)
                continue
            raise RuntimeError(f'Chrome profile 已被另一个 explore_live 进程使用（PID {owner}）。')
    raise RuntimeError('无法获取 Chrome profile 锁。')


async def main(args):
    load_dotenv(ROOT / '.env')
    key, base, model = (os.getenv(k) for k in ('OPENAI_API_KEY', 'OPENAI_BASE_URL', 'MODEL'))
    if os.getenv('AT_SETTINGS_PATH'):
        settings = json.loads(Path(os.environ['AT_SETTINGS_PATH']).read_text(encoding='utf-8'))
        provider, configured_model = settings['defaultModel'].split('/', 1)
        config = settings['modelProviders'][provider]
        key, base, model = config['apiKey'], config['baseUrl'], model or configured_model
    llm = make_llm(key, base, model)
    folder = ROOT / 'runs' / ('explore-live-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    folder.mkdir(parents=True)
    process = None
    profile_lock = None
    port = args.port
    browser = None
    result = {'success': False, 'task': args.task, 'errors': ['interrupted']}
    try:
        if args.user_data_dir:
            profile_lock = acquire_profile_lock(args.user_data_dir)
        if not port:
            process, port = await launch_chrome(folder, args.headless, args.user_data_dir)
        browser = await start_browser(port, retries=3, retry_delay=1)
        result = await run_task(browser, args, folder, llm)
    except Exception as exc:
        result = {'success': False, 'task': args.task, 'errors': [f'{type(exc).__name__}: {exc}']}
    finally:
        await disconnect_browser(browser)
        if process is not None and (args.headless or browser is None):
            process.terminate()
            try:
                await asyncio.to_thread(process.wait, timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                await asyncio.to_thread(process.wait, timeout=5)
        (folder / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if profile_lock is not None:
            profile_lock.unlink(missing_ok=True)


async def run_task(browser, args, folder, llm):
    # CDP attachment may focus a new about:blank tab rather than the visible tab.
    await (await browser.get_current_page()).goto(args.url)
    # Do not close tabs from cached get_tabs() metadata immediately after goto:
    # a navigating target can still be listed as about:blank at this point.
    human = HumanInteraction(folder, timeout=600)
    if args.baseline:
        human.login_baseline = json.loads(Path(args.baseline).read_text(encoding='utf-8'))
        human.pending = True
    print(f'OUTPUT: {folder}', flush=True)
    content_policy = ('允许读取用户明确指定的邮件正文，但不得发送、回复、转发、删除、标记已读或修改任何邮件。'
                      if args.allow_content_read else
                      '不得打开邮件正文、聊天会话或文件内容。')
    agent = LoginGuardAgent(human=human, task=args.task + COMPLETION_RULE,
        llm=llm, browser=browser, tools=human.tools,
        extend_system_message='只读测试。遇到登录必须 handoff_browser 等待用户。禁止输入账号密码。'
        + content_policy + '完成用户明确任务后立即 done。',
        use_vision=False, use_judge=False, max_actions_per_step=1,
        llm_timeout=90, step_timeout=150, max_failures=3,
        file_system_path=str(folder / 'agent-files'))
    history = await agent.run(max_steps=12, on_step_start=human.on_step_start, on_step_end=human.on_step_end)
    history.save_to_file(folder / 'history.json')
    result = {'success': history.is_successful(), 'steps': len(history.history), 'max_steps': 12,
              'result': history.final_result(), 'errors': history.errors()}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int)
    parser.add_argument('--url', default='https://www.feishu.cn/messenger/')
    parser.add_argument('--baseline')
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--user-data-dir',
                        help='可选：复用已建立信任的 Chrome profile；不要与正在运行的 Chrome 共用')
    parser.add_argument('--allow-content-read', action='store_true',
                        help='允许读取用户任务明确指定的内容，仍禁止任何写操作')
    parser.add_argument('--task', required=True)
    asyncio.run(main(parser.parse_args()))
