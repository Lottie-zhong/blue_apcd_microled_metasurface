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
    preentry_cid = sq.FAILED_PREENTRY_AUTHORITY["case_id"]
    ids = list(initial) + [cid, preentry_cid]
    root = tmp_path / "runner"
    monkeypatch.setattr(sq, "RUN_ROOT", root)
    monkeypatch.setattr(sq, "INITIAL", initial)
    monkeypatch.setattr(sq, "LEDGER", tmp_path / "ledger.json")
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
    assert preentry_cid not in entered and preentry_cid not in done and preentry_cid not in failures

    stale = {"current_case": {"case_id": preentry_cid,
        "run_id": sq.FAILED_PREENTRY_AUTHORITY["run_id"],
        "sequence_index": sq.FAILED_PREENTRY_AUTHORITY["sequence_index"]}}
    _json(sq.LEDGER, stale)
    with pytest.raises(sq.StopQueue, match="FAILED_PREENTRY_FIXED_RUN_MISSING_BUT_LEDGER_POINTS_TO_OLD_RUN"):
        sq.reconcile(ids, set(initial))

    sq.LEDGER.unlink()
    attempt_dir = root / "runs" / preentry_cid / "attempt_001"
    attempt_dir.mkdir(parents=True)
    with pytest.raises(sq.StopQueue, match="FAILED_PREENTRY_FIXED_RUN_MISSING_OR_DUPLICATE"):
        sq.reconcile(ids, set(initial))


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

