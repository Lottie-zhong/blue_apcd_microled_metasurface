import csv, json, unittest
from pathlib import Path

ROOT=Path(r'D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1')
R=ROOT/'reports'/'stage_h1f4b0_secondary_compensator_grammar_audit'

class H1F4B0AuditTest(unittest.TestCase):
    def test_zero_solver_route_and_governance(self):
        d=json.load(open(R/'h1f4b0_route_decision.json'))
        self.assertEqual(d['status'],'PASS_ZERO_SOLVER_AUDIT')
        self.assertEqual(d['solver_entered_delta'],0)
        self.assertFalse(d['ml_admitted'])
        self.assertEqual(d['primary_route'],'GROUPED_D_PLUS_J1_ANISOTROPY_COMPENSATOR_PROBE_READY')
        self.assertEqual(d['proposed_next_solver_probe']['maximum_cases_if_approved'],4)
        self.assertFalse(d['proposed_next_solver_probe']['solver_authorized_now'])
    def test_evidence_table_and_global_h(self):
        rows=list(csv.DictReader(open(R/'candidate_evidence_table.csv',newline='')))
        self.assertEqual(len(rows),8)
        self.assertIn('FULL_K6_CURRENT_FORMAL',{r['evidence_class'] for r in rows})
        self.assertIn('LOCAL_CURRENT_FORMAL',{r['evidence_class'] for r in rows})
        g=json.load(open(R/'h1f4b0_global_h_revisit.json'))
        self.assertEqual(g['value'],'GLOBAL_H_REVISIT_VALUE_MEDIUM')
        self.assertEqual(g['H_grid_nm'],[400.0,450.0,500.0,550.0,600.0])

if __name__=='__main__': unittest.main()
