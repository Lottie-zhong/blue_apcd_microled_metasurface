from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

import mpmath as mp

ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
REPORT = ROOT / "paper_a_broadband/reports/lp_anisotropy_expanded_search_v1"
DOE_PATH = ROOT / "paper_a_broadband/configs/anisotropy_expanded_doe_v1.json"
BUILDER = ROOT / "paper_a_broadband/scripts/lp_anisotropy_bootstrap_v1.py"
AUTH = ROOT / "paper_a_broadband/authority"
UPSTREAM = Path(r"D:/project/worktrees/blue_apcd_lp_global_h_manifold_v1")

mp.mp.dps = 80


def mpf(x): return mp.mpf(str(x))


def polygon(length, width, cx, cy, theta_deg):
    a, b = mpf(length) / 2, mpf(width) / 2
    t = mp.radians(mpf(theta_deg)); c, s = mp.cos(t), mp.sin(t)
    return [(mpf(cx) + c*x - s*y, mpf(cy) + s*x + c*y) for x, y in [(-a,-b),(a,-b),(a,b),(-a,b)]]


def orient(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def on_segment(a,b,p):
    return min(a[0],b[0]) <= p[0] <= max(a[0],b[0]) and min(a[1],b[1]) <= p[1] <= max(a[1],b[1])


def intersects(a,b,c,d):
    o1,o2,o3,o4=orient(a,b,c),orient(a,b,d),orient(c,d,a),orient(c,d,b)
    if o1 == 0 and on_segment(a,b,c): return True
    if o2 == 0 and on_segment(a,b,d): return True
    if o3 == 0 and on_segment(c,d,a): return True
    if o4 == 0 and on_segment(c,d,b): return True
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)


def point_segment(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]; den=dx*dx+dy*dy
    t=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den
    t=max(mp.mpf(0),min(mp.mpf(1),t))
    q=(a[0]+t*dx,a[1]+t*dy)
    return mp.sqrt((p[0]-q[0])**2+(p[1]-q[1])**2), q, t


def polygon_pair_distance(a,b):
    for i in range(4):
        for j in range(4):
            if intersects(a[i],a[(i+1)%4],b[j],b[(j+1)%4]):
                return mp.mpf(0), None
    best=None
    for side, pset, qset in [('A_to_B',a,b),('B_to_A',b,a)]:
        for i,p in enumerate(pset):
            for j in range(4):
                d,q,t=point_segment(p,qset[j],qset[(j+1)%4])
                rec=(d,side,i,j,p,q,t)
                if best is None or d<best[0]: best=rec
    return best[0], best


def fmt(x): return mp.nstr(x, 30)
def point_fmt(p): return [fmt(p[0]),fmt(p[1])] if p is not None else None


def simple_status(cmd, cwd=ROOT):
    p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True)
    return {'rc':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()}


def boundary_clearance(poly, name, half_x, half_y):
    rows=[]
    for i,(x,y) in enumerate(poly):
        rows.extend([
          {'object':name,'vertex_index':i,'boundary':'left','clearance_nm':fmt(x+half_x),'point_nm':point_fmt((x,y))},
          {'object':name,'vertex_index':i,'boundary':'right','clearance_nm':fmt(half_x-x),'point_nm':point_fmt((x,y))},
          {'object':name,'vertex_index':i,'boundary':'bottom','clearance_nm':fmt(y+half_y),'point_nm':point_fmt((x,y))},
          {'object':name,'vertex_index':i,'boundary':'top','clearance_nm':fmt(half_y-y),'point_nm':point_fmt((x,y))},
        ])
    return sorted(rows,key=lambda x:mpf(x['clearance_nm']))


