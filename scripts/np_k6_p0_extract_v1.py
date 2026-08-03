import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
sys.path.insert(0, r'N:/Program Files/ANSYS Inc/v251/Lumerical/api/python')
import lumapi

ROOT = Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
STAGE = ROOT / 'outputs/np_k6_hf_p0_label_generator_recovery_v1'

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def flat(x): return np.asarray(x).reshape(-1)

def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        keys = list(rows[0].keys()) if rows else []
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)

def array_hash(x):
    return hashlib.sha256(np.ascontiguousarray(np.asarray(x)).tobytes()).hexdigest()

def safe_grating(fdtd, monitor, index):
    out = {}
    for key, fn in [('fraction', 'grating'), ('order', 'gratingn'), ('u_x', 'gratingu1')]:
        try:
            out[key] = flat(getattr(fdtd, fn)(monitor, index))
        except Exception as exc:
            out[key] = None; out[key + '_error'] = repr(exc)
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--case', required=True); args = ap.parse_args()
    case = args.case; cdir = STAGE / 'cases' / case; run_dir = STAGE / 'runtime_runs' / case / 'attempt_001'
    ledger = json.loads((run_dir / 'entered_ledger.json').read_text(encoding='utf-8-sig'))
    post = Path(ledger['post_fsp_path'])
    if not ledger.get('entered') or not ledger.get('engine_completed') or not ledger.get('post_saved') or not ledger.get('controller_returned'):
        raise RuntimeError('post-FSP lifecycle incomplete')
    fdtd = lumapi.FDTD(str(post), hide=True)
    try:
        tr = fdtd.getresult('transmission_monitor', 'T'); rr = fdtd.getresult('reflection_monitor', 'T')
        lam = flat(tr['lambda']) * 1e9; freq = flat(tr['f']); t = np.real(flat(tr['T'])); r_signed = np.real(flat(rr['T'])); r = np.abs(r_signed)
        if len(lam) != 11 or list(np.rint(lam).astype(int)) != list(range(445, 456)): raise RuntimeError(f'bad wavelength grid {lam}')
        metric_rows=[]; order_rows=[]; reflected_rows=[]; raw_rows=[]; sourcepower=[]
        for i, wavelength in enumerate(lam):
            g = safe_grating(fdtd, 'transmission_monitor', i+1)
            if g['fraction'] is None or g['order'] is None or g['u_x'] is None: raise RuntimeError('transmitted order API unavailable')
            fr = np.real(g['fraction']); orders = np.rint(np.real(g['order'])).astype(int); ux = np.real(g['u_x']);
            eta = {int(n): float(t[i] * fr[j]) for j,n in enumerate(orders)}
            plus = eta.get(1, float('nan')); zero = eta.get(0, float('nan')); minus = eta.get(-1, float('nan'))
            plus_idx = np.where(orders == 1)[0]; angle = float(np.degrees(np.arcsin(np.clip(ux[plus_idx[0]], -1, 1)))) if len(plus_idx) else float('nan')
            for j,n in enumerate(orders):
                order_rows.append({'case_id':case,'wavelength_nm':float(wavelength),'grating_order_n':int(n),'u_x':float(ux[j]),'angle_deg':float(np.degrees(np.arcsin(np.clip(ux[j],-1,1)))),'transmitted_fraction':float(fr[j]),'absolute_efficiency':float(t[i]*fr[j])})
            try:
                rg = safe_grating(fdtd, 'reflection_monitor', i+1)
                if rg['fraction'] is not None and rg['order'] is not None and rg['u_x'] is not None:
                    for j,n in enumerate(np.rint(np.real(rg['order'])).astype(int)):
                        reflected_rows.append({'case_id':case,'wavelength_nm':float(wavelength),'grating_order_n':int(n),'u_x':float(np.real(rg['u_x'][j])),'angle_deg':float(np.degrees(np.arcsin(np.clip(np.real(rg['u_x'][j]),-1,1)))),'reflected_fraction':float(np.real(rg['fraction'][j])),'absolute_efficiency':float(r[i]*np.real(rg['fraction'][j]))})
            except Exception:
                pass
            try: sp=float(fdtd.sourcepower(float(freq[i])))
            except Exception: sp=float('nan')
            sourcepower.append(sp)
            metric_rows.append({'case_id':case,'wavelength_nm':float(wavelength),'frequency_hz':float(freq[i]),'T_total':float(t[i]),'R_total':float(r[i]),'R_signed_monitor':float(r_signed[i]),'closure':float(t[i]+r[i]),'signed_closure_residual':float(1-t[i]-r[i]),'sourcepower_W':sp,'transmitted_order_sum':float(np.sum(t[i]*fr)),'transmitted_order_sum_mismatch':float(np.sum(t[i]*fr)-t[i]),'eta_plus1':plus,'eta_0':zero,'eta_minus1':minus,'non_target_efficiency':float(t[i]-plus) if np.isfinite(plus) else float('nan'),'directionality':float(plus/(plus+minus)) if np.isfinite(plus) and np.isfinite(minus) and plus+minus else float('nan'),'eta_plus1_over_minus1':float(plus/minus) if np.isfinite(plus) and np.isfinite(minus) and minus else float('nan'),'plus1_transmitted_fraction':float(plus/t[i]) if np.isfinite(plus) and t[i] else float('nan'),'plus1_air_side_angle_deg':angle,'transmitted_order_count':int(len(orders))})
        finite = np.isfinite(t).all() and np.isfinite(r).all() and all(np.isfinite(float(row['eta_plus1'])) for row in metric_rows)
        tr_sum_err = max(abs(row['transmitted_order_sum_mismatch']) for row in metric_rows)
        closure_max = max(abs(row['signed_closure_residual']) for row in metric_rows)
        write_csv(cdir/'hf_observations_long.csv', metric_rows)
        write_csv(cdir/'hf_transmitted_orders_long.csv', order_rows)
        if reflected_rows: write_csv(cdir/'hf_reflected_orders_long.csv', reflected_rows)
        else: (cdir/'hf_reflected_order_capability.json').write_text(json.dumps({'capability':False,'reason':'reflection grating API unavailable'},indent=2),encoding='utf-8')
        manifest={'case_id':case,'attempt_id':'attempt_001','post_fsp_path':str(post),'post_fsp_sha256':sha256(post),'readonly_reload':True,'run_called':False,'save_called':False,'wavelengths_nm':[float(x) for x in lam],'all_finite':bool(finite),'max_abs_closure_residual':float(closure_max),'transmitted_order_sum_mismatch_max':float(tr_sum_err),'reflection_order_capability':bool(reflected_rows),'gate_closure_pass':bool(closure_max<=0.02),'gate_transmitted_order_sum_pass':bool(tr_sum_err<=1e-8),'gate_bounds_pass':bool(np.all(t>=0)&np.all(t<=1.02)&np.all(r>=0)&np.all(r<=1.02)),'quality_gate_pass':bool(finite and closure_max<=0.02 and tr_sum_err<=1e-8 and np.all(t>=0) and np.all(r>=0))}
        (cdir/'extraction_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        (cdir/'post_fsp_checksum.json').write_text(json.dumps({'post_fsp_path':str(post),'sha256':sha256(post),'size_bytes':post.stat().st_size},indent=2),encoding='utf-8')
        ledger['extraction_completed']=True; ledger['extraction_manifest_path']=str(cdir/'extraction_manifest.json'); ledger['quality_gate_pass']=manifest['quality_gate_pass']; ledger['extraction_sha256']=sha256(cdir/'hf_observations_long.csv')
        (run_dir/'entered_ledger.json').write_text(json.dumps(ledger,indent=2),encoding='utf-8'); (cdir/'attempt_ledger.json').write_text(json.dumps(ledger,indent=2),encoding='utf-8')
        print(json.dumps(manifest,indent=2))
    finally: fdtd.close()

if __name__ == '__main__': main()
