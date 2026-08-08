import csv,json,unittest
from pathlib import Path
R=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4');O=R/'outputs/lp_ml_dataset_v1';A=O/'analysis';P=O/'plans';S=O/'staging/lp_ml_inverse_stage1_fdt_validation_v1'
class Stage1ClosureTest(unittest.TestCase):
 def test_counts_and_tuple_gate(self):
  with (P/'lp_ml_inverse_stage1_36_candidate_manifest_v1.csv').open(encoding='utf-8-sig') as f:m=list(csv.DictReader(f))
  self.assertEqual(len(m),36);self.assertEqual([sum(int(r['target_bin'])==b for r in m) for b in range(6)],[6]*6);self.assertEqual(sum(r['calibrated_risk_class']=='CALIBRATED_HIGH_RISK' for r in m),0)
  q=json.loads((A/'lp_ml_inverse_stage1_physics_closure_decision_v1.json').read_text());self.assertEqual(q['complete_counts']['B2'],5);self.assertEqual(q['raw_tuple_combinations'],38880);self.assertEqual(q['solver_calls'],0);self.assertEqual(q['outcome'],'LP_ML_INVERSE_STAGE1_FIVED_SPACE_INSUFFICIENT_EVIDENCE')
 def test_raw_physics_and_quarantine(self):
  with (A/'lp_ml_inverse_stage1_35_physics_immutable_manifest_v1.csv').open(encoding='utf-8-sig') as f:r=list(csv.DictReader(f))
  self.assertEqual(len(r),35);self.assertTrue(all(x['physics_origin']=='PROSPECTIVE_SINGLE_DIMER_FDTD_PHYSICS' for x in r));self.assertFalse(any('054' in x['candidate_id'] for x in r));self.assertEqual(json.loads((S/'final_sentinel_v1.json').read_text())['entered'],72)
 def test_no_execution_proposal(self):
  p=json.loads((A/'lp_ml_inverse_stage1_broadband_confirmation_proposal_v1.json').read_text());self.assertTrue(p['no_execution_in_this_task']);self.assertEqual(p['candidate_count'],0)
if __name__=='__main__':unittest.main()
