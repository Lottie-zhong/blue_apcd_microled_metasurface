from __future__ import annotations
import csv, hashlib, json, math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'outputs/np_k6_m11b_control0_neg0378_p_matched_hf_v1'
RUN=E/'runtime_runs/CONTROL0_NEG0378_P/attempt_001'
EXPECTED_POST='bd71b568c1a9632a27e92d956ebcdd708c7739e35756c8202cccdcf7badb91cb'
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def main():
 post=RUN/'CONTROL0_NEG0378_P_attempt_001_post.fsp'
 assert post.exists()
 assert sha(post)==EXPECTED_POST
 q=load(RUN/'quality_gate.json')
 led=load(RUN/'attempt_ledger.json')
 ext=load(E/'independent_reload_audit.json')
 term=load(E/'terminal_failure.json')
 budget=load(E/'solver_budget_audit.json')
 rows=list(csv.DictReader((RUN/'spectral_metrics.csv').open(encoding='utf-8-sig',newline='')))
 w=[int(round(float(r['wavelength_nm']))) for r in rows]
 assert w==list(range(445,456)) and len(rows)==11
 for r in rows:
  for k,v in r.items():
   if k not in ('case_id','polarization','plus1_air_side_angle_deg') and v not in ('',None):
    assert math.isfinite(float(v))
 assert led['entered'] is True and led['run_invocation_count']==1
 assert led['engine_completed'] and led['post_saved'] and led['controller_returned']
 assert ext['independent_reload'] is True and ext['run_called_during_extraction'] is False
 assert q['closure_gate_pass'] is False and q['max_closure_residual']>0.01
 assert q['order_sum_gate_pass'] is True and q['max_order_sum_T_mismatch']<=1e-8
 assert q['normalization_gate_pass'] is True and q['max_normalization_mismatch']<=1e-8
 assert term['formal_accept'] is False and term['attempt_002'] is False and term['control0_s_started'] is False
 assert budget['new_rcwa_calls']==0 and budget['control0_s_entered']==0 and budget['attempt_002']==0
 mt=list(csv.DictReader((E/'matched_control0_alt1_22row_table.csv').open(encoding='utf-8-sig',newline='')))
 assert len(mt)==11
 assert load(E/'control0_s_recommendation.json')['auto_run'] is False
 print('M11B_CONTROL0_POSTFSP_QUALITY_AUDIT_VALIDATION_PASS')
if __name__=='__main__': main()
