from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans']
plt.rcParams['svg.fonttype'] = 'none'
plt.rcParams['pdf.fonttype'] = 42
plt.rcParams.update({'svg.fonttype': 'none', 'pdf.fonttype': 42})
plt.rcParams['axes.spines.top'] = False
plt.rcParams['axes.spines.right'] = False

ROOT = Path(r'D:/project/worktrees/blue_apcd_mdc_hf_surrogate_v2')
OUT = ROOT / 'outputs' / 'mdc_hf_surrogate_v2_standalone_nature_paper_assets_v1' / '20260809T_standalone_nature_assets_631080f'
FINAL = ROOT / 'outputs' / 'mdc_hf_surrogate_v2_m1_final_5seed_ensemble_v1' / '20260804T_final_m1_5seed_067c76b'
COMP = ROOT / 'outputs' / 'mdc_hf_surrogate_v2_doe96_joint_profile_database_v1' / '20260803T_doe96_joint_profile_6b6d7e2'
OOF = ROOT / 'outputs' / 'mdc_hf_surrogate_v2_oof_model_selection_v1' / '20260804T_oof_model_selection_08915e7'
TEST = ROOT / 'outputs' / 'mdc_hf_surrogate_v2_test40_selection_conflict_resolution_v1' / '20260808T_test40_selection_conflict_resolution_489b54e'
GEOM = Path(r'D:/project/worktrees/blue_apcd_mdc_defect_450/datasets/mdc_ml_database_v1/geometry_master.csv')
RUNTIME = ROOT / 'runtime' / 'mdc_hf_surrogate_v2_test40_external_eval_v1' / 'geometry_profiles'
COMMIT = '631080fcb6a5ed8626fba412bb19366b8b291d33'
MODEL_ID = 'MDC_HF_M1_GEOMETRY_CONDITIONED_DIRECT_FINAL_5SEED_V1'
RUN_ID = OUT.name

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def dump(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True), encoding='utf-8')

def csv(path: Path, frame: pd.DataFrame):
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)

def now():
    return datetime.now(timezone.utc).isoformat()

def setup_dirs():
    for name in ['figure_a', 'figure_b', 'figure_c', 'figure_d', 'workflow', 'tables', 'source_data', 'contracts', 'captions', 'reports', 'provenance', 'nature_skill_logs']:
        (OUT / name).mkdir(parents=True, exist_ok=True)

def savefig(base: Path):
    base.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(base.with_suffix('.pdf'), bbox_inches='tight', facecolor='white')
    plt.savefig(base.with_suffix('.svg'), bbox_inches='tight', facecolor='white')
    plt.savefig(base.with_suffix('.png'), dpi=600, bbox_inches='tight', facecolor='white')
    plt.close()

def json_value(obj, *keys, default='NOT_RECORDED_OR_NOT_FROZEN'):
    for key in keys:
        if isinstance(obj, dict) and key in obj:
            return obj[key]
    return default

def load_assets():
    comp_raw = json.loads((COMP / 'profile_compression_crossfit_summary.json').read_text(encoding='utf-8'))
    comp = {row['candidate_id']: row for row in comp_raw} if isinstance(comp_raw, list) else comp_raw
    comp_manifest = json.loads((COMP / 'profile_compression_crossfit_manifest.json').read_text(encoding='utf-8'))
    basis = json.loads((COMP / 'final_profile_basis_manifest.json').read_text(encoding='utf-8'))
    final_manifest = json.loads((FINAL / 'final_m1_ensemble_manifest.json').read_text(encoding='utf-8'))
    final_schema = json.loads((FINAL / 'final_ensemble_output_schema.json').read_text(encoding='utf-8'))
    final_registry = json.loads((FINAL / 'final_ensemble_seed_registry.json').read_text(encoding='utf-8'))
    oof_cmp = json.loads((OOF / 'oof_model_comparison.json').read_text(encoding='utf-8'))
    test_metrics = json.loads((TEST / 'test40_external_evaluation_metrics_v1.json').read_text(encoding='utf-8'))
    test_sha = json.loads((TEST / 'test40_blind_prediction_sha256.json').read_text(encoding='utf-8'))
    geom = pd.read_csv(GEOM)
    doe = pd.read_csv(COMP / 'profile_compatible_geometry_membership.csv')
    cases = pd.read_csv(COMP / 'profile_compatible_case_membership.csv')
    final_hist = pd.read_csv(FINAL / 'final_training_history_summary.csv')
    oof_hist = pd.read_csv(OOF / 'oof_training_history_summary.csv')
    geometry_metrics = pd.DataFrame(test_metrics['geometry_metrics'])
    case_metrics = pd.DataFrame(test_metrics['case_metrics'])
    pred_index = pd.read_parquet(TEST / 'test40_blind_prediction_case_index.parquet')
    pred_profiles = np.load(TEST / 'test40_blind_prediction_profiles.npy', mmap_mode='r')
    return locals()

