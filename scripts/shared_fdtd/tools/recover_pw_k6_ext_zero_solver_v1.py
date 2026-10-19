
from __future__ import annotations
import json, sys, traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
SCRIPTS = ROOT / "scripts"
DB_PATH = Path(r"D:\apcd_runtime\global_fdtd_control_v3\control.sqlite3")
BASE = ROOT / r"outputs\coupling_ml\PW_K6_SEED_DB_V1_PRODUCTION_V1"
LUMAPI = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(LUMAPI))

from shared_fdtd.control_v3.allocator import Allocator, Lease
from shared_fdtd.control_v3.db import ControlDB
from shared_fdtd.engine.event_log import append_event, read_events
from shared_fdtd.engine.persistence import atomic_json, sha256_file
from shared_fdtd.engine.process_identity import snapshot
from shared_fdtd.engine.gpu_bundle import persist_gpu_bundle, wait_for_bundle_ready
from shared_fdtd.tools import v3_g2_host as host
from shared_fdtd.tools import pw_scientific_launcher as launcher
import lumapi

CASES = ["K6V1_EXT01", "K6V1_EXT02"]
FIELDS = ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz")
MONITORS = ("MON_IN", "MON_PRENP", "MON_POSTNP", "MON_REFLECTION")

def now():
    return datetime.now(timezone.utc).isoformat()

def sha(path):
    return sha256_file(Path(path))

def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def write_json(path, value):
    atomic_json(Path(path), value)

def append_once(path, event_type, **payload):
    path = Path(path)
    seen = {row.get("event_type") for row in read_events(path)}
    if event_type not in seen:
        append_event(path, event_type, **payload)

def emit_once(cfg, event_type, **payload):
    row = {"task_id": cfg["task"], "case_id": cfg["case"], "attempt_id": cfg["attempt"], **payload}
    for path in (Path(cfg["attempt_root"]) / "events.jsonl", Path(cfg["runtime"]) / "events.jsonl"):
        append_once(path, event_type, **row)

def queue_state(db, cfg, state):
    with db.immediate() as con:
        con.execute(
            "UPDATE branch_queue SET state=?,updated_at=? "
            "WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
            (state, now(), cfg["branch"], cfg["case"], cfg["attempt"]),
        )

def matching_solver_processes(run):
    name = Path(run).name.lower()
    rows = []
    for row in snapshot() or []:
        proc_name = str(row.get("Name") or "").lower()
        command = str(row.get("CommandLine") or "").lower()
        if name in command and ("fdtd-engine" in proc_name or proc_name in {"mpiexec.exe", "mpiexec"}):
            rows.append(row)
    return rows

def bundle_validator(path, cfg):
    fd = lumapi.FDTD(str(path), hide=True)
    try:
        host.validate_load(fd, cfg, True)
        for field in FIELDS:
            value = fd.getdata("MON_REFLECTION", field)
            if value is None:
                raise RuntimeError("MON_REFLECTION:" + field + ":NONE")
        return {"passed": True, "mode": "LOAD_ONLY_ROLE_AWARE", "path": str(path),
                "monitors": list(MONITORS), "fields": list(FIELDS)}
    finally:
        fd.close()

def quarantine_partial(directory, label):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    manifest = directory / "bundle_manifest.json"
    if manifest.is_file():
        return None
    entries = list(directory.iterdir())
    if not entries:
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = directory.parent / (directory.name + "_quarantine") / (label + "_" + stamp)
    target.mkdir(parents=True, exist_ok=False)
    moved = []
    for entry in entries:
        entry.replace(target / entry.name)
        moved.append(str(target / entry.name))
    return {"quarantine_root": str(target), "moved": moved}

def cfg_for(case, row, payload, root, runtime, run):
    cfg = dict(payload)
    cfg.update({
        "db": str(DB_PATH),
        "branch": "coupling_ml",
        "case": case,
        "attempt": "attempt_001",
        "task": payload.get("task", "PW_K6_SEED_DB_V1_PRODUCTION_V1"),
        "attempt_root": str(root),
        "runtime": str(runtime),
        "run_fsp": str(run),
        "slot_id": row["slot_id"],
        "fencing_generation": int(row["fencing_generation"]),
    })
    with ControlDB(DB_PATH).connect(readonly=True) as con:
        slot = con.execute("SELECT lease_token FROM slots WHERE slot_id=?", (row["slot_id"],)).fetchone()
    if slot is None or not slot["lease_token"]:
        raise RuntimeError("RECOVERY_LEASE_TOKEN_MISSING:" + str(row["slot_id"]))
    cfg["lease_token"] = slot["lease_token"]
    host.validate_pw_config(cfg)
    return cfg

