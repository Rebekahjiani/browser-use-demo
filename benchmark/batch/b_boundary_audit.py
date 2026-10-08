"""Observed offline tool boundary audit, separate from semantic scoring."""
import collections
import json
import ntpath
import pathlib
import run_b as b


def inside(path, root):
    if not isinstance(path, str) or not ntpath.isabs(path):
        return None
    normalized = ntpath.normcase(ntpath.normpath(path))
    normalized_root = ntpath.normcase(ntpath.normpath(str(root)))
    try:
        return ntpath.commonpath([normalized, normalized_root]) == normalized_root
    except ValueError:
        return False


def audit():
    rows = []
    for info in b.read(b.REPORTS / 'experiment.json')['tasks']:
        for combination in ['aqi', 'claudecode']:
            root = pathlib.Path(info['path']) / combination / 'entity-extract'
            parent = b.REPORTS / info['run'] / combination
            for directory in [parent, *sorted(parent.glob('attempt-*'))]:
                calls = []
                if combination == 'aqi' and (directory / 'latest-run.json').exists():
                    events = b.read(directory / 'latest-run.json').get('events', [])
                    outcomes = {event.get('tool_call_id'): event.get('head', {}).get('status') for event in events
                                if event.get('event_type') in ['tool_call_completed', 'tool_call_failed']}
                    for event in events:
                        if event.get('event_type') == 'tool_call_started':
                            tail = event.get('tail', {})
                            calls.append({'id': event.get('tool_call_id'), 'name': tail.get('algorithm', {}).get('algo_id'),
                                          'arguments': tail.get('configuration', {}).get('arguments', {}),
                                          'outcome': outcomes.get(event.get('tool_call_id'))})
                elif combination == 'claudecode' and (directory / 'stdout.jsonl').exists():
                    by_id = {}
                    with (directory / 'stdout.jsonl').open(encoding='utf-8-sig') as stream:
                        for line in stream:
                            try:
                                record = json.loads(line)
                            except ValueError:
                                continue
                            for block in record.get('message', {}).get('content', []):
                                if isinstance(block, dict) and block.get('type') == 'tool_use':
                                    by_id[block['id']] = {'id': block['id'], 'name': block.get('name'), 'arguments': block.get('input', {})}
                    calls = list(by_id.values())
                else:
                    continue
                outside, unresolved, forbidden = [], [], []
                allowed = {'read_file', 'write_file', 'edit_file', 'list_dir', 'glob', 'grep',
                           'apply_patch', 'Read', 'Write', 'Edit', 'Glob', 'Grep'}
                for call in calls:
                    if call['name'] not in allowed:
                        forbidden.append(call)
                    arguments = call['arguments']
                    if not isinstance(arguments, dict):
                        unresolved.append({'tool': call['name'], 'key': 'arguments', 'path': None,
                                           'reason': 'Arguments not available as a mapping in recorded event'})
                        continue
                    for key in ['file_path', 'path', 'root', 'directory']:
                        value = arguments.get(key)
                        if not isinstance(value, str):
                            continue
                        normalized = value
                        if value.startswith('task://'):
                            normalized = ntpath.join(info['path'], value[len('task://'):])
                        elif value.startswith('workspace://'):
                            normalized = ntpath.join(str(b.WORKSPACE), value[len('workspace://'):])
                        elif not ntpath.isabs(value):
                            # AT ToolContext::resolve_path uses task_dir for relative paths.
                            base = str(root) if combination == 'claudecode' else info['path']
                            normalized = ntpath.join(base, value)
                        status = inside(normalized, root)
                        entry = {'tool': call['name'], 'key': key, 'path': value, 'normalized': normalized,
                                 'outcome': call.get('outcome')}
                        if status is False:
                            entry['access_kind'] = 'directory_metadata' if call['name'] in ['list_dir', 'glob', 'Glob'] else 'file_content_or_write'
                            if ntpath.normcase(ntpath.normpath(normalized)) == ntpath.normcase(ntpath.join(info['path'], 'TASK.md')):
                                entry['access_kind'] = 'shared_task_instructions'
                            if call.get('outcome') == 'failed':
                                entry['access_kind'] = 'failed_path_attempt'
                            outside.append(entry)
                        elif status is None:
                            unresolved.append(entry)
                rows.append({'trace': info['run'], 'combination': combination, 'attempt': directory.name,
                             'tool_counts': dict(collections.Counter(call['name'] for call in calls)),
                             'outside_assigned_directory': outside, 'unresolved_paths': unresolved,
                             'unexpected_tools': forbidden})
    result = {'rows': rows, 'at_path_resolution_source': r'C:\Users\bulin\artifacttrace\crates\executor\src\tool_context.rs:580',
              'limitations': ['Observed tool calls only; this is not an operating-system sandbox proof.',
              'Unknown argument formats or relative AT paths require review; they are not silently treated as compliant.']}
    b.write(b.REPORTS / 'boundary-audit.json', result)
    return result


if __name__ == '__main__':
    result = audit()
    print(json.dumps({'attempts': len(result['rows']), 'outside': sum(len(r['outside_assigned_directory']) for r in result['rows']),
                      'unresolved': sum(len(r['unresolved_paths']) for r in result['rows']),
                      'unexpected_tools': sum(len(r['unexpected_tools']) for r in result['rows'])}))
