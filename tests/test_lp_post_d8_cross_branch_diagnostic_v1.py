import json
from pathlib import Path
ROOT=Path(__file__).parents[1]
ML=ROOT / "outputs/lp_ml_dataset_v1"
PLAN=ML/"plans/b120_j2lm06_post_d8_cross_branch_diagnostic_plan_v1.json"
ST=ML/"staging/b120_j2lm06_post_d8_cross_branch_diagnostic_v1"
AN=ML/"analysis"
def test_cross_branch_counts_and_labels():
    p=json.loads(PLAN.read_text()); assert p["candidate_count"]==18
    assert [len([r for r in p["candidates"] if r["group"]==g]) for g in ("PHASE_LOCAL","PROJECTOR_LOCAL","BRIDGE")] == [6,6,6]
    assert len({r["exact_geometry_hash_sha256"] for r in p["candidates"]})==18
    assert len(list(ST.rglob("checkpoint.json")))==36
    assert len(list((ST/"candidates").glob("*.json")))==18
    out=json.loads((AN/"b120_j2lm06_post_d8_cross_branch_outcome_v1.json").read_text())
    assert out["prospective_only"] and out["no_d9_candidate_or_geometry"]
    assert out["historical_hard_gate_preserved"]=="HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE"
    assert out["solver_calls"]==36
