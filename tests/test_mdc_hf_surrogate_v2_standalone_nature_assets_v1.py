import json
from pathlib import Path
import pandas as pd

ROOT = Path(r'D:/project/worktrees/blue_apcd_mdc_hf_surrogate_v2')
OUT = ROOT / 'outputs' / 'mdc_hf_surrogate_v2_standalone_nature_paper_assets_v1' / '20260809T_standalone_nature_assets_631080f'

def test_manifest_pass_and_safety():
    m = json.loads((OUT / 'mdc_standalone_nature_paper_asset_manifest.json').read_text())
    assert m['status'] == 'PASS'
    assert m['capability'] == 'RANKING_SCREENING_ONLY'
    assert all(v == 0 for v in m['safety'].values())

def test_required_figure_formats_and_scope():
    for folder, stem in [('figure_a', 'figure_a_frozen_profile_representation'), ('figure_b', 'figure_b_compression_selection'), ('figure_c', 'figure_c_test40_representative_profiles'), ('figure_d', 'figure_d_test40_outcomes'), ('workflow', 'mdc_to_np_workflow')]:
        for ext in ['pdf', 'svg', 'png']:
            assert (OUT / folder / f'{stem}.{ext}').exists()
    scope = json.loads((OUT / 'contracts' / 'standalone_final_scope_registry.json').read_text())
    assert scope['solver_calls'] == 0
    assert scope['test40_metrics_recomputed'] is False

def test_frozen_metrics_and_model_selection():
    a = pd.read_csv(OUT / 'tables' / 'table_a_oof_model_comparison.csv')
    assert a.loc[a.architecture == 'M1', 'selection'].item() == 'winner'
    b = pd.read_csv(OUT / 'tables' / 'table_b_test40_frozen_metrics.csv')
    assert b.loc[b.aggregation == 'Case', 'n'].item() == 240
    assert b.loc[b.aggregation == 'Geometry', 'n'].item() == 40

def test_power_prohibition_and_handoff():
    prohibition = json.loads((OUT / 'contracts' / 'mdc_power_head_usage_prohibition.json').read_text())
    assert 'native FDTD power equivalence' in prohibition['prohibited_claims']
    handoff = json.loads((OUT / 'contracts' / 'mdc_np_handoff_v1.json').read_text())
    assert handoff['one_way'] is True
