import csv, hashlib, json
from pathlib import Path
ROOT=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
OUT=ROOT/'outputs/np_k6_m7a_primary4_targeted_hf_acquisition_closeout_v1'
def test_manifest_and_rows():
 m=json.loads((OUT/'m7a_dataset_manifest.json').read_text(encoding='utf-8-sig'))
 assert m['status']=='NP_K6_M7A_PRIMARY4_TARGETED_HF_ACQUISITION_COMPLETE_20G_M8_RETRAIN_READY'
 assert (m['new_hf_rows'],m['existing_hf_rows'],m['merged_hf_rows'])==(88,352,440)
 for fn,n in [('m7a_hf_observations_88rows.csv',88),('m7a_formal_development_hf_observations_440rows.csv',440),('m7a_lf_baseline_88rows.csv',88),('m7a_formal_development_lf_baseline_440rows.csv',440)]:
  with (OUT/fn).open(encoding='utf-8-sig',newline='') as f: assert len(list(csv.DictReader(f)))==n
def test_quality_and_budget():
 q=json.loads((OUT/'m7a_case_quality_audit.json').read_text(encoding='utf-8-sig')); assert q['all_quality_gate_pass'] and q['case_count']==8
 assert all(x['checks']['post_hash_matches_record'] and x['checks']['readonly_reload'] and x['checks']['resource_readback_4x1'] for x in q['cases'])
 b=json.loads((OUT/'m7a_solver_budget_audit.json').read_text(encoding='utf-8-sig')); assert b['m7a_entered_solver']==8 and b['m7a_run_invocations']==8 and b['attempt_002_count']==0 and b['external_hf_calls']==0 and b['sealed_target_reads']==0 and not b['m8_started']
def test_validator_and_trial():
 v=json.loads((OUT/'m7a_final_validator_report.json').read_text(encoding='utf-8-sig')); assert v['status']=='PASS' and v['error_count']==0
 t=json.loads((OUT/'m7a_concurrency3_trial_observation.json').read_text(encoding='utf-8-sig')); assert t['global_cap']==3 and t['max_observed_active_fdtd']<=3 and t['fourth_fdtd_authorized'] is False and 'all 8' in t['quality_gate_impact']
