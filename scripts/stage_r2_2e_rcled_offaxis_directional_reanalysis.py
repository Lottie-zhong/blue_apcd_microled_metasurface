#!/usr/bin/env python3
"""Re-analyze completed R2-2D angle cuts as off-axis directional emission."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "outputs" / "r2_2d_rcled_fdtd_smoke_solve"
OUT = ROOT / "outputs" / "r2_2e_rcled_offaxis_directional_reanalysis"
INDEX = ROOT / "reports" / "rcled_mdc_workspace_index.md"

CASES = [
    ("center_x", IN / "r2_2d_angle_cut_453_center_x.csv"),
    ("center_z_outofplane", IN / "r2_2d_angle_cut_453_center_z_outofplane.csv"),
    ("incoherent_average", IN / "r2_2d_angle_cut_453_incoherent_avg.csv"),
]
WINDOWS = [1, 2, 3, 5, 10]


def read_cut(path: Path) -> tuple[np.ndarray, np.ndarray, list[str]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)
    a = np.array([float(r["angle_deg"]) for r in rows], dtype=float)
    i = np.array([float(r["intensity_proxy"]) for r in rows], dtype=float)
    order = np.argsort(a)
    return a[order], np.maximum(i[order], 0), headers


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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def trapz(y: np.ndarray, x: np.ndarray) -> float:
    return float(np.trapz(y, x)) if len(y) > 1 else float(np.sum(y))


def mask_power(a: np.ndarray, i: np.ndarray, mask: np.ndarray) -> float:
    return trapz(i[mask], a[mask]) if np.count_nonzero(mask) > 1 else 0.0


def fwhm_about_peak(a: np.ndarray, i: np.ndarray, peak_idx: int) -> float:
    if len(a) < 3 or i[peak_idx] <= 0:
        return math.nan
    half = i[peak_idx] * 0.5
    left = peak_idx
    while left > 0 and i[left] >= half:
        left -= 1
    right = peak_idx
    while right < len(i) - 1 and i[right] >= half:
        right += 1
    if left == 0 or right == len(i) - 1:
        return math.nan

    def cross(a0: float, y0: float, a1: float, y1: float) -> float:
        return a0 if y1 == y0 else a0 + (half - y0) * (a1 - a0) / (y1 - y0)

    return float(cross(a[right - 1], i[right - 1], a[right], i[right]) - cross(a[left], i[left], a[left + 1], i[left + 1]))


def peak_rows(data: dict[str, tuple[np.ndarray, np.ndarray]]) -> list[dict[str, Any]]:
    rows = []
    for name, (a, i) in data.items():
        k = int(np.argmax(i))
        pos = a > 0
        neg = a < 0
        kp = np.where(pos)[0][int(np.argmax(i[pos]))]
        kn = np.where(neg)[0][int(np.argmax(i[neg]))]
        rows.append({
            "case": name,
            "has_negative_angles": bool(np.any(a < 0)),
            "has_positive_angles": bool(np.any(a > 0)),
            "angle_min_deg": float(np.min(a)),
            "angle_max_deg": float(np.max(a)),
            "signed_global_peak_angle_deg": float(a[k]),
            "global_peak_abs_angle_deg": float(abs(a[k])),
            "positive_peak_angle_deg": float(a[kp]),
            "positive_peak_intensity": float(i[kp]),
            "negative_peak_angle_deg": float(a[kn]),
            "negative_peak_intensity": float(i[kn]),
            "positive_to_negative_peak_ratio": float(i[kp] / i[kn]) if i[kn] > 0 else math.inf,
            "dominant_lobe_fwhm_deg": fwhm_about_peak(a, i, k),
        })
    return rows


def window_rows(data: dict[str, tuple[np.ndarray, np.ndarray]], target: float) -> list[dict[str, Any]]:
    rows = []
    for name, (a, i) in data.items():
        total = trapz(i, a)
        normal = mask_power(a, i, np.abs(a) <= 5)
        k = int(np.argmax(i))
        for w in WINDOWS:
            pmask = np.abs(a - target) <= w
            nmask = np.abs(a + target) <= w
            pos_power = mask_power(a, i, pmask)
            neg_power = mask_power(a, i, nmask)
            target_power = pos_power + neg_power
            offtarget = max(total - target_power, 0.0)
            rows.append({
                "case": name,
                "target_angle_deg": target,
                "window_half_width_deg": w,
                "positive_target_power_fraction": pos_power / total if total > 0 else math.nan,
                "negative_target_power_fraction": neg_power / total if total > 0 else math.nan,
                "positive_to_negative_ratio": pos_power / neg_power if neg_power > 0 else math.inf,
                "target_total_fraction": target_power / total if total > 0 else math.nan,
                "target_to_normal_ratio": target_power / normal if normal > 0 else math.inf,
                "target_to_offtarget_ratio": target_power / offtarget if offtarget > 0 else math.inf,
                "FWHM_around_dominant_offaxis_lobe_deg": fwhm_about_peak(a, i, k),
                "peak_intensity_normalized": 1.0,
            })
    return rows


def classify(avg_peak: dict[str, Any], win_rows: list[dict[str, Any]]) -> str:
    r3 = [r for r in win_rows if r["case"] == "incoherent_average" and r["window_half_width_deg"] == 3][0]
    ratio = r3["positive_to_negative_ratio"]
    pos = r3["positive_target_power_fraction"]
    neg = r3["negative_target_power_fraction"]
    if pos <= 0 or neg <= 0:
        return "unclear_due_to_missing_signed_lobe_power"
    if 0.5 <= ratio <= 2.0:
        return "symmetric_plus_minus_offaxis_double_lobe"
    return "single_sided_positive_offaxis" if ratio > 2 else "single_sided_negative_offaxis"


def contribution_rows(data: dict[str, tuple[np.ndarray, np.ndarray]], signed_target: float) -> list[dict[str, Any]]:
    ax, ix = data["center_x"]
    az, iz = data["center_z_outofplane"]
    x_val = float(np.interp(signed_target, ax, ix))
    z_val = float(np.interp(signed_target, az, iz))
    s = x_val + z_val
    if s <= 0:
        dominant = "unavailable"
    elif x_val / s > 0.6:
        dominant = "center_x_dominated"
    elif z_val / s > 0.6:
        dominant = "center_z_outofplane_dominated"
    else:
        dominant = "balanced"
    return [{
        "dominant_signed_target_angle_deg": signed_target,
        "center_x_intensity_at_target": x_val,
        "center_z_outofplane_intensity_at_target": z_val,
        "center_x_fraction": x_val / s if s > 0 else math.nan,
        "center_z_outofplane_fraction": z_val / s if s > 0 else math.nan,
        "contribution_classification": dominant,
    }]


def append_index() -> None:
    if not INDEX.exists():
        return
    text = INDEX.read_text(encoding="utf-8")
    marker = "## R2-2E off-axis re-analysis"
    if marker in text:
        return
    INDEX.write_text(text.rstrip() + "\n\n" + marker + "\n\n- Re-analyzed R2-2D 453 nm angle cuts as an off-axis directional-emission seed.\n- No FDTD was run.\n- Output folder: outputs/r2_2e_rcled_offaxis_directional_reanalysis.\n", encoding="utf-8")


def main() -> int:
    data: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    headers: dict[str, list[str]] = {}
    for name, path in CASES:
        if not path.exists():
            raise SystemExit(f"missing input: {path}")
        a, i, h = read_cut(path)
        data[name] = (a, i)
        headers[name] = h

    peaks = peak_rows(data)
    avg_peak = next(r for r in peaks if r["case"] == "incoherent_average")
    target = float(avg_peak["global_peak_abs_angle_deg"])
    signed_target = float(avg_peak["signed_global_peak_angle_deg"])
    windows = window_rows(data, target)
    classification = classify(avg_peak, windows)
    contrib = contribution_rows(data, signed_target)

    recentered = []
    aa, ii = data["incoherent_average"]
    for a, i in zip(aa, ii):
        recentered.append({"angle_minus_positive_target_deg": float(a - target), "angle_deg": float(a), "incoherent_intensity_proxy": float(i)})

    lobe_compare = [r for r in windows if r["case"] == "incoherent_average"]

    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "r2_2e_signed_peak_analysis.csv", peaks)
    write_csv(OUT / "r2_2e_target_window_metrics.csv", windows)
    write_csv(OUT / "r2_2e_dipole_contribution_balance.csv", contrib)
    write_csv(OUT / "r2_2e_target_angle_cut_recentered.csv", recentered)
    write_csv(OUT / "r2_2e_positive_negative_lobe_comparison.csv", lobe_compare)

    normal_fail = "fail"
    seed = "promising" if target >= 20 and avg_peak["dominant_lobe_fwhm_deg"] <= 10 else "weak"
    if classification.startswith("single_sided"):
        direction_text = "Signed-angle data suggests asymmetric off-axis emission, but this is still a 2D proxy and needs validation."
    elif classification.startswith("symmetric"):
        direction_text = "Signed-angle analysis shows a +/- off-axis double-lobe, so this is not true unidirectional beam steering."
    else:
        direction_text = "Directionality is unclear because signed-lobe power could not be resolved."

    write_text(OUT / "r2_2e_offaxis_seed_classification.md", f"""
