# -*- coding: utf-8 -*-
"""Fail-closed reconciliation for a controller stopped before run-one entry."""
import argparse, importlib.util, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
QUEUE_SCRIPT = ROOT / "scripts/coupling_ml/k6_v2_pipeline/serial_queue.py"


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def has_interruption_generation(history, request_id, resume_generation):
    return any(item.get("request_id") == request_id
               and item.get("resume_generation", 0) == resume_generation
               for item in history if isinstance(item, dict))


def queue_module():
    spec = importlib.util.spec_from_file_location("apcd_serial_queue_preentry_reconcile", QUEUE_SCRIPT)
    need(spec is not None and spec.loader is not None, "QUEUE_MODULE_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_preentry_candidate(controller, status, ledger, batch, registry_rows, *,
        attempt_directory_exists, active_run_exists, runner_lock_exists, run_envelopes,
        scheduled_run_requests, related_processes, task_state, scheduler_last_result):
    """Pure fail-closed gate for a current, unentered preflight cursor."""
    req, case_ids = controller["request_id"], list(controller["case_ids"])
    need(status.get("request_id") == req
         and status.get("controller_manifest_sha256") == controller["manifest_sha256"]
         and status.get("queue_id") == controller["queue_id"]
         and status.get("state") == "RUNNING" and status.get("startup_reconciled") is True,
         "PREENTRY_CONTROLLER_STATUS_IDENTITY_INVALID")
    cid = status.get("current_case_id")
    need(cid in case_ids, "PREENTRY_CURRENT_CASE_OUTSIDE_CONTROLLER")
    need(status.get("runner_request_ids") == []
         and status.get("unresolved_runner_request_ids") == []
         and status.get("post_entry_automatic_replays") == 0,
         "PREENTRY_CONTROLLER_HAS_RUNNER_REQUEST_OR_REPLAY")
    lc, bc = ledger.get("current_case"), batch.get("current_case")
    need(isinstance(lc, dict) and isinstance(bc, dict)
         and lc.get("case_id") == cid == bc.get("case_id")
         and lc.get("phase") == "ENSURE_CURRENT_ROUTE_AND_PREFLIGHT"
         and bc.get("phase") in {"ENSURE_CURRENT_ROUTE_AND_PREFLIGHT", "LIVE_ENTRY_GATE"}
         and lc.get("sequence_index") == bc.get("sequence_index")
         and lc.get("run_id") is None and bc.get("run_id") is None,
         "PREENTRY_QUEUE_POINTER_IDENTITY_INVALID")
    entered = list(ledger.get("entered_case_ids", []))
    truth = list(ledger.get("truth_valid_case_ids", []))
    labels = list(ledger.get("labels_valid_case_ids", []))
    need(ledger.get("authorized_development_case_count") == 128
         and ledger.get("entered_count") == len(entered)
         and ledger.get("truth_valid_count") == len(truth)
         and ledger.get("labels_valid_count") == len(labels)
         and set(truth).issubset(entered) and set(labels).issubset(truth)
         and ledger.get("entered_count", 0) + ledger.get("remaining_unentered_count", 0) == 128
         and ledger.get("automatic_replay_count") == 0
         and ledger.get("training_fits") == 0 and ledger.get("p_scale_fits") == 0
         and ledger.get("confirmation_response_access_count") == 0,
         "PREENTRY_LEDGER_COUNTERS_INVALID")
    first = next((x for x in case_ids if x not in set(entered)), None)
    need(cid == first and cid not in entered and cid not in truth and cid not in labels,
         "PREENTRY_CASE_NOT_FIRST_UNENTERED")
    need(lc.get("sequence_index") == len(entered) + 1, "PREENTRY_SEQUENCE_INDEX_INVALID")
    need(cid not in ledger.get("case_records", {})
         and not any(isinstance(x, dict) and x.get("case_id") == cid
                     for x in ledger.get("failed_or_isolated_cases", [])),
         "PREENTRY_CASE_HAS_EXISTING_RUN_RECORD")
    if (registry_rows or attempt_directory_exists or active_run_exists or runner_lock_exists
            or run_envelopes or scheduled_run_requests or related_processes):
        details = {"registry_rows": registry_rows, "attempt_directory_exists": attempt_directory_exists,
            "active_run_exists": active_run_exists, "runner_lock_exists": runner_lock_exists,
            "run_envelopes": run_envelopes, "scheduled_run_requests": scheduled_run_requests,
            "related_processes": related_processes}
        raise RuntimeError("PREENTRY_RUN_ONE_OR_SLOT_EVIDENCE_PRESENT:" + json.dumps(details))
    need(str(task_state).casefold() not in {"running", "queued"}
         and isinstance(scheduler_last_result, int) and scheduler_last_result != 0,
         "PREENTRY_CONTROLLER_TASK_NOT_PROVEN_STOPPED")
    return {"case_id": cid, "attempt_id": "attempt_001",
            "sequence_index": lc["sequence_index"], "entry_consumed": False,
            "solver_invocations": 0, "automatic_replay_count": 0, "truth_available": False}


