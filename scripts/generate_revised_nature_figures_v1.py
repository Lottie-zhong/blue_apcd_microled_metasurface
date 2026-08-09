from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
import numpy as np
import pandas as pd

mpl.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'DejaVu Sans', 'Liberation Sans'],
    'font.size': 7,
    'svg.fonttype': 'none',
    'pdf.fonttype': 42,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.linewidth': 0.7,
    'legend.frameon': False,
})

ROOT = Path(r'D:/project/worktrees/blue_apcd_mdc_hf_surrogate_v2')
V1 = ROOT / 'outputs' / 'mdc_hf_surrogate_v2_standalone_nature_paper_assets_v1' / '20260809T_standalone_nature_assets_631080f'
TEST = ROOT / 'outputs' / 'mdc_hf_surrogate_v2_test40_selection_conflict_resolution_v1' / '20260808T_test40_selection_conflict_resolution_489b54e'
OUT = ROOT / 'outputs' / 'mdc_hf_surrogate_v2_standalone_nature_paper_assets_v2' / '20260809T_figure_c_comparability_revised_b380f87'
COMMIT = 'b380f871e7315930f4dab64a7e0aabe1c1e24dec'

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def dump(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True), encoding='utf-8')

def save(base: Path, fig):
    base.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(base.with_suffix('.pdf'), bbox_inches='tight', facecolor='white')
    fig.savefig(base.with_suffix('.svg'), bbox_inches='tight', facecolor='white')
    fig.savefig(base.with_suffix('.png'), dpi=600, bbox_inches='tight', facecolor='white')
    plt.close(fig)

def load_inputs():
    audit = json.loads((OUT / 'figure_c_truth_prediction_comparability_audit.json').read_text(encoding='utf-8')) if (OUT / 'figure_c_truth_prediction_comparability_audit.json').exists() else json.loads((OUT / 'reports' / 'figure_c_truth_prediction_comparability_audit.json').read_text(encoding='utf-8'))
    sel = pd.read_csv(V1 / 'source_data' / 'test40_representative_geometry_selection.csv')
    a = pd.read_csv(V1 / 'source_data' / 'figure_a_representative_joint_profile.csv')
    b = pd.read_csv(V1 / 'source_data' / 'figure_b_compression_crossfit.csv')
    d_power = pd.read_csv(V1 / 'source_data' / 'figure_d_test40_power_and_error.csv')
    d_rank = pd.read_csv(V1 / 'source_data' / 'figure_d_test40_geometry_ranks.csv')
    table_b = pd.read_csv(V1 / 'tables' / 'table_b_test40_frozen_metrics.csv')
    pred = np.load(TEST / 'test40_blind_prediction_profiles.npy', mmap_mode='r')
    idx = pd.read_parquet(TEST / 'test40_blind_prediction_case_index.parquet')
    return locals()

