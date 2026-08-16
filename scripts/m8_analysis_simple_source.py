import csv
import json
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT = Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
OUT = ROOT / 'outputs/np_k6_m8_20g_forward_retraining_v1'
HF = ROOT / 'outputs/np_k6_m7a_primary4_targeted_hf_acquisition_closeout_v1/m7a_formal_development_hf_observations_440rows.csv'
SEL = ROOT / 'outputs/np_k6_m7a_targeted_development_acquisition_design_v1/selection_manifest.json'

def read_csv(p):
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def write_csv(name, rows):
    with (OUT / name).open('w', encoding='utf-8', newline='') as f:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)

def write_json(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')

hf = read_csv(HF)
selection = json.loads(SEL.read_text(encoding='utf-8-sig'))['Primary4']
selected = {x['geometry_id'] for x in selection}
scopes = {'HF16': {r['geometry_id'] for r in hf} - selected, 'M7A4': selected, 'HF20': {r['geometry_id'] for r in hf}}

# HF20 truth distributions for the required paired outputs.
truth_rows = []
for scope, geos in scopes.items():
    for metric in ['eta_m+1', 'eta_m+0', 'eta_m-1', 'R_total', 'T_total', 'full_order_profile']:
        vals = []
        for row in hf:
            if row['geometry_id'] not in geos:
                continue
            if metric in {'T_total', 'full_order_profile'}:
                vals.append(sum(float(row[f'eta_m{m:+d}']) for m in (-3, -2, -1, 0, 1, 2, 3)))
            else:
                vals.append(float(row[metric]))
        a = np.asarray(vals, dtype=float)
        truth_rows.append({'scope': scope, 'metric': metric, 'n': len(a), 'mean': float(a.mean()), 'median': float(np.median(a)), 'p90': float(np.quantile(a, .9)), 'max': float(a.max()), 'min': float(a.min())})
write_csv('hf20_truth_distribution_summary.csv', truth_rows)

# HF-LF residual structure using the frozen LF-only OOF row for each key.
oof = read_csv(OUT / 'oof_predictions_20g.csv')
lf = {(r['geometry_id'], r['polarization'].lower(), int(float(r['wavelength_nm']))): r for r in oof if r['model'] == 'LF_only'}
residual = []
for row in hf:
    key = (row['geometry_id'], row['polarization'].lower(), int(float(row['wavelength_nm'])))
    base = lf[key]
    for m in (-3, -2, -1, 0, 1, 2, 3):
        residual.append({'geometry_id': row['geometry_id'], 'polarization': row['polarization'].lower(), 'wavelength_nm': key[2], 'order_n': m, 'hf_minus_lf': float(row[f'eta_m{m:+d}']) - float(base[f'pred_eta_m{m:+d}'])})
write_csv('hf_minus_lf_residual_long.csv', residual)
by_geo = []
for geo in sorted({r['geometry_id'] for r in hf}):
    for pol in ('p', 's'):
        for order in (-3, -2, -1, 0, 1, 2, 3):
            a = np.asarray([x['hf_minus_lf'] for x in residual if x['geometry_id'] == geo and x['polarization'] == pol and int(x['order_n']) == order])
            by_geo.append({'geometry_id': geo, 'polarization': pol, 'order_n': order, 'mean_hf_minus_lf': float(a.mean()), 'mae_hf_minus_lf': float(np.abs(a).mean()), 'max_abs_hf_minus_lf': float(np.abs(a).max())})
write_csv('residual_structure_by_geometry.csv', by_geo)

# Model disagreement buckets and frozen M7/M8 common-HF16 deltas.
dis = read_csv(OUT / 'model_disagreement_long.csv')
audits = []
for signal, error in [('eta_plus1_disagreement', 'ensemble_eta_plus1_abs_error'), ('order_profile_disagreement', 'ensemble_order_profile_abs_error'), ('eta_plus1_disagreement', 'ensemble_R_abs_error')]:
    values = np.asarray([float(x[signal]) for x in dis]); median = float(np.median(values))
    hi = [float(x[error]) for x in dis if float(x[signal]) >= median]; lo = [float(x[error]) for x in dis if float(x[signal]) < median]
    audits.append({'signal': signal, 'error': error, 'median_disagreement': median, 'high_bucket_n': len(hi), 'high_bucket_mean_error': float(np.mean(hi)), 'low_bucket_n': len(lo), 'low_bucket_mean_error': float(np.mean(lo))})
write_json('model_disagreement_summary.json', {'audits': audits, 'uncertainty_claim': 'not calibrated probability'})

old = read_csv(ROOT / 'outputs/np_k6_m7_16g_forward_retraining_v1/oof_predictions_16g.csv')
new = read_csv(OUT / 'oof_predictions_20g.csv')
old_geos = sorted({x['geometry_id'] for x in old})
new_map = {(x['model'], x['geometry_id'], x['polarization'].lower(), int(float(x['wavelength_nm']))): x for x in new}
hf_map = {(x['geometry_id'], x['polarization'].lower(), int(float(x['wavelength_nm']))): x for x in hf}
common = []; summary = []
for model in sorted({x['model'] for x in old}):
    for geo in old_geos:
        old_err = []; new_err = []
        for x in old:
            if x['model'] != model or x['geometry_id'] != geo or x['variant'] != 'ensemble_raw':
                continue
            key = (geo, x['polarization'].lower(), int(float(x['wavelength_nm'])))
            y = hf_map[key]; z = new_map[(model,) + key]
            old_v = np.asarray([float(x[f'pred_eta_m{m:+d}']) for m in (-3, -2, -1, 0, 1, 2, 3)])
            new_v = np.asarray([float(z[f'pred_eta_m{m:+d}']) for m in (-3, -2, -1, 0, 1, 2, 3)])
            true_v = np.asarray([float(y[f'eta_m{m:+d}']) for m in (-3, -2, -1, 0, 1, 2, 3)])
            old_err.append(float(np.abs(old_v - true_v).mean())); new_err.append(float(np.abs(new_v - true_v).mean()))
        if old_err:
            common.append({'model': model, 'geometry_id': geo, 'M7_order_profile_mae': float(np.mean(old_err)), 'M8_order_profile_mae': float(np.mean(new_err)), 'delta_M8_minus_M7': float(np.mean(new_err) - np.mean(old_err))})
    group = [x for x in common if x['model'] == model]
    summary.append({'model': model, 'geometry_count': len(group), 'improved_geometry_count': sum(x['delta_M8_minus_M7'] < 0 for x in group), 'degraded_geometry_count': sum(x['delta_M8_minus_M7'] > 0 for x in group), 'median_delta_M8_minus_M7': float(np.median([x['delta_M8_minus_M7'] for x in group])), 'M7_mean_order_profile_mae': float(np.mean([x['M7_order_profile_mae'] for x in group])), 'M8_mean_order_profile_mae': float(np.mean([x['M8_order_profile_mae'] for x in group]))})
write_csv('common_HF16_geometry_level_delta.csv', common); write_csv('common_HF16_learning_value.csv', summary)

# New4 held-out difficulty and M7 selection-time prospective-like audit.
new4_rows = []
for geo in selected:
    for model in sorted({x['model'] for x in new}):
        pred = [x for x in new if x['model'] == model and x['geometry_id'] == geo]
        if not pred: continue
        errs = []; plus = []
        for x in pred:
            y = hf_map[(geo, x['polarization'].lower(), int(float(x['wavelength_nm'])))]
            errs.append(np.mean([abs(float(x[f'pred_eta_m{m:+d}']) - float(y[f'eta_m{m:+d}'])) for m in (-3, -2, -1, 0, 1, 2, 3)])); plus.append(abs(float(x['pred_eta_m+1']) - float(y['eta_m+1'])))
        new4_rows.append({'model': model, 'geometry_id': geo, 'role': next(s['acquisition_role'] for s in selection if s['geometry_id'] == geo), 'order_profile_mae': float(np.mean(errs)), 'eta_plus1_mae': float(np.mean(plus))})
write_csv('new4_heldout_difficulty.csv', new4_rows)
truth_g = {g: float(np.mean([float(x['eta_m+1']) for x in hf if x['geometry_id'] == g])) for g in selected}
fields = [('lf_eta_plus1', 'LF_only'), ('calibrated_eta_plus1', 'LF_global_bias'), ('ridge_eta_plus1', 'LF_ridge_residual'), ('residual_mlp_eta_plus1', 'corrected_residual_mlp'), ('cnn_eta_plus1', 'circular_cnn')]
pros = []
for s in selection:
    for field, model in fields:
        val = float(s[field]); pros.append({'geometry_id': s['geometry_id'], 'role': s['acquisition_role'], 'selection_model': model, 'selection_time_predicted_broadband_eta_plus1': val, 'M7A_true_broadband_eta_plus1': truth_g[s['geometry_id']], 'absolute_error': abs(val - truth_g[s['geometry_id']])})
write_csv('m7a_prospective_like_selection_time_audit.csv', pros)

# Promotion review with preregistered thresholds.
raw = {x['model']: x for x in read_csv(OUT / 'model_metrics_raw.csv')}; ps = {x['model']: float(x['contrast_mae']) for x in read_csv(OUT / 'ps_contrast_summary.csv')}; inc = raw['LF_global_bias']
thresholds = json.loads((OUT / 'NP_K6_M8_20G_FORWARD_RETRAINING_PREREG_V1.json').read_text(encoding='utf-8-sig'))['promotion_gate']['quantitative_thresholds']; reviews = []
for model in ['LF_ridge_residual', 'LF_paired_shared_contrast', 'corrected_residual_mlp', 'circular_cnn', 'direct_mlp', 'resmlp']:
    r = raw[model]; checks = {}
    checks['order_profile_vs_incumbent'] = float(r['order_profile_mae']) <= float(inc['order_profile_mae'])
    checks['eta_plus1_vs_incumbent'] = float(r['eta_plus1_mae']) <= float(inc['eta_plus1_mae'])
    checks['ranking'] = float(r['ranking_spearman']) >= thresholds['ranking_spearman_min']
    checks['top3'] = float(r['top3_recall']) >= thresholds['top3_recall_min']
    checks['champion_rank'] = int(r['true_champion_predicted_rank']) <= thresholds['true_champion_predicted_rank_max']
    checks['worst_case'] = float(r['worst_geometry_order_profile_mae']) <= thresholds['worst_geometry_order_profile_mae_max']
    checks['R'] = r['R_mae'] not in ('', 'None', 'nan') and float(r['R_mae']) <= thresholds['R_mae_max']
    checks['T'] = float(r['T_mae']) <= thresholds['T_mae_max']
    checks['energy'] = r['energy_residual_max'] not in ('', 'None', 'nan') and float(r['energy_residual_max']) <= thresholds['energy_residual_max']
    checks['PS'] = ps[model] <= thresholds['P_S_contrast_mae_max']
    reviews.append({'model': model, 'checks': checks, 'all_development_gate_checks': all(checks.values())})
new4_summary = []
for model in sorted({x['model'] for x in new4_rows}):
    z = [x for x in new4_rows if x['model'] == model]; new4_summary.append({'model': model, 'worst_new4_order_profile_mae': max(x['order_profile_mae'] for x in z), 'worst_new4_eta_plus1_mae': max(x['eta_plus1_mae'] for x in z)})
if any(x['all_development_gate_checks'] for x in reviews): decision, reason = 'EXTERNAL_HF_PROMOTION_READY', 'a trainable model passed all frozen development gates'
elif any(x['worst_new4_order_profile_mae'] > 0.05 for x in new4_summary): decision, reason = 'MORE_TARGETED_DEVELOPMENT_HF_REQUIRED', 'new4 retains a measurable error tail and no model passed all frozen gates'
else: decision, reason = 'FORWARD_MODEL_PLATEAU_REASSESSMENT_REQUIRED', 'no model passed all gates and no distinct new4 tail remained'
write_json('m8_promotion_review.json', {'decision': decision, 'rationale': reason, 'incumbent_model': 'LF_global_bias', 'frozen_thresholds': thresholds, 'model_reviews': reviews, 'common_HF16_learning_value': summary, 'new4_summary': new4_summary, 'external_hf_authorized': False, 'solver_calls': 0})
write_json('m8_external_promotion_decision.json', {'final_state': decision, 'decision_rationale': reason, 'external_target_reads': 0, 'external_solver_calls': 0, 'external_registry': 'NP_K6_FORWARD_EXTERNAL_FROZEN_SET_V1', 'future_logical_cases': 24, 'do_not_run_external_automatically': True})
print(json.dumps({'status': 'PASS', 'decision': decision, 'models_reviewed': len(reviews), 'solver_calls': 0}, indent=2))
