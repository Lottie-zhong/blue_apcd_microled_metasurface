from pathlib import Path
import csv, json, math

ROOT = Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1')
OUT = ROOT / 'outputs' / 'np_k6_m2_batch1_hf_dataset_v1'

def read(path):
    with path.open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def test_batch1_dataset_exact_shape_and_gates():
    rows = read(OUT / 'hf_observations_long.csv')
    assert len(rows) == 132
    assert len({r['case_id'] for r in rows}) == 12
    assert all(sorted(int(r['wavelength_nm']) for r in rows if r['case_id'] == c) == list(range(445,456)) for c in {r['case_id'] for r in rows})
    assert len({(r['case_id'], r['wavelength_nm']) for r in rows}) == 132
    assert all(r['quality_gate_pass'] == 'true' and r['training_label'] == 'false' for r in rows)
    assert all(math.isfinite(float(r[k])) for r in rows for k in ('T_total','R_total','eta_plus1','eta_0','eta_minus1'))

def test_batch1_state_and_validator_report():
    state = json.loads((OUT / 'batch1_dataset_state.json').read_text())
    report = json.loads((OUT / 'batch1_dataset_validator_report.json').read_text())
    assert state['status'] == 'NP_K6_M2_BATCH1_HF_ACQUISITION_COMPLETE_RETRAIN_READY'
    assert state['formal_observation_count'] == 132
    assert state['real_training_started'] is False and state['sealed_access'] == 0
    assert report['status'] == 'PASS'
