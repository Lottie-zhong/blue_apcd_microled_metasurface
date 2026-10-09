"""Regression coverage for Runner-generic failed post-entry closeouts."""

from copy import deepcopy

import pytest

from scripts.coupling_ml.k6_v2_pipeline import serial_queue as sq


CASE_ID = "K6GDP2_DEV_G026"
RUN_ID = "K6V2_G026_TEST_RUN"
REQUEST_ID = "42d15429cb67170e7a515dfe0078edeb"


def _fixture():
    evidence = {
        "case_id": CASE_ID,
        "attempt_id": "attempt_001",
        "run_id": RUN_ID,
        "phase": "FAILED_POSTENTRY_NO_TRUTH",
        "entry_consumed": True,
        "solver_invocations": 1,
        "automatic_replay_count": 0,
        "truth_available": False,
        "quarantine": True,
        "failure": "RunnerError:LICENSE_STARTUP_FAILED",
        "runner_request_id": REQUEST_ID,
        "runner_closeout_schema": "APCD_GPU_RUNNER_V1_POSTENTRY_FAILURE_CLOSEOUT_RECEIPT_V1",
        "postentry_closeout_receipt_file_sha256": "a" * 64,
        "postentry_closeout_receipt_sha256": "b" * 64,
        "runner_status_sha256": "c" * 64,
        "run_envelope_sha256": "d" * 64,
    }
    current = {
        "case_id": CASE_ID,
        "run_id": RUN_ID,
        "sequence_index": 38,
        "phase": "FAILED_OR_ISOLATED",
    }
    record = {
        "attempt_id": "attempt_001",
        "run_id": RUN_ID,
        "sequence_index": 38,
        "phase": "RUN_ONE_IN_PROGRESS",
        "run_envelope_sha256": "d" * 64,
    }
    ledger = {
        "entered_count": 1,
        "truth_valid_count": 0,
        "labels_valid_count": 0,
        "remaining_unentered_count": 0,
        "entered_case_ids": [CASE_ID],
        "truth_valid_case_ids": [],
        "labels_valid_case_ids": [],
        "remaining_unentered_case_ids": [],
        "failed_or_isolated_cases": [],
        "case_records": {CASE_ID: record},
        "current_case": current,
        "automatic_replay_count": 0,
        "training_fits": 0,
        "p_scale_fits": 0,
        "confirmation_response_access_count": 0,
    }
    return ledger, current, evidence


def test_generic_closeout_route_is_schema_based(monkeypatch):
    expected = {"case_id": CASE_ID, "runner_closeout_schema": "generic"}
    monkeypatch.setattr(sq, "verify_runner_generic_postentry_closeout",
                        lambda row, cid: expected)
    assert sq.verify_failed_postentry_closeout({"case_id": CASE_ID}, CASE_ID) == expected


def test_generic_closeout_terminalizes_without_changing_budget_counts(monkeypatch):
    ledger, current, evidence = _fixture()
    monkeypatch.setattr(sq, "now", lambda: "2026-10-09T00:00:00Z")
    before = {key: ledger[key] for key in (
        "entered_count", "truth_valid_count", "labels_valid_count",
        "remaining_unentered_count", "automatic_replay_count",
        "training_fits", "p_scale_fits", "confirmation_response_access_count")}

    sq.record_generic_failed_postentry_recovery(ledger, current, evidence)
    sq._assert_failed_postentry_recorded(ledger, evidence)

    assert ledger["current_case"] is None
    assert ledger["case_records"][CASE_ID]["phase"] == "FAILED_POSTENTRY_NO_TRUTH"
    assert CASE_ID in ledger["entered_case_ids"]
    assert CASE_ID not in ledger["truth_valid_case_ids"]
    assert CASE_ID not in ledger["labels_valid_case_ids"]
    assert {key: ledger[key] for key in before} == before


def test_generic_closeout_rejects_replay_or_missing_quarantine():
    ledger, current, evidence = _fixture()
    evidence["automatic_replay_count"] = 1
    with pytest.raises(sq.StopQueue, match="GENERIC_POSTENTRY_EVIDENCE_INVALID"):
        sq.record_generic_failed_postentry_recovery(ledger, current, evidence)
    assert ledger["current_case"] is current


def test_generic_closeout_rejects_non_development_case():
    with pytest.raises(sq.StopQueue, match="OUTSIDE_DEVELOPMENT_SCOPE"):
        sq.verify_failed_postentry_closeout({}, "K6GDP2_CONFIRM_G001")


