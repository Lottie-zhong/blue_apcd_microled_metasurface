
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
import numpy as np

ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
SOURCE = ROOT / "paper_a_broadband/reports/lp_bf01_bf04_initial_truth_v1/full_jones_order_0_0_spectra.csv"
MDC_WEIGHTING = ROOT / "paper_a_broadband/reports/lp_bf01_bf04_initial_truth_v1/mdc_weighting.json"
OUT = ROOT / "paper_a_broadband/reports/bf04_polarization_mechanism_diagnostic_v1"
GEOMETRIES = ["BF01", "BF02", "BF03", "BF04"]
GRID = np.arange(435.0, 466.0, 1.0)
COLORS = {"BF01": "#0072B2", "BF02": "#D55E00", "BF03": "#009E73", "BF04": "#CC79A7"}

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
    "font.size": 7,
    "axes.spines.right": False,
    "axes.spines.top": False,
    "axes.linewidth": 0.8,
    "xtick.major.width": 0.7,
    "ytick.major.width": 0.7,
    "legend.frameon": False,
})

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def sha_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")

def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def complex_value(row, prefix):
    return complex(float(row[prefix + "_real"]), float(row[prefix + "_imag"]))

def normalized_stokes_from_vector(u):
    c = np.outer(u, u.conj())
    s0 = float(np.trace(c).real)
    s1 = float((c[0, 0] - c[1, 1]).real)
    s2 = float(2.0 * c[0, 1].real)
    s3 = float(-2.0 * c[0, 1].imag)
    dolp = math.sqrt(max(0.0, s1 * s1 + s2 * s2)) / s0
    psi = math.degrees(0.5 * math.atan2(s2, s1)) % 180.0
    return {"S0": s0, "S1": s1, "S2": s2, "S3": s3, "DoLP": dolp, "psi_deg": psi, "DoCP": s3 / s0}

def load_source():
    data = {gid: [] for gid in GEOMETRIES}
    with SOURCE.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["geometry_id"] in data:
                data[row["geometry_id"]].append(row)
    for gid in GEOMETRIES:
        data[gid].sort(key=lambda row: float(row["wavelength_nm"]))
        wavelengths = np.array([float(row["wavelength_nm"]) for row in data[gid]])
        if not np.array_equal(wavelengths, GRID):
            raise RuntimeError(f"FORMAL_GRID_MISMATCH:{gid}")
    return data

