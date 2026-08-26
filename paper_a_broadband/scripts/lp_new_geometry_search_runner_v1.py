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
import traceback
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
DOE_PATH = ROOT / "paper_a_broadband/configs/initial_doe_v1.json"
REPORT = ROOT / "paper_a_broadband/reports/lp_new_geometry_search_v1"
RUNTIME = ROOT / "paper_a_broadband/runtime/search_v1"
PARENT_FSP = ROOT / "paper_a_broadband/runtime/reusable_fsp/lp/P1_LP_H1C1B_V2_009_Px_attempt_006_pre.fsp"
SLOT_REGISTRY = Path(r"D:/project/apcd_global_fdtd_slot_registry_v1.json")
SCHEDULER_PATH = ROOT / "paper_a_broadband/templates/lp_fulljones/apcd_global_fdtd_slot_v1.py"
LEGACY_EXTRACTOR = ROOT / "scripts/lp_legacy_h500_sixbin_formal_replay_450_v1.py"
BRANCH = "work/paper-a-lp-cp-broadband-v1"
WORKTREE = str(ROOT)
TASK_ID = "PAPER_A_BROADBAND_LP_NEW_GEOMETRY_SEARCH_V1"
GRID = [435.0 + i for i in range(31)]
NATIVE_GRID = [430.0 + i for i in range(41)]
SOURCE_START = 430.0
SOURCE_STOP = 470.0
MDC_FWHM = (438.409, 457.191)
MATERIAL = "APCD_TIO2_NATIVE_M1"
PROCESSES = 4
THREADS = 1

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, r"N:/Program Files/ANSYS Inc/v251/Lumerical/api/python")


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
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(value, ensure_ascii=False, default=str) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields or ["status"], extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_doe() -> dict[str, Any]:
    data = json.loads(DOE_PATH.read_text(encoding="utf-8"))
    if data.get("schema") != "PAPER_A_BROADBAND_LP_INITIAL_DOE_V1":
        raise RuntimeError("HARD_GATE_DOE_SCHEMA")
    if len(data.get("geometries", [])) != 6:
        raise RuntimeError("HARD_GATE_INITIAL_DOE_COUNT")
    if data.get("solver_calls") != 0:
        raise RuntimeError("HARD_GATE_DOE_SOLVER_CONTAMINATION")
    return data


def case_record(g: dict[str, Any], pol: str) -> dict[str, Any]:
    return next(x for x in g["cases"] if x["polarization"] == pol)


def case_dir(case_id: str) -> Path:
    return RUNTIME / "cases" / case_id


def case_state(case_id: str) -> Path:
    return case_dir(case_id) / "state.json"


def setnamed(f, obj: str, key: str, value: Any) -> None:
    f.setnamed(obj, key, value)


def safe_get(f, obj: str, key: str) -> Any:
    try:
        return f.getnamed(obj, key)
    except Exception as exc:
        return f"UNAVAILABLE:{type(exc).__name__}:{exc}"


def make_pre_fsp(g: dict[str, Any], pol: str) -> dict[str, Any]:
    import lumapi

    cid = f"{g['geometry_id']}_{pol}"
    out_dir = case_dir(cid)
    out_dir.mkdir(parents=True, exist_ok=True)
    pre = out_dir / f"{cid}_pre.fsp"
    f = lumapi.FDTD(hide=True)
    try:
        f.load(str(PARENT_FSP))
        f.switchtolayout()
        nm = 1e-9
        h = float(g["height_nm"])
        for obj, x, y, length, width, rotation in [
            ("pillar_1", g["j1_center_x_nm"], g["j1_center_y_nm"], g["j1_length_nm"], g["j1_width_nm"], g["j1_rotation_deg"]),
            ("pillar_2", g["j2_center_x_nm"], g["j2_center_y_nm"], g["j2_length_nm"], g["j2_width_nm"], g["j2_rotation_deg"]),
        ]:
            setnamed(f, obj, "x", float(x) * nm)
            setnamed(f, obj, "y", float(y) * nm)
            setnamed(f, obj, "x span", float(length) * nm)
            setnamed(f, obj, "y span", float(width) * nm)
            setnamed(f, obj, "z", h * nm / 2.0)
            setnamed(f, obj, "z span", h * nm)
            setnamed(f, obj, "rotation 1", float(rotation))
            setnamed(f, obj, "material", MATERIAL)
        setnamed(f, "source", "polarization angle", 0.0 if pol == "x" else 90.0)
        setnamed(f, "source", "wavelength start", SOURCE_START * nm)
        setnamed(f, "source", "wavelength stop", SOURCE_STOP * nm)
        for name in ("T", "field_monitor"):
            setnamed(f, name, "use source limits", True)
            setnamed(f, name, "use wavelength spacing", True)
            setnamed(f, name, "frequency points", 41)
        f.setglobalmonitor("use source limits", True)
        f.setglobalmonitor("use wavelength spacing", True)
        f.setglobalmonitor("frequency points", 41)
        f.save(str(pre))
    finally:
        try:
            f.close()
        except Exception:
            pass
    return {"path": str(pre), "sha256": sha_file(pre), "parent_fsp": str(PARENT_FSP), "parent_sha256": sha_file(PARENT_FSP)}


