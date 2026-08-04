import csv, hashlib, json, math, re, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, r'N:/Program Files/ANSYS Inc/v251/Lumerical/api/python')
import lumapi

ROOT = Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
STAGE = ROOT / 'outputs/np_k6_p0_simtime_2ps_recovery_v2_runtime'
CASE = 'RUN3C_P_PILOT_HF_SIMTIME_2PS_RECOVERY_V2'
RUN = STAGE / 'runtime_runs' / CASE / 'attempt_001'
W = np.arange(445, 456, dtype=int)
PLANES = ['N1_DIAG_PML_LOWER','N1_DIAG_LOWER_OUTSIDE','N1_DIAG_LOWER_INSIDE',
          'N1_DIAG_UPPER_INSIDE','N1_DIAG_UPPER_OUTSIDE','N1_DIAG_PML_UPPER']

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def flat(value):
    return np.asarray(value).reshape(-1)

def csv_write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)

def result(fd, name, kind='T'):
    try:
        d = fd.getresult(name, kind)
        if hasattr(d, 'items'):
            out = {'keys': list(d.keys()), 'raw': {}}
            for k, v in d.items():
                try: out['raw'][k] = flat(v)
                except Exception: pass
            out['T'] = out['raw'].get('T')
            out['lambda'] = out['raw'].get('lambda')
            if out['lambda'] is None: out['lambda'] = W * 1e-9
            return out
    except Exception:
        pass
    try:
        return {'keys': ['transmission'], 'raw': {}, 'T': flat(fd.transmission(name)), 'lambda': W * 1e-9}
    except Exception:
        return None

def grating(fd, name, index):
    out = {}
    for key, fn in [('fraction', 'grating'), ('order', 'gratingn'), ('u_x', 'gratingu1')]:
        try: out[key] = flat(getattr(fd, fn)(name, index + 1))
        except Exception: out[key] = None
    return out

def prop(fd, name, field):
    try: return float(fd.getnamed(name, field))
    except Exception: return None

def parse_runtime_log():
    logs = [p for p in RUN.glob('*.log') if p.is_file()]
    text = '\n'.join(p.read_text(encoding='utf-8', errors='replace') for p in logs)
    vals = [float(x) for x in re.findall(r'Auto Shutoff:\s*([0-9.eE+-]+)', text)]
    elapsed = [float(x) for x in re.findall(r'Elapsed simulation time:\s*([0-9.eE+-]+)\s*secs', text)]
    iterations = re.findall(r'Starting\s+([0-9]+)\s+total iterations', text)
    return {'log_paths': [str(p) for p in logs], 'final_auto_shutoff': vals[-1] if vals else None,
            'final_elapsed_simulation_time_s': elapsed[-1] if elapsed else None,
            'total_iterations': int(iterations[-1]) if iterations else None,
            'auto_shutoff_threshold': 1e-5, 'log_tail': text[-5000:]}

