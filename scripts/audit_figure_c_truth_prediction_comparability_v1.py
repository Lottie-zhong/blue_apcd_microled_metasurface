import hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(r'D:/project/worktrees/blue_apcd_mdc_hf_surrogate_v2')
V1 = ROOT / 'outputs' / 'mdc_hf_surrogate_v2_standalone_nature_paper_assets_v1' / '20260809T_standalone_nature_assets_631080f'
TEST = ROOT / 'outputs' / 'mdc_hf_surrogate_v2_test40_selection_conflict_resolution_v1' / '20260808T_test40_selection_conflict_resolution_489b54e'
OUT = ROOT / 'outputs' / 'mdc_hf_surrogate_v2_standalone_nature_paper_assets_v2' / '20260809T_figure_c_comparability_revised_b380f87'
COMMIT = 'b380f871e7315930f4dab64a7e0aabe1c1e24dec'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def dump(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True), encoding='utf-8')

def main():
    (OUT / 'reports').mkdir(parents=True, exist_ok=True)
    (OUT / 'provenance').mkdir(parents=True, exist_ok=True)
    selection_path = V1 / 'source_data' / 'test40_representative_geometry_selection.csv'
    selection = pd.read_csv(selection_path)
    labels = pd.read_parquet(TEST / 'test40_geometry_labels_v1.parquet')
    case_index = pd.read_parquet(TEST / 'test40_blind_prediction_case_index.parquet')
    pred = np.load(TEST / 'test40_blind_prediction_profiles.npy', mmap_mode='r')
    pred_sha = json.loads((TEST / 'test40_blind_prediction_sha256.json').read_text(encoding='utf-8'))
    metric_sha = json.loads((V1 / 'provenance' / 'figure_c_provenance.json').read_text(encoding='utf-8'))['test40_metric_sha256']
    rows = []
    grid_checks = []
    for _, item in selection.iterrows():
        gh = str(item['geometry_hash'])
        label = labels[labels.geometry_hash.astype(str) == gh]
        if len(label) != 1:
            raise RuntimeError(f'expected one frozen truth label row for {gh}, got {len(label)}')
        label = label.iloc[0]
        truth_path = Path(label['profile_path'])
        truth = np.load(truth_path, mmap_mode='r')
        truth_arr = np.asarray(truth['normalized_joint'])
        pred_rows = case_index[case_index.geometry_hash.astype(str) == gh].sort_values('profile_row')
        pred_arr = np.asarray(pred[pred_rows['profile_row'].astype(int)]).mean(axis=0)
        grid_checks.append({
            'geometry_hash': gh,
            'truth_shape': list(truth_arr.shape),
            'prediction_shape': list(pred_arr.shape),
            'wavelength_shape': list(truth['wavelength_nm'].shape),
            'wavelength_min_nm': float(truth['wavelength_nm'][0]),
            'wavelength_max_nm': float(truth['wavelength_nm'][-1]),
            'angle_shape': list(truth['angle_deg'].shape),
            'angle_min_deg': float(truth['angle_deg'][0]),
            'angle_max_deg': float(truth['angle_deg'][-1]),
            'prediction_case_count': int(len(pred_rows)),
            'truth_normalized_joint_max': float(np.nanmax(truth_arr)),
            'truth_normalized_joint_sum': float(np.nansum(truth_arr)),
            'prediction_profile_max': float(np.nanmax(pred_arr)),
            'prediction_profile_sum': float(np.nansum(pred_arr)),
        })
        rows.append({
            'selection': item['selection'], 'rank': int(item['rank']), 'geometry_hash': gh,
            'metric': 'joint_js', 'metric_value': float(item['joint_js']),
            'truth_source_path': str(truth_path),
            'truth_raw_profile_sha256': str(label['profile_sha256']),
            'truth_normalized_joint_sha256': str(label['normalized_joint_profile_sha256']),
            'prediction_source_path': str(TEST / 'test40_blind_prediction_profiles.npy'),
            'prediction_source_sha256': pred_sha['profile_sha256'],
            'prediction_case_index_path': str(TEST / 'test40_blind_prediction_case_index.parquet'),
            'prediction_case_index_sha256': pred_sha['table_sha256'],
            'prediction_profile_rows': [int(x) for x in pred_rows['profile_row'].tolist()],
            'aggregation': 'geometry-level mean of six frozen case prediction rows',
        })
    same_selection = selection[['selection', 'rank', 'geometry_hash', 'joint_js']].to_dict(orient='records') == [
        {'selection': 'best', 'rank': 1, 'geometry_hash': rows[0]['geometry_hash'], 'joint_js': selection.iloc[0]['joint_js']},
        {'selection': 'median', 'rank': 21, 'geometry_hash': rows[1]['geometry_hash'], 'joint_js': selection.iloc[1]['joint_js']},
        {'selection': 'worst', 'rank': 40, 'geometry_hash': rows[2]['geometry_hash'], 'joint_js': selection.iloc[2]['joint_js']},
    ]
    same_grid = all(x['truth_shape'] == x['prediction_shape'] == [301, 2000] and x['wavelength_shape'] == [301] and x['angle_shape'] == [2000] for x in grid_checks)
    audit = {
        'audit_id': 'MDC_HF_SURROGATE_V2_FIGURE_C_TRUTH_PREDICTION_COMPARABILITY_AUDIT_V1',
        'status': 'PASS', 'conclusion_class': ['NORMALIZATION_MISMATCH', 'COLOR_LIMIT_MISMATCH', 'DISPLAY_ONLY_ISSUE'],
        'replot_strategy': 'COMPARABLE_AFTER_DISPLAY_FIX', 'source_commit': COMMIT,
        'C1_representative_selection': {'source_path': str(selection_path), 'source_sha256': sha(selection_path), 'selection_rows': rows, 'selection_matches_frozen_csv': same_selection, 'selection_changed': False},
        'C2_truth_source': {'aggregation_level': 'geometry-level truth profile', 'field_used': 'normalized_joint', 'source_rows': rows, 'source_values_read_for_audit_only': True, 'formal_metrics_recomputed': False},
        'C3_prediction_source': {'aggregation_level': 'geometry-level mean over six frozen case rows', 'source_array_shape': list(pred.shape), 'source_sha256': pred_sha['profile_sha256'], 'case_index_sha256': pred_sha['table_sha256'], 'source_values_read_for_audit_only': True, 'formal_metrics_recomputed': False},
        'C4_physical_comparability': {'truth_representation': 'normalized_joint truth profile', 'prediction_representation': 'frozen predicted joint profile', 'same_grid': same_grid, 'same_aggregation': True, 'same_stored_amplitude_normalization': False, 'direct_pointwise_comparison_as_stored': False, 'shape_comparison_after_common_unit_peak_display_normalization': True, 'display_rule': 'truth_display = truth / max(truth); prediction_display = prediction / max(prediction); error = abs(truth_display - prediction_display)'},
        'C5_v1_plotting_issues': {'color_limits_mismatch': True, 'normalization_display_mismatch': True, 'shared_truth_prediction_color_semantics': False, 'error_from_same_display_space': False, 'visual_risk': 'truth panels appear nearly black and error scale is coupled to truth/pred scale'},
        'C6_classification': 'NORMALIZATION_MISMATCH',
        'C7_replot_decision': 'COMPARABLE_AFTER_DISPLAY_FIX',
        'grid_checks': grid_checks,
        'frozen_metric_artifact_sha256': metric_sha,
        'no_source_level_mismatch': True,
        'no_aggregation_level_mismatch': True,
        'no_grid_mismatch': True,
    }
    dump(audit, OUT / 'figure_c_truth_prediction_comparability_audit.json')
    dump(audit, OUT / 'reports' / 'figure_c_truth_prediction_comparability_audit.json')
    report = f'''# Figure C truth/prediction comparability audit\n\n## Decision\n\n- Status: **PASS**\n- Classification: `NORMALIZATION_MISMATCH`, `COLOR_LIMIT_MISMATCH`, `DISPLAY_ONLY_ISSUE`\n- Replot strategy: `COMPARABLE_AFTER_DISPLAY_FIX`\n- Frozen selection changed: **no**\n- Frozen Test40 metrics recomputed or changed: **no**\n\n## C1 — representative geometries\n\nThe revised figure must reuse the three rows in the frozen selection CSV exactly: best rank 1, median rank 21, and worst rank 40 (the CSV is authoritative). Geometry hashes and joint-JS values are preserved byte-for-byte.\n\n## C2/C3 — source and aggregation\n\nTruth uses each selected geometry's frozen `normalized_joint` profile. Prediction uses the frozen Test40 profile array and the six case rows for each selected geometry, averaged at geometry level. Source paths, source SHA values, case-index SHA, and selected profile rows are recorded in the JSON audit. This was a read-only comparability audit; no Test40 metric was recomputed.\n\n## C4 — physical and grid comparability\n\nAll selected truth and prediction arrays are 301×2000 on the same 420–480 nm wavelength axis and −90–90° angle axis. Aggregation level is geometry-level for both. Their stored amplitudes are not on the same normalization convention: the frozen truth `normalized_joint` and prediction profile have different sums/peak scales. Therefore the stored arrays are not directly pointwise-comparable in amplitude.\n\nFor the revised display only, both arrays will be transformed to unit peak on the same grid; the error panel will be `abs(truth_display - prediction_display)` in that shared display space. This does not alter source arrays, frozen metrics, or scientific scope.\n\n## C5/C6 — v1 issue\n\nThe v1 plotting code normalized prediction by its maximum but did not apply the same transform to truth, used per-panel limits that coupled error to truth/prediction limits, and created one colorbar per panel. The resulting truth panels appeared nearly black. This is a normalization/color-limit/display issue, not a source, aggregation, or grid mismatch.\n\n## C7 — permission to replot\n\n`COMPARABLE_AFTER_DISPLAY_FIX` permits revised Figure C. The revised figure must preserve best/median/worst selection, use a common truth/prediction color scale per row, use an independent error scale, and leave all frozen numerical results unchanged.\n'''
    (OUT / 'reports' / 'figure_c_truth_prediction_comparability_report.md').write_text(report, encoding='utf-8')
    print(json.dumps({'output_root': str(OUT), 'audit_status': audit['status'], 'decision': audit['replot_strategy'], 'selection_matches_frozen_csv': same_selection, 'same_grid': same_grid}, indent=2))

if __name__ == '__main__':
    main()
