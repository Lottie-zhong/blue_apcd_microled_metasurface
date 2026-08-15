from __future__ import annotations
import copy, csv, hashlib, json, math, sys
from pathlib import Path

ROOT=Path(r'D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1')
R=ROOT/'reports'/'stage_h1f4a_phase2_grouped_d_transfer_validation'
H1F4A=ROOT/'reports'/'stage_h1f4a_grouped_d_first_harmonic_jacobian_probe'
sys.path.insert(0,str(ROOT/'scripts'))
import lp_h1f4a_prepare as base

def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def objsha(x): return hashlib.sha256(canon(x)).hexdigest()
def file_sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(name,x):
    R.mkdir(parents=True,exist_ok=True)
    (R/name).write_text(json.dumps(x,indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8')

def main():
    rows=list(csv.DictReader(open(H1F4A/'h1f4a_central_difference_jacobian.csv',newline='',encoding='utf-8')))
    grid=[450.0+0.5*i for i in range(9)]
    def axis_values(axis):
        x=[r for r in rows if r['axis']==axis and r['polarization']=='x']
        if len(x)!=9 or [float(r['wavelength_nm']) for r in x]!=grid: raise RuntimeError('PHASE1_JACOBIAN_GRID_GATE')
        return [float(r['d_eta_target_per_nm']) for r in x]
    ga,gb=axis_values('A'),axis_values('B')
    gbar_a=sum(ga)/9.0; gbar_b=sum(gb)/9.0; norm=math.hypot(gbar_a,gbar_b)
    if not math.isfinite(norm) or norm==0.0: raise RuntimeError('GROUPED_D_PHASE2_BROADBAND_MEAN_GRADIENT_UNDEFINED')
    ua,ub=gbar_a/norm,gbar_b/norm
    phi=math.atan2(gbar_b,gbar_a)
    if phi<=-math.pi: phi=math.pi
    if phi>math.pi: phi-=2*math.pi
    gphi=[a*ua+b*ub for a,b in zip(ga,gb)]
    transfer_manifest=ROOT/'reports'/'stage_h1f2_k6_frontier_level1'/'h1f2_candidate_manifest.json'
    transfer=json.loads(transfer_manifest.read_text(encoding='utf-8'))['candidates']['K6_L1_B']
    if transfer['candidate_hash']!='ea25ff16c44e2dd00eb9fc6805b6f174a635668f65edad2666f641faf9880a78': raise RuntimeError('TRANSFER_HASH_GATE')
    h1f4a_manifest=json.loads((H1F4A/'grouped_d_candidate_manifest.json').read_text(encoding='utf-8'))
    source_hashes={c['candidate_uid']:c['candidate_hash'] for c in h1f4a_manifest['children']}
    rule={
      'schema':'H1F4A_PHASE2_DIRECTION_RULE_V1','rule_version':'H1F4A_PHASE2_DIRECTION_RULE_V1',
      'rule_authority':'CHART_PROSPECTIVE_POST_PHASE1_PRE_TRANSFER','transfer_data_seen':False,'transfer_solver_entered_before_rule':0,
      'observable':'M(lambda)=eta_x_mplus1(lambda)','wavelength_grid_nm':grid,'source_phase1_case_uids':['H1F4A_K6_L1_C_POS_PLUS10_A_PLUS_x','H1F4A_K6_L1_C_POS_PLUS10_A_MINUS_x','H1F4A_K6_L1_C_POS_PLUS10_B_PLUS_x','H1F4A_K6_L1_C_POS_PLUS10_B_MINUS_x'],
      'source_phase1_candidate_hashes':source_hashes,'source_artifact_sha256':{'jacobian_csv':file_sha(H1F4A/'h1f4a_central_difference_jacobian.csv'),'manifest':file_sha(H1F4A/'grouped_d_candidate_manifest.json'),'accounting':file_sha(H1F4A/'h1f4a_solver_accounting.json')},
      'g_a_per_nm':ga,'g_b_per_nm':gb,'gbar_a_per_nm':gbar_a,'gbar_b_per_nm':gbar_b,'norm_g_per_nm':norm,'u_a':ua,'u_b':ub,'phi_D_star_rad':phi,'phi_D_star_deg':math.degrees(phi),'g_phi_per_nm':gphi,
      'g_phi_diagnostic':{'mean':sum(gphi)/9.0,'median':sorted(gphi)[4],'min':min(gphi),'max':max(gphi),'std':(sum((v-sum(gphi)/9.0)**2 for v in gphi)/9.0)**0.5,'rms':(sum(v*v for v in gphi)/9.0)**0.5,'positive_count':sum(v>0 for v in gphi),'negative_count':sum(v<0 for v in gphi),'zero_count':sum(v==0 for v in gphi),'sign_consistency':all(v>0 for v in gphi) or all(v<0 for v in gphi)},
      'direction_selection_rule':'equal-weight nine-point mean gradient; leakage/other orders are not used for phi selection','plus_sign_convention':'increases 9-point mean eta_x,+1 at primary under first-order model','pre_transfer_solver_ledger_proof':{'phase1_planned':8,'phase1_entered':8,'phase1_accepted':8,'phase1_replay':0,'transfer_entered_before_rule':0}
    }
    rule_hash=objsha(rule); rule['rule_artifact_sha256']=rule_hash
    dump('H1F4A_PHASE2_DIRECTION_RULE_V1.json',rule)
    # Geometry is created only after the rule artifact is frozen.
    children=[]
    for label,sign in (('TRANSFER_PLUS',1.0),('TRANSFER_MINUS',-1.0)):
        c=copy.deepcopy(transfer); c['candidate_uid']='H1F4A_K6_L1_B_'+label; c['base_candidate_uid']='K6_L1_B'; c['base_candidate_hash']=transfer['candidate_hash']; c['grouped_d_mode']='D_n=D_n_baseline+a_D*cos(2*pi*n/6)+b_D*sin(2*pi*n/6)'; c['harmonic_coefficients']={'a_D_nm':4.0*ua*sign,'b_D_nm':4.0*ub*sign}; c['site_ordering']='n=0..5 authoritative K6_L1_B order'; c['direction_rule_version']=rule['rule_version']; c['direction_rule_hash']=rule_hash; c['local_geometries']=[]; ds=[]; bases=[]
        for n,g0 in enumerate(transfer['local_geometries']):
            g=copy.deepcopy(g0); b=float(g0.get('D_nm',float(g0['J2_center_x_nm'])-float(g0['J1_center_x_nm']))); delta=4.0*sign*(ua*math.cos(2*math.pi*n/6)+ub*math.sin(2*math.pi*n/6)); d=b+delta; mid=(float(g0['J1_center_x_nm'])+float(g0['J2_center_x_nm']))/2.0; g['J1_center_x_nm']=mid-d/2.0; g['J2_center_x_nm']=mid+d/2.0; g['D_n_baseline_nm']=b; g['D_n_nm']=d; c['local_geometries'].append(g); bases.append(b); ds.append(d)
        c['D_n_baseline_nm']=bases; c['D_n_nm']=ds; c['no_position_modulation']=True; c['helper_J3']=None; c['no_new_seed']=True
        payload={'H_global_nm':c['H_global_nm'],'P_supercell_nm':c['P_supercell_nm'],'P_y_nm':c['P_y_nm'],'material':c['material'],'local_geometries':c['local_geometries'],'site_positions_nm':c['site_positions_nm'],'grouped_d_mode':c['grouped_d_mode'],'harmonic_coefficients':c['harmonic_coefficients'],'base_candidate_hash':c['base_candidate_hash'],'direction_rule_hash':rule_hash}
        c['candidate_hash']=objsha(payload); c['physical_canonical_hash']=c['candidate_hash']; c['solver_case_uids']=[c['candidate_uid']+'_x',c['candidate_uid']+'_y']; c['geometry_legality']=base.legality(c); children.append(c)
    if not all(c['geometry_legality']['pass'] for c in children): raise RuntimeError('GROUPED_D_PHASE2_TRANSFER_GEOMETRY_ILLEGAL')
    manifest={'schema':'H1F4A_PHASE2_TRANSFER_MANIFEST_V1','status':'FROZEN_READY_FOR_SOLVER','stage':'H1F4A_PHASE2','route':'GROUPED_D_FIRST_HARMONIC_TRANSFER_VALIDATION','branch':'work/lp-global-h-manifold-v1','worktree':str(ROOT),'rule_artifact':'H1F4A_PHASE2_DIRECTION_RULE_V1.json','rule_artifact_sha256':rule_hash,'transfer_parent_uid':'K6_L1_B','transfer_parent_hash':transfer['candidate_hash'],'candidate_count':2,'max_new_formal_cases':4,'A_D_nm':4.0,'P_supercell_nm':transfer['P_supercell_nm'],'P_y_nm':transfer['P_y_nm'],'wavelength_grid_nm':grid,'polarizations':['x','y'],'processes':4,'threads':1,'ml_admitted':False,'children':children,'solver_plan':{'cases':['TRANSFER_PLUS_X','TRANSFER_PLUS_Y','TRANSFER_MINUS_X','TRANSFER_MINUS_Y'],'serial_within_lp':True,'max_active_lp_fdtd':1,'effective_global_fdtd_capacity':3,'permanent_global_fdtd_policy':2,'rcwa_consumes_fdtd_slot':False}}
    manifest['freeze_sha256']=objsha(manifest); dump('transfer_candidate_manifest.json',manifest); dump('transfer_geometry_legality.json',{'schema':'H1F4A_PHASE2_TRANSFER_GEOMETRY_LEGALITY_V1','all_pass':True,'layouts':{c['candidate_uid']:c['geometry_legality'] for c in children}})
    dump('transfer_preregistration.json',{'schema':'H1F4A_PHASE2_TRANSFER_PREREGISTRATION_V1','rule_artifact_sha256':rule_hash,'transfer_parent_uid':'K6_L1_B','transfer_parent_hash':transfer['candidate_hash'],'children':[(c['candidate_uid'],c['candidate_hash'],c['harmonic_coefficients'],c['D_n_nm']) for c in children],'cases':[u for c in children for u in c['solver_case_uids']],'wavelength_grid_nm':grid,'solver_budget':4,'solver_entered':0,'replay':0,'no_auto_replay':True,'baseline_provenance':str(H1F4A/'h1f3b_order_resolved_fullwave.csv')})
    cases=[{'case_uid':u,'candidate_uid':u.rsplit('_',1)[0],'polarization':u.rsplit('_',1)[1],'solver_entered':False,'accepted':False,'replay':False,'planned':True} for c in children for u in c['solver_case_uids']]
    dump('h1f4a_phase2_solver_accounting.json',{'schema':'H1F4A_PHASE2_SOLVER_ACCOUNTING_V1','planned_formal_cases':4,'entered_formal_cases':0,'accepted_formal_cases':0,'solver_entered_delta':0,'solver_accepted_delta':0,'replay_cases':0,'quarantine_cases':0,'max_global_active_fdtd_jobs':3,'max_lp_active_fdtd_jobs':1,'permanent_global_fdtd_policy':2,'ml_admitted':False,'cases':cases})
    dump('h1f4a_phase2_solver_ledger.json',{'schema':'H1F4A_PHASE2_SOLVER_LEDGER_V1','planned_cases':[x['case_uid'] for x in cases],'solver_entered':[],'solver_accepted':[],'solver_entered_count':0,'solver_accepted_count':0,'replay_cases':[],'status':'FROZEN_PREREGISTERED','no_auto_replay':True})
    dump('h1f4a_phase2_scheduler_preregistration.json',{'permanent_global_fdtd_policy':2,'temporary_stage_capacity':3,'max_active_lp_fdtd':1,'rcwa_consumes_fdtd_slot':False,'fresh_audit_required_before_each_entry':True,'no_fourth_fdtd':True})
    print(json.dumps({'rule_hash':rule_hash,'gbar_a':gbar_a,'gbar_b':gbar_b,'norm_g':norm,'u_a':ua,'u_b':ub,'phi_deg':math.degrees(phi),'gphi':gphi,'children':[(c['candidate_uid'],c['candidate_hash'],c['harmonic_coefficients'],c['D_n_nm'],c['geometry_legality']['minimum_clearance_nm']) for c in children]},indent=2))

if __name__=='__main__': main()
