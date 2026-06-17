from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from metasurface.stage12_8_xgrad_refinement import (
    audit_variant,
    bool_from,
    flt,
    metric_ratio,
    source_to_layout_row,
)
from metasurface.stage12_k6_fdtd import (
    ORDER_POWER_FIELDS,
    RESULT_FIELDS,
    Stage12Paths,
    order_power,
    read_csv_rows,
    run_one_fdtd,
    write_csv_rows,
)
from metasurface.stage12_k6_layout import GEOMETRY_AUDIT_FIELDS, LAYOUT_FIELDS

OUTPUT_DIR_NAME = "stage12_11b_h500_lp_k6_shifted_tuple_fdtd"
DELTA_DEG = 1.0
EPS = 1e-12
BASELINE = {"source":"Stage12-2 official x-gradient baseline","variant_id":"stage12_2_official_baseline","x_LP_target_plus1_power":0.35782382585849376,"y_LP_target_plus1_leakage":0.03070098955871727,"target_order_selectivity_ratio":11.655123531902342,"steering_angle_deg":10.0000000055,"x_LP_dominant_order":"+1","y_LP_dominant_leakage_order":"+2","x_LP_order_contrast":4.4245556829}
STAGE12_8_BEST = {"source":"Stage12-8 best","variant_id":"variant_001_sub_bin240","x_LP_target_plus1_power":0.3649581358292434,"y_LP_target_plus1_leakage":0.029614335772574624,"target_order_selectivity_ratio":12.323698178880834,"steering_angle_deg":10.000000005514977}
STAGE12_9_BEST = {"source":"Stage12-9 best","variant_id":"stage12_9_best","x_LP_target_plus1_power":0.35322919818880544,"y_LP_target_plus1_leakage":0.0286169367800548,"target_order_selectivity_ratio":12.34597729075494,"steering_angle_deg":10.000000005514977}
SHIFTED_LAYOUT_FIELDS = list(LAYOUT_FIELDS) + ["phase_origin_delta_deg","shifted_target_phase_deg","actual_common_phase_deg","phase_error_deg","Tx","leakage","conversion_to_leakage_ratio","matrix_error","estimated_leakage","geometry_family","tolerance_mode"]
PHASE_FIELDS = ["supercell_index","nominal_phase_bin_deg","shifted_target_phase_deg","candidate_id","geometry_family","actual_common_phase_deg","phase_error_deg","Tx","leakage","conversion_to_leakage_ratio","matrix_error","estimated_leakage","tolerance_mode"]
RUN_MATRIX_FIELDS = ["run_id","polarization","gradient_axis","target_order","selected_channel","wavelength_nm","supercell_period_nm","expected_theta_deg","status","notes"]
SELECTIVITY_FIELDS = ["metric","value","notes"]
COMPARE_FIELDS = ["source","variant_id","x_LP_target_plus1_power","y_LP_target_plus1_leakage","target_order_selectivity_ratio","steering_angle_deg","x_LP_dominant_order","y_LP_dominant_leakage_order","replacement_worthy"]

@dataclass(frozen=True)
class Stage12_11BPaths:
    best_tuple_csv: Path
    baseline_layout_csv: Path
    output_dir: Path
    fdtd_work_dir: Path

def expected_theta_deg(wavelength_nm: float, period_nm: float) -> float:
    return math.degrees(math.asin(max(-1.0, min(1.0, wavelength_nm / period_nm))))

def load_best_tuple(path: Path) -> list[dict[str, str]]:
    rows = sorted(read_csv_rows(path), key=lambda row: int(float(row["slot_index"])))
    if len(rows) != 6:
        raise ValueError(f"Stage12-11B requires six tuple rows; got {len(rows)}")
    targets = [flt(row["target_phase_deg"]) for row in rows]
    expected = [(DELTA_DEG + 60.0 * i) % 360.0 for i in range(6)]
    if any(abs(a - b) > 1e-6 for a, b in zip(targets, expected)):
        raise ValueError(f"Unexpected shifted target sequence {targets}; expected {expected}")
    return rows