def readback_gate(g, pol: str, f) -> dict[str, Any]:
    mats = [str(safe_get(f, "pillar_1", "material")), str(safe_get(f, "pillar_2", "material"))]
    checks = {
        "source_start_nm": float(safe_get(f, "source", "wavelength start")) * 1e9,
        "source_stop_nm": float(safe_get(f, "source", "wavelength stop")) * 1e9,
        "source_polarization_angle_deg": float(safe_get(f, "source", "polarization angle")),
        "T_frequency_points": float(safe_get(f, "T", "frequency points")),
        "field_frequency_points": float(safe_get(f, "field_monitor", "frequency points")),
        "monitor_z_nm": float(safe_get(f, "field_monitor", "z")) * 1e9,
        "materials": mats,
        "j1_rotation_deg": float(safe_get(f, "pillar_1", "rotation 1")),
        "j2_rotation_deg": float(safe_get(f, "pillar_2", "rotation 1")),
        "j1_height_nm": float(safe_get(f, "pillar_1", "z span")) * 1e9,
        "j2_height_nm": float(safe_get(f, "pillar_2", "z span")) * 1e9,
    }
    expected = {
        "source_start_nm": SOURCE_START,
        "source_stop_nm": SOURCE_STOP,
        "source_polarization_angle_deg": 0.0 if pol == "x" else 90.0,
        "T_frequency_points": 41.0,
        "field_frequency_points": 41.0,
        "monitor_z_nm": 1000.0,
        "materials": [MATERIAL, MATERIAL],
        "j1_rotation_deg": float(g["j1_rotation_deg"]),
        "j2_rotation_deg": float(g["j2_rotation_deg"]),
        "j1_height_nm": float(g["height_nm"]),
        "j2_height_nm": float(g["height_nm"]),
    }
    ok = True
    for key, value in expected.items():
        actual = checks[key]
        if isinstance(value, list):
            ok = ok and actual == value
        else:
            ok = ok and abs(float(actual) - float(value)) < 1e-6
    return {
        "pass": bool(ok),
        "checks": checks,
        "expected": expected,
        "mesh_boundary_unchanged": True,
        "normalization_renormalized": False,
        "formal_extraction_points": 31,
        "native_monitor_points": 41,
    }


def setup_case(g: dict[str, Any], pol: str) -> dict[str, Any]:
    import lumapi

    cid = f"{g['geometry_id']}_{pol}"
    pre_meta = make_pre_fsp(g, pol)
    f = lumapi.FDTD(hide=True)
    try:
        f.load(pre_meta["path"])
        gate = readback_gate(g, pol, f)
    finally:
        try:
            f.close()
        except Exception:
            pass
    result = {
        "schema": "PAPER_A_LP_NEW_GEOMETRY_SETUP_ONLY_V1",
        "case_id": cid,
        "geometry_id": g["geometry_id"],
        "polarization": pol,
        "status": "PASS" if gate["pass"] else "BLOCKED",
        "solver_entered": False,
        "solver_run_called": False,
        "pre_fsp": pre_meta,
        "gate": gate,
        "material_contract": MATERIAL,
        "source_span_nm": [SOURCE_START, SOURCE_STOP],
        "formal_grid_nm": [GRID[0], GRID[-1]],
        "formal_points": len(GRID),
        "processes": PROCESSES,
        "threads": THREADS,
        "timestamp_utc": now(),
    }
    write_json(case_dir(cid) / "setup_only.json", result)
    return result


def material_audit() -> dict[str, Any]:
    path = ROOT / "outputs/material_reference/mdc_blue_oujizi_m/material_ref_native_sampled.csv"
    result = {"path": str(path), "exists": path.exists(), "models": {}}
    if not path.exists():
        return result
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for name in ("sio222", "tio22", "gan"):
        vals = [float(r["wavelength_nm"]) for r in rows if r.get("material_name") == name]
        result["models"][name] = {"min_nm": min(vals) if vals else None, "max_nm": max(vals) if vals else None, "covers_430_470": bool(vals and min(vals) <= 430 and max(vals) >= 470)}
    result["required_models_in_lp_parent"] = ["sio222", "tio22"]
    result["unused_native_model_in_parent"] = "gan"
    result["pass"] = all(result["models"][name]["covers_430_470"] for name in result["required_models_in_lp_parent"])
    return result


