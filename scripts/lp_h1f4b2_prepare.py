from __future__ import annotations
import copy, hashlib, importlib.util, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/stage_h1f4b2_grouped_d_j1_combined_local_validation'
H1F4A_REPORT = ROOT / 'reports/stage_h1f4a_grouped_d_first_harmonic_jacobian_probe'
H1F4A_PHASE2 = ROOT / 'reports/stage_h1f4a_phase2_grouped_d_transfer_validation'
H1F4B1_REPORT = ROOT / 'reports/stage_h1f4b1_j1_anisotropy_fullk6_compensator_probe'
PRIMARY_UID = 'K6_L1_C_POS_PLUS10'
PRIMARY_HASH = 'a8606d8f44a4675db08493c3dd95c8ea43f30882d3a9bbb18a65b59c2ba45198'
AD = 4.0
GRID = [450.0 + 0.5*i for i in range(9)]
POLS = ['x', 'y']
MODE = 'J1_length=J1_side+delta_nm; J1_width=J1_side-delta_nm; preserve mean dimension and all six-site local-axis convention'

def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def write(name, value):
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT/name).write_text(json.dumps(value, indent=2), encoding='utf-8')
def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def legality(candidate):
    # Reuse the already audited H1F4B1 polygon legality implementation.
    path = ROOT / 'scripts/lp_h1f4b1_prepare.py'
    spec = importlib.util.spec_from_file_location('h1f4b1_prepare_for_legality', path)
    mod = importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(mod)
    return mod.legality(candidate)

