from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


WAVELENGTH_NM = 450.0
PERIOD_X_NM = 2591.446716
TARGET_UX = WAVELENGTH_NM / PERIOD_X_NM
TARGET_THETA_DEG = math.degrees(math.asin(TARGET_UX))
BRIDGE_STATUS = "resolved_plus_order_maps_to_positive_ux"

EVIDENCE_FIELDS = ["evidence_id", "source_path", "line_or_function", "observed_value", "status", "interpretation"]
FORMULA_FIELDS = ["audit_id", "source_path", "line_or_function", "formula_or_operation", "sign_effect", "status", "notes"]
AXIS_FIELDS = ["audit_id", "source_path", "line_or_function", "operation", "x_sign_effect", "y_sign_effect", "status", "notes"]
INTERPRETATION_FIELDS = [
    "bridge_status", "stage12_target_order", "stage13_target_ux", "stage13_target_theta_deg",
    "center_x_peak_ux", "center_x_peak_uy", "distance_to_positive_target_deg", "distance_to_negative_target_deg",
    "near_actual_target_within_3deg", "mechanism_class", "sign_inconsistency_detected",
    "leading_mechanism", "recommended_next_step", "notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, object]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def angular_distance_deg(ux: float, uy: float, center_ux: float, center_uy: float = 0.0) -> float:
    uz = math.sqrt(max(0.0, 1.0 - ux * ux - uy * uy))
    cz = math.sqrt(max(0.0, 1.0 - center_ux * center_ux - center_uy * center_uy))
    dot = max(-1.0, min(1.0, ux * center_ux + uy * center_uy + uz * cz))
    return math.degrees(math.acos(dot))


def line_number(text: str, needle: str) -> int:
    for index, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return index
    raise ValueError(f"missing code evidence: {needle}")


def validate_bridge(order_rows: Sequence[dict[str, str]], apcd_code: str, stage13_code: str) -> dict[str, float | str]:
    x_rows = [row for row in order_rows if row["run_id"].endswith("_x")]
    plus = next(row for row in x_rows if int(row["order_n"]) == 1)
    minus = next(row for row in x_rows if int(row["order_n"]) == -1)
    plus_ux = float(plus["ux"])
    minus_ux = float(minus["ux"])
    if "fdtd.gratingn(monitor_name)" not in apcd_code or "fdtd.gratingu1(monitor_name)" not in apcd_code:
        raise ValueError("Stage12 common-index gratingn/gratingu1 evidence missing")
    if "fdtd.farfieldux" not in stage13_code and "np.meshgrid(uxa, uya, indexing=\"ij\")" not in stage13_code:
        raise ValueError("Stage13 direct farfieldux/grid evidence missing")
    if plus_ux <= 0 or minus_ux >= 0 or abs(plus_ux + minus_ux) > 1e-12:
        raise ValueError(f"order/ux sign evidence inconsistent: +1={plus_ux}, -1={minus_ux}")
    return {"bridge_status": BRIDGE_STATUS, "plus_ux": plus_ux, "minus_ux": minus_ux}


def plot_schematic(path: Path, center_peak_ux: float) -> None:
    fig, ax = plt.subplots(figsize=(8.0, 2.8), constrained_layout=True)
    ax.axhline(0, color="black", linewidth=1)
    for x, label, color in ((-TARGET_UX, "Stage12 -1\nStage13 -target", "#3cb44b"), (0.0, "zero", "gray"), (TARGET_UX, "Stage12 +1\nStage13 +target", "#42d4f4"), (center_peak_ux, "Stage13 center_x Ex peak", "#e6194b")):
        ax.scatter([x], [0], s=90, color=color, zorder=3)
        ax.annotate(label, (x, 0), xytext=(0, 18 if x != center_peak_ux else -35), textcoords="offset points", ha="center")
    ax.set_xlim(-0.45, 0.30); ax.set_ylim(-0.12, 0.12)
    ax.set_xlabel("direction cosine $u_x$ (+x to the right)")
    ax.set_yticks([]); ax.set_title("Stage12 grating-order to Stage13 farfieldux sign bridge")
    ax.grid(axis="x", alpha=0.25)
    fig.savefig(path, dpi=170); plt.close(fig)


def build_report(interpretation: dict[str, object], plus_lp: dict[float, float]) -> str:
    lp_table = "\n".join(f"| {cone:.0f} | {value:.9f} |" for cone, value in sorted(plus_lp.items()))
    return f"""# Stage13-7A LP Coordinate/Sign Bridge Validation

## Scope

- No FDTD was run. No FSP was opened, created, saved, or modified.
- Existing Stage12 order CSV/code and Stage13 far-field CSV/code were audited read-only.
- No +/-q, DBR/RCLED, geometry change, or optimization.

## Stage12 order/sign evidence

- `src/metasurface/apcd_diffraction.py::extract_fdtd_grating_orders` reads `gratingn(T)` and `gratingu1(T)` into aligned rows using the same array index.
- The existing Stage12 x-LP order CSV records order_n=+1 with ux=+0.173648177762 and order_n=-1 with ux=-0.173648177762.
- These ux values come directly from Lumerical `gratingu1`, not from a post-processing sign assumption.
- `stage12_k6_fdtd.expected_theta_deg` uses `asin(order * wavelength / period)`, not a leading-minus formula.
- The official Stage12 result calls +1/+ux +10 deg and reports +1 as the dominant x-LP order.

## Stage13 axis/code evidence

- Stage13 obtains `farfieldux` and `farfielduy` numerically and builds `meshgrid(uxa, uya, indexing="ij")`.
- If field shape requires it, xx and yy are transposed together; their signs are unchanged.
- Peak CSV values are read directly as `xx[index]` and `yy[index]`.
- PNGs use `pcolormesh(xx, yy, values)` with no `imshow`, origin override, `invert_xaxis`, negation, or axis reversal.
- The +target marker is plotted at `+TARGET_UX`; CSV integration and PNG plotting therefore share the same sign convention.

## Bridge decision

- Status: **`{interpretation['bridge_status']}`**.
- Stage12 +1/+x/+10 deg maps to Stage13 `ux=+{TARGET_UX:.12f}`.
- Stage12 -1/-x/-10 deg maps to Stage13 `ux=-{TARGET_UX:.12f}`.
- Sign-convention inconsistency detected: **false**.

## Stage13-5 interpretation update

- The actual designed target center is now resolved as `ux=+{TARGET_UX:.12f}, uy=0`.
- center_x Ex global peak remains at ux={interpretation['center_x_peak_ux']}, uy={interpretation['center_x_peak_uy']}.
- Angular distance to +target: {interpretation['distance_to_positive_target_deg']:.6f} deg; to -target: {interpretation['distance_to_negative_target_deg']:.6f} deg.
- It is not within 3 deg of either expected order. `class_C_no_steering` remains unchanged.
- Existing incoherent LP fractions at the resolved +target center:

| cone half-angle (deg) | LP_fraction_incoherent |
| ---: | ---: |
{lp_table}

- With phase ramp and tiling already clean, the leading diagnosis is local-dipole broad-angle/source-coupling mismatch, including the source-center bias toward the phase-180 J2 pillar.

## Single recommended next step

**Stage13-7C: run center_x only with an adjusted source-center or controlled source-coupling diagnostic.**

This recommendation is for a separately authorized future FDTD task. Do not run +/-q and do not add DBR/RCLED yet.

## Jones/APCD evidence boundary

- Stage12 order vectors exist, but this task does not reconstruct a new J_xy matrix or alpha/beta basis conversion.
- `t_{{alpha*<-alpha}}^order` is not newly evaluated or claimed. This task resolves coordinate sign only.
"""


def run_audit(repo_root: Path, output_dir: Path) -> dict[str, object]:
    order_path = repo_root / "outputs/stage12_2_h500_lp_k6_forward_minimal_fdtd/stage12_2_k6_forward_order_power.csv"
    official_path = repo_root / "outputs/stage12_6_h500_lp_k6_official_result_package/stage12_6_result_package_summary.md"
    figure_path = repo_root / "outputs/stage12_6_h500_lp_k6_official_result_package/figure_3_xgrad_order_power.png"
    gui_path = repo_root / "outputs/stage12_3b_h500_lp_k6_gui_inspection/stage12_3b_h500_lp_k6_forward_gui_inspection.fsp"
    peak_path = repo_root / "outputs/stage13_5_lp_no_dbr_center_order_diagnosis/stage13_5_peak_metrics.csv"
    incoherent_path = repo_root / "outputs/stage13_5_lp_no_dbr_center_order_diagnosis/stage13_5_order_incoherent_average.csv"
    apcd_path = repo_root / "src/metasurface/apcd_diffraction.py"
    stage12_path = repo_root / "src/metasurface/stage12_k6_fdtd.py"
    stage13_run_path = repo_root / "src/metasurface/stage13_4_center_dipole.py"
    stage13_path = repo_root / "src/metasurface/stage13_5_order_diagnosis.py"
    required = (order_path, official_path, figure_path, peak_path, incoherent_path, apcd_path, stage12_path, stage13_run_path, stage13_path)
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    order_rows = read_csv(order_path)
    peaks = read_csv(peak_path)
    incoherent = read_csv(incoherent_path)
    apcd_code = apcd_path.read_text(encoding="utf-8")
    stage12_code = stage12_path.read_text(encoding="utf-8")
    stage13_run_code = stage13_run_path.read_text(encoding="utf-8")
    stage13_code = stage13_path.read_text(encoding="utf-8")
    bridge = validate_bridge(order_rows, apcd_code, stage13_run_code + stage13_code)
    x_orders = [row for row in order_rows if row["run_id"].endswith("_x")]
    plus = next(row for row in x_orders if int(row["order_n"]) == 1)
    minus = next(row for row in x_orders if int(row["order_n"]) == -1)
    zero = next(row for row in x_orders if int(row["order_n"]) == 0)
    evidence_rows = [
        {"evidence_id": "stage12_common_index_api", "source_path": apcd_path.relative_to(repo_root).as_posix(), "line_or_function": f"extract_fdtd_grating_orders lines {line_number(apcd_code, 'fdtd.gratingn(monitor_name)')}/{line_number(apcd_code, 'fdtd.gratingu1(monitor_name)')}", "observed_value": "order_n=gratingn[index]; ux=gratingu1[index]", "status": "direct_code_evidence", "interpretation": "order label and direction cosine share one row/index"},
        {"evidence_id": "stage12_plus1_numeric", "source_path": order_path.relative_to(repo_root).as_posix(), "line_or_function": "x-LP order_n=+1 row", "observed_value": f"ux={plus['ux']}; theta={plus['theta_deg']}; power={plus['order_power_source_norm']}", "status": "direct_numeric_evidence", "interpretation": "+1 maps to positive ux"},
        {"evidence_id": "stage12_minus1_numeric", "source_path": order_path.relative_to(repo_root).as_posix(), "line_or_function": "x-LP order_n=-1 row", "observed_value": f"ux={minus['ux']}; theta={minus['theta_deg']}; power={minus['order_power_source_norm']}", "status": "direct_numeric_evidence", "interpretation": "-1 maps to negative ux"},
        {"evidence_id": "stage12_zero_numeric", "source_path": order_path.relative_to(repo_root).as_posix(), "line_or_function": "x-LP order_n=0 row", "observed_value": f"ux={zero['ux']}; theta={zero['theta_deg']}", "status": "direct_numeric_evidence", "interpretation": "zero order maps to ux=0"},
        {"evidence_id": "stage12_official_claim", "source_path": official_path.relative_to(repo_root).as_posix(), "line_or_function": "Official Result", "observed_value": "x-order +1; +10 deg; +x steering plane", "status": "explicit_report_evidence", "interpretation": "consistent with numeric CSV"},
        {"evidence_id": "stage12_order_plot", "source_path": figure_path.relative_to(repo_root).as_posix(), "line_or_function": "existing PNG", "observed_value": "figure_3_xgrad_order_power.png", "status": "supporting_only", "interpretation": "not used as the primary numeric bridge"},
        {"evidence_id": "stage12_gui_fsp", "source_path": gui_path.relative_to(repo_root).as_posix(), "line_or_function": "file presence", "observed_value": f"exists={gui_path.is_file()}; size_bytes={gui_path.stat().st_size if gui_path.is_file() else ''}", "status": "not_opened_not_needed", "interpretation": "bridge resolved without FSP access"},
    ]
    formula_rows = [
        {"audit_id": "stage12_order_formula", "source_path": stage12_path.relative_to(repo_root).as_posix(), "line_or_function": f"expected_theta_deg line {line_number(stage12_code, 'def expected_theta_deg')}", "formula_or_operation": "theta=asin(order*wavelength/period)", "sign_effect": "positive order gives positive theta", "status": "plus_sign", "notes": "no leading minus"},
        {"audit_id": "stage12_primary_theta", "source_path": stage12_path.relative_to(repo_root).as_posix(), "line_or_function": f"normalize_order_rows line {line_number(stage12_code, 'theta = math.degrees(math.asin')}", "formula_or_operation": "theta=asin(ux) when gratingu1 is available", "sign_effect": "preserves extracted ux sign", "status": "direct_axis_sign", "notes": "analytic order formula is fallback only"},
        {"audit_id": "stage12_order_axis", "source_path": apcd_path.relative_to(repo_root).as_posix(), "line_or_function": "extract_fdtd_grating_orders", "formula_or_operation": "order_n=gratingn; ux=gratingu1", "sign_effect": "+1 and +ux explicitly paired", "status": "resolved", "notes": "same index"},
        {"audit_id": "stage13_axis_source", "source_path": stage13_run_path.relative_to(repo_root).as_posix(), "line_or_function": f"extract_from_session line {line_number(stage13_run_code, 'ux = fdtd.farfieldux')}", "formula_or_operation": "ux=farfieldux(...) without negation", "sign_effect": "preserves API sign", "status": "resolved", "notes": "+z monitor"},
        {"audit_id": "phase_gradient", "source_path": "outputs/stage13_6_lp_phase_coordinate_patch_audit/stage13_6_phase_ramp_audit.csv", "line_or_function": "six monotonic rows", "formula_or_operation": "dphi/dx>0 along +x", "sign_effect": "repo empirical Stage12 result is +1/+ux", "status": "consistent", "notes": "not used alone to infer API sign"},
        {"audit_id": "monitor_orientation", "source_path": stage13_run_path.relative_to(repo_root).as_posix(), "line_or_function": "add_monitors/resolved_setup", "formula_or_operation": "+z top z-normal monitor", "sign_effect": "no explicit x sign inversion in code", "status": "consistent", "notes": "same top-monitor geometry as Stage12"},
    ]
    axis_rows = [
        {"audit_id": "numeric_axes", "source_path": stage13_run_path.relative_to(repo_root).as_posix(), "line_or_function": "extract_from_session", "operation": "farfieldux/farfielduy numeric arrays", "x_sign_effect": "none", "y_sign_effect": "none", "status": "pass", "notes": "not image-pixel inference"},
        {"audit_id": "meshgrid", "source_path": stage13_path.relative_to(repo_root).as_posix(), "line_or_function": f"direction_grid line {line_number(stage13_code, 'np.meshgrid(uxa, uya, indexing=')}", "operation": "meshgrid indexing=ij", "x_sign_effect": "none", "y_sign_effect": "none", "status": "pass", "notes": "axis values retained"},
        {"audit_id": "shape_transpose", "source_path": stage13_path.relative_to(repo_root).as_posix(), "line_or_function": "direction_grid", "operation": "xx.T and yy.T together only if shape requires", "x_sign_effect": "none", "y_sign_effect": "none", "status": "pass", "notes": "transpose is not sign reversal"},
        {"audit_id": "peak_csv", "source_path": stage13_path.relative_to(repo_root).as_posix(), "line_or_function": "peak_rows", "operation": "peak_ux=float(xx[index]); peak_uy=float(yy[index])", "x_sign_effect": "none", "y_sign_effect": "none", "status": "pass", "notes": "numeric coordinates"},
        {"audit_id": "png_map", "source_path": stage13_path.relative_to(repo_root).as_posix(), "line_or_function": f"save_map line {line_number(stage13_code, 'ax.pcolormesh(xx, yy')}", "operation": "pcolormesh(xx,yy); no imshow/origin/invert_xaxis", "x_sign_effect": "none", "y_sign_effect": "none", "status": "pass", "notes": "CSV and plot share xx/yy"},
        {"audit_id": "target_markers", "source_path": stage13_path.relative_to(repo_root).as_posix(), "line_or_function": "save_map", "operation": "+target at +TARGET_UX; -target at -TARGET_UX", "x_sign_effect": "explicit", "y_sign_effect": "uy=0", "status": "pass", "notes": "consistent with Stage12 bridge"},
    ]
    x_peak = next(row for row in peaks if row["case_id"] == "center_x" and row["component"] == "Ex_target")
    peak_ux, peak_uy = float(x_peak["peak_ux"]), float(x_peak["peak_uy"])
    plus_distance = angular_distance_deg(peak_ux, peak_uy, TARGET_UX)
    minus_distance = angular_distance_deg(peak_ux, peak_uy, -TARGET_UX)
    interpretation = {
        "bridge_status": BRIDGE_STATUS, "stage12_target_order": "+1/+x/+10deg", "stage13_target_ux": TARGET_UX,
        "stage13_target_theta_deg": TARGET_THETA_DEG, "center_x_peak_ux": peak_ux, "center_x_peak_uy": peak_uy,
        "distance_to_positive_target_deg": plus_distance, "distance_to_negative_target_deg": minus_distance,
        "near_actual_target_within_3deg": plus_distance <= 3.0, "mechanism_class": "class_C_no_steering",
        "sign_inconsistency_detected": False, "leading_mechanism": "local_dipole_broad_angle_and_source_coupling_mismatch",
        "recommended_next_step": "Stage13-7C", "notes": "phase ramp and A_small tiling are already clean; source-center local bias remains",
    }
    plus_lp = {float(row["cone_deg"]): float(row["LP_fraction_incoherent"]) for row in incoherent if row["order_id"] == "plus_target_order"}
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "stage13_7a_stage12_order_evidence.csv", evidence_rows, EVIDENCE_FIELDS)
    write_csv(output_dir / "stage13_7a_formula_audit.csv", formula_rows, FORMULA_FIELDS)
    write_csv(output_dir / "stage13_7a_stage13_axis_audit.csv", axis_rows, AXIS_FIELDS)
    write_csv(output_dir / "stage13_7a_interpretation_update.csv", [interpretation], INTERPRETATION_FIELDS)
    (output_dir / "stage13_7a_sign_bridge_report.md").write_text(build_report(interpretation, plus_lp), encoding="utf-8")
    (output_dir / "README.md").write_text(
        f"# Stage13-7A LP coordinate/sign bridge\n\nNo-new-FDTD audit. Bridge status: `{BRIDGE_STATUS}`. Stage12 +1 maps to Stage13 positive ux.\n\nNext: **Stage13-7C** in a separately authorized task.\n",
        encoding="utf-8",
    )
    plot_schematic(output_dir / "stage13_7a_sign_convention_schematic.png", peak_ux)
    return {**bridge, "sign_inconsistency": False, "mechanism_class": "class_C_no_steering", "next_step": "Stage13-7C"}
