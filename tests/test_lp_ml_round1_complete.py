import csv,json
from pathlib import Path
R=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4');O=R/'outputs/lp_ml_dataset_v1';A=O/'analysis';S=O/'staging/lp_ml_dataset_v1_round1_continuation_attempt1_v1'
def test_054_permanent_quarantine_and_continuation_budget():
    d=json.loads((S/'final_sentinel_v1.json').read_text()); a=json.loads((S/'entered_accounting_v1.json').read_text()); assert d['entered']==388; assert d['accepted']==388; assert d['quarantined_count']==0; assert a['count']==388
    rows=list(csv.DictReader((S/'candidate_wavelength_jones_v1.csv').open(encoding='utf-8-sig'))); assert all(r['candidate_id']!='LPML_R1_GLOBAL_SOBOL_054' for r in rows)
def test_complete_255_2295_and_grid():
    rows=list(csv.DictReader((O/'lp_ml_dataset_v1_round1_complete_255_geometry_2295_rows.csv').open(encoding='utf-8-sig'))); assert len(rows)==2295; ids={r['candidate_id'] for r in rows}; assert len(ids)==255; assert 'LPML_R1_GLOBAL_SOBOL_054' not in ids
    assert all(len([x for x in rows if x['candidate_id']==c])==9 for c in ids); assert all(float(r['wavelength_nm']) in {450+i*.5 for i in range(9)} for r in rows); assert all(r['Jones_complete'].lower()=='true' for r in rows)
def test_from_scratch_models_and_contracts():
    m=json.loads((A/'lp_ml_round1_full_residual_mlp_5seed_v1.json').read_text()); assert m['from_scratch'] and not m['warm_start']; assert len(m['seeds'])==5; assert m['cuda_available']; assert 'Huber' in m['loss']
    q=json.loads((A/'lp_ml_dataset_v1_round1_complete_255_quality_audit_v1.json').read_text()); assert q['model_filled_rows']==0 and q['solver_authorized'] is False and q['no_active_learning'] and q['no_d9']
    assert q['symmetry_group_single_split'] and q['wavelength_leakage'] is False
    s=json.loads((A/'lp_ml_round1_strata_metrics_v1.json').read_text()); assert 'GLOBAL_SOBOL' in s['test_metrics_by_slice'] and 'WAVELENGTH_450' in s['test_metrics_by_slice']
