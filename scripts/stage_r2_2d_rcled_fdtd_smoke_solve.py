#!/usr/bin/env python3
"""Run R2-2D two-case FDTD smoke solve and extract 453 nm angle metrics.

This runner intentionally solves only the valid R2-2C setup pair: center_x and
center_z_outofplane. center_y is invalid for the 2D x-y layout and is never
copied or solved here.
"""
from __future__ import annotations

import csv
import json
import math
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
IN_DIR = ROOT / "outputs" / "r2_2c_rcled_fdtd_smoke_setup_only" / "runtime_fsp"
OUT = ROOT / "outputs" / "r2_2d_rcled_fdtd_smoke_solve"
SOLVE_DIR = OUT / "runtime_solve_fsp"
INDEX = ROOT / "reports" / "rcled_mdc_workspace_index.md"
LUMAPI_DIR = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")

STAGE = "R2_2D_RCLED_FDTD_smoke_solve"
CANDIDATE_ID = "R2_1_00223"
WAVELENGTH_NM = 453.0
MONITOR = "top_farfield_monitor"

CASES = [
    {
        "case_id": "R2_2D_R2_1_00223_453_center_x",
        "source_case_id": "R2_2C_R2_1_00223_453_center_x",
        "dipole_orientation": "x",
        "setup_fsp": IN_DIR / "R2_2C_R2_1_00223_453_center_x_setup_only.fsp",
        "solve_fsp": SOLVE_DIR / "R2_2D_R2_1_00223_453_center_x_solve.fsp",
        "angle_csv": OUT / "r2_2d_angle_cut_453_center_x.csv",
    },
    {
        "case_id": "R2_2D_R2_1_00223_453_center_z_outofplane",
        "source_case_id": "R2_2C_R2_1_00223_453_center_z_outofplane",
        "dipole_orientation": "z_outofplane",
        "setup_fsp": IN_DIR / "R2_2C_R2_1_00223_453_center_z_outofplane_setup_only.fsp",
        "solve_fsp": SOLVE_DIR / "R2_2D_R2_1_00223_453_center_z_outofplane_solve.fsp",
        "angle_csv": OUT / "r2_2d_angle_cut_453_center_z_outofplane.csv",
    },
]
INVALID_CENTER_Y = IN_DIR / "R2_2C_R2_1_00223_453_center_y_setup_only.fsp"


def import_lumapi() -> Any:
    sys.path.insert(0, str(LUMAPI_DIR))
    import lumapi  # type: ignore[import-not-found]

    return lumapi


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def trapz(y: np.ndarray, x: np.ndarray) -> float:
    if len(y) < 2:
        return float(np.sum(y))
    return float(np.trapz(y, x))


def sanitize_angle_intensity(angles: Any, intensity: Any) -> tuple[np.ndarray, np.ndarray]:
    a = np.asarray(angles, dtype=float).squeeze().reshape(-1)
    i = np.asarray(intensity, dtype=float).squeeze().reshape(-1)
    n = min(len(a), len(i))
    a = a[:n]
    i = np.nan_to_num(i[:n], nan=0.0, posinf=0.0, neginf=0.0)
    i = np.maximum(i, 0.0)
    order = np.argsort(a)
    return a[order], i[order]


def band_power(angles: np.ndarray, intensity: np.ndarray, lo: float, hi: float) -> float:
    mask = (np.abs(angles) >= lo) & (np.abs(angles) <= hi)
    return trapz(intensity[mask], angles[mask]) if np.count_nonzero(mask) >= 2 else 0.0


def cone_power(angles: np.ndarray, intensity: np.ndarray, cone: float) -> float:
    mask = np.abs(angles) <= cone
    return trapz(intensity[mask], angles[mask]) if np.count_nonzero(mask) >= 2 else 0.0


def fwhm_deg(angles: np.ndarray, intensity: np.ndarray) -> float:
    if len(angles) < 3 or float(np.max(intensity)) <= 0:
        return math.nan
    k = int(np.argmax(intensity))
    half = float(intensity[k]) * 0.5
    left = k
    while left > 0 and intensity[left] >= half:
        left -= 1
    right = k
    while right < len(intensity) - 1 and intensity[right] >= half:
        right += 1
    if left == 0 or right == len(intensity) - 1:
        return math.nan

    def cross(a0: float, y0: float, a1: float, y1: float) -> float:
        return a0 if y1 == y0 else a0 + (half - y0) * (a1 - a0) / (y1 - y0)

    a_left = cross(float(angles[left]), float(intensity[left]), float(angles[left + 1]), float(intensity[left + 1]))
    a_right = cross(float(angles[right - 1]), float(intensity[right - 1]), float(angles[right]), float(intensity[right]))
    return float(a_right - a_left)


