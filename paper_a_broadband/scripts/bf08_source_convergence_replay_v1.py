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
import sys
import threading
import traceback
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
REPORT = ROOT / "paper_a_broadband/reports/lp_bf08_source_convergence_replay_v1"
RUNTIME = ROOT / "paper_a_broadband/runtime/bf08_source_convergence_replay_v1"
AUTH = ROOT / "paper_a_broadband/authority/paper_a_lp_bf08_source_convergence_replay_contract_v1.json"
BASE_PATH = ROOT / "paper_a_broadband/scripts/lp_new_geometry_search_runner_v1.py"
ORIGINAL_RUNTIME = ROOT / "paper_a_broadband/runtime/search_anisotropy_balanced_truth_v1/cases"
SLOT_REGISTRY = Path(r"D:/project/apcd_global_fdtd_slot_registry_v1.json")
SCHEDULER_PATH = ROOT / "paper_a_broadband/templates/lp_fulljones/apcd_global_fdtd_slot_v1.py"
LEGACY_EXTRACTOR = ROOT / "scripts/lp_legacy_h500_sixbin_formal_replay_450_v1.py"
BRANCH = "work/paper-a-lp-cp-broadband-v1"
TASK_ID = "PAPER_A_LP_BF08_SOURCE_CONVERGENCE_REPLAY_V1"
CASES = ("BF08_x", "BF08_y")
FORMAL_GRID = np.arange(435.0, 466.0, 1.0)
NATIVE_GRID = np.arange(430.0, 470.0001, 0.5)
C0 = 299792458.0
PROCESSES = 4
THREADS = 1

sys.path.insert(0, r"N:/Program Files/ANSYS Inc/v251/Lumerical/api/python")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"MODULE_LOAD_FAILURE:{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = load_module(BASE_PATH, "bf08_replay_base")
LEGACY = load_module(LEGACY_EXTRACTOR, "bf08_replay_legacy")


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, default=str) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_contract() -> dict[str, Any]:
    contract = json.loads(AUTH.read_text(encoding="utf-8"))
    if contract.get("physical_jobs_max") != 2 or contract.get("cases") != list(CASES):
        raise RuntimeError("HARD_GATE_REPLAY_AUTHORITY_SCOPE")
    return contract


def case_dir(case_id: str) -> Path:
    return RUNTIME / "cases" / case_id


def source_case_dir(case_id: str) -> Path:
    return ORIGINAL_RUNTIME / case_id


def state_path(case_id: str) -> Path:
    return case_dir(case_id) / "state.json"


def update_state(case_id: str, **updates: Any) -> dict[str, Any]:
    path = state_path(case_id)
    state: dict[str, Any] = {}
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
    state.update(updates)
    state["updated_utc"] = now()
    write_json(path, state)
    return state


def getnamed(fdtd, name: str, prop: str) -> Any:
    value = fdtd.getnamed(name, prop)
    return value.item() if hasattr(value, "item") else value


def source_power_gate(fdtd) -> dict[str, Any]:
    wavelengths_nm = FORMAL_GRID
    frequencies = C0 / (wavelengths_nm * 1e-9)
    powers = np.asarray(fdtd.sourcepower(frequencies)).reshape(-1).astype(float)
    ratio = float(powers.min() / powers.max()) if powers.max() > 0 else 0.0
    return {
        "wavelengths_nm": wavelengths_nm.tolist(),
        "sourcepower": powers.tolist(),
        "minimum": float(powers.min()),
        "maximum": float(powers.max()),
        "min_over_max": ratio,
        "pass": bool(np.all(powers > 0) and ratio >= 0.99),
    }


def immutable_source_power_gate(path: Path) -> dict[str, Any]:
    import lumapi

    with lumapi.FDTD(hide=True) as fdtd:
        fdtd.load(str(path))
        return source_power_gate(fdtd)


def mesh_boundary_readback(fdtd) -> dict[str, Any]:
    return {
        "mesh_accuracy": float(getnamed(fdtd, "FDTD", "mesh accuracy")),
        "x_min_bc": str(getnamed(fdtd, "FDTD", "x min bc")),
        "x_max_bc": str(getnamed(fdtd, "FDTD", "x max bc")),
        "y_min_bc": str(getnamed(fdtd, "FDTD", "y min bc")),
        "y_max_bc": str(getnamed(fdtd, "FDTD", "y max bc")),
        "z_min_bc": str(getnamed(fdtd, "FDTD", "z min bc")),
        "z_max_bc": str(getnamed(fdtd, "FDTD", "z max bc")),
    }


