import unittest
from audit_b import reference


class References(unittest.TestCase):
    def test_role_name_is_page_local(self):
        tree = '- rowheader "ASIN"\n'
        self.assertEqual(reference('page.aria.yml:rowheader:ASIN', tree, set(), '000_state'), 'role_name_match')
        self.assertEqual(reference('page.aria.yml:rowheader:SKU', tree, set(), '000_state'), 'unresolved_anchor')

    def test_endpoint_presence_not_semantics(self):
        self.assertEqual(reference('E001', '', {'E001'}, '000_state'), 'endpoint_match')
        self.assertEqual(reference('E002', '', {'E001'}, '000_state'), 'unknown_endpoint')

    def test_page_cross_reference(self):
        self.assertEqual(reference('001_state', '', set(), '000_state'), 'unsupported_syntax')
        self.assertEqual(reference('000_state', '', set(), '000_state'), 'page_match')


if __name__ == '__main__':
    unittest.main()