def _preentry_fixture(tmp_path, monkeypatch):
    cid = "K6LDA1_DEV_D6_P05"
    attempt_id = "attempt_001"
    run_id = "K6V2_D6P05_20261006T063951Z_c6f073e5"
    runner_root, report = tmp_path / "runner", tmp_path / "report"
    monkeypatch.setattr(sq, "RUN_ROOT", runner_root)
    monkeypatch.setattr(sq, "REPORT", report)
    run = runner_root / "runs" / cid / attempt_id / run_id
    run.mkdir(parents=True)
    recovery = run / "preentry_recovery_v1"
    recovery.mkdir()
    (run / "solver.log").write_bytes(b"")
    _json(run / "validation.json", {"state": "PENDING"})
    _json(run / "hashes.json", {"state": "PENDING"})
    manifest_path = _json(run / "manifest.json",
        {"case_id": cid, "attempt_id": attempt_id, "run_id": run_id,
         "physical_contract_sha256": "1" * 64, "pre_fsp_sha256": "2" * 64})
    manifest_sha = sq.sha(manifest_path)

    envelope_path = report / ("RUN_ENVELOPE_" + run_id + ".json")
    _json(envelope_path, {"case_id": cid, "attempt_id": attempt_id, "run_id": run_id})
    immutable_root = tmp_path / "immutable"
    immutable_root.mkdir()
    authority_path = immutable_root / "authority.json"
    contract_path = immutable_root / "contract.json"
    source_manifest_path = immutable_root / "source_manifest.json"
    pre_fsp_path = immutable_root / "runtime.fsp"
    _json(authority_path, {"fixture": "authority"})
    _json(contract_path, {"fixture": "contract"})
    _json(source_manifest_path, {"fixture": "source"})
    pre_fsp_path.write_bytes(b"fixture pre-fsp")

    ledger_path = report / "QUEUE_EXECUTION_LEDGER_V1.json"
    queue_sha = "f" * 64
    initial_ledger = {
        "schema": "COUPLING_K6_V2_SERIAL_QUEUE_EXECUTION_LEDGER_V1",
        "queue_manifest_sha256": queue_sha, "authorized_development_case_count": 128,
        "entered_count": 11, "truth_valid_count": 10, "labels_valid_count": 10,
        "automatic_replay_count": 0, "training_fits": 0, "p_scale_fits": 0,
        "confirmation_response_access_count": 0,
        "entered_case_ids": ["ENTERED_" + str(i) for i in range(11)],
        "truth_valid_case_ids": ["TRUTH_" + str(i) for i in range(10)],
        "labels_valid_case_ids": ["LABEL_" + str(i) for i in range(10)],
        "remaining_unentered_case_ids": [cid],
        "current_case": {"case_id": cid, "phase": "RUN_ONE_IN_PROGRESS",
            "run_id": run_id, "sequence_index": 12,
            "run_envelope_path": str(envelope_path), "run_envelope_sha256": sq.sha(envelope_path)},
        "case_records": {cid: {"run_id": run_id, "sequence_index": 12,
            "phase": "RUN_ONE_IN_PROGRESS", "run_envelope_path": str(envelope_path),
            "run_envelope_sha256": sq.sha(envelope_path)}},
        "failed_or_isolated_cases": [],
    }
    _json(ledger_path, initial_ledger)
    monkeypatch.setattr(sq, "LEDGER", ledger_path)
    monkeypatch.setattr(sq, "BATCH", report / "BATCH_PREPARATION_STATUS_V1.json")

    empty_sha = hashlib.sha256(b"").hexdigest()
    pending_status_sha = "a" * 64
    pending_registry_sha = "b" * 64
    process_sha = "c" * 64
    control_sha = "d" * 64
    others_sha = "e" * 64
    immutable = {
        "authority": {"path": str(authority_path), "sha256": sq.sha(authority_path)},
        "contract": {"path": str(contract_path), "sha256": sq.sha(contract_path)},
        "coupling_ledger_counts": {"automatic_replay_count": 0, "entered_count": 11,
            "target_phase": "RUN_ONE_IN_PROGRESS", "target_sequence_index": 12,
            "truth_valid_count": 10},
        "envelope": {"path": str(envelope_path), "sha256": sq.sha(envelope_path)},
        "ledger": {"path": str(ledger_path), "sha256": sq.sha(ledger_path)},
        "pre_fsp": {"path": str(pre_fsp_path), "sha256": sq.sha(pre_fsp_path)},
        "source_manifest": {"path": str(source_manifest_path), "sha256": sq.sha(source_manifest_path)},
    }
    targets = {"hashes": sq.sha(run / "hashes.json"), "manifest": manifest_sha,
        "solver_log": empty_sha, "validation": sq.sha(run / "validation.json")}
    archive_path = recovery / "released_runner.lock"
    _json(archive_path, {"pid": 34072, "run_id": run_id, "case_id": cid, "attempt_id": attempt_id})
    lock_sha = sq.sha(archive_path)
    fence_basis = {"schema": "APCD_GPU_RUNNER_V1_P05_ORPHAN_RECOVERY_FENCE_BASIS_V1",
        "case_id": cid, "attempt_id": attempt_id, "run_id": run_id,
        "lock_sha256": lock_sha, "manifest_sha256": manifest_sha,
        "process_census_sha256": process_sha, "registry_sha256": pending_registry_sha,
        "status_sha256": pending_status_sha, "control_snapshot_sha256": control_sha}
    fence_sha = sq.canonical_sha(fence_basis)
    control_snapshot = {"schema": "APCD_GPU_RUNNER_GLOBAL_ENTRY_HOLD_SNAPSHOT_V1",
        "result": "PASS", "health_status": "PASS", "new_entry_hold": 0,
        "active_global_hold_ids": [], "control_db_sha256": "6" * 64,
        "control_generation": 27, "snapshot_sha256": control_sha}
    claim = {"schema": "APCD_GPU_RUNNER_V1_P05_ORPHAN_RECOVERY_CLAIM_V1",
        "case_id": cid, "attempt_id": attempt_id, "run_id": run_id,
        "control_snapshot": control_snapshot, "fence_basis": fence_basis,
        "fence_sha256": fence_sha, "immutable_artifacts": immutable,
        "target_artifacts": targets, "registry_other_rows_sha256": others_sha,
        "process_snapshot": {"lock_pid": 34072, "lock_pid_present": False,
            "descendant_pids": [], "target_related_pids": [], "process_census_sha256": process_sha}}
    claim_path = _json(recovery / "claim.json", claim)
    claim_sha = sq.sha(claim_path)
    disposition = {"schema": "APCD_GPU_RUNNER_V1_P05_ORPHAN_PREENTRY_DISPOSITION_V1",
        "case_id": cid, "attempt_id": attempt_id, "run_id": run_id,
        "result": "FAILED_PREENTRY", "classification": "ORPHANED_RUNNER_LOCK_BEFORE_SOLVER_ENTRY",
        "claim_sha256": claim_sha, "recovery_fence_sha256": fence_sha,
        "lock_original_sha256": lock_sha, "attempt_budget_consumed": False,
        "physical_solver_entry_count": 0, "solver_entered": False, "solver_invocations": 0,
        "automatic_replay_count": 0, "truth_created": False, "truth_valid": False,
        "same_run_id_reuse_supported": False,
        "next_run_policy": "same case_id and attempt_id may use a new run_id only after Coupling ledger reconciliation and fresh official launch revalidation",
        "evidence": {"manifest_sha256": manifest_sha,
            "status_sha256_before": pending_status_sha, "registry_sha256_before": pending_registry_sha,
            "process_census_sha256": process_sha, "control_generation": 27,
            "control_snapshot_sha256": control_sha, "coupling_artifacts": immutable}}
    disposition_path = _json(recovery / "disposition.json", disposition)
    disposition_sha = sq.sha(disposition_path)
    status_path = _json(run / "status.json", {"schema": "APCD_GPU_RUN_STATUS_V1",
        "case_id": cid, "attempt_id": attempt_id, "run_id": run_id,
        "state": "FAILED_PREENTRY", "solver_entered": False, "solver_invocations": 0,
        "automatic_replay_count": 0, "failure": "ORPHANED_RUNNER_LOCK_BEFORE_SOLVER_ENTRY",
        "preentry_recovery_claim_sha256": claim_sha,
        "preentry_recovery_disposition_sha256": disposition_sha,
        "preentry_recovery_fence_sha256": fence_sha})
    status_sha = sq.sha(status_path)
    row = {"case_id": cid, "attempt_id": attempt_id, "run_id": run_id, "run_dir": str(run),
        "state": "FAILED_PREENTRY", "solver_entered": False, "solver_invocations": 0,
        "automatic_replay_count": 0, "preentry_recovery_disposition_sha256": disposition_sha,
        "preentry_recovery_fence_sha256": fence_sha}
    registry_path = runner_root / "registry.json"
    _json(registry_path, {"runs": [row]})
    registry_sha = sq.sha(registry_path)
    events = []
    previous = "0" * 64
    zero = {"automatic_replay_count": 0, "solver_entered": False, "solver_invocations": 0}
    entries = [
        ("CLAIMED", {"claim_sha256": claim_sha, "disposition_sha256": disposition_sha, "fence_sha256": fence_sha}),
        ("STATUS_TERMINALIZATION_INTENT", dict(zero, disposition_sha256=disposition_sha, fence_sha256=fence_sha)),
        ("STATUS_TERMINALIZED", dict(zero, disposition_sha256=disposition_sha, fence_sha256=fence_sha, status_sha256=status_sha)),
        ("REGISTRY_TERMINALIZATION_INTENT", dict(zero, disposition_sha256=disposition_sha, fence_sha256=fence_sha)),
        ("REGISTRY_TERMINALIZED", dict(zero, disposition_sha256=disposition_sha, fence_sha256=fence_sha, registry_sha256=registry_sha)),
        ("RELEASE_READY", dict(zero, status_sha256=status_sha, registry_sha256=registry_sha, lock_archive_path=str(archive_path.resolve()))),
        ("LOCK_RELEASE_INTENT", dict(zero, archive_path=str(archive_path.resolve()), original_lock_sha256=lock_sha)),
    ]
    for sequence, (event_type, details) in enumerate(entries, 1):
        event = {"sequence": sequence, "event_type": event_type, "timestamp_unix": 123.0,
            "previous_event_sha256": previous, "details": details}
        event["event_sha256"] = sq.canonical_sha(event)
        previous = event["event_sha256"]
        events.append(event)
    journal_path = _json(recovery / "journal.json", {"schema": "APCD_GPU_RUNNER_V1_P05_ORPHAN_RECOVERY_JOURNAL_V1",
        "case_id": cid, "attempt_id": attempt_id, "run_id": run_id, "fence_sha256": fence_sha, "events": events})
    expected = {"case_id": cid, "attempt_id": attempt_id, "run_id": run_id, "sequence_index": 12,
        "ledger_sha256": sq.sha(ledger_path), "queue_manifest_sha256": queue_sha,
        "envelope_sha256": sq.sha(envelope_path), "manifest_sha256": manifest_sha,
        "pending_status_sha256": pending_status_sha, "status_sha256": status_sha,
        "pending_registry_sha256": pending_registry_sha, "registry_terminal_sha256": registry_sha,
        "disposition_sha256": disposition_sha, "claim_sha256": claim_sha,
        "journal_sha256": sq.sha(journal_path), "fence_sha256": fence_sha,
        "lock_sha256": lock_sha, "lock_pid": 34072, "process_census_sha256": process_sha,
        "control_snapshot_sha256": control_sha, "control_db_sha256": "6" * 64,
        "control_generation": 27, "registry_other_rows_sha256": others_sha,
        "immutable_artifacts": immutable, "target_artifacts": targets}
    monkeypatch.setattr(sq, "FAILED_PREENTRY_AUTHORITY", expected)
    batch = {"current_case": {"case_id": cid, "sequence_index": 12, "phase": "LIVE_ENTRY_GATE"},
        "queue_phase": "LIVE_ENTRY_GATE"}
    return row, cid, sq.read(ledger_path), batch, expected