def write_scope_contracts(a):
    scope = {
        'contract_id': 'MDC_HF_SURROGATE_V2_STANDALONE_NATURE_PAPER_SCOPE_V1',
        'status': 'CLOSED_TEST40_RANKING_SCREENING_ONLY',
        'source_commit': COMMIT,
        'model_id': MODEL_ID,
        'capability': 'RANKING_SCREENING_ONLY',
        'training_assets_frozen': True,
        'test40_metrics_recomputed': False,
        'solver_calls': 0,
        'forbidden': ['FDTD', 'TMM', 'RCWA', 'new neural fit', 'optimizer', 'backward design', 'PCA/scaler refit', 'HF15 values', 'R12 values', 'sealed test', 'active learning'],
        'source_assets': {
            'doe96_cases': 576,
            'test40_cases': 240,
            'test40_geometries': 40,
            'final_seed_registry': a['final_registry'],
            'compression_selection': a['comp_manifest'].get('selected_method', 'PCA32'),
        },
    }
    dump(scope, OUT / 'contracts' / 'standalone_final_scope_registry.json')
    (OUT / 'contracts' / 'standalone_model_card_final.md').write_text(
        '# MDC-HF surrogate v2 standalone model card\n\n'
        f'- Model ID: `{MODEL_ID}`\n- Commit: `{COMMIT}`\n- Capability: ranking/screening only.\n'
        '- Frozen model consumes geometry-conditioned inputs and predicts source-normalized joint spectral-angular profiles and derived power/auxiliary quantities.\n'
        '- It is not a calibrated uncertainty model, not a generative model, and not a replacement for direct FDTD.\n'
        '- Test40 metrics are frozen external screening evidence; no retraining or metric recomputation is part of this asset task.\n', encoding='utf-8')
    cap = pd.DataFrame([
        ['MDC level 0', 'ranking_screening', 'Frozen M1 ensemble', 'Permitted for candidate ranking and descriptive screening', 'No physical validation claim'],
        ['MDC level 1', 'direct_fdtd_confirmation', 'One-way handoff contract', 'Direct FDTD remains required for confirmation', 'Not executed in this task'],
        ['MDC power head', 'source-normalized proxy', 'Frozen output definition', 'Use only with explicit scale caveat', 'Do not treat as native FDTD power'],
    ], columns=['level', 'capability', 'asset', 'allowed_use', 'prohibition'])
    csv(OUT / 'contracts' / 'standalone_capability_matrix.csv', cap)
    handoff = {
        'contract_id': 'MDC_NP_HANDOFF_V1', 'source_commit': COMMIT, 'source_model_id': MODEL_ID,
        'status': 'FROZEN_FOR_HANDOFF', 'one_way': True, 'downstream_required': 'direct FDTD confirmation',
        'interfaces': ['mdc_level0_screening_interface_contract', 'mdc_level1_direct_fdtd_interface_contract'],
        'no_solver_executed': True, 'no_power_head_replacement': True,
    }
    dump(handoff, OUT / 'contracts' / 'mdc_np_handoff_v1.json')
    final_schema = a['final_schema']
    dump({'contract_id': 'MDC_LEVEL0_SCREENING_INTERFACE_CONTRACT_V1', 'model_id': MODEL_ID, 'inputs': final_schema.get('geometry_fields', []), 'outputs': final_schema.get('profile_fields', []) + final_schema.get('power_fields', []), 'capability': 'RANKING_SCREENING_ONLY', 'fresh_load_required': True}, OUT / 'contracts' / 'mdc_level0_screening_interface_contract.json')
    dump({'contract_id': 'MDC_LEVEL1_DIRECT_FDTD_INTERFACE_CONTRACT_V1', 'required_confirmation': 'direct FDTD', 'input_source': 'MDC level 0 ranked candidate', 'solver_run_count': 0, 'status': 'HANDOFF_ONLY'}, OUT / 'contracts' / 'mdc_level1_direct_fdtd_interface_contract.json')
    dump({'contract_id': 'MDC_POWER_HEAD_USAGE_PROHIBITION_V1', 'prohibited_claims': ['native FDTD power equivalence', 'absolute radiometric calibration', 'external physical validation'], 'allowed_claim': 'source-normalized screening proxy with explicit scale caveat'}, OUT / 'contracts' / 'mdc_power_head_usage_prohibition.json')
    coupling = pd.DataFrame([
        ['geometry_hash', 'string', 'Frozen DOE96/Test40 geometry identifier'],
        ['candidate_rank', 'integer', 'MDC ranking output only'],
        ['predicted_joint_profile', 'array[301,2000]', 'Source-normalized surrogate output'],
        ['predicted_relative_upward_power', 'float', 'Proxy; not native FDTD power'],
        ['direct_fdtd_confirmation_required', 'boolean', 'True for publication-grade confirmation'],
    ], columns=['field', 'type', 'definition'])
    csv(OUT / 'contracts' / 'mdc_coupling_source_schema.csv', coupling)
    return scope

