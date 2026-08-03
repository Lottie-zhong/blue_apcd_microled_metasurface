import json
from pathlib import Path
R=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4');A=R/'outputs/lp_ml_dataset_v1/analysis';S=R/'outputs/lp_ml_dataset_v1/staging/lp_ml_dataset_v1_round1_recovery_attempt1_v1';P=R/'outputs/lp_ml_dataset_v1/plans'
def j(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    m=j(P/'lp_ml_dataset_v1_round1_recovery_389_plan_v1.json'); assert m['candidate_count']==195 and m['new_entered_ceiling']==389
    with (P/'lp_ml_dataset_v1_round1_recovery_389_plan_v1.csv').open(encoding='utf-8') as f: assert sum(1 for _ in f)==196
    assert m['first_candidate']=='LPML_R1_GLOBAL_SOBOL_054' and m['first_run_polarizations']=='y'
    a=j(S/'entered_accounting_v1.json'); assert a['count']==1 and a['ceiling']==389
    q=j(A/'lp_ml_round1_recovery_attempt1_forensic_v1.json'); assert q['solver_entered']==1 and q['accepted_subruns']==0 and q['untouched_194_started'] is False
    assert q['negative_T_value']<0 and q['checkpoint_present'] is False
    assert not (S/'candidate_wavelength_jones_v1.csv').read_text(encoding='utf-8').strip() or len((S/'candidate_wavelength_jones_v1.csv').read_text(encoding='utf-8').splitlines())==1
    assert not list(S.rglob('*.fsp'))
    print('recovery hard-gate assertions passed')
if __name__=='__main__':main()
