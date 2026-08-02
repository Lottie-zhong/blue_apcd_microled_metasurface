import csv, json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
E=R/'outputs/np_k6_hf_pilot_gate0_n2_production_mesh_v1_corrected_monitor_contract_v1'
C=E/'cases/RUN3C_N2_NATIVE_M1_X_PRODUCTION_GATE'
s=json.loads((C/'extraction_manifest.json').read_text())
assert s['case_id']=='RUN3C_N2_NATIVE_M1_X_PRODUCTION_GATE' and s['attempt_id']=='attempt_001'
assert s['readonly_session'] and not s['run_called'] and not s['save_called'] and s['all_finite']
assert not s['gate_closure_pass'] and s['gate_order_sum_pass']
a=json.loads((C/'run_attempt_ledger.json').read_text())
assert a['entered'] and a['run_invocation_count']==1 and a['engine_completed'] and a['post_saved'] and a['controller_returned']
b=json.loads((E/'solver_budget_audit.json').read_text())
assert b['entered_total_corrected_root']==1 and b['attempt_002_count']==0 and b['automatic_reruns']==0
d=json.loads((E/'gate0_sequence_decision.json').read_text())
assert d['state']=='BLOCKED_BY_GATE0_NUMERICAL_CLOSURE_GATE' and not d['promotion_allowed'] and not d['formal_hf_dataset_created']
rows=list(csv.DictReader((C/'results_11points.csv').open()))
assert len(rows)==11 and max(abs(float(r['residual'])) for r in rows)>0.02 and max(abs(float(r['order_sum_relative_error'])) for r in rows)<=1e-8
print('PASS_NP_K6_HF_PILOT_GATE0_RUN1_DIAGNOSTIC_STOP_VALIDATOR')
