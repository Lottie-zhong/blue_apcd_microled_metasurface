from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_SPEC = importlib.util.spec_from_file_location(
    "k6_v2_serial_queue_test_module", _ROOT / "scripts/coupling_ml/k6_v2_pipeline/serial_queue.py")
sq = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sq)


def _json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return path


def _canonical_sha(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _closeout_fixture(tmp_path, monkeypatch):
    case_id = "K6LDA1_DEV_D6_M05"
    attempt_id = "attempt_001"
    run_id = "K6V2_D6M05_20261005T182728Z_92041df6"
    fence = "fixture-fence"
    runner_root, report = tmp_path / "runner", tmp_path / "report"
    monkeypatch.setattr(sq, "RUN_ROOT", runner_root)
    monkeypatch.setattr(sq, "REPORT", report)
    run = runner_root / "runs" / case_id / attempt_id / run_id
    run.mkdir(parents=True)
    _json(run / "validation.json", {"state": "PENDING"})
    _json(run / "hashes.json", {"state": "PENDING"})
    manifest = _json(run / "manifest.json", {"fixture": True})
    h5 = run / "run" / "run_output.h5"
    h5.parent.mkdir(parents=True)
    h5.write_bytes(b"coordinate-only fixture")
    target = {"case_id": case_id, "attempt_id": attempt_id, "run_id": run_id}
    input_hashes = {"manifest": sq.sha(manifest), "status": "1" * 64}
    claim_body = {"schema": "APCD_GPU_RUNNER_D6_M05_ORPHAN_CLOSEOUT_V1_RECOVERY_FENCE",
                  "target": target, "recovery_fence_id": fence, "input_hashes": input_hashes}
    claim_sha = _canonical_sha(claim_body)
    closeout = run / "postentry_closeout_v1"
    _json(closeout / "claim.json", dict(claim_body, claim_sha256=claim_sha))
    truth = {"truth_available": False, "truth_valid_case": False, "labels_valid_case": False,
             "validation_state": "PENDING", "hashes_state": "PENDING", "candidate_truth_artifacts": [],
             "non_coordinate_dataset_paths": [], "h5_path": str(h5), "h5_sha256": sq.sha(h5)}
    disposition = {"schema": "APCD_GPU_RUNNER_D6_M05_ORPHAN_CLOSEOUT_V1_DISPOSITION",
        "case_id": case_id, "attempt_id": attempt_id, "run_id": run_id,
        "disposition": "FAILED_POSTENTRY_NO_TRUTH", "claim_sha256": claim_sha,
        "recovery_fence_id": fence, "entry_consumed": True, "solver_invocations": 1,
        "automatic_replay_count": 0, "truth_available": False, "training_admitted": False,
        "scientific_valid": False, "input_hashes": input_hashes, "truth_evidence": truth}
    disposition_path = _json(closeout / "disposition.json", disposition)
    disposition_sha = sq.sha(disposition_path)
    status = {"case_id": case_id, "attempt_id": attempt_id, "run_id": run_id,
        "state": "FAILED_POSTENTRY", "solver_entered": True, "solver_invocations": 1,
        "failure": "ORPHAN_POSTENTRY_NO_TRUTH_EXIT_REASON_UNKNOWN",
        "postentry_closeout_v1": {"schema": "APCD_GPU_RUNNER_D6_M05_ORPHAN_CLOSEOUT_V1",
            "disposition_sha256": disposition_sha, "recovery_fence_id": fence,
            "entry_consumed": True, "truth_available": False, "automatic_replay_count": 0}}
    status_path = _json(run / "status.json", status)
    status_sha = sq.sha(status_path)
    control = {"health_status": "PASS", "new_entry_hold": 0, "active_hold_count": 0}
    events = [
        ("PREPARED", {"claim_sha256": claim_sha, "recovery_fence_id": fence}),
        ("DISPOSITION_WRITTEN", {"disposition_sha256": disposition_sha, "recovery_fence_id": fence}),
        ("STATUS_TERMINALIZATION_INTENT", {"from": "SOLVER_ENTERED", "to": "FAILED_POSTENTRY", "disposition_sha256": disposition_sha, "recovery_fence_id": fence}),
        ("STATUS_TERMINALIZED", {"status_sha256": status_sha, "disposition_sha256": disposition_sha, "solver_invocations": 1, "automatic_replay_count": 0}),
        ("REGISTRY_TERMINALIZATION_INTENT", {"status_sha256": status_sha, "disposition_sha256": disposition_sha, "recovery_fence_id": fence}),
        ("REGISTRY_TERMINALIZED", {"registry_sha256": "2" * 64, "disposition_sha256": disposition_sha, "solver_invocations": 1, "automatic_replay_count": 0}),
        ("RELEASE_READY", {"identity": target, "control_snapshot": control,
            "process_snapshot": {"available": True, "live_related": []},
            "truth_snapshot": {"truth_available": False, "truth_valid_case": False, "labels_valid_case": False}}),
        ("ACTIVE_MARKER_RELEASED", {"marker": "active_run.json", "result": "ARCHIVED"}),
        ("LOCK_RELEASE_INTENT", {"status_sha256": status_sha, "registry_sha256": "2" * 64}),
        ("LOCK_RELEASED", {"marker": ".runner.lock", "result": "ARCHIVED", "registry_target_state": "FAILED_POSTENTRY",
            "solver_entry_count": 1, "automatic_replay_count": 0, "status_sha256": status_sha}),
    ]
    records, previous = [], None
    for sequence, (event, payload) in enumerate(events, 1):
        body = {"sequence": sequence, "event": event, "payload": payload,
                "recorded_utc": "2026-10-06T00:00:00Z", "previous_record_sha256": previous}
        previous = _canonical_sha(body)
        records.append(dict(body, record_sha256=previous))
    journal = {"schema": "APCD_GPU_RUNNER_D6_M05_ORPHAN_CLOSEOUT_V1_HASH_CHAIN",
               "claim_sha256": claim_sha, "records": records, "chain_head_sha256": previous}
    journal_path = _json(closeout / "journal.json", journal)
    monkeypatch.setattr(sq, "FAILED_POSTENTRY_AUTHORITY", {
        "case_id": case_id, "attempt_id": attempt_id, "run_id": run_id,
        "disposition_sha256": disposition_sha, "journal_sha256": sq.sha(journal_path),
        "claim_sha256": claim_sha, "recovery_fence_id": fence})
    row = {"case_id": case_id, "attempt_id": attempt_id, "run_id": run_id, "run_dir": str(run),
        "state": "FAILED_POSTENTRY", "solver_invocations": 1, "automatic_replay_count": 0,
        "postentry_disposition_sha256": disposition_sha, "postentry_closeout_fence_id": fence}
    return row, case_id, run


def test_verified_closeout_consumes_entry_without_truth_or_replay(tmp_path, monkeypatch):
    row, cid, _ = _closeout_fixture(tmp_path, monkeypatch)
    result = sq.verify_failed_postentry_closeout(row, cid)
    assert result["entry_consumed"] and not result["truth_available"]
    assert result["automatic_replay_count"] == 0 and result["runner_slot_released"]


def test_closeout_rejects_wrong_run_and_tampered_journal(tmp_path, monkeypatch):
    row, cid, run = _closeout_fixture(tmp_path, monkeypatch)
    with pytest.raises(sq.StopQueue, match="FAILED_POSTENTRY_IDENTITY_MISMATCH"):
        sq.verify_failed_postentry_closeout(dict(row, run_id="wrong-run"), cid)
    (run / "postentry_closeout_v1" / "journal.json").write_text("{}", encoding="utf-8")
    with pytest.raises(sq.StopQueue, match="CLOSEOUT_FILE_SHA_MISMATCH"):
        sq.verify_failed_postentry_closeout(row, cid)


def test_historical_closeout_allows_other_active_identity_but_not_failed_run(tmp_path, monkeypatch):
    row, cid, run = _closeout_fixture(tmp_path, monkeypatch)
    runner_root = run.parents[3]
    active = {"case_id": "K6LDA1_DEV_D6_P05", "attempt_id": "attempt_001",
              "run_id": "K6V2_D6P05_CURRENT", "state": "SOLVER_ENTERED"}
    _json(runner_root / "active_run.json", active)
    _json(runner_root / ".runner.lock", active)
    assert sq.verify_failed_postentry_closeout(row, cid)["runner_slot_released"]
    failed = dict(active, case_id=cid, run_id=row["run_id"])
    _json(runner_root / "active_run.json", failed)
    _json(runner_root / ".runner.lock", failed)
    with pytest.raises(sq.StopQueue, match="FAILED_POSTENTRY_CURRENT_SLOT_STILL_POINTS_TO_FAILED_RUN"):
        sq.verify_failed_postentry_closeout(row, cid)


def test_reconcile_counts_verified_failure_as_entered_not_done(tmp_path, monkeypatch):
    initial = ("INIT_A", "INIT_B", "INIT_C")
    cid = "K6LDA1_DEV_D6_M05"
    ids = list(initial) + [cid, "K6LDA1_DEV_D6_P05"]
    root = tmp_path / "runner"
    monkeypatch.setattr(sq, "RUN_ROOT", root)
    monkeypatch.setattr(sq, "INITIAL", initial)
    rows, states = [], {}
    for name in initial:
        run = root / "runs" / name / "attempt_001" / (name + "_run")
        run.mkdir(parents=True)
        for artifact in ("truth.h5", "hashes.json", "run.fsp"):
            (run / artifact).write_bytes(b"fixture")
        _json(run / "validation.json", {k: True for k in ("fresh_load_verified", "monitors_valid", "state_valid", "scientific_valid")})
        row = {"case_id": name, "attempt_id": "attempt_001", "run_id": name + "_run", "run_dir": str(run)}
        rows.append(row)
        states[row["run_id"]] = {**{k: row[k] for k in ("case_id", "attempt_id", "run_id")},
            "state": "DONE", "solver_entered": True, "solver_invocations": 1, "replay_count": 0}
    failed_run = root / "runs" / cid / "attempt_001" / sq.FAILED_POSTENTRY_AUTHORITY["run_id"]
    failed = {"case_id": cid, "attempt_id": "attempt_001", "run_id": sq.FAILED_POSTENTRY_AUTHORITY["run_id"],
              "run_dir": str(failed_run), "state": "FAILED_POSTENTRY", "solver_invocations": 1, "automatic_replay_count": 0}
    rows.append(failed)
    states[failed["run_id"]] = {"case_id": cid, "attempt_id": "attempt_001", "run_id": failed["run_id"],
                               "state": "FAILED_POSTENTRY", "solver_entered": True, "solver_invocations": 1}
    rr = {"runs": rows}
    monkeypatch.setattr(sq, "runner_registry", lambda: (tmp_path / "registry.json", rr))
    monkeypatch.setattr(sq, "runner_status", lambda row, case: states[row["run_id"]])
    proof = {"case_id": cid, "run_id": failed["run_id"], "truth_available": False}
    monkeypatch.setattr(sq, "verify_failed_postentry_closeout", lambda row, case: proof)
    _, _, done, entered, failures = sq.reconcile(ids, set(initial))
    assert set(done) == set(initial)
    assert set(entered) == set(initial) | {cid}
    assert set(failures) == {cid}


def test_ledger_recovery_keeps_failed_case_out_of_truth_and_checks_identity():
    cid = sq.FAILED_POSTENTRY_AUTHORITY["case_id"]
    evidence = {"case_id": cid, "attempt_id": "attempt_001", "run_id": sq.FAILED_POSTENTRY_AUTHORITY["run_id"],
        "phase": "FAILED_POSTENTRY_NO_TRUTH", "entry_consumed": True, "solver_invocations": 1,
        "automatic_replay_count": 0, "truth_available": False, "runner_status_sha256": "a" * 64,
        "postentry_disposition_sha256": sq.FAILED_POSTENTRY_AUTHORITY["disposition_sha256"],
        "postentry_journal_sha256": sq.FAILED_POSTENTRY_AUTHORITY["journal_sha256"],
        "postentry_claim_sha256": sq.FAILED_POSTENTRY_AUTHORITY["claim_sha256"],
        "recovery_fence_id": sq.FAILED_POSTENTRY_AUTHORITY["recovery_fence_id"],
        "postentry_disposition_path": "disposition.json", "postentry_journal_path": "journal.json", "runner_slot_released": True}
    current = {"case_id": cid, "run_id": evidence["run_id"], "sequence_index": 11, "phase": "RUN_ONE_IN_PROGRESS"}
    ledger = {"entered_count": 11, "truth_valid_count": 10, "labels_valid_count": 10,
        "automatic_replay_count": 0, "training_fits": 0, "p_scale_fits": 0,
        "confirmation_response_access_count": 0, "entered_case_ids": [cid], "truth_valid_case_ids": [],
        "labels_valid_case_ids": [], "current_case": dict(current), "failed_or_isolated_cases": [],
        "case_records": {cid: {"run_id": evidence["run_id"], "sequence_index": 11, "phase": "RUN_ONE_IN_PROGRESS"}}}
    sq.record_failed_postentry_recovery(ledger, current, evidence)
    assert ledger["current_case"] is None and ledger["case_records"][cid]["entry_consumed"]
    assert cid in ledger["entered_case_ids"] and cid not in ledger["truth_valid_case_ids"] + ledger["labels_valid_case_ids"]
    sq._assert_failed_postentry_recorded(ledger, evidence)
    with pytest.raises(sq.StopQueue, match="FAILED_POSTENTRY_CURRENT_CASE_IDENTITY_MISMATCH"):
        sq.record_failed_postentry_recovery(copy.deepcopy(ledger), dict(current, run_id="wrong"), evidence)
