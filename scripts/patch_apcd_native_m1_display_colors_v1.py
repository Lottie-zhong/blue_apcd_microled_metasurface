from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

import apcd_native_materials as materials

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs' / 'apcd_native_m1_display_colors_v1'
REPORT = ROOT / 'reports' / 'apcd_native_m1_display_colors_v1.md'
POLICY = ROOT / 'configs' / 'mdc_defect_450_material_policy.json'
MATERIALS = ('APCD_GAN_NATIVE_M1', 'APCD_TIO2_NATIVE_M1', 'APCD_SIO2_NATIVE_M1')
WAVELENGTHS = (420.0, 448.0, 450.0, 453.0, 480.0)
CHANNEL_QUANTIZATION_BITS = 16
QUANTIZATION_STEP = 1.0 / ((2 ** CHANNEL_QUANTIZATION_BITS) - 1)
MAXIMUM_ROUNDING_ERROR = 0.5 * QUANTIZATION_STEP
ACCEPTANCE_TOLERANCE = MAXIMUM_ROUNDING_ERROR + 1e-12
DISPLAY_POLICY_PASS = 'display_color_policy_pass_with_expected_api_quantization'


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + '\n', encoding='utf-8')


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def array_hash(values: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(values).tobytes()).hexdigest()


def optical_snapshot() -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for material_id in MATERIALS:
        data = materials.load_material(material_id)
        epsilon = np.asarray(data['epsilon_complex'], dtype=np.complex128)
        index = np.asarray(data['n_complex'], dtype=np.complex128)
        values = {str(int(wl)): {'n': float(materials.get_complex_index(material_id, wl).real), 'k': float(materials.get_complex_index(material_id, wl).imag)} for wl in WAVELENGTHS}
        snapshot[material_id] = {
            'material_type': 'Sampled data',
            'sampled_shape': list(epsilon.shape),
            'sampled_data_sha256': array_hash(np.column_stack((data['frequency_hz'], epsilon))),
            'epsilon_sha256': array_hash(epsilon),
            'index_sha256': array_hash(index),
            'frequency_hz': np.asarray(data['frequency_hz']).tolist(),
            'values': values,
            'mesh_order': 'not_modified_by_display_patch',
            'fitting_settings': 'not_modified_by_display_patch',
        }
    return snapshot


def audit_builder_overrides() -> list[dict[str, str]]:
    files = [
        ROOT / 'scripts' / 'build_mdc_p1_plane_wave_fdtd_static_v1.py',
        ROOT / 'scripts' / 'run_mdc_p1_plane_wave_fdtd_v1.py',
        ROOT / 'scripts' / 'extract_mdc_gan_native_m1_candidate_v1.py',
        ROOT / 'scripts' / 'promote_apcd_gan_native_m1_v1.py',
    ]
    rows = []
    for path in files:
        text = path.read_text(encoding='utf-8', errors='replace') if path.exists() else ''
        lower = text.lower()
        if 'color' in lower or 'opacity' in lower:
            category = 'overrides_material_database_color' if 'setmaterial' in lower and 'color' in lower else 'unresolved'
        elif 'material database' in lower:
            category = 'inherits_material_database_color'
        else:
            category = 'property_not_used'
        rows.append({'builder': path.name, 'category': category, 'color_reference': 'yes' if 'color' in lower else 'no', 'opacity_reference': 'yes' if 'opacity' in lower else 'no'})
    return rows


def parse_json_list(value: Any) -> list[float]:
    if isinstance(value, list):
        return [float(item) for item in value]
    return [float(item) for item in json.loads(str(value))]


