import json
import pathlib
import tempfile
import unittest
from score import Page, fullmatch


class Tests(unittest.TestCase):
    def page(self, html, role='link', target='http://site/product.html'):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        p = pathlib.Path(folder.name)
        nodes = [
            {'nodeId': '0', 'role': {'value': 'RootWebArea'}, 'name': {'value': 'Category'},
             'properties': [{'name': 'url', 'value': {'value': 'http://site/category.html'}}]},
            {'nodeId': '1', 'role': {'value': 'heading'}, 'name': {'value': 'Category Items 1-12 of 20'}},
            {'nodeId': '2', 'role': {'value': role}, 'name': {'value': 'Product'},
             'properties': [{'name': 'url', 'value': {'value': target}}]}]
        (p / 'accessibility.json').write_text(json.dumps({'nodes': nodes}), encoding='utf-8')
        (p / 'page.html').write_text('<body class="catalog-category-view">' + html + '</body>', encoding='utf-8')
        return Page(p / 'accessibility.json')

    def test_product_card_link_supported(self):
        p = self.page('<li class="product-item"><a class="product-item-link" href="http://site/product.html">Product</a></li>')
        self.assertTrue(fullmatch(p, {'rule': 'product_card_relation'}))

    def test_navigation_cooccurrence_rejected(self):
        p = self.page('<nav><a href="http://site/product.html">Product</a></nav>')
        self.assertFalse(fullmatch(p, {'rule': 'product_card_relation'}))

    def test_matching_class_outside_card_rejected(self):
        p = self.page('<a class="product-item-link" href="http://site/product.html">Product</a>')
        self.assertFalse(fullmatch(p, {'rule': 'product_card_relation'}))

    def test_wrong_ax_target_rejected(self):
        p = self.page('<li class="product-item"><a class="product-item-link" href="http://site/product.html">Product</a></li>',
                      target='http://site/other.html')
        self.assertFalse(fullmatch(p, {'rule': 'product_card_relation'}))


if __name__ == '__main__':
    unittest.main()
