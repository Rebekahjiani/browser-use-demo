"""Observed B usage/runtime records; gateway pricing is not inferred."""
import collections
import json
import pathlib
import run_b as b


def build():
    rows = []
    for info in b.read(b.REPORTS / 'experiment.json')['tasks']:
        for combination in ['aqi', 'claudecode']:
            parent = b.REPORTS / info['run'] / combination
            for directory in [parent, *sorted(parent.glob('attempt-*'))]:
                row = {'trace': info['run'], 'combination': combination, 'attempt': directory.name,
                       'directory': str(directory), 'billing_cost': None}
                process_file = directory / 'process.json'
                if process_file.exists():
                    row['process'] = b.read(process_file)
                if (directory / 'interruption.json').exists():
                    row['interruption'] = b.read(directory / 'interruption.json')
                if combination == 'aqi' and (directory / 'latest-run.json').exists():
                    run = b.read(directory / 'latest-run.json')
                    calls = [event for event in run.get('events', []) if event.get('event_type') == 'model_call_completed']
                    row['status'] = run.get('status')
                    row['model_calls_completed'] = len(calls)
                    row['model_call_failures_recorded'] = sum(event.get('event_type') == 'model_call_failed' for event in run.get('events', []))
                    row['completed_call_token_usage'] = {
                        key: sum(event.get('head', {}).get('token_usage', {}).get(key, 0) for event in calls)
                        for key in ['input', 'output']}
                    row['usage_basis'] = 'Sum of completed AT model-call events; failed-call billing is unavailable.'
                elif combination == 'claudecode' and (directory / 'stdout.jsonl').exists():
                    records = []
                    incomplete_lines = 0
                    with (directory / 'stdout.jsonl').open(encoding='utf-8-sig') as stream:
                        for line in stream:
                            try:
                                records.append(json.loads(line))
                            except ValueError:
                                incomplete_lines += 1
                    results = [record for record in records if record.get('type') == 'result']
                    row['stream_event_types'] = dict(collections.Counter(record.get('type') for record in records))
                    row['incomplete_json_lines'] = incomplete_lines
                    if results:
                        result = results[-1]
                        row['cli_result'] = {key: result.get(key) for key in
                                             ['subtype', 'is_error', 'num_turns', 'duration_ms', 'usage', 'modelUsage', 'terminal_reason']}
                        row['cli_estimated_cost_usd'] = result.get('total_cost_usd')
                        row['usage_basis'] = 'Final CLI result counters; pricing costBasis may be unknown and estimate is not a bill.'
                    else:
                        row['usage_basis'] = 'No terminal CLI result; input/output token totals are unavailable, not zero.'
                else:
                    continue
                rows.append(row)
    result = {'rows': rows,
              'limitations': ['All original and recovery attempts are included; do not compare successful attempts alone.',
                              'AT completed-call usage and final CLI usage have different accounting formats.',
                              'Claude estimated USD is not provider billing; unknown pricing is not resolved by assumptions.',
                              'Interrupted or failed calls can have unreported usage.']}
    b.write(b.REPORTS / 'cost-ledger.json', result)
    return result


if __name__ == '__main__':
    print(json.dumps({'attempts': len(build()['rows'])}))
