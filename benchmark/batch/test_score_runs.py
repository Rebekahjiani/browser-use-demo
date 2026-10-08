"""Regress arbitrary-run admission, immutable inputs and historical scoring."""
import copy
import json
import pathlib
import shutil
import tempfile
import unittest
import score_runs as batch


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.historical = batch.read(batch.HERE / 'historical.runs.json')
        source = pathlib.Path(self.historical['runs'][0]['snapshots'])
        source = next(source.glob('*/accessibility.json')).parent
        self.snapshots = self.root / 'new-run/snapshots/0001'
        self.snapshots.mkdir(parents=True)
        for name in ['accessibility.json', 'page.html']:
            shutil.copyfile(source / name, self.snapshots / name)
        self.spec = {'gold': str(batch.BENCHMARK / 'coverage-v3/gold.v1.json'),
                     'mapping': str(batch.BENCHMARK / 'ground-truth-vnext/db-ui-mapping.v1.json'),
                     'runs': [{'id': 'new-third-party-run', 'strategy': 'custom',
                               'snapshots': str(self.snapshots.parent)}]}

    def tearDown(self):
        self.tmp.cleanup()

    def frozen(self):
        spec = self.root / 'spec.json'
        batch.write(spec, self.spec)
        bundle = self.root / 'bundle'
        batch.freeze(spec, bundle)
        return bundle

    def test_arbitrary_run_and_identical_replay(self):
        bundle = self.frozen()
        output = self.root / 'report'
        batch.score(bundle, output)
        before = (output / 'results.json').read_bytes()
        batch.score(bundle, output)
        self.assertEqual(before, (output / 'results.json').read_bytes())
        self.assertIn('new-third-party-run', batch.read(output / 'results.json')['results'])

    def test_mutated_source_rejected(self):
        bundle = self.frozen()
        with (self.snapshots / 'page.html').open('a', encoding='utf-8') as stream:
            stream.write('tampered')
        with self.assertRaisesRegex(RuntimeError, 'Frozen input changed'):
            batch.verify(bundle)

    def test_mutated_rules_rejected(self):
        bundle = self.frozen()
        with (bundle / 'ui_engine.py').open('a', encoding='utf-8') as stream:
            stream.write('\n# changed')
        with self.assertRaisesRegex(RuntimeError, 'Bundle changed'):
            batch.verify(bundle)

    def test_missing_pair_rejected_before_freeze(self):
        (self.snapshots / 'page.html').unlink()
        with self.assertRaisesRegex(ValueError, 'paired HTML'):
            batch.validate_runs(self.spec, self.root)

    def test_duplicate_run_not_counted_as_repetition(self):
        other = copy.deepcopy(self.spec['runs'][0])
        other['id'] = 'fake-repeat'
        self.spec['runs'].append(other)
        with self.assertRaisesRegex(ValueError, 'independent run'):
            batch.validate_runs(self.spec, self.root)

    def test_historical_scores_match_original(self):
        report = batch.read(batch.HERE / 'reports/historical-v1/results.json')['results']
        old = batch.read(batch.BENCHMARK / 'coverage-v3/results.v1.json')['results']
        for new_id, old_id in [('drive-historical', 'drive'), ('browser-use-historical', 'browser-use')]:
            for kind, metric in old[old_id]['metrics'].items():
                self.assertEqual(report[new_id]['metrics'][kind],
                                 {'hit': metric['supported'], 'denominator': metric['denominator']})


if __name__ == '__main__':
    unittest.main()
