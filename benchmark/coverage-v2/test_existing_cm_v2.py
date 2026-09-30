import unittest
from score_existing_cm_v2 import normalize

class MappingTests(unittest.TestCase):
    def test_annotated_aliases(self):
        c,_=normalize({'entities':[{'name':'商品','attributes':[{'name':'Qty（数量输入）'}]}, {'name':'分类','attributes':[{'name':'Price（Shop By Price 区间）'}]}]})
        self.assertEqual(c['attributes'], {'product.quantity','category.price_range'})
    def test_facet_not_category_count(self):
        c,u=normalize({'entities':[{'name':'价格区间','attributes':[{'name':'range'},{'name':'itemCount'}]}]})
        self.assertEqual(c['attributes'], {'category.price_range'})
        self.assertEqual(c['entities'],set())
        self.assertTrue(u)
    def test_generic_search_not_both_controls(self):
        c,_=normalize({'operations':[{'name':'商品-搜索'}]})
        self.assertFalse(c['operations'])
    def test_explicit_two_controls(self):
        c,_=normalize({'operations':[{'name':'商品-搜索','description':'首页搜索框与 Advanced Search 可见，未提交'}]})
        self.assertEqual(c['operations'],{'search.basic','search.advanced'})
    def test_search_conditions_not_product(self):
        c,_=normalize({'entities':[{'name':'高级搜索条件','attributes':[{'name':'shortDescription'}]}]})
        self.assertFalse(c['attributes'])

if __name__=='__main__': unittest.main()
