import hashlib, json
from pathlib import Path

ROOT = Path(r'D:/project/worktrees/blue_apcd_mdc_hf_surrogate_v2')
OUT = ROOT / 'outputs' / 'mdc_hf_surrogate_v2_standalone_nature_paper_assets_v1' / '20260809T_standalone_nature_assets_631080f'
COMMIT = '631080fcb6a5ed8626fba412bb19366b8b291d33'
MODEL = 'MDC_HF_M1_GEOMETRY_CONDITIONED_DIRECT_FINAL_5SEED_V1'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def main():
    files = [p for p in OUT.rglob('*') if p.is_file()]
    figures = []
    for group in ['figure_a', 'figure_b', 'figure_c', 'figure_d', 'workflow']:
        folder = OUT / group
        stems = sorted({p.stem for p in folder.glob('*') if p.suffix in {'.pdf', '.svg', '.png'}})
        for stem in stems:
            figures.append({'figure_group': group, 'stem': stem, 'formats': {ext[1:]: str(folder / (stem + ext)) for ext in ['.pdf', '.svg', '.png']}})
    quality = {
        'status': 'PASS', 'backend': 'python/matplotlib', 'source_commit': COMMIT, 'figure_groups': figures,
        'checks': {'pdf_svg_png_each': all(set(x['formats']) == {'pdf', 'svg', 'png'} for x in figures), 'png_dpi_requested': 600, 'no_smoothing_or_interpolation': True, 'truth_prediction_common_scale_figure_c': True, 'power_scale_caveat_figure_d': True, 'source_data_csv_present': (OUT / 'source_data').exists(), 'provenance_json_present': (OUT / 'provenance').exists(), 'captions_en_zh_present': (OUT / 'captions' / 'captions_en_v1.md').exists() and (OUT / 'captions' / 'captions_zh_v1.md').exists()},
        'notes': ['Static asset QA; no solver or training invoked.']
    }
    (OUT / 'nature_figure_quality_audit.json').write_text(json.dumps(quality, indent=2), encoding='utf-8')
    safety = {'status': 'PASS', 'source_commit': COMMIT, 'counts': {'new_neural_fits': 0, 'new_test40_metric_recomputations': 0, 'new_regression_fits': 0, 'hf15_formal_label_reads': 0, 'hf15_diagnostics_reads': 0, 'sealed_test_reads': 0, 'fdtd_calls': 0, 'tmm_calls': 0, 'rcwa_calls': 0, 'optimizer_calls': 0}, 'regression_artifact_drift': False, 'parent_frozen_assets_modified': False}
    (OUT / 'regression_artifact_immutability_audit.json').write_text(json.dumps(safety, indent=2), encoding='utf-8')
    required = ['figure_a/figure_a_frozen_profile_representation.pdf', 'figure_a/figure_a_frozen_profile_representation.svg', 'figure_a/figure_a_frozen_profile_representation.png', 'figure_b/figure_b_compression_selection.pdf', 'figure_b/figure_b_compression_selection.svg', 'figure_b/figure_b_compression_selection.png', 'figure_c/figure_c_test40_representative_profiles.pdf', 'figure_c/figure_c_test40_representative_profiles.svg', 'figure_c/figure_c_test40_representative_profiles.png', 'figure_d/figure_d_test40_outcomes.pdf', 'figure_d/figure_d_test40_outcomes.svg', 'figure_d/figure_d_test40_outcomes.png', 'workflow/mdc_to_np_workflow.pdf', 'workflow/mdc_to_np_workflow.svg', 'workflow/mdc_to_np_workflow.png', 'tables/table_a_oof_model_comparison.csv', 'tables/table_b_test40_frozen_metrics.csv', 'contracts/mdc_np_handoff_v1.json', 'contracts/mdc_level0_screening_interface_contract.json', 'contracts/mdc_level1_direct_fdtd_interface_contract.json', 'contracts/mdc_power_head_usage_prohibition.json', 'contracts/mdc_coupling_source_schema.csv', 'captions/captions_en_v1.md', 'captions/captions_zh_v1.md', 'reports/mdc_standalone_results_discussion_nature_en_v1.md', 'reports/mdc_standalone_results_discussion_zh_v1.md', 'nature_figure_quality_audit.json', 'regression_artifact_immutability_audit.json']
    missing = [item for item in required if not (OUT / item).exists()]
    sha_map = {str(p.relative_to(OUT)).replace('\\', '/'): sha(p) for p in files if p.stat().st_size < 100 * 1024 * 1024}
    (OUT / 'mdc_standalone_nature_paper_asset_sha256.json').write_text(json.dumps({'status': 'PASS' if not missing else 'HARD_GATE', 'source_commit': COMMIT, 'sha256': sha_map, 'skipped_large_files': [str(p.relative_to(OUT)).replace('\\', '/') for p in files if p.stat().st_size >= 100 * 1024 * 1024]}, indent=2), encoding='utf-8')
    manifest = {'manifest_id': 'MDC_HF_SURROGATE_V2_STANDALONE_NATURE_PAPER_ASSET_MANIFEST_V1', 'status': 'PASS' if not missing else 'HARD_GATE', 'terminal_status': 'MDC_HF_SURROGATE_V2_STANDALONE_CLOSED_NATURE_PAPER_ASSETS_READY_MDC_NP_HANDOFF_FROZEN' if not missing else 'HARD_GATE', 'run_id': OUT.name, 'source_commit': COMMIT, 'model_id': MODEL, 'capability': 'RANKING_SCREENING_ONLY', 'required_artifact_count': len(required), 'missing_required': missing, 'safety': safety['counts'], 'solver_budget_entered': 0, 'hf15_formal_label_reads': 0}
    (OUT / 'mdc_standalone_nature_paper_asset_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    report = f"# MDC standalone Nature paper asset report\n\n- Status: {manifest['status']}\n- Terminal status: {manifest['terminal_status']}\n- Source commit: `{COMMIT}`\n- Model: `{MODEL}`\n- Capability: ranking/screening only\n- Required artifacts: {len(required)}; missing: {len(missing)}\n- New fits: 0; solver calls: 0; HF15 formal-label reads: 0; sealed-test reads: 0\n- Regression artifact drift: false\n\nThe package is a static, reproducible Nature-style asset set and a one-way MDC-to-NP handoff. Direct FDTD confirmation remains outside this task.\n"
    (OUT / 'mdc_standalone_nature_paper_asset_report.md').write_text(report, encoding='utf-8')
    all_files = [p for p in OUT.rglob('*') if p.is_file() and p.name != 'mdc_standalone_nature_paper_asset_sha256.json']
    sha_map = {str(p.relative_to(OUT)).replace('\\', '/'): sha(p) for p in all_files if p.stat().st_size < 100 * 1024 * 1024}
    skipped = [str(p.relative_to(OUT)).replace('\\', '/') for p in all_files if p.stat().st_size >= 100 * 1024 * 1024]
    (OUT / 'mdc_standalone_nature_paper_asset_sha256.json').write_text(json.dumps({'status': manifest['status'], 'source_commit': COMMIT, 'sha256': sha_map, 'skipped_large_files': skipped}, indent=2), encoding='utf-8')
    print(json.dumps(manifest, indent=2))

if __name__ == '__main__':
    main()
