from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
REPORT = ROOT / "paper_a_broadband/reports/lp_bf01_bf04_initial_truth_v1"
RUNTIME = ROOT / "paper_a_broadband/runtime/search_anisotropy_bf01_bf04_initial_truth_v1"
SELECTION = ROOT / "paper_a_broadband/reports/lp_anisotropy_feasible_space_v2_balanced_selection/balanced_selected_candidates.json"
PREPARED = ROOT / "paper_a_broadband/reports/lp_anisotropy_feasible_space_v2_balanced_selection/prepared_fsp_provenance.json"
AUTHORITY = ROOT / "paper_a_broadband/authority/paper_a_bf01_bf04_prepared_fsp_authority_v1.json"
SEMANTIC_FINGERPRINT_MANIFEST = ROOT / "paper_a_broadband/reports/bf01_bf04_provenance_reconciliation_v1/semantic_fingerprint_manifest.json"
SEMANTIC_READER_PATH = ROOT / "paper_a_broadband/scripts/bf01_bf04_prepared_fsp_reconciliation_v1.py"
BASE_RUNNER = ROOT / "paper_a_broadband/scripts/lp_anisotropy_expanded_search_runner_v1.py"
SLOT_REGISTRY = Path(r"D:/project/apcd_global_fdtd_slot_registry_v1.json")
TASK_ID = "PAPER_A_LP_BF01_BF04_INITIAL_BROADBAND_FULL_JONES_TRUTH_BATCH_V1"
INITIAL = ["BF01", "BF02", "BF03", "BF04"]
CONDITIONAL = ["BF05", "BF06", "BF07", "BF08"]
GRID = [435.0 + i for i in range(31)]
MAX_PHYSICS_JOBS = 8
MAX_ACTIVE_PAPER_A_FDTD = 1
MONITOR_INTERVAL_S = 600.0

sys.path.insert(0, r"N:/Program Files/ANSYS Inc/v251/Lumerical/api/python")
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def sha_obj(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(temp, path)


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, default=str) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    temp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    with temp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or ["status"], extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temp, path)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"MODULE_LOAD_FAILED:{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = load_module(BASE_RUNNER, "lp_anisotropy_expanded_search_runner_v1_balanced_truth")
SEMANTIC_READER = load_module(SEMANTIC_READER_PATH, "bf01_bf04_semantic_reader_for_admission")
BASE.PLANNING_ONLY = False
BASE.REPORT = REPORT
BASE.RUNTIME = RUNTIME
BASE.TASK_ID = TASK_ID
BASE.PREV.REPORT = REPORT
BASE.PREV.RUNTIME = RUNTIME
BASE.PREV.TASK_ID = TASK_ID
BASE.PREV.PROCESSES = 12
BASE.PREV.THREADS = 1


def selected_rows() -> list[dict[str, Any]]:
    data = json.loads(SELECTION.read_text(encoding="utf-8"))
    rows = data.get("candidates", [])
    if [row.get("geometry_id") for row in rows] != INITIAL + CONDITIONAL:
        raise RuntimeError("HARD_GATE_BALANCED_SELECTION_IDENTITY")
    if data.get("optical_information_used") is not False:
        raise RuntimeError("HARD_GATE_SELECTION_OPTICAL_CONTAMINATION")
    return rows


def mapped_geometry(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "j1_length_nm": row["L1_nm"],
        "j1_width_nm": row["W1_nm"],
        "j2_length_nm": row["L2_nm"],
        "j2_width_nm": row["W2_nm"],
        "j1_rotation_deg": row["theta1_deg"],
        "j2_rotation_deg": row["theta2_deg"],
        "source": "BALANCED_MECHANISM_STRATIFIED_SELECTION",
        "anisotropy_ratio_1": float(row["L1_nm"]) / float(row["W1_nm"]),
        "anisotropy_ratio_2": float(row["L2_nm"]) / float(row["W2_nm"]),
        "relative_anisotropy": row["delta_A"],
        "validity": {"geometry_valid": row.get("validity") == "PASS"},
    }


def load_doe() -> dict[str, Any]:
    rows = [mapped_geometry(row) for row in selected_rows()]
    return {
        "schema": "PAPER_A_LP_ANISOTROPY_BALANCED_TRUTH_DOE_V1",
        "freeze_sha256": sha_file(SELECTION),
        "geometries": rows,
        "initial_geometry_ids": INITIAL,
        "conditional_geometry_ids": CONDITIONAL,
        "solver_calls": 0,
    }


BASE.load_doe = load_doe
BASE.PREV.load_doe = load_doe


_base_write_json = BASE.PREV.write_json