def preflight() -> dict[str, Any]:
    doe = load_doe()
    audit = {
        "schema": "PAPER_A_LP_NEW_GEOMETRY_SEARCH_PREFLIGHT_V1",
        "timestamp_utc": now(),
        "status": "PASS",
        "solver_entered": False,
        "solver_run_called": False,
        "material_validity": material_audit(),
        "source_content_contract": {"source_span_nm": [SOURCE_START, SOURCE_STOP], "formal_window_nm": [GRID[0], GRID[-1]], "formal_points": len(GRID), "reliable_amplitude_boundary_margin": True},
        "monitor_extractor_contract": {"native_points": 41, "formal_points": 31, "spacing_nm": 1.0, "formal_subset_indices": [5, 35]},
        "mesh_boundary_contract": "parent LP FDTD mesh and boundaries unchanged; geometry-only object edits",
        "normalization_contract": "existing complex weighted field normalization; no historical-window renormalization",
        "scheduler_contract": {"global_cap": 3, "max_active_fdt": 2, "processes": PROCESSES, "threads": THREADS},
        "doe_freeze_sha256": doe["freeze_sha256"],
        "old_candidate_bank_used": False,
    }
    if not audit["material_validity"].get("pass"):
        audit["status"] = "HARD_GATE_MATERIAL_VALIDITY"
    write_json(REPORT / "preflight.json", audit)
    return audit


def update_state(cid: str, **changes: Any) -> dict[str, Any]:
    p = case_state(cid)
    data = {}
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data.update(changes)
    data["updated_utc"] = now()
    write_json(p, data)
    return data


def extract_rows(f) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    low = load_module(LEGACY_EXTRACTOR, "lp_new_search_legacy_grid")
    transmission = np.asarray(f.transmission("T")).squeeze()
    transmission = np.real(np.asarray(transmission).reshape(-1))
    if len(transmission) != 41:
        raise RuntimeError(f"NATIVE_MONITOR_GRID_MISMATCH:{len(transmission)}")
    x, y, ex, ey, grid = low.base.b.f1.grid_plane(f, float(transmission[0]))
    ex, ey = np.asarray(ex).squeeze(), np.asarray(ey).squeeze()
    if ex.ndim == 2:
        ex, ey = ex[:, :, None], ey[:, :, None]
    if ex.shape[2] != 41:
        raise RuntimeError(f"NATIVE_FIELD_GRID_MISMATCH:{ex.shape}")
    rows = []
    for idx, wl in enumerate(NATIVE_GRID):
        raw_x = low.base.b.f1.periodic_weighted(x, y, ex[:, :, idx], grid["x_periodic_duplicate_endpoint"], grid["y_periodic_duplicate_endpoint"])
        raw_y = low.base.b.f1.periodic_weighted(x, y, ey[:, :, idx], grid["x_periodic_duplicate_endpoint"], grid["y_periodic_duplicate_endpoint"])
        t = float(transmission[idx])
        if wl < GRID[0] or wl > GRID[-1]:
            continue
        if t < 0 and GRID[0] <= wl <= GRID[-1]:
            raise RuntimeError(f"NEGATIVE_FORMAL_TRANSMISSION:{wl}:{t}")
        nx, ny = low.base.b.f1.normalize_pair(raw_x, raw_y, t)
        rows.append({
            "wavelength_nm": float(wl),
            "raw_weighted_Ex_real": float(raw_x.real),
            "raw_weighted_Ex_imag": float(raw_x.imag),
            "raw_weighted_Ey_real": float(raw_y.real),
            "raw_weighted_Ey_imag": float(raw_y.imag),
            "weighted_Ex_real": float(nx.real),
            "weighted_Ex_imag": float(nx.imag),
            "weighted_Ey_real": float(ny.real),
            "weighted_Ey_imag": float(ny.imag),
            "source_T": t,
            "selected_power": float(abs(nx) ** 2 + abs(ny) ** 2),
            "normalization_renormalized": False,
        })
    if [r["wavelength_nm"] for r in rows] != GRID:
        raise RuntimeError("FORMAL_GRID_EXTRACTOR_MISMATCH")
    return rows, {"native_negative_transmission_outside_formal": [{"wavelength_nm": float(wl), "value": t} for wl, t in zip(NATIVE_GRID, transmission) if t < 0 and not (GRID[0] <= wl <= GRID[-1])], "formal_negative_transmission": [{"wavelength_nm": float(wl), "value": t} for wl, t in zip(NATIVE_GRID, transmission) if t < 0 and GRID[0] <= wl <= GRID[-1]]}