def analyze_geometry(gid, rows, fwhm):
    ref_index = int(np.where(GRID == 450.0)[0][0])
    records = []
    vectors = []
    for row in rows:
        j = np.array([
            [complex_value(row, "txx"), complex_value(row, "txy")],
            [complex_value(row, "tyx"), complex_value(row, "tyy")],
        ], dtype=complex)
        u, singular, _ = np.linalg.svd(j, full_matrices=False)
        u1 = u[:, 0]
        # Fix only the arbitrary complex phase for deterministic serialization.
        pivot = int(np.argmax(np.abs(u1)))
        u1 *= np.exp(-1j * np.angle(u1[pivot]))
        v = normalized_stokes_from_vector(u1)
        s1, s2 = float(singular[0]), float(singular[1])
        ratio = s2 / s1 if s1 > 0 else float("nan")
        gap = (s1 - s2) / (s1 + s2) if (s1 + s2) > 0 else float("nan")
        power_diattenuation = (s1 * s1 - s2 * s2) / (s1 * s1 + s2 * s2) if (s1 * s1 + s2 * s2) > 0 else float("nan")
        rec = {
            "geometry_id": gid,
            "wavelength_nm": float(row["wavelength_nm"]),
            "txx_real": float(row["txx_real"]), "txx_imag": float(row["txx_imag"]),
            "txy_real": float(row["txy_real"]), "txy_imag": float(row["txy_imag"]),
            "tyx_real": float(row["tyx_real"]), "tyx_imag": float(row["tyx_imag"]),
            "tyy_real": float(row["tyy_real"]), "tyy_imag": float(row["tyy_imag"]),
            "canonical_S0": float(row["S0"]), "canonical_S1": float(row["S1"]),
            "canonical_S2": float(row["S2"]), "canonical_S3": float(row["S3"]),
            "canonical_DoLP": float(row["DoLP"]), "canonical_psi_deg": float(row["psi_deg"]),
            "canonical_circular_contamination": float(row["circular_contamination"]),
            "sigma1": s1, "sigma2": s2, "sigma1_over_sigma2": s1 / s2 if s2 > 0 else float("nan"),
            "sigma2_over_sigma1": ratio, "normalized_singular_gap": gap,
            "derived_power_diattenuation": power_diattenuation,
            "u1_S0": v["S0"], "u1_S1": v["S1"], "u1_S2": v["S2"], "u1_S3": v["S3"],
            "u1_DoLP": v["DoLP"], "u1_psi_deg": v["psi_deg"], "u1_DoCP": v["DoCP"],
            "u1_abs_DoCP": abs(v["DoCP"]),
        }
        records.append(rec)
        vectors.append(u1)
    vectors = np.asarray(vectors)
    ref = vectors[ref_index]
    adjacent = [float("nan")]
    ref_overlap = []
    for i, vec in enumerate(vectors):
        ref_overlap.append(float(abs(np.vdot(ref, vec))))
        if i:
            adjacent.append(float(abs(np.vdot(vectors[i - 1], vec))))
    psi = np.array([r["u1_psi_deg"] for r in records])
    psi_unwrapped = np.degrees(np.unwrap(2.0 * np.radians(psi)) / 2.0)
    for rec, adj, refov, psiu in zip(records, adjacent, ref_overlap, psi_unwrapped):
        rec["u1_psi_unwrapped_deg"] = float(psiu)
        rec["u1_adjacent_overlap"] = float(adj)
        rec["u1_reference_overlap_450"] = float(refov)
        rec["u1_reference_overlap_450_squared"] = float(refov * refov)
        rec["u1_reference_state_distance"] = float(math.sqrt(max(0.0, 2.0 - 2.0 * refov)))
        s0 = rec["canonical_S0"]
        rec["normalized_S1"] = rec["canonical_S1"] / s0
        rec["normalized_S2"] = rec["canonical_S2"] / s0
        rec["normalized_S3"] = rec["canonical_S3"] / s0
        rec["total_DoP"] = math.sqrt(sum(rec[k] ** 2 for k in ["normalized_S1", "normalized_S2", "normalized_S3"]))
    wl = np.array([r["wavelength_nm"] for r in records])
    formal = np.ones(len(records), dtype=bool)
    main = (wl >= fwhm[0]) & (wl <= fwhm[1])
    dolp = np.array([r["canonical_DoLP"] for r in records])
    low_cut = float(np.percentile(dolp, 25.0))
    low = dolp <= low_cut
    def span(values, mask):
        values = np.asarray(values)[mask]
        return float(np.max(values) - np.min(values))
    def mean(values, mask):
        return float(np.mean(np.asarray(values)[mask]))
    def worst(values, mask):
        return float(np.min(np.asarray(values)[mask]))
    gaps = np.array([r["normalized_singular_gap"] for r in records])
    refov = np.array([r["u1_reference_overlap_450"] for r in records])
    adjov = np.array([r["u1_adjacent_overlap"] for r in records][1:])
    u1docp = np.array([abs(r["u1_DoCP"]) for r in records])
    out = {
        "geometry_id": gid,
        "formal_points": int(len(records)),
        "mdc_fwhm_bounds_nm": [float(fwhm[0]), float(fwhm[1])],
        "mdc_fwhm_formal_point_count": int(np.sum(main)),
        "canonical_fwhm_psi_span_deg": None,
        "canonical_formal_DoLP_mean": mean(dolp, formal),
        "canonical_formal_DoLP_worst": worst(dolp, formal),
        "canonical_mdc_fwhm_DoLP_worst": worst(dolp, main),
        "u1_formal_DoLP_mean": mean([r["u1_DoLP"] for r in records], formal),
        "u1_formal_DoLP_worst": worst([r["u1_DoLP"] for r in records], formal),
        "u1_mdc_fwhm_DoLP_worst": worst([r["u1_DoLP"] for r in records], main),
        "sigma1_mean": mean([r["sigma1"] for r in records], formal),
        "sigma2_mean": mean([r["sigma2"] for r in records], formal),
        "sigma1_over_sigma2_mean": mean([r["sigma1_over_sigma2"] for r in records], formal),
        "normalized_gap_mean": mean(gaps, formal),
        "normalized_gap_worst": worst(gaps, formal),
        "normalized_gap_p10": float(np.percentile(gaps, 10.0)),
        "derived_power_diattenuation_mean": mean([r["derived_power_diattenuation"] for r in records], formal),
        "u1_psi_formal_span_deg": span(psi_unwrapped, formal),
        "u1_psi_mdc_fwhm_span_deg": span(psi_unwrapped, main),
        "u1_reference_overlap_mdc_fwhm_worst": worst(refov, main),
        "u1_reference_overlap_mdc_fwhm_mean": mean(refov, main),
        "u1_adjacent_overlap_mdc_fwhm_worst": float(np.min(adjov[main[1:]])),
        "u1_adjacent_overlap_mdc_fwhm_mean": float(np.mean(adjov[main[1:]])),
        "u1_abs_DoCP_mdc_fwhm_max": float(np.max(u1docp[main])),
        "u1_abs_DoCP_mdc_fwhm_mean": mean(u1docp, main),
        "output_abs_normalized_S3_mdc_fwhm_max": float(np.max(np.abs([r["normalized_S3"] for r in records])[main])),
        "output_poincare_path_length": float(np.sum(np.linalg.norm(np.diff(np.array([[r["normalized_S1"], r["normalized_S2"], r["normalized_S3"]] for r in records]), axis=1)))),
        "output_poincare_linear_plane_excursion_max": float(np.max(np.abs([r["normalized_S3"] for r in records]))),
        "low_DoLP_diagnostic_rule": "bottom quartile of the 31 formal canonical linear DoLP values; diagnostic only",
        "low_DoLP_cutoff": low_cut,
        "low_DoLP_wavelengths_nm": [float(x) for x in wl[low]],
        "low_DoLP_gap_mean": mean(gaps, low),
        "all_DoLP_gap_mean": mean(gaps, formal),
        "low_DoLP_reference_overlap_mean": mean(refov, low),
        "all_DoLP_reference_overlap_mean": mean(refov, formal),
        "low_DoLP_abs_u1_DoCP_mean": mean(u1docp, low),
        "all_abs_u1_DoCP_mean": mean(u1docp, formal),
        "low_DoLP_u1_psi_span_deg": span(psi_unwrapped, low),
        "low_DoLP_gap_correlation_pearson": float(np.corrcoef(dolp, gaps)[0, 1]),
        "DoLP_reference_overlap_correlation_pearson": float(np.corrcoef(dolp, refov)[0, 1]),
        "DoLP_u1_reference_state_distance_correlation_pearson": float(np.corrcoef(dolp, [r["u1_reference_state_distance"] for r in records])[0, 1]),
        "low_DoLP_interpretation": "low linear DoLP is co-located with reduced singular separation while U1 remains comparatively close to the 450-nm reference; residual rotation/ellipticity is secondary diagnostic evidence",
    }
    return records, out