def main():
    ledger_path = RUN / 'entered_ledger.json'
    ledger = json.loads(ledger_path.read_text(encoding='utf-8-sig'))
    post = Path(ledger.get('post_fsp_path', RUN / f'{CASE}_attempt_001_post.fsp'))
    if not post.exists(): raise RuntimeError(f'post-FSP missing: {post}')
    fd = lumapi.FDTD(str(post), hide=True)
    try:
        tr, rr = result(fd, 'transmission_monitor'), result(fd, 'reflection_monitor')
        if not tr or not rr or tr.get('T') is None or rr.get('T') is None: raise RuntimeError('T/R unavailable')
        lam = np.rint(np.asarray(tr.get('lambda', W * 1e-9)) * 1e9).astype(int)
        if list(lam) != list(W): raise RuntimeError(f'wavelength grid {lam.tolist()}')
        t, r_signed = np.real(tr['T']), np.real(rr['T'])
        r_abs = np.abs(r_signed)
        metrics, orders, refl_orders = [], [], []
        for i, wl in enumerate(W):
            g = grating(fd, 'transmission_monitor', i)
            if g['fraction'] is None or g['order'] is None or g['u_x'] is None: raise RuntimeError('grating API unavailable')
            frac, order, ux = np.real(g['fraction']), np.rint(np.real(g['order'])).astype(int), np.real(g['u_x'])
            eta = {int(n): float(t[i] * frac[j]) for j, n in enumerate(order)}
            p, z, m = eta.get(1, float('nan')), eta.get(0, float('nan')), eta.get(-1, float('nan'))
            plus = np.flatnonzero(order == 1)
            angle = float(np.degrees(np.arcsin(np.clip(ux[plus[0]], -1, 1)))) if len(plus) else float('nan')
            for j, n in enumerate(order):
                orders.append({'wavelength_nm': int(wl), 'order_n': int(n), 'u_x': float(ux[j]),
                               'angle_deg': float(np.degrees(np.arcsin(np.clip(ux[j], -1, 1)))),
                               'transmitted_fraction': float(frac[j]), 'absolute_efficiency': float(t[i] * frac[j])})
            rg = grating(fd, 'reflection_monitor', i)
            if rg['fraction'] is not None and rg['order'] is not None:
                for j, n in enumerate(np.rint(np.real(rg['order'])).astype(int)):
                    refl_orders.append({'wavelength_nm': int(wl), 'order_n': int(n),
                                        'u_x': float(np.real(rg['u_x'][j])) if rg['u_x'] is not None else float('nan'),
                                        'reflected_fraction': float(np.real(rg['fraction'][j])),
                                        'absolute_efficiency': float(r_abs[i] * np.real(rg['fraction'][j]))})
            freq = tr.get('raw', {}).get('f')
            try: sourcepower = float(fd.sourcepower(float(freq[i]))) if freq is not None else float('nan')
            except Exception: sourcepower = float('nan')
            raw_t = None
            raw_r = None
            for key in ('power', 'Pz', 'power_total', 'T_raw'):
                if key in tr.get('raw', {}):
                    try: raw_t = float(np.real(tr['raw'][key][i])); break
                    except Exception: pass
                if key in rr.get('raw', {}):
                    try: raw_r = float(np.real(rr['raw'][key][i])); break
                    except Exception: pass
            metrics.append({'case_id': CASE, 'wavelength_nm': int(wl), 'T_total': float(t[i]),
                            'R_signed_monitor': float(r_signed[i]), 'R_total': float(r_abs[i]),
                            'closure': float(t[i] + r_abs[i]), 'signed_closure_residual': float(1 - t[i] - r_abs[i]),
                            'sourcepower_W': sourcepower, 'raw_transmitted_power_W': raw_t,
                            'raw_reflected_power_W': raw_r, 'normalization_path': 'monitor_T_and_order_sum',
                            'transmitted_order_sum': float(np.sum(t[i] * frac)),
                            'transmitted_order_sum_mismatch': float(np.sum(t[i] * frac) - t[i]),
                            'eta_plus1': p, 'eta_0': z, 'eta_minus1': m,
                            'non_target_efficiency': float(t[i] - p) if np.isfinite(p) else float('nan'),
                            'directionality': float(p / (p + m)) if np.isfinite(p) and np.isfinite(m) and p + m else float('nan'),
                            'eta_plus1_over_minus1': float(p / m) if np.isfinite(p) and np.isfinite(m) and m else float('nan'),
                            'plus1_transmitted_fraction': float(p / t[i]) if np.isfinite(p) and t[i] else float('nan'),
                            'plus1_air_side_angle_deg': angle, 'transmitted_order_count': int(len(order))})
        inv, flux_rows = [], []
        for name in PLANES:
            res = result(fd, name); vals = res.get('T') if res else None
            z = prop(fd, name, 'z')
            inv.append({'monitor': name, 'z_m': z, 'result_keys': res.get('keys', []) if res else [],
                        'inside_fixed_mesh': None, 'signed_flux_convention': 'monitor_result_T'})
            for i, wl in enumerate(W):
                flux_rows.append({'monitor': name, 'z_m': z, 'wavelength_nm': int(wl),
                                  'signed_normalized_flux': float(vals[i]) if vals is not None and i < len(vals) else float('nan')})
        inv.sort(key=lambda x: x['z_m'] if x['z_m'] is not None else 1e99)
        csv_write(STAGE / 'spectral_metrics_11points.csv', metrics)
        csv_write(STAGE / 'transmitted_orders_11points.csv', orders)
        csv_write(STAGE / 'reflected_orders_11points.csv', refl_orders)
        csv_write(STAGE / 'boundary_plane_flux_spectrum.csv', flux_rows)
        by = {(x['monitor'], x['wavelength_nm']): x['signed_normalized_flux'] for x in flux_rows}
        intervals = []
        for a, b in zip(inv, inv[1:]):
            for wl in W:
                fa, fb = by[(a['monitor'], int(wl))], by[(b['monitor'], int(wl))]
                intervals.append({'from_monitor': a['monitor'], 'to_monitor': b['monitor'], 'wavelength_nm': int(wl),
                                  'flux_a': fa, 'flux_b': fb, 'delta_F': fb - fa,
                                  'abs_delta_F': abs(fb - fa) if np.isfinite(fa + fb) else float('nan')})
        csv_write(STAGE / 'boundary_interval_flux_balance.csv', intervals)
        runtime = parse_runtime_log()
        summary = {'case_id': CASE, 'post_fsp_path': str(post), 'post_fsp_sha256': sha(post),
                   'readonly_reload': True, 'run_called': False, 'save_called': False,
                   'wavelengths_nm': [int(x) for x in W], 'metrics': metrics,
                   'boundary_monitor_inventory': inv, 'runtime': runtime,
                   'max_abs_closure_residual': max(abs(x['signed_closure_residual']) for x in metrics),
                   'order_mismatch_max': max(abs(x['transmitted_order_sum_mismatch']) for x in metrics)}
        (STAGE / 'runtime_extraction_summary.json').write_text(json.dumps(summary, indent=2, default=str), encoding='utf-8')
        print(json.dumps(summary, indent=2, default=str))
    finally:
        fd.close()

if __name__ == '__main__': main()
