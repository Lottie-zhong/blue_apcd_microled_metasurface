from __future__ import annotations
import csv, json, math, struct, zlib
from pathlib import Path
REPO_ROOT=Path(__file__).resolve().parents[1]
OUT_DIR=REPO_ROOT/'outputs'/'blue10k6_lp_apcd_stage11_2b_h500_dimer_rebin'
REBIN=OUT_DIR/'h500_dimer_actual_phase_rebinned_stage11_2b.csv'
PLAN2A=REPO_ROOT/'outputs'/'blue10k6_lp_apcd_stage11_2a_h500_dimer_validation'/'h500_dimer_validation_plan_stage11_2a.csv'
PATCH=OUT_DIR/'h500_dimer_placement_patch_plan_stage11_2b.csv'; SUMMARY=OUT_DIR/'h500_dimer_placement_patch_plan_summary_stage11_2b.md'; PREVIEW=OUT_DIR/'h500_dimer_placement_patch_preview_stage11_2b.png'
PX=431.907786; PY=432.0; H=500.0; LAM=450.0
FIELDS=['dimer_patch_id','source_dimer_case_id','source_pair_id','original_static_bin_deg','target_actual_bin_deg','patch_reason','failure_mode_to_fix','j1_candidate_id','j2_candidate_id','height_nm','lambda_nm','p_x_nm','p_y_nm','j1_shape_family','j1_geometry_params','j2_length_nm','j2_width_nm','j2_rotation_deg','placement_type','swap_order','gap_nm','local_offset_nm','j1_center_x_nm','j1_center_y_nm','j2_center_x_nm','j2_center_y_nm','geometry_legal','expected_effect','priority','notes']
def read_csv(p):
    if not p.exists(): return []
    with p.open('r',encoding='utf-8-sig',newline='') as f: return [{str(k):'' if v is None else str(v) for k,v in r.items()} for r in csv.DictReader(f)]
def write_csv(p,rows,fields):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8',newline='') as f: w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def f(v,d=math.nan):
    try:
        if v is None or str(v).strip()=='': return d
        return float(v)
    except Exception: return d
def fmt(v): return '' if math.isnan(v) else f'{v:.6f}'
def sizes(src):
    gp=json.loads(src.get('j1_geometry_params','{}')); fam=src.get('j1_shape_family','')
    if fam=='circle': j1x=j1y=f(gp.get('diameter_nm'))
    elif fam=='square': j1x=j1y=f(gp.get('side_nm'))
    else: j1x=f(gp.get('length_nm')); j1y=f(gp.get('width_nm'))
    return j1x,j1y,f(src.get('j2_length_nm')),f(src.get('j2_width_nm'))
def place(src,placement,gap,offset,swap):
    j1x,j1y,j2x,j2y=sizes(src)
    if placement=='x_pair': sep=(j1x+j2x)/2+gap; x1,y1,x2,y2=-sep/2+offset/2,0,sep/2+offset/2,0
    elif placement=='y_pair': sep=(j1y+j2y)/2+gap; x1,y1,x2,y2=0,-sep/2+offset/2,0,sep/2+offset/2
    else: sepx=(j1x+j2x)/2+gap/math.sqrt(2); sepy=(j1y+j2y)/2+gap/math.sqrt(2); x1,y1,x2,y2=-sepx/2+offset/2,-sepy/2+offset/2,sepx/2+offset/2,sepy/2+offset/2
    if swap: x1,y1,x2,y2=x2,y2,x1,y1
    dx=abs(x2-x1)-(j1x+j2x)/2; dy=abs(y2-y1)-(j1y+j2y)/2
    dgap=math.hypot(dx,dy) if dx>=0 and dy>=0 else (dx if dx>=0 else (dy if dy>=0 else -min(-dx,-dy)))
    edge=min(PX/2-max(abs(x1)+j1x/2,abs(x2)+j2x/2), PY/2-max(abs(y1)+j1y/2,abs(y2)+j2y/2))
    return x1,y1,x2,y2,dgap,edge,dgap>=20 and edge>=10
def strategies(r):
    if r['actual_dimer_status']=='high_selectivity_common_phase_missed' or r['failure_mode']=='common_phase_shift_only': return ('A','same source, pull selected common phase by placement/gap/swap','common-phase pull/rebin',['y_pair','diag_pair'],[20,40,60],[-20,0,20],[False,True],4)
    if r['failure_mode']=='projection_matrix_broken_y_leakage': return ('B','restore projection matrix by reducing blocked y leakage','reduce blocked_input_total_power',['x_pair','diag_pair'],[60,80,100],[-20,0,20],[False,True],3)
    if r['failure_mode']=='selected_power_too_low': return ('C','source pair replacement recommended; diagnostic placement only','check whether placement recovers selected power',['diag_pair'],[60,80],[0],[False,True],2)
    return ('B','improve projection matrix and selected common phase','diagnostic placement patch',['x_pair','diag_pair'],[60,80],[-20,0],[False,True],3)
