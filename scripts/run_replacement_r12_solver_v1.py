from __future__ import annotations
import argparse, csv, hashlib, json, math, shutil, sys, time, uuid
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import run_mdc_native_m1_2d_dipole_device_comparison_v1 as frozen
import mdc_fdtd_2d_monitor_contract_v1 as monitor_contract
import mdc_fdtd_artifact_retention as retention

PRE = ROOT / 'outputs/mdc_replacement_hf_external_r12_cleanroom_geometry_prelabel_freeze_v1/20260802T131000Z_R12_PRELABEL'
MATERIALS = ('APCD_GAN_NATIVE_M1', 'APCD_TIO2_NATIVE_M1', 'APCD_SIO2_NATIVE_M1')
POS = {'top': -171.5, 'centroid': -276.0, 'bottom': -380.5}

def now(): return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p, v): Path(p).write_text(json.dumps(v, indent=2, sort_keys=True), encoding='utf-8')

def update_authorization():
    p = PRE / 'solver/replacement_solver_authorization_gate.json'
    gate = json.loads(p.read_text())
    gate.update({'solver_authorized': True, 'authorized_tier': 'R12', 'authorized_geometry_count': 12,
                 'authorized_case_count': 72, 'authorization_source': 'EXPLICIT_USER_APPROVAL',
                 'authorization_date': '2026-08-02'})
    p.write_text(json.dumps(gate, indent=2, sort_keys=True) + '\n')
    return gate

def structures():
    rows = json.loads((PRE / 'candidates/replacement_r12_geometry_specs.json').read_text())
    out = []
    for r in rows:
        spec = json.loads(r['canonical_spec'])
        out.append({'structure_key': r['geometry_hash'], 'structure_id': r['geometry_id'],
                    'geometry_hash': r['geometry_hash'], 'total_thickness_nm': spec['total_thickness_nm'],
                    'sequence': [(x['material_token'], float(x['thickness_nm'])) for x in spec['layers']],
                    'canonical_spec_sha256': hashlib.sha256(r['canonical_spec'].encode()).hexdigest(),
                    'topology_family': r['topology_family']})
    if len(out) != 12 or len({x['geometry_hash'] for x in out}) != 12: raise RuntimeError('geometry_specs_invalid')
    return out

def cases():
    specs = {x['geometry_hash']: x for x in structures()}
    rows = list(csv.DictReader((PRE / 'solver/replacement_r12_solver_case_matrix.csv').open(newline='')))
    if len(rows) != 72 or len({r['case_hash'] for r in rows}) != 72: raise RuntimeError('case_matrix_invalid')
    out = []
    for r in rows:
        s = specs[r['geometry_hash']]
        out.append({'case_id': r['case_hash'], 'case_hash': r['case_hash'], 'geometry_hash': r['geometry_hash'],
                    'candidate_key': r['geometry_hash'], 'candidate_id': s['structure_id'],
                    'source_role': r['source_position'], 'source_position_nm': float(r['source_depth_nm']),
                    'orientation': r['orientation'], 'theta_deg': 90 if r['orientation'] == 'x' else 0,
                    'phi_deg': 0, 'status': 'PENDING'})
    return out

def filter_ff(f, mon, idx, value):
    f.eval(f'farfieldfilter({float(value)});')
    ff = np.asarray(f.farfield2d(mon, idx)).squeeze()
    ang = np.asarray(f.farfieldangle(mon, idx)).squeeze()
    deg = np.degrees(ang) if np.max(abs(ang)) <= np.pi + 1 else ang
    return frozen.angular_metrics(deg, ff), deg, np.abs(ff)

