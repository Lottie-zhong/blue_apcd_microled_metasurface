import csv, json
import subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[1]
E=R/'outputs/np_k6_hf_pilot_gate0_n2_production_mesh_v1_corrected_monitor_contract_v1'
C=E/'cases/RUN3C_N2_NATIVE_M1_X_PRODUCTION_GATE'
s=json.loads((C/'extraction_manifest.json').read_text())
assert s['case_id']=='RUN3C_N2_NATIVE_M1_X_PRODUCTION_GATE' and s['attempt_id']=='attempt_001'
assert s['readonly_session'] and not s['run_called'] and not s['save_called'] and s['all_finite']
assert s['sourcepower_api_extracted'] and s['raw_power_api_extracted'] and s['all_solver_reported_transmitted_orders_retained']
assert not s['gate_closure_pass'] and s['gate_order_sum_pass']
a=json.loads((C/'run_attempt_ledger.json').read_text())
assert a['entered'] and a['run_invocation_count']==1 and a['engine_completed'] and a['post_saved'] and a['controller_returned']
b=json.loads((E/'solver_budget_audit.json').read_text())
assert b['entered_total_corrected_root']==1 and b['attempt_002_count']==0 and b['automatic_reruns']==0
d=json.loads((E/'gate0_sequence_decision.json').read_text())
assert d['state']=='NP_K6_HF_PILOT_GATE0_BLOCKED_BY_NUMERICAL_FIDELITY' and not d['promotion_allowed'] and not d['formal_hf_dataset_created']
rows=list(csv.DictReader((C/'results_11points.csv').open()))
assert len(rows)==11 and max(abs(float(r['residual'])) for r in rows)>0.02 and max(abs(float(r['order_sum_relative_error'])) for r in rows)<=1e-8
manifest=json.loads((E/'gate0_setup_manifest.json').read_text())
assert len(manifest['cases'])==6 and [x['case_order'] for x in manifest['cases']]==list(range(1,7))
assert manifest['sealed_test_touched'] is False and manifest['solver_entered']==0
for spec in manifest['cases']:
 a=json.loads((E/'cases'/spec['case_id']/'setup_readback_audit.json').read_text())
 assert a['setup_diff_pass'] and a['native_m1_sampled_confirmed'] and not a['unexpected_differences']
 assert a['material_readback']['APCD_TIO2_NATIVE_M1']['type']=='Sampled 3D data'
 assert a['material_readback']['APCD_SIO2_NATIVE_M1']['type']=='Sampled 3D data'
summary=list(csv.DictReader((E/'gate0_case_execution_summary.csv').open()))
assert len(summary)==6 and sum(r['entered']=='True' for r in summary)==1 and summary[0]['case_id']=='RUN3C_N2_NATIVE_M1_X_PRODUCTION_GATE'
assert all(r['entered']=='False' for r in summary[1:])
mesh=json.loads((E/'production_mesh_candidate_contract_v1.json').read_text())
assert mesh['production_mesh_candidate_id']=='NP_K6_N2_FIXED_5NM_NATIVE_M1_CANDIDATE_V1' and mesh['dx_dy_dz_nm']==[5,5,5]
assert all(x in mesh['intended_axis_arrays_nm']['x'] for x in range(-870,871,10))
assert all(y in mesh['intended_axis_arrays_nm']['y'] for y in range(-145,146,10))
assert all(z in mesh['intended_axis_arrays_nm']['z'] for z in range(-100,601,10))
b=json.loads((E/'solver_budget_audit.json').read_text())
assert b['entered_total_corrected_root']==1 and b['attempt_002_count']==0 and b['automatic_reruns']==0
norm=json.loads((C/'normalization_audit.json').read_text()); assert norm['pass'] and norm['max_abs_raw_sourcepower_monitor_mismatch']<=1e-8
runtime=json.loads((C/'runtime_audit.json').read_text()); assert runtime['iterations']==104900 and runtime['auto_shutoff_confirmed']
cap=json.loads((C/'order_extraction_capability_audit.json').read_text()); assert cap['order_count']==7 and cap['order_sum_gate_max_relative_error']<=1e-8
struct=json.loads((C/'structure_interval_audit.json').read_text()); assert struct['pass'] and abs(struct['structure_interval_signed_anomaly'])<=0.02
conv=json.loads((E/'run3c_x_n1_n2_convergence_audit.json').read_text()); assert conv['status']=='NOT_EVALUATED_DUE_TO_EARLY_STOP'
promo=json.loads((E/'hf_promotion_decision.json').read_text()); assert promo['promoted_task_count']==0 and not promo['formal_hf_dataset_created'] and promo['sealed_test_labels_generated']==0
assert not (E.parent/'np_k6_hf_dataset_v1').exists()
assert subprocess.run(['git','diff','--quiet','--','outputs/np_k6_ml_d0_database_foundation_v1'],cwd=str(R)).returncode==0
grid=json.loads((E/'actual_grid_gate_audit.json').read_text()); assert grid['status']=='NOT_EVALUATED_CROSS_CASE_EARLY_STOP'
assert json.loads((E/'gate0_completion_audit.json').read_text())['transactional_promotion']=='PASS_NO_PARTIAL_PROMOTION'
print('PASS_NP_K6_HF_PILOT_GATE0_RUN1_DIAGNOSTIC_STOP_VALIDATOR')
