import unittest
from audit_traces import normalize_url,visible_nodes,matches
class Tests(unittest.TestCase):
 def page(self,nodes,typ='product_detail'):return dict(type=typ,nodes=nodes,ax_file='fixture.json')
 def node(self,name,role='rowheader',value=None):return dict(index=0,node_id='1',name=name,role=role,value=value,properties=[])
 def fact(self,regex,roles=None,**kw):return dict(id='test',clauses=[dict(name_regex=regex,roles=roles,**kw)])
 def test_query_preserved(self):self.assertNotEqual(normalize_url('http://x/c?p=1'),normalize_url('http://x/c?p=2'))
 def test_tracking_removed(self):self.assertEqual(normalize_url('http://x/c?price=0-10&utm_source=a#x'),'http://x/c?price=0-10')
 def test_hidden_ignored(self):self.assertEqual(visible_nodes({'nodes':[{'ignored':True,'name':{'value':'SKU'}}]}),[])
 def test_battery_field(self):
  f=self.fact(r'^Batteries[\s\u200f]*$',['rowheader']);self.assertIsNone(matches(self.page([self.node('Batteries Included?')]),f));self.assertTrue(matches(self.page([self.node('Batteries ‏')]),f))
 def test_search_sidebar_not_empty(self):self.assertIsNone(matches(self.page([self.node('You have no items to compare.','StaticText')]),self.fact(r'^Your search returned no results\.$')))
 def test_sort_value_required(self):
  f=self.fact('^Sort By$',['combobox'],value_equals='Price');self.assertIsNone(matches(self.page([self.node('Sort By','combobox','Position')]),f));self.assertEqual(len(matches(self.page([self.node('Sort By','combobox','Price')]),f)),2)
 def test_subcategory_not_price(self):self.assertIsNone(matches(self.page([self.node('$0.00 - $999.99( 22 item )','link')]),self.fact(r'^(?!\$).+\(\s*\d+\s*item\s*\)',['link'])))
 def test_page_scope(self):self.assertIsNone(matches(self.page([self.node('Qty')]),dict(self.fact('Qty'),page_types=['cart'])))
if __name__=='__main__':unittest.main()