def tiny(path):
    w,h=320,180; pix=bytearray([255,255,255]*w*h)
    def ch(t,d): return struct.pack('!I',len(d))+t+d+struct.pack('!I',zlib.crc32(t+d)&0xffffffff)
    raw=b''.join(b'\x00'+bytes(pix[y*w*3:(y+1)*w*3]) for y in range(h)); path.write_bytes(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('!IIBBBBB',w,h,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw,9))+ch(b'IEND',b''))
def main():
    if not REBIN.exists(): raise SystemExit(f'missing required input: {REBIN}')
    plan={r['dimer_case_id']:r for r in read_csv(PLAN2A)}; srcs=[r for r in read_csv(REBIN) if r['dimer_case_id'] in plan]
    srcs.sort(key=lambda r:({'A':0,'B':1,'C':2}.get(strategies(r)[0],9), f(r.get('actual_common_phase_error_deg'),999), -f(r.get('projection_selectivity_ratio'),0)))
    rows=[]; seen=set(); counts={}
    for r in srcs:
        pri,reason,effect,placements,gaps,offs,swaps,cap=strategies(r); src=plan[r['dimer_case_id']]
        for pl in placements:
          for gap in gaps:
           for off in offs:
            for sw in swaps:
             if counts.get(r['dimer_case_id'],0)>=cap or len(rows)>=24: break
             x1,y1,x2,y2,dgap,edge,legal=place(src,pl,gap,off,sw)
             if not legal: continue
             key=(r['source_pair_id'],pl,gap,off,sw)
             if key in seen: continue
             seen.add(key); counts[r['dimer_case_id']]=counts.get(r['dimer_case_id'],0)+1
             rows.append({'dimer_patch_id':f"H500DIMER2B_{len(rows)+1:03d}_B{int(f(r['actual_nearest_bin_deg']))}_{pl}_{'swap' if sw else 'noswap'}_G{int(gap)}_O{int(off)}",'source_dimer_case_id':r['dimer_case_id'],'source_pair_id':r['source_pair_id'],'original_static_bin_deg':r['original_static_bin_deg'],'target_actual_bin_deg':r['actual_nearest_bin_deg'],'patch_reason':reason,'failure_mode_to_fix':r['failure_mode'],'j1_candidate_id':r['j1_candidate_id'],'j2_candidate_id':r['j2_candidate_id'],'height_nm':fmt(H),'lambda_nm':fmt(LAM),'p_x_nm':fmt(PX),'p_y_nm':fmt(PY),'j1_shape_family':src.get('j1_shape_family',''),'j1_geometry_params':src.get('j1_geometry_params',''),'j2_length_nm':src.get('j2_length_nm',''),'j2_width_nm':src.get('j2_width_nm',''),'j2_rotation_deg':src.get('j2_rotation_deg','0'),'placement_type':pl,'swap_order':'J2-J1' if sw else 'J1-J2','gap_nm':fmt(gap),'local_offset_nm':fmt(off),'j1_center_x_nm':fmt(x1),'j1_center_y_nm':fmt(y1),'j2_center_x_nm':fmt(x2),'j2_center_y_nm':fmt(y2),'geometry_legal':'true','expected_effect':effect,'priority':'Priority '+pri,'notes':'Stage11-2B revised projection-matrix aware placement patch'})
            if len(rows)>=24: break
           if len(rows)>=24: break
          if len(rows)>=24: break
        if len(rows)>=24: break
    write_csv(PATCH,rows,FIELDS)
    lines=['# Stage11-2B Revised H500 Dimer Placement Patch Plan','',f'patch_case_count = {len(rows)}',f'legal_count = {sum(1 for r in rows if r["geometry_legal"]=="true")}', 'No H600/H700, no K=6 supercell, no phase-gradient layout.','','| priority | failure_mode_to_fix | target_actual_bin | count | reason |','|---|---|---:|---:|---|']
    groups={}
    for r in rows: groups[(r['priority'],r['failure_mode_to_fix'],r['target_actual_bin_deg'],r['patch_reason'])]=groups.get((r['priority'],r['failure_mode_to_fix'],r['target_actual_bin_deg'],r['patch_reason']),0)+1
    for (pri,fm,b,reason),cnt in sorted(groups.items()): lines.append(f'| {pri} | {fm} | {b} | {cnt} | {reason} |')
    SUMMARY.write_text('\n'.join(lines)+'\n',encoding='utf-8'); tiny(PREVIEW); print(f'placement_patch_case_count={len(rows)}'); print(f'legal_count={sum(1 for r in rows if r["geometry_legal"]=="true")}')
if __name__=='__main__': main()