def readback_gate(fdtd, case_id: str, expected_mesh_boundary: dict[str, Any] | None = None, source_content: dict[str, Any] | None = None) -> dict[str, Any]:
    pol = case_id.rsplit("_", 1)[1]
    mesh_boundary = mesh_boundary_readback(fdtd)
    checks = {
        "source_start_nm": float(getnamed(fdtd, "source", "wavelength start")) * 1e9,
        "source_stop_nm": float(getnamed(fdtd, "source", "wavelength stop")) * 1e9,
        "source_polarization_angle_deg": float(getnamed(fdtd, "source", "polarization angle")),
        "T_frequency_points": float(getnamed(fdtd, "T", "frequency points")),
        "field_frequency_points": float(getnamed(fdtd, "field_monitor", "frequency points")),
        "simulation_time_ps": float(getnamed(fdtd, "FDTD", "simulation time")) * 1e12,
        "auto_shutoff_min": float(getnamed(fdtd, "FDTD", "auto shutoff min")),
        "materials": [str(getnamed(fdtd, "pillar_1", "material")), str(getnamed(fdtd, "pillar_2", "material"))],
        "mesh_boundary": mesh_boundary,
        "source_content": source_content or {"pass": False, "reason": "IMMUTABLE_SOURCE_AUDIT_MISSING"},
    }
    expected = {
        "source_start_nm": 430.0,
        "source_stop_nm": 470.0,
        "source_polarization_angle_deg": 0.0 if pol == "x" else 90.0,
        "T_frequency_points": 81.0,
        "field_frequency_points": 81.0,
        "simulation_time_ps": 5.0,
        "auto_shutoff_min": 1e-7,
        "materials": ["APCD_TIO2_NATIVE_M1", "APCD_TIO2_NATIVE_M1"],
    }
    checks_pass = all(
        checks[key] == value if isinstance(value, list) else abs(float(checks[key]) - float(value)) < 1e-9
        for key, value in expected.items()
    )
    mesh_pass = expected_mesh_boundary is None or mesh_boundary == expected_mesh_boundary
    return {
        "pass": bool(checks_pass and mesh_pass and checks["source_content"]["pass"]),
        "checks": checks,
        "expected": expected,
        "mesh_boundary_unchanged": mesh_pass,
        "formal_grid_nm": FORMAL_GRID.tolist(),
        "native_grid_nm": NATIVE_GRID.tolist(),
        "normalization_renormalized": False,
    }


