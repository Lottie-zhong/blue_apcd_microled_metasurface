import copy
import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("reconcile_g024_preentry_v1.py")
SPEC = importlib.util.spec_from_file_location("reconcile_g024_preentry_v1", MODULE_PATH)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)

def worker_fixture():
    claim = {
        "schema": "APCD_GPU_RUNNER_V1_SCHEDULED_WORKER_CLAIM_V1",
        "pid": 17032,
        "request_id": M.REQUEST_ID,
        "request_sha256": "0" * 64,
        "task_name": r"\APCD_GPU_RUNNER_V1_SINGLE_CASE_WORKER",
    }
    request_body = {
        "schema": "APCD_GPU_RUNNER_V1_SCHEDULED_REQUEST_V1",
        "request_id": M.REQUEST_ID,
        "identity": {"case_id": M.CASE_ID, "attempt_id": M.ATTEMPT_ID,
                     "run_id": M.OLD_RUN_ID},
        "manifest_path": str(M.ENVELOPE),
        "manifest_sha256": M.file_sha256(M.ENVELOPE),
    }
    request_body["request_sha256"] = M.canonical_sha256(request_body)
    claim["request_sha256"] = request_body["request_sha256"]
    result_body = {
        "schema": "APCD_GPU_RUNNER_V1_SCHEDULED_RESULT_V1",
        "request_id": M.REQUEST_ID,
        "request_sha256": request_body["request_sha256"],
        "claim_sha256": M.canonical_sha256(claim),
        "worker_pid": claim["pid"],
        "exit_code": 2,
        "error": "GPU_RESOURCE_NAME_REQUIRED",
        "run_status": None,
        "solver_entered": False,
    }
    result_body["result_sha256"] = M.canonical_sha256(result_body)
    return request_body, result_body, claim

def ledger_fixture():
    failed = {
        "case_id": M.CASE_ID, "phase": "RUN_ONE", "sequence_index": 36,
        "evidence": {"returncode": 2, "run_log_sha256": "b" * 64,
                     "registry_rows": []},
    }
    record = {
        "attempt_id": M.ATTEMPT_ID, "run_id": M.OLD_RUN_ID,
        "phase": "RUN_ONE_IN_PROGRESS", "sequence_index": 36,
    }
    ledger = {
        "current_case": {"case_id": M.CASE_ID, "phase": "FAILED_OR_ISOLATED",
                         "run_id": M.OLD_RUN_ID, "sequence_index": 36},
        "case_records": {M.CASE_ID: record},
        "failed_or_isolated_cases": [failed],
        "entered_case_ids": ["entered_%02d" % i for i in range(35)],
        "truth_valid_case_ids": ["truth_%02d" % i for i in range(33)],
        "labels_valid_case_ids": ["label_%02d" % i for i in range(33)],
        "entered_count": 35, "truth_valid_count": 33, "labels_valid_count": 33,
        "remaining_unentered_count": 93, "automatic_replay_count": 0,
        "training_fits": 0, "p_scale_fits": 0,
        "confirmation_response_access_count": 0,
    }
    batch = {"current_case": {"case_id": M.CASE_ID, "phase": "RUN_ONE_IN_PROGRESS",
                              "run_id": M.OLD_RUN_ID}}
    status = {
        "schema": "APCD_GPU_RUNNER_V1_QUEUE_CONTROLLER_STATUS_V1",
        "state": "RUNNING", "current_case_id": M.CASE_ID,
        "request_id": M.CONTROLLER_REQUEST_ID,
        "controller_manifest_sha256": M.PINNED_RAW_SHA256[str(M.CONTROLLER_MANIFEST)],
        "queue_id": M.QUEUE_ID, "unresolved_runner_request_ids": [],
        "post_entry_automatic_replays": 0, "resume_generation": 0,
    }
    return ledger, batch, status

def test_canonical_request_result_and_claim_hashes():
    req, result, claim = worker_fixture()
    evidence = M.verify_worker_chain(req, result, claim)
    assert evidence["solver_entered"] is False
    assert evidence["exit_code"] == 2
    assert evidence["request_canonical_sha256"] == req["request_sha256"]
    assert evidence["result_canonical_sha256"] == result["result_sha256"]

