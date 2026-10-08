import unittest,tempfile,pathlib
from score_citations_v3 import supported_ref,parse_tree
class Tests(unittest.TestCase):
 def setUp(self):
  self.marker={'line':2,'role':'rowheader','name':'ASIN','parents':[1]};self.nodes=[{'line':1,'role':'table','name':'','parents':[]},self.marker]
 def test_fake_endpoint_no_score(self):self.assertEqual(supported_ref('E999999',[self.marker],self.nodes,{})['status'],'incorrect_reference')
 def test_exists_is_not_support(self):self.assertEqual(supported_ref('E001',[self.marker],self.nodes,{'E001':{}})['status'],'unresolved')
 def test_container_reference(self):self.assertEqual(supported_ref('page.aria.yml:table:ASIN',[self.marker],self.nodes,{})['status'],'supported')
 def test_wrong_field_reference(self):self.assertEqual(supported_ref('page.aria.yml:table:SKU',[self.marker],self.nodes,{})['status'],'unresolved')
 def test_no_markers(self):self.assertEqual(supported_ref('page.aria.yml:table:ASIN',[],self.nodes,{})['status'],'unresolved')
 def test_quoted_text_after_metadata(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'x.yml';p.write_text('- generic [ref=e101]: "Rating:"\n- generic "63%" [ref=e102]:\n',encoding='utf-8')
   nodes=parse_tree(p);self.assertEqual([n['name'] for n in nodes],['Rating:','63%'])
if __name__=='__main__':unittest.main()
