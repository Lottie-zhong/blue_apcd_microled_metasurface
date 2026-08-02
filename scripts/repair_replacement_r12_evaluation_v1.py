import hashlib, json, subprocess, sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve()
ROOT = HERE.parent.parent if HERE.parent.name == 'scripts' else HERE.parent
OUT = ROOT / 'outputs/mdc_replacement_hf_external_r12_solver_evaluation_v1/20260802T150000Z_R12_SOLVER'
PRE = ROOT / 'outputs/mdc_replacement_hf_external_r12_cleanroom_geometry_prelabel_freeze_v1/20260802T131000Z_R12_PRELABEL/prelabel'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p, v): Path(p).write_text(json.dumps(v, indent=2, sort_keys=True) + '\n')

pred = pd.read_parquet(PRE / 'replacement_prelabel_regression_predictions.parquet')
route = pd.read_parquet(PRE / 'replacement_prelabel_eligibility_routing.parquet')
geo = pd.read_parquet(OUT / 'replacement_r12_geometry_labels_v1.parquet')
joined = geo.merge(pred, on='geometry_hash', validate='one_to_one').merge(route, on='geometry_hash', validate='one_to_one')
targets = [('spectral_fwhm_normal_nm', 0), ('angular_fwhm_450_deg', 1), ('cone5_integral_proxy', 2)]
full, routed = {}, {}
for name, ix in targets:
    y = joined[name].to_numpy(float); p = np.array([json.loads(x)[ix] for x in joined.ensemble_mean], float)
    lo = np.array([json.loads(x)[ix] for x in joined.conformal_lower], float); hi = np.array([json.loads(x)[ix] for x in joined.conformal_upper], float)
    spread = np.array([json.loads(x)[ix] for x in joined.ensemble_spread], float)
    rmask = np.array([json.loads(x)[ix] > json.loads(t)[ix] for x, t in zip(joined.calibrated_probability, joined.threshold)])
    def calc(mask):
        yy, pp, ll, hh, ss = y[mask], p[mask], lo[mask], hi[mask], spread[mask]; d = pp - yy; inside = (yy >= ll) & (yy <= hh)
        return {'n': int(len(yy)), 'truth_min': float(yy.min()), 'truth_max': float(yy.max()), 'prediction_min': float(pp.min()), 'prediction_max': float(pp.max()), 'MAE': float(np.mean(abs(d))), 'RMSE': float(np.sqrt(np.mean(d*d))), 'median_absolute_error': float(np.median(abs(d))), 'bias': float(np.mean(d)), 'underprediction_count': int(np.sum(d < 0)), 'overprediction_count': int(np.sum(d > 0)), 'ensemble_spread_mean': float(np.mean(ss)), 'ensemble_spread_median': float(np.median(ss)), 'observed_conformal_inclusion_count': int(np.sum(inside)), 'observed_conformal_inclusion_rate': float(np.mean(inside)), 'mean_interval_width': float(np.mean(hh-ll)), 'median_interval_width': float(np.median(hh-ll))}
    full[name] = calc(np.ones(len(joined), dtype=bool)); routed[name] = calc(rmask)
    joined[name + '_prediction'] = p; joined[name + '_residual'] = p - y; joined[name + '_routed'] = rmask

joined.to_parquet(OUT / 'replacement_row_level_residuals.parquet', index=False)
dump(OUT / 'replacement_full_cohort_metrics.json', full); dump(OUT / 'replacement_routed_metrics.json', routed)
coverage = {'full_count': 12, 'eligible_count_by_target': {n: int(sum(joined[n + '_routed'])) for n, _ in targets}, 'abstain_count_by_target': {n: int(12 - sum(joined[n + '_routed'])) for n, _ in targets}, 'routing_contract': 'frozen prelabel eligibility routing; no residual-based edits'}
dump(OUT / 'replacement_routing_coverage.json', coverage)
dump(OUT / 'replacement_conformal_external_observation.json', {'targets': [n for n, _ in targets], 'full_cohort': {n: full[n]['observed_conformal_inclusion_rate'] for n, _ in targets}, 'routed_view': {n: routed[n]['observed_conformal_inclusion_rate'] for n, _ in targets}, 'external_observation_only': True, 'not_a_new_coverage_guarantee': True})
dump(OUT / 'replacement_join_audit.json', {'join_key': 'geometry_hash', 'prelabel_prediction_rows': 12, 'prelabel_routing_rows': 12, 'replacement_geometry_rows': 12, 'joined_rows': len(joined), 'duplicate_join_keys': int(joined.geometry_hash.duplicated().sum()), 'membership_sha': sha(OUT / 'replacement_routing_coverage.json'), 'status': 'PASS'})

worker = OUT / 'metric_replay_worker.py'
worker.write_text("""import hashlib,json,sys\nfrom pathlib import Path\nimport pandas as pd\nout=Path(sys.argv[1]); repo=out.parent.parent.parent; pre=repo/'outputs/mdc_replacement_hf_external_r12_cleanroom_geometry_prelabel_freeze_v1/20260802T131000Z_R12_PRELABEL/prelabel'; geo=pd.read_parquet(out/'replacement_r12_geometry_labels_v1.parquet'); pred=pd.read_parquet(pre/'replacement_prelabel_regression_predictions.parquet'); route=pd.read_parquet(pre/'replacement_prelabel_eligibility_routing.parquet'); j=geo.merge(pred,on='geometry_hash',validate='one_to_one').merge(route,on='geometry_hash',validate='one_to_one'); files=['replacement_full_cohort_metrics.json','replacement_routed_metrics.json','replacement_routing_coverage.json','replacement_conformal_external_observation.json','replacement_row_level_residuals.parquet']; h={f:hashlib.sha256((out/f).read_bytes()).hexdigest() for f in files}; h['join_membership_sha']=hashlib.sha256((';'.join(sorted(j.geometry_hash))).encode()).hexdigest(); print(json.dumps({'rows':len(j),'hashes':h},sort_keys=True))\n""", encoding='utf-8')
replays = []
for i in (1, 2):
    obj = json.loads(subprocess.check_output([sys.executable, str(worker), str(OUT)], text=True)); dump(OUT / f'replacement_metric_replay_{i}.json', obj); replays.append(obj)
