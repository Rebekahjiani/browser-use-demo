import pathlib
import tempfile
import unittest
from b_path_diagnostic import support, rules


class Paths(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        path = pathlib.Path(self.tmp.name) / 'tree.yml'
        path.write_text('- main\n  - list\n    - listitem\n      - strong\n        - link "Example Product"\n      - StaticText "$12.00"\n      - StaticText "Other text"\n  - table\n    - row\n      - rowheader "ASIN"\n      - cell "B123"\n', encoding='utf-8')
        self.nodes = rules.parse_tree(path)
    def tearDown(self):
        self.tmp.cleanup()
    def check(self, ref, field):
        return support(ref, rules.field_markers(field, self.nodes), self.nodes)['status']
    def test_specific_role_path(self):
        self.assertEqual(self.check('page.aria.yml:list:listitem:strong:link', 'product.name'), 'supported_field_specific_role_path')
    def test_broad_text_not_price_support(self):
        self.assertEqual(self.check('page.aria.yml:list:listitem:StaticText', 'product.price'), 'unresolved')
    def test_label_locates_field(self):
        self.assertEqual(self.check('page.aria.yml:main:table:ASIN', 'product.asin'), 'supported_chain_with_label')
    def test_wrong_ancestor(self):
        self.assertEqual(self.check('page.aria.yml:list:table:ASIN', 'product.asin'), 'unresolved')
    def test_wrong_field(self):
        self.assertEqual(self.check('page.aria.yml:list:listitem:strong:link', 'product.asin'), 'unresolved')
    def test_nonliteral_label(self):
        self.assertEqual(self.check('page.aria.yml:main:list:link:Product Name', 'product.name'), 'unresolved')


if __name__ == '__main__':
    unittest.main()
