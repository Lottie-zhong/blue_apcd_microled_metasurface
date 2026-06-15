from __future__ import annotations
import csv, json, math, struct, zlib
from pathlib import Path
REPO_ROOT=Path(__file__).resolve().parents[1]
OUT_DIR=REPO_ROOT/'outputs'/'blue10k6_lp_apcd_stage11_2c_h500_dimer_alt_pairs'
ALT=OUT_DIR/'h500_dimer_alt_source_pairs_stage11_2c.csv'
BEST2B=REPO_ROOT/'outputs'/'blue10k6_lp_apcd_stage11_2b_h500_dimer_rebin'/'h500_dimer_best_actual_6bin_candidates_stage11_2b.csv'
PLAN=OUT_DIR/'h500_dimer_alt_patch_plan_stage11_2c.csv'; SUMMARY=OUT_DIR/'h500_dimer_alt_patch_plan_summary_stage11_2c.md'; PREVIEW=OUT_DIR/'h500_dimer_alt_patch_preview_stage11_2c.png'
PX=431.907786; PY=432.0; H=500.0; LAM=450.0
FIELDS=['dimer_case_id','alt_pair_id','target_actual_bin_deg','source_pair_id','static_original_bin_deg','j1_candidate_id','j2_candidate_id','height_nm','lambda_nm','p_x_nm','p_y_nm','j1_shape_family','j1_geometry_params','j2_length_nm','j2_width_nm','j2_rotation_deg','placement_type','swap_order','gap_nm','local_offset_nm','j1_center_x_nm','j1_center_y_nm','j2_center_x_nm','j2_center_y_nm','dimer_gap_nm','edge_margin_nm','geometry_legal','expected_failure_mode_to_fix','expected_effect','priority','notes']
def read_csv(p):
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
def sizes(r):
    gp=json.loads(r['j1_geometry_params']); fam=r['j1_shape_family']
    if fam=='circle': j1x=j1y=f(gp.get('diameter_nm'))
    elif fam=='square': j1x=j1y=f(gp.get('side_nm'))
    else: j1x=f(gp.get('length_nm')); j1y=f(gp.get('width_nm'))
    return j1x,j1y,f(r['j2_length_nm']),f(r['j2_width_nm'])
def place(r,placement,gap,offset,swap):
    j1x,j1y,j2x,j2y=sizes(r)
    if placement=='x_pair': sep=(j1x+j2x)/2+gap; x1,y1,x2,y2=-sep/2+offset/2,0,sep/2+offset/2,0
    elif placement=='y_pair': sep=(j1y+j2y)/2+gap; x1,y1,x2,y2=0,-sep/2+offset/2,0,sep/2+offset/2
    else: sepx=(j1x+j2x)/2+gap/math.sqrt(2); sepy=(j1y+j2y)/2+gap/math.sqrt(2); x1,y1,x2,y2=-sepx/2+offset/2,-sepy/2+offset/2,sepx/2+offset/2,sepy/2+offset/2
    if swap: x1,y1,x2,y2=x2,y2,x1,y1
    dx=abs(x2-x1)-(j1x+j2x)/2; dy=abs(y2-y1)-(j1y+j2y)/2
    dgap=math.hypot(dx,dy) if dx>=0 and dy>=0 else (dx if dx>=0 else (dy if dy>=0 else -min(-dx,-dy)))
    edge=min(PX/2-max(abs(x1)+j1x/2,abs(x2)+j2x/2), PY/2-max(abs(y1)+j1y/2,abs(y2)+j2y/2))
    return x1,y1,x2,y2,dgap,edge,dgap>=20 and edge>=10
def variants(r):
    if r['priority']=='common_phase_pull': return ['y_pair','diag_pair','x_pair'],[20,40,60,80],[-30,-20,-10,0,10,20,30],[False,True],3,'maintain projection matrix and pull selected common phase toward target bin'
    return ['x_pair','diag_pair'],[60,80,100,120],[-20,0,20],[False,True],2,'reduce blocked y-input leakage and restore projection matrix'
