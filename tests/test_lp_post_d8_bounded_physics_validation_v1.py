import json
from pathlib import Path

ROOT=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
ML=ROOT/"outputs/lp_ml_dataset_v1"
ST=ML/"staging/b120_j2lm06_post_d8_bounded_physics_validation_v1"
IDS=["POSTD8_BOUNDED_PROJECTOR_03","POSTD8_BOUNDED_PROJECTOR_04","POSTD8_BOUNDED_PHASE_01","POSTD8_BOUNDED_PHASE_02","POSTD8_BOUNDED_DIAG_05","POSTD8_BOUNDED_DIAG_06"]

def test_exact_candidate_order_and_subruns():
    plan=json.loads((ML/"plans/b120_j2lm06_post_d8_dual_anchor_bounded_candidate_plan_v1.json").read_text())
    assert {x["candidate_id"] for x in plan["candidates"]}==set(IDS)
    assert [x["candidate_id"] for x in plan["candidates"]]==["POSTD8_BOUNDED_PHASE_01","POSTD8_BOUNDED_PHASE_02","POSTD8_BOUNDED_PROJECTOR_03","POSTD8_BOUNDED_PROJECTOR_04","POSTD8_BOUNDED_DIAG_05","POSTD8_BOUNDED_DIAG_06"]
    assert sum(1 for _ in ST.glob("subruns/*/*/checkpoint.json"))==12

def test_batch_gate_and_outcome():
    gate=json.loads((ML/"analysis/b120_j2lm06_post_d8_bounded_batch1_gate_v1.json").read_text())
    out=json.loads((ML/"analysis/b120_j2lm06_post_d8_bounded_outcome_v1.json").read_text())
    assert gate["outcome"]=="BATCH1_GATE_PASS_CONTINUE_BATCH2"
    assert out["outcome"]=="BOUNDED_PHASE_AND_PROJECTOR_VALIDATED"

def test_prediction_physics_separation():
    for p in (ST/"candidates").glob("*.json"):
        x=json.loads(p.read_text())
        assert x["physics_label"]=="FORMAL_ACCEPTED_WEIGHTED_G0"
        assert x["prediction_label"]=="MODEL_PREDICTION_NOT_PHYSICS_LABEL"

def test_no_d9_and_solver_accounting():
    a=json.loads((ML/"analysis/b120_j2lm06_post_d8_bounded_solver_accounting_v1.json").read_text())
    assert a["raw_solver_invocations"]==12 and a["wavelength_nm"]==[450]
    assert not any("d9" in p.name.lower() for p in (ML/"staging").glob("b120_j2lm06_post_d9*") )
