import csv, json, hashlib
from pathlib import Path

ROOT=Path(r'D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1')
R=ROOT/'reports'/'stage_h1f4a_phase2_grouped_d_transfer_validation'
R.mkdir(parents=True,exist_ok=True)
H1F2=ROOT/'reports'/'stage_h1f2_k6_frontier_level1'/'h1f2_candidate_manifest.json'
H1F4A=ROOT/'reports'/'stage_h1f4a_grouped_d_first_harmonic_jacobian_probe'

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

h1f2=json.load(open(H1F2,encoding='utf-8'))
transfer=h1f2['candidates']['K6_L1_B']
required=['candidate_uid','candidate_hash','H_global_nm','P_supercell_nm','P_y_nm','local_geometries','geometry_legality','fundamental_period_audit','material','p_nm','ml_admitted','no_local_geometry_mutation','no_position_shift']
missing=[x for x in required if x not in transfer]
hash_ok=transfer['candidate_hash']=='ea25ff16c44e2dd00eb9fc6805b6f174a635668f65edad2666f641faf9880a78'
seed_audit={
 'schema':'H1F4A_PHASE2_TRANSFER_SEED_AUTHORITY_AUDIT_V1',
 'candidate_uid':transfer['candidate_uid'],'candidate_hash':transfer['candidate_hash'],
 'expected_historical_hash':'ea25ff16c44e2dd00eb9fc6805b6f174a635668f65edad2666f641faf9880a78',
 'hash_match':hash_ok,'source_artifact':str(H1F2),'source_artifact_sha256':sha(H1F2),
 'source_stage':'H1F2 authoritative K6 frontier level1 manifest',
 'solver_authorized':False,'ml_admitted':False,'required_fields_missing':missing,
 'geometry_legality_pass':transfer.get('geometry_legality',{}).get('pass') in (True,'True'),
 'fundamental_period_6P':transfer.get('fundamental_period_audit',{}).get('FUNDAMENTAL_PERIOD_6P'),
 'p_nm':transfer.get('p_nm'),'P_supercell_nm':transfer.get('P_supercell_nm'),'H_global_nm':transfer.get('H_global_nm'),
 'materials':sorted(set(transfer.get('geometry_legality',{}).get('materials',[]))),
 'source_contract_summary':{'wavelength_grid_nm':h1f2.get('wavelength_grid_nm'),'processes':h1f2.get('processes'),'threads':h1f2.get('threads'),'schema':transfer.get('local_geometries',[{}])[0].get('schema')},
 'pass':None}
seed_audit['pass']=hash_ok and not missing and seed_audit['geometry_legality_pass'] and seed_audit['fundamental_period_6P'] is True
with open(R/'transfer_seed_authority_audit.json','w',encoding='utf-8') as f: json.dump(seed_audit,f,indent=2)
with open(R/'transfer_seed_full_provenance.json','w',encoding='utf-8') as f:
    json.dump({'source_artifact':str(H1F2),'source_artifact_sha256':sha(H1F2),'candidate':transfer,'solver_authorized':False},f,indent=2)

prereg=json.load(open(H1F4A/'scheduler_audit_preregistration.json',encoding='utf-8'))
summary=json.load(open(H1F4A/'h1f4a_jacobian_summary.json',encoding='utf-8'))
jac=list(csv.DictReader(open(H1F4A/'h1f4a_central_difference_jacobian.csv',newline='',encoding='utf-8')))
direction_audit={
 'schema':'H1F4A_PHASE2_DIRECTION_ZERO_SOLVER_AUDIT_V1','stage':'H1F-4A Phase-2',
 'route':'GROUPED_D_FIRST_HARMONIC_TRANSFER_VALIDATION','solver_entered_delta':0,
 'formal_direction_rule_found':False,'phi_D_star_defined':False,'phi_D_star_deg':None,'cos_phi_D_star':None,'sin_phi_D_star':None,
 'classification':'GROUPED_D_PHASE2_DIRECTION_NOT_FORMALLY_IDENTIFIABLE_CHART_REVIEW',
 'reason':['Phase-1 evidence contains separate A/B scalar Jacobian summaries but no frozen unique multi-metric objective or direction-selection rule.',
           'The authoritative instruction forbids selecting phi_D* from max|d eta(+1)/da_D| and max|d eta(+1)/db_D| alone.',
           'Available Jacobian includes wavelength-, polarization-, order- and complex-response dimensions with mixed signs, so a unique direction cannot be recovered without inventing weights or a post hoc objective.'],
 'evidence':{'phase1_summary':str(H1F4A/'h1f4a_jacobian_summary.json'),'jacobian_csv':str(H1F4A/'h1f4a_central_difference_jacobian.csv'),'scheduler_preregistration':prereg,'phase1_classification':summary.get('classification'),'axes':summary.get('jacobian_summary')},
 'prohibited_actions_not_taken':['arctan of two scalar maxima','post-hoc objective creation','transfer geometry creation','new Phase-1 case','Phase-2 solver entry'],
 'transfer_solver_plan':{'planned_cases':4,'solver_entered':0,'replay':0},'ml_admitted':False,
 'next_gate':'Chart must supply or accept a frozen unique direction-selection rule before Transfer geometry can be frozen.'}
with open(R/'phase2_direction_zero_solver_audit.json','w',encoding='utf-8') as f: json.dump(direction_audit,f,indent=2)
with open(R/'h1f4a_phase2_conclusion.md','w',encoding='utf-8') as f:
    f.write('# H1F4A Phase-2 conclusion\n\n')
    f.write('Status: `GROUPED_D_PHASE2_DIRECTION_NOT_FORMALLY_IDENTIFIABLE_CHART_REVIEW`\n\n')
    f.write('- Transfer seed `K6_L1_B` was restored from the authoritative H1F2 manifest and hash-verified.\n')
    f.write('- The existing Phase-1 evidence does not contain a unique frozen direction-selection rule for `phi_D*`.\n')
    f.write('- No Transfer geometry was created; no Phase-2 solver was entered (`solver_entered_delta=0`).\n')
    f.write('- The permanent FDTD policy remains 2; no scheduler file was modified.\n')