def instrumented_base_write_json(path: Path, value: Any) -> None:
    if path.name == "attempt_provenance.json" and isinstance(value, dict):
        value = dict(value)
        case_id = value.get("case_id")
        geometry = next((g for g in load_doe()["geometries"] if g["geometry_id"] == str(case_id).rsplit("_", 1)[0]), None)
        contract = {
            "task_id": TASK_ID,
            "case_id": case_id,
            "geometry_hash_sha256": geometry.get("geometry_hash_sha256") if geometry else None,
            "pre_fsp_sha256": value.get("pre_fsp_sha256"),
            "material": "APCD_TIO2_NATIVE_M1",
            "source_span_nm": [430.0, 470.0],
            "formal_window_nm": [435.0, 465.0],
            "formal_points": 31,
            "diffraction_order": [0, 0],
            "mpi_processes": 12,
            "threads": 1,
            "mesh_boundary_unchanged": True,
            "normalization_renormalized": False,
        }
        case_runtime = RUNTIME / "cases" / str(case_id)
        archived_attempts = list(case_runtime.glob("attempt_provenance_attempt_*.json"))
        value.setdefault("attempt_id", f"{case_id}_attempt_{len(archived_attempts) + 1:03d}")
        value["physical_contract"] = contract
        value["physical_contract_sha256"] = sha_obj(contract)
    _base_write_json(path, value)


BASE.PREV.write_json = instrumented_base_write_json