def figure_a(a):
    doe, cases = a['doe'], a['cases']
    row = cases.iloc[0]
    raw = np.load(ROOT / row['joint_tensor_path'], mmap_mode='r')
    wl = np.asarray(raw['wavelength_nm']); ang = np.asarray(raw['angle_deg']); z = np.asarray(raw['joint_raw'])
    fig, ax = plt.subplots(1, 3, figsize=(7.1, 2.4), gridspec_kw={'width_ratios': [1, 1, .8]})
    vmax = float(np.nanpercentile(z, 99.8)); vmin = max(0.0, float(np.nanpercentile(z, 1)))
    for axis, data, title in [(ax[0], z, 'Joint spectral–angular profile'), (ax[1], z / max(np.nanmax(z), 1e-30), 'Normalized profile')]:
        im = axis.imshow(data.T, origin='lower', aspect='auto', extent=[wl[0], wl[-1], ang[0], ang[-1]], cmap='magma', interpolation='none', vmin=vmin if title.startswith('Joint') else 0, vmax=vmax if title.startswith('Joint') else 1)
        axis.set_xlabel('Wavelength (nm)'); axis.set_ylabel('Angle (deg)'); axis.set_title(title, fontsize=8)
        fig.colorbar(im, ax=axis, fraction=.046, pad=.04)
    ax[2].plot(wl, np.nanmean(z, axis=1), color='#1f4e79', lw=1.2, label='Spectral marginal')
    ax[2].plot(ang, np.nanmean(z, axis=0) / max(np.nanmax(np.nanmean(z, axis=0)), 1e-30), color='#c44e52', lw=1.2, label='Angular marginal (scaled)')
    ax[2].set_xlabel('Grid coordinate'); ax[2].set_ylabel('Marginal (display scale)'); ax[2].set_title('Marginals', fontsize=8); ax[2].legend(fontsize=6, frameon=False)
    fig.suptitle('(a) Frozen DOE96 profile representation', x=.02, ha='left', fontsize=10, fontweight='bold')
    savefig(OUT / 'figure_a' / 'figure_a_frozen_profile_representation')
    csv(OUT / 'source_data' / 'figure_a_representative_joint_profile.csv', pd.DataFrame({'wavelength_nm': np.repeat(wl, len(ang)), 'angle_deg': np.tile(ang, len(wl)), 'joint_raw': z.reshape(-1)}))
    dump({'figure_id': 'A', 'claim': 'Frozen DOE96 joint profile representation and marginals', 'source_commit': COMMIT, 'source_case_hash': str(row['case_hash']), 'source_tensor_sha256': str(row['joint_tensor_sha256']), 'display_transform': 'raw and max-normalized only; no smoothing'}, OUT / 'provenance' / 'figure_a_provenance.json')

