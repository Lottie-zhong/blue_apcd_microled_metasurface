import csv,json,math,hashlib
from pathlib import Path
ROOT=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
EV=ROOT/'outputs/np_k6_p0_simtime_2ps_recovery_v2'
def j(n): return json.loads((EV/n).read_text(encoding='utf-8-sig'))
def test_recovery_v2_evidence_and_budget():
 c=j('classification.json'); l=j('entered_ledger.json'); b=j('closure_audit.json'); p=j('post_fsp_checksum.json'); d=j('data_gate.json')
 rows=list(csv.DictReader((EV/'spectral_metrics_11points.csv').open(encoding='utf-8')))
 assert c['classification']=='SIMULATION_TIME_EXTENSION_CLOSURE_PASS_DECAY_CONVERGENCE_UNRESOLVED'
 assert len(rows)==11 and [int(r['wavelength_nm']) for r in rows]==list(range(445,456))
 assert all(math.isfinite(float(r['T_total'])) and math.isfinite(float(r['R_total'])) for r in rows)
 assert l['entered'] is True and l['run_invocation_count']==1 and l['attempt_002_forbidden'] is True
 assert b['max_abs_residual_2ps']>0.02 and b['order_sum_mismatch_max']<=1e-8
 assert p['sha256']=='f0119e256cf64e4875d82c0c5cca3dbc854936fc429aca4643577d7b2b1005d7'
 assert d['formal_hf_labels']==0 and d['candidate_performance_labels']==0 and d['remaining_five_cases_untouched']
