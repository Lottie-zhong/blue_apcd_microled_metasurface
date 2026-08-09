import json
from pathlib import Path
import pandas as pd

ROOT = Path(r'D:/project/worktrees/blue_apcd_mdc_hf_surrogate_v2')
OUT = ROOT / 'outputs' / 'mdc_hf_surrogate_v2_standalone_nature_paper_assets_v2' / '20260809T_figure_c_comparability_revised_b380f87'
V1 = ROOT / 'outputs' / 'mdc_hf_surrogate_v2_standalone_nature_paper_assets_v1' / '20260809T_standalone_nature_assets_631080f'

def test_comparability_audit_passes_and_selection_is_frozen():
    audit = json.loads((OUT / 'figure_c_truth_prediction_comparability_audit.json').read_text())
    assert audit['status'] == 'PASS'
    assert audit['C7_replot_decision'] == 'COMPARABLE_AFTER_DISPLAY_FIX'
    assert audit['C1_representative_selection']['selection_matches_frozen_csv'] is True
    assert audit['C4_physical_comparability']['same_grid'] is True
    assert audit['C4_physical_comparability']['same_stored_amplitude_normalization'] is False

def test_revised_formats_and_provenance():
    for stem in ['figure_a_revised', 'figure_b_revised', 'figure_c_revised', 'figure_d_revised']:
        for ext in ['pdf', 'svg', 'png']:
            assert (OUT / 'figures' / f'{stem}.{ext}').exists()
        assert (OUT / 'provenance' / f'{stem}_provenance.json').exists()

def test_c_display_contract_is_explicit():
    prov = json.loads((OUT / 'provenance' / 'figure_c_revised_provenance.json').read_text())
    assert prov['selection_unchanged'] is True
    assert prov['truth_prediction_common_color_scale'] == [0, 1]
    assert prov['error_independent_color_scale'][0] == 0
    assert prov['colorbar_count'] == 2
    assert prov['scientific_values_changed'] is False

def test_frozen_inputs_and_qc_pass():
    qc = json.loads((OUT / 'reports' / 'visual_qc_report.json').read_text())
    manifest = json.loads((OUT / 'revised_figure_asset_manifest.json').read_text())
    assert qc['status'] == 'PASS'
    assert qc['static_source_preflight']['fail'] == 0
    assert all(item['status'] == 'PASS' for item in qc['pdf_text_audit'].values())
    assert manifest['status'] == 'PASS'
    assert manifest['selection_unchanged'] is True
    assert manifest['frozen_metrics_unchanged'] is True
    assert all(v == 0 for v in manifest['safety_counts'].values())

def test_frozen_selection_csv_not_modified():
    selected = pd.read_csv(V1 / 'source_data' / 'test40_representative_geometry_selection.csv')
    audit = json.loads((OUT / 'figure_c_truth_prediction_comparability_audit.json').read_text())
    rows = audit['C1_representative_selection']['selection_rows']
    assert [x['geometry_hash'] for x in rows] == selected['geometry_hash'].tolist()
    assert [x['selection'] for x in rows] == selected['selection'].tolist()
