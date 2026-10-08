"""Run the authorized six paired B tasks serially with input and output ledgers."""
import asyncio
import datetime
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import time
import uuid

HERE = pathlib.Path(__file__).resolve().parent
SOURCE = HERE / 'b-inputs/controlled-v02'
WORKSPACE = pathlib.Path(r'C:\Users\bulin\artifacttrace\templates\at-template')
REPORTS = HERE / 'b-runs/controlled-v02'
MODEL = 'sophnet/DeepSeek-V4-Flash-0731'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


async def rpc(method, payload):
    import websockets
    request_id = str(uuid.uuid4())
    async with websockets.connect('ws://127.0.0.1:8080/ws', max_size=64 * 1024 * 1024) as ws:
        await ws.send(json.dumps({'type': method, 'id': request_id, 'payload': payload}, ensure_ascii=False))
        while True:
            message = json.loads(await asyncio.wait_for(ws.recv(), 60))
            if message.get('id') == request_id:
                if not message.get('success'):
                    raise RuntimeError('AT RPC failed: ' + json.dumps(message, ensure_ascii=False))
                return message['payload']


def copied_inputs(task):
    for relative in ['TASK.md', 'schema.json', 'INDEX.json']:
        a, b = task / 'aqi/entity-extract' / relative, task / 'claudecode/entity-extract' / relative
        if sha(a) != sha(b):
            raise RuntimeError('Combination inputs differ: ' + relative)
    files = list((task / 'aqi/entity-extract').glob('*/inputs/*'))
    for a in files:
        b = task / 'claudecode/entity-extract' / a.relative_to(task / 'aqi/entity-extract')
        if sha(a) != sha(b):
            raise RuntimeError('Combination page inputs differ')


def progress(task, combination):
    root = task / combination / 'entity-extract'
    pages = read(root / 'INDEX.json')['pages']
    return {'outputs': sum((root / p['dir'] / 'output/concepts.json').is_file() for p in pages), 'pages': len(pages)}


def verify_task_inputs(task):
    manifest = read(task / 'input-freeze.json')
    for item in manifest['files']:
        if sha(task / item['file']) != item['sha256']:
            raise RuntimeError('Frozen input modified by candidate: ' + item['file'])


def prepare_tasks():
    manifest = read(SOURCE / 'freeze.json')
    for item in manifest['source_files']:
        if sha(pathlib.Path(item['file'])) != item['sha256']:
            raise RuntimeError('Prepared source changed')
    for item in manifest['input_files']:
        if sha(SOURCE / item['file']) != item['sha256']:
            raise RuntimeError('Prepared B input changed')
    tasks = []
    for name in manifest['summary']:
        task_id = 'benchmark-20261008-b-' + name
        task = WORKSPACE / 'tasks' / task_id
        if task.exists():
            raise RuntimeError('Task exists; no silent resume: ' + task_id)
        task.mkdir()
        (task / 'TASK.md').write_text('# Paired offline B extraction\nOnly process your assigned combination directory. '
                                     'Do not browse websites, use subagents, read scoring gold, or read other combination outputs.\n', encoding='utf-8')
        for combination in ['aqi', 'claudecode']:
            shutil.copytree(SOURCE / name, task / combination / 'entity-extract')
        copied_inputs(task)
        files = [p for p in task.rglob('*') if p.is_file()]
        write(task / 'input-freeze.json', {'files': [{'file': str(p.relative_to(task)), 'sha256': sha(p)} for p in sorted(files)]})
        tasks.append({'run': name, 'task_id': task_id, 'path': str(task), 'pages': manifest['summary'][name]['states']})
    return tasks


