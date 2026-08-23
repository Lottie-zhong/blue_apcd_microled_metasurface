from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, TwoSlopeNorm
from matplotlib.cm import ScalarMappable
import numpy as np

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
HF = ROOT / "outputs/np_k6_m8a_primary2_closeout_v1/hf22_formal_development_484rows.csv"
OOF = ROOT / "outputs/np_k6_m9_22g_forward_retraining_v1/oof_predictions_22g.csv"
M9A = ROOT / "outputs/np_k6_m9a_normal_incidence_plateau_reassessment_v1/normal_incidence_freeze_decision.json"
SCRIPT = ROOT / "scripts/np_k6_frozen_forward_surrogate_order_heatmap_nature_figure_v1.py"
FIG = ROOT / "figures/np_k6_frozen_forward_surrogate_order_heatmap_nature_figure_v1"
OUT = ROOT / "outputs/np_k6_frozen_forward_surrogate_order_heatmap_nature_figure_v1"
DOC = ROOT / "docs/np_k6_frozen_forward_surrogate_order_heatmap_nature_figure_v1.md"
RANKING_MODEL = "LF_only"
SPECTRAL_MODEL = "LF_ridge_residual"
VARIANT = "ensemble_raw"
ORDERS = [-3, -2, -1, 0, 1, 2, 3]
WAVELENGTHS = list(range(445, 456))

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader(); w.writerows(rows)

def average_ranks(values: list[float]) -> np.ndarray:
    a = np.asarray(values, dtype=float)
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(len(a), dtype=float)
    i = 0
    while i < len(a):
        j = i + 1
        while j < len(a) and a[order[j]] == a[order[i]]:
            j += 1
        ranks[order[i:j]] = (i + 1 + j) / 2.0
        i = j
    return ranks

def spearman(x: list[float], y: list[float]) -> float:
    return float(np.corrcoef(average_ranks(x), average_ranks(y))[0, 1])

def key(row: dict[str, str]) -> tuple[str, str, int]:
    return row["geometry_id"], row["polarization"], int(float(row["wavelength_nm"]))

def truth_order(row: dict[str, str], m: int) -> float:
    return float(row[f"eta_m{m:+d}"])

def pred_order(row: dict[str, str], m: int) -> float:
    return float(row[f"pred_eta_m{m:+d}"])