def prepare_case(case_id: str) -> dict[str, Any]:
    import lumapi

    load_contract()
    current_pre = source_case_dir(case_id) / f"{case_id}_pre.fsp"
    original_run = source_case_dir(case_id) / f"{case_id}_run.fsp"
    original_attempt = source_case_dir(case_id) / "attempt_provenance.json"
    original_setup = source_case_dir(case_id) / "setup_only.json"
    if not original_run.exists() or not original_attempt.exists() or not original_setup.exists():
        raise RuntimeError(f"HARD_GATE_IMMUTABLE_PARENT_MISSING:{case_id}")
    original_meta = json.loads(original_setup.read_text(encoding="utf-8"))
    attempt_meta = json.loads(original_attempt.read_text(encoding="utf-8"))
    if sha_file(original_run) != attempt_meta.get("run_fsp_sha256"):
        raise RuntimeError(f"HARD_GATE_RETURNED_RUN_FSP_PROVENANCE:{case_id}")
    out_dir = case_dir(case_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    replay_pre = out_dir / f"{case_id}_attempt_002_replay_pre.fsp"
    shutil.copy2(original_run, replay_pre)
    source_content = immutable_source_power_gate(original_run)
    with lumapi.FDTD(hide=True) as fdtd:
        fdtd.load(str(replay_pre))
        fdtd.switchtolayout()
        fdtd.setnamed("FDTD", "simulation time", 5e-12)
        fdtd.setnamed("FDTD", "auto shutoff min", 1e-7)
        fdtd.setnamed("source", "wavelength start", 430e-9)
        fdtd.setnamed("source", "wavelength stop", 470e-9)
        for monitor in ("T", "field_monitor"):
            fdtd.setnamed(monitor, "use source limits", True)
            fdtd.setnamed(monitor, "use wavelength spacing", True)
            fdtd.setnamed(monitor, "frequency points", 81)
        fdtd.setglobalmonitor("use source limits", True)
        fdtd.setglobalmonitor("use wavelength spacing", True)
        fdtd.setglobalmonitor("frequency points", 81)
        fdtd.save(str(replay_pre))
    with lumapi.FDTD(hide=True) as fdtd:
        fdtd.load(str(replay_pre))
        expected_mesh = {
            "mesh_accuracy": float(original_meta["readback"].get("mesh_accuracy", 2.0)),
            "x_min_bc": "Periodic", "x_max_bc": "Periodic",
            "y_min_bc": "Periodic", "y_max_bc": "Periodic",
            "z_min_bc": "PML", "z_max_bc": "PML",
        }
        gate = readback_gate(fdtd, case_id, expected_mesh, source_content)
    result = {
        "schema": "PAPER_A_LP_BF08_SOURCE_CONVERGENCE_SETUP_ONLY_V1",
        "case_id": case_id,
        "status": "PASS" if gate["pass"] else "HARD_GATE_SETUP_ONLY",
        "solver_run_called": False,
        "solver_entered": False,
        "immutable_returned_run_fsp_path": str(original_run),
        "immutable_returned_run_fsp_sha256": sha_file(original_run),
        "attempt_recorded_returned_run_fsp_sha256": attempt_meta.get("run_fsp_sha256"),
        "returned_run_fsp_hash_match": True,
        "current_pre_fsp_path": str(current_pre),
        "current_pre_fsp_sha256": sha_file(current_pre) if current_pre.exists() else None,
        "attempt_recorded_pre_fsp_sha256": attempt_meta.get("pre_fsp_sha256"),
        "current_pre_fsp_hash_matches_attempt": bool(current_pre.exists() and sha_file(current_pre) == attempt_meta.get("pre_fsp_sha256")),
        "original_setup_sha256": sha_file(original_setup),
        "replay_pre_fsp_path": str(replay_pre),
        "replay_pre_fsp_sha256": sha_file(replay_pre),
        "geometry_hash_sha256": attempt_meta.get("geometry_hash_sha256", original_meta.get("geometry_hash")),
        "gate": gate,
        "timestamp_utc": now(),
    }
    write_json(out_dir / "setup_only.json", result)
    return result


def preflight() -> dict[str, Any]:
    contract = load_contract()
    setups = [prepare_case(case_id) for case_id in CASES]
    result = {
        "schema": "PAPER_A_LP_BF08_SOURCE_CONVERGENCE_PREFLIGHT_V1",
        "status": "PASS" if all(item["status"] == "PASS" for item in setups) else "HARD_GATE_SETUP_ONLY",
        "solver_run_called": False,
        "solver_entered": 0,
        "contract_sha256": sha_file(AUTH),
        "contract": contract,
        "setups": setups,
        "scheduler_snapshot": BASE.scheduler_snapshot(),
        "timestamp_utc": now(),
    }
    write_json(REPORT / "preflight.json", result)
    return result


def extract_rows(fdtd) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    transmission = np.real(np.asarray(fdtd.transmission("T")).reshape(-1))
    if len(transmission) != len(NATIVE_GRID):
        raise RuntimeError(f"HARD_GATE_NATIVE_MONITOR_COUNT:{len(transmission)}")
    x, y, ex, ey, grid = LEGACY.base.b.f1.grid_plane(fdtd, float(transmission[0]))
    ex, ey = np.asarray(ex).squeeze(), np.asarray(ey).squeeze()
    if ex.ndim == 2:
        ex, ey = ex[:, :, None], ey[:, :, None]
    if ex.shape[2] != len(NATIVE_GRID):
        raise RuntimeError(f"HARD_GATE_NATIVE_FIELD_COUNT:{ex.shape}")
    rows = []
    negative = []
    for index, wavelength_nm in enumerate(NATIVE_GRID):
        if not any(abs(wavelength_nm - formal) < 1e-9 for formal in FORMAL_GRID):
            continue
        transmission_value = float(transmission[index])
        if transmission_value < 0:
            negative.append({"wavelength_nm": float(wavelength_nm), "T": transmission_value})
            continue
        raw_x = LEGACY.base.b.f1.periodic_weighted(x, y, ex[:, :, index], grid["x_periodic_duplicate_endpoint"], grid["y_periodic_duplicate_endpoint"])
        raw_y = LEGACY.base.b.f1.periodic_weighted(x, y, ey[:, :, index], grid["x_periodic_duplicate_endpoint"], grid["y_periodic_duplicate_endpoint"])
        normalized_x, normalized_y = LEGACY.base.b.f1.normalize_pair(raw_x, raw_y, transmission_value)
        rows.append({
            "wavelength_nm": float(wavelength_nm),
            "raw_weighted_Ex_real": float(raw_x.real), "raw_weighted_Ex_imag": float(raw_x.imag),
            "raw_weighted_Ey_real": float(raw_y.real), "raw_weighted_Ey_imag": float(raw_y.imag),
            "weighted_Ex_real": float(normalized_x.real), "weighted_Ex_imag": float(normalized_x.imag),
            "weighted_Ey_real": float(normalized_y.real), "weighted_Ey_imag": float(normalized_y.imag),
            "source_T": transmission_value,
            "selected_power": float(abs(normalized_x) ** 2 + abs(normalized_y) ** 2),
            "normalization_renormalized": False,
        })
    if negative:
        raise RuntimeError("NEGATIVE_FORMAL_TRANSMISSION:" + json.dumps(negative, separators=(",", ":")))
    if [row["wavelength_nm"] for row in rows] != FORMAL_GRID.tolist():
        raise RuntimeError("HARD_GATE_FORMAL_GRID_EXACT_SELECTION")
    return rows, {"formal_negative_transmission": [], "native_points": len(NATIVE_GRID)}


def run_case(case_id: str) -> dict[str, Any]:
    import lumapi

    setup_path = case_dir(case_id) / "setup_only.json"
    if not setup_path.exists():
        raise RuntimeError(f"HARD_GATE_SETUP_MISSING:{case_id}")
    setup = json.loads(setup_path.read_text(encoding="utf-8"))
    if setup.get("status") != "PASS":
        raise RuntimeError(f"HARD_GATE_SETUP_STATUS:{case_id}")
    pre = Path(setup["replay_pre_fsp_path"])
    attempt_path = case_dir(case_id) / "attempt_002_authorized_replay_provenance.json"
    if attempt_path.exists():
        previous = json.loads(attempt_path.read_text(encoding="utf-8"))
        if previous.get("solver_entered") is True:
            raise RuntimeError(f"HARD_GATE_ENTERED_REPLAY_ATTEMPT_EXISTS:{case_id}")
        write_json(case_dir(case_id) / "attempt_002_preentry_failure.json", previous)
    record = {
        "schema": "PAPER_A_LP_BF08_AUTHORIZED_REPLAY_ATTEMPT_V1",
        "case_id": case_id,
        "attempt_id": f"{case_id}_attempt_002",
        "solver_replay": True,
        "replay_authorization": "USER_EXPLICIT_BF08_X_Y_ONE_TIME_TWO_JOB_REPLAY_2026_08_23",
        "solver_entered": False,
        "geometry_hash_sha256": setup["geometry_hash_sha256"],
        "immutable_returned_run_fsp_sha256": setup["immutable_returned_run_fsp_sha256"],
        "replay_pre_fsp_sha256": sha_file(pre),
        "physical_contract_sha256": sha_file(AUTH),
        "mpi_processes": PROCESSES,
        "threads": THREADS,
        "started_utc": now(),
    }
    write_json(attempt_path, record)
    lease = None
    fdtd = None
    try:
        scheduler_module = load_module(SCHEDULER_PATH, f"bf08_replay_scheduler_{case_id}")
        scheduler = scheduler_module.GlobalSlotScheduler(SLOT_REGISTRY)
        update_state(case_id, status="WAITING", solver_entered=False)
        lease = scheduler.acquire_wait(
            branch=BRANCH, worktree=str(ROOT), task_id=TASK_ID, case_uid=case_id,
            pid=os.getpid(), metadata={"task_class": "PAPER_A_BF08_AUTHORIZED_REPLAY", "attempt_id": record["attempt_id"]},
            timeout_s=3600.0, poll_s=30.0,
        )
        record.update({"slot_id": lease.slot_id, "slot_acquired": True, "admission_snapshot": lease.record.get("admission_snapshot")})
        write_json(attempt_path, record)
        fdtd = lumapi.FDTD(hide=True)
        fdtd.load(str(pre))
        gate = readback_gate(fdtd, case_id, setup["gate"]["checks"]["mesh_boundary"], setup["gate"]["checks"]["source_content"])
        record["configuration_gate"] = gate
        if not gate["pass"]:
            record["status"] = "HARD_GATE_PRE_ENTRY_CONFIGURATION"
            update_state(case_id, status=record["status"], solver_entered=False, configuration_gate=gate)
            return record
        fdtd.setresource("FDTD", 1, "processes", str(PROCESSES))
        entered = now()
        lease.mark_solver_entered(entered)
        record.update({"solver_entered": True, "entered_utc": entered, "status": "ENTERED"})
        update_state(case_id, status="RUNNING", solver_entered=True, entered_utc=entered, slot_id=lease.slot_id, configuration_gate=gate)
        write_json(attempt_path, record)
        fdtd.run()
        returned = now()
        post = case_dir(case_id) / f"{case_id}_attempt_002_replay_run.fsp"
        fdtd.save(str(post))
        record.update({"status": "RETURNED", "solver_returned_utc": returned, "run_fsp_path": str(post), "run_fsp_sha256": sha_file(post)})
        lease.release("SOLVER_RETURNED", returned)
        lease = None
        update_state(case_id, status="RETURNED", solver_entered=True, run_fsp_sha256=record["run_fsp_sha256"])
        rows, diagnostics = extract_rows(fdtd)
        checkpoint = {
            "schema": "PAPER_A_LP_BF08_SOURCE_CONVERGENCE_REPLAY_CHECKPOINT_V1",
            "status": "ACCEPTED",
            "case_id": case_id,
            "solver_entered": True,
            "solver_replay": True,
            "rows": rows,
            "formal_grid_nm": FORMAL_GRID.tolist(),
            "configuration_gate": gate,
            "extraction_diagnostics": diagnostics,
        }
        checkpoint_path = case_dir(case_id) / "checkpoint.json"
        write_json(checkpoint_path, checkpoint)
        record.update({"status": "ACCEPTED", "checkpoint_path": str(checkpoint_path), "checkpoint_sha256": sha_file(checkpoint_path), "row_count": len(rows)})
        update_state(case_id, status="COMPLETED", solver_entered=True, checkpoint_sha256=record["checkpoint_sha256"])
        return record
    except Exception as exc:
        record.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()})
        update_state(case_id, status="FAILED", solver_entered=bool(record.get("solver_entered")), error=record["error"])
        return record
    finally:
        if lease is not None:
            try:
                lease.release("FAILED_ENTERED" if record.get("solver_entered") else "FAILED_PRE_ENTRY")
            except Exception as exc:
                record["slot_release_error"] = str(exc)
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass
        write_json(attempt_path, record)


