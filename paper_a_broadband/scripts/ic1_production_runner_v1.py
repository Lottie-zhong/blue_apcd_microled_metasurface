from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("PAPER_A_ROOT", r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1"))
BASE = ROOT / "paper_a_broadband"
RUNTIME = BASE / "runtime/ic1_solver_ready"
REPORT = BASE / "reports/ic1_solver_ready_runner"
CASE_ID = "IC1_MDC_I03_TOPWELL_X"
BRANCH = "work/paper-a-lp-cp-broadband-v1"
SLOT_REGISTRY = Path(r"D:/project/apcd_global_fdtd_slot_registry_v1.json")
SCHEDULER_PATH = BASE / "templates/lp_fulljones/apcd_global_fdtd_slot_v1.py"
PROCESSES, THREADS, MAX_NEW_ENTRIES = 12, 1, 1
sys.path.insert(0, r"N:/Program Files/ANSYS Inc/v251/Lumerical/api/python")


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


def load_builder():
    path = BASE / "scripts/ic1_solver_ready_prefsp_builder_v1.py"
    spec = importlib.util.spec_from_file_location("ic1_prefsp_builder", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("IC1_BUILDER_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_authority() -> dict[str, Any]:
    path = BASE / "authority/ic1_solver_ready_prefsp_authority_v1.json"
    if not path.exists():
        raise RuntimeError("IC1_PREFSP_AUTHORITY_MISSING")
    authority = json.loads(path.read_text(encoding="utf-8"))
    if authority.get("status") != "PASS_SOLVER_READY_PREFSP" or authority.get("case_id") != CASE_ID:
        raise RuntimeError("IC1_PREFSP_AUTHORITY_NOT_PASS")
    if authority.get("authorization", {}).get("authorization_used"):
        raise RuntimeError("IC1_AUTHORIZATION_ALREADY_USED")
    if authority.get("production_runner", {}).get("max_new_fdtd_entries") != MAX_NEW_ENTRIES:
        raise RuntimeError("IC1_BUDGET_AUTHORITY_CONFLICT")
    return authority


def read_registry() -> dict[str, Any]:
    if not SLOT_REGISTRY.exists():
        return {"status": "REGISTRY_UNAVAILABLE", "path": str(SLOT_REGISTRY), "safe_to_execute": False}
    try:
        data = json.loads(SLOT_REGISTRY.read_text(encoding="utf-8"))
        return {"status": "READ_ONLY", "path": str(SLOT_REGISTRY), "active_slots": data.get("active_slots", []),
                "global_capacity": data.get("global_capacity"), "safe_to_execute": True}
    except Exception as exc:
        return {"status": "REGISTRY_UNREADABLE", "path": str(SLOT_REGISTRY),
                "error": f"{type(exc).__name__}:{exc}", "safe_to_execute": False}


def dry_run() -> dict[str, Any]:
    builder = load_builder()
    authority = load_authority()
    pre = Path(authority["canonical_prefsp"]["path"])
    read = builder.readback(pre) if pre.exists() else None
    validation = builder.validate_readback(read) if read is not None else {"prefsp_exists": False, "all": False}
    result = {
        "schema": "PAPER_A_IC1_PRODUCTION_RUNNER_DRY_RUN_V1",
        "status": "READY" if read is not None and validation.get("all") else "BLOCKED_PREFSP_OR_READBACK",
        "case_id": CASE_ID, "pre_fsp": str(pre),
        "pre_fsp_sha256": sha_file(pre) if pre.exists() else None,
        "authority_prefsp_sha256": authority["canonical_prefsp"]["sha256"],
        "sha_match": pre.exists() and sha_file(pre) == authority["canonical_prefsp"]["sha256"],
        "validation": validation, "resource_audit": read_registry(),
        "production_resources": {"mpi_processes": PROCESSES, "threads_per_process": THREADS,
                                 "max_new_fdtd_entries": MAX_NEW_ENTRIES},
        "solver_counters": {"run_called": False, "entered": 0, "active_fdtd": 0, "rcwa": 0, "ml": 0,
                            "hidden_auto_admission": False},
        "execute_requires": "--confirm-solver-entry", "no_dispatch_in_dry_run": True,
        "timestamp_utc": now(),
    }
    write_json(REPORT / "dry_run.json", result)
    return result


def execute(confirm: bool) -> dict[str, Any]:
    if not confirm:
        raise RuntimeError("EXPLICIT_CONFIRMATION_REQUIRED:--confirm-solver-entry")
    builder = load_builder()
    authority = load_authority()
    pre = Path(authority["canonical_prefsp"]["path"])
    if not pre.exists() or sha_file(pre) != authority["canonical_prefsp"]["sha256"]:
        raise RuntimeError("IC1_PREFSP_SHA_MISMATCH")
    read = builder.readback(pre)
    if not builder.validate_readback(read).get("all"):
        raise RuntimeError("IC1_PREFSP_READBACK_GATE")
    if not read_registry().get("safe_to_execute"):
        raise RuntimeError("IC1_RESOURCE_REGISTRY_NOT_AUTHORITATIVE")
    case_dir = RUNTIME / "production"
    provenance_path = case_dir / f"{CASE_ID}_attempt_001_provenance.json"
    post = case_dir / f"{CASE_ID}_attempt_001_post.fsp"
    provenance = {
        "schema": "PAPER_A_IC1_PRODUCTION_RUNNER_PROVENANCE_V1", "case_id": CASE_ID,
        "attempt_id": "attempt_001", "status": "WAITING", "solver_entered": False,
        "solver_run_called": False, "pre_fsp": str(pre), "pre_fsp_sha256": sha_file(pre),
        "physical_contract_sha256": sha_obj(authority["physics_contract"]),
        "physics_semantic_fingerprint": authority["physics_semantic_fingerprint"],
        "integrated_instrumentation_fingerprint": authority["integrated_instrumentation_fingerprint"],
        "mpi_processes": PROCESSES, "threads_per_process": THREADS,
        "new_fdtd_budget": MAX_NEW_ENTRIES, "created_utc": now(),
    }
    write_json(provenance_path, provenance)
    lease = None
    fdtd = None
    try:
        spec = importlib.util.spec_from_file_location("ic1_scheduler", SCHEDULER_PATH)
        if spec is None or spec.loader is None:
            raise RuntimeError("SCHEDULER_IMPORT_FAILED")
        sched = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sched)
        scheduler = sched.GlobalSlotScheduler(SLOT_REGISTRY)
        lease = scheduler.acquire_wait(branch=BRANCH, worktree=str(ROOT),
                                       task_id="PAPER_A_IC1_PRODUCTION_RUNNER_V1", case_uid=CASE_ID,
                                       pid=os.getpid(), metadata={"task_class": "PAPER_A_IC1",
                                       "mpi_processes": PROCESSES, "threads_per_process": THREADS},
                                       timeout_s=21600.0, poll_s=30.0)
        provenance.update({"status": "SLOT_ACQUIRED", "slot_id": lease.slot_id,
                           "admission_snapshot": lease.record.get("admission_snapshot")})
        write_json(provenance_path, provenance)
        import lumapi
        fdtd = lumapi.FDTD(hide=True)
        fdtd.load(str(pre))
        fdtd.setresource("FDTD", 1, "processes", str(PROCESSES))
        entered_utc = now()
        lease.mark_solver_entered(entered_utc)
        provenance.update({"status": "ENTERED", "solver_entered": True,
                           "solver_run_called": True, "entered_utc": entered_utc})
        write_json(provenance_path, provenance)
        fdtd.run()
        returned_utc = now()
        fdtd.save(str(post))
        provenance.update({"status": "RETURNED", "returned_utc": returned_utc,
                           "post_fsp": str(post), "post_fsp_sha256": sha_file(post),
                           "no_auto_replay": True})
        write_json(provenance_path, provenance)
        lease.release("SOLVER_RETURNED", returned_utc)
        lease = None
        return provenance
    except Exception as exc:
        provenance.update({"status": "FAILED", "error": f"{type(exc).__name__}:{exc}",
                           "traceback": traceback.format_exc(),
                           "no_auto_replay": bool(provenance.get("solver_entered"))})
        write_json(provenance_path, provenance)
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
    return 0 if result.get("status") in ("READY", "RETURNED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
