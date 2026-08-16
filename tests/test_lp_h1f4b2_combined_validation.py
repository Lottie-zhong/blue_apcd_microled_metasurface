import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/stage_h1f4b2_grouped_d_j1_combined_local_validation'

def test_combined_rule_and_precision_are_frozen():
    m = json.loads((REPORT / 'h1f4b2_combined_candidate_manifest.json').read_text(encoding='utf-8'))
    p = json.loads((REPORT / 'h1f4b2_fabrication_precision_audit.json').read_text(encoding='utf-8'))
    assert m['status'] == 'FROZEN_READY_FOR_SOLVER'
    assert m['candidate_count'] == 2 and m['max_new_formal_cases'] == 4
    assert m['parent_hash'] == 'a8606d8f44a4675db08493c3dd95c8ea43f30882d3a9bbb18a65b59c2ba45198'
    assert m['exact_delta_J1_plus_nm'] == -0.3714949866125559
    assert m['exact_delta_J1_minus_nm'] == 0.3714949866125559
    assert p['rounding_applied'] is False and p['builder_rounding_or_quantization'] is False

def test_four_cases_pass_without_replay():
    a = json.loads((REPORT / 'h1f4b2_solver_accounting.json').read_text(encoding='utf-8'))
    assert a['planned_formal_cases'] == 4
    assert a['entered_formal_cases'] == 4
    assert a['accepted_formal_cases'] == 4
    assert a['replay_cases'] == 0
    assert all(row['status'] == 'ACCEPTED' for row in a['cases'])

def test_observed_prediction_and_cancellation_artifacts():
    a = json.loads((REPORT / 'h1f4b2_observed_analysis.json').read_text(encoding='utf-8'))
    assert a['ml_admitted'] is False
    assert a['verdict'] == 'GROUPED_D_PLUS_J1_CANCELLATION_FAILED'
    assert a['cancellation']['compensation_failure'] is True
    assert a['concurrency_3_observation']['peak_simultaneous_real_fdtd_jobs'] == 1
    with (REPORT / 'h1f4b2_observed_vs_predicted_metrics.csv').open(encoding='utf-8') as f:
        assert len(list(csv.DictReader(f))) == 36
    with (REPORT / 'h1f4b2_cancellation_validation.csv').open(encoding='utf-8') as f:
        assert len(list(csv.DictReader(f))) == 9
