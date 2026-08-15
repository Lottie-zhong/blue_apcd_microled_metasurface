import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/stage_h1f4b1_j1_anisotropy_fullk6_compensator_probe'

def test_manifest_and_scheduler_contract():
    m = json.loads((REPORT / 'j1_anisotropy_candidate_manifest.json').read_text(encoding='utf-8'))
    assert m['status'] == 'FROZEN_READY_FOR_SOLVER'
    assert m['candidate_count'] == 2 and m['max_new_formal_cases'] == 4
    assert m['solver_plan']['effective_global_fdtd_capacity'] == 3
    assert m['solver_plan']['permanent_global_fdtd_policy'] == 2
    assert m['ml_admitted'] is False
    assert m['grouped_d_perturbation_nm'] == 0.0

def test_four_cases_accepted_without_replay():
    a = json.loads((REPORT / 'h1f4b1_solver_accounting.json').read_text(encoding='utf-8'))
    assert a['entered_formal_cases'] == 4
    assert a['accepted_formal_cases'] == 4
    assert a['replay_cases'] == 0
    assert all(x['status'] == 'ACCEPTED' for x in a['cases'])

def test_jacobian_and_concurrency_artifacts():
    analysis = json.loads((REPORT / 'h1f4b1_jacobian_cancellation_analysis.json').read_text(encoding='utf-8'))
    assert analysis['accepted_formal_cases'] == 4
    assert analysis['j1_jacobian']['delta_span_nm'] == 4.0
    assert analysis['concurrency_3_observation']['peak_simultaneous_real_fdtd_jobs'] == 3
    assert analysis['concurrency_3_observation']['concurrent_rcwa_jobs'] == 1
    assert analysis['ml_admitted'] is False
    assert analysis['baseline']['uid'] == 'K6_L1_C_POS_PLUS10'
    assert analysis['baseline']['solver_not_repeated'] is True
    assert analysis['baseline']['prior_accounting']['accepted_formal_cases'] == 8
    assert analysis['j1_jacobian']['even_residuals']['eta_x_plus1']['mean'] is not None
    assert analysis['cancellation']['r_cancel'] is not None
    assert analysis['response_plane']['j1_vs_grouped_d_cosine'] is not None
    with (REPORT / 'h1f4b1_two_lever_jacobian.csv').open(encoding='utf-8') as f:
        assert len(list(csv.DictReader(f))) == 36
    legality = json.loads((REPORT / 'h1f4b1_legality_detail.json').read_text(encoding='utf-8'))
    assert legality['all_pass'] is True
    assert all(x['pass'] for x in legality['layouts'].values())
    with (REPORT / 'h1f4b1_j1_jacobian.csv').open(encoding='utf-8') as f:
        assert len(list(csv.DictReader(f))) == 9
