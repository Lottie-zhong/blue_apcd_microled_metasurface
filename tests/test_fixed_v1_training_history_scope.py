from pathlib import Path
import json

ROOT = Path(r'D:\project\worktrees\blue_apcd_mdc_ml_inverse_v1')
OUT = ROOT / 'outputs/mdc_replacement_hf_external_r12_solver_evaluation_v1/20260802T150000Z_R12_SOLVER/promotion_review/training_history_scope'

def read(name): return json.loads((OUT / name).read_text())

def test_contract_and_fit_counts():
    c = read('regression_training_contract_extracted.json')
    assert c['optimizer']['value'] == 'AdamW'
    assert c['batch_size']['value'] == 128
    assert c['max_epochs']['value'] == 240
    assert c['early_stopping_patience']['value'] == 35
    assert read('regression_oof_fit_history.json')['fit_count'] == 12
    assert read('regression_final_training_summary.json')['fit_count'] == 3

def test_unrecorded_history_is_explicit():
    summary = read('regression_oof_training_summary.json')
    assert summary['history_status'] == 'PARTIALLY_UNRECORDED_NO_HISTORY_PERSISTED'
    assert summary['epochs_ran']['min'] == 'NOT_RECORDED'
    final = read('regression_final_training_summary.json')
    assert final['independent_validation'] is False
    classifier = read('classification_training_and_calibration_summary.json')
    assert classifier['epoch'] == 'NOT_APPLICABLE_NO_EPOCH'
    assert len(classifier['calibration_brier_recorded']) == 4

def test_scope_and_safety():
    registry = read('fixed_v1_targetwise_scope_registry.json')
    completion = read('completion_manifest.json')
    assert registry['overall_quantitative_high_fidelity_scope'] == 'REJECTED'
    assert registry['cone5']['rank_only_use'] == 'EXPLORATORY_ELIGIBILITY_ROUTED_ONLY'
    assert completion['new_fits'] == 0
    assert completion['solver_calls'] == 0
    assert completion['HF15_reads'] == 0
    assert completion['sealed_test_reads'] == 0