def _preentry_ledger_fixture(tmp_path, monkeypatch):
    cid = "K6LDA1_DEV_D6_P05"
    attempt_id = "attempt_001"
    run_id = "K6V2_D6P05_20261006T063951Z_c6f073e5"
    envelope = _json(tmp_path / "envelope.json", {"case_id": cid, "attempt_id": attempt_id, "run_id": run_id})
    queue_sha = "f" * 64
    current = {"case_id": cid, "attempt_id": attempt_id, "run_id": run_id,
        "sequence_index": 12, "phase": "RUN_ONE_IN_PROGRESS",
        "run_envelope_path": str(envelope), "run_envelope_sha256": sq.sha(envelope)}
    ledger = {"queue_manifest_sha256": queue_sha, "authorized_development_case_count": 128,
        "entered_count": 11, "truth_valid_count": 10, "labels_valid_count": 10,
        "automatic_replay_count": 0, "training_fits": 0, "p_scale_fits": 0,
        "confirmation_response_access_count": 0,
        "entered_case_ids": ["ENTERED_" + str(i) for i in range(11)],
        "truth_valid_case_ids": ["TRUTH_" + str(i) for i in range(10)],
        "labels_valid_case_ids": ["LABEL_" + str(i) for i in range(10)],
        "remaining_unentered_case_ids": [cid], "current_case": copy.deepcopy(current),
        "case_records": {cid: copy.deepcopy(current)}, "failed_or_isolated_cases": []}
    ledger_path = _json(tmp_path / "ledger.json", ledger)
    expected_authority = {"case_id": cid, "attempt_id": attempt_id, "run_id": run_id,
        "sequence_index": 12, "ledger_sha256": sq.sha(ledger_path),
        "queue_manifest_sha256": queue_sha, "envelope_sha256": sq.sha(envelope),
        "immutable_artifacts": {"envelope": {"path": str(envelope), "sha256": sq.sha(envelope)}},
        "claim_sha256": "1" * 64, "disposition_sha256": "2" * 64,
        "journal_sha256": "3" * 64, "fence_sha256": "4" * 64, "status_sha256": "5" * 64}
    evidence = {"case_id": cid, "attempt_id": attempt_id, "run_id": run_id,
        "phase": "FAILED_PREENTRY_NO_ENTRY", "entry_consumed": False,
        "solver_invocations": 0, "automatic_replay_count": 0, "truth_available": False,
        "claim_sha256": expected_authority["claim_sha256"],
        "disposition_sha256": expected_authority["disposition_sha256"],
        "journal_sha256": expected_authority["journal_sha256"],
        "recovery_fence_sha256": expected_authority["fence_sha256"],
        "archived_lock_sha256": "6" * 64, "runner_status_sha256": expected_authority["status_sha256"],
        "runner_slot_released": True}
    monkeypatch.setattr(sq, "FAILED_PREENTRY_AUTHORITY", expected_authority)
    monkeypatch.setattr(sq, "LEDGER", ledger_path)
    batch = {"current_case": {"case_id": cid, "sequence_index": 12,
        "phase": "LIVE_ENTRY_GATE", "run_id": run_id}, "queue_phase": "LIVE_ENTRY_GATE"}
    return sq.read(ledger_path), batch, evidence


