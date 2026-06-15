from __future__ import annotations

import csv
import json
import math
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from metasurface.apcd_diffraction import extract_fdtd_grating_orders


EPS = 1e-12
K = 6
TARGET_ORDER = 1
EXPECTED_THETA_DEG = 10.0

RUN_PLAN_FIELDS = [
    "run_id",
    "polarization",
    "polarization_angle_deg",
    "layout_plan_csv",
    "geometry_audit_csv",
    "phase_amplitude_audit_csv",
    "wavelength_nm",
    "height_nm",
    "supercell_period_nm",
    "period_y_nm",
    "expected_target_order",
    "expected_theta_deg",
    "mode",
    "status",
    "notes",
]

RESULT_FIELDS = [
    "run_id",
    "polarization",
    "fdtd_status",
    "total_transmission",
    "dominant_order_n",
    "dominant_order_m",
    "dominant_order_power",
    "dominant_theta_deg",
    "target_plus1_power",
    "zero_order_power",
    "minus1_order_power",
    "order_contrast_plus1_vs_next",
    "plus1_direction_consistent",
    "fsp_path",
    "fsp_retained",
    "diagnostics",
    "notes",
]

ORDER_POWER_FIELDS = [
    "run_id",
    "polarization",
    "order_n",
    "order_m",
    "ux",
    "uy",
    "theta_deg",
    "order_power_fraction_of_transmitted",
    "total_transmission",
    "order_power_source_norm",
    "Ex_order_complex_real",
    "Ex_order_complex_imag",
    "Ey_order_complex_real",
    "Ey_order_complex_imag",
    "Ez_order_complex_real",
    "Ez_order_complex_imag",
]

SELECTIVITY_FIELDS = [
    "metric",
    "value",
    "notes",
]


