from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
REPORT = ROOT / "paper_a_broadband/reports/lp_anisotropy_expanded_search_v1"
CONFIG = ROOT / "paper_a_broadband/configs"
REPORT.mkdir(parents=True, exist_ok=True)
CONFIG.mkdir(parents=True, exist_ok=True)


def canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()


def sha(x):
    return hashlib.sha256(canon(x)).hexdigest()


def polygon(length, width, cx, cy, theta):
    a, b = length / 2.0, width / 2.0
    t = math.radians(theta)
    c, s = math.cos(t), math.sin(t)
    return [(cx + c*x - s*y, cy + s*x + c*y) for x, y in [(-a,-b),(a,-b),(a,b),(-a,b)]]


def axes(poly):
    out=[]
    for i in range(len(poly)):
        x1,y1=poly[i]; x2,y2=poly[(i+1)%len(poly)]
        ex,ey=x2-x1,y2-y1
        out.append((-ey,ex))
    return out


def overlap(a,b):
    for ax,ay in axes(a)+axes(b):
        norm=math.hypot(ax,ay); ax/=norm; ay/=norm
        pa=[x*ax+y*ay for x,y in a]; pb=[x*ax+y*ay for x,y in b]
        if max(pa) < min(pb)-1e-9 or max(pb) < min(pa)-1e-9: return False
    return True


def orient(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def between(a,b,c): return min(a[0],b[0])-1e-9<=c[0]<=max(a[0],b[0])+1e-9 and min(a[1],b[1])-1e-9<=c[1]<=max(a[1],b[1])+1e-9
def seg_inter(a,b,c,d):
    o1,o2,o3,o4=orient(a,b,c),orient(a,b,d),orient(c,d,a),orient(c,d,b)
    if abs(o1)<1e-9 and between(a,b,c): return True
    if abs(o2)<1e-9 and between(a,b,d): return True
    if abs(o3)<1e-9 and between(c,d,a): return True
    if abs(o4)<1e-9 and between(c,d,b): return True
    return (o1>0)!=(o2>0) and (o3>0)!=(o4>0)


def point_seg(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    den=dx*dx+dy*dy
    if den==0: return math.hypot(p[0]-a[0],p[1]-a[1])
    q=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den))
    return math.hypot(p[0]-(a[0]+q*dx),p[1]-(a[1]+q*dy))


def poly_gap(a,b):
    if overlap(a,b): return 0.0
    return min(point_seg(p,c,d) for p in a for c,d in zip(b,b[1:]+b[:1]))


def validity(g):
    px=py=432.0
    p1=polygon(g['L1_nm'],g['W1_nm'],0.0,g['D_nm']/2.0,0.0)
    p2=polygon(g['L2_nm'],g['W2_nm'],0.0,-g['D_nm']/2.0,g['delta_theta_deg'])
    polys=[p1,p2]
    reasons=[]; gaps=[]
    for idx,p in enumerate(polys):
        if any(abs(x)>px/2+1e-9 or abs(y)>py/2+1e-9 for x,y in p): reasons.append('CELL_CONTAINMENT')
        gaps += [px/2-abs(x) for x,y in p] + [py/2-abs(y) for x,y in p]
    for i in range(2):
        for j in range(2):
            for tx in (-px,0.0,px):
                for ty in (-py,0.0,py):
                    if i==j and tx==0 and ty==0: continue
                    q=[(x+tx,y+ty) for x,y in polys[j]]
                    if overlap(polys[i],q): reasons.append('PERIODIC_OR_PILLAR_OVERLAP')
                    else: gaps.append(poly_gap(polys[i],q))
    return {
        'geometry_valid': not reasons,
        'reasons': sorted(set(reasons)),
        'min_edge_gap_nm': float(max(0.0,min(gaps))) if gaps else None,
        'cell_containment_pass': 'CELL_CONTAINMENT' not in reasons,
        'no_overlap_pass': 'PERIODIC_OR_PILLAR_OVERLAP' not in reasons,
    }


