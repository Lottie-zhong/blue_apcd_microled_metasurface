from __future__ import annotations

import cmath
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from metasurface.stage12_10a_240bin_refinement import (
    bool_from,
    estimated_leakage,
    flt,
    fmt,
    load_stage11_runner,
    nearest_bin,
    read_csv,
    wrap180,
    write_csv,
)

OUTPUT_DIR_NAME = "stage12_12a_h500_lp_6bin_spectral_audit"
WAVELENGTH_GRID_NM = [447, 448, 449, 450, 451, 452, 453]
BIN_ORDER = [0, 60, 120, 180, 240, 300]
FWHM_VALUES_NM = [6, 4, 3, 2]
EPS = 1e-12

RUN_MATRIX_FIELDS = [
    "run_id", "wavelength_nm", "bin_deg", "candidate_id", "dimer_case_id",
    "polarizations", "height_nm", "lambda_nm", "geometry_legal", "status", "notes",
]
RESULT_FIELDS = [
    "wavelength_nm", "bin_deg", "candidate_id", "dimer_case_id", "fdtd_status",
    "t_xx_amplitude", "t_xx_phase_deg", "t_yy_leakage_amplitude_or_power",
    "t_yy_amp", "t_yy_power", "t_xy_cross_leakage", "t_yx_cross_leakage",
    "selected_channel_phase_deg", "selected_channel_phase_error_deg",
    "nearest_bin_deg", "conversion_to_leakage_ratio", "Tx", "target_conversion",
    "blocked_y_total_leakage", "matrix_error", "geometry_legal", "minimum_clearance_nm",
    "result_csv", "source_file", "x_result_csv", "y_result_csv", "notes",
]
PHASE_STEP_FIELDS = [
    "wavelength_nm", "step_label", "from_bin_deg", "to_bin_deg", "phase_from_deg",
    "phase_to_deg", "phase_step_deg", "phase_step_error_from_60_deg",
    "rms_phase_step_error_deg", "max_phase_step_error_deg", "weakest_bin_by_ratio",
    "weakest_bin_by_leakage", "bin120_ratio", "bin240_ratio", "bin120_warning", "bin240_warning",
]
WEIGHTED_FIELDS = [
    "fwhm_nm", "row_type", "bin_deg", "weight_sum", "weighted_Tx", "weighted_ratio",
    "weighted_leakage", "weighted_matrix_error", "weighted_phase_error_deg",
    "weighted_phase_step_rms_error_deg", "weighted_phase_step_max_error_deg",
    "weakest_bin_by_ratio", "weakest_bin_by_leakage", "notes",
]
WEAK_FIELDS = [
    "wavelength_nm", "weakest_bin_by_ratio", "weakest_ratio", "weakest_bin_by_leakage",
    "max_leakage", "bin120_ratio", "bin240_ratio", "bin120_warning", "bin240_warning",
    "nearest_bin_changed", "phase_step_rms_error_deg", "phase_step_max_error_deg", "notes",
]


@dataclass(frozen=True)
class Stage12_12APaths:
    freeze_library_csv: Path
    layout_plan_csv: Path
    output_dir: Path
    fdtd_work_dir: Path


def phase_distance_deg(a: float, b: float) -> float:
    return abs(wrap180(a - b))


def generate_wavelength_grid(start_nm: int = 447, stop_nm: int = 453) -> list[int]:
    if stop_nm < start_nm:
        raise ValueError("stop_nm must be >= start_nm")
    return list(range(start_nm, stop_nm + 1))


def gaussian_weights(wavelengths_nm: Sequence[float], fwhm_nm: float, center_nm: float = 450.0) -> list[float]:
    if fwhm_nm <= 0:
        raise ValueError("fwhm_nm must be positive")
    raw = [math.exp(-4.0 * math.log(2.0) * ((float(w) - center_nm) / fwhm_nm) ** 2) for w in wavelengths_nm]
    total = sum(raw)
    if total <= 0:
        raise ValueError("Gaussian weight sum is zero")
    return [v / total for v in raw]


