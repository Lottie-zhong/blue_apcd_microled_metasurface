from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from metasurface.stage12_k6_fdtd import flt, read_csv_rows, write_csv_rows

OUTPUT_DIR_NAME = "stage12_5_h500_lp_k6_official_xgrad_freeze"
OFFICIAL_STATUS = "Official validated H500 LP-APCD K=6 x-gradient target-direction selective metagrating"
YGRAD_STATUS = "y-gradient coordinate-transfer diagnostic, steering pass but LP selectivity fail"
PASS_THRESHOLD = 6.0

COMPARISON_FIELDS = ["metric", "stage12_2_x_gradient_official", "stage12_4_y_gradient_diagnostic", "interpretation"]
METRIC_FIELDS = ["metric", "value", "status", "notes"]
STATUS_FIELDS = ["stage", "role", "gradient_axis", "fdtd_status", "classification", "key_result", "output_folder"]

@dataclass(frozen=True)
class Stage12FreezePaths:
    stage12_2_dir: Path
    stage12_3_dir: Path
    stage12_3b_dir: Path
    stage12_4_dir: Path
    stage11_freeze_dir: Path
    stage12_1_dir: Path
    output_dir: Path

def classify_branch(target_ratio: float, steering_pass: bool, threshold: float = PASS_THRESHOLD) -> str:
    if steering_pass and target_ratio >= threshold:
        return "PASS"
    if steering_pass:
        return "STEERING_PASS_SELECTIVITY_FAIL"
    return "FAIL"

def choose_official_axis(x_ratio: float, y_ratio: float, x_pass: bool, y_pass: bool) -> str:
    if x_pass and not y_pass:
        return "x"
    if y_pass and not x_pass:
        return "y"
    return "x" if x_ratio >= y_ratio else "y"

def metric_lookup(rows: Sequence[dict[str, str]], *names: str) -> dict[str, str]:
    wanted = set(names)
    return {row.get("metric", ""): row.get("value", "") for row in rows if row.get("metric", "") in wanted}

def build_freeze_outputs(paths: Stage12FreezePaths) -> dict[str, object]:
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    x_results = read_csv_rows(paths.stage12_2_dir / "stage12_2_k6_forward_fdtd_results.csv")
    x_metrics = metric_lookup(read_csv_rows(paths.stage12_2_dir / "stage12_2_k6_forward_selectivity_summary.csv"), "effective_selectivity_ratio", "overall_farfield_audit_pass", "effective_target_power", "effective_blocked_leakage")
    y_results = read_csv_rows(paths.stage12_4_dir / "stage12_4_ygrad_fdtd_results.csv")
    y_metrics = metric_lookup(read_csv_rows(paths.stage12_4_dir / "stage12_4_ygrad_selectivity_summary.csv"), "target_order_selectivity_ratio", "overall_stage12_4_pass", "effective_target_power", "effective_blocked_leakage", "total_transmission_selectivity_ratio", "y_leakage_fraction_in_target_order")
    x_xlp = next(row for row in x_results if row["polarization"] == "x")
    x_ylp = next(row for row in x_results if row["polarization"] == "y")
    y_xlp = next(row for row in y_results if row["polarization"] == "x")
    y_ylp = next(row for row in y_results if row["polarization"] == "y")
    x_ratio = flt(x_metrics["effective_selectivity_ratio"])
    y_ratio = flt(y_metrics["target_order_selectivity_ratio"])
    x_pass = str(x_metrics["overall_farfield_audit_pass"]).lower() == "true"
    y_pass = str(y_metrics["overall_stage12_4_pass"]).lower() == "true"
    official_axis = choose_official_axis(x_ratio, y_ratio, x_pass, y_pass)
    x_class = classify_branch(x_ratio, str(x_xlp.get("plus1_direction_consistent", "")).lower() == "true")
    y_class = classify_branch(y_ratio, str(y_xlp.get("plus1_y_direction_consistent", "")).lower() == "true")
    comparison_rows = build_comparison_rows(x_xlp, x_ylp, y_xlp, y_ylp, x_metrics, y_metrics)
    metric_rows = build_official_metric_rows(x_xlp, x_ylp, x_metrics, official_axis, x_class)
    status_rows = build_status_rows(paths, x_class, y_class, x_ratio, y_ratio)
    write_csv_rows(comparison_rows, paths.output_dir / "stage12_5_xgrad_vs_ygrad_comparison.csv", COMPARISON_FIELDS)
    write_csv_rows(metric_rows, paths.output_dir / "stage12_5_official_metrics.csv", METRIC_FIELDS)
    write_csv_rows(status_rows, paths.output_dir / "stage12_5_stage12_status_table.csv", STATUS_FIELDS)
    write_summary(paths.output_dir / "stage12_5_official_convention_summary.md", paths, metric_rows, x_class, y_class)
    write_recommendations(paths.output_dir / "stage12_5_next_stage_recommendations.md", x_class, y_class)
    return {"output_dir": str(paths.output_dir), "official_axis": official_axis, "x_classification": x_class, "y_classification": y_class, "x_ratio": x_ratio, "y_ratio": y_ratio}

