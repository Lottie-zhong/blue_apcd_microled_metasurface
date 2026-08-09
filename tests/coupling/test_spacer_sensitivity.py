import json
from pathlib import Path

from apcd_coupling.joint_stack_builder import build_joint_case

ROOT = Path(__file__).resolve().parents[2]
CFG = json.loads((ROOT / 'configs/coupling/stage_a_spacer_sensitivity_v1.json').read_text(encoding='utf-8'))

def test_spacer_declarative_semantics_and_continuity():
    for item in CFG['controls']:
        case = build_joint_case(item['mdc_candidate'], item['np_candidate'], item['spacer_nm'], 450, 'x', 0, interface_candidate=item['interface_candidate'], case_id=item['case_id'], control_group=item['control_group'])
        spacer = next(obj for obj in case['objects'] if obj['role'] == 'extra_spacer')
        final_mdc = [obj for obj in case['objects'] if obj['role'] == 'mdc_layer'][-1]
        pillars = [obj for obj in case['objects'] if obj['role'] == 'np_pillar']
        assert case['spacer_nm'] == item['spacer_nm']
        assert spacer['material_id'] == 'APCD_SIO2_NATIVE_M1'
        assert spacer['z_min_nm'] == final_mdc['z_max_nm'] == 975.0
        assert spacer['z_max_nm'] == 975.0 + item['spacer_nm']
        assert case['coordinates']['total_sio2_separation_nm'] == 79.0 + item['spacer_nm']
        assert all(p['z_min_nm'] == spacer['z_max_nm'] for p in pillars)
        assert all(p['z_max_nm'] - p['z_min_nm'] == 500.0 for p in pillars)
        assert case['coordinates']['same_material_spacer_continuity'] is True

def test_spacer_setup_outputs_are_readback_auditable_after_build():
    for item in CFG['controls']:
        out = ROOT / 'outputs/coupling' / f"stage_a_s{item['spacer_nm']}_450nm_xpol_normal_v1"
        if out.exists():
            gate = json.loads((out / 'setup_gate.json').read_text(encoding='utf-8'))
            rb = json.loads((out / 'setup_readback.json').read_text(encoding='utf-8'))
            assert gate['pass'] is True
            assert gate['checks']['no_gap_no_overlap'] is True
            assert gate['checks']['same_material_continuity'] is True
            assert rb['monitors']['transmission_monitor']['z'] > 1875e-9


def test_four_point_matrix_and_selection():
    matrix = json.loads((ROOT / 'outputs/coupling/stage_a_spacer_sensitivity_comparison_v1/spacer_matrix.json').read_text(encoding='utf-8'))
    assert [row['comparison_id'] for row in matrix['rows']] == ['NP_R0_STANDALONE_REFERENCE', 'B3_TEXTRA0', 'S79', 'S158', 'S237']
    assert matrix['candidate_decision']['status'] == 'BEST_450NM_SPACER_CANDIDATE'
    assert matrix['candidate_decision']['candidate_control_group'] == 'S237'
    assert matrix['candidate_decision']['final_spacer_freeze'] is False
    assert matrix['candidate_decision']['narrowband_confirmation_required'] is True
    for item in matrix['spacer_comparisons']:
        assert item['power_closure']['pass'] is True
        assert item['order_closure']['pass'] is True