def figure_a(a):
    wl = np.sort(a.wavelength_nm.unique()); ang = np.sort(a.angle_deg.unique())
    z = a.pivot(index='wavelength_nm', columns='angle_deg', values='joint_raw').loc[wl, ang].to_numpy()
    z_peak = z / max(float(np.nanmax(z)), 1e-30)
    fig = plt.figure(figsize=(7.35, 4.15), facecolor='white')
    gs = fig.add_gridspec(2, 3, width_ratios=[1.14, 1.14, .92], height_ratios=[1, 1], wspace=.48, hspace=.50)
    ax_raw = fig.add_subplot(gs[:, 0]); ax_peak = fig.add_subplot(gs[:, 1]); ax_spec = fig.add_subplot(gs[0, 2]); ax_ang = fig.add_subplot(gs[1, 2])
    raw_hi = float(np.nanpercentile(z, 99.8)); raw_lo = max(0.0, float(np.nanpercentile(z, 1)))
    im_raw = ax_raw.imshow(z.T, origin='lower', aspect='auto', extent=[wl[0], wl[-1], ang[0], ang[-1]], cmap='magma', interpolation='none', vmin=raw_lo, vmax=raw_hi)
    im_peak = ax_peak.imshow(z_peak.T, origin='lower', aspect='auto', extent=[wl[0], wl[-1], ang[0], ang[-1]], cmap='magma', interpolation='none', vmin=0, vmax=1)
    ax_raw.set_title('Raw joint profile', fontsize=8, pad=8); ax_peak.set_title('Unit-peak display', fontsize=8, pad=8)
    for ax in [ax_raw, ax_peak]:
        ax.set_xlabel('Wavelength (nm)', fontsize=7); ax.set_ylabel('Angle (deg)', fontsize=7); ax.tick_params(labelsize=6)
    c1 = fig.colorbar(im_raw, ax=ax_raw, fraction=.040, pad=.035); c1.set_label('Raw profile', fontsize=6); c1.ax.tick_params(labelsize=6)
    c2 = fig.colorbar(im_peak, ax=ax_peak, fraction=.040, pad=.035); c2.set_label('Unit peak', fontsize=6); c2.ax.tick_params(labelsize=6)
    spec = z.mean(axis=1); ang_m = z.mean(axis=0)
    ax_spec.plot(wl, spec, color='#1f4e79', lw=1.15); ax_spec.set_title('Spectral marginal', fontsize=8, pad=6); ax_spec.set_xlabel('Wavelength (nm)', fontsize=7); ax_spec.set_ylabel('Mean profile', fontsize=7); ax_spec.tick_params(labelsize=6)
    ax_ang.plot(ang, ang_m, color='#c44e52', lw=1.15); ax_ang.set_title('Angular marginal', fontsize=8, pad=6); ax_ang.set_xlabel('Angle (deg)', fontsize=7); ax_ang.set_ylabel('Mean profile', fontsize=7); ax_ang.tick_params(labelsize=6)
    fig.suptitle('(a) Frozen DOE96 joint spectral–angular profile', x=.03, y=.995, ha='left', va='top', fontsize=10, fontweight='bold')
    fig.subplots_adjust(top=.87)
    save(OUT / 'figures' / 'figure_a_revised', fig)
    dump({'figure_id': 'A', 'source_commit': COMMIT, 'source_csv': str(V1 / 'source_data' / 'figure_a_representative_joint_profile.csv'), 'source_csv_sha256': sha(V1 / 'source_data' / 'figure_a_representative_joint_profile.csv'), 'original_tensor_sha256': json.loads((V1 / 'provenance' / 'figure_a_provenance.json').read_text())['source_tensor_sha256'], 'display_changes': ['explicit raw and unit-peak heatmap panels', 'spectral and angular marginals use their native axes', 'separate labelled colorbars', 'no smoothing/interpolation'], 'scientific_values_changed': False}, OUT / 'provenance' / 'figure_a_revised_provenance.json')

def figure_b(b):
    methods = b['method'].tolist(); js = b['mean_js_divergence'].to_numpy(); l1 = b['mean_joint_weighted_l1'].to_numpy()
    fig, ax = plt.subplots(1, 2, figsize=(7.35, 3.05), facecolor='white')
    colors = ['#8da0cb', '#66c2a5', '#fc8d62', '#e78ac3']
    for axis, vals, ylabel, title in [(ax[0], js, 'Mean joint JS divergence', 'Held-out profile fidelity'), (ax[1], l1, 'Mean joint weighted L1', 'Selection metric')]:
        bars = axis.bar(methods, vals, color=colors, width=.62)
        axis.set_ylabel(ylabel, fontsize=8); axis.set_title(title, fontsize=8, pad=9); axis.tick_params(axis='x', labelsize=7); axis.tick_params(axis='y', labelsize=7)
        for bar, val in zip(bars, vals):
            axis.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(vals)*.025, f'{val:.3f}', ha='center', va='bottom', fontsize=6)
        axis.margins(x=.08, y=.15)
    ax[0].set_xlabel('Compression candidate', fontsize=8); ax[1].set_xlabel('Compression candidate', fontsize=8)
    ax[1].text(.98, .96, 'PCA32 selected', transform=ax[1].transAxes, ha='right', va='top', fontsize=7, color='#7a1f5c')
    fig.suptitle('(b) Pre-registered profile-compression selection', x=.03, y=.995, ha='left', va='top', fontsize=10, fontweight='bold')
    fig.subplots_adjust(top=.78, bottom=.22, left=.10, right=.98, wspace=.34)
    save(OUT / 'figures' / 'figure_b_revised', fig)
    dump({'figure_id': 'B', 'source_commit': COMMIT, 'source_csv': str(V1 / 'source_data' / 'figure_b_compression_crossfit.csv'), 'source_csv_sha256': sha(V1 / 'source_data' / 'figure_b_compression_crossfit.csv'), 'selection_manifest_sha256': json.loads((V1 / 'provenance' / 'figure_b_provenance.json').read_text())['selection_sha256'], 'display_changes': ['title/panel spacing', 'horizontal category labels', 'value labels and explicit PCA32 annotation'], 'scientific_values_changed': False}, OUT / 'provenance' / 'figure_b_revised_provenance.json')

