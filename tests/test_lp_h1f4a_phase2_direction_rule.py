import json, unittest
from pathlib import Path

ROOT=Path(r'D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1')
R=ROOT/'reports'/'stage_h1f4a_phase2_grouped_d_transfer_validation'

class H1F4ADirectionRuleTest(unittest.TestCase):
    def test_rule_is_frozen_from_phase1_only(self):
        d=json.load(open(R/'H1F4A_PHASE2_DIRECTION_RULE_V1.json'))
        self.assertEqual(d['rule_authority'],'CHART_PROSPECTIVE_POST_PHASE1_PRE_TRANSFER')
        self.assertFalse(d['transfer_data_seen'])
        self.assertEqual(d['transfer_solver_entered_before_rule'],0)
        self.assertEqual(len(d['g_a_per_nm']),9); self.assertEqual(len(d['g_b_per_nm']),9)
        self.assertAlmostEqual(d['norm_g_per_nm'],0.0007344670142591269,15)
        self.assertAlmostEqual(d['phi_D_star_deg'],-89.22790442006784,12)
        self.assertEqual(d['g_phi_diagnostic']['positive_count'],6)
        self.assertEqual(d['g_phi_diagnostic']['negative_count'],3)
        self.assertFalse(d['g_phi_diagnostic']['sign_consistency'])
    def test_transfer_preregistration_and_legality(self):
        m=json.load(open(R/'transfer_candidate_manifest.json'))
        self.assertEqual(m['transfer_parent_uid'],'K6_L1_B')
        self.assertEqual(m['transfer_parent_hash'],'ea25ff16c44e2dd00eb9fc6805b6f174a635668f65edad2666f641faf9880a78')
        self.assertEqual(m['candidate_count'],2); self.assertEqual(m['max_new_formal_cases'],4)
        self.assertTrue(all(c['geometry_legality']['pass'] for c in m['children']))
        self.assertEqual({c['harmonic_coefficients']['a_D_nm'] for c in m['children']},{0.053900808678556546,-0.053900808678556546})
        self.assertEqual({c['harmonic_coefficients']['b_D_nm'] for c in m['children']},{-3.999636821365635,3.999636821365635})
        self.assertEqual(json.load(open(R/'h1f4a_phase2_solver_accounting.json'))['solver_entered_delta'],0)

if __name__=='__main__': unittest.main()
