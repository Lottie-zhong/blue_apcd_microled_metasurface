from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs' / 'apcd_native_m1_display_colors_v1'


def rows(name):
    return list(csv.DictReader((OUT / name).open(encoding='utf-8')))


def test_policy_and_exact_colors():
    policy = json.loads((ROOT / 'configs' / 'mdc_defect_450_material_policy.json').read_text())
    assert policy['material_policy_version'] == 5
    display = policy['display_policy']
    assert display['version'] == 1
    assert display['materials']['APCD_GAN_NATIVE_M1']['rgba'] == [0.05, 0.30, 0.95, 1.0]
    assert display['materials']['APCD_TIO2_NATIVE_M1']['rgba'] == [1.0, 0.82, 0.05, 1.0]
    assert 'APCD_SIO2_NATIVE_M1' not in display['materials']


def test_optical_invariance():
    audit = rows('optical_invariance_validation.csv')
    assert {row['material_id'] for row in audit} == {'APCD_GAN_NATIVE_M1', 'APCD_TIO2_NATIVE_M1', 'APCD_SIO2_NATIVE_M1'}
    assert all(row['status'] == 'pass' and row['optical_hash_unchanged'] == 'True' for row in audit)
    assert all(float(row['max_abs_delta_epsilon']) == 0.0 and float(row['max_abs_delta_n']) <= 1e-12 and float(row['max_abs_delta_k']) <= 1e-12 for row in audit)


def test_blank_readback_and_session_safety():
    validation = json.loads((OUT / 'validation.json').read_text())
    # The requested command order runs this test before --audit-only refreshes
    # the existing blank-session evidence into the quantization-aware schema.
    assert validation['status'] in {'audit_pass', 'display_color_policy_pass_with_expected_api_quantization'}
    assert validation['session_status'] == 'blank_session_pass'
    assert validation.get('readback_status', 'api_quantized') in {'pass', 'api_quantized'}
    assert validation['session']['started'] and validation['session']['closed']
    assert not validation['session']['source_fsp_loaded'] and not validation['session']['solver_run']
    readback = rows('material_color_readback.csv')
    gan = next(row for row in readback if row['material_id'] == 'APCD_GAN_NATIVE_M1')
    tio2 = next(row for row in readback if row['material_id'] == 'APCD_TIO2_NATIVE_M1')
    expected_tolerance = 0.5 / 65535.0 + 1e-12
    gan_error = float(gan.get('observed_max_channel_error') or gan['max_channel_error'])
    tio2_error = float(tio2.get('observed_max_channel_error') or tio2['max_channel_error'])
    assert gan_error <= expected_tolerance
    assert tio2_error <= expected_tolerance


def test_quantization_acceptance_definition():
    import sys
    sys.path.insert(0, str(ROOT / 'scripts'))
    import patch_apcd_native_m1_display_colors_v1 as patch
    assert patch.CHANNEL_QUANTIZATION_BITS == 16
    assert patch.QUANTIZATION_STEP == 1.0 / 65535.0
    assert patch.MAXIMUM_ROUNDING_ERROR == 0.5 / 65535.0
    assert patch.ACCEPTANCE_TOLERANCE == 0.5 / 65535.0 + 1e-12


def test_registration_helper_and_builder_scope():
    text = (ROOT / 'scripts' / 'apcd_native_materials.py').read_text(encoding='utf-8')
    assert 'register_lumerical_sampled_material' in text
    assert 'setmaterial(canonical, "color"' in text
    report = (ROOT / 'reports' / 'apcd_native_m1_display_colors_v1.md').read_text(encoding='utf-8')
    assert 'This freeze covers the unified display policy and registration helper only.' in report
    assert 'visualization metadata' in report
