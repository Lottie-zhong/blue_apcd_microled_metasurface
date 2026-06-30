from __future__ import annotations
import csv, json, math, sys
from pathlib import Path

ROOT = Path(r'D:\project\worktrees\blue_apcd_rcled_mdc')
OUT = ROOT / 'outputs' / 'r2_1b_rcled_highres_tmm_shortlist_verify'
INDEX = ROOT / 'reports' / 'rcled_mdc_workspace_index.md'
sys.path.insert(0, str(ROOT / 'scripts'))
import stage_r2_1_rcled_stack_tmm_453_highq_screen as r21

SHORTLIST = [
    ('best_true_or_weak_two_mirror','R2_1_00227','R2A_Taguchi2026_scaled_control',6,6,290,'none'),
    ('best_all_dielectric_highR_mediumR','R2_1_04067','R2D_all_dielectric_highR_mediumR_scan',8,4,290,'none'),
    ('best_Taguchi_style','R2_1_00223','R2A_Taguchi2026_scaled_control',6,6,280,'none'),
    ('best_Khaidarov_style','R2_1_02264','R2B_Khaidarov_hybrid_scaled_control',12,4,290,'TiO2_50nm'),
    ('top_filter_control','R2_1_00359','R2A_Taguchi2026_scaled_control',8,0,320,'none'),
    ('C2_fallback_control','R2_1_02653','R2C_C2_medium_bottomR_upgrade',6,8,210,'TiO2_25nm'),
]
TERMS={'none':(0,'none'),'TiO2_50nm':(50,'TiO2'),'TiO2_25nm':(25,'TiO2'),'SiO2_25nm':(25,'SiO2')}
LAM=[round(448+0.05*i,2) for i in range(201)]
TH=[round(0+0.25*i,2) for i in range(141)]