def test_preentry_ledger_reconciliation_is_zero_entry_and_idempotent(tmp_path, monkeypatch):
    ledger, batch, evidence = _preentry_ledger_fixture(tmp_path, monkeypatch)
    before = {k: ledger[k] for k in ("entered_count", "truth_valid_count", "labels_valid_count",
        "automatic_replay_count", "training_fits", "p_scale_fits", "confirmation_response_access_count")}
    changed_ledger, changed_status = sq.reconcile_failed_preentry(ledger, batch, evidence)
    assert changed_ledger and changed_status
    assert {k: ledger[k] for k in before} == before
    cid = evidence["case_id"]
    assert ledger["current_case"] is None and cid not in ledger["entered_case_ids"]
    assert cid not in ledger["truth_valid_case_ids"] and cid not in ledger["labels_valid_case_ids"]
    assert cid in ledger["remaining_unentered_case_ids"]
    assert batch["current_case"] is None and batch["queue_phase"] == "QUEUE_ACTIVE"
    sq._assert_failed_preentry_recorded(ledger, evidence)
    assert not any(sq.reconcile_failed_preentry(ledger, batch, evidence))


def test_preentry_verifier_rejects_wrong_identity_and_tampered_receipt(tmp_path, monkeypatch):
    row, cid, _, _, _ = _preentry_fixture(tmp_path, monkeypatch)
    with pytest.raises(sq.StopQueue, match="FAILED_PREENTRY_IDENTITY_MISMATCH"):
        sq.verify_failed_preentry_recovery(dict(row, run_id="wrong"), cid)
    disposition = Path(row["run_dir"]) / "preentry_recovery_v1" / "disposition.json"
    value = json.loads(disposition.read_text(encoding="utf-8"))
    value["solver_invocations"] = 1
    _json(disposition, value)
    with pytest.raises(sq.StopQueue, match="FAILED_PREENTRY_RECOVERY_FILE_SHA_MISMATCH"):
        sq.verify_failed_preentry_recovery(row, cid)


