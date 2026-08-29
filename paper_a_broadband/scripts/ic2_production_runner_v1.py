from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import traceback
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("PAPER_A_ROOT", r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1"))
BASE = ROOT / "paper_a_broadband"
RUNTIME = BASE / "runtime/ic2_solver_ready"
REPORT = BASE / "reports/ic2_solver_ready_runner"
AUTHORITY_PATH = BASE / "authority/ic2_solver_ready_prefsp_authority_v1.json"
BUILDER_PATH = BASE / "scripts/ic2_solver_ready_prefsp_builder_v1.py"
SCHEDULER_PATH = BASE / "templates/lp_fulljones/apcd_global_fdtd_slot_v1.py"
SLOT_REGISTRY = Path(r"D:/project/apcd_global_fdtd_slot_registry_v1.json")
BRANCH = "work/paper-a-lp-cp-broadband-v1"
CASE_ID = "IC2_TOPWELL_Y"
ATTEMPT_ID = "attempt_001"
PROCESSES, THREADS, MAX_NEW_ENTRIES = 12, 1, 1
GLOBAL_CAPACITY = 3


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha_obj(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def append_log(path: Path, event: str, **fields: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"timestamp_utc": now(), "event": event, **fields}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_builder():
    spec = importlib.util.spec_from_file_location("ic2_prefsp_builder", BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("IC2_BUILDER_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_authority() -> dict[str, Any]:
    if not AUTHORITY_PATH.exists():
        raise RuntimeError("IC2_AUTHORITY_MISSING")
    authority = load_json(AUTHORITY_PATH)
    if authority.get("status") != "PASS_SOLVER_READY_PREFSP" or authority.get("case_id") != CASE_ID:
        raise RuntimeError("IC2_AUTHORITY_NOT_PASS")
    if authority.get("authorization", {}).get("authorization_used"):
        raise RuntimeError("IC2_AUTHORIZATION_ALREADY_USED")
    if authority.get("production_runner", {}).get("max_new_fdtd_entries") != MAX_NEW_ENTRIES:
        raise RuntimeError("IC2_BUDGET_AUTHORITY_CONFLICT")
    return authority


def load_scheduler():
    spec = importlib.util.spec_from_file_location("ic2_scheduler", SCHEDULER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("SCHEDULER_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_registry() -> dict[str, Any]:
    if not SLOT_REGISTRY.exists():
        return {"status": "REGISTRY_UNAVAILABLE", "path": str(SLOT_REGISTRY), "safe_to_execute": False}
    try:
        data = load_json(SLOT_REGISTRY)
        policy_ok = data.get("schema") == "APCD_GLOBAL_FDTD_SLOT_REGISTRY_V1" and data.get("policy_id") == "APCD_GLOBAL_FDTD_SCHEDULING_POLICY_V3"
        return {"status": "READ_ONLY", "path": str(SLOT_REGISTRY), "active_slots": data.get("active_slots", []),
                "global_capacity": data.get("global_capacity"), "policy_ok": policy_ok,
                "safe_to_execute": policy_ok and data.get("global_capacity") == GLOBAL_CAPACITY}
    except Exception as exc:
        return {"status": "REGISTRY_UNREADABLE", "path": str(SLOT_REGISTRY),
                "error": f"{type(exc).__name__}:{exc}", "safe_to_execute": False}


def resource_audit(scheduler: Any) -> dict[str, Any]:
    live = scheduler.live_job_snapshot()
    registry = read_registry()
    active_registry_fdtd = sum(
        str(row.get("solver_type", "FDTD")).upper() == "FDTD" for row in registry.get("active_slots", [])
    )
    try:
        import psutil
        vm = psutil.virtual_memory()
        free_ram_kb = int(vm.available // 1024)
        ram_source = "psutil.virtual_memory.available"
    except Exception:
        free_ram_kb = None
        ram_source = "unavailable"
    logical = os.cpu_count()
    unknown = live.get("unknown_solver_jobs", [])
    effective_active_fdtd = max(active_registry_fdtd, int(live.get("active_fdtd_jobs", 0)))
    return {
        "status": "READ_ONLY",
        "timestamp_utc": now(),
        "registry": {"active_slots": registry.get("active_slots", []), "global_capacity": registry.get("global_capacity"),
                      "policy_ok": registry.get("policy_ok", False)},
        "effective_active_fdtd": effective_active_fdtd,
        "global_fdtd_capacity": GLOBAL_CAPACITY,
        "active_rcwa": int(live.get("active_rcwa_jobs", 0)),
        "unknown_solver_jobs": unknown,
        "external_fluent_jobs": live.get("external_fluent_jobs", []),
        "live_jobs": live.get("jobs", []),
        "cpu_logical_processors": logical,
        "requested_mpi_processes": PROCESSES,
        "cpu_headroom_for_12_ranks": bool(logical and logical >= PROCESSES),
        "free_ram_kb": free_ram_kb,
        "free_ram_source": ram_source,
        "ram_headroom_obvious_hard_gate": free_ram_kb is not None and free_ram_kb > 0,
        "safe_headroom": bool(
            registry.get("safe_to_execute")
            and effective_active_fdtd + 1 <= GLOBAL_CAPACITY
            and not unknown
            and logical is not None
            and logical >= PROCESSES
            and free_ram_kb is not None
            and free_ram_kb > 0
        ),
    }


def dry_run() -> dict[str, Any]:
    authority = load_authority()
    builder = load_builder()
    pre = Path(authority["canonical_prefsp"]["path"])
    readback = builder.readback(pre) if pre.exists() else None
    validation = builder.validate_readback(readback) if readback is not None else {"prefsp_exists": False, "all": False}
    scheduler = load_scheduler()
    resources = resource_audit(scheduler)
    result = {
        "schema": "PAPER_A_IC2_PRODUCTION_RUNNER_DRY_RUN_V1",
        "status": "READY" if pre.exists() and validation.get("all") and sha_file(pre) == authority["canonical_prefsp"]["sha256"] else "BLOCKED_PREFSP_OR_READBACK",
        "case_id": CASE_ID,
        "pre_fsp": str(pre),
        "pre_fsp_sha256": sha_file(pre) if pre.exists() else None,
        "authority_prefsp_sha256": authority["canonical_prefsp"]["sha256"],
        "sha_match": pre.exists() and sha_file(pre) == authority["canonical_prefsp"]["sha256"],
        "validation": validation,
        "resource_audit": resources,
        "production_resources": {"mpi_processes": PROCESSES, "threads_per_process": THREADS, "max_new_fdtd_entries": MAX_NEW_ENTRIES},
        "solver_counters": {"run_called": False, "entered": 0, "active_fdtd": resources["effective_active_fdtd"], "rcwa": resources["active_rcwa"], "ml": 0, "hidden_auto_admission": False},
        "execute_requires": "--confirm-solver-entry",
        "no_dispatch_in_dry_run": True,
        "timestamp_utc": now(),
    }
    write_json(REPORT / "dry_run.json", result)
    return result


def execute(confirm: bool) -> dict[str, Any]:
    if not confirm:
        raise RuntimeError("EXPLICIT_CONFIRMATION_REQUIRED:--confirm-solver-entry")
    authority = load_authority()
    builder = load_builder()
    pre = Path(authority["canonical_prefsp"]["path"])
    expected_pre_sha = authority["canonical_prefsp"]["sha256"]
    if not pre.exists() or sha_file(pre) != expected_pre_sha:
        raise RuntimeError("IC2_PREFSP_SHA_MISMATCH_OR_PARENT_RUNTIME_MUTATED")
    readback = builder.readback(pre)
    validation = builder.validate_readback(readback)
    if not validation.get("all"):
        raise RuntimeError(f"IC2_PREFSP_READBACK_GATE:{json.dumps(validation, sort_keys=True)}")

    case_dir = RUNTIME / "production"
    case_dir.mkdir(parents=True, exist_ok=True)
    provenance_path = case_dir / f"{CASE_ID}_{ATTEMPT_ID}_provenance.json"
    post = case_dir / f"{CASE_ID}_{ATTEMPT_ID}_post.fsp"
    solver_input = case_dir / f"{CASE_ID}_{ATTEMPT_ID}_run_input.fsp"
    solver_log = case_dir / f"{CASE_ID}_{ATTEMPT_ID}_runner.log"
    if provenance_path.exists() or post.exists() or solver_input.exists():
        raise RuntimeError("REFUSE_REUSE_IC2_ATTEMPT_001_ARTIFACT")
    # Lumerical may materialize results into the loaded FSP. Use a byte-identical
    # run-input copy so the setup-only canonical pre-FSP remains immutable.
    shutil.copyfile(pre, solver_input)
    solver_input_sha = sha_file(solver_input)
    if solver_input_sha != expected_pre_sha:
        raise RuntimeError("IC2_RUN_INPUT_COPY_HASH_MISMATCH")
    scheduler = load_scheduler()
    pre_resources = resource_audit(scheduler)
    if not pre_resources["safe_headroom"]:
        result = {
            "schema": "PAPER_A_IC2_PRODUCTION_RUNNER_RESOURCE_GATE_V1",
            "status": "WAIT_RESOURCE_GATE",
            "case_id": CASE_ID,
            "solver_entered": 0,
            "solver_run_called": False,
            "resource_audit": pre_resources,
            "authorization_preserved_unused": True,
            "timestamp_utc": now(),
        }
        write_json(REPORT / "resource_gate.json", result)
        return result

    provenance = {
        "schema": "PAPER_A_IC2_PRODUCTION_RUNNER_PROVENANCE_V1",
        "case_id": CASE_ID,
        "attempt_id": ATTEMPT_ID,
        "status": "WAITING",
        "solver_entered": False,
        "solver_run_called": False,
        "pre_fsp": str(pre),
        "pre_fsp_sha256": expected_pre_sha,
        "solver_input_fsp": str(solver_input),
        "solver_input_fsp_sha256": solver_input_sha,
        "post_fsp": str(post),
        "solver_log": str(solver_log),
        "physical_contract_sha256": sha_obj(authority["physics_contract"]),
        "physics_semantic_fingerprint": authority["physics_semantic_fingerprint"],
        "integrated_instrumentation_fingerprint": authority["integrated_instrumentation_fingerprint"],
        "mpi_processes": PROCESSES,
        "threads_per_process": THREADS,
        "new_fdtd_budget": MAX_NEW_ENTRIES,
        "created_utc": now(),
        "no_auto_replay": True,
        "resource_audit_before_scheduler": pre_resources,
    }
    write_json(provenance_path, provenance)
    append_log(solver_log, "PROVENANCE_CREATED", case_id=CASE_ID, solver_entered=False, solver_run_called=False)
    lease = None
    fdtd = None
    try:
        try:
            lease = scheduler.GlobalSlotScheduler(SLOT_REGISTRY).acquire(
                branch=BRANCH,
                worktree=str(ROOT),
                task_id="PAPER_A_IC2_TOPWELL_Y_SINGLE_FDTD_V1",
                case_uid=CASE_ID,
                pid=os.getpid(),
                metadata={"task_class": "PAPER_A_IC2", "attempt_id": ATTEMPT_ID, "polarization": "y", "mpi_processes": PROCESSES, "threads_per_process": THREADS},
            )
        except scheduler.SlotError as exc:
            provenance.update({"status": "WAIT_RESOURCE_GATE", "resource_gate_reason": f"{type(exc).__name__}:{exc}", "solver_entered": False, "solver_run_called": False})
            write_json(provenance_path, provenance)
            append_log(solver_log, "RESOURCE_GATE", reason=provenance["resource_gate_reason"], solver_entered=False)
            return {"schema": "PAPER_A_IC2_PRODUCTION_RUNNER_RESOURCE_GATE_V1", "status": "WAIT_RESOURCE_GATE", "case_id": CASE_ID,
                    "solver_entered": 0, "solver_run_called": False, "resource_gate_reason": provenance["resource_gate_reason"],
                    "authorization_preserved_unused": True, "timestamp_utc": now()}
        provenance.update({"status": "SLOT_ACQUIRED", "slot_id": lease.slot_id,
                           "admission_snapshot": lease.record.get("admission_snapshot")})
        write_json(provenance_path, provenance)
        append_log(solver_log, "SLOT_ACQUIRED", slot_id=lease.slot_id, admission_snapshot=lease.record.get("admission_snapshot"))
        import lumapi
        fdtd = lumapi.FDTD(hide=True)
        fdtd.load(str(solver_input))
        fdtd.setresource("FDTD", 1, "processes", str(PROCESSES))
        if sha_file(solver_input) != expected_pre_sha:
            raise RuntimeError("IC2_RUN_INPUT_HASH_CHANGED_BEFORE_ENTRY")
        entered_utc = now()
        lease.mark_solver_entered(entered_utc)
        lease.start_heartbeat()
        provenance.update({"status": "ENTERED", "solver_entered": True, "solver_run_called": True, "entered_utc": entered_utc})
        write_json(provenance_path, provenance)
        append_log(solver_log, "SOLVER_ENTERED", solver_entered=True, solver_run_called=True, mpi_processes=PROCESSES, threads_per_process=THREADS)
        fdtd.run()
        returned_utc = now()
        fdtd.save(str(post))
        provenance.update({"status": "RETURNED", "returned_utc": returned_utc,
                           "post_fsp_sha256": sha_file(post), "post_fsp_present": post.exists(),
                           "native_engine_log_exposed": False, "native_engine_log_note": "runner retains lifecycle log; engine-native trajectory/log not exposed"})
        write_json(provenance_path, provenance)
        append_log(solver_log, "SOLVER_RETURNED", post_fsp_sha256=provenance["post_fsp_sha256"])
        lease.release("SOLVER_RETURNED", returned_utc)
        lease = None
        return provenance
    except Exception as exc:
        provenance.update({"status": "FAILED", "error": f"{type(exc).__name__}:{exc}", "traceback": traceback.format_exc(),
                           "no_auto_replay": bool(provenance.get("solver_entered"))})
        write_json(provenance_path, provenance)
        append_log(solver_log, "SOLVER_FAILURE", error=provenance["error"], solver_entered=provenance.get("solver_entered"))
        raise
    finally:
        if lease is not None:
            try:
                lease.release("FAILED_ENTERED" if provenance.get("solver_entered") else "FAILED_PRE_ENTRY")
            except Exception:
                pass
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("dry-run", "execute"), required=True)
    parser.add_argument("--confirm-solver-entry", action="store_true")
    args = parser.parse_args()
    result = dry_run() if args.mode == "dry-run" else execute(args.confirm_solver_entry)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0 if result.get("status") in {"READY", "RETURNED", "WAIT_RESOURCE_GATE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
