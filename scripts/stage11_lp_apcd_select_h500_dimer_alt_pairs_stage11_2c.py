from __future__ import annotations
import csv, json, math
from pathlib import Path
REPO_ROOT=Path(__file__).resolve().parents[1]
PAIR_CSV=REPO_ROOT/'outputs'/'blue10k6_lp_apcd_stage11_1e_h500_gap_closure'/'lp_pair_candidates_h500_stage11_1e_merged_reranked.csv'
BEST_2B=REPO_ROOT/'outputs'/'blue10k6_lp_apcd_stage11_2b_h500_dimer_rebin'/'h500_dimer_best_actual_6bin_candidates_stage11_2b.csv'
GAP_2B=REPO_ROOT/'outputs'/'blue10k6_lp_apcd_stage11_2b_h500_dimer_rebin'/'h500_dimer_remaining_gap_diagnosis_stage11_2b.md'
PROJ_2B=REPO_ROOT/'outputs'/'blue10k6_lp_apcd_stage11_2b_h500_dimer_rebin'/'h500_dimer_projection_matrix_diagnosis_stage11_2b.md'
OUT_DIR=REPO_ROOT/'outputs'/'blue10k6_lp_apcd_stage11_2c_h500_dimer_alt_pairs'
OUT_CSV=OUT_DIR/'h500_dimer_alt_source_pairs_stage11_2c.csv'
SUMMARY=OUT_DIR/'h500_dimer_alt_pair_selection_summary_stage11_2c.md'
TARGET_BINS=[120,180,240,300]
FIELDS=['alt_pair_id','target_actual_bin_deg','source_pair_id','static_original_bin_deg','j1_candidate_id','j2_candidate_id','height_nm','j1_shape_family','j1_geometry_params','j2_length_nm','j2_width_nm','static_predicted_ratio','static_target_x_power','static_leak_y_power','static_output_phase_deg','static_phase_error_deg','static_s1_amp','static_s2_amp','static_s1_phase_deg','static_s2_phase_deg','static_s1_s2_amp_ratio','static_s1_s2_phase_mismatch_deg','selection_reason','expected_failure_mode_to_fix','priority','avoid_reason_if_any']
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
def load_lookup(paths, key='candidate_id'):
    out={}
    for p in paths:
        if p.exists():
            for r in read_csv(p):
                k=r.get(key,'')
                if k and k not in out: out[k]=r
    return out
def j1_geom(row):
    fam=row.get('shape_family','')
    if fam=='circle': return fam, json.dumps({'diameter_nm':f(row.get('diameter_nm'))})
    if fam=='square': return fam, json.dumps({'side_nm':f(row.get('side_nm'))})
    return fam, json.dumps({'length_nm':f(row.get('length_nm')),'width_nm':f(row.get('width_nm'))})
def dims_from(j1row, j2row):
    fam, geom = j1_geom(j1row)
    g = json.loads(geom)
    if fam == 'circle': j1x = j1y = f(g.get('diameter_nm'))
    elif fam == 'square': j1x = j1y = f(g.get('side_nm'))
    else: j1x, j1y = f(g.get('length_nm')), f(g.get('width_nm'))
    return fam, geom, j1x, j1y, f(j2row.get('length_nm')), f(j2row.get('width_nm'))
def feasible(j1row, j2row, mode):
    fam, geom, j1x, j1y, j2x, j2y = dims_from(j1row, j2row)
    limit_x = 431.907786 - 20
    limit_y = 432.0 - 20
    if math.isnan(j2x) or math.isnan(j2y): return False, 1e9
    # projection repair needs at least x_pair with gap 60; common pull accepts y_pair with gap 20.
    if mode == 'projection_repair':
        ok = (j1x + j2x + 60 <= limit_x) and (max(j1y, j2y) <= limit_y)
    else:
        ok = (max(j1x, j2x) <= limit_x) and (j1y + j2y + 20 <= limit_y)
    footprint = max(j1x, j2x) + max(j1y, j2y)
    return ok, footprint