def adjacent_phase_steps(phases_by_bin: dict[int, float]) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    for i, source_bin in enumerate(BIN_ORDER):
        target_bin = BIN_ORDER[(i + 1) % len(BIN_ORDER)]
        phase_from = phases_by_bin[source_bin]
        phase_to = phases_by_bin[target_bin]
        step = (phase_to - phase_from) % 360.0
        err = wrap180(step - 60.0)
        rows.append({
            "step_label": f"{source_bin}->{target_bin}",
            "from_bin_deg": source_bin,
            "to_bin_deg": target_bin,
            "phase_from_deg": phase_from,
            "phase_to_deg": phase_to,
            "phase_step_deg": step,
            "phase_step_error_from_60_deg": err,
        })
    return rows


def rms(values: Sequence[float]) -> float:
    vals = [float(v) for v in values if not math.isnan(float(v))]
    return math.sqrt(sum(v * v for v in vals) / len(vals)) if vals else math.nan


def weak_bin_summary(rows: Sequence[dict]) -> dict[str, object]:
    ok = [r for r in rows if str(r.get("fdtd_status")) == "ok"]
    if not ok:
        return {
            "weakest_bin_by_ratio": "", "weakest_ratio": math.nan,
            "weakest_bin_by_leakage": "", "max_leakage": math.nan,
            "bin120_ratio": math.nan, "bin240_ratio": math.nan,
            "bin120_warning": True, "bin240_warning": True,
        }
    by_ratio = min(ok, key=lambda r: flt(r.get("conversion_to_leakage_ratio"), math.inf))
    by_leak = max(ok, key=lambda r: flt(r.get("blocked_y_total_leakage"), -math.inf))
    b120 = next((r for r in ok if int(flt(r.get("bin_deg"))) == 120), {})
    b240 = next((r for r in ok if int(flt(r.get("bin_deg"))) == 240), {})
    b120_ratio = flt(b120.get("conversion_to_leakage_ratio"))
    b240_ratio = flt(b240.get("conversion_to_leakage_ratio"))
    return {
        "weakest_bin_by_ratio": int(flt(by_ratio.get("bin_deg"))),
        "weakest_ratio": flt(by_ratio.get("conversion_to_leakage_ratio")),
        "weakest_bin_by_leakage": int(flt(by_leak.get("bin_deg"))),
        "max_leakage": flt(by_leak.get("blocked_y_total_leakage")),
        "bin120_ratio": b120_ratio,
        "bin240_ratio": b240_ratio,
        "bin120_warning": math.isnan(b120_ratio) or b120_ratio < 6.0,
        "bin240_warning": math.isnan(b240_ratio) or b240_ratio < 6.0,
    }


def complex_from_amp_phase(amp: object, phase_deg: object) -> complex:
    a = flt(amp, 0.0)
    p = math.radians(flt(phase_deg, 0.0))
    return a * complex(math.cos(p), math.sin(p))


def circular_mean_deg(values_deg: Sequence[float], weights: Sequence[float]) -> float:
    z = sum(w * complex(math.cos(math.radians(v)), math.sin(math.radians(v))) for v, w in zip(values_deg, weights))
    if abs(z) <= EPS:
        return math.nan
    return math.degrees(cmath.phase(z)) % 360.0


def load_official_rows(paths: Stage12_12APaths) -> list[dict[str, str]]:
    library = {row["candidate_id"]: row for row in read_csv(paths.freeze_library_csv)}
    layout_rows = read_csv(paths.layout_plan_csv)
    selected = []
    for bin_deg in BIN_ORDER:
        row = next((r for r in layout_rows if int(flt(r.get("phase_bin_deg"))) == bin_deg), None)
        if row is None:
            raise FileNotFoundError(f"Missing Stage12-1 layout row for bin {bin_deg}")
        cid = row["candidate_id"]
        merged = {**row, **{f"library_{k}": v for k, v in library.get(cid, {}).items()}}
        merged["bin_deg"] = str(bin_deg)
        merged["static_output_phase_deg"] = str(bin_deg)
        merged["static_predicted_ratio"] = library.get(cid, {}).get("conversion_to_leakage_ratio", row.get("static_predicted_ratio", ""))
        merged["source_pair_id"] = row.get("source_plan_id", cid)
        selected.append(merged)
    return selected


