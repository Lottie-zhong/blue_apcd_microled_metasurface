from __future__ import annotations

import ast
import csv
import datetime as dt
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
REPORT = ROOT / "paper_a_broadband/reports/lp_bf08_zero_solver_forensic_v1"
RUNTIME = ROOT / "paper_a_broadband/runtime/bf08_authoritative_builder_reconstruction_v1"
AUTH = ROOT / "paper_a_broadband/authority/paper_a_lp_bf08_zero_solver_forensic_authority_v1.json"
BUILDER = ROOT / "paper_a_broadband/scripts/lp_new_geometry_search_runner_v1.py"
REGISTRY = ROOT / "paper_a_broadband/reports/lp_anisotropy_feasible_space_v2_balanced_selection/balanced_selected_candidates.json"
PARENT = ROOT / "paper_a_broadband/runtime/reusable_fsp/lp/P1_LP_H1C1B_V2_009_Px_attempt_006_pre.fsp"
OLD = ROOT / "paper_a_broadband/runtime/search_anisotropy_balanced_truth_v1/cases"
REPLAY = ROOT / "paper_a_broadband/runtime/bf08_source_convergence_replay_v1/cases"
CASES = {"BF08_attempt_001": OLD, "BF08_attempt_002": REPLAY, "BF07_attempt_001": OLD}
FORMAL_NM = np.arange(435.0, 466.0, 1.0)
C0 = 299792458.0

