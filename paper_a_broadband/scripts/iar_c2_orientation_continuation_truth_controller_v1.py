from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import math
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
REPORT = BASE / "reports/iar_c2_orientation_continuation_truth_v1"
RUNTIME = BASE / "runtime/iar_c2_orientation_continuation_truth_v1"
CONTRACT_DIR = BASE / "reports/iar_c2_orientation_continuation_control_contract_v1"
CONTROL_CONTRACT = CONTRACT_DIR / "control_contract.json"
CONDITIONAL_REGISTRY = BASE / "reports/integrated_aware_lp_redesign_contract_v1/integrated_candidate_registry_conditional.csv"
BUILDER = BASE / "scripts/integrated_aware_lp_initial_truth_builder_v1.py"
SOURCE_POST = BASE / "scripts/integrated_aware_lp_source_postprocess_v1.py"
PAIR_CLOSEOUT = BASE / "scripts/integrated_aware_lp_pair_closeout_v1.py"
SCHEDULER = BASE / "templates/lp_fulljones/apcd_global_fdtd_slot_v1.py"
SLOT_REGISTRY = Path(r"D:/project/apcd_global_fdtd_slot_registry_v1.json")
BRANCH = "work/paper-a-lp-cp-broadband-v1"
TASK_ID = "PAPER_A_IAR_C2_ORIENTATION_CONTINUATION_TRUTH_V1"
PROCESSES, THREADS = 12, 1
NEW_BUDGET = 4
CASES = (("IAR-C2", "IAR-C2_x", "x"), ("IAR-C2", "IAR-C2_y", "y"),
         ("IAR-C2-OC80", "IAR-C2-OC80_x", "x"), ("IAR-C2-OC80", "IAR-C2-OC80_y", "y"))


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha_obj(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def append_log(path: Path, event: str, **fields: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"timestamp_utc": now(), "event": event, **fields}, ensure_ascii=False, default=str) + "\n")


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
    registry = load_json(SLOT_REGISTRY) if SLOT_REGISTRY.exists() else {}
    resources: dict[str, Any] = {"cpu_count": os.cpu_count()}
    try:
        import psutil
        vm = psutil.virtual_memory()
        resources.update({"ram_total_bytes": int(vm.total), "ram_available_bytes": int(vm.available), "ram_percent": float(vm.percent),
                          "cpu_percent": float(psutil.cpu_percent(interval=None))})
    except Exception:
        resources["psutil"] = "UNAVAILABLE"
    return {
        "timestamp_utc": now(), "registry_active_slots": registry.get("active_slots", []),
        "global_capacity": registry.get("global_capacity"), "live": live,
        "active_fdtd_jobs": int(live.get("active_fdtd_jobs", 0)),
        "active_rcwa_jobs": int(live.get("active_rcwa_jobs", 0)),
        "unknown_solver_jobs": live.get("unknown_solver_jobs", []),
        "external_fluent_jobs": live.get("external_fluent_jobs", []),
        "global_active_jobs": int(live.get("global_active_jobs", 0)),
        "controller_pid": os.getpid(), "controller_status": "ALIVE", "resources": resources,
    }