def run_case(case_id: str) -> dict[str, Any]:
    import lumapi

    doe = load_doe()
    gid, pol = case_id.rsplit("_", 1)
    g = next(x for x in doe["geometries"] if x["geometry_id"] == gid)
    cid = case_id
    d = case_dir(cid)
    d.mkdir(parents=True, exist_ok=True)
    checkpoint = d / "checkpoint.json"
    if checkpoint.exists():
        data = json.loads(checkpoint.read_text(encoding="utf-8"))
        if data.get("status") == "ACCEPTED":
            return {"case_id": cid, "status": "RECOVERED_FROM_CHECKPOINT", "solver_entered": True}
    state_p = case_state(cid)
    if state_p.exists():
        old = json.loads(state_p.read_text(encoding="utf-8"))
        if old.get("solver_entered") is True:
            return {"case_id": cid, "status": "QUARANTINED_ENTERED_NO_REPLAY", "solver_entered": True}
    setup = json.loads((d / "setup_only.json").read_text(encoding="utf-8"))
    if setup.get("status") != "PASS" or not setup.get("gate", {}).get("pass"):
        return {"case_id": cid, "status": "BLOCKED_SETUP_GATE", "solver_entered": False}
    pre = Path(setup["pre_fsp"]["path"])
    record = {
        "schema": "PAPER_A_LP_NEW_GEOMETRY_ATTEMPT_V1",
        "case_id": cid,
        "geometry_id": gid,
        "polarization": pol,
        "geometry_hash_sha256": g["geometry_hash_sha256"],
        "doe_freeze_sha256": doe["freeze_sha256"],
        "branch": BRANCH,
        "worktree": WORKTREE,
        "pre_fsp_path": str(pre),
        "pre_fsp_sha256": sha_file(pre),
        "solver_entered": False,
        "entered_solver": False,
        "processes": PROCESSES,
        "threads": THREADS,
        "started_utc": now(),
        "solver_replay": False,
    }
    write_json(d / "attempt_provenance.json", record)
    lease = None
    f = None
    try:
        sched = load_module(SCHEDULER_PATH, "lp_new_search_scheduler")
        scheduler = sched.GlobalSlotScheduler(SLOT_REGISTRY)
        update_state(cid, case_id=cid, geometry_id=gid, polarization=pol, status="WAITING", solver_entered=False)
        lease = scheduler.acquire_wait(
            branch=BRANCH,
            worktree=WORKTREE,
            task_id=TASK_ID,
            case_uid=cid,
            pid=os.getpid(),
            metadata={"task_class": "PAPER_A_NEW_LP_FDTD", "attempt_id": cid, "polarization": pol, "H_global_nm": g["height_nm"]},
            timeout_s=21600.0,
            poll_s=30.0,
        )
        record.update({"slot_acquired": True, "slot_id": lease.slot_id, "slot_acquire_time": lease.record.get("slot_acquire_time"), "admission_snapshot": lease.record.get("admission_snapshot"), "status": "SLOT_ACQUIRED"})
        update_state(cid, status="SLOT_ACQUIRED", slot_id=lease.slot_id, solver_entered=False)
        write_json(d / "attempt_provenance.json", record)
        f = lumapi.FDTD(hide=True)
        f.load(str(pre))
        gate = readback_gate(g, pol, f)
        record["configuration_gate"] = gate
        if not gate["pass"]:
            record["status"] = "QUARANTINED_PREFLIGHT_GATE"
            update_state(cid, status=record["status"], solver_entered=False, configuration_gate=gate)
            return record
        authority_hook = globals().get("PRE_ENTRY_AUTHORITY_CHECK")
        if authority_hook is not None:
            authority_check = authority_hook(cid, pre)
            record["prepared_input_authority"] = authority_check
            if not authority_check.get("pass"):
                record["status"] = "QUARANTINED_PRE_ENTRY_AUTHORITY"
                update_state(cid, status=record["status"], solver_entered=False, configuration_gate=gate, prepared_input_authority=authority_check)
                return record
        f.setresource("FDTD", 1, "processes", str(PROCESSES))
        entered = now()
        lease.mark_solver_entered(entered)
        record.update({"solver_entered": True, "entered_solver": True, "entered_utc": entered, "solver_start": entered, "status": "ENTERED"})
        update_state(cid, status="RUNNING", solver_entered=True, entered_utc=entered, slot_id=lease.slot_id, solver_pid=os.getpid(), configuration_gate=gate)
        write_json(d / "attempt_provenance.json", record)
        f.run()
        completed = now()
        record["solver_complete"] = completed
        run_fsp = d / f"{cid}_run.fsp"
        f.save(str(run_fsp))
        record.update({"run_fsp_path": str(run_fsp), "run_fsp_sha256": sha_file(run_fsp), "status": "RETURNED"})
        lease.release("SOLVER_COMPLETED", completed)
        lease = None
        update_state(cid, status="RETURNED", solver_entered=True, solver_complete=completed, run_fsp_sha256=record["run_fsp_sha256"])
        rows, extraction_diagnostics = extract_rows(f)
        checkpoint_data = {
            "schema": "PAPER_A_LP_NEW_GEOMETRY_CHECKPOINT_V1",
            "status": "ACCEPTED",
            "case_id": cid,
            "geometry_id": gid,
            "polarization": pol,
            "geometry": g,
            "doe_freeze_sha256": doe["freeze_sha256"],
            "setup": setup,
            "configuration_gate": gate,
            "rows": rows,
            "formal_grid_nm": GRID,
            "source_span_nm": [SOURCE_START, SOURCE_STOP],
            "solver_entered": True,
            "solver_replay": False,
            "extraction_diagnostics": extraction_diagnostics,
        }
        write_json(checkpoint, checkpoint_data)
        record.update({"status": "ACCEPTED", "checkpoint_path": str(checkpoint), "checkpoint_sha256": sha_file(checkpoint), "row_count": len(rows)})
        update_state(cid, status="COMPLETED", solver_entered=True, checkpoint_path=str(checkpoint), checkpoint_sha256=record["checkpoint_sha256"])
        return record
    except Exception as exc:
        record.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc(), "retained_data_status": "entered_evidence_preserved_no_replay" if record.get("solver_entered") else "pre_entry_failure_evidence_preserved"})
        update_state(cid, status="FAILED", solver_entered=bool(record.get("solver_entered")), error=record["error"])
        return record
    finally:
        if lease is not None:
            try:
                lease.release("FAILED_ENTERED" if record.get("solver_entered") else "FAILED_PRE_ENTRY")
            except Exception as exc:
                record["slot_release_error"] = str(exc)
        if f is not None:
            try:
                f.close()
            except Exception:
                pass
        write_json(d / "attempt_provenance.json", record)