def test_git_source_hash_accepts_line_ending_only_checkout_conversion():
    import hashlib

    git_bytes = b"\xef\xbb\xbf# test\nprint('ok')\n"
    windows_checkout = git_bytes.replace(b"\n", b"\r\n")
    accepted = sq._git_source_serialized_hashes(git_bytes)
    assert hashlib.sha256(git_bytes).hexdigest() in accepted
    assert hashlib.sha256(windows_checkout).hexdigest() in accepted
    changed_content = windows_checkout.replace(b"print", b"raise")
    assert hashlib.sha256(changed_content).hexdigest() not in accepted


def test_reconcile_self_process_filter_excludes_only_verified_current_cli():
    script = str(sq.Path(sq.__file__).resolve())
    request_id = "bb93248ca2dff9605d7885554a319394"
    own = {
        "ProcessId": 1234,
        "CommandLine": f'"python.exe" "{script}" --reconcile-generic-postentry-only '
                       f'--runner-controller-request-id {request_id}',
    }
    other_controller = {
        "ProcessId": 1235,
        "CommandLine": f'"python.exe" "{script}" --execute',
    }
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(sq.os, "getpid", lambda: 1234)
        monkeypatch.setattr(sq.sys, "argv", [
            script, "--reconcile-generic-postentry-only",
            "--runner-controller-request-id", request_id,
        ])
        kept = sq._exclude_verified_current_reconciler_process(
            [own, other_controller], request_id)
        assert kept == [other_controller]
    finally:
        monkeypatch.undo()


def test_reconcile_self_process_filter_fails_closed_on_mismatched_request(monkeypatch):
    script = str(sq.Path(sq.__file__).resolve())
    request_id = "bb93248ca2dff9605d7885554a319394"
    own = {
        "ProcessId": 1234,
        "CommandLine": f'"python.exe" "{script}" --reconcile-generic-postentry-only '
                       f'--runner-controller-request-id {request_id}',
    }
    monkeypatch.setattr(sq.os, "getpid", lambda: 1234)
    monkeypatch.setattr(sq.sys, "argv", [
        script, "--reconcile-generic-postentry-only",
        "--runner-controller-request-id", request_id,
    ])
    with pytest.raises(Exception, match="SELF_REQUEST_IDENTITY"):
        sq._exclude_verified_current_reconciler_process([own], "other-request-id")


def test_postentry_queue_manifest_checks_canonical_and_runner_raw_hashes(tmp_path):
    import json

    queue_path = tmp_path / "queue.json"
    queue = {
        "schema": "QUEUE_TEST",
        "ordered_case_ids": ["K6GDP2_DEV_G027"],
    }
    queue["queue_manifest_sha256"] = sq.runner_canonical_sha(queue)
    queue_path.write_text(json.dumps(queue, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    runner_manifest = {
        "queue_manifest_path": str(queue_path),
        "queue_manifest_sha256": sq.sha(queue_path),
    }
    assert sq._verify_postentry_queue_manifest_binding(
        queue, runner_manifest, queue_path) == queue["queue_manifest_sha256"]
    runner_manifest["queue_manifest_sha256"] = queue["queue_manifest_sha256"]
    with pytest.raises(Exception, match="RUNNER_QUEUE_FILE_HASH_MISMATCH"):
        sq._verify_postentry_queue_manifest_binding(queue, runner_manifest, queue_path)


def test_controller_resume_receipt_path_preserves_prior_generations(tmp_path):
    import json

    request_id = "bb93248ca2dff9605d7885554a319394"
    status_path = tmp_path / "status.json"
    status_path.write_text(json.dumps({"request_id": request_id, "resume_generation": 4}),
                           encoding="utf-8")
    legacy = status_path.with_name("resume_receipt_" + request_id + ".json")
    legacy.write_text("legacy-generation-4", encoding="utf-8")
    controller = {"status_path": status_path, "request_id": request_id}
    expected = status_path.with_name(
        "resume_receipt_" + request_id + "_generation_5.json")
    assert sq.controller_resume_receipt_path(controller) == expected
    assert legacy.read_text(encoding="utf-8") == "legacy-generation-4"
    expected.write_text("new-generation-5", encoding="utf-8")
    assert sq.controller_resume_receipt_path(controller) == expected