def resolve_source_plan_rows(repo_root: Path, candidate_ids: Sequence[str]) -> dict[str, dict[str, str]]:
    pending = set(candidate_ids)
    found: dict[str, dict[str, str]] = {}
    for path in sorted((repo_root / "outputs").rglob("*.csv")):
        name = path.name.lower()
        if not any(token in name for token in ("plan", "candidate_plan")):
            continue
        for row in read_csv_rows(path):
            row_id = row.get("dimer_case_id") or row.get("dimer_patch_id") or row.get("candidate_id") or ""
            if row_id in pending:
                row = dict(row)
                row["_source_plan_file"] = path.relative_to(repo_root).as_posix()
                found[row_id] = row
                pending.remove(row_id)
        if not pending:
            break
    if pending:
        raise FileNotFoundError(f"Could not resolve source plan rows for: {sorted(pending)}")
    return found

def build_shifted_tuple_layout(repo_root: Path, baseline_layout_csv: Path, best_tuple_csv: Path) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    baseline_rows = read_csv_rows(baseline_layout_csv)
    tuple_rows = load_best_tuple(best_tuple_csv)
    if len(baseline_rows) != 6:
        raise ValueError(f"Expected six baseline layout slots; got {len(baseline_rows)}")
    sources = resolve_source_plan_rows(repo_root, [row["candidate_id"] for row in tuple_rows])
    layout_rows: list[dict[str, object]] = []
    phase_rows: list[dict[str, object]] = []
    for index, tuple_row in enumerate(tuple_rows):
        base = baseline_rows[index]
        candidate_id = tuple_row["candidate_id"]
        layout = source_to_layout_row(base, {"candidate_id": candidate_id, "source_stage": "Stage12-11A_shifted_tuple", "source_file": tuple_row.get("source_file", "")}, sources[candidate_id])
        layout.update({"phase_origin_delta_deg": DELTA_DEG,"shifted_target_phase_deg": tuple_row["target_phase_deg"],"actual_common_phase_deg": tuple_row["phase_mod_360_deg"],"phase_error_deg": tuple_row["phase_error_deg"],"Tx": tuple_row["Tx"],"leakage": tuple_row.get("leakage", ""),"conversion_to_leakage_ratio": tuple_row["ratio"],"matrix_error": tuple_row["matrix_error"],"estimated_leakage": tuple_row["estimated_leakage"],"geometry_family": tuple_row["geometry_family"],"tolerance_mode": tuple_row["tolerance_mode"]})
        layout_rows.append(layout)
        phase_rows.append({"supercell_index": index,"nominal_phase_bin_deg": base["phase_bin_deg"],"shifted_target_phase_deg": tuple_row["target_phase_deg"],"candidate_id": candidate_id,"geometry_family": tuple_row["geometry_family"],"actual_common_phase_deg": tuple_row["phase_mod_360_deg"],"phase_error_deg": tuple_row["phase_error_deg"],"Tx": tuple_row["Tx"],"leakage": tuple_row.get("leakage", ""),"conversion_to_leakage_ratio": tuple_row["ratio"],"matrix_error": tuple_row["matrix_error"],"estimated_leakage": tuple_row["estimated_leakage"],"tolerance_mode": tuple_row["tolerance_mode"]})
    geometry_rows, aggregate = audit_variant(layout_rows)
    return layout_rows, geometry_rows, phase_rows, aggregate