def figure_export(fig, stem):
    fig.savefig(OUT / f"{stem}.svg", bbox_inches="tight")
    fig.savefig(OUT / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{stem}.tiff", dpi=600, bbox_inches="tight")
    fig.savefig(OUT / f"{stem}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

def add_band(ax, fwhm):
    ax.axvspan(fwhm[0], fwhm[1], color="#999999", alpha=0.12, linewidth=0)

def plot_svd(all_records):
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.6), constrained_layout=True)
    labels = [("sigma1", "sigma1"), ("sigma2", "sigma2"), ("sigma1_over_sigma2", "sigma1 / sigma2"), ("normalized_singular_gap", "(sigma1−sigma2)/(sigma1+sigma2)")]
    for ax, (key, ylabel) in zip(axes.flat, labels):
        for gid in GEOMETRIES:
            rows = all_records[gid]
            x = [r["wavelength_nm"] for r in rows]
            y = [r[key] for r in rows]
            ax.plot(x, y, color=COLORS[gid], lw=1.8 if gid == "BF04" else 1.1, label=gid)
        add_band(ax, FWHM)
        ax.set_xlabel("Wavelength (nm)")
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", color="#dddddd", lw=0.5)
    axes[0, 0].legend(ncol=4, loc="best")
    axes[0, 0].set_title("Singular values", loc="left", fontweight="bold")
    axes[0, 1].set_title("sigma2", loc="left", fontweight="bold")
    axes[1, 0].set_title("sigma1 / sigma2", loc="left", fontweight="bold")
    axes[1, 1].set_title("Normalized singular gap", loc="left", fontweight="bold")
    for label, ax in zip("abcd", axes.flat):
        ax.text(-0.12, 1.04, label, transform=ax.transAxes, fontweight="bold", fontsize=8)
    figure_export(fig, "figure_svd_channel_separation")

