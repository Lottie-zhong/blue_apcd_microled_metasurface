from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
import uuid
import os
import traceback
from datetime import datetime, timezone
from pathlib import Path


def _early_event_path(path, event_type, **payload):
    """Write startup/uncaught telemetry without importing project modules."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"timestamp": datetime.now(timezone.utc).isoformat(), "event_type": event_type, **payload}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False, default=str) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return row


def _early_config_context():
    if len(sys.argv) < 2:
        return None
    config_path = Path(sys.argv[1])
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
    except BaseException:
        return {"config_path": str(config_path)}
    runtime = Path(cfg.get("runtime", config_path.parent))
    attempt_root = Path(cfg.get("attempt_root", config_path.parent))
    context = {
        "config_path": str(config_path),
        "runtime": str(runtime),
        "attempt_root": str(attempt_root),
        "host_pid": os.getpid(),
        "task_id": cfg.get("task"),
        "case_id": cfg.get("case"),
        "attempt_id": cfg.get("attempt"),
        "scientific_entry_count": 0,
    }
    for root in (runtime, attempt_root):
        _early_event_path(root / "events.jsonl", "HOST_RUNTIME_ENTERED", **context)
        _early_event_path(root / "events.jsonl", "PREENTRY_VALIDATION_STARTED", **context)
    return {"cfg": cfg, "runtime": runtime, "attempt_root": attempt_root, "context": context}


_EARLY_CONTEXT = _early_config_context()

ROOT = Path(__file__).resolve().parents[3]
SCIENCE_ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
G2_SOURCE = SCIENCE_ROOT / r"scripts\coupling_ml\apcd_coupling_2d3d_g2_attempt003_production_v1.py"
LUMAPI = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
BRANCH = "coupling_ml"
sys.path.insert(0, str(ROOT / "scripts"))

from shared_fdtd.engine.persistence import (
    ensure_parent,
    persistence_failure_status,
    persistence_path_preflight,
    persist_and_verify,
    save_and_verify,
    sha256_equal,
)
from shared_fdtd.engine.gpu_bundle import persist_gpu_bundle, wait_for_bundle_ready
from shared_fdtd.control_v3.resources import ResourceRequest, RuntimeResourceMonitor, read_resource_snapshot
from shared_fdtd.engine.attempt_state import write_durable_attempt_state


class AdmissionGateBlocked(RuntimeError):
    def __init__(self, evidence):
        super().__init__("FINAL_LAUNCH_REVALIDATION_BLOCKED")
        self.evidence = evidence




from shared_fdtd.tools.pw_scientific_launcher import (
    LAUNCHER_ID,
    load_only_validate as pw_load_only_validate,
    postprocess as pw_postprocess,
    run_and_confirm_entry,
    run_standalone_gpu_and_confirm_completion,
    validate_config as validate_pw_config,
)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def import_authority(output_root, task):
    sys.path.insert(0, str(ROOT / "scripts"))
    sys.path.insert(0, str(LUMAPI))
    spec = importlib.util.spec_from_file_location("g2_v3_runtime_authority", str(G2_SOURCE))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    mod.OUT = Path(output_root)
    mod.TASK_ID = task
    mod.CASES = ["W2H_06824"]
    mod.G1 = None
    g = mod.load_g1()
    g.OUT = Path(output_root)
    g.TASK_ID = task
    g._attempt003_base_case_contract = g.case_contract
    return mod, g


def queue_state(db, cfg, state):
    with db.immediate() as con:
        if state == "WAIT_RESOURCE_CAPACITY":
            con.execute(
                "UPDATE branch_queue SET state=?,slot_id=NULL,lease_token_hash=NULL,fencing_generation=NULL,updated_at=? WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
                (state, datetime.now(timezone.utc).isoformat(), cfg["branch"], cfg["case"], cfg["attempt"]),
            )
        else:
            con.execute("UPDATE branch_queue SET state=?,updated_at=? WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
                        (state, datetime.now(timezone.utc).isoformat(), cfg["branch"], cfg["case"], cfg["attempt"]))


def emit(cfg, event_type, **payload):
    from shared_fdtd.engine.event_log import append_event
    row = {"task_id": cfg["task"], "case_id": cfg["case"], "attempt_id": cfg["attempt"], "launch_id": cfg.get("launch_id"), **payload}
    for path in (Path(cfg["runtime"]) / "events.jsonl", Path(cfg["attempt_root"]) / "events.jsonl"):
        append_event(path, event_type, **row)


def mirror_initial(cfg):
    runtime = Path(cfg["runtime"])
    runtime.mkdir(parents=True, exist_ok=True)
    target = runtime / "events.jsonl"
    source = Path(cfg["attempt_root"]) / "events.jsonl"
    if not target.exists() and source.exists():
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def validate_load(fd, cfg, is_pw):
    if is_pw:
        pw_load_only_validate(fd, cfg)
        return
    _ = fd.getdata("top_farfield3d_monitor", "f")
    _ = fd.getdata("top_farfield3d_monitor", "Ex")
    _ = fd.farfield3d("top_farfield3d_monitor", 1)


def fresh_load_validate_path(path, cfg, is_pw):
    import lumapi
    handle = lumapi.FDTD(str(path), hide=True)
    try:
        validate_load(handle, cfg, is_pw)
        return {"passed": True, "mode": "LOAD_ONLY", "path": str(path)}
    finally:
        handle.close()


def _main_owned(cfg):
    is_pw = cfg.get("scientific_launcher") == "PW_PERIODIC_PLANAR"
    if is_pw:
        validate_pw_config(cfg)
    mirror_initial(cfg)
    from shared_fdtd.control_v3.allocator import Allocator, Lease
    from shared_fdtd.control_v3.db import ControlDB

    db = ControlDB(cfg["db"])
    allocator = Allocator(db)
    lease = Lease(
        cfg["slot_id"], cfg["branch"], cfg["case"], cfg["attempt"],
        cfg["lease_token"], int(cfg["fencing_generation"]),
        int(cfg.get("admission_control_generation", -1)),
        cfg.get("admission_provenance"),
    )
    attempt_root = Path(cfg["attempt_root"])
    case_root = attempt_root
    artifact_tag = f"{cfg['case']}__{cfg['attempt']}"
    pre = Path(cfg["pre_fsp"])
    run = case_root / "run" / f"{cfg['case']}__{cfg['attempt']}_runtime.fsp"
    native = case_root / "native" / run.name
    post = case_root / "post" / run.name
    ledger_path = case_root / "attempt_ledger.json"
    ledger = {
        "schema": "APCD_COUPLING_V3_ATTEMPT_LEDGER_V1",
        "task_id": cfg["task"], "case_id": cfg["case"], "attempt_id": cfg["attempt"],
        "pre_fsp": str(pre), "pre_fsp_sha256": sha(pre), "physical_contract_hash": cfg["physical_contract_hash"],
        "solver_entered": False, "solver_returned": False, "run_invocation_count": 0, "replay": False,
        "created_utc": now(),
    }
    write(ledger_path, ledger)
    entered = False
    entry_confirmed = False
    returned = False
    gpu_completion_barrier = False
    fd = None
    load_fd = None
    resource_monitor = None
    adapter_identity = LAUNCHER_ID if is_pw else 'APCD_G2_ATTEMPT003'
    try:
        emit(cfg, "HOST_STARTED", host_pid=__import__("os").getpid(), runtime=str(Path(cfg["runtime"])))
        queue_state(db, cfg, "SLOT_ACQUIRED")
        emit(cfg, "SLOT_ACQUIRED", slot_id=lease.slot_id, fencing_generation=lease.fencing_generation)
        if not pre.is_file() or not sha256_equal(sha(pre), cfg["pre_fsp_sha256"]):
            raise RuntimeError("PRE_FSP_HASH_MISMATCH")
        preflight = persistence_path_preflight(case_root, cfg["runtime"])
        write(case_root / "persistence_path_preflight.json", preflight)
        emit(cfg, "PERSISTENCE_PATH_PREFLIGHT", **preflight)
        run.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pre, run)
        if not sha256_equal(sha(run), sha(pre)):
            raise RuntimeError("RUNTIME_FSP_COPY_HASH_MISMATCH")
        write_durable_attempt_state(
            case_root / "attempt_state.json",
            cfg={**cfg, "scientific_invocation_count": 0, "canonical_state": "SETUP_READY"},
            lease=lease, setup_path=pre, runtime_fsp=run, native_target=native,
            post_target=post, raw_target=case_root / "raw_result.json",
            logs=[case_root / "solver.log"], adapter_identity=adapter_identity,
            persistence_preflight=preflight,
            scientific_contract_hash=cfg["physical_contract_hash"],
        )
        queue_state(db, cfg, "SOLVER_ENTRY_INTENT")
        emit(cfg, "SOLVER_ENTRY_INTENT", run_fsp=str(run), run_fsp_sha256=sha(run))
        if not bool(cfg.get("scientific_entry_allowed", True)):
            boundary = {
                "status": "PREENTRY_BOUNDARY_REACHED",
                "case_id": cfg["case"],
                "attempt_id": cfg["attempt"],
                "slot_id": lease.slot_id,
                "fencing_generation": lease.fencing_generation,
                "solver_entered": False,
                "scientific_solver_entry_count": 0,
                "run_invocation_count": 0,
                "next_action": "LUMERICAL_SCIENTIFIC_INVOCATION_BLOCKED",
                "timestamp_utc": now(),
            }
            write(case_root / "scientific_entry_boundary.json", boundary)
            emit(cfg, "SCIENTIFIC_ENTRY_BOUNDARY_REACHED", **boundary)
            allocator.release_owned(lease, scientific_terminal="FAILED_PREENTRY")
            queue_state(db, cfg, "WAIT_RESOURCE_CAPACITY")
            emit(cfg, "PREENTRY_LEASE_RELEASED", slot_id=lease.slot_id)
            print(json.dumps({"status": "PREENTRY_BOUNDARY_REACHED", "case": cfg["case"], "attempt": cfg["attempt"], "solver_entered": False}, ensure_ascii=False), flush=True)
            return
        mod = g = None
        if not is_pw:
            mod, g = import_authority(Path(cfg["output_root"]), cfg["task"])
        if str(LUMAPI) not in sys.path:
            sys.path.insert(0, str(LUMAPI))
        import lumapi
        fd = lumapi.FDTD(str(run), hide=True)
        backend_type = str(cfg.get("backend_type", "CPU")).upper()
        if backend_type != "GPU":
            fd.setresource("FDTD", 1, "processes", "12")
            fd.setresource("FDTD", 1, "threads", "1")
        cfg["run_fsp"] = str(run)
        def confirm_entry(evidence):
            nonlocal entered, entry_confirmed
            if entry_confirmed:
                return
            entry_confirmed = True
            entered = True
            entry_timestamp = now()
            process_binding = None
            if cfg.get("launch_id"):
                rows = evidence.get("processes") or []
                candidate = next((row for row in rows if row.get("ProcessId")), None)
                if candidate is not None:
                    from shared_fdtd.control_v3.launch_authority import ScientificLaunchAuthority
                    process_binding = {
                        "pid": int(candidate["ProcessId"]),
                        "created_at": str(candidate.get("CreationDate") or entry_timestamp),
                        "executable": str(candidate.get("ExecutablePath") or candidate.get("Name") or "UNKNOWN"),
                    }
                    ScientificLaunchAuthority(db).record_process(lease, cfg["launch_id"], **process_binding)
            ledger.update({"solver_entered": True, "physical_solver_entry": True, "entered_timestamp_utc": entry_timestamp,
                           "process_identity": process_binding or {"launch_id": cfg.get("launch_id"), "observation": "NO_PID_EXPOSED"},
                           "run_invocation_count": 1, "slot_id": lease.slot_id, "run_fsp": str(run), "run_fsp_sha256": sha(run),
                           "entry_evidence": evidence})
            write(ledger_path, ledger)
            write_durable_attempt_state(
                case_root / "attempt_state.json",
                cfg={**cfg, "scientific_invocation_count": 1, "canonical_state": "SCIENTIFIC_SOLVER_RUNNING"},
                lease=lease, setup_path=pre, runtime_fsp=run, native_target=native,
                post_target=post, raw_target=case_root / "raw_result.json",
                logs=[case_root / "solver.log"], adapter_identity=adapter_identity,
                persistence_preflight=preflight,
                expected_process_identity=evidence,
                scientific_contract_hash=cfg["physical_contract_hash"],
                solver_entry_timestamp=entry_timestamp,
            )
            allocator.mark_entered(lease)
            if backend_type == "GPU":
                emit(cfg, "GPU_ENGINE_ENTRY_CONFIRMED", slot_id=lease.slot_id, entry_evidence=evidence)
            queue_state(db, cfg, "SCIENTIFIC_SOLVER_ENTERED")
            emit(cfg, "SCIENTIFIC_SOLVER_ENTERED", slot_id=lease.slot_id, mpi_processes=12, threads=1, entry_evidence=evidence)
            queue_state(db, cfg, "SCIENTIFIC_SOLVER_RUNNING")
            emit(cfg, "SCIENTIFIC_SOLVER_RUNNING", slot_id=lease.slot_id)
        resource_request = ResourceRequest.from_payload(cfg)
        resource_monitor = RuntimeResourceMonitor(
            resource_request,
            case_root / "resource_samples.jsonl",
            interval_s=float(cfg.get("resource_monitor_interval_s", 30.0)),
        )
        resource_monitor.start()
        launch_snapshot = read_resource_snapshot() if (resource_request is not None or backend_type is not None) else None
        def guarded_start(start_child):
            nonlocal entered
            from shared_fdtd.control_v3.launch_authority import ScientificLaunchAuthority
            from shared_fdtd.control_v3.allocator import AdmissionGateBlocked as LaunchAdmissionBlocked
            authority = ScientificLaunchAuthority(db)
            def invoke_claimed(claim):
                nonlocal entered
                # Conservative entry is already durable in the DB before this
                # callback. A bookkeeping error cannot make this retryable.
                entered = True
                cfg["launch_id"] = claim["launch_id"]
                ledger.update({"solver_entered": True, "launch_id": claim["launch_id"],
                               "entered_timestamp_utc": claim["claimed_at"],
                               "run_invocation_count": 1, "launch_identity": claim})
                write(ledger_path, ledger)
                emit(cfg, "SCIENTIFIC_LAUNCH_CLAIMED", launch_identity=claim)
                return start_child()
            try:
                claim = authority.claim(
                    lease, pre_fsp_hash=cfg["pre_fsp_sha256"],
                    physical_contract_hash=cfg["physical_contract_hash"],
                    command=getattr(start_child, "launch_command", ["lumapi.FDTD.run", str(run)]),
                    executable=getattr(start_child, "launch_executable", sys.executable),
                    resource_request=resource_request, resource_snapshot=launch_snapshot,
                    resource_policy=cfg.get("resource_policy"), backend_type=backend_type,
                    exact_permit_id=cfg.get("exact_launch_permit_id"),
                )
            except LaunchAdmissionBlocked as exc:
                allocator.release_provisional(lease, "SCIENTIFIC_LAUNCH_ADMISSION_BLOCKED")
                raise AdmissionGateBlocked({"eligible": False, "reason": str(exc)}) from exc
            entered = True
            allocator.mark_entered(lease, launch_identity=claim)
            return invoke_claimed(claim)
        if is_pw:
            if backend_type == "GPU":
                fd.close()
                fd = None
                run_standalone_gpu_and_confirm_completion(
                    {**cfg, "run_fsp": str(run)},
                    confirm_entry,
                    launcher_id=LAUNCHER_ID + ":GPU_STANDALONE",
                    launch_guard=guarded_start,
                )
                load_fd = lumapi.FDTD(str(run), hide=True)
                validate_load(load_fd, cfg, is_pw)
                fd, load_fd = load_fd, None
                gpu_completion_barrier = True
            else:
                run_and_confirm_entry(fd, cfg, confirm_entry, launch_guard=guarded_start)
        else:
            guarded_start(fd.run)
            confirm_entry({"observation": "legacy_api_run_returned"})
        if not gpu_completion_barrier:
            returned = True
            ledger.update({"solver_returned": True, "solver_returned_timestamp_utc": now()})
            write(ledger_path, ledger)
            emit(cfg, "SOLVER_RETURNED", slot_id=lease.slot_id)
        if backend_type == "GPU":
            emit(cfg, "NATIVE_TRUTH_PERSISTING", runtime_fsp=str(run))
            fd.close(); fd = None
            ready_manifest = wait_for_bundle_ready(
                run,
                timeout_s=float(cfg.get("gpu_bundle_ready_timeout_s", 120.0)),
                poll_s=float(cfg.get("gpu_bundle_ready_poll_s", 0.5)),
                stable_polls=int(cfg.get("gpu_bundle_ready_stable_polls", 2)),
                readiness_validator=lambda candidate: fresh_load_validate_path(candidate, cfg, is_pw),
            )
            emit(
                cfg,
                "GPU_NATIVE_BUNDLE_READY",
                runtime_fsp=str(run),
                sidecar_paths=ready_manifest.get("sidecar_paths", []),
            )
            native_record = persist_gpu_bundle(
                run,
                native,
                staging_root=case_root / "bundle_stage_native",
                require_sidecars=True,
                validator=lambda staged: fresh_load_validate_path(staged, cfg, is_pw),
            )
            native = Path(native_record["fsp_path"])
        else:
            emit(cfg, "NATIVE_TRUTH_PERSISTING", runtime_fsp=str(run))
            native_record = save_and_verify(fd, native)
        emit(
            cfg,
            "NATIVE_TRUTH_DURABLE",
            native_fsp=str(native),
            native_fsp_sha256=native_record["sha256"],
            native_bundle_manifest=native_record.get("manifest"),
        )
        if backend_type != "GPU":
            fd.close(); fd = None
        load_fd = lumapi.FDTD(str(native), hide=True)
        validate_load(load_fd, cfg, is_pw)
        emit(cfg, "NATIVE_TRUTH_LOAD_ONLY_VALIDATED", native_fsp=str(native), native_fsp_sha256=native_record["sha256"])
        load_fd.close(); load_fd = None
        if gpu_completion_barrier:
            returned = True
            ledger.update({"solver_returned": True, "solver_returned_timestamp_utc": now()})
            write(ledger_path, ledger)
            emit(cfg, "SOLVER_RETURNED", slot_id=lease.slot_id)
        if backend_type == "GPU":
            post_record = persist_gpu_bundle(
                native,
                post,
                staging_root=case_root / "bundle_stage_post",
                require_sidecars=True,
                validator=lambda staged: fresh_load_validate_path(staged, cfg, is_pw),
            )
            post = Path(post_record["fsp_path"])
        else:
            post_record = persist_and_verify(native, post)
        write(case_root / "post_fsp_verification.json", {"status": "PASS", **post_record, "load_only": True, "source_native_fsp": str(native), "source_native_sha256": native_record["sha256"]})
        load_fd = lumapi.FDTD(str(post), hide=True)
        validate_load(load_fd, cfg, is_pw)
        queue_state(db, cfg, "POSTPROCESSING")
        emit(cfg, "POSTPROCESSING", post_fsp=str(post))
        if is_pw:
            raw, metrics, paths = pw_postprocess(load_fd, cfg, case_root)
            transfer = {"schema": "APCD_PW_STANDARDIZED_DB_PAYLOAD_V1", "wavelength_count": len(metrics.get("rows", [])), "projection": str(paths["projection"]), "orders": str(paths["angular"]), "raw_complex_fields": str(paths["raw_fields"]), "canonical_state_npz": str(paths["state_npz"]), "canonical_state_metadata": str(paths["state_metadata"])}
        else:
            contract = mod.contract(cfg["case"])
            contract["attempt_id"] = cfg["attempt"]
            raw, metrics, paths = g.extract_and_project(load_fd, {"geometry_id": cfg["case"]}, post, case_root)
            raw["attempt_id"] = cfg["attempt"]
            raw["task_id"] = cfg["task"]
            ensure_parent(paths["raw_json"])
            g.atomic_json(paths["raw_json"], raw)
        queue_state(db, cfg, "POST_FSP_VALID")
        emit(cfg, "POST_FSP_VALID", post_fsp=str(post), post_fsp_sha256=sha(post))
        queue_state(db, cfg, "RAW_VALID")
        emit(cfg, "RAW_VALID", raw_result=str(paths["raw_json"]), raw_sha256=sha(paths["raw_json"]))
        if not is_pw:
            transfer = g.transfer_metrics(cfg["case"], metrics, paths["projection"])
        write(case_root / "scientific_validation.json", {"status": "PASS", "load_only": "PASS", "raw_fields": "PASS", "angular": "PASS", "projection": "PASS", "transfer_metrics": transfer})
        queue_state(db, cfg, "SCIENTIFIC_VALID")
        emit(cfg, "SCIENTIFIC_VALID", raw_result=str(paths["raw_json"]), projection=str(paths["projection"]))
        archive = {"status": "PASS", "case_id": cfg["case"], "attempt_id": cfg["attempt"], "post_fsp": str(post), "post_fsp_sha256": sha(post), "raw_json": str(paths["raw_json"]), "raw_json_sha256": sha(paths["raw_json"]), "raw_complex_fields": str(paths.get("raw_fields")) if is_pw else None, "canonical_state_npz": str(paths.get("state_npz")) if is_pw else None, "canonical_state_metadata": str(paths.get("state_metadata")) if is_pw else None, "angular": str(paths["angular"]), "projection": str(paths["projection"]), "training_admitted": False}
        archive_stage = case_root / "archive_staging" / f"HF_ARCHIVE_MANIFEST_{artifact_tag}.json"
        archive_path = case_root / "HF_ARCHIVE_MANIFEST.json"
        write(archive_stage, archive)
        ensure_parent(archive_path)
        shutil.copy2(archive_stage, archive_path)
        if not sha256_equal(sha(archive_stage), sha(archive_path)):
            raise RuntimeError("HF_ARCHIVE_MANIFEST_SHA_MISMATCH")
        queue_state(db, cfg, "HF_ARCHIVED")
        emit(cfg, "HF_ARCHIVED", archive=str(archive_path), archive_staging=str(archive_stage))
        allocator.release_pending(lease, "SCIENTIFIC_VALID_TRUTH_DURABLE")
        queue_state(db, cfg, "RELEASE_PENDING")
        emit(cfg, "RELEASE_PENDING", reason="SCIENTIFIC_VALID_TRUTH_DURABLE")
        prior_state = json.loads((case_root / "attempt_state.json").read_text(encoding="utf-8"))
        write_durable_attempt_state(
            case_root / "attempt_state.json",
            cfg={**cfg, "scientific_invocation_count": 1, "canonical_state": "SCIENTIFIC_VALID"},
            lease=lease, setup_path=pre, runtime_fsp=run, native_target=native,
            post_target=post, raw_target=case_root / "raw_result.json",
            logs=[case_root / "solver.log"], adapter_identity=adapter_identity,
            persistence_preflight=prior_state.get("persistence_preflight") or preflight,
            expected_process_identity=prior_state.get("expected_process_identity"),
            scientific_contract_hash=cfg["physical_contract_hash"],
            solver_entry_timestamp=prior_state.get("solver_entry_timestamp_utc"),
            canonical_state="SCIENTIFIC_VALID",
        )
        allocator.release_owned(lease, scientific_terminal="SCIENTIFIC_VALID")
        queue_state(db, cfg, "RELEASED")
        emit(cfg, "RELEASED", slot_id=lease.slot_id)
        write(case_root / "terminal.json", {"status": "SCIENTIFIC_VALID", "case_id": cfg["case"], "attempt_id": cfg["attempt"], "solver_entered": True, "solver_returned": True, "solver_entry_count": 1, "rerun": False, "native_fsp": str(native), "native_fsp_sha256": native_record["sha256"], "post_fsp": str(post), "post_fsp_sha256": sha(post), "raw_result": str(paths["raw_json"]), "raw_result_sha256": sha(paths["raw_json"]), "slot_id": lease.slot_id, "slot_release_status": "RELEASED", "completed_utc": now(), "transfer_metrics": transfer})
        if resource_monitor is not None:
            resource_monitor.stop()
            resource_monitor = None
        print(json.dumps({"status": "PASS", "case": cfg["case"], "attempt": cfg["attempt"], "slot": lease.slot_id, "post_fsp": str(post), "raw": str(paths["raw_json"])}, ensure_ascii=False), flush=True)
    except Exception as exc:
        if resource_monitor is not None:
            try:
                resource_monitor.stop()
            except BaseException:
                pass
        if load_fd is not None:
            try: load_fd.close()
            except Exception: pass
        if fd is not None:
            if not entered or returned:
                try: fd.close()
                except Exception: pass
            # An exception after scientific entry must not close the live owner
            # merely because bookkeeping or persistence failed.
        if isinstance(exc, AdmissionGateBlocked):
            write(case_root / "admission_revalidation_blocked.json", exc.evidence)
            emit(cfg, "FINAL_LAUNCH_REVALIDATION_BLOCKED", evidence=exc.evidence)
            queue_state(db, cfg, "WAIT_RESOURCE_CAPACITY")
            print(json.dumps({"status": "WAIT_RESOURCE_CAPACITY", "case": cfg["case"], "attempt": cfg["attempt"], "solver_entered": False, "admission": exc.evidence}, ensure_ascii=False), flush=True)
            return
        if isinstance(exc, AdmissionGateBlocked):
            write(case_root / "admission_revalidation_blocked.json", exc.evidence)
            emit(cfg, "FINAL_LAUNCH_REVALIDATION_BLOCKED", evidence=exc.evidence)
            queue_state(db, cfg, "WAIT_RESOURCE_CAPACITY")
            print(json.dumps({"status": "WAIT_RESOURCE_CAPACITY", "case": cfg["case"], "attempt": cfg["attempt"], "solver_entered": False, "admission": exc.evidence}, ensure_ascii=False), flush=True)
            return
        if isinstance(exc, AdmissionGateBlocked):
            write(case_root / "admission_revalidation_blocked.json", exc.evidence)
            emit(cfg, "FINAL_LAUNCH_REVALIDATION_BLOCKED", evidence=exc.evidence)
            queue_state(db, cfg, "WAIT_RESOURCE_CAPACITY")
            print(json.dumps({"status": "WAIT_RESOURCE_CAPACITY", "case": cfg["case"], "attempt": cfg["attempt"], "solver_entered": False, "admission": exc.evidence}, ensure_ascii=False), flush=True)
            return
        from shared_fdtd.control_v3.launch_authority import LaunchAlreadyClaimed
        if isinstance(exc, LaunchAlreadyClaimed):
            # Another committed launch is authoritative. Never release or
            # overwrite its queue/terminal state from this duplicate host.
            raise
        status = persistence_failure_status(returned) if returned else ("FAILED_AFTER_ENTRY" if entered else "FAILED_PREENTRY")
        queue_failure_state = "FAILED_AFTER_ENTRY" if entered else "FAILED_PREENTRY"
        write(case_root / "terminal_failure.json", {"status": status, "queue_state": queue_failure_state, "failure_class": status, "case_id": cfg["case"], "attempt_id": cfg["attempt"], "solver_entered": entered, "solver_returned": returned, "error": repr(exc), "rerun": False, "timestamp_utc": now()})
        emit(cfg, status, error=repr(exc), solver_entered=entered, solver_returned=returned, rerun=False)
        try:
            if entered:
                allocator.quarantine_owned(lease, repr(exc))
                queue_state(db, cfg, queue_failure_state)
            else:
                allocator.release_owned(lease, scientific_terminal="FAILED_PREENTRY")
                queue_state(db, cfg, "FAILED_PREENTRY")
        except Exception as release_exc:
            emit(cfg, "CONTROL_PLANE_DEGRADED", error=repr(release_exc), original_error=repr(exc))
            queue_state(db, cfg, "AMBIGUOUS_QUARANTINED")
        print(json.dumps({"status": status, "case": cfg["case"], "attempt": cfg["attempt"], "error": repr(exc)}, ensure_ascii=False), flush=True)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    cfg = json.loads(Path(parser.parse_args().config).read_text(encoding="utf-8"))
    from shared_fdtd.engine.attempt_guard import exclusive_attempt
    with exclusive_attempt(cfg):
        return _main_owned(cfg)


def _record_uncaught_exception(exc):
    context = (_EARLY_CONTEXT or {}).get("context", {})
    cfg = (_EARLY_CONTEXT or {}).get("cfg", {})
    runtime = (_EARLY_CONTEXT or {}).get("runtime")
    attempt_root = (_EARLY_CONTEXT or {}).get("attempt_root")
    entered = False
    for root in (runtime, attempt_root):
        if root is None:
            continue
        try:
            events = (Path(root) / "events.jsonl").read_text(encoding="utf-8")
            entered = entered or "SCIENTIFIC_SOLVER_ENTERED" in events or "GPU_ENGINE_ENTRY_CONFIRMED" in events
        except OSError:
            pass
    evidence = {
        **context,
        "event_type": "HOST_EXIT_PREENTRY" if not entered else "HOST_EXIT_AFTER_ENTRY",
        "scientific_solver_entry_count": 1 if entered else 0,
        "solver_entered": entered,
        "exception": repr(exc),
        "traceback": traceback.format_exc(),
        "exit_detection_timestamp_utc": now(),
        "return_code": 1,
    }
    for root in (runtime, attempt_root):
        if root is None:
            continue
        try:
            write(Path(root) / "host_uncaught_exception.json", evidence)
            _early_event_path(Path(root) / "events.jsonl", evidence["event_type"], **evidence)
        except BaseException:
            pass


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        from shared_fdtd.control_v3.launch_authority import LaunchAlreadyClaimed
        if not isinstance(exc, LaunchAlreadyClaimed):
            _record_uncaught_exception(exc)
        raise
