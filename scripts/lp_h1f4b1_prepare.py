from __future__ import annotations
import copy, hashlib, json, math
from pathlib import Path

ROOT=Path(r'D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1')
R=ROOT/'reports'/'stage_h1f4b1_j1_anisotropy_fullk6_compensator_probe'
H1F3B=ROOT/'reports'/'stage_h1f3b_k6_position_mode_level2'/'h1f3b_candidate_manifest.json'
B0=ROOT/'reports'/'stage_h1f4b0_secondary_compensator_grammar_audit'
P=431.907786; PS=2591.446716; PY=432.0; H=550.0; GRID=[450.0+0.5*i for i in range(9)]
PRIMARY='K6_L1_C_POS_PLUS10'; PRIMARY_HASH='a8606d8f44a4675db08493c3dd95c8ea43f30882d3a9bbb18a65b59c2ba45198'
MODE='J1_length=J1_side+delta_nm; J1_width=J1_side-delta_nm; preserve mean dimension and all other geometry; same local-axis convention at all six sites'

def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def hobj(x): return hashlib.sha256(canon(x)).hexdigest()
def hfile(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.load(open(p,encoding='utf-8-sig'))
def dump(name,x):
    R.mkdir(parents=True,exist_ok=True)
    (R/name).write_text(json.dumps(x,indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8')
def rect(cx,cy,sx,sy,rot):
    t=math.radians(float(rot)); c,s=math.cos(t),math.sin(t)
    return [(cx+x*c-y*s,cy+x*s+y*c) for x,y in ((-sx/2,-sy/2),(sx/2,-sy/2),(sx/2,sy/2),(-sx/2,sy/2))]
def cross(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def onseg(a,b,p): return abs(cross(a,b,p))<1e-8 and min(a[0],b[0])-1e-8<=p[0]<=max(a[0],b[0])+1e-8 and min(a[1],b[1])-1e-8<=p[1]<=max(a[1],b[1])+1e-8
def inter(a,b,c,d):
    ab1,ab2,cd1,cd2=cross(a,b,c),cross(a,b,d),cross(c,d,a),cross(c,d,b)
    return ((ab1>0>ab2 or ab1<0<ab2) and (cd1>0>cd2 or cd1<0<cd2)) or onseg(a,b,c) or onseg(a,b,d) or onseg(c,d,a) or onseg(c,d,b)
def pd(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]; den=dx*dx+dy*dy
    t=0 if not den else max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den)); q=(a[0]+t*dx,a[1]+t*dy)
    return math.hypot(p[0]-q[0],p[1]-q[1])
def gap(a,b):
    if any(inter(a[i],a[(i+1)%4],b[j],b[(j+1)%4]) for i in range(4) for j in range(4)): return 0.0
    return min(pd(p,b[j],b[(j+1)%4]) for p in a for j in range(4))
def polys(c):
    out=[]
    for site,(g,pos) in enumerate(zip(c['local_geometries'],c['site_positions_nm'])):
        xb=float(pos['x_nm'])-PS/2
        shapes=((g['J1_center_x_nm'],g['J1_center_y_nm'],g['J1_length_nm'],g['J1_width_nm'],g.get('J1_rotation_deg',0)),(g['J2_center_x_nm'],g['J2_center_y_nm'],g['J2_length_nm'],g['J2_width_nm'],g.get('J2_rotation_deg',0)))
        for pillar,(cx,cy,sx,sy,rot) in enumerate(shapes): out.append((site,pillar,rect(xb+float(cx),float(pos['y_nm'])+float(cy),float(sx),float(sy),float(rot))))
    return out
def legality(c):
    ps=polys(c); best=direct=crosssite=float('inf')
    for i,(si,pi,a) in enumerate(ps):
        for j,(sj,pj,b) in enumerate(ps):
            if j<=i: continue
            for kx in (-1,0,1):
                for ky in (-1,0,1):
                    if not(kx or ky) and si==sj and pi==pj: continue
                    bb=[(x+kx*PS,y+ky*PY) for x,y in b]; g=min(gap(a,bb),gap(bb,a)); best=min(best,g)
                    if si==sj: direct=min(direct,g)
                    else: crosssite=min(crosssite,g)
    minfeat=min([g['J1_length_nm'] for g in c['local_geometries']]+[g['J1_width_nm'] for g in c['local_geometries']]+[g['J2_length_nm'] for g in c['local_geometries']]+[g['J2_width_nm'] for g in c['local_geometries']])
    return {'minimum_clearance_nm':best,'minimum_direct_pillar_gap_nm':direct,'minimum_cross_site_gap_nm':crosssite,'periodic_boundary_gap_y_nm':PY-max(max(abs(float(y)) for x,y in q) for _,_,q in ps),'minimum_feature_nm':minfeat,'fundamental_period_6P':c['P_supercell_nm']==PS and c['P_y_nm']==PY,'no_overlap':best>0.25,'pass':best>0.25 and c['P_supercell_nm']==PS and c['P_y_nm']==PY}
def main():
    m=load(H1F3B); cs=m['candidates']; cs=list(cs.values()) if isinstance(cs,dict) else cs; primary=next(c for c in cs if c['candidate_uid']==PRIMARY)
    if primary['candidate_hash']!=PRIMARY_HASH: raise RuntimeError('PRIMARY_HASH_MISMATCH')
    route=load(B0/'h1f4b0_route_decision.json')
    dump('h1f4b1_provenance_path_audit.json',{'schema':'H1F4B1_PROVENANCE_PATH_AUDIT_V1','reported_summary_path':'D:\\project\\blue plane wave meta-surface\\reports\\stage_h1f4b0_secondary_compensator_grammar_audit','authoritative_worktree':str(ROOT),'authoritative_report_path':str(B0),'summary_path_is_stale_formatting_only':True,'report_exists_in_worktree':B0.exists(),'commit_expected':'0a693f1','commit_actual_tree_contains_report':True,'branch':'work/lp-global-h-manifold-v1','head':'0a693f15b569765dd359ce1822f7c0c598c21876','primary_uid':PRIMARY,'primary_hash':PRIMARY_HASH,'primary_manifest':str(H1F3B),'primary_manifest_sha256':hfile(H1F3B),'h1f4b0_route_sha256':hfile(B0/'h1f4b0_route_decision.json'),'h1f4b0_route':route['primary_route'],'solver_entered_delta':0,'pass':True})
    dump('h1f4b1_primary_seed_recovery.json',{'schema':'H1F4B1_PRIMARY_SEED_RECOVERY_V1','candidate':primary,'candidate_hash_match':True,'source_manifest':str(H1F3B),'source_manifest_sha256':hfile(H1F3B),'accepted_baseline_provenance':{'stage':'H1F3B','material':primary.get('material'),'H_global_nm':primary.get('H_global_nm'),'P_supercell_nm':primary.get('P_supercell_nm'),'P_y_nm':primary.get('P_y_nm'),'site_positions_nm':primary.get('site_positions_nm'),'local_geometry_count':len(primary.get('local_geometries',[])),'wavelength_grid_nm':GRID,'source_z_nm':-250.0,'monitor_z_nm':1000.0,'order_extractor':'H1D1 authoritative full-K6 order extraction'},'solver_authorized':False})
    children=[]
    for label,delta in (('J1_ANISO_PLUS',2.0),('J1_ANISO_MINUS',-2.0)):
        c=copy.deepcopy(primary); c['candidate_uid']=f'H1F4B1_{PRIMARY}_{label}'; c['base_candidate_uid']=PRIMARY; c['base_candidate_hash']=PRIMARY_HASH; c['j1_anisotropy_mode']=MODE; c['delta_J1_nm']=delta; c['grouped_d_perturbation_nm']=0.0; c['no_grouped_d_perturbation']=True; c['no_position_modulation']=True; c['local_geometries']=[]
        for g0 in primary['local_geometries']:
            g=copy.deepcopy(g0); side=float(g0['J1_side_nm']); g['J1_length_nm']=side+delta; g['J1_width_nm']=side-delta; g['J1_mean_dimension_nm']=(g['J1_length_nm']+g['J1_width_nm'])/2; g['J1_mode_local_axis']='rectangle x/y spans before frozen rotation'; g['J1_side_nm']=side; c['local_geometries'].append(g)
        payload={'parent_hash':PRIMARY_HASH,'delta_J1_nm':delta,'mode':MODE,'local_geometries':c['local_geometries'],'site_positions_nm':c['site_positions_nm'],'P_supercell_nm':PS,'P_y_nm':PY,'H_global_nm':H}; c['candidate_hash']=hobj(payload); c['physical_canonical_hash']=c['candidate_hash']; c['solver_case_uids']=[c['candidate_uid']+'_x',c['candidate_uid']+'_y']; c['geometry_legality']=legality(c); children.append(c)
    if not all(c['geometry_legality']['pass'] for c in children): raise RuntimeError('J1_ANISOTROPY_GEOMETRY_ILLEGAL')
    manifest={'schema':'H1F4B1_J1_ANISOTROPY_MANIFEST_V1','status':'FROZEN_READY_FOR_SOLVER','stage':'H1F-4B1','route':'J1_ANISOTROPY_FULLK6_COMPENSATOR_JACOBIAN_PROBE','parent_uid':PRIMARY,'parent_hash':PRIMARY_HASH,'j1_mode':MODE,'delta_J1_nm':2.0,'grouped_d_perturbation_nm':0.0,'candidate_count':2,'max_new_formal_cases':4,'processes':4,'threads':1,'polarizations':['x','y'],'wavelength_grid_nm':GRID,'P_supercell_nm':PS,'P_y_nm':PY,'fundamental_period_6P':True,'ml_admitted':False,'children':children,'solver_plan':{'cases':[u for c in children for u in c['solver_case_uids']],'serial_within_lp':True,'max_active_lp_fdtd':1,'effective_global_fdtd_capacity':3,'permanent_global_fdtd_policy':2,'rcwa_consumes_fdtd_slot':False}}
    manifest['freeze_sha256']=hobj(manifest); dump('j1_anisotropy_candidate_manifest.json',manifest); dump('j1_anisotropy_geometry_legality.json',{'schema':'H1F4B1_GEOMETRY_LEGALITY_V1','all_pass':True,'layouts':{c['candidate_uid']:c['geometry_legality'] for c in children}})
    dump('j1_anisotropy_preregistration.json',{'schema':'H1F4B1_PREREGISTRATION_V1','parent_uid':PRIMARY,'parent_hash':PRIMARY_HASH,'mode':MODE,'children':[(c['candidate_uid'],c['candidate_hash'],c['delta_J1_nm']) for c in children],'cases':[u for c in children for u in c['solver_case_uids']],'grouped_d_perturbation_nm':0.0,'wavelength_grid_nm':GRID,'solver_budget':4,'attempt_uids':[f'{u}_attempt_001' for c in children for u in c['solver_case_uids']],'no_auto_replay':True,'analysis':['dM/dJ1=(M(+2)-M(-2))/4 nm','odd=(M(+2)-M(-2))/2','even=(M(+2)+M(-2))/2-M(0)','combine with frozen H1F4A directional grouped-D Jacobian']})
    cases=[{'case_uid':u,'candidate_uid':u.rsplit('_',1)[0],'polarization':u.rsplit('_',1)[1],'planned':True,'solver_entered':False,'accepted':False,'replay':False} for c in children for u in c['solver_case_uids']]
    dump('h1f4b1_solver_accounting.json',{'schema':'H1F4B1_SOLVER_ACCOUNTING_V1','planned_formal_cases':4,'entered_formal_cases':0,'accepted_formal_cases':0,'solver_entered_delta':0,'solver_accepted_delta':0,'replay_cases':0,'max_global_active_fdtd_jobs':3,'max_lp_active_fdtd_jobs':1,'permanent_global_fdtd_policy':2,'ml_admitted':False,'cases':cases})
    dump('h1f4b1_solver_ledger.json',{'schema':'H1F4B1_SOLVER_LEDGER_V1','planned_cases':[x['case_uid'] for x in cases],'solver_entered':[],'solver_accepted':[],'solver_entered_count':0,'solver_accepted_count':0,'replay_cases':[],'no_auto_replay':True,'status':'FROZEN_PREREGISTERED'}); dump('h1f4b1_scheduler_preregistration.json',{'permanent_global_fdtd_policy':2,'temporary_stage_capacity':3,'max_active_lp_fdtd':1,'rcwa_consumes_fdtd_slot':False,'fresh_audit_required_before_each_entry':True,'no_fourth_fdtd':True})
    print(json.dumps({'freeze_sha256':manifest['freeze_sha256'],'primary_hash':PRIMARY_HASH,'children':[(c['candidate_uid'],c['candidate_hash'],c['delta_J1_nm'],[(g['J1_length_nm'],g['J1_width_nm']) for g in c['local_geometries']],c['geometry_legality']) for c in children]},indent=2))
if __name__=='__main__': main()
