from __future__ import annotations
import csv, json, math
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "stage10_cp_bw2_robust_narrowband_dimer_screen"
BASE_ID = "B4INT_J1J2_D194_T90_PSI97_H525"
BASE = dict(d=194.0, theta=90.0, psi=97.0, j1l=230.0, j1w=100.0, j2l=180.0, j2w=90.0)
WLS = [448.0, 450.0, 452.0, 453.0, 454.0]
LINS = ["x", "y"]
PX, PY, H, N = 431.907786, 432.0, 525.0, 2.6
HELPERS = [
    ROOT / "scripts/blue_stage10_cp_zprop_validation/stage10_cp_route_b4_integer_plane_wave_screen.py",
    ROOT / "scripts/blue_stage10_cp_zprop_validation/stage10_cp_bw1_spectral_tolerance.py",
    ROOT / "scripts/blue_stage10_cp_zprop_validation/stage10_cp_bw1r2_dense_448nm_notch_check.py",
]
BW1R2 = ROOT / "outputs/stage10_cp_bw1r2_dense_448nm_notch_check/stage10_cp_bw1r2_dense_merged_447_449nm.csv"

def tok(x): return str(int(round(x))) if abs(x-round(x)) < 1e-9 else str(x).replace('.', 'p')
def cid(p):
    s = ""
    if any(abs(p[k]-BASE[k]) > 1e-9 for k in ("j1l","j1w","j2l","j2w")):
        s = f"_J1{tok(p['j1l'])}x{tok(p['j1w'])}_J2{tok(p['j2l'])}x{tok(p['j2w'])}"
    return f"BW2_J1J2_D{tok(p['d'])}_T{tok(p['theta'])}_PSI{tok(p['psi'])}_H525{s}"
def geom(p):
    a = math.radians(p['theta']); x = 0.5*p['d']*math.cos(a); y = 0.5*p['d']*math.sin(a)
    clear = min(PX - max(p['j1l'], p['j2l']), PY - (p['d'] + 0.5*(p['j1w']+p['j2w'])))
    return dict(J1_x_nm=x,J1_y_nm=y,J2_x_nm=-x,J2_y_nm=-y,J1_rotation_deg=90-p['psi'],J2_rotation_deg=135-p['psi'],delta_x_nm=-2*x,delta_y_nm=-2*y,x_bias_abs_nm=abs(2*x),rough_min_clearance_nm=clear,geometry_valid=clear>=20,geometry_note="rough planning clearance only")
def add(rows,fam,note,**kw):
    p = dict(BASE); p.update(kw); r = dict(candidate_id=cid(p),perturbation_family=fam,d_nm=p['d'],theta_deg=p['theta'],psi_deg=p['psi'],H_nm=H,period_x_nm=PX,period_y_nm=PY,material_index=N,J1_L_nm=p['j1l'],J1_W_nm=p['j1w'],J2_L_nm=p['j2l'],J2_W_nm=p['j2w'],planning_note=note)
    r.update(geom(p))
    if r['candidate_id'] not in {x['candidate_id'] for x in rows}: rows.append(r)
def candidates():
    r=[]; add(r,'baseline','current frozen fabrication-aware CP candidate')
    for v in [-5,-2.5,2.5,5]: add(r,'BW2-A d micro-perturbation',f'd offset {v:+g} nm',d=BASE['d']+v)
    for v in [-2,-1,1,2]: add(r,'BW2-A theta micro-perturbation',f'theta offset {v:+g} deg',theta=BASE['theta']+v)
    for v in [-2,-1,1,2]: add(r,'BW2-A psi micro-perturbation',f'psi offset {v:+g} deg',psi=BASE['psi']+v)
    add(r,'BW2-B size micro-perturbation','J1 +1 nm',j1l=231,j1w=101); add(r,'BW2-B size micro-perturbation','J1 -1 nm',j1l=229,j1w=99)
    add(r,'BW2-B size micro-perturbation','J2 +1 nm',j2l=181,j2w=91); add(r,'BW2-B size micro-perturbation','J2 -1 nm',j2l=179,j2w=89)
    add(r,'BW2-B size micro-perturbation','both +1 nm',j1l=231,j1w=101,j2l=181,j2w=91); add(r,'BW2-B size micro-perturbation','both -1 nm',j1l=229,j1w=99,j2l=179,j2w=89)
    add(r,'BW2-C right-shifted local candidate','D195/PSI98 right-weight candidate',d=195,psi=98); add(r,'BW2-C right-shifted local candidate','D196/PSI98 right-weight candidate',d=196,psi=98)
    return r