def main():
    a = read(H1F4A_REPORT/'grouped_d_candidate_manifest.json')
    rule = read(H1F4A_PHASE2/'H1F4A_PHASE2_DIRECTION_RULE_V1.json')
    b = read(H1F4B1_REPORT/'h1f4b1_jacobian_cancellation_analysis.json')
    b1_manifest = read(H1F4B1_REPORT/'j1_anisotropy_candidate_manifest.json')
    r = float(b['cancellation']['r_cancel'])
    children = a['children']
    source = {c['candidate_uid']: c for c in children if c.get('base_candidate_uid') == PRIMARY_UID}
    if set(source) != {'H1F4A_K6_L1_C_POS_PLUS10_A_PLUS', 'H1F4A_K6_L1_C_POS_PLUS10_A_MINUS', 'H1F4A_K6_L1_C_POS_PLUS10_B_PLUS', 'H1F4A_K6_L1_C_POS_PLUS10_B_MINUS'}:
        raise RuntimeError('H1F4B2 grouped-D source children incomplete')
    if a['primary_seed']['primary_seed_frozen_hash'] != PRIMARY_HASH:
        raise RuntimeError('H1F4B2 primary hash drift')
    if rule['u_a'] != b['grouped_d_directional_jacobian']['u_a'] or rule['u_b'] != b['grouped_d_directional_jacobian']['u_b']:
        raise RuntimeError('H1F4B2 direction rule drift')
    if b1_manifest['parent_hash'] != PRIMARY_HASH or b1_manifest['grouped_d_perturbation_nm'] != 0.0:
        raise RuntimeError('H1F4B1 authority drift')
    exact_delta = r * AD
    plus_source = source['H1F4A_K6_L1_C_POS_PLUS10_A_PLUS']
    minus_source = source['H1F4A_K6_L1_C_POS_PLUS10_A_MINUS']
    child_specs = [("H1F4B2_K6_L1_C_POS_PLUS10_COMBINED_PLUS", AD, exact_delta, plus_source),
                   ("H1F4B2_K6_L1_C_POS_PLUS10_COMBINED_MINUS", -AD, -exact_delta, minus_source)]
    out_children = []
    for uid, ad, dj, src in child_specs:
        c = copy.deepcopy(src)
        c['candidate_uid'] = uid
        c['base_candidate_uid'] = PRIMARY_UID
        c['base_candidate_hash'] = PRIMARY_HASH
        c['A_D_nm'] = ad
        c['delta_J1_nm'] = dj
        c['grouped_d_direction_phi_deg'] = rule['phi_D_star_deg']
        c['grouped_d_direction_u'] = {'u_a': rule['u_a'], 'u_b': rule['u_b']}
        c['j1_anisotropy_mode'] = MODE
        c['grouped_d_perturbation_nm'] = ad
        c['no_new_seed'] = True
        c['ml_admitted'] = False
        for g in c['local_geometries']:
            side = float(g['J1_side_nm'])
            g['J1_length_nm'] = side + dj
            g['J1_width_nm'] = side - dj
            g['J1_mean_dimension_nm'] = side
        c['geometry_legality'] = legality(c)
        c['candidate_hash'] = digest({k:v for k,v in c.items() if k != 'candidate_hash'})
        c['physical_canonical_hash'] = c['candidate_hash']
        c['solver_case_uids'] = [f'{uid}_x', f'{uid}_y']
        out_children.append(c)
    if not all(c['geometry_legality']['pass'] for c in out_children):
        raise RuntimeError('H1F4B2_COMBINED_GEOMETRY_ILLEGAL')

    # Frozen precision audit: exact double value is retained; no quantization or rounding.
    precision = {
        'schema': 'H1F4B2_FABRICATION_PRECISION_AUDIT_V1',
        'contract_result': 'CONTINUOUS_DOUBLE_PRECISION_GEOMETRY_SUPPORTED',
        'integer_nm_quantization': False, 'half_nm_quantization': False,
        'one_nm_quantization': False, 'builder_rounding_or_quantization': False,
        'evidence': ['scripts/lp_h1f4b1_prepare.py', 'scripts/lp_h1f4b1_runner.py',
                     'j1_anisotropy_candidate_manifest.json'],
        'exact_r_cancel': r, 'exact_AD_nm': AD,
        'exact_delta_J1_plus_nm': exact_delta, 'exact_delta_J1_minus_nm': -exact_delta,
        'rounding_applied': False, 'ratio_reoptimized': False,
    }
    write('h1f4b2_fabrication_precision_audit.json', precision)

    manifest = {
        'schema': 'H1F4B2_COMBINED_MANIFEST_V1', 'stage': 'H1F-4B2',
        'status': 'FROZEN_READY_FOR_SOLVER', 'route': 'GROUPED_D_PLUS_J1_TWO_LEVER_COMBINED_LOCAL_VALIDATION',
        'parent_uid': PRIMARY_UID, 'parent_hash': PRIMARY_HASH, 'children': out_children,
        'candidate_count': 2, 'max_new_formal_cases': 4, 'processes': 4, 'threads': 1,
        'polarizations': POLS, 'wavelength_grid_nm': GRID, 'ml_admitted': False,
        'A_D_abs_nm': AD, 'r_cancel': r, 'delta_J1_abs_nm': abs(exact_delta),
        'grouped_d_direction_rule_artifact': 'H1F4A_PHASE2_DIRECTION_RULE_V1.json',
        'grouped_d_u_a': rule['u_a'], 'grouped_d_u_b': rule['u_b'], 'phi_D_star_deg': rule['phi_D_star_deg'],
        'exact_delta_J1_plus_nm': exact_delta, 'exact_delta_J1_minus_nm': -exact_delta,
        'no_new_seed': True, 'no_new_amplitude_sweep': True, 'no_new_phi_sweep': True,
        'no_grouped_d_only_rerun': True, 'no_j1_only_rerun': True,
        'solver_plan': {'cases': [x for c in out_children for x in c['solver_case_uids']],
                        'serial_within_lp': True, 'max_active_lp_fdtd': 1,
                        'effective_global_fdtd_capacity': 3, 'permanent_global_fdtd_policy': 2,
                        'rcwa_consumes_fdtd_slot': False, 'no_auto_replay': True},
        'freeze_sha256': digest({'children': out_children, 'r_cancel': r, 'rule': rule}),
    }
    write('h1f4b2_combined_candidate_manifest.json', manifest)
    write('h1f4b2_geometry_legality.json', {'schema':'H1F4B2_GEOMETRY_LEGALITY_V1','all_pass':True,
                                           'layouts':{c['candidate_uid']:c['geometry_legality'] for c in out_children}})
    write('h1f4b2_preregistration.json', {'schema':'H1F4B2_PREREGISTRATION_V1','parent_uid':PRIMARY_UID,
        'parent_hash':PRIMARY_HASH,'r_cancel':r,'A_D_plus_nm':AD,'A_D_minus_nm':-AD,
        'delta_J1_plus_nm':exact_delta,'delta_J1_minus_nm':-exact_delta,
        'children':[[c['candidate_uid'],c['candidate_hash'],c['A_D_nm'],c['delta_J1_nm']] for c in out_children],
        'cases':[x for c in out_children for x in c['solver_case_uids']], 'attempt_uids':[f'{x}_attempt_001' for c in out_children for x in c['solver_case_uids']],
        'wavelength_grid_nm':GRID,'analysis_equations':['G_combined=G_D+r_cancel*G_J1','G_obs=(M(PLUS)-M(MINUS))/8 nm','even=(M(PLUS)+M(MINUS))/2-M(baseline)'],
        'no_auto_replay':True,'solver_budget':4,'ml_admitted':False})
    # Re-register exact linearized predictions from H1F4B1, not rounded chat values.
    matrix_path = H1F4B1_REPORT/'h1f4b1_two_lever_jacobian.csv'
    import csv
    with matrix_path.open(encoding='utf-8-sig', newline='') as f: matrix = list(csv.DictReader(f))
    predictions=[]
    for row in matrix:
        gd=float(row['g_D_per_nm']); gj=float(row['g_J1_per_nm'])
        predictions.append({'wavelength_nm':float(row['wavelength_nm']),'metric':row['metric'],
                            'g_D_per_nm':gd,'g_J1_per_nm':gj,'g_combined_pred_per_nm':gd+r*gj,
                            'delta_M_predicted_8nm':8.0*(gd+r*gj)})
    with (REPORT/'h1f4b2_predicted_combined_jacobian.csv').open('w',newline='',encoding='utf-8') as f:
        fields=list(predictions[0]); w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(predictions)
    means={}
    for metric in ('eta_x_plus1','eta_y_plus1','eta_x_0','eta_x_minus1'):
        vals=[x['g_combined_pred_per_nm'] for x in predictions if x['metric']==metric]
        means[metric]={'values':vals,'mean':sum(vals)/len(vals),'std':(sum((v-sum(vals)/len(vals))**2 for v in vals)/len(vals))**0.5,'min':min(vals),'max':max(vals),'positive_count':sum(v>0 for v in vals),'negative_count':sum(v<0 for v in vals)}
    write('h1f4b2_predicted_summary.json', {'schema':'H1F4B2_PREDICTED_COMBINED_SUMMARY_V1','r_cancel':r,'means':means})
    write('h1f4b2_solver_accounting.json', {'schema':'H1F4B2_SOLVER_ACCOUNTING_V1','status':'PREREGISTERED','planned_formal_cases':4,'entered_formal_cases':0,'accepted_formal_cases':0,'replay_cases':0,'cases':[],'solver_entered_delta':0,'solver_accepted_delta':0,'ml_admitted':False})
    write('h1f4b2_solver_ledger.json', {'schema':'H1F4B2_SOLVER_LEDGER_V1','planned_cases':[x for c in out_children for x in c['solver_case_uids']],'solver_entered':[],'solver_entered_count':0,'replay_count':0,'no_auto_replay':True})
    write('h1f4b2_scheduler_preregistration.json', {'schema':'H1F4B2_SCHEDULER_PREREGISTRATION_V1','permanent_global_fdtd_policy':2,'effective_stage_capacity':3,'max_active_lp_fdtd':1,'rcwa_consumes_fdtd_slot':False,'serial_within_lp':True,'fresh_audit_before_each_entry':True,'fourth_fdtd_authorized':False})
    write('h1f4b2_authority_audit.json', {'schema':'H1F4B2_AUTHORITY_AUDIT_V1','branch':'work/lp-global-h-manifold-v1','head_expected':'17f2fae','primary_uid':PRIMARY_UID,'primary_hash':PRIMARY_HASH,'h1f4a_rule':str(H1F4A_PHASE2/'H1F4A_PHASE2_DIRECTION_RULE_V1.json'),'h1f4b1_analysis':str(H1F4B1_REPORT/'h1f4b1_jacobian_cancellation_analysis.json'),'solver_entered_delta':0,'existing_dirty_files_preserved':True})
    print(json.dumps({'r_cancel':r,'delta_plus_nm':exact_delta,'delta_minus_nm':-exact_delta,'children':[(c['candidate_uid'],c['candidate_hash'],c['geometry_legality']) for c in out_children],'freeze_sha256':manifest['freeze_sha256']},indent=2))

if __name__ == '__main__': main()
