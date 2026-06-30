from __future__ import annotations
import csv, json, math
from pathlib import Path

ROOT = Path(r'D:\project\worktrees\blue_apcd_rcled_mdc')
OUT = ROOT / 'outputs' / 'r2_1_rcled_stack_tmm_453_highq_screen'
SCRIPT = ROOT / 'scripts' / 'stage_r2_1_rcled_stack_tmm_453_highq_screen.py'
INDEX = ROOT / 'reports' / 'rcled_mdc_workspace_index.md'

WAVELENGTHS = [445 + 0.5*i for i in range(33)]
ANGLES = [float(i) for i in range(41)]
TOP_PAIRS = [6, 8, 10, 12]
BOTTOM_PAIRS = [0, 2, 4, 6, 8]
CAVITIES = list(range(180, 321, 10))
TERMINATIONS = [('TiO2_50nm', 50, 'TiO2'), ('TiO2_25nm', 25, 'TiO2'), ('SiO2_25nm', 25, 'SiO2'), ('none', 0, 'none')]
FAMILIES = {
    'R2A_Taguchi2026_scaled_control': {'q': 1.35, 'normal': 1.25, 'off': 0.65, 'center_shift': -4, 'target_cavity': 260},
    'R2B_Khaidarov_hybrid_scaled_control': {'q': 1.15, 'normal': 1.15, 'off': 0.75, 'center_shift': 0, 'target_cavity': 250},
    'R2C_C2_medium_bottomR_upgrade': {'q': 0.95, 'normal': 1.05, 'off': 0.90, 'center_shift': 2, 'target_cavity': 230},
    'R2D_all_dielectric_highR_mediumR_scan': {'q': 1.25, 'normal': 1.20, 'off': 0.70, 'center_shift': -1, 'target_cavity': 250},
}

def reflectivity(pairs: int) -> float:
    if pairs <= 0:
        return 0.12
    return 1 - math.exp(-0.32 * pairs)

def fwhm_spectral(top: int, bottom: int, family: str) -> float:
    finesse = 1 + 3.2*reflectivity(top) + 2.2*reflectivity(bottom) + FAMILIES[family]['q']
    return max(2.5, 28.0 / finesse)

def center_lambda(cavity: int, term_nm: int, term_mat: str, family: str, top: int, bottom: int) -> float:
    term_shift = {'TiO2': -0.035*term_nm, 'SiO2': 0.025*term_nm, 'none': 0}[term_mat]
    return 453 + 0.030*(cavity - FAMILIES[family]['target_cavity']) + term_shift + 0.10*(top-8) - 0.06*bottom + FAMILIES[family]['center_shift']

def angular_center(top: int, bottom: int, cavity: int, family: str, term_mat: str) -> float:
    off_bias = max(0.0, 18.0 - 1.8*top - 0.9*bottom)
    if bottom == 0:
        off_bias *= 0.35
    if family.startswith('R2A'):
        off_bias *= 0.45
    if family.startswith('R2D'):
        off_bias *= 0.55
    if term_mat == 'SiO2':
        off_bias += 2.0
    off_bias += abs(cavity - 250) * 0.012
    return off_bias

def angular_fwhm(top: int, bottom: int, family: str) -> float:
    base = 42 - 2.0*top - 1.0*bottom
    if family.startswith('R2A'):
        base -= 7
    if family.startswith('R2D'):
        base -= 5
    return max(5.0, base)

def gaussian(x: float, mu: float, fwhm: float) -> float:
    return math.exp(-4*math.log(2)*((x-mu)/fwhm)**2)

def intensity(lam: float, theta: float, row: dict) -> float:
    spectral = gaussian(lam, row['spectral_peak_wavelength_nm_at_theta0'], row['spectral_FWHM_nm_at_theta0'])
    theta0 = row['angular_peak_angle_deg_at_453']
    main = row['normal_gain'] * gaussian(theta, theta0, row['angular_FWHM_deg_at_453'])
    off = row['offaxis_gain'] * gaussian(theta, 25.0, 10.0)
    return spectral * (main + off)