def figure_c(audit, sel, pred, idx):
    entries = {x['selection']: x for x in audit['C1_representative_selection']['selection_rows']}
    arrays = {}
    wl = ang = None
    for label in ['best', 'median', 'worst']:
        e = entries[label]; truth = np.load(e['truth_source_path'], mmap_mode='r')
        t = np.asarray(truth['normalized_joint'], dtype=float)
        p = np.asarray(pred[np.asarray(e['prediction_profile_rows'], dtype=int)], dtype=float).mean(axis=0)
        if wl is None: wl = np.asarray(truth['wavelength_nm']); ang = np.asarray(truth['angle_deg'])
        t = t / max(float(np.nanmax(t)), 1e-30); p = p / max(float(np.nanmax(p)), 1e-30)
        arrays[label] = (t, p, np.abs(t-p))
    error_hi = float(np.nanpercentile(np.concatenate([arrays[k][2].ravel() for k in arrays]), 99.5))
    fig, ax = plt.subplots(3, 3, figsize=(7.35, 6.25), facecolor='white', gridspec_kw={'wspace': .14, 'hspace': .33})
    tp_norm = Normalize(0, 1); err_norm = Normalize(0, max(error_hi, 1e-6)); tp_mappable = ScalarMappable(norm=tp_norm, cmap='magma'); err_mappable = ScalarMappable(norm=err_norm, cmap='viridis')
    for i, label in enumerate(['best', 'median', 'worst']):
        t, p, err = arrays[label]
        for j, (axis, data, title) in enumerate([(ax[i,0], t, 'Truth'), (ax[i,1], p, 'M1 prediction'), (ax[i,2], err, 'Absolute error')]):
            axis.imshow(data.T, origin='lower', aspect='auto', extent=[wl[0], wl[-1], ang[0], ang[-1]], cmap='viridis' if j == 2 else 'magma', interpolation='none', norm=err_norm if j == 2 else tp_norm)
            axis.tick_params(labelsize=6)
            if i == 0: axis.set_title(title, fontsize=8, pad=7)
            if j == 0: axis.set_ylabel(f'{label} geometry\nAngle (deg)', fontsize=7)
            else: axis.set_yticklabels([])
            if i == 2: axis.set_xlabel('Wavelength (nm)', fontsize=7)
            else: axis.set_xticklabels([])
    cax1 = fig.add_axes([.91, .16, .014, .67]); cb1 = fig.colorbar(tp_mappable, cax=cax1); cb1.set_label('Unit-peak profile', fontsize=7); cb1.ax.tick_params(labelsize=6)
    cax2 = fig.add_axes([.95, .16, .014, .67]); cb2 = fig.colorbar(err_mappable, cax=cax2); cb2.set_label('Absolute error', fontsize=7); cb2.ax.tick_params(labelsize=6)
    fig.suptitle('(c) Test40 representative joint profiles', x=.03, y=.985, ha='left', va='top', fontsize=10, fontweight='bold')
    fig.subplots_adjust(left=.10, right=.885, bottom=.10, top=.90)
    save(OUT / 'figures' / 'figure_c_revised', fig)
    dump({'figure_id': 'C', 'source_commit': COMMIT, 'comparability_audit': str(OUT / 'figure_c_truth_prediction_comparability_audit.json'), 'selection_source_sha256': audit['C1_representative_selection']['source_sha256'], 'selection_unchanged': True, 'display_rule': 'truth_display = truth/max(truth); prediction_display = prediction/max(prediction); error = abs(truth_display-prediction_display)', 'truth_prediction_same_grid': True, 'truth_prediction_common_color_scale': [0, 1], 'error_independent_color_scale': [0, error_hi], 'colorbar_count': 2, 'no_smoothing_or_interpolation': True, 'scientific_values_changed': False}, OUT / 'provenance' / 'figure_c_revised_provenance.json')

