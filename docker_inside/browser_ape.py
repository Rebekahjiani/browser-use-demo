"""容器内 browser-use 自动探索驱动: 经 CDP 驱动现有 kiosk Chrome, 自动探索目标网址。

预置于镜像 /opt/kaiwu/ape/bin/, 由宿主机 scripts/browser-ape.sh 经 docker exec 调用。
所有输入均通过命令行参数传入 (不从环境读取)。
"""
import argparse
import asyncio
import json
import math
import os
import sys
from pathlib import Path

os.environ.setdefault('ANONYMIZED_TELEMETRY', 'false')
os.environ.setdefault('BROWSER_USE_CLOUD_SYNC', 'false')

from browser_use import Browser, ChatOpenAI
from human_interaction import HumanInteraction, LoginGuardAgent

DEFAULT_TASK = (
    '打开 {url} 并探索网站。遇到登录时等待用户自行完成登录。'
    '登录后浏览主要导航和功能页面，整理页面用途、可见功能及发现的问题。'
    '默认只进行浏览，不提交新增、修改、删除、发送或支付操作。用中文报告结果。'
)

DEFAULT_CDP_START_RETRIES = 3
DEFAULT_CDP_START_DELAY = 1.0

COMPLETION_RULE = (
    '\n\n结束条件：先把用户要求拆成有限的完成清单，每步核对已有证据。'
    '所有要求已满足时立即调用 done 并汇总结果，不要继续探索无关页面或等待步数耗尽。'
    '无法完成时调用 done(success=false)，说明已完成部分和具体阻碍。'
    '最大步数仅为安全上限，不是任务目标；不能因为接近上限就宣称完成。'
    '调用 done 前检查最终回复是否满足数量、格式和禁止事项。数量上限适用于整段回复，'
    '前言、补充说明也不能列出额外项目；只输出用户要求的结果。'
)


def build_task(args):
    template = args.task_template.strip()
    if not template:
        raise ValueError('--task-template 不能为空。')
    prompt = args.explore_prompt
    if args.explore_prompt_file is not None:
        prompt = Path(args.explore_prompt_file).read_text(encoding='utf-8-sig')
    if prompt is not None and not prompt.strip():
        raise ValueError('探索提示词不能为空。')
    task = template.replace('{url}', args.url)
    if prompt is not None:
        if template == DEFAULT_TASK:
            task = f'打开 {args.url}。只执行下面用户指定的任务，不额外进行全站探索。'
        task += '\n\n用户任务（任务范围和结束条件优先于基础模板）：\n' + prompt.strip().replace('{url}', args.url)
    return task + COMPLETION_RULE


def make_llm(api_key: str, base_url: str, model: str):
    if not api_key or not model:
        raise ValueError('缺少 --llm-api-key / --llm-model。')
    print(f'模型：{model}', flush=True)
    deepseek_model = 'deepseek' in model.lower()
    return ChatOpenAI(
        model=model, api_key=api_key, base_url=base_url or None,
        temperature=0.2, frequency_penalty=None, reasoning_effort=None,
        add_schema_to_system_prompt=deepseek_model,
        dont_force_structured_output=deepseek_model,
        timeout=60, max_retries=1,
    )


def make_browser(cdp_port: int):
    # 经 CDP 连接容器内已由看门狗拉起的 kiosk Chrome (而非 executable_path 另起浏览器)。
    # 具体参数名以 browser-use 0.13.10 为准 (实施时已核对 cdp_url)。
    return Browser(
        cdp_url=f'http://127.0.0.1:{cdp_port}',
        keep_alive=True,
        highlight_elements=True,
    )


async def start_browser(cdp_port: int, retries: int, retry_delay: float):
    """Connect to an externally managed Chrome, retrying transient CDP failures."""
    last_error = None
    for attempt in range(1, retries + 1):
        browser = make_browser(cdp_port)
        try:
            await browser.start()
            return browser
        except Exception as exc:
            last_error = exc
            print(f'连接 Chrome 失败（第 {attempt}/{retries} 次）：{type(exc).__name__}', flush=True)
            await disconnect_browser(browser)
            if attempt < retries:
                await asyncio.sleep(retry_delay)
    raise RuntimeError(f'无法连接 Chrome CDP（{retries} 次尝试均失败）。') from last_error


async def disconnect_browser(browser):
    """Close CDP/event resources while leaving the container's Chrome alive."""
    if browser is None:
        return
    try:
        await asyncio.wait_for(browser.stop(), timeout=15)
    except Exception as exc:
        # A disconnected tab or failed startup must not discard task results.
        print(f'浏览器会话清理未完成：{type(exc).__name__}', flush=True)
        try:
            await asyncio.wait_for(browser.reset(), timeout=5)
        except Exception:
            pass