def build_run_matrix(layout_rows: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    first = layout_rows[0]
    wavelength = flt(first["lambda_nm"])
    period = flt(first["supercell_period_lambda_nm"])
    theta = expected_theta_deg(wavelength, period)
    rows = []
    for pol in ("x", "y"):
        rows.append({"run_id": f"stage12_11b_shifted_tuple_{pol}_lp","polarization": pol,"gradient_axis": "x","target_order": "x-order +1","selected_channel": "x-LP" if pol == "x" else "blocked y-LP leakage channel","wavelength_nm": wavelength,"supercell_period_nm": period,"expected_theta_deg": theta,"status": "planned","notes": "Stage12-11B shifted phase-origin K=6 plane-wave validation; no sweep"})
    return rows

def order_label(value: object) -> str:
    try:
        return f"{int(round(float(value))):+d}"
    except Exception:
        return ""

def compute_metrics(x_result: dict[str, object], y_result: dict[str, object], x_orders: Sequence[dict[str, object]], y_orders: Sequence[dict[str, object]], geometry_audit: dict[str, object]) -> dict[str, object]:
    x_power = flt(x_result.get("target_plus1_power"), 0.0)
    y_leakage = flt(y_result.get("target_plus1_power"), 0.0)
    x_total = flt(x_result.get("total_transmission"), 0.0)
    y_total = flt(y_result.get("total_transmission"), 0.0)
    return {"variant_id": "stage12_11b_shifted_delta1_tuple","x_LP_target_plus1_power": x_power,"y_LP_target_plus1_leakage": y_leakage,"target_order_selectivity_ratio": metric_ratio(x_power, y_leakage),"steering_angle_deg": flt(x_result.get("dominant_theta_deg")),"x_LP_dominant_order": order_label(x_result.get("dominant_order_n")),"y_LP_dominant_leakage_order": order_label(y_result.get("dominant_order_n")),"x_LP_order_contrast": flt(x_result.get("order_contrast_plus1_vs_next")),"total_transmission_selectivity_ratio": x_total / max(y_total, EPS) if y_total > 0 else math.inf,"y_leakage_fraction_in_target_order": y_leakage / max(y_total, EPS) if y_total > 0 else math.nan,"geometry_legal": bool_from(geometry_audit.get("geometry_legal")),"minimum_clearance_nm": flt(geometry_audit.get("minimum_clearance_nm")),"minimum_neighbor_clearance_nm": flt(geometry_audit.get("minimum_neighbor_clearance_nm")),"x_zero_order_power": order_power(x_orders, 0),"x_minus1_order_power": order_power(x_orders, -1),"y_zero_order_power": order_power(y_orders, 0),"y_minus1_order_power": order_power(y_orders, -1)}

def replacement_decision(metrics: dict[str, object], baseline: dict[str, object] = BASELINE) -> dict[str, object]:
    x_power = flt(metrics["x_LP_target_plus1_power"])
    y_leak = flt(metrics["y_LP_target_plus1_leakage"])
    ratio = flt(metrics["target_order_selectivity_ratio"])
    base_y = flt(baseline["y_LP_target_plus1_leakage"])
    base_ratio = flt(baseline["target_order_selectivity_ratio"])
    criterion_ratio15 = ratio >= 15.0 and y_leak < base_y
    criterion_leak20 = y_leak <= 0.8 * base_y and x_power >= 0.30
    criterion_ratio25 = ratio >= 1.25 * base_ratio
    preferred = ratio >= 20.0 and y_leak <= 0.015 and x_power >= 0.25
    return {"criterion_ratio_ge15_and_leak_below_baseline": criterion_ratio15,"criterion_leakage_drop_ge20pct_with_x_power_ge030": criterion_leak20,"criterion_ratio_improves_ge25pct": criterion_ratio25,"replacement_worthy": criterion_ratio15 or criterion_leak20 or criterion_ratio25,"hard_preferred_target_met": preferred}

def selectivity_rows(metrics: dict[str, object], decision: dict[str, object]) -> list[dict[str, object]]:
    rows = [("x_LP_target_plus1_power", metrics["x_LP_target_plus1_power"], "selected x-LP x-order +1 source-normalized power"),("y_LP_target_plus1_leakage", metrics["y_LP_target_plus1_leakage"], "blocked y-LP x-order +1 leakage"),("target_order_selectivity_ratio", metrics["target_order_selectivity_ratio"], "x +1 power divided by y +1 leakage"),("steering_angle_deg", metrics["steering_angle_deg"], "dominant x-LP steering angle in x-z plane"),("x_LP_dominant_order", metrics["x_LP_dominant_order"], "x-gradient diffraction order"),("y_LP_dominant_leakage_order", metrics["y_LP_dominant_leakage_order"], "dominant blocked-channel leakage order"),("x_LP_order_contrast", metrics["x_LP_order_contrast"], "+1 order contrast against next order"),("total_transmission_selectivity_ratio", metrics["total_transmission_selectivity_ratio"], "x total transmitted power divided by y total transmitted power"),("y_leakage_fraction_in_target_order", metrics["y_leakage_fraction_in_target_order"], "fraction of y transmission in target +1 order"),("geometry_legal", metrics["geometry_legal"], "shifted tuple geometry audit result"),("minimum_clearance_nm", metrics["minimum_clearance_nm"], "minimum intra-dimer clearance"),("minimum_neighbor_clearance_nm", metrics["minimum_neighbor_clearance_nm"], "minimum neighboring-dimer clearance")]
    rows.extend((key, value, "replacement decision criterion") for key, value in decision.items())
    return [{"metric": key, "value": value, "notes": note} for key, value, note in rows]

def comparison_rows(metrics: dict[str, object], decision: dict[str, object]) -> list[dict[str, object]]:
    shifted = {"source": "Stage12-11B shifted delta=1 tuple","variant_id": metrics["variant_id"],"x_LP_target_plus1_power": metrics["x_LP_target_plus1_power"],"y_LP_target_plus1_leakage": metrics["y_LP_target_plus1_leakage"],"target_order_selectivity_ratio": metrics["target_order_selectivity_ratio"],"steering_angle_deg": metrics["steering_angle_deg"],"x_LP_dominant_order": metrics["x_LP_dominant_order"],"y_LP_dominant_leakage_order": metrics["y_LP_dominant_leakage_order"],"replacement_worthy": decision["replacement_worthy"]}
    rows = []
    for row in (BASELINE, STAGE12_8_BEST, STAGE12_9_BEST, shifted):
        item = dict(row)
        item.setdefault("x_LP_dominant_order", "")
        item.setdefault("y_LP_dominant_leakage_order", "")
        item.setdefault("replacement_worthy", False)
        rows.append(item)
    return rows

def write_markdown(paths: Stage12_11BPaths, metrics: dict[str, object], decision: dict[str, object]) -> None:
    out = paths.output_dir
    worthy = bool(decision["replacement_worthy"])
    preferred = bool(decision["hard_preferred_target_met"])
    summary = ["# Stage12-11B Shifted Phase-Origin Tuple K=6 FDTD Summary","","## Boundary","","- This stage ran K=6 plane-wave validation only.","- Exactly two FDTD simulations were run: x-LP and y-LP.","- No dipoles, no CP branch, no y-gradient, no reverse layout, no H600/H700, and no broad sweep were run.","- The official Stage12-2 baseline files were not modified.","","## Shifted Tuple","","- Phase origin delta: 1 deg.","- Target phase sequence: [1, 61, 121, 181, 241, 301] deg.","- Gradient axis: x.","- Steering plane: x-z.","- Target diffraction order: x-order +1.","","## FDTD Metrics","",f"- x-LP +1 target power: `{metrics['x_LP_target_plus1_power']}`.",f"- y-LP +1 target leakage: `{metrics['y_LP_target_plus1_leakage']}`.",f"- target_order_selectivity_ratio: `{metrics['target_order_selectivity_ratio']}`.",f"- steering angle: `{metrics['steering_angle_deg']}` deg.",f"- x-LP dominant order: `{metrics['x_LP_dominant_order']}`.",f"- y-LP dominant leakage order: `{metrics['y_LP_dominant_leakage_order']}`.",f"- x-LP order contrast: `{metrics['x_LP_order_contrast']}`.",f"- geometry legal: `{metrics['geometry_legal']}`.",f"- minimum clearance: `{metrics['minimum_clearance_nm']}` nm.","","## Replacement Decision","",f"- Replacement-worthy: `{worthy}`.",f"- Hard preferred target met: `{preferred}`.",f"- Criterion ratio >= 15 and leakage below baseline: `{decision['criterion_ratio_ge15_and_leak_below_baseline']}`.",f"- Criterion leakage drop >= 20 percent with x power >= 0.30: `{decision['criterion_leakage_drop_ge20pct_with_x_power_ge030']}`.",f"- Criterion ratio improves >= 25 percent: `{decision['criterion_ratio_improves_ge25pct']}`."]
    out.joinpath("stage12_11b_best_tuple_fdtd_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    recommendation = ["# Stage12-11B Next Recommendation","",("The shifted tuple is replacement-worthy by the Stage12-11B decision criteria. A later freeze stage can consider replacing the official Stage12-2 baseline after GUI/setup review." if worthy else "The shifted tuple does not clearly improve K=6 FDTD metrics. Keep the official Stage12-2 baseline."),("It still does not meet the hard preferred target; further gains would likely need broader high-margin library redesign." if not preferred else "It meets the hard preferred target for plane-wave selectivity."),"Stage12 plane-wave refinement should stop if no replacement-worthy improvement is observed; Stage13 remains dipole-source / MicroLED coupling, not part of this validation."]
    out.joinpath("stage12_11b_next_recommendation.md").write_text("\n".join(recommendation) + "\n", encoding="utf-8")

def run_stage12_11b(repo_root: Path, paths: Stage12_11BPaths, lumapi: object, runtime: object, keep_fsp: bool = False) -> dict[str, object]:
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    layout_rows, geometry_rows, phase_rows, geometry_audit = build_shifted_tuple_layout(repo_root, paths.baseline_layout_csv, paths.best_tuple_csv)
    write_csv_rows(layout_rows, paths.output_dir / "stage12_11b_shifted_tuple_layout_plan.csv", SHIFTED_LAYOUT_FIELDS)
    write_csv_rows(geometry_rows, paths.output_dir / "stage12_11b_shifted_tuple_geometry_audit.csv", GEOMETRY_AUDIT_FIELDS)
    write_csv_rows(phase_rows, paths.output_dir / "stage12_11b_shifted_tuple_phase_amplitude_audit.csv", PHASE_FIELDS)
    run_matrix = build_run_matrix(layout_rows)
    write_csv_rows(run_matrix, paths.output_dir / "stage12_11b_fdtd_run_matrix.csv", RUN_MATRIX_FIELDS)
    fdtd_paths = Stage12Paths(paths.output_dir / "stage12_11b_shifted_tuple_layout_plan.csv", paths.output_dir / "stage12_11b_shifted_tuple_geometry_audit.csv", paths.output_dir / "stage12_11b_shifted_tuple_phase_amplitude_audit.csv", paths.output_dir, paths.fdtd_work_dir)
    results: list[dict[str, object]] = []
    x_orders: list[dict[str, object]] = []
    y_orders: list[dict[str, object]] = []
    for row in run_matrix:
        result, orders = run_one_fdtd(lumapi, runtime, layout_rows, row, fdtd_paths, keep_fsp=keep_fsp)
        results.append(result)
        if row["polarization"] == "x":
            x_orders = list(orders)
            write_csv_rows(x_orders, paths.output_dir / "stage12_11b_order_power_x_lp.csv", ORDER_POWER_FIELDS)
        else:
            y_orders = list(orders)
            write_csv_rows(y_orders, paths.output_dir / "stage12_11b_order_power_y_lp.csv", ORDER_POWER_FIELDS)
        write_csv_rows(results, paths.output_dir / "stage12_11b_fdtd_results.csv", RESULT_FIELDS)
    if len(results) != 2 or any(row.get("fdtd_status") != "ok" for row in results):
        raise RuntimeError(f"Stage12-11B expected two successful FDTD runs, got {results}")
    x_result = next(row for row in results if row["polarization"] == "x")
    y_result = next(row for row in results if row["polarization"] == "y")
    metrics = compute_metrics(x_result, y_result, x_orders, y_orders, geometry_audit)
    decision = replacement_decision(metrics)
    write_csv_rows(selectivity_rows(metrics, decision), paths.output_dir / "stage12_11b_selectivity_summary.csv", SELECTIVITY_FIELDS)
    write_csv_rows(comparison_rows(metrics, decision), paths.output_dir / "stage12_11b_baseline_vs_shifted_tuple_comparison.csv", COMPARE_FIELDS)
    write_markdown(paths, metrics, decision)
    return {"output_dir": str(paths.output_dir),"fdtd_runs": len(results),"geometry_legal": metrics["geometry_legal"],"minimum_clearance_nm": metrics["minimum_clearance_nm"],"x_LP_target_plus1_power": metrics["x_LP_target_plus1_power"],"y_LP_target_plus1_leakage": metrics["y_LP_target_plus1_leakage"],"target_order_selectivity_ratio": metrics["target_order_selectivity_ratio"],"baseline_ratio": BASELINE["target_order_selectivity_ratio"],"baseline_y_leakage": BASELINE["y_LP_target_plus1_leakage"],"replacement_worthy": decision["replacement_worthy"],"hard_preferred_target_met": decision["hard_preferred_target_met"],"gui_fsp_generated": False}
