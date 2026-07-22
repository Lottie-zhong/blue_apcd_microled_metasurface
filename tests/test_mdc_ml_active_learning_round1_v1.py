from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"outputs"/"mdc_ml_active_learning_round1_v1"
def rows(name): return [json.loads(x) for x in (OUT/name).read_text(encoding="utf-8").splitlines() if x]
def state(selected,labels):
    return "proposal" if len(selected)==128 and len(labels)==0 else "smoke" if len(selected)==128 and len(labels)==8 else "formal_complete" if len(selected)==128 and len(labels)==128 else "invalid"
def test_state_machine_and_membership():
    s=rows("selected_batch_v1.jsonl");l=rows("tmm_labels_v1.jsonl")
    assert state(s,[])=="proposal" and state(s,l[:8])=="smoke" and state(s,l)=="formal_complete"
    assert state(s,l[:7])=="invalid" and state(s,l[:9])=="invalid"
    assert {x["candidate_id"] for x in l}=={x["candidate_id"] for x in s} and len({x["candidate_id"] for x in l})==128
def test_exact_random_and_metadata():
    s=rows("selected_batch_v1.jsonl");f=sorted({x["topology_family"] for x in s})
    assert len(f)==8 and len({x["canonical_geometry_hash"] for x in s})==128 and sum(x["random_control_flag"] for x in s)==16
    assert all(sum(x["random_control_flag"] and x["topology_family"]==q for x in s)==2 for q in f)
    assert all({"selection_mode","selection_reasons","selection_order","random_control_flag","explicit_anchor_flag","family_quota_state","acquisition"}.issubset(x) and "signal_values" in x["acquisition"] and "signal_ranks" in x["acquisition"] for x in s)
def test_formal_labels():
    m=json.loads((OUT/"manifest_v1.json").read_text(encoding="utf-8"));l=rows("tmm_labels_v1.jsonl")
    assert m["candidate_count"]==m["label_count"]==128
    assert all(not x["solver_execution_failure"] and x["nan_inf_audit_pass"] for x in l)
    assert sum(x.get("power_balance_failure",False) for x in l)<=6