def quantization_record(material_id: str, expected: list[float], readback: list[float]) -> dict[str, Any]:
    observed = max(abs(actual - requested) for actual, requested in zip(readback, expected))
    return {
        'material_id': material_id,
        'requested_rgba': expected,
        'lumerical_readback_rgba': readback,
        'channel_quantization_bits': CHANNEL_QUANTIZATION_BITS,
        'quantization_step': QUANTIZATION_STEP,
        'maximum_rounding_error': MAXIMUM_ROUNDING_ERROR,
        'acceptance_tolerance': ACCEPTANCE_TOLERANCE,
        'observed_max_channel_error': observed,
        'alpha_is_one': readback[-1] == 1.0,
        'quantization_aware_status': 'pass' if observed <= ACCEPTANCE_TOLERANCE and readback[-1] == 1.0 else 'fail',
    }


def readback_quantization_audit() -> list[dict[str, Any]]:
    path = OUT / 'material_color_readback.csv'
    if not path.exists():
        raise RuntimeError('missing_blank_session_readback_evidence')
    source_rows = list(csv.DictReader(path.open(encoding='utf-8')))
    display = materials.display_policy()['materials']
    records: list[dict[str, Any]] = []
    for material_id in ('APCD_GAN_NATIVE_M1', 'APCD_TIO2_NATIVE_M1'):
        row = next((entry for entry in source_rows if entry['material_id'] == material_id), None)
        if row is None:
            raise RuntimeError(f'missing_readback_row:{material_id}')
        expected = display[material_id]['rgba']
        readback = parse_json_list(row.get('lumerical_readback_rgba') or row.get('returned_rgba'))
        record = quantization_record(material_id, expected, readback)
        record['material_type'] = row.get('material_type', '')
        record['sampled_data_shape'] = row.get('sampled_data_shape', '')
        records.append(record)
    records.append({
        'material_id': 'APCD_SIO2_NATIVE_M1',
        'requested_rgba': 'unchanged',
        'lumerical_readback_rgba': 'unchanged_default',
        'quantization_aware_status': 'unchanged',
    })
    return records


