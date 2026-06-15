from __future__ import annotations
import csv,json,math
from pathlib import Path
REPO_ROOT=Path(__file__).resolve().parents[1]
PAIR_CSV=REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_1e_h500_gap_closure/lp_pair_candidates_h500_stage11_1e_merged_reranked.csv'
BEST=REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_2c_h500_dimer_alt_pairs/h500_dimer_best_actual_6bin_library_stage11_2c.csv'
GAP=REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_2c_h500_dimer_alt_pairs/h500_dimer_remaining_gap_diagnosis_stage11_2c.md'
PROJ=REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_2c_h500_dimer_alt_pairs/h500_dimer_projection_matrix_diagnosis_stage11_2c.md'
OUT_DIR=REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_2d_h500_dimer_final_gap'
OUT=OUT_DIR/'h500_dimer_final_gap_source_pairs_stage11_2d.csv'; SUMMARY=OUT_DIR/'h500_dimer_final_gap_pair_selection_summary_stage11_2d.md'
FIELDS=['final_gap_pair_id','target_actual_bin_deg','source_pair_id','static_original_bin_deg','j1_candidate_id','j2_candidate_id','height_nm','j1_shape_family','j1_geometry_params','j2_length_nm','j2_width_nm','static_predicted_ratio','static_target_x_power','static_leak_y_power','static_output_phase_deg','static_s1_s2_amp_ratio','static_s1_s2_phase_mismatch_deg','selection_reason','expected_failure_mode_to_fix','priority']
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
def load_lookup(paths):
    out={}
    for p in paths:
        for r in read_csv(p):
            if r.get('candidate_id') and r['candidate_id'] not in out: out[r['candidate_id']]=r
    return out
def j1_geom(r):
    fam=r.get('shape_family','')
    if fam=='circle': return fam,json.dumps({'diameter_nm':f(r.get('diameter_nm'))})
    if fam=='square': return fam,json.dumps({'side_nm':f(r.get('side_nm'))})
    return fam,json.dumps({'length_nm':f(r.get('length_nm')),'width_nm':f(r.get('width_nm'))})
def dims(j1row,j2row):
    fam,geom=j1_geom(j1row); g=json.loads(geom)
    if fam=='circle': j1x=j1y=f(g.get('diameter_nm'))
    elif fam=='square': j1x=j1y=f(g.get('side_nm'))
    else: j1x,j1y=f(g.get('length_nm')),f(g.get('width_nm'))
    return fam,geom,j1x,j1y,f(j2row.get('length_nm')),f(j2row.get('width_nm'))
def feasible(j1row,j2row,mode):
    fam,geom,j1x,j1y,j2x,j2y=dims(j1row,j2row)
    if math.isnan(j2x) or math.isnan(j2y): return False,1e9
    if mode=='projection_repair': ok=(j1x+j2x+80<=411.907786 and max(j1y,j2y)<=412)
    else: ok=(max(j1x,j2x)<=411.907786 and j1y+j2y+20<=412)
    return ok,max(j1x,j2x)+max(j1y,j2y)