def run_aqi(task_id, task, out, selected=None):
    prompt = ('离线 Benchmark B：只处理 aqi/entity-extract/。先读TASK.md、schema.json、INDEX.json，'
              '逐页读inputs并写各页output/concepts.json，自查schema。只用现有材料，'
              '不打开网页、不回溯trace、不读评分gold或另一组合目录，不调用其他agent。'
              '一次处理完整清单；每5页汇报计数，结束时区分完成、失败、缺失页。')
    if selected is not None:
        prompt += '\n本次是留痕补跑，只处理以下缺失页：' + ', '.join(selected) + '。不得修改任何已存在的output/concepts.json。'
        prompt += '逐页按读取本页材料→写出本页结果的顺序推进。当前页output/concepts.json写出前，禁止读取下一页材料。不得先预读整批页面。'
    start = time.time()
    response = asyncio.run(rpc('runs.start', {'task_id': task_id, 'agent_id': '阿器',
                             'history_mode': 'one_on_one', 'inputs': {'prompt': prompt},
                             'run_mode': 'user_reply', 'call_from': 'user'}))
    write(out / 'start.json', response)
    run_id = None
    while True:
        runs = asyncio.run(rpc('runs.list', {'task_id': task_id, 'agent_id': '阿器', 'count': 2, 'offset': 0}))['runs']
        if runs:
            latest = runs[0]
            run_id = latest.get('id') or latest.get('run_id')
            write(out / 'latest-run.json', latest)
            if latest.get('completed_at'):
                break
        write(out / 'progress.json', {**progress(task, 'aqi'), 'elapsed_s': time.time() - start,
                                      'run_id': run_id, 'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat()})
        # No automatic budget expansion or resume. Partial results remain visible.
        if time.time() - start > 3600:
            if run_id:
                asyncio.run(rpc('runs.stop', {'run_id': run_id}))
            raise TimeoutError('Aqi task exceeded the one-hour per-trace guard; preserve partial output and request decision')
        time.sleep(10)
    write(out / 'process.json', {'elapsed_s': time.time() - start, 'model': MODEL,
                                'run_id': run_id, 'status': latest.get('status'), **progress(task, 'aqi')})
    if latest.get('status') != 'completed':
        raise RuntimeError('Aqi run ended with status ' + str(latest.get('status')))


def run_claude(task, out, selected=None):
    root = task / 'claudecode/entity-extract'
    prompt = ('Read TASK.md, schema.json and INDEX.json here. Complete offline extraction for every listed page, '
              'read only the listed inputs, write each output/concepts.json and validate schema. '
              'Do not browse, read scoring gold or another combination directory, or use subagents. '
              'Keep references page-local. Complete the full list and report completed/failed/missing pages.')
    if selected is not None:
        prompt += '\nThis is a recorded recovery attempt. Process ONLY these missing page directories: ' + ', '.join(selected) + '. Do not modify any existing output/concepts.json.'
        prompt += ' Process one page at a time: read that page inputs, write its output, then move to the next page. Do not read ANY later page inputs until the current page output/concepts.json has been written. Do not preload the full batch.'
    cmd = ['claude', '--print', '--bare', '--model', MODEL, '--permission-mode', 'acceptEdits',
           '--tools', 'Read,Write,Edit,Glob,Grep', '--allowedTools', 'Read', 'Write', 'Edit', 'Glob', 'Grep',
           '--disallowedTools', 'Bash', 'WebFetch', 'WebSearch', 'Agent', 'Task',
           '--output-format', 'stream-json', '--verbose', prompt]
    write(out / 'command.json', {'command': cmd, 'working_directory': str(root), 'model': MODEL})
    start = time.time()
    with (out / 'stdout.jsonl').open('w', encoding='utf-8') as stdout, (out / 'stderr.log').open('w', encoding='utf-8') as stderr:
        process = subprocess.Popen(cmd, cwd=root, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, env={**os.environ, 'PYTHONUTF8': '1'})
        last_activity, last_marker = start, None
        while process.poll() is None:
            # Windows directory metadata can report a stale size while the writer is open.
            # Read the file handle directly; an idle decision must not rely on stat().
            with (out / 'stdout.jsonl').open('rb') as stream:
                stream.seek(0, 2)
                stdout_length = stream.tell()
            with (out / 'stderr.log').open('rb') as stream:
                stream.seek(0, 2)
                stderr_length = stream.tell()
            marker = (progress(task, 'claudecode')['outputs'], stdout_length, stderr_length)
            if marker != last_marker:
                last_marker, last_activity = marker, time.time()
            write(out / 'progress.json', {**progress(task, 'claudecode'), 'elapsed_s': time.time() - start,
                                          'pid': process.pid, 'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat()})
            if time.time() - last_activity > 300 or time.time() - start > 3600:
                process.terminate()
                process.wait(timeout=30)
                raise TimeoutError('Claude task exceeded 300 seconds without output/log activity or one-hour total guard; raw attempt retained')
            time.sleep(10)
    write(out / 'process.json', {'exit_code': process.returncode, 'elapsed_s': time.time() - start,
                                'model': MODEL, **progress(task, 'claudecode')})
    if process.returncode:
        raise RuntimeError('Claude CLI failed; inspect retained stderr, do not automatically restart')


def main():
    if REPORTS.exists():
        raise RuntimeError('B report directory already exists')
    REPORTS.mkdir(parents=True)
    tasks = prepare_tasks()
    write(REPORTS / 'experiment.json', {'tasks': tasks, 'model': MODEL, 'order': 'aqi then claudecode per trace',
                                      'harness_guard_s': 3600, 'strategy': 'fresh task per trace; raw outputs retained',
                                      'source_freeze_sha256': sha(SOURCE / 'freeze.json')})
    for info in tasks:
        task = pathlib.Path(info['path'])
        for combination in ['aqi', 'claudecode']:
            out = REPORTS / info['run'] / combination
            out.mkdir(parents=True)
            print('Starting B', info['run'], combination, info['pages'], 'pages', flush=True)
            try:
                (run_aqi(info['task_id'], task, out) if combination == 'aqi' else run_claude(task, out))
                verify_task_inputs(task)
                write(out / 'output-hashes.json', {'files': [{'file': str(p), 'sha256': sha(p)}
                                                           for p in sorted((task / combination / 'entity-extract').glob('*/output/concepts.json'))]})
                print('Completed B', info['run'], combination, progress(task, combination), flush=True)
            except Exception as exc:
                write(out / 'error.json', {'error': str(exc), **progress(task, combination)})
                raise
    print('All twelve B jobs completed', flush=True)


if __name__ == '__main__':
    main()