def upsert_geometry_rows(path: Path, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    geometry_ids = {str(row.get("geometry_id")) for row in rows}
    old: list[dict[str, Any]] = []
    if path.exists():
        with path.open(encoding="utf-8", newline="") as handle:
            old = [row for row in csv.DictReader(handle) if str(row.get("geometry_id")) not in geometry_ids]
    return old + rows


BASE._append_csv = upsert_geometry_rows


def prepared_map() -> dict[str, dict[str, Any]]:
    data = json.loads(AUTHORITY.read_text(encoding="utf-8"))
    if data.get("schema") != "PAPER_A_BF01_BF04_PREPARED_FSP_AUTHORITY_V1":
        raise RuntimeError("HARD_GATE_PREPARED_AUTHORITY_SCHEMA")
    if data.get("status") != "FRESH_SETUP_ONLY_INPUTS_AUTHORIZED_PENDING_SOLVER_ADMISSION":
        raise RuntimeError("HARD_GATE_PREPARED_AUTHORITY_STATUS")
    rows = {case_id: dict(row) for case_id, row in data.get("cases", {}).items()}
    v2_report_dir = ROOT / "paper_a_broadband/reports/fdtd_physics_validity_gate_v2_instrumented"
    for case_id in list(rows):
        v2_setup_path = v2_report_dir / (case_id + "_attempt_002_setup_only.json")
        if not v2_setup_path.exists():
            continue
        v2 = json.loads(v2_setup_path.read_text(encoding="utf-8"))
        if v2.get("status") == "PASS" and v2.get("case_id") == case_id:
            row = rows[case_id]
            row.update({
                "path": v2["instrumented_pre_fsp"]["path"],
                "sha256": v2["instrumented_pre_fsp"]["sha256"],
                "semantic_fingerprint": v2["physics_semantic_fingerprint"]["legacy_full_semantic_before"],
                "physics_semantic_fingerprint": v2["physics_semantic_fingerprint"]["after"],
                "convergence_instrumentation_fingerprint": v2["convergence_instrumentation_fingerprint"],
                "physics_fingerprint_mode": v2.get("physics_semantic_fingerprint", {}).get("numeric_normalization", "exact"),
                "instrumented_v2": True,
            })
            rows[case_id] = row
    return rows


def _normalize_numeric(value: Any) -> Any:
    if isinstance(value, float):
        return float(format(value, ".15g"))
    if isinstance(value, dict):
        return {str(k): _normalize_numeric(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_numeric(v) for v in value]
    return value


def physics_semantic_view(semantic: dict[str, Any]) -> dict[str, Any]:
    view = json.loads(json.dumps(semantic, default=str))
    view.pop("object_names", None)
    return view


def normalized_physics_semantic_view(semantic: dict[str, Any]) -> dict[str, Any]:
    return _normalize_numeric(physics_semantic_view(semantic))


def verify_authoritative_input(case_id: str, path: Path | None = None) -> dict[str, Any]:
    authority = prepared_map().get(case_id)
    if authority is None:
        return {"pass": False, "case_id": case_id, "failure": "AUTHORITY_CASE_MISSING"}
    expected_path = Path(authority["path"])
    actual_path = Path(path) if path is not None else expected_path
    path_match = actual_path.resolve() == expected_path.resolve()
    actual_sha = sha_file(actual_path) if actual_path.exists() else None
    polarization = case_id.rsplit("_", 1)[1]
    readback = SEMANTIC_READER.read_fsp(actual_path, case_id, polarization) if actual_path.exists() else None
    actual_fingerprint = SEMANTIC_READER.sha_obj(readback["semantic"]) if readback and readback.get("readback_complete") else None
    if readback and readback.get("readback_complete"):
        fingerprint_view = normalized_physics_semantic_view(readback["semantic"]) if authority.get("physics_fingerprint_mode") == "15 significant digits for audit-only serialization; no physics values changed" else physics_semantic_view(readback["semantic"])
        actual_physics_fingerprint = SEMANTIC_READER.sha_obj(fingerprint_view)
    else:
        actual_physics_fingerprint = None
    binary_match = actual_sha == authority.get("sha256")
    instrumented = bool(authority.get("instrumented_v2"))
    fingerprint_match = actual_physics_fingerprint == authority.get("physics_semantic_fingerprint") if instrumented else actual_fingerprint == authority.get("semantic_fingerprint")
    readback_complete = bool(readback and readback.get("readback_complete"))
    return {
        "pass": bool(path_match and binary_match and fingerprint_match and readback_complete),
        "case_id": case_id,
        "path": str(actual_path),
        "authority_path": str(expected_path),
        "path_match": path_match,
        "actual_sha256": actual_sha,
        "authority_sha256": authority.get("sha256"),
        "binary_sha_match": binary_match,
        "actual_semantic_fingerprint": actual_fingerprint,
        "actual_physics_semantic_fingerprint": actual_physics_fingerprint,
        "authority_semantic_fingerprint": authority.get("semantic_fingerprint"),
        "authority_physics_semantic_fingerprint": authority.get("physics_semantic_fingerprint"),
        "semantic_fingerprint_match": fingerprint_match,
        "instrumented_v2": instrumented,
        "convergence_instrumentation_fingerprint": authority.get("convergence_instrumentation_fingerprint"),
        "readback_complete": readback_complete,
        "failure": None if path_match and binary_match and fingerprint_match and readback_complete else "PREPARED_INPUT_AUTHORITY_MISMATCH",
    }


def pre_entry_authority_check(case_id: str, path: Path) -> dict[str, Any]:
    result = verify_authoritative_input(case_id, path)
    result["checked_before_solver_entry"] = True
    result["timestamp_utc"] = now()
    return result


BASE.PREV.PRE_ENTRY_AUTHORITY_CHECK = pre_entry_authority_check


def materialize_setup_metadata() -> list[dict[str, Any]]:
    geometries = {g["geometry_id"]: g for g in load_doe()["geometries"]}
    prepared = prepared_map()
    results = []
    for geometry_id in INITIAL:
        geometry = geometries[geometry_id]
        for polarization in ("x", "y"):
            case_id = f"{geometry_id}_{polarization}"
            source = prepared.get(case_id)
            if source is None:
                raise RuntimeError(f"HARD_GATE_PREPARED_AUTHORITY_MISSING:{case_id}")
            path = Path(source["path"])
            verification = verify_authoritative_input(case_id, path)
            actual_hash = verification["actual_sha256"]
            passed = bool(verification["pass"])
            setup = {
                "schema": "PAPER_A_LP_ANISOTROPY_BALANCED_TRUTH_SETUP_REUSE_V1",
                "case_id": case_id,
                "geometry_id": geometry_id,
                "polarization": polarization,
                "status": "PASS" if passed else "HARD_GATE",
                "solver_entered": False,
                "solver_run_called": False,
                "pre_fsp": {"path": str(path), "sha256": actual_hash, "authority_sha256": source.get("sha256"), "semantic_fingerprint": verification["actual_semantic_fingerprint"], "physics_semantic_fingerprint": verification.get("actual_physics_semantic_fingerprint"), "authority_semantic_fingerprint": source.get("semantic_fingerprint"), "authority_physics_semantic_fingerprint": source.get("physics_semantic_fingerprint"), "convergence_instrumentation_fingerprint": source.get("convergence_instrumentation_fingerprint"), "instrumented_v2": bool(source.get("instrumented_v2")), "parent_sha256": source.get("parent_fsp_sha256")},
                "gate": {"pass": passed, "authority_binary_match": verification["binary_sha_match"], "authority_semantic_fingerprint_match": verification["semantic_fingerprint_match"], "readback_complete": verification["readback_complete"], "path_match": verification["path_match"], "readback": {"semantic_fingerprint": verification["actual_semantic_fingerprint"]}},
                "material_contract": "APCD_TIO2_NATIVE_M1",
                "source_span_nm": [430.0, 470.0],
                "formal_grid_nm": [435.0, 465.0],
                "formal_points": 31,
                "processes": 12,
                "threads": 1,
                "timestamp_utc": now(),
            }
            write_json(RUNTIME / "cases" / case_id / "setup_only.json", setup)
            if source.get("instrumented_v2"):
                write_json(RUNTIME / "cases" / f"{case_id}_attempt_002" / "setup_only.json", setup)
            results.append(setup)
    return results


def scheduler_snapshot() -> dict[str, Any]:
    return BASE.scheduler_snapshot()


def registry_queue_demands() -> list[dict[str, Any]]:
    if not SLOT_REGISTRY.exists():
        return []
    data = json.loads(SLOT_REGISTRY.read_text(encoding="utf-8-sig"))
    demands = []
    for key in ("pending_jobs", "waiting_jobs", "ready_jobs", "queue"):
        for row in data.get(key, []) if isinstance(data.get(key), list) else []:
            branch = str(row.get("branch") or row.get("task_id") or "")
            if "np" in branch.lower() or "coupling" in branch.lower() or "mdc" in branch.lower():
                demands.append({"registry_field": key, "record": row})
    return demands


def boundary_check() -> dict[str, Any]:
    snapshot = scheduler_snapshot()
    other = [job for job in snapshot.get("jobs", []) if job.get("branch") != BASE.BRANCH]
    queued = registry_queue_demands()
    allowed = not snapshot.get("unknown_solver_jobs") and not other and not queued and snapshot.get("active_fdtd_jobs") == 0
    result = {
        "timestamp_utc": now(),
        "snapshot": snapshot,
        "explicit_high_priority_registry_demand": queued,
        "allow_next_wave": allowed,
        "reason": "NO_ACTIVE_OR_EXPLICIT_QUEUED_HIGH_PRIORITY_SOLVER" if allowed else "CASE_BOUNDARY_YIELD",
    }
    append_jsonl(REPORT / "boundary_events.jsonl", result)
    return result


BASE.boundary_check = boundary_check


def preflight() -> dict[str, Any]:
    setup = materialize_setup_metadata()
    material = BASE.PREV.material_audit()
    snapshot = scheduler_snapshot()
    git_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    result = {
        "schema": "PAPER_A_LP_ANISOTROPY_BALANCED_INITIAL_TRUTH_PREFLIGHT_V1",
        "timestamp_utc": now(),
        "status": "PASS",
        "canonical_head": git_head,
        "selection_sha256": sha_file(SELECTION),
        "initial_geometry_ids": INITIAL,
        "authorized_case_ids": [f"{gid}_{pol}" for gid in INITIAL for pol in ("x", "y")],
        "conditional_authorized": False,
        "prepared_case_count": len(setup),
        "all_pre_fsp_hashes_match": all(row["status"] == "PASS" for row in setup),
        "material_validity": material,
        "source_monitor": {"source_span_nm": [430.0, 470.0], "formal_window_nm": [435.0, 465.0], "spacing_nm": 1.0, "formal_points": 31, "anchor_nm": 450.0},
        "solver_policy": {"maximum_physics_jobs": MAX_PHYSICS_JOBS, "paper_a_max_active_fdtd": MAX_ACTIVE_PAPER_A_FDTD, "global_cap": 3, "mpi_processes": 12, "threads": 1, "entered_true_no_replay": True},
        "scheduler_snapshot": snapshot,
        "explicit_high_priority_registry_demand": registry_queue_demands(),
        "no_rcwa": True,
        "no_ml": True,
        "conditional_batch_not_ready": True,
    }
    if not result["all_pre_fsp_hashes_match"] or not material.get("pass") or snapshot.get("unknown_solver_jobs"):
        result["status"] = "HARD_GATE_PREFLIGHT"
    write_json(REPORT / "preflight.json", result)
    return result


def case_states() -> list[dict[str, Any]]:
    states = []
    for path in RUNTIME.glob("cases/*/state.json"):
        try:
            states.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    return states


def monitor_sample(previous_cpu: float | None) -> tuple[dict[str, Any], float | None]:
    states = case_states()
    snapshot = scheduler_snapshot()
    cpu_time = None
    resource = {"cpu_percent": None, "ram_percent": None, "io": None}
    try:
        import psutil
        process = psutil.Process(os.getpid())
        times = process.cpu_times()
        cpu_time = float(times.user + times.system)
        resource = {"cpu_percent": psutil.cpu_percent(interval=None), "ram_percent": psutil.virtual_memory().percent, "io": process.io_counters()._asdict()}
    except Exception:
        pass
    entered_unresolved = [s.get("case_id") for s in states if s.get("solver_entered") and s.get("status") in {"FAILED", "RUNNING", "RETURNED"}]
    anomalies = []
    if snapshot.get("unknown_solver_jobs"):
        anomalies.append("UNKNOWN_SOLVER_LINEAGE")
    if any(s.get("status") == "RUNNING" and not snapshot.get("active_fdtd_jobs") for s in states):
        anomalies.append("RUNNING_STATE_WITHOUT_LIVE_FDTD_LINEAGE")
    record = {
        "timestamp": now(),
        "task": TASK_ID,
        "stage": "BALANCED_INITIAL_TRUTH",
        "completed": sum(s.get("status") == "COMPLETED" for s in states),
        "total": MAX_PHYSICS_JOBS,
        "waiting": sum(s.get("status") == "WAITING" for s in states),
        "running": sum(s.get("status") == "RUNNING" for s in states),
        "returned": sum(s.get("status") == "RETURNED" for s in states),
        "accepted": sum(s.get("status") == "COMPLETED" for s in states),
        "current_cases": [{"case_id": s.get("case_id"), "status": s.get("status"), "attempt_id": s.get("attempt_id"), "solver_entered": s.get("solver_entered"), "solver_pid": s.get("solver_pid")} for s in states],
        "controller": {"pid": os.getpid(), "status": "RUNNING"},
        "cpu_time_delta_s": None if cpu_time is None or previous_cpu is None else cpu_time - previous_cpu,
        "queue": {"explicit_high_priority_registry_demand": registry_queue_demands()},
        "global_fdtd_slots": snapshot,
        "resource": resource,
        "license_status": "NO_EXPLICIT_LICENSE_HARD_GATE_OBSERVED",
        "entered_unresolved": entered_unresolved,
        "active_hard_gate": anomalies or None,
        "progress": None,
    }
    return record, cpu_time


def monitor_loop(stop: threading.Event) -> None:
    monitor = RUNTIME / "monitor"
    monitor.mkdir(parents=True, exist_ok=True)
    lock = monitor / "paper_a_lp_balanced_truth_monitor.lock"
    try:
        descriptor = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError("DUPLICATE_MONITOR_GUARD") from exc
    os.write(descriptor, canonical({"pid": os.getpid(), "created_utc": now(), "task": TASK_ID}))
    os.close(descriptor)
    previous_cpu = None
    try:
        while True:
            record, previous_cpu = monitor_sample(previous_cpu)
            append_jsonl(monitor / "paper_a_lp_balanced_truth_progress.jsonl", record)
            write_json(monitor / "paper_a_lp_balanced_truth_monitor_state.json", record)
            if stop.wait(MONITOR_INTERVAL_S):
                break
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


def full_jones_rows(geometry_id: str) -> list[dict[str, Any]]:
    checkpoints = {}
    for polarization in ("x", "y"):
        path = RUNTIME / "cases" / f"{geometry_id}_{polarization}" / "checkpoint.json"
        checkpoints[polarization] = {float(row["wavelength_nm"]): row for row in json.loads(path.read_text(encoding="utf-8"))["rows"]}
    rows = []
    for wavelength in GRID:
        xrow, yrow = checkpoints["x"][wavelength], checkpoints["y"][wavelength]
        txx = complex(xrow["weighted_Ex_real"], xrow["weighted_Ex_imag"])
        tyx = complex(xrow["weighted_Ey_real"], xrow["weighted_Ey_imag"])
        txy = complex(yrow["weighted_Ex_real"], yrow["weighted_Ex_imag"])
        tyy = complex(yrow["weighted_Ey_real"], yrow["weighted_Ey_imag"])
        matrix = np.array([[txx, txy], [tyx, tyy]], dtype=complex)
        stokes = BASE.stokes(matrix)
        stokes.pop("dominant_vector_real", None)
        stokes.pop("dominant_vector_imag", None)
        rows.append({
            "geometry_id": geometry_id,
            "wavelength_nm": wavelength,
            "diffraction_order_m": 0,
            "diffraction_order_n": 0,
            "J_xy_column_convention": "x-input then y-input",
            "txx_real": txx.real, "txx_imag": txx.imag,
            "txy_real": txy.real, "txy_imag": txy.imag,
            "tyx_real": tyx.real, "tyx_imag": tyx.imag,
            "tyy_real": tyy.real, "tyy_imag": tyy.imag,
            **stokes,
        })
    return rows


_base_postprocess_geometry = BASE.postprocess_geometry


def postprocess_geometry(geometry_id: str) -> dict[str, Any]:
    summary = _base_postprocess_geometry(geometry_id)
    path = REPORT / "full_jones_order_0_0_spectra.csv"
    rows = full_jones_rows(geometry_id)
    write_csv(path, upsert_geometry_rows(path, rows))
    summary["diffraction_order"] = [0, 0]
    summary["jones_basis"] = "J_xy; columns are independent x/y plane-wave inputs"
    summary["qualification"] = "axis-free linear Stokes/coherency; phase/K6 excluded"
    metric_path = REPORT / f"{geometry_id}_metrics.json"
    metrics = json.loads(metric_path.read_text(encoding="utf-8"))
    metrics["summary"] = summary
    metrics["order_resolved_full_jones_path"] = str(path)
    write_json(metric_path, metrics)
    return summary


BASE.postprocess_geometry = postprocess_geometry


def run_case(case_id: str) -> dict[str, Any]:
    return BASE.PREV.run_case(case_id)


def invoke_physics_validity_gate(case_id: str) -> dict[str, Any]:
    case_runtime = RUNTIME / "cases" / case_id
    provenance = json.loads((case_runtime / "attempt_provenance.json").read_text(encoding="utf-8"))
    if provenance.get("solver_entered") is not True:
        raise RuntimeError(f"PHYSICS_GATE_REQUIRES_ENTERED_CASE:{case_id}")
    output = case_runtime / "physics_validity_gate_v2.json"
    command = [
        sys.executable,
        str(ROOT / "paper_a_broadband/scripts/fdtd_physics_validity_gate_v2_instrumented.py"),
        "--case-id", case_id,
        "--post-fsp", str(Path(provenance["run_fsp_path"])),
        "--solver-log", str(case_runtime / "controller.log"),
        "--output", str(output),
    ]
    evidence_path = provenance.get("convergence_evidence_path")
    if evidence_path:
        command.extend(["--convergence-evidence", str(Path(evidence_path))])
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"PHYSICS_VALIDITY_GATE_EXECUTION_FAILED:{case_id}:{completed.stderr[-2000:]}")
    result = json.loads(output.read_text(encoding="utf-8"))
    if result.get("case_id") != case_id:
        raise RuntimeError(f"PHYSICS_VALIDITY_GATE_CASE_MISMATCH:{case_id}")
    state_path = case_runtime / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state.update({
        "physics_validity_gate": str(output),
        "physics_validity_status": result.get("status"),
        "physics_validity_root_cause": result.get("root_cause"),
        "updated_utc": now(),
    })
    write_json(state_path, state)
    return result


def run_wave(geometry_id: str) -> dict[str, Any]:
    results = []
    for polarization in ("x", "y"):
        case_id = f"{geometry_id}_{polarization}"
        log_path = RUNTIME / "cases" / case_id / "controller.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            process = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "run-case", "--case-id", case_id],
                stdout=handle,
                stderr=handle,
            )
            returncode = process.wait()
        state_path = RUNTIME / "cases" / case_id / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else None
        result = {"case_id": case_id, "returncode": returncode, "state": state}
        results.append(result)
        if returncode != 0 or not state or state.get("status") != "COMPLETED":
            return {"geometry_id": geometry_id, "status": "HARD_GATE_CASE_FAILURE", "failed_case": case_id, "cases": results}
        validity = invoke_physics_validity_gate(case_id)
        result["physics_validity"] = validity
        if validity.get("status") != "VALID_FOR_PHYSICS_TRUTH":
            return {
                "geometry_id": geometry_id,
                "status": "HARD_GATE_PHYSICS_VALIDITY",
                "failed_case": case_id,
                "cases": results,
                "physics_validity": validity,
            }
    return {"geometry_id": geometry_id, "status": "COMPLETED", "cases": results, "summary": postprocess_geometry(geometry_id)}

