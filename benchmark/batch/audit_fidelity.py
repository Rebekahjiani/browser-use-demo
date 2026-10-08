"""Separate independently captured UI pairs from Chrome segment timeline integrity."""
import collections
import hashlib
import html
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def timeline(manifest):
    segments = manifest.get('segments', [])
    invalid = [s['segmentIndex'] for s in segments
               if s.get('stoppedAt', 0) < s.get('startedAt', 0) or
               abs(s.get('stoppedAt', 0) - s.get('startedAt', 0) - s.get('durationMs', 0)) > 5]
    paths = collections.Counter(s['filePath'] for s in segments)
    duplicates = {p: n for p, n in paths.items() if n > 1}
    failed = [{k: s.get(k) for k in ['segmentIndex', 'startedAt', 'stoppedAt', 'filePath', 'error']}
              for s in segments if s.get('status') != 'completed']
    valid = sorted((s['startedAt'], s['stoppedAt']) for s in segments
                   if s.get('status') == 'completed' and s['segmentIndex'] not in invalid)
    gaps = []
    end = manifest.get('startedAt', 0)
    for start, stop in valid:
        if start > end:
            gaps.append({'start': end, 'stop': start, 'ms': start - end})
        end = max(end, stop)
    if manifest.get('stoppedAt', end) > end:
        gaps.append({'start': end, 'stop': manifest['stoppedAt'], 'ms': manifest['stoppedAt'] - end})
    return {'invalid_timestamp_segments': invalid, 'duplicate_file_paths': duplicates,
            'failed_segments': failed, 'provisional_gaps': gaps,
            'timeline_reliable': not invalid and not duplicates,
            'gap_interpretation': 'If timestamps/paths are inconsistent, gaps cannot quantify actual lost events.'}


def normalized(text):
    return re.sub(r'\s+', ' ', html.unescape(text)).strip()


def main():
    spec_path = HERE / 'experiments/20261008/controlled-v02/runs.json'
    spec = read(spec_path)
    report = {'scope': 'UI snapshot integrity and recorder metadata; not complete action-response fidelity', 'runs': {}}
    for run in spec['runs']:
        root = pathlib.Path(run['snapshots'])
        pairs = []
        for ax in sorted(root.glob('*/accessibility.json')):
            raw = read(ax)
            web = next(n for n in raw['nodes'] if n.get('role', {}).get('value') == 'RootWebArea')
            url = next((p['value']['value'] for p in web.get('properties', []) if p['name'] == 'url'), None)
            page = ax.parent / 'page.html'
            match = re.search(r'<title\b[^>]*>(.*?)</title>', page.read_text(encoding='utf-8-sig'), re.S | re.I)
            same_title = bool(match) and normalized(match[1]) == normalized(web.get('name', {}).get('value', ''))
            meta = ax.parent / 'metadata.json'
            metadata = read(meta) if meta.exists() else {}
            pairs.append({'snapshot': str(ax.parent), 'url': url, 'title_pair_matches': same_title,
                          'metadata_url_matches': metadata.get('url') == url if metadata else None,
                          'captured_at': metadata.get('captured_at'),
                          'sha256_AX': hashlib.sha256(ax.read_bytes()).hexdigest(),
                          'sha256_HTML': hashlib.sha256(page.read_bytes()).hexdigest()})
        manifests = []
        for artifact in run['artifacts']:
            path = pathlib.Path(artifact)
            if path.name == 'trace.segments.summary.json':
                manifest_path = path.parent / 'trace.segments.manifest.json'
                manifests.append({'source': str(manifest_path),
                                  'sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                                  **timeline(read(manifest_path))})
        report['runs'][run['id']] = {'snapshot_count': len(pairs),
            'title_pair_matches': sum(p['title_pair_matches'] for p in pairs),
            'metadata_url_conflicts': sum(p['metadata_url_matches'] is False for p in pairs),
            'snapshot_timestamp_missing': sum(not p['captured_at'] for p in pairs),
            'pairs': pairs, 'recorder_timelines': manifests,
            'UI_use': 'Use witnessed AX/HTML facts; mismatches require page-level review.',
            'trace_fidelity_status': 'not_accepted',
            'limitation': 'Matching titles do not prove atomic DOM/AX capture or full action-response causality.'}
    output = HERE / 'reports/controlled-v02/fidelity-audit.json'
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for name, r in report['runs'].items():
        print(name, 'title pairs', r['title_pair_matches'], '/', r['snapshot_count'],
              'invalid intervals', sum(len(m['invalid_timestamp_segments']) for m in r['recorder_timelines']))


if __name__ == '__main__':
    main()