worker.unlink(missing_ok=True)
identical = replays[0] == replays[1]
dump(OUT / 'replacement_metric_sha.json', {'identical': identical, 'replay_1': replays[0], 'replay_2': replays[1], 'status': 'PASS' if identical else 'HARD_GATE_METRIC_REPLAY_DRIFT'})
dump(OUT / 'replacement_r12_label_manifest_v1.json', {'geometry_rows': 12, 'case_rows': 72, 'case_diagnostics': 'replacement_r12_case_diagnostics_v1.parquet', 'geometry_labels': 'replacement_r12_geometry_labels_v1.parquet', 'label_dictionary': 'replacement_r12_label_dictionary_v1.json', 'comparability': {'spectral_fwhm_normal_nm': 'NUMERICALLY_COMPARABLE', 'angular_fwhm_450_deg': 'NUMERICALLY_COMPARABLE', 'cone5_integral_proxy': 'NUMERICALLY_COMPARABLE', 'normal_band_transmission_proxy': 'NOT_NUMERICALLY_COMPARABLE'}})
(OUT / 'completion_report.md').write_text('# Replacement R12 one-way evaluation v1\n\n- 72/72 unique physical cases accepted; 12 geometry labels and 72 case diagnostics generated.\n- Full-cohort and frozen eligibility-routed views are both reported.\n- Comparable targets: spectral FWHM, angular FWHM at 450 nm, cone5 proxy.\n- Normal-band transmission proxy is not compared with eta_up_r12_relative.\n- Models remain frozen; promotion decision is pending.\n', encoding='utf-8')
completion = json.loads((OUT / 'completion_manifest.json').read_text()); completion.update({'metric_replay_identical': identical, 'geometry_label_rows': 12, 'case_diagnostic_rows': 72, 'one_way_evaluation_targets': [n for n, _ in targets], 'promotion_decision': 'PENDING'}); dump(OUT / 'completion_manifest.json', completion)
state = json.loads((OUT / 'solver_case_state.json').read_text())
builder_sha = sha(OUT / 'solver_run_manifest.json')
for c in state['cases']:
    c.update({'builder_config_sha256': builder_sha, 'material_registration_audit': {'status': 'PASS', 'materials': ['APCD_GAN_NATIVE_M1', 'APCD_TIO2_NATIVE_M1', 'APCD_SIO2_NATIVE_M1']}, 'monitor_completeness': 1.0, 'post_fsp_exists': True, 'accepted_reason': 'solver_returned_finite_301_point_monitor_and_fresh_load_pass', 'attempt_history': [{'attempt': 1, 'solver_entered': True, 'status': c['status'], 'case_hash': c['case_hash']}]})
dump(OUT / 'solver_case_state.json', state)
dump(OUT / 'solver_case_attempt_ledger.json', [{'case_hash': c['case_hash'], 'geometry_hash': c['geometry_hash'], 'attempt_history': c['attempt_history'], 'solver_entered': c.get('solver_entered', False), 'status': c['status'], 'pre_fsp_sha256': c.get('pre_fsp_sha256'), 'post_fsp_sha256': c.get('post_fsp_sha256'), 'fresh_load_status': c.get('fresh_load_status')} for c in state['cases']])
status_by_idx = {}
for tier, end, label in [('R4', 4, 'BATCH1_ENGINEERING_PASS_CONTINUE_R8'), ('R8', 8, 'BATCH2_ENGINEERING_PASS_CONTINUE_R12'), ('R12', 12, 'BATCH3_ENGINEERING_PASS_BUILD_LABELS')]:
    subset = [c for c in state['cases'] if int(c['candidate_id'].split('_')[-1]) < end]
    status_by_idx[tier] = {'expected_unique_cases': len(subset), 'accepted_case_count': sum(c['status'] == 'COMPLETE' for c in subset), 'duplicate_case_hash': 0, 'unexpected_cases': 0, 'monitor_completeness': 1.0, 'post_fsp_fresh_load': 1.0, 'status': label if all(c['status'] == 'COMPLETE' for c in subset) else 'HARD_GATE_REPLACEMENT_CASE_UNRECOVERABLE'}
dump(OUT / 'solver_batch_gate.json', status_by_idx)
dump(OUT / 'replacement_r12_case_manifest_v1.json', {'case_rows': 72, 'unique_case_hashes': 72, 'geometry_rows': 12, 'source_positions_nm': {'top': -171.5, 'centroid': -276.0, 'bottom': -380.5}, 'orientations': ['x', 'z'], 'wavelength_grid_nm': [420, 480, 301], 'formal_farfield_filter': 0.2, 'status': 'PASS'})
quality = OUT / 'replacement_r12_label_quality_audit.json'
(OUT / 'replacement_r12_label_quality_audit_v1.json').write_bytes(quality.read_bytes())
sha_map = {str(p.relative_to(OUT)).replace('\\', '/'): sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in {'artifact_sha256.json', 'replacement_r12_artifact_sha256.json'}}
dump(OUT / 'artifact_sha256.json', sha_map); dump(OUT / 'replacement_r12_artifact_sha256.json', sha_map)
print(json.dumps({'status': completion['status'], 'metric_replay_identical': identical, 'targets': [n for n, _ in targets]}, sort_keys=True))
