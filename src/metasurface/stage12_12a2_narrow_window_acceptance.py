from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from metasurface.stage12_12a_spectral_audit import gaussian_weights

OUTPUT_DIR_NAME = "stage12_12a2_h500_lp_6bin_narrow_window_acceptance"
WINDOWS = [(447, 453), (448, 452), (449, 451), (449, 450), (450, 451), (450, 450)]
FWHM_VALUES_NM = [6, 4, 3, 2, 1]
RESULT_FIELDS = ["window_nm","wavelengths_nm","min_ratio_floor","weakest_bin","weakest_wavelength_nm","max_leakage","max_leakage_bin","max_leakage_wavelength_nm","avg_rms_phase_step_error_deg","max_phase_step_error_deg","bin240_min_ratio","bin120_min_ratio","bin240_collapses","bin120_stable","acceptable","notes"]
WEIGHT_FIELDS = ["fwhm_nm","weighted_ratio_floor","weighted_max_leakage","weighted_weakest_bin","weighted_max_leakage_bin","long_wavelength_leakage_contribution_451_453","long_wavelength_tail_dominates_failure","notes"]
FAIL_FIELDS = ["wavelength_nm","bin240_ratio","bin240_leakage","phase_step_rms_error_deg","phase_step_max_error_deg","bin240_collapses","notes"]