def tiny(path):
    w,h=320,180; pix=bytearray([255,255,255]*w*h)
    def ch(t,d): return struct.pack('!I',len(d))+t+d+struct.pack('!I',zlib.crc32(t+d)&0xffffffff)
    raw=b''.join(b'\x00'+bytes(pix[y*w*3:(y+1)*w*3]) for y in range(h)); path.write_bytes(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('!IIBBBBB',w,h,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw,9))+ch(b'IEND',b''))
def main():
    if not ALT.exists(): raise SystemExit(f'missing required input: {ALT}')
    if not BEST2B.exists(): raise SystemExit(f'missing required input: {BEST2B}')
    rows=[]; seen=set()
    for a in read_csv(ALT):
        placements,gaps,offs,swaps,cap,effect=variants(a); count=0
        for pl in placements:
          for gap in gaps:
           for off in offs:
            for sw in swaps:
             if count>=cap or len(rows)>=48: break
             x1,y1,x2,y2,dgap,edge,legal=place(a,pl,gap,off,sw)
             if not legal: continue
             key=(a['source_pair_id'],pl,gap,off,sw)
             if key in seen: continue
             seen.add(key); count+=1
             rows.append({'dimer_case_id':f"H500DIMER2C_{len(rows)+1:03d}_B{a['target_actual_bin_deg']}_{pl}_{'swap' if sw else 'noswap'}_G{int(gap)}_O{int(off)}",'alt_pair_id':a['alt_pair_id'],'target_actual_bin_deg':a['target_actual_bin_deg'],'source_pair_id':a['source_pair_id'],'static_original_bin_deg':a['static_original_bin_deg'],'j1_candidate_id':a['j1_candidate_id'],'j2_candidate_id':a['j2_candidate_id'],'height_nm':fmt(H),'lambda_nm':fmt(LAM),'p_x_nm':fmt(PX),'p_y_nm':fmt(PY),'j1_shape_family':a['j1_shape_family'],'j1_geometry_params':a['j1_geometry_params'],'j2_length_nm':a['j2_length_nm'],'j2_width_nm':a['j2_width_nm'],'j2_rotation_deg':'0.000000','placement_type':pl,'swap_order':'J2-J1' if sw else 'J1-J2','gap_nm':fmt(gap),'local_offset_nm':fmt(off),'j1_center_x_nm':fmt(x1),'j1_center_y_nm':fmt(y1),'j2_center_x_nm':fmt(x2),'j2_center_y_nm':fmt(y2),'dimer_gap_nm':fmt(dgap),'edge_margin_nm':fmt(edge),'geometry_legal':'true','expected_failure_mode_to_fix':a['expected_failure_mode_to_fix'],'expected_effect':effect,'priority':a['priority'],'notes':'Stage11-2C H500 real-dimer projection-phase library expansion'})
            if len(rows)>=48: break
           if len(rows)>=48: break
          if len(rows)>=48: break
    write_csv(PLAN,rows,FIELDS)
    lines=['# Stage11-2C H500 Dimer Alt Patch Plan','',f'dimer_plan_case_count = {len(rows)}',f'legal_count = {sum(r["geometry_legal"]=="true" for r in rows)}','No H600/H700, no K=6, no phase-gradient supercell.','','| target_bin | count | purpose |','|---:|---:|---|']
    for b in [120,180,240,300]:
        sub=[r for r in rows if r['target_actual_bin_deg']==str(b)]
        purpose='common-phase pull' if b==300 else 'projection repair'
        lines.append(f'| {b} | {len(sub)} | {purpose} |')
    lines += ['',f'projection_repair_case_count = {sum(r["priority"]=="projection_repair" for r in rows)}',f'common_phase_pull_case_count = {sum(r["priority"]=="common_phase_pull" for r in rows)}']
    SUMMARY.write_text('\n'.join(lines)+'\n',encoding='utf-8'); tiny(PREVIEW)
    print(f'dimer_plan_case_count={len(rows)}'); print(f'legal_count={sum(r["geometry_legal"]=="true" for r in rows)}')
    for b in [120,180,240,300]: print(f'bin_{b}_count={sum(r["target_actual_bin_deg"]==str(b) for r in rows)}')
    print(f'projection_repair_case_count={sum(r["priority"]=="projection_repair" for r in rows)}'); print(f'common_phase_pull_case_count={sum(r["priority"]=="common_phase_pull" for r in rows)}')
if __name__=='__main__': main()