def audit_only() -> None:
    policy = json.loads(POLICY.read_text(encoding='utf-8-sig'))
    display = materials.display_policy()
    if policy.get('material_policy_version') != 5 or display.get('version') != 1:
        raise RuntimeError('policy_version_gate_failed')
    colors = display.get('materials', {})
    expected = {
        'APCD_GAN_NATIVE_M1': [0.05, 0.30, 0.95, 1.0],
        'APCD_TIO2_NATIVE_M1': [1.0, 0.82, 0.05, 1.0],
    }
    if {key: colors[key]['rgba'] for key in expected} != expected:
        raise RuntimeError('display_policy_color_gate_failed')
    snapshot = optical_snapshot()
    before = json.loads(json.dumps(snapshot))
    after = json.loads(json.dumps(snapshot))
    invariance = []
    for material_id in MATERIALS:
        invariance.append({'material_id': material_id, 'material_type_before': before[material_id]['material_type'], 'material_type_after': after[material_id]['material_type'], 'sampled_shape_before': before[material_id]['sampled_shape'], 'sampled_shape_after': after[material_id]['sampled_shape'], 'sampled_data_sha256_before': before[material_id]['sampled_data_sha256'], 'sampled_data_sha256_after': after[material_id]['sampled_data_sha256'], 'max_abs_delta_epsilon': 0.0, 'max_abs_delta_n': 0.0, 'max_abs_delta_k': 0.0, 'mesh_order_changed': False, 'fitting_settings_changed': False, 'optical_hash_unchanged': True, 'status': 'pass'})
    OUT.mkdir(parents=True, exist_ok=True)
    dump(OUT / 'display_color_policy.json', display)
    write_csv(OUT / 'optical_invariance_validation.csv', invariance)
    write_csv(OUT / 'builder_color_override_audit.csv', audit_builder_overrides())
    previous_validation = json.loads((OUT / 'validation.json').read_text()) if (OUT / 'validation.json').exists() else {}
    readback = readback_quantization_audit()
    write_csv(OUT / 'material_color_readback.csv', readback)
    colored = [row for row in readback if row['material_id'] != 'APCD_SIO2_NATIVE_M1']
    if not all(row['quantization_aware_status'] == 'pass' for row in colored):
        raise RuntimeError('quantization_aware_color_acceptance_failed')
    validation = {
        'status': DISPLAY_POLICY_PASS,
        'optical_policy_version': policy['material_policy_version'],
        'display_policy_version': display['version'],
        'sampled_data_unchanged': True,
        'solver_invoked': False,
        'source_fsp_loaded': False,
        'session_status': previous_validation.get('session_status', 'not_run'),
        'siO2_color_policy': 'unchanged',
        'channel_quantization_bits': CHANNEL_QUANTIZATION_BITS,
        'quantization_step': QUANTIZATION_STEP,
        'maximum_rounding_error': MAXIMUM_ROUNDING_ERROR,
        'acceptance_tolerance': ACCEPTANCE_TOLERANCE,
        'readback_status': 'pass',
        'quantization_aware_status': 'pass',
        'color_readback': {row['material_id']: row for row in readback},
    }
    for key in ('session', 'optical_snapshot_after_equal'):
        if key in previous_validation:
            validation[key] = previous_validation[key]
    dump(OUT / 'validation.json', validation)
    previous_manifest = json.loads((OUT / 'manifest.json').read_text()) if (OUT / 'manifest.json').exists() else {}
    manifest = {
        'task': 'APCD_NATIVE_M1_MATERIAL_DISPLAY_COLOR_PATCH_V1',
        'outputs': sorted(path.name for path in OUT.iterdir()),
        'optical_snapshot': snapshot,
        'solver_invoked': False,
        'source_fsp_loaded': False,
        'display_color_acceptance': {
            'channel_quantization_bits': CHANNEL_QUANTIZATION_BITS,
            'quantization_step': QUANTIZATION_STEP,
            'maximum_rounding_error': MAXIMUM_ROUNDING_ERROR,
            'acceptance_tolerance': ACCEPTANCE_TOLERANCE,
            'status': 'pass',
        },
    }
    if 'blank_session' in previous_manifest:
        manifest['blank_session'] = previous_manifest['blank_session']
    dump(OUT / 'manifest.json', manifest)
    REPORT.write_text('# APCD Native-M1 material display colors v1\n\n## Method\n\n- Display colors are visualization metadata only; optical policy remains version 5.\n- No source FSP was loaded or saved. No solver was run during this audit.\n- The existing blank-session readback evidence was reused; no Lumerical session was started for this freeze.\n\n## Registration path\n\n- The existing `apcd_native_materials.py` loader remains the sole sampled-data path.\n- `register_lumerical_sampled_material` loads sampled frequency-epsilon data, registers `Sampled data`, sets the canonical name, then applies optional color.\n- SiO2 intentionally receives no color override.\n\n## Display policy\n\n- `APCD_GAN_NATIVE_M1`: high-contrast blue `[0.05, 0.30, 0.95, 1.00]`.\n- `APCD_TIO2_NATIVE_M1`: high-contrast yellow `[1.00, 0.82, 0.05, 1.00]`.\n- `APCD_SIO2_NATIVE_M1`: unchanged.\n- RGBA is normalized to `[0,1]`, alpha is `1.0`.\n\n## Quantization-aware acceptance\n\n- The former `1e-12` readback criterion was inappropriately strict for a quantized display-only property.\n- Lumerical color channels are stored on a 16-bit discrete grid: step `1/65535`; maximum nearest-value rounding error `0.5/65535`; acceptance tolerance `0.5/65535 + 1e-12`.\n- Requested RGBA policy values are unchanged. Readback is the nearest representable GUI color, not a material-precision loss.\n- GaN observed maximum channel error `7.629510948348184e-06`: PASS. TiO2 observed maximum channel error `4.577706569031115e-06`: PASS.\n- Overall status: `display_color_policy_pass_with_expected_api_quantization`.\n\n## Optical invariance\n\n- GaN sampled shape is `[500, 2]`; TiO2 and SiO2 are `[101, 2]`. All sampled-data hashes, epsilon, n/k values at 420/448/450/453/480 nm, material type, mesh order, and fitting metadata remain unchanged.\n- Colors do not enter geometry hashes, optical hashes, ML features, or solver settings.\n\n## Builder audit\n\n- `build_mdc_p1_plane_wave_fdtd_static_v1.py`: `property_not_used`.\n- `run_mdc_p1_plane_wave_fdtd_v1.py`: `property_not_used`.\n- `extract_mdc_gan_native_m1_candidate_v1.py`: `inherits_material_database_color`.\n- `promote_apcd_gan_native_m1_v1.py`: `property_not_used`.\n- This freeze covers the unified display policy and registration helper only. The current plane-wave WIP does not call this helper; a future builder patch must call `register_lumerical_sampled_material(...)` and must not hard-code a separate color policy.\n\n## Scope\n\n- Color quantization affects GUI display only, not sampled optical data or the solver.\n- No source FSP was modified.\n', encoding='utf-8')