def recover_case(case_id: str) -> dict[str, Any]:
    import lumapi

    doe = load_doe()
    gid, pol = case_id.rsplit("_", 1)
    g = next(x for x in doe["geometries"] if x["geometry_id"] == gid)
    d = case_dir(case_id)
    state = json.loads(case_state(case_id).read_text(encoding="utf-8"))
    if state.get("solver_entered") is not True:
        raise RuntimeError("RECOVERY_REQUIRES_ENTERED_TRUE")
    run_fsp = d / f"{case_id}_run.fsp"
    if not run_fsp.exists():
        raise RuntimeError("RECOVERY_RUN_FSP_MISSING")
    setup = json.loads((d / "setup_only.json").read_text(encoding="utf-8"))
    f = lumapi.FDTD(hide=True)
    try:
        f.load(str(run_fsp))
        rows, diagnostics = extract_rows(f)
    finally:
        try: f.close()
        except Exception: pass
    checkpoint_data = {
        "schema": "PAPER_A_LP_NEW_GEOMETRY_CHECKPOINT_V1",
        "status": "ACCEPTED",
        "case_id": case_id, "geometry_id": gid, "polarization": pol,
        "geometry": g, "doe_freeze_sha256": doe["freeze_sha256"], "setup": setup,
        "configuration_gate": setup["gate"], "rows": rows, "formal_grid_nm": GRID,
        "source_span_nm": [SOURCE_START, SOURCE_STOP], "solver_entered": True,
        "solver_replay": False, "recovered_from_returned_run_fsp": True,
        "extraction_diagnostics": diagnostics,
    }
    checkpoint_path = d / "checkpoint.json"
    write_json(checkpoint_path, checkpoint_data)
    update_state(case_id, status="COMPLETED", solver_entered=True, recovered_from_returned_run_fsp=True, checkpoint_path=str(checkpoint_path), checkpoint_sha256=sha_file(checkpoint_path), extraction_diagnostics=diagnostics)
    p = d / "attempt_provenance.json"
    rec = json.loads(p.read_text(encoding="utf-8"))
    rec.update({"status": "ACCEPTED", "recovered_from_returned_run_fsp": True, "checkpoint_path": str(checkpoint_path), "checkpoint_sha256": sha_file(checkpoint_path), "extraction_diagnostics": diagnostics, "solver_replay": False})
    write_json(p, rec)
    return {"case_id": case_id, "status": "RECOVERED_FROM_RETURNED_RUN_FSP", "solver_entered": True, "extraction_diagnostics": diagnostics, "checkpoint_sha256": sha_file(checkpoint_path)}


def mdc_weights() -> dict[str, Any]:
    path = ROOT / "paper_a_broadband/references/mdc/spectral_profiles_420_480_plot_data.csv"
    rows = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if row.get("structure_key") == "zl1_alternative":
                rows.append((float(row["wavelength_nm"]), float(row["r12_normalized_output"])))
    rows.sort()
    wavelengths = np.asarray([x[0] for x in rows])
    values = np.asarray([x[1] for x in rows])
    if wavelengths.min() > 435 or wavelengths.max() < 465:
        raise RuntimeError("MDC_WEIGHTING_COVERAGE_CONFLICT")
    formal_values = np.interp(np.asarray(GRID), wavelengths, values)
    formal_weights = formal_values / formal_values.sum()
    overlap_fraction = float(np.trapezoid(values[(wavelengths >= 435) & (wavelengths <= 465)], wavelengths[(wavelengths >= 435) & (wavelengths <= 465)]) / np.trapezoid(values, wavelengths))
    fwhm_mask = (np.asarray(GRID) >= MDC_FWHM[0]) & (np.asarray(GRID) <= MDC_FWHM[1])
    fwhm_weights = formal_values[fwhm_mask] / formal_values[fwhm_mask].sum()
    result = {
        "schema": "PAPER_A_MDC_ZL1_ALTERNATIVE_WEIGHTING_V1",
        "source_csv": str(path),
        "structure_key": "zl1_alternative",
        "normalization": "r12_normalized_output relative spectral shape; not absolute emitted power or LEE",
        "source_range_nm": [float(wavelengths.min()), float(wavelengths.max())],
        "formal_grid_nm": GRID,
        "normalized_weights_435_465": formal_weights.tolist(),
        "formal_overlap_fraction_from_420_480_integral": overlap_fraction,
        "effective_center_nm_435_465": float(np.sum(np.asarray(GRID) * formal_weights)),
        "effective_sigma_nm_435_465": float(np.sqrt(np.sum((np.asarray(GRID) - np.sum(np.asarray(GRID) * formal_weights)) ** 2 * formal_weights))),
        "fwhm_nm": list(MDC_FWHM),
        "fwhm_formal_indices": np.where(fwhm_mask)[0].tolist(),
        "normalized_weights_mdc_fwhm": fwhm_weights.tolist(),
    }
    write_json(REPORT / "mdc_weighting.json", result)
    return result


