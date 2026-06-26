from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUTPUT_DIR_NAME = "stage12_lp_k6_450nm_farfield_visualization"
BASELINE = {
    "x_power": 0.35782382585849376,
    "y_leakage": 0.03070098955871727,
    "ratio": 11.655123531902342,
    "theta": 10.000000005514977,
}
FIGURES = [
    "stage12_lp_k6_450nm_xLP_farfield_2d.png",
    "stage12_lp_k6_450nm_yLP_leakage_farfield_2d.png",
    "stage12_lp_k6_450nm_xLP_vs_yLP_1d_cut.png",
    "stage12_lp_k6_450nm_target_selectivity_bar.png",
    "stage12_lp_k6_450nm_summary_panel.png",
]

@dataclass(frozen=True)
class Stage12LPVizPaths:
    stage12_2_dir: Path
    stage12_6_dir: Path
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


def target_peak(angles: Sequence[float], intensities: Sequence[float], target_angle: float, window_deg: float = 5.0) -> int:
    candidates = [i for i, a in enumerate(angles) if abs(float(a) - target_angle) <= window_deg]
    if not candidates:
        return min(range(len(angles)), key=lambda i: abs(float(angles[i]) - target_angle))
    return max(candidates, key=lambda i: float(intensities[i]))


def fwhm_from_cut(angles: Sequence[float], intensities: Sequence[float], target_angle: float) -> dict[str, float]:
    data = sorted((float(a), float(i)) for a, i in zip(angles, intensities))
    if not data:
        return {"peak_angle_deg": math.nan, "peak_intensity": math.nan, "half_max_intensity": math.nan, "fwhm_deg": math.nan, "left_halfmax_angle_deg": math.nan, "right_halfmax_angle_deg": math.nan}
    a = [x for x, _ in data]
    y = [max(0.0, v) for _, v in data]
    peak_i = target_peak(a, y, target_angle)
    peak = y[peak_i]
    half = peak / 2.0
    left = math.nan
    for i in range(peak_i, 0, -1):
        if y[i - 1] <= half <= y[i] and y[i] != y[i - 1]:
            left = a[i - 1] + (half - y[i - 1]) * (a[i] - a[i - 1]) / (y[i] - y[i - 1])
            break
    right = math.nan
    for i in range(peak_i, len(y) - 1):
        if y[i] >= half >= y[i + 1] and y[i] != y[i + 1]:
            right = a[i] + (half - y[i]) * (a[i + 1] - a[i]) / (y[i + 1] - y[i])
            break
    fwhm = right - left if not math.isnan(left) and not math.isnan(right) else math.nan
    return {"peak_angle_deg": a[peak_i], "peak_intensity": peak, "half_max_intensity": half, "fwhm_deg": fwhm, "left_halfmax_angle_deg": left, "right_halfmax_angle_deg": right}


def find_raw_arrays(input_dirs: Sequence[Path]) -> list[str]:
    suffixes = {".npz", ".npy", ".h5", ".hdf5", ".mat"}
    found = []
    for folder in input_dirs:
        if folder.exists():
            found.extend(str(p) for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in suffixes and any(k in p.name.lower() for k in ("far", "field", "ux", "uy", "theta")))
    return sorted(found)


def split_orders(rows: Sequence[dict]) -> dict[str, list[dict]]:
    out = {"x": [], "y": []}
    for row in rows:
        pol = row.get("polarization", "")
        if pol in out:
            out[pol].append(row)
    return out


def proxy_grid(rows: Sequence[dict], sigma: float = 0.025) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ux = np.linspace(-1.0, 1.0, 300)
    uy = np.linspace(-0.35, 0.35, 160)
    xx, yy = np.meshgrid(ux, uy)
    zz = np.zeros_like(xx)
    for r in rows:
        power = flt(r.get("order_power_source_norm"), 0.0)
        zz += power * np.exp(-((xx - flt(r.get("ux"))) ** 2 + (yy - flt(r.get("uy"))) ** 2) / (2 * sigma ** 2))
    return xx, yy, zz