def main():
    doe=json.loads(DOE_PATH.read_text(encoding='utf-8'))
    g=next(x for x in doe['geometries'] if x['geometry_id']=='ANISO_A02')
    px=py=mpf(432)
    p1=polygon(g['L1_nm'],g['W1_nm'],g['j1_center_x_nm'],g['j1_center_y_nm'],g['j1_rotation_deg'])
    p2=polygon(g['L2_nm'],g['W2_nm'],g['j2_center_x_nm'],g['j2_center_y_nm'],g['j2_rotation_deg'])
    pairs=[]
    for i,a in enumerate([p1,p2],1):
        for j,b in enumerate([p1,p2],1):
            for tx in [-px,mpf(0),px]:
                for ty in [-py,mpf(0),py]:
                    if i==j and tx==0 and ty==0: continue
                    shifted=[(x+tx,y+ty) for x,y in b]
                    d,detail=polygon_pair_distance(a,shifted)
                    pairs.append({'object_a':f'pillar_{i}','object_b':f'pillar_{j}','image_shift_nm':[fmt(tx),fmt(ty)],'distance_nm':fmt(d),'detail':{'side':detail[1],'a_vertex_index':detail[2],'b_side_index':detail[3],'point_a':point_fmt(detail[4]),'point_b':point_fmt(detail[5]),'projection_t':fmt(detail[6])} if detail else {'intersection':True}})
    pairs.sort(key=lambda x:mpf(x['distance_nm']))
    same=[x for x in pairs if x['image_shift_nm']==['0.0','0.0'] and x['object_a']!=x['object_b']]
    periodic=[x for x in pairs if x['image_shift_nm']!=['0.0','0.0'] and x['object_a']!=x['object_b']]
    boundaries=boundary_clearance(p1,'pillar_1',px/2,py/2)+boundary_clearance(p2,'pillar_2',px/2,py/2)
    boundaries.sort(key=lambda x:mpf(x['clearance_nm']))
    boundary_min=boundaries[0]
    same_min=sorted(same,key=lambda x:mpf(x['distance_nm']))[0]
    periodic_direct_min=sorted(periodic,key=lambda x:mpf(x['distance_nm']))[0]
    seam_gap=2*mpf(boundary_min['clearance_nm'])
    source_lines=BUILDER.read_text(encoding='utf-8',errors='replace').splitlines()
    validity_start=next((i+1 for i,x in enumerate(source_lines) if x.startswith('def validity')),None)
    validity_end=next((i for i,x in enumerate(source_lines[validity_start or 1:],validity_start or 1) if x.startswith('def make_geom')),None)
    rules_current=[]; rules_upstream=[]
    current_paths=[AUTH,BUILDER]
    for pth in current_paths:
        if pth.is_file():
            for n,line in enumerate(pth.read_text(encoding='utf-8',errors='replace').splitlines(),1):
                if re.search(r'(MIN[_ -]?GAP|minimum[_ -]?gap|clearance.*20|minimum.*20|mesh.*separ|separab)',line,re.I): rules_current.append({'path':str(pth),'line':n,'text':line[:300]})
    for pth in [UPSTREAM/'scripts/lp_ml1/lp_ml1a4_explicit_geometry_seed_generator.py',UPSTREAM/'scripts/lp_ml1/lp_ml1a_seed_manifest_dryrun.py']:
        if pth.exists():
            for n,line in enumerate(pth.read_text(encoding='utf-8',errors='replace').splitlines(),1):
                if re.search(r'(clearance.*20|minimum.*20|< 20)',line,re.I): rules_upstream.append({'path':str(pth),'line':n,'text':line[:300],'classification':'historical LP-ML-specific rule; not current Paper A anisotropy authority'})
    out={
      'schema':'PAPER_A_ANISO_A02_INDEPENDENT_GEOMETRY_AUDIT_V1',
      'canonical_geometry_id':'ANISO_A02',
      'source_doe_sha256':hashlib.sha256(DOE_PATH.read_bytes()).hexdigest(),
      'exact_geometry':{k:g.get(k) for k in ['L1_nm','W1_nm','L2_nm','W2_nm','j1_center_x_nm','j1_center_y_nm','j2_center_x_nm','j2_center_y_nm','j1_rotation_deg','j2_rotation_deg','D_nm','period_x_nm','period_y_nm','height_nm']},
      'vertices_nm':{'pillar_1':[point_fmt(x) for x in p1],'pillar_2':[point_fmt(x) for x in p2]},
      'canonical_validity_reconstruction':{'source_path':str(BUILDER),'source_sha256':hashlib.sha256(BUILDER.read_bytes()).hexdigest(),'validity_function_line_start':validity_start,'validity_function_line_end':validity_end,'cell_boundary_convention':'x,y in [-P/2,+P/2]; boundary clearance is included in the canonical aggregate min_edge_gap_nm','pair_translation_convention':'periodic shifts tx,ty in {-P,0,+P}','minimum_same_cell_pair_gap_nm':same_min['distance_nm'],'minimum_direct_distinct_periodic_pair_gap_nm':periodic_direct_min['distance_nm'],'minimum_cell_boundary_clearance_nm':boundary_min['clearance_nm'],'minimum_aggregate_value_nm':fmt(min(mpf(same_min['distance_nm']),mpf(periodic_direct_min['distance_nm']),mpf(boundary_min['clearance_nm'])))},
      'periodic_seam':{'boundary_record':boundary_min,'boundary_to_boundary_same_object_seam_gap_nm':fmt(seam_gap),'object':'pillar_2','copy_translation_nm':['0.0','432.0'],'original_point_nm':boundary_min['point_nm'],'periodic_copy_point_nm':[boundary_min['point_nm'][0],fmt(mpf(boundary_min['point_nm'][1])+py)]},
      'interpretation':{'reported_canonical_min_edge_gap_nm':g['validity']['min_edge_gap_nm'],'reported_value_definition':'aggregate of polygon pair distances and cell-boundary clearances; field name is not a pure pillar-to-pillar edge gap','reported_value_source':'pillar_2 vertex 2 to bottom cell boundary y=-216 nm','reported_pair_is_same_cell':False,'reported_pair_is_periodic_image':False,'independent_same_cell_pillar_pair_gap_nm':same_min['distance_nm'],'independent_periodic_seam_gap_nm':fmt(seam_gap),'classification':'REPORTING_DEFINITION_ARTIFACT_REVEALS_GENUINE_PERIODIC_SEAM_NEAR_CONTACT','pre_admission_status':'PRE_ADMISSION_GEOMETRY_RISK'},
      'topology':{'same_cell_polygon_intersection':same_min['distance_nm']=='0.0','mathematical_non_overlap':mpf(same_min['distance_nm'])>0,'two_distinct_pillar_objects_in_builder':True,'a02_child_fsp_exists':(ROOT/'paper_a_broadband/runtime/search_anisotropy_v1/cases/ANISO_A02_x/ANISO_A02_x_pre.fsp').exists() or (ROOT/'paper_a_broadband/runtime/search_anisotropy_v1/cases/ANISO_A02_y/ANISO_A02_y_pre.fsp').exists(),'canonical_fsp_topology_evidence':'No A02 child FSP exists; topology is established from the canonical two-object builder model, not from an instantiated A02 FSP.','periodic_tiling_near_contact':True},
      'authoritative_rules_scan':{'current_paper_a':rules_current,'historical_upstream_noncurrent':rules_upstream},
      'git_snapshot':{'branch':simple_status(['git','branch','--show-current'])['stdout'],'head':simple_status(['git','rev-parse','HEAD'])['stdout']},
    }
    out['authoritative_rules_summary']={'current_paper_a_hard_minimum_gap_nm_found':False,'historical_upstream_noncurrent_20nm_rules_found':bool(rules_upstream),'note':'No hard minimum-gap or mesh-separability threshold exists in the current Paper A anisotropy authority. Historical LP-ML rules mention 20 nm but are not current Paper A authority and were not imported.'}
    out['safety_invariants']={'DOE_changed':False,'new_fdtd_budget':0,'solver_run_called':False,'solver_entered':0,'active_fdtd':0,'rcwa':0,'ml':0,'ready_pending_hidden_auto_admission':0}
    out['decision']={'status':'PRE_ADMISSION_GEOMETRY_RISK','benchmark_admission_safe':False,'reason':'Periodic seam clearance is 0.06399106024997536 nm, with 0.03199553012498768 nm boundary margin; do not authorize A02 benchmark entry without scientific decision.'}
    out_path=REPORT/'a02_pre_admission_geometry_audit.json'; out_path.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    md=['# A02 pre-admission geometry audit','',f"Status: `PRE_ADMISSION_GEOMETRY_RISK`",'',f"The reported 0.032 nm is not the pillar-1/pillar-2 edge gap. It is the distance from pillar_2 vertex 2 to the lower periodic cell boundary y=-216 nm: `{boundary_min['clearance_nm']} nm`. The implied same-object periodic seam gap is `{fmt(seam_gap)} nm`.",'',f"Same-cell pillar_1/pillar_2 minimum edge gap: `{same_min['distance_nm']} nm`, between pillar_2 vertex 2 and the bottom edge of pillar_1 at x approximately `{same_min['detail']['point_a'][0]} nm`.",f"Minimum direct distinct periodic-image pair gap: `{periodic_direct_min['distance_nm']} nm`; the limiting physical periodic seam is the pillar_2 copy across the y boundary.",'', 'A02 consists of two distinct non-intersecting rectangles in the builder model, but its periodic seam clearance is sub-resolution/physically ambiguous. No A02 child FSP exists, so FSP topology was not claimed from an uninstantiated file.', '', 'No current Paper A hard minimum-gap or mesh-separability threshold was found. Historical LP-ML-specific 20 nm rules exist upstream but were not imported into this Paper A contract.', '', 'DOE unchanged. No FDTD/RCWA/ML was run. Benchmark admission remains blocked pending scientific decision.']
    (REPORT/'a02_pre_admission_geometry_audit.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps({'status':out['decision']['status'],'reported_nm':g['validity']['min_edge_gap_nm'],'same_cell_gap_nm':same_min['distance_nm'],'periodic_seam_gap_nm':fmt(seam_gap),'benchmark_admission_safe':False,'audit_json':str(out_path)},indent=2))

if __name__=='__main__': main()
