import csv, json, math, sys, hashlib, traceback
from pathlib import Path
import numpy as np

R = Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1')
E = R / 'outputs/np_k6_hf_pilot_gate0_n2_production_mesh_v1_corrected_monitor_contract_v1'
case = 'RUN3C_N2_NATIVE_M1_X_PRODUCTION_GATE'
run_dir = E / 'runtime_runs' / case / 'attempt_001'
case_dir = E / 'cases' / case
post = run_dir / (case + '_attempt_001_post.fsp')
boundary_names = [
    'N1_DIAG_PML_LOWER', 'N1_DIAG_LOWER_OUTSIDE', 'N1_DIAG_LOWER_INSIDE',
    'N1_DIAG_UPPER_INSIDE', 'N1_DIAG_UPPER_OUTSIDE', 'N1_DIAG_PML_UPPER'
]

def sha256(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def arr(x):
    return np.asarray(x).reshape(-1)

def trapz2(a, x, y):
    a = np.asarray(a)
    try:
        return np.trapezoid(np.trapezoid(a, x=x, axis=0), x=y, axis=0)
    except AttributeError:
        return np.trapz(np.trapz(a, x=x, axis=0), x=y, axis=0)

def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)

def main():
    import lumapi
    fdtd = lumapi.FDTD(str(post), hide=True)
    try:
        tr = fdtd.getresult('transmission_monitor', 'T')
        rr = fdtd.getresult('reflection_monitor', 'T')
        lam = arr(tr['lambda']) * 1e9
        freq = arr(tr['f'])
        T = np.real(arr(tr['T']))
        R_signed = np.real(arr(rr['T']))
        R = np.abs(R_signed)
        n = min(len(lam), len(T), len(R))
        lam, freq, T, R, R_signed = lam[:n], freq[:n], T[:n], R[:n], R_signed[:n]
        order_rows = []
        metric_rows = []
        for i in range(n):
            gp = arr(fdtd.grating('transmission_monitor', i + 1))
            gn = arr(fdtd.gratingn('transmission_monitor', i + 1))
            gu = arr(fdtd.gratingu1('transmission_monitor', i + 1))
            m = min(len(gp), len(gn), len(gu))
            gp, gn, gu = np.real(gp[:m]), np.real(gn[:m]), np.real(gu[:m])
            frac_sum = float(np.sum(gp))
            abs_sum = float(T[i] * frac_sum)
            eta = {int(round(gn[j])): float(T[i] * gp[j]) for j in range(m)}
            eta_p = eta.get(1, float('nan')); eta_0 = eta.get(0, float('nan')); eta_m = eta.get(-1, float('nan'))
            angle_p = float(np.degrees(np.arcsin(np.clip(gu[np.where(np.rint(gn).astype(int) == 1)[0][0]], -1, 1)))) if np.any(np.rint(gn).astype(int) == 1) else float('nan')
            for j in range(m):
                order_rows.append({'wavelength_nm': float(lam[i]), 'grating_order_n': int(round(gn[j])), 'u_x': float(gu[j]), 'angle_deg': float(np.degrees(np.arcsin(np.clip(gu[j], -1, 1)))), 'fraction': float(gp[j]), 'absolute_efficiency': float(T[i] * gp[j])})
            metric_rows.append({
                'wavelength_nm': float(lam[i]), 'T_total': float(T[i]), 'R_total': float(R[i]), 'R_signed_monitor': float(R_signed[i]),
                'closure': float(T[i] + R[i]), 'residual': float(1 - T[i] - R[i]), 'order_fraction_sum': frac_sum,
                'order_absolute_sum': abs_sum, 'order_sum_relative_error': float((abs_sum - T[i]) / T[i]) if T[i] else float('nan'),
                'eta_plus1': eta_p, 'eta_0': eta_0, 'eta_minus1': eta_m,
                'non_target_efficiency': float(T[i] - eta_p) if np.isfinite(eta_p) else float('nan'),
                'plus1_fraction': float(eta_p / T[i]) if T[i] and np.isfinite(eta_p) else float('nan'),
                'directionality_fraction': float(eta_p / (eta_p + eta_m)) if np.isfinite(eta_p) and np.isfinite(eta_m) and (eta_p + eta_m) else float('nan'),
                'eta_plus1_over_minus1': float(eta_p / eta_m) if np.isfinite(eta_p) and np.isfinite(eta_m) and eta_m else float('nan'),
                'plus1_air_angle_deg': angle_p,
            })
        fields = list(metric_rows[0].keys())
        write_csv(case_dir / 'results_11points.csv', metric_rows, fields)
        write_csv(case_dir / 'order_spectrum.csv', order_rows, list(order_rows[0].keys()))

        b_rows = []
        b_meta = {}
        for name in boundary_names:
            z = float(fdtd.getnamed(name, 'z'))
            td = fdtd.getresult(name, 'T')
            bt = np.real(arr(td['T']))[:n]
            pd = fdtd.getresult(name, 'P')
            x = arr(pd['x']); y = arr(pd['y']); pa = np.asarray(pd['P'])
            pz = np.real(pa[:, :, 0, :n, 2])
            raw_int = np.asarray(trapz2(pz, x, y)).reshape(-1)[:n]
            src = np.array([float(fdtd.sourcepower(float(freq[i]))) for i in range(n)])
            # Lumerical P result is the un-halved E x H flux; time-averaged
            # normalized power uses 0.5 * integral(P) / sourcepower.
            raw_norm = 0.5 * raw_int / src
            b_meta[name] = {'z_m': z, 'x_points': int(len(x)), 'y_points': int(len(y)), 'x_min_m': float(x.min()), 'x_max_m': float(x.max()), 'y_min_m': float(y.min()), 'y_max_m': float(y.max()), 'dx_median_m': float(np.median(np.diff(x))), 'dy_median_m': float(np.median(np.diff(y))), 'time_averaged_poynting_factor': 0.5}
            for i in range(n):
                b_rows.append({'monitor': name, 'z_nm': z * 1e9, 'wavelength_nm': float(lam[i]), 'signed_T_result': float(bt[i]), 'raw_Pz_integral_W': float(raw_int[i]), 'sourcepower_W': float(src[i]), 'raw_Pz_over_sourcepower': float(raw_norm[i]), 'raw_vs_T_difference': float(raw_norm[i] - bt[i])})
        write_csv(case_dir / 'boundary_flux_11points.csv', b_rows, list(b_rows[0].keys()))
        Path(case_dir / 'boundary_monitor_inventory.json').write_text(json.dumps(b_meta, indent=2), encoding='utf-8')

        idx = fdtd.getresult('N1_DIAG_XZ_INDEX_449', 'index')
        xz = {k: np.asarray(v) for k, v in idx.items() if k in ('x','y','z','index_x','index_y','index_z')}
        raw_npz = run_dir / 'N1_DIAG_XZ_INDEX_449_449nm_raw.npz'
        np.savez_compressed(raw_npz, **xz)
        idx_summary = {'keys': list(idx.keys()), 'shape_index_x': list(np.asarray(idx['index_x']).shape), 'shape_index_y': list(np.asarray(idx['index_y']).shape), 'shape_index_z': list(np.asarray(idx['index_z']).shape), 'x_points': int(np.asarray(idx['x']).size), 'z_points': int(np.asarray(idx['z']).size), 'y_m': float(np.asarray(idx['y']).reshape(-1)[0]), 'x_min_nm': float(np.min(idx['x']) * 1e9), 'x_max_nm': float(np.max(idx['x']) * 1e9), 'z_min_nm': float(np.min(idx['z']) * 1e9), 'z_max_nm': float(np.max(idx['z']) * 1e9), 'raw_npz_sha256': sha256(raw_npz), 'raw_npz_path': str(raw_npz)}
        Path(case_dir / 'xz_index_summary.json').write_text(json.dumps(idx_summary, indent=2), encoding='utf-8')

        post_sha = sha256(post)
        summary = {'case_id': case, 'attempt_id': 'attempt_001', 'post_fsp_path': str(post), 'post_fsp_sha256': post_sha, 'readonly_session': True, 'run_called': False, 'save_called': False, 'wavelengths_nm': [float(x) for x in lam], 'max_abs_closure_residual': float(np.max(np.abs(1 - T - R))), 'min_T': float(np.min(T)), 'max_T': float(np.max(T)), 'min_R': float(np.min(R)), 'max_R': float(np.max(R)), 'max_abs_order_sum_relative_error': float(np.max(np.abs([(r['order_sum_relative_error']) for r in metric_rows]))), 'all_finite': bool(np.isfinite(T).all() and np.isfinite(R).all() and all(np.isfinite(float(r['eta_plus1'])) for r in metric_rows)), 'gate_closure_pass': bool(np.max(np.abs(1 - T - R)) <= 0.02), 'gate_order_sum_pass': bool(np.max(np.abs([(r['order_sum_relative_error']) for r in metric_rows])) <= 1e-8)}
        Path(case_dir / 'extraction_manifest.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        Path(case_dir / 'post_fsp_checksum.json').write_text(json.dumps({'post_fsp_path': str(post), 'sha256': post_sha, 'size_bytes': post.stat().st_size}, indent=2), encoding='utf-8')
        print(json.dumps(summary, indent=2))
    finally:
        fdtd.close()

if __name__ == '__main__':
    try: main()
    except Exception:
        traceback.print_exc(); raise
