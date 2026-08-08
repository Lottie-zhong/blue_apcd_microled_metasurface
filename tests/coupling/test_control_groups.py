import json
from pathlib import Path

from apcd_coupling.comparison_engine import build_comparison, row_from_result, standalone_row
from apcd_coupling.joint_stack_builder import build_joint_case

ROOT = Path(__file__).resolve().parents[2]
CFG = json.loads((ROOT / 'configs/coupling/stage_a_control_groups_v1.json').read_text(encoding='utf-8'))
OUT = ROOT / 'outputs/coupling'

def cases():
    return {item['control_group']: build_joint_case(item['mdc_candidate'], item['np_candidate'], 0, 450, 'x', 0, interface_candidate=item.get('interface_candidate'), case_id=item['case_id'], control_group=item['control_group']) for item in CFG['controls']}

def test_declarative_presence_absence_and_common_cell():
    built = cases()
    assert len([x for x in built['B0']['objects'] if x['role'] == 'mdc_layer']) == 0
    assert len([x for x in built['B0']['objects'] if x['role'] == 'np_pillar']) == 0
    assert len([x for x in built['B1']['objects'] if x['role'] == 'mdc_layer']) == 12
    assert len([x for x in built['B1']['objects'] if x['role'] == 'np_pillar']) == 0
    assert len([x for x in built['B2']['objects'] if x['role'] == 'interface_support_layer']) == 1
    assert len([x for x in built['B2']['objects'] if x['role'] == 'mdc_layer']) == 0
    assert len([x for x in built['B2']['objects'] if x['role'] == 'np_pillar']) == 6
    assert {x['np_candidate']['period_x_nm'] for x in built.values()} == {1740}
    assert {x['np_candidate']['period_y_nm'] for x in built.values()} == {290}

def test_control_results_and_comparison_artifact():
    results = {g: json.loads((OUT / f'stage_a_{g.lower()}_450nm_xpol_normal_v1/results/result.json').read_text(encoding='utf-8')) for g in ('B0','B1','B2')}
    results['B3'] = json.loads((OUT / 'stage_a_450nm_xpol_normal_textra0_golden_fixture_v1/results/result.json').read_text(encoding='utf-8'))
    for group, result in results.items():
        assert result['solver_entered'] is True and result['solver_completed'] is True
        assert result['order_closure']['pass'] is True
        assert result['power_closure']['pass'] is True
        assert result['pre_fsp_post_entry_mutation']['detected'] is True
    assert results['B0']['not_applicable']['eta_plus1'].startswith('NOT_APPLICABLE')
    assert results['B1']['not_applicable']['directionality'].startswith('NOT_APPLICABLE')
    assert results['B2']['eta_plus1'] > 0
    matrix = json.loads((OUT / 'stage_a_control_groups_comparison_v1/comparison_matrix.json').read_text(encoding='utf-8'))
    assert [row['comparison_id'] for row in matrix['rows']] == ['NP_R0_STANDALONE_REFERENCE','B0','B1','B2','B3']
    assert matrix['provenance_status'] == 'PASS'
    assert 'full_mdc_B3_minus_B2' in matrix['attribution']