def test_rejects_solver_entered_true_even_with_recomputed_result_hash():
    req, result, claim = worker_fixture()
    result["solver_entered"] = True
    body = dict(result)
    body.pop("result_sha256")
    result["result_sha256"] = M.canonical_sha256(body)
    try:
        M.verify_worker_chain(req, result, claim)
    except M.ReconcileError as exc:
        assert str(exc) == "RESULT_NOT_PROVEN_PREENTRY_FAILURE"
    else:
        raise AssertionError("solver_entered=true must be refused")

def test_rejects_wrong_case_identity():
    req, result, claim = worker_fixture()
    req["identity"]["case_id"] = "K6GDP2_DEV_G025"
    body = dict(req)
    body.pop("request_sha256")
    req["request_sha256"] = M.canonical_sha256(body)
    result["request_sha256"] = req["request_sha256"]
    body = dict(result)
    body.pop("result_sha256")
    result["result_sha256"] = M.canonical_sha256(body)
    try:
        M.verify_worker_chain(req, result, claim)
    except M.ReconcileError as exc:
        assert str(exc) == "REQUEST_IDENTITY_INVALID"
    else:
        raise AssertionError("wrong case identity must be refused")

def test_pure_transition_preserves_counters_and_attempt_evidence():
    ledger, batch, status = ledger_fixture()
    original = copy.deepcopy((ledger, batch, status))
    evidence = {
        "run_log_sha256": "b" * 64,
        "runner_request_chain": {"solver_entered": False},
        "artifact_sha256": {"request": "a" * 64},
        "preflight": {"result": "PASS"},
        "fresh_load_readback": {"status": "PASS"},
        "runner_state": {"active_run_exists": False},
    }
    nl, nb, ns = M.build_reconciled_snapshots(
        ledger, batch, status, evidence, "2026-10-07T00:00:00Z")
    assert (ledger, batch, status) == original
    assert M._counter_snapshot(nl) == M._counter_snapshot(ledger)
    assert M.CASE_ID not in nl["case_records"]
    assert M.CASE_ID not in nl["entered_case_ids"]
    preserved = nl["failed_or_isolated_cases"][0]["evidence"]["preentry_reconciliation"]
    assert preserved["prior_case_record"]["attempt_id"] == M.ATTEMPT_ID
    assert preserved["prior_case_record"]["run_id"] == M.OLD_RUN_ID
    assert preserved["same_attempt_remains_unentered"] is True
    assert nb["current_case"] is None
    assert ns["current_case_id"] is None

def test_refuses_case_already_entered():
    ledger, batch, status = ledger_fixture()
    ledger["entered_case_ids"].append(M.CASE_ID)
    ledger["entered_count"] += 1
    try:
        M.build_reconciled_snapshots(ledger, batch, status, {
            "run_log_sha256": "b" * 64, "runner_request_chain": {},
            "artifact_sha256": {}, "preflight": {}, "fresh_load_readback": {},
            "runner_state": {},
        }, "2026-10-07T00:00:00Z")
    except M.ReconcileError as exc:
        assert str(exc) == "LEDGER_COUNTS_OUTSIDE_G024_SNAPSHOT"
    else:
        raise AssertionError("entered case must be refused")

def test_refuses_other_inflight_case():
    ledger, batch, status = ledger_fixture()
    batch["current_case"]["case_id"] = "K6GDP2_DEV_G025"
    try:
        M.build_reconciled_snapshots(ledger, batch, status, {
            "run_log_sha256": "b" * 64, "runner_request_chain": {},
            "artifact_sha256": {}, "preflight": {}, "fresh_load_readback": {},
            "runner_state": {},
        }, "2026-10-07T00:00:00Z")
    except M.ReconcileError as exc:
        assert str(exc) == "BATCH_CURRENT_POINTER_NOT_G024"
    else:
        raise AssertionError("other inflight case must be refused")

def test_frozen_queue_manifest_uses_ordered_case_ids():
    queue_manifest = {"ordered_case_ids": [M.CASE_ID, "K6GDP2_DEV_G025"]}
    controller = {"case_ids": [M.CASE_ID, "K6GDP2_DEV_G025"]}
    M.validate_queue_membership(queue_manifest, controller)

def test_queue_manifest_rejects_non_authoritative_case_ids_alias():
    queue_manifest = {"case_ids": [M.CASE_ID]}
    controller = {"case_ids": [M.CASE_ID]}
    try:
        M.validate_queue_membership(queue_manifest, controller)
    except M.ReconcileError as exc:
        assert str(exc) == "G024_NOT_IN_FROZEN_QUEUE_MANIFEST"
    else:
        raise AssertionError("non-authoritative queue key must be refused")
