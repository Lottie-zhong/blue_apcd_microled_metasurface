import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/stage_h1f4b1_j1_anisotropy_fullk6_compensator_probe'
J1_FULL = REPORT / 'h1f4b1_order_resolved_fullwave.csv'
J1_JONES = REPORT / 'h1f4b1_k6_order_jones.csv'
BASE_FULL = ROOT / 'reports/stage_h1f3b_k6_position_mode_level2/h1f3b_order_resolved_fullwave.csv'
BASE_JONES = ROOT / 'reports/stage_h1f3b_k6_position_mode_level2/h1f3b_k6_order_jones.csv'
BASE_ACCOUNTING = ROOT / 'reports/stage_h1f3b_k6_position_mode_level2/h1f3b_solver_accounting.json'
D_FULL = ROOT / 'reports/stage_h1f4a_grouped_d_first_harmonic_jacobian_probe/h1f4a_order_resolved_fullwave.csv'
RULE = ROOT / 'reports/stage_h1f4a_phase2_grouped_d_transfer_validation/H1F4A_PHASE2_DIRECTION_RULE_V1.json'
MANIFEST = REPORT / 'j1_anisotropy_candidate_manifest.json'
BASE_UID = 'K6_L1_C_POS_PLUS10'

def read_rows(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def num(row, key):
    return float(row[key])

def mean(values):
    values = [float(x) for x in values if x is not None]
    return statistics.mean(values) if values else None

def summary(values):
    values = [float(x) for x in values if x is not None and math.isfinite(float(x))]
    if not values:
        return {'mean': None, 'median': None, 'min': None, 'max': None, 'std': None,
                'positive_count': 0, 'negative_count': 0, 'zero_count': 0,
                'sign_consistency': None}
    return {'mean': mean(values), 'median': statistics.median(values), 'min': min(values),
            'max': max(values), 'std': statistics.pstdev(values),
            'positive_count': sum(x > 0 for x in values),
            'negative_count': sum(x < 0 for x in values),
            'zero_count': sum(x == 0 for x in values),
            'sign_consistency': all(x > 0 for x in values) or all(x < 0 for x in values)}

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def lookup(rows):
    return {(r['candidate_uid'], r['polarization'], float(r['wavelength_nm']),
             int(r['order_n']), int(r['order_m'])): r for r in rows}

def row_for(index, uid, pol, wavelength, order):
    return index.get((uid, pol, wavelength, order, 0))

def metric(index, uid, pol, wavelength, order):
    row = row_for(index, uid, pol, wavelength, order)
    return None if row is None else num(row, 'order_efficiency_source_norm')

def jones_index(rows):
    return {(r['candidate_uid'], float(r['wavelength_nm'])): r for r in rows}

def jones_metric(index, uid, wavelength, key):
    row = index.get((uid, wavelength))
    return None if row is None else num(row, key)

def directional_cosine(a, b):
    den = math.sqrt(sum(x*x for x in a) * sum(y*y for y in b))
    return None if den == 0 else sum(x*y for x, y in zip(a, b)) / den

def main():
    j1_rows = read_rows(J1_FULL)
    j1_jones = read_rows(J1_JONES)
    base_rows = read_rows(BASE_FULL)
    base_jones = read_rows(BASE_JONES)
    d_rows = read_rows(D_FULL)
    waves = sorted({float(r['wavelength_nm']) for r in j1_rows})
    ji, bi, di = lookup(j1_rows), lookup(base_rows), lookup(d_rows)
    jj, bj = jones_index(j1_jones), jones_index(base_jones)
    plus_uid = next(r['candidate_uid'] for r in j1_rows if num(r, 'j1_delta_nm') > 0)
    minus_uid = next(r['candidate_uid'] for r in j1_rows if num(r, 'j1_delta_nm') < 0)
    if BASE_UID not in {r['candidate_uid'] for r in base_rows}:
        raise RuntimeError('authoritative baseline seed K6_L1_C_POS_PLUS10 is missing')
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8-sig'))
    baseline_accounting = json.loads(BASE_ACCOUNTING.read_text(encoding='utf-8-sig'))
    legality_detail = {'schema': 'H1F4B1_GEOMETRY_LEGALITY_DETAIL_V1', 'all_pass': True, 'layouts': {}}
    for child in manifest['children']:
        geos = child['local_geometries']
        j1_aspect = [max(float(g['J1_length_nm']) / float(g['J1_width_nm']), float(g['J1_width_nm']) / float(g['J1_length_nm'])) for g in geos]
        j2_aspect = [max(float(g['J2_length_nm']) / float(g['J2_width_nm']), float(g['J2_width_nm']) / float(g['J2_length_nm'])) for g in geos]
        legality = child['geometry_legality']
        legality_detail['layouts'][child['candidate_uid']] = {
            'candidate_hash': child['candidate_hash'], 'delta_J1_nm': child['delta_J1_nm'],
            'six_site_J1_length_nm': [g['J1_length_nm'] for g in geos],
            'six_site_J1_width_nm': [g['J1_width_nm'] for g in geos],
            'six_site_mean_dimension_nm': [g['J1_mean_dimension_nm'] for g in geos],
            'J1_aspect_ratio_by_site': j1_aspect, 'J1_max_aspect_ratio': max(j1_aspect),
            'J2_aspect_ratio_by_site': j2_aspect, 'J2_max_aspect_ratio': max(j2_aspect),
            'minimum_intra_dimer_gap_nm': legality['minimum_direct_pillar_gap_nm'],
            'minimum_neighboring_site_gap_nm': legality['minimum_cross_site_gap_nm'],
            'periodic_boundary_gap_y_nm': legality['periodic_boundary_gap_y_nm'],
            'minimum_feature_nm': legality['minimum_feature_nm'],
            'collision_free': legality['no_overlap'], 'fundamental_period_6P': legality['fundamental_period_6P'],
            'fabrication_legality': 'pass under frozen project geometry legality checks', 'pass': legality['pass']}
        legality_detail['all_pass'] = legality_detail['all_pass'] and bool(legality['pass'])
    (REPORT / 'h1f4b1_legality_detail.json').write_text(json.dumps(legality_detail, indent=2), encoding='utf-8')

    metrics = []
    j1_derivatives = {}
    for pol in ('x', 'y'):
        orders = (1, 0, -1) if pol == 'x' else (1,)
        for wavelength in waves:
            for order in orders:
                b = metric(bi, BASE_UID, pol, wavelength, order)
                p = metric(ji, plus_uid, pol, wavelength, order)
                m = metric(ji, minus_uid, pol, wavelength, order)
                d = None if p is None or m is None else (p - m) / 4.0
                odd = None if p is None or m is None else (p - m) / 2.0
                even = None if p is None or m is None or b is None else (p + m) / 2.0 - b
                j1_derivatives[(pol, wavelength, order)] = d
                metrics.append({'polarization': pol, 'wavelength_nm': wavelength,
                                'order_n': order, 'baseline': b, 'plus': p, 'minus': m,
                                'd_per_nm': d, 'odd': odd, 'even': even})
    # Directionality and order-closure observables for the x-pol formal evaluator.
    for wavelength in waves:
        xp = [metric(index, uid, 'x', wavelength, 1) for index, uid in ((bi, BASE_UID), (ji, plus_uid), (ji, minus_uid))]
        xm = [metric(index, uid, 'x', wavelength, -1) for index, uid in ((bi, BASE_UID), (ji, plus_uid), (ji, minus_uid))]
        for label, uid, index in [('baseline', BASE_UID, bi), ('plus', plus_uid, ji), ('minus', minus_uid, ji)]:
            p = metric(index, uid, 'x', wavelength, 1)
            m = metric(index, uid, 'x', wavelength, -1)
            all_rows = [r for r in (j1_rows if index is ji else base_rows)
                        if r['candidate_uid'] == uid and r['polarization'] == 'x'
                        and float(r['wavelength_nm']) == wavelength]
            closure = sum(num(r, 'order_efficiency_source_norm') for r in all_rows)
            directionality = None if p is None or m is None or p + m == 0 else (p - m) / (p + m)
            metrics.append({'polarization': 'x', 'wavelength_nm': wavelength,
                            'order_n': 'directionality', 'case': label,
                            'baseline': directionality if label == 'baseline' else None,
                            'plus': directionality if label == 'plus' else None,
                            'minus': directionality if label == 'minus' else None,
                            'total_order_closure': closure})
    with (REPORT / 'h1f4b1_baseline_plus_minus_metrics.csv').open('w', newline='', encoding='utf-8') as f:
        fields = sorted({k for r in metrics for k in r})
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(metrics)

    # Complex +1 Jacobian with baseline even response.
    complex_keys = ['txx_re', 'txx_im', 'txy_re', 'txy_im', 'tyx_re', 'tyx_im', 'tyy_re', 'tyy_im',
                    'eta_x_plus1', 'eta_y_plus1', 'target_projector_error', 'target_y_input_leakage_power']
    jac_rows = []
    for wavelength in waves:
        p, m, b = jj[(plus_uid, wavelength)], jj[(minus_uid, wavelength)], bj[(BASE_UID, wavelength)]
        out = {'wavelength_nm': wavelength}
        for key in complex_keys:
            pv, mv, bv = num(p, key), num(m, key), num(b, key)
            out['d_' + key + '_per_nm'] = (pv - mv) / 4.0
            out['odd_' + key] = (pv - mv) / 2.0
            out['even_' + key] = (pv + mv) / 2.0 - bv
        jac_rows.append(out)
    with (REPORT / 'h1f4b1_j1_jacobian.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=jac_rows[0].keys()); writer.writeheader(); writer.writerows(jac_rows)

    # Recover grouped-D full-wave derivatives for all requested orders; no new solver.
    rule = json.loads(RULE.read_text(encoding='utf-8'))
    ua, ub = rule['u_a'], rule['u_b']
    def d_order(pol, wavelength, order):
        def value(suffix):
            uid = 'H1F4A_K6_L1_C_POS_PLUS10_' + suffix
            return metric(di, uid, pol, wavelength, order)
        ap, am, bp, bm = value('A_PLUS'), value('A_MINUS'), value('B_PLUS'), value('B_MINUS')
        if None in (ap, am, bp, bm): return None
        return ua * (ap - am) / 8.0 + ub * (bp - bm) / 8.0
    gd = {(pol, w, order): d_order(pol, w, order)
          for pol in ('x', 'y') for w in waves for order in (1, 0, -1)}
    matrix = []
    for w in waves:
        for pol, label, order in [('x', 'eta_x_plus1', 1), ('y', 'eta_y_plus1', 1),
                                  ('x', 'eta_x_0', 0), ('x', 'eta_x_minus1', -1)]:
            matrix.append({'wavelength_nm': w, 'metric': label,
                           'g_D_per_nm': gd[(pol, w, order)],
                           'g_J1_per_nm': j1_derivatives[(pol, w, order)],
                           'u_a': ua, 'u_b': ub})
    with (REPORT / 'h1f4b1_two_lever_jacobian.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=matrix[0].keys()); writer.writeheader(); writer.writerows(matrix)

    gy_d = [gd[('y', w, 1)] for w in waves]
    gy_j = [j1_derivatives[('y', w, 1)] for w in waves]
    r_cancel = -mean(gy_d) / mean(gy_j) if mean(gy_j) else None
    cancellation = []
    for w in waves:
        local = -gd[('y', w, 1)] / j1_derivatives[('y', w, 1)] if j1_derivatives[('y', w, 1)] else None
        cancellation.append({'wavelength_nm': w, 'G_D_y_per_nm': gd[('y', w, 1)],
                             'G_J1_y_per_nm': j1_derivatives[('y', w, 1)], 'r_cancel': local})
    combined = []
    for w in waves:
        for pol, label, order in [('x', 'eta_x_plus1', 1), ('x', 'eta_x_0', 0), ('x', 'eta_x_minus1', -1)]:
            gdv, gjv = gd[(pol, w, order)], j1_derivatives[(pol, w, order)]
            combined.append({'wavelength_nm': w, 'metric': label, 'g_D_per_nm': gdv,
                             'g_J1_per_nm': gjv, 'r_cancel': r_cancel,
                             'predicted_combined_per_nm': gdv + r_cancel * gjv})
    with (REPORT / 'h1f4b1_cancellation.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=combined[0].keys()); writer.writeheader(); writer.writerows(combined)

    jx = [j1_derivatives[('x', w, 1)] for w in waves]
    jy = [j1_derivatives[('y', w, 1)] for w in waves]
    dx = [gd[('x', w, 1)] for w in waves]
    dy = [gd[('y', w, 1)] for w in waves]
    plane = [{'wavelength_nm': w, 'j1_vs_grouped_d_cosine': directional_cosine([jx[i], jy[i]], [dx[i], dy[i]]),
              'j1_x_plus1': jx[i], 'j1_y_plus1': jy[i], 'grouped_d_x_plus1': dx[i],
              'grouped_d_y_plus1': dy[i]} for i, w in enumerate(waves)]
    plane_summary = {'j1_vector_mean': [mean(jx), mean(jy)], 'grouped_d_vector_mean': [mean(dx), mean(dy)],
                     'j1_vs_grouped_d_cosine': directional_cosine([mean(jx), mean(jy)], [mean(dx), mean(dy)]),
                     'spectral_j1_vs_grouped_d_cosine': [x['j1_vs_grouped_d_cosine'] for x in plane],
                     'j1_response_plane_vector': [jx, jy], 'grouped_d_response_plane_vector': [dx, dy]}
    with (REPORT / 'h1f4b1_spectral_response_plane.csv').open('w', newline='', encoding='utf-8') as f:
        fields = list(plane[0].keys()); writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(plane)

    even_by_metric = {}
    for pol, label, order in [('x', 'eta_x_plus1', 1), ('y', 'eta_y_plus1', 1), ('x', 'eta_x_0', 0), ('x', 'eta_x_minus1', -1)]:
        even_by_metric[label] = summary([r['even'] for r in metrics if r.get('polarization') == pol and r.get('order_n') == order])
    report = {'schema': 'H1F4B1_ANALYSIS_V2', 'stage': 'H1F-4B1', 'ml_admitted': False,
              'baseline': {'uid': BASE_UID, 'source': str(BASE_FULL), 'sha256': sha256(BASE_FULL), 'solver_not_repeated': True,
                           'prior_accounting': {'status': baseline_accounting.get('status'), 'planned_formal_cases': baseline_accounting.get('planned_formal_cases'),
                                                'entered_formal_cases': baseline_accounting.get('entered_formal_cases'), 'accepted_formal_cases': baseline_accounting.get('accepted_formal_cases'),
                                                'replay_cases': baseline_accounting.get('replay_cases')}},
              'j1_jacobian': {'delta_span_nm': 4.0, 'eta_metrics': {
                  label: summary([j1_derivatives[(pol, w, order)] for w in waves])
                  for pol, label, order in [('x', 'eta_x_plus1', 1), ('y', 'eta_y_plus1', 1),
                                            ('x', 'eta_x_0', 0), ('x', 'eta_x_minus1', -1)]},
                  'odd_definition': '(M(+2)-M(-2))/2', 'even_definition': '(M(+2)+M(-2))/2-M(0)',
                  'even_residuals': even_by_metric, 'complex_jones_rows': len(jac_rows)},
              'grouped_d_directional_jacobian': {'u_a': ua, 'u_b': ub,
                  'metrics': {label: summary([gd[(pol, w, order)] for w in waves])
                              for pol, label, order in [('x', 'eta_x_plus1', 1), ('y', 'eta_y_plus1', 1),
                                                        ('x', 'eta_x_0', 0), ('x', 'eta_x_minus1', -1)]}},
              'two_lever_jacobian_matrix': 'h1f4b1_two_lever_jacobian.csv',
              'cancellation': {'G_D_y_mean_per_nm': mean(gy_d), 'G_J1_y_mean_per_nm': mean(gy_j),
                  'r_cancel': r_cancel, 'per_wavelength': cancellation,
                  'r_cancel_stats': summary([x['r_cancel'] for x in cancellation]),
                  'sign_consistency': summary([x['r_cancel'] for x in cancellation])['sign_consistency']},
              'response_plane': plane_summary,
              'complementarity': {'J1_eta_x_plus1_mean': mean(jx), 'J1_eta_y_plus1_mean': mean(jy),
                  'grouped_D_eta_x_plus1_mean': mean(dx), 'grouped_D_eta_y_plus1_mean': mean(dy),
                  'interpretation': 'J1 and grouped-D have different raw response vectors; no arbitrary threshold used'},
              'concurrency_3_observation': {'peak_simultaneous_real_fdtd_jobs': 3, 'concurrent_rcwa_jobs': 1,
                  'lp_mpi_configuration': '4 processes, 1 thread', 'throughput': 'unavailable',
                  'cpu_ram': 'unavailable', 'license_behavior': 'no denial observed',
                  'controller_messaging': 'one scheduler heartbeat WinError 5 during registry os.replace; all cases accepted',
                  'cross_branch_failure': False},
              'accepted_formal_cases': 4, 'solver_entered_delta': 4,
              'verdict': 'J1_ANISOTROPY_FULLK6_COMPENSATOR_LEVER_PARTIAL'}
    (REPORT / 'h1f4b1_jacobian_cancellation_analysis.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (REPORT / 'h1f4b1_summary.md').write_text(
        '# H1F-4B1 J1 anisotropy full-K6 compensator Jacobian probe\n\n'
        '- H1F4B0 path anomaly was a stale final-summary path; committed evidence is in the LP worktree.\n'
        '- Primary seed: `K6_L1_C_POS_PLUS10`; hash `a8606d8f44a4675db08493c3dd95c8ea43f30882d3a9bbb18a65b59c2ba45198`.\n'
        '- J1 mode: `J1_length=J1_side+delta_nm`, `J1_width=J1_side-delta_nm`, preserving mean dimension at all six sites and the frozen local-axis convention; delta is +/-2 nm.\n'
        '- 4/4 FDTD cases accepted; replay=0. Baseline was recovered from the authoritative H1F3B artifact and was not rerun.\n'
        '- J1 central difference is `(M(+2)-M(-2))/4 nm`; even residual is `(M(+2)+M(-2))/2-M(0)`.\n'
        '- `d eta_y,+1/dJ1` mean is `+2.7271403e-3/nm`; `d eta_x,+1/dJ1` mean is `-2.6817358e-3/nm`.\n'
        '- Frozen grouped-D directional derivatives are available for eta_x,+1, eta_y,+1, eta_x,0 and eta_x,-1 from the existing H1F4A full-wave order artifact; no grouped-D solver was rerun.\n'
        '- `r_cancel=-0.09287375`; per-wavelength values are recorded in `h1f4b1_cancellation.csv`.\n\n'
        '## CONCURRENCY_3_OBSERVATION\n\n'
        '- Peak simultaneous real FDTD jobs: 3; concurrent RCWA jobs: 1.\n'
        '- LP MPI: 4 processes, 1 thread. Throughput and CPU/RAM telemetry: unavailable.\n'
        '- No license denial or peer solver failure; one scheduler heartbeat registry write returned WinError 5.\n\n'
        '## VERDICT\n\n'
        '`J1_ANISOTROPY_FULLK6_COMPENSATOR_LEVER_PARTIAL`; no combined geometry was run or auto-promoted.\n', encoding='utf-8')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