def test_preentry_verifier_rejects_missing_receipt_artifact(tmp_path, monkeypatch):
    row, cid, _, _, _ = _preentry_fixture(tmp_path, monkeypatch)
    claim = Path(row["run_dir"]) / "preentry_recovery_v1" / "claim.json"
    claim.unlink()
    with pytest.raises(sq.StopQueue, match="FAILED_PREENTRY_RECOVERY_ARTIFACT_MISSING"):
        sq.verify_failed_preentry_recovery(row, cid)


def test_preentry_ledger_reconciliation_rejects_counted_or_wrong_sequence_case(tmp_path, monkeypatch):
    ledger, _, evidence = _preentry_ledger_fixture(tmp_path, monkeypatch)
    ledger["entered_case_ids"].append(evidence["case_id"])
    with pytest.raises(sq.StopQueue, match="FAILED_PREENTRY_CASE_ALREADY_COUNTED"):
        sq.record_failed_preentry_recovery(ledger, ledger["current_case"], evidence)
    ledger, _, evidence = _preentry_ledger_fixture(tmp_path / "wrong-sequence", monkeypatch)
    wrong = dict(ledger["current_case"], sequence_index=11)
    with pytest.raises(sq.StopQueue, match="FAILED_PREENTRY_CURRENT_CASE_IDENTITY_MISMATCH"):
        sq.record_failed_preentry_recovery(ledger, wrong, evidence)