def make_geom(gid, role, a1,b1,a2,b2,delta,D,source,idx=None):
    vals={'a1':float(a1),'b1':float(b1),'a2':float(a2),'b2':float(b2),'delta_theta_deg':float(delta),'D_nm':float(D)}
    g={'geometry_id':gid,'role':role,'source':source,'sobol_index':idx,**vals,
       'L1_nm':230.0*float(a1),'W1_nm':100.0*float(b1),'L2_nm':180.0*float(a2),'W2_nm':90.0*float(b2),
       'height_nm':525.0,'period_x_nm':432.0,'period_y_nm':432.0,
       'j1_center_x_nm':0.0,'j1_center_y_nm':float(D)/2.0,'j2_center_x_nm':0.0,'j2_center_y_nm':-float(D)/2.0,
       'j1_rotation_deg':0.0,'j2_rotation_deg':float(delta),
       'anisotropy_ratio_1':230.0*float(a1)/(100.0*float(b1)),
       'anisotropy_ratio_2':180.0*float(a2)/(90.0*float(b2))}
    g.update({'j1_length_nm':g['L1_nm'],'j1_width_nm':g['W1_nm'],'j2_length_nm':g['L2_nm'],'j2_width_nm':g['W2_nm']})
    g['relative_anisotropy']=g['anisotropy_ratio_1']/g['anisotropy_ratio_2']
    g['geometry_hash_sha256']=sha(g)
    g['validity']=validity(g)
    return g


def sobol_points(n):
    try:
        from scipy.stats import qmc
        return qmc.Sobol(d=6, scramble=False, seed=20260818).random_base2(m=4)
    except Exception as e:
        raise RuntimeError('SCIPY_SOBOL_REQUIRED_FOR_DETERMINISTIC_DOE') from e


def map_sobol(u):
    lo=np.array([.85,.85,.85,.85,0.,170.]); hi=np.array([1.15,1.15,1.15,1.15,90.,220.])
    return lo+(hi-lo)*u


