import csv,hashlib,json,math
from pathlib import Path
ROOT=Path(r"D:/project/worktrees/blue_apcd_np_k6_mdc_v1")
EV=ROOT/'outputs/np_k6_p0_decay_tail_projection_v1'
EXPECTED_POST='c14fd3a2464e11c3ba667e4b513bd76a1828c918f80df54511fec7862e2705ca'
def j(n): return json.loads((EV/n).read_text(encoding='utf-8-sig'))
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''): h.update(c)
 return h.hexdigest()
def main():
 e=[]; s=j('solver_zero_audit.json'); p=j('decay_projection_summary.json'); f=j('decay_tail_fit_windows.json'); n=j('next_simulation_time_recommendation.json'); prov=j('provenance_audit.json'); rows=list(csv.DictReader((EV/'decay_history.csv').open(encoding='utf-8')))
 if len(rows)<30 or any(not math.isfinite(float(r['time_s'])) or not math.isfinite(float(r['auto_shutoff_value'])) for r in rows): e.append('history')
 if any(float(rows[i+1]['time_s'])<=float(rows[i]['time_s']) for i in range(len(rows)-1)): e.append('time_not_strictly_increasing')
 if p.get('classification')!='DECAY_TAIL_PROJECTION_INCONCLUSIVE' or n.get('classification')!=p.get('classification'): e.append('classification')
 if s.get('solver_run_called_this_turn') or s.get('fsp_save_called_this_turn') or s.get('authorized_solver_budget_this_turn')!=0 or s.get('new_attempt'): e.append('solver_zero')
 if s.get('existing_entered')!=1 or not s.get('post_fsp_unchanged') or s.get('post_fsp_sha256')!=EXPECTED_POST: e.append('immutability')
 if len(f.get('windows',[]))!=3 or any(w.get('sample_count',0)<10 for w in f['windows']): e.append('fit_windows')
 if any(w.get('reliable') for w in f['windows']) or f.get('reliable_window_count')!=0: e.append('fit_reliability')
 if n.get('recommended_max_simulation_time_ps') is not None or n.get('solver_run_performed') is not False: e.append('recommendation')
 if prov.get('post_fsp_sha256')!=EXPECTED_POST or prov.get('solver_run_performed') is not False: e.append('provenance')
 if not (j('no_label_promotion_audit.json').get('formal_hf_labels')==0 and j('no_label_promotion_audit.json').get('training_labels')==0 and j('no_label_promotion_audit.json').get('candidate_labels')==0 and j('no_label_promotion_audit.json').get('remaining_five_cases_untouched')): e.append('labels')
 out={'validator':'np_k6_p0_decay_tail_projection_v1','errors':e,'pass':not e,'classification':p.get('classification'),'sample_count':len(rows),'post_fsp_sha256':s.get('post_fsp_sha256'),'solver_run_performed':False,'reliable_window_count':f.get('reliable_window_count'),'recommended_max_simulation_time_ps':n.get('recommended_max_simulation_time_ps'),'formal_hf_labels':0,'training_labels':0,'candidate_labels':0,'remaining_five_untouched':True}
 (EV/'standalone_validator_report.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8'); print(json.dumps(out,indent=2,sort_keys=True)); raise SystemExit(0 if not e else 1)
if __name__=='__main__': main()
