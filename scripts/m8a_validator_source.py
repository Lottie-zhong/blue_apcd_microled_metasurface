import csv, json, hashlib
from pathlib import Path

R=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
O=R/'outputs/np_k6_m8a_final_targeted_acquisition_design_v1'
M7A=R/'outputs/np_k6_m7a_targeted_development_acquisition_design_v1'
PRE=O/'NP_K6_M8A_FINAL_TARGETED_ACQUISITION_PREREG_V1.json'
G01='K6X_D135_D155_D190_D220_D225_D230'

def js(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):
    with p.open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def fail(msg): raise RuntimeError(msg)

pre=js(PRE)
pre_sha=hashlib.sha256(PRE.read_bytes()).hexdigest()
pre_record=js(O/'preregistration_sha256.json')
if pre_record.get('sha256') != pre_sha or pre_record.get('candidate_identities_generated_after_hash') is not False: fail('preregistration_order')
sel=js(O/'primary2_selection.json')
if sel.get('preregistration_sha256') != pre_sha or sel.get('primary_count') != 2: fail('primary2_contract')
primary=sel.get('primary',[])
if len({x.get('geometry_id') for x in primary}) != 2: fail('primary2_unique')
roles={x.get('role') for x in primary}
if roles != {'TAIL-LOCALIZATION','RANKING-DISAMBIGUATION'}: fail('primary_roles')
if primary[0].get('geometry_id') == G01 or primary[1].get('geometry_id') == G01: fail('g01_quarantined')
back=rows(O/'backup_ranking.csv')
if len(back) != 6 or len({x['geometry_id'] for x in back}) != 6: fail('backup_count')
if set(x['geometry_id'] for x in back) & set(x['geometry_id'] for x in primary): fail('backup_overlap')
all_cand=rows(M7A/'candidate_acquisition_features.csv')
hf_rows=rows(R/'outputs/np_k6_m7a_primary4_targeted_hf_acquisition_closeout_v1/m7a_formal_development_hf_observations_440rows.csv')
hf_ids={x['geometry_id'] for x in hf_rows}
cand=rows(O/'candidate_selection_scores.csv')
if len(all_cand) != 31 or not cand or any(x['geometry_id'] in hf_ids for x in cand): fail('candidate_pool_count_or_hf_overlap')
cmap={x['geometry_id']:x for x in all_cand}
for x in primary+back:
    if x['geometry_id'] not in cmap: fail('candidate_not_in_pool')
    if x['geometry_hash'] != cmap[x['geometry_id']]['geometry_hash']: fail('candidate_hash_mismatch')
    ds=[int(v) for v in x['geometry_id'].split('_D')[1:]]
    if len(ds)!=6: fail('geometry_arity')
    if any(v<100 or v>230 for v in ds): fail('diameter_bounds')
    if [int(float(cmap[x['geometry_id']][f'D{i}'])) for i in range(1,7)] != ds: fail('ordered_geometry')
if float(pre['scope'].get('u_x_only',1.0)) != 0.0 or pre['scope'].get('no_angular_acquisition') is not True: fail('scope')
if pre.get('sealed_target_reads') != 0 or pre.get('external_hf') != 0 or pre.get('new_hf') != 0: fail('sealed_external')
zero=js(O/'solver_zero_audit.json')
if any(int(zero.get(k,0)) != 0 for k in ('solver_calls','new_hf','external_hf','sealed_target_reads','inverse_design')): fail('solver_nonzero')
budget=js(O/'solver_cost_budget.json')
if budget['primary2']['formal_cases'] != 4 or budget['primary2']['rows'] != 44 or budget['optional_first4']['formal_cases'] != 8 or budget['optional_first4']['rows'] != 88: fail('budget')
report={'status':'PASS','preregistration_sha256':pre_sha,'candidate_universe_count':31,'excluded_g01':G01,'primary2_count':2,'primary2_roles':sorted(roles),'backup_count':6,'primary2_geometry_ids':[x['geometry_id'] for x in primary],'backup_geometry_ids':[x['geometry_id'] for x in back],'solver_calls':0,'new_hf':0,'sealed_target_reads':0,'external_hf_reads':0,'inverse_design':0,'primary2_future_cases':4,'primary2_future_rows':44,'optional_first4_future_cases':8,'optional_first4_future_rows':88,'external_hf_recommendation':False,'candidate_identities_generated_after_prereg_hash':True}
(O/'m8a_final_validator_report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