@dataclass(frozen=True)
class Stage12_12A2Paths:
    input_dir: Path
    output_dir: Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{str(k): "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def flt(value: object, default: float = math.nan) -> float:
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except Exception:
        return default


def in_window(rows: Sequence[dict], start: int, stop: int) -> list[dict]:
    return [r for r in rows if start <= int(flt(r.get("wavelength_nm"))) <= stop]


def bin_rows(rows: Sequence[dict], bin_deg: int) -> list[dict]:
    return [r for r in rows if int(flt(r.get("bin_deg"), -1)) == bin_deg]


def weak_bin(rows: Sequence[dict]) -> dict:
    return min(rows, key=lambda r: flt(r.get("conversion_to_leakage_ratio"), math.inf))


def leakage_row(rows: Sequence[dict]) -> dict:
    return max(rows, key=lambda r: flt(r.get("blocked_y_total_leakage"), -math.inf))


def window_metrics(results: Sequence[dict], steps: Sequence[dict]) -> list[dict]:
    out = []
    for start, stop in WINDOWS:
        rows = in_window(results, start, stop)
        step_rows = in_window(steps, start, stop)
        weak = weak_bin(rows)
        leak = leakage_row(rows)
        b240 = bin_rows(rows, 240)
        b120 = bin_rows(rows, 120)
        min240 = min(flt(r.get("conversion_to_leakage_ratio"), math.inf) for r in b240)
        min120 = min(flt(r.get("conversion_to_leakage_ratio"), math.inf) for r in b120)
        avg_rms = sum(flt(r.get("rms_phase_step_error_deg"), 0) for r in step_rows) / max(len(step_rows), 1)
        max_step = max(flt(r.get("max_phase_step_error_deg"), -math.inf) for r in step_rows)
        collapses240 = min240 < 6.0
        stable120 = min120 >= 6.0
        acceptable = (not collapses240) and stable120 and flt(weak.get("conversion_to_leakage_ratio"), 0) >= 6.0 and avg_rms <= 20.0 and max_step <= 30.0
        out.append({
            "window_nm": f"{start}-{stop}" if start != stop else str(start),
            "wavelengths_nm": ";".join(str(w) for w in range(start, stop + 1)),
            "min_ratio_floor": flt(weak.get("conversion_to_leakage_ratio")),
            "weakest_bin": int(flt(weak.get("bin_deg"))),
            "weakest_wavelength_nm": int(flt(weak.get("wavelength_nm"))),
            "max_leakage": flt(leak.get("blocked_y_total_leakage")),
            "max_leakage_bin": int(flt(leak.get("bin_deg"))),
            "max_leakage_wavelength_nm": int(flt(leak.get("wavelength_nm"))),
            "avg_rms_phase_step_error_deg": avg_rms,
            "max_phase_step_error_deg": max_step,
            "bin240_min_ratio": min240,
            "bin120_min_ratio": min120,
            "bin240_collapses": collapses240,
            "bin120_stable": stable120,
            "acceptable": acceptable,
            "notes": "acceptable" if acceptable else "warning",
        })
    return out


def weighted_metrics(results: Sequence[dict]) -> list[dict]:
    wavelengths = sorted({int(flt(r.get("wavelength_nm"))) for r in results})
    out = []
    for fwhm in FWHM_VALUES_NM:
        weights = dict(zip(wavelengths, gaussian_weights(wavelengths, fwhm)))
        per_bin = []
        for bin_deg in [0, 60, 120, 180, 240, 300]:
            rows = bin_rows(results, bin_deg)
            ratio = sum(flt(r.get("conversion_to_leakage_ratio"), 0) * weights[int(flt(r.get("wavelength_nm")))] for r in rows)
            leakage = sum(flt(r.get("blocked_y_total_leakage"), 0) * weights[int(flt(r.get("wavelength_nm")))] for r in rows)
            tail = sum(flt(r.get("blocked_y_total_leakage"), 0) * weights[int(flt(r.get("wavelength_nm")))] for r in rows if int(flt(r.get("wavelength_nm"))) >= 451)
            per_bin.append({"bin": bin_deg, "ratio": ratio, "leakage": leakage, "tail": tail})
        weakest = min(per_bin, key=lambda r: r["ratio"])
        leakiest = max(per_bin, key=lambda r: r["leakage"])
        tail_fraction = leakiest["tail"] / max(leakiest["leakage"], 1e-12)
        out.append({
            "fwhm_nm": fwhm,
            "weighted_ratio_floor": weakest["ratio"],
            "weighted_max_leakage": leakiest["leakage"],
            "weighted_weakest_bin": weakest["bin"],
            "weighted_max_leakage_bin": leakiest["bin"],
            "long_wavelength_leakage_contribution_451_453": tail_fraction,
            "long_wavelength_tail_dominates_failure": tail_fraction >= 0.5,
            "notes": "tail-dominated" if tail_fraction >= 0.5 else "center-weighted",
        })
    return out


def failure_rows(results: Sequence[dict], steps: Sequence[dict]) -> list[dict]:
    out = []
    for wavelength in sorted({int(flt(r.get("wavelength_nm"))) for r in results}):
        b240 = next(r for r in results if int(flt(r.get("wavelength_nm"))) == wavelength and int(flt(r.get("bin_deg"))) == 240)
        step = next(r for r in steps if int(flt(r.get("wavelength_nm"))) == wavelength)
        ratio = flt(b240.get("conversion_to_leakage_ratio"))
        out.append({
            "wavelength_nm": wavelength,
            "bin240_ratio": ratio,
            "bin240_leakage": flt(b240.get("blocked_y_total_leakage")),
            "phase_step_rms_error_deg": flt(step.get("rms_phase_step_error_deg")),
            "phase_step_max_error_deg": flt(step.get("max_phase_step_error_deg")),
            "bin240_collapses": ratio < 6.0,
            "notes": "long-edge-collapse" if wavelength >= 451 and ratio < 6.0 else "usable",
        })
    return out


def recommend_window(metrics: Sequence[dict]) -> dict:
    lookup = {r["window_nm"]: r for r in metrics}
    for name in ["447-453", "448-452", "449-451", "449-450", "450-451", "450"]:
        if str(lookup[name]["acceptable"]).lower() == "true":
            return lookup[name]
    return lookup["450"]


def write_markdown(paths: Stage12_12A2Paths, metrics: list[dict], weighted: list[dict], failures: list[dict]) -> None:
    out = paths.output_dir
    lookup = {r["window_nm"]: r for r in metrics}
    best = recommend_window(metrics)
    fwhm_target = "<=2 nm" if not bool(lookup["450-451"]["acceptable"]) else "2-3 nm"
    tail = next(r for r in weighted if int(flt(r["fwhm_nm"])) == 6)
    lines = [
        "# Stage12-12A2 Narrow-Window Spectral Acceptance",
        "",
        "Boundary: read-only postprocessing only. No FDTD, no K6, no DBR, no RCLED, no dipoles, no finite patch, no optimization, and no new .fsp.",
        "",
        f"- 447-453 nm acceptable: `{lookup['447-453']['acceptable']}`.",
        f"- 448-452 nm acceptable: `{lookup['448-452']['acceptable']}`.",
        f"- 449-451 nm acceptable: `{lookup['449-451']['acceptable']}`.",
        f"- Failure dominated by 240 deg long-wavelength edge: `{any(str(r['bin240_collapses']).lower() == 'true' and int(r['wavelength_nm']) >= 451 for r in failures)}`.",
        f"- Recommended Stage12-12B K6 wavelength grid: `{best['wavelengths_nm']}`.",
        f"- Recommended RCLED/DBR spectral FWHM target: `{fwhm_target}`.",
        f"- FWHM=6 nm long-wavelength leakage contribution: `{tail['long_wavelength_leakage_contribution_451_453']}`.",
        "- Stage13 dipole-source / DBR coupling should wait until K6 narrow-window validation is done.",
    ]
    (out / "stage12_12a2_k6_validation_recommendation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "stage12_12a2_rcled_bandwidth_requirement.md").write_text("\n".join([
        "# Stage12-12A2 RCLED Bandwidth Requirement",
        "",
        f"Recommended FWHM target: `{fwhm_target}`.",
        "The current H500 LP-APCD six-bin library should not be treated as broadband over 447-453 nm because the 240 deg bin fails on the long-wavelength tail.",
    ]) + "\n", encoding="utf-8")
    (out / "stage12_12a2_next_recommendation.md").write_text("\n".join([
        "# Stage12-12A2 Next Recommendation",
        "",
        f"Use `{best['wavelengths_nm']}` for Stage12-12B K6 spectral steering validation.",
        "Do Stage12-12B before Stage13 dipole-source / DBR coupling.",
    ]) + "\n", encoding="utf-8")