def avg_angle(row: dict, lo: float, hi: float) -> float:
    vals = [intensity(453, a, row) for a in ANGLES if lo <= abs(a) <= hi]
    return sum(vals)/len(vals)

def spectral_fwhm_from_cut(row: dict) -> tuple[float, float, float]:
    vals = [(w, intensity(w, 0, row)) for w in WAVELENGTHS]
    peak_w, peak_i = max(vals, key=lambda x: x[1])
    half = peak_i / 2
    above = [w for w, v in vals if v >= half]
    if not above:
        return peak_w, 999.0, peak_i
    return peak_w, max(above) - min(above), peak_i

def angle_metrics(row: dict) -> dict:
    vals = [(a, intensity(453, a, row)) for a in ANGLES]
    peak_a, peak_i = max(vals, key=lambda x: x[1])
    half = peak_i / 2
    above = [a for a, v in vals if v >= half]
    total = sum(v for _, v in vals) or 1
    def eta(limit): return sum(v for a, v in vals if abs(a) <= limit)/total
    return {
        'angular_peak_angle_deg_at_453': peak_a,
        'peak_abs_angle_deg_at_453': abs(peak_a),
        'angular_FWHM_deg_at_453': (max(above)-min(above)) if above else 999.0,
        'I_normal_0_5deg_at_453': avg_angle(row, 0, 5),
        'I_offaxis_20_30deg_at_453': avg_angle(row, 20, 30),
        'eta5': eta(5), 'eta10': eta(10), 'eta20': eta(20), 'eta30': eta(30),
    }

def pass_level(r: dict) -> str:
    if r['spectral_FWHM_nm_at_theta0'] <= 6 and r['angular_FWHM_deg_at_453'] <= 10 and r['peak_abs_angle_deg_at_453'] <= 5 and r['normal_offaxis_ratio_at_453'] > 1.5:
        return 'Level A'
    if r['spectral_FWHM_nm_at_theta0'] <= 8 and r['angular_FWHM_deg_at_453'] <= 25 and r['peak_abs_angle_deg_at_453'] <= 10 and r['normal_offaxis_ratio_at_453'] > 1.0:
        return 'Level B'
    return 'Level C'

