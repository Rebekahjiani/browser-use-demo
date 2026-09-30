import unittest,tempfile,pathlib
from score_context_models import normalize,metric,validate_ref,score
G={'entities':[{'id':'product','name':'商品','aliases':['Product']}], 'attributes':[{'entity':'product','id':'review_count','aliases':['reviews','reviewCount']},{'entity':'product','id':'name','aliases':['名称']}], 'operations':[], 'relations':[]}
P={'facet_entities':['价格区间'],'excluded_entities':[],'excluded_operations':[]}
class Tests(unittest.TestCase):
 def test_alias_duplicate(self):
  cm={'entities':[{'name':'Product','attributes':[{'name':'reviewCount'},{'name':'reviews'},{'name':'名称'}]}]};r=score(cm,G,P,{'trace':'.'})
  self.assertEqual(r['metrics']['attributes']['tp'],2);self.assertEqual(r['metrics']['attributes']['duplicates_collapsed'],1)
 def test_missing_parent_keeps_denominator(self):
  r=score({'entities':[]},G,P,{'trace':'.'});self.assertEqual(r['metrics']['attributes']['fn'],2);self.assertEqual(r['metrics']['entities']['fn'],1)
 def test_extra_not_hallucination(self):
  r=score({'entities':[{'name':'商品','attributes':[{'name':'invented'}]}]},G,P,{'trace':'.'});self.assertEqual(r['metrics']['attributes']['unresolved'],1);self.assertEqual(r['metrics']['attributes']['fp'],0)
 def test_forged_refs(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/'x.json';p.write_text('{"x":"real"}')
   self.assertTrue(validate_ref({'file':str(p),'pointer':'/x','quote':'real'}));self.assertFalse(validate_ref({'file':str(p),'pointer':'/x','quote':'fake'}));self.assertFalse(validate_ref({'file':str(p)+'absent','pointer':'/x','quote':'real'}))
 def test_parent_ref_not_inherited(self):
  r=score({'entities':[{'name':'商品','page_refs':['.'],'attributes':[{'name':'name'}]}]},G,P,{'trace':'.'});self.assertFalse(r['assertions'][1]['evidence']['has_assertion_ref'])
 def test_facet_not_entity_hit(self):
  claims,_=normalize({'entities':[{'name':'价格区间','attributes':[{'name':'range'},{'name':'itemCount'}]}]},G,P);self.assertEqual([(x['section'],x['canonical']) for x in claims],[('attributes','category.price_range')])
 def test_structural_relation(self):
  g={**G,'relations':[{'id':'self','source':'product','target':'product','predicate':'related','predicate_aliases':['links']}]}
  c,_=normalize({'entities':[{'id':'p','name':'商品'}],'relations':[{'source':'p','target':'p','predicate':'links'}]},g,P);self.assertEqual(c[-1]['canonical'],'self')
 def test_metrics(self):
  r=metric({'a','b'},{'a','c'},1);self.assertEqual((r['tp'],r['fp'],r['fn']),(1,1,1));self.assertEqual(r['f1'],.5);self.assertEqual(r['precision_lower'],1/3)
if __name__=='__main__':unittest.main()