def main():
    u=sobol_points(16)
    rows=[]
    rows.append(make_geom('ANISO_A01','ANISOTROPY_CONTRAST_J1_ENHANCED',1.15,.85,.85,1.15,25.,178.,'EXPLICIT_CONTRAST_ANCHOR'))
    rows.append(make_geom('ANISO_A02','ANISOTROPY_CONTRAST_REVERSE',.85,1.15,1.15,.85,65.,212.,'EXPLICIT_REVERSE_CONTRAST_ANCHOR'))
    for k,idx in enumerate([4,5,6,7,8,9], start=3):
        v=map_sobol(u[idx])
        phase='INITIAL_SOBOL' if k<=4 else 'CONDITIONAL_SOBOL'
        rows.append(make_geom(f'ANISO_A{k:02d}',phase,*v,source=f'SOBOL_SPACE_FILLING_SEED_20260818_INDEX_{idx}',idx=idx))
    replacement_log=[]
    for i,g in enumerate(rows):
        if g['validity']['geometry_valid']: continue
        for idx in range(10,16):
            v=map_sobol(u[idx])
            r=make_geom(g['geometry_id'],g['role'],*v,source=f'DETERMINISTIC_REPLACEMENT_FOR_{g["source"]}',idx=idx)
            replacement_log.append({'geometry_id':g['geometry_id'],'original':g,'replacement':r,'reason':g['validity']['reasons'],'replacement_sobol_index':idx})
            if r['validity']['geometry_valid']:
                rows[i]=r; break
        else: raise RuntimeError(f'NO_VALID_REPLACEMENT:{g["geometry_id"]}')
    for g in rows:
        g['case_ids']=[f"{g['geometry_id']}_x",f"{g['geometry_id']}_y"]
        g['solver_entered']=False
    doe={'schema':'PAPER_A_BROADBAND_LP_ANISOTROPY_EXPANDED_DOE_V1','stage':'PAPER_A_BROADBAND_LP_ANISOTROPY_EXPANDED_SEARCH_V1','seed':20260818,'dimension':6,'bounds':{'a1':[.85,1.15],'b1':[.85,1.15],'a2':[.85,1.15],'b2':[.85,1.15],'delta_theta_deg':[0.,90.],'D_nm':[170.,220.]},'initial_geometry_ids':['ANISO_A01','ANISO_A02','ANISO_A03','ANISO_A04'],'conditional_geometry_ids':['ANISO_A05','ANISO_A06','ANISO_A07','ANISO_A08'],'geometries':rows,'replacement_log':replacement_log,'solver_calls':0}
    doe['freeze_sha256']=sha(doe)
    (CONFIG/'anisotropy_expanded_doe_v1.json').write_text(json.dumps(doe,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (REPORT/'anisotropy_doe.csv').write_text('',encoding='utf-8')
    fields=[]
    for g in rows:
        for k in g:
            if k not in fields: fields.append(k)
    with (REPORT/'anisotropy_doe.csv').open('w',newline='',encoding='utf-8') as fh:
        w=csv.DictWriter(fh,fieldnames=fields,extrasaction='ignore'); w.writeheader()
        for g in rows: w.writerow({**g,'validity':json.dumps(g['validity'],sort_keys=True)})
    param={'schema':'PAPER_A_BROADBAND_LP_ANISOTROPY_PARAMETERIZATION_V1','stage':'PAPER_A_BROADBAND_LP_ANISOTROPY_EXPANDED_SEARCH_V1','backbone':{'candidate':'BW2_J1J2_D194_T90_PSI99_H525','cp_source_csv':str(ROOT/'paper_a_broadband/references/cp/stage10_cp_bw2_candidate_geometry.csv'),'exact_cp_values':{'period_x_nm':431.907786,'period_y_nm':432.0,'height_nm':525.0,'J1_L_nm':230.0,'J1_W_nm':100.0,'J2_L_nm':180.0,'J2_W_nm':90.0,'J1_rotation_deg':-9.0,'J2_rotation_deg':36.0,'relative_rotation_deg':45.0,'D_nm':194.0},'frozen_lp_projection':{'period_x_nm':432.0,'period_y_nm':432.0,'theta1_deg':0.0,'theta2_deg':'delta_theta','note':'existing LP plane-wave template projection; global common rotation redundancy not supported by H1E3A audit and no seventh DOF is introduced'}},'variables':['a1','b1','a2','b2','delta_theta_deg','D_nm'],'formulae':{'L1_nm':'a1*230.0','W1_nm':'b1*100.0','L2_nm':'a2*180.0','W2_nm':'b2*90.0'},'axis_free':True,'no_fixed_x_target':True,'stokes_contract':'C_in=0.5I; C_out=0.5 J J^H; DoLP=sqrt(S1^2+S2^2)/S0; psi=0.5 atan2(S2,S1) modulo-pi unwrap; P_LP_axisfree=0.5*(S0+sqrt(S1^2+S2^2))','rotation_audit':{'route_decision':'J1_ROTATION_PROJECTOR_RISK_DOMINANT','common_phase_lever':False,'minimum_treatment':'theta1=0, theta2=delta_theta; no global-angle expansion'},'source_monitor':{'source_span_nm':[430.,470.],'formal_window_nm':[435.,465.],'formal_points':31,'spacing_nm':1.0,'anchor_nm':450.},'solver_policy':{'max_geometries':8,'max_fdt_jobs':16,'max_active_paper_a_fdtd':2,'jobs_per_geometry':2,'mpi_processes':4,'threads':1,'global_fdtd_cap':3,'np_coupling_higher_priority':True,'entered_true_no_replay':True},'solver_entered':False}
    (REPORT/'anisotropy_parameterization.json').write_text(json.dumps(param,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','doe':str(CONFIG/'anisotropy_expanded_doe_v1.json'),'geometry_count':len(rows),'invalid_count':sum(not g['validity']['geometry_valid'] for g in rows),'replacement_count':len(replacement_log),'freeze_sha256':doe['freeze_sha256']},indent=2))


if __name__=='__main__': main()
