import json, hashlib, unittest
from pathlib import Path

ROOT=Path(r'D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1')
R=ROOT/'reports'/'stage_h1f4a_phase2_grouped_d_transfer_validation'

class H1F4APhase2ZeroSolverTest(unittest.TestCase):
    def test_transfer_seed_authority(self):
        d=json.load(open(R/'transfer_seed_authority_audit.json'))
        self.assertTrue(d['pass'])
        self.assertEqual(d['candidate_uid'],'K6_L1_B')
        self.assertEqual(d['candidate_hash'],d['expected_historical_hash'])
        self.assertEqual(d['required_fields_missing'],[])
        self.assertFalse(d['solver_authorized'])
        self.assertFalse(d['ml_admitted'])
    def test_direction_gate_stops_before_solver(self):
        d=json.load(open(R/'phase2_direction_zero_solver_audit.json'))
        self.assertFalse(d['formal_direction_rule_found'])
        self.assertFalse(d['phi_D_star_defined'])
        self.assertEqual(d['solver_entered_delta'],0)
        self.assertEqual(d['transfer_solver_plan']['solver_entered'],0)
        self.assertEqual(d['classification'],'GROUPED_D_PHASE2_DIRECTION_NOT_FORMALLY_IDENTIFIABLE_CHART_REVIEW')
        self.assertFalse((R/'transfer_plus_manifest.json').exists())
        self.assertFalse((R/'transfer_minus_manifest.json').exists())

if __name__ == '__main__': unittest.main()