def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
    hf_rows = read_csv(HF)
    all_oof = read_csv(OOF)
    ranking_rows = [r for r in all_oof if r["model"] == RANKING_MODEL and r["variant"] == VARIANT]
    spectral_rows = [r for r in all_oof if r["model"] == SPECTRAL_MODEL and r["variant"] == VARIANT]
    assert len(hf_rows) == len(ranking_rows) == len(spectral_rows) == 484
    assert sorted({int(float(r["wavelength_nm"])) for r in hf_rows}) == WAVELENGTHS
    assert sorted({r["polarization"] for r in hf_rows}) == ["p", "s"]
    stable_truth = sorted(int(name.removeprefix("eta_m")) for name in hf_rows[0] if name.startswith("eta_m") and name not in {"eta_minus1"})
    stable_pred = sorted(int(name.removeprefix("pred_eta_m")) for name in spectral_rows[0] if name.startswith("pred_eta_m"))
    assert stable_truth == stable_pred == ORDERS
    hf = {key(r): r for r in hf_rows}; rank = {key(r): r for r in ranking_rows}; spec = {key(r): r for r in spectral_rows}
    assert len(hf) == len(rank) == len(spec) == 484

    geometries = sorted({r["geometry_id"] for r in hf_rows})
    ranking_data = []
    selection = []
    for geometry in geometries:
        ks = sorted(k for k in hf if k[0] == geometry)
        truth_score = float(np.mean([truth_order(hf[k], 1) for k in ks]))
        pred_score = float(np.mean([pred_order(rank[k], 1) for k in ks]))
        mae = float(np.mean([abs(truth_order(hf[k], 1) - pred_order(spec[k], 1)) for k in ks]))
        ranking_data.append({"geometry_id": geometry, "fdt_broadband_eta_plus1_score": truth_score, "predicted_broadband_eta_plus1_score": pred_score, "ranking_provider": f"{RANKING_MODEL}/{VARIANT}", "replicate_unit": "one held-out geometry"})
        selection.append((mae, geometry))
    selection.sort(key=lambda x: (x[0], x[1]))
    indices = {"Best": 0, "Median": (len(selection) - 1) // 2, "Worst": len(selection) - 1}
    selected = []
    for label, idx in indices.items():
        mae, geometry = selection[idx]
        selected.append({"selection": label, "rank_ascending_eta_plus1_mae": idx + 1, "geometry_count": len(selection), "geometry_id": geometry, "error_metric": "mean absolute eta(+1) OOF error over explicit P/S and all 11 wavelengths", "error_value": mae, "prediction_source": f"{SPECTRAL_MODEL}/{VARIANT}", "truth_source": "HF22 formal held-out authority"})
    rho = spearman([r["fdt_broadband_eta_plus1_score"] for r in ranking_data], [r["predicted_broadband_eta_plus1_score"] for r in ranking_data])
    assert abs(rho - 0.961603613777527) < 1e-12

    heat_rows = []
    for info in selected:
        geometry = info["geometry_id"]
        for pol in ("p", "s"):
            for wl in WAVELENGTHS:
                k = (geometry, pol, wl)
                for m in ORDERS:
                    t = truth_order(hf[k], m); p = pred_order(spec[k], m)
                    heat_rows.append({"selection": info["selection"], "rank": info["rank_ascending_eta_plus1_mae"], "geometry_id": geometry, "polarization": "P_XLIKE" if pol == "p" else "S_YLIKE", "wavelength_nm": wl, "diffraction_order_m": m, "fdt_absolute_order_efficiency": t, "predicted_absolute_order_efficiency": p, "absolute_prediction_error": abs(t - p), "spectral_provider": f"{SPECTRAL_MODEL}/{VARIANT}"})
    assert len(heat_rows) == 3 * 2 * 11 * 7
    write_csv(OUT / "heldout_ranking_data.csv", ranking_data, list(ranking_data[0]))
    write_csv(OUT / "representative_order_heatmap_data.csv", heat_rows, list(heat_rows[0]))
    write_json(OUT / "representative_cases.json", {"selection_policy": "ascending geometry-level mean absolute eta(+1) OOF error; lower central rank used for even n", "selected_cases": selected})

    mpl.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": 5.7, "axes.titlesize": 6.2, "axes.labelsize": 5.7, "xtick.labelsize": 5.1, "ytick.labelsize": 5.1,
        "axes.linewidth": 0.65, "axes.spines.top": False, "axes.spines.right": False,
        "xtick.direction": "out", "ytick.direction": "out", "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "svg.fonttype": "none", "pdf.fonttype": 42, "legend.frameon": False,
    })
    fig = plt.figure(figsize=(7.205, 6.45), facecolor="white")
    outer = fig.add_gridspec(2, 1, height_ratios=[1.2, 4.8], left=0.125, right=0.93, top=0.96, bottom=0.075, hspace=0.22)
    top = outer[0].subgridspec(1, 2, width_ratios=[1.25, 1.65], wspace=0.34)
    ax_rank = fig.add_subplot(top[0, 0])
    ax_note = fig.add_subplot(top[0, 1]); ax_note.set_axis_off()

    x = np.asarray([r["fdt_broadband_eta_plus1_score"] for r in ranking_data]); y = np.asarray([r["predicted_broadband_eta_plus1_score"] for r in ranking_data])
    lo = min(float(x.min()), float(y.min())) - 0.03; hi = max(float(x.max()), float(y.max())) + 0.05
    ax_rank.plot([lo, hi], [lo, hi], color="#777777", lw=0.75, zorder=1)
    ax_rank.scatter(x, y, s=17, color="#3B708F", edgecolor="white", linewidth=0.35, zorder=2)
    ax_rank.set_xlim(lo, hi); ax_rank.set_ylim(lo, hi)
    ax_rank.set_xlabel("FDTD broadband score"); ax_rank.set_ylabel("Predicted broadband score")
    ax_rank.set_title("Held-out geometry ranking", loc="left", pad=3.0, fontweight="bold")
    ax_rank.text(0.04, 0.94, f"22 geometries\nSpearman ρ = {rho:.3f}", transform=ax_rank.transAxes, ha="left", va="top", fontsize=5.5, color="#333333")
    ax_rank.text(-0.13, 1.10, "a", transform=ax_rank.transAxes, fontsize=8, fontweight="bold", va="top")
    ax_note.text(0.0, 0.90, "Frozen provider components", fontsize=6.4, fontweight="bold", va="top")
    ax_note.text(0.0, 0.68, "Ranking   LF_only / ensemble_raw\nSpectra    LF_ridge_residual / ensemble_raw", fontsize=5.6, va="top", linespacing=1.45)
    ax_note.text(0.0, 0.30, "Distinct components; not a universal surrogate\nu_x = 0, k_y = 0 · explicit P/S · 445–455 nm", fontsize=5.3, color="#444444", va="top", linespacing=1.45)

    bottom = outer[1].subgridspec(3, 4, width_ratios=[1, 1, 1, 0.06], wspace=0.20, hspace=0.28)
    values = [float(r["fdt_absolute_order_efficiency"]) for r in heat_rows] + [float(r["predicted_absolute_order_efficiency"]) for r in heat_rows]
    errors = [float(r["absolute_prediction_error"]) for r in heat_rows]
    eff_min = min(0.0, min(values)); eff_max = max(values)
    eff_norm = TwoSlopeNorm(vmin=eff_min, vcenter=0.0, vmax=eff_max) if eff_min < 0 else Normalize(0, eff_max)
    err_norm = Normalize(0, max(errors))
    eff_cmap = plt.get_cmap("coolwarm")
    err_cmap = plt.get_cmap("magma")
    x_edges = np.arange(444.5, 456.0, 1.0); y_edges = np.arange(-3.5, 4.0, 1.0)
    pair_axes: dict[tuple[int, int], tuple] = {}
    for row_i, info in enumerate(selected):
        geometry = info["geometry_id"]
        for col_i, kind in enumerate(("fdt", "prediction", "error")):
            cell = bottom[row_i, col_i].subgridspec(2, 1, hspace=0.13)
            axes = []
            for pol_i, pol in enumerate(("P_XLIKE", "S_YLIKE")):
                ax = fig.add_subplot(cell[pol_i, 0]); axes.append(ax)
                data = np.empty((len(ORDERS), len(WAVELENGTHS)), dtype=float)
                subset = [r for r in heat_rows if r["selection"] == info["selection"] and r["polarization"] == pol]
                by = {(int(r["diffraction_order_m"]), int(r["wavelength_nm"])): r for r in subset}
                for oi, m in enumerate(ORDERS):
                    for wi, wl in enumerate(WAVELENGTHS):
                        rec = by[(m, wl)]
                        data[oi, wi] = float(rec[{"fdt": "fdt_absolute_order_efficiency", "prediction": "predicted_absolute_order_efficiency", "error": "absolute_prediction_error"}[kind]])
                ax.pcolormesh(x_edges, y_edges, data, cmap=err_cmap if kind == "error" else eff_cmap, norm=err_norm if kind == "error" else eff_norm, shading="flat", rasterized=False)
                ax.set_xlim(444.5, 455.5); ax.set_ylim(-3.5, 3.5)
                ax.set_yticks([-3, 0, 3]); ax.set_xticks([445, 450, 455])
                ax.set_title(pol, loc="left", pad=1.0, fontsize=5.1, fontweight="normal")
                if col_i != 0: ax.set_yticklabels([])
                if pol_i == 0: ax.set_xticklabels([])
                if row_i < 2 and pol_i == 1: ax.set_xticklabels([])
                if row_i == 2 and pol_i == 1: ax.set_xlabel("Wavelength (nm)", labelpad=1.5)
                ax.tick_params(length=2.0, pad=1.3)
            pair_axes[(row_i, col_i)] = tuple(axes)

    cslot = bottom[:, 3].subgridspec(2, 1, hspace=0.55)
    cax_eff = fig.add_subplot(cslot[0, 0]); cax_err = fig.add_subplot(cslot[1, 0])
    cb1 = fig.colorbar(ScalarMappable(norm=eff_norm, cmap=eff_cmap), cax=cax_eff)
    eff_ticks = sorted({round(eff_min, 2), 0.0, 0.2, 0.4, 0.6})
    eff_ticks = [tick for tick in eff_ticks if eff_min <= tick <= eff_max]
    cb1.set_ticks(eff_ticks)
    cb1.set_label("Absolute order efficiency", fontsize=5.2, labelpad=3); cb1.ax.tick_params(labelsize=5.1, length=2)
    cb2 = fig.colorbar(ScalarMappable(norm=err_norm, cmap=err_cmap), cax=cax_err)
    cb2.set_label("Absolute prediction error", fontsize=5.2, labelpad=3); cb2.ax.tick_params(labelsize=5.1, length=2)
    fig.canvas.draw()
    for col_i, title in enumerate(("FDTD", "Prediction", "Absolute error")):
        a = pair_axes[(0, col_i)][0].get_position()
        fig.text((a.x0 + a.x1) / 2, a.y1 + 0.033, title, ha="center", va="bottom", fontsize=6.5, fontweight="bold")
    first_top = pair_axes[(0, 0)][0].get_position()
    fig.text(0.018, first_top.y1 + 0.040, "b", fontsize=8, fontweight="bold", va="bottom")
    for row_i, info in enumerate(selected):
        pbox = pair_axes[(row_i, 0)][0].get_position(); sbox = pair_axes[(row_i, 0)][1].get_position()
        fig.text(0.018, (pbox.y1 + sbox.y0) / 2, f"{info['selection']}\nrank {info['rank_ascending_eta_plus1_mae']}/22\nMAE {info['error_value']:.3f}", ha="left", va="center", fontsize=5.15, color="#333333")
    y0 = pair_axes[(2, 0)][1].get_position().y0; y1 = pair_axes[(0, 0)][0].get_position().y1
    fig.text(0.090, (y0 + y1) / 2, "Diffraction order m", rotation=90, rotation_mode="anchor", ha="center", va="center", fontsize=5.6)
    fig.text(0.93, 0.022, "Screening/ranking only; final quantitative verification uses FDTD.", ha="right", va="bottom", fontsize=5.2, color="#444444")

    base = FIG / "np_k6_frozen_forward_surrogate_order_heatmap_nature_figure_v1"
    fig.savefig(base.with_suffix(".png"), dpi=600, facecolor="white")
    fig.savefig(base.with_suffix(".tiff"), dpi=600, facecolor="white", pil_kwargs={"compression": "tiff_lzw"})
    fig.savefig(base.with_suffix(".pdf"), facecolor="white")
    fig.savefig(base.with_suffix(".svg"), facecolor="white")
    svg = base.with_suffix(".svg")
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8")
    plt.close(fig)

    manifest = {
        "artifact_id": "NP_K6_FROZEN_FORWARD_SURROGATE_ORDER_HEATMAP_NATURE_FIGURE_V1",
        "core_conclusion": "The frozen NP surrogate preserves useful held-out K6 ranking and order-resolved broadband response trends for rapid screening before full-wave FDTD verification.",
        "backend": "python/matplotlib", "archetype": "quantitative grid", "final_size_mm": {"width": 183.0, "height": 163.8},
        "scope": {"u_x": 0.0, "k_y": 0.0, "polarizations": ["P_XLIKE", "S_YLIKE"], "wavelengths_nm": WAVELENGTHS, "heldout_geometries": 22, "hf_rows": 484},
        "providers": {"ranking": {"model": RANKING_MODEL, "variant": VARIANT}, "spectral": {"model": SPECTRAL_MODEL, "variant": VARIANT}, "components_are_distinct": True},
        "tracked_order_vector": ORDERS,
        "selection_metric": "mean absolute eta(+1) OOF error over explicit P/S and all 11 wavelengths; lower central rank for even n",
        "selected_cases": selected,
        "metrics": {"geometry_ranking_spearman": rho, "efficiency_common_scale": [eff_min, eff_max], "absolute_error_scale": [0.0, max(errors)], "negative_raw_spectral_predictions_preserved": sum(v < 0 for v in values)},
        "source_artifacts": {"hf_truth": {"path": str(HF.relative_to(ROOT)).replace("/", "\\"), "sha256": sha(HF)}, "oof_predictions": {"path": str(OOF.relative_to(ROOT)).replace("/", "\\"), "sha256": sha(OOF)}, "normal_incidence_freeze": {"path": str(M9A.relative_to(ROOT)).replace("/", "\\"), "sha256": sha(M9A)}},
        "script_sha256": sha(SCRIPT),
        "data_integrity": {"interpolation": False, "smoothing": False, "clipping": False, "renormalization": False, "P_S_averaging": False, "wavelength_rows_as_independent_geometries": False},
        "zero_compute_audit": {"new_fdtd": 0, "new_rcwa": 0, "new_training": 0, "external_hf": 0, "inverse": 0, "data_regeneration": 0},
        "generation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json(OUT / "figure_manifest.json", manifest)
    write_json(OUT / "visual_qa.json", {"source_preflight": "PENDING", "pdf_glyph_audit": "PENDING", "panel_a_annotation_overlap": "PENDING", "panel_b_facet_overlap": "PENDING", "clipping": "PENDING", "color_scale_contract": "PENDING", "typography": "PENDING", "raster_600dpi": "PENDING"})
    DOC.write_text(f"""# NP K6 frozen forward-surrogate order heatmap Nature figure v1\n\n## Caption\n\n**Order-resolved held-out evidence for rapid K6 screening.** **a,** Geometry-level held-out ranking for 22 K6 geometries. Each marker is one held-out geometry and uses the frozen broadband η(+1) score across explicit P/S and 445–455 nm; the ranking component is `LF_only / ensemble_raw` (Spearman ρ = {rho:.3f}). **b,** Programmatically selected Best, Median and Worst geometries ranked by mean absolute η(+1) OOF error across both polarizations and 11 wavelengths. Each cell shows the authority-derived transmitted-order vector `m = −3,…,+3` for P_XLIKE and S_YLIKE without interpolation, smoothing, clipping or renormalization. FDTD and `LF_ridge_residual / ensemble_raw` prediction use one common linear efficiency scale; absolute error uses a separate linear scale. Raw negative model predictions remain visible.\n\n## Frozen data and selection\n\n- HF authority: `outputs/np_k6_m8a_primary2_closeout_v1/hf22_formal_development_484rows.csv` (484 rows; 22 geometries × 2 polarizations × 11 wavelengths).\n- OOF authority: `outputs/np_k6_m9_22g_forward_retraining_v1/oof_predictions_22g.csv`.\n- Best: `{selected[0]['geometry_id']}`, rank 1/22, mean η(+1) error {selected[0]['error_value']:.6f}.\n- Median: `{selected[1]['geometry_id']}`, rank 11/22, mean η(+1) error {selected[1]['error_value']:.6f}.\n- Worst: `{selected[2]['geometry_id']}`, rank 22/22, mean η(+1) error {selected[2]['error_value']:.6f}.\n\n## Interpretation boundary\n\nThe ranking and spectral panels use distinct frozen provider components, not one universal surrogate. Scope is normal incidence (`u_x = 0`, `k_y = 0`) only. The figure supports screening/ranking before full-wave FDTD verification; it does not support FDTD replacement, angular generalization, Jones-matrix prediction or integrated MDC–NP truth.\n\n## Compute and export audit\n\nNew FDTD, RCWA, training, external-HF access, inverse design and data regeneration are all zero. Final exports are 183 × 163.8 mm in PNG/TIFF (600 dpi) and editable PDF/SVG.\n""", encoding="utf-8")
    print(json.dumps({"status": "GENERATED", "tracked_orders": ORDERS, "rho": rho, "selected": selected, "heatmap_rows": len(heat_rows), "efficiency_scale": [eff_min, eff_max], "error_scale": [0, max(errors)], "zero_compute": manifest["zero_compute_audit"]}, indent=2))

if __name__ == "__main__": main()
