from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs' / 'mdc_gan_native_m1_tmm_spectral_rebaseline_v1'
REPS = {'legacy_n241', 'native_m1_raw_table', 'native_m1_lumerical_query_diagnostic'}
KEY = ('structure_id', 'geometry_hash', 'canonical_sequence_hash', 'gan_material_id', 'gan_representation')
METRICS = ('spectral_peak_nm', 'spectral_FWHM_nm', 'T448', 'T450', 'T453', 'edge_stability', 'R450', 'power_entering_450', 'A_stack_450', 'far_field_balance_offset_450')


def rows(name: str):
    return list(csv.DictReader((OUT / name).open(encoding='utf-8')))


def keyed(metrics):
    result = {tuple(row[name] for name in KEY): row for row in metrics}
    assert len(result) == len(metrics) == 9
    return result


def test_frozen_controls_and_method_status():
    candidates = rows('candidate_manifest.csv')
    assert [row['static_structure_id'] for row in candidates] == ['P1_EXPLICIT_FAB_G3_A3', 'P1_ZL1_NOMINAL_G3_A3', 'P1_ZL1_ALTERNATIVE_G3_A3']
    assert [(row['layer_count'], row['total_thickness_nm']) for row in candidates] == [('13', '900'), ('12', '978'), ('12', '975')]
    validation = json.loads((OUT / 'validation.json').read_text())
    assert validation['status'] == 'complex_incident_normalization_pass'
    assert validation['identity_key_fields'] == list(KEY)
    assert validation['metric_identity_rows'] == 9
    assert not validation['solver_invoked'] and validation['no_oblique_tmm'] and validation['no_finite_GaN_propagation']


def test_identity_is_exact_and_representations_are_separated():
    metrics = rows('spectral_metrics.csv')
    keyed(metrics)
    by_structure = {}
    for row in metrics:
        by_structure.setdefault(row['structure_id'], set()).add(row['gan_representation'])
    assert set(by_structure) == {'P1_EXPLICIT_FAB_G3_A3', 'P1_ZL1_NOMINAL_G3_A3', 'P1_ZL1_ALTERNATIVE_G3_A3'}
    assert all(values == REPS for values in by_structure.values())
    assert all(float(row['gan_k450']) > 0 for row in metrics if row['gan_representation'] != 'legacy_n241')
    assert all(row['angular_missing_reason'] == '' for row in metrics)
    assert all(row['angle_convention_id'] == 'air_side_far_field_conserved_real_kx_v1' for row in metrics)


def test_delta_algebra_is_keyed_not_positional():
    metrics = rows('spectral_metrics.csv')
    by_key = keyed(metrics)
    for name, base_rep, other_rep in (
        ('legacy_vs_native_comparison.csv', 'legacy_n241', 'native_m1_raw_table'),
        ('representation_delta_metrics.csv', 'native_m1_raw_table', 'native_m1_lumerical_query_diagnostic'),
    ):
        comparison_rows = rows(name)
        assert len(comparison_rows) == 3
        for row in comparison_rows:
            shared = (row['structure_id'], row['geometry_hash'], row['canonical_sequence_hash'])
            base_id = 'APCD_GAN_LEGACY_N241' if base_rep == 'legacy_n241' else 'APCD_GAN_NATIVE_M1'
            other_id = 'APCD_GAN_NATIVE_M1'
            base = by_key[shared + (base_id, base_rep)]
            other = by_key[shared + (other_id, other_rep)]
            for metric in METRICS:
                field = 'delta_' + metric
                if row[field]:
                    assert abs(float(row[field]) - (float(other[metric]) - float(base[metric]))) <= 1e-12
    assert all('+10.9/-11.4/+0.447770' not in line for line in (ROOT / 'reports' / 'mdc_gan_native_m1_tmm_spectral_rebaseline_v1.md').read_text(encoding='utf-8').splitlines())


def test_power_method_and_oracle_contracts_remain_passed():
    audit = rows('complex_incident_normalization_audit.csv')
    assert all(row['status'] == 'pass' for row in audit)
    assert len([row for row in audit if row['gate'] == 'complex_GaN_air_interface']) == 2
    assert len(rows('legacy_control_replay.csv')) == 3
    oracle = rows('independent_oracle_comparison.csv')
    assert len(oracle) == 5 and all(row['oracle_status'] == 'pass' for row in oracle)


def test_no_solver_api_or_positional_comparison_code():
    text = (ROOT / 'scripts' / 'run_mdc_gan_native_m1_tmm_spectral_rebaseline_v1.py').read_text(encoding='utf-8')
    assert 'import ' + 'lumapi' not in text and 'runanalysis' not in text
    assert 'comparison_source' in text and 'identity_key' in text


def test_ratio_closure_uses_strict_angle_identity_and_replays_known_values():
    metrics = rows('spectral_metrics.csv')
    assert all(row['ratio_status'] == 'finite' for row in metrics)
    raw = {r['structure_id']: float(r['ratio']) for r in metrics if r['gan_representation'] == 'native_m1_raw_table'}
    assert abs(raw['P1_EXPLICIT_FAB_G3_A3'] - 40.115520224477926) < 1e-9
    assert abs(raw['P1_ZL1_NOMINAL_G3_A3'] - 63.08879456874723) < 1e-9
    assert abs(raw['P1_ZL1_ALTERNATIVE_G3_A3'] - 45.66660483135923) < 1e-9
    replay = rows('ratio_replay_validation.csv')
    assert len(replay) == 3 and all(r['status'] == 'pass' for r in replay)
    assert all(abs(float(r['delta_algebra_identity'])) <= 1e-12 for r in replay)