def stokes_from_jones(J: np.ndarray) -> dict[str, float]:
    C = 0.5 * J @ J.conj().T
    s0 = float(np.trace(C).real)
    s1 = float((C[0, 0] - C[1, 1]).real)
    s2 = float((2.0 * C[0, 1].real))
    s3 = float((-2.0 * C[0, 1].imag))
    dolp = math.sqrt(max(0.0, s1 * s1 + s2 * s2)) / s0 if s0 > 0 else float("nan")
    psi = 0.5 * math.atan2(s2, s1) if s0 > 0 else float("nan")
    vals, vecs = np.linalg.eigh(C)
    v = vecs[:, int(np.argmax(vals))]
    dom_psi = 0.5 * math.atan2(float(2.0 * (v[0].conjugate() * v[1]).real), float(abs(v[0]) ** 2 - abs(v[1]) ** 2))
    sv = np.linalg.svd(J, compute_uv=False)
    return {
        "S0": s0, "S1": s1, "S2": s2, "S3": s3, "DoLP": float(dolp),
        "psi_deg": math.degrees(psi) % 180.0, "dominant_psi_deg": math.degrees(dom_psi) % 180.0,
        "total_power": 0.5 * s0, "useful_lp_power": 0.5 * math.sqrt(max(0.0, s1 * s1 + s2 * s2)),
        "circular_contamination": abs(s3) / s0 if s0 > 0 else float("nan"),
        "sigma1": float(sv[0]), "sigma2": float(sv[1]), "sigma2_over_sigma1": float(sv[1] / sv[0]) if sv[0] > 0 else float("nan"),
    }


def integrate_metrics(rows_x: list[dict[str, Any]], rows_y: list[dict[str, Any]], g: dict[str, Any]) -> dict[str, Any]:
    by_x = {float(x["wavelength_nm"]): x for x in rows_x}
    by_y = {float(x["wavelength_nm"]): x for x in rows_y}
    spectrum = []
    Cs = []
    for wl in GRID:
        x, y = by_x[wl], by_y[wl]
        J = np.asarray([
            [complex(x["weighted_Ex_real"], x["weighted_Ex_imag"]), complex(y["weighted_Ex_real"], y["weighted_Ex_imag"])],
            [complex(x["weighted_Ey_real"], x["weighted_Ey_imag"]), complex(y["weighted_Ey_real"], y["weighted_Ey_imag"])],
        ], dtype=complex)
        metric = stokes_from_jones(J)
        metric.update({"geometry_id": g["geometry_id"], "wavelength_nm": wl})
        spectrum.append(metric)
        Cs.append(0.5 * J @ J.conj().T)
    w = mdc_weights()
    weights = np.asarray(w["normalized_weights_435_465"])
    Cw = np.sum(np.asarray(Cs) * weights[:, None, None], axis=0)
    sw = {
        "S0": float(np.trace(Cw).real),
        "S1": float((Cw[0, 0] - Cw[1, 1]).real),
        "S2": float(2 * Cw[0, 1].real),
        "S3": float(-2 * Cw[0, 1].imag),
    }
    sw["DoLP"] = math.sqrt(max(0.0, sw["S1"] ** 2 + sw["S2"] ** 2)) / sw["S0"] if sw["S0"] > 0 else float("nan")
    sw["psi_deg"] = math.degrees(0.5 * math.atan2(sw["S2"], sw["S1"])) % 180.0
    sw["total_power"] = 0.5 * sw["S0"]
    sw["useful_lp_power"] = 0.5 * math.sqrt(max(0.0, sw["S1"] ** 2 + sw["S2"] ** 2))
    sw["circular_contamination"] = abs(sw["S3"]) / sw["S0"] if sw["S0"] > 0 else float("nan")
    fidx = [i for i, wl in enumerate(GRID) if MDC_FWHM[0] <= wl <= MDC_FWHM[1]]
    psi_rad = np.unwrap(2 * np.radians([spectrum[i]["psi_deg"] for i in fidx])) / 2
    psi_span = math.degrees(float(np.max(psi_rad) - np.min(psi_rad))) if len(psi_rad) else float("nan")
    dolp_f = [spectrum[i]["DoLP"] for i in fidx]
    useful_f = [spectrum[i]["useful_lp_power"] for i in fidx]
    sigma_ratio = [spectrum[i]["sigma2_over_sigma1"] for i in fidx]
    summary = {
        "geometry_id": g["geometry_id"],
        "role": g["role"],
        "mdc_weighted_DoLP": sw["DoLP"],
        "mdc_weighted_useful_lp_power": sw["useful_lp_power"],
        "mdc_weighted_total_power": sw["total_power"],
        "mdc_weighted_psi_deg": sw["psi_deg"],
        "mdc_weighted_circular_contamination": sw["circular_contamination"],
        "mdc_fwhm_psi_span_deg": psi_span,
        "mdc_fwhm_DoLP_worst": float(min(dolp_f)) if dolp_f else None,
        "mdc_fwhm_DoLP_mean": float(np.mean(dolp_f)) if dolp_f else None,
        "mdc_fwhm_useful_lp_power_worst": float(min(useful_f)) if useful_f else None,
        "mdc_fwhm_sigma2_over_sigma1_worst": float(max(sigma_ratio)) if sigma_ratio else None,
        "formal_DoLP_worst": float(min(s["DoLP"] for s in spectrum)),
        "formal_DoLP_mean": float(np.mean([s["DoLP"] for s in spectrum])),
        "formal_useful_lp_power_mean": float(np.mean([s["useful_lp_power"] for s in spectrum])),
        "formal_useful_lp_power_worst": float(min(s["useful_lp_power"] for s in spectrum)),
        "state_flip": False,
        "final_pass": bool(sw["DoLP"] >= 0.80 and sw["useful_lp_power"] >= 0.35 and psi_span <= 10.0 and (min(dolp_f) if dolp_f else 0.0) >= 0.70 and sw["circular_contamination"] < sw["DoLP"]),
        "promising": bool(sw["DoLP"] >= 0.65 and sw["useful_lp_power"] >= 0.30 and psi_span <= 15.0 and (min(dolp_f) if dolp_f else 0.0) > 0.50),
        "qualification_axis_free": True,
        "phase_used_for_qualification": False,
        "k6_used": False,
    }
    write_csv(REPORT / f"{g['geometry_id']}_formal_spectra.csv", spectrum)
    write_json(REPORT / f"{g['geometry_id']}_metrics.json", {"summary": summary, "weighted_stokes": sw, "spectrum": spectrum, "mdc_weighting": w})
    return summary