def build_run_matrix(paths: Stage12_12APaths) -> list[dict[str, object]]:
    rows = []
    for base in load_official_rows(paths):
        cid = base["candidate_id"]
        bin_deg = int(flt(base["bin_deg"]))
        for wavelength in WAVELENGTH_GRID_NM:
            run_id = f"stage12_12a_bin{bin_deg:03d}_{wavelength}nm"
            case_id = f"{cid}_WL{wavelength}NM"
            row = dict(base)
            row.update({
                "run_id": run_id,
                "dimer_case_id": case_id,
                "candidate_id": cid,
                "wavelength_nm": wavelength,
                "lambda_nm": f"{wavelength:.6f}",
                "polarizations": "x,y",
                "status": "planned",
                "notes": "Stage12-12A single-dimer spectral audit; no K6, no DBR, no RCLED, no dipoles.",
            })
            rows.append(row)
    return rows


def matrix_error(tx: float, x_cross: float, y_total: float) -> float:
    return math.sqrt(max(x_cross, 0.0) + max(y_total, 0.0)) / max(math.sqrt(max(tx, 0.0)), EPS)


def spectral_metric_from_combined(combined: dict, plan_row: dict) -> dict[str, object]:
    status = combined.get("fdtd_status", "failed")
    tx = flt(combined.get("target_x_power"))
    y_total = flt(combined.get("y_input_total_leak_power"))
    x_cross = flt(combined.get("x_input_cross_leak_power"))
    ratio = flt(combined.get("dimer_selectivity_ratio"))
    phase = flt(combined.get("dimer_output_phase_deg"))
    bin_deg = int(flt(plan_row["bin_deg"]))
    t_yy_amp = flt(combined.get("t_yy_amp"))
    row = {
        "wavelength_nm": plan_row["wavelength_nm"],
        "bin_deg": bin_deg,
        "candidate_id": plan_row["candidate_id"],
        "dimer_case_id": plan_row["dimer_case_id"],
        "fdtd_status": status,
        "t_xx_amplitude": combined.get("t_xx_amp", ""),
        "t_xx_phase_deg": combined.get("t_xx_phase_deg", ""),
        "t_yy_leakage_amplitude_or_power": combined.get("t_yy_amp", ""),
        "t_yy_amp": combined.get("t_yy_amp", ""),
        "t_yy_power": fmt(t_yy_amp * t_yy_amp) if not math.isnan(t_yy_amp) else "",
        "t_xy_cross_leakage": combined.get("t_xy_amp", ""),
        "t_yx_cross_leakage": combined.get("t_yx_amp", ""),
        "selected_channel_phase_deg": fmt(phase),
        "selected_channel_phase_error_deg": fmt(phase_distance_deg(phase, bin_deg)) if not math.isnan(phase) else "",
        "nearest_bin_deg": nearest_bin(phase) if not math.isnan(phase) else "",
        "conversion_to_leakage_ratio": fmt(ratio),
        "Tx": fmt(tx),
        "target_conversion": fmt(tx),
        "blocked_y_total_leakage": fmt(y_total),
        "matrix_error": fmt(matrix_error(tx, x_cross, y_total)) if not math.isnan(tx) else "",
        "geometry_legal": plan_row.get("geometry_legal", ""),
        "minimum_clearance_nm": plan_row.get("minimum_clearance_nm", plan_row.get("dimer_gap_nm", "")),
        "result_csv": plan_row.get("_result_csv", ""),
        "source_file": plan_row.get("source_file", plan_row.get("library_source_file", "")),
        "x_result_csv": combined.get("x_result_csv", ""),
        "y_result_csv": combined.get("y_result_csv", ""),
        "notes": combined.get("notes", ""),
    }
    return row


