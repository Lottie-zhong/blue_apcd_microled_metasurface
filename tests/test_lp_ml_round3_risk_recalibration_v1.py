import csv, json
from pathlib import Path

ROOT=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
O=ROOT/'outputs/lp_ml_dataset_v1'; A=O/'analysis'; P=O/'plans'; SEARCH=P/'lp_ml_six_bin_inverse_search_round3_v1'
def rd(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def test_frozen_sources_and_accounting():
    audit=json.loads(A.joinpath('lp_ml_round3_accounting_audit_v1.json').read_text())
    assert set(['planned','entered','unique','duplicate','accepted','complete_geometries','admitted_rows']).issubset(audit)
    assert (audit['entered'],audit['unique'],audit['duplicate'],audit['accepted'],audit['complete_geometries'],audit['admitted_rows'])==(127,126,1,121,58,522)
    assert audit['solver_calls']==0 and audit['duplicate_preserved'] is True

def test_forensic_cohort_and_causes():
    f=json.loads(A.joinpath('lp_ml_round3_low_dispersion_high_error_forensic_v1.json').read_text())
    assert f['row_count']==27 and len(f['rows'])==27
    assert set(x['primary_failure_class'] for x in f['rows']) <= set(f['classification_enums'])

def test_calibration_is_nontrivial_and_held_out():
    e=json.loads(A.joinpath('lp_ml_round3_risk_calibration_evaluation_v1.json').read_text())
    c=e['cross_validation']
    assert c['calibrated_rank_correlation']>c['dispersion_only_rank_correlation']
    assert c['calibrated_high_error_low_risk_count']<c['dispersion_only_high_error_low_risk_count']
    assert len(c['calibrated_risk_classes'])==3
    assert e['frozen_tests_used_for_tuning'] is False and e['solver_calls']==0

def test_rescored_pool_and_tuple_front_identity():
    r=rd(A/'lp_ml_round3_recalibrated_508_candidate_table_v1.csv')
    assert len(r)==508 and len({x['candidate_id'] for x in r})==508
    assert len({x['calibrated_risk_class'] for x in r})==3
    t=json.loads((SEARCH/'lp_ml_six_bin_recalibrated_tuple_front_v1.json').read_text())
    assert t['tuple_count']==103 and len(t['top_tuples'])==103 and t['solver_calls']==0
    assert all(len(x['candidate_ids'])==6 and x['all_bins_covered'] for x in t['top_tuples'])

def test_route_has_no_solver_or_round4_execution():
    a=json.loads(A.joinpath('lp_ml_round3_round4_need_assessment_v1.json').read_text())
    assert a['outcome']=='LP_ML_ROUND3_RECALIBRATED_POOL_READY_FOR_INVERSE_FDTD_PLANNING'
    assert a['solver_calls']==0 and a['no_solver_authorization'] is True
    assert a['round4_plan_path'] is None