def make_rows(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    with CONDITIONAL_REGISTRY.open(newline="", encoding="utf-8-sig") as f:
        rows = {row["geometry_id"]: row for row in csv.DictReader(f)}
    if "IAR-C2" not in rows:
        raise RuntimeError("IAR_C2_REGISTRY_ROW_MISSING")
    c2 = dict(rows["IAR-C2"])
    fixed = contract["fixed_IAR_C2_geometry"]
    match = contract["angle_only_control"]
    oc = match["geometry"]
    c2["geometry_id"] = "IAR-C2"
    c2["geometry_hash_sha256"] = contract["IAR_C2_source_geometry_hash"]
    for key in ("L1_nm", "W1_nm", "L2_nm", "W2_nm", "D_nm", "delta_theta_deg", "theta1_deg", "theta2_deg",
                "j1_center_x_nm", "j1_center_y_nm", "j2_center_x_nm", "j2_center_y_nm", "height_nm", "period_x_nm", "period_y_nm"):
        c2[key] = fixed[key]
    # Keep the exact parent clearance values from the authoritative conditional
    # registry; the control contract intentionally embeds only the OC80
    # high-precision audit, not a second rounded parent clearance record.
    for key in ("direct_clearance_nm", "periodic_image_clearance_nm", "global_minimum_clearance_nm"):
        c2[key] = float(c2[key])
    c2["geometry_hash_sha256"] = contract["IAR_C2_source_geometry_hash"]
    ocrow = dict(c2)
    ocrow["geometry_id"] = "IAR-C2-OC80"
    for key in ("L1_nm", "W1_nm", "L2_nm", "W2_nm", "D_nm", "delta_theta_deg", "theta1_deg", "theta2_deg",
                "j1_center_x_nm", "j1_center_y_nm", "j2_center_x_nm", "j2_center_y_nm", "height_nm", "period_x_nm", "period_y_nm"):
        ocrow[key] = oc[key]
    oc_audit = match["validity_audit_high_precision"]
    ocrow["direct_clearance_nm"] = float(oc_audit["direct_clearance_nm"])
    ocrow["periodic_image_clearance_nm"] = float(oc_audit["periodic_image_clearance_nm"])
    ocrow["global_minimum_clearance_nm"] = float(oc_audit["physical_polygon_minimum_nm"])
    ocrow["geometry_hash_sha256"] = match["geometry_hash_sha256_recomputed"]
    for row in (c2, ocrow):
        for key in ("L1_nm", "W1_nm", "L2_nm", "W2_nm", "D_nm", "height_nm", "period_x_nm", "period_y_nm"):
            row[key] = int(round(float(row[key])))
        for key in ("W1_nm", "W2_nm", "delta_theta_deg", "theta1_deg", "theta2_deg", "j1_center_x_nm", "j1_center_y_nm", "j2_center_x_nm", "j2_center_y_nm"):
            row[key] = float(row[key])
    return {"IAR-C2": c2, "IAR-C2-OC80": ocrow}


def validate_contract(contract: dict[str, Any]) -> dict[str, Any]:
    if contract.get("schema") != "PAPER_A_IAR_C2_ORIENTATION_CONTINUATION_CONTROL_CONTRACT_V1":
        raise RuntimeError("C2_CONTRACT_SCHEMA_INVALID")
    fixed = contract["fixed_IAR_C2_geometry"]
    expected = {"L1_nm": 258, "W1_nm": 88, "L2_nm": 198, "W2_nm": 78, "D_nm": 217,
                "height_nm": 525.0, "period_x_nm": 432.0, "period_y_nm": 432.0}
    if any(float(fixed[k]) != v for k, v in expected.items()):
        raise RuntimeError("C2_FIXED_GEOMETRY_CONTRACT_MISMATCH")
    oc = contract["angle_only_control"]
    audit = oc["validity_audit_high_precision"]
    if oc["geometry_hash_sha256_recomputed"] != "4e5a2cd840e948d7adc6827926514d95fe6a4d1eefb8e5d4f51d952f7a1bd574":
        raise RuntimeError("OC80_GEOMETRY_HASH_AUTHORITY_MISMATCH")
    if contract["IAR_C2_source_geometry_hash"] != "3f09a8a9dd696630b80e7265436157601ee84490d36c02d3ac1e7bd7a6c4636a":
        raise RuntimeError("C2_GEOMETRY_HASH_AUTHORITY_MISMATCH")
    if not all(bool(audit.get(k)) for k in ("direct_no_overlap_or_touch_pass", "periodic_no_overlap_or_touch_pass", "cell_containment_pass", "integer_lateral_dimensions_pass", "half_grid_centers_pass", "current_inherited_gate_pass")):
        raise RuntimeError("OC80_GEOMETRY_VALIDITY_GATE_FAILED")
    if float(audit["direct_clearance_nm"]) < 60.0 or float(audit["periodic_image_clearance_nm"]) < 60.0:
        raise RuntimeError("OC80_CLEARANCE_AUTHORITY_FAILED")
    return {"contract_sha256": sha256(CONTROL_CONTRACT), "c2_hash": contract["IAR_C2_source_geometry_hash"],
            "oc80_hash": oc["geometry_hash_sha256_recomputed"], "c2_geometry": fixed, "oc80_geometry": oc["geometry"],
            "oc80_validity": {"direct_clearance_nm": audit["direct_clearance_nm"], "periodic_clearance_nm": audit["periodic_image_clearance_nm"],
                               "overlap_or_touching": False, "cell_containment_pass": True, "integer_lateral_dimensions_pass": True, "half_grid_centers_pass": True}}


def load_state() -> dict[str, Any]:
    p = RUNTIME / "controller_state.json"
    if p.exists():
        return load_json(p)
    return {"schema": "PAPER_A_IAR_C2_ORIENTATION_CONTINUATION_CONTROLLER_V1", "status": "INITIALIZING",
            "completed_cases": [], "completed_pairs": [], "total_cases": 4,
            "solver_accounting": {"authorized": NEW_BUDGET, "entered": 0, "returned": 0, "accepted": 0, "replay": 0, "RCWA": 0, "ML": 0}}


def save_state(state: dict[str, Any], **updates: Any) -> None:
    state.update(updates); state["updated_utc"] = now(); write_json(RUNTIME / "controller_state.json", state)


def ensure_setup(builder: Any, candidate: str, case_id: str, polarization: str, rows: dict[str, dict[str, Any]], log_path: Path) -> dict[str, Any]:
    case_runtime = RUNTIME / "cases" / case_id
    case_report = REPORT / "sources" / case_id
    case_runtime.mkdir(parents=True, exist_ok=True); case_report.mkdir(parents=True, exist_ok=True)
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
    append_log(log_path, "SETUP_ONLY_START", case_id=case_id, candidate_id=candidate, polarization=polarization)
    original = getattr(builder, "read_row", None)
    builder.read_row = lambda name: rows[name]
    try:
        setup = builder.build(candidate, case_id, polarization, pre)
    finally:
        if original is not None:
            builder.read_row = original
    write_json(setup_path, setup)
    write_json(case_report / "pre_solver_readback.json", {"schema": "PAPER_A_IAR_C2_PRE_SOLVER_READBACK_AUDIT_V1", "status": "PASS",
               "case_id": case_id, "candidate_id": candidate, "polarization": polarization, "setup_only": True,
               "pre_fsp": setup["pre_fsp"], "validation": setup["validation"], "geometry_contract": setup["candidate_registry"],
               "solver_run_called": False, "solver_entered": 0, "timestamp_utc": now()})
    write_json(case_report / "candidate_provenance.json", {"schema": "PAPER_A_IAR_C2_CANDIDATE_PROVENANCE_V1", "case_id": case_id,
               "candidate_id": candidate, "polarization": polarization, "setup_only": True, "pre_fsp": setup["pre_fsp"],
               "candidate_geometry_hash": setup["candidate_geometry_hash_authority"], "builder_path": str(BUILDER), "builder_sha256": sha256(BUILDER),
               "setup_readback_path": str(setup_path), "solver_run_called": False, "solver_entered": 0, "timestamp_utc": now()})
    append_log(log_path, "SETUP_ONLY_PASS", case_id=case_id, pre_fsp_sha256=setup["pre_fsp"]["sha256"])
    return setup


def run_case(builder: Any, scheduler: Any, candidate: str, case_id: str, polarization: str, rows: dict[str, dict[str, Any]], state: dict[str, Any], log_path: Path, contract: dict[str, Any]) -> None:
    setup = ensure_setup(builder, candidate, case_id, polarization, rows, log_path)
    case_runtime = RUNTIME / "cases" / case_id; case_report = REPORT / "sources" / case_id
    pre = case_runtime / f"{case_id}_attempt_001_pre.fsp"; run_input = case_runtime / f"{case_id}_attempt_001_run_input.fsp"
    post = case_runtime / f"{case_id}_attempt_001_post.fsp"; solver_log = case_runtime / f"{case_id}_attempt_001_runner.log"
    provenance_path = case_runtime / f"{case_id}_attempt_001_provenance.json"; expected_sha = setup["pre_fsp"]["sha256"]
    if sha256(pre) != expected_sha:
        raise RuntimeError(f"PREFSP_HASH_MISMATCH:{case_id}")
    if not run_input.exists():
        shutil.copyfile(pre, run_input)
    if sha256(run_input) != expected_sha:
        raise RuntimeError(f"RUN_INPUT_HASH_MISMATCH:{case_id}")
    if provenance_path.exists():
        old = load_json(provenance_path)
        if old.get("solver_entered") and old.get("status") != "ACCEPTED":
            raise RuntimeError(f"HARD_GATE_ENTERED_UNRESOLVED_NO_REPLAY:{case_id}")
        if old.get("status") == "ACCEPTED" and (case_report / "validity_gate_v2.json").exists():
            state["completed_cases"] = sorted(set(state.get("completed_cases", [])) | {case_id}); return
    physical_contract = {"schema": "PAPER_A_IAR_C2_PHYSICAL_CONTRACT_V1", "task": TASK_ID, "candidate_id": candidate, "case_id": case_id,
        "polarization": polarization, "geometry_hash_sha256": rows[candidate]["geometry_hash_sha256"],
        "geometry": rows[candidate], "architecture": "IC1_IC2_FINITE_INTEGRATED_NATIVE_M1", "mesa_nm": [3000, 3000], "array": "5x5 centered finite",
        "source_grid_nm": [400.0, 500.0, 101], "source_position_nm": [0.0, 0.0, -171.5], "domain": "finite xyz PML; no periodic xy",
        "same_integrated_architecture_as_IAR4": True, "mpi_processes": PROCESSES, "threads_per_process": THREADS, "no_auto_replay": True}
    provenance = {"schema": "PAPER_A_IAR_C2_PRODUCTION_PROVENANCE_V1", "case_id": case_id, "candidate_id": candidate, "polarization": polarization,
        "attempt_id": "attempt_001", "status": "WAITING", "solver_entered": False, "solver_run_called": False, "pre_fsp": str(pre),
        "pre_fsp_sha256": expected_sha, "solver_input_fsp": str(run_input), "solver_input_fsp_sha256": sha256(run_input), "post_fsp": str(post),
        "solver_log": str(solver_log), "physical_contract": physical_contract, "physical_contract_sha256": sha_obj(physical_contract),
        "setup_readback": str(case_report / "setup_readback.json"), "setup_readback_sha256": sha256(case_report / "setup_readback.json"),
        "mpi_processes": PROCESSES, "threads_per_process": THREADS, "authorized_new_fdtd_entry": True, "new_fdtd_budget": NEW_BUDGET,
        "no_auto_replay": True, "created_utc": now()}
    write_json(provenance_path, provenance); append_log(solver_log, "PROVENANCE_CREATED", case_id=case_id, solver_entered=False, solver_run_called=False)
    lease = None; fdtd = None
    try:
        while lease is None:
            snap = resource_snapshot(scheduler)
            save_state(state, status="WAITING_FOR_GLOBAL_FDTD_SLOT", current_case=case_id, active_paper_a_fdtd=0, scheduler=snap)
            provenance["last_resource_gate"] = snap; write_json(provenance_path, provenance); append_log(log_path, "RESOURCE_CHECK", case_id=case_id, snapshot=snap)
            if snap["unknown_solver_jobs"]:
                raise RuntimeError(f"HARD_GATE_UNKNOWN_SOLVER_LINEAGE:{json.dumps(snap['unknown_solver_jobs'], sort_keys=True)}")
            try:
                lease = scheduler.GlobalSlotScheduler(SLOT_REGISTRY, process_provider=lambda: process_provider_without_controller(scheduler)).acquire(
                    branch=BRANCH, worktree=str(ROOT), task_id=TASK_ID, case_uid=case_id, pid=os.getpid(),
                    metadata={"task_class": "PAPER_A_IAR_C2_ORIENTATION_CONTINUATION", "candidate_id": candidate, "attempt_id": "attempt_001",
                              "polarization": polarization, "mpi_processes": PROCESSES, "threads_per_process": THREADS, "solver_type": "FDTD"})
            except scheduler.SlotUnavailable as exc:
                provenance["last_slot_exception"] = f"{type(exc).__name__}:{exc}"; write_json(provenance_path, provenance); time.sleep(30.0)
        provenance.update({"status": "SLOT_ACQUIRED", "slot_id": lease.slot_id, "admission_snapshot": lease.record.get("admission_snapshot")}); write_json(provenance_path, provenance)
        append_log(solver_log, "SLOT_ACQUIRED", slot_id=lease.slot_id)
        import lumapi
        fdtd = lumapi.FDTD(hide=True); fdtd.load(str(run_input)); fdtd.setresource("FDTD", 1, "processes", str(PROCESSES))
        if sha256(run_input) != expected_sha:
            raise RuntimeError(f"RUN_INPUT_HASH_CHANGED_BEFORE_ENTRY:{case_id}")
        entered = now(); lease.mark_solver_entered(entered); lease.start_heartbeat()
        provenance.update({"status": "ENTERED", "solver_entered": True, "solver_run_called": True, "entered_utc": entered,
                           "controller_pid": os.getpid(), "solver_engine_resource": {"processes": PROCESSES, "threads": THREADS}})
        write_json(provenance_path, provenance); append_log(solver_log, "SOLVER_ENTERED", case_id=case_id, solver_entered=True, solver_run_called=True,
                                                            mpi_processes=PROCESSES, threads_per_process=THREADS)
        acct = dict(state["solver_accounting"]); acct["entered"] = int(acct.get("entered", 0)) + 1
        save_state(state, status="RUNNING", current_case=case_id, current_solver_pid=os.getpid(), active_paper_a_fdtd=1, solver_accounting=acct)
        fdtd.run()
        returned = now(); fdtd.save(str(post))
        if not post.exists():
            raise RuntimeError(f"POST_FSP_MISSING_AFTER_RETURN:{case_id}")
        provenance.update({"status": "RETURNED", "returned_utc": returned, "post_fsp_sha256": sha256(post), "post_fsp_present": True,
                           "post_return_resource_snapshot": resource_snapshot(scheduler)})
        write_json(provenance_path, provenance); append_log(solver_log, "SOLVER_RETURNED", post_fsp_sha256=provenance["post_fsp_sha256"])
        lease.release("SOLVER_RETURNED", returned); lease = None
        acct["returned"] = int(acct.get("returned", 0)) + 1; save_state(state, status="POSTPROCESSING", current_case=case_id, active_paper_a_fdtd=0, solver_accounting=acct)
    except Exception as exc:
        provenance.update({"status": "FAILED", "error": f"{type(exc).__name__}:{exc}", "traceback": traceback.format_exc(), "non_replayable": bool(provenance.get("solver_entered"))})
        write_json(provenance_path, provenance); append_log(solver_log, "SOLVER_FAILURE", error=provenance["error"], solver_entered=provenance.get("solver_entered")); raise
    finally:
        if lease is not None:
            try: lease.release("FAILED_ENTERED" if provenance.get("solver_entered") else "FAILED_PRE_ENTRY")
            except Exception: append_log(log_path, "LEASE_RELEASE_EXCEPTION", case_id=case_id, traceback=traceback.format_exc())
        if fdtd is not None:
            try: fdtd.close()
            except Exception: pass
    cmd = [sys.executable, str(SOURCE_POST), "--case-id", case_id, "--candidate-id", candidate, "--polarization", polarization,
           "--post-fsp", str(post), "--provenance", str(provenance_path), "--output-dir", str(case_report), "--runtime-dir", str(case_runtime)]
    last = None
    for n in (1, 2):
        last = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
        (case_runtime / f"postprocess_attempt_{n}.stdout.log").write_text(last.stdout + "\n" + last.stderr, encoding="utf-8")
        if last.returncode == 0: break
        append_log(log_path, "POSTPROCESS_ATTEMPT_FAILED", case_id=case_id, attempt=n, returncode=last.returncode, stderr=last.stderr[-5000:])
    if last is None or last.returncode != 0:
        raise RuntimeError(f"HARD_GATE_POSTPROCESS_FAILED:{case_id}")
    validity_path = case_report / "validity_gate_v2.json"
    if not validity_path.exists(): raise RuntimeError(f"HARD_GATE_VALIDITY_ARTIFACT_MISSING:{case_id}")
    validity = load_json(validity_path)
    if validity.get("status") != "VALID_FOR_IC1_INTEGRATED_CANARY_TRUTH":
        raise RuntimeError(f"HARD_GATE_PHYSICS_VALIDITY:{case_id}:{validity.get('status')}")
    provenance.update({"status": "ACCEPTED", "accepted_utc": now(), "validity_gate": validity.get("status")}); write_json(provenance_path, provenance)
    state["completed_cases"] = sorted(set(state.get("completed_cases", [])) | {case_id})
    acct = dict(state["solver_accounting"]); acct["accepted"] = int(acct.get("accepted", 0)) + 1
    save_state(state, status="CASE_COMPLETED", current_case=case_id, active_paper_a_fdtd=0, solver_accounting=acct)
    append_log(log_path, "CASE_ACCEPTED", case_id=case_id, validity_status=validity.get("status"))


def run_pair(candidate: str, x_case: str, y_case: str, state: dict[str, Any], log_path: Path) -> None:
    runtime_out = RUNTIME / "pairs" / candidate; report_out = REPORT / "pairs" / candidate
    runtime_out.mkdir(parents=True, exist_ok=True); report_out.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(PAIR_CLOSEOUT), "--candidate-id", candidate, "--x-case", x_case, "--y-case", y_case,
           "--x-dir", str(REPORT / "sources" / x_case), "--y-dir", str(REPORT / "sources" / y_case),
           "--x-post-fsp", str(RUNTIME / "cases" / x_case / f"{x_case}_attempt_001_post.fsp"),
           "--y-post-fsp", str(RUNTIME / "cases" / y_case / f"{y_case}_attempt_001_post.fsp"), "--output-dir", str(runtime_out)]
    save_state(state, status="PAIR_POSTPROCESSING", current_pair=candidate, active_paper_a_fdtd=0)
    result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    (RUNTIME / f"{candidate}_pair_postprocess.stdout.log").write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
    if result.returncode != 0: append_log(log_path, "PAIR_FAILURE", candidate_id=candidate, stderr=result.stderr[-5000:]); raise RuntimeError(f"HARD_GATE_PAIR_CLOSEOUT_FAILED:{candidate}")
    summary = load_json(runtime_out / "pair_summary.json")
    if summary.get("status") != "PASS": raise RuntimeError(f"HARD_GATE_PAIR_CLOSEOUT_STATUS:{candidate}:{summary.get('status')}")
    formal = {"pair_wavelength_metrics.csv", "angular_cancellation_metrics.csv", "source_cancellation_metrics.csv", "pair_stokes.csv",
              "pair_450nm_anchor.json", "pair_broadband_summary.json", "pair_summary.json", "pair_audit.json"}
    for name in formal:
        src = runtime_out / name
        if not src.exists(): raise RuntimeError(f"PAIR_FORMAL_ARTIFACT_MISSING:{candidate}:{name}")
        shutil.copy2(src, report_out / name)
    state["completed_pairs"] = sorted(set(state.get("completed_pairs", [])) | {candidate}); save_state(state, status="PAIR_COMPLETED", current_pair=candidate)
    append_log(log_path, "PAIR_CLOSEOUT_PASS", candidate_id=candidate, report_dir=str(report_out))


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return [{k: (float(v) if k != "individual_axis_confident" and k != "psi_axis_ill_conditioned" else v.lower() == "true") for k, v in row.items()} for row in csv.DictReader(f)]


