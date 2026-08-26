from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
AUTHORITY = ROOT / "paper_a_broadband/authority/paper_a_fdtd_physics_validity_gate_v1.json"
C0 = 299792458.0
sys.path.insert(0, r"N:/Program Files/ANSYS Inc/v251/Lumerical/api/python")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def authority() -> dict[str, Any]:
    data = json.loads(AUTHORITY.read_text(encoding="utf-8"))
    if data.get("schema") != "PAPER_A_FDTD_PHYSICS_VALIDITY_GATE_V1":
        raise RuntimeError("AUTHORITY_SCHEMA_INVALID")
    if data.get("resource_safety", {}).get("NEW_FDTD_BUDGET") != 0:
        raise RuntimeError("AUTHORITY_ZERO_SOLVER_CONFLICT")
    return data


def formal_grid(contract: dict[str, Any]) -> np.ndarray:
    start, stop = contract["formal_window_nm"]
    step = contract["formal_spacing_nm"]
    points = contract["formal_points"]
    grid = np.asarray([start + i * step for i in range(points)], dtype=float)
    if not math.isclose(float(grid[-1]), float(stop), abs_tol=1e-12):
        raise RuntimeError("FORMAL_GRID_CONTRACT_INVALID")
    return grid


def exact_indices(wavelength_nm: np.ndarray, grid: np.ndarray) -> list[int]:
    indices: list[int] = []
    for target in grid:
        hit = np.flatnonzero(np.isclose(wavelength_nm, target, rtol=0.0, atol=1e-8))
        if len(hit) != 1:
            raise RuntimeError(f"FORMAL_MONITOR_COORDINATE_UNAVAILABLE:{target}:{len(hit)}")
        indices.append(int(hit[0]))
    return indices


def parse_log(path: Path, thresholds: dict[str, Any]) -> dict[str, Any]:
    values: list[float] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.search(r"Auto Shutoff:\s*([0-9.eE+-]+)", line)
        if match:
            values.append(float(match.group(1)))
    if not values:
        return {"status": "INSUFFICIENT_EVIDENCE_NOT_VALIDATED", "reason": "no Auto Shutoff trajectory in immutable solver log", "path": str(path), "sha256": sha_file(path)}
    initial_ref = float(thresholds["auto_shutoff_initial_reference"]["value"])
    tail_count = max(3, math.ceil(len(values) / 3))
    tail = np.asarray(values[-tail_count:], dtype=float)
    slope = float(np.polyfit(np.arange(len(tail), dtype=float), tail, 1)[0]) if len(tail) >= 2 else 0.0
    log_tail_slope = None
    if np.all(tail > 0) and len(tail) >= 2:
        log_tail_slope = float(np.polyfit(np.arange(len(tail), dtype=float), np.log(tail), 1)[0])
    prior_min = min(values[:-tail_count] or values)
    returned_above_reference = bool(prior_min < initial_ref and values[-1] > initial_ref)
    positive_tail_growth = bool(tail[-1] > tail[0] and slope > 0.0)
    invalid = bool(returned_above_reference and positive_tail_growth)
    return {
        "status": "INVALID_FOR_PHYSICS_TRUTH" if invalid else "PASS",
        "path": str(path), "sha256": sha_file(path), "sample_count": len(values),
        "trajectory": values, "final_auto_shutoff": values[-1], "peak_auto_shutoff": max(values), "minimum_auto_shutoff": min(values),
        "late_window": {"count": tail_count, "first": float(tail[0]), "last": float(tail[-1]), "linear_slope": slope, "log_linear_slope": log_tail_slope},
        "signals": {"previous_decay_below_initial_reference": prior_min < initial_ref, "returned_above_initial_reference": returned_above_reference, "positive_tail_growth": positive_tail_growth, "exponential_like_growth_indicator": bool(log_tail_slope is not None and log_tail_slope > 0.0)},
        "threshold_provenance": thresholds["late_time_divergence"],
    }


def inspect_completed_fsp(path: Path, gate_authority: dict[str, Any]) -> dict[str, Any]:
    import lumapi

    grid = formal_grid(gate_authority["formal_spectral_contract"])
    f = lumapi.FDTD(hide=True)
    try:
        f.load(str(path))
        frequency = np.asarray(f.getdata("T", "f")).reshape(-1)
        wavelength_nm = C0 / frequency * 1e9
        transmission = np.real(np.asarray(f.transmission("T")).reshape(-1))
        sourcepower = np.real(np.asarray(f.sourcepower(frequency)).reshape(-1))
        indices = exact_indices(wavelength_nm, grid)
        t = transmission[indices]
        p = sourcepower[indices]
        threshold = float(gate_authority["thresholds"]["passive_transmission_control_envelope_max_abs"]["value"])
        ratio = float(np.min(np.abs(p)) / np.max(np.abs(p))) if np.max(np.abs(p)) else 0.0
        source_pass = bool(np.all(np.isfinite(p)) and np.all(p > 0.0) and ratio >= float(gate_authority["thresholds"]["sourcepower_ratio_min"]["value"]))
        return {
            "path": str(path), "sha256": sha_file(path),
            "source": {"polarization_angle_deg": float(f.getnamed("source", "polarization angle")), "injection_axis": str(f.getnamed("source", "injection axis")), "direction": str(f.getnamed("source", "direction")), "z_nm": float(f.getnamed("source", "z")) * 1e9},
            "monitor": {"type": str(f.getnamed("T", "monitor type")), "z_nm": float(f.getnamed("T", "z")) * 1e9, "frequency_points": int(round(float(f.getnamed("T", "frequency points"))))},
            "grid": {"native_points": len(wavelength_nm), "start_nm": float(wavelength_nm[0]), "stop_nm": float(wavelength_nm[-1]), "ascending": bool(np.all(np.diff(wavelength_nm) > 0.0)), "formal_indices": indices, "formal_exact": True},
            "transmission": {"values": t.tolist(), "finite": bool(np.all(np.isfinite(t))), "negative_count": int(np.sum(t < 0.0)), "persistent_negative": bool(np.any(t < 0.0)), "max_abs": float(np.max(np.abs(t))), "control_envelope_excess_count": int(np.sum(np.abs(t) > threshold)), "control_envelope_max_abs": threshold},
            "source_normalization": {"values": p.tolist(), "finite": bool(np.all(np.isfinite(p))), "strictly_positive": bool(np.all(p > 0.0)), "min": float(np.min(p)), "max": float(np.max(p)), "min_over_max": ratio, "pass": source_pass},
        }
    finally:
        f.close()