def postprocess_geometry(gid: str) -> dict[str, Any]:
    doe = load_doe()
    g = next(x for x in doe["geometries"] if x["geometry_id"] == gid)
    rows = []
    for pol in ("x", "y"):
        cp = case_dir(f"{gid}_{pol}") / "checkpoint.json"
        if not cp.exists():
            raise RuntimeError(f"POSTPROCESS_MISSING_CHECKPOINT:{gid}_{pol}")
        rows.append(json.loads(cp.read_text(encoding="utf-8"))["rows"])
    result = integrate_metrics(rows[0], rows[1], g)
    write_json(REPORT / f"{gid}_decision.json", {"schema": "PAPER_A_LP_GEOMETRY_WAVE_DECISION_V1", "timestamp_utc": now(), "summary": result, "stop_after_this_geometry": result["final_pass"]})
    return result


def scheduler_snapshot() -> dict[str, Any]:
    sched = load_module(SCHEDULER_PATH, "lp_new_search_snapshot")
    raw = sched.live_job_snapshot()
    return {
        "timestamp_utc": raw.get("timestamp_utc"),
        "global_active_jobs": raw.get("global_active_jobs"),
        "active_fdtd_jobs": raw.get("active_fdtd_jobs"),
        "active_rcwa_jobs": raw.get("active_rcwa_jobs"),
        "unknown_solver_jobs": raw.get("unknown_solver_jobs"),
        "jobs": [{"branch": j.get("branch"), "case_uid": j.get("case_uid"), "solver_type": j.get("solver_type")} for j in raw.get("jobs", [])],
    }


def boundary_check() -> dict[str, Any]:
    snap = scheduler_snapshot()
    other = [j for j in snap["jobs"] if j.get("branch") != BRANCH]
    result = {"snapshot": snap, "allow_next_wave": not snap["unknown_solver_jobs"] and not other and snap["active_fdtd_jobs"] == 0, "reason": "NO_OTHER_ACTIVE_SOLVER" if not other else "HIGHER_PRIORITY_OR_EXTERNAL_ACTIVE"}
    append_jsonl(REPORT / "boundary_events.jsonl", result)
    return result


def monitor_loop(stop: threading.Event, wave: str) -> None:
    lock = RUNTIME / "monitor" / "paper_a_lp_new_search_monitor.lock"
    if lock.exists():
        raise RuntimeError("DUPLICATE_MONITOR_GUARD")
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps({"pid": os.getpid(), "created_utc": now(), "wave": wave}), encoding="utf-8")
    try:
        while not stop.wait(600.0):
            states = []
            for p in RUNTIME.glob("cases/*/state.json"):
                try:
                    states.append(json.loads(p.read_text(encoding="utf-8")))
                except Exception:
                    pass
            append_jsonl(RUNTIME / "monitor/paper_a_lp_new_search_progress.jsonl", {
                "timestamp": now(), "task": TASK_ID, "wave": wave,
                "completed": sum(s.get("status") == "COMPLETED" for s in states),
                "running": sum(s.get("status") == "RUNNING" for s in states),
                "waiting": sum(s.get("status") == "WAITING" for s in states),
                "states": [{"case_id": s.get("case_id"), "status": s.get("status"), "solver_entered": s.get("solver_entered")} for s in states],
                "scheduler": scheduler_snapshot(),
            })
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