def metrics(case_id: str, orientation: str, angles: np.ndarray, intensity: np.ndarray, runtime_s: float = 0.0) -> dict[str, Any]:
    total = trapz(intensity, angles)
    peak_idx = int(np.argmax(intensity)) if len(intensity) else 0
    peak = float(angles[peak_idx]) if len(angles) else math.nan
    normal = band_power(angles, intensity, 0, 5)
    offaxis = band_power(angles, intensity, 20, 30)
    return {
        "case_id": case_id,
        "candidate_id": CANDIDATE_ID,
        "wavelength_nm": WAVELENGTH_NM,
        "dipole_orientation": orientation,
        "runtime_s": round(runtime_s, 3),
        "total_upward_power_proxy": total,
        "angular_peak_angle_deg_at_453": peak,
        "peak_abs_angle_deg_at_453": abs(peak) if not math.isnan(peak) else math.nan,
        "angular_FWHM_deg_at_453": fwhm_deg(angles, intensity),
        "eta5": cone_power(angles, intensity, 5) / total if total > 0 else math.nan,
        "eta10": cone_power(angles, intensity, 10) / total if total > 0 else math.nan,
        "eta20": cone_power(angles, intensity, 20) / total if total > 0 else math.nan,
        "eta30": cone_power(angles, intensity, 30) / total if total > 0 else math.nan,
        "I_normal_0_5deg": normal,
        "I_offaxis_20_30deg": offaxis,
        "normal_offaxis_ratio": normal / offaxis if offaxis > 0 else math.inf,
        "spectral_FWHM_nm": "not_extracted_single_wavelength_smoke",
        "status": "extracted",
    }


def write_angle_csv(path: Path, angles: np.ndarray, intensity: np.ndarray) -> None:
    write_csv(path, [{"angle_deg": float(a), "intensity_proxy": float(v)} for a, v in zip(angles, intensity)])


