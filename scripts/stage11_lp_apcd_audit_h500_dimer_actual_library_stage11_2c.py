from __future__ import annotations
import csv, math
from pathlib import Path
REPO_ROOT=Path(__file__).resolve().parents[1]
IN_FILES=[REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_2a_h500_dimer_validation/h500_dimer_fdtd_results_stage11_2a.csv', REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_2b_h500_dimer_rebin/h500_dimer_placement_patch_fdtd_results_stage11_2b.csv', REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_2c_h500_dimer_alt_pairs/h500_dimer_alt_patch_fdtd_results_stage11_2c.csv']
OUT_DIR=REPO_ROOT/'outputs'/'blue10k6_lp_apcd_stage11_2c_h500_dimer_alt_pairs'
SUMMARY=OUT_DIR/'h500_dimer_actual_6bin_summary_stage11_2c.md'; BEST=OUT_DIR/'h500_dimer_best_actual_6bin_library_stage11_2c.csv'; GAP=OUT_DIR/'h500_dimer_remaining_gap_diagnosis_stage11_2c.md'; PROJ=OUT_DIR/'h500_dimer_projection_matrix_diagnosis_stage11_2c.md'
PHASE_BINS=[0,60,120,180,240,300]; EPS=1e-12
BEST_FIELDS=['bin_deg','candidate_count','best_case_id','projection_selectivity_ratio','selected_power','blocked_input_total_power','selected_polarization_purity','matrix_projection_error_norm','actual_common_phase_deg','actual_common_phase_error_deg','usable_status','failure_mode','notes']
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
def wrap180(v): return (v+180)%360-180
def nearest(ph):
    b=min(PHASE_BINS,key=lambda x:abs(wrap180(ph-x))); return b,abs(wrap180(ph-b))
def metric(r):
    tx=f(r.get('t_xx_amp')); tyx=f(r.get('t_yx_amp')); txy=f(r.get('t_xy_amp')); tyy=f(r.get('t_yy_amp'))
    selected=tx*tx; blocked=txy*txy+tyy*tyy; purity=selected/max(selected+tyx*tyx,EPS); ratio=selected/max(blocked,EPS); err=math.sqrt(tyx*tyx+txy*txy+tyy*tyy)/max(tx,EPS)
    phase=f(r.get('t_xx_phase_deg',r.get('dimer_output_phase_deg'))); b,e=nearest(phase)
    if selected<0.10: status='selected_power_too_low'; fm='selected_power_too_low'
    elif purity<0.80: status='cross_polarization_leakage'; fm='cross_polarization_leakage'
    elif ratio<3 or blocked>selected/3: status='projection_matrix_broken_y_leakage'; fm='projection_matrix_broken_y_leakage'
    elif e<=8 and ratio>=6 and err<=0.60: status='actual_dimer_usable_strict'; fm='projection_matrix_usable_phase_hit'
    elif e<=15 and ratio>=3 and err<=1.00: status='actual_dimer_usable_loose'; fm='projection_matrix_usable_phase_hit'
    elif ratio>=6 and selected>=0.10 and purity>=0.80 and e>15: status='common_phase_missed'; fm='common_phase_missed'
    else: status='projection_matrix_or_phase_not_usable'; fm='projection_matrix_or_phase_not_usable'
    return {**r,'actual_nearest_bin_deg':str(b),'actual_common_phase_deg':fmt(phase),'actual_common_phase_error_deg':fmt(e),'selected_power':fmt(selected),'blocked_input_total_power':fmt(blocked),'projection_selectivity_ratio':fmt(ratio),'selected_polarization_purity':fmt(purity),'matrix_projection_error_norm':fmt(err),'usable_status':status,'failure_mode':fm}
def rank(r):
    sr={'actual_dimer_usable_strict':0,'actual_dimer_usable_loose':1,'common_phase_missed':2}.get(r['usable_status'],3)
    return (sr, f(r['actual_common_phase_error_deg'],999), -f(r['projection_selectivity_ratio'],0), f(r['matrix_projection_error_norm'],999))
def main():
    missing=[p for p in IN_FILES if not p.exists()]
    if missing: raise SystemExit('missing required input: '+', '.join(str(p) for p in missing))
    rows=[]
    for p in IN_FILES:
        src=p.name
        for r in read_csv(p): rows.append(metric({**r,'source_file':src}))
    best=[]; lines=['# Stage11-2C H500 Actual Dimer Projection-Phase 6-bin Summary','', 'Merged 2A + 2B + 2C real H500 dimer FDTD. Bins use selected-channel actual common phase angle(t_xx).','', '| bin_deg | candidate_count | best_case_id | projection_selectivity_ratio | selected_power | blocked_input_total_power | selected_polarization_purity | matrix_projection_error_norm | actual_common_phase_deg | actual_common_phase_error_deg | usable_status | failure_mode |','|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|---|']
    for b in PHASE_BINS:
        sub=[r for r in rows if int(f(r['actual_nearest_bin_deg']))==b]; sub.sort(key=rank); x=sub[0] if sub else None
        if x: best.append({'bin_deg':str(b),'candidate_count':str(len(sub)),'best_case_id':x['dimer_case_id'],'projection_selectivity_ratio':x['projection_selectivity_ratio'],'selected_power':x['selected_power'],'blocked_input_total_power':x['blocked_input_total_power'],'selected_polarization_purity':x['selected_polarization_purity'],'matrix_projection_error_norm':x['matrix_projection_error_norm'],'actual_common_phase_deg':x['actual_common_phase_deg'],'actual_common_phase_error_deg':x['actual_common_phase_error_deg'],'usable_status':x['usable_status'],'failure_mode':x['failure_mode'],'notes':'real H500 dimer projection-phase candidate'})
        lines.append(f"| {b} | {len(sub)} | {x['dimer_case_id'] if x else ''} | {x['projection_selectivity_ratio'] if x else ''} | {x['selected_power'] if x else ''} | {x['blocked_input_total_power'] if x else ''} | {x['selected_polarization_purity'] if x else ''} | {x['matrix_projection_error_norm'] if x else ''} | {x['actual_common_phase_deg'] if x else ''} | {x['actual_common_phase_error_deg'] if x else ''} | {x['usable_status'] if x else 'missing_dimer'} | {x['failure_mode'] if x else 'missing_dimer'} |")
    SUMMARY.write_text('\n'.join(lines)+'\n',encoding='utf-8'); write_csv(BEST,best,BEST_FIELDS)
    counts={}
    for r in rows: counts[r['failure_mode']]=counts.get(r['failure_mode'],0)+1
    PROJ.write_text('\n'.join(['# Stage11-2C Projection Matrix Diagnosis','',f'total_real_dimer_cases = {len(rows)}',f'actual_dimer_usable_loose_or_strict = {sum(r["usable_status"] in {"actual_dimer_usable_loose","actual_dimer_usable_strict"} for r in rows)}',f'actual_dimer_usable_strict = {sum(r["usable_status"]=="actual_dimer_usable_strict" for r in rows)}','']+[f'- {k}: {v}' for k,v in sorted(counts.items())])+'\n',encoding='utf-8')
    gap=['# Stage11-2C Remaining Gap Diagnosis','']
    for r in best:
        if r['usable_status'].startswith('actual_dimer_usable'): gap.append(f"- {r['bin_deg']} deg: usable via {r['best_case_id']}, ratio={r['projection_selectivity_ratio']}, selected_power={r['selected_power']}, matrix_error={r['matrix_projection_error_norm']}.")
        else: gap.append(f"- {r['bin_deg']} deg: gap remains; failure={r['failure_mode']}, best={r['best_case_id']}.")
    GAP.write_text('\n'.join(gap)+'\n',encoding='utf-8')
    print(f'total_cases={len(rows)}'); print(f"actual_dimer_usable_loose={sum(r['usable_status'] in {'actual_dimer_usable_loose','actual_dimer_usable_strict'} for r in rows)}"); print(f"actual_dimer_usable_strict={sum(r['usable_status']=='actual_dimer_usable_strict' for r in rows)}")
if __name__=='__main__': main()