def run_stage12_12a2(paths: Stage12_12A2Paths) -> dict[str, object]:
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    results = read_csv(paths.input_dir / "stage12_12a_6bin_spectral_results.csv")
    steps = read_csv(paths.input_dir / "stage12_12a_phase_step_vs_wavelength.csv")
    metrics = window_metrics(results, steps)
    weighted = weighted_metrics(results)
    failures = failure_rows(results, steps)
    write_csv(paths.output_dir / "stage12_12a2_window_acceptance_metrics.csv", metrics, RESULT_FIELDS)
    write_csv(paths.output_dir / "stage12_12a2_weighted_fwhm_metrics.csv", weighted, WEIGHT_FIELDS)
    write_csv(paths.output_dir / "stage12_12a2_240bin_long_wavelength_failure.csv", failures, FAIL_FIELDS)
    write_markdown(paths, metrics, weighted, failures)
    best = recommend_window(metrics)
    return {
        "output_folder": str(paths.output_dir),
        "best_acceptable_window": best["window_nm"],
        "stage12_12b_grid": best["wavelengths_nm"],
        "full_447_453_acceptable": next(r for r in metrics if r["window_nm"] == "447-453")["acceptable"],
        "window_448_452_acceptable": next(r for r in metrics if r["window_nm"] == "448-452")["acceptable"],
        "window_449_451_acceptable": next(r for r in metrics if r["window_nm"] == "449-451")["acceptable"],
        "recommended_rcled_fwhm_target": "<=2 nm" if not bool(next(r for r in metrics if r["window_nm"] == "450-451")["acceptable"]) else "2-3 nm",
    }