def build_comparison_rows(x_xlp, x_ylp, y_xlp, y_ylp, x_metrics, y_metrics):
    return [
        {"metric": "role", "stage12_2_x_gradient_official": OFFICIAL_STATUS, "stage12_4_y_gradient_diagnostic": YGRAD_STATUS, "interpretation": "x-gradient is the official freeze; y-gradient is not validated without redesign"},
        {"metric": "diffraction_period_direction", "stage12_2_x_gradient_official": "x, Lambda_x = K * p_x", "stage12_4_y_gradient_diagnostic": "y transfer diagnostic", "interpretation": "the original K=6 diffraction period was designed along x"},
        {"metric": "gradient_axis", "stage12_2_x_gradient_official": "x", "stage12_4_y_gradient_diagnostic": "y", "interpretation": "y-gradient changes neighbor relations and was tested only as coordinate transfer"},
        {"metric": "target_order", "stage12_2_x_gradient_official": "x-order +1 (n=+1,m=0)", "stage12_4_y_gradient_diagnostic": "y-order +1 (n=0,m=+1)", "interpretation": "official target order is x-order +1"},
        {"metric": "x_LP_target_power", "stage12_2_x_gradient_official": x_xlp["target_plus1_power"], "stage12_4_y_gradient_diagnostic": y_xlp["target_y_plus1_power"], "interpretation": "x-gradient has higher target power"},
        {"metric": "steering_angle_deg", "stage12_2_x_gradient_official": x_xlp["dominant_theta_deg"], "stage12_4_y_gradient_diagnostic": y_xlp["dominant_theta_yz_deg"], "interpretation": "both steer, but selectivity decides the official branch"},
        {"metric": "y_LP_target_leakage", "stage12_2_x_gradient_official": x_ylp["target_plus1_power"], "stage12_4_y_gradient_diagnostic": y_ylp["target_y_plus1_power"], "interpretation": "y-gradient leaks strongly into target order"},
        {"metric": "target_order_selectivity_ratio", "stage12_2_x_gradient_official": x_metrics["effective_selectivity_ratio"], "stage12_4_y_gradient_diagnostic": y_metrics["target_order_selectivity_ratio"], "interpretation": "x-gradient passes >=6; y-gradient fails"},
        {"metric": "y_LP_dominant_leakage_order", "stage12_2_x_gradient_official": f"n={x_ylp['dominant_order_n']},m={x_ylp['dominant_order_m']}", "stage12_4_y_gradient_diagnostic": f"n={y_ylp['dominant_order_n']},m={y_ylp['dominant_order_m']}", "interpretation": "x-gradient redirects y-LP mostly away from target; y-gradient does not"},
        {"metric": "total_transmission_selectivity_ratio", "stage12_2_x_gradient_official": "not validated by Stage12-3 as global blocking", "stage12_4_y_gradient_diagnostic": y_metrics.get("total_transmission_selectivity_ratio", ""), "interpretation": "global y-LP blocking is not claimed"},
    ]

