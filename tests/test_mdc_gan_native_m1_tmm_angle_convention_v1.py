from __future__ import annotations

import math
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from mdc_tmm_complex_incident_power_v1 import oblique_interface_rt, oblique_stack_rt, select_forward_kz, tangential_admittance


def test_air_side_kx_is_real_and_final_air_propagates_to_60_deg():
    result = oblique_interface_rt(2.41 + 0j, 1 + 0j, math.sin(math.radians(60)), 'TE')
    assert result['final_propagating']
    assert result['T'] > 0


def test_internal_counterfactual_above_critical_has_no_propagating_air_power():
    result = oblique_interface_rt(2.41 + 0j, 1 + 0j, 2.41 * math.sin(math.radians(30)), 'TE')
    assert not result['final_propagating']
    assert result['T'] == 0


def test_passive_branch_and_admittance_normal_reduction():
    kz = select_forward_kz(2.4 + .08j, .5)
    assert kz.imag >= 0
    assert tangential_admittance(2.4 + .08j, 2.4 + .08j, 'TE') == 2.4 + .08j
    assert abs(tangential_admittance(2.4 + .08j, 2.4 + .08j, 'TM') - (2.4 + .08j)) < 1e-12


def test_lossless_interface_and_plus_minus_symmetry():
    for pol in ('TE', 'TM'):
        plus = oblique_interface_rt(2.41 + 0j, 1 + 0j, math.sin(math.radians(20)), pol)
        minus = oblique_interface_rt(2.41 + 0j, 1 + 0j, math.sin(math.radians(-20)), pol)
        assert abs(plus['R'] + plus['T'] - 1) < 1e-12
        assert abs(plus['T'] - minus['T']) < 1e-12


def test_normal_oblique_matches_normal_stack_power():
    from mdc_tmm_complex_incident_power_v1 import normal_stack_power
    stack = [(2.25 + 0j, 50.0)]
    old = normal_stack_power(2.41 + 0j, 1 + 0j, stack, 450, historical_lossless=True)
    new = oblique_stack_rt(2.41 + 0j, 1 + 0j, stack, 450, 0.0, 'TE', historical_lossless=True)
    for field in ('r', 't', 'R', 'T', 'power_entering', 'A_stack'):
        assert abs(old[field] - new[field]) < 1e-12


def test_audit_script_has_frozen_ratio_provenance_and_no_lumapi():
    text = (ROOT / 'scripts' / 'audit_mdc_gan_native_m1_tmm_angle_convention_v1.py').read_text(encoding='utf-8')
    assert 'MDC1B_normal_to_40_60_ratio_fixed_8_angles_v1' in text
    assert "'source_commit': 'cfa72d7'" in text
    assert 'import lumapi' not in text.lower()


def test_symmetry_aware_peak_fields_are_declared_without_solver():
    text = (ROOT / 'scripts' / 'audit_mdc_gan_native_m1_tmm_angle_convention_v1.py').read_text(encoding='utf-8')
    for field in ('maximum_angle_raw_argmax_deg', 'maximum_angle_set_deg', 'maximum_abs_angle_deg', 'center_is_global_max', 'symmetric_peak_pair', 'peak_tie_tolerance', 'symmetry_residual'):
        assert field in text
    assert '--postprocess-only' in text and ('import ' + 'lumapi') not in text.lower()


def test_frozen_peak_sets_are_symmetric_or_unique_center_deterministically():
    path = ROOT / 'outputs' / 'mdc_gan_native_m1_tmm_angle_convention_v1' / 'peak_angle_symmetry_validation.csv'
    rows = list(csv.DictReader(path.open(encoding='utf-8')))
    raw = {r['structure_id']: r for r in rows if r['gan_representation'] == 'native_m1_raw_table'}
    assert raw['P1_EXPLICIT_FAB_G3_A3']['maximum_angle_set_deg'] == '[-3.0,3.0]'
    assert raw['P1_ZL1_NOMINAL_G3_A3']['maximum_angle_set_deg'] == '[-4.0,4.0]'
    assert raw['P1_ZL1_ALTERNATIVE_G3_A3']['maximum_angle_set_deg'] == '[0.0]'
    assert raw['P1_ZL1_ALTERNATIVE_G3_A3']['center_is_global_max'] == 'true'
