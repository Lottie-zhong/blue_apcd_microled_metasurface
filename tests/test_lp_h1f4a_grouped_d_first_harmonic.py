import csv, json, hashlib, unittest
from pathlib import Path

ROOT = Path(r'D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1')
R = ROOT/'reports'/'stage_h1f4a_grouped_d_first_harmonic_jacobian_probe'

class H1F4ATest(unittest.TestCase):
    def test_phase1_artifacts_and_accounting(self):
        s=json.load(open(R/'h1f4a_jacobian_summary.json'))
        a=json.load(open(R/'h1f4a_solver_accounting.json'))
        c=json.load(open(R/'CONCURRENCY_3_OBSERVATION.json'))
        self.assertEqual(s['primary_seed_hash'],'a8606d8f44a4675db08493c3dd95c8ea43f30882d3a9bbb18a65b59c2ba45198')
        self.assertEqual((a['planned_formal_cases'],a['entered_formal_cases'],a['accepted_formal_cases'],a['replay_cases']),(8,8,8,0))
        self.assertEqual(c['peak_simultaneous_real_fdtd_jobs'],3)
        self.assertEqual(c['permanent_validated_production_fdtd_concurrency'],2)
        self.assertFalse(s['phase2_authorized']); self.assertFalse(s['ml_admitted'])
        self.assertTrue(json.load(open(R/'geometry_legality.json'))['all_pass'])
    def test_broadband_and_jacobian_shapes(self):
        rows=list(csv.DictReader(open(R/'h1f4a_order_resolved_fullwave.csv',newline='')))
        self.assertEqual(len(rows),792)
        target=[x for x in rows if x['order_m']=='0' and x['order_n']=='1']
        self.assertEqual(len(target),72)
        jac=list(csv.DictReader(open(R/'h1f4a_central_difference_jacobian.csv',newline='')))
        self.assertEqual(len(jac),36)
        self.assertEqual({x['axis'] for x in jac},{'A','B'})
        self.assertEqual({x['polarization'] for x in jac},{'x','y'})

if __name__ == '__main__': unittest.main()
