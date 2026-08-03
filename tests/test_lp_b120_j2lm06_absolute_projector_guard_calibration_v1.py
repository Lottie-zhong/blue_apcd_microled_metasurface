from pathlib import Path
import csv, json
ROOT=Path(__file__).resolve().parents[1]
AN=ROOT/"outputs/lp_ml_dataset_v1/analysis"; PL=ROOT/"outputs/lp_ml_dataset_v1/plans"
def j(n): return json.loads((AN/n).read_text(encoding="utf-8"))
def test_guard_outcome_and_solver_zero():
    s=j("b120_j2lm06_projector_guard_execution_summary_v1.json")
    assert s["outcome"]=="PROJECTOR_GUARD_CONTRACT_NOT_IDENTIFIABLE" and s["solver_calls"]==0 and s["batch_a_calibration_leakage"]==0
def test_metric_contract_semantics():
    c=j("b120_j2lm06_projector_guard_metric_definition_contract_v1.json")
    assert c["definitions"]["combined_leakage"]=="Tyy + Txy + Tyx (formal row convention)"
    assert c["formula_audit"]["projection_error_formula_identifiable"] is False
    assert c["observable"]["wavelength_nm"]==450 and c["observable"]["material"]=="APCD_TIO2_NATIVE_M1"
def test_cohorts_and_batch_a_exclusion():
    rows=list(csv.DictReader((AN/"b120_j2lm06_projector_guard_historical_cohort_manifest_v1.csv").open(encoding="utf-8-sig")))
    assert len(rows)==22 and sum(r["cohort"]=="positive_core" for r in rows)==5 and sum(r["cohort"]=="negative_core" for r in rows)==11 and sum(r["cohort"]=="positive_supporting" for r in rows)==6
    assert all(r["calibration_role"]!="CALIBRATION_CORE" or r["source_stage"]!="POST_D8_BOUNDED_PRE_BATCH_A" for r in rows)
def test_threshold_identifiability_and_layers():
    a=j("b120_j2lm06_projector_guard_threshold_identifiability_audit_v1.json")
    assert a["batch_a_excluded"] is True and a["identifiability"]["absolute_quality_thresholds"] is False
    p=j("b120_j2lm06_projector_guard_absolute_contract_proposal_v1.json")
    assert p["status"]=="EVIDENCE_GAP_NOT_FROZEN" and p["layer3_local_continuation"]["status"]=="FROZEN_FOR_RELATIVE_CONTINUATION_ONLY"
def test_holdout_and_d9():
    h=j("b120_j2lm06_batch_a_holdout_projector_guard_evaluation_v1.json")
    assert h["holdout_count"]==4 and h["calibration_leakage"]==0 and all(r["holdout_verdict"]=="PROJECTOR_GUARD_REMAINS_INDETERMINATE" for r in h["rows"])
    q=json.loads((PL/"b120_j2lm06_d9_phase_local_final_for_approval_or_evidence_gap_v1.json").read_text(encoding="utf-8"))
    assert q["status"]=="CONTRACT_EVIDENCE_GAP" and q["candidate_count"]==0 and q["solver_authorized"] is False
def test_historical_gate_preserved():
    s=j("b120_j2lm06_projector_guard_source_audit_v1.json")
    assert s["historical_hard_gate_preserved"] is True and s["canonical_modified"] is False
