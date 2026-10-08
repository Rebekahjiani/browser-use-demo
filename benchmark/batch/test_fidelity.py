import unittest
from audit_fidelity import timeline


class Tests(unittest.TestCase):
    def manifest(self):
        return {'startedAt': 0, 'stoppedAt': 30, 'segments': [
            {'segmentIndex': 0, 'filePath': 'a', 'startedAt': 0, 'stoppedAt': 10, 'durationMs': 10, 'status': 'completed'},
            {'segmentIndex': 1, 'filePath': 'b', 'startedAt': 20, 'stoppedAt': 30, 'durationMs': 10, 'status': 'completed'}]}

    def test_real_gap_not_hidden(self):
        r = timeline(self.manifest())
        self.assertTrue(r['timeline_reliable'])
        self.assertEqual(r['provisional_gaps'], [{'start': 10, 'stop': 20, 'ms': 10}])

    def test_negative_interval_not_used_as_coverage(self):
        m = self.manifest()
        m['segments'][0]['startedAt'] = 15
        r = timeline(m)
        self.assertFalse(r['timeline_reliable'])
        self.assertIn(0, r['invalid_timestamp_segments'])

    def test_reused_file_path_invalidates_timeline(self):
        m = self.manifest()
        m['segments'][1]['filePath'] = 'a'
        self.assertFalse(timeline(m)['timeline_reliable'])


if __name__ == '__main__':
    unittest.main()