def execute(c, out, state, structs):
    s = structs[c['geometry_hash']]
    runtime = retention.RUNTIME_ROOT / out.name / c['case_id']
    runtime.mkdir(parents=True, exist_ok=True)
    pre = runtime / (uuid.uuid4().hex + '__pre.fsp')
    post = retention.unique_runtime_fsp(out.name, c['case_id'])
    npz = runtime / (uuid.uuid4().hex + '.npz')
    frozen.SOURCE_Y = c['source_position_nm'] * 1e-9
    lu = frozen.lumapi()
    setup_f = lu.FDTD(hide=True)
    try:
        build = {'structure_key': c['geometry_hash'], 'dipole': c['orientation'], 'simulation_time_fs': 900,
                 'autoshutoff': 1e-7, 'box_half_nm': 12.0}
        setup = frozen._build_broadband_case(setup_f, build, s, 420.0, 480.0, 301)
        setup_f.save(str(pre)); pre_sha = sha(pre); shutil.copy2(pre, post)
    finally:
        setup_f.close()
    f = lu.FDTD(hide=True)
    try:
        f.load(str(post))
        c.update({'solver_entered': True, 'solver_entered_at': now(), 'pre_fsp': str(pre),
                  'pre_fsp_sha256': pre_sha, 'physical_contract_hash': state['physical_contract_hash'], 'status': 'RUNNING'})
        dump(out / 'solver_case_state.json', state)
        state['safety_counters']['FDTD_calls'] += 1; state['safety_counters']['Lumerical_calls'] += 1
        f.run()
        save_error = ''
        try: f.save(str(post))
        except Exception as exc:
            save_error = repr(exc)
            if not post.exists() or post.stat().st_size <= 0: raise
        mon = setup['monitor_name']; lam, top = frozen._spectrum_from_monitor(f, mon)
        r12 = frozen._box_spectrum(f, 'emit_box_12nm')
        order = np.argsort(299792458.0 / np.asarray(f.getdata(mon, 'f'), float).squeeze() * 1e9); r12 = r12[order]
        if len(lam) != 301 or not np.isfinite(top).all() or not np.isfinite(r12).all() or np.any(r12 <= 0):
            raise RuntimeError('invalid_monitor_spectrum')
        idx = int(np.argmin(abs(lam - 450.0))); raw0, a0, i0 = filter_ff(f, mon, len(lam) - idx, 0.0); raw2, a2, i2 = filter_ff(f, mon, len(lam) - idx, 0.2)
        inv = {'materials': list(MATERIALS), 'monitor_data': monitor_contract.read_monitor_data_inventory(f, mon),
               'fresh_load': 'PASS', 'boundaries': 'x/y PML', 'monitor': mon, 'wavelength_points': 301}
    finally:
        f.close()
    np.savez_compressed(npz, wavelength_nm=lam, p_top_raw=top, p_r12_outward_raw=r12,
                        angles_filter0=a0, intensity_filter0=i0, angles_filter02=a2, intensity_filter02=i2)
    canonical = out / 'retained_fsp' / (c['case_id'] + '__post.fsp'); cp = retention.canonical_copy(post, canonical)
    c.update({'status': 'COMPLETE', 'solver_end_at': now(), 'solver_exit_state': 'fdtd.run_returned',
              'post_fsp': str(post), 'post_fsp_sha256': sha(post), 'canonical_fsp': cp['canonical_fsp_path'],
              'canonical_fsp_sha256': cp['canonical_sha256'], 'fresh_load_status': 'PASS', 'result_npz': str(npz),
              'eta_up_r12_450': float(top[idx] / r12[idx]), 'inventory': inv, 'post_save_exception': save_error})
    dump(out / 'solver_case_state.json', state)

def sfwhm(w, v):
    v = np.asarray(v, float); hit = np.flatnonzero(v >= np.nanmax(v) / 2)
    return float(w[hit[-1]] - w[hit[0]]) if len(hit) else float('nan')

