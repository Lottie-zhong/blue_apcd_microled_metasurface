#!/usr/bin/env python3
"""Plot R2-2D/R2-2E off-axis double-lobe far-field figures from CSV only."""
from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
IN_D = ROOT / "outputs" / "r2_2d_rcled_fdtd_smoke_solve"
IN_E = ROOT / "outputs" / "r2_2e_rcled_offaxis_directional_reanalysis"
OUT = ROOT / "outputs" / "r2_2g_offaxis_farfield_polar_plot"
INDEX = ROOT / "reports" / "rcled_mdc_workspace_index.md"

CUTS = {
    "center_x": IN_D / "r2_2d_angle_cut_453_center_x.csv",
    "center_z_outofplane": IN_D / "r2_2d_angle_cut_453_center_z_outofplane.csv",
    "incoherent_average": IN_D / "r2_2d_angle_cut_453_incoherent_avg.csv",
}
PEAKS = IN_E / "r2_2e_signed_peak_analysis.csv"


def read_cut(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    a = np.array([float(r["angle_deg"]) for r in rows])
    i = np.array([float(r["intensity_proxy"]) for r in rows])
    order = np.argsort(a)
    i = np.maximum(i[order], 0)
    return a[order], i / np.max(i) if np.max(i) > 0 else i


def read_peaks() -> dict[str, dict[str, float]]:
    with PEAKS.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = {}
    for r in rows:
        out[r["case"]] = {k: float(v) for k, v in r.items() if k != "case" and v not in ("True", "False")}
    return out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def interp_x(a: np.ndarray, y: np.ndarray, x: float) -> float:
    return float(np.interp(x, a, y))


def halfmax_points(a: np.ndarray, y: np.ndarray, peak_angle: float) -> tuple[float, float, float]:
    k = int(np.argmin(np.abs(a - peak_angle)))
    half = float(y[k] * 0.5)
    left = k
    while left > 0 and y[left] >= half:
        left -= 1
    right = k
    while right < len(y) - 1 and y[right] >= half:
        right += 1

    def cross(i0: int, i1: int) -> float:
        x0, x1 = float(a[i0]), float(a[i1])
        y0, y1 = float(y[i0]), float(y[i1])
        return x0 if y1 == y0 else x0 + (half - y0) * (x1 - x0) / (y1 - y0)

    l = cross(left, left + 1) if left < k else float(a[left])
    r = cross(right - 1, right) if right > k else float(a[right])
    return l, r, float(r - l)


def save_all(fig: plt.Figure, stem: str) -> None:
    for ext in ("png", "svg", "pdf"):
        fig.savefig(OUT / f"{stem}.{ext}", dpi=300, bbox_inches="tight")


def append_index() -> None:
    marker = "## R2-2G off-axis far-field figures"
    if not INDEX.exists():
        return
    text = INDEX.read_text(encoding="utf-8")
    if marker in text:
        return
    INDEX.write_text(text.rstrip() + f"\n\n{marker}\n\n- Generated polar and Cartesian far-field plots from existing R2-2D/R2-2E CSV data.\n- No FDTD or Lumerical run.\n- Output folder: outputs/r2_2g_offaxis_farfield_polar_plot.\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    data = {name: read_cut(path) for name, path in CUTS.items()}
    peaks = read_peaks()
    a, y = data["incoherent_average"]
    target = abs(peaks["incoherent_average"]["signed_global_peak_angle_deg"])
    fwhm_report = peaks["incoherent_average"]["dominant_lobe_fwhm_deg"]
    neg_l, neg_r, neg_f = halfmax_points(a, y, -target)
    pos_l, pos_r, pos_f = halfmax_points(a, y, target)

    fwhm_rows = [
        {"lobe": "negative", "peak_angle_deg": -target, "left_halfmax_deg": neg_l, "right_halfmax_deg": neg_r, "fwhm_deg": neg_f},
        {"lobe": "positive", "peak_angle_deg": target, "left_halfmax_deg": pos_l, "right_halfmax_deg": pos_r, "fwhm_deg": pos_f},
    ]
    write_csv(OUT / "r2_2g_fwhm_points.csv", fwhm_rows)
    write_csv(OUT / "r2_2g_interpolated_incoherent_curve.csv", [{"angle_deg": float(x), "normalized_intensity": float(v)} for x, v in zip(a, y)])

    # Polar: theta=0 at top, negative left, positive right. Matplotlib theta is radians.
    theta = np.deg2rad(a)
    fig = plt.figure(figsize=(7.2, 5.4))
    ax = fig.add_subplot(111, projection="polar")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_thetamin(-90)
    ax.set_thetamax(90)
    ax.set_rlim(0, 1.08)
    ax.plot(theta, y, color="#1f77b4", lw=2.0, label="incoherent x + z")
    for peak, l, r, color in [(-target, neg_l, neg_r, "#d62728"), (target, pos_l, pos_r, "#d62728")]:
        ax.plot(np.deg2rad([peak]), [interp_x(a, y, peak)], "o", color=color, ms=5)
        ax.plot(np.deg2rad(np.linspace(l, r, 60)), np.full(60, 0.5), color=color, lw=3, alpha=0.8)
        ax.annotate(f"{peak:+.1f} deg", xy=(np.deg2rad(peak), 1.0), xytext=(np.deg2rad(peak), 1.16), ha="center", fontsize=9)
    ax.set_title("R2-2D 453 nm symmetric off-axis double-lobe", pad=18)
    ax.text(0.5, -0.13, f"Peaks near +/-{target:.3f} deg; FWHM ~{fwhm_report:.3f} deg; symmetric off-axis double-lobe emission", transform=ax.transAxes, ha="center", va="top", fontsize=9)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.24), frameon=False)
    save_all(fig, "r2_2g_incoherent_polar_farfield")
    fig.savefig(OUT / "r2_2g_incoherent_polar_farfield_light.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    styles = {
        "center_x": ("#d62728", "center_x"),
        "center_z_outofplane": ("#2ca02c", "center_z_outofplane"),
        "incoherent_average": ("#1f77b4", "incoherent average"),
    }
    for name, (aa, yy) in data.items():
        color, label = styles[name]
        ax.plot(aa, yy, lw=1.5 if name != "incoherent_average" else 2.2, color=color, label=label)
    ax.axhline(0.5, color="0.35", ls="--", lw=1.0, label="half maximum")
    for peak, l, r in [(-target, neg_l, neg_r), (target, pos_l, pos_r)]:
        ax.axvline(peak, color="#d62728", ls=":", lw=1.2)
        ax.plot([l, r], [0.5, 0.5], color="#d62728", lw=4, alpha=0.55)
        ax.annotate(f"peak {peak:+.2f} deg\nFWHM {abs(r-l):.2f} deg", xy=(peak, 1.0), xytext=(peak + (8 if peak < 0 else -28), 0.78), arrowprops={"arrowstyle": "->", "lw": 0.8}, fontsize=9)
    ax.set_xlim(-90, 90)
    ax.set_ylim(0, 1.08)
    ax.set_xlabel("signed angle from surface normal (deg)")
    ax.set_ylabel("normalized far-field intensity")
    ax.set_title("R2-2D 453 nm far-field angle cuts")
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False, ncol=2, fontsize=9)
    save_all(fig, "r2_2g_angle_cut_farfield")
    plt.close(fig)

    metadata = [{
        "figure_set": "R2-2G",
        "source_data": "R2-2D/R2-2E CSV only",
        "target_peak_abs_angle_deg": target,
        "reported_fwhm_deg": fwhm_report,
        "negative_lobe_fwhm_deg": neg_f,
        "positive_lobe_fwhm_deg": pos_f,
        "classification": "symmetric off-axis double-lobe emission",
        "polar_convention": "0 deg at top; negative angles left; positive angles right; visible range -90 to +90 deg",
    }]
    write_csv(OUT / "r2_2g_plot_metadata.csv", metadata)
    (OUT / "r2_2g_summary.md").write_text(f"""# R2-2G off-axis far-field plots

No FDTD or Lumerical run was performed. Figures were generated from existing R2-2D/R2-2E CSV data.

- Polar convention: 0 deg is surface normal/upward; negative signed angles are left; positive signed angles are right.
- Incoherent peaks annotated near +/-{target:.3f} deg.
- Dominant lobe FWHM used in annotation: {fwhm_report:.3f} deg.
- Classification: symmetric off-axis double-lobe emission, not unidirectional steering.

## Figures

- r2_2g_incoherent_polar_farfield.png/svg/pdf
- r2_2g_angle_cut_farfield.png/svg/pdf
""", encoding="utf-8")
    append_index()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