def plot_proxy_map(rows: Sequence[dict], out: Path, title: str, target_power: float, target_angle: float, vmax: float | None = None) -> None:
    xx, yy, zz = proxy_grid(rows)
    fig, ax = plt.subplots(figsize=(6.4, 3.8), dpi=160)
    im = ax.imshow(zz, extent=[xx.min(), xx.max(), yy.min(), yy.max()], origin="lower", aspect="auto", cmap="magma", vmax=vmax)
    target_ux = math.sin(math.radians(target_angle))
    peak = max(rows, key=lambda r: flt(r.get("order_power_source_norm"), -1))
    ax.scatter([target_ux], [0], marker="x", s=80, color="cyan", label="target +1 / +10 deg")
    ax.scatter([flt(peak.get("ux"))], [flt(peak.get("uy"))], marker="o", s=45, facecolors="none", edgecolors="white", label="global peak")
    ax.set_xlabel("ux")
    ax.set_ylabel("uy")
    ax.set_title(title)
    ax.text(0.02, 0.97, f"target power/leakage={target_power:.4f}\nangle={target_angle:.2f} deg", transform=ax.transAxes, va="top", color="white", fontsize=8)
    ax.legend(loc="lower right", fontsize=7)
    fig.colorbar(im, ax=ax, label="order-power proxy intensity")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def plot_1d_cut(x_rows: Sequence[dict], y_rows: Sequence[dict], out: Path, fwhm: dict[str, float]) -> None:
    x = sorted((flt(r.get("theta_deg")), flt(r.get("order_power_source_norm"))) for r in x_rows)
    y = sorted((flt(r.get("theta_deg")), flt(r.get("order_power_source_norm"))) for r in y_rows)
    xmax = max(v for _, v in x) or 1.0
    ymax = max(v for _, v in y) or 1.0
    fig, ax = plt.subplots(figsize=(6.4, 3.8), dpi=160)
    ax.plot([a for a, _ in x], [v / xmax for _, v in x], "o-", label="x-LP normalized order powers")
    ax.plot([a for a, _ in y], [v / ymax for _, v in y], "s--", label="y-LP normalized leakage orders")
    ax.axvline(BASELINE["theta"], color="k", linestyle=":", label="+10 deg target")
    if not math.isnan(fwhm["left_halfmax_angle_deg"]):
        ax.axvline(fwhm["left_halfmax_angle_deg"], color="tab:blue", alpha=0.5)
        ax.axvline(fwhm["right_halfmax_angle_deg"], color="tab:blue", alpha=0.5)
    ax.set_xlabel("theta in x-z steering plane (deg)")
    ax.set_ylabel("normalized source-order power")
    ax.set_title("Order-resolved 1D steering-plane cut (raw continuous cut unavailable)")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def plot_bar(out: Path) -> None:
    fig, ax = plt.subplots(figsize=(4.8, 3.4), dpi=160)
    vals = [BASELINE["x_power"], BASELINE["y_leakage"]]
    bars = ax.bar(["x-LP +1 target", "y-LP +1 leakage"], vals, color=["#2b6cb0", "#c53030"])
    ax.set_ylabel("source-normalized order power")
    ax.set_title(f"Target-order selectivity = {BASELINE['ratio']:.3f}x")
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, val, f"{val:.4f}", ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def plot_summary(output_dir: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), dpi=160)
    for ax, name, title in zip(axes.flat[:3], FIGURES[:3], ["x-LP proxy far-field", "y-LP proxy leakage", "1D order cut"]):
        img = plt.imread(output_dir / name)
        ax.imshow(img)
        ax.set_title(title, fontsize=9)
        ax.axis("off")
    img = plt.imread(output_dir / FIGURES[3])
    axes.flat[3].imshow(img)
    axes.flat[3].set_title("target selectivity", fontsize=9)
    axes.flat[3].axis("off")
    fig.suptitle("Stage12 LP-K6 450-nm plane-wave baseline visualization", fontsize=12)
    fig.tight_layout()
    fig.savefig(output_dir / FIGURES[4])
    plt.close(fig)


def make_manifest(inputs: list[str], figures: list[str], raw_arrays: list[str], output_dir: Path) -> dict:
    return {"input_files_used": inputs, "generated_figures": figures, "raw_farfield_arrays_found": raw_arrays, "output_dir": str(output_dir)}


