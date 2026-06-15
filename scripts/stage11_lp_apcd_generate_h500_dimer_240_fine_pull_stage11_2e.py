from __future__ import annotations
import csv,json,math,struct,zlib
from pathlib import Path
REPO_ROOT=Path(__file__).resolve().parents[1]
RESULT2D=REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_2d_h500_dimer_final_gap/h500_dimer_final_gap_fdtd_results_stage11_2d.csv'
PLAN2D=REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_2d_h500_dimer_final_gap/h500_dimer_final_gap_patch_plan_stage11_2d.csv'
BEST2D=REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_2d_h500_dimer_final_gap/h500_dimer_best_actual_6bin_library_stage11_2d.csv'
GAP2D=REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_2d_h500_dimer_final_gap/h500_dimer_remaining_gap_diagnosis_stage11_2d.md'
OUT_DIR=REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_2e_h500_dimer_240_fine_pull'
OUT=OUT_DIR/'h500_dimer_240_fine_pull_plan_stage11_2e.csv'; SUMMARY=OUT_DIR/'h500_dimer_240_fine_pull_plan_summary_stage11_2e.md'; PREVIEW=OUT_DIR/'h500_dimer_240_fine_pull_preview_stage11_2e.png'
BASE='H500DIMER2D_018_B240_x_pair_swap_G80_O-30'; PX=431.907786; PY=432.0; H=500.0; LAM=450.0
FIELDS=['dimer_case_id','base_case_id','target_actual_bin_deg','source_pair_id','static_original_bin_deg','j1_candidate_id','j2_candidate_id','height_nm','lambda_nm','p_x_nm','p_y_nm','j1_shape_family','j1_geometry_params','j2_length_nm','j2_width_nm','j2_rotation_deg','placement_type','swap_order','gap_nm','local_offset_nm','j1_center_x_nm','j1_center_y_nm','j2_center_x_nm','j2_center_y_nm','dimer_gap_nm','edge_margin_nm','geometry_legal','expected_failure_mode_to_fix','expected_effect','priority','notes']
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
def sizes(r):
    gp=json.loads(r['j1_geometry_params']); fam=r['j1_shape_family']
    if fam=='circle': j1x=j1y=f(gp.get('diameter_nm'))
    elif fam=='square': j1x=j1y=f(gp.get('side_nm'))
    else: j1x=f(gp.get('length_nm')); j1y=f(gp.get('width_nm'))
    return j1x,j1y,f(r['j2_length_nm']),f(r['j2_width_nm'])
def place(r,placement,gap,offset,swap=True):
    j1x,j1y,j2x,j2y=sizes(r)
    if placement=='x_pair': sep=(j1x+j2x)/2+gap; x1,y1,x2,y2=-sep/2+offset/2,0,sep/2+offset/2,0
    elif placement=='diag_pair': sepx=(j1x+j2x)/2+gap/math.sqrt(2); sepy=(j1y+j2y)/2+gap/math.sqrt(2); x1,y1,x2,y2=-sepx/2+offset/2,-sepy/2+offset/2,sepx/2+offset/2,sepy/2+offset/2
    else: sep=(j1y+j2y)/2+gap; x1,y1,x2,y2=0,-sep/2+offset/2,0,sep/2+offset/2
    if swap: x1,y1,x2,y2=x2,y2,x1,y1
    dx=abs(x2-x1)-(j1x+j2x)/2; dy=abs(y2-y1)-(j1y+j2y)/2
    dgap=math.hypot(dx,dy) if dx>=0 and dy>=0 else (dx if dx>=0 else (dy if dy>=0 else -min(-dx,-dy)))
    edge=min(PX/2-max(abs(x1)+j1x/2,abs(x2)+j2x/2), PY/2-max(abs(y1)+j1y/2,abs(y2)+j2y/2))
    return x1,y1,x2,y2,dgap,edge,dgap>=20 and edge>=10
def tiny(path):
    w,h=320,180; pix=bytearray([255,255,255]*w*h)
    def ch(t,d): return struct.pack('!I',len(d))+t+d+struct.pack('!I',zlib.crc32(t+d)&0xffffffff)
    raw=b''.join(b'\x00'+bytes(pix[y*w*3:(y+1)*w*3]) for y in range(h)); path.write_bytes(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('!IIBBBBB',w,h,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw,9))+ch(b'IEND',b''))