def fv(row: dict[str, Any], key: str) -> float:
    return float(row[key])


def load_pair_directory(path: Path) -> dict[float, dict[str, float]]:
    pair = read_csv(path / "pair_wavelength_metrics.csv")
    angular = read_csv(path / "angular_cancellation_metrics.csv")
    a = {round(fv(r, "wavelength_nm"), 8): r for r in angular}
    out = {}
    for r in pair:
        key = round(fv(r, "wavelength_nm"), 8)
        if key not in a: raise RuntimeError(f"PAIR_ANGULAR_WAVELENGTH_MISSING:{path}:{key}")
        out[key] = {**r, **a[key]}
    if len(out) != 101: raise RuntimeError(f"PAIR_POINT_COUNT_INVALID:{path}:{len(out)}")
    return out


METRICS = ("DoLP_pair", "C_source", "C_angular", "full_angle_pair_DoLP", "upward_source_normalized_power_pair",
           "useful_LP_axisfree_pair", "useful_LP_over_S0_pair", "normal_5deg_DoLP", "normal_10deg_DoLP", "normal_20deg_DoLP")


def metric_stats(values: list[float]) -> dict[str, Any]:
    values = [float(v) for v in values]
    return {"count": len(values), "mean": sum(values) / len(values), "median": sorted(values)[len(values) // 2] if len(values) % 2 else (sorted(values)[len(values)//2-1] + sorted(values)[len(values)//2]) / 2.0,
            "minimum": min(values), "maximum": max(values)}


def intervals(wavelengths: list[float]) -> list[list[float]]:
    if not wavelengths: return []
    vals = sorted(wavelengths); groups = [[vals[0]]]
    for v in vals[1:]:
        if abs(v - groups[-1][-1] - 1.0) < 1e-6: groups[-1].append(v)
        else: groups.append([v])
    return [[g[0], g[-1]] for g in groups]


def comparison(new: dict[float, dict[str, float]], ref: dict[float, dict[str, float]], scopes: dict[str, list[float]], label: str, csv_rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {"comparison": label, "delta_definition": "new_minus_reference", "scopes": {}}
    for scope, wavelengths in scopes.items():
        by_metric: dict[str, Any] = {}
        for metric in METRICS:
            vals = []
            for wl in wavelengths:
                key = round(wl, 8)
                delta = fv(new[key], metric) - fv(ref[key], metric)
                vals.append(delta)
                csv_rows.append({"comparison": label, "scope": scope, "wavelength_nm": key, "metric": metric, "new": fv(new[key], metric), "reference": fv(ref[key], metric), "delta": delta})
            pos = [w for w, v in zip(wavelengths, vals) if v > 0.0]; neg = [w for w, v in zip(wavelengths, vals) if v < 0.0]
            by_metric[metric] = {**metric_stats(vals), "positive_count": len(pos), "negative_count": len(neg), "positive_fraction": len(pos)/len(vals), "negative_fraction": len(neg)/len(vals),
                                 "positive_intervals_nm": intervals(pos), "negative_intervals_nm": intervals(neg)}
        result["scopes"][scope] = {"wavelength_count": len(wavelengths), "metrics": by_metric}
    return result


def anchor(pair: dict[float, dict[str, float]]) -> dict[str, Any]:
    r = pair[450.0]
    return {"wavelength_nm": 450.0, **{m: fv(r, m) for m in METRICS}}


def write_analysis(contract_snapshot: dict[str, Any]) -> dict[str, Any]:
    c2 = load_pair_directory(REPORT / "pairs" / "IAR-C2")
    oc = load_pair_directory(REPORT / "pairs" / "IAR-C2-OC80")
    iar4 = load_pair_directory(BASE / "reports/integrated_aware_lp_initial_truth_v1/pairs/IAR4")
    scopes = {"exact_450_nm": [450.0], "diagnostic_445_455_nm": [float(x) for x in range(445, 456)], "diagnostic_400_500_nm": [float(x) for x in range(400, 501)]}
    delta_rows: list[dict[str, Any]] = []
    oc_vs_c2 = comparison(oc, c2, scopes, "IAR-C2-OC80_minus_IAR-C2", delta_rows)
    c2_vs_iar4 = comparison(c2, iar4, scopes, "IAR-C2_minus_IAR4", delta_rows)
    oc_vs_iar4 = comparison(oc, iar4, scopes, "IAR-C2-OC80_minus_IAR4", delta_rows)
    with (REPORT / "spectral_delta_metrics.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["comparison", "scope", "wavelength_nm", "metric", "new", "reference", "delta"]); writer.writeheader(); writer.writerows(delta_rows)
    write_json(REPORT / "iar_c2_pair_summary.json", load_json(REPORT / "pairs/IAR-C2/pair_summary.json"))
    write_json(REPORT / "iar_c2_oc80_pair_summary.json", load_json(REPORT / "pairs/IAR-C2-OC80/pair_summary.json"))
    write_json(REPORT / "iar_c2_vs_iar4_basin_comparison.json", c2_vs_iar4)
    write_json(REPORT / "oc80_vs_c2_causal_comparison.json", oc_vs_c2)
    write_json(REPORT / "oc80_vs_iar4_practical_comparison.json", oc_vs_iar4)
    absolute = {"schema": "PAPER_A_IAR_C2_ABSOLUTE_PERFORMANCE_SUMMARY_V1", "source_normalization": "sourcepower-normalized; no W_emit; no absolute LEE",
                "I03_baseline": load_json(BASE / "reports/integrated_aware_lp_redesign_contract_v1/integrated_baseline_metrics.json"),
                "IAR4": anchor(iar4), "IAR-C2": anchor(c2), "IAR-C2-OC80": anchor(oc)}
    write_json(REPORT / "absolute_performance_summary.json", absolute)
    ratios = {"schema": "PAPER_A_IAR_C2_POWER_COLLAPSE_AUDIT_V1", "metric_semantics": {"upward": "top-face source-normalized upward power", "useful_LP": "axis-free useful LP power"}, "ratios": {}}
    for num, den in (("IAR-C2", "IAR4"), ("IAR-C2-OC80", "IAR-C2"), ("IAR-C2-OC80", "IAR4")):
        ratios["ratios"][f"{num}_over_{den}"] = {"450_nm": {}, "full_400_500_nm": {}}
        for key in ("upward_source_normalized_power_pair", "useful_LP_axisfree_pair"):
            ratios["ratios"][f"{num}_over_{den}"]["450_nm"][key] = fv((oc if num == "IAR-C2-OC80" else c2 if num == "IAR-C2" else iar4)[450.0], key) / fv((iar4 if den == "IAR4" else c2)[450.0], key)
            ns = oc if num == "IAR-C2-OC80" else c2 if num == "IAR-C2" else iar4; ds = iar4 if den == "IAR4" else c2
            vals = [fv(ns[w], key) / fv(ds[w], key) for w in ns]
            ratios["ratios"][f"{num}_over_{den}"]["full_400_500_nm"][key] = metric_stats(vals)
    write_json(REPORT / "power_collapse_audit.json", ratios)
    result = {"schema": "PAPER_A_IAR_C2_ORIENTATION_CONTINUATION_FINAL_ANALYSIS_V1", "status": "PASS", "scopes": scopes,
              "IAR-C2_450_nm": anchor(c2), "IAR-C2-OC80_450_nm": anchor(oc), "OC80_vs_C2": oc_vs_c2,
              "C2_vs_IAR4": c2_vs_iar4, "OC80_vs_IAR4": oc_vs_iar4,
              "interpretation": {"local_basin": "DESCRIPTIVE_COMPARISON_READY; not an orientation-causality claim", "orientation_replication": "REQUIRES_NUMERIC_REVIEW; no automatic GO/STOP", "absolute_functional_gain": "DESCRIPTIVE_ONLY", "W_emit": "UNRESOLVED_NOT_USED"},
              "contract": contract_snapshot, "solver_accounting": {"new_solver_in_analysis": 0}}
    write_json(REPORT / "analysis_summary.json", result)
    return result


def write_report(snapshot: dict[str, Any], analysis: dict[str, Any], contract_snapshot: dict[str, Any], state: dict[str, Any]) -> None:
    c2a = analysis["IAR-C2_450_nm"]; oca = analysis["IAR-C2-OC80_450_nm"]
    report = f"""# IAR-C2 / IAR-C2-OC80 bounded validation

This is the final bounded local integrated-aware LP validation batch. It uses current Native-M1, the existing finite 3000 x 3000 nm mesa / centered 5 x 5 architecture, 400-500 nm and 101 points, and sourcepower normalization. W_emit remains unresolved; no historical Gaussian or absolute LEE claim is used.

## Solver truth

Four independent cases were authorized and run sequentially with 12 MPI processes x 1 thread and PAPER_A active FDTD <= 1. Pair Stokes uses S_i,pair = 0.5 S_i,x + 0.5 S_i,y; fields are not coherently added and DoLP/psi are not averaged.

## 450 nm anchor

| candidate | pair DoLP | C_source | C_angular | upward top-face/source | useful LP | useful LP/S0 |
|---|---:|---:|---:|---:|---:|---:|
| IAR-C2 | {c2a['DoLP_pair']:.9g} | {c2a['C_source']:.9g} | {c2a['C_angular']:.9g} | {c2a['upward_source_normalized_power_pair']:.9g} | {c2a['useful_LP_axisfree_pair']:.9g} | {c2a['useful_LP_over_S0_pair']:.9g} |
| IAR-C2-OC80 | {oca['DoLP_pair']:.9g} | {oca['C_source']:.9g} | {oca['C_angular']:.9g} | {oca['upward_source_normalized_power_pair']:.9g} | {oca['useful_LP_axisfree_pair']:.9g} | {oca['useful_LP_over_S0_pair']:.9g} |

## Scope boundaries

The OC80-C2 comparison is the strict orientation continuation comparison; C2-IAR4 is a local-basin/clearance transfer comparison; OC80-IAR4 is a practical continuation comparison. 445-455 nm is an unweighted diagnostic window and 400-500 nm is a diagnostic band. No new composite score or promotion threshold is introduced. Chart retains the final LP GO/STOP decision.

## Status

4/4 individual validity and both pair closeouts are PASS. Individual validity status is `VALID_FOR_IC1_INTEGRATED_CANARY_TRUTH`; the active V2 instrumented contract is retained in each validity artifact. Solver accounting: {json.dumps(state['solver_accounting'], ensure_ascii=False)}; active FDTD after closeout: {snapshot.get('active_fdtd_jobs')}.

## Artifacts

See `canonical_geometry_provenance.json`, `per_source_validity/`, the three comparison JSON files, `spectral_delta_metrics.csv`, `absolute_performance_summary.json`, `power_collapse_audit.json`, `solver_accounting.json`, and `validation_tests.json`. Runtime FSP/MAT/LOG remain outside Git.
"""
    (REPORT / "final_report.md").write_text(report, encoding="utf-8")


def execute() -> None:
    REPORT.mkdir(parents=True, exist_ok=True); RUNTIME.mkdir(parents=True, exist_ok=True)
    contract = load_json(CONTROL_CONTRACT); contract_snapshot = validate_contract(contract); rows = make_rows(contract)
    scheduler = load_module(SCHEDULER, "iar_global_scheduler_c2"); builder = load_module(BUILDER, "iar_c2_integrated_builder")
    log_path = RUNTIME / "controller.jsonl"; state = load_state()
    save_state(state, status="PREFLIGHT", authorized_cases=[x[1] for x in CASES], active_limit=1, production_resources={"mpi_processes": PROCESSES, "threads_per_process": THREADS}, contract_sha256=contract_snapshot["contract_sha256"])
    snap = resource_snapshot(scheduler); write_json(REPORT / "resource_preflight.json", snap)
    if snap["unknown_solver_jobs"]: raise RuntimeError(f"HARD_GATE_UNKNOWN_SOLVER_LINEAGE:{json.dumps(snap['unknown_solver_jobs'], sort_keys=True)}")
    provenance = {"schema": "PAPER_A_IAR_C2_CANONICAL_GEOMETRY_PROVENANCE_V1", "status": "PASS", "contract": contract_snapshot,
                  "contract_path": str(CONTROL_CONTRACT), "contract_sha256": sha256(CONTROL_CONTRACT), "source_registry_path": str(CONDITIONAL_REGISTRY),
                  "source_registry_sha256": sha256(CONDITIONAL_REGISTRY), "cases": {k: {"geometry": rows[k], "geometry_hash": rows[k]["geometry_hash_sha256"]} for k in rows},
                  "physics_architecture": "existing IAR4 finite integrated architecture; no mesh/domain/source/monitor changes", "pre_solver_resource_snapshot": snap,
                  "solver_run_called": False, "solver_entered": 0, "new_fdtd_budget": NEW_BUDGET, "timestamp_utc": now()}
    write_json(REPORT / "canonical_geometry_provenance.json", provenance)
    for candidate, case_id, polarization in CASES:
        if case_id not in state.get("completed_cases", []):
            run_case(builder, scheduler, candidate, case_id, polarization, rows, state, log_path, contract)
        save_state(state, status="CASE_BOUNDARY_CHECK", current_case=None, active_paper_a_fdtd=0, scheduler=resource_snapshot(scheduler))
    if "IAR-C2" not in state.get("completed_pairs", []): run_pair("IAR-C2", "IAR-C2_x", "IAR-C2_y", state, log_path)
    if "IAR-C2-OC80" not in state.get("completed_pairs", []): run_pair("IAR-C2-OC80", "IAR-C2-OC80_x", "IAR-C2-OC80_y", state, log_path)
    analysis = write_analysis(contract_snapshot); final_snap = resource_snapshot(scheduler)
    if final_snap["active_fdtd_jobs"] != 0: raise RuntimeError(f"HARD_GATE_ACTIVE_FDTD_AFTER_CLOSEOUT:{final_snap['active_fdtd_jobs']}")
    write_json(REPORT / "solver_accounting.json", {"schema": "PAPER_A_IAR_C2_SOLVER_ACCOUNTING_V1", **state["solver_accounting"], "replay": 0, "RCWA": 0, "ML": 0,
                "new_fdtd_budget": NEW_BUDGET, "active_fdtd": 0, "solver_run_called": True, "timestamp_utc": now()})
    write_json(REPORT / "validation_tests.json", {"schema": "PAPER_A_IAR_C2_VALIDATION_TESTS_V1", "status": "PASS", "individual_cases": 4,
                "individual_validity": "VALID_FOR_IC1_INTEGRATED_CANARY_TRUTH", "pair_closeouts": 2, "spectral_grid_101": True, "exact_450_anchor": True,
                "pair_incoherent_stokes": True, "no_W_emit": True, "no_historical_gaussian": True, "no_new_solver_in_analysis": True,
                "no_new_composite_score": True, "paper_a_active_limit": 1, "active_fdtd_after_closeout": 0, "timestamp_utc": now()})
    write_report(final_snap, analysis, contract_snapshot, state)
    save_state(state, status="TERMINAL_COMPLETION", current_case=None, current_pair=None, active_paper_a_fdtd=0, solver_accounting=state["solver_accounting"], final_resource_snapshot=final_snap)
    write_json(REPORT / "terminal_success.json", {"schema": "PAPER_A_IAR_C2_ORIENTATION_CONTINUATION_TERMINAL_SUCCESS_V1", "status": "PASS",
                "case_ids": [x[1] for x in CASES], "pair_closeouts": ["IAR-C2", "IAR-C2-OC80"], "analysis": "PASS", "solver_accounting": state["solver_accounting"],
                "active_fdtd": 0, "no_additional_solver": True, "timestamp_utc": now()})
    append_log(log_path, "TERMINAL_SUCCESS", report=str(REPORT / "final_report.md"))


def preflight() -> int:
    contract = load_json(CONTROL_CONTRACT); snap_contract = validate_contract(contract); scheduler = load_module(SCHEDULER, "iar_global_scheduler_c2_preflight")
    snap = resource_snapshot(scheduler); write_json(REPORT / "resource_preflight.json", snap)
    out = {"status": "PASS" if not snap["unknown_solver_jobs"] else "HARD_GATE", "contract": snap_contract, "active_fdtd_jobs": snap["active_fdtd_jobs"],
           "active_rcwa_jobs": snap["active_rcwa_jobs"], "unknown_solver_jobs": snap["unknown_solver_jobs"], "external_fluent_jobs": snap.get("external_fluent_jobs", []),
           "solver_run_called": False, "solver_entered": 0, "new_fdtd_budget": NEW_BUDGET}
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str)); return 0 if out["status"] == "PASS" else 2


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--preflight", action="store_true"); parser.add_argument("--execute", action="store_true"); args = parser.parse_args()
    try:
        if args.preflight: return preflight()
        if not args.execute: raise SystemExit("EXECUTE_FLAG_REQUIRED")
        execute(); return 0
    except Exception as exc:
        REPORT.mkdir(parents=True, exist_ok=True); RUNTIME.mkdir(parents=True, exist_ok=True); state = load_state()
        write_json(REPORT / "terminal_failure.json", {"schema": "PAPER_A_IAR_C2_ORIENTATION_CONTINUATION_TERMINAL_FAILURE_V1", "status": "HARD_GATE",
                    "error": f"{type(exc).__name__}:{exc}", "traceback": traceback.format_exc(), "solver_accounting": state.get("solver_accounting", {}),
                    "no_auto_replay": True, "timestamp_utc": now()})
        save_state(state, status="HARD_GATE", terminal_artifact=str(REPORT / "terminal_failure.json"), hard_gate=f"{type(exc).__name__}:{exc}")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