def figure_b(a):
    comp = a['comp']; methods = ['NMF16', 'NMF32', 'PCA16', 'PCA32']
    js = [comp[m]['mean_js_divergence'] for m in methods]; l1 = [comp[m]['mean_joint_weighted_l1'] for m in methods]
    fig, ax = plt.subplots(1, 2, figsize=(6.7, 2.7))
    colors = ['#8da0cb', '#66c2a5', '#fc8d62', '#e78ac3']
    ax[0].bar(methods, js, color=colors); ax[0].set_ylabel('Mean joint JS divergence'); ax[0].set_title('Cross-fit fidelity', fontsize=8); ax[0].tick_params(axis='x', rotation=25)
    ax[1].bar(methods, l1, color=colors); ax[1].set_ylabel('Mean joint weighted L1'); ax[1].set_title('Held-out profile error', fontsize=8); ax[1].tick_params(axis='x', rotation=25)
    fig.suptitle('(b) Pre-registered profile-compression selection', x=.02, ha='left', fontsize=10, fontweight='bold')
    savefig(OUT / 'figure_b' / 'figure_b_compression_selection')
    csv(OUT / 'source_data' / 'figure_b_compression_crossfit.csv', pd.DataFrame({'method': methods, 'mean_js_divergence': js, 'mean_joint_weighted_l1': l1, 'selected': [m == 'PCA32' for m in methods]}))
    dump({'figure_id': 'B', 'claim': 'PCA32 is selected from frozen DOE96 held-out cross-fit comparisons', 'source_commit': COMMIT, 'selection_manifest': str(COMP / 'profile_compression_crossfit_manifest.json'), 'selection_sha256': sha256(COMP / 'profile_compression_crossfit_manifest.json'), 'no_refit': True}, OUT / 'provenance' / 'figure_b_provenance.json')

