import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'outputs/np_k6_hf_p0_label_generator_recovery_v1'
EXPECTED_ORDER = [
    'RUN3C_P_PILOT_HF_V1', 'RUN3C_S_PILOT_HF_V1',
    'RUN3A_P_PILOT_HF_V1', 'RUN3A_S_PILOT_HF_V1',
    'RUN3B_P_PILOT_HF_V1', 'RUN3B_S_PILOT_HF_V1',
]
EXPECTED_GENERATOR = 'NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_V1'
EXPECTED_MESH = 'NP_K6_PILOT_FIXED_GRID_V1'
EXPECTED_STACK = 'NP_K6_INDEPENDENT_STACK_PILOT_V1'

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def main():
    errors = []
    manifest_path = STAGE / 'pilot_generator_manifest.json'
    preflight_path = STAGE / 'pilot_setup_preflight.json'
    if not manifest_path.exists():
        errors.append('missing pilot_generator_manifest.json')
        print(json.dumps({'status': 'FAIL', 'errors': errors}, indent=2))
        return 1
    manifest = read(manifest_path)
    preflight = read(preflight_path)
    if manifest.get('generator_id') != EXPECTED_GENERATOR: errors.append('generator_id')
    if manifest.get('pilot_mesh_id') != EXPECTED_MESH: errors.append('pilot_mesh_id')
    if manifest.get('interface_stack_id') != EXPECTED_STACK: errors.append('interface_stack_id')
    for key in ['pilot_scope_only', 'final_mdc_stack_compatible', 'bulk_mdc_compatible']:
        expected = key == 'pilot_scope_only'
        if manifest.get(key) is not expected: errors.append(key)
    if manifest.get('strict_order') != EXPECTED_ORDER: errors.append('strict_order')
    if manifest.get('wavelengths_nm') != list(range(445, 456)): errors.append('wavelength grid')
    if manifest.get('u_x') != 0.0 or manifest.get('k_y') != 0.0: errors.append('incidence')
    if manifest.get('solver_entered') != 0 or manifest.get('run_invocation_count') != 0: errors.append('root solver zero')
    rows = manifest.get('cases', [])
    if len(rows) != 6: errors.append('case count')
    d0 = read(ROOT / 'outputs/np_k6_ml_d0_database_foundation_v1/k6_hf_pilot_geometry_manifest.json')
    d0_hashes = {r['geometry_id']: r['geometry_hash'] for r in d0['rows']}
    mesh_signatures = []
    monitor_signatures = []
    for i, case_id in enumerate(EXPECTED_ORDER):
        row = next((r for r in rows if r.get('case_id') == case_id), None)
        if row is None:
            errors.append(f'missing row {case_id}')
            continue
        cdir = STAGE / 'cases' / case_id
        setup = Path(row['setup_path'])
        if not setup.exists(): errors.append(f'missing setup {case_id}')
        else:
            actual_sha = sha256(setup)
            if actual_sha != row.get('setup_sha256'): errors.append(f'setup sha {case_id}')
        contract = read(cdir / 'setup_contract.json')
        audit = read(cdir / 'setup_readback_audit.json')
        checksum = read(cdir / 'setup_checksum.json')
        ledger = read(cdir / 'attempt_ledger.json')
        if contract.get('geometry_hash') != d0_hashes.get(contract.get('geometry_id')): errors.append(f'geometry hash {case_id}')
        if not audit.get('setup_diff_pass'): errors.append(f'setup diff {case_id}')
        if audit.get('unexpected_differences') != []: errors.append(f'unexpected differences {case_id}')
        if audit.get('native_m1_sampled_confirmed') is not True: errors.append(f'materials {case_id}')
        if contract.get('wavelengths_nm') != list(range(445, 456)): errors.append(f'wavelength contract {case_id}')
        if contract.get('entered') is not False or contract.get('run_invocation_count') != 0: errors.append(f'contract ledger zero {case_id}')
        for k in ['entered', 'engine_completed', 'controller_returned', 'post_saved']:
            if ledger.get(k) is not False: errors.append(f'ledger {k} {case_id}')
        if ledger.get('run_invocation_count') != 0: errors.append(f'ledger run zero {case_id}')
        if checksum.get('sha256') != row.get('setup_sha256') or checksum.get('sha_stable_after_reload') is not True: errors.append(f'checksum {case_id}')
        mesh = audit.get('mesh_readback', {})
        mesh_signatures.append(tuple(mesh.get(k) for k in ['x', 'y', 'z', 'x span', 'y span', 'z span', 'dx', 'dy', 'dz']))
        monitor_signatures.append(json.dumps(audit.get('monitor_readback', {}), sort_keys=True, default=str))
        if contract.get('production_generator_id') != EXPECTED_GENERATOR: errors.append(f'generator contract {case_id}')
        if contract.get('production_mesh_id') != EXPECTED_MESH: errors.append(f'mesh contract {case_id}')
        if contract.get('interface_stack_id') != EXPECTED_STACK: errors.append(f'stack contract {case_id}')
        if contract.get('pilot_scope_only') is not True or contract.get('bulk_mdc_compatible') is not False: errors.append(f'scope contract {case_id}')
    if mesh_signatures and any(sig != mesh_signatures[0] for sig in mesh_signatures): errors.append('cross-case mesh identity')
    if monitor_signatures and any(sig != monitor_signatures[0] for sig in monitor_signatures): errors.append('cross-case monitor identity')
    if preflight.get('all_setup_diff_pass') is not True: errors.append('preflight all_setup_diff_pass')
    if read(STAGE / 'solver_zero_audit.json').get('solver_entered') != 0: errors.append('solver_zero_audit')
    result = {'status': 'PASS_NP_K6_P0_SETUP_VALIDATOR' if not errors else 'FAIL_NP_K6_P0_SETUP_VALIDATOR', 'errors': errors, 'case_count': len(rows), 'solver_entered': 0 if not errors else 'unknown', 'sealed_test_touched': manifest.get('sealed_test_touched')}
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1

if __name__ == '__main__':
    raise SystemExit(main())
