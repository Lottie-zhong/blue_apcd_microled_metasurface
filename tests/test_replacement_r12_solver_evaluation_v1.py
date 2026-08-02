from pathlib import Path
import json

ROOT = Path(r'D:\project\worktrees\blue_apcd_mdc_ml_inverse_v1')
OUT = ROOT / 'outputs/mdc_replacement_hf_external_r12_solver_evaluation_v1/20260802T150000Z_R12_SOLVER'

def read(name):
    return json.loads((OUT / name).read_text())

def test_solver_completion_and_batch_gates():
    m = read('completion_manifest.json')
    assert m['completed_unique_physical_cases'] == 72
    assert m['accepted_cases'] == 72
    assert m['rejected_cases'] == 0
    gates = read('solver_batch_gate.json')
    assert gates['R4']['accepted_case_count'] == 24
    assert gates['R8']['accepted_case_count'] == 48
    assert gates['R12']['accepted_case_count'] == 72
    assert all(v['monitor_completeness'] == 1.0 and v['post_fsp_fresh_load'] == 1.0 for v in gates.values())

def test_labels_and_metric_replay():
    m = read('completion_manifest.json')
    assert m['geometry_label_rows'] == 12
    assert m['case_diagnostic_rows'] == 72
    assert m['metric_replay_identical'] is True
    assert read('replacement_metric_sha.json')['identical'] is True
    quality = read('replacement_r12_label_quality_audit_v1.json')
    assert quality['geometry_rows'] == 12 and quality['case_rows'] == 72

def test_safety_counters_and_scope():
    m = read('completion_manifest.json')
    assert m['HF15_formal_reads'] == 0
    assert m['HF15_diagnostics_reads'] == 0
    assert m['sealed_test_reads'] == 0
    assert m['new_regression_fits'] == 0 and m['new_classification_fits'] == 0
    assert m['TMM_calls'] == 0 and m['RCWA_calls'] == 0
    full = read('replacement_full_cohort_metrics.json')
    routed = read('replacement_routed_metrics.json')
    for target, row in full.items():
        assert row['n'] == 12
        assert 0.0 <= row['observed_conformal_inclusion_rate'] <= 1.0
        assert routed[target]['n'] <= 12