def stokes(jones: np.ndarray) -> dict[str, float]:
    coherency = 0.5 * jones @ jones.conj().T
    s0 = float(np.trace(coherency).real)
    s1 = float((coherency[0, 0] - coherency[1, 1]).real)
    s2 = float(2.0 * coherency[0, 1].real)
    s3 = float(-2.0 * coherency[0, 1].imag)
    dolp = math.sqrt(max(0.0, s1 * s1 + s2 * s2)) / s0 if s0 > 0 else float("nan")
    psi = math.degrees(0.5 * math.atan2(s2, s1)) % 180.0
    return {"S0": s0, "S1": s1, "S2": s2, "S3": s3, "DoLP": dolp, "psi_deg": psi,
            "useful_lp_power": 0.5 * math.sqrt(max(0.0, s1 * s1 + s2 * s2)), "total_power": 0.5 * s0}


def postprocess(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not all(record.get("status") == "ACCEPTED" for record in records):
        return {"status": "HARD_GATE_REPLAY_CASE_FAILURE"}
    checkpoints = {
        case_id: json.loads((case_dir(case_id) / "checkpoint.json").read_text(encoding="utf-8"))["rows"]
        for case_id in CASES
    }
    x_rows = {row["wavelength_nm"]: row for row in checkpoints["BF08_x"]}
    y_rows = {row["wavelength_nm"]: row for row in checkpoints["BF08_y"]}
    spectrum = []
    for wavelength_nm in FORMAL_GRID:
        x = x_rows[float(wavelength_nm)]
        y = y_rows[float(wavelength_nm)]
        jones = np.asarray([
            [complex(x["weighted_Ex_real"], x["weighted_Ex_imag"]), complex(y["weighted_Ex_real"], y["weighted_Ex_imag"])],
            [complex(x["weighted_Ey_real"], x["weighted_Ey_imag"]), complex(y["weighted_Ey_real"], y["weighted_Ey_imag"])],
        ])
        row = {"wavelength_nm": float(wavelength_nm), "Jxx": jones[0, 0], "Jxy": jones[0, 1], "Jyx": jones[1, 0], "Jyy": jones[1, 1]}
        row.update(stokes(jones))
        spectrum.append(row)
    output_rows = []
    for row in spectrum:
        flattened = {key: value for key, value in row.items() if key not in ("Jxx", "Jxy", "Jyx", "Jyy")}
        for key in ("Jxx", "Jxy", "Jyx", "Jyy"):
            flattened[f"{key}_real"] = float(row[key].real)
            flattened[f"{key}_imag"] = float(row[key].imag)
        output_rows.append(flattened)
    write_csv(REPORT / "bf08_full_jones_order_0_0_spectra.csv", output_rows)
    at_450 = next(row for row in spectrum if row["wavelength_nm"] == 450.0)
    summary = {
        "status": "PASS_REPLAY_VALID_FORMAL_SPECTRA",
        "formal_points": len(spectrum),
        "formal_DoLP_mean": float(np.mean([row["DoLP"] for row in spectrum])),
        "formal_DoLP_worst": float(np.min([row["DoLP"] for row in spectrum])),
        "formal_useful_lp_power_mean": float(np.mean([row["useful_lp_power"] for row in spectrum])),
        "formal_useful_lp_power_worst": float(np.min([row["useful_lp_power"] for row in spectrum])),
        "anchor_450_nm": {key: value for key, value in at_450.items() if key not in ("Jxx", "Jxy", "Jyx", "Jyy")},
        "qualification": "axis-free Stokes/coherency from independent x/y order-(0,0) Jones columns; phase/K6 excluded",
    }
    write_json(REPORT / "bf08_replay_metrics.json", summary)
    return summary


def monitor(stop: threading.Event) -> None:
    lock = RUNTIME / "monitor/bf08_replay_monitor.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    if lock.exists():
        raise RuntimeError("HARD_GATE_DUPLICATE_MONITOR")
    lock.write_text(json.dumps({"pid": os.getpid(), "started_utc": now()}), encoding="utf-8")
    try:
        while not stop.wait(600.0):
            states = []
            for case_id in CASES:
                path = state_path(case_id)
                if path.exists():
                    states.append(json.loads(path.read_text(encoding="utf-8")))
            append_jsonl(RUNTIME / "monitor/bf08_replay_progress.jsonl", {"timestamp_utc": now(), "task_id": TASK_ID, "states": states, "scheduler": BASE.scheduler_snapshot()})
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


def run_replay() -> dict[str, Any]:
    pre = preflight()
    if pre["status"] != "PASS":
        final = {"status": "HARD_GATE_PRE_ENTRY", "preflight": pre, "solver_entered": 0}
        write_json(REPORT / "terminal_failure.json", final)
        return final
    prior_terminal = REPORT / "terminal_failure.json"
    if prior_terminal.exists():
        prior = json.loads(prior_terminal.read_text(encoding="utf-8"))
        if prior.get("solver_accounting", {}).get("entered") != 0:
            raise RuntimeError("HARD_GATE_PRIOR_ENTERED_REPLAY_TERMINAL")
        write_json(REPORT / "terminal_failure_preentry_controller.json", prior)
        prior_terminal.unlink()
    stop = threading.Event()
    worker = threading.Thread(target=monitor, args=(stop,), daemon=True)
    worker.start()
    try:
        records = [run_case(case_id) for case_id in CASES]
        result = postprocess(records)
        final = {"schema": "PAPER_A_LP_BF08_SOURCE_CONVERGENCE_REPLAY_TERMINAL_V1", "timestamp_utc": now(), "records": records, "analysis": result,
                 "solver_accounting": {"authorized": 2, "entered": sum(bool(r.get("solver_entered")) for r in records), "accepted": sum(r.get("status") == "ACCEPTED" for r in records), "rcwa": 0, "ml": 0},
                 "scheduler_final": BASE.scheduler_snapshot()}
        write_json(REPORT / ("terminal_success.json" if result.get("status") == "PASS_REPLAY_VALID_FORMAL_SPECTRA" else "terminal_failure.json"), final)
        return final
    finally:
        stop.set()
        worker.join(timeout=2.0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "run"))
    args = parser.parse_args()
    result = preflight() if args.mode == "preflight" else run_replay()
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0 if result.get("status") not in ("HARD_GATE_PRE_ENTRY", "HARD_GATE_REPLAY_CASE_FAILURE") else 1


if __name__ == "__main__":
    raise SystemExit(main())
