import json
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, r'N:/Program Files/ANSYS Inc/v251/Lumerical/api/python')
import lumapi

ROOT = Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
STAGE = ROOT / 'outputs/np_k6_m2_batch1_hf_acquisition_v1'
PREFSP = STAGE / 'runtime_prefsp'
CASES_DIR = STAGE / 'cases'
PILOT_STACK = 'NP_K6_INDEPENDENT_STACK_PILOT_V1'
GENERATOR = 'NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_3PS_V2'
MESH_ID = 'NP_K6_PILOT_FIXED_GRID_V2'
SOURCE = ROOT / 'outputs/np_k6_p0_remaining_five_anchors_execution_v1/runtime_prefsp/RUN3A_P_PILOT_HF_V1.fsp'
CASES = [
    ('NP_K6_M2_BATCH1_G01_P', 'U1', 'p', [200,205,215,220,225,230]),
    ('NP_K6_M2_BATCH1_G01_S', 'U1', 's', [200,205,215,220,225,230]),
    ('NP_K6_M2_BATCH1_G02_P', 'U2', 'p', [100,140,145,155,225,230]),
    ('NP_K6_M2_BATCH1_G02_S', 'U2', 's', [100,140,145,155,225,230]),
    ('NP_K6_M2_BATCH1_G03_P', 'D1', 'p', [100,200,205,210,215,220]),
    ('NP_K6_M2_BATCH1_G03_S', 'D1', 's', [100,200,205,210,215,220]),
    ('NP_K6_M2_BATCH1_G04_P', 'D2', 'p', [100,110,115,220,225,230]),
    ('NP_K6_M2_BATCH1_G04_S', 'D2', 's', [100,110,115,220,225,230]),
    ('NP_K6_M2_BATCH1_G05_P', 'X1', 'p', [100,130,135,155,160,225]),
    ('NP_K6_M2_BATCH1_G05_S', 'X1', 's', [100,130,135,155,160,225]),
    ('NP_K6_M2_BATCH1_G06_P', 'P1', 'p', [100,105,115,120,125,130]),
    ('NP_K6_M2_BATCH1_G06_S', 'P1', 's', [100,105,115,120,125,130]),
]
REQUIRED = ['reflection_monitor', 'transmission_monitor', 'order_monitor', 'field_450_monitor',
            'N1_DIAG_PML_LOWER', 'N1_DIAG_LOWER_OUTSIDE', 'N1_DIAG_LOWER_INSIDE',
            'N1_DIAG_UPPER_INSIDE', 'N1_DIAG_UPPER_OUTSIDE', 'N1_DIAG_PML_UPPER',
            'N1_DIAG_XZ_INDEX_449']
PILLAR_POS = [-725, -435, -145, 145, 435, 725]
WAVELENGTHS = list(range(445, 456))

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()

def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str), encoding='utf-8')

def get_named(fdtd, name, prop):
    try:
        value = fdtd.getnamed(name, prop)
        return value.tolist() if hasattr(value, 'tolist') else value
    except Exception as exc:
        return f'UNAVAILABLE:{exc}'

def object_names(fdtd):
    fdtd.eval("groupscope('::model'); unselectall; selectall;")
    names = []
    for obj in fdtd.getAllSelectedObjects():
        try:
            names.append({'name': str(obj.name), 'type': str(obj.type)})
        except Exception:
            pass
    return names

def monitor_readback(fdtd, name):
    props = ['type', 'monitor type', 'x', 'y', 'z', 'x span', 'y span', 'z span',
             'frequency points', 'use source limits', 'use wavelength spacing',
             'spatial interpolation', 'override global monitor settings',
             'wavelength center', 'wavelength span', 'down sample X', 'down sample Y', 'down sample Z']
    return {prop: get_named(fdtd, name, prop) for prop in props}

def material_readback(fdtd, name):
    out = {'type': str(fdtd.getmaterial(name, 'type'))}
    try:
        sampled = fdtd.getmaterial(name, 'sampled data')
        out['sampled_rows'] = len(sampled)
        out['sampled_data_sha256'] = digest(sampled.tolist() if hasattr(sampled, 'tolist') else sampled)
        if len(sampled):
            out['sampled_first'] = str(sampled[0])
            out['sampled_last'] = str(sampled[-1])
    except Exception as exc:
        out['sampled_rows'] = 0
        out['sampled_data_error'] = str(exc)
    return out

