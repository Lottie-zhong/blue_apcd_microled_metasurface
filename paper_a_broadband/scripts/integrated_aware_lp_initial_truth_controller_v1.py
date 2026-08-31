from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(os.environ.get("PAPER_A_ROOT", r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1"))
BASE = ROOT / "paper_a_broadband"
REPORT = BASE / "reports/integrated_aware_lp_initial_truth_v1"
RUNTIME = BASE / "runtime/integrated_aware_lp_initial_truth_v1"
SLOT_REGISTRY = Path(r"D:/project/apcd_global_fdtd_slot_registry_v1.json")
SCHEDULER_PATH = BASE / "templates/lp_fulljones/apcd_global_fdtd_slot_v1.py"
BUILDER_PATH = BASE / "scripts/integrated_aware_lp_initial_truth_builder_v1.py"
SOURCE_POST_PATH = BASE / "scripts/integrated_aware_lp_source_postprocess_v1.py"
PAIR_PATH = BASE / "scripts/integrated_aware_lp_pair_closeout_v1.py"
FINALIZER_PATH = BASE / "scripts/integrated_aware_lp_initial_truth_finalizer_v1.py"
BASELINE_ANCHOR = BASE / "reports/ic2_pair_polarization_cancellation_forensic_v1/pair_450nm_forensic_anchor.json"
BRANCH = "work/paper-a-lp-cp-broadband-v1"
PROCESSES, THREADS = 12, 1
PLAN = (("IAR3", "IAR3_x", "x"), ("IAR3", "IAR3_y", "y"), ("IAR4", "IAR4_x", "x"), ("IAR4", "IAR4_y", "y"))


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha_obj(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()).hexdigest()


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def log(path: Path, event: str, **fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"timestamp_utc": now(), "event": event, **fields}, ensure_ascii=False, default=str) + "\n")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"MODULE_IMPORT_FAILED:{path}")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def load_scheduler():
    return load_module(SCHEDULER_PATH, "iar_global_scheduler")


def load_state():
    path = RUNTIME / "controller_state.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"schema": "PAPER_A_INTEGRATED_AWARE_LP_INITIAL_TRUTH_CONTROLLER_V1", "status": "INITIALIZING", "completed_cases": [], "completed_pairs": [], "total_cases": 4, "solver_accounting": {"authorized": 4, "entered": 0, "returned": 0, "accepted": 0, "replay": 0, "rcwa": 0, "ml": 0}}


def save_state(state, **updates):
    state.update(updates); state["updated_utc"] = now(); write_json(RUNTIME / "controller_state.json", state)


def process_provider_without_controller(scheduler):
    return [row for row in scheduler._ps_snapshot() if int(row.get("pid", -1)) != os.getpid()]


def resource_snapshot(scheduler):
    live = scheduler.live_job_snapshot(lambda: process_provider_without_controller(scheduler))
    registry = {}
    if SLOT_REGISTRY.exists():
        registry = json.loads(SLOT_REGISTRY.read_text(encoding="utf-8-sig"))
    return {"timestamp_utc": now(), "registry_active_slots": registry.get("active_slots", []), "global_capacity": registry.get("global_capacity"), "live": live, "unknown_solver_jobs": live.get("unknown_solver_jobs", []), "active_fdtd_jobs": live.get("active_fdtd_jobs", 0), "active_rcwa_jobs": live.get("active_rcwa_jobs", 0), "cpu_count": os.cpu_count()}


def setup_case(builder, candidate, case_id, polarization, state, controller_log):
    case_runtime = RUNTIME / "cases" / case_id
    case_report = REPORT / "sources" / case_id
    case_runtime.mkdir(parents=True, exist_ok=True); case_report.mkdir(parents=True, exist_ok=True)
    pre = case_runtime / f"{case_id}_attempt_001_pre.fsp"
    setup_manifest = case_report / "setup_readback.json"
    if setup_manifest.exists() and pre.exists():
        existing = json.loads(setup_manifest.read_text(encoding="utf-8-sig"))
        if existing.get("status") == "PASS_SOLVER_READY_PREFSP" and existing.get("pre_fsp", {}).get("sha256") == sha256(pre):
            return existing
    if pre.exists() or setup_manifest.exists():
        raise RuntimeError(f"REFUSE_UNVERIFIED_EXISTING_SETUP:{case_id}")
    log(controller_log, "SETUP_ONLY_START", case_id=case_id, candidate_id=candidate, polarization=polarization)
    result = builder.build(candidate, case_id, polarization, pre)
    write_json(setup_manifest, result)
    provenance = {"schema": "PAPER_A_INTEGRATED_AWARE_LP_CANDIDATE_PROVENANCE_V1", "case_id": case_id, "candidate_id": candidate, "polarization": polarization, "candidate_registry_record": result["candidate_registry"], "candidate_geometry_hash": result["candidate_geometry_hash_authority"], "pre_fsp": result["pre_fsp"], "builder_path": str(BUILDER_PATH), "builder_sha256": sha256(BUILDER_PATH), "setup_readback_path": str(setup_manifest), "setup_only": True, "solver_run_called": False, "solver_entered": 0, "timestamp_utc": now()}
    write_json(case_report / "candidate_provenance.json", provenance)
    log(controller_log, "SETUP_ONLY_PASS", case_id=case_id, pre_fsp_sha256=result["pre_fsp"]["sha256"])
    return result


