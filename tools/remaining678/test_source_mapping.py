import unittest,copy
from pipeline import Q,load
from physical_alignment import physical_groups

class PhysicalSourceTests(unittest.TestCase):
 def setUp(self):
  self.expected=[r for r in load(Q/'expected_candidates.json') if r['stage']=='C']
  self.mapping=load(Q/'physical_source_map_C.json')
 def test_every_available_candidate_is_assigned_once(self):
  groups,missing=physical_groups(self.expected,self.mapping)
  rows=[r for blocks in groups.values() for block in blocks for r in block]
  self.assertEqual(len([r for r in rows if not r['excluded']]),391)
  self.assertEqual({r['id'] for r in missing},{'u000972','u000975'})
  self.assertEqual(len([r for r in rows if r['excluded']]),16)
 def test_grouped_fx_and_clean_remain_in_their_physical_sources(self):
  groups,_=physical_groups(self.expected,self.mapping)
  for n in [8,36,43,46]:
   left=[r for g in groups[f'C_file{n:02}'] for r in g if not r['excluded']]
   right=[r for g in groups[f'C_file{n+1:02}'] for r in g if r['take']=='CLEAN']
   self.assertTrue(all(r['take']=='FX_FIRST' for r in left))
   self.assertEqual([r['id'] for r in left],[r['id'] for r in right])
 def test_duplicate_source_cannot_silently_reassign_id(self):
  bad=copy.deepcopy(self.mapping);bad['files']['C_file08'][-1].pop('exclude_duplicate')
  with self.assertRaises(AssertionError):physical_groups(self.expected,bad)
 def test_missing_role_cannot_borrow_another_short_response(self):
  groups,missing=physical_groups(self.expected,self.mapping)
  self.assertEqual([r['speaker'] for r in missing],['S126','S126'])
  self.assertTrue(any(r['id']=='u000975' and r['expected_text']=='Emredersiniz.' for r in missing))
if __name__=='__main__':unittest.main()
