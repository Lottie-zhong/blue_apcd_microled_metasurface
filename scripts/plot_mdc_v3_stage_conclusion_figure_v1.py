"""Nature-style stage-conclusion figure for frozen MDC HF surrogate V3-C.

Read-only figure generation from frozen Test40 external artifacts.  The plot
uses the inherited profile display normalization and introduces no metric,
selection rule, model fit, PCA/scaler fit, or solver call.
"""
from __future__ import annotations

import hashlib
import json
import copy
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm


ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2")
EXT = ROOT / "outputs" / "mdc_hf_surrogate_v3_test40_external_2d_fdtd_v1" / "20260813T_test40_external_hf_acquisition_v2"
PKG = ROOT / "outputs" / "mdc_hf_surrogate_v3_test40_external_evaluation_package_v1" / "20260813T_external_package_audit_d016284"
SCOPE = ROOT / "outputs" / "mdc_hf_surrogate_v3_test40_latent_scope_reconciliation_v1" / "20260813T_scope_reconciliation_c7bbbba"
OUT = ROOT / "outputs" / "mdc_hf_surrogate_v3_stage_conclusion_figure_v1" / "20260813T_stage_conclusion_figure_58fc73f"


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha_array(value: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(value).tobytes()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def normalize_display(profile: np.ndarray) -> np.ndarray:
    x = np.maximum(np.asarray(profile, dtype=np.float64), 0.0)
    return x / max(float(x.sum()), 1e-12)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": 7,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.65,
        "xtick.major.width": 0.55,
        "ytick.major.width": 0.55,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "savefig.facecolor": "white",
    })

    pred = np.load(EXT / "test40_external_ensemble_prediction_profiles.npy", mmap_mode="r")
    pred_sha_file = sha_file(EXT / "test40_external_ensemble_prediction_profiles.npy")
    pred_sha_array = sha_array(pred)
    truth_freeze = read_json(EXT / "test40_truth_freeze_manifest.json")
    if truth_freeze.get("case_count") != 240 or truth_freeze.get("geometry_count") != 40 or truth_freeze.get("cases_per_geometry") != 6:
        raise RuntimeError("HARD_GATE_TEST40_MEMBERSHIP_DRIFT")
    if read_json(EXT / "test40_truth_aggregation_audit.json").get("all_integrals_close_to_one") is not True:
        raise RuntimeError("HARD_GATE_TRUTH_AGGREGATION")
    if read_json(EXT / "test40_external_prediction_manifest.json").get("prediction_sha256") != pred_sha_array:
        raise RuntimeError("HARD_GATE_PREDICTION_SHA")
    case_index = read_json(EXT / "test40_truth_case_index.json")
    geometry_index = read_json(EXT / "test40_truth_geometry_index.json")
    geometry_map = {str(r["geometry_hash"]): r for r in geometry_index}
    diagnostics = read_json(PKG / "representative_profile_diagnostics.json")["representatives"]
    selection = {
        "best": diagnostics["best"],
        "median": diagnostics["median_error"],
        "worst": diagnostics["worst"],
    }
    rows = []
    for role, item in selection.items():
        gh = str(item["geometry_hash"])
        indices = [i for i, r in enumerate(case_index) if str(r["geometry_hash"]) == gh]
        if len(indices) != 6:
            raise RuntimeError(f"Expected six source-conditioned cases for {role}, got {len(indices)}")
        truth_raw = np.load(geometry_map[gh]["profile_path"], allow_pickle=False)["normalized_joint"]
        truth = normalize_display(truth_raw)
        prediction = normalize_display(np.asarray(pred[indices], dtype=np.float64).mean(axis=0)).reshape(truth.shape)
        truth = truth.reshape(truth.shape)
        error = np.abs(prediction - truth)
        rows.append({
            "role": role,
            "display_label": {"best": "Best representative", "median": "Median representative", "worst": "Worst representative"}[role],
            "geometry_hash": gh,
            "geometry_id": str(case_index[indices[0]]["geometry_id"]),
            "topology": "ZL2" if role == "worst" else "ZL1",
            "case_count": len(indices),
            "case_uids": [str(case_index[i]["case_uid"]) for i in indices],
            "source_conditions": [{"source_position": str(case_index[i]["source_position"]), "dipole_orientation": str(case_index[i]["dipole_orientation"])} for i in indices],
            "truth": truth,
            "prediction": prediction,
            "error": error,
            "diagnostics": item["diagnostic"],
        })

    source_ref = {
        "external_prediction": {"logical_artifact": "frozen Test40 ensemble prediction profiles", "file_sha256": pred_sha_file, "array_payload_sha256": pred_sha_array},
        "truth_freeze_manifest": {"logical_artifact": "frozen Test40 truth freeze manifest", "sha256": sha_file(EXT / "test40_truth_freeze_manifest.json")},
        "truth_aggregation_audit": {"logical_artifact": "frozen Test40 truth aggregation audit", "sha256": sha_file(EXT / "test40_truth_aggregation_audit.json")},
        "prediction_manifest": {"logical_artifact": "frozen Test40 prediction manifest", "sha256": sha_file(EXT / "test40_external_prediction_manifest.json")},
        "truth_case_index": {"logical_artifact": "frozen Test40 case index", "sha256": sha_file(EXT / "test40_truth_case_index.json")},
        "truth_geometry_index": {"logical_artifact": "frozen Test40 geometry profile index", "sha256": sha_file(EXT / "test40_truth_geometry_index.json")},
        "external_metrics": {"logical_artifact": "frozen Test40 external metrics", "sha256": sha_file(EXT / "test40_external_metrics.json")},
        "representative_diagnostics": {"logical_artifact": "frozen representative profile diagnostics", "sha256": sha_file(PKG / "representative_profile_diagnostics.json")},
        "latent_scope_closure": {"logical_artifact": "frozen V3 latent scope reconciliation", "sha256": sha_file(SCOPE / "artifact_sha256.json")},
    }

    manifest_rows = []
    for r in rows:
        d = r["diagnostics"]
        manifest_rows.append({
            "role": r["role"],
            "selection_rule": {"best": "minimum authoritative geometry-level composite", "median": "geometry-level composite nearest the authoritative Test40 median", "worst": "maximum authoritative geometry-level composite"}[r["role"]],
            "geometry_id": r["geometry_id"],
            "geometry_hash": r["geometry_hash"],
            "topology": r["topology"],
            "display_unit": "geometry-level aggregate over all six frozen source-conditioned cases",
            "case_count": r["case_count"],
            "case_uids": r["case_uids"],
            "source_conditions": r["source_conditions"],
            "authoritative_diagnostics": {k: d["metrics"][k] for k in ("profile", "JS", "spectral_CDF", "angular_CDF", "weighted_L1")},
            "profile_sha256": {"truth": d["truth_profile_sha256"], "prediction": d["pred_profile_sha256"]},
        })
    dump_json(OUT / "sample_selection_manifest.json", {
        "status": "PASS",
        "selection_is_descriptive_only": True,
        "external_scope": {"geometries": 40, "cases": 240, "prospective": True},
        "rows": manifest_rows,
        "difficult_control": {"included": False, "reason": "Three rows preserve heatmap/colorbar readability; the worst representative is ZL2 and serves as the difficult-stratum control."},
        "source_artifacts": source_ref,
        "display_normalization": "nonnegative array-sum normalization for truth and prediction, matching the inherited frozen profile metric display path",
        "no_new_metric": True,
    })

    all_values = np.concatenate([np.concatenate([r["truth"].ravel(), r["prediction"].ravel()]) for r in rows])
    err_values = np.concatenate([r["error"].ravel() for r in rows])
    vmin = max(float(np.quantile(all_values[all_values > 0], 0.01)), 1e-9)
    vmax = float(all_values.max())
    evmin = max(float(np.quantile(err_values[err_values > 0], 0.01)), 1e-10)
    evmax = float(err_values.max())
    norm = LogNorm(vmin=vmin, vmax=vmax)
    en = LogNorm(vmin=evmin, vmax=evmax)
    cmap_profile = copy.copy(plt.get_cmap("magma"))
    cmap_profile.set_bad("#140d21")
    cmap_error = plt.get_cmap("cividis")

    fig = plt.figure(figsize=(7.2, 7.2), constrained_layout=False)
    gs = fig.add_gridspec(3, 6, width_ratios=[1, 1, 1, 0.08, 0.08, 0.02], height_ratios=[1, 1, 1], left=0.105, right=0.965, bottom=0.075, top=0.865, wspace=0.16, hspace=0.28)
    axes = [[fig.add_subplot(gs[i, j]) for j in range(3)] for i in range(3)]
    cax_profile = fig.add_subplot(gs[:, 3]); cax_error = fig.add_subplot(gs[:, 4])
    ims = []
    for i, r in enumerate(rows):
        for j, (data, cmap, nrm) in enumerate(((r["truth"], cmap_profile, norm), (r["prediction"], cmap_profile, norm), (r["error"], cmap_error, en))):
            ax = axes[i][j]
            display_data = np.ma.masked_less_equal(data, 0.0) if j == 1 else data
            im = ax.imshow(display_data, origin="lower", aspect="auto", extent=[420, 480, -90, 90], cmap=cmap, norm=nrm, interpolation="nearest", rasterized=True)
            ims.append(im)
            ax.set_xlim(420, 480); ax.set_ylim(-90, 90)
            ax.set_xticks([420, 450, 480]); ax.set_yticks([-90, 0, 90])
            ax.tick_params(labelsize=6, length=2.5, pad=1.5)
            ax.set_xlabel("Wavelength (nm)", fontsize=6.5, labelpad=2)
            if j == 0:
                ax.set_ylabel("Angle (deg)", fontsize=6.5, labelpad=2)
            if i == 0:
                ax.set_title(["Truth", "V3-C prediction", "Absolute error"][j], fontsize=8, fontweight="bold", pad=5)
            if j == 0:
                row_y = {"best": 0.755, "median": 0.495, "worst": 0.235}[r["role"]]
                short_id = r["geometry_id"].replace("MDC_V3_TEST_", "")
                fig.text(0.008, row_y, f"{r['role'].capitalize()}\n{short_id} · {r['topology']}", ha="left", va="center", fontsize=6.8, fontweight="bold", linespacing=1.05)
    cb1 = fig.colorbar(ims[0], cax=cax_profile)
    cb1.set_label("Normalized intensity", fontsize=6.2, labelpad=4)
    cb1.ax.tick_params(labelsize=8.0, length=2)
    cb2 = fig.colorbar(ims[2], cax=cax_error)
    cb2.set_label("Absolute error", fontsize=6.2, labelpad=4)
    cb2.ax.tick_params(labelsize=8.0, length=2)
    fig.text(0.105, 0.945, "Frozen MDC HF surrogate V3-C: profile-shape screening", ha="left", va="bottom", fontsize=11, fontweight="bold")
    fig.text(0.105, 0.918, "Coarse spectral-angular structure is retained, while smoothing, lobe displacement and under-dispersion remain visible", ha="left", va="bottom", fontsize=7.2, color="#444444")
    fig.text(0.105, 0.018, "Prospective Test40 external evidence · scope: RANKING_SCREENING_ONLY · error uses an independent color scale", ha="left", va="bottom", fontsize=6.2, color="#555555")
    for ext, name in (("png", "stage_conclusion_figure.png"), ("tiff", "stage_conclusion_figure.tiff"), ("pdf", "stage_conclusion_figure.pdf"), ("svg", "stage_conclusion_figure.svg")):
        path = OUT / name
        if ext in {"png", "tiff"}: fig.savefig(path, dpi=600, bbox_inches="tight", facecolor="white")
        else: fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    caption = """# Figure caption draft

**Frozen MDC HF surrogate V3-C supports profile-shape screening but remains ranking-only.** Heatmaps show geometry-level six-source-condition aggregates for three representative geometries selected from the prospective Test40 external set: the best, the geometry-level composite nearest the Test40 median, and the worst. Truth and V3-C prediction use the same non-negative array-sum display normalization and share one intensity scale; absolute error is shown with an independent scale. V3-C captures the coarse spectral-angular structure, while the residual maps expose smoothing, lobe displacement and profile under-dispersion. The difficult-stratum control is the worst ZL2 representative. These results support Level-0 profile-shape screening and coarse ranking, but do not establish quantitative FDTD replacement, power, LEE, Level-1 MDC-NP truth or integrated device coupling. The formal scope therefore remains **RANKING_SCREENING_ONLY**. Sample selection and source artifact hashes are recorded in the accompanying manifest; no new metric or model selection was introduced for this figure.
"""
    (OUT / "caption_draft.md").write_text(caption, encoding="utf-8")
    readme = """# MDC V3 stage-conclusion figure package

Archetype: quantitative heatmap grid. Backend: Python/matplotlib only. The figure uses three rows because the worst representative is ZL2 and provides the difficult-stratum control; adding a fourth row would reduce final-size heatmap and colorbar readability.

The data are read-only views of frozen Test40 external prediction, truth geometry profiles, authoritative representative diagnostics and the latent-scope closure package. Truth and prediction are normalized with the inherited non-negative array-sum profile display path. No PCA/scaler fit, solver call, training, model modification or new metric inference is performed.

Panel audit:

- Each row answers one question: how does the frozen V3-C profile compare with truth for a best, median, or worst authoritative geometry?
- Truth and prediction share one logarithmic intensity color scale.
- Absolute error has a separate logarithmic color scale.
- Row metadata and all six source-conditioned case identifiers are in `sample_selection_manifest.json`.
- The output is a stage-conclusion figure, not a quantitative power/coupling validation figure.

Exports: 600-dpi PNG, editable-text PDF, and editable-text SVG.
"""
    (OUT / "figure_readme.md").write_text(readme, encoding="utf-8")
    manifest = {
        "status": "PASS",
        "figure_id": "MDC_HF_SURROGATE_V3_STAGE_CONCLUSION_FIGURE_NATURESTYLE_V1",
        "model_id": "MDC_HF_SURROGATE_V3_C_FINAL_5SEED_PROFILE_ONLY_V1",
        "backend": "python_matplotlib",
        "rows": 3,
        "columns": ["Truth", "V3-C prediction", "Absolute error"],
        "png_dpi": 600,
        "solver_calls": 0,
        "training_fits": 0,
        "pca_fit_calls": 0,
        "scaler_fit_calls": 0,
        "new_evaluation_metric": False,
        "source_artifact_registry": "sample_selection_manifest.json",
        "caption": "caption_draft.md",
    }
    dump_json(OUT / "completion_manifest.json", manifest)
    files = {str(p.relative_to(OUT)): sha_file(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name != "artifact_sha256.json"}
    dump_json(OUT / "artifact_sha256.json", {"status": "PASS", "file_count": len(files), "files": files})
    print(json.dumps({"status": "PASS", "package": str(OUT), "files": len(files), "png_dpi": 600, "rows": 3}, sort_keys=True))


if __name__ == "__main__":
    main()
