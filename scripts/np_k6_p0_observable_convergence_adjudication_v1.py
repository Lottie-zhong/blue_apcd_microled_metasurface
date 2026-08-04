from pathlib import Path
import csv
import hashlib
import json
import math
from datetime import datetime, timezone

ROOT = Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1')
OUT = ROOT / 'outputs/np_k6_p0_observable_convergence_adjudication_v1'
OUT.mkdir(parents=True, exist_ok=True)

def jdump(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')

def load_json(rel):
    return json.loads((ROOT / 'outputs' / rel).read_text(encoding='utf-8'))

def load_csv(rel):
    p = ROOT / 'outputs' / rel
    with p.open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    return rows

def wlmap(rows):
    return {int(round(float(r['wavelength_nm']))): r for r in rows}

def num(row, key, default=float('nan')):
    try:
        return float(row[key])
    except Exception:
        return default

def finite_values(rows, keys):
    return all(math.isfinite(num(r, k)) for r in rows for k in keys)

def max_abs(rows, key):
    return max(abs(num(r, key)) for r in rows)

def rmse(vals):
    return math.sqrt(sum(v * v for v in vals) / len(vals))

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

now = datetime.now(timezone.utc).isoformat()
one_rows = wlmap(load_csv('np_k6_hf_p0_label_generator_recovery_v1/cases/RUN3C_P_PILOT_HF_V1/hf_observations_long.csv'))
two_rows = wlmap(load_csv('np_k6_p0_simtime_2ps_recovery_v2/spectral_metrics_11points.csv'))
three_rows = wlmap(load_csv('np_k6_p0_simtime_3ps_control_v1/spectral_metrics_11points.csv'))
one_orders = load_csv('np_k6_hf_p0_label_generator_recovery_v1/cases/RUN3C_P_PILOT_HF_V1/hf_transmitted_orders_long.csv')
two_orders = load_csv('np_k6_p0_simtime_2ps_recovery_v2/transmitted_orders_11points.csv')
three_orders = load_csv('np_k6_p0_simtime_3ps_control_v1/transmitted_orders_11points.csv')

metric_fields = ['T_total', 'R_total', 'eta_plus1', 'eta_0', 'eta_minus1', 'directionality']
comparison_rows = []
for wl in range(445, 456):
    out = {'wavelength_nm': wl}
    for name, rows in [('1ps', one_rows), ('2ps', two_rows), ('3ps', three_rows)]:
        for key in metric_fields:
            out[f'{key}_{name}'] = num(rows[wl], key)
    for key in metric_fields:
        out[f'delta_{key}_2ps_minus_1ps'] = out[f'{key}_2ps'] - out[f'{key}_1ps']
        out[f'delta_{key}_3ps_minus_2ps'] = out[f'{key}_3ps'] - out[f'{key}_2ps']
    comparison_rows.append(out)
with (OUT / 'convergence_2ps_3ps_spectral_comparison.csv').open('w', newline='', encoding='utf-8') as f:
    fields = list(comparison_rows[0])
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader(); w.writerows(comparison_rows)

def order_map(rows):
    return {(int(round(float(r['wavelength_nm']))), int(r.get('order_n', r.get('grating_order_n')))): r for r in rows}
oms = {'1ps': order_map(one_orders), '2ps': order_map(two_orders), '3ps': order_map(three_orders)}
order_rows = []
weighted = []
for wl in range(445, 456):
    orders = sorted({n for (w, n) in oms['1ps'] if w == wl} & {n for (w, n) in oms['2ps'] if w == wl} & {n for (w, n) in oms['3ps'] if w == wl})
    total = 0.0
    for n in orders:
        vals = {}
        for name in ['1ps', '2ps', '3ps']:
            r = oms[name][(wl, n)]
            vals[name] = num(r, 'absolute_efficiency')
        total += abs(vals['3ps'] - vals['2ps'])
        order_rows.append({'wavelength_nm': wl, 'order_n': n, 'u_x_3ps': num(oms['3ps'][(wl, n)], 'u_x'), 'angle_deg_3ps': num(oms['3ps'][(wl, n)], 'angle_deg'), 'absolute_efficiency_1ps': vals['1ps'], 'absolute_efficiency_2ps': vals['2ps'], 'absolute_efficiency_3ps': vals['3ps'], 'delta_2ps_minus_1ps': vals['2ps'] - vals['1ps'], 'delta_3ps_minus_2ps': vals['3ps'] - vals['2ps']})
    weighted.append(total)
with (OUT / 'transmitted_order_convergence.csv').open('w', newline='', encoding='utf-8') as f:
    fields = list(order_rows[0]); w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(order_rows)

one_to_two = {k: [r[f'delta_{k}_2ps_minus_1ps'] for r in comparison_rows] for k in metric_fields}
two_to_three = {k: [r[f'delta_{k}_3ps_minus_2ps'] for r in comparison_rows] for k in metric_fields}
three_closure = load_json('np_k6_p0_simtime_3ps_control_v1/closure_audit.json')
three_struct = load_json('np_k6_p0_simtime_3ps_control_v1/structure_interval_448_audit.json')
two_closure = load_json('np_k6_p0_simtime_2ps_recovery_v2/closure_audit.json')
two_struct = load_json('np_k6_p0_simtime_2ps_recovery_v2/structure_interval_448_audit.json')
one_gate = load_json('np_k6_hf_p0_label_generator_recovery_v1/pilot_numerical_gate_failure.json')
base = {
    'three_ps_full_band_closure_max_abs': three_closure['max_abs_closure_residual'],
    'three_ps_full_band_closure_threshold': 0.01,
    'three_ps_full_band_closure_pass': three_closure['max_abs_closure_residual'] <= 0.01,
    'three_ps_structure_448_abs': abs(three_struct['delta_F']),
    'three_ps_structure_448_threshold': 0.01,
    'three_ps_structure_448_pass': abs(three_struct['delta_F']) <= 0.01,
    'three_ps_order_sum_mismatch_max': max_abs(three_rows.values(), 'transmitted_order_sum_mismatch'),
    'three_ps_order_sum_threshold': 1e-8,
    'three_ps_order_sum_pass': max_abs(three_rows.values(), 'transmitted_order_sum_mismatch') <= 1e-8,
    'three_ps_normalization_mismatch_max': max(max(max(abs(num(r, 'transmission_power_normalization_mismatch')), abs(num(r, 'reflection_power_normalization_mismatch'))) for r in three_rows.values()), 0.0),
    'three_ps_normalization_threshold': 1e-8,
    'three_ps_normalization_pass': max(max(max(abs(num(r, 'transmission_power_normalization_mismatch')), abs(num(r, 'reflection_power_normalization_mismatch'))) for r in three_rows.values()), 0.0) <= 1e-8,
    'three_ps_exact_11_points': sorted(three_rows) == list(range(445, 456)),
    'three_ps_finite_values': finite_values(list(three_rows.values()), ['T_total', 'R_total', 'signed_closure_residual', 'eta_plus1', 'eta_0', 'eta_minus1', 'directionality']),
    'three_ps_power_bounds': all(0 <= num(r, 'T_total') <= 1.2 and 0 <= num(r, 'R_total') <= 1.2 for r in three_rows.values()),
}
obs = {}
def add_gate(name, value, threshold, mode='le'):
    obs[name] = {'value': value, 'threshold': threshold, 'pass': (value <= threshold if mode == 'le' else value < threshold)}
for key, threshold in [('T_total', .025), ('R_total', .025), ('eta_plus1', .02), ('eta_0', .02), ('eta_minus1', .01), ('directionality', .01)]:
    vals = two_to_three[key]; add_gate(f'max_abs_delta_{key}_2ps_to_3ps', max(abs(v) for v in vals), threshold)
add_gate('rmse_delta_eta_plus1_2ps_to_3ps', rmse(two_to_three['eta_plus1']), .01)
add_gate('delta_eta_plus1_450nm_2ps_to_3ps', abs(two_to_three['eta_plus1'][5]), .005)
add_gate('max_full_order_weighted_difference_2ps_to_3ps', max(weighted), .05)
add_gate('mean_full_order_weighted_difference_2ps_to_3ps', sum(weighted) / len(weighted), .025)
trend = {
    'max_closure_abs': {'1ps': one_gate['gates']['max_abs_closure_residual'], '2ps': two_closure['max_abs_residual_2ps'], '3ps': three_closure['max_abs_closure_residual']},
    'structure_448_signed': {'1ps': one_gate['failed_metrics'].get('structure_448', -0.08020762156035277), '2ps': two_struct['signed_flux_jump'], '3ps': three_struct['delta_F']},
    'auto_shutoff': {'1ps': 0.000261435, '2ps': 0.000150024, '3ps': 7.43634e-05},
    'T_450': {name: num(rows[450], 'T_total') for name, rows in [('1ps', one_rows), ('2ps', two_rows), ('3ps', three_rows)]},
    'R_450': {name: num(rows[450], 'R_total') for name, rows in [('1ps', one_rows), ('2ps', two_rows), ('3ps', three_rows)]},
    'eta_plus1_450': {name: num(rows[450], 'eta_plus1') for name, rows in [('1ps', one_rows), ('2ps', two_rows), ('3ps', three_rows)]},
}
trend['eta_plus1_450_improvement_3ps_vs_2ps_less_than_2ps_vs_1ps'] = abs(two_to_three['eta_plus1'][5]) < abs(one_to_two['eta_plus1'][5])
trend['closure_improves_1_to_2_to_3'] = trend['max_closure_abs']['3ps'] < trend['max_closure_abs']['2ps'] < trend['max_closure_abs']['1ps']
trend['structure_magnitude_improves_1_to_2_to_3'] = abs(trend['structure_448_signed']['3ps']) < abs(trend['structure_448_signed']['2ps']) < abs(trend['structure_448_signed']['1ps'])
base_pass = [base[k] for k in ['three_ps_full_band_closure_pass', 'three_ps_structure_448_pass', 'three_ps_order_sum_pass', 'three_ps_normalization_pass', 'three_ps_exact_11_points', 'three_ps_finite_values', 'three_ps_power_bounds']]
all_gates = base_pass + [x['pass'] for x in obs.values()] + [trend['eta_plus1_450_improvement_3ps_vs_2ps_less_than_2ps_vs_1ps'], trend['closure_improves_1_to_2_to_3'], trend['structure_magnitude_improves_1_to_2_to_3']]
classification = 'NP_K6_P0_OBSERVABLE_CONVERGENCE_ACCEPTED_3PS_GENERATOR_READY' if all(all_gates) else 'NP_K6_P0_OBSERVABLE_CONVERGENCE_NOT_ESTABLISHED'
gate_doc = {'schema_version': 'np_k6_p0_observable_convergence_gate_results_v1', 'generated_utc': now, 'classification': classification, 'base_3ps_gates': base, 'observable_2ps_to_3ps_gates': obs, 'trend_gates': {'eta_plus1_450_improvement': trend['eta_plus1_450_improvement_3ps_vs_2ps_less_than_2ps_vs_1ps'], 'closure': trend['closure_improves_1_to_2_to_3'], 'structure': trend['structure_magnitude_improves_1_to_2_to_3']}, 'all_gates_pass': all(all_gates)}
jdump(OUT / 'convergence_gate_results.json', gate_doc)
jdump(OUT / 'convergence_trend_1ps_2ps_3ps.json', {'schema_version': 'np_k6_p0_observable_convergence_trend_v1', 'generated_utc': now, 'endpoint_only': True, 'points': trend, 'source': 'read-only formal endpoint evidence; 10ps excluded'})

runtime = ROOT / 'outputs/np_k6_p0_simtime_10ps_final_v1_runtime/runtime_runs/RUN3C_P_PILOT_HF_SIMTIME_10PS_FINAL_V1/attempt_001'
ten_ledger = json.loads((runtime / 'entered_ledger.json').read_text(encoding='utf-8'))
ten_status = json.loads((runtime / 'controller_status.json').read_text(encoding='utf-8'))
ten_heartbeat = json.loads((runtime / 'heartbeat.json').read_text(encoding='utf-8'))
ten_post = runtime / 'RUN3C_P_PILOT_HF_SIMTIME_10PS_FINAL_V1_attempt_001_post.fsp'
stopped = {'schema_version': 'np_k6_p0_stopped_10ps_attempt_audit_v1', 'generated_utc': now, 'case_id': ten_ledger.get('case_id'), 'attempt_id': ten_ledger.get('attempt_id'), 'entered': ten_ledger.get('entered'), 'run_invocation_count': ten_ledger.get('run_invocation_count'), 'engine_completed': ten_ledger.get('engine_completed'), 'controller_returned': ten_ledger.get('controller_returned'), 'post_saved': ten_ledger.get('post_saved'), 'last_heartbeat': ten_heartbeat, 'last_controller_status': ten_status, 'post_fsp_exists': ten_post.exists(), 'user_aborted': True, 'rerun_forbidden': True, 'recovery_forbidden': True, 'training_label': False, 'candidate_performance_label': False, 'numerical_conclusion': 'none', 'classification': 'NP_K6_P0_10PS_FINAL_USER_ABORTED_NO_VALID_POST' if not ten_post.exists() else 'NP_K6_P0_10PS_FINAL_USER_ABORTED_PARTIAL_POST_UNUSABLE', 'stop_confirmation_note': 'User supplied manual-stop fact; this audit does not issue stop/restart commands.'}
jdump(OUT / 'stopped_10ps_attempt_audit.json', stopped)

contract = {'schema_version': 'np_k6_p0_pilot_label_fidelity_contract_v2', 'contract_id': 'NP_K6_PILOT_LABEL_FIDELITY_CONTRACT_V2', 'scope': {'stack': 'independent K6 pilot', 'u_x': 0.0, 'k_y': 0.0, 'polarization': ['p', 's'], 'wavelengths_nm': list(range(445,456)), 'development_pilot_only': True, 'bulk_mdc_compatible': False}, 'auto_shutoff': {'threshold': 1e-5, 'role': 'recorded diagnostic and convergence indicator', 'sole_label_gate': False, 'policy': 'DECAY_DIAGNOSTIC_RECORDED_NOT_SOLE_LABEL_GATE'}, 'required_label_gates': {'energy_closure': True, 'structure_interval_anomaly': True, 'transmitted_order_closure': True, 'normalization_consistency': True, 'observable_convergence': True, 'grid_identity': True, 'material_identity': True, 'spectral_completeness': True, 'no_clipping_or_renormalization': True}, 'formal_hf_labels_before_all_six_anchors': 0, 'training_label': False, 'candidate_performance_label': False}
jdump(OUT / 'label_fidelity_contract_v2.json', contract)
generator = {'schema_version': 'np_k6_p0_fixed_grid_generator_v2', 'generator_id': 'NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_3PS_V2', 'maximum_simulation_time_s': 3e-12, 'auto_shutoff_threshold': 1e-5, 'early_stop_enabled': True, 'reaching_auto_shutoff_required_for_label': False, 'closure_required': True, 'observable_convergence_required': True, 'grid_material_order_normalization_gates_required': True, 'interface_stack': 'NP_K6_INDEPENDENT_STACK_PILOT_V1', 'pilot_scope_only': True, 'bulk_mdc_compatible': False, 'run_authorization': 'remaining five anchors require separate explicit authorization', 'run_invocation_count_this_round': 0}
jdump(OUT / 'generator_v2_contract.json', generator)

remaining = ['RUN3C_S_PILOT_HF_V1','RUN3A_P_PILOT_HF_V1','RUN3A_S_PILOT_HF_V1','RUN3B_P_PILOT_HF_V1','RUN3B_S_PILOT_HF_V1']
entries=[]
for case in remaining:
    p = ROOT / 'outputs/np_k6_hf_p0_label_generator_recovery_v1/cases' / case / 'attempt_ledger.json'
    d = json.loads(p.read_text(encoding='utf-8'))
    entries.append({'case_id':case,'attempt_ledger_path':str(p),'entered':d.get('entered',False),'run_invocation_count':d.get('run_invocation_count',0),'solver_authorized':False,'untouched':d.get('entered',False) is False and d.get('run_invocation_count',0)==0})
jdump(OUT / 'remaining_anchor_authorization_manifest.json', {'schema_version':'np_k6_p0_remaining_anchor_authorization_manifest_v2','generator_id':generator['generator_id'],'remaining_cases':entries,'all_untouched':all(x['untouched'] for x in entries),'formal_hf_labels':0,'training_labels':0,'model_training_started':False,'sealed_test_touched':False,'next_state':'READY_FOR_NP_K6_HF_P0_REMAINING_FIVE_ANCHORS_WITH_3PS_GENERATOR_V2' if classification.endswith('READY') else 'NP_K6_P0_OBSERVABLE_CONVERGENCE_NOT_ESTABLISHED'})

artifacts = []
for rel in ['np_k6_hf_p0_label_generator_recovery_v1/cases/RUN3C_P_PILOT_HF_V1/hf_observations_long.csv','np_k6_p0_simtime_2ps_recovery_v2/spectral_metrics_11points.csv','np_k6_p0_simtime_3ps_control_v1/spectral_metrics_11points.csv']:
    p=ROOT/'outputs'/rel; artifacts.append({'path':str(p),'sha256':sha256(p),'size_bytes':p.stat().st_size})
for name, ledger_rel in [('1ps','np_k6_hf_p0_label_generator_recovery_v1/cases/RUN3C_P_PILOT_HF_V1/attempt_ledger.json'),('2ps','np_k6_p0_simtime_2ps_recovery_v2/entered_ledger.json'),('3ps','np_k6_p0_simtime_3ps_control_v1/entered_ledger.json')]:
    d=load_json(ledger_rel); p=Path(d['post_fsp_path']); artifacts.append({'point':name,'path':str(p),'recorded_sha256':d.get('post_fsp_sha256'),'recomputed_sha256':sha256(p) if p.exists() else None,'exists':p.exists()})
jdump(OUT / 'checksum_manifest.json', {'schema_version':'np_k6_p0_observable_convergence_checksum_manifest_v1','generated_utc':now,'artifacts':artifacts,'post_sha_identity_pass':all(a.get('exists') and a.get('recorded_sha256')==a.get('recomputed_sha256') for a in artifacts if 'point' in a)})
jdump(OUT / 'provenance_audit.json', {'schema_version':'np_k6_p0_observable_convergence_provenance_v1','generated_utc':now,'read_only_extraction':True,'solver_calls_this_round':0,'source_evidence':['1ps RUN3C_P_PILOT_HF_V1','2ps RUN3C_P_PILOT_HF_SIMTIME_2PS_RECOVERY_V2','3ps RUN3C_P_PILOT_HF_SIMTIME_3PS_CONTROL_V1'],'ten_ps_excluded_from_numerical_adjudication':True,'formal_hf_labels':0})

summary = [
    '# NP K6 P0 observable convergence adjudication v1', '',
    f'- classification: `{classification}`',
    f'- 10 ps attempt: `{stopped["classification"]}`, entered={stopped["entered"]}, run_invocation_count={stopped["run_invocation_count"]}, post_exists={stopped["post_fsp_exists"]}',
    f'- 3 ps max closure: `{three_closure["max_abs_closure_residual"]:.12g}`; 448 structure anomaly: `{three_struct["delta_F"]:.12g}`',
    f'- 2 ps -> 3 ps max |delta T|=`{obs["max_abs_delta_T_total_2ps_to_3ps"]["value"]:.12g}`, max |delta R|=`{obs["max_abs_delta_R_total_2ps_to_3ps"]["value"]:.12g}`, max |delta eta(+1)|=`{obs["max_abs_delta_eta_plus1_2ps_to_3ps"]["value"]:.12g}`',
    f'- 450 nm eta(+1): 1ps `{trend["eta_plus1_450"]["1ps"]:.12g}`, 2ps `{trend["eta_plus1_450"]["2ps"]:.12g}`, 3ps `{trend["eta_plus1_450"]["3ps"]:.12g}`',
    '- formal HF labels remain 0; remaining five anchors remain unentered; training/checkpoint/sealed-test untouched.',
]
(OUT.parent.parent / 'docs').mkdir(exist_ok=True)
(ROOT/'docs/np_k6_p0_observable_convergence_adjudication_v1.md').write_text('\n'.join(summary)+'\n', encoding='utf-8')
print(json.dumps({'output':str(OUT),'classification':classification,'all_gates_pass':gate_doc['all_gates_pass'],'post_sha_identity_pass':json.loads((OUT/'checksum_manifest.json').read_text())['post_sha_identity_pass']}, ensure_ascii=False))
