import json,pathlib,tempfile,unittest
from score import Page,fullmatch,verify_ref
def node(i,role,name,parent=None,children=None,value=None,properties=None):
 n={'nodeId':str(i),'role':{'value':role},'name':{'value':name},'childIds':list(map(str,children or [])),'properties':properties or []}
 if parent is not None:n['parentId']=str(parent)
 if value is not None:n['value']={'value':value}
 return n
class Tests(unittest.TestCase):
 def page(self,nodes,url='http://test/p.html',css='catalog-product-view'):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);p=pathlib.Path(tmp.name)
  root=node(0,'RootWebArea','Page',properties=[{'name':'url','value':{'value':url}}]);(p/'accessibility.json').write_text(json.dumps({'nodes':[root]+nodes}),encoding='utf-8');(p/'page.html').write_text(f'<body class="{css}"></body>',encoding='utf-8');return Page(p/'accessibility.json')
 def fact(self,rule,regex='^ASIN$',roles=None,**kw):return dict(id='product.asin',rule=rule,clauses=[dict(name_regex=regex,roles=roles)],**kw)
 def test_name_only_no_value(self):self.assertFalse(fullmatch(self.page([node(1,'rowheader','ASIN')]),self.fact('row_value_or_option')))
 def test_row_value(self):
  p=self.page([node(1,'row','',children=[2,3]),node(2,'rowheader','ASIN',1),node(3,'cell','ABC123',1)]);refs=fullmatch(p,self.fact('row_value_or_option'));self.assertEqual(len(refs),2)
  for r in refs:verify_ref(r)
 def test_unrelated_value(self):self.assertFalse(fullmatch(self.page([node(1,'row','',children=[2]),node(2,'rowheader','ASIN',1),node(3,'cell','ABC123')]),self.fact('row_value_or_option')))
 def test_hidden_value(self):
  n=node(3,'cell','ABC123',1);n['ignored']=True
  self.assertFalse(fullmatch(self.page([node(1,'row','',children=[2,3]),node(2,'rowheader','ASIN',1),n]),self.fact('row_value_or_option')))
 def test_cart_menu_not_entity(self):self.assertFalse(fullmatch(self.page([node(1,'link','My Cart')]),self.fact('cart_page','My Cart',page_types=['cart'])))
 def test_sort_selection_requires_url(self):
  f=self.fact('sort_selection','^Sort By$');p=self.page([node(1,'combobox','Sort By',value='Price')]);self.assertFalse(fullmatch(p,f))
 def test_description_heading_not_content(self):self.assertFalse(fullmatch(self.page([node(1,'tabpanel','Details')]),self.fact('description_content','Details')))
 def test_pagination_requires_url(self):self.assertFalse(fullmatch(self.page([node(1,'heading','Items 13-24 of 99')]),self.fact('page2_result','Items')))
 def test_quote_tamper_rejected(self):
  p=self.page([node(1,'StaticText','SKU')]);r=p.ref(p.nodes[1]);r['quote']='forged'
  with self.assertRaises(ValueError):verify_ref(r)
 def test_fake_pointer_rejected(self):
  p=self.page([])
  with self.assertRaises(IndexError):verify_ref({'file':str(p.path),'pointer':'/nodes/999/name/value','quote':'ASIN'})
 def test_title_not_heading_identity(self):self.assertFalse(fullmatch(self.page([node(1,'heading','Product',properties=[{'name':'level','value':{'value':2}}])]),self.fact('heading_identity','Product')))
 def test_script_class_not_page_type(self):
  p=self.page([],css='other');(p.path.parent/'page.html').write_text('<body class="other"><script>catalog-product-view</script></body>');self.assertEqual(Page(p.path).type,'unknown')
if __name__=='__main__':unittest.main()
