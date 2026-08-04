from __future__ import annotations
from pathlib import Path
import csv
import json
import math
import sys

ROOT = Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1')
OUT = ROOT / 'outputs/np_k6_p0_observable_convergence_adjudication_v1'
REQUIRED = [
    'stopped_10ps_attempt_audit.json', 'label_fidelity_contract_v2.json',
    'convergence_2ps_3ps_spectral_comparison.csv', 'transmitted_order_convergence.csv',
    'convergence_gate_results.json', 'convergence_trend_1ps_2ps_3ps.json',
    'generator_v2_contract.json', 'remaining_anchor_authorization_manifest.json',
    'checksum_manifest.json', 'provenance_audit.json',
]

def load(name):
    return json.loads((OUT / name).read_text(encoding='utf-8'))

errors = []
for name in REQUIRED:
    if not (OUT / name).is_file(): errors.append(f'missing:{name}')
if not errors:
    gates = load('convergence_gate_results.json')
    if gates.get('classification') != 'NP_K6_P0_OBSERVABLE_CONVERGENCE_ACCEPTED_3PS_GENERATOR_READY': errors.append('classification')
    if gates.get('all_gates_pass') is not True: errors.append('all_gates_pass')
    stop = load('stopped_10ps_attempt_audit.json')
    if stop.get('entered') is not True or stop.get('run_invocation_count') != 1: errors.append('10ps_budget')
    if stop.get('classification') not in {'NP_K6_P0_10PS_FINAL_USER_ABORTED_NO_VALID_POST', 'NP_K6_P0_10PS_FINAL_USER_ABORTED_PARTIAL_POST_UNUSABLE'}: errors.append('10ps_classification')
    if stop.get('rerun_forbidden') is not True or stop.get('recovery_forbidden') is not True: errors.append('10ps_no_recovery')
    checks = load('checksum_manifest.json')
    if checks.get('post_sha_identity_pass') is not True: errors.append('post_sha_identity')
    gen = load('generator_v2_contract.json')
    if gen.get('generator_id') != 'NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_3PS_V2' or gen.get('maximum_simulation_time_s') != 3e-12: errors.append('generator_contract')
    contract = load('label_fidelity_contract_v2.json')
    if contract.get('auto_shutoff', {}).get('sole_label_gate') is not False: errors.append('auto_shutoff_role')
    rem = load('remaining_anchor_authorization_manifest.json')
    if rem.get('all_untouched') is not True or any(not x.get('untouched') for x in rem.get('remaining_cases', [])): errors.append('remaining_anchor')
    if rem.get('formal_hf_labels') != 0 or rem.get('training_labels') != 0: errors.append('labels')
    if load('provenance_audit.json').get('solver_calls_this_round') != 0: errors.append('solver_calls')
    with (OUT / 'convergence_2ps_3ps_spectral_comparison.csv').open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 11 or [int(r['wavelength_nm']) for r in rows] != list(range(445, 456)): errors.append('spectral_11_points')
    with (OUT / 'transmitted_order_convergence.csv').open(newline='', encoding='utf-8') as f:
        order_rows = list(csv.DictReader(f))
    if len(order_rows) != 77: errors.append('order_rows')
    for r in rows + order_rows:
        for v in r.values():
            if v == '': continue
            try:
                if not math.isfinite(float(v)): errors.append('nonfinite'); raise ValueError
            except ValueError:
                if v == 'nan' or v == 'inf' or v == '-inf': errors.append('nonfinite')

report = {'validator': 'np_k6_p0_observable_convergence_adjudication_v1', 'pass': not errors, 'errors': errors, 'solver_calls_this_round': 0, 'classification': load('convergence_gate_results.json').get('classification') if not errors else None}
(OUT / 'stage_validator_report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
if errors: raise SystemExit(1)
