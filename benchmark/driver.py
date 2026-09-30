"""Benchmark-owned helpers, initially copied from docker_inside at fa45a5e.
Changes here do not affect the independent container driver.
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