def write_csv(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not fields: fields=list(rows[0])
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows([{k:r.get(k,'') for k in fields} for r in rows])

def interp_crossing(xs, ys, half, side):
    pairs=list(zip(xs,ys))
    if side=='left': pairs=pairs[:pairs.index(max(pairs,key=lambda p:p[1]))+1]
    else: pairs=pairs[pairs.index(max(pairs,key=lambda p:p[1])):]
    for (x1,y1),(x2,y2) in zip(pairs,pairs[1:]):
        if (y1-half)*(y2-half) <= 0 and y1 != y2:
            return x1 + (half-y1)*(x2-x1)/(y2-y1)
    return None

def fwhm(xs, ys):
    peak=max(ys); half=peak/2
    above=[x for x,y in zip(xs,ys) if y>=half]
    left=interp_crossing(xs,ys,half,'left')
    right=interp_crossing(xs,ys,half,'right')
    bounded=left is not None and right is not None
    if bounded: return right-left, bounded, left, right
    return (max(above)-min(above) if above else 999), False, left, right

def local_lobes(xs, ys):
    peaks=[]
    for i in range(1,len(ys)-1):
        if ys[i]>=ys[i-1] and ys[i]>=ys[i+1]: peaks.append((xs[i],ys[i]))
    peaks=sorted(peaks,key=lambda p:p[1],reverse=True)
    if len(peaks)>=2 and peaks[1][1] >= 0.75*peaks[0][1]: return 'multiple_comparable_lobes'
    return 'single_dominant_lobe_proxy'

def validity(bottom):
    if bottom==0: return 'top_filter_only'
    if bottom<=2: return 'weak_bottom_reflector'
    return 'true_two_mirror_cavity'

def risk(top):
    return 'high' if top>=10 else ('medium' if top>=8 else 'low')

def pass_level(m):
    valid=m['cavity_validity_class'] in {'true_two_mirror_cavity','weak_bottom_reflector'}
    if valid and m['spectral_FWHM_nm_at_theta0_interpolated']<=6 and m['angular_FWHM_deg_at_453_interpolated']<=10 and m['peak_abs_angle_deg_at_453']<=5 and m['normal_offaxis_ratio_at_453']>1.5:
        return 'Level A_highres'
    if valid and m['spectral_FWHM_nm_at_theta0_interpolated']<=8 and m['angular_FWHM_deg_at_453_interpolated']<=25 and m['peak_abs_angle_deg_at_453']<=10 and m['normal_offaxis_ratio_at_453']>1.0:
        return 'Level B_highres'
    return 'Control' if m['cavity_validity_class']=='top_filter_only' else 'Fail_highres'

def reason(m):
    if m['highres_pass_level'] in {'Level A_highres','Level B_highres'}: return 'passes highres proxy constraints'
    if m['highres_pass_level']=='Control': return 'top_filter_only control, not true RCLED cavity'
    out=[]
    if m['spectral_FWHM_nm_at_theta0_interpolated']>8: out.append('spectral too broad')
    if m['angular_FWHM_deg_at_453_interpolated']>25: out.append('angular too broad')
    if m['peak_abs_angle_deg_at_453']>10: out.append('peak too off-normal')
    if m['normal_offaxis_ratio_at_453']<=1.0: out.append('off-axis resonance too strong')
    if m['absolute_peak_proxy_at_453']<0.02: out.append('weak-output false positive risk')
    return '; '.join(out) if out else 'needs FDTD confirmation'

def candidate_row(role,cid,fam,top,bottom,cav,term):
    term_nm,term_mat=TERMS[term]
    row={'candidate_id':cid,'role':role,'family':fam,'center_wavelength_nm':453,'cavity_span_nm':cav,'top_pair_count':top,'bottom_pair_count':bottom,'bottom_reflectivity_proxy':r21.reflectivity(bottom),'termination':term,'spectral_peak_wavelength_nm_at_theta0':r21.center_lambda(cav,term_nm,term_mat,fam,top,bottom),'spectral_FWHM_nm_at_theta0':r21.fwhm_spectral(top,bottom,fam),'normal_gain':r21.FAMILIES[fam]['normal']*(1+0.04*top),'offaxis_gain':r21.FAMILIES[fam]['off']*(1+0.03*bottom),'angular_peak_angle_deg_at_453':r21.angular_center(top,bottom,cav,fam,term_mat),'angular_FWHM_deg_at_453':r21.angular_fwhm(top,bottom,fam)}
    return row

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    metrics=[]
    for spec in SHORTLIST:
        base=candidate_row(*spec)
        cid=base['candidate_id']
        spec_cut=[{'wavelength_nm':l,'I_proxy':r21.intensity(l,0,base)} for l in LAM]
        angle_cut=[{'theta_deg':t,'I_proxy':r21.intensity(453,t,base)} for t in TH]
        map_rows=[{'wavelength_nm':l,'theta_deg':t,'I_proxy':round(r21.intensity(l,t,base),10)} for l in LAM for t in TH]
        write_csv(OUT/f'highres_lambda_theta_map_{cid}.csv',map_rows)
        write_csv(OUT/f'spectral_cut_theta0_{cid}.csv',[{'wavelength_nm':r['wavelength_nm'],'I_proxy':round(r['I_proxy'],10)} for r in spec_cut])
        write_csv(OUT/f'angle_cut_453_{cid}.csv',[{'theta_deg':r['theta_deg'],'I_proxy':round(r['I_proxy'],10)} for r in angle_cut])
        sw=[r['wavelength_nm'] for r in spec_cut]; sy=[r['I_proxy'] for r in spec_cut]
        tw=[r['theta_deg'] for r in angle_cut]; ty=[r['I_proxy'] for r in angle_cut]
        peak_lam=sw[sy.index(max(sy))]; sf, sbound, sl, sr=fwhm(sw,sy)
        peak_th=tw[ty.index(max(ty))]; af, abound, al, ar=fwhm(tw,ty)
        total=sum(ty) or 1
        def avg(lo,hi):
            vals=[y for x,y in zip(tw,ty) if lo<=abs(x)<=hi]
            return sum(vals)/len(vals)
        def eta(limit): return sum(y for x,y in zip(tw,ty) if abs(x)<=limit)/total
        normal=avg(0,5); off=avg(20,30); peak=max(ty)
        m={'candidate_id':cid,'role':base['role'],'family':base['family'],'cavity_validity_class':validity(base['bottom_pair_count']),'top_pair_count':base['top_pair_count'],'bottom_pair_count':base['bottom_pair_count'],'cavity_span_nm':base['cavity_span_nm'],'termination':base['termination'],'spectral_peak_wavelength_nm_at_theta0':round(peak_lam,4),'spectral_FWHM_nm_at_theta0_interpolated':round(sf,4),'spectral_fwhm_bounded_in_window':sbound,'angular_peak_angle_deg_at_453':round(peak_th,4),'peak_abs_angle_deg_at_453':round(abs(peak_th),4),'angular_FWHM_deg_at_453_interpolated':round(af,4),'angular_fwhm_bounded_in_window':abound,'angular_lobe_pattern':local_lobes(tw,ty),'I_normal_0_5deg_at_453':round(normal,8),'I_offaxis_20_30deg_at_453':round(off,8),'normal_offaxis_ratio_at_453':round(normal/max(off,1e-12),6),'absolute_peak_proxy_at_453':round(peak,8),'absolute_normal_proxy_at_453':round(normal,8),'eta5':round(eta(5),6),'eta10':round(eta(10),6),'eta20':round(eta(20),6),'eta30':round(eta(30),6),'top_mirror_extraction_risk':risk(base['top_pair_count']),'spectral_window_warning':'' if sbound else 'spectral FWHM touches scan window','weak_output_warning':'weak-output false positive risk' if peak<0.02 else ''}
        m['highres_pass_level']=pass_level(m); m['failure_reason']=reason(m)
        metrics.append(m)
    fields=list(metrics[0])
    write_csv(OUT/'r2_1b_highres_metrics.csv',metrics,fields)
    rank=sorted(metrics,key=lambda m:({'Level A_highres':0,'Level B_highres':1,'Control':2,'Fail_highres':3}[m['highres_pass_level']], m['top_mirror_extraction_risk']=='high', -m['normal_offaxis_ratio_at_453']))
    write_csv(OUT/'r2_1b_candidate_rank.csv',rank,fields)
    rec=[m for m in rank if m['highres_pass_level'] in {'Level A_highres','Level B_highres'} and m['cavity_validity_class']!='top_filter_only'][:3]
    controls=[m for m in rank if m['cavity_validity_class']=='top_filter_only'][:1]+[m for m in rank if m['role']=='C2_fallback_control'][:1]
    fdtd=[]
    for m in rec+controls:
        x=dict(m); x['fdtd_role']='primary_validation' if m in rec else 'control'; fdtd.append(x)
    write_csv(OUT/'r2_1b_fdtd_recommendation.csv',fdtd,['fdtd_role']+fields)
    table='\n'.join(f"| {m['candidate_id']} | {m['role']} | {m['cavity_validity_class']} | {m['spectral_FWHM_nm_at_theta0_interpolated']} | {m['angular_FWHM_deg_at_453_interpolated']} | {m['peak_abs_angle_deg_at_453']} | {m['normal_offaxis_ratio_at_453']} | {m['top_mirror_extraction_risk']} | {m['highres_pass_level']} |" for m in metrics)
    (OUT/'r2_1b_summary.md').write_text(f'''# R2-1B High-Resolution TMM/STACK Shortlist Verification\n\nRCLED = Resonant-Cavity LED, 谐振腔发光二极管. DBR = Distributed Bragg Reflector, 分布式布拉格反射镜. TMM = Transfer Matrix Method, 传输矩阵法. STACK = multilayer stack optical solver, 多层膜堆光学求解器. FDTD = Finite-Difference Time-Domain, 时域有限差分法. FWHM = Full Width at Half Maximum, 半高全宽. Q = Quality factor, 品质因子. MQW = Multiple Quantum Wells, 多量子阱. APCD = Arbitrary Polarization Conversion Dichroism, 任意偏振转换二色性.\n\nNo FDTD was run. Spectral and angular FWHM values were recomputed from high-resolution proxy curves: wavelength 448-458 nm step 0.05 nm, theta 0-35 deg step 0.25 deg.\n\n| candidate | role | validity | spectral_FWHM | angular_FWHM | peak_abs | normal/offaxis | extraction_risk | pass |\n|---|---|---|---:|---:|---:|---:|---|---|\n{table}\n\nTop-filter-only candidates remain controls even when metrics look good. Top=12 candidates have high extraction risk until transmitted/upward output is checked by FDTD.\n''',encoding='utf-8')
    (OUT/'r2_1b_metric_warnings.md').write_text('''# R2-1B Metric Warnings\n\nHigh-resolution FWHM values are recomputed from proxy curves, but the curves still come from the lightweight STACK/TMM-style proxy rather than a full physical FDTD model.\n\nMulti-lobe detection is based on comparable local maxima in the proxy angular cut and should be confirmed by 2D FDTD.\n\nNormal/off-axis ratios use the same proxy intensity basis. Candidates with low absolute_peak_proxy_at_453 should be treated as weak-output false positives.\n\nTop=12 candidates are high extraction-risk because very high top reflectivity can increase Q while reducing useful upward extraction. Top=6/bottom=6 candidates are better balanced candidates for useful upward extraction in the current proxy.\n''',encoding='utf-8')
    lines='\n'.join(f"- {m['fdtd_role']}: {m['candidate_id']} ({m['role']}, {m['highres_pass_level']})" for m in fdtd)
    (OUT/'r2_1b_next_steps.md').write_text(f'''# R2-1B Next Steps\n\nRecommended maximum shortlist for 2D FDTD validation:\n\n{lines}\n\nRun only these before any broader sweep. Validate upward power, angular lobe shape, spectral response around 453 nm, and extraction loss for high-top-reflector candidates.\n''',encoding='utf-8')
    idx=INDEX.read_text(encoding='utf-8') if INDEX.exists() else '# RCLED/MDC Workspace Index\n'
    marker='## R2-1B High-Resolution Shortlist Verification'
    section=f'''{marker}\n\n- Output: outputs/r2_1b_rcled_highres_tmm_shortlist_verify\n- No FDTD run.\n- High-resolution proxy grid: wavelength 448-458 nm step 0.05 nm, theta 0-35 deg step 0.25 deg.\n- FDTD shortlist count: {len(fdtd)}.\n- Main recommendation: validate top balanced true-cavity candidates first, keep top-filter and C2 rows as controls.\n'''
    INDEX.write_text((idx.split(marker)[0].rstrip()+'\n\n'+section) if marker in idx else (idx.rstrip()+'\n\n'+section),encoding='utf-8')
    print(f'Wrote {OUT}')
if __name__=='__main__': main()