def run_stage12_lp_k6_visualization(paths: Stage12LPVizPaths) -> dict[str, object]:
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    order_csv = paths.stage12_2_dir / "stage12_2_k6_forward_order_power.csv"
    result_csv = paths.stage12_2_dir / "stage12_2_k6_forward_fdtd_results.csv"
    order_rows = read_csv(order_csv)
    result_rows = read_csv(result_csv)
    raw = find_raw_arrays([paths.stage12_2_dir, paths.stage12_6_dir])
    by_pol = split_orders(order_rows)
    fwhm = fwhm_from_cut(
        [flt(r.get("theta_deg")) for r in by_pol["x"]],
        [flt(r.get("order_power_source_norm")) for r in by_pol["x"]],
        BASELINE["theta"],
    )
    if not raw:
        fwhm["fwhm_deg"] = math.nan
        fwhm["left_halfmax_angle_deg"] = math.nan
        fwhm["right_halfmax_angle_deg"] = math.nan
    vmax = max(proxy_grid(by_pol["x"])[2].max(), proxy_grid(by_pol["y"])[2].max())
    plot_proxy_map(by_pol["x"], paths.output_dir / FIGURES[0], "x-LP 450 nm far-field order proxy", BASELINE["x_power"], BASELINE["theta"], vmax=vmax)
    plot_proxy_map(by_pol["y"], paths.output_dir / FIGURES[1], "y-LP 450 nm leakage order proxy", BASELINE["y_leakage"], BASELINE["theta"], vmax=vmax)
    plot_1d_cut(by_pol["x"], by_pol["y"], paths.output_dir / FIGURES[2], fwhm)
    plot_bar(paths.output_dir / FIGURES[3])
    plot_summary(paths.output_dir)
    metrics = [{
        "input_polarization": "x",
        "wavelength_nm": 450.0,
        "target_angle_deg": BASELINE["theta"],
        **fwhm,
        "target_power": BASELINE["x_power"],
        "leakage_power": BASELINE["y_leakage"],
        "target_to_leakage_ratio": BASELINE["ratio"],
    }]
    write_csv(paths.output_dir / "stage12_lp_k6_450nm_farfield_fwhm_metrics.csv", metrics, list(metrics[0].keys()))
    manifest = make_manifest([str(order_csv), str(result_csv)], [str(paths.output_dir / f) for f in FIGURES], raw, paths.output_dir)
    (paths.output_dir / "stage12_lp_k6_450nm_plot_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    summary = [
        "# Stage12 LP-K6 450-nm Far-field Visualization",
        "",
        "This is 450-nm plane-wave LP-K6 steering visualization.",
        "This is not dipole-source/MicroLED directional emission.",
        f"x-LP is directed to the +10 deg target order with source-normalized +1 power `{BASELINE['x_power']}`.",
        f"y-LP target-order leakage is much lower: `{BASELINE['y_leakage']}`.",
        f"Target-order selectivity ratio: `{BASELINE['ratio']}`.",
        f"Extracted/measured x-LP main-lobe peak angle: `{fwhm['peak_angle_deg']}` deg.",
        f"Extracted x-LP main-lobe FWHM: `{fwhm['fwhm_deg']}` deg.",
        "Raw far-field arrays were not available; figures use existing order/angle summary data and order-power proxy maps.",
        "FWHM is reported as NaN because a continuous raw 1D far-field cut is unavailable.",
        "Boundary: read-only postprocessing; no FDTD, no new .fsp, no K6 rerun, no DBR, no RCLED, no dipole, no finite patch, no optimization.",
    ]
    (paths.output_dir / "stage12_lp_k6_450nm_visual_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    return {
        "output_folder": str(paths.output_dir),
        "figures": FIGURES,
        "raw_farfield_arrays_found": bool(raw),
        "peak_angle_deg": fwhm["peak_angle_deg"],
        "fwhm_deg": fwhm["fwhm_deg"],
        "y_lp_target_leakage": BASELINE["y_leakage"],
        "target_order_selectivity_ratio": BASELINE["ratio"],
    }