# R2-2E off-axis seed classification

- Normal RCLED source module: {normal_fail}.
- Off-axis narrow-angle emission seed: {seed}.
- Incoherent signed peak: {signed_target:.3f} deg.
- Incoherent dominant-lobe FWHM: {avg_peak['dominant_lobe_fwhm_deg']:.3f} deg.
- Signed-lobe class: {classification}.
""")
    write_text(OUT / "r2_2e_directionality_interpretation.md", f"""
# R2-2E directionality interpretation

{direction_text}

The R2-2D failure likely means the literal-spacer cavity supports a narrow off-axis leakage/cavity mode for the x dipole. Do not claim true unidirectional beam steering unless a later signed-lobe validation shows strong +theta/-theta asymmetry.
""")
    next_step = "keep as off-axis seed and do a signed-lobe validation"
    if classification.startswith("symmetric"):
        next_step = "add asymmetric grating/metasurface later to break +/- symmetry, or return to normal-RCLED redesign for near-normal emission"
    write_text(OUT / "r2_2e_next_steps.md", f"# R2-2E next steps\n\nRecommended next step: {next_step}.\n\nDo not broaden FDTD before deciding whether the goal is near-normal RCLED or off-axis narrow-angle emission.")
    write_text(OUT / "r2_2e_summary.md", f"""
# R2-2E off-axis directional re-analysis

No FDTD or Lumerical run was performed. This stage uses only committed R2-2D lightweight angle-cut CSV data.

## Signed angle convention

Angle-cut headers are `{headers['incoherent_average']}`. The data include negative and positive signed angles from {avg_peak['angle_min_deg']:.3f} to {avg_peak['angle_max_deg']:.3f} deg.

## Main result

- Incoherent signed peak: {signed_target:.3f} deg.
- Target absolute angle: {target:.3f} deg.
- Dominant-lobe FWHM: {avg_peak['dominant_lobe_fwhm_deg']:.3f} deg.
- Signed-lobe classification: {classification}.
- Normal RCLED source-module classification: {normal_fail}.
- Off-axis narrow-angle seed classification: {seed}.
- Dipole contribution at dominant signed target: {contrib[0]['contribution_classification']}.

## Physics note

The literal-spacer cavity appears to support a narrow off-axis leakage/cavity mode. If the +/- lobes are symmetric, this should be called off-axis narrow-angle emission, not unidirectional emission.
""")
    append_index()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
