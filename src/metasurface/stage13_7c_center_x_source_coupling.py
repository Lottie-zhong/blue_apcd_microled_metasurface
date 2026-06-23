from __future__ import annotations

import csv
import json
import math
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from metasurface.stage13_4_center_dipole import (
    CANDIDATE_ID,
    FIELD_MONITOR,
    PATCH_OPTION_ID,
    X_SOURCE,
    Y_SOURCE,
    build_patch_inventory,
    build_setup,
    _component_arrays as stage13_4_component_arrays,
    load_approved_plan,
    lp_metrics_from_fields,
    resolved_setup,
)
from metasurface.stage13_5_order_diagnosis import (
    ORDER_CENTERS,
    TARGET_UX,
    angular_distance_deg,
    cone_rows,
    direction_grid,
    intensity_components,
    peak_rows,
    save_map,
)


OUTPUT_DIR_NAME = "stage13_7c_lp_center_x_source_coupling"
SHIFT_CANDIDATES_NM = [-100.0, -75.0, -50.0, -25.0, 25.0, 50.0, 75.0, 100.0]
NORMAL_CONES = [5.0, 10.0, 20.0]

SHIFT_FIELDS = ["shift_x_nm", "nearest_pillar_distance_nm", "nearest_pillar_phase", "nearest_pillar_role", "nearest_dimer_phase", "safe_for_case3", "selection_note"]
CASE_FIELDS = ["case_id", "candidate_id", "patch_option_id", "source_x_nm", "source_y_nm", "source_z_nm", "cone_deg", "target_LP_power", "leakage_LP_power", "LP_fraction", "target_to_leakage_ratio", "total_vector_power", "farfield_grid", "simulation_time_fs", "extraction_status", "runtime_minutes", "status", "notes"]
ORDER_FIELDS = ["case_id", "order_id", "order_center_ux", "order_center_uy", "cone_deg", "target_LP_power", "leakage_LP_power", "LP_fraction", "target_to_leakage_ratio", "total_vector_power", "source_x_nm", "source_y_nm", "source_z_nm", "status", "notes"]
PEAK_FIELDS = ["case_id", "peak_ux", "peak_uy", "peak_theta_x_deg", "peak_theta_y_deg", "peak_polar_angle_deg", "nearest_order", "distance_to_plus_target_deg", "distance_to_minus_target_deg", "within_3deg_plus_target", "peak_value", "source_x_nm", "source_y_nm", "source_z_nm", "status", "notes"]


