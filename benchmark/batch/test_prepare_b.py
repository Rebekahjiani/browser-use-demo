import unittest
from prepare_b import pair_network, tree


class Tests(unittest.TestCase):
    def test_duplicate_outstanding_requests_not_guessed(self):
        rows = [{'type': 'request', 'url': 'x'}, {'type': 'request', 'url': 'x'}, {'type': 'response', 'url': 'x'}]
        self.assertEqual(pair_network(rows), [])

    def test_unique_exact_url_pair(self):
        rows = [{'type': 'request', 'url': 'x?a=1'}, {'type': 'response', 'url': 'x?a=2'}, {'type': 'response', 'url': 'x?a=1'}]
        self.assertEqual(len(pair_network(rows)), 1)

    def test_hidden_wrapper_keeps_visible_children_and_long_label(self):
        nodes = [{'nodeId': '0', 'role': {'value': 'RootWebArea'}, 'childIds': ['1']},
                 {'nodeId': '1', 'ignored': True, 'childIds': ['2']},
                 {'nodeId': '2', 'role': {'value': 'heading'}, 'name': {'value': 'X' * 200},
                  'properties': [{'name': 'level', 'value': {'value': 1}}]}]
        text = tree({'nodes': nodes})
        self.assertIn('X' * 200, text)
        self.assertIn('[level=1]', text)


if __name__ == '__main__':
    unittest.main()