def combine(case_id: str, post_fsp: Path, log: Path, gate_authority: dict[str, Any]) -> dict[str, Any]:
    convergence = parse_log(log, gate_authority["thresholds"])
    completed = inspect_completed_fsp(post_fsp, gate_authority)
    gate_1 = convergence
    gate_2 = {
        "status": convergence["status"],
        "observable": "solver Auto Shutoff trajectory (only persisted time-resolved electromagnetic-energy/residual proxy)",
        "independent_time_series_field_energy": "NOT_PERSISTED",
        "late_time_energy_accumulation": convergence.get("signals", {}).get("returned_above_initial_reference"),
        "growth_indicator": convergence.get("signals", {}).get("exponential_like_growth_indicator"),
    }
    t = completed["transmission"]
    gate_3_invalid = (not t["finite"]) or (gate_1["status"] == "INVALID_FOR_PHYSICS_TRUTH" and (t["persistent_negative"] or t["control_envelope_excess_count"] > 0))
    gate_3 = {"status": "INVALID_FOR_PHYSICS_TRUTH" if gate_3_invalid else "PASS", "finite": t["finite"], "negative_count": t["negative_count"], "control_envelope_excess_count": t["control_envelope_excess_count"], "no_transformation_applied": True}
    gate_4 = {"status": "PASS" if completed["source_normalization"]["pass"] else "INVALID_FOR_PHYSICS_TRUTH", **completed["source_normalization"]}
    statuses = [gate_1["status"], gate_2["status"], gate_3["status"], gate_4["status"]]
    if "INSUFFICIENT_EVIDENCE_NOT_VALIDATED" in statuses:
        final = "INSUFFICIENT_EVIDENCE_NOT_VALIDATED"
    elif "INVALID_FOR_PHYSICS_TRUTH" in statuses:
        final = "INVALID_FOR_PHYSICS_TRUTH"
    else:
        final = "VALID_FOR_PHYSICS_TRUTH"
    return {
        "schema": "PAPER_A_FDTD_PHYSICS_VALIDITY_GATE_RESULT_V1", "case_id": case_id, "status": final,
        "root_cause": "E_NUMERICAL_TIME_DOMAIN_DIVERGENCE_IN_STORED_SOLVER_ENERGY_RESULT" if final == "INVALID_FOR_PHYSICS_TRUTH" and gate_1["status"] == "INVALID_FOR_PHYSICS_TRUTH" else None,
        "authority_path": str(AUTHORITY), "authority_sha256": sha_file(AUTHORITY), "post_fsp": completed, "solver_log": convergence,
        "gates": {"gate_1_solver_convergence": gate_1, "gate_2_late_time_energy": gate_2, "gate_3_transmission_sanity": gate_3, "gate_4_source_normalization": gate_4},
        "resource_safety": {"NEW_FDTD_BUDGET": 0, "solver_run_called": False, "solver_entered": 0, "scheduler_admission": False, "rcwa": 0, "ml": 0},
        "raw_solver_data_modified": False, "timestamp_utc": now(),
    }


def setup_compatibility(setup_paths: list[Path]) -> dict[str, Any]:
    rows = []
    for path in setup_paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        rows.append({"path": str(path), "sha256": sha_file(path), "case_id": data.get("case_id"), "solver_entered": data.get("solver_entered"), "solver_run_called": data.get("solver_run_called"), "status": data.get("status")})
    return {"schema": "PAPER_A_FDTD_PHYSICS_VALIDITY_GATE_SETUP_COMPATIBILITY_V1", "status": "PASS", "setup_artifacts": rows, "all_setup_only": all(row["solver_entered"] is False and row["solver_run_called"] is False for row in rows), "gate_invocation_contract": "future completed post-FSP plus immutable p0 log may invoke this gate without scheduler admission", "resource_safety": {"NEW_FDTD_BUDGET": 0, "solver_run_called": False, "solver_entered": 0, "scheduler_admission": False}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id")
    parser.add_argument("--post-fsp", type=Path)
    parser.add_argument("--solver-log", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--setup-compatibility", nargs="*", type=Path)
    args = parser.parse_args()
    source = Path(__file__).read_text(encoding="utf-8")
    if any(token in source for token in ["f." + "run(", "switch" + "tolayout(", ".save(" + "str("]):
        raise RuntimeError("ZERO_SOLVER_GUARD_SOURCE_VIOLATION")
    gate_authority = authority()
    if args.setup_compatibility is not None:
        result = setup_compatibility(args.setup_compatibility)
    else:
        if not (args.case_id and args.post_fsp and args.solver_log and args.output):
            parser.error("case-id, post-fsp, solver-log, and output are required")
        result = combine(args.case_id, args.post_fsp, args.solver_log, gate_authority)
    if args.output:
        write_json(args.output, result)
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
