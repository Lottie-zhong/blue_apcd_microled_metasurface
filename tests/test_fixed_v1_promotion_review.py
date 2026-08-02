from pathlib import Path
import json

ROOT = Path(r'D:\project\worktrees\blue_apcd_mdc_ml_inverse_v1')
REVIEW = ROOT / 'outputs/mdc_replacement_hf_external_r12_solver_evaluation_v1/20260802T150000Z_R12_SOLVER/promotion_review'

def read(name):
    return json.loads((REVIEW / name).read_text())

def test_integrity_and_decision():
    audit = read('promotion_input_integrity_audit.json')
    assert audit['status'] == 'PASS'
    assert audit['prediction_sha_observed'] == '80cf649a194aa95f362388a619c095c3e2fb97626cc54ca37df9b84ddc72a061'
    assert audit['routing_sha_observed'] == '2f0bc3223a9228e8c4c9c494942178fe203e3959598bdaeb635bc6e1da5f56a0'
    registry = read('fixed_v1_promotion_review_registry.json')
    assert registry['quantitative_high_fidelity_promotion'] == 'REJECTED'
    assert registry['model_state'] == 'FROZEN'
    assert registry['sealed_test_authorized'] is False

def test_summary_and_rank_outputs():
    assert read('formal_metric_summary_check.json')['status'] == 'PASS'
    rank = read('targetwise_rank_evidence.json')
    assert set(rank) == {'spectral_fwhm_normal_nm', 'angular_fwhm_450_deg', 'cone5_integral_proxy'}
    for value in rank.values():
        assert value['full_cohort']['n'] == 12
        assert value['full_cohort']['pair_count'] == 66

def test_scope_and_safety():
    scope = read('classification_scope_statement.json')
    transmission = read('transmission_noncomparability_statement.json')
    completion = read('completion_manifest.json')
    assert scope['semantic'] == 'REGRESSION_ELIGIBILITY'
    assert transmission['status'] == 'NOT_NUMERICALLY_COMPARABLE'
    assert completion['solver_calls'] == 0
    assert completion['HF15_reads'] == 0
    assert completion['sealed_test_reads'] == 0
