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
from typing import Any

ROOT = Path(os.environ.get("PAPER_A_ROOT", r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1"))
BASE = ROOT / "paper_a_broadband"
REPORT = BASE / "reports/iar4_orientation_causal_control_truth_v1"
RUNTIME = BASE / "runtime/iar4_orientation_causal_control_truth_v1"
CONTRACT = BASE / "reports/iar4_orientation_causal_control_contract_v1/causal_control_contract.json"
BUILDER = BASE / "scripts/iar4_orientation_causal_control_truth_builder_v1.py"
SOURCE_POST = BASE / "scripts/integrated_aware_lp_source_postprocess_v1.py"
PAIR_CLOSEOUT = BASE / "scripts/integrated_aware_lp_pair_closeout_v1.py"
ANALYSIS = BASE / "scripts/iar4_orientation_causal_control_truth_analysis_v1.py"
SCHEDULER = BASE / "templates/lp_fulljones/apcd_global_fdtd_slot_v1.py"
SLOT_REGISTRY = Path(r"D:/project/apcd_global_fdtd_slot_registry_v1.json")
BRANCH = "work/paper-a-lp-cp-broadband-v1"
PROCESSES, THREADS = 12, 1
CASES = (("IAR4-OC1_x", "x"), ("IAR4-OC1_y", "y"))
TASK_ID = "PAPER_A_IAR4_OC1_CAUSAL_CONTROL_V1"


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha_obj(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    temp.replace(path)


def append_log(path: Path, event: str, **fields: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"timestamp_utc": now(), "event": event, **fields}, ensure_ascii=False, default=str) + "\n")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"MODULE_LOAD_FAILED:{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def process_provider_without_controller(scheduler: Any):
    return [row for row in scheduler._ps_snapshot() if int(row.get("pid", -1)) != os.getpid()]


def resource_snapshot(scheduler: Any) -> dict[str, Any]:
    live = scheduler.live_job_snapshot(lambda: process_provider_without_controller(scheduler))
    registry: dict[str, Any] = {}
    if SLOT_REGISTRY.exists():
        registry = load_json(SLOT_REGISTRY)
    return {
        "timestamp_utc": now(),
        "registry_active_slots": registry.get("active_slots", []),
        "global_capacity": registry.get("global_capacity"),
        "live": live,
        "active_fdtd_jobs": live.get("active_fdtd_jobs", 0),
        "active_rcwa_jobs": live.get("active_rcwa_jobs", 0),
        "unknown_solver_jobs": live.get("unknown_solver_jobs", []),
        "controller_pid": os.getpid(),
        "controller_status": "ALIVE",
    }


def load_state() -> dict[str, Any]:
    path = RUNTIME / "controller_state.json"
    if path.exists():
        return load_json(path)
    return {
        "schema": "PAPER_A_IAR4_OC1_CAUSAL_CONTROL_CONTROLLER_V1",
        "status": "INITIALIZING", "completed_cases": [], "total_cases": 2,
        "solver_accounting": {"authorized": 2, "entered": 0, "returned": 0, "accepted": 0, "replay": 0, "RCWA": 0, "ML": 0},
    }


def save_state(state: dict[str, Any], **updates: Any) -> None:
    state.update(updates)
    state["updated_utc"] = now()
    write_json(RUNTIME / "controller_state.json", state)


def contract_snapshot() -> dict[str, Any]:
    contract = load_json(CONTRACT)
    if contract.get("schema") != "PAPER_A_IAR4_ORIENTATION_CAUSAL_CONTROL_CONTRACT_V1":
        raise RuntimeError("OC1_CONTRACT_SCHEMA_INVALID")
    match = contract.get("matched_control", {})
    if match.get("label") != "IAR4-OC1" or not bool(match.get("geometry_valid")):
        raise RuntimeError("OC1_CONTRACT_MATCHED_CONTROL_INVALID")
    if float(match["direct_clearance_nm"]) < 60.0 or float(match["periodic_image_clearance_nm"]) < 60.0:
        raise RuntimeError("OC1_CONTRACT_CLEARANCE_GATE_INVALID")
    fixed = contract["IAR4_fixed_exact_authority"]
    required = {"L1_nm": 259, "W1_nm": 87, "L2_nm": 203, "W2_nm": 79, "D_nm": 210, "height_nm": 525.0, "period_x_nm": 432.0, "period_y_nm": 432.0}
    if any(float(fixed[key]) != value for key, value in required.items()):
        raise RuntimeError("OC1_FIXED_GEOMETRY_CONTRACT_MISMATCH")
    return contract


def ensure_setup(builder: Any, case_id: str, polarization: str, controller_log: Path) -> dict[str, Any]:
    case_runtime = RUNTIME / "cases" / case_id
    case_report = REPORT / "sources" / case_id
    case_runtime.mkdir(parents=True, exist_ok=True)
    case_report.mkdir(parents=True, exist_ok=True)
    pre = case_runtime / f"{case_id}_attempt_001_pre.fsp"
    setup_path = case_report / "setup_readback.json"
    if pre.exists() or setup_path.exists():
        if not (pre.exists() and setup_path.exists()):
            raise RuntimeError(f"REFUSE_PARTIAL_SETUP_ARTIFACT:{case_id}")
        setup = load_json(setup_path)
        if setup.get("status") != "PASS_SOLVER_READY_PREFSP" or setup.get("pre_fsp", {}).get("sha256") != sha256(pre):
            raise RuntimeError(f"REFUSE_UNVERIFIED_PREFSP:{case_id}")
        if not setup.get("validation", {}).get("checks", {}).get("all"):
            raise RuntimeError(f"REFUSE_INVALID_PREFSP:{case_id}")
        return setup
    append_log(controller_log, "SETUP_ONLY_START", case_id=case_id, polarization=polarization)
    setup = builder.build("IAR4-OC1", case_id, polarization, pre)
    write_json(setup_path, setup)
    write_json(case_report / "pre_solver_readback.json", {
        "schema": "PAPER_A_IAR4_OC1_PRE_SOLVER_READBACK_AUDIT_V1",
        "status": "PASS",
        "case_id": case_id, "candidate_id": "IAR4-OC1", "polarization": polarization,
        "setup_only": True, "pre_fsp": setup["pre_fsp"], "validation": setup["validation"],
        "geometry_contract": setup["candidate_registry"], "solver_run_called": False, "solver_entered": 0,
        "timestamp_utc": now(),
    })
    write_json(case_report / "candidate_provenance.json", {
        "schema": "PAPER_A_IAR4_OC1_CANDIDATE_PROVENANCE_V1", "case_id": case_id,
        "candidate_id": "IAR4-OC1", "polarization": polarization, "setup_only": True,
        "pre_fsp": setup["pre_fsp"], "candidate_geometry_hash": setup["candidate_geometry_hash_authority"],
        "builder_path": str(BUILDER), "builder_sha256": sha256(BUILDER),
        "setup_readback_path": str(setup_path), "solver_run_called": False, "solver_entered": 0,
        "timestamp_utc": now(),
    })
    append_log(controller_log, "SETUP_ONLY_PASS", case_id=case_id, pre_fsp_sha256=setup["pre_fsp"]["sha256"])
    return setup


def run_case(builder: Any, scheduler_module: Any, case_id: str, polarization: str, state: dict[str, Any], controller_log: Path, contract: dict[str, Any]) -> None:
    setup = ensure_setup(builder, case_id, polarization, controller_log)
    case_runtime = RUNTIME / "cases" / case_id
    case_report = REPORT / "sources" / case_id
    pre = case_runtime / f"{case_id}_attempt_001_pre.fsp"
    solver_input = case_runtime / f"{case_id}_attempt_001_run_input.fsp"
    post = case_runtime / f"{case_id}_attempt_001_post.fsp"
    solver_log = case_runtime / f"{case_id}_attempt_001_runner.log"
    provenance_path = case_runtime / f"{case_id}_attempt_001_provenance.json"
    expected_pre_sha = setup["pre_fsp"]["sha256"]
    if sha256(pre) != expected_pre_sha:
        raise RuntimeError(f"PREFSP_HASH_MISMATCH:{case_id}")
    if not solver_input.exists():
        shutil.copyfile(pre, solver_input)
    if sha256(solver_input) != expected_pre_sha:
        raise RuntimeError(f"RUN_INPUT_HASH_MISMATCH:{case_id}")
    physical_contract = {
        "schema": "PAPER_A_IAR4_OC1_PHYSICAL_CONTRACT_V1", "candidate_id": "IAR4-OC1", "case_id": case_id,
        "polarization": polarization, "geometry_hash_sha256": contract["matched_control"]["geometry_hash_sha256"],
        "architecture": "IC1_IC2_FINITE_MESA_5X5_NATIVE_M1", "domain": "3000x3000 nm finite mesa; lateral PML; no periodic xy",
        "source_grid_nm": [400.0, 500.0, 101], "monitor_grid": [150, 150], "mpi_processes": PROCESSES, "threads_per_process": THREADS,
        "no_auto_replay": True, "source_convention": "center dipole; x/y independent; pair incoherent",
    }
    if provenance_path.exists():
        provenance = load_json(provenance_path)
        if provenance.get("solver_entered") and provenance.get("status") not in {"ACCEPTED"}:
            raise RuntimeError(f"HARD_GATE_ENTERED_UNRESOLVED_NO_REPLAY:{case_id}")
        if provenance.get("status") == "ACCEPTED" and (case_report / "validity_gate_v2.json").exists():
            state["completed_cases"] = sorted(set(state.get("completed_cases", [])) | {case_id})
            return
    provenance = {
        "schema": "PAPER_A_IAR4_OC1_PRODUCTION_PROVENANCE_V1", "case_id": case_id, "candidate_id": "IAR4-OC1",
        "polarization": polarization, "attempt_id": "attempt_001", "status": "WAITING", "solver_entered": False,
        "solver_run_called": False, "pre_fsp": str(pre), "pre_fsp_sha256": expected_pre_sha,
        "solver_input_fsp": str(solver_input), "solver_input_fsp_sha256": sha256(solver_input), "post_fsp": str(post),
        "solver_log": str(solver_log), "physical_contract": physical_contract, "physical_contract_sha256": sha_obj(physical_contract),
        "setup_readback": str(case_report / "setup_readback.json"), "setup_readback_sha256": sha256(case_report / "setup_readback.json"),
        "mpi_processes": PROCESSES, "threads_per_process": THREADS, "authorized_new_fdtd_entry": True,
        "new_fdtd_budget": 2, "no_auto_replay": True, "created_utc": now(),
    }
    write_json(provenance_path, provenance)
    append_log(solver_log, "PROVENANCE_CREATED", case_id=case_id, solver_entered=False, solver_run_called=False)
    lease = None
    fdtd = None
    try:
        while lease is None:
            snapshot = resource_snapshot(scheduler_module)
            save_state(state, status="WAITING_FOR_GLOBAL_FDTD_SLOT", current_case=case_id, scheduler=snapshot, active_paper_a_fdtd=0)
            write_json(provenance_path, {**provenance, "last_resource_gate": snapshot, "status": "WAITING"})
            append_log(controller_log, "RESOURCE_CHECK", case_id=case_id, snapshot=snapshot)
            if snapshot["unknown_solver_jobs"]:
                raise RuntimeError(f"HARD_GATE_UNKNOWN_SOLVER_LINEAGE:{json.dumps(snapshot['unknown_solver_jobs'], sort_keys=True)}")
            try:
                lease = scheduler_module.GlobalSlotScheduler(SLOT_REGISTRY, process_provider=lambda: process_provider_without_controller(scheduler_module)).acquire(
                    branch=BRANCH, worktree=str(ROOT), task_id=TASK_ID, case_uid=case_id, pid=os.getpid(),
                    metadata={"task_class": "PAPER_A_INTEGRATED_AWARE_LP_CAUSAL_CONTROL", "candidate_id": "IAR4-OC1",
                              "attempt_id": "attempt_001", "polarization": polarization, "mpi_processes": PROCESSES,
                              "threads_per_process": THREADS, "solver_type": "FDTD", "H_global_nm": 525.0})
            except scheduler_module.SlotUnavailable as exc:
                provenance["last_slot_exception"] = f"{type(exc).__name__}:{exc}"
                write_json(provenance_path, provenance)
                time.sleep(30.0)
        provenance.update({"status": "SLOT_ACQUIRED", "slot_id": lease.slot_id, "admission_snapshot": lease.record.get("admission_snapshot")})
        write_json(provenance_path, provenance)
        append_log(solver_log, "SLOT_ACQUIRED", slot_id=lease.slot_id)
        import lumapi
        fdtd = lumapi.FDTD(hide=True)
        fdtd.load(str(solver_input))
        fdtd.setresource("FDTD", 1, "processes", str(PROCESSES))
        if sha256(solver_input) != expected_pre_sha:
            raise RuntimeError(f"RUN_INPUT_HASH_CHANGED_BEFORE_ENTRY:{case_id}")
        entered_utc = now()
        # Entered and solver-run intent are persisted immediately before run;
        # any failure after this point is non-replayable by policy.
        lease.mark_solver_entered(entered_utc)
        provenance.update({"status": "ENTERED", "solver_entered": True, "solver_run_called": True, "entered_utc": entered_utc,
                           "controller_pid": os.getpid(), "solver_engine_resource": {"processes": PROCESSES, "threads": THREADS}})
        write_json(provenance_path, provenance)
        append_log(solver_log, "SOLVER_ENTERED", case_id=case_id, solver_entered=True, solver_run_called=True, mpi_processes=PROCESSES, threads_per_process=THREADS)
        save_state(state, status="RUNNING", current_case=case_id, current_solver_pid=os.getpid(), solver_accounting={**state["solver_accounting"], "entered": state["solver_accounting"].get("entered", 0) + 1})
        lease.start_heartbeat()
        fdtd.run()
        returned_utc = now()
        fdtd.save(str(post))
        if not post.exists():
            raise RuntimeError(f"POST_FSP_MISSING_AFTER_RETURN:{case_id}")
        provenance.update({"status": "RETURNED", "returned_utc": returned_utc, "post_fsp_sha256": sha256(post), "post_fsp_present": True,
                           "post_return_resource_snapshot": resource_snapshot(scheduler_module)})
        write_json(provenance_path, provenance)
        append_log(solver_log, "SOLVER_RETURNED", post_fsp_sha256=provenance["post_fsp_sha256"])
        lease.release("SOLVER_RETURNED", returned_utc)
        lease = None
        state["solver_accounting"]["returned"] += 1
        save_state(state, status="POSTPROCESSING", current_case=case_id, active_paper_a_fdtd=0)
    except Exception as exc:
        provenance.update({"status": "FAILED", "error": f"{type(exc).__name__}:{exc}", "traceback": traceback.format_exc(),
                           "non_replayable": bool(provenance.get("solver_entered"))})
        write_json(provenance_path, provenance)
        append_log(solver_log, "SOLVER_FAILURE", error=provenance["error"], solver_entered=provenance.get("solver_entered"))
        raise
    finally:
        if lease is not None:
            try:
                lease.release("FAILED_ENTERED" if provenance.get("solver_entered") else "FAILED_PRE_ENTRY")
            except Exception:
                append_log(controller_log, "LEASE_RELEASE_EXCEPTION", case_id=case_id, traceback=traceback.format_exc())
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass
    post_cmd = [sys.executable, str(SOURCE_POST), "--case-id", case_id, "--candidate-id", "IAR4-OC1", "--polarization", polarization,
                "--post-fsp", str(post), "--provenance", str(provenance_path), "--output-dir", str(case_report), "--runtime-dir", str(case_runtime)]
    last_result = None
    for post_attempt in range(1, 3):
        result = subprocess.run(post_cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
        (case_runtime / f"postprocess_attempt_{post_attempt}.stdout.log").write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
        last_result = result
        if result.returncode == 0:
            break
        append_log(controller_log, "POSTPROCESS_ATTEMPT_FAILED", case_id=case_id, attempt=post_attempt, returncode=result.returncode, stderr=result.stderr[-4000:])
    if last_result is None or last_result.returncode != 0:
        raise RuntimeError(f"HARD_GATE_POSTPROCESS_FAILED:{case_id}")
    validity_path = case_report / "validity_gate_v2.json"
    if not validity_path.exists():
        raise RuntimeError(f"HARD_GATE_VALIDITY_ARTIFACT_MISSING:{case_id}")
    validity = load_json(validity_path)
    if validity.get("status") != "VALID_FOR_IC1_INTEGRATED_CANARY_TRUTH":
        raise RuntimeError(f"HARD_GATE_PHYSICS_VALIDITY:{case_id}:{validity.get('status')}")
    provenance["status"] = "ACCEPTED"
    provenance["accepted_utc"] = now()
    provenance["validity_gate"] = validity.get("status")
    write_json(provenance_path, provenance)
    state["completed_cases"] = sorted(set(state.get("completed_cases", [])) | {case_id})
    state["solver_accounting"]["accepted"] += 1
    save_state(state, status="CASE_COMPLETED", current_case=case_id, active_paper_a_fdtd=0)
    append_log(controller_log, "CASE_ACCEPTED", case_id=case_id, validity_status=validity.get("status"))


def run_pair_closeout(state: dict[str, Any], controller_log: Path) -> None:
    pair_runtime = RUNTIME / "pair" / "IAR4-OC1"
    pair_report = REPORT / "pairs" / "IAR4-OC1"
    pair_runtime.mkdir(parents=True, exist_ok=True)
    pair_report.mkdir(parents=True, exist_ok=True)
    x_case, y_case = "IAR4-OC1_x", "IAR4-OC1_y"
    cmd = [sys.executable, str(PAIR_CLOSEOUT), "--candidate-id", "IAR4-OC1", "--x-case", x_case, "--y-case", y_case,
           "--x-dir", str(REPORT / "sources" / x_case), "--y-dir", str(REPORT / "sources" / y_case),
           "--x-post-fsp", str(RUNTIME / "cases" / x_case / f"{x_case}_attempt_001_post.fsp"),
           "--y-post-fsp", str(RUNTIME / "cases" / y_case / f"{y_case}_attempt_001_post.fsp"), "--output-dir", str(pair_runtime)]
    save_state(state, status="PAIR_POSTPROCESSING", current_case=None, active_paper_a_fdtd=0)
    result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    (RUNTIME / "pair_postprocess.stdout.log").write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
    if result.returncode != 0:
        append_log(controller_log, "PAIR_CLOSEOUT_FAILED", returncode=result.returncode, stderr=result.stderr[-5000:])
        raise RuntimeError("HARD_GATE_PAIR_CLOSEOUT_FAILED")
    summary = load_json(pair_runtime / "pair_summary.json")
    if summary.get("status") != "PASS":
        raise RuntimeError(f"HARD_GATE_PAIR_CLOSEOUT_STATUS:{summary.get('status')}")
    formal_names = {"pair_wavelength_metrics.csv", "angular_cancellation_metrics.csv", "source_cancellation_metrics.csv", "pair_stokes.csv",
                    "pair_450nm_anchor.json", "pair_broadband_summary.json", "pair_summary.json", "pair_audit.json"}
    for name in formal_names:
        source = pair_runtime / name
        if not source.exists():
            raise RuntimeError(f"PAIR_FORMAL_ARTIFACT_MISSING:{name}")
        shutil.copy2(source, pair_report / name)
    append_log(controller_log, "PAIR_CLOSEOUT_PASS", candidate_id="IAR4-OC1", runtime_dir=str(pair_runtime), report_dir=str(pair_report))


def execute() -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    contract = contract_snapshot()
    builder = load_module(BUILDER, "iar4_oc1_builder_runtime")
    scheduler_module = load_module(SCHEDULER, "iar_global_scheduler_oc1")
    controller_log = RUNTIME / "controller.jsonl"
    state = load_state()
    save_state(state, status="PREFLIGHT", authorized_cases=[case[0] for case in CASES], active_limit=1,
               production_resources={"mpi_processes": PROCESSES, "threads_per_process": THREADS}, contract_hash=sha256(CONTRACT))
    snapshot = resource_snapshot(scheduler_module)
    write_json(REPORT / "resource_preflight.json", snapshot)
    if snapshot["unknown_solver_jobs"]:
        raise RuntimeError(f"HARD_GATE_UNKNOWN_SOLVER_LINEAGE:{json.dumps(snapshot['unknown_solver_jobs'], sort_keys=True)}")
    for case_id, polarization in CASES:
        if case_id not in state.get("completed_cases", []):
            run_case(builder, scheduler_module, case_id, polarization, state, controller_log, contract)
        # Sequential control is intentional: PAPER_A_MAX_ACTIVE_FDTD=1.
        save_state(state, status="CASE_BOUNDARY_CHECK", current_case=None, active_paper_a_fdtd=0, scheduler=resource_snapshot(scheduler_module))
    run_pair_closeout(state, controller_log)
    analysis_result = subprocess.run([sys.executable, str(ANALYSIS)], cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    (RUNTIME / "analysis.stdout.log").write_text(analysis_result.stdout + "\n" + analysis_result.stderr, encoding="utf-8")
    if analysis_result.returncode != 0:
        raise RuntimeError(f"HARD_GATE_ANALYSIS_FAILED:{analysis_result.stderr[-4000:]}")
    accounting = {**state["solver_accounting"], "replay": 0, "RCWA": 0, "ML": 0, "active_fdtd": resource_snapshot(scheduler_module)["active_fdtd_jobs"]}
    save_state(state, status="TERMINAL_COMPLETION", current_case=None, active_paper_a_fdtd=0, solver_accounting=accounting)
    write_json(REPORT / "solver_accounting.json", {"schema": "PAPER_A_IAR4_OC1_SOLVER_ACCOUNTING_V1", **accounting, "new_fdtd_budget": 2, "solver_run_called": accounting["entered"] > 0, "timestamp_utc": now()})
    write_json(REPORT / "terminal_success.json", {"schema": "PAPER_A_IAR4_OC1_CAUSAL_CONTROL_TERMINAL_SUCCESS_V1", "status": "PASS", "case_ids": [case[0] for case in CASES], "analysis": "PASS", "solver_accounting": accounting, "no_additional_solver": True, "timestamp_utc": now()})
    append_log(controller_log, "TERMINAL_SUCCESS", report=str(REPORT / "final_report.md"))


def preflight() -> int:
    contract = contract_snapshot()
    scheduler_module = load_module(SCHEDULER, "iar_global_scheduler_oc1_preflight")
    snapshot = resource_snapshot(scheduler_module)
    result = {
        "status": "PASS" if not snapshot["unknown_solver_jobs"] else "HARD_GATE",
        "contract_id": contract["matched_control"]["label"],
        "contract_geometry_hash": contract["matched_control"]["geometry_hash_sha256"],
        "global_capacity": snapshot.get("global_capacity"),
        "active_fdtd_jobs": snapshot.get("active_fdtd_jobs"),
        "active_rcwa_jobs": snapshot.get("active_rcwa_jobs"),
        "unknown_solver_jobs": snapshot.get("unknown_solver_jobs"),
        "controller_pid": os.getpid(),
        "solver_run_called": False,
        "solver_entered": 0,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0 if result["status"] == "PASS" else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    if args.preflight:
        return preflight()
    if not args.execute:
        raise SystemExit("EXECUTE_FLAG_REQUIRED")
    try:
        execute()
    except Exception as exc:
        REPORT.mkdir(parents=True, exist_ok=True)
        RUNTIME.mkdir(parents=True, exist_ok=True)
        state = load_state()
        failure = {"schema": "PAPER_A_IAR4_OC1_CAUSAL_CONTROL_TERMINAL_FAILURE_V1", "status": "HARD_GATE", "error": f"{type(exc).__name__}:{exc}", "traceback": traceback.format_exc(), "solver_accounting": state.get("solver_accounting", {}), "no_auto_replay": True, "timestamp_utc": now()}
        write_json(REPORT / "terminal_failure.json", failure)
        save_state(state, status="HARD_GATE", terminal_artifact=str(REPORT / "terminal_failure.json"), hard_gate=failure["error"])
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
