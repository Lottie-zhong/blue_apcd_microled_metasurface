import csv,json,math
from pathlib import Path
ROOT=Path(r"D:/project/worktrees/blue_apcd_np_k6_mdc_v1"); EV=ROOT/'outputs/np_k6_p0_decay_tail_projection_v1'
def j(n): return json.loads((EV/n).read_text(encoding='utf-8-sig'))
def test_decay_history_provenance_and_zero_budget():
 s=j('solver_zero_audit.json'); p=j('decay_projection_summary.json'); rows=list(csv.DictReader((EV/'decay_history.csv').open(encoding='utf-8')))
 assert len(rows)>=30 and s['authorized_solver_budget_this_turn']==0 and not s['solver_run_called_this_turn'] and not s['fsp_save_called_this_turn']
 assert s['post_fsp_sha256']=='c14fd3a2464e11c3ba667e4b513bd76a1828c918f80df54511fec7862e2705ca' and s['post_fsp_unchanged']
 assert p['classification']=='DECAY_TAIL_PROJECTION_INCONCLUSIVE'
def test_fit_windows_and_threshold_gate():
 f=j('decay_tail_fit_windows.json'); n=j('next_simulation_time_recommendation.json')
 assert len(f['windows'])==3 and all(w['sample_count']>=10 for w in f['windows'])
 assert f['reliable_window_count']==0 and all(not w['reliable'] for w in f['windows'])
 assert n['recommended_max_simulation_time_ps'] is None and n['solver_run_performed'] is False
def test_no_label_promotion_and_remaining_untouched():
 x=j('no_label_promotion_audit.json'); assert x['formal_hf_labels']==0 and x['training_labels']==0 and x['candidate_labels']==0 and x['remaining_five_cases_untouched']