def geometry_contract(fdtd, diameters):
    pillars = []
    for i, diameter in enumerate(diameters):
        name = f'TiO2_pillar_{i}'
        pillars.append({
            'name': name,
            'x_nm': float(get_named(fdtd, name, 'x') * 1e9),
            'y_nm': float(get_named(fdtd, name, 'y') * 1e9),
            'z_min_nm': float(get_named(fdtd, name, 'z min') * 1e9),
            'z_max_nm': float(get_named(fdtd, name, 'z max') * 1e9),
            'diameter_nm': float(get_named(fdtd, name, 'radius') * 2e9),
            'material': str(get_named(fdtd, name, 'material')),
            'expected_diameter_nm': diameter,
        })
    return {
        'period_x_nm': float(get_named(fdtd, 'FDTD', 'x span') * 1e9),
        'period_y_nm': float(get_named(fdtd, 'FDTD', 'y span') * 1e9),
        'pillar_height_nm': 500.0,
        'pillars': pillars,
    }

def main():
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    source_sha = sha256(SOURCE)
    STAGE.mkdir(parents=True, exist_ok=True)
    PREFSP.mkdir(parents=True, exist_ok=True)
    d0 = json.loads((ROOT / 'outputs/np_k6_ml_d0_database_foundation_v1/k6_hf_pilot_geometry_manifest.json').read_text(encoding='utf-8-sig'))
    geometry_map = {row['geometry_id']: row for row in d0['rows']}
    source_probe = lumapi.FDTD(str(SOURCE), hide=True)
    try:
        source_names = object_names(source_probe)
        source_mesh = {p: get_named(source_probe, 'RUN3C_FIXED_NESTED_N2', p) for p in ['x', 'y', 'z', 'x span', 'y span', 'z span', 'dx', 'dy', 'dz']}
        source_fdt = {p: get_named(source_probe, 'FDTD', p) for p in ['mesh accuracy', 'mesh refinement', 'x span', 'y span', 'z span']}
        source_materials = {m: material_readback(source_probe, m) for m in ['APCD_TIO2_NATIVE_M1', 'APCD_SIO2_NATIVE_M1']}
        source_monitor = {name: monitor_readback(source_probe, name) for name in REQUIRED}
        source_source = {p: get_named(source_probe, 'source_x_forward', p) for p in ['direction', 'injection axis', 'x', 'y', 'z', 'x span', 'y span', 'wavelength start', 'wavelength stop']}
    finally:
        source_probe.close()
    missing_source = [x for x in REQUIRED if x not in [o['name'] for o in source_names]]
    if missing_source:
        raise RuntimeError(f'missing frozen objects in source: {missing_source}')
    source_contract = {
        'source_prefsp_path': str(SOURCE), 'source_prefsp_sha256': source_sha,
        'source_object_names': source_names, 'mesh_readback': source_mesh,
        'fdtd_readback': source_fdt, 'material_readback': source_materials,
        'monitor_readback': source_monitor, 'source_readback': source_source,
        'source_sha_stable': sha256(SOURCE) == source_sha,
    }
    dump(STAGE / 'source_lineage_audit.json', source_contract)
    rows = []
    common_mesh = {'origin_nm': [-870, -145, -100], 'bounds_nm': {'x': [-870, 870], 'y': [-145, 145], 'z': [-100, 600]}, 'dx_dy_dz_nm': [5, 5, 5], 'mesh_accuracy_readback': source_fdt['mesh accuracy'], 'mesh_refinement_readback': source_fdt['mesh refinement']}
    for case_order, (case_id, role, pol, diameters) in enumerate(CASES, 1):
        geometry_id = 'K6X_D' + '_D'.join(str(x) for x in diameters)
        if geometry_id not in geometry_map:
            raise RuntimeError(f'geometry not in D0 manifest: {geometry_id}')
        geometry_hash = geometry_map[geometry_id]['geometry_hash']
        setup_path = PREFSP / f'{case_id}.fsp'
        if setup_path.exists():
            raise RuntimeError(f'refusing overwrite of {setup_path}')
        setup = lumapi.FDTD(str(SOURCE), hide=True)
        changes = []
        try:
            for i, diameter in enumerate(diameters):
                name = f'TiO2_pillar_{i}'
                old_radius = float(get_named(setup, name, 'radius'))
                new_radius = diameter * 0.5e-9
                if abs(old_radius - new_radius) > 1e-20:
                    setup.setnamed(name, 'radius', new_radius)
                    changes.append({'object': name, 'property': 'radius', 'from_m': old_radius, 'to_m': new_radius, 'reason': 'geometry_identity'})
            old_pol = float(get_named(setup, 'source_x_forward', 'polarization angle'))
            new_pol = 0.0 if pol == 'p' else 90.0
            if abs(old_pol - new_pol) > 1e-12:
                setup.setnamed('source_x_forward', 'polarization angle', new_pol)
                changes.append({'object': 'source_x_forward', 'property': 'polarization angle', 'from_deg': old_pol, 'to_deg': new_pol, 'reason': 'p_s_mapping'})
            setup.save(str(setup_path))
        finally:
            setup.close()
        reloaded = lumapi.FDTD(str(setup_path), hide=True)
        try:
            names = object_names(reloaded)
            mesh = {p: get_named(reloaded, 'RUN3C_FIXED_NESTED_N2', p) for p in ['x', 'y', 'z', 'x span', 'y span', 'z span', 'dx', 'dy', 'dz']}
            fdt = {p: get_named(reloaded, 'FDTD', p) for p in ['mesh accuracy', 'mesh refinement', 'x span', 'y span', 'z span']}
            src = {p: get_named(reloaded, 'source_x_forward', p) for p in ['direction', 'injection axis', 'polarization angle', 'x', 'y', 'z', 'x span', 'y span', 'wavelength start', 'wavelength stop']}
            monitors = {name: monitor_readback(reloaded, name) for name in REQUIRED}
            materials = {name: material_readback(reloaded, name) for name in ['APCD_TIO2_NATIVE_M1', 'APCD_SIO2_NATIVE_M1']}
            geometry = geometry_contract(reloaded, diameters)
        finally:
            reloaded.close()
        missing = [x for x in REQUIRED if x not in [o['name'] for o in names]]
        geom_ok = all(abs(p['diameter_nm'] - p['expected_diameter_nm']) < 1e-6 for p in geometry['pillars'])
        mesh_ok = all(abs(float(mesh[k]) - float(source_mesh[k])) < 1e-30 for k in ['x', 'y', 'z', 'x span', 'y span', 'z span', 'dx', 'dy', 'dz'])
        monitor_ok = monitors == source_monitor
        material_ok = all(materials[m]['type'] == 'Sampled 3D data' and materials[m]['sampled_rows'] == 101 for m in materials)
        source_ok = src['direction'] == source_source['direction'] and src['injection axis'] == source_source['injection axis'] and abs(float(src['wavelength start']) - float(source_source['wavelength start'])) < 1e-20 and abs(float(src['wavelength stop']) - float(source_source['wavelength stop'])) < 1e-20
        unexpected = []
        if missing: unexpected.append({'kind': 'missing_required_objects', 'objects': missing})
        if not geom_ok: unexpected.append({'kind': 'geometry_readback_mismatch'})
        if not mesh_ok: unexpected.append({'kind': 'mesh_contract_drift'})
        if not monitor_ok: unexpected.append({'kind': 'monitor_contract_drift'})
        if not material_ok: unexpected.append({'kind': 'material_provenance_drift'})
        if not source_ok: unexpected.append({'kind': 'source_contract_drift'})
        setup_sha = sha256(setup_path)
        case_dir = CASES_DIR / case_id
        ledger = {
            'case_id': case_id, 'attempt_id': 'attempt_001', 'case_order': case_order,
            'source_prefsp_path': str(setup_path), 'source_prefsp_sha256': setup_sha,
            'geometry_id': geometry_id, 'geometry_hash': geometry_hash, 'polarization': pol,
            'u_x': 0.0, 'k_y': 0.0, 'interface_stack_id': PILOT_STACK,
            'production_generator_id': GENERATOR, 'production_mesh_id': MESH_ID,
            'entered': False, 'run_invocation_count': 0, 'engine_completed': False,
            'controller_returned': False, 'post_saved': False, 'solver_authorized': True,
            'provisional_hf_label': True, 'training_label': False, 'diagnostic_only': False,
            'candidate_performance_label': False, 'pilot_scope_only': True,
            'final_mdc_stack_compatible': False, 'bulk_mdc_compatible': False,
            'timestamps': {'created_utc': datetime.now(timezone.utc).isoformat()},
            'host': 'DESKTOP-NNE313K', 'lumerical_version': 'Ansys Lumerical 2025 R1', 'python_path': 'N:/anaconda_envs/RCP_LCP/python.exe',
        }
        contract_core = {
            'case_id': case_id, 'case_order': case_order, 'role': role, 'geometry_id': geometry_id, 'geometry_hash': geometry_hash,
            'polarization': pol, 'u_x': 0.0, 'k_y': 0.0, 'interface_stack_id': PILOT_STACK,
            'production_generator_id': GENERATOR, 'production_mesh_id': MESH_ID, 'wavelengths_nm': WAVELENGTHS,
            'mesh_contract': common_mesh, 'geometry_contract': geometry, 'source_contract': src, 'monitor_contract': monitors,
            'material_contract': materials, 'parent_source_sha256': source_sha, 'expected_changes': changes,
            'setup_only': True, 'solver_entered': 0, 'entered': False, 'run_invocation_count': 0,
            'provisional_hf_label': True, 'training_label': False, 'candidate_performance_label': False,
            'pilot_scope_only': True, 'final_mdc_stack_compatible': False, 'bulk_mdc_compatible': False,
        }
        audit = {
            'case_id': case_id, 'setup_sha256': setup_sha, 'parent_source_sha256': source_sha,
            'expected_changes': changes, 'added_objects': [], 'removed_objects': [], 'modified_properties': changes,
            'unexpected_differences': unexpected, 'geometry_readback': geometry, 'mesh_readback': mesh,
            'fdtd_readback': fdt, 'source_readback': src, 'monitor_readback': monitors, 'material_readback': materials,
            'native_m1_sampled_confirmed': material_ok, 'exact_wavelength_contract_nm': WAVELENGTHS,
            'actual_solver_grid_equality_proven': False, 'setup_diff_pass': not unexpected,
            'independent_reload': True, 'run_called': False, 'save_called_after_reload': False,
        }
        contract = dict(contract_core); contract['contract_hash'] = digest(contract_core)
        dump(case_dir / 'setup_contract.json', contract)
        dump(case_dir / 'setup_readback_audit.json', audit)
        dump(case_dir / 'setup_checksum.json', {'path': str(setup_path), 'sha256': setup_sha, 'size_bytes': setup_path.stat().st_size, 'sha_stable_after_reload': sha256(setup_path) == setup_sha})
        dump(case_dir / 'attempt_ledger.json', ledger)
        rows.append({'case_id': case_id, 'case_order': case_order, 'role': role, 'geometry_id': geometry_id, 'geometry_hash': geometry_hash, 'polarization': pol, 'setup_path': str(setup_path), 'setup_sha256': setup_sha, 'setup_diff_pass': not unexpected, 'entered': False, 'run_invocation_count': 0})
    root_manifest = {
        'stage': 'NP_K6_M2_BATCH1_FDTD_ACQUISITION_V1', 'batch_id': 'NP_K6_M2_BATCH1', 'task_count': 12,
        'generator_id': GENERATOR, 'pilot_mesh_id': MESH_ID, 'interface_stack_id': PILOT_STACK,
        'pilot_scope_only': True, 'final_mdc_stack_compatible': False, 'bulk_mdc_compatible': False,
        'source_lineage_path': str(SOURCE), 'source_lineage_sha256': source_sha,
        'fixed_grid_contract': common_mesh, 'wavelengths_nm': WAVELENGTHS, 'u_x': 0.0, 'k_y': 0.0,
        'materials': source_materials, 'cases': rows, 'strict_order': [c[0] for c in CASES],
        'setup_only': True, 'solver_entered': 0, 'run_invocation_count': 0, 'sealed_test_touched': False,
        'all_setup_diff_pass': all(r['setup_diff_pass'] for r in rows),
        'created_utc': datetime.now(timezone.utc).isoformat(), 'schema_version': 'np_k6_m2_batch1_setup_manifest_v1',
    }
    dump(STAGE / 'pilot_generator_manifest.json', root_manifest)
    dump(STAGE / 'pilot_setup_preflight.json', {'stage': root_manifest['stage'], 'cases': rows, 'all_setup_diff_pass': root_manifest['all_setup_diff_pass'], 'solver_entered': 0, 'run_invocation_count': 0, 'sealed_test_touched': False, 'source_sha_stable': sha256(SOURCE) == source_sha, 'hard_gate': None if root_manifest['all_setup_diff_pass'] else 'HARD_GATE_NP_K6_P0_SETUP_CONTRACT_DRIFT'})
    dump(STAGE / 'solver_zero_audit.json', {'solver_run_called': False, 'solver_entered': 0, 'engine_completed': 0, 'controller_returned': 0, 'post_saved': 0, 'case_count': 6, 'scheduler_registered': False, 'sealed_test_touched': False})
    dump(STAGE / 'state.json', {'state': 'READY_FOR_NP_K6_HF_P0_SEQUENTIAL_SOLVER_EXECUTION' if root_manifest['all_setup_diff_pass'] else 'HARD_GATE_NP_K6_P0_SETUP_CONTRACT_DRIFT', 'generator_id': GENERATOR, 'pilot_mesh_id': MESH_ID, 'interface_stack_id': PILOT_STACK, 'formal_hf_label_count': 0, 'training_label_count': 0, 'production_mesh_frozen': False, 'solver_entered': 0, 'all_setup_diff_pass': root_manifest['all_setup_diff_pass']})
    print(json.dumps({'stage': str(STAGE), 'source_sha256': source_sha, 'cases': rows, 'all_setup_diff_pass': root_manifest['all_setup_diff_pass'], 'solver_entered': 0}, indent=2))

if __name__ == '__main__':
    main()
