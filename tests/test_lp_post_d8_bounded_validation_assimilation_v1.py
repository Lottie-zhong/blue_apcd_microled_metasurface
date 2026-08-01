import csv,json
from pathlib import Path
ROOT=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4"); ML=ROOT/"outputs/lp_ml_dataset_v1"; AN=ML/"analysis"

def read(name): return json.loads((AN/name).read_text())

def test_28_point_assimilation_separates_sources():
    rows=list(csv.DictReader((AN/"b120_j2lm06_post_d8_28unique_assimilated_metrics_v1.csv").open()))
    assert len(rows)==28
    assert sum(r["source_class"]=="ORIGINAL_22_TRAINING_PHYSICS" for r in rows)==22
    assert sum(r["source_class"]=="BOUNDED_6_EXTERNAL_PHYSICS" for r in rows)==6

def test_assimilation_rank_and_drift():
    m=read("b120_j2lm06_post_d8_28unique_quadratic_model_v1.json")
    d=read("b120_j2lm06_post_d8_22_vs_28_model_drift_v1.json")
    assert m["rank"]==10 and m["condition_number"]>0
    assert d["classification"] in {"STABLE_ASSIMILATION","MODERATE_BOUNDARY_UPDATE","ACTIVE_BASIS_ROTATION","HIGHER_ORDER_LACK_OF_FIT"}
    assert d["classification"]=="ACTIVE_BASIS_ROTATION"

def test_primary_replay_and_holdout_are_distinct():
    p=read("b120_j2lm06_post_d8_bounded_primary_external_validation_replay_v1.json")
    h=read("b120_j2lm06_post_d8_28unique_holdout_validation_v1.json")
    assert p["validation_type"]=="PRIMARY_EXTERNAL_VALIDATION"
    assert h["training_error_not_substituted_for_external_error"] is True
    assert p["bounded_count"]==6

def test_full_history_and_readiness():
    ph=read("b120_j2lm06_post_d8_full_history_phase_progress_v1.json")
    r=read("b120_j2lm06_post_d8_d9_readiness_decision_v1.json")
    assert ph["bounded_stage_replaced_global_minimum"] is False
    assert r["readiness_outcome"]=="POSTHOC_MODEL_DRIFT_REQUIRES_MORE_DIAGNOSTIC"
    assert r["d9_candidate_ids"]==[] and r["d9_geometry_created"] is False

def test_route_contract_forbids_execution():
    c=json.loads((ML/"plans/b120_j2lm06_post_d8_d9_readiness_route_contract_v1.json").read_text())
    assert c["route_decision"]=="ROUTE_DECISION_ONLY_NO_CANDIDATE_PLAN"
    assert c["NO_SOLVER_AUTHORIZATION"] is True and c["NO_D9_GEOMETRY"] is True