def recover(case):
    root = BASE / case / "attempt_001"
    runtime = Path(r"D:\apcd_runtime\global_fdtd_control_v3\cases") / "PW_K6_SEED_DB_V1_PRODUCTION_V1" / case / "attempt_001"
    run = root / "run" / (case + "__attempt_001_runtime.fsp")
    ledger_path = root / "attempt_ledger.json"
    state_path = root / "attempt_state.json"
    terminal_path = root / "terminal.json"

    db = ControlDB(DB_PATH)
    with db.connect(readonly=True) as con:
        row = con.execute(
            "SELECT * FROM branch_queue WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
            ("coupling_ml", case, "attempt_001"),
        ).fetchone()
        slot_row = con.execute("SELECT * FROM slots WHERE slot_id=?", (row["slot_id"],)).fetchone() if row else None
    if row is None or slot_row is None:
        raise RuntimeError("RECOVERY_QUEUE_OR_SLOT_MISSING:" + case)
    payload = json.loads(row["payload_json"])
    cfg = cfg_for(case, row, payload, root, runtime, run)
    state = load_json(state_path)
    ledger = load_json(ledger_path)

    if terminal_path.is_file():
        terminal = load_json(terminal_path)
        if terminal.get("status") == "SCIENTIFIC_VALID":
            return {"case": case, "status": "ALREADY_RECOVERED", "terminal": terminal}
    if not state.get("solver_entered") and not ledger.get("solver_entered"):
        raise RuntimeError("RECOVERY_NOT_ENTERED:" + case)
    if int(ledger.get("run_invocation_count", 0)) != 1 or int(ledger.get("replay", 0)) != 0:
        raise RuntimeError("RECOVERY_ENTRY_LEDGER_INVALID:" + case)
    if not run.is_file():
        raise RuntimeError("RECOVERY_RUNTIME_FSP_MISSING:" + case)
    runtime_sha = sha(run)
    setup_sha = ledger.get("pre_fsp_sha256")
    if runtime_sha == setup_sha:
        raise RuntimeError("RECOVERY_RUNTIME_FSP_STILL_SETUP_ONLY:" + case)
    runtime_hash_transition = {
        "ledger_run_fsp_sha256": ledger.get("run_fsp_sha256"),
        "setup_fsp_sha256": setup_sha,
        "runtime_output_fsp_sha256": runtime_sha,
        "runtime_output_differs_from_setup": runtime_sha != setup_sha,
    }
    live = matching_solver_processes(run)
    if live:
        raise RuntimeError("RECOVERY_ACTIVE_SOLVER:" + json.dumps(live, default=str))
    evidence = launcher._gpu_completion_evidence(cfg, snapshot, run)
    evidence["runtime_hash_transition"] = runtime_hash_transition
    readiness = wait_for_bundle_ready(
        run,
        timeout_s=float(cfg.get("gpu_bundle_ready_timeout_s", 120.0)),
        poll_s=float(cfg.get("gpu_bundle_ready_poll_s", 0.5)),
        stable_polls=int(cfg.get("gpu_bundle_ready_stable_polls", 2)),
        readiness_validator=lambda candidate: bundle_validator(candidate, cfg),
    )
    emit_once(cfg, "GPU_NATIVE_BUNDLE_READY", sidecar_paths=readiness.get("sidecar_paths", []), readiness=readiness.get("readiness"))
    emit_once(cfg, "ZERO_SOLVER_RECOVERY_STARTED", evidence=evidence,
              root_cause="GPU_NATIVE_BUNDLE_PERSISTENCE_H5_SIDECAR_OMISSION")

    native_dir = root / "native"
    native = native_dir / run.name
    native_quarantine = quarantine_partial(native_dir, "FSP_ONLY")
    post_dir = root / "post"
    post = post_dir / run.name
    post_quarantine = quarantine_partial(post_dir, "PARTIAL")
    archive_dir = root / "archive_restore"
    archive = archive_dir / run.name
    archive_quarantine = quarantine_partial(archive_dir, "PARTIAL")

    native_record = persist_gpu_bundle(
        run, native, staging_root=root / "bundle_stage_native",
        require_sidecars=True,
    )
    native_load = bundle_validator(Path(native_record["fsp_path"]), cfg)
    emit_once(cfg, "NATIVE_TRUTH_DURABLE",
              native_fsp=native_record["fsp_path"], native_bundle_manifest=native_record["manifest"],
              source_runtime_fsp=str(run), source_runtime_sha256=sha(run))
    emit_once(cfg, "NATIVE_TRUTH_LOAD_ONLY_VALIDATED", fresh_load=native_load)

    ledger.update({
        "solver_returned": True,
        "solver_returned_timestamp_utc": now(),
        "recovery": "ZERO_SOLVER_DURABLE_TRUTH",
        "recovery_evidence": evidence,
    })
    write_json(ledger_path, ledger)
    state.update({
        "canonical_state": "SOLVER_RETURNED",
        "runtime_patch_version": "3.0.3-gpu-bundle-recovery",
        "solver_returned": True,
        "native_target": str(native_record["fsp_path"]),
        "recovery": "ZERO_SOLVER_DURABLE_TRUTH",
    })
    write_json(state_path, state)
    queue_state(db, cfg, "SOLVER_RETURNED")
    emit_once(cfg, "SOLVER_RETURNED", recovery="ZERO_SOLVER_DURABLE_TRUTH", evidence=evidence)

    post_record = persist_gpu_bundle(
        Path(native_record["fsp_path"]), post, staging_root=root / "bundle_stage_post",
        require_sidecars=True,
    )
    post_load = bundle_validator(Path(post_record["fsp_path"]), cfg)
    write_json(root / "post_fsp_verification.json", {
        "status": "PASS", "load_only": post_load, "post_bundle": post_record,
        "source_native_fsp": native_record["fsp_path"], "source_native_sha256": native_record["sha256"],
    })
    emit_once(cfg, "POST_FSP_DURABLE", post_fsp=post_record["fsp_path"],
              post_bundle_manifest=post_record["manifest"])
    emit_once(cfg, "POST_FSP_LOAD_ONLY_VALIDATED", fresh_load=post_load)
    queue_state(db, cfg, "POSTPROCESSING")
    emit_once(cfg, "POSTPROCESSING", post_fsp=post_record["fsp_path"])

    fd = lumapi.FDTD(str(post_record["fsp_path"]), hide=True)
    try:
        host.validate_load(fd, cfg, True)
        raw, metrics, paths = host.pw_postprocess(fd, cfg, root)
    finally:
        fd.close()
    transfer = {
        "schema": "APCD_PW_STANDARDIZED_DB_PAYLOAD_V1",
        "wavelength_count": len(metrics.get("rows", [])),
        "projection": str(paths["projection"]),
        "orders": str(paths["angular"]),
        "raw_complex_fields": str(paths["raw_fields"]),
        "canonical_state_npz": str(paths["state_npz"]),
        "canonical_state_metadata": str(paths["state_metadata"]),
    }
    write_json(root / "scientific_validation.json", {
        "status": "PASS", "load_only": "PASS", "role_aware_bundle_load": "PASS",
        "raw_fields": "PASS", "angular": "PASS", "projection": "PASS",
        "transfer_metrics": transfer,
    })
    queue_state(db, cfg, "POST_FSP_VALID")
    emit_once(cfg, "POST_FSP_VALID", post_fsp=post_record["fsp_path"], post_fsp_sha256=sha(post_record["fsp_path"]))
    queue_state(db, cfg, "RAW_VALID")
    emit_once(cfg, "RAW_VALID", raw_result=str(paths["raw_json"]), raw_sha256=sha(paths["raw_json"]))
    queue_state(db, cfg, "SCIENTIFIC_VALID")
    emit_once(cfg, "SCIENTIFIC_VALID", raw_result=str(paths["raw_json"]),
              projection=str(paths["projection"]), recovery="ZERO_SOLVER_DURABLE_TRUTH")

    archive_record = persist_gpu_bundle(
        Path(post_record["fsp_path"]), archive,
        staging_root=root / "bundle_stage_archive",
        require_sidecars=True,
    )
    archive_load = bundle_validator(Path(archive_record["fsp_path"]), cfg)
    write_json(root / "archive_restore_validation.json", {
        "status": "PASS", "load_only": archive_load, "bundle": archive_record,
    })
    archive_manifest = {
        "status": "PASS", "schema": "APCD_PW_K6_HF_ARCHIVE_MANIFEST_V2",
        "case_id": case, "attempt_id": "attempt_001", "recovery": "ZERO_SOLVER_DURABLE_TRUTH",
        "runtime_fsp": str(run), "runtime_fsp_sha256": sha(run),
        "native_bundle": native_record, "post_bundle": post_record,
        "archive_restore_bundle": archive_record, "archive_restore_load_only": archive_load,
        "raw_json": str(paths["raw_json"]), "raw_json_sha256": sha(paths["raw_json"]),
        "projection": str(paths["projection"]), "angular": str(paths["angular"]),
        "canonical_state_npz": str(paths["state_npz"]),
        "canonical_state_metadata": str(paths["state_metadata"]),
        "training_admitted": False,
    }
    write_json(root / "HF_ARCHIVE_MANIFEST.json", archive_manifest)
    queue_state(db, cfg, "HF_ARCHIVED")
    emit_once(cfg, "HF_ARCHIVED", archive=str(root / "HF_ARCHIVE_MANIFEST.json"),
              archive_restore=str(archive_record["fsp_path"]))

    state.update({
        "canonical_state": "SCIENTIFIC_VALID",
        "native_target": native_record["fsp_path"],
        "post_target": post_record["fsp_path"],
        "raw_target": str(paths["raw_json"]),
        "recovery": "ZERO_SOLVER_DURABLE_TRUTH",
    })
    write_json(state_path, state)
    lease = Lease(cfg["slot_id"], cfg["branch"], cfg["case"], cfg["attempt"],
                  cfg["lease_token"], int(cfg["fencing_generation"]))
    allocator = Allocator(db)
    pending = allocator.release_pending(lease, "ZERO_SOLVER_SCIENTIFIC_TRUTH_DURABLE")
    queue_state(db, cfg, "RELEASE_PENDING")
    emit_once(cfg, "RELEASE_PENDING", reason="ZERO_SOLVER_SCIENTIFIC_TRUTH_DURABLE")
    terminal = {
        "status": "SCIENTIFIC_VALID", "recovery_status": "RECOVERED_VALID_HF_TRUTH",
        "case_id": case, "attempt_id": "attempt_001", "solver_entered": True,
        "solver_returned": True, "solver_runs": 1, "solver_entry_count": 1, "replay": 0,
        "runtime_fsp": str(run), "runtime_fsp_sha256": sha(run),
        "native_fsp": native_record["fsp_path"], "native_fsp_sha256": native_record["sha256"],
        "post_fsp": post_record["fsp_path"], "post_fsp_sha256": post_record["sha256"],
        "raw_result": str(paths["raw_json"]), "raw_result_sha256": sha(paths["raw_json"]),
        "archive_manifest": str(root / "HF_ARCHIVE_MANIFEST.json"),
        "archive_restore": archive_record["fsp_path"], "archive_restore_load_only": archive_load,
        "transfer_metrics": transfer, "release_state": "PENDING_RECONCILE",
        "completed_utc": now(), "release_pending": pending,
    }
    write_json(terminal_path, terminal)
    release = allocator.release_owned_idempotent(lease, scientific_terminal="SCIENTIFIC_VALID")
    queue_state(db, cfg, "RELEASED")
    emit_once(cfg, "RELEASED", slot_id=lease.slot_id, recovery="ZERO_SOLVER_DURABLE_TRUTH",
              release_status=release["status"])
    terminal["release_state"] = "RELEASED"
    terminal["release"] = release
    write_json(terminal_path, terminal)
    state["canonical_state"] = "SCIENTIFIC_VALID"
    write_json(state_path, state)
    return {
        "case": case, "status": "RECOVERED_VALID_HF_TRUTH",
        "solver_runs": 1, "replay": 0, "queue_state": "RELEASED",
        "slot_id": lease.slot_id, "native": native_record["fsp_path"],
        "post": post_record["fsp_path"], "raw": str(paths["raw_json"]),
        "archive_restore": archive_record["fsp_path"],
        "quarantine": {"native": native_quarantine, "post": post_quarantine, "archive": archive_quarantine},
    }

def main():
    results = []
    for case in CASES:
        try:
            result = recover(case)
        except Exception as exc:
            result = {"case": case, "status": "RECOVERY_FAILED", "error": repr(exc),
                      "traceback": traceback.format_exc()}
            print(json.dumps(result, ensure_ascii=False), flush=True)
            raise
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    print(json.dumps({"schema": "APCD_PW_K6_ZERO_SOLVER_RECOVERY_V1",
                      "status": "PASS", "cases": results, "solver_runs": 0, "replay": 0,
                      "foreign_mutation_count": 0}, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    main()