def _write_done_case(root, cid):
    run = root / "runs" / cid / "attempt_001" / (cid + "_fresh")
    run.mkdir(parents=True)
    row = {"case_id": cid, "attempt_id": "attempt_001", "run_id": cid + "_fresh", "run_dir": str(run)}
    _json(run / "status.json", {**{k: row[k] for k in ("case_id", "attempt_id", "run_id")},
        "state": "DONE", "solver_entered": True, "solver_invocations": 1, "replay_count": 0})
    _json(run / "validation.json", {k: True for k in
        ("fresh_load_verified", "monitors_valid", "state_valid", "scientific_valid")})
    _json(run / "hashes.json", {"fixture": True})
    for name in ("truth.h5", "run.fsp"):
        (run / name).write_bytes(b"fixture")
    return row


def _write_bound_ingest_artifacts(report, row):
    run = Path(row["run_dir"])
    cid, attempt_id, run_id = row["case_id"], row["attempt_id"], row["run_id"]
    contract_sha = "a" * 64
    geometry = [220, 195, 210, 150, 140, 215]
    manifest_path = _json(run / "manifest.json", {"case_id": cid, "attempt_id": attempt_id,
        "run_id": run_id, "geometry": geometry, "physical_contract_sha256": contract_sha})
    truth_path, fsp_path = run / "truth.h5", run / "run.fsp"
    truth_sha, fsp_sha = sq.sha(truth_path), sq.sha(fsp_path)
    validation_path = _json(run / "validation.json", {"fresh_load_verified": True,
        "monitors_valid": True, "state_valid": True, "scientific_valid": True,
        "run_id": run_id, "truth_h5": str(truth_path), "truth_h5_sha256": truth_sha,
        "run_fsp_sha256": fsp_sha})
    _json(run / "status.json", {"case_id": cid, "attempt_id": attempt_id, "run_id": run_id,
        "state": "DONE", "solver_entered": True, "solver_invocations": 1, "replay_count": 0})
    _json(run / "hashes.json", {"manifest_sha256": sq.sha(manifest_path),
        "truth_h5_sha256": truth_sha, "run_fsp_sha256": fsp_sha,
        "validation_sha256": sq.sha(validation_path)})
    descriptors = {}
    for key, rel in (("orders_json", "orders/orders.json"), ("raw_metadata", "raw/raw.json"),
                     ("raw_npz", "raw/raw.npz"), ("state_metadata", "state/state.json"),
                     ("state_npz", "state/state.npz")):
        p = run / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((key + " fixture").encode())
        descriptors[key] = {"path": str(p), "sha256": sq.sha(p)}
    label_path = report / ("INGESTED_TRUTH_" + cid + "_V1.npz")
    label_path.parent.mkdir(parents=True, exist_ok=True)
    label_path.write_bytes(b"synthetic label fixture")
    result_path = report / ("INGEST_RESULT_" + cid + "_V1.json")
    result = {"schema": "COUPLING_K6_V2_DEVELOPMENT_CASE_INGEST_RESULT_V1",
        "case_id": cid, "attempt_id": attempt_id, "run_id": run_id,
        "status": "PASS", "role": "DEVELOPMENT_LOCAL_AXIS", "ordered_D_nm": geometry,
        "solver_entered": True, "solver_invocations": 1, "replay_count": 0,
        "input_artifacts": {"case_id": cid, "attempt_id": attempt_id, "role": "DEVELOPMENT_LOCAL_AXIS",
            "ordered_D_nm": geometry, "status": "DONE", "solver_invocations": 1, "replay_count": 0,
            "physical_contract_sha256": contract_sha,
            "source_manifest": {"path": str(manifest_path), "sha256": sq.sha(manifest_path)},
            "truth_h5": {"path": str(truth_path), "sha256": truth_sha}, **descriptors},
        "truth_provenance": {"source_manifest_sha256": sq.sha(manifest_path),
            "physical_contract_sha256": contract_sha,
            "orders_sha256": descriptors["orders_json"]["sha256"],
            "raw_metadata_sha256": descriptors["raw_metadata"]["sha256"],
            "raw_npz_sha256": descriptors["raw_npz"]["sha256"],
            "state_metadata_sha256": descriptors["state_metadata"]["sha256"],
            "state_npz_sha256": descriptors["state_npz"]["sha256"]},
        "truth_artifact": {"path": str(label_path), "sha256": sq.sha(label_path)}}
    _json(result_path, result)
    row["state"] = "DONE"
    return result_path, label_path


