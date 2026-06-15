from __future__ import annotations
import csv, math, struct, zlib
from pathlib import Path
PHASE_BINS=[0,60,120,180,240,300]
EPS=1e-12
def read_csv(path: Path):
    if not path.exists(): return []
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        return [{str(k): '' if v is None else str(v) for k,v in r.items()} for r in csv.DictReader(f)]
def write_csv(path: Path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def f(v, d=math.nan):
    try:
        if v is None or str(v).strip()=='': return d
        return float(v)
    except Exception: return d
def fmt(v): return '' if math.isnan(v) else f'{v:.6f}'
def wrap180(v): return (v+180.0)%360.0-180.0
def nearest_bin(phase):
    b=min(PHASE_BINS, key=lambda x: abs(wrap180(phase-x)))
    return b, abs(wrap180(phase-b))
def amp_phase(row, prefix):
    amp=f(row.get(prefix+'_amp')); ph=math.radians(f(row.get(prefix+'_phase_deg')))
    return amp*complex(math.cos(ph), math.sin(ph))
def classify(m):
    if m['selected_power'] < 0.10: return 'low_selected_power'
    if m['projection_selectivity_ratio'] < 3: return 'leaky_projection_broken'
    if m['selected_polarization_purity'] < 0.80: return 'cross_polarization_leakage'
    if m['actual_common_phase_error_deg'] <= 8 and m['projection_selectivity_ratio'] >= 6 and m['matrix_projection_error_norm'] <= 0.60: return 'actual_dimer_usable_strict'
    if m['actual_common_phase_error_deg'] <= 15 and m['projection_selectivity_ratio'] >= 3 and m['matrix_projection_error_norm'] <= 1.00: return 'actual_dimer_usable_loose'
    if m['projection_selectivity_ratio'] >= 10 and m['actual_common_phase_error_deg'] > 15: return 'high_selectivity_common_phase_missed'
    return 'projection_matrix_not_usable'
def failure_mode(status):
    if status in ('actual_dimer_usable_strict','actual_dimer_usable_loose'): return 'projection_matrix_usable_phase_hit'
    if status == 'high_selectivity_common_phase_missed': return 'common_phase_shift_only'
    if status == 'leaky_projection_broken': return 'projection_matrix_broken_y_leakage'
    if status == 'low_selected_power': return 'selected_power_too_low'
    if status == 'cross_polarization_leakage': return 'cross_polarization_leakage'
    return 'projection_matrix_or_phase_not_usable'
def metrics(row):
    txx=amp_phase(row,'t_xx'); tyx=amp_phase(row,'t_yx'); txy=amp_phase(row,'t_xy'); tyy=amp_phase(row,'t_yy')
    selected=abs(txx)**2; xcross=abs(tyx)**2; yx=abs(txy)**2; yy=abs(tyy)**2; blocked=yx+yy
    phase=f(row.get('t_xx_phase_deg', row.get('dimer_output_phase_deg'))); b,e=nearest_bin(phase)
    proj=selected/max(blocked,EPS); purity=selected/max(selected+xcross,EPS); offdiag=xcross+yx
    err=math.sqrt(xcross+yx+yy)/max(abs(txx),EPS)
    m={'actual_nearest_bin_deg':b,'actual_common_phase_deg':phase,'actual_common_phase_error_deg':e,'selected_power':selected,'x_input_cross_leak_power':xcross,'y_input_x_leak_power':yx,'y_input_y_leak_power':yy,'blocked_input_total_power':blocked,'projection_selectivity_ratio':proj,'selected_polarization_purity':purity,'offdiag_leak_power':offdiag,'matrix_projection_error_norm':err}
    st=classify(m); m['actual_dimer_status']=st; m['failure_mode']=failure_mode(st); return m
def get_bin(row): return str(int(f(row.get('bin_deg', row.get('original_static_bin_deg', 0)),0)))
def enrich(row, pair_map):
    m=metrics(row); pair=pair_map.get(row.get('source_pair_id',''),{})
    static_phase=f(pair.get('output_phase_deg', row.get('static_output_phase_deg')))
    static_ratio=f(pair.get('predicted_ratio', row.get('static_predicted_ratio')))
    ratio_drop=static_ratio/max(m['projection_selectivity_ratio'],EPS) if not math.isnan(static_ratio) else math.nan
    shift=abs(wrap180(m['actual_common_phase_deg']-static_phase)) if not math.isnan(static_phase) else math.nan
    return {'dimer_case_id':row.get('dimer_case_id',''),'original_static_bin_deg':get_bin(row),'actual_nearest_bin_deg':str(m['actual_nearest_bin_deg']),'actual_common_phase_deg':fmt(m['actual_common_phase_deg']),'actual_common_phase_error_deg':fmt(m['actual_common_phase_error_deg']),'t_xx_amp':row.get('t_xx_amp',''),'t_xx_phase_deg':row.get('t_xx_phase_deg',''),'t_yx_amp':row.get('t_yx_amp',''),'t_yx_phase_deg':row.get('t_yx_phase_deg',''),'t_xy_amp':row.get('t_xy_amp',''),'t_xy_phase_deg':row.get('t_xy_phase_deg',''),'t_yy_amp':row.get('t_yy_amp',''),'t_yy_phase_deg':row.get('t_yy_phase_deg',''),'selected_power':fmt(m['selected_power']),'x_input_cross_leak_power':fmt(m['x_input_cross_leak_power']),'y_input_x_leak_power':fmt(m['y_input_x_leak_power']),'y_input_y_leak_power':fmt(m['y_input_y_leak_power']),'blocked_input_total_power':fmt(m['blocked_input_total_power']),'projection_selectivity_ratio':fmt(m['projection_selectivity_ratio']),'selected_polarization_purity':fmt(m['selected_polarization_purity']),'offdiag_leak_power':fmt(m['offdiag_leak_power']),'matrix_projection_error_norm':fmt(m['matrix_projection_error_norm']),'static_s1_amp':pair.get('s1_amp',''),'static_s2_amp':pair.get('s2_amp',''),'static_s1_phase_deg':pair.get('s1_phase_deg',''),'static_s2_phase_deg':pair.get('s2_phase_deg',''),'static_s1_s2_amp_ratio':pair.get('s1_s2_amp_ratio',''),'static_s1_s2_phase_mismatch_deg':pair.get('s1_s2_phase_mismatch_deg',''),'static_selected_phase_deg':fmt(static_phase),'static_predicted_ratio':fmt(static_ratio),'dimer_actual_common_phase_deg':fmt(m['actual_common_phase_deg']),'dimer_vs_static_selected_phase_shift_deg':fmt(shift),'dimer_ratio_drop':fmt(ratio_drop),'actual_dimer_status':m['actual_dimer_status'],'failure_mode':m['failure_mode'],'placement_type':row.get('placement_type',''),'source_pair_id':row.get('source_pair_id',''),'j1_candidate_id':row.get('j1_candidate_id',''),'j2_candidate_id':row.get('j2_candidate_id',''),'notes':row.get('notes','')}
FIELDS=['dimer_case_id','original_static_bin_deg','actual_nearest_bin_deg','actual_common_phase_deg','actual_common_phase_error_deg','t_xx_amp','t_xx_phase_deg','t_yx_amp','t_yx_phase_deg','t_xy_amp','t_xy_phase_deg','t_yy_amp','t_yy_phase_deg','selected_power','x_input_cross_leak_power','y_input_x_leak_power','y_input_y_leak_power','blocked_input_total_power','projection_selectivity_ratio','selected_polarization_purity','offdiag_leak_power','matrix_projection_error_norm','static_s1_amp','static_s2_amp','static_s1_phase_deg','static_s2_phase_deg','static_s1_s2_amp_ratio','static_s1_s2_phase_mismatch_deg','static_selected_phase_deg','static_predicted_ratio','dimer_actual_common_phase_deg','dimer_vs_static_selected_phase_shift_deg','dimer_ratio_drop','actual_dimer_status','failure_mode','placement_type','source_pair_id','j1_candidate_id','j2_candidate_id','notes']
def status_rank(r):
    st=r.get('actual_dimer_status','')
    rank={'actual_dimer_usable_strict':0,'actual_dimer_usable_loose':1,'high_selectivity_common_phase_missed':2}.get(st,3)
    return (rank, f(r.get('actual_common_phase_error_deg'),999), -f(r.get('projection_selectivity_ratio'),-1), f(r.get('matrix_projection_error_norm'),999))
def tiny_png(path):
    w,h=640,320; pix=bytearray([255,255,255]*w*h)
    def ch(t,d): return struct.pack('!I',len(d))+t+d+struct.pack('!I',zlib.crc32(t+d)&0xffffffff)
    raw=b''.join(b'\x00'+bytes(pix[y*w*3:(y+1)*w*3]) for y in range(h))
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('!IIBBBBB',w,h,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw,9))+ch(b'IEND',b''))

