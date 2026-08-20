from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
M9 = ROOT / "outputs/np_k6_m9_22g_forward_retraining_v1"
M9A = ROOT / "outputs/np_k6_m9a_normal_incidence_plateau_reassessment_v1"
HF = ROOT / "outputs/np_k6_m8a_primary2_closeout_v1/hf22_formal_development_484rows.csv"
OUT = ROOT / "outputs/np_k6_frozen_forward_surrogate_nature_figure_v1"
FIG = ROOT / "figures/np_k6_frozen_forward_surrogate_nature_figure_v1"
DOC = ROOT / "docs/np_k6_frozen_forward_surrogate_nature_figure_v1.md"
SCRIPT = ROOT / "scripts/np_k6_frozen_forward_surrogate_nature_figure_v1.py"
RANKING_MODEL = "LF_only"
SPECTRAL_MODEL = "LF_ridge_residual"
VARIANT = "ensemble_raw"
WAVELENGTHS = list(range(445, 456))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rankdata(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    ranks[order] = np.arange(1, len(values) + 1, dtype=float)
    return ranks


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    return float(np.corrcoef(rankdata(x), rankdata(y))[0, 1])


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def add_panel_label(ax, label: str) -> None:
    ax.text(-0.14, 1.09, label, transform=ax.transAxes, fontsize=8,
            fontweight="bold", va="top", ha="left", clip_on=False)


def style_axes(ax, *, show_left: bool, show_bottom: bool) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(direction="out", length=2.5, width=0.65, pad=2)
    ax.grid(False)
    if not show_left:
        ax.set_yticklabels([])
        ax.tick_params(left=False)
        ax.spines["left"].set_visible(False)
    if not show_bottom:
        ax.set_xticklabels([])
        ax.tick_params(bottom=False)
        ax.spines["bottom"].set_visible(False)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    hf = read_csv(HF)
    oof_path = M9 / "oof_predictions_22g.csv"
    oof = read_csv(oof_path)
    ranking_metrics = read_csv(M9 / "ranking_metrics.csv")
    constrained = read_csv(M9 / "model_metrics_constrained.csv")
    m9_validator = json.loads((M9 / "m9_final_validator_report.json").read_text(encoding="utf-8"))
    freeze = json.loads((M9A / "normal_incidence_freeze_decision.json").read_text(encoding="utf-8"))
    snapshot = json.loads((M9A / "authority_snapshot.json").read_text(encoding="utf-8"))

    ensure(m9_validator["status"] == "PASS", "M9 validator")
    ensure(snapshot["hf22_rows"] == 484 and snapshot["hf22_geometry_count"] == 22, "HF22 authority")
    ensure(freeze["provider"]["ranking_component"] == RANKING_MODEL, "ranking provider mismatch")
    ensure(freeze["provider"]["order_profile_component"] == SPECTRAL_MODEL, "spectral provider mismatch")
    ensure(freeze["provider"]["role"] == "RANKING_SCREENING_ONLY", "provider role")
    ensure(freeze["u_x_scope"] == [0.0], "normal-incidence scope")

    hf_map = {}
    for r in hf:
        key = (r["geometry_id"], r["polarization"].lower(), int(float(r["wavelength_nm"])))
        ensure(key not in hf_map, "duplicate HF key")
        ensure(r["quality_gate_pass"] == "true" and r["diagnostic_only"] == "false", "HF quality flag")
        ensure(r["training_label"] == "true" or r["m5_training_label"] == "true", "HF training flag")
        hf_map[key] = r
    ensure(len(hf_map) == 484, "HF row count")

    def prediction_map(model: str) -> dict[tuple[str, str, int], dict[str, str]]:
        out = {}
        for r in oof:
            if r["model"] != model or r["variant"] != VARIANT:
                continue
            key = (r["geometry_id"], r["polarization"].lower(), int(float(r["wavelength_nm"])))
            ensure(key not in out, f"duplicate OOF key {model}")
            out[key] = r
        ensure(set(out) == set(hf_map), f"OOF authority mismatch {model}")
        return out

    ranking_pred = prediction_map(RANKING_MODEL)
    spectral_pred = prediction_map(SPECTRAL_MODEL)
    geometries = sorted({k[0] for k in hf_map})
    ensure(len(geometries) == 22, "geometry count")
    for g in geometries:
        expected = {(g, p, w) for p in ("p", "s") for w in WAVELENGTHS}
        ensure(expected <= set(hf_map), f"coverage {g}")

    rank_rows = []
    for g in geometries:
        keys = [(g, p, w) for p in ("p", "s") for w in WAVELENGTHS]
        truth = float(np.mean([float(hf_map[k]["eta_m+1"]) for k in keys]))
        predicted = float(np.mean([float(ranking_pred[k]["pred_eta_m+1"]) for k in keys]))
        rank_rows.append({"geometry_id": g, "fdtd_score_mean_eta_plus1_over_P_S_wavelength": truth,
                          "surrogate_score_mean_eta_plus1_over_P_S_wavelength": predicted,
                          "sample_unit": "one held-out K6 geometry (P/S paired, 11 wavelengths each)",
                          "ranking_provider": f"{RANKING_MODEL}/{VARIANT}"})
    rank_rows.sort(key=lambda r: r["geometry_id"])
    truth_scores = np.asarray([r["fdtd_score_mean_eta_plus1_over_P_S_wavelength"] for r in rank_rows])
    pred_scores = np.asarray([r["surrogate_score_mean_eta_plus1_over_P_S_wavelength"] for r in rank_rows])
    rho_recomputed = spearman(truth_scores, pred_scores)
    rank_metric = next(r for r in ranking_metrics if r["model"] == RANKING_MODEL and r["variant"] == "raw")
    rho_frozen = float(rank_metric["ranking_spearman"])
    ensure(abs(rho_recomputed - rho_frozen) < 1e-12, "ranking Spearman mismatch")
    write_csv(OUT / "heldout_geometry_ranking_data.csv", rank_rows)

    spectral_geometry = []
    selected_all = []
    for g in geometries:
        records = []
        for p in ("p", "s"):
            for w in WAVELENGTHS:
                k = (g, p, w)
                truth = float(hf_map[k]["eta_m+1"])
                pred = float(spectral_pred[k]["pred_eta_m+1"])
                ensure(math.isfinite(truth) and math.isfinite(pred), "finite spectral values")
                records.append({"geometry_id": g, "polarization": p, "wavelength_nm": w,
                                "eta_plus1_truth": truth, "eta_plus1_prediction": pred,
                                "absolute_error": abs(pred - truth),
                                "spectral_provider": f"{SPECTRAL_MODEL}/{VARIANT}"})
        mae = float(np.mean([r["absolute_error"] for r in records]))
        spectral_geometry.append({"geometry_id": g, "spectral_eta_plus1_mae_over_P_S_11wavelengths": mae,
                                  "records": records})
    spectral_geometry.sort(key=lambda r: (r["spectral_eta_plus1_mae_over_P_S_11wavelengths"], r["geometry_id"]))
    ranks = {"Best": 1, "Median": (len(spectral_geometry) // 2), "Worst": len(spectral_geometry)}
    selected = []
    for label, rank in ranks.items():
        item = spectral_geometry[rank - 1]
        selected.append({"selection": label, "rank_ascending_eta_plus1_mae": rank,
                         "geometry_count": len(spectral_geometry), "geometry_id": item["geometry_id"],
                         "error_metric": "mean absolute eta(+1) OOF error over explicit P/S and 445-455 nm",
                         "error_value": item["spectral_eta_plus1_mae_over_P_S_11wavelengths"],
                         "prediction_source": f"M9 {SPECTRAL_MODEL}/{VARIANT}",
                         "truth_source": "HF22 formal held-out authority"})
        for rec in item["records"]:
            selected_all.append({"selection": label, "rank_ascending_eta_plus1_mae": rank,
                                 **rec})
    write_json(OUT / "representative_cases.json", {"selection_rule": "programmatic ascending geometry-level η(+1) MAE; for 22 geometries median is lower central rank 11",
                                                     "selected_cases": selected})
    write_csv(OUT / "representative_spectral_data.csv", selected_all)

    spectral_metric = next(r for r in constrained if r["model"] == SPECTRAL_MODEL and r["variant"] == "constrained")

    mpl.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": 6.2, "axes.labelsize": 6.4, "axes.titlesize": 6.5, "xtick.labelsize": 5.6,
        "ytick.labelsize": 5.6, "legend.fontsize": 5.5, "axes.linewidth": 0.75,
        "svg.fonttype": "none", "pdf.fonttype": 42, "legend.frameon": False,
    })
    fig = plt.figure(figsize=(7.205, 6.48), facecolor="white")
    outer = fig.add_gridspec(2, 1, height_ratios=[1.06, 3.94], left=0.105, right=0.985, top=0.935, bottom=0.095, hspace=0.28)
    top = outer[0].subgridspec(1, 2, width_ratios=[1.30, 1.70], wspace=0.42)
    ax_a = fig.add_subplot(top[0, 0])
    ax_b = fig.add_subplot(top[0, 1])
    bottom = outer[1].subgridspec(3, 3, hspace=0.34, wspace=0.25)
    fig.text(0.105, 0.983, "Forward surrogate for rapid K6 metagrating screening", fontsize=9, fontweight="bold", va="top")

    # Panel a: compact schematic.
    ax_a.set_axis_off(); add_panel_label(ax_a, "a")
    ax_a.set_xlim(0, 1); ax_a.set_ylim(0, 1)
    for i, height in enumerate([0.28, 0.43, 0.58, 0.49, 0.67, 0.37]):
        x = 0.04 + i * 0.047
        ax_a.add_patch(plt.Rectangle((x, 0.63 - height / 2), 0.028, height,
                                     facecolor="#B9C7D5", edgecolor="#5B7187", linewidth=0.55))
    ax_a.text(0.17, 0.16, "Ordered K6\n[D1…D6]", ha="center", va="center", fontsize=5.35)
    ax_a.text(0.39, 0.61, "+", ha="center", va="center", fontsize=9, color="#6A6A6A")
    ax_a.text(0.49, 0.61, "λ\nP/S", ha="center", va="center", fontsize=5.5)
    ax_a.annotate("", xy=(0.62, 0.61), xytext=(0.55, 0.61), arrowprops=dict(arrowstyle="->", color="#555555", lw=0.75))
    ax_a.text(0.72, 0.61, "Frozen\nforward\nsurrogate", ha="center", va="center", fontsize=5.2, fontweight="bold", color="#1F4E79")
    ax_a.annotate("", xy=(0.86, 0.61), xytext=(0.80, 0.61), arrowprops=dict(arrowstyle="->", color="#555555", lw=0.75))
    ax_a.text(0.94, 0.73, "Broadband\nresponse", ha="center", va="center", fontsize=5.1)
    ax_a.text(0.94, 0.43, "Candidate\nranking", ha="center", va="center", fontsize=5.1)

    # Panel b: ranking scatter.
    add_panel_label(ax_b, "b")
    ax_b.scatter(truth_scores, pred_scores, s=20, color="#3F6D8E", alpha=0.88, edgecolor="white", linewidth=0.35, zorder=3)
    lo = min(float(truth_scores.min()), float(pred_scores.min())); hi = max(float(truth_scores.max()), float(pred_scores.max()))
    pad = max((hi - lo) * 0.10, 0.008); lo -= pad; hi += pad
    ax_b.plot([lo, hi], [lo, hi], color="#777777", linewidth=0.75, zorder=1)
    ax_b.set_xlim(lo, hi); ax_b.set_ylim(lo, hi)
    ax_b.set_aspect("equal", adjustable="box")
    ax_b.set_xlabel("FDTD score")
    ax_b.set_ylabel("Predicted score")
    ax_b.set_title("Held-out geometry ranking", loc="left", pad=2.5, fontweight="bold")
    ax_b.text(0.04, 0.93, f"22 geometries\nSpearman ρ = {rho_frozen:.3f}", transform=ax_b.transAxes,
              ha="left", va="top", fontsize=5.7, color="#303030")
    style_axes(ax_b, show_left=True, show_bottom=True)

    # Panel c: three programmatically selected geometry rows and three evidence columns.
    colors = {"truth": "#1F4E79", "prediction": "#D97757", "error": "#555555"}
    style = {"p": ("-", "o"), "s": ("--", "s")}
    all_truth = [r["eta_plus1_truth"] for r in selected_all]; all_pred = [r["eta_plus1_prediction"] for r in selected_all]
    response_lo = min(min(all_truth), min(all_pred)); response_hi = max(max(all_truth), max(all_pred))
    response_pad = max((response_hi - response_lo) * 0.12, 0.03)
    response_lo = max(-0.05, response_lo - response_pad); response_hi = min(1.05, response_hi + response_pad)
    by_selection = defaultdict(list)
    for r in selected_all: by_selection[r["selection"]].append(r)
    selections = ["Best", "Median", "Worst"]
    qa_axes = []
    for row, label in enumerate(selections):
        records = by_selection[label]
        info = next(x for x in selected if x["selection"] == label)
        err_max = max(r["absolute_error"] for r in records)
        err_hi = max(0.03, math.ceil(err_max * 25) / 25 * 1.15)
        for col, kind in enumerate(("truth", "prediction", "error")):
            ax = fig.add_subplot(bottom[row, col]); qa_axes.append(ax)
            if row == 0:
                add_panel_label(ax, "c" if col == 0 else "")
                ax.set_title({"truth": "FDTD", "prediction": "Prediction", "error": "Absolute error"}[kind], pad=3.5, fontweight="bold")
            for pol in ("p", "s"):
                z = sorted((r for r in records if r["polarization"] == pol), key=lambda r: r["wavelength_nm"])
                x = [r["wavelength_nm"] for r in z]
                if kind == "truth": y = [r["eta_plus1_truth"] for r in z]; color = colors["truth"]
                elif kind == "prediction": y = [r["eta_plus1_prediction"] for r in z]; color = colors["prediction"]
                else: y = [r["absolute_error"] for r in z]; color = colors["error"]
                ls, marker = style[pol]
                ax.plot(x, y, linestyle=ls, marker=marker, markersize=2.1, color=color, linewidth=1.05,
                        markerfacecolor="white" if kind != "truth" else color, markeredgewidth=0.65)
            ax.set_xlim(444.7, 455.3)
            ax.set_xticks([445, 450, 455])
            if kind == "error": ax.set_ylim(0, err_hi)
            else: ax.set_ylim(response_lo, response_hi)
            if col == 0:
                ax.set_ylabel("η(+1)")
            elif kind == "error":
                ax.set_ylabel("|Δη(+1)|")
            if row == 2:
                ax.set_xlabel("Wavelength (nm)")
            style_axes(ax, show_left=(col in (0, 2)), show_bottom=(row == 2))

    for row, label in enumerate(selections):
        info = next(x for x in selected if x["selection"] == label)
        bounds = qa_axes[row * 3].get_position()
        fig.text(0.012, (bounds.y0 + bounds.y1) / 2,
                 f"{label}\nrank {info['rank_ascending_eta_plus1_mae']}/22\nMAE {info['error_value']:.3f}",
                 ha="left", va="center", fontsize=5.25, color="#333333")

    fig.text(0.985, 0.020, "P: solid circles; S: dashed squares. Screening/ranking only; final quantitative verification uses FDTD.",
             ha="right", va="bottom", fontsize=5.2, color="#444444")
    fig.savefig(FIG / "np_k6_frozen_forward_surrogate_nature_figure_v1.png", dpi=600, facecolor="white")
    fig.savefig(FIG / "np_k6_frozen_forward_surrogate_nature_figure_v1.pdf", facecolor="white")
    svg_path = FIG / "np_k6_frozen_forward_surrogate_nature_figure_v1.svg"
    fig.savefig(svg_path, facecolor="white")
    # Keep the editable SVG semantically unchanged while avoiding diff-check noise
    # from matplotlib's line-ending whitespace serialization.
    svg_path.write_text("\n".join(line.rstrip() for line in svg_path.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8")
    fig.savefig(FIG / "np_k6_frozen_forward_surrogate_nature_figure_v1.tiff", dpi=600, facecolor="white")
    plt.close(fig)

    manifest = {
        "artifact_id": "NP_K6_FROZEN_FORWARD_SURROGATE_NATURE_FIGURE_V1",
        "core_conclusion": "The frozen NP forward surrogate preserves useful performance ranking and broadband response trends for unseen K6 metagratings, enabling rapid screening before full-wave FDTD verification.",
        "archetype": "asymmetric mixed-modality figure",
        "backend": "python/matplotlib",
        "final_size_mm": {"width": 183, "height": 164.6},
        "scope": {"u_x": [0.0], "normal_incidence_only": True, "geometries": 22, "polarizations": ["p", "s"], "wavelengths_nm": WAVELENGTHS, "hf_rows": 484},
        "providers": {
            "ranking": {"provider_id": freeze["provider"]["id"], "model": RANKING_MODEL, "variant": VARIANT,
                        "score_definition": "mean eta(+1) over explicit P/S and 11 wavelengths per held-out geometry", "frozen_spearman": rho_frozen},
            "spectral": {"provider_id": freeze["provider"]["id"], "model": SPECTRAL_MODEL, "variant": VARIANT,
                         "observable": "eta(+1)", "selection_error_metric": "mean absolute eta(+1) OOF error over explicit P/S and 445-455 nm"},
        },
        "source_artifacts": {
            "hf22_authority": {"path": str(HF.relative_to(ROOT)), "sha256": sha256(HF)},
            "m9_oof_predictions": {"path": str(oof_path.relative_to(ROOT)), "sha256": sha256(oof_path)},
            "m9_ranking_metrics": {"path": str((M9 / 'ranking_metrics.csv').relative_to(ROOT)), "sha256": sha256(M9 / 'ranking_metrics.csv')},
            "m9_constrained_metrics": {"path": str((M9 / 'model_metrics_constrained.csv').relative_to(ROOT)), "sha256": sha256(M9 / 'model_metrics_constrained.csv')},
            "m9a_freeze_decision": {"path": str((M9A / 'normal_incidence_freeze_decision.json').relative_to(ROOT)), "sha256": sha256(M9A / 'normal_incidence_freeze_decision.json')},
            "m9_validator": {"path": str((M9 / 'm9_final_validator_report.json').relative_to(ROOT)), "sha256": sha256(M9 / 'm9_final_validator_report.json')},
        },
        "selected_cases": selected,
        "metrics": {"ranking_spearman": rho_frozen, "spectral_provider_constrained_order_profile_mae_reference": float(spectral_metric["order_profile_mae"])},
        "data_governance": {"heldout_oof_only": True, "training_predictions_used": False, "new_solver_calls": 0, "new_rcwa_calls": 0,
                            "new_ml_training": 0, "external_hf": 0, "inverse": 0, "data_regeneration": 0},
        "script_sha256": sha256(SCRIPT),
        "generation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json(OUT / "figure_manifest.json", manifest)
    write_json(OUT / "figure_contract.json", {"core_conclusion": manifest["core_conclusion"], "panel_map": {"a": "ordered-geometry forward-surrogate role", "b": "held-out geometry-level ranking", "c": "programmatic Best/Median/Worst held-out η(+1) spectra"}, "reviewer_risk": "The provider is screening/ranking-only, normal-incidence-only, and uses separate frozen components for ranking and spectra."})
    write_json(OUT / "visual_qa.json", {"source_preflight": "PENDING", "pdf_glyph_audit": "PENDING", "manual_rendered_panel_inspection": "PENDING", "no_overlap": "PENDING", "data_region_text_overlap": "PENDING"})
    DOC.write_text("""# NP K6 frozen forward-surrogate Nature figure v1

## Caption

**Forward surrogate for rapid K6 metagrating screening.** **a,** Ordered six-pillar K6 geometry, wavelength and explicit polarization are supplied to the frozen forward-surrogate workflow, which supports broadband-response estimation and candidate ranking before final FDTD verification. **b,** Held-out geometry-level ranking: each marker is one of 22 K6 geometries, using the frozen mean η(+1) score across paired P/S cases and 445–455 nm. This panel uses the frozen `LF_only` ranking component (Spearman ρ = 0.962). **c,** Held-out broadband η(+1) spectra from the frozen `LF_ridge_residual` spectral component. Best, Median and Worst are selected programmatically by geometry-level mean absolute η(+1) OOF error over explicit P/S and all 11 wavelengths; P is solid with circles and S is dashed with squares. Absolute-error panels have their own y scales.

The figure presents normal-incidence held-out/OOF evidence only: 22 geometries, paired P/S conditions, 445–455 nm, and 484 HF rows. The ranking and spectral panels deliberately use different frozen provider components; the figure does not claim that one universal model achieved both results. It supports screening/ranking only, not angular generalization, full FDTD replacement, integrated MDC–NP truth, or a universal quantitative predictor. Final quantitative verification remains full-wave FDTD.
""", encoding="utf-8")
    print(json.dumps({"status": "GENERATED", "geometries": len(geometries), "hf_rows": len(hf_map), "ranking_provider": RANKING_MODEL, "spectral_provider": SPECTRAL_MODEL, "rho": rho_frozen, "selected": selected, "solver_calls": 0}, indent=2))


if __name__ == "__main__":
    main()
