import json, csv, hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1]
E=R/'outputs/np_k6_hf_pilot_gate0a_run3c_x_n2_v1'
case='RUN3C_N2_NATIVE_M1_X_PRODUCTION_GATE0A'
state=json.loads((E/'gate0a_state_update.json').read_text()); led=json.loads((E/'attempt_ledger.json').read_text()); num=json.loads((E/'n2_numerical_gate_audit.json').read_text()); nest=json.loads((E/'strict_actual_nesting_audit.json').read_text()); post=json.loads((E/'n2_post_reload_audit.json').read_text());
assert state['state']=='NP_K6_HF_PILOT_GATE0A_BLOCKED_BY_NUMERICAL_FIDELITY'
assert led['case_id']==case and led['entered'] and led['run_invocation_count']==1 and led['engine_completed'] and led['controller_returned'] and led['post_saved']
assert post['sha_stable'] and post['readonly_reload'] and post['native_m1_sampled_101_point'] and all(post['required_diagnostic_objects'].values())
assert num['wavelength_count']==11 and num['closure_pass'] is False and num['order_sum_pass'] and num['normalization_pass']
assert nest['strict_actual_nesting'] is False and state['strict_nesting_classification']=='HARD_GATE_RUN3C_N2_NOT_STRICTLY_NESTED'
assert state['production_mesh_frozen'] is False and state['training_label'] is False and state['candidate_performance_label'] is False and state['diagnostic_only'] is True
assert not (E/'runtime_runs'/case/'attempt_002').exists()
print('PASS_NP_K6_HF_PILOT_GATE0A_FINAL_VALIDATOR')