def extract_angle(fdtd: Any) -> tuple[np.ndarray, np.ndarray, str]:
    warnings: list[str] = []
    try:
        ff = fdtd.farfield2d(MONITOR, 1)
        ang = fdtd.farfieldangle(MONITOR, 1)
        angles, intensity = sanitize_angle_intensity(ang, ff)
        return angles, intensity, "farfield2d_farfieldangle"
    except Exception as exc:
        warnings.append(f"farfield2d failed: {exc}")
    try:
        t = float(fdtd.transmission(MONITOR))
        angles = np.linspace(-90.0, 90.0, 181)
        intensity = np.zeros_like(angles)
        intensity[len(angles) // 2] = max(t, 0.0)
        return angles, intensity, "fallback_transmission_delta_normal"
    except Exception as exc:
        warnings.append(f"transmission fallback failed: {exc}")
    raise RuntimeError("; ".join(warnings))


def append_index() -> None:
    note = """

## R2-2D FDTD smoke solve

- Stage: R2-2D minimal 2D FDTD smoke solve.
- Candidate: R2_1_00223 at 453 nm.
- Valid solved pair: center_x + center_z_outofplane.
- Invalid center_y was not solved.
- Output folder: outputs/r2_2d_rcled_fdtd_smoke_solve.
""".rstrip()
    if INDEX.exists():
        text = INDEX.read_text(encoding="utf-8")
        if "## R2-2D FDTD smoke solve" not in text:
            INDEX.write_text(text.rstrip() + "\n\n" + note + "\n", encoding="utf-8")


def main() -> int:
    if any("center_y" in str(case["solve_fsp"]) for case in CASES):
        raise SystemExit("center_y appeared in solve queue; refusing to run")
    missing = [str(case["setup_fsp"]) for case in CASES if not Path(case["setup_fsp"]).exists()]
    if missing:
        raise SystemExit("Missing valid setup FSP(s): " + "; ".join(missing))

    OUT.mkdir(parents=True, exist_ok=True)
    SOLVE_DIR.mkdir(parents=True, exist_ok=True)

    manifest = []
    for case in CASES:
        shutil.copy2(case["setup_fsp"], case["solve_fsp"])
        manifest.append({
            "case_id": case["case_id"],
            "source_setup_fsp": str(case["setup_fsp"]),
            "runtime_solve_fsp": str(case["solve_fsp"]),
            "dipole_orientation": case["dipole_orientation"],
            "will_solve": True,
        })
    manifest.append({
        "case_id": "R2_2C_R2_1_00223_453_center_y",
        "source_setup_fsp": str(INVALID_CENTER_Y),
        "runtime_solve_fsp": "",
        "dipole_orientation": "y_invalid_cavity_normal",
        "will_solve": False,
        "status": "INVALID_DO_NOT_SOLVE",
    })
    write_csv(OUT / "r2_2d_run_manifest.csv", manifest)
    write_json(OUT / "r2_2d_run_manifest.json", manifest)

    lumapi = import_lumapi()
    case_rows: list[dict[str, Any]] = []
    warning_lines: list[str] = ["# R2-2D warnings", "", "- center_y was intentionally not solved."]
    cuts: list[tuple[str, np.ndarray, np.ndarray]] = []

    fdtd = lumapi.FDTD(hide=True)
    try:
        for case in CASES:
            t0 = time.time()
            runtime = 0.0
            try:
                fdtd.load(str(case["solve_fsp"]))
                fdtd.run()
                runtime = time.time() - t0
                fdtd.save(str(case["solve_fsp"]))
                angles, intensity, mode = extract_angle(fdtd)
                row = metrics(case["case_id"], case["dipole_orientation"], angles, intensity, runtime)
                row["extraction_mode"] = mode
                row["runtime_solve_fsp"] = str(case["solve_fsp"])
                case_rows.append(row)
                cuts.append((case["dipole_orientation"], angles, intensity))
                write_angle_csv(case["angle_csv"], angles, intensity)
            except Exception as exc:
                runtime = time.time() - t0
                case_rows.append({
                    "case_id": case["case_id"],
                    "candidate_id": CANDIDATE_ID,
                    "wavelength_nm": WAVELENGTH_NM,
                    "dipole_orientation": case["dipole_orientation"],
                    "runtime_s": round(runtime, 3),
                    "status": "failed",
                    "error": str(exc),
                    "runtime_solve_fsp": str(case["solve_fsp"]),
                })
                warning_lines.append(f"- {case['case_id']} failed: {exc}")
    finally:
        try:
            fdtd.close()
        except Exception:
            pass

    write_csv(OUT / "r2_2d_case_metrics.csv", case_rows)
    write_json(OUT / "r2_2d_case_metrics.json", case_rows)

    avg_rows: list[dict[str, Any]] = []
    if len(cuts) == 2:
        base_angles = cuts[0][1]
        total_i = cuts[0][2].copy()
        for _, angles, intensity in cuts[1:]:
            total_i += intensity if len(angles) == len(base_angles) and np.allclose(angles, base_angles) else np.interp(base_angles, angles, intensity, left=0.0, right=0.0)
        write_angle_csv(OUT / "r2_2d_angle_cut_453_incoherent_avg.csv", base_angles, total_i)
        row = metrics("R2_2D_R2_1_00223_453_incoherent_x_plus_z_outofplane", "x_plus_z_outofplane_incoherent", base_angles, total_i)
        prefix_map = {
            "angular_peak_angle_deg_at_453": "incoherent_angular_peak_angle_deg_at_453",
            "peak_abs_angle_deg_at_453": "incoherent_peak_abs_angle_deg_at_453",
            "angular_FWHM_deg_at_453": "incoherent_angular_FWHM_deg_at_453",
            "eta5": "incoherent_eta5",
            "eta10": "incoherent_eta10",
            "eta20": "incoherent_eta20",
            "eta30": "incoherent_eta30",
            "I_normal_0_5deg": "incoherent_I_normal_0_5deg",
            "I_offaxis_20_30deg": "incoherent_I_offaxis_20_30deg",
            "normal_offaxis_ratio": "incoherent_normal_offaxis_ratio",
        }
        avg = {prefix_map.get(k, k): v for k, v in row.items()}
        fwhm = float(avg.get("incoherent_angular_FWHM_deg_at_453", math.nan))
        peak_abs = float(avg.get("incoherent_peak_abs_angle_deg_at_453", math.nan))
        ratio = float(avg.get("incoherent_normal_offaxis_ratio", math.nan))
        avg["ideal_criteria_pass"] = bool(fwhm <= 10 and peak_abs <= 5 and ratio > 1.5)
        avg["acceptable_criteria_pass"] = bool(fwhm <= 25 and peak_abs <= 10 and ratio > 1.0)
        avg_rows.append(avg)
    else:
        warning_lines.append("- Incoherent average unavailable because both valid angle cuts were not extracted.")
    write_csv(OUT / "r2_2d_incoherent_average_metrics.csv", avg_rows)
    write_json(OUT / "r2_2d_incoherent_average_metrics.json", avg_rows)

    if avg_rows:
        avg = avg_rows[0]
        verdict = "ideal" if avg.get("ideal_criteria_pass") else "acceptable" if avg.get("acceptable_criteria_pass") else "not_passed"
    else:
        verdict = "not_available"

    write_text(OUT / "r2_2d_failure_or_warning_log.md", "\n".join(warning_lines) + "\n\n- Spectral FWHM cannot be extracted from this single-wavelength smoke setup.")
    write_text(OUT / "r2_2d_next_steps.md", f"# R2-2D next steps\n\nVerdict: {verdict}.\n\nIf acceptable or ideal, review CSVs and proceed to the next explicit R2-2 FDTD validation request. If not passed or extraction failed, inspect monitor/far-field setup before any broader run.")
    write_text(OUT / "r2_2d_summary.md", f"""
# R2-2D RCLED FDTD smoke solve

- Branch: work/rcled-mdc-source-module
- Candidate: {CANDIDATE_ID}
- Wavelength: {WAVELENGTH_NM:.0f} nm
- Solved cases: center_x and center_z_outofplane only.
- Invalid center_y: not solved.
- Incoherent verdict: {verdict}
- Spectral FWHM: not extracted from this single-wavelength smoke setup.

## Runtime solve FSPs

- {CASES[0]['solve_fsp']}
- {CASES[1]['solve_fsp']}

## Criteria

Ideal: FWHM <= 10 deg, peak_abs <= 5 deg, normal/offaxis > 1.5.
Acceptable: FWHM <= 25 deg, peak_abs <= 10 deg, normal/offaxis > 1.0.
""")
    append_index()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