def test_reconcile_accepts_only_one_fresh_same_attempt_run_after_preentry(tmp_path, monkeypatch):
    cid = "K6LDA1_DEV_D6_P05"
    old_run_id = "K6V2_D6P05_20261006T063951Z_c6f073e5"
    initial = ("INIT_A", "INIT_B", "INIT_C")
    ids = list(initial) + [cid]
    root = tmp_path / "runner"
    monkeypatch.setattr(sq, "RUN_ROOT", root)
    monkeypatch.setattr(sq, "INITIAL", initial)
    expected = {"case_id": cid, "attempt_id": "attempt_001", "run_id": old_run_id, "sequence_index": 12}
    monkeypatch.setattr(sq, "FAILED_PREENTRY_AUTHORITY", expected)
    evidence = {"case_id": cid, "attempt_id": "attempt_001", "run_id": old_run_id,
        "phase": "FAILED_PREENTRY_NO_ENTRY", "entry_consumed": False,
        "solver_invocations": 0, "automatic_replay_count": 0, "truth_available": False}
    monkeypatch.setattr(sq, "verify_failed_preentry_recovery", lambda row, case, require_slot_free=False, fresh_success_row=None: evidence)
    rows, states = [], {}
    for name in initial:
        row = _write_done_case(root, name)
        rows.append(row)
        states[row["run_id"]] = {**{k: row[k] for k in ("case_id", "attempt_id", "run_id")},
            "state": "DONE", "solver_entered": True, "solver_invocations": 1, "replay_count": 0}
    old = {"case_id": cid, "attempt_id": "attempt_001", "run_id": old_run_id,
        "run_dir": str(root / "runs" / cid / "attempt_001" / old_run_id)}
    fresh = _write_done_case(root, cid)
    rows.extend((old, fresh))
    states[fresh["run_id"]] = {**{k: fresh[k] for k in ("case_id", "attempt_id", "run_id")},
        "state": "DONE", "solver_entered": True, "solver_invocations": 1, "replay_count": 0}
    rr = {"runs": rows}
    monkeypatch.setattr(sq, "runner_registry", lambda: (tmp_path / "registry.json", rr))
    monkeypatch.setattr(sq, "runner_status", lambda row, case: states[row["run_id"]])
    _, _, done, entered, failures = sq.reconcile(ids, set(initial))
    assert set(done) == set(ids)
    assert cid in entered and failures[cid] == evidence
    rr["runs"].append({"case_id": cid, "attempt_id": "attempt_002", "run_id": "unauthorized"})
    with pytest.raises(sq.StopQueue, match="FAILED_PREENTRY_UNAUTHORIZED_ATTEMPT"):
        sq.reconcile(ids, set(initial))


