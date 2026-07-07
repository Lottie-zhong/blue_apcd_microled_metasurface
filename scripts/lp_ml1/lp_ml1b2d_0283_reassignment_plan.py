from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[2]
CID = "LPML1A4_0283_B240_exploration_B240_H650"
ORIG_BIN = 240
REASSIGNED_BIN = 120
OUT = ROOT / "outputs" / "lp_ml1b2d_0283_refinement"
REPORT = ROOT / "reports" / "lp_ml1b2d_0283_reassignment_and_refinement_plan.md"
RESULTS = ROOT / "outputs" / "lp_ml1b2b_36case_pilot" / "batch_04" / "lp_ml1b2b_batch04_results.csv"
RANKING = ROOT / "outputs" / "lp_ml1b2c_selectivity_first_ranking" / "batch_04" / "lp_ml1b2c_batch04_selectivity_first_ranking.csv"
MANIFEST = ROOT / "outputs" / "lp_ml1a4_explicit_geometry_seed_generator" / "lp_ml1a4_explicit_seed_manifest.csv"
QUEUE = ROOT / "outputs" / "lp_ml1b2a_36case_pilot_plan" / "lp_ml1b2a_pilot_queue_audit.csv"

METRIC_FIELDS = [
    "candidate_id", "wavelength_nm", "selected_phase_deg", "nearest_bin_deg",
    "phase_err_to_original_240_deg", "phase_err_to_reassigned_120_deg", "phase_err_to_nearest_bin_deg",
    "selected_Tx", "conversion_to_leakage_ratio", "y_direct_leakage", "matrix_error",
]
PLAN_FIELDS = [
    "candidate_id", "parent_id", "refinement_family", "intended_reassigned_bin", "H_nm",
    "period_x_nm", "period_y_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg",
    "center_dx_nm", "center_dy_nm", "gap_or_dx_nm", "geometry_valid", "validity_flags",
    "edge_margin_nm", "aabb_gap_x_nm", "aspect_ratio_H_over_minW", "rationale",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return [{k: "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({field: row.get(field, "") for field in fields})


def f(value: object, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        x = float(value)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def fmt(x: float) -> str:
    return f"{x:.6f}" if math.isfinite(x) else ""


def wrap_phase(deg: float) -> float:
    return deg % 360.0


def angular_error(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def row_for(path: Path, candidate_id: str) -> dict[str, str]:
    for row in read_csv(path):
        if row.get("candidate_id") == candidate_id:
            return row
    raise KeyError(candidate_id)


def aabb_half_x(length: float, width: float, theta_deg: float) -> float:
    t = math.radians(theta_deg)
    return abs(length * 0.5 * math.cos(t)) + abs(width * 0.5 * math.sin(t))


def validate_geometry(g: dict[str, float]) -> tuple[bool, list[str], float, float, float]:
    px = g["period_x_nm"]
    dx = abs(g["center_dx_nm"])
    h1 = aabb_half_x(g["L1_nm"], g["W1_nm"], g["theta1_deg"])
    h2 = aabb_half_x(g["L2_nm"], g["W2_nm"], g["theta2_deg"])
    aabb_gap = dx - h1 - h2
    edge_margin = px / 2.0 - max(dx / 2.0 + h1, dx / 2.0 + h2)
    aspect = g["H_nm"] / max(min(g["W1_nm"], g["W2_nm"]), 1e-9)
    flags: list[str] = []
    if g["L1_nm"] < g["W1_nm"] + 20 or g["L2_nm"] < g["W2_nm"] + 20:
        flags.append("L_less_than_W_plus_20")
    if aspect > 10.5:
        flags.append("aspect_ratio_above_10p5")
    if aabb_gap < 10:
        flags.append("aabb_gap_below_10nm")
    if edge_margin < 10:
        flags.append("edge_margin_below_10nm")
    if min(g["L1_nm"], g["W1_nm"], g["L2_nm"], g["W2_nm"], g["H_nm"]) <= 0:
        flags.append("nonpositive_dimension")
    return not flags, flags, edge_margin, aabb_gap, aspect


def make_metrics(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    out = []
    for row in sorted(rows, key=lambda r: f(r.get("wavelength_nm"))):
        phase = wrap_phase(f(row.get("selected_phase_deg")))
        nearest = int(f(row.get("nearest_bin_deg")))
        out.append({
            "candidate_id": CID,
            "wavelength_nm": row.get("wavelength_nm", ""),
            "selected_phase_deg": fmt(phase),
            "nearest_bin_deg": nearest,
            "phase_err_to_original_240_deg": fmt(angular_error(phase, ORIG_BIN)),
            "phase_err_to_reassigned_120_deg": fmt(angular_error(phase, REASSIGNED_BIN)),
            "phase_err_to_nearest_bin_deg": fmt(angular_error(phase, nearest)),
            "selected_Tx": row.get("selected_Tx", ""),
            "conversion_to_leakage_ratio": row.get("conversion_to_leakage_ratio", ""),
            "y_direct_leakage": row.get("y_direct_leakage", ""),
            "matrix_error": row.get("matrix_error", ""),
        })
    return out


def proposed_plan(base: dict[str, str]) -> list[dict[str, object]]:
    b = {k: f(base[k]) for k in ["H_nm", "period_x_nm", "period_y_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg", "center_dx_nm", "center_dy_nm", "gap_or_dx_nm"]}
    specs = [
        ("B2D_0283_A01", "reassigned_B120_cleanup", {"theta1_deg": b["theta1_deg"] - 2.5}, "small theta1 pull for B120 phase cleanup"),
        ("B2D_0283_A02", "reassigned_B120_cleanup", {"theta1_deg": b["theta1_deg"] + 2.5}, "small theta1 push for B120 phase cleanup"),
        ("B2D_0283_A03", "reassigned_B120_cleanup", {"theta2_deg": b["theta2_deg"] - 2.5}, "small theta2 pull for B120 phase cleanup"),
        ("B2D_0283_A04", "reassigned_B120_cleanup", {"theta2_deg": b["theta2_deg"] + 2.5}, "small theta2 push for B120 phase cleanup"),
        ("B2D_0283_A05", "reassigned_B120_cleanup", {"center_dx_nm": b["center_dx_nm"] - 5, "gap_or_dx_nm": b["gap_or_dx_nm"] - 5}, "slightly stronger coupling while preserving projector backbone"),
        ("B2D_0283_A06", "reassigned_B120_cleanup", {"center_dx_nm": b["center_dx_nm"] + 5, "gap_or_dx_nm": b["gap_or_dx_nm"] + 5}, "slightly weaker coupling while preserving projector backbone"),
        ("B2D_0283_B01", "phase_tuning_scout", {"L1_nm": b["L1_nm"] - 5}, "local L1 phase perturbation"),
        ("B2D_0283_B02", "phase_tuning_scout", {"L1_nm": b["L1_nm"] + 5}, "local L1 phase perturbation"),
        ("B2D_0283_B03", "phase_tuning_scout", {"L2_nm": b["L2_nm"] - 5}, "local L2 phase perturbation"),
        ("B2D_0283_B04", "phase_tuning_scout", {"L2_nm": b["L2_nm"] + 5}, "local L2 phase perturbation"),
        ("B2D_0283_B05", "phase_tuning_scout", {"W1_nm": b["W1_nm"] - 5}, "local W1 projector/leakage perturbation"),
        ("B2D_0283_B06", "phase_tuning_scout", {"W2_nm": b["W2_nm"] - 5}, "local W2 projector/leakage perturbation"),
        ("B2D_0283_C01", "fabrication_friendly_H_check", {"H_nm": 625}, "height-only H625 check from strong H650 projector seed"),
        ("B2D_0283_C02", "fabrication_friendly_H_check", {"H_nm": 600}, "height-only H600 check from strong H650 projector seed"),
        ("B2D_0283_C03", "fabrication_friendly_H_check", {"H_nm": 575}, "height-only H575 check from strong H650 projector seed"),
        ("B2D_0283_C04", "fabrication_friendly_H_check", {"H_nm": 550}, "height-only H550 check from strong H650 projector seed"),
        ("B2D_0283_C05", "fabrication_friendly_H_check", {"H_nm": 500}, "height-only H500 experimental convenience check"),
    ]
    rows = []
    for suffix, family, patch, rationale in specs:
        g = dict(b)
        g.update(patch)
        valid, flags, edge, gap, aspect = validate_geometry(g)
        rows.append({
            "candidate_id": f"LPML1B2D_{suffix}",
            "parent_id": CID,
            "refinement_family": family,
            "intended_reassigned_bin": REASSIGNED_BIN,
            **{k: fmt(v) for k, v in g.items()},
            "geometry_valid": str(valid).lower(),
            "validity_flags": ";".join(flags),
            "edge_margin_nm": fmt(edge),
            "aabb_gap_x_nm": fmt(gap),
            "aspect_ratio_H_over_minW": fmt(aspect),
            "rationale": rationale,
        })
    return [r for r in rows if r["geometry_valid"] == "true"][:18]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    all_results = [r for r in read_csv(RESULTS) if r.get("candidate_id") == CID]
    if not all_results:
        raise FileNotFoundError(f"No batch-04 rows for {CID}")
    manifest = row_for(MANIFEST, CID)
    queue = row_for(QUEUE, CID)
    ranking = row_for(RANKING, CID)
    metrics = make_metrics(all_results)
    write_csv(OUT / "lp_ml1b2d_0283_reassignment_metrics.csv", metrics, METRIC_FIELDS)
    plan = proposed_plan(manifest)
    write_csv(OUT / "lp_ml1b2d_0283_local_refinement_plan.csv", plan, PLAN_FIELDS)

    phases120 = [f(r["phase_err_to_reassigned_120_deg"]) for r in metrics]
    txs = [f(r["selected_Tx"]) for r in metrics]
    ratios = [f(r["conversion_to_leakage_ratio"]) for r in metrics]
    ydirs = [f(r["y_direct_leakage"]) for r in metrics]
    matrices = [f(r["matrix_error"]) for r in metrics]
    nearest = [str(r["nearest_bin_deg"]) for r in metrics]
    row452 = next(r for r in metrics if abs(f(r["wavelength_nm"]) - 452) < 1e-9)
    tx_med = median(txs)
    ratio_med = median(ratios)
    ydir_med = median(ydirs)
    matrix_med = median(matrices)
    stable = len(set(nearest)) <= 1
    projector_pass = tx_med >= 0.45 and ratio_med >= 6 and ydir_med <= tx_med / 6 and matrix_med <= 0.60
    phase120_pass = f(row452["phase_err_to_reassigned_120_deg"]) <= 15
    if projector_pass and phase120_pass and stable:
        label = "strong_B120_reassigned_seed"
    elif tx_med >= 0.10 and ratio_med >= 3 and f(row452["phase_err_to_reassigned_120_deg"]) <= 25 and stable:
        label = "usable_B120_reassigned_seed"
    elif projector_pass:
        label = "projector_seed_needs_phase_refinement"
    else:
        label = "unstable_projector_negative"

    geom = {k: manifest.get(k, "") for k in ["H_nm", "period_x_nm", "period_y_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg", "center_dx_nm", "center_dy_nm", "gap_or_dx_nm", "sampling_group", "sampling_family", "target_bin_deg"]}
    gfloat = {k: f(geom[k]) for k in ["H_nm", "period_x_nm", "period_y_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg", "center_dx_nm", "center_dy_nm", "gap_or_dx_nm"]}
    valid, flags, edge, gap, aspect = validate_geometry(gfloat)
    summary = {
        "candidate_id": CID,
        "original_target_bin": ORIG_BIN,
        "reassigned_bin": REASSIGNED_BIN,
        "reassignment_label": label,
        "phase_err_to_120_at_452_deg": row452["phase_err_to_reassigned_120_deg"],
        "phase_err_to_240_at_452_deg": row452["phase_err_to_original_240_deg"],
        "nearest_bin_stability_count": len(set(nearest)),
        "nearest_bin_counts": dict(Counter(nearest)),
        "Tx_median": fmt(tx_med),
        "ratio_median": fmt(ratio_med),
        "y_direct_leakage_median": fmt(ydir_med),
        "matrix_error_median": fmt(matrix_med),
        "b2c_class": ranking.get("b2c_class", ""),
        "geometry": geom,
        "geometry_valid": valid,
        "geometry_flags": flags,
        "edge_margin_nm": fmt(edge),
        "aabb_gap_x_nm": fmt(gap),
        "aspect_ratio_H_over_minW": fmt(aspect),
        "proposed_candidate_count": len(plan),
        "no_fdtd_run": True,
        "no_k6": True,
    }
    (OUT / "lp_ml1b2d_0283_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# LP-ML1B2D 0283 reassignment and local refinement plan",
        "",
        "## Decision",
        f"`{CID}` should be treated as `{label}`.",
        f"It is not a B240 success. Its selected-channel phase is stably assigned to B120 over the sampled wavelengths.",
        "",
        "## Key metrics",
        f"- phase_err_to_120_at_452_deg: {row452['phase_err_to_reassigned_120_deg']}",
        f"- phase_err_to_240_at_452_deg: {row452['phase_err_to_original_240_deg']}",
        f"- nearest_bin_counts: `{summary['nearest_bin_counts']}`",
        f"- Tx_median: {summary['Tx_median']}",
        f"- ratio_median: {summary['ratio_median']}",
        f"- y_direct_leakage_median: {summary['y_direct_leakage_median']}",
        f"- matrix_error_median: {summary['matrix_error_median']}",
        "",
        "## Geometry and constraints",
        f"- H/L1/W1/theta1: {geom['H_nm']} / {geom['L1_nm']} / {geom['W1_nm']} / {geom['theta1_deg']}",
        f"- L2/W2/theta2: {geom['L2_nm']} / {geom['W2_nm']} / {geom['theta2_deg']}",
        f"- center_dx_nm: {geom['center_dx_nm']}",
        f"- period_x_nm, period_y_nm: {geom['period_x_nm']}, {geom['period_y_nm']}",
        f"- edge_margin_nm: {summary['edge_margin_nm']}",
        f"- aabb_gap_x_nm: {summary['aabb_gap_x_nm']}",
        f"- aspect_ratio_H_over_minW: {summary['aspect_ratio_H_over_minW']}",
        f"- geometry_valid: {summary['geometry_valid']}, flags: `{summary['geometry_flags']}`",
        "",
        "## Local refinement candidate count",
        f"Generated {len(plan)} proposed candidates. These are planning rows only; they are not added to the frozen B2A 36-case plan and were not simulated.",
        "",
        "## Recommended next action",
        "Run a small 0283-local refinement batch before broad batch-05. The goal should be B120 cleanup and phase-anchor mapping around the strong projector backbone.",
        "Do not declare K=6 readiness from this single reassigned seed.",
        "",
        "No FDTD, GUI, FMM, ML training, K=6, coverage, or heavy output generation was performed in this B2D audit.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
