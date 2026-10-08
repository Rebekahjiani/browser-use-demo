import unittest
from score_two_layers import project
class Tests(unittest.TestCase):
 def test_description_collapses(self):
  m=[{'fact_id':x,'physical_key':'product.description'} for x in ['asin','upc','dimensions']]
  self.assertEqual(project({'asin','upc','dimensions'},m),{'product.description'})
 def test_unknown_does_not_score(self):self.assertEqual(project({'x'},[{'fact_id':'x','physical_key':None}]),set())
 def test_unsupported_does_not_score(self):self.assertEqual(project(set(),[{'fact_id':'x','physical_key':'product.name'}]),set())
 def test_layers_not_added(self):self.assertEqual(len(project({'a','b'},[{'fact_id':'a','physical_key':'product.name'},{'fact_id':'b','physical_key':'product.price'}])),2)
if __name__=='__main__':unittest.main()