def phase_step_rows(results: Sequence[dict]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for wavelength in WAVELENGTH_GRID_NM:
        rows = [r for r in results if int(flt(r.get("wavelength_nm"))) == wavelength and r.get("fdtd_status") == "ok"]
        if len(rows) != 6:
            continue
        phases = {int(flt(r["bin_deg"])): flt(r["selected_channel_phase_deg"]) for r in rows}
        steps = adjacent_phase_steps(phases)
        errs = [flt(s["phase_step_error_from_60_deg"]) for s in steps]
        weak = weak_bin_summary(rows)
        nearest_changed = any(int(flt(r.get("nearest_bin_deg"), -1)) != int(flt(r.get("bin_deg"), -2)) for r in rows)
        for step in steps:
            out.append({
                "wavelength_nm": wavelength,
                **step,
                "rms_phase_step_error_deg": rms(errs),
                "max_phase_step_error_deg": max(abs(e) for e in errs),
                "weakest_bin_by_ratio": weak["weakest_bin_by_ratio"],
                "weakest_bin_by_leakage": weak["weakest_bin_by_leakage"],
                "bin120_ratio": weak["bin120_ratio"],
                "bin240_ratio": weak["bin240_ratio"],
                "bin120_warning": weak["bin120_warning"],
                "bin240_warning": weak["bin240_warning"],
                "nearest_bin_changed": nearest_changed,
            })
    return out


def weak_rows(results: Sequence[dict], step_rows: Sequence[dict]) -> list[dict[str, object]]:
    out = []
    for wavelength in WAVELENGTH_GRID_NM:
        rows = [r for r in results if int(flt(r.get("wavelength_nm"))) == wavelength]
        weak = weak_bin_summary(rows)
        steps = [s for s in step_rows if int(flt(s.get("wavelength_nm"))) == wavelength]
        nearest_changed = any(str(r.get("fdtd_status")) == "ok" and int(flt(r.get("nearest_bin_deg"), -1)) != int(flt(r.get("bin_deg"), -2)) for r in rows)
        out.append({
            "wavelength_nm": wavelength,
            **weak,
            "nearest_bin_changed": nearest_changed,
            "phase_step_rms_error_deg": flt(steps[0].get("rms_phase_step_error_deg")) if steps else math.nan,
            "phase_step_max_error_deg": flt(steps[0].get("max_phase_step_error_deg")) if steps else math.nan,
            "notes": "warning" if nearest_changed or weak.get("bin120_warning") or weak.get("bin240_warning") else "pass_like",
        })
    return out


def weighted_metrics(results: Sequence[dict], step_rows: Sequence[dict]) -> list[dict[str, object]]:
    out = []
    wavelengths = [float(w) for w in WAVELENGTH_GRID_NM]
    for fwhm in FWHM_VALUES_NM:
        weights = gaussian_weights(wavelengths, float(fwhm))
        by_w = dict(zip(WAVELENGTH_GRID_NM, weights))
        per_bin = []
        for bin_deg in BIN_ORDER:
            rows = [r for r in results if int(flt(r.get("bin_deg"))) == bin_deg and r.get("fdtd_status") == "ok"]
            used = [(r, by_w[int(flt(r["wavelength_nm"]))]) for r in rows]
            wsum = sum(w for _, w in used)
            if wsum <= 0:
                continue
            norm = [w / wsum for _, w in used]
            phases = [flt(r["selected_channel_phase_deg"]) for r, _ in used]
            phase_mean = circular_mean_deg(phases, norm)
            row = {
                "fwhm_nm": fwhm,
                "row_type": "bin",
                "bin_deg": bin_deg,
                "weight_sum": wsum,
                "weighted_Tx": sum(flt(r.get("Tx"), 0) * nw for (r, _), nw in zip(used, norm)),
                "weighted_ratio": sum(flt(r.get("conversion_to_leakage_ratio"), 0) * nw for (r, _), nw in zip(used, norm)),
                "weighted_leakage": sum(flt(r.get("blocked_y_total_leakage"), 0) * nw for (r, _), nw in zip(used, norm)),
                "weighted_matrix_error": sum(flt(r.get("matrix_error"), 0) * nw for (r, _), nw in zip(used, norm)),
                "weighted_phase_error_deg": phase_distance_deg(phase_mean, bin_deg) if not math.isnan(phase_mean) else math.nan,
                "weighted_phase_step_rms_error_deg": "",
                "weighted_phase_step_max_error_deg": "",
                "weakest_bin_by_ratio": "",
                "weakest_bin_by_leakage": "",
                "notes": "Gaussian weighted bin metric",
            }
            per_bin.append(row)
            out.append(row)
        if per_bin:
            step_rms = []
            step_max = []
            for wavelength in WAVELENGTH_GRID_NM:
                steps = [s for s in step_rows if int(flt(s.get("wavelength_nm"))) == wavelength]
                if steps:
                    step_rms.append(flt(steps[0].get("rms_phase_step_error_deg")) * by_w[wavelength])
                    step_max.append(flt(steps[0].get("max_phase_step_error_deg")) * by_w[wavelength])
            weakest_ratio = min(per_bin, key=lambda r: flt(r.get("weighted_ratio"), math.inf))
            weakest_leak = max(per_bin, key=lambda r: flt(r.get("weighted_leakage"), -math.inf))
            out.append({
                "fwhm_nm": fwhm,
                "row_type": "aggregate",
                "bin_deg": "all",
                "weight_sum": sum(weights),
                "weighted_Tx": sum(flt(r.get("weighted_Tx"), 0) for r in per_bin) / len(per_bin),
                "weighted_ratio": min(flt(r.get("weighted_ratio"), math.inf) for r in per_bin),
                "weighted_leakage": max(flt(r.get("weighted_leakage"), -math.inf) for r in per_bin),
                "weighted_matrix_error": max(flt(r.get("weighted_matrix_error"), -math.inf) for r in per_bin),
                "weighted_phase_error_deg": rms([flt(r.get("weighted_phase_error_deg")) for r in per_bin]),
                "weighted_phase_step_rms_error_deg": sum(step_rms),
                "weighted_phase_step_max_error_deg": sum(step_max),
                "weakest_bin_by_ratio": weakest_ratio["bin_deg"],
                "weakest_bin_by_leakage": weakest_leak["bin_deg"],
                "notes": "Gaussian weighted aggregate; weighted_ratio is six-bin floor, weighted_leakage is six-bin max",
            })
    return out


def write_markdown(paths: Stage12_12APaths, results: Sequence[dict], step_rows_: Sequence[dict], weak_rows_: Sequence[dict], weighted_rows: Sequence[dict], total_runs: int) -> None:
    ok_pairs = [r for r in results if r.get("fdtd_status") == "ok"]
    complete_bins = len(ok_pairs) == len(BIN_ORDER) * len(WAVELENGTH_GRID_NM)
    nearest_changed = any(bool_from(r.get("nearest_bin_changed")) for r in weak_rows_)
    edge_warning = any(
        bool_from(r.get("bin120_warning")) or bool_from(r.get("bin240_warning")) or flt(r.get("weakest_ratio"), math.inf) < 3.0
        for r in weak_rows_
    )
    worst = max(weak_rows_, key=lambda r: flt(r.get("phase_step_rms_error_deg"), -math.inf)) if weak_rows_ else {}
    weakest = min(ok_pairs, key=lambda r: flt(r.get("conversion_to_leakage_ratio"), math.inf)) if ok_pairs else {}
    fwhm6 = next((r for r in weighted_rows if r.get("row_type") == "aggregate" and int(flt(r.get("fwhm_nm"))) == 6), {})
    pass_like = complete_bins and not nearest_changed and not edge_warning and flt(fwhm6.get("weighted_ratio"), 0) >= 6.0
    summary = [
        "# Stage12-12A H500 LP-APCD Six-Bin Spectral Audit",
        "",
        "## Boundary",
        "",
        "- This is a metasurface-only, single-dimer / phase-bin spectral audit.",
        "- No K=6 FDTD, no DBR, no RCLED, no dipoles, no finite patch, and no geometry optimization were run.",
        "- Separate single-wavelength points were used for 447, 448, 449, 450, 451, 452, and 453 nm.",
        "",
        "## Run Summary",
        "",
        f"- Wavelength grid: `{WAVELENGTH_GRID_NM}` nm.",
        f"- Bin count: `{len(BIN_ORDER)}`.",
        f"- Total FDTD runs: `{total_runs}` (x-LP and y-LP for each bin/wavelength point).",
        f"- Completed bin-wavelength pairs: `{len(ok_pairs)}` / `{len(BIN_ORDER) * len(WAVELENGTH_GRID_NM)}`.",
        f"- All six bins completed across wavelengths: `{complete_bins}`.",
        "",
        "## Spectral Interpretation",
        "",
        f"- Nearest-bin changes observed: `{nearest_changed}`.",
        f"- Worst wavelength by phase-step RMS error: `{worst.get('wavelength_nm', '')}` nm.",
        f"- Weakest bin across wavelength by ratio: `{weakest.get('bin_deg', '')}` at `{weakest.get('wavelength_nm', '')}` nm, ratio `{weakest.get('conversion_to_leakage_ratio', '')}`.",
        f"- FWHM=6 nm weighted six-bin ratio floor: `{fwhm6.get('weighted_ratio', '')}`.",
        f"- FWHM=6 nm weighted max leakage: `{fwhm6.get('weighted_leakage', '')}`.",
        "",
        "## Required Statements",
        "",
        f"- Each bin remains usable across 447-453 nm: `{complete_bins and not nearest_changed}`.",
        f"- Relative 60 deg phase-step condition remains stable enough for a next K=6 spectral validation: `{pass_like}`.",
        f"- 120 deg or 240 deg spectral bottleneck warning: `{edge_warning}`.",
        f"- 447-453 nm appears safe for K6 spectral steering validation: `{pass_like}`.",
        f"- Stage12-12B K6 spectral validation recommended: `{pass_like}`.",
    ]
    paths.output_dir.joinpath("stage12_12a_spectral_audit_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    recommendation = [
        "# Stage12-12A Next Recommendation",
        "",
        ("Proceed to Stage12-12B K=6 spectral steering validation over the same 447-453 nm grid." if pass_like else "Do not proceed directly to broad K=6 spectral validation without reviewing weak bins and edge wavelengths."),
        "Because edge-wavelength warnings can dominate this audit, test narrower windows such as 448-452 nm or 449-451 nm before any K6 spectral or Stage13 dipole-source / DBR coupling work.",
        "Boundary: single-dimer spectral audit only; no K6, no DBR, no RCLED, no dipoles, no finite patch, no optimization.",
    ]
    paths.output_dir.joinpath("stage12_12a_next_recommendation.md").write_text("\n".join(recommendation) + "\n", encoding="utf-8")


def cleanup_fsp_files(combined: dict) -> None:
    for key in ("x_fsp", "y_fsp"):
        path = combined.get(key)
        if path:
            try:
                Path(str(path)).unlink(missing_ok=True)
            except Exception:
                pass




def summarize_existing_stage12_12a(paths: Stage12_12APaths) -> dict[str, object]:
    spectral_rows = read_csv(paths.output_dir / "stage12_12a_6bin_spectral_results.csv")
    steps = phase_step_rows(spectral_rows)
    weak = weak_rows(spectral_rows, steps)
    weighted = weighted_metrics(spectral_rows, steps)
    write_csv(paths.output_dir / "stage12_12a_phase_step_vs_wavelength.csv", steps, PHASE_STEP_FIELDS)
    write_csv(paths.output_dir / "stage12_12a_weak_bin_spectral_summary.csv", weak, WEAK_FIELDS)
    write_csv(paths.output_dir / "stage12_12a_weighted_6bin_metrics.csv", weighted, WEIGHTED_FIELDS)
    total_runs = 2 * len(spectral_rows)
    write_markdown(paths, spectral_rows, steps, weak, weighted, total_runs)
    completed_pairs = sum(1 for r in spectral_rows if r.get("fdtd_status") == "ok")
    worst = max(weak, key=lambda r: flt(r.get("phase_step_rms_error_deg"), -math.inf)) if weak else {}
    ok_rows = [r for r in spectral_rows if r.get("fdtd_status") == "ok"]
    weakest = min(ok_rows, key=lambda r: flt(r.get("conversion_to_leakage_ratio"), math.inf), default={})
    fwhm6 = next((r for r in weighted if r.get("row_type") == "aggregate" and int(flt(r.get("fwhm_nm"))) == 6), {})
    edge_warning = any(bool_from(r.get("bin120_warning")) or bool_from(r.get("bin240_warning")) or flt(r.get("weakest_ratio"), math.inf) < 3.0 for r in weak)
    return {
        "output_dir": str(paths.output_dir),
        "wavelength_grid": WAVELENGTH_GRID_NM,
        "total_fdtd_runs": total_runs,
        "completed_pairs": completed_pairs,
        "all_six_bins_completed": completed_pairs == len(BIN_ORDER) * len(WAVELENGTH_GRID_NM),
        "worst_wavelength_nm": worst.get("wavelength_nm", ""),
        "weakest_bin": weakest.get("bin_deg", ""),
        "weakest_bin_wavelength_nm": weakest.get("wavelength_nm", ""),
        "weakest_bin_ratio": weakest.get("conversion_to_leakage_ratio", ""),
        "fwhm6_ratio_floor": fwhm6.get("weighted_ratio", ""),
        "fwhm6_max_leakage": fwhm6.get("weighted_leakage", ""),
        "stage12_12b_recommended": False if edge_warning else bool(fwhm6) and completed_pairs == len(BIN_ORDER) * len(WAVELENGTH_GRID_NM) and flt(fwhm6.get("weighted_ratio"), 0) >= 6.0,
    }

def run_stage12_12a(repo_root: Path, paths: Stage12_12APaths, runtime_path: str = "configs/runtime.yaml", cleanup_fsp: bool = True, dry_run: bool = False) -> dict[str, object]:
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    paths.fdtd_work_dir.mkdir(parents=True, exist_ok=True)
    run_rows = build_run_matrix(paths)
    write_csv(paths.output_dir / "stage12_12a_6bin_spectral_run_matrix.csv", run_rows, RUN_MATRIX_FIELDS)
    if dry_run:
        write_markdown(paths, [], [], [], [], 0)
        return {"output_dir": str(paths.output_dir), "wavelength_grid": WAVELENGTH_GRID_NM, "total_fdtd_runs": 0, "completed_pairs": 0, "dry_run": True}
    runner = load_stage11_runner(repo_root)
    runner.FDTD_DIR = paths.fdtd_work_dir
    runner.RESULT_CSV = paths.output_dir / "stage12_12a_raw_dimer_spectral_results.csv"
    runner.SUMMARY_MD = paths.output_dir / "stage12_12a_raw_dimer_spectral_summary.md"
    runtime = runner.load_runtime_config(runtime_path)
    lumapi = runner.import_lumapi(runtime)
    combined_rows = []
    spectral_rows = []
    total_runs = 0
    for row in run_rows:
        x = runner.run_one(lumapi, runtime, row, "x")
        total_runs += 1
        y = runner.run_one(lumapi, runtime, row, "y")
        total_runs += 1
        combined = runner.combine(row, x, y)
        combined_rows.append(combined)
        metric = spectral_metric_from_combined(combined, {**row, "_result_csv": str(runner.RESULT_CSV)})
        spectral_rows.append(metric)
        runner.write_csv(runner.RESULT_CSV, combined_rows, runner.RESULT_FIELDS)
        write_csv(paths.output_dir / "stage12_12a_6bin_spectral_results.csv", spectral_rows, RESULT_FIELDS)
        if cleanup_fsp:
            cleanup_fsp_files(combined)
    steps = phase_step_rows(spectral_rows)
    weak = weak_rows(spectral_rows, steps)
    weighted = weighted_metrics(spectral_rows, steps)
    write_csv(paths.output_dir / "stage12_12a_phase_step_vs_wavelength.csv", steps, PHASE_STEP_FIELDS)
    write_csv(paths.output_dir / "stage12_12a_weak_bin_spectral_summary.csv", weak, WEAK_FIELDS)
    write_csv(paths.output_dir / "stage12_12a_weighted_6bin_metrics.csv", weighted, WEIGHTED_FIELDS)
    write_markdown(paths, spectral_rows, steps, weak, weighted, total_runs)
    completed_pairs = sum(1 for r in spectral_rows if r.get("fdtd_status") == "ok")
    worst = max(weak, key=lambda r: flt(r.get("phase_step_rms_error_deg"), -math.inf)) if weak else {}
    weakest = min([r for r in spectral_rows if r.get("fdtd_status") == "ok"], key=lambda r: flt(r.get("conversion_to_leakage_ratio"), math.inf), default={})
    fwhm6 = next((r for r in weighted if r.get("row_type") == "aggregate" and int(flt(r.get("fwhm_nm"))) == 6), {})
    return {
        "output_dir": str(paths.output_dir),
        "wavelength_grid": WAVELENGTH_GRID_NM,
        "total_fdtd_runs": total_runs,
        "completed_pairs": completed_pairs,
        "all_six_bins_completed": completed_pairs == len(BIN_ORDER) * len(WAVELENGTH_GRID_NM),
        "worst_wavelength_nm": worst.get("wavelength_nm", ""),
        "weakest_bin": weakest.get("bin_deg", ""),
        "weakest_bin_wavelength_nm": weakest.get("wavelength_nm", ""),
        "weakest_bin_ratio": weakest.get("conversion_to_leakage_ratio", ""),
        "fwhm6_ratio_floor": fwhm6.get("weighted_ratio", ""),
        "fwhm6_max_leakage": fwhm6.get("weighted_leakage", ""),
        "stage12_12b_recommended": bool(fwhm6) and completed_pairs == len(BIN_ORDER) * len(WAVELENGTH_GRID_NM) and flt(fwhm6.get("weighted_ratio"), 0) >= 6.0,
    }
