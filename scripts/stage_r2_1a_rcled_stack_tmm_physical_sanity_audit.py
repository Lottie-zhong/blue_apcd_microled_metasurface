from __future__ import annotations
import csv, json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r'D:\project\worktrees\blue_apcd_rcled_mdc')
IN = ROOT / 'outputs' / 'r2_1_rcled_stack_tmm_453_highq_screen'
OUT = ROOT / 'outputs' / 'r2_1a_rcled_stack_tmm_physical_sanity_audit'
INDEX = ROOT / 'reports' / 'rcled_mdc_workspace_index.md'
SCRIPT = ROOT / 'scripts' / 'stage_r2_1a_rcled_stack_tmm_physical_sanity_audit.py'

def f(x, default=0.0):
    try: return float(x)
    except Exception: return default

def read_csv(path: Path) -> list[dict]:
    with path.open(newline='', encoding='utf-8') as fh:
        return list(csv.DictReader(fh))

def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not fields: fields = list(rows[0])
    with path.open('w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows([{k:r.get(k,'') for k in fields} for r in rows])

def validity(bottom: float) -> str:
    if bottom == 0: return 'top_filter_only'
    if bottom <= 2: return 'weak_bottom_reflector'
    return 'true_two_mirror_cavity'

def risk(top: float) -> str:
    if top >= 10: return 'high'
    if top >= 8: return 'medium'
    return 'low'

def angular_flag(r: dict) -> str:
    af=f(r.get('angular_FWHM_deg_at_453')); peak=f(r.get('peak_abs_angle_deg_at_453'))
    if peak <= 5 and af <= 15: return 'single_near_normal_lobe_proxy'
    if af > 25: return 'broad_or_pedestal_proxy'
    if peak > 10: return 'off_normal_or_split_lobe_proxy'
    return 'needs_FDTD_confirmation'

def conservative_score(r: dict) -> float:
    valid_bonus={'true_two_mirror_cavity':2.0,'weak_bottom_reflector':1.0,'top_filter_only':-1.0}[r['cavity_validity_class']]
    risk_pen={'low':0.0,'medium':0.4,'high':1.0}[r['top_mirror_extraction_risk']]
    return (valid_bonus + 0.6*f(r.get('normal_offaxis_ratio_at_453')) + 0.15*f(r.get('I_normal_0_5deg_at_453'))
            - 0.08*f(r.get('spectral_FWHM_nm_at_theta0')) - 0.06*f(r.get('angular_FWHM_deg_at_453'))
            - 0.08*f(r.get('peak_abs_angle_deg_at_453')) - risk_pen)

def audit_row(r: dict) -> dict:
    top=f(r.get('top_pair_count')); bottom=f(r.get('bottom_pair_count'))
    normal=f(r.get('I_normal_0_5deg_at_453')); off=f(r.get('I_offaxis_20_30deg_at_453'))
    a=dict(r)
    a['cavity_validity_class']=validity(bottom)
    a['effective_bottom_reflector']='none in proxy' if bottom==0 else ('weak DBR proxy' if bottom<=2 else 'DBR proxy')
    a['top_mirror_extraction_risk']=risk(top)
    a['angular_lobe_quality_flag']=angular_flag(r)
    a['normal_offaxis_same_basis']='yes_proxy_I_basis'
    a['I_proxy_normal_abs_at_453']=normal
    a['I_proxy_offaxis_abs_at_453']=off
    a['I_proxy_peak_estimate_at_453']=max(normal, off)
    a['ratio_artifact_warning']='possible_low_output_or_proxy_artifact' if max(normal,off) < 0.02 else ''
    a['fwhm_artifact_warning']='proxy_formula_repeated_value_not_true_interpolated_TMM_FWHM'
    a['physical_audit_warning']='top-filter control, not true RCLED cavity' if bottom==0 else 'needs FDTD confirmation'
    a['conservative_score']=round(conservative_score(a),6)
    return a

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows=[audit_row(r) for r in read_csv(IN/'r2_1_all_candidates.csv')]
    fields=list(rows[0])
    write_csv(OUT/'r2_1a_candidate_audit.csv', rows, fields)
    conservative=sorted(rows, key=lambda r: (r['cavity_validity_class']=='top_filter_only', -f(r['conservative_score'])))
    write_csv(OUT/'r2_1a_conservative_top_candidates.csv', conservative[:50], fields)
    by_family=defaultdict(list)
    for r in rows: by_family[r['family']].append(r)
    shortlist=[]
    def add_first(label, pred):
        for r in conservative:
            if pred(r) and r['candidate_id'] not in {x['candidate_id'] for x in shortlist}:
                rr=dict(r); rr['shortlist_role']=label; shortlist.append(rr); return
    add_first('best_true_or_weak_two_mirror', lambda r: r['cavity_validity_class'] in {'true_two_mirror_cavity','weak_bottom_reflector'})
    add_first('best_all_dielectric_highR_mediumR', lambda r: r['family']=='R2D_all_dielectric_highR_mediumR_scan' and r['cavity_validity_class']!='top_filter_only')
    add_first('best_Taguchi_style', lambda r: r['family']=='R2A_Taguchi2026_scaled_control' and r['cavity_validity_class']!='top_filter_only')
    add_first('best_Khaidarov_style', lambda r: r['family']=='R2B_Khaidarov_hybrid_scaled_control' and r['cavity_validity_class']!='top_filter_only')
    add_first('top_filter_control', lambda r: r['cavity_validity_class']=='top_filter_only')
    add_first('C2_fallback_control', lambda r: r['family']=='R2C_C2_medium_bottomR_upgrade')
    sfields=['shortlist_role']+fields
    write_csv(OUT/'r2_1a_fdtd_shortlist.csv', shortlist, sfields)
    counts=Counter(r['cavity_validity_class'] for r in rows)
    fam_lines=[]
    for fam, rs in by_family.items():
        levela=sum(r.get('pass_level')=='Level A' for r in rs); levelb=sum(r.get('pass_level')=='Level B' for r in rs)
        topfilter=sum(r['cavity_validity_class']=='top_filter_only' for r in rs)
        fam_lines.append(f'- {fam}: Level A={levela}, Level B={levelb}, top_filter_only={topfilter}.')
    best10='\n'.join(f"| {r['candidate_id']} | {r['family']} | {r['cavity_validity_class']} | {r['top_pair_count']} | {r['bottom_pair_count']} | {r['cavity_span_nm']} | {r['termination']} | {r['spectral_FWHM_nm_at_theta0']} | {r['angular_FWHM_deg_at_453']} | {r['normal_offaxis_ratio_at_453']} | {r['top_mirror_extraction_risk']} |" for r in conservative[:10])
    (OUT/'r2_1a_audit_summary.md').write_text(f'''# R2-1A Physical Sanity Audit\n\nRCLED = Resonant-Cavity LED, 谐振腔发光二极管. DBR = Distributed Bragg Reflector, 分布式布拉格反射镜. FDTD = Finite-Difference Time-Domain, 时域有限差分法. TMM = Transfer Matrix Method, 传输矩阵法. STACK = multilayer stack optical solver, 多层膜堆光学求解器. FWHM = Full Width at Half Maximum, 半高全宽. Q = Quality factor, 品质因子. MQW = Multiple Quantum Wells, 多量子阱. APCD = Arbitrary Polarization Conversion Dichroism, 任意偏振转换二色性. eta20/eta30 = ±20°/±30° cone collection efficiency, ±20°/±30°锥角收集效率.\n\nNo FDTD was run. This audit reclassifies R2-1 proxy candidates before any FDTD validation.\n\n## Cavity Validity Counts\n\n- true_two_mirror_cavity: {counts['true_two_mirror_cavity']}\n- weak_bottom_reflector: {counts['weak_bottom_reflector']}\n- top_filter_only: {counts['top_filter_only']}\n\nBottom_pair_count=0 candidates are not true high-Q RCLED cavity candidates in this proxy; they are top-filter controls because the effective bottom reflector is absent except for the weak background/proxy baseline.\n\n## Conservative Top 10\n\n| candidate | family | validity | top | bottom | cavity_nm | termination | spectral_FWHM | angular_FWHM | normal/offaxis | extraction_risk |\n|---|---|---|---:|---:|---:|---|---:|---:|---:|---|\n{best10}\n\n## Family Behavior\n\n{chr(10).join(fam_lines)}\n\nR2A produced many Level A candidates because its proxy parameters favor normal resonance and suppress off-axis strength. R2B produced fewer Level A candidates because the hybrid-style proxy is less aggressive. R2C produced no Level A/B because adding bottom reflectivity to the C2 fallback does not overcome broad/angular constraints in this proxy. R2D produced many top candidates because all-dielectric high top reflectivity plus controlled bottom reflectivity scores well in the proxy.\n''',encoding='utf-8')
    (OUT/'r2_1a_metric_warnings.md').write_text('''# R2-1A Metric Warnings\n\nRepeated spectral FWHM values such as 4.959948 nm and 4.360571 nm come from the lightweight proxy formula, not from a dense physical TMM interpolation. Treat them as screening labels, not measured FWHM.\n\nAngular FWHM is computed from the proxy angular curve. It can miss split lobes, broad pedestals, and finite-aperture effects. FDTD validation is required before claiming a true single near-normal lobe.\n\nNormal/off-axis ratio uses the same proxy intensity basis for I_normal_0_5deg_at_453 and I_offaxis_20_30deg_at_453. A high ratio can still be misleading if absolute output is weak.\n\nTop_pair_count >= 10 is marked high extraction risk unless transmitted output strength is independently validated.\n''',encoding='utf-8')
    roles='\n'.join(f"- {r['shortlist_role']}: {r['candidate_id']} ({r['family']}, bottom={r['bottom_pair_count']}, top={r['top_pair_count']})" for r in shortlist)
    (OUT/'r2_1a_next_steps.md').write_text(f'''# R2-1A Next Steps\n\nDo not run a broad FDTD sweep. Validate only the shortlist:\n\n{roles}\n\nFor R2-2, run 2D FDTD dipole validation and check transmitted/upward output, angular lobe shape, spectral response around 453 nm, and whether top_pair_count >= 10 causes extraction loss.\n''',encoding='utf-8')
    idx=INDEX.read_text(encoding='utf-8') if INDEX.exists() else '# RCLED/MDC Workspace Index\n'
    marker='## R2-1A Physical Sanity Audit'
    section=f'''{marker}\n\n- Output: outputs/r2_1a_rcled_stack_tmm_physical_sanity_audit\n- No FDTD run.\n- Cavity validity counts: true_two_mirror={counts['true_two_mirror_cavity']}, weak_bottom={counts['weak_bottom_reflector']}, top_filter_only={counts['top_filter_only']}.\n- Main warning: bottom_pair_count=0 rows are top-filter controls, not true high-Q RCLED cavities.\n- Next: R2-2 FDTD validation only for r2_1a_fdtd_shortlist.csv candidates.\n'''
    INDEX.write_text((idx.split(marker)[0].rstrip()+'\n\n'+section) if marker in idx else (idx.rstrip()+'\n\n'+section),encoding='utf-8')
    print(f'Wrote {OUT}')
if __name__=='__main__': main()