BASE.run_wave = run_wave


def midpoint_balanced(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    final = [row for row in summaries if row.get("final_pass")]
    promising = [row for row in summaries if row.get("promising")]
    directional = [row for row in summaries if row.get("MDC_weighted", {}).get("DoLP", 0.0) >= 0.40 or row.get("MDC_FWHM_psi_span_deg", 999.0) <= 45.0]
    continuation = bool(final or promising)
    result = {
        "schema": "PAPER_A_LP_ANISOTROPY_BALANCED_MIDPOINT_AUDIT_V1",
        "timestamp_utc": now(),
        "geometries_completed": len(summaries),
        "final_pass_count": len(final),
        "promising_count": len(promising),
        "directional_diagnostic_count": len(directional),
        "continue_to_BF05_BF08": continuation,
        "conditional_admission_rule": "final_pass_count > 0 or promising_count > 0; directional diagnostics alone do not authorize conditional truth",
        "status": "CONDITIONAL_BATCH_ELIGIBLE_PENDING_USER_AUTHORIZATION" if continuation else "CONDITIONAL_BATCH_NOT_ADMITTED_MIDPOINT_NOT_PROMISING",
        "summaries": summaries,
    }
    write_json(REPORT / "midpoint_physics_audit.json", result)
    return result


BASE.midpoint = midpoint_balanced


def finalize(status: str, waves: list[dict[str, Any]], midpoint: dict[str, Any] | None = None, reason: str | None = None) -> dict[str, Any]:
    summaries = [wave["summary"] for wave in waves if wave.get("summary")]
    ranked = sorted(summaries, key=lambda row: (bool(row.get("final_pass")), bool(row.get("promising")), row.get("MDC_weighted", {}).get("DoLP", -1), row.get("MDC_weighted", {}).get("P_LP_axisfree", -1), -row.get("MDC_FWHM_psi_span_deg", 999)), reverse=True)
    entered = sum(1 for gid in INITIAL for pol in ("x", "y") if (RUNTIME / "cases" / f"{gid}_{pol}" / "state.json").exists() and json.loads((RUNTIME / "cases" / f"{gid}_{pol}" / "state.json").read_text(encoding="utf-8")).get("solver_entered"))
    conditional_eligible = bool(midpoint and midpoint.get("continue_to_BF05_BF08"))
    decision = {
        "schema": "PAPER_A_LP_ANISOTROPY_BALANCED_INITIAL_TRUTH_DECISION_V1",
        "timestamp_utc": now(),
        "status": status,
        "reason": reason,
        "initial_geometries_completed": len(summaries),
        "solver_budget_max_cases": MAX_PHYSICS_JOBS,
        "solver_entered_cases": entered,
        "ranked_initial_geometry_ids": [row["geometry_id"] for row in ranked],
        "midpoint_physics_audit": midpoint,
        "conditional_batch_authorized": False,
        "conditional_batch_eligible": conditional_eligible,
        "next_authority": "USER_DECISION_REQUIRED_FOR_BF05_BF08" if conditional_eligible else "BF05_BF08_NOT_ADMITTED_MIDPOINT_NOT_PROMISING",
        "no_rcwa": True,
        "no_ml": True,
        "summaries": summaries,
        "scheduler_snapshot": scheduler_snapshot(),
    }
    terminal_name = "terminal_success.json" if status == "PAPER_A_LP_BALANCED_INITIAL_TRUTH_COMPLETE" else "terminal_failure.json"
    write_json(REPORT / terminal_name, decision)
    write_json(REPORT / "audit.json", decision)
    rows = []
    for item in ranked:
        rows.append({
            "geometry_id": item["geometry_id"],
            "MDC_weighted_DoLP": item["MDC_weighted"]["DoLP"],
            "MDC_weighted_P_LP_axisfree": item["MDC_weighted"]["P_LP_axisfree"],
            "MDC_FWHM_psi_span_deg": item["MDC_FWHM_psi_span_deg"],
            "MDC_FWHM_DoLP_worst": item["MDC_FWHM_DoLP_worst"],
            "formal_DoLP_worst": item["formal_DoLP_worst"],
            "formal_P_LP_axisfree_worst": item["formal_P_LP_axisfree_worst"],
            "final_pass": item["final_pass"],
            "promising": item["promising"],
        })
    write_csv(REPORT / "initial_candidate_comparison.csv", rows)
    report = [
        "# Paper A LP balanced initial truth v1",
        "",
        f"Status: `{status}`",
        "",
        "Current Native-M1; source/monitor 430-470 nm; formal axis-free full-Jones evaluation 435-465 nm at 1 nm; zero-order J_xy from independent x/y inputs.",
        f"Solver entered: {entered}/{MAX_PHYSICS_JOBS}. Conditional BF05-BF08 was not authorized or run.",
        "",
        "| geometry | weighted DoLP | weighted P_LP | FWHM psi span | FWHM DoLP worst | pass | promising |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for item in ranked:
        report.append(f"| {item['geometry_id']} | {item['MDC_weighted']['DoLP']:.6f} | {item['MDC_weighted']['P_LP_axisfree']:.6f} | {item['MDC_FWHM_psi_span_deg']:.3f} | {item['MDC_FWHM_DoLP_worst']:.6f} | {item['final_pass']} | {item['promising']} |")
    (REPORT / "final_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return decision


def zero_solver_closeout() -> dict[str, Any]:
    checkpoint_paths = [RUNTIME / "cases" / f"{geometry_id}_{polarization}" / "checkpoint.json" for geometry_id in INITIAL for polarization in ("x", "y")]
    if not all(path.exists() and json.loads(path.read_text(encoding="utf-8")).get("status") == "ACCEPTED" for path in checkpoint_paths):
        raise RuntimeError("HARD_GATE_ZERO_SOLVER_CLOSEOUT_CHECKPOINT_CHAIN")
    waves = []
    for geometry_id in INITIAL:
        waves.append({"geometry_id": geometry_id, "status": "COMPLETED", "summary": postprocess_geometry(geometry_id)})
    midpoint = midpoint_balanced([wave["summary"] for wave in waves])
    return finalize("PAPER_A_LP_BALANCED_INITIAL_TRUTH_COMPLETE", waves, midpoint=midpoint, reason="ZERO_SOLVER_MIDPOINT_AUTHORITY_CORRECTION")


def run_initial() -> dict[str, Any]:
    REPORT.mkdir(parents=True, exist_ok=True)
    pre = preflight()
    if pre["status"] != "PASS":
        return finalize("HARD_GATE_PREFLIGHT", [], reason=pre["status"])
    controller = {"schema": "PAPER_A_LP_BALANCED_CONTROLLER_STATE_V1", "task": TASK_ID, "pid": os.getpid(), "status": "RUNNING", "timestamp_utc": now()}
    write_json(RUNTIME / "controller_state.json", controller)
    stop = threading.Event()
    monitor = threading.Thread(target=monitor_loop, args=(stop,), name="balanced-truth-monitor", daemon=True)
    monitor.start()
    waves: list[dict[str, Any]] = []
    try:
        for geometry_id in INITIAL:
            boundary = boundary_check()
            if not boundary["allow_next_wave"]:
                controller.update({"status": "LOW_PRIORITY_BACKGROUND_WAIT", "timestamp_utc": now(), "next_geometry_id": geometry_id})
                write_json(RUNTIME / "controller_state.json", controller)
                return finalize("LOW_PRIORITY_BACKGROUND_WAIT", waves, reason="CASE_BOUNDARY_YIELD")
            append_jsonl(REPORT / "visible_events.jsonl", {"timestamp_utc": now(), "event": "WAVE_ENTERING", "geometry_id": geometry_id, "case_ids": [f"{geometry_id}_x", f"{geometry_id}_y"]})
            wave = BASE.run_wave(geometry_id)
            waves.append(wave)
            if wave.get("status") != "COMPLETED":
                controller.update({"status": "HARD_GATE_CASE_FAILURE", "timestamp_utc": now(), "geometry_id": geometry_id})
                write_json(RUNTIME / "controller_state.json", controller)
                return finalize("HARD_GATE_CASE_FAILURE", waves, reason=geometry_id)
            append_jsonl(REPORT / "visible_events.jsonl", {"timestamp_utc": now(), "event": "WAVE_COMPLETED", "geometry_id": geometry_id})
        summaries = [wave["summary"] for wave in waves]
        midpoint = BASE.midpoint(summaries)
        controller.update({"status": "COMPLETED", "timestamp_utc": now(), "solver_entered_cases": MAX_PHYSICS_JOBS})
        write_json(RUNTIME / "controller_state.json", controller)
        return finalize("PAPER_A_LP_BALANCED_INITIAL_TRUTH_COMPLETE", waves, midpoint=midpoint, reason="INITIAL_BF01_BF04_COMPLETE")
    finally:
        stop.set()
        monitor.join(timeout=5)


def status() -> dict[str, Any]:
    controller_path = RUNTIME / "controller_state.json"
    terminal_success = REPORT / "terminal_success.json"
    terminal_failure = REPORT / "terminal_failure.json"
    return {
        "controller": json.loads(controller_path.read_text(encoding="utf-8")) if controller_path.exists() else None,
        "terminal_success": json.loads(terminal_success.read_text(encoding="utf-8")) if terminal_success.exists() else None,
        "terminal_failure": json.loads(terminal_failure.read_text(encoding="utf-8")) if terminal_failure.exists() else None,
        "states": case_states(),
        "scheduler": scheduler_snapshot(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["preflight", "run-case", "run-initial", "zero-solver-closeout", "status"])
    parser.add_argument("--case-id")
    args = parser.parse_args()
    if args.mode == "preflight":
        output = preflight()
    elif args.mode == "run-case":
        if not args.case_id:
            raise RuntimeError("CASE_ID_REQUIRED")
        output = run_case(args.case_id)
    elif args.mode == "run-initial":
        output = run_initial()
    elif args.mode == "zero-solver-closeout":
        output = zero_solver_closeout()
    else:
        output = status()
    print(json.dumps(output, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
