import importlib.util
from pathlib import Path

import pytest

HELPER_PATH = (Path(__file__).resolve().parents[3]
               / "scripts/coupling_ml/k6_v2_pipeline/reconcile_controller_preentry_exit.py")
_spec = importlib.util.spec_from_file_location("controller_preentry_reconcile_tested", HELPER_PATH)
helper = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(helper)


def _fixture():
    req, cid = "a" * 32, "K6GDP2_DEV_G025"
    entered = [f"historical-{i:03d}" for i in range(36)]
    truth = entered[:33]
    pointer = {"case_id": cid, "sequence_index": 37,
               "phase": "ENSURE_CURRENT_ROUTE_AND_PREFLIGHT"}
    controller = {"request_id": req, "manifest_sha256": "b" * 64,
        "queue_id": "queue-test", "case_ids": [cid, "K6GDP2_DEV_G026"]}
    status = {"request_id": req, "controller_manifest_sha256": "b" * 64,
        "queue_id": "queue-test", "state": "RUNNING", "startup_reconciled": True,
        "current_case_id": cid, "runner_request_ids": [],
        "unresolved_runner_request_ids": [], "post_entry_automatic_replays": 0}
    ledger = {"authorized_development_case_count": 128, "entered_count": 36,
        "truth_valid_count": 33, "labels_valid_count": 33, "remaining_unentered_count": 92,
        "entered_case_ids": entered, "truth_valid_case_ids": truth,
        "labels_valid_case_ids": list(truth), "automatic_replay_count": 0,
        "training_fits": 0, "p_scale_fits": 0, "confirmation_response_access_count": 0,
        "case_records": {}, "failed_or_isolated_cases": [], "current_case": dict(pointer)}
    batch = {"current_case": dict(pointer)}
    kwargs = {"attempt_directory_exists": False, "active_run_exists": False,
        "runner_lock_exists": False, "run_envelopes": [], "scheduled_run_requests": [],
        "related_processes": [], "task_state": "Ready", "scheduler_last_result": 2}
    return controller, status, ledger, batch, kwargs


def test_valid_preentry_exit_preserves_unentered_case():
    c, s, l, b, kw = _fixture()
    result = helper.validate_preentry_candidate(c, s, l, b, [], **kw)
    assert result == {"case_id": "K6GDP2_DEV_G025", "attempt_id": "attempt_001",
        "sequence_index": 37, "entry_consumed": False, "solver_invocations": 0,
        "automatic_replay_count": 0, "truth_available": False}


def test_live_entry_gate_batch_pointer_is_still_preentry_before_run_one():
    c, s, l, b, kw = _fixture()
    b["current_case"]["phase"] = "LIVE_ENTRY_GATE"
    result = helper.validate_preentry_candidate(c, s, l, b, [], **kw)
    assert result == {"case_id": "K6GDP2_DEV_G025", "attempt_id": "attempt_001",
        "sequence_index": 37, "entry_consumed": False, "solver_invocations": 0,
        "automatic_replay_count": 0, "truth_available": False}


def test_live_entry_gate_with_run_id_is_not_reconciled_as_preentry():
    c, s, l, b, kw = _fixture()
    b["current_case"].update({"phase": "LIVE_ENTRY_GATE", "run_id": "unexpected-run"})
    with pytest.raises(RuntimeError, match="PREENTRY_QUEUE_POINTER_IDENTITY_INVALID"):
        helper.validate_preentry_candidate(c, s, l, b, [], **kw)


def test_preentry_interruptions_are_unique_per_resume_generation():
    history = [{"request_id": "a" * 32, "case_id": "K6GDP2_DEV_G025",
                "entry_consumed": False}]
    assert helper.has_interruption_generation(history, "a" * 32, 0)
    assert not helper.has_interruption_generation(history, "a" * 32, 1)
    history.append({"request_id": "a" * 32, "resume_generation": 1})
    assert helper.has_interruption_generation(history, "a" * 32, 1)
    assert not helper.has_interruption_generation(history, "a" * 32, 2)


@pytest.mark.parametrize("field,value", [
    ("registry_rows", [{"case_id": "K6GDP2_DEV_G025"}]),
    ("attempt_directory_exists", True), ("active_run_exists", True),
    ("runner_lock_exists", True), ("run_envelopes", ["run-envelope.json"]),
    ("scheduled_run_requests", [{"request_id": "run-one"}]),
    ("related_processes", [{"process_id": "123"}]),
])
def test_any_run_one_or_slot_evidence_blocks_reconciliation(field, value):
    c, s, l, b, kw = _fixture()
    registry = value if field == "registry_rows" else []
    if field != "registry_rows":
        kw[field] = value
    with pytest.raises(RuntimeError, match="PREENTRY_RUN_ONE_OR_SLOT_EVIDENCE_PRESENT"):
        helper.validate_preentry_candidate(c, s, l, b, registry, **kw)


def test_wrong_phase_cannot_be_cleared_as_preentry():
    c, s, l, b, kw = _fixture()
    l["current_case"]["phase"] = "RUN_ONE_IN_PROGRESS"
    with pytest.raises(RuntimeError, match="PREENTRY_QUEUE_POINTER_IDENTITY_INVALID"):
        helper.validate_preentry_candidate(c, s, l, b, [], **kw)


def test_already_counted_case_cannot_be_reconciled_as_unentered():
    c, s, l, b, kw = _fixture()
    l["entered_case_ids"].append("K6GDP2_DEV_G025")
    l["entered_count"] += 1
    l["remaining_unentered_count"] -= 1
    with pytest.raises(RuntimeError, match="PREENTRY_CASE_NOT_FIRST_UNENTERED"):
        helper.validate_preentry_candidate(c, s, l, b, [], **kw)