def reconcile(manifest_path, manifest_sha256, request_id):
    q = queue_module()
    controller = q.verify_controller_manifest_for_stop_reconciliation(
        manifest_path, manifest_sha256, request_id)
    controller["controller_script_path"] = Path(controller["manifest"]["controller_script_path"]).resolve()
    controller["queue_manifest_path"] = Path(controller["manifest"]["queue_manifest_path"]).resolve()
    status_path = controller["status_path"]
    receipt_path = q.controller_resume_receipt_path(controller)
    need(status_path.is_file() and not status_path.is_symlink(), "PREENTRY_CONTROLLER_STATUS_MISSING")
    status = q.read(status_path)
    resume_generation = status.get("resume_generation", 0)
    need(isinstance(resume_generation, int) and not isinstance(resume_generation, bool)
         and resume_generation >= 0, "PREENTRY_RESUME_GENERATION_INVALID")
    runner = controller.get("runner_scheduler") or q._load_runner_scheduler_for_reconciliation()
    binding = runner._read_controller_task_binding(q.RUN_ROOT)
    manifest = controller["manifest"]
    need(binding.get("request_id") == request_id
         and binding.get("controller_manifest_sha256") == controller["manifest_sha256"]
         and binding.get("controller_script_sha256") == manifest["controller_script_sha256"],
         "PREENTRY_TASK_BINDING_MISMATCH")
    archived_receipt_path = None
    archived_receipt_sha256 = None
    if receipt_path.exists():
        prior_receipt_raw = receipt_path.read_bytes()
        prior_receipt = q.read(receipt_path)
        prior_receipt_sha256 = q.sha(receipt_path)
        need(resume_generation > 0
             and binding.get("resume_generation") == resume_generation
             and binding.get("resume_receipt_sha256") == prior_receipt_sha256
             and prior_receipt.get("resume_generation") == resume_generation,
             "PREENTRY_PRIOR_RESUME_RECEIPT_BINDING_INVALID")
        archived_receipt_path = receipt_path.with_name(
            "resume_receipt_" + request_id + "_generation_" + str(resume_generation) + ".json")
        if archived_receipt_path.exists():
            need(q.sha(archived_receipt_path) == prior_receipt_sha256,
                 "PREENTRY_PRIOR_RESUME_RECEIPT_ARCHIVE_CONFLICT")
        else:
            with archived_receipt_path.open("xb") as stream:
                stream.write(prior_receipt_raw)
        archived_receipt_sha256 = prior_receipt_sha256
    else:
        need(resume_generation == 0 and binding.get("resume_generation", 0) == 0,
             "PREENTRY_RESUME_RECEIPT_MISSING_AFTER_RESUME")
    xml = runner._query_task_xml(runner.CONTROLLER_TASK_NAME)
    request_files = runner._controller_request_files(q.RUN_ROOT, request_id)
    runner._validate_controller_task_xml(xml, controller, request_id, request_files[1],
        runner._expected_principal(), binding.get("resume_receipt_path"),
        binding.get("resume_receipt_sha256"))
    task = runner._task_info(runner.CONTROLLER_TASK_NAME)
    task_state = runner._task_state_value(task)
    raw_result = next((v for k, v in task.items() if str(k).casefold() == "lasttaskresult"), None)
    try:
        task_result = int(raw_result)
    except (TypeError, ValueError):
        raise RuntimeError("PREENTRY_SCHEDULER_EXIT_CODE_MISSING")
    try:
        scheduler_event_snapshot = q._controller_task_event_snapshot(runner)
    except Exception as exc:
        scheduler_event_snapshot = {"available": False, "error_type": type(exc).__name__,
                                    "error": str(exc)[:500]}
    need(str(task_state).casefold() not in {"running", "queued"}, "PREENTRY_CONTROLLER_TASK_STILL_ACTIVE")
    claim_path = request_files[3]
    need(claim_path.is_file() and not claim_path.is_symlink(), "PREENTRY_START_CLAIM_MISSING")
    claim = q.read(claim_path)
    need(claim.get("schema") == "APCD_GPU_RUNNER_V1_CONTROLLER_START_CLAIM_V1"
         and claim.get("request_id") == request_id
         and claim.get("controller_manifest_sha256") == controller["manifest_sha256"]
         and claim.get("queue_id") == controller["queue_id"], "PREENTRY_START_CLAIM_INVALID")

    _batch, _budget, _frozen_registry, ids, qman, qsha, _ingest, ctrl, _adapter = q.load_inputs()
    labels = q.initial_labels()
    _regpath, _rows, done, entered, failed = q.reconcile(ids, labels)
    ledger, batch = q.read(q.LEDGER), q.read(q.BATCH)
    need(q.sha(q.QMAN) == manifest["queue_manifest_sha256"]
         and set(controller["case_ids"]).issubset(set(ids)), "PREENTRY_QUEUE_MANIFEST_MISMATCH")
    for _cid, evidence in failed.items():
        if evidence.get("entry_consumed") is True:
            q._assert_failed_postentry_recorded(ledger, evidence)
        else:
            q._assert_failed_preentry_recorded(ledger, evidence)
    need(ledger.get("entered_count") == len(entered)
         and ledger.get("truth_valid_count") == len(done),
         "PREENTRY_LEDGER_RUNNER_RECONCILIATION_MISMATCH")

    cid = status.get("current_case_id")
    registry_path, registry = q.runner_registry()
    rows = [x for x in registry["runs"] if x.get("case_id") == cid]
    attempt_dir = q.RUN_ROOT / "runs" / cid / "attempt_001"
    request_root = q.RUN_ROOT / "requests" / "scheduled_run_one_v1"
    requests = []
    if request_root.is_dir():
        for p in request_root.glob("*/request.json"):
            try:
                item = q.read(p)
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            if item.get("case_id") == cid:
                requests.append({"path": str(p), "request_id": item.get("request_id")})
    process_rows = runner._controller_process_inventory()
    by_pid = {str(x.get("ProcessId") or x.get("process_id") or ""): x for x in process_rows}
    own_chain = {str(os.getpid())}
    cursor = str(os.getpid())
    for _ in range(len(process_rows)):
        own = by_pid.get(cursor)
        parent = str((own or {}).get("ParentProcessId") or (own or {}).get("parent_process_id") or "")
        if not parent or parent in own_chain:
            break
        own_chain.add(parent)
        cursor = parent
    related = []
    for proc in process_rows:
        pid = str(proc.get("ProcessId") or proc.get("process_id") or "")
        if pid in own_chain:
            continue
        command = str(proc.get("CommandLine") or proc.get("command_line") or "")
        script_path = str(manifest["controller_script_path"]).casefold()
        if script_path in command.casefold() and any(token in command for token in (request_id, controller["queue_id"], manifest["controller_run_id"])):
            related.append({"process_id": pid, "name": proc.get("Name"), "command_line": command[:500]})
    envelopes = sorted(str(p) for p in q.REPORT.glob("RUN_ENVELOPE_*" + str(cid) + "*"))
    candidate = validate_preentry_candidate(controller, status, ledger, batch, rows,
        attempt_directory_exists=attempt_dir.exists(),
        active_run_exists=(q.RUN_ROOT / "active_run.json").exists(),
        runner_lock_exists=(q.RUN_ROOT / ".runner.lock").exists(),
        run_envelopes=envelopes, scheduled_run_requests=requests,
        related_processes=related, task_state=task_state, scheduler_last_result=task_result)

    case_dir = q.CASE_ROOT / cid / "attempt_001"
    sm_path = case_dir / "source_manifest.json"
    source_manifest = q.read(sm_path)
    source_manifest_sha256 = q.sha(sm_path)
    preflight_log_path = q.REPORT / ("FORMAL_PREFLIGHT_LOG_" + cid + "_A78274BE_"
        + source_manifest_sha256[:12] + ".txt")
    preflight_log_evidence = {"path": str(preflight_log_path), "exists": preflight_log_path.is_file()}
    if preflight_log_path.is_file():
        preflight_log_evidence["sha256"] = q.sha(preflight_log_path)
        log_text = preflight_log_path.read_text(encoding="utf-8", errors="replace")
        preflight_log_evidence["error_excerpt"] = [line.strip()[:500] for line in log_text.splitlines()
            if any(token in line.casefold() for token in
                   ("could not bind socket", "ansysli exited", "no such file", "runner_error"))][-12:]
    need(q.current_proof_valid(case_dir, source_manifest, ctrl), "PREENTRY_CURRENT_ROUTE_LOAD_PROOF_INVALID")
    batch_case = batch.get("cases", {}).get(cid, {})
    formal_preflight_result = {"path": batch_case.get("preflight_result_path"), "exists": False}
    result_path_value = batch_case.get("preflight_result_path")
    if result_path_value:
        result_path = Path(result_path_value)
        formal_preflight_result["exists"] = result_path.is_file()
        if result_path.is_file():
            result_value = q.read(result_path)
            result_sha = q.sha(result_path)
            formal_preflight_result.update({"sha256": result_sha,
                "expected_sha256": batch_case.get("preflight_result_sha256"),
                "hash_matches_batch_status": result_sha == batch_case.get("preflight_result_sha256"),
                "result": result_value.get("result"),
                "solver_run_called": result_value.get("solver_run_called"),
                "solver_invocations": result_value.get("solver_invocations"),
                "scientific_entry_count": result_value.get("scientific_entry_count")})
            need(formal_preflight_result["hash_matches_batch_status"]
                 and result_value.get("result") == "PASS"
                 and result_value.get("solver_run_called") is False
                 and result_value.get("solver_invocations") == 0
                 and result_value.get("scientific_entry_count") == 0,
                 "PREENTRY_FORMAL_PREFLIGHT_RESULT_NOT_CURRENT_ZERO_SOLVER_PASS")
    formal_preflight_logs = []
    for current_log in sorted(q.REPORT.glob("FORMAL_PREFLIGHT_LOG_" + cid + "_A78274BE_*.txt")):
        formal_preflight_logs.append({"path": str(current_log), "sha256": q.sha(current_log),
            "size_bytes": current_log.stat().st_size})
    try:
        post_exit_gate_snapshot = {"captured_at_utc": q.now(),
            "global_entry_control": _adapter.read_global_entry_control(),
            "runner_owner_probe": _adapter.NativeAdapter.runner_owner_probe(q.RUN_ROOT),
            "active_run_exists": (q.RUN_ROOT / "active_run.json").exists(),
            "runner_lock_exists": (q.RUN_ROOT / ".runner.lock").exists()}
    except Exception as exc:
        post_exit_gate_snapshot = {"captured_at_utc": q.now(),
            "error_type": type(exc).__name__, "error": str(exc)[:500]}
    need(batch_case.get("status") in {"LOAD_PROOF_PASS", "PASS"}
         and batch_case.get("source_manifest_sha256") == q.sha(sm_path),
         "PREENTRY_BATCH_LOAD_PROOF_NOT_CURRENT")
    proof = q.artifact(case_dir, source_manifest["artifacts"]["pre_entry_setup_load_proof"], "proof")
    need(q.sha(proof) == source_manifest["artifacts"]["pre_entry_setup_load_proof"]["sha256"],
         "PREENTRY_PROOF_SHA_MISMATCH")
    old_routes = []
    for p in case_dir.glob("legacy_route_*/attempt_001/source_manifest.json"):
        old = q.read(p)
        old_routes.append({"path": str(p), "sha256": q.sha(p),
                           "route_authority_sha256": old.get("route_authority_sha256")})

    evidence_suffix = ("" if resume_generation == 0 else
                       "_RESUME_GENERATION_" + str(resume_generation))
    evidence_path = q.REPORT / ("CONTROLLER_PREENTRY_INTERRUPTION_EVIDENCE_" + request_id + "_"
                                + cid + evidence_suffix + ".json")
    need(not evidence_path.exists() and not evidence_path.is_symlink(), "PREENTRY_EVIDENCE_PATH_ALREADY_EXISTS")
    before = {"controller_status_sha256": q.sha(status_path), "ledger_sha256": q.sha(q.LEDGER),
        "batch_status_sha256": q.sha(q.BATCH), "runner_registry_path": str(registry_path),
        "runner_registry_sha256": q.sha(registry_path)}
    evidence = {"schema": "COUPLING_K6_V2_CONTROLLER_PREENTRY_INTERRUPTION_EVIDENCE_V1",
        "captured_at_utc": q.now(), "request_id": request_id,
        "resume_generation": resume_generation,
        "controller_manifest_sha256": controller["manifest_sha256"],
        "controller_script_sha256": manifest["controller_script_sha256"],
        "controller_run_id": manifest["controller_run_id"], "queue_id": controller["queue_id"],
        "scheduler_task": task, "scheduler_state": str(task_state),
        "scheduler_last_task_result": task_result, "status_missing_before_reconciliation": False,
        "status_before_reconciliation": status, "pre_reconciliation_hashes": before,
        "pre_entry_cursor": {"case_id": cid, "attempt_id": "attempt_001",
            "sequence_index": candidate["sequence_index"], "ledger_current_case": ledger.get("current_case"),
            "batch_current_case": batch.get("current_case"), "ledger_phase": ledger.get("current_case", {}).get("phase"),
            "batch_phase": batch.get("current_case", {}).get("phase"), "phase": "PRE_RUN_ONE_ENTRY_GATE"},
        "runner_evidence": {"case_registry_rows": rows, "case_attempt_directory_exists": attempt_dir.exists(),
            "active_run_exists": (q.RUN_ROOT / "active_run.json").exists(),
            "runner_lock_exists": (q.RUN_ROOT / ".runner.lock").exists(),
            "case_requests": requests, "run_envelopes": envelopes, "related_controller_processes": related},
        "load_proof": {"current_route_authority_sha256": q.AUTH_SHA,
            "source_manifest_path": str(sm_path), "source_manifest_sha256": q.sha(sm_path),
            "proof_path": str(proof), "proof_sha256": q.sha(proof),
            "fresh_load_readback_path": batch_case.get("fresh_load_readback_path"),
            "fresh_load_readback_sha256": batch_case.get("fresh_load_readback_sha256"),
            "legacy_routes": old_routes},
        "failure_diagnosis": {"last_persisted_phase": batch.get("current_case", {}).get("phase"),
            "exact_original_exception": None, "exception_capture_status": "NOT_PERSISTED_BY_CONTROLLER",
            "observed_boundary": "Scheduler exited nonzero before run-one request, run envelope, Runner attempt, or solver entry.",
            "route_refresh_context": "Current-route LOAD-only proof and the bound formal setup preflight both pass. The later LIVE_ENTRY_GATE exception was not persisted; the saved preflight and scheduler-event evidence are listed below.",
            "formal_preflight_log": preflight_log_evidence,
            "formal_preflight_log_inventory": formal_preflight_logs,
            "formal_preflight_result": formal_preflight_result,
            "task_scheduler_event_snapshot": scheduler_event_snapshot,
            "post_exit_current_gate_snapshot": post_exit_gate_snapshot,
            "solver_entry": False, "automatic_replay": False},
        "reconciliation": {"case_remains_unentered": True, "resume_same_attempt_allowed": True,
            "solver_entries": 0, "automatic_replays": 0, "training_fits": 0,
            "p_scale_fits": 0, "confirmation_response_access_count": 0}}
    q.write(evidence_path, evidence)
    evidence_sha = q.sha(evidence_path)
    interruption = {"schema": "COUPLING_K6_V2_CONTROLLER_PREENTRY_INTERRUPTION_V1",
        "request_id": request_id, "controller_manifest_sha256": controller["manifest_sha256"],
        "resume_generation": resume_generation,
        "case_id": cid, "attempt_id": "attempt_001", "sequence_index": candidate["sequence_index"],
        "phase": "ENSURE_CURRENT_ROUTE_AND_PREFLIGHT", "entry_consumed": False,
        "solver_invocations": 0, "automatic_replay_count": 0,
        "evidence_path": str(evidence_path), "evidence_sha256": evidence_sha, "recorded_at_utc": q.now()}
    history = ledger.setdefault("controller_preentry_interruptions", [])
    need(not has_interruption_generation(history, request_id, resume_generation),
         "PREENTRY_INTERRUPTION_ALREADY_RECORDED")
    counts = {k: ledger.get(k) for k in ("entered_count", "truth_valid_count", "labels_valid_count",
        "remaining_unentered_count", "automatic_replay_count", "training_fits", "p_scale_fits",
        "confirmation_response_access_count")}
    history.append(interruption)
    ledger["current_case"] = None
    ledger["queue_phase"] = "QUEUE_RECOVERY_RECONCILED_STOPPED"
    ledger["last_updated_utc"] = q.now()
    batch["current_case"] = None
    batch["queue_phase"] = "QUEUE_RECOVERY_RECONCILED_STOPPED"
    batch["last_updated_utc"] = q.now()
    need(all(ledger.get(k) == v for k, v in counts.items()), "PREENTRY_RECONCILIATION_CHANGED_COUNTERS")
    q.write(q.LEDGER, ledger)
    q.write(q.BATCH, batch)
    status.update({"state": "STOPPED_RECONCILED", "startup_reconciled": True,
        "current_case_id": None, "unresolved_runner_request_ids": [],
        "post_entry_automatic_replays": 0, "stopped_at_utc": q.now(),
        "interrupted_preentry_case_id": cid, "preentry_interruption_evidence_path": str(evidence_path),
        "preentry_interruption_evidence_sha256": evidence_sha,
        "interrupted_resume_generation": resume_generation})
    q.write(status_path, status)
    receipt = {"schema": q.SCHEMA_CONTROLLER_RESUME, "request_id": request_id,
        "controller_manifest_sha256": controller["manifest_sha256"], "queue_id": controller["queue_id"],
        "previous_status_sha256": q.sha(status_path),
        "resume_generation": int(status.get("resume_generation", 0)) + 1,
        "safe_to_resume": True, "startup_reconciled": True, "current_case_id": None,
        "unresolved_runner_request_ids": [], "post_entry_automatic_replays": 0,
        "runner_request_ids": list(status.get("runner_request_ids", []))}
    q.write(receipt_path, receipt)
    q.verify_controller_resume_receipt(controller, receipt_path, q.sha(receipt_path))
    verified = q.reconcile_controller_stopped_boundary(controller)
    return {"state": "STOPPED_RECONCILED", "request_id": request_id,
        "case_id_retained_unentered": cid, "sequence_index": candidate["sequence_index"],
        "solver_entries_this_call": 0, "automatic_replays_this_call": 0,
        "evidence_path": str(evidence_path), "evidence_sha256": evidence_sha,
        "archived_prior_resume_receipt_path": (str(archived_receipt_path)
            if archived_receipt_path else None),
        "archived_prior_resume_receipt_sha256": archived_receipt_sha256,
        "status_path": str(status_path), "status_sha256": q.sha(status_path),
        "resume_receipt_path": str(receipt_path), "resume_receipt_sha256": q.sha(receipt_path),
        "queue_checker": verified}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner-controller-manifest", required=True)
    parser.add_argument("--runner-controller-manifest-sha256", required=True)
    parser.add_argument("--runner-controller-request-id", required=True)
    args = parser.parse_args()
    print(json.dumps(reconcile(args.runner_controller_manifest,
        args.runner_controller_manifest_sha256, args.runner_controller_request_id), indent=2), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"state": "BLOCKED", "error_type": type(exc).__name__,
                          "error": str(exc)}, indent=2), flush=True)
        raise SystemExit(2)