def main():
    for p in [PAIR_CSV,BEST_2B,GAP_2B,PROJ_2B]:
        if not p.exists(): raise SystemExit(f'missing required input: {p}')
    j1=load_lookup([REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_1e_h500_gap_closure/h500_j1_gap_closure_plan_stage11_1e.csv',REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_1d_targeted_patch/j1_identity_patch_plan_stage11_1d.csv',REPO_ROOT/'outputs/blue10k6_lp_apcd_j1_identity_scan/j1_identity_plan.csv'])
    j2=load_lookup([REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_1e_h500_gap_closure/h500_j2_gap_closure_plan_stage11_1e.csv',REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_1d_targeted_patch/j2_hwp_patch_plan_stage11_1d.csv',REPO_ROOT/'outputs/blue10k6_lp_apcd_j2_hwp_scan/j2_hwp_plan.csv',REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_1e_h500_gap_closure/h500_j2_gap_closure_fdtd_results_stage11_1e.csv',REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_1d_targeted_patch/j2_hwp_patch_fdtd_results_stage11_1d.csv',REPO_ROOT/'outputs/blue10k6_lp_apcd_j2_hwp_scan/j2_hwp_fdtd_results_pilot.csv'])
    tested=set()
    for p in [REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_2a_h500_dimer_validation/h500_dimer_fdtd_results_stage11_2a.csv', REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_2b_h500_dimer_rebin/h500_dimer_placement_patch_fdtd_results_stage11_2b.csv']:
        if p.exists():
            for r in read_csv(p): tested.add(r.get('source_pair_id',''))
    pairs=[r for r in read_csv(PAIR_CSV) if f(r.get('j1_height_nm'))==500 and f(r.get('j2_height_nm'))==500 and r.get('same_height_pair')=='true' and f(r.get('predicted_ratio'))>=6 and f(r.get('target_x_power'))>=0.15]
    rows=[]; used=set()
    def score(r, target, mode):
        phase=abs(((f(r.get('output_phase_deg'))-target+180)%360)-180)
        amp=abs(1-f(r.get('s1_s2_amp_ratio'),0))
        mismatch=f(r.get('s1_s2_phase_mismatch_deg'),999)
        leak=f(r.get('leak_y_power'),999)
        ratio=f(r.get('predicted_ratio'),0)
        avoid=10 if r.get('pair_id') in tested else 0
        j1row=j1.get(r.get('j1_candidate_id','')); j2row=j2.get(r.get('j2_candidate_id',''))
        ok, footprint = feasible(j1row, j2row, mode) if j1row and j2row else (False, 1e9)
        bad=0 if ok else 100
        if mode=='projection_repair': return (bad, avoid, footprint, mismatch, amp, leak, phase, -ratio)
        return (bad, avoid, footprint, phase, mismatch, amp, leak, -ratio)
    for target in [120,180,240]:
        candidates=sorted(pairs, key=lambda r: score(r,target,'projection_repair'))
        count=0
        for r in candidates:
            if count>=5: break
            if r['pair_id'] in used: continue
            j1row=j1.get(r['j1_candidate_id']); j2row=j2.get(r['j2_candidate_id'])
            if not j1row or not j2row: continue
            fam,geom=j1_geom(j1row)
            ok,_foot=feasible(j1row,j2row,'projection_repair')
            if not ok: continue
            j2_len=fmt(f(j2row.get('length_nm'))); j2_wid=fmt(f(j2row.get('width_nm')))
            rows.append({'alt_pair_id':f'ALT2C_B{target}_{count+1:02d}','target_actual_bin_deg':str(target),'source_pair_id':r['pair_id'],'static_original_bin_deg':r.get('target_phase_bin_deg',''),'j1_candidate_id':r['j1_candidate_id'],'j2_candidate_id':r['j2_candidate_id'],'height_nm':'500.000000','j1_shape_family':fam,'j1_geometry_params':geom,'j2_length_nm':j2_len,'j2_width_nm':j2_wid,'static_predicted_ratio':r.get('predicted_ratio',''),'static_target_x_power':r.get('target_x_power',''),'static_leak_y_power':r.get('leak_y_power',''),'static_output_phase_deg':r.get('output_phase_deg',''),'static_phase_error_deg':r.get('phase_error_deg',''),'static_s1_amp':r.get('s1_amp',''),'static_s2_amp':r.get('s2_amp',''),'static_s1_phase_deg':r.get('s1_phase_deg',''),'static_s2_phase_deg':r.get('s2_phase_deg',''),'static_s1_s2_amp_ratio':r.get('s1_s2_amp_ratio',''),'static_s1_s2_phase_mismatch_deg':r.get('s1_s2_phase_mismatch_deg',''),'selection_reason':'projection repair: prioritize static cancellation and J1/J2 matching, not phase-only hit','expected_failure_mode_to_fix':'projection_matrix_broken_y_leakage','priority':'projection_repair','avoid_reason_if_any':'previously tested source pair' if r['pair_id'] in tested else ''})
            used.add(r['pair_id']); count+=1
    target=300
    candidates=sorted(pairs, key=lambda r: score(r,target,'common_phase_pull'))
    count=0
    for r in candidates:
        if count>=8 or len(rows)>=23: break
        if r['pair_id'] in used: continue
        j1row=j1.get(r['j1_candidate_id']); j2row=j2.get(r['j2_candidate_id'])
        if not j1row or not j2row: continue
        fam,geom=j1_geom(j1row)
        ok,_foot=feasible(j1row,j2row,'common_phase_pull')
        if not ok: continue
        j2_len=fmt(f(j2row.get('length_nm'))); j2_wid=fmt(f(j2row.get('width_nm')))
        rows.append({'alt_pair_id':f'ALT2C_B300_{count+1:02d}','target_actual_bin_deg':'300','source_pair_id':r['pair_id'],'static_original_bin_deg':r.get('target_phase_bin_deg',''),'j1_candidate_id':r['j1_candidate_id'],'j2_candidate_id':r['j2_candidate_id'],'height_nm':'500.000000','j1_shape_family':fam,'j1_geometry_params':geom,'j2_length_nm':j2_len,'j2_width_nm':j2_wid,'static_predicted_ratio':r.get('predicted_ratio',''),'static_target_x_power':r.get('target_x_power',''),'static_leak_y_power':r.get('leak_y_power',''),'static_output_phase_deg':r.get('output_phase_deg',''),'static_phase_error_deg':r.get('phase_error_deg',''),'static_s1_amp':r.get('s1_amp',''),'static_s2_amp':r.get('s2_amp',''),'static_s1_phase_deg':r.get('s1_phase_deg',''),'static_s2_phase_deg':r.get('s2_phase_deg',''),'static_s1_s2_amp_ratio':r.get('s1_s2_amp_ratio',''),'static_s1_s2_phase_mismatch_deg':r.get('s1_s2_phase_mismatch_deg',''),'selection_reason':'common-phase pull: keep projection quality while moving selected common phase toward 300 deg','expected_failure_mode_to_fix':'common_phase_missed','priority':'common_phase_pull','avoid_reason_if_any':'previously tested source pair' if r['pair_id'] in tested else ''})
        used.add(r['pair_id']); count+=1
    write_csv(OUT_CSV,rows,FIELDS)
    lines=['# Stage11-2C H500 Dimer Alternative Source Pair Selection','',f'alt_source_pair_count = {len(rows)}','target_actual_bins = 120, 180, 240, 300','', '| target_bin | count | purpose |','|---:|---:|---|']
    for b in TARGET_BINS:
        sub=[r for r in rows if r['target_actual_bin_deg']==str(b)]
        purpose='projection repair' if b!=300 else 'common-phase pull'
        lines.append(f'| {b} | {len(sub)} | {purpose} |')
    lines += ['', f'projection_repair_count = {sum(r["priority"]=="projection_repair" for r in rows)}', f'common_phase_pull_count = {sum(r["priority"]=="common_phase_pull" for r in rows)}']
    SUMMARY.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'alt_source_pair_count={len(rows)}')
    for b in TARGET_BINS: print(f'bin_{b}_count={sum(r["target_actual_bin_deg"]==str(b) for r in rows)}')
    print(f'projection_repair_count={sum(r["priority"]=="projection_repair" for r in rows)}')
    print(f'common_phase_pull_count={sum(r["priority"]=="common_phase_pull" for r in rows)}')
if __name__=='__main__': main()