def run_wave(gid: str) -> dict[str, Any]:
    doe = load_doe()
    g = next(x for x in doe["geometries"] if x["geometry_id"] == gid)
    for pol in ("x", "y"):
        if not (case_dir(f"{gid}_{pol}") / "setup_only.json").exists():
            setup_case(g, pol)
    results = []
    procs = []
    logs = []
    for pol in ("x", "y"):
        cid = f"{gid}_{pol}"
        log_path = case_dir(cid) / "controller.log"
        fh = log_path.open("a", encoding="utf-8")
        logs.append(fh)
        p = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "run-case", "--case-id", cid], stdout=fh, stderr=fh)
        procs.append((cid, p))
    while any(p.poll() is None for _, p in procs):
        time.sleep(5.0)
    for cid, p in procs:
        results.append({"case_id": cid, "returncode": p.returncode, "state": json.loads(case_state(cid).read_text(encoding="utf-8")) if case_state(cid).exists() else None})
    for fh in logs:
        fh.close()
    if any(x["returncode"] != 0 or not x["state"] or x["state"].get("status") != "COMPLETED" for x in results):
        return {"geometry_id": gid, "status": "FAILED", "cases": results}
    summary = postprocess_geometry(gid)
    return {"geometry_id": gid, "status": "COMPLETED", "cases": results, "summary": summary}


def run_search() -> dict[str, Any]:
    REPORT.mkdir(parents=True, exist_ok=True)
    pre = preflight()
    if pre["status"] != "PASS":
        return {"status": pre["status"], "preflight": pre}
    stop = threading.Event()
    monitor = threading.Thread(target=monitor_loop, args=(stop, "search"), daemon=True)
    monitor.start()
    waves = []
    try:
        doe = load_doe()
        for g in doe["geometries"]:
            boundary = boundary_check()
            if not boundary["allow_next_wave"]:
                result = {"status": "LOW_PRIORITY_BACKGROUND_WAIT", "geometry_id": g["geometry_id"], "boundary": boundary, "waves_completed": waves}
                write_json(REPORT / "terminal_state.json", result)
                return result
            result = run_wave(g["geometry_id"])
            waves.append(result)
            if result.get("status") != "COMPLETED":
                final = {"status": "HARD_GATE_CASE_FAILURE", "waves": waves}
                write_json(REPORT / "terminal_state.json", final)
                return final
            if result["summary"].get("final_pass"):
                final = {"status": "PAPER_A_BROADBAND_LP_NEW_GEOMETRY_SEARCH_FINAL_PASS", "primary": g["geometry_id"], "waves": waves, "solver_entered_cases": len(waves) * 2}
                write_json(REPORT / "terminal_success.json", final)
                return final
        summaries = [w["summary"] for w in waves if "summary" in w]
        final = {"status": "PAPER_A_BROADBAND_LP_NEW_GEOMETRY_SEARCH_INITIAL_DOE_COMPLETE", "waves": waves, "promising_count": sum(bool(x.get("promising")) for x in summaries), "solver_entered_cases": len(waves) * 2, "next_action": "evaluate preregistered local refinement allowance if promising_count>0"}
        write_json(REPORT / "terminal_success.json", final)
        return final
    finally:
        stop.set()
        monitor.join(timeout=2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["preflight", "setup-wave", "run-case", "run-wave", "recover-case", "postprocess", "run-search", "scheduler"])
    ap.add_argument("--geometry-id")
    ap.add_argument("--case-id")
    args = ap.parse_args()
    if args.mode == "preflight":
        print(json.dumps(preflight(), indent=2, ensure_ascii=False))
    elif args.mode == "setup-wave":
        doe = load_doe(); gid = args.geometry_id or "LPBROAD_G001"; g = next(x for x in doe["geometries"] if x["geometry_id"] == gid)
        results = [setup_case(g, p) for p in ("x", "y")]
        write_json(REPORT / f"{gid}_setup_only.json", {"status": "PASS" if all(x["status"] == "PASS" for x in results) else "BLOCKED", "cases": results, "solver_calls": 0})
        print(json.dumps(results, indent=2, ensure_ascii=False))
    elif args.mode == "run-case":
        print(json.dumps(run_case(args.case_id), indent=2, ensure_ascii=False))
    elif args.mode == "run-wave":
        print(json.dumps(run_wave(args.geometry_id or "LPBROAD_G001"), indent=2, ensure_ascii=False))
    elif args.mode == "recover-case":
        print(json.dumps(recover_case(args.case_id), indent=2, ensure_ascii=False))
    elif args.mode == "postprocess":
        print(json.dumps(postprocess_geometry(args.geometry_id or "LPBROAD_G001"), indent=2, ensure_ascii=False))
    elif args.mode == "run-search":
        print(json.dumps(run_search(), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(scheduler_snapshot(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
