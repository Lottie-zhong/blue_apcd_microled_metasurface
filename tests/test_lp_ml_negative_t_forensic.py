import json
from pathlib import Path

R=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4')
A=R/'outputs/lp_ml_dataset_v1/analysis'
S=R/'outputs/lp_ml_dataset_v1/staging/lp_ml_dataset_v1_round1_production_attempt1_v1'
def j(p): return json.loads(p.read_text(encoding='utf-8'))
def main():
    q=j(A/'lp_ml_round1_negative_t_accounting_freeze_v1.json')
    assert q['entered_subruns']==92 and q['accepted_subruns']==91 and q['failed_subruns']==1
    assert q['complete_geometries']==61 and q['untouched_candidates_count']==194
    assert q['prospective_new_subrun_budget']==389
    audit=j(A/'lp_ml_round1_61_geometry_normalization_audit_v1.json')
    assert audit['all_accepted_cases_clean'] is True and audit['negative_T_in_accepted_rows']==0
    f=j(A/'lp_ml_round1_negative_t_failed_case_forensic_v1.json')
    assert f['y_checkpoint_present'] is False and f['full_jones_recoverable_without_solver'] is False
    assert 'abs(T)' in f['forbidden_recovery']
    cls=j(A/'lp_ml_round1_negative_t_recovery_classification_v1.json')
    assert cls['classification']=='SINGLE_CASE_RUNTIME_FAILURE_PRIOR_DATA_CLEAN'
    d=j(A/'lp_ml_round1_partial_model_downgrade_ledger_v1.json')
    assert d['status']=='DIAGNOSTIC_ONLY_NOT_PROMOTABLE'
    src=(R/'scripts/lp_ml_broadband_production.py').read_text(encoding='utf-8')
    assert 'if t_value < 0.0' in src and 'NORMALIZATION_REVIEW_REQUIRED' in src
    assert 'abs(T)' not in src and not list(S.rglob('*.fsp'))
    print('negative-T forensic assertions passed')
if __name__=='__main__': main()