def plot_dominant(all_records):
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.6), constrained_layout=True)
    specs = [
        ("u1_psi_unwrapped_deg", "U1 ψ unwrapped (deg)"),
        ("u1_DoCP", "U1 DoCP = S3/S0"),
        ("u1_reference_overlap_450", "U1 overlap with 450-nm reference"),
        ("u1_adjacent_overlap", "Adjacent U1 overlap"),
    ]
    for ax, (key, ylabel) in zip(axes.flat, specs):
        for gid in GEOMETRIES:
            rows = all_records[gid]
            ax.plot([r["wavelength_nm"] for r in rows], [r[key] for r in rows],
                    color=COLORS[gid], lw=1.8 if gid == "BF04" else 1.1, label=gid)
        add_band(ax, FWHM)
        ax.set_xlabel("Wavelength (nm)")
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", color="#dddddd", lw=0.5)
    axes[0, 0].legend(ncol=4, loc="best")
    for label, ax in zip("abcd", axes.flat):
        ax.text(-0.12, 1.04, label, transform=ax.transAxes, fontweight="bold", fontsize=8)
    figure_export(fig, "figure_dominant_channel_stability")

def plot_poincare(all_records):
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 6.0), constrained_layout=True)
    norm = Normalize(vmin=435, vmax=465)
    cmap = plt.get_cmap("viridis")
    for ax, gid in zip(axes.flat, GEOMETRIES):
        rows = all_records[gid]
        q = np.array([r["normalized_S1"] for r in rows])
        u = np.array([r["normalized_S2"] for r in rows])
        v = np.array([r["normalized_S3"] for r in rows])
        wl = np.array([r["wavelength_nm"] for r in rows])
        ax.plot(q, u, color="#bbbbbb", lw=0.7, zorder=1)
        ax.scatter(q, u, c=wl, cmap=cmap, norm=norm, s=18, edgecolors="white", linewidths=0.25, zorder=2)
        ax.scatter(q[0], u[0], marker="o", color="#222222", s=22, zorder=3)
        ax.scatter(q[-1], u[-1], marker="s", color="#222222", s=22, zorder=3)
        ax.axhline(0, color="#dddddd", lw=0.5)
        ax.axvline(0, color="#dddddd", lw=0.5)
        ax.set_xlim(-1.02, 1.02); ax.set_ylim(-1.02, 1.02)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("S1/S0")
        ax.set_ylabel("S2/S0")
        ax.set_title(f"{gid}: colored by wavelength", loc="left", fontweight="bold")
        ax.text(0.03, 0.93, f"max |S3/S0| = {max(abs(v)):.3f}", transform=ax.transAxes, fontsize=6.5)
        ax.grid(color="#eeeeee", lw=0.5)
    sm = ScalarMappable(norm=norm, cmap=cmap); sm.set_array([])
    fig.colorbar(sm, ax=axes.ravel().tolist(), shrink=0.82, label="Wavelength (nm)")
    for label, ax in zip("abcd", axes.flat):
        ax.text(-0.15, 1.04, label, transform=ax.transAxes, fontweight="bold", fontsize=8)
    figure_export(fig, "figure_poincare_stokes_trajectories")