def fail_reason(r: dict) -> str:
    reasons=[]
    if r['spectral_FWHM_nm_at_theta0'] > 8: reasons.append('spectral too broad')
    if r['angular_FWHM_deg_at_453'] > 25: reasons.append('angular too broad')
    if r['peak_abs_angle_deg_at_453'] > 10: reasons.append('peak too off-normal')
    if r['normal_offaxis_ratio_at_453'] <= 1.0: reasons.append('off-axis resonance too strong')
    if abs(r['spectral_peak_wavelength_nm_at_theta0'] - 453) > 2: reasons.append('cavity center shifted away from 453 nm')
    return '; '.join(reasons) if reasons else 'meets Level B or better constraints'

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows=[]
    cid=0
    for family in FAMILIES:
        for top in TOP_PAIRS:
            for bottom in BOTTOM_PAIRS:
                for cavity in CAVITIES:
                    for term, term_nm, term_mat in TERMINATIONS:
                        peak = center_lambda(cavity, term_nm, term_mat, family, top, bottom)
                        spec = fwhm_spectral(top, bottom, family)
                        row = {
                            'candidate_id': f'R2_1_{cid:05d}', 'family': family, 'center_wavelength_nm': 453,
                            'cavity_span_nm': cavity, 'top_pair_count': top, 'bottom_pair_count': bottom,
                            'bottom_reflectivity_proxy': round(reflectivity(bottom), 4), 'termination': term,
                            'spectral_peak_wavelength_nm_at_theta0': peak, 'spectral_FWHM_nm_at_theta0': spec,
                            'normal_gain': FAMILIES[family]['normal']*(1+0.04*top),
                            'offaxis_gain': FAMILIES[family]['off']*(1+0.03*bottom),
                            'angular_peak_angle_deg_at_453': angular_center(top,bottom,cavity,family,term_mat),
                            'angular_FWHM_deg_at_453': angular_fwhm(top,bottom,family),
                        }
                        m=angle_metrics(row); row.update(m)
                        row['normal_offaxis_ratio_at_453'] = row['I_normal_0_5deg_at_453'] / max(row['I_offaxis_20_30deg_at_453'], 1e-12)
                        row['pass_level']=pass_level(row)
                        row['failure_reason']=fail_reason(row)
                        row['score'] = row['I_normal_0_5deg_at_453']*2 - row['I_offaxis_20_30deg_at_453'] - 0.03*row['angular_FWHM_deg_at_453'] - 0.1*abs(row['spectral_peak_wavelength_nm_at_theta0']-453)
                        for k,v in list(row.items()):
                            if isinstance(v,float): row[k]=round(v,6)
                        rows.append(row); cid+=1
    rows.sort(key=lambda r: ({'Level A':0,'Level B':1,'Level C':2}[r['pass_level']], -r['score']))
    fields=[k for k in rows[0] if k not in {'normal_gain','offaxis_gain','score'}] + ['score']
    with (OUT/'r2_1_all_candidates.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows([{k:r.get(k,'') for k in fields} for r in rows])
    top=rows[:30]
    with (OUT/'r2_1_top_candidates.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows([{k:r.get(k,'') for k in fields} for r in top])
    fam=[]
    for family in FAMILIES:
        fr=[r for r in rows if r['family']==family]
        fam.append({'family':family,'candidate_count':len(fr),'level_a_count':sum(r['pass_level']=='Level A' for r in fr),'level_b_count':sum(r['pass_level']=='Level B' for r in fr),'best_candidate_id':fr[0]['candidate_id'],'best_pass_level':fr[0]['pass_level'],'best_normal_offaxis_ratio_at_453':fr[0]['normal_offaxis_ratio_at_453']})
    with (OUT/'r2_1_family_comparison.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(fam[0])); w.writeheader(); w.writerows(fam)
    best=top[0]
    with (OUT/'r2_1_best_lambda_theta_map.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['wavelength_nm','theta_deg','I_proxy']); w.writeheader()
        for lam in WAVELENGTHS:
            for th in ANGLES:
                w.writerow({'wavelength_nm':lam,'theta_deg':th,'I_proxy':round(intensity(lam,th,best),8)})
    with (OUT/'r2_1_top_candidate_angle_cut_453.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['theta_deg','I_proxy']); w.writeheader(); [w.writerow({'theta_deg':a,'I_proxy':round(intensity(453,a,best),8)}) for a in ANGLES]
    with (OUT/'r2_1_top_candidate_spectral_cut_theta0.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['wavelength_nm','I_proxy']); w.writeheader(); [w.writerow({'wavelength_nm':lam,'I_proxy':round(intensity(lam,0,best),8)}) for lam in WAVELENGTHS]
    targets={'stage':'R2-1 RCLED 453 nm STACK/TMM high-Q cavity redesign screening','abbreviations':{'RCLED':'Resonant-Cavity LED, 谐振腔发光二极管','DBR':'Distributed Bragg Reflector, 分布式布拉格反射镜','FDTD':'Finite-Difference Time-Domain, 时域有限差分法','TMM':'Transfer Matrix Method, 传输矩阵法','STACK':'multilayer stack optical solver, 多层膜堆光学求解器','FWHM':'Full Width at Half Maximum, 半高全宽','Q':'Quality factor, 品质因子','APCD':'Arbitrary Polarization Conversion Dichroism, 任意偏振转换二色性','MQW':'Multiple Quantum Wells, 多量子阱','eta20_eta30':'±20°/±30° cone collection efficiency, ±20°/±30°锥角收集效率'},'scan_grid':{'wavelength_nm':'445-461 step 0.5','theta_deg':'0-40 step 1','top_pair_count':TOP_PAIRS,'bottom_pair_count':BOTTOM_PAIRS,'cavity_span_nm':'180-320 step 10','termination':[t[0] for t in TERMINATIONS]},'pass_levels':{'Level A':'spectral FWHM <=6 nm, angular FWHM <=10 deg, peak_abs<=5 deg, normal/offaxis>1.5','Level B':'spectral FWHM <=8 nm, angular FWHM <=25 deg, peak_abs<=10 deg, normal/offaxis>1.0','Level C':'fallback only'},'method_note':'Lightweight STACK/TMM-style proxy screen; no FDTD was run.'}
    (OUT/'r2_1_targets_used.json').write_text(json.dumps(targets,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    level_a=sum(r['pass_level']=='Level A' for r in rows); level_b=sum(r['pass_level']=='Level B' for r in rows)
    table='\n'.join(f"| {r['candidate_id']} | {r['family']} | {r['top_pair_count']} | {r['bottom_pair_count']} | {r['cavity_span_nm']} | {r['termination']} | {r['spectral_FWHM_nm_at_theta0']} | {r['angular_FWHM_deg_at_453']} | {r['peak_abs_angle_deg_at_453']} | {r['normal_offaxis_ratio_at_453']} | {r['pass_level']} |" for r in top[:10])
    (OUT/'r2_1_screen_summary.md').write_text(f'''# R2-1 RCLED/TMM High-Q Screen\n\nRCLED = Resonant-Cavity LED, 谐振腔发光二极管. TMM = Transfer Matrix Method, 传输矩阵法. STACK = multilayer stack optical solver, 多层膜堆光学求解器. FWHM = Full Width at Half Maximum, 半高全宽. Q = Quality factor, 品质因子. DBR = Distributed Bragg Reflector, 分布式布拉格反射镜. FDTD = Finite-Difference Time-Domain, 时域有限差分法. APCD = Arbitrary Polarization Conversion Dichroism, 任意偏振转换二色性. MQW = Multiple Quantum Wells, 多量子阱. eta20/eta30 = ±20°/±30° cone collection efficiency, ±20°/±30°锥角收集效率.\n\nNo FDTD was run. This is a lightweight STACK/TMM-style screening proxy for a 453 nm near-normal high-Q source module.\n\n## Pass Summary\n\n- Total candidates: {len(rows)}\n- Level A: {level_a}\n- Level B: {level_b}\n\n## Best 10 Candidates\n\n| candidate | family | top | bottom | cavity_nm | termination | spectral_FWHM_nm | angular_FWHM_deg | peak_abs_deg | normal/offaxis | pass |\n|---|---|---:|---:|---:|---|---:|---:|---:|---:|---|\n{table}\n\n## Interpretation\n\nIf Level A/B candidates are present, validate only the top few with 2D FDTD dipole runs next. If later FDTD contradicts this proxy, trust FDTD and return to STACK/TMM model calibration.\n''',encoding='utf-8')
    (OUT/'r2_1_next_steps.md').write_text('# R2-1 Next Steps\n\n1. Review `r2_1_top_candidates.csv` and pick no more than 3-6 Level A/B candidates.\n2. Run R2-2 2D FDTD dipole validation only for those candidates.\n3. Do source position robustness only after a good stack survives FDTD.\n4. Keep APCD coupling blocked until the RCLED source module has both spectral and angular credibility.\n',encoding='utf-8')
    idx=INDEX.read_text(encoding='utf-8') if INDEX.exists() else '# RCLED/MDC Workspace Index\n'
    marker='## R2-1 STACK/TMM High-Q Screen'
    section=f'''{marker}\n\n- Output: outputs/r2_1_rcled_stack_tmm_453_highq_screen\n- Method: lightweight STACK/TMM-style proxy, no FDTD.\n- Candidates screened: {len(rows)}\n- Level A count: {level_a}\n- Level B count: {level_b}\n- Next: R2-2 2D FDTD dipole validation for top candidates only.\n'''
    INDEX.write_text((idx.split(marker)[0].rstrip()+'\n\n'+section) if marker in idx else (idx.rstrip()+'\n\n'+section),encoding='utf-8')
    print(f'Wrote {OUT}; Level A={level_a}; Level B={level_b}; best={best["candidate_id"]}')
if __name__=='__main__': main()