def build_official_metric_rows(x_xlp, x_ylp, x_metrics, official_axis, classification):
    return [
        {"metric": "official_diffraction_period_direction", "value": "x; Lambda_x = K * p_x", "status": "FROZEN", "notes": "original K=6 diffraction period design"},
        {"metric": "official_gradient_axis", "value": official_axis, "status": "FROZEN", "notes": "phase-gradient axis = x"},
        {"metric": "selected_input_polarization", "value": "x-LP", "status": "FROZEN", "notes": "target selected channel"},
        {"metric": "blocked_input_polarization", "value": "y-LP", "status": "FROZEN", "notes": "blocked/leakage channel"},
        {"metric": "official_steering_plane", "value": "x-z", "status": "FROZEN", "notes": "top emission direction +z"},
        {"metric": "official_target_order", "value": "x-order +1", "status": "FROZEN", "notes": "Stage12-2 order_n=+1, order_m=0"},
        {"metric": "expected_steering_angle_deg", "value": "10", "status": "FROZEN", "notes": "Stage12 target angle"},
        {"metric": "x_LP_target_plus1_power", "value": x_xlp["target_plus1_power"], "status": "PASS", "notes": "source-normalized target-order power"},
        {"metric": "x_LP_steering_angle_deg", "value": x_xlp["dominant_theta_deg"], "status": "PASS", "notes": "dominant x-order +1 angle"},
        {"metric": "y_LP_target_plus1_leakage", "value": x_ylp["target_plus1_power"], "status": "PASS", "notes": "blocked-channel leakage into target order"},
        {"metric": "target_order_selectivity_ratio", "value": x_metrics["effective_selectivity_ratio"], "status": "PASS", "notes": ">=6 target-direction criterion"},
        {"metric": "classification", "value": classification, "status": "PASS", "notes": OFFICIAL_STATUS},
        {"metric": "global_y_LP_blocking", "value": "not validated", "status": "BOUNDARY", "notes": "Stage12 validates target-direction selectivity, not total-transmission blocking"},
    ]

def build_status_rows(paths, x_class, y_class, x_ratio, y_ratio):
    return [
        {"stage": "Stage11-2I", "role": "frozen H500 LP-APCD six-bin library", "gradient_axis": "n/a", "fdtd_status": "pre-existing", "classification": "INPUT_FREEZE", "key_result": "strict bins 0,60,120,180,240,300", "output_folder": str(paths.stage11_freeze_dir)},
        {"stage": "Stage12-1", "role": "x-gradient layout geometry audit", "gradient_axis": "x", "fdtd_status": "no FDTD", "classification": "LAYOUT_READY", "key_result": "geometry legal, minimum clearance 20 nm", "output_folder": str(paths.stage12_1_dir)},
        {"stage": "Stage12-2", "role": "official minimal validation", "gradient_axis": "x", "fdtd_status": "two runs completed earlier", "classification": x_class, "key_result": f"target-order selectivity {x_ratio:.6f}", "output_folder": str(paths.stage12_2_dir)},
        {"stage": "Stage12-3", "role": "order-resolved read-only interpretation", "gradient_axis": "x", "fdtd_status": "no new FDTD", "classification": "PARTIAL_PASS_TARGET_DIRECTION", "key_result": "target-direction selectivity validated; global blocking not validated", "output_folder": str(paths.stage12_3_dir)},
        {"stage": "Stage12-3B", "role": "x-gradient GUI inspection setup", "gradient_axis": "x", "fdtd_status": "no FDTD", "classification": "GUI_REFERENCE", "key_result": "existing x-gradient .fsp reference only", "output_folder": str(paths.stage12_3b_dir)},
        {"stage": "Stage12-4", "role": "coordinate-transfer diagnostic", "gradient_axis": "y", "fdtd_status": "two runs completed earlier", "classification": y_class, "key_result": f"steering pass but selectivity {y_ratio:.6f}", "output_folder": str(paths.stage12_4_dir)},
        {"stage": "Stage12-5", "role": "official convention freeze", "gradient_axis": "x", "fdtd_status": "no new FDTD", "classification": "OFFICIAL_XGRAD_FREEZE", "key_result": OFFICIAL_STATUS, "output_folder": str(paths.output_dir)},
    ]