def main():
    for p in [PAIR_CSV,BEST,GAP,PROJ]:
        if not p.exists(): raise SystemExit(f'missing required input: {p}')
    j1=load_lookup([REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_1e_h500_gap_closure/h500_j1_gap_closure_plan_stage11_1e.csv',REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_1d_targeted_patch/j1_identity_patch_plan_stage11_1d.csv',REPO_ROOT/'outputs/blue10k6_lp_apcd_j1_identity_scan/j1_identity_plan.csv'])
    j2=load_lookup([REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_1e_h500_gap_closure/h500_j2_gap_closure_plan_stage11_1e.csv',REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_1d_targeted_patch/j2_hwp_patch_plan_stage11_1d.csv',REPO_ROOT/'outputs/blue10k6_lp_apcd_j2_hwp_scan/j2_hwp_plan.csv',REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_1e_h500_gap_closure/h500_j2_gap_closure_fdtd_results_stage11_1e.csv'])
    pairs=[r for r in read_csv(PAIR_CSV) if f(r.get('j1_height_nm'))==500 and f(r.get('j2_height_nm'))==500 and r.get('same_height_pair')=='true' and f(r.get('predicted_ratio'))>=6 and f(r.get('target_x_power'))>=0.15]
    rows=[]; used=set()
    def score(r,target,mode):
        phase=abs(((f(r.get('output_phase_deg'))-target+180)%360)-180); mismatch=f(r.get('s1_s2_phase_mismatch_deg'),999); amp=abs(1-f(r.get('s1_s2_amp_ratio'),0)); leak=f(r.get('leak_y_power'),999); ratio=f(r.get('predicted_ratio'),0)
        a=j1.get(r.get('j1_candidate_id','')); b=j2.get(r.get('j2_candidate_id','')); ok,foot=feasible(a,b,mode) if a and b else (False,1e9)
        bad=0 if ok else 100
        return (bad, foot, mismatch if mode=='projection_repair' else phase, amp, leak, phase, -ratio)
    def add(target, mode, maxn, reason, fail, priority):
        nonlocal rows
        count=0
        for r in sorted(pairs,key=lambda x:score(x,target,mode)):
            if count>=maxn: break
            if r['pair_id'] in used: continue
            a=j1.get(r['j1_candidate_id']); b=j2.get(r['j2_candidate_id'])
            if not a or not b: continue
            ok,foot=feasible(a,b,mode)
            if not ok: continue
            fam,geom,j1x,j1y,j2x,j2y=dims(a,b)
            rows.append({'final_gap_pair_id':f'FG2D_B{target}_{count+1:02d}','target_actual_bin_deg':str(target),'source_pair_id':r['pair_id'],'static_original_bin_deg':r.get('target_phase_bin_deg',''),'j1_candidate_id':r['j1_candidate_id'],'j2_candidate_id':r['j2_candidate_id'],'height_nm':'500.000000','j1_shape_family':fam,'j1_geometry_params':geom,'j2_length_nm':fmt(j2x),'j2_width_nm':fmt(j2y),'static_predicted_ratio':r.get('predicted_ratio',''),'static_target_x_power':r.get('target_x_power',''),'static_leak_y_power':r.get('leak_y_power',''),'static_output_phase_deg':r.get('output_phase_deg',''),'static_s1_s2_amp_ratio':r.get('s1_s2_amp_ratio',''),'static_s1_s2_phase_mismatch_deg':r.get('s1_s2_phase_mismatch_deg',''),'selection_reason':reason,'expected_failure_mode_to_fix':fail,'priority':priority})
            used.add(r['pair_id']); count+=1
    add(240,'projection_repair',12,'240 projection repair: prioritize static y-cancellation and feasible large-gap x/diag placement','projection_matrix_broken_y_leakage','projection_repair')
    add(300,'common_phase_pull',12,'300 common-phase pull: preserve projection quality and tune selected-channel phase','common_phase_missed','common_phase_pull')
    write_csv(OUT,rows,FIELDS)
    lines=['# Stage11-2D H500 Final Gap Source Pair Selection','',f'source_pair_count = {len(rows)}','target_actual_bins = 240, 300','', '| target_bin | count | purpose |','|---:|---:|---|']
    for b in [240,300]: lines.append(f'| {b} | {sum(r["target_actual_bin_deg"]==str(b) for r in rows)} | {"projection repair" if b==240 else "common-phase pull"} |')
    SUMMARY.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'source_pair_count={len(rows)}'); print(f'bin_240_count={sum(r["target_actual_bin_deg"]=="240" for r in rows)}'); print(f'bin_300_count={sum(r["target_actual_bin_deg"]=="300" for r in rows)}')
if __name__=='__main__': main()