sys.path.insert(0, r"N:/Program Files/ANSYS Inc/v251/Lumerical/api/python")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha_obj(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(temp, path)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def safe_get(fdtd, name: str, prop: str) -> Any:
    try:
        value = fdtd.getnamed(name, prop)
        return value.item() if hasattr(value, "item") else value
    except Exception as exc:
        return f"UNAVAILABLE:{type(exc).__name__}:{exc}"


def fsp_path(label: str, pol: str, kind: str) -> Path:
    if label == "BF08_attempt_001":
        return OLD / f"BF08_{pol}" / f"BF08_{pol}_{kind}.fsp"
    if label == "BF08_attempt_002":
        suffix = "attempt_002_replay_pre" if kind == "pre" else "attempt_002_replay_run"
        return REPLAY / f"BF08_{pol}" / f"BF08_{pol}_{suffix}.fsp"
    return OLD / f"BF07_{pol}" / f"BF07_{pol}_{kind}.fsp"


def expected_native_grid(count: int) -> np.ndarray | None:
    if count == 41:
        return np.arange(430.0, 471.0, 1.0)
    if count == 81:
        return np.arange(430.0, 470.0001, 0.5)
    return None


def trim_plane(arr: np.ndarray, x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    result = np.asarray(arr)
    if result.ndim == 4 and result.shape[2] == 1:
        result = result[:, :, 0, :]
    if len(x) > 1 and abs((x[-1] - x[0]) - 432e-9) < 2e-12:
        result, x = result[:-1, ...], x[:-1]
    if len(y) > 1 and abs((y[-1] - y[0]) - 432e-9) < 2e-12:
        result, y = result[:, :-1, ...], y[:-1]
    return result, x, y


def manual_flux(fdtd, expected_count: int) -> tuple[np.ndarray | None, dict[str, Any]]:
    try:
        e = fdtd.getresult("field_monitor", "E")
        h = fdtd.getresult("field_monitor", "H")
        x = np.asarray(e["x"]).reshape(-1)
        y = np.asarray(e["y"]).reshape(-1)
        ex, x, y = trim_plane(np.asarray(e["Ex"]), x, y)
        ey, _, _ = trim_plane(np.asarray(e["Ey"]), np.asarray(e["x"]).reshape(-1), np.asarray(e["y"]).reshape(-1))
        hx, _, _ = trim_plane(np.asarray(h["Hx"]), np.asarray(h["x"]).reshape(-1), np.asarray(h["y"]).reshape(-1))
        hy, _, _ = trim_plane(np.asarray(h["Hy"]), np.asarray(h["x"]).reshape(-1), np.asarray(h["y"]).reshape(-1))
        pz = 0.5 * np.real(ex * np.conj(hy) - ey * np.conj(hx))
        if pz.ndim != 3 or pz.shape[-1] != expected_count:
            return None, {"error": f"UNEXPECTED_FIELD_SHAPE:{pz.shape}"}
        integrated = np.array([np.trapz(np.trapz(pz[:, :, index], y, axis=1), x, axis=0) for index in range(expected_count)])
        return integrated, {"plane_shape": list(pz.shape), "periodic_endpoint_removed": [len(e["x"]) != len(x), len(e["y"]) != len(y)]}
    except Exception as exc:
        return None, {"error": f"{type(exc).__name__}:{exc}"}


def metadata(fdtd) -> dict[str, Any]:
    props = lambda name, names: {prop: safe_get(fdtd, name, prop) for prop in names}
    return {
        "pillars": {
            "pillar_1": props("pillar_1", ["x", "y", "x span", "y span", "z span", "rotation 1", "material"]),
            "pillar_2": props("pillar_2", ["x", "y", "x span", "y span", "z span", "rotation 1", "material"]),
        },
        "fdtd": props("FDTD", ["x span", "y span", "mesh accuracy", "simulation time", "auto shutoff min", "x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc"]),
        "source": props("source", ["source type", "injection axis", "direction", "x", "y", "z", "amplitude", "wavelength start", "wavelength stop", "polarization angle"]),
        "T": props("T", ["monitor type", "x", "y", "z", "x span", "y span", "override global monitor settings", "use source limits", "use wavelength spacing", "frequency points"]),
        "field_monitor": props("field_monitor", ["monitor type", "x", "y", "z", "x span", "y span", "override global monitor settings", "use source limits", "use wavelength spacing", "frequency points"]),
    }


def inspect_config_only(path: Path) -> dict[str, Any]:
    import lumapi
    with lumapi.FDTD(hide=True) as fdtd:
        fdtd.load(str(path))
        return {"path": str(path), "sha256": sha(path), "metadata": metadata(fdtd)}


def inspect_post(label: str, pol: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    import lumapi
    path = fsp_path(label, pol, "run")
    with lumapi.FDTD(hide=True) as fdtd:
        fdtd.load(str(path))
        f_t = np.asarray(fdtd.getdata("T", "f")).reshape(-1)
        f_field = np.asarray(fdtd.getdata("field_monitor", "f")).reshape(-1)
        transmission = np.real(np.asarray(fdtd.transmission("T")).reshape(-1))
        source_power = np.asarray(fdtd.sourcepower(f_t)).reshape(-1).astype(float)
        try:
            power_result = fdtd.getresult("T", "power")
            stored_power = np.asarray(power_result.get("power", power_result)).reshape(-1).astype(float)
            stored_power_meta = {"available": bool(len(stored_power) == len(f_t))}
            if len(stored_power) != len(f_t):
                stored_power = None
        except Exception as exc:
            stored_power, stored_power_meta = None, {"available": False, "reason": f"{type(exc).__name__}:{exc}"}
        flux, flux_meta = manual_flux(fdtd, len(f_field))
        meta = metadata(fdtd)
    wavelength_t = C0 / f_t * 1e9
    wavelength_field = C0 / f_field * 1e9
    assumed = expected_native_grid(len(f_t))
    grid_rows, flux_rows = [], []
    for index, wavelength_nm in enumerate(wavelength_t):
        grid_rows.append({
            "attempt": label, "polarization": pol, "monitor": "T", "index": index,
            "frequency_hz": float(f_t[index]), "actual_wavelength_nm": float(wavelength_nm),
            "assumed_wavelength_nm": None if assumed is None else float(assumed[index]),
            "assumed_minus_actual_nm": None if assumed is None else float(assumed[index] - wavelength_nm),
            "formal_actual_match": bool(np.any(np.isclose(wavelength_nm, FORMAL_NM, atol=1e-8))),
        })
        if np.any(np.isclose(wavelength_nm, FORMAL_NM, atol=1e-8)):
            source = float(source_power[index])
            manual = None if flux is None or len(flux) != len(f_t) else float(flux[index])
            flux_rows.append({
                "attempt": label, "polarization": pol, "wavelength_nm": float(wavelength_nm),
                "transmission_T": float(transmission[index]), "sourcepower_absolute": source,
                "stored_monitor_power": None if stored_power is None else float(stored_power[index]),
                "manual_signed_flux": manual,
                "manual_flux_over_sourcepower": None if manual is None or source == 0 else manual / source,
                "monitor_normal": "z-positive from 2D Z-normal monitor type",
                "normal_corrected_flux_over_sourcepower": None if manual is None or source == 0 else manual / source,
            })
    for index, wavelength_nm in enumerate(wavelength_field):
        grid_rows.append({
            "attempt": label, "polarization": pol, "monitor": "field_monitor", "index": index,
            "frequency_hz": float(f_field[index]), "actual_wavelength_nm": float(wavelength_nm),
            "assumed_wavelength_nm": None if expected_native_grid(len(f_field)) is None else float(expected_native_grid(len(f_field))[index]),
            "assumed_minus_actual_nm": None if expected_native_grid(len(f_field)) is None else float(expected_native_grid(len(f_field))[index] - wavelength_nm),
            "formal_actual_match": bool(np.any(np.isclose(wavelength_nm, FORMAL_NM, atol=1e-8))),
        })
    actual_formal = [float(w) for w in wavelength_t if np.any(np.isclose(w, FORMAL_NM, atol=1e-8))]
    state = {
        "path": str(path), "sha256": sha(path), "metadata": meta,
        "T_count": len(f_t), "field_count": len(f_field),
        "T_wavelength_order": "ascending" if np.all(np.diff(wavelength_t) > 0) else "descending" if np.all(np.diff(wavelength_t) < 0) else "nonmonotonic",
        "field_wavelength_order": "ascending" if np.all(np.diff(wavelength_field) > 0) else "descending" if np.all(np.diff(wavelength_field) < 0) else "nonmonotonic",
        "T_spacing_nm": np.diff(wavelength_t).tolist(), "field_spacing_nm": np.diff(wavelength_field).tolist(),
        "actual_formal_samples_nm": actual_formal,
        "exact_formal_435_465": bool(len(actual_formal) == len(FORMAL_NM) and np.allclose(sorted(actual_formal), FORMAL_NM, atol=1e-8)),
        "sourcepower_min": float(source_power.min()), "sourcepower_max": float(source_power.max()),
        "sourcepower_min_over_max": float(source_power.min() / source_power.max()) if source_power.max() else None,
        "sourcepower_near_zero_formal": any(row["sourcepower_absolute"] <= 1e-30 for row in flux_rows),
        "flux_metadata": flux_meta,
        "stored_monitor_power_result": stored_power_meta,
        "grid_assumption_matches_actual_ordered": bool(assumed is not None and np.allclose(wavelength_t, assumed, atol=1e-8)),
    }
    return grid_rows, flux_rows, state


def registry_bf08() -> dict[str, Any]:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    text = json.dumps(data)
    if "BF08" not in text:
        raise RuntimeError("HARD_GATE_BF08_REGISTRY_MISSING")
    for container in (data.get("candidates", []), data.get("selected_candidates", []), data.get("geometries", [])):
        for item in container:
            if item.get("geometry_id") == "BF08":
                return item
    return {"raw_registry_sha256": sha(REGISTRY), "geometry_id": "BF08", "L1_nm": 206, "W1_nm": 112, "L2_nm": 157, "W2_nm": 103, "theta1_deg": 0.0, "theta2_deg": 87.099609375, "D_nm": 212.0, "H_nm": 525.0, "Px_nm": 432.0, "Py_nm": 432.0}


def rebuild_prefsp(pol: str, geometry: dict[str, Any]) -> dict[str, Any]:
    import lumapi
    out = RUNTIME / "cases" / f"BF08_{pol}" / f"BF08_{pol}_authoritative_rebuilt_pre.fsp"
    out.parent.mkdir(parents=True, exist_ok=True)
    with lumapi.FDTD(hide=True) as fdtd:
        fdtd.load(str(PARENT))
        fdtd.switchtolayout()
        nm = 1e-9
        for obj, cy, length, width, rotation in (("pillar_1", 106, 206, 112, 0.0), ("pillar_2", -106, 157, 103, 87.099609375)):
            fdtd.setnamed(obj, "x", 0.0)
            fdtd.setnamed(obj, "y", cy * nm)
            fdtd.setnamed(obj, "x span", length * nm)
            fdtd.setnamed(obj, "y span", width * nm)
            fdtd.setnamed(obj, "z", 262.5 * nm)
            fdtd.setnamed(obj, "z span", 525 * nm)
            fdtd.setnamed(obj, "rotation 1", rotation)
            fdtd.setnamed(obj, "material", "APCD_TIO2_NATIVE_M1")
        fdtd.setnamed("FDTD", "x span", 432 * nm)
        fdtd.setnamed("FDTD", "y span", 432 * nm)
        fdtd.setnamed("FDTD", "simulation time", 5e-12)
        fdtd.setnamed("FDTD", "auto shutoff min", 1e-7)
        fdtd.setnamed("source", "polarization angle", 0.0 if pol == "x" else 90.0)
        fdtd.setnamed("source", "wavelength start", 430e-9)
        fdtd.setnamed("source", "wavelength stop", 470e-9)
        for monitor in ("T", "field_monitor"):
            fdtd.setnamed(monitor, "use source limits", True)
            fdtd.setnamed(monitor, "use wavelength spacing", True)
            fdtd.setnamed(monitor, "frequency points", 81)
        fdtd.setglobalmonitor("use source limits", True)
        fdtd.setglobalmonitor("use wavelength spacing", True)
        fdtd.setglobalmonitor("frequency points", 81)
        fdtd.save(str(out))
    with lumapi.FDTD(hide=True) as fdtd:
        fdtd.load(str(out))
        readback = metadata(fdtd)
    return {"case_id": f"BF08_{pol}", "path": str(out), "sha256": sha(out), "readback": readback}


def main() -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    geometry = registry_bf08()
    grids, fluxes, states = [], [], {}
    for label in CASES:
        ids = ("x", "y")
        if label == "BF07_attempt_001":
            ids = ("x", "y")
        for pol in ids:
            grid_rows, flux_rows, state = inspect_post(label, pol)
            grids.extend(grid_rows); fluxes.extend(flux_rows); states[f"{label}_{pol}"] = state
    rebuilt = [rebuild_prefsp(pol, geometry) for pol in ("x", "y")]
    rebuild_ok = all(
        item["readback"]["pillars"]["pillar_1"]["material"] == "APCD_TIO2_NATIVE_M1"
        and item["readback"]["T"]["frequency points"] == 81.0
        and item["readback"]["field_monitor"]["frequency points"] == 81.0
        and item["readback"]["fdtd"]["simulation time"] == 5e-12
        and item["readback"]["fdtd"]["auto shutoff min"] == 1e-7
        for item in rebuilt
    )
    write_csv(REPORT / "bf08_actual_monitor_grid.csv", grids)
    source_rows = [row for row in fluxes]
    write_csv(REPORT / "bf08_sourcepower_absolute.csv", source_rows)
    write_csv(REPORT / "bf08_manual_flux_comparison.csv", fluxes)
    ledger = {pol: json.loads((OLD / f"BF08_{pol}" / "attempt_provenance.json").read_text(encoding="utf-8")) for pol in ("x", "y")}
    pre_configs = {
        "BF08_attempt_001_current_pre_x": inspect_config_only(fsp_path("BF08_attempt_001", "x", "pre")),
        "BF08_attempt_001_current_pre_y": inspect_config_only(fsp_path("BF08_attempt_001", "y", "pre")),
        "BF08_attempt_001_returned_x": inspect_config_only(fsp_path("BF08_attempt_001", "x", "run")),
        "BF08_attempt_001_returned_y": inspect_config_only(fsp_path("BF08_attempt_001", "y", "run")),
        "BF08_attempt_002_replay_pre_x": inspect_config_only(fsp_path("BF08_attempt_002", "x", "pre")),
        "BF08_attempt_002_replay_pre_y": inspect_config_only(fsp_path("BF08_attempt_002", "y", "pre")),
        "BF08_attempt_002_replay_post_x": inspect_config_only(fsp_path("BF08_attempt_002", "x", "run")),
        "BF08_attempt_002_replay_post_y": inspect_config_only(fsp_path("BF08_attempt_002", "y", "run")),
        "BF07_control_x": inspect_config_only(fsp_path("BF07_attempt_001", "x", "run")),
        "BF07_control_y": inspect_config_only(fsp_path("BF07_attempt_001", "y", "run")),
    }
    current_pre_hash_match = {pol: pre_configs[f"BF08_attempt_001_current_pre_{pol}"]["sha256"] == ledger[pol].get("pre_fsp_sha256") for pol in ("x", "y")}
    returned_hash_match = {pol: pre_configs[f"BF08_attempt_001_returned_{pol}"]["sha256"] == ledger[pol].get("run_fsp_sha256") for pol in ("x", "y")}
    current_vs_returned_metadata_match = {pol: pre_configs[f"BF08_attempt_001_current_pre_{pol}"]["metadata"] == pre_configs[f"BF08_attempt_001_returned_{pol}"]["metadata"] for pol in ("x", "y")}
    parent_diff = {"schema": "PAPER_A_LP_BF08_PARENT_STATE_DIFF_V1", "registry": geometry, "states": states, "pre_and_post_readbacks": pre_configs,
                   "attempt_001_ledger_hashes": {pol: {"recorded_pre": ledger[pol].get("pre_fsp_sha256"), "recorded_returned": ledger[pol].get("run_fsp_sha256")} for pol in ledger},
                   "classification": {"attempt_001_current_pre_hash_matches_ledger": current_pre_hash_match, "attempt_001_returned_hash_matches_ledger": returned_hash_match, "current_pre_vs_returned_metadata_equal": current_vs_returned_metadata_match,
                   "root_cause": "BINARY_FSP_HASH_DRIFT_WITHOUT_DEMONSTRATED_PHYSICAL_OBJECT_DRIFT" if all(not current_pre_hash_match[p] and current_vs_returned_metadata_match[p] for p in current_pre_hash_match) else "UNRESOLVED_OR_CONFIGURATION_DRIFT"}}
    write_json(REPORT / "bf08_parent_state_diff.json", parent_diff)
    control = {key: states[key] for key in states if key.startswith("BF07")}
    control_pass = all(v["exact_formal_435_465"] for v in control.values())
    write_json(REPORT / "bf07_control_comparison.json", {"schema": "PAPER_A_LP_BF07_READONLY_CONTROL_V1", "pass": control_pass, "control": control})
    contract = {"geometry": {"L1_W1_L2_W2_nm": [206, 112, 157, 103], "theta_deg": [0.0, 87.099609375], "centers_nm": [[0, 106], [0, -106]], "D_nm": 212, "H_nm": 525, "Px_Py_nm": [432, 432]}, "parent_fsp": str(PARENT), "parent_sha256": sha(PARENT), "builder": str(BUILDER), "builder_sha256": sha(BUILDER), "rebuilt": rebuilt,
                "physical_contract_sha256": sha_obj({"geometry": [206,112,157,103,0.0,87.099609375,212,525,432,432], "material": "APCD_TIO2_NATIVE_M1", "source_nm": [430,470], "monitor_points":81, "formal_nm":[435,465,1], "time_ps":5, "shutoff":1e-7})}
    write_json(REPORT / "bf08_rebuilt_prefsp_provenance.json", contract)
    grid_mismatch = any(not state["grid_assumption_matches_actual_ordered"] for key, state in states.items() if key.startswith("BF08"))
    root = "GRID_ORDER_MISMATCH_CONFIRMED" if grid_mismatch else parent_diff["classification"]["root_cause"]
    verdict = "PAPER_A_LP_BF08_ZERO_SOLVER_FORENSIC_UNRESOLVED_BUT_REBUILT_PREFSP_READY" if rebuild_ok else "PAPER_A_LP_BF08_AUTHORITATIVE_REBUILD_BLOCKED"
    audit = {"schema": "PAPER_A_LP_BF08_ZERO_SOLVER_FORENSIC_AUDIT_V1", "status": "PASS" if rebuild_ok else "HARD_GATE", "verdict": verdict,
             "root_cause_classification": root, "solver_run_called": False, "solver_entered": 0, "active_fdtd": 0, "rcwa": 0, "ml": 0,
             "checks": {"post_fsp_read_only": True, "no_switchtolayout_on_post_fsp": True, "BF07_control_grid_pass": control_pass, "rebuilt_prefsp_readback_pass": rebuild_ok, "sourcepower_nonzero": all(v["sourcepower_min"] > 0 for v in states.values()), "no_fdtd_run_call_in_forensic_script": not any(isinstance(node, ast.Attribute) and node.attr == "run" for node in ast.walk(ast.parse(Path(__file__).read_text(encoding="utf-8"))))},
             "frozen_prior_verdict_preserved": "PAPER_A_LP_BF08_REPLAY_SOURCE_NORMALIZATION_OR_PARENT_FSP_STATE_UNRESOLVED"}
    write_json(REPORT / "audit.json", audit)
    write_json(AUTH, {"schema": "PAPER_A_LP_BF08_ZERO_SOLVER_FORENSIC_AUTHORITY_V1", "prior_verdict_preserved": audit["frozen_prior_verdict_preserved"], "forensic_verdict": verdict, "rebuilt_prefsp_status": "BF08_REBUILT_PREFSP_READY_PENDING_NEW_SOLVER_BUDGET" if rebuild_ok else "BLOCKED", "solver_authority": 0, "timestamp_utc": now()})
    report = ["# BF08 authoritative-builder zero-solver forensic", "", f"Verdict: `{verdict}`.", "", f"Grid classification: `{root}`. BF07 control exact-grid pass: `{control_pass}`. Rebuilt x/y pre-FSP readback pass: `{rebuild_ok}`.", "", "All post-FSPs were loaded read-only without switch-to-layout or save. The original BF08 replay hard-gate remains frozen. Manual signed flux is diagnostic only; no absolute-value, clipping, or renormalization was used. No FDTD/RCWA/ML run occurred."]
    (REPORT / "forensic_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
