from pathlib import Path
import json
import pytest

ROOT=Path(__file__).parents[1]
OUT=ROOT/'outputs/mdc_hf_surrogate_v2_test40_selection_conflict_resolution_v1/20260808T_test40_selection_conflict_resolution_489b54e'

def _load(name):
    p=OUT/name
    if not p.exists(): pytest.skip(f'missing runtime artifact: {name}')
    return json.loads(p.read_text(encoding='utf-8'))

def test_test40_case_identity_and_solver_completion():
    m=_load('test40_solver_run_manifest.json')
    assert m['case_identity']=='test_case_uid'
    assert m['authorized_unique_physical_cases']==240
    assert m['completed_unique_physical_cases']==240
    assert m['counters']['fdtd_lumerical_calls']==240
    assert m['counters']['solver_calls']==240

def test_test40_forbidden_reads_and_replay():
    c=_load('test40_external_evaluation_counters_v1.json')
    r=_load('test40_extraction_reproducibility_audit.json')
    assert c['HF15_formal_label_reads']==0
    assert c['HF15_diagnostics_reads']==0
    assert c['sealed_test_reads']==0
    assert c['TMM_calls']==0 and c['RCWA_calls']==0 and c['NP_solver_calls']==0
    assert r['status']=='PASS'

def test_test40_scope_is_explicit_and_prediction_prelabel_audit_is_blind():
    m=_load('test40_external_evaluation_metrics_v1.json')
    a=_load('test40_prediction_before_label_audit.json')
    assert m['scope_decision'] in {'MDC_HF_SURROGATE_V2_TEST40_QUANTITATIVE_PROFILE_ACCEPTED','MDC_HF_SURROGATE_V2_TEST40_RANKING_SCREENING_ONLY','MDC_HF_SURROGATE_V2_TEST40_EXPLORATORY_NP_COUPLING_ONLY','MDC_HF_SURROGATE_V2_TEST40_EXTERNAL_GENERALIZATION_REJECTED'}
    assert a['labels_read']==0
