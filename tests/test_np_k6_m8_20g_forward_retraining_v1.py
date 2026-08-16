import csv, json, hashlib
from pathlib import Path

R = Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
O = R / 'outputs/np_k6_m8_20g_forward_retraining_v1'

def load_json(name):
    return json.loads((O / name).read_text(encoding='utf-8-sig'))

def load_csv(name):
    with (O / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def test_m8_final_validator_passes():
    assert load_json('m8_final_validator_report.json')['status'] == 'PASS'

def test_m8_prereg_and_authority():
    p = O / 'NP_K6_M8_20G_FORWARD_RETRAINING_PREREG_V1.json'
    assert hashlib.sha256(p.read_bytes()).hexdigest() == 'fc05bc4d99cb54fa48558cda3605da53aa3fbda3f84c995a5493dfb820131ef9'
    m = load_json('m8_training_run_manifest.json')
    assert (m['rows'], m['geometries'], m['paired_cases']) == (440, 20, 40)
    assert m['outer_cv'] == '20-fold LOGO' and m['seeds'] == [17, 29, 43]

def test_m8_oof_contract_and_solver_zero():
    rows = load_csv('oof_predictions_20g.csv')
    assert len(rows) == 3960
    assert len({(r['geometry_id'], r['polarization'], r['wavelength_nm'], r['model']) for r in rows}) == 3960
    assert load_json('solver_zero_audit.json').get('solver_calls', 0) == 0
    assert load_json('m8_external_promotion_decision.json').get('external_hf_authorized', False) is False

def test_m8_requirement_audit_and_detailed_learning_value():
    assert load_json('m8_requirement_audit.json')['status'] == 'PASS'
    assert load_json('residual_reconstruction_audit.json')['pass'] is True
    assert load_json('selection_time_preservation_audit.json')['fields_match_manifest'] is True
    assert len(load_csv('common_HF16_full_metric_delta.csv')) == 144
    assert len(load_csv('new4_heldout_full_difficulty.csv')) == 36
    assert len(load_csv('hf20_ps_truth_distribution_summary.csv')) == 24