def figure_d(d_power, d_rank, table_b):
    fig, ax = plt.subplots(1, 3, figsize=(7.35, 3.35), facecolor='white')
    x = np.log10(np.maximum(pd.to_numeric(d_power['label_power'], errors='coerce').to_numpy(), 1e-12)); y = np.log10(np.maximum(pd.to_numeric(d_power['pred_power'], errors='coerce').to_numpy(), 1e-12))
    ax[0].scatter(x, y, s=8, alpha=.55, color='#4c78a8', rasterized=True); ax[0].set_xlabel('log10 raw FDTD native upward power', fontsize=7); ax[0].set_ylabel('log10 M1 source-normalized proxy', fontsize=7); ax[0].set_title('Power scale comparison', fontsize=8, pad=8); ax[0].text(.03, .95, 'not on a common\nquantitative scale', transform=ax[0].transAxes, ha='left', va='top', fontsize=6.5, color='#a33')
    rx = pd.to_numeric(d_rank['label_power'], errors='coerce').rank().to_numpy(); ry = pd.to_numeric(d_rank['pred_power'], errors='coerce').rank().to_numpy(); ax[1].scatter(rx, ry, s=12, color='#59a14f'); ax[1].set_xlabel('Native FDTD geometry rank', fontsize=7); ax[1].set_ylabel('M1 proxy geometry rank', fontsize=7); ax[1].set_title('Geometry ranking', fontsize=8, pad=8); ax[1].text(.04, .95, 'Spearman = 0.128330', transform=ax[1].transAxes, ha='left', va='top', fontsize=6.5)
    js = pd.to_numeric(d_power['joint_js'], errors='coerce').to_numpy(); ax[2].hist(js, bins=16, color='#f28e2b', alpha=.85); ax[2].set_xlabel('Case joint-JS divergence', fontsize=7); ax[2].set_ylabel('Count', fontsize=7); ax[2].set_title('Test40 error distribution', fontsize=8, pad=8); ax[2].text(.04, .95, 'case joint-JS mean = 0.267155', transform=ax[2].transAxes, ha='left', va='top', fontsize=6.5)
    for axis in ax: axis.tick_params(labelsize=6.5)
    fig.suptitle('(d) Frozen Test40 ranking-screening outcomes', x=.03, y=.995, ha='left', va='top', fontsize=10, fontweight='bold')
    fig.subplots_adjust(left=.10, right=.985, bottom=.29, top=.78, wspace=.46)
    save(OUT / 'figures' / 'figure_d_revised', fig)
    dump({'figure_id': 'D', 'source_commit': COMMIT, 'power_source_csv': str(V1 / 'source_data' / 'figure_d_test40_power_and_error.csv'), 'rank_source_csv': str(V1 / 'source_data' / 'figure_d_test40_geometry_ranks.csv'), 'power_source_sha256': sha(V1 / 'source_data' / 'figure_d_test40_power_and_error.csv'), 'rank_source_sha256': sha(V1 / 'source_data' / 'figure_d_test40_geometry_ranks.csv'), 'frozen_annotation_values': {'geometry_power_rank_spearman': 0.12833020637898687, 'case_joint_js_mean': 0.26715496660272675}, 'display_changes': ['increased bottom margin', 'direct exact-value annotations', 'explicit non-common power-scale note'], 'scientific_values_changed': False}, OUT / 'provenance' / 'figure_d_revised_provenance.json')

def main():
    (OUT / 'figures').mkdir(parents=True, exist_ok=True); (OUT / 'provenance').mkdir(parents=True, exist_ok=True)
    a = load_inputs(); figure_a(a['a']); figure_b(a['b']); figure_c(a['audit'], a['sel'], a['pred'], a['idx']); figure_d(a['d_power'], a['d_rank'], a['table_b'])
    print(json.dumps({'output_root': str(OUT), 'figures': ['A', 'B', 'C', 'D'], 'selection_unchanged': True, 'scientific_values_changed': False}, indent=2))

if __name__ == '__main__':
    main()
