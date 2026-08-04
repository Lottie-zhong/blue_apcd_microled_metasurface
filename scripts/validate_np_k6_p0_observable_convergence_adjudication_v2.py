import json, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'outputs/np_k6_p0_observable_convergence_adjudication_v1_correction_v2'
def read(n): return json.loads((EV/n).read_text(encoding='utf-8-sig'))
def validate():
 errors=[]
 required=['stopped_10ps_attempt_audit_v2.json','scope_correction_audit.json','convergence_revalidation_summary.json','convergence_gate_results_v2.json','convergence_trend_1ps_2ps_3ps_v2.json','post_sha_identity_v2.json','solver_budget_audit_v2.json','provenance_audit_v2.json','state_v2.json']
 for n in required:
  if not (EV/n).exists(): errors.append('missing '+n)
 if errors:return errors
 stop=read('stopped_10ps_attempt_audit_v2.json'); scope=read('scope_correction_audit.json'); summary=read('convergence_revalidation_summary.json'); sha=read('post_sha_identity_v2.json'); budget=read('solver_budget_audit_v2.json'); state=read('state_v2.json')
 if state.get('state')!='NP_K6_P0_OBSERVABLE_CONVERGENCE_ACCEPTED_3PS_GENERATOR_READY': errors.append('state')
 if not (stop.get('entered') is True and stop.get('run_invocation_count')==1 and stop.get('post_saved') is False and stop.get('targeted_termination_confirmed') is True and stop.get('user_aborted') is True and stop.get('numerical_conclusion')=='none'): errors.append('10ps stop contract')
 if scope.get('formal_remaining_five_entered') is not False or scope.get('formal_remaining_five_run_invocation_count')!=0: errors.append('remaining five not zero')
 if scope.get('accidental_v2_case_aborted') is not True or scope.get('accidental_v2_case_valid_post') is not False: errors.append('accidental case correction')
 if summary.get('all_11_points') is not True or summary.get('post_sha_unchanged') is not True: errors.append('readonly summary')
 gates=summary.get('gate_results',{}); base=gates.get('base_3ps_gates',{}); obs=gates.get('observable_2ps_to_3ps_gates',{})
 if gates.get('all_gates_pass') is not True: errors.append('gate decision')
 for k in ['three_ps_full_band_closure_pass','three_ps_structure_448_pass','three_ps_order_sum_pass','three_ps_normalization_pass']:
  if base.get(k) is not True: errors.append(k)
 if any(v.get('pass') is not True for v in obs.values() if isinstance(v,dict)): errors.append('observable gates')
 if not all(x.get('sha_match') is True for x in sha.get('rows',[])): errors.append('post SHA')
 if budget.get('solver_calls_this_adjudication_round')!=0 or budget.get('remaining_five_started_this_round') is not False: errors.append('solver budget')
 if state.get('formal_hf_labels')!=0 or state.get('remaining_five_entered') is not False: errors.append('label scope')
 return errors
if __name__=='__main__':
 e=validate(); print(json.dumps({'status':'PASS_NP_K6_P0_ADJUDICATION_V2' if not e else 'FAIL_NP_K6_P0_ADJUDICATION_V2','errors':e},indent=2)); raise SystemExit(0 if not e else 1)