def run_case(builder, scheduler, candidate, case_id, polarization, state, controller_log):
    setup = setup_case(builder, candidate, case_id, polarization, state, controller_log)
    case_runtime = RUNTIME / "cases" / case_id; case_report = REPORT / "sources" / case_id
    pre = Path(setup["pre_fsp"]["path"]); expected_pre_sha = setup["pre_fsp"]["sha256"]
    provenance_path = case_runtime / f"{case_id}_attempt_001_provenance.json"
    post = case_runtime / f"{case_id}_attempt_001_post.fsp"
    solver_input = case_runtime / f"{case_id}_attempt_001_run_input.fsp"
    solver_log = case_runtime / f"{case_id}_attempt_001_runner.log"
    source_dir = case_report
    if provenance_path.exists():
        old = json.loads(provenance_path.read_text(encoding="utf-8"))
        if old.get("solver_entered") and old.get("status") != "RETURNED":
            raise RuntimeError(f"HARD_GATE_ENTERED_UNRESOLVED_NO_REPLAY:{case_id}")
        if old.get("status") == "RETURNED" and (source_dir / "validity_gate_v2.json").exists():
            return old
    physical_contract = {"candidate_id": candidate, "polarization": polarization, "candidate_registry": setup["candidate_registry"], "architecture": "IC1_IC2_FINITE_INTEGRATED_NATIVE_M1", "source_grid_nm": [400.0, 500.0, 101], "domain_boundary": "finite xyz PML; no periodic xy", "source_position_nm": [0.0, 0.0, -171.5], "mpi_processes": PROCESSES, "threads_per_process": THREADS, "no_auto_replay": True}
    if sha256(pre) != expected_pre_sha:
        raise RuntimeError(f"PREFSP_HASH_MISMATCH:{case_id}")
    if not solver_input.exists():
        shutil.copyfile(pre, solver_input)
    if sha256(solver_input) != expected_pre_sha:
        raise RuntimeError(f"RUN_INPUT_HASH_MISMATCH:{case_id}")
    provenance = {"schema": "PAPER_A_INTEGRATED_AWARE_LP_PRODUCTION_PROVENANCE_V1", "case_id": case_id, "candidate_id": candidate, "polarization": polarization, "attempt_id": "attempt_001", "status": "WAITING", "solver_entered": False, "solver_run_called": False, "pre_fsp": str(pre), "pre_fsp_sha256": expected_pre_sha, "solver_input_fsp": str(solver_input), "solver_input_fsp_sha256": sha256(solver_input), "post_fsp": str(post), "solver_log": str(solver_log), "physical_contract": physical_contract, "physical_contract_sha256": sha_obj(physical_contract), "setup_readback": str(case_report / "setup_readback.json"), "setup_readback_sha256": sha256(case_report / "setup_readback.json"), "mpi_processes": PROCESSES, "threads_per_process": THREADS, "authorized_new_fdtd_entry": True, "new_fdtd_budget": 4, "no_auto_replay": True, "created_utc": now()}
    write_json(provenance_path, provenance); log(solver_log, "PROVENANCE_CREATED", case_id=case_id, solver_entered=False, solver_run_called=False)
    lease = None; fdtd = None
    try:
        while lease is None:
            snapshot = resource_snapshot(scheduler); save_state(state, status="WAITING_FOR_SLOT", current_case=case_id, scheduler=snapshot)
            log(controller_log, "RESOURCE_CHECK", case_id=case_id, snapshot=snapshot)
            if snapshot.get("unknown_solver_jobs"):
                raise RuntimeError(f"HARD_GATE_UNKNOWN_SOLVER_LINEAGE:{json.dumps(snapshot['unknown_solver_jobs'], sort_keys=True)}")
            try:
                lease = scheduler.GlobalSlotScheduler(SLOT_REGISTRY, process_provider=lambda: process_provider_without_controller(scheduler)).acquire(branch=BRANCH, worktree=str(ROOT), task_id="PAPER_A_INTEGRATED_AWARE_LP_INITIAL_TRUTH_V1", case_uid=case_id, pid=os.getpid(), metadata={"task_class": "PAPER_A_INTEGRATED_AWARE_LP", "candidate_id": candidate, "attempt_id": "attempt_001", "polarization": polarization, "mpi_processes": PROCESSES, "threads_per_process": THREADS})
            except scheduler.SlotUnavailable as exc:
                provenance["last_resource_gate"] = {"reason": f"{type(exc).__name__}:{exc}", "snapshot": snapshot, "timestamp_utc": now()}; write_json(provenance_path, provenance); time.sleep(60.0)
        provenance.update({"status": "SLOT_ACQUIRED", "slot_id": lease.slot_id, "admission_snapshot": lease.record.get("admission_snapshot")}); write_json(provenance_path, provenance); log(solver_log, "SLOT_ACQUIRED", slot_id=lease.slot_id)
        import lumapi
        fdtd = lumapi.FDTD(hide=True); fdtd.load(str(solver_input)); fdtd.setresource("FDTD", 1, "processes", str(PROCESSES))
        if sha256(solver_input) != expected_pre_sha:
            raise RuntimeError(f"RUN_INPUT_HASH_CHANGED_BEFORE_ENTRY:{case_id}")
        entered_utc = now()
        lease.mark_solver_entered(entered_utc); lease.start_heartbeat()
        provenance.update({"status": "ENTERED", "solver_entered": True, "solver_run_called": True, "entered_utc": entered_utc}); write_json(provenance_path, provenance); log(solver_log, "SOLVER_ENTERED", case_id=case_id, solver_entered=True, solver_run_called=True, mpi_processes=PROCESSES, threads_per_process=THREADS); save_state(state, status="RUNNING", current_case=case_id, current_solver_pid=os.getpid(), solver_entry_case=case_id, solver_accounting={**state.get("solver_accounting", {}), "entered": state.get("solver_accounting", {}).get("entered", 0) + 1})
        fdtd.run()
        returned_utc = now(); fdtd.save(str(post))
        if not post.exists():
            raise RuntimeError(f"POST_FSP_MISSING_AFTER_RETURN:{case_id}")
        provenance.update({"status": "RETURNED", "returned_utc": returned_utc, "post_fsp_sha256": sha256(post), "post_fsp_present": True}); write_json(provenance_path, provenance); log(solver_log, "SOLVER_RETURNED", post_fsp_sha256=provenance["post_fsp_sha256"]); lease.release("SOLVER_RETURNED", returned_utc); lease = None
        save_state(state, status="POSTPROCESSING", current_case=case_id, solver_accounting={**state.get("solver_accounting", {}), "returned": state.get("solver_accounting", {}).get("returned", 0) + 1})
    except Exception as exc:
        provenance.update({"status": "FAILED", "error": f"{type(exc).__name__}:{exc}", "traceback": traceback.format_exc(), "no_auto_replay": bool(provenance.get("solver_entered"))}); write_json(provenance_path, provenance); log(solver_log, "SOLVER_FAILURE", error=provenance["error"], solver_entered=provenance.get("solver_entered")); raise
    finally:
        if lease is not None:
            try: lease.release("FAILED_ENTERED" if provenance.get("solver_entered") else "FAILED_PRE_ENTRY")
            except Exception: pass
        if fdtd is not None:
            try: fdtd.close()
            except Exception: pass
    post_cmd = [sys.executable, str(SOURCE_POST_PATH), "--case-id", case_id, "--candidate-id", candidate, "--polarization", polarization, "--post-fsp", str(post), "--provenance", str(provenance_path), "--output-dir", str(source_dir), "--runtime-dir", str(case_runtime)]
    for attempt in range(1, 3):
        completed = subprocess.run(post_cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
        (case_runtime / f"postprocess_attempt_{attempt}.stdout.log").write_text(completed.stdout + "\n" + completed.stderr, encoding="utf-8")
        if completed.returncode == 0:
            break
        log(controller_log, "POSTPROCESS_RETRY_OR_FAILURE", case_id=case_id, attempt=attempt, returncode=completed.returncode, stdout=completed.stdout[-4000:], stderr=completed.stderr[-4000:])
    else:
        raise RuntimeError(f"HARD_GATE_POSTPROCESS_FAILED:{case_id}")
    validity = json.loads((source_dir / "validity_gate_v2.json").read_text(encoding="utf-8"))
    if validity.get("status") != "VALID_FOR_IC1_INTEGRATED_CANARY_TRUTH":
        raise RuntimeError(f"HARD_GATE_PHYSICS_VALIDITY:{case_id}:{validity.get('status')}")
    save_state(state, status="CASE_COMPLETED", current_case=case_id, completed_cases=state.get("completed_cases", []) + [case_id], solver_accounting={**state.get("solver_accounting", {}), "accepted": state.get("solver_accounting", {}).get("accepted", 0) + 1})
    log(controller_log, "CASE_ACCEPTED", case_id=case_id, validity_status=validity.get("status"))
    return provenance


def run_pair(scheduler, candidate, x_case, y_case, state, controller_log):
    out = REPORT / "pairs" / candidate; out.mkdir(parents=True, exist_ok=True)
    x_dir = REPORT / "sources" / x_case; y_dir = REPORT / "sources" / y_case
    x_post = RUNTIME / "cases" / x_case / f"{x_case}_attempt_001_post.fsp"; y_post = RUNTIME / "cases" / y_case / f"{y_case}_attempt_001_post.fsp"
    cmd = [sys.executable, str(PAIR_PATH), "--candidate-id", candidate, "--x-case", x_case, "--y-case", y_case, "--x-dir", str(x_dir), "--y-dir", str(y_dir), "--x-post-fsp", str(x_post), "--y-post-fsp", str(y_post), "--output-dir", str(out)]
    save_state(state, status="PAIR_POSTPROCESSING", current_pair=candidate)
    result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    (RUNTIME / f"{candidate}_pair_postprocess.stdout.log").write_text(result.stdout + "\n" + result.stderr, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        log(controller_log, "PAIR_FAILURE", candidate_id=candidate, returncode=result.returncode, stdout=result.stdout[-5000:], stderr=result.stderr[-5000:]); raise RuntimeError(f"PAIR_POSTPROCESS_FAILED:{candidate}")
    pair_summary = json.loads((out / "pair_summary.json").read_text(encoding="utf-8"))
    if pair_summary.get("status") != "PASS":
        raise RuntimeError(f"HARD_GATE_PAIR_CLOSEOUT:{candidate}")
    save_state(state, status="PAIR_COMPLETED", current_pair=candidate, completed_pairs=state.get("completed_pairs", []) + [candidate])
    log(controller_log, "PAIR_ACCEPTED", candidate_id=candidate)


def execute():
    RUNTIME.mkdir(parents=True, exist_ok=True); REPORT.mkdir(parents=True, exist_ok=True)
    state = load_state(); controller_log = RUNTIME / "controller.jsonl"; builder = load_module(BUILDER_PATH, "iar_candidate_builder"); scheduler = load_scheduler()
    save_state(state, status="SETUP_ONLY_AND_ADMISSION", authorized_cases=[item[1] for item in PLAN], active_limit=1, production_resources={"mpi_processes": PROCESSES, "threads_per_process": THREADS})
    for candidate, case_id, polarization in PLAN[:2]:
        if case_id not in state.get("completed_cases", []): run_case(builder, scheduler, candidate, case_id, polarization, state, controller_log)
    if "IAR3" not in state.get("completed_pairs", []): run_pair(scheduler, "IAR3", "IAR3_x", "IAR3_y", state, controller_log)
    for candidate, case_id, polarization in PLAN[2:]:
        if case_id not in state.get("completed_cases", []): run_case(builder, scheduler, candidate, case_id, polarization, state, controller_log)
    if "IAR4" not in state.get("completed_pairs", []): run_pair(scheduler, "IAR4", "IAR4_x", "IAR4_y", state, controller_log)
    final_cmd = [sys.executable, str(FINALIZER_PATH), "--output-dir", str(REPORT), "--runtime-dir", str(RUNTIME), "--controller-state", str(RUNTIME / "controller_state.json"), "--baseline-anchor", str(BASELINE_ANCHOR)]
    result = subprocess.run(final_cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    (RUNTIME / "finalizer.stdout.log").write_text(result.stdout + "\n" + result.stderr, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"FINALIZER_FAILED:{result.stdout[-4000:]}:{result.stderr[-4000:]}")
    save_state(state, status="TERMINAL_COMPLETION", terminal_artifact=str(REPORT / "terminal_success.json"), current_case=None, current_pair=None)
    log(controller_log, "TERMINAL_SUCCESS", report=str(REPORT / "final_report.md"))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--execute", action="store_true"); args = parser.parse_args()
    if not args.execute: raise SystemExit("EXECUTE_FLAG_REQUIRED")
    try:
        execute()
    except Exception as exc:
        RUNTIME.mkdir(parents=True, exist_ok=True); REPORT.mkdir(parents=True, exist_ok=True)
        state = load_state(); failure = {"schema": "PAPER_A_INTEGRATED_AWARE_LP_INITIAL_TRUTH_TERMINAL_FAILURE_V1", "status": "HARD_GATE", "error": f"{type(exc).__name__}:{exc}", "traceback": traceback.format_exc(), "solver_accounting": state.get("solver_accounting", {}), "no_auto_replay": True, "timestamp_utc": now()}
        write_json(REPORT / "terminal_failure.json", failure); save_state(state, status="HARD_GATE", terminal_artifact=str(REPORT / "terminal_failure.json"), hard_gate=failure["error"])
        raise


if __name__ == "__main__":
    main()