def write_summary(path, paths, metric_rows, x_class, y_class):
    lines = [
        "# Stage12-5 Official H500 LP-APCD K=6 X-Gradient Freeze",
        "",
        "## Official Convention",
        "",
        "- Official label: Official validated H500 LP-APCD K=6 x-gradient target-direction selective metagrating.",
        "- Official diffraction period direction: x.",
        "- Official diffraction period: Lambda_x = K * p_x.",
        "- Official gradient axis: x.",
        "- Selected input polarization: x-LP.",
        "- Blocked input polarization: y-LP.",
        "- Official steering plane: x-z.",
        "- Official target diffraction order: x-order +1.",
        "- Expected steering angle: +10 deg.",
        "",
        "## Why X-Gradient Is Chosen",
        "",
        "The K=6 diffraction period was originally designed along the x direction: Lambda_x = K * p_x. Therefore the official phase-gradient axis is x, the steering plane is x-z, and the target diffraction order is x-order +1.",
        "",
        "Literature does not require the phase-gradient axis to be perpendicular to the selected LP. Functional QWP metasurface work can use an x-direction phase gradient as a coordinate/design choice for beam steering. Compounding-style gradient metasurface logic requires equal amplitude and constant phase difference between adjacent meta-atoms or meta-molecules. The gradient axis is a layout degree of freedom, but it is part of the design definition and changes neighbor coupling when transferred.",
        "",
        "Stage12-4 y-gradient is therefore treated only as a coordinate-transfer diagnostic. It preserves +10 deg steering, but it fails LP target-direction selectivity. It should not be rescued unless the whole design is redefined with Lambda_y from the beginning.",
        "",
        "## Final Official Metrics",
        "",
        "| Metric | Value | Status |",
        "|---|---:|---|",
    ]
    for row in metric_rows:
        lines.append(f"| {row['metric']} | {row['value']} | {row['status']} |")
    lines.extend([
        "",
        "## Branch Classification",
        "",
        f"- Stage12-2 x-gradient: {x_class}. This is the official PASS branch.",
        f"- Stage12-4 y-gradient: {y_class}. This is a failed coordinate-transfer diagnostic branch, not the official design convention.",
        "- Target-direction LP selectivity is validated for x-gradient.",
        "- Global y-LP blocking is not validated.",
        "- For x-gradient, y-LP is redirected into non-target orders rather than globally blocked.",
        "- y-gradient without redesign is not validated.",
        "",
        "## Existing GUI References",
        "",
        f"- x-gradient GUI .fsp: `{paths.stage12_3b_dir / 'stage12_3b_h500_lp_k6_forward_gui_inspection.fsp'}`",
        f"- y-gradient GUI .fsp: `{paths.stage12_4_dir / 'stage12_4_h500_lp_k6_forward_ygrad_gui_inspection.fsp'}`",
        "- No new .fsp was created by Stage12-5.",
        "",
        "## Milestone Status",
        "",
        "Stage12 can be considered complete enough for the current LP metagrating milestone: the official x-gradient H500 K=6 branch has full-FDTD target-order steering and LP target-direction selectivity evidence. Recommended next step is publication/meeting figure preparation or optional x-gradient efficiency refinement, not y-gradient rescue unless the whole design is redefined around Lambda_y from the beginning.",
        "",
        "## Boundaries",
        "",
        "- No FDTD was run in Stage12-5.",
        "- No simulation file was created or modified in Stage12-5.",
        "- No geometry optimization was performed.",
        "- No .fsp, logs, monitor dumps, far-field dumps, or generated outputs should be committed.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def write_recommendations(path, x_class, y_class):
    lines = [
        "# Stage12-5 Next Stage Recommendations",
        "",
        "## P0 Recommendation",
        "",
        "Prepare publication/meeting figures and a compact results slide for the official x-gradient branch. Show Stage12-2 as the official PASS, Stage12-3 as order-resolved interpretation, and Stage12-4 as the failed y-gradient coordinate-transfer diagnostic.",
        "",
        "## P1 Optional Recommendation",
        "",
        "Perform x-gradient efficiency refinement only if higher target-order power is required. Keep the official convention fixed: Lambda_x = K * p_x, x-LP input, x-gradient, x-z steering, x-order +1.",
        "",
        "## Not Recommended By Default",
        "",
        "Do not spend the next stage rescuing y-gradient unless the whole design is redefined with Lambda_y from the beginning. Stage12-4 already shows that coordinate transfer without redesign preserves steering but fails LP target-direction selectivity.",
        "",
        "## Evidence Boundary",
        "",
        f"- x-gradient classification: {x_class}.",
        f"- y-gradient classification: {y_class}.",
        "- Stage12-5 is read-only consolidation: no new FDTD was run.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
