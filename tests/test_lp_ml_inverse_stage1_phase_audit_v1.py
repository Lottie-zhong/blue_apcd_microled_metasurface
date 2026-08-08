import csv,json,unittest
from pathlib import Path
R=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4');A=R/'outputs/lp_ml_dataset_v1/analysis'
class PhaseAuditTest(unittest.TestCase):
 def test_circular_error_and_root_cause(self):
  rows=list(csv.DictReader((A/'lp_ml_inverse_stage1_35_phase_recomputation_v1.csv').open(encoding='utf-8-sig')));self.assertEqual(len(rows),35);self.assertTrue(all(0<=float(r['circular_phase_error_deg_provisional'])<=180 for r in rows));self.assertEqual(json.loads((A/'lp_ml_inverse_stage1_phase_audit_decision_v1.json').read_text())['previous_gt180_root_cause'],'POSTPROCESS_UNWRAPPED_PHASE_BUG_IN_RANGE_REPORT')
 def test_reference_and_hard_gate(self):
  r=json.loads((A/'lp_ml_inverse_stage1_p_apcd_reference_audit_v1.json').read_text());self.assertTrue(r['source_hash_match']);self.assertFalse(r['numeric_projector_present']);d=json.loads((A/'lp_ml_inverse_stage1_phase_audit_decision_v1.json').read_text());self.assertEqual(d['outcome'],'LP_ML_INVERSE_STAGE1_PHASE_AUDIT_HARD_GATE');self.assertEqual(d['solver_calls'],0)
 def test_coverage_and_tuple(self):
  c=json.loads((A/'lp_ml_inverse_stage1_377_phase_coverage_v1.json').read_text());self.assertEqual(c['rows_450nm'],377);t=json.loads((A/'lp_ml_inverse_stage1_phase_audit_corrected_tuple_closure_v1.json').read_text());self.assertEqual(t['raw_tuple_combinations'],38880);self.assertEqual(t['status'],'SUPERSEDED_BY_PHASE_CONVENTION_AUDIT')
if __name__=='__main__':unittest.main()
