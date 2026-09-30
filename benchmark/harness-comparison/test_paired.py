import unittest
from evaluate_original_task import locate,ROOTS,audit
class AuditTests(unittest.TestCase):
 def test_endpoint_scope(self):
  self.assertEqual(locate('E001',None,None,{'E001':{'path':'/x'}})['status'],'endpoint_exists')
  self.assertEqual(locate('E002',None,None,{'E001':{'path':'/x'}})['status'],'missing_endpoint')
 def test_literal_anchor(self):
  r=ROOTS['claudecode']
  self.assertEqual(locate('page.aria.yml:button:Add to Cart',r,'000_root',{})['status'],'literal_tree_anchor_found')
  self.assertEqual(locate('page.aria.yml:button:NOT_A_REAL_LABEL_89123',r,'000_root',{})['status'],'tree_anchor_not_literal')
 def test_not_accept_any_file_reference(self):
  self.assertEqual(locate('arbitrary-file',None,None,{})['status'],'unsupported_reference_syntax')
if __name__=='__main__':unittest.main()