def write_csv(path, rows):
    keys=[]
    for row in rows:
        for k in row:
            if k not in keys: keys.append(k)
    with path.open('w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=keys); w.writeheader(); w.writerows(rows)
def manifest(cs):
    rows=[]
    for c in cs:
        for wl in WLS:
            for lin in LINS:
                fsp = OUT / '_planned_fsp_not_run' / c['candidate_id'] / f"{c['candidate_id']}_{tok(wl)}NM_{lin.upper()}IN.fsp"
                rows.append(dict(candidate_id=c['candidate_id'],perturbation_family=c['perturbation_family'],d_nm=c['d_nm'],theta_deg=c['theta_deg'],psi_deg=c['psi_deg'],J1_L_nm=c['J1_L_nm'],J1_W_nm=c['J1_W_nm'],J2_L_nm=c['J2_L_nm'],J2_W_nm=c['J2_W_nm'],wavelength_nm=wl,input_linear_basis=lin,expected_output_fsp_path=str(fsp),extraction_output_path=str(OUT/'per_case_extract'/c['candidate_id']/f'{tok(wl)}nm_{lin}.json'),fresh_run='planned_true_not_run'))
    return rows
def runtime_s():
    p=ROOT/'outputs/stage10_cp_bw1r2_dense_448nm_notch_check/stage10_cp_bw1r2_fresh_run_table.csv'; vals=[]
    if p.exists():
        for row in csv.DictReader(p.open(newline='',encoding='utf-8')):
            for k in ('runtime_s','runtime_seconds'):
                try: vals.append(float(row.get(k,'')))
                except ValueError: pass
    return mean(vals) if vals else 45.0
def context():
    out={'source':str(BW1R2),'known_issue':'B4INT blue-side narrow notch from BW1R/BW1R2'}
    if BW1R2.exists():
        for row in csv.DictReader(BW1R2.open(newline='',encoding='utf-8')):
            wl=float(row['wavelength_nm'])
            if wl in {447.25,447.5,447.75,448.0,448.25,448.5,449.0}: out[f'ratio_{tok(wl)}nm']=row['conversion_to_leakage_ratio']; out[f'L_fraction_{tok(wl)}nm']=row['L_fraction_under_R_in']
    return out
def write_plan(cs,cases,sec):
    lines=['# Stage10-CP-BW2 robust narrow-band dimer screen plan\n\n','- Scope: CP-APCD metasurface-only periodic plane-wave planning/dry-run.\n','- No FDTD was run.\n','- No DBR/RCLED/MQW/dipole/finite-patch/+/-q/tolerance geometry/LP/Stage11/Stage12/Stage13 included.\n',f'- Baseline candidate: `{BASE_ID}`.\n','- Target: `R_in -> L_out`; leakage: `R_in -> R_out`. Negative DoCP_RminusL means desired L_out dominance.\n\n','## Existing helpers found\n\n']
    lines += [f'- `{p}`\n' for p in HELPERS if p.exists()]
    lines += ['\nB4INT local perturbation is supported at planning level by the existing B4 integer plane-wave geometry pattern. Execution should reuse the B4/BW1 model builder and run exact clearance audit before launch.\n\n','## Candidate list\n\n','| candidate_id | family | d | theta | psi | J1 | J2 | valid | note |\n','|---|---|---:|---:|---:|---|---|---|---|\n']
    for c in cs: lines.append(f"| {c['candidate_id']} | {c['perturbation_family']} | {c['d_nm']} | {c['theta_deg']} | {c['psi_deg']} | {c['J1_L_nm']}x{c['J1_W_nm']} | {c['J2_L_nm']}x{c['J2_W_nm']} | {c['geometry_valid']} | {c['planning_note']} |\n")
    hrs=len(cases)*sec/3600
    lines += ['\n## Case count and runtime\n\n',f'- Candidates: {len(cs)}\n- Sentinel wavelengths: {WLS}\n- Linear inputs: {LINS}\n',f'- Total planned case count = {len(cs)} x 5 x 2 = {len(cases)}\n',f'- Runtime estimate: {sec:.1f} s/case, total about {hrs:.2f} h.\n\n','## Planned scoring logic\n\n','- Prefer strong 453, 452, 450, 454 red-side safety, plus 448 guard.\n','- Reject or heavily penalize CP flip, L_fraction < 0.5, 448 ratio < 8, 452/453 worse than B4INT, fake high ratio from target-power collapse, or invalid geometry.\n','- strict_pass: all sentinel ratios >= 20, L_fraction >= 0.95, no CP flip, target power not below 60-70% of B4INT.\n','- useful_pass: 450-454 ratios >= 20, 448 ratio >= 10-15, L_fraction >= 0.90, no CP flip, no target-power collapse.\n']
    (OUT/'stage10_cp_bw2_robust_narrowband_dimer_screen_plan.md').write_text(''.join(lines),encoding='utf-8')
def main():
    OUT.mkdir(parents=True,exist_ok=True); cs=candidates(); cases=manifest(cs); sec=runtime_s()
    write_csv(OUT/'stage10_cp_bw2_candidate_geometry.csv',cs); write_csv(OUT/'stage10_cp_bw2_planned_fdtd_case_manifest.csv',cases)
    (OUT/'stage10_cp_bw2_planned_fdtd_case_manifest.json').write_text(json.dumps({'cases':cases},indent=2),encoding='utf-8')
    summary=dict(task='Stage10-CP-BW2 right-weighted narrow-band robust CP dimer screen planning/dry-run',no_fdtd_run=True,candidate_count=len(cs),sentinel_wavelengths_nm=WLS,linear_inputs=LINS,total_planned_case_count=len(cases),estimated_seconds_per_case=sec,estimated_total_hours=len(cases)*sec/3600,baseline_context=context(),scope_guard='metasurface-only periodic plane-wave planning only; no DBR/RCLED/MQW/dipole/finite-patch/+/-q/tolerance geometry/LP/Stage11/Stage12/Stage13')
    (OUT/'stage10_cp_bw2_case_count_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8'); write_csv(OUT/'stage10_cp_bw2_case_count_summary.csv',[{**summary,'baseline_context':json.dumps(summary['baseline_context'])}]); write_plan(cs,cases,sec)
    print('NO_FDTD_RUN=True'); print(f'CANDIDATES={len(cs)}'); print(f'TOTAL_CASES={len(cases)}'); print(f'EST_RUNTIME_HOURS={summary["estimated_total_hours"]:.2f}'); print(f'MANIFEST={OUT / "stage10_cp_bw2_planned_fdtd_case_manifest.csv"}')
    for c in cs: print(c['candidate_id'])
if __name__ == '__main__': main()