def test_reconcile_accepts_success_labels_only_when_bound_to_fresh_run(tmp_path, monkeypatch):
    old_row, cid, _, _, _ = _preentry_fixture(tmp_path, monkeypatch)
    initial = ("INIT_A", "INIT_B", "INIT_C")
    monkeypatch.setattr(sq, "INITIAL", initial)
    root = Path(sq.RUN_ROOT)
    rows = []
    for name in initial:
        row = _write_done_case(root, name)
        row["state"] = "DONE"
        rows.append(row)
    fresh = _write_done_case(root, cid)
    _, label_path = _write_bound_ingest_artifacts(Path(sq.REPORT), fresh)
    rows.extend((old_row, fresh))
    registry = {"runs": rows}
    monkeypatch.setattr(sq, "runner_registry", lambda: (tmp_path / "registry.json", registry))
    labels = set(initial) | {cid}
    _, _, done, entered, failures = sq.reconcile(list(initial) + [cid], labels)
    assert set(done) == set(initial) | {cid}
    assert cid in entered
    assert failures[cid]["run_id"] == sq.FAILED_PREENTRY_AUTHORITY["run_id"]
    result_path = Path(sq.REPORT) / ("INGEST_RESULT_" + cid + "_V1.json")
    valid = json.loads(result_path.read_text(encoding="utf-8"))
    assert sq.verify_preentry_case_label_binding(cid, "attempt_001",
        sq.FAILED_PREENTRY_AUTHORITY["run_id"], fresh)["label_sha256"] == sq.sha(label_path)
    bad = copy.deepcopy(valid); bad["run_id"] = sq.FAILED_PREENTRY_AUTHORITY["run_id"]
    _json(result_path, bad)
    with pytest.raises(sq.StopQueue, match="FAILED_PREENTRY_LABEL_RESULT_IDENTITY_MISMATCH"):
        sq.verify_preentry_case_label_binding(cid, "attempt_001", sq.FAILED_PREENTRY_AUTHORITY["run_id"], fresh)
    bad = copy.deepcopy(valid); bad["input_artifacts"]["truth_h5"]["sha256"] = "0" * 64
    _json(result_path, bad)
    with pytest.raises(sq.StopQueue, match="FAILED_PREENTRY_LABEL_TRUTH_SOURCE_MISMATCH"):
        sq.verify_preentry_case_label_binding(cid, "attempt_001", sq.FAILED_PREENTRY_AUTHORITY["run_id"], fresh)
    bad = copy.deepcopy(valid); bad["truth_provenance"]["source_manifest_sha256"] = "0" * 64
    _json(result_path, bad)
    with pytest.raises(sq.StopQueue, match="FAILED_PREENTRY_LABEL_SOURCE_MANIFEST_MISMATCH"):
        sq.verify_preentry_case_label_binding(cid, "attempt_001", sq.FAILED_PREENTRY_AUTHORITY["run_id"], fresh)
    old_as_success = dict(old_row, state="DONE")
    with pytest.raises(sq.StopQueue, match="FAILED_PREENTRY_LABEL_RUN_ID_MISMATCH"):
        sq.verify_preentry_case_label_binding(cid, "attempt_001", sq.FAILED_PREENTRY_AUTHORITY["run_id"], old_as_success)


def test_fresh_run_id_is_distinct_from_recovered_run_and_uses_same_case(tmp_path, monkeypatch):
    row, cid, _, _, _ = _preentry_fixture(tmp_path, monkeypatch)
    candidate = sq.fresh_run_id(cid, {"runs": [row]})
    assert candidate.startswith("K6V2_D6P05_")
    assert candidate != row["run_id"]
    assert candidate not in {x["run_id"] for x in (row,)}