def main():
    for p in [RESULT2D,BEST2D,GAP2D,PLAN2D]:
        if not p.exists(): raise SystemExit(f'missing required input: {p}')
    base=next((r for r in read_csv(PLAN2D) if r['dimer_case_id']==BASE),None)
    if not base: raise SystemExit(f'missing base case in plan: {BASE}')
    specs=[]
    for gap in [70,75,80,85,90,95,100]:
        for off in [-45,-40,-35,-30,-25,-20,-15]: specs.append(('x_pair',gap,off))
    for gap in [70,80,90]:
        for off in [-40,-30,-20]: specs.append(('diag_pair',gap,off))
    x_specs=sorted([s for s in specs if s[0]=='x_pair'],key=lambda x:(abs(x[1]-80), abs(x[2]+30), 0 if 75<=x[1]<=90 else 1, 0 if -40<=x[2]<=-20 else 1))
    diag_specs=sorted([s for s in specs if s[0]=='diag_pair'],key=lambda x:(abs(x[1]-80), abs(x[2]+30)))
    # Keep the fine-pull dominated by the base x-pair swap geometry, while
    # reserving a small diagnostic slice for conservative diag-pair backups.
    ordered_specs=x_specs[:30]+diag_specs[:6]
    rows=[]; seen=set()
    for pl,gap,off in ordered_specs:
        if len(rows)>=36: break
        x1,y1,x2,y2,dgap,edge,legal=place(base,pl,gap,off,True)
        if not legal: continue
        key=(pl,gap,off)
        if key in seen: continue
        seen.add(key)
        rows.append({'dimer_case_id':f"H500DIMER2E_{len(rows)+1:03d}_B240_{pl}_swap_G{int(gap)}_O{int(off)}",'base_case_id':BASE,'target_actual_bin_deg':'240','source_pair_id':base['source_pair_id'],'static_original_bin_deg':base.get('static_original_bin_deg',''),'j1_candidate_id':base['j1_candidate_id'],'j2_candidate_id':base['j2_candidate_id'],'height_nm':fmt(H),'lambda_nm':fmt(LAM),'p_x_nm':fmt(PX),'p_y_nm':fmt(PY),'j1_shape_family':base['j1_shape_family'],'j1_geometry_params':base['j1_geometry_params'],'j2_length_nm':base['j2_length_nm'],'j2_width_nm':base['j2_width_nm'],'j2_rotation_deg':base.get('j2_rotation_deg','0'),'placement_type':pl,'swap_order':'J2-J1','gap_nm':fmt(gap),'local_offset_nm':fmt(off),'j1_center_x_nm':fmt(x1),'j1_center_y_nm':fmt(y1),'j2_center_x_nm':fmt(x2),'j2_center_y_nm':fmt(y2),'dimer_gap_nm':fmt(dgap),'edge_margin_nm':fmt(edge),'geometry_legal':'true','expected_failure_mode_to_fix':'common_phase_missed','expected_effect':'fine pull selected-channel actual common phase into 240 deg loose/strict bin','priority':'common_phase_fine_pull','notes':'Stage11-2E H500 240 deg common-phase fine pull around best 2D near-miss'})
    write_csv(OUT,rows,FIELDS)
    gaps=[f(r['gap_nm']) for r in rows]; offs=[f(r['local_offset_nm']) for r in rows]
    lines=['# Stage11-2E H500 240 Fine Pull Plan','',f'base_case = {BASE}',f'plan_case_count = {len(rows)}',f'legal_count = {sum(r["geometry_legal"]=="true" for r in rows)}',f'x_pair_count = {sum(r["placement_type"]=="x_pair" for r in rows)}',f'diag_pair_count = {sum(r["placement_type"]=="diag_pair" for r in rows)}',f'gap_range_nm = {min(gaps) if gaps else ""} to {max(gaps) if gaps else ""}',f'offset_range_nm = {min(offs) if offs else ""} to {max(offs) if offs else ""}','','Only H500 dimer common-phase fine pull. No K=6, no H600/H700.']
    SUMMARY.write_text('\n'.join(lines)+'\n',encoding='utf-8'); tiny(PREVIEW)
    print(f'plan_case_count={len(rows)}'); print(f'legal_count={sum(r["geometry_legal"]=="true" for r in rows)}'); print(f'x_pair_count={sum(r["placement_type"]=="x_pair" for r in rows)}'); print(f'diag_pair_count={sum(r["placement_type"]=="diag_pair" for r in rows)}')
if __name__=='__main__': main()
