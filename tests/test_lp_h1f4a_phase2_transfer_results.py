import csv, json, unittest
from pathlib import Path

ROOT=Path(r'D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1')
R=ROOT/'reports'/'stage_h1f4a_phase2_grouped_d_transfer_validation'

class H1F4ATransferResultsTest(unittest.TestCase):
    def test_four_case_accounting_and_concurrency(self):
        a=json.load(open(R/'h1f4a_phase2_solver_accounting.json'))
        l=json.load(open(R/'h1f4a_phase2_solver_ledger.json'))
        c=json.load(open(R/'h1f4a_phase2_concurrency_observation.json'))
        self.assertEqual((a['planned_formal_cases'],a['entered_formal_cases'],a['accepted_formal_cases'],a['replay_cases']),(4,4,4,0))
        self.assertEqual((l['solver_entered_count'],l['solver_accepted_count']), (4,4))
        self.assertEqual(c['peak_simultaneous_real_fdtd_jobs'],3)
        self.assertEqual(c['permanent_validated_production_fdtd_concurrency'],2)
    def test_fullwave_and_verdict(self):
        rows=list(csv.DictReader(open(R/'h1f4a_phase2_order_resolved_fullwave.csv',newline='')))
        self.assertEqual(len(rows),396)
        self.assertEqual(len([x for x in rows if x['order_m']=='0' and x['order_n']=='1']),36)
        d=json.load(open(R/'h1f4a_phase2_transfer_analysis.json'))
        self.assertEqual(d['classification'],'GROUPED_D_PHASE2_TRANSFER_PARTIAL')
        self.assertTrue(d['directional_comparison']['sign_match'])
        self.assertFalse(d['spectral_diagnostic']['eta_x_plus1_sign_consistency'])
        self.assertFalse(d['ml_admitted'])

if __name__=='__main__': unittest.main()