async def main(args):
    task = args.resolved_task
    capture_dir = Path(args.capture_dir)
    capture_dir.mkdir(parents=True, exist_ok=True)

    result = {'mode': 'agent', 'success': False, 'url': args.url}
    browser = None
    try:
        llm = make_llm(args.llm_api_key, args.llm_base_url, args.llm_model)
        browser = await start_browser(args.cdp_port, args.cdp_start_retries,
                           args.cdp_start_delay)
        # The login guard may otherwise block the first navigation on about:blank.
        page = await browser.get_current_page()
        if page is None:
            raise RuntimeError('浏览器没有可用页面。')
        await page.goto(args.url)
        human = HumanInteraction(capture_dir, args.login_success_selector, args.login_wait_timeout)
        agent = LoginGuardAgent(
            human=human,
            task=task, llm=llm, browser=browser, tools=human.tools,
            extend_system_message=(
                '遇到登录、注册、登录验证码或密码页面时，必须调用 handoff_browser 等待用户登录。'
                '禁止自行点击注册、填写凭据、提交登录、切换登录方式或绕过登录。'
                '用户直接操作浏览器，系统检测登录完成后自动恢复，不存在弹窗或继续按钮。'
                '恢复后重新读取页面，不要沿用旧元素编号。'
                '其他表单缺少用户信息时不要猜测，结束任务并说明缺少的信息。'
                + COMPLETION_RULE
            ),
            use_vision=False, use_judge=False,
            max_failures=3, max_actions_per_step=1,
            llm_timeout=90, step_timeout=150,
            file_system_path=str(capture_dir / 'ape-agent-files'),
        )
        history = await agent.run(max_steps=args.max_steps,
                                  on_step_start=human.on_step_start,
                                  on_step_end=human.on_step_end)
        history.save_to_file(capture_dir / 'ape-history.json')
        success = history.is_successful() is True
        result = {
            'mode': 'agent', 'success': success,
            'url': args.url, 'task': task,
            'result': history.final_result(),
            'steps': len(history.history), 'errors': history.errors(),
            'stop_reason': ('completed' if success else
                            'max_steps' if any('maximum steps' in str(error).lower()
                                               for error in history.errors()) else 'incomplete'),
        }
    except Exception as exc:  # noqa: BLE001 探索异常不影响结果落盘与退出码
        result = {'mode': 'agent', 'success': False, 'url': args.url, 'error': str(exc)}
    finally:
        await disconnect_browser(browser)
        (capture_dir / 'ape-status.json').write_text(json.dumps({
            'state': 'completed' if result.get('success') else 'stopped',
            'message': '探索完成。' if result.get('success') else '探索已停止，请查看 ape-result.json。',
        }, ensure_ascii=False, indent=2), encoding='utf-8')
        # CDP 已显式断开；不 kill 容器看门狗管理的 Chrome。
        (capture_dir / 'ape-result.json').write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0 if result.get('success') else 1


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True, help='目标网址')
    parser.add_argument('--capture-dir', required=True, help='采集产物目录 (结果写入 <dir>/ape-result.json)')
    parser.add_argument('--llm-api-key', default='', help='LLM 网关 API Key')
    parser.add_argument('--llm-base-url', default='', help='OpenAI 兼容网关 base_url')
    parser.add_argument('--llm-model', default='', help='模型 id')
    parser.add_argument('--task-template', default=DEFAULT_TASK, help='基础任务模板，支持 {url}，省略时使用默认浏览探索任务')
    prompts = parser.add_mutually_exclusive_group()
    prompts.add_argument('--explore-prompt', help='补充探索提示词，追加到基础任务后，支持 {url}')
    prompts.add_argument('--explore-prompt-file', help='UTF-8 探索提示词文件（容器内路径），与 --explore-prompt 二选一')
    parser.add_argument('--max-steps', type=int, default=15, help='最大步数')
    parser.add_argument('--cdp-port', type=int, default=9222, help='Chrome 远程调试端口')
    parser.add_argument('--cdp-start-retries', type=int, default=DEFAULT_CDP_START_RETRIES,
                        help='连接 Chrome CDP 的最大尝试次数')
    parser.add_argument('--cdp-start-delay', type=float, default=DEFAULT_CDP_START_DELAY,
                        help='CDP 重试间隔秒数')
    parser.add_argument('--login-success-selector', default='', help='可选：仅登录后可见的元素 CSS 选择器')
    parser.add_argument('--login-wait-timeout', type=float, default=0, help='等待登录秒数，0 表示无限等待')
    args = parser.parse_args(argv)
    if not math.isfinite(args.login_wait_timeout) or args.login_wait_timeout < 0:
        parser.error('--login-wait-timeout 必须是大于等于 0 的有限数值')
    if args.max_steps < 1:
        parser.error('--max-steps 必须大于 0')
    if args.cdp_start_retries < 1:
        parser.error('--cdp-start-retries 必须大于 0')
    if not math.isfinite(args.cdp_start_delay) or args.cdp_start_delay < 0:
        parser.error('--cdp-start-delay 必须是大于等于 0 的有限数值')
    if not 1 <= args.cdp_port <= 65535:
        parser.error('--cdp-port 必须在 1 到 65535 之间')
    try:
        args.resolved_task = build_task(args)
    except (OSError, UnicodeError, ValueError) as exc:
        parser.error(str(exc))
    return args


if __name__ == '__main__':
    args = parse_args()
    try:
        sys.exit(asyncio.run(main(args)))
    except KeyboardInterrupt:
        print('\n探索已停止。', flush=True)
        sys.exit(130)
