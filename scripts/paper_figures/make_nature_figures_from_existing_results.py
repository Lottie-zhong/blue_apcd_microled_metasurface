#!/usr/bin/env python3
"""Generate publication figures from existing APCD/metasurface result files only.

This script performs no simulation and never imports lumapi. It scans existing
outputs/reports, anonymizes structure identifiers, and exports Nature-like
JPG/PDF/SVG figure bundles plus lightweight source indexes.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, Rectangle


FIG_W = 7.2
COLORS = {
    "blue": "#3B6FB6",
    "orange": "#D8833A",
    "teal": "#2A9D8F",
    "red": "#C44E52",
    "grey": "#8A8A8A",
    "light": "#D9E2EC",
    "dark": "#252525",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--out", default="outputs/paper_figures/nature_ready")
    parser.add_argument("--style", default="nature", choices=("nature",))
    parser.add_argument("--dpi", type=int, default=600)
    return parser.parse_args()


def configure_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 7,
            "axes.labelsize": 7.5,
            "axes.titlesize": 8,
            "xtick.labelsize": 6.5,
            "ytick.labelsize": 6.5,
            "legend.fontsize": 6.5,
            "axes.linewidth": 0.7,
            "xtick.major.width": 0.7,
            "ytick.major.width": 0.7,
            "xtick.major.size": 3,
            "ytick.major.size": 3,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "legend.frameon": False,
            "lines.linewidth": 0.8,
            "patch.linewidth": 0.55,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "savefig.facecolor": "white",
            "figure.facecolor": "white",
        }
    )


def panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(-0.15, 1.05, f"({label})", transform=ax.transAxes, fontsize=8,
            fontweight="bold", va="bottom", ha="left")


def save_figure(fig: plt.Figure, out_dir: Path, stem: str, dpi: int) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    names = []
    for suffix in ("jpg", "pdf", "svg"):
        path = out_dir / f"{stem}.{suffix}"
        kwargs = {"bbox_inches": "tight", "pad_inches": 0.04}
        if suffix == "jpg":
            kwargs.update({"dpi": max(dpi, 600), "pil_kwargs": {"quality": 95}})
        fig.savefig(path, **kwargs)
        names.append(path.name)
    plt.close(fig)
    return names


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def as_float(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    return float(value) if value not in (None, "") else math.nan


def finite(value: float) -> bool:
    return math.isfinite(value)


def csv_header(path: Path) -> set[str]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return set(next(csv.reader(handle), []))
    except (OSError, StopIteration, UnicodeDecodeError):
        return set()


def iter_files(roots: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(path for path in root.rglob("*") if path.is_file())
    return sorted(set(files), key=lambda path: str(path).lower())


def source_label(path: Path, repo_root: Path, data_root: Path) -> str:
    for prefix, root in (("red_archive", data_root), ("blue_repo", repo_root)):
        try:
            label = f"{prefix}/{path.resolve().relative_to(root.resolve()).as_posix()}"
            return sanitize_source_label(label)
        except ValueError:
            continue
    return sanitize_source_label(path.name)


def sanitize_source_label(label: str) -> str:
    """Remove identifiers and geometry-bearing PB case names from report paths."""
    label = re.sub(r"(?i)(?:cpk|aggr)_[^/\\]+", "<candidate-redacted>", label)
    label = re.sub(
        r"(?i)N6_L[0-9.]+_W[0-9.]+_H[0-9.]+_R[0-9.]+",
        "PB_N6_CASE_REDACTED",
        label,
    )
    return label


def write_indexes(
    files: Sequence[Path], repo_root: Path, data_root: Path, report_dir: Path
) -> tuple[list[Path], list[str]]:
    report_dir.mkdir(parents=True, exist_ok=True)
    labels = [source_label(path, repo_root, data_root) for path in files]
    (report_dir / "paper_figure_file_index.txt").write_text(
        "\n".join(labels) + ("\n" if labels else ""), encoding="utf-8"
    )
    relevant: list[Path] = []
    keywords = (
        "phase", "grating", "order_spectrum", "handedness", "dipole",
        "cone", "docp", "farfield", "position_average",
    )
    core_columns = {
        "phase_deg", "target_conversion", "opposite_spin_leakage",
        "conversion_to_leakage_ratio",
    }
    for path in files:
        if path.suffix.lower() != ".csv":
            continue
        header = csv_header(path)
        if core_columns.issubset(header) or any(key in path.name.lower() for key in keywords):
            relevant.append(path)
    relevant_labels = [source_label(path, repo_root, data_root) for path in relevant]
    (report_dir / "paper_figure_relevant_csvs.txt").write_text(
        "\n".join(relevant_labels) + ("\n" if relevant_labels else ""), encoding="utf-8"
    )
    candidate_dirs = sorted({str(Path(label).parent).replace("\\", "/") for label in relevant_labels})
    (report_dir / "paper_figure_candidate_dirs.txt").write_text(
        "\n".join(candidate_dirs) + ("\n" if candidate_dirs else ""), encoding="utf-8"
    )
    return relevant, labels


def find_named(files: Sequence[Path], filename: str) -> Path | None:
    matches = [path for path in files if path.name == filename]
    if not matches:
        return None
    preferred = [path for path in matches if "archive_mixed_height_k6_p179_p183" in str(path)]
    return sorted(preferred or matches, key=lambda path: str(path).lower())[0]


def find_by_columns(files: Sequence[Path], required: set[str]) -> Path | None:
    for path in files:
        if path.suffix.lower() == ".csv" and required.issubset(csv_header(path)):
            return path
    return None


def phase_display(value: float) -> float:
    wrapped = value % 360.0
    return 0.0 if math.isclose(wrapped, 360.0) else wrapped


def phase_sort_key(row: dict[str, str]) -> float:
    return phase_display(float(row["bin_deg"]))


def make_fig2(path: Path, out_dir: Path, dpi: int) -> list[str]:
    rows = sorted(read_csv(path), key=phase_sort_key)
    if len(rows) != 6:
        raise ValueError(f"Fig. 2 requires exactly six rows; found {len(rows)}")
    targets = np.array([phase_display(as_float(row, "bin_deg")) for row in rows])
    extracted = np.array([phase_display(as_float(row, "phase_deg")) for row in rows])
    conversion = np.array([as_float(row, "target_conversion") for row in rows])
    leakage = np.array([as_float(row, "opposite_spin_leakage") for row in rows])
    ratio = np.array([as_float(row, "conversion_to_leakage_ratio") for row in rows])
    error = np.array([as_float(row, "phase_error_to_bin") for row in rows])
    labels = [f"State {int(v)}" for v in targets]
    x = np.arange(6)

    fig, axes = plt.subplots(2, 2, figsize=(FIG_W, 4.7), constrained_layout=True)
    ax = axes[0, 0]
    ax.plot(x, targets, "--", color=COLORS["grey"], marker="o", ms=3, label="Ideal")
    ax.plot(x, extracted, color=COLORS["blue"], marker="o", ms=3.5, label="Extracted")
    ax.set_xticks(x, labels, rotation=35, ha="right")
    ax.set_ylabel("Phase (deg)")
    ax.set_ylim(-15, 330)
    ax.legend(loc="upper left")
    panel_label(ax, "a")

    ax = axes[0, 1]
    width = 0.36
    ax.bar(x - width / 2, conversion, width, color=COLORS["blue"], edgecolor="black", label="Target conversion")
    ax.bar(x + width / 2, leakage, width, color=COLORS["orange"], edgecolor="black", label="Opposite-spin leakage")
    ax.set_xticks(x, labels, rotation=35, ha="right")
    ax.set_ylabel("Power fraction")
    ax.set_ylim(0, 1.03)
    ax.legend(loc="upper center", ncol=2)
    panel_label(ax, "b")

    ax = axes[1, 0]
    ax.bar(x, ratio, color=COLORS["teal"], edgecolor="black")
    ax.axhline(6, color=COLORS["grey"], ls="--", lw=0.8, label="Ratio = 6")
    ax.set_xticks(x, labels, rotation=35, ha="right")
    ax.set_ylabel("Conversion-to-leakage ratio")
    ax.legend(loc="upper left")
    panel_label(ax, "c")

    ax = axes[1, 1]
    ax.bar(x, error, color=COLORS["red"], edgecolor="black")
    ax.axhline(25, color=COLORS["grey"], ls="--", lw=0.8, label="25 deg guide")
    ax.set_xticks(x, labels, rotation=35, ha="right")
    ax.set_ylabel("Phase error (deg)")
    ax.legend(loc="upper right")
    panel_label(ax, "d")
    return save_figure(fig, out_dir, "fig2_phase_library_metrics", dpi)


def make_fig3(path: Path, out_dir: Path, dpi: int) -> list[str]:
    rows = sorted(read_csv(path), key=lambda row: int(row["supercell_index"]))
    if len(rows) != 6:
        raise ValueError(f"Fig. 3 requires exactly six rows; found {len(rows)}")
    x = np.arange(6)
    cumulative = np.array([as_float(row, "cumulative_target_phase_deg") for row in rows])
    extracted = np.array([phase_display(as_float(row, "phase_deg")) for row in rows])
    conversion = np.array([as_float(row, "target_conversion") for row in rows])
    leakage = np.array([as_float(row, "opposite_spin_leakage") for row in rows])
    ratio = np.array([as_float(row, "conversion_to_leakage_ratio") for row in rows])
    states = [int(phase_display(as_float(row, "target_bin_deg"))) for row in rows]

    fig = plt.figure(figsize=(FIG_W, 4.35), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, height_ratios=(0.9, 1.1))
    ax = fig.add_subplot(gs[0, :])
    ax.set_xlim(-0.3, 6.3)
    ax.set_ylim(-0.2, 1.5)
    for i, (letter, state) in enumerate(zip("ABCDEF", states)):
        ax.add_patch(Rectangle((i + 0.08, 0.15), 0.84, 0.62, facecolor=COLORS["light"], edgecolor=COLORS["dark"], lw=0.7))
        ax.add_patch(Rectangle((i + 0.27, 0.28), 0.17, 0.36, angle=12, facecolor=COLORS["blue"], edgecolor="none"))
        ax.add_patch(Rectangle((i + 0.58, 0.28), 0.17, 0.36, angle=-12, facecolor=COLORS["orange"], edgecolor="none"))
        ax.text(i + 0.5, 0.94, f"{letter}\n{state} deg", ha="center", va="bottom", fontsize=6.5)
    ax.add_patch(FancyArrowPatch((0.2, 1.32), (5.8, 1.32), arrowstyle="-|>", mutation_scale=10, lw=0.9, color=COLORS["red"]))
    ax.text(3.0, 1.39, "60 deg phase ramp", ha="center", va="bottom", color=COLORS["red"], fontsize=7)
    ax.axis("off")
    panel_label(ax, "a")

    ax = fig.add_subplot(gs[1, 0])
    ax.plot(x, cumulative, color=COLORS["blue"], marker="o", ms=3.2)
    ax.set_xticks(x)
    ax.set_ylabel("Target phase (deg)")
    ax.set_xlabel("Supercell index")
    panel_label(ax, "b")
    ax = fig.add_subplot(gs[1, 1])
    ax.plot(x, extracted, color=COLORS["orange"], marker="o", ms=3.2)
    ax.set_xticks(x)
    ax.set_ylabel("Extracted phase (deg)")
    ax.set_xlabel("Supercell index")
    panel_label(ax, "c")

    ax = fig.add_subplot(gs[1, 2])
    ax.vlines(x, 0, conversion, color=COLORS["blue"], lw=2.2, label="Target conversion")
    ax.scatter(x, conversion, color=COLORS["blue"], s=18, zorder=3)
    ax.vlines(x, 0, leakage, color=COLORS["orange"], lw=2.2, label="Leakage")
    ax.scatter(x, leakage, color=COLORS["orange"], s=18, zorder=3)
    ax2 = ax.twinx()
    ax2.plot(x, ratio, color=COLORS["teal"], marker="D", ms=3, label="Ratio")
    ax.set_xticks(x, list("ABCDEF"))
    ax.set_xlabel("Anonymous structure")
    ax.set_ylabel("Power fraction")
    ax2.set_ylabel("Conversion/leakage")
    handles, labels = ax.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(handles + handles2, labels + labels2, loc="upper left", fontsize=5.5)
    ax.text(0.02, 0.02, "Mixed-height proof-of-concept", transform=ax.transAxes, fontsize=5.5, color=COLORS["dark"])
    panel_label(ax, "d")
    return save_figure(fig, out_dir, "fig3_k6_phase_ramp_summary", dpi)


def transmission_from_summary(path: Path | None) -> float | None:
    if path is None or not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"transmission_monitor_value\s*:\s*([0-9.eE+-]+)", text)
    return float(match.group(1)) if match else None


def make_fig4(path: Path, summary: Path | None, out_dir: Path, dpi: int) -> tuple[list[str], bool]:
    rows = read_csv(path)
    rows = sorted(rows, key=lambda row: as_float(row, "theta_x_deg"))
    theta = np.array([as_float(row, "theta_x_deg") for row in rows])
    values = np.array([as_float(row, "grating_value") for row in rows])
    order = np.array([int(float(row["order_n"])) for row in rows])
    transmission = transmission_from_summary(summary)

    fig, axes = plt.subplots(2, 2, figsize=(FIG_W, 4.8), constrained_layout=True)
    ax = axes[0, 0]
    colors = [COLORS["red"] if n == 1 else COLORS["blue"] for n in order]
    ax.bar(theta, values, width=5.2, color=colors, edgecolor="black")
    ax.axvline(15, color=COLORS["red"], ls="--", lw=0.8)
    ax.set_xlabel(r"Diffraction angle $\theta_x$ (deg)")
    ax.set_ylabel("Grating value")
    panel_label(ax, "a")

    selected = []
    for target in (-1, 0, 1):
        match = next((row for row in rows if int(float(row["order_n"])) == target and int(float(row.get("order_m", 0))) == 0), None)
        selected.append(as_float(match, "grating_value") if match else math.nan)
    ax = axes[0, 1]
    ax.bar(np.arange(3), selected, color=[COLORS["grey"], COLORS["blue"], COLORS["red"]], edgecolor="black")
    ax.set_xticks(np.arange(3), ["-1 (-15 deg)", "0 (0 deg)", "+1 (+15 deg)"], rotation=20, ha="right")
    ax.set_ylabel("Grating value")
    panel_label(ax, "b")

    ax = axes[1, 0]
    if transmission is not None:
        eta = values * transmission
        ax.bar(theta, eta, width=5.2, color=colors, edgecolor="black")
        ax.set_xlabel(r"Diffraction angle $\theta_x$ (deg)")
        ax.set_ylabel("Approx. source-normalized\norder efficiency")
        ax.text(0.02, 0.96, "grating value x monitor transmission", transform=ax.transAxes, va="top", fontsize=6)
    else:
        ax.text(0.5, 0.5, "Transmission monitor value unavailable", ha="center", va="center", transform=ax.transAxes)
        ax.axis("off")
    panel_label(ax, "c")

    ax = axes[1, 1]
    ax.axis("off")
    ax.text(0.03, 0.80, "+15 deg order exists", fontsize=10, fontweight="bold", color=COLORS["red"], transform=ax.transAxes)
    ax.text(0.03, 0.60, "but is not the dominant scalar order", fontsize=8, transform=ax.transAxes)
    ax.text(0.03, 0.34, "No order-resolved APCD\npolarization-channel claim", fontsize=8, fontweight="bold", transform=ax.transAxes)
    ax.text(0.03, 0.10, "Scalar/default extraction only", fontsize=7, color=COLORS["grey"], transform=ax.transAxes)
    panel_label(ax, "d")
    return save_figure(fig, out_dir, "fig4_k6_scalar_grating_orders", dpi), transmission is not None


def find_pb_summary(files: Sequence[Path]) -> Path | None:
    summaries = [
        path for path in files
        if path.name == "pb_sweep_summary.csv"
        and ("pb_supercell_N6_refine_LW_H450" in str(path) or "pb_supercell_N6_L210_W70_H_sweep" in str(path))
    ]
    if summaries:
        return sorted(summaries, key=lambda path: ("refine" not in str(path), str(path)))[0]
    candidates = [
        path for path in files
        if path.name.endswith("_handedness_summary.csv")
        and ("pb_supercell_N6_refine_LW_H450" in str(path) or "pb_supercell_N6_L210_W70_H_sweep" in str(path))
    ]
    return sorted(candidates, key=lambda path: str(path))[0] if candidates else None


def make_fig5(summary_path: Path, files: Sequence[Path], out_dir: Path, dpi: int) -> tuple[list[str], list[Path]]:
    rows = read_csv(summary_path)
    rows = [row for row in rows if finite(as_float(row, "target_efficiency_from_lcp")) and finite(as_float(row, "spin_extinction_ratio_db"))]
    if not rows:
        raise ValueError("PB summary has no finite efficiency/extinction rows")
    rows.sort(key=lambda row: as_float(row, "target_efficiency_from_lcp"), reverse=True)
    top_rows = rows[: min(12, len(rows))]
    labels = [f"PB-{i + 1}" for i in range(len(top_rows))]
    efficiency = np.array([as_float(row, "target_efficiency_from_lcp") for row in top_rows])
    extinction = np.array([as_float(row, "spin_extinction_ratio_db") for row in top_rows])
    top_case = top_rows[0].get("case_id", "")
    lcp = next((p for p in files if p.name == f"{top_case}_lcp_order_spectrum.csv"), None)
    rcp = next((p for p in files if p.name == f"{top_case}_rcp_order_spectrum.csv"), None)
    if lcp is None or rcp is None:
        raise ValueError("Top PB case lacks paired LCP/RCP order spectra")

    fig, axes = plt.subplots(2, 2, figsize=(FIG_W, 4.8), constrained_layout=True)
    ax = axes[0, 0]
    ax.bar(np.arange(len(top_rows)), efficiency, color=COLORS["blue"], edgecolor="black")
    ax.set_xticks(np.arange(len(top_rows)), labels, rotation=45, ha="right")
    ax.set_ylabel("Target efficiency from LCP")
    ax.set_ylim(0, 1.03)
    panel_label(ax, "a")
    ax = axes[0, 1]
    ax.bar(np.arange(len(top_rows)), extinction, color=COLORS["teal"], edgecolor="black")
    ax.set_xticks(np.arange(len(top_rows)), labels, rotation=45, ha="right")
    ax.set_ylabel("Spin extinction ratio (dB)")
    panel_label(ax, "b")

    for ax, spectrum_path, label, panel in ((axes[1, 0], lcp, "LCP incidence", "c"), (axes[1, 1], rcp, "RCP incidence", "d")):
        spectrum = read_csv(spectrum_path)
        order_n = np.array([int(float(row["order_n"])) for row in spectrum])
        value = np.array([as_float(row, "order_efficiency_total") for row in spectrum])
        ax.bar(order_n, value, width=0.72, color=COLORS["orange"] if panel == "c" else COLORS["grey"], edgecolor="black")
        ax.set_xlabel("Diffraction order n")
        ax.set_ylabel("Order efficiency")
        ax.set_title(label, loc="left", fontsize=7.5)
        panel_label(ax, panel)
    fig.suptitle("PB N=6 blue reference, not APCD", fontsize=8.5, fontweight="bold")
    return save_figure(fig, out_dir, "fig5_pb_n6_blue_reference", dpi), [summary_path, lcp, rcp]


def find_cp_position_average(files: Sequence[Path]) -> Path | None:
    required = {"position_id", "cone_deg", "DoCP_total_RminusL", "L_fraction_total", "R_fraction_total", "P_total"}
    candidates = [path for path in files if path.suffix.lower() == ".csv" and required.issubset(csv_header(path))]
    preferred = [path for path in candidates if path.name == "five_position_position_averages.csv"]
    return sorted(preferred or candidates, key=lambda path: str(path))[0] if candidates else None


def make_fig6(path: Path, out_dir: Path, dpi: int) -> list[str]:
    rows = read_csv(path)
    rows = [row for row in rows if all(finite(as_float(row, key)) for key in ("cone_deg", "DoCP_total_RminusL", "L_fraction_total", "R_fraction_total", "P_total"))]
    positions = sorted({row["position_id"] for row in rows})
    cones = sorted({as_float(row, "cone_deg") for row in rows})
    if len(positions) < 2 or len(cones) < 2:
        raise ValueError("CP robustness data lacks at least two positions and two cone angles")
    aliases = {name: f"Position {chr(65 + i)}" for i, name in enumerate(positions)}
    selected_cone = max(cones)
    selected = [row for row in rows if math.isclose(as_float(row, "cone_deg"), selected_cone)]
    selected.sort(key=lambda row: positions.index(row["position_id"]))
    x = np.arange(len(selected))
    labels = [aliases[row["position_id"]] for row in selected]
    docp = np.array([as_float(row, "DoCP_total_RminusL") for row in selected])
    lf = np.array([as_float(row, "L_fraction_total") for row in selected])
    rf = np.array([as_float(row, "R_fraction_total") for row in selected])
    power = np.array([as_float(row, "P_total") for row in selected])

    fig, axes = plt.subplots(2, 2, figsize=(FIG_W, 4.8), constrained_layout=True)
    ax = axes[0, 0]
    ax.bar(x, docp, color=[COLORS["blue"] if value < 0 else COLORS["red"] for value in docp], edgecolor="black")
    ax.axhline(0, color=COLORS["dark"], lw=0.7)
    ax.set_xticks(x, labels, rotation=35, ha="right")
    ax.set_ylabel("DoCP (R - L)")
    ax.set_title(f"Cone half-angle = {selected_cone:g} deg", loc="left")
    panel_label(ax, "a")
    ax = axes[0, 1]
    ax.bar(x, lf, color=COLORS["blue"], edgecolor="black", label="L fraction")
    ax.bar(x, rf, bottom=lf, color=COLORS["orange"], edgecolor="black", label="R fraction")
    ax.set_xticks(x, labels, rotation=35, ha="right")
    ax.set_ylabel("Polarization fraction")
    ax.set_ylim(0, 1)
    ax.legend(loc="upper center", ncol=2)
    panel_label(ax, "b")
    ax = axes[1, 0]
    ax.bar(x, power, color=COLORS["teal"], edgecolor="black")
    ax.set_yscale("log")
    ax.set_xticks(x, labels, rotation=35, ha="right")
    ax.set_ylabel("Total cone power (a.u.)")
    panel_label(ax, "c")
    ax = axes[1, 1]
    for position in positions:
        group = sorted((row for row in rows if row["position_id"] == position), key=lambda row: as_float(row, "cone_deg"))
        ax.plot([as_float(row, "cone_deg") for row in group], [as_float(row, "DoCP_total_RminusL") for row in group], marker="o", ms=2.8, label=aliases[position])
    ax.axhline(0, color=COLORS["grey"], lw=0.7)
    ax.set_xlabel("Cone half-angle (deg)")
    ax.set_ylabel("DoCP (R - L)")
    ax.legend(ncol=2, loc="best")
    panel_label(ax, "d")
    return save_figure(fig, out_dir, "fig6_cp_position_robustness", dpi)


def write_reports(
    report_dir: Path,
    generated: dict[str, list[str]],
    sources: dict[str, list[Path]],
    missing: list[str],
    repo_root: Path,
    data_root: Path,
    eta_used: bool,
) -> None:
    lines = [
        "# Nature-ready figures from existing results",
        "",
        "All panels were generated from existing CSV/Markdown results. No FDTD was run and no Lumerical solver was opened.",
        "",
        "## Generated figures",
        "",
    ]
    for key in sorted(generated):
        lines.append(f"### {key}")
        lines.append("")
        lines.append("Files: " + ", ".join(f"`{name}`" for name in generated[key]))
        lines.append("")
        lines.append("Sources:")
        for path in sources.get(key, []):
            lines.append(f"- `{source_label(path, repo_root, data_root)}`")
        lines.append("")
    lines.extend(
        [
            "## Metric definitions",
            "",
            "- `target_conversion`: power fraction in the intended converted-spin channel for a selected single-dimer state.",
            "- `opposite_spin_leakage`: power fraction in the undesired opposite-spin leakage channel.",
            "- `conversion_to_leakage_ratio`: target conversion divided by opposite-spin leakage.",
            "- `phase_error`: wrapped absolute phase difference between extracted phase and target phase state.",
            "- `grating_value`: scalar/default normalized grating-order value from the existing extraction.",
        ]
    )
    if eta_used:
        lines.append("- `eta_order_source_norm`: approximate source-normalized order efficiency, calculated as `grating_value x transmission_monitor_value`.")
    lines.extend(
        [
            "",
            "## Anonymization",
            "",
            "Candidate identifiers, exact geometry, and server paths are hidden from figure panels.",
            "",
            "- Structure A = 0 deg state",
            "- Structure B = 60 deg state",
            "- Structure C = 120 deg state",
            "- Structure D = 180 deg state",
            "- Structure E = 240 deg state",
            "- Structure F = 300 deg state",
            "",
            "## Interpretation boundaries",
            "",
            "- Mixed-height APCD K=6 proof-of-concept; not a final single-height fabrication library.",
            "- This is scalar/default grating-order extraction only; it is not order-resolved APCD alpha/beta polarization-channel extraction.",
            "- The +15 deg scalar order exists but is not the dominant scalar order; no verified APCD steering claim is made.",
            "- PB N=6 blue reference is not APCD.",
            "- CP dipole-position robustness, when present, is a separate blue-reference dataset and is not evidence for APCD K=6 steering.",
            "- No FDTD was run.",
            "",
            "## Figure contract and QA",
            "",
            "- Backend: Python/matplotlib only.",
            "- Archetypes: quantitative grids and a schematic-led composite.",
            "- Export: editable-text SVG/PDF and 600 dpi or higher JPG.",
            "- Image integrity: plots reproduce tabulated values; no interpolation or synthetic values were introduced.",
            "- Review risk: scalar diffraction data cannot establish order-resolved APCD polarization selectivity without a Jones-basis extraction.",
            "",
        ]
    )
    (report_dir / "nature_ready_README.md").write_text("\n".join(lines), encoding="utf-8")

    missing_lines = ["# Missing-data report", ""]
    if missing:
        missing_lines.extend(f"- {item}" for item in missing)
    else:
        missing_lines.append("- No requested figure was skipped for missing data.")
    missing_lines.extend(["", "No missing value was imputed or fabricated.", ""])
    (report_dir / "missing_data_report.md").write_text("\n".join(missing_lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    data_root = Path(args.data_root).resolve()
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = repo_root / out_dir
    report_dir = repo_root / "reports" / "paper_figures"
    configure_style()

    roots = [data_root / "outputs", data_root / "reports", repo_root / "outputs", repo_root / "reports"]
    files = iter_files(roots)
    write_indexes(files, repo_root, data_root, report_dir)
    generated: dict[str, list[str]] = {}
    sources: dict[str, list[Path]] = {}
    missing: list[str] = []
    eta_used = False

    fig2 = find_named(files, "outputs__apcd_k6_active_learning__p179_stage10_frozen_phase_library.csv")
    if fig2 is None:
        fig2 = find_by_columns(files, {"phase_deg", "target_conversion", "opposite_spin_leakage", "conversion_to_leakage_ratio"})
    if fig2:
        try:
            generated["Fig. 2 - APCD six-state phase-library metrics"] = make_fig2(fig2, out_dir, args.dpi)
            sources["Fig. 2 - APCD six-state phase-library metrics"] = [fig2]
        except (ValueError, KeyError) as exc:
            missing.append(f"Fig. 2 skipped: {exc}")
    else:
        missing.append("Fig. 2 skipped: no CSV contains all required phase-library columns.")

    fig3 = find_named(files, "outputs__apcd_k6_active_learning__p180_k6_phase_ramp_supercell_plan.csv")
    fig3_geometry = find_named(files, "outputs__apcd_k6_active_learning__p181_k6_supercell_geometry_plan.csv")
    if fig3:
        try:
            key = "Fig. 3 - APCD K=6 phase-ramp supercell summary"
            generated[key] = make_fig3(fig3, out_dir, args.dpi)
            sources[key] = [fig3] + ([fig3_geometry] if fig3_geometry else [])
        except (ValueError, KeyError) as exc:
            missing.append(f"Fig. 3 skipped: {exc}")
    else:
        missing.append("Fig. 3 skipped: K=6 phase-ramp plan CSV not found.")

    fig4 = find_named(files, "outputs__apcd_k6_metagrating_633nm__p182c_p181_phase_ramp_substrate_incidence_setup_only__p183_p182c_grating_orders.csv")
    fig4_summary = find_named(files, "outputs__apcd_k6_metagrating_633nm__p182c_p181_phase_ramp_substrate_incidence_setup_only__p183_p182c_grating_order_summary.md")
    if fig4:
        try:
            key = "Fig. 4 - APCD K=6 scalar grating orders"
            generated[key], eta_used = make_fig4(fig4, fig4_summary, out_dir, args.dpi)
            sources[key] = [fig4] + ([fig4_summary] if fig4_summary else [])
            if not eta_used:
                missing.append("Fig. 4 panel (c): transmission monitor value unavailable; approximate source-normalized efficiency omitted.")
        except (ValueError, KeyError) as exc:
            missing.append(f"Fig. 4 skipped: {exc}")
    else:
        missing.append("Fig. 4 skipped: scalar grating-order CSV not found.")

    pb_summary = find_pb_summary(files)
    if pb_summary:
        try:
            key = "Fig. 5 - PB N=6 blue reference (not APCD)"
            generated[key], sources[key] = make_fig5(pb_summary, files, out_dir, args.dpi)
        except (ValueError, KeyError) as exc:
            missing.append(f"Fig. 5 skipped: {exc}")
    else:
        missing.append("Fig. 5 skipped: no qualifying PB N=6 summary CSV found.")

    cp_path = find_cp_position_average(files)
    if cp_path:
        try:
            key = "Fig. 6 - CP dipole-position robustness"
            generated[key] = make_fig6(cp_path, out_dir, args.dpi)
            sources[key] = [cp_path]
        except (ValueError, KeyError) as exc:
            missing.append(f"Fig. 6 skipped: {exc}")
    else:
        missing.append("Fig. 6 skipped: no CSV with complete CP position, DoCP, L/R fraction, and total cone-power fields was found.")

    write_reports(report_dir, generated, sources, missing, repo_root, data_root, eta_used)
    print(f"Indexed files: {len(files)}")
    print(f"Generated figure groups: {len(generated)}")
    for key, names in generated.items():
        print(f"{key}: {', '.join(names)}")
    for item in missing:
        print(f"MISSING: {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