@dataclass(frozen=True)
class Stage12Paths:
    layout_plan_csv: Path
    geometry_audit_csv: Path
    phase_amplitude_audit_csv: Path
    output_dir: Path
    fdtd_work_dir: Path


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{str(k): "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(handle)]


def write_csv_rows(rows: Iterable[dict[str, object]], path: Path, fields: Sequence[str]) -> None:
    row_list = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(row_list)


def flt(value: object, default: float = math.nan) -> float:
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except Exception:
        return default


def build_run_plan(paths: Stage12Paths) -> list[dict[str, object]]:
    layout = read_csv_rows(paths.layout_plan_csv)
    geometry = read_csv_rows(paths.geometry_audit_csv)
    validate_stage12_2_inputs(layout, geometry)
    first = layout[0]
    wavelength = flt(first["lambda_nm"])
    height = flt(first["height_nm"])
    period = flt(first["supercell_period_lambda_nm"])
    period_y = flt(first["p_y_nm"])
    rows = []
    for pol, angle in (("x", 0.0), ("y", 90.0)):
        rows.append(
            {
                "run_id": f"stage12_2_h500_k6_forward_{pol}",
                "polarization": pol,
                "polarization_angle_deg": angle,
                "layout_plan_csv": paths.layout_plan_csv.as_posix(),
                "geometry_audit_csv": paths.geometry_audit_csv.as_posix(),
                "phase_amplitude_audit_csv": paths.phase_amplitude_audit_csv.as_posix(),
                "wavelength_nm": wavelength,
                "height_nm": height,
                "supercell_period_nm": period,
                "period_y_nm": period_y,
                "expected_target_order": TARGET_ORDER,
                "expected_theta_deg": expected_theta_deg(TARGET_ORDER, wavelength, period),
                "mode": "minimal_two_input_full_fdtd_validation",
                "status": "planned",
                "notes": "H500 forward K=6 only; no sweep; no reverse; no H600/H700; no CP branch",
            }
        )
    return rows


def validate_stage12_2_inputs(layout: Sequence[dict[str, str]], geometry: Sequence[dict[str, str]]) -> None:
    if len(layout) != K:
        raise ValueError(f"Stage12-2 requires exactly {K} layout rows; got {len(layout)}")
    bins = [int(row["phase_bin_deg"]) for row in layout]
    if bins != [0, 60, 120, 180, 240, 300]:
        raise ValueError(f"Stage12-2 requires forward order [0,60,120,180,240,300]; got {bins}")
    if any(abs(flt(row["height_nm"]) - 500.0) > 1e-6 for row in layout):
        raise ValueError("Stage12-2 is H500 only")
    illegal = [row for row in geometry if str(row.get("geometry_legal", "")).lower() != "true"]
    if illegal:
        raise ValueError("Stage12-2 cannot run: Stage12-1 geometry audit has illegal rows")


def build_model(fdtd: object, layout_rows: Sequence[dict[str, str]], polarization: str) -> None:
    nm = 1e-9
    first = layout_rows[0]
    wavelength_nm = flt(first["lambda_nm"])
    height_nm = flt(first["height_nm"])
    period_x_nm = flt(first["supercell_period_lambda_nm"])
    period_y_nm = flt(first["p_y_nm"])
    center_shift_x_nm = period_x_nm / 2.0

    fdtd.switchtolayout()
    fdtd.deleteall()
    fdtd.addfdtd()
    fdtd.set("dimension", "3D")
    fdtd.set("x", 0)
    fdtd.set("x span", period_x_nm * nm)
    fdtd.set("y", 0)
    fdtd.set("y span", period_y_nm * nm)
    fdtd.set("z min", -500 * nm)
    fdtd.set("z max", (height_nm + 700.0) * nm)
    fdtd.set("x min bc", "Periodic")
    fdtd.set("x max bc", "Periodic")
    fdtd.set("y min bc", "Periodic")
    fdtd.set("y max bc", "Periodic")
    fdtd.set("z min bc", "PML")
    fdtd.set("z max bc", "PML")
    fdtd.set("mesh accuracy", 2)
    fdtd.set("simulation time", 1000e-15)

    for row in layout_rows:
        add_j1(fdtd, row, center_shift_x_nm)
        add_j2(fdtd, row, center_shift_x_nm)

    fdtd.addplane()
    fdtd.set("name", "source")
    fdtd.set("injection axis", "z")
    fdtd.set("direction", "Forward")
    fdtd.set("x", 0)
    fdtd.set("x span", period_x_nm * nm)
    fdtd.set("y", 0)
    fdtd.set("y span", period_y_nm * nm)
    fdtd.set("z", -250 * nm)
    fdtd.set("wavelength start", wavelength_nm * nm)
    fdtd.set("wavelength stop", wavelength_nm * nm)
    fdtd.set("polarization angle", 0 if polarization == "x" else 90)

    fdtd.addpower()
    fdtd.set("name", "T")
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x", 0)
    fdtd.set("x span", period_x_nm * nm)
    fdtd.set("y", 0)
    fdtd.set("y span", period_y_nm * nm)
    fdtd.set("z", (height_nm + 350.0) * nm)


def add_j1(fdtd: object, row: dict[str, str], center_shift_x_nm: float) -> None:
    nm = 1e-9
    shape = row["j1_shape_family"]
    params = json.loads(row["j1_geometry_params"])
    name = f"d{row['supercell_index']}_j1_bin{row['phase_bin_deg']}"
    if shape == "circle":
        fdtd.addcircle()
        fdtd.set("name", name)
        fdtd.set("radius", 0.5 * flt(params.get("diameter_nm")) * nm)
    else:
        fdtd.addrect()
        fdtd.set("name", name)
        if shape == "square":
            side = flt(params.get("side_nm"))
            fdtd.set("x span", side * nm)
            fdtd.set("y span", side * nm)
        else:
            fdtd.set("x span", flt(params.get("length_nm")) * nm)
            fdtd.set("y span", flt(params.get("width_nm")) * nm)
        rotation = flt(params.get("rotation_deg"), 0.0)
        if abs(rotation) > 1e-9:
            fdtd.set("first axis", "z")
            fdtd.set("rotation 1", rotation)
    fdtd.set("x", (flt(row["j1_abs_center_x_nm"]) - center_shift_x_nm) * nm)
    fdtd.set("y", flt(row["j1_abs_center_y_nm"]) * nm)
    fdtd.set("z min", 0)
    fdtd.set("z max", flt(row["height_nm"]) * nm)
    fdtd.set("material", "<Object defined dielectric>")
    fdtd.set("index", 2.6)


def add_j2(fdtd: object, row: dict[str, str], center_shift_x_nm: float) -> None:
    nm = 1e-9
    fdtd.addrect()
    fdtd.set("name", f"d{row['supercell_index']}_j2_bin{row['phase_bin_deg']}")
    fdtd.set("x", (flt(row["j2_abs_center_x_nm"]) - center_shift_x_nm) * nm)
    fdtd.set("y", flt(row["j2_abs_center_y_nm"]) * nm)
    fdtd.set("x span", flt(row["j2_length_nm"]) * nm)
    fdtd.set("y span", flt(row["j2_width_nm"]) * nm)
    fdtd.set("z min", 0)
    fdtd.set("z max", flt(row["height_nm"]) * nm)
    rot = flt(row.get("j2_rotation_deg"), 0.0)
    if abs(rot) > 1e-9:
        fdtd.set("first axis", "z")
        fdtd.set("rotation 1", rot)
    fdtd.set("material", "<Object defined dielectric>")
    fdtd.set("index", 2.6)


def run_one_fdtd(lumapi: object, runtime: object, layout_rows: Sequence[dict[str, str]], run_plan_row: dict[str, object], paths: Stage12Paths, keep_fsp: bool = False) -> tuple[dict[str, object], list[dict[str, object]]]:
    run_id = str(run_plan_row["run_id"])
    polarization = str(run_plan_row["polarization"])
    paths.fdtd_work_dir.mkdir(parents=True, exist_ok=True)
    fsp_path = paths.fdtd_work_dir / f"{run_id}.fsp"
    fdtd = None
    diagnostics: list[str] = []
    order_rows: list[dict[str, object]] = []
    status = "failed"
    note = ""
    try:
        fdtd = lumapi.FDTD(hide=getattr(runtime, "hide_gui", True))
        build_model(fdtd, layout_rows, polarization)
        fdtd.save(str(fsp_path))
        fdtd.close()
        fdtd = None
        fdtd = lumapi.FDTD(hide=getattr(runtime, "hide_gui", True))
        fdtd.load(str(fsp_path))
        fdtd.run()
        raw_rows = extract_fdtd_grating_orders(fdtd, monitor_name="T", K=K, diagnostics=diagnostics)
        order_rows = normalize_order_rows(raw_rows, run_id, polarization, flt(run_plan_row["wavelength_nm"]), flt(run_plan_row["supercell_period_nm"]))
        status = "ok"
    except Exception as exc:
        note = f"{type(exc).__name__}: {exc}\n{''.join(traceback.format_exception(type(exc), exc, exc.__traceback__)).strip()}"
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass
        if fsp_path.exists() and not keep_fsp:
            try:
                fsp_path.unlink()
            except Exception as exc:
                diagnostics.append(f"failed_to_delete_fsp: {type(exc).__name__}: {exc}")
    result = summarize_single_run(run_id, polarization, status, order_rows, str(fsp_path), fsp_path.exists(), diagnostics, note)
    return result, order_rows


def normalize_order_rows(raw_rows: Sequence[dict[str, object]], run_id: str, polarization: str, wavelength_nm: float, period_nm: float) -> list[dict[str, object]]:
    rows = []
    for row in raw_rows:
        order_n = int(round(flt(row.get("order_n"), 0.0)))
        order_m = int(round(flt(row.get("order_m"), 0.0)))
        ux = flt(row.get("expected_ux"))
        theta = math.degrees(math.asin(max(-1.0, min(1.0, ux)))) if not math.isnan(ux) else expected_theta_deg(order_n, wavelength_nm, period_nm)
        rows.append(
            {
                "run_id": run_id,
                "polarization": polarization,
                "order_n": order_n,
                "order_m": order_m,
                "ux": ux,
                "uy": flt(row.get("expected_uy"), 0.0),
                "theta_deg": theta,
                "order_power_fraction_of_transmitted": flt(row.get("order_power_fraction_of_transmitted"), 0.0),
                "total_transmission": flt(row.get("total_transmission"), 0.0),
                "order_power_source_norm": flt(row.get("order_efficiency_source_norm"), 0.0),
                "Ex_order_complex_real": row.get("Ex_order_complex_real", ""),
                "Ex_order_complex_imag": row.get("Ex_order_complex_imag", ""),
                "Ey_order_complex_real": row.get("Ey_order_complex_real", ""),
                "Ey_order_complex_imag": row.get("Ey_order_complex_imag", ""),
                "Ez_order_complex_real": row.get("Ez_order_complex_real", ""),
                "Ez_order_complex_imag": row.get("Ez_order_complex_imag", ""),
            }
        )
    return rows


def summarize_single_run(run_id: str, polarization: str, status: str, order_rows: Sequence[dict[str, object]], fsp_path: str, fsp_retained: bool, diagnostics: Sequence[str], note: str) -> dict[str, object]:
    if status != "ok" or not order_rows:
        return {
            "run_id": run_id,
            "polarization": polarization,
            "fdtd_status": status,
            "fsp_path": fsp_path,
            "fsp_retained": fsp_retained,
            "diagnostics": " | ".join(diagnostics),
            "notes": note[:2000],
        }
    dominant = dominant_order(order_rows)
    plus = order_power(order_rows, TARGET_ORDER)
    zero = order_power(order_rows, 0)
    minus = order_power(order_rows, -1)
    contrast = order_contrast(order_rows, TARGET_ORDER)
    theta = flt(dominant.get("theta_deg"))
    return {
        "run_id": run_id,
        "polarization": polarization,
        "fdtd_status": status,
        "total_transmission": flt(dominant.get("total_transmission"), 0.0),
        "dominant_order_n": dominant["order_n"],
        "dominant_order_m": dominant["order_m"],
        "dominant_order_power": dominant["order_power_source_norm"],
        "dominant_theta_deg": theta,
        "target_plus1_power": plus,
        "zero_order_power": zero,
        "minus1_order_power": minus,
        "order_contrast_plus1_vs_next": contrast,
        "plus1_direction_consistent": abs(theta - EXPECTED_THETA_DEG) <= 2.0 if int(dominant["order_n"]) == TARGET_ORDER else False,
        "fsp_path": fsp_path,
        "fsp_retained": fsp_retained,
        "diagnostics": " | ".join(diagnostics),
        "notes": note,
    }


def dominant_order(order_rows: Sequence[dict[str, object]]) -> dict[str, object]:
    return max(order_rows, key=lambda row: flt(row.get("order_power_source_norm"), 0.0))


def order_power(order_rows: Sequence[dict[str, object]], order_n: int) -> float:
    matches = [row for row in order_rows if int(row["order_n"]) == order_n]
    if not matches:
        return 0.0
    return max(flt(row.get("order_power_source_norm"), 0.0) for row in matches)


def order_contrast(order_rows: Sequence[dict[str, object]], target_order: int = TARGET_ORDER) -> float:
    target = order_power(order_rows, target_order)
    others = [flt(row.get("order_power_source_norm"), 0.0) for row in order_rows if int(row["order_n"]) != target_order]
    competitor = max(others) if others else 0.0
    return target / max(competitor, EPS)


def compute_selectivity_summary(result_rows: Sequence[dict[str, object]], order_rows: Sequence[dict[str, object]], phase_rows: Sequence[dict[str, str]]) -> list[dict[str, object]]:
    x_orders = [row for row in order_rows if row["polarization"] == "x"]
    y_orders = [row for row in order_rows if row["polarization"] == "y"]
    x_plus = order_power(x_orders, TARGET_ORDER)
    y_plus = order_power(y_orders, TARGET_ORDER)
    y_total = max((flt(row.get("total_transmission"), 0.0) for row in y_orders), default=0.0)
    leakage = y_plus if y_plus > 0 else y_total
    ratio = x_plus / max(leakage, EPS)
    library_ratios = [flt(row["conversion_to_leakage_ratio"]) for row in phase_rows]
    library_txs = [flt(row["Tx"]) for row in phase_rows]
    weakest = min(phase_rows, key=lambda row: flt(row["Tx"]))
    pass_x = any(row.get("polarization") == "x" and row.get("fdtd_status") == "ok" and int(row.get("dominant_order_n", 999)) == TARGET_ORDER and bool_from(row.get("plus1_direction_consistent")) for row in result_rows)
    pass_ratio = ratio >= 6.0
    return [
        {"metric": "effective_target_power", "value": x_plus, "notes": "x-input +1 order source-normalized power"},
        {"metric": "effective_blocked_leakage", "value": leakage, "notes": "y-input +1 order power if available, otherwise y total transmission"},
        {"metric": "y_input_plus1_power", "value": y_plus, "notes": "blocked-channel +1 leakage"},
        {"metric": "y_input_total_transmission", "value": y_total, "notes": "total transmitted/leaked power for y-LP input"},
        {"metric": "effective_selectivity_ratio", "value": ratio, "notes": "effective_target_power / effective_blocked_leakage"},
        {"metric": "single_dimer_library_min_ratio", "value": min(library_ratios), "notes": "minimum frozen single-dimer ratio"},
        {"metric": "single_dimer_library_mean_ratio", "value": sum(library_ratios) / len(library_ratios), "notes": "mean frozen single-dimer ratio"},
        {"metric": "single_dimer_library_min_Tx", "value": min(library_txs), "notes": "minimum frozen single-dimer Tx"},
        {"metric": "key_risk_bin", "value": weakest["phase_bin_deg"], "notes": "weakest Tx bin in Stage12-1 phase audit"},
        {"metric": "x_dominant_plus1_pass", "value": pass_x, "notes": "x-LP dominant order is +1 and near +10 deg"},
        {"metric": "selectivity_ratio_ge_6_pass", "value": pass_ratio, "notes": "effective selectivity ratio >= 6"},
        {"metric": "overall_farfield_audit_pass", "value": pass_x and pass_ratio, "notes": "success criteria summary; no steering completion claim beyond this audit"},
    ]


def write_farfield_audit(path: Path, result_rows: Sequence[dict[str, object]], selectivity_rows: Sequence[dict[str, object]]) -> None:
    metrics = {row["metric"]: row["value"] for row in selectivity_rows}
    x = next((row for row in result_rows if row.get("polarization") == "x"), {})
    y = next((row for row in result_rows if row.get("polarization") == "y"), {})
    passed = bool_from(metrics.get("overall_farfield_audit_pass"))
    lines = [
        "# Stage12-2 H500 LP-APCD K=6 Forward Far-Field Audit",
        "",
        "## Boundary",
        "",
        "- This was one minimal H500 forward K=6 validation: x-LP and y-LP inputs only.",
        "- No sweep was run.",
        "- No reverse-order FDTD was run.",
        "- No H600/H700 was run.",
        "- No CP branch was run.",
        "- LP steering is not claimed unless this audit passes.",
        "",
        "## x-LP Target Input",
        "",
        f"- FDTD status: `{x.get('fdtd_status', '')}`.",
        f"- Dominant order: `{x.get('dominant_order_n', '')}`.",
        f"- +1 power: `{x.get('target_plus1_power', '')}`.",
        f"- 0 order power: `{x.get('zero_order_power', '')}`.",
        f"- -1 order power: `{x.get('minus1_order_power', '')}`.",
        f"- Estimated dominant angle: `{x.get('dominant_theta_deg', '')}` deg.",
        f"- +1 contrast: `{x.get('order_contrast_plus1_vs_next', '')}`.",
        f"- +10 deg direction consistency: `{x.get('plus1_direction_consistent', '')}`.",
        "",
        "## y-LP Blocked Input",
        "",
        f"- FDTD status: `{y.get('fdtd_status', '')}`.",
        f"- Total transmitted/leaked power: `{y.get('total_transmission', '')}`.",
        f"- +1 leakage power: `{metrics.get('y_input_plus1_power', '')}`.",
        f"- Dominant leakage order: `{y.get('dominant_order_n', '')}`.",
        "",
        "## Effective Metrics",
        "",
        f"- effective_target_power: `{metrics.get('effective_target_power', '')}`.",
        f"- effective_blocked_leakage: `{metrics.get('effective_blocked_leakage', '')}`.",
        f"- effective_selectivity_ratio: `{metrics.get('effective_selectivity_ratio', '')}`.",
        f"- single-dimer library min ratio: `{metrics.get('single_dimer_library_min_ratio', '')}`.",
        f"- key risk bin: `{metrics.get('key_risk_bin', '')}` deg.",
        "- The 240 deg bin and 20 nm clearance region remain the first diagnostic targets if the ratio or far-field order fails.",
        "",
        "## Pass/Fail",
        "",
        f"- x-LP dominant +1 and near +10 deg: `{metrics.get('x_dominant_plus1_pass', '')}`.",
        f"- effective selectivity ratio >= 6: `{metrics.get('selectivity_ratio_ge_6_pass', '')}`.",
        f"- far-field audit pass: `{passed}`.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_before_after(path: Path, selectivity_rows: Sequence[dict[str, object]]) -> None:
    metrics = {row["metric"]: row["value"] for row in selectivity_rows}
    lines = [
        "# Stage12-2 Before/After Versus Analytic",
        "",
        "## Before Stage12-2",
        "",
        "- Stage12-0 analytic forward order predicted dominant +1 order, relative strength 0.983731, contrast 158.057817, theta about +10 deg.",
        "- Stage12-1 geometry audit was legal with minimum clearance 20.000000 nm and minimum neighboring-dimer clearance 76.907786 nm.",
        "",
        "## After Stage12-2 FDTD",
        "",
        f"- effective_target_power: `{metrics.get('effective_target_power', '')}`.",
        f"- effective_blocked_leakage: `{metrics.get('effective_blocked_leakage', '')}`.",
        f"- effective_selectivity_ratio: `{metrics.get('effective_selectivity_ratio', '')}`.",
        f"- far-field audit pass: `{metrics.get('overall_farfield_audit_pass', '')}`.",
        "",
        "## Boundary",
        "",
        "This compares one minimal full-FDTD validation against the analytic/layout preflight. It is not a sweep and does not include reverse, H600/H700, or CP branch runs.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def expected_theta_deg(order: int, wavelength_nm: float, period_nm: float) -> float:
    argument = order * wavelength_nm / period_nm
    if abs(argument) > 1:
        return math.nan
    return math.degrees(math.asin(argument))


def bool_from(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "pass"}
