from __future__ import annotations
import csv,json,math,struct,zlib
from pathlib import Path
REPO_ROOT=Path(__file__).resolve().parents[1]
OUT_DIR=REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_2d_h500_dimer_final_gap'
SRC=OUT_DIR/'h500_dimer_final_gap_source_pairs_stage11_2d.csv'
BEST=REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_2c_h500_dimer_alt_pairs/h500_dimer_best_actual_6bin_library_stage11_2c.csv'
PLAN=OUT_DIR/'h500_dimer_final_gap_patch_plan_stage11_2d.csv'; SUMMARY=OUT_DIR/'h500_dimer_final_gap_patch_plan_summary_stage11_2d.md'; PREVIEW=OUT_DIR/'h500_dimer_final_gap_patch_preview_stage11_2d.png'
PX=431.907786; PY=432.0; H=500.0; LAM=450.0
FIELDS=['dimer_case_id','final_gap_pair_id','target_actual_bin_deg','source_pair_id','static_original_bin_deg','j1_candidate_id','j2_candidate_id','height_nm','lambda_nm','p_x_nm','p_y_nm','j1_shape_family','j1_geometry_params','j2_length_nm','j2_width_nm','j2_rotation_deg','placement_type','swap_order','gap_nm','local_offset_nm','j1_center_x_nm','j1_center_y_nm','j2_center_x_nm','j2_center_y_nm','dimer_gap_nm','edge_margin_nm','geometry_legal','expected_failure_mode_to_fix','expected_effect','priority','notes']
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
    if r['target_actual_bin_deg']=='240': return ['x_pair','diag_pair'],[80,100,120,140],[-30,-15,0,15,30],[False,True],2,'reduce blocked_input_total_power and restore projection matrix'
    return ['y_pair','diag_pair','x_pair'],[20,30,40,50,60,80],[-40,-30,-20,-10,0,10,20,30,40],[False,True],3,'preserve projection and pull selected common phase toward 300 deg'
def tiny(path):
    w,h=320,180; pix=bytearray([255,255,255]*w*h)
    def ch(t,d): return struct.pack('!I',len(d))+t+d+struct.pack('!I',zlib.crc32(t+d)&0xffffffff)
    raw=b''.join(b'\x00'+bytes(pix[y*w*3:(y+1)*w*3]) for y in range(h)); path.write_bytes(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('!IIBBBBB',w,h,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw,9))+ch(b'IEND',b''))
def main():
    if not SRC.exists(): raise SystemExit(f'missing required input: {SRC}')
    if not BEST.exists(): raise SystemExit(f'missing required input: {BEST}')
    rows=[]; seen=set()
    for s in read_csv(SRC):
        placements,gaps,offs,swaps,cap,effect=variants(s); count=0
        for pl in placements:
          for gap in gaps:
           for off in offs:
            for sw in swaps:
             if count>=cap or len(rows)>=48: break
             x1,y1,x2,y2,dgap,edge,legal=place(s,pl,gap,off,sw)
             if not legal: continue
             key=(s['source_pair_id'],pl,gap,off,sw)
             if key in seen: continue
             seen.add(key); count+=1
             rows.append({'dimer_case_id':f"H500DIMER2D_{len(rows)+1:03d}_B{s['target_actual_bin_deg']}_{pl}_{'swap' if sw else 'noswap'}_G{int(gap)}_O{int(off)}",'final_gap_pair_id':s['final_gap_pair_id'],'target_actual_bin_deg':s['target_actual_bin_deg'],'source_pair_id':s['source_pair_id'],'static_original_bin_deg':s['static_original_bin_deg'],'j1_candidate_id':s['j1_candidate_id'],'j2_candidate_id':s['j2_candidate_id'],'height_nm':fmt(H),'lambda_nm':fmt(LAM),'p_x_nm':fmt(PX),'p_y_nm':fmt(PY),'j1_shape_family':s['j1_shape_family'],'j1_geometry_params':s['j1_geometry_params'],'j2_length_nm':s['j2_length_nm'],'j2_width_nm':s['j2_width_nm'],'j2_rotation_deg':'0.000000','placement_type':pl,'swap_order':'J2-J1' if sw else 'J1-J2','gap_nm':fmt(gap),'local_offset_nm':fmt(off),'j1_center_x_nm':fmt(x1),'j1_center_y_nm':fmt(y1),'j2_center_x_nm':fmt(x2),'j2_center_y_nm':fmt(y2),'dimer_gap_nm':fmt(dgap),'edge_margin_nm':fmt(edge),'geometry_legal':'true','expected_failure_mode_to_fix':s['expected_failure_mode_to_fix'],'expected_effect':effect,'priority':s['priority'],'notes':'Stage11-2D final two-bin H500 dimer projection-phase closure'})
            if len(rows)>=48: break
           if len(rows)>=48: break
          if len(rows)>=48: break
    write_csv(PLAN,rows,FIELDS)
    lines=['# Stage11-2D H500 Final Gap Patch Plan','',f'source_pair_count = {len(read_csv(SRC))}',f'plan_case_count = {len(rows)}',f'legal_count = {sum(r["geometry_legal"]=="true" for r in rows)}','No H600/H700, no K=6, no phase-gradient supercell.','','| target_bin | count | purpose |','|---:|---:|---|']
    for b in [240,300]: lines.append(f'| {b} | {sum(r["target_actual_bin_deg"]==str(b) for r in rows)} | {"projection repair" if b==240 else "common phase pull"} |')
    SUMMARY.write_text('\n'.join(lines)+'\n',encoding='utf-8'); tiny(PREVIEW)
    print(f'source_pair_count={len(read_csv(SRC))}'); print(f'plan_case_count={len(rows)}'); print(f'legal_count={sum(r["geometry_legal"]=="true" for r in rows)}'); print(f'bin_240_count={sum(r["target_actual_bin_deg"]=="240" for r in rows)}'); print(f'bin_300_count={sum(r["target_actual_bin_deg"]=="300" for r in rows)}')
if __name__=='__main__': main()