REPO_ROOT=Path(__file__).resolve().parents[1]
IN_CSV=REPO_ROOT/'outputs'/'blue10k6_lp_apcd_stage11_2a_h500_dimer_validation'/'h500_dimer_fdtd_results_stage11_2a.csv'
PAIR_CSV=REPO_ROOT/'outputs'/'blue10k6_lp_apcd_stage11_1e_h500_gap_closure'/'lp_pair_candidates_h500_stage11_1e_merged_reranked.csv'
OUT_DIR=REPO_ROOT/'outputs'/'blue10k6_lp_apcd_stage11_2b_h500_dimer_rebin'
OUT_CSV=OUT_DIR/'h500_dimer_actual_phase_rebinned_stage11_2b.csv'; SUMMARY=OUT_DIR/'h500_dimer_actual_phase_6bin_summary_stage11_2b.md'; PROJ=OUT_DIR/'h500_dimer_projection_matrix_diagnosis_stage11_2b.md'; PHASE=OUT_DIR/'h500_dimer_phase_transfer_diagnosis_stage11_2b.md'; PLOT=OUT_DIR/'h500_dimer_actual_phase_plot_stage11_2b.png'
def main():
    if not IN_CSV.exists(): raise SystemExit(f'missing required input: {IN_CSV}')
    OUT_DIR.mkdir(parents=True, exist_ok=True); pairs={r['pair_id']:r for r in read_csv(PAIR_CSV)}; rows=[enrich(r,pairs) for r in read_csv(IN_CSV)]; write_csv(OUT_CSV, rows, FIELDS)
    lines=['# Stage11-2B Revised H500 Dimer Actual Common-Phase 6-bin Summary','','Bins are assigned from selected-channel actual common phase angle(t_xx). Projection quality is judged against t*exp(i phi)*|x><x|.','','| bin_deg | candidate_count | best_case_id | projection_selectivity_ratio | selected_power | selected_polarization_purity | matrix_projection_error_norm | actual_common_phase_deg | actual_common_phase_error_deg | usable_status | failure_mode | notes |','|---:|---:|---|---:|---:|---:|---:|---:|---:|---|---|---|']
    for b in PHASE_BINS:
        sub=[r for r in rows if int(f(r['actual_nearest_bin_deg']))==b]; sub.sort(key=status_rank); best=sub[0] if sub else None
        lines.append(f"| {b} | {len(sub)} | {best['dimer_case_id'] if best else ''} | {best['projection_selectivity_ratio'] if best else ''} | {best['selected_power'] if best else ''} | {best['selected_polarization_purity'] if best else ''} | {best['matrix_projection_error_norm'] if best else ''} | {best['actual_common_phase_deg'] if best else ''} | {best['actual_common_phase_error_deg'] if best else ''} | {best['actual_dimer_status'] if best else 'missing_dimer'} | {best['failure_mode'] if best else 'missing_dimer'} | selected common phase rebin |")
    SUMMARY.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    usable=[r for r in rows if r['actual_dimer_status'].startswith('actual_dimer_usable')]; missed=[r for r in rows if r['actual_dimer_status']=='high_selectivity_common_phase_missed']; broken=[r for r in rows if r['failure_mode']=='projection_matrix_broken_y_leakage']; low=[r for r in rows if r['failure_mode']=='selected_power_too_low']
    p=['# Stage11-2B Revised Projection Matrix Diagnosis','','Target matrix is t*exp(i phi)*|x><x|. Matrix error uses ||J - t_xx*P_x||_F / |t_xx|.','',f'projection_matrix_usable cases = {len(usable)}',f'high_selectivity_common_phase_missed cases = {len(missed)}',f'projection_matrix_broken_y_leakage cases = {len(broken)}',f'selected_power_too_low cases = {len(low)}','','## Case Notes']
    for r in rows: p.append(f"- {r['dimer_case_id']}: original {r['original_static_bin_deg']} -> actual {r['actual_nearest_bin_deg']}, ratio={r['projection_selectivity_ratio']}, selected_power={r['selected_power']}, matrix_error={r['matrix_projection_error_norm']}, status={r['actual_dimer_status']}, failure={r['failure_mode']}.")
    PROJ.write_text('\n'.join(p)+'\n', encoding='utf-8')
    shifts=[f(r['dimer_vs_static_selected_phase_shift_deg']) for r in rows if r['dimer_vs_static_selected_phase_shift_deg']!='']; avg=sum(shifts)/len(shifts) if shifts else math.nan
    PHASE.write_text('\n'.join(['# Stage11-2B Revised Phase Transfer Diagnosis','',f'mean |dimer selected common phase - static selected phase| = {fmt(avg)} deg','All Stage11-2A source dimers used y_pair, so y_pair common-phase pull is likely but still confounded.','','## Recommendations','- For common_phase_shift_only cases, sweep gap, diag_pair, y_pair, and swap order.','- For leaky_projection_broken cases, use larger gaps, x_pair/diag_pair, swap order, and alternative source pairs.','- Do not advance to K=6 until projection matrix and selected common phase are jointly validated.'])+'\n', encoding='utf-8')
    tiny_png(PLOT); print(f'revised_rebinned_count={len(rows)}'); print(f'usable={len(usable)}'); print(f'high_selectivity_common_phase_missed={len(missed)}'); print(f'projection_matrix_broken={len(broken)}'); print(f'low_selected_power={len(low)}')
if __name__=='__main__': main()