def write_csv(path: Path, rows: Iterable[dict[str, object]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def central_dimer_centers(layout_rows: Sequence[dict[str, str]]) -> list[dict[str, object]]:
    period = float(layout_rows[0]["supercell_period_lambda_nm"])
    return [{"phase": int(float(row["phase_bin_deg"])), "x": float(row["supercell_center_x_nm"]) - period / 2.0, "y": float(row["supercell_center_y_nm"])} for row in layout_rows]


def build_shift_candidates(inventory: Sequence[dict[str, object]], layout_rows: Sequence[dict[str, str]]) -> list[dict[str, object]]:
    dimers = central_dimer_centers(layout_rows)
    baseline_nearest = min(math.hypot(float(item["x_nm"]), float(item["y_nm"])) for item in inventory)
    central_left = next(item for item in dimers if item["phase"] == 120)
    central_right = next(item for item in dimers if item["phase"] == 180)
    rows = []
    for shift in SHIFT_CANDIDATES_NM:
        nearest_pillar = min(inventory, key=lambda item: math.hypot(float(item["x_nm"]) - shift, float(item["y_nm"])))
        nearest_distance = math.hypot(float(nearest_pillar["x_nm"]) - shift, float(nearest_pillar["y_nm"]))
        nearest_dimer = min(dimers, key=lambda item: math.hypot(float(item["x"]) - shift, float(item["y"])))
        remains_between = float(central_left["x"]) < shift < float(central_right["x"])
        safe = remains_between and nearest_distance > baseline_nearest + 1e-6
        rows.append({
            "shift_x_nm": shift, "nearest_pillar_distance_nm": nearest_distance,
            "nearest_pillar_phase": nearest_pillar["phase_bin_deg"], "nearest_pillar_role": nearest_pillar["role"],
            "nearest_dimer_phase": nearest_dimer["phase"], "safe_for_case3": safe,
            "selection_note": "safe improvement over x=0 baseline" if safe else "does not improve minimum pillar distance or leaves central region",
        })
    safe_rows = [row for row in rows if row["safe_for_case3"]]
    if safe_rows:
        selected = max(safe_rows, key=lambda row: float(row["nearest_pillar_distance_nm"]))
        selected["selection_note"] = "selected: maximum nearest-pillar distance among safe central-region candidates"
    return rows


def selected_shift(rows: Sequence[dict[str, object]]) -> float | None:
    selected = [row for row in rows if str(row["selection_note"]).startswith("selected:")]
    return float(selected[0]["shift_x_nm"]) if len(selected) == 1 else None


def configure_x_case(fdtd: Any, case: dict[str, object], setup: dict[str, object]) -> list[str]:
    for name, enabled in ((X_SOURCE, 1), (Y_SOURCE, 0)):
        fdtd.select(name); fdtd.set("enabled", enabled)
    fdtd.select(X_SOURCE)
    fdtd.set("x", float(case["source_x_nm"]) * 1e-9)
    fdtd.set("y", float(case["source_y_nm"]) * 1e-9)
    fdtd.set("z", float(case["source_z_nm"]) * 1e-9)
    fdtd.set("theta", 90.0); fdtd.set("phi", 0.0)
    errors: list[str] = []
    for name, expected in ((X_SOURCE, 1), (Y_SOURCE, 0)):
        try:
            actual = int(round(float(fdtd.getnamed(name, "enabled"))))
            if actual != expected: errors.append(f"{name}.enabled={actual}, expected {expected}")
        except Exception as exc: errors.append(f"cannot verify {name}: {type(exc).__name__}: {exc}")
    for prop in ("x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc"):
        actual = str(fdtd.getnamed("FDTD", prop)).strip().upper()
        if actual != "PML": errors.append(f"FDTD {prop}={actual}, expected PML")
    return errors


def extract_fields(fdtd: Any, setup: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    grid = int(setup["farfield_grid"])
    vector = fdtd.farfieldvector3d(FIELD_MONITOR, 1, grid, grid)
    ux = fdtd.farfieldux(FIELD_MONITOR, 1, grid, grid)
    uy = fdtd.farfielduy(FIELD_MONITOR, 1, grid, grid)
    ex, ey, ez, vector_debug = stage13_4_component_arrays(vector)
    xx, yy = direction_grid(ux, uy, ex.shape)
    maps = intensity_components(ex, ey, ez)
    normal = lp_metrics_from_fields(ex, ey, ez, ux, uy, NORMAL_CONES)
    return {"ex": ex, "ey": ey, "ez": ez, "xx": xx, "yy": yy, "maps": maps, "normal": normal}, {"vector": vector_debug, "ux_shape": list(np.asarray(ux).shape), "uy_shape": list(np.asarray(uy).shape), "raw_arrays_saved": False}


def run_case(lumapi: Any, runtime: Any, setup_fsp: Path, output_dir: Path, setup: dict[str, object], case: dict[str, object], show_gui: bool = False) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object], dict[str, object]]:
    case_id = str(case["case_id"]); fsp_path = output_dir / "_saved_fsp" / f"stage13_7c_{case_id}.fsp"
    state: dict[str, object] = {"case_id": case_id, "fsp_path": str(fsp_path), "lifecycle": []}
    fdtd = None; start = time.perf_counter()
    try:
        fdtd = lumapi.FDTD(hide=(not show_gui) and runtime.hide_gui)
        fdtd.setresource("FDTD", 1, "processes", str(int(setup["solver_processes"])))
        fdtd.load(str(setup_fsp.resolve())); state["lifecycle"].append("load_setup")
        errors = configure_x_case(fdtd, case, setup); state["preflight_errors"] = errors
        if errors: raise RuntimeError("preflight failed: " + " | ".join(errors))
        fdtd.save(str(fsp_path.resolve())); state["lifecycle"].append("save_configured_case")
        fdtd.run(); state["lifecycle"].append("run")
        fdtd.save(str(fsp_path.resolve())); state["lifecycle"].append("save_with_results")
        fields, debug = extract_fields(fdtd, setup); state["lifecycle"].append("extract_complex_vector")
        elapsed = (time.perf_counter() - start) / 60.0
        normal_rows = [{
            "case_id": case_id, "candidate_id": CANDIDATE_ID, "patch_option_id": PATCH_OPTION_ID,
            "source_x_nm": case["source_x_nm"], "source_y_nm": case["source_y_nm"], "source_z_nm": case["source_z_nm"],
            "cone_deg": metric["cone_deg"], "target_LP_power": metric["target_LP_power"], "leakage_LP_power": metric["leakage_LP_power"],
            "LP_fraction": metric["LP_fraction"], "target_to_leakage_ratio": metric["target_to_leakage_ratio"], "total_vector_power": metric["total_cone_power"],
            "farfield_grid": setup["farfield_grid"], "simulation_time_fs": setup["simulation_time_fs"], "extraction_status": "complex_vector_ok",
            "runtime_minutes": elapsed, "status": "ok", "notes": "x dipole only; Ez excluded from LP projection and included in total vector power",
        } for metric in fields["normal"]]
        orders = cone_rows(case_id, fields["maps"], fields["xx"], fields["yy"])
        order_rows = [{
            "case_id": case_id, "order_id": row["order_id"], "order_center_ux": row["order_center_ux"], "order_center_uy": row["order_center_uy"],
            "cone_deg": row["cone_deg"], "target_LP_power": row["target_LP_power"], "leakage_LP_power": row["leakage_LP_power"], "LP_fraction": row["LP_fraction"],
            "target_to_leakage_ratio": row["target_to_leakage_ratio"], "total_vector_power": row["total_vector_power"], "source_x_nm": case["source_x_nm"],
            "source_y_nm": case["source_y_nm"], "source_z_nm": case["source_z_nm"], "status": "ok", "notes": row["notes"],
        } for row in orders]
        ex_peak = next(row for row in peak_rows(case_id, fields["maps"], fields["xx"], fields["yy"]) if row["component"] == "Ex_target")
        peak = {
            "case_id": case_id, "peak_ux": ex_peak["peak_ux"], "peak_uy": ex_peak["peak_uy"], "peak_theta_x_deg": ex_peak["peak_theta_x_deg"],
            "peak_theta_y_deg": ex_peak["peak_theta_y_deg"], "peak_polar_angle_deg": ex_peak["peak_polar_angle_deg"], "nearest_order": ex_peak["nearest_expected_order"],
            "distance_to_plus_target_deg": angular_distance_deg(float(ex_peak["peak_ux"]), float(ex_peak["peak_uy"]), TARGET_UX, 0.0),
            "distance_to_minus_target_deg": angular_distance_deg(float(ex_peak["peak_ux"]), float(ex_peak["peak_uy"]), -TARGET_UX, 0.0),
            "within_3deg_plus_target": angular_distance_deg(float(ex_peak["peak_ux"]), float(ex_peak["peak_uy"]), TARGET_UX, 0.0) <= 3.0,
            "peak_value": ex_peak["peak_value"], "source_x_nm": case["source_x_nm"], "source_y_nm": case["source_y_nm"], "source_z_nm": case["source_z_nm"],
            "status": "ok", "notes": "global Ex^2 peak on numeric farfieldux/farfielduy grid",
        }
        save_map(output_dir / f"{case_id}_Ex2_map.png", f"{case_id}: Ex target", fields["maps"]["Ex_target"], fields["xx"], fields["yy"], ex_peak)
        ey_peak = next(row for row in peak_rows(case_id, fields["maps"], fields["xx"], fields["yy"]) if row["component"] == "Ey_leakage")
        save_map(output_dir / f"{case_id}_Ey2_map.png", f"{case_id}: Ey leakage", fields["maps"]["Ey_leakage"], fields["xx"], fields["yy"], ey_peak)
        state.update({"status": "ok", "runtime_minutes": elapsed, "extraction_debug": debug})
        return normal_rows, order_rows, peak, state
    except Exception as exc:
        state.update({"status": "failed", "error": f"{type(exc).__name__}: {exc}", "runtime_minutes": (time.perf_counter() - start) / 60.0})
        return [], [], {"case_id": case_id, "status": "failed", "notes": state["error"]}, state
    finally:
        if fdtd is not None:
            try: fdtd.close()
            except Exception: pass


def reproducibility_check(case_rows: Sequence[dict[str, object]], peak: dict[str, object], baseline_case_rows: Sequence[dict[str, str]], baseline_peaks: Sequence[dict[str, str]]) -> dict[str, object]:
    baseline = [row for row in baseline_case_rows if row["case_id"] == "center_x" and row["status"] == "ok"]
    lp_deltas = []; power_rel = []
    for row in case_rows:
        ref = next(item for item in baseline if abs(float(item["cone_deg"]) - float(row["cone_deg"])) < 1e-9)
        lp_deltas.append(abs(float(row["LP_fraction"]) - float(ref["LP_fraction"])))
        denom = max(abs(float(ref["target_LP_power"])), 1e-30)
        power_rel.append(abs(float(row["target_LP_power"]) - float(ref["target_LP_power"])) / denom)
    ref_peak = next(row for row in baseline_peaks if row["case_id"] == "center_x" and row["component"] == "Ex_target")
    peak_grid_delta = math.hypot(float(peak["peak_ux"]) - float(ref_peak["peak_ux"]), float(peak["peak_uy"]) - float(ref_peak["peak_uy"]))
    passed = max(lp_deltas) <= 0.02 and max(power_rel) <= 0.05 and peak_grid_delta <= 0.03
    return {"passed": passed, "max_abs_lp_fraction_delta": max(lp_deltas), "max_relative_target_power_delta": max(power_rel), "peak_grid_delta": peak_grid_delta}


def plus_order_power(order_rows: Sequence[dict[str, object]], case_id: str, cone: float = 5.0) -> float:
    return float(next(row for row in order_rows if row["case_id"] == case_id and row["order_id"] == "plus_target_order" and float(row["cone_deg"]) == cone)["target_LP_power"])


def bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def mechanism_summary(cases: Sequence[dict[str, object]], case_rows: Sequence[dict[str, object]], order_rows: Sequence[dict[str, object]], peaks: Sequence[dict[str, object]], states: dict[str, object], repeat_check: dict[str, object] | None, shift: float | None) -> dict[str, object]:
    good_peaks = [row for row in peaks if row.get("status") == "ok"]
    restored = any(bool_value(row["within_3deg_plus_target"]) for row in good_peaks)
    depth_sensitive = False; local_bias = False
    if {row["case_id"] for row in good_peaks} >= {"center_x_repeat", "center_mid_120_180_x"}:
        base = next(row for row in good_peaks if row["case_id"] == "center_x_repeat")
        deep = next(row for row in good_peaks if row["case_id"] == "center_mid_120_180_x")
        depth_sensitive = float(deep["distance_to_plus_target_deg"]) < float(base["distance_to_plus_target_deg"]) and plus_order_power(order_rows, "center_mid_120_180_x") > plus_order_power(order_rows, "center_x_repeat")
    if shift is not None and {row["case_id"] for row in good_peaks} >= {"center_x_repeat", "source_shift_to_cell_mid_x"}:
        base = next(row for row in good_peaks if row["case_id"] == "center_x_repeat")
        shifted = next(row for row in good_peaks if row["case_id"] == "source_shift_to_cell_mid_x")
        peak_change = angular_distance_deg(float(base["peak_ux"]), float(base["peak_uy"]), float(shifted["peak_ux"]), float(shifted["peak_uy"]))
        power_change = abs(plus_order_power(order_rows, "source_shift_to_cell_mid_x") / plus_order_power(order_rows, "center_x_repeat") - 1.0)
        local_bias = peak_change >= 3.0 or power_change >= 0.20
    all_completed = all(states.get(str(case["case_id"]), {}).get("status") == "ok" for case in cases)
    insufficient = all_completed and not restored
    recommendation = "Stage13-7B: tiny A_small finite-patch plane-wave sanity FDTD with the same +z complex-vector extraction" if insufficient else ("Review restored-steering case before any further source study" if restored else "Stop and diagnose failed setup/extraction or repeat reproducibility")
    return {"repeat_reproduced": bool(repeat_check and repeat_check["passed"]), "source_coupling_can_restore_steering": restored, "source_depth_sensitivity": depth_sensitive, "source_center_local_bias_confirmed": local_bias, "local_source_correction_not_sufficient": insufficient, "all_selected_cases_completed": all_completed, "recommendation": recommendation}


def build_report(cases: Sequence[dict[str, object]], shifts: Sequence[dict[str, object]], case_rows: Sequence[dict[str, object]], order_rows: Sequence[dict[str, object]], peaks: Sequence[dict[str, object]], summary: dict[str, object], repeat: dict[str, object] | None) -> str:
    selected = next((row for row in shifts if str(row["selection_note"]).startswith("selected:")), None)
    lines = ["# Stage13-7C LP center_x controlled source-coupling diagnostic", "", "## Scope", "", "- Only x-oriented dipoles were run; no center_y, +/-q, DBR/RCLED, geometry change, optimization, or x-y sweep.", "- A_small remains 3 x 19 tiles (342 dimers / 684 nanopillars), +z emission/monitor, 450 nm, grid 101.", "- Complex Ex/Ey/Ez was required; Ez is excluded from LP projection and included only in total vector power.", "", "## Case selection", ""]
    for case in cases: lines.append(f"- `{case['case_id']}`: source=({case['source_x_nm']}, {case['source_y_nm']}, {case['source_z_nm']}) nm; {case['purpose']}")
    if selected: lines.append(f"- Case 3 selected shift: {selected['shift_x_nm']} nm; nearest-pillar distance {float(selected['nearest_pillar_distance_nm']):.6f} nm; {selected['selection_note']}.")
    lines += ["", "## Repeat gate", "", f"- center_x_repeat reproduced Stage13-4: `{summary['repeat_reproduced']}`.", f"- Repeat comparison: `{json.dumps(repeat or {}, ensure_ascii=False)}`.", "", "## Peak results", "", "| case | peak ux | peak uy | distance to +target (deg) | nearest order |", "| --- | ---: | ---: | ---: | --- |"]
    for row in peaks: lines.append(f"| {row['case_id']} | {row.get('peak_ux','')} | {row.get('peak_uy','')} | {row.get('distance_to_plus_target_deg','')} | {row.get('nearest_order','')} |")
    lines += ["", "## Normal-cone LP fraction", "", "| case | cone (deg) | LP_fraction |", "| --- | ---: | ---: |"]
    for row in case_rows: lines.append(f"| {row['case_id']} | {row['cone_deg']} | {row['LP_fraction']} |")
    lines += ["", "## Resolved +target comparison", "", "| case | +target Ex power, 5 deg | peak distance to +target (deg) |", "| --- | ---: | ---: |"]
    for row in peaks:
        if row.get("status") == "ok": lines.append(f"| {row['case_id']} | {plus_order_power(order_rows, str(row['case_id']))} | {row['distance_to_plus_target_deg']} |")
    lines += ["", "## Mechanism classification", "", f"- source_coupling_can_restore_steering: `{summary['source_coupling_can_restore_steering']}`.", f"- source_depth_sensitivity: `{summary['source_depth_sensitivity']}`.", f"- source_center_local_bias_confirmed: `{summary['source_center_local_bias_confirmed']}`.", f"- local_source_correction_not_sufficient: `{summary['local_source_correction_not_sufficient']}`.", "", "## Single recommended next step", "", f"**{summary['recommendation']}**", "", "Do not run +/-q or add DBR/RCLED before that separately authorized step.", "", "## Jones/APCD evidence boundary", "", "- These are finite-patch dipole angular-power diagnostics, not a new incident-wave order-resolved J_xy/APCD measurement.", "- No alpha/beta conversion or t_{alpha*<-alpha}^order claim is made.", ""]
    return "\n".join(lines)


def build_extraction_notes(states: dict[str, object], operational_note: str = "") -> str:
    return f"""# Stage13-7C extraction notes

- Lifecycle per case: load saved setup, configure x dipole, preflight, save configured case, run, save with results, extract complex vector, close.
- API: farfieldvector3d + farfieldux + farfielduy on `{FIELD_MONITOR}`.
- No intensity-only farfield3d LP inference.
- Normal cones: {NORMAL_CONES} deg; order-centered cones: 3, 5, 10 deg around zero and +/-target.
- Ez excluded from LP projection; included in total vector power.
- Raw complex arrays saved: False.
- Operational note: {operational_note or 'none'}
- Runtime states: `{json.dumps(states, ensure_ascii=False)}`.
"""
