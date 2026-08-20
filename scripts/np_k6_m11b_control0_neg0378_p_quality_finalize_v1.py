from __future__ import annotations
import json, hashlib, csv
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1')
E=ROOT/'outputs/np_k6_m11b_control0_neg0378_p_matched_hf_v1'
RUN=E/'runtime_runs/CONTROL0_NEG0378_P/attempt_001'
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def atomic(p,o):
 p.parent.mkdir(parents=True,exist_ok=True)
 t=p.with_name(p.name+'.tmp')
 t.write_text(json.dumps(o,indent=2,sort_keys=True,ensure_ascii=False,default=str)+'\n',encoding='utf-8')
 t.replace(p)
q=load(RUN/'quality_gate.json')
led=load(RUN/'attempt_ledger.json')
ext=load(E/'extraction_manifest.json')
post=RUN/'CONTROL0_NEG0378_P_attempt_001_post.fsp'
postsha=sha(post)
rows=list(csv.DictReader((RUN/'spectral_metrics.csv').open(encoding='utf-8-sig',newline='')))
wl=[int(round(float(r['wavelength_nm']))) for r in rows]
maxres=max(abs(float(r['residual'])) for r in rows)
summary=load(E/'geometry_dependent_provider_error_audit.json')
decision=load(E/'decision_audit.json')
ts=datetime.now(timezone.utc).isoformat()
atomic(E/'independent_reload_audit.json',{'case_id':'CONTROL0_NEG0378_P','attempt_id':'attempt_001','post_fsp_path':str(post),'post_fsp_sha256':postsha,'independent_reload':bool(ext.get('independent_reload')),'run_called_during_extraction':bool(ext.get('run_called_during_extraction')),'exact_wavelengths':wl,'result_datasets_queryable':True,'source':'existing independent read-only extraction manifest; no solver/save during audit'})
atomic(E/'formal_quality_audit.json',{'case_id':'CONTROL0_NEG0378_P','geometry_hash':'5744baf84e4b4405711f0aabdbb7965c294d4b3e4f099f670457fbbbae1c2710','u_x_exact':-0.3786893999886029,'polarization':'P_XLIKE','post_fsp_sha256':postsha,'exact_11_points':wl==list(range(445,456)),'finite_11_points':q.get('finite_11_points'),'duplicate_wavelengths':not q.get('no_duplicate_wavelengths'),'max_abs_closure_residual':maxres,'closure_threshold':0.01,'closure_gate_pass':q.get('closure_gate_pass'),'max_order_sum_T_mismatch':q.get('max_order_sum_T_mismatch'),'order_mismatch_threshold':1e-8,'order_gate_pass':q.get('order_sum_gate_pass'),'max_normalization_mismatch':q.get('max_normalization_mismatch'),'normalization_threshold':1e-8,'normalization_gate_pass':q.get('normalization_gate_pass'),'structure_anomaly':'NOT_OBSERVABLE_FROM_SAVED_STATE','formal_accept':False,'quality_gate_pass':False,'failure_reason':'max |1-T-R| exceeds 0.01 at 453 nm'})
atomic(E/'terminal_failure.json',{'schema':'NP_K6_M11B_CONTROL0_NEG0378_P_POSTFSP_QUALITY_AND_DECISION_AUDIT_V1','task_id':'NP_K6_M11B_CONTROL0_NEG0378_P_MATCHED_HF_DECISION_BOUND_V1','case_id':'CONTROL0_NEG0378_P','attempt_id':'attempt_001','terminal_timestamp_utc':ts,'state':'QUALITY_GATE_FAIL','quality_gate_pass':False,'formal_accept':False,'failure_reasons':['closure_gate_fail','max_abs_closure_residual=0.012351796077454041>0.01'],'post_fsp_path':str(post),'post_fsp_sha256':postsha,'entered':led.get('entered'),'run_invocation_count':led.get('run_invocation_count'),'engine_completed':led.get('engine_completed'),'post_saved':led.get('post_saved'),'controller_returned':led.get('controller_returned'),'replay':False,'attempt_002':False,'control0_s_started':False,'solver_calls_in_audit':0,'rcwa_calls_in_audit':0,'next_action':'Return to Chart; do not rerun CONTROL0 or start CONTROL0 S automatically.'})
atomic(E/'terminal_state.json',{'task_id':'NP_K6_M11B_CONTROL0_NEG0378_P_MATCHED_HF_DECISION_BOUND_V1','case_id':'CONTROL0_NEG0378_P','attempt_id':'attempt_001','state':'TERMINAL_QUALITY_GATE_FAIL','terminal_artifact':'terminal_failure.json','monitor_state':'RESULT_READY','slot_released':True,'post_fsp_sha256':postsha})
atomic(E/'matched_decision_summary.json',{'p_side_two_sided_decision_stability':load(E/'p_side_two_sided_decision_stability.json'),'geometry_dependence':summary,'control0_s_recommendation':load(E/'control0_s_recommendation.json'),'decision_audit':decision,'full_p_s_two_sided':'NOT_PROVEN','alt1_h1_handoff':'NP_ALT1_ANGULAR_COMPONENT_PROVIDER_HANDOFF_READY'})
md=ROOT/'docs/np_k6_m11b_control0_neg0378_p_postfsp_quality_and_decision_audit_v1.md'
md.parent.mkdir(parents=True,exist_ok=True)
text=f'''# NP K6 M11B CONTROL0 P post-FSP quality and decision audit v1

Status: TERMINAL_QUALITY_GATE_FAIL / formal_accept=false.

## Frozen identity

- case: CONTROL0_NEG0378_P, attempt attempt_001
- ordered diameters: [125, 135, 150, 175, 190, 210] nm
- polarization: P_XLIKE
- exact u_x: -0.3786893999886029
- canonical geometry hash: 5744baf84e4b4405711f0aabdbb7965c294d4b3e4f099f670457fbbbae1c2710
- pre-FSP SHA256: d980fbded5cb59f7ff2d7712897d5d9d3c34dc705358db2b217f0de8f298a10f
- post-FSP SHA256: {postsha}

## Formal quality

- independent read-only extraction: {bool(ext.get('independent_reload'))}
- exact wavelengths: {wl}
- closure max |1-T-R|: {maxres:.15g}; threshold 0.01; FAIL
- order-sum/T max mismatch: {q.get('max_order_sum_T_mismatch')}; threshold 1e-8; PASS
- normalization max mismatch: {q.get('max_normalization_mismatch')}; threshold 1e-8; PASS
- structure anomaly: NOT_OBSERVABLE_FROM_SAVED_STATE
- no NaN/Inf or duplicate wavelength rows

The 453 nm row is the closure worst case. No renormalization or clipping was applied.

## Matched RCWA audit

The pinned CONTROL0 RCWA provider was read from the existing coupling terminal package; no RCWA was run. Existing ALT1 matched RCWA/FDTD rows were read from the frozen M11 table. Residuals and candidate separations are in CONTROL0_NEG0378_P_RCWA_VS_FDTD_AUDIT_V1.json, control0_rcwa_vs_fdtd_residual_long.csv, and matched_control0_alt1_22row_table.csv.

- provider-error classification: {summary.get('classification')}
- P-side decision stability: {decision.get('p_side_two_sided_decision_stability')}
- candidate ordering: {decision.get('classification')}
- CONTROL0 S recommendation: {load(E/'control0_s_recommendation.json').get('recommendation')}
- full P/S two-sided decision: NOT_PROVEN (CONTROL0 S was not run)
- ALT1 handoff: NP_ALT1_ANGULAR_COMPONENT_PROVIDER_HANDOFF_READY remains valid

## Governance

solver_calls_in_audit=0, rcwa_calls_in_audit=0, replay=0, attempt_002=0, CONTROL0 S=0, training/external/inverse=0. The original slot was released after the original attempt and no slot was reacquired.

Evidence directory: outputs/np_k6_m11b_control0_neg0378_p_matched_hf_v1/.
'''
md.write_text(text,encoding='utf-8')
print(json.dumps({'post_sha256':postsha,'max_closure_residual':maxres,'status':'TERMINAL_QUALITY_GATE_FAIL'},indent=2))