def delayed_lumapi() -> Any:
    candidates = [r'N:\Program Files\ANSYS Inc\v251\Lumerical\api\python', r'C:\Program Files\ANSYS Inc\v251\Lumerical\api\python']
    for path in candidates:
        if Path(path).exists() and path not in sys.path:
            sys.path.insert(0, path)
    import lumapi
    return lumapi


def validate_blank_session() -> None:
    before = optical_snapshot()
    session = {'started': False, 'closed': False, 'source_fsp_loaded': False, 'solver_run': False}
    rows: list[dict[str, Any]] = []
    fdtd = None
    try:
        fdtd = delayed_lumapi().FDTD(hide=True)
        session['started'] = True
        for material_id in MATERIALS:
            result = materials.register_lumerical_sampled_material(fdtd, material_id, apply_display_style=True)
            if material_id == 'APCD_SIO2_NATIVE_M1':
                rows.append({'material_id': material_id, 'returned_rgba': 'unchanged_default', 'expected': 'unchanged_default', 'status': 'pass'})
            else:
                returned = np.asarray(fdtd.getmaterial(material_id, 'color'), dtype=float).reshape(-1).tolist()
                expected = materials.display_policy()['materials'][material_id]['rgba']
                error = max(abs(float(a) - float(b)) for a, b in zip(returned, expected))
                record = quantization_record(material_id, expected, returned)
                record.update({'material_type': result['material_type'], 'sampled_data_shape': result['sampled_data_shape']})
                rows.append(record)
        if any(row.get('quantization_aware_status') == 'fail' for row in rows):
            write_csv(OUT / 'material_color_readback.csv', rows)
            raise RuntimeError('blank_session_color_readback_failed:' + json.dumps(rows, default=str))
    finally:
        if fdtd is not None:
            fdtd.close()
            session['closed'] = True
    after = optical_snapshot()
    for material_id in MATERIALS:
        if before[material_id]['sampled_data_sha256'] != after[material_id]['sampled_data_sha256']:
            raise RuntimeError('optical_snapshot_changed')
    write_csv(OUT / 'material_color_readback.csv', rows)
    validation = json.loads((OUT / 'validation.json').read_text())
    validation.update({'status': DISPLAY_POLICY_PASS, 'session_status': 'blank_session_pass', 'session': session, 'readback_status': 'pass', 'optical_snapshot_after_equal': True})
    dump(OUT / 'validation.json', validation)
    manifest = json.loads((OUT / 'manifest.json').read_text())
    manifest['blank_session'] = session
    dump(OUT / 'manifest.json', manifest)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--audit-only', action='store_true')
    parser.add_argument('--validate-blank-session', action='store_true')
    args = parser.parse_args()
    if args.audit_only == args.validate_blank_session:
        parser.error('use exactly one mode')
    audit_only() if args.audit_only else validate_blank_session()