def figure_c(a):
    metrics = a['geometry_metrics'].copy().sort_values(['joint_js', 'geometry_hash'], kind='mergesort').reset_index(drop=True)
    metrics['rank'] = np.arange(1, len(metrics) + 1)
    picks = metrics.iloc[[0, len(metrics)//2, len(metrics)-1]].copy(); picks['selection'] = ['best', 'median', 'worst']
    picks.to_csv(OUT / 'source_data' / 'test40_representative_geometry_selection.csv', index=False)
    pred_index, pred = a['pred_index'], a['pred_profiles']
    fig, ax = plt.subplots(3, 3, figsize=(7.1, 7.1), gridspec_kw={'wspace': .22, 'hspace': .35})
    for i, (_, r) in enumerate(picks.iterrows()):
        gh = str(r.geometry_hash); truth_path = RUNTIME / f'{gh}__geometry_profile.npz'; truth = np.load(truth_path)
        rows = pred_index[pred_index.geometry_hash.astype(str) == gh]
        p = np.asarray(pred[rows.profile_row.astype(int)]).mean(axis=0)
        t = np.asarray(truth['normalized_joint']); p = p / max(np.nanmax(p), 1e-30)
        lo, hi = 0, float(max(np.nanpercentile(t, 99.5), np.nanpercentile(p, 99.5)))
        for axis, data, title in [(ax[i, 0], t, 'Truth'), (ax[i, 1], p, 'M1 prediction'), (ax[i, 2], np.abs(t-p), 'Absolute error')]:
            im = axis.imshow(data.T, origin='lower', aspect='auto', cmap='viridis' if title == 'Absolute error' else 'magma', interpolation='none', vmin=0 if title != 'M1 prediction' else 0, vmax=hi if title != 'Absolute error' else max(hi, float(np.nanpercentile(np.abs(t-p), 99))))
            axis.set_xticks([]); axis.set_yticks([]); axis.set_title(f'{r.selection}: {title}', fontsize=7)
            if i == 2: axis.set_xlabel('Wavelength/angle grid', fontsize=6)
            fig.colorbar(im, ax=axis, fraction=.046, pad=.02)
    fig.suptitle('(c) Test40 representative joint profiles', x=.02, ha='left', fontsize=10, fontweight='bold')
    savefig(OUT / 'figure_c' / 'figure_c_test40_representative_profiles')
    dump({'figure_id': 'C', 'claim': 'Representative best/median/worst Test40 profile comparisons under frozen joint-JS ranking', 'selection_rule': 'joint_js ascending then geometry_hash ascending; ranks 1,20,40', 'source_commit': COMMIT, 'test40_metric_sha256': sha256(TEST / 'test40_external_evaluation_metrics_v1.json'), 'display_only': True}, OUT / 'provenance' / 'figure_c_provenance.json')

def figure_d(a):
    gm, cm = a['geometry_metrics'], a['case_metrics']
    fig, ax = plt.subplots(1, 3, figsize=(7.1, 2.55))
    x = np.log10(np.maximum(pd.to_numeric(cm['label_power'], errors='coerce'), 1e-12)); y = np.log10(np.maximum(pd.to_numeric(cm['pred_power'], errors='coerce'), 1e-12))
    ax[0].scatter(x, y, s=8, alpha=.55, color='#4c78a8'); ax[0].set_xlabel('log10 raw FDTD native upward power'); ax[0].set_ylabel('log10 M1 source-normalized proxy'); ax[0].set_title('Power scale comparison', fontsize=8)
    r1 = pd.Series(pd.to_numeric(gm['label_power'], errors='coerce')).rank().to_numpy(); r2 = pd.Series(pd.to_numeric(gm['pred_power'], errors='coerce')).rank().to_numpy(); ax[1].scatter(r1, r2, s=12, color='#59a14f'); ax[1].set_xlabel('Native FDTD geometry rank'); ax[1].set_ylabel('M1 proxy geometry rank'); ax[1].set_title('Geometry ranking', fontsize=8)
    ax[2].hist(pd.to_numeric(cm['joint_js'], errors='coerce'), bins=16, color='#f28e2b', alpha=.85); ax[2].set_xlabel('Case joint JS divergence'); ax[2].set_ylabel('Count'); ax[2].set_title('Test40 error distribution', fontsize=8)
    fig.subplots_adjust(bottom=.27, top=.78, wspace=.35)
    fig.text(.5, .045, 'POWER DEFINITIONS / SCALES ARE NOT QUANTITATIVELY ALIGNED', ha='center', fontsize=7, color='#a33')
    for axis in ax:
        axis.xaxis.label.set_size(8)
        axis.yaxis.label.set_size(8)
        axis.tick_params(labelsize=7)
    fig.suptitle('(d) Frozen Test40 ranking-screening outcomes', x=.02, ha='left', fontsize=10, fontweight='bold')
    savefig(OUT / 'figure_d' / 'figure_d_test40_outcomes')
    csv(OUT / 'source_data' / 'figure_d_test40_power_and_error.csv', cm[['test_case_uid', 'geometry_hash', 'label_power', 'pred_power', 'joint_js']])
    csv(OUT / 'source_data' / 'figure_d_test40_geometry_ranks.csv', gm[['geometry_hash', 'label_power', 'pred_power', 'joint_js']])
    dump({'figure_id': 'D', 'claim': 'Test40 supports ranking/screening-only use with non-aligned power scales', 'source_commit': COMMIT, 'frozen_geometry_power_rank_spearman': a['test_metrics']['geometry_power_rank_spearman'], 'frozen_case_power_rank_spearman': a['test_metrics']['case_power_rank_spearman'], 'display_transform': 'log10 floor 1e-12 for visualization only', 'no_identity_line': True}, OUT / 'provenance' / 'figure_d_provenance.json')

def figure_workflow(a):
    fig, ax = plt.subplots(figsize=(7.1, 1.9)); ax.axis('off')
    boxes = [('Frozen DOE96\nprofiles', .08), ('M1 geometry-conditioned\n5-seed ensemble', .35), ('Test40 ranking\nscreening', .62), ('Direct FDTD\nconfirmation', .88)]
    for i, (label, x) in enumerate(boxes):
        ax.text(x, .5, label, ha='center', va='center', fontsize=9, bbox=dict(boxstyle='round,pad=.6', fc='#eaf2f8' if i < 3 else '#fce4d6', ec='#4c78a8' if i < 3 else '#c55a11', lw=1.2))
        if i < len(boxes)-1: ax.annotate('', xy=(boxes[i+1][1]-.10, .5), xytext=(x+.10, .5), arrowprops=dict(arrowstyle='->', lw=1.2, color='#555'))
    ax.text(.5, .12, 'One-way MDC→NP handoff; no solver or external-label evaluation in this asset task', ha='center', fontsize=8, color='#555')
    ax.set_title('(workflow) MDC-to-NP coupling handoff', loc='left', fontsize=10, fontweight='bold')
    savefig(OUT / 'workflow' / 'mdc_to_np_workflow')
    dump({'figure_id': 'workflow', 'claim': 'One-way handoff from frozen screening outputs to required direct FDTD confirmation', 'source_commit': COMMIT, 'solver_calls': 0}, OUT / 'provenance' / 'workflow_provenance.json')

def write_tables(a):
    comp = a['comp']; tm = a['test_metrics']; oof = a['oof_cmp']
    table_a = pd.DataFrame([
        ['M1', 'geometry-conditioned direct', 1.0, oof['scores']['M1'], oof['ratios_to_M1']['M1'], 'winner'],
        ['M2', 'alternative frozen architecture', 2.0, oof['scores']['M2'], oof['ratios_to_M1']['M2'], 'not selected'],
        ['M3', 'alternative frozen architecture', 3.0, oof['scores']['M3'], oof['ratios_to_M1']['M3'], 'not selected'],
    ], columns=['architecture', 'description', 'rank', 'oof_score', 'ratio_to_M1', 'selection'])
    csv(OUT / 'tables' / 'table_a_oof_model_comparison.csv', table_a)
    case = tm['case_metrics_summary']; geo = tm['geometry_metrics_summary']
    rows = [
        ['Case', 240, case.get('joint_js', {}).get('mean', 'NOT_RECORDED_OR_NOT_FROZEN'), case.get('joint_weighted_l1', {}).get('mean', 'NOT_RECORDED_OR_NOT_FROZEN'), case.get('spectral_cdf_l1', {}).get('mean', 'NOT_RECORDED_OR_NOT_FROZEN'), case.get('angular_cdf_l1', {}).get('mean', 'NOT_RECORDED_OR_NOT_FROZEN'), tm.get('case_power_rank_spearman', 'NOT_RECORDED_OR_NOT_FROZEN')],
        ['Geometry', 40, geo.get('joint_js', {}).get('mean', 'NOT_RECORDED_OR_NOT_FROZEN'), geo.get('joint_weighted_l1', {}).get('mean', 'NOT_RECORDED_OR_NOT_FROZEN'), geo.get('spectral_cdf_l1', {}).get('mean', 'NOT_RECORDED_OR_NOT_FROZEN'), geo.get('angular_cdf_l1', {}).get('mean', 'NOT_RECORDED_OR_NOT_FROZEN'), tm.get('geometry_power_rank_spearman', 'NOT_RECORDED_OR_NOT_FROZEN')],
    ]
    csv(OUT / 'tables' / 'table_b_test40_frozen_metrics.csv', pd.DataFrame(rows, columns=['aggregation', 'n', 'joint_js_mean', 'joint_weighted_l1_mean', 'spectral_cdf_l1_mean', 'angular_cdf_l1_mean', 'power_rank_spearman']))
    csv(OUT / 'tables' / 'table_b_test40_frozen_metrics_full.csv', pd.DataFrame([
        ['case_log_power_mae', tm['case_log_power_mae']], ['case_log_power_rmse', tm['case_log_power_rmse']], ['case_log_power_bias', tm['case_log_power_bias']], ['case_power_rank_spearman', tm['case_power_rank_spearman']], ['geometry_power_rank_spearman', tm['geometry_power_rank_spearman']], ['case_count', 240], ['geometry_count', 40]
    ], columns=['metric', 'value']))
    csv(OUT / 'source_data' / 'table_a_compression_candidates.csv', pd.DataFrame({'method': ['NMF16', 'NMF32', 'PCA16', 'PCA32'], 'mean_js_divergence': [comp[m]['mean_js_divergence'] for m in ['NMF16','NMF32','PCA16','PCA32']], 'mean_joint_weighted_l1': [comp[m]['mean_joint_weighted_l1'] for m in ['NMF16','NMF32','PCA16','PCA32']]}))

def write_captions_reports(a):
    en = {
        'A': 'Figure A | Frozen DOE96 joint spectral–angular profile representation. Raw and max-normalized views are shown with their spectral and angular marginals. No smoothing or interpolation was applied.',
        'B': 'Figure B | Pre-registered profile-compression selection. PCA32 was selected from held-out DOE96 cross-fit comparisons using joint JS divergence and joint weighted L1 error; no Test40 or sealed data entered selection.',
        'C': 'Figure C | Representative Test40 joint profiles. Best, median and worst geometries are selected by frozen geometry-level joint JS rank (ascending JS, then geometry hash). Heatmaps are display transformations of frozen prediction and truth artifacts.',
        'D': 'Figure D | Frozen Test40 ranking-screening outcomes. Native FDTD power and M1 source-normalized proxy power are plotted on separate, explicitly non-aligned scales. The model is not presented as an absolute power-calibrated predictor.',
        'workflow': 'Workflow | MDC-to-NP handoff. Frozen MDC screening outputs provide a one-way ranking interface; direct FDTD remains required for confirmation.',
    }
    zh = {
        'A': '图A｜冻结 DOE96 联合光谱–角度剖面表示。展示原始与最大值归一化视图及其边缘分布；未进行平滑或插值。',
        'B': '图B｜预注册的剖面压缩选择。依据 DOE96 留出交叉拟合的联合 JS 散度和联合加权 L1 误差选择 PCA32；Test40 与 sealed 数据未参与选择。',
        'C': '图C｜Test40 代表性联合剖面。按冻结的几何级联合 JS 排名（JS 升序、geometry hash 次序）选取最佳、中位和最差几何；热图仅是冻结预测与真值的显示变换。',
        'D': '图D｜冻结 Test40 排名筛选结果。原生 FDTD 功率与 M1 源归一化代理功率使用明确不对齐的独立尺度展示；模型不被表述为绝对功率标定预测器。',
        'workflow': '工作流｜MDC 到 NP 的交接。冻结的 MDC 筛选输出只提供单向排序接口；确认仍需直接 FDTD。',
    }
    (OUT / 'captions' / 'captions_en_v1.md').write_text('\n'.join(f'### {k}\n\n{v}\n' for k, v in en.items()), encoding='utf-8')
    (OUT / 'captions' / 'captions_zh_v1.md').write_text('\n'.join(f'### {k}\n\n{v}\n' for k, v in zh.items()), encoding='utf-8')
    en_report = '''# Standalone MDC results and discussion\n\nThe frozen M1 geometry-conditioned ensemble is useful as a ranking and screening instrument over the defined DOE96/Test40 interface. OOF comparison selected M1 before external Test40 inspection, while PCA32 was selected by held-out DOE96 cross-fit profile fidelity. On Test40, the frozen metrics quantify profile discrepancy and rank behavior; they do not establish absolute physical power calibration.\n\nThe MDC-to-NP coupling is therefore one-way: the surrogate identifies candidates and exposes a compact source-normalized profile interface, after which direct FDTD confirmation is required. The scope deliberately excludes HF15 labels, sealed tests, solver execution, retraining, and any reinterpretation of the frozen power head.\n'''
    zh_report = '''# 独立 MDC 结果与讨论\n\n冻结的 M1 几何条件集成模型可在定义好的 DOE96/Test40 接口上用于排序与筛选。OOF 比较在查看外部 Test40 之前选择 M1；PCA32 则由 DOE96 留出交叉拟合的剖面保真度选择。Test40 冻结指标用于量化剖面差异和排序行为，不构成绝对物理功率标定证据。\n\n因此 MDC 到 NP 采用单向交接：代理模型筛选候选并提供源归一化剖面接口，随后必须使用直接 FDTD 进行确认。本资产任务明确排除 HF15 标签、sealed test、solver 执行、重新训练，以及对冻结功率头的重新解释。\n'''
    (OUT / 'reports' / 'mdc_standalone_results_discussion_nature_en_v1.md').write_text(en_report, encoding='utf-8')
    (OUT / 'reports' / 'mdc_standalone_results_discussion_zh_v1.md').write_text(zh_report, encoding='utf-8')
    (OUT / 'reports' / 'mdc_standalone_paper_narrative_v1.md').write_text('# MDC standalone paper narrative\n\nThis package provides the frozen model-comparison, profile-compression, Test40 screening, and one-way MDC-to-NP handoff assets required for a standalone Nature-style results package. Claims remain bounded by the ranking-screening-only capability contract.\n', encoding='utf-8')

def write_provenance_and_logs(a):
    refs = [FINAL / 'final_m1_ensemble_manifest.json', FINAL / 'final_ensemble_output_schema.json', FINAL / 'final_training_membership_audit.json', FINAL / 'final_ensemble_safety_audit.json', COMP / 'profile_compression_crossfit_summary.json', COMP / 'profile_compression_crossfit_manifest.json', OOF / 'oof_model_comparison.json', TEST / 'test40_external_evaluation_metrics_v1.json', TEST / 'test40_blind_prediction_sha256.json']
    entries = []
    for p in refs:
        entries.append({'path': str(p), 'sha256': sha256(p), 'status': 'frozen_reference'})
    dump({'source_commit': COMMIT, 'generated_at': now(), 'references': entries, 'formal_reads': {'hf15_labels': 0, 'hf15_diagnostics': 0, 'sealed_test': 0, 'solver': 0}}, OUT / 'provenance' / 'source_artifact_registry.json')
    (OUT / 'nature_skill_logs' / 'nature_figure_skill_note.md').write_text('Python backend selected by task contract. Figures A–D and workflow use fixed Arial-compatible sans-serif settings, no smoothing/interpolation, explicit source-data CSVs, and frozen artifact provenance.\n', encoding='utf-8')
    (OUT / 'nature_skill_logs' / 'nature_writing_skill_note.md').write_text('Nature-writing axes: manuscript / algorithmic / experiments+discussion+method+conclusion / English / generic Nature-style. Claims are bounded to ranking-screening-only capability.\n', encoding='utf-8')
    dump({'source_commit': COMMIT, 'generator': 'generate_mdc_standalone_nature_assets_v1.py', 'generated_at': now(), 'python': platform.python_version()}, OUT / 'nature_skill_logs' / 'generation_log.json')

def main():
    setup_dirs(); a = load_assets(); write_scope_contracts(a); figure_a(a); figure_b(a); figure_c(a); figure_d(a); figure_workflow(a); write_tables(a); write_captions_reports(a); write_provenance_and_logs(a)
    print(json.dumps({'output_root': str(OUT), 'status': 'GENERATED', 'figures': ['A','B','C','D','workflow'], 'solver_calls': 0, 'hf15_formal_label_reads': 0}, indent=2))

if __name__ == '__main__':
    main()