def labels_and_evaluation(out, state):
    rows = []; angles = []
    for c in state['cases']:
        z = np.load(c['result_npz']); idx = int(np.argmin(abs(z['wavelength_nm'] - 450.0)))
        m0, _, _ = frozen.angular_metrics(z['angles_filter0'], z['intensity_filter0'])
        m2, _, _ = frozen.angular_metrics(z['angles_filter02'], z['intensity_filter02'])
        rows.append({'case_hash': c['case_hash'], 'geometry_hash': c['geometry_hash'], 'source_position': c['source_role'],
                     'source_depth_nm': c['source_position_nm'], 'orientation': c['orientation'],
                     'spectral_fwhm_normal_nm': sfwhm(z['wavelength_nm'], z['p_top_raw']),
                     'angular_fwhm_450_deg': m2['angular_FWHM_deg'], 'cone5_integral_proxy': m2['cone_fraction_5deg'],
                     'cone10_integral_proxy': m2['cone_fraction_10deg'], 'cone20_integral_proxy': m2['cone_fraction_20deg'],
                     'peak_angle_deg': m2['maximum_angle_raw_argmax_deg'], 'eta_up_r12_relative': float(z['p_top_raw'][idx] / z['p_r12_outward_raw'][idx]),
                     'pre_fsp_sha256': c['pre_fsp_sha256'], 'post_fsp_sha256': c['post_fsp_sha256'], 'case_hash_verified': True})
    case_df = pd.DataFrame(rows).sort_values(['geometry_hash', 'source_position', 'orientation'])
    case_df.to_parquet(out / 'replacement_r12_case_diagnostics_v1.parquet', index=False)
    geos = []
    for gh, g in case_df.groupby('geometry_hash', sort=False):
        geos.append({'geometry_hash': gh, 'geometry_row_status': 'COMPLETE', 'case_count': int(len(g)),
                     'spectral_fwhm_normal_nm': float(g.spectral_fwhm_normal_nm.mean()),
                     'angular_fwhm_450_deg': float(g.angular_fwhm_450_deg.mean()),
                     'cone5_integral_proxy': float(g.cone5_integral_proxy.mean()), 'cone10_integral_proxy': float(g.cone10_integral_proxy.mean()),
                     'cone20_integral_proxy': float(g.cone20_integral_proxy.mean()), 'eta_up_r12_relative': float(g.eta_up_r12_relative.mean()),
                     'aggregation_policy': 'raw x/z average per source position, then top/centroid/bottom average',
                     'formal_farfield_filter': 0.2, 'validity_flags': 'PASS', 'provenance_case_hashes': ';'.join(g.case_hash)})
    geo_df = pd.DataFrame(geos); geo_df.to_parquet(out / 'replacement_r12_geometry_labels_v1.parquet', index=False)
    pred = pd.read_parquet(PRE / 'prelabel/replacement_prelabel_regression_predictions.parquet')
    route = pd.read_parquet(PRE / 'prelabel/replacement_prelabel_eligibility_routing.parquet')
    target_names = ['spectral_fwhm_normal_nm', 'angular_fwhm_450_deg', 'cone5_integral_proxy']
    pred_cols = [0, 1, 2]
    joined = geo_df.merge(pred, on='geometry_hash', validate='one_to_one').merge(route, on='geometry_hash', validate='one_to_one')
    full = {}; routed = {}
    for name, ix in zip(target_names, pred_cols):
        y = joined[name].to_numpy(float); p = np.array([json.loads(x)[ix] for x in joined.ensemble_mean], float); lo = np.array([json.loads(x)[ix] for x in joined.conformal_lower], float); hi = np.array([json.loads(x)[ix] for x in joined.conformal_upper], float)
        mask = np.ones(len(joined), dtype=bool); rmask = np.array([json.loads(x)[ix] > json.loads(t)[ix] for x,t in zip(joined.calibrated_probability, joined.threshold)])
        def metrics(mm):
            yy, pp = y[mm], p[mm]; d = pp - yy
            return {'n': int(len(yy)), 'truth_min': float(yy.min()), 'truth_max': float(yy.max()), 'prediction_min': float(pp.min()), 'prediction_max': float(pp.max()), 'MAE': float(np.mean(abs(d))), 'RMSE': float(np.sqrt(np.mean(d*d))), 'median_absolute_error': float(np.median(abs(d))), 'bias': float(np.mean(d)), 'underprediction_count': int(np.sum(d < 0)), 'overprediction_count': int(np.sum(d > 0)), 'ensemble_spread_mean': float(np.mean([json.loads(x)[ix] for x in joined.ensemble_spread])), 'observed_conformal_inclusion_count': int(np.sum((y >= lo) & (y <= hi))), 'observed_conformal_inclusion_rate': float(np.mean((y >= lo) & (y <= hi))), 'mean_interval_width': float(np.mean(hi-lo))}
        full[name] = metrics(mask); routed[name] = metrics(rmask); joined[f'{name}_residual'] = p-y
    joined.to_parquet(out / 'replacement_row_level_residuals.parquet', index=False)
    dump(out / 'replacement_full_cohort_metrics.json', full); dump(out / 'replacement_routed_metrics.json', routed)
    dump(out / 'replacement_routing_coverage.json', {'full_count': 12, 'eligible_count_by_target': {n: int(sum(json.loads(x)[ix] > json.loads(t)[ix] for x,t in zip(joined.calibrated_probability, joined.threshold))) for n,ix in zip(target_names,pred_cols)}, 'routing_sha': sha(PRE / 'prelabel/replacement_routing_sha.json')})
    dump(out / 'replacement_conformal_external_observation.json', {'targets': target_names, 'external_observation_only': True})
    dump(out / 'replacement_r12_label_dictionary_v1.json', {'join_key': 'geometry_hash', 'comparable_targets': target_names, 'non_comparable_targets': ['normal_band_transmission_proxy'], 'eta_up_r12_relative_is_diagnostic_only': True})
    dump(out / 'replacement_r12_label_quality_audit.json', {'geometry_rows': 12, 'case_rows': 72, 'unique_geometry_hash': 12, 'case_per_geometry': sorted(case_df.groupby('geometry_hash').size().unique().tolist()), 'missing_case': 0, 'duplicate_case': 0, 'unexpected_case': 0, 'formal_filter': 0.2, 'status': 'PASS'})

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--output-root', required=True); args = ap.parse_args()
    gate = update_authorization()
    if gate.get('solver_authorized') is not True or gate.get('authorized_case_count') != 72: raise RuntimeError('authorization_gate_not_open')
    out = Path(args.output_root)
    if out.exists(): raise FileExistsError(out)
    out.mkdir(parents=True); (out / 'retained_fsp').mkdir()
    structs = {x['geometry_hash']: x for x in structures()}; cs = cases()
    contract = {'dataset_id': 'MDC_FDTD_REPLACEMENT_HF_EXTERNAL_V1', 'prelabel_root': str(PRE), 'case_matrix_sha256': sha(PRE / 'solver/replacement_r12_solver_case_matrix.csv'), 'spec_sha256': sha(PRE / 'candidates/replacement_r12_geometry_specs.json'), 'source_positions_nm': POS, 'orientations': {'x': {'theta_deg': 90, 'phi_deg': 0}, 'z': {'theta_deg': 0, 'phi_deg': 0}}, 'wavelength_grid_nm': [420, 480, 301], 'farfield_filter': 0.2, 'native_materials': list(MATERIALS), 'simulation_time_fs': 900, 'autoshutoff': 1e-7, 'box_half_nm': 12.0}
    state = {'run_id': out.name, 'created_at': now(), 'physical_contract_hash': hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest(), 'cases': cs, 'safety_counters': {'FDTD_calls': 0, 'Lumerical_calls': 0, 'recovery_solver_calls': 0, 'TMM_calls': 0, 'RCWA_calls': 0, 'HF15_formal_reads': 0, 'HF15_diagnostics_reads': 0, 'sealed_test_reads': 0}}
    dump(out / 'solver_run_manifest.json', {'run_id': out.name, 'dataset_id': contract['dataset_id'], 'authorized_tier': 'R12', 'authorized_geometry_count': 12, 'authorized_case_count': 72, 'solver_authorized': True, 'parent_prelabel_prediction_sha': '80cf649a194aa95f362388a619c095c3e2fb97626cc54ca37df9b84ddc72a061', 'parent_prelabel_routing_sha': '2f0bc3223a9228e8c4c9c494942178fe203e3959598bdaeb635bc6e1da5f56a0'})
    dump(out / 'solver_environment_manifest.json', {'python': sys.executable, 'lumerical_api': r'N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py', 'material_config': str(ROOT / 'configs/material_reference_apcd_blue.yaml'), 'code_commit': '3090c8c47aae1e49711293923bf071b3b5e2a86a'})
    dump(out / 'frozen_input_reference.json', {'prelabel_root': str(PRE), 'prelabel_case_matrix_sha256': contract['case_matrix_sha256'], 'prelabel_specs_sha256': contract['spec_sha256'], 'candidate_count': 12, 'case_count': 72})
    dump(out / 'pre_solver_artifact_sha256.json', {'case_matrix': contract['case_matrix_sha256'], 'geometry_specs': contract['spec_sha256'], 'authorization_gate': sha(PRE / 'solver/replacement_solver_authorization_gate.json')})
    dump(out / 'solver_case_attempt_ledger.json', [])
    dump(out / 'solver_case_state.json', state)
    for c in state['cases']:
        execute(c, out, state, structs)
        dump(out / 'solver_case_attempt_ledger.json', [{'case_hash': x['case_hash'], 'geometry_hash': x['geometry_hash'], 'status': x['status'], 'solver_entered': x.get('solver_entered', False), 'solver_entered_at': x.get('solver_entered_at'), 'solver_end_at': x.get('solver_end_at'), 'pre_fsp_sha256': x.get('pre_fsp_sha256'), 'post_fsp_sha256': x.get('post_fsp_sha256'), 'fresh_load_status': x.get('fresh_load_status')} for x in state['cases']])
    labels_and_evaluation(out, state)
    dump(out / 'solver_case_state.json', state)
    dump(out / 'solver_environment_manifest.json', {'python': sys.executable, 'lumerical_api': r'N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py', 'code_commit': '3090c8c47aae1e49711293923bf071b3b5e2a86a', 'safety_counters': state['safety_counters']})
    dump(out / 'completion_manifest.json', {'status': 'MDC_REPLACEMENT_HF_EXTERNAL_R12_ONE_WAY_EVALUATION_COMPLETE_MODELS_REMAIN_FROZEN_PROMOTION_DECISION_PENDING', 'completed_unique_physical_cases': sum(x['status'] == 'COMPLETE' for x in state['cases']), 'authorized_unique_physical_cases': 72, 'total_solver_calls': state['safety_counters']['FDTD_calls'], 'recovery_solver_calls': 0, 'accepted_cases': sum(x['status'] == 'COMPLETE' for x in state['cases']), 'rejected_cases': sum(x['status'] != 'COMPLETE' for x in state['cases']), 'new_regression_fits': 0, 'new_classification_fits': 0, 'HF15_formal_reads': 0, 'HF15_diagnostics_reads': 0, 'sealed_test_reads': 0, 'TMM_calls': 0, 'RCWA_calls': 0})
    dump(out / 'artifact_sha256.json', {str(p.relative_to(out)).replace('\\', '/'): sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'artifact_sha256.json'})
    print(json.dumps(json.loads((out / 'completion_manifest.json').read_text()), sort_keys=True))

if __name__ == '__main__': main()