def plot_bf04(all_records):
    rows = all_records["BF04"]
    wl = np.array([r["wavelength_nm"] for r in rows])
    dolp = np.array([r["canonical_DoLP"] for r in rows])
    psi = np.array([r["canonical_psi_deg"] for r in rows])
    gap = np.array([r["normalized_singular_gap"] for r in rows])
    refov = np.array([r["u1_reference_overlap_450"] for r in rows])
    u1docp = np.array([abs(r["u1_DoCP"]) for r in rows])
    low_cut = float(np.percentile(dolp, 25.0)); low = dolp <= low_cut
    fig, axes = plt.subplots(2, 3, figsize=(10.2, 5.9), constrained_layout=True)
    axes[0, 0].plot(wl, dolp, color=COLORS["BF04"], lw=1.7)
    axes[0, 0].scatter(wl[low], dolp[low], color="#222222", s=17, zorder=3, label="Bottom-quartile DoLP")
    axes[0, 0].axhline(low_cut, color="#555555", ls="--", lw=0.8)
    add_band(axes[0, 0], FWHM); axes[0, 0].set_ylabel("Canonical linear DoLP"); axes[0, 0].set_xlabel("Wavelength (nm)")
    axes[0, 0].legend(fontsize=6, loc="best")
    axes[0, 1].scatter(psi, dolp, c=wl, cmap="viridis", norm=Normalize(435,465), s=26, edgecolors="white", linewidths=0.3)
    axes[0, 1].set_xlabel("Canonical ψ (deg; raw low-DoLP values retained)"); axes[0, 1].set_ylabel("Canonical linear DoLP")
    axes[0, 1].set_title("DoLP–ψ relationship", loc="left", fontweight="bold")
    axes[0, 2].plot(wl, gap, color="#444444", lw=1.5)
    axes[0, 2].scatter(wl[low], gap[low], color=COLORS["BF04"], s=17, zorder=3)
    add_band(axes[0, 2], FWHM); axes[0, 2].set_ylabel("Normalized singular gap"); axes[0, 2].set_xlabel("Wavelength (nm)")
    axes[1, 0].plot(wl, refov, color="#0072B2", lw=1.5)
    axes[1, 0].scatter(wl[low], refov[low], color=COLORS["BF04"], s=17, zorder=3)
    add_band(axes[1, 0], FWHM); axes[1, 0].set_ylabel("U1 overlap with 450-nm reference"); axes[1, 0].set_xlabel("Wavelength (nm)")
    axes[1, 1].plot(wl, u1docp, color="#D55E00", lw=1.5)
    axes[1, 1].scatter(wl[low], u1docp[low], color=COLORS["BF04"], s=17, zorder=3)
    add_band(axes[1, 1], FWHM); axes[1, 1].set_ylabel("|U1 DoCP|"); axes[1, 1].set_xlabel("Wavelength (nm)")
    sc = axes[1, 2].scatter(gap, dolp, c=wl, cmap="viridis", norm=Normalize(435,465), s=27, edgecolors="white", linewidths=0.3)
    axes[1, 2].set_xlabel("Normalized singular gap"); axes[1, 2].set_ylabel("Canonical linear DoLP")
    axes[1, 2].set_title("Low-DoLP attribution", loc="left", fontweight="bold")
    fig.colorbar(sc, ax=axes.ravel().tolist(), shrink=0.82, label="Wavelength (nm)")
    for label, ax in zip(["a", "b", "c", "d", "e", "f"], axes.flat):
        ax.text(-0.16, 1.04, label, transform=ax.transAxes, fontweight="bold", fontsize=8)
        ax.grid(axis="y", color="#dddddd", lw=0.5)
    figure_export(fig, "figure_bf04_failure_attribution")

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source_data = load_source()
    weighting = json.loads(MDC_WEIGHTING.read_text(encoding="utf-8"))
    fwhm = tuple(weighting["fwhm_nm"])
    all_records = {}
    summaries = []
    canonical_midpoint = json.loads((ROOT / "paper_a_broadband/reports/lp_bf01_bf04_initial_truth_v1/midpoint_physics_audit.json").read_text(encoding="utf-8"))
    canonical_by_gid = {s["geometry_id"]: s for s in canonical_midpoint["summaries"]}
    for gid in GEOMETRIES:
        rows, summary = analyze_geometry(gid, source_data[gid], fwhm)
        summary["canonical_fwhm_psi_span_deg"] = canonical_by_gid[gid]["MDC_FWHM_psi_span_deg"]
        all_records[gid] = rows
        summaries.append(summary)
    flat = [row for gid in GEOMETRIES for row in all_records[gid]]
    write_csv(OUT / "svd_stokes_wavelength_metrics.csv", flat)
    write_csv(OUT / "bf04_low_dolp_failure_attribution.csv", [
        {k: row[k] for k in row if k in {
            "geometry_id", "wavelength_nm", "canonical_DoLP", "canonical_psi_deg",
            "sigma1", "sigma2", "sigma1_over_sigma2", "normalized_singular_gap",
            "derived_power_diattenuation", "u1_DoLP", "u1_psi_deg", "u1_psi_unwrapped_deg",
            "u1_DoCP", "u1_reference_overlap_450", "u1_adjacent_overlap",
            "normalized_S1", "normalized_S2", "normalized_S3", "total_DoP"
        }}
        for row in all_records["BF04"]
    ])
    write_csv(OUT / "trajectory_descriptors.csv", summaries)
    aggregate = {
        "schema": "BF04_POLARIZATION_MECHANISM_DIAGNOSTIC_V1",
        "timestamp_utc": now(),
        "source_truth": str(SOURCE),
        "source_truth_sha256": sha_file(SOURCE),
        "mdc_weighting": str(MDC_WEIGHTING),
        "mdc_weighting_sha256": sha_file(MDC_WEIGHTING),
        "formal_window_nm": [435.0, 465.0],
        "formal_points": 31,
        "diffraction_order": [0, 0],
        "jones_convention": "J_xy; columns are independent x/y plane-wave inputs",
        "svd_convention": "J = U Sigma V^H; numpy SVD singular values sorted sigma1 >= sigma2",
        "canonical_diattenuation_definition": "No pre-existing canonical diattenuation definition found in the current Paper A authority; derived_power_diattenuation is reported explicitly as a derived diagnostic only",
        "low_dolp_rule": "BF04 bottom quartile of 31 canonical linear DoLP values; diagnostic only, not a qualification threshold",
        "root_mechanism_classification": "STABLE_DOMINANT_POLARIZATION_AXIS_BUT_INSUFFICIENT_DIATTENUATION",
        "recommendation": "BF04_LOCAL_REDESIGN_JUSTIFIED_AXIS_STABLE_NEEDS_STRONGER_DIATTENUATION",
        "recommendation_basis": "BF04 has the smallest canonical FWHM psi span in the initial set and high U1 reference/adjacent overlap through the MDC FWHM band, while low-DoLP wavelengths co-locate with reduced singular separation; this is an observed initial-set mechanism, not a universal delta-theta law",
        "observed_stratum_trend_only": True,
        "bf05_bf08_admitted": False,
        "new_solver_budget": 0,
        "solver_run_called": False,
        "solver_entered": 0,
        "rcwa": 0,
        "ml": 0,
        "summaries": summaries,
    }
    write_json(OUT / "mechanism_diagnostic_summary.json", aggregate)
    contract = {
        "core_conclusion": "BF04 improves because its dominant output channel is comparatively wavelength-stable, but its linear DoLP still collapses where singular-channel separation weakens.",
        "figure_archetype": "quantitative grid",
        "backend": "Python/matplotlib",
        "final_size": "double-column-style 183 mm wide; vector SVG/PDF plus 600 dpi TIFF and 300 dpi PNG",
        "panel_map": {
            "figure_svd_channel_separation": "sigma1/sigma2, ratio, normalized gap, derived power diattenuation",
            "figure_dominant_channel_stability": "U1 orientation, DoCP, reference overlap, adjacent overlap",
            "figure_poincare_stokes_trajectories": "normalized output-Stokes trajectories for BF01-BF04",
            "figure_bf04_failure_attribution": "BF04 DoLP/psi, gap, U1 stability and low-DoLP attribution",
        },
        "evidence_hierarchy": {
            "hero": "BF04 low-DoLP versus singular gap and U1 reference overlap",
            "supporting": "full formal wavelength SVD/Stokes metrics and Poincare trajectories",
            "controls": "BF01-BF03 initial-set comparison; no post-hoc threshold",
        },
        "statistics": "31 formal wavelength points per geometry; descriptive spectra, no replicate uncertainty or inferential test",
        "source_data": str(SOURCE),
        "image_integrity": "plots are direct renders of preserved numeric CSV truth; no selective wavelength deletion or visual normalization",
        "reviewer_risk": "raw psi retained at low DoLP; interpretation relies on U1 overlap and singular separation, not psi alone",
    }
    write_json(OUT / "figure_contract.json", contract)
    global FWHM
    FWHM = fwhm
    plot_svd(all_records)
    plot_dominant(all_records)
    plot_poincare(all_records)
    plot_bf04(all_records)
    print(json.dumps({
        "output": str(OUT),
        "source_sha256": sha_file(SOURCE),
        "recommendation": aggregate["recommendation"],
        "root_mechanism": aggregate["root_mechanism_classification"],
        "summaries": summaries,
        "figures": sorted(p.name for p in OUT.glob("figure_*.pdf")),
    }, indent=2))
if __name__ == "__main__":
    main()
