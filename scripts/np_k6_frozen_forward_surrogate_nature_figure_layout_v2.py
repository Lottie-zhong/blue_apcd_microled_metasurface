from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize, TwoSlopeNorm
import numpy as np


ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
HF = ROOT / "outputs/np_k6_m8a_primary2_closeout_v1/hf22_formal_development_484rows.csv"
OOF = ROOT / "outputs/np_k6_m9_22g_forward_retraining_v1/oof_predictions_22g.csv"
PREVIOUS = ROOT / "outputs/np_k6_frozen_forward_surrogate_order_heatmap_nature_figure_v1"
SCRIPT = ROOT / "scripts/np_k6_frozen_forward_surrogate_nature_figure_layout_v2.py"
FIG = ROOT / "figures/np_k6_frozen_forward_surrogate_nature_figure_layout_v2"
OUT = ROOT / "outputs/np_k6_frozen_forward_surrogate_nature_figure_layout_v2"
DOC = ROOT / "docs/np_k6_frozen_forward_surrogate_nature_figure_layout_v2.md"
RANKING_MODEL = "LF_only"
SPECTRAL_MODEL = "LF_ridge_residual"
VARIANT = "ensemble_raw"
WAVELENGTHS = list(range(445, 456))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def average_ranks(values: list[float]) -> np.ndarray:
    vector = np.asarray(values, dtype=float)
    order = np.argsort(vector, kind="mergesort")
    ranks = np.empty(len(vector), dtype=float)
    start = 0
    while start < len(vector):
        end = start + 1
        while end < len(vector) and vector[order[end]] == vector[order[start]]:
            end += 1
        ranks[order[start:end]] = (start + 1 + end) / 2.0
        start = end
    return ranks


def spearman(x: list[float], y: list[float]) -> float:
    return float(np.corrcoef(average_ranks(x), average_ranks(y))[0, 1])


def row_key(row: dict[str, str]) -> tuple[str, str, int]:
    return row["geometry_id"], row["polarization"], int(float(row["wavelength_nm"]))


def derive_orders(hf_row: dict[str, str], oof_row: dict[str, str]) -> list[int]:
    truth = sorted(int(name.removeprefix("eta_m")) for name in hf_row if name.startswith("eta_m") and name != "eta_minus1")
    predicted = sorted(int(name.removeprefix("pred_eta_m")) for name in oof_row if name.startswith("pred_eta_m"))
    if truth != predicted:
        raise ValueError(f"tracked-order authority mismatch: truth={truth}; prediction={predicted}")
    return truth


def format_order(order: int) -> str:
    return f"+{order}" if order > 0 else str(order)


def colorbar_ticks(minimum: float, maximum: float, tick_candidates: list[float]) -> list[float]:
    return sorted({round(value, 2) for value in tick_candidates if minimum <= value <= maximum} | {round(minimum, 2), round(maximum, 2)})


def save_vector_and_raster(fig: plt.Figure, base: Path) -> dict[str, str]:
    fig.savefig(base.with_suffix(".png"), dpi=600, facecolor="white")
    fig.savefig(base.with_suffix(".tiff"), dpi=600, facecolor="white", pil_kwargs={"compression": "tiff_lzw"})
    fig.savefig(base.with_suffix(".pdf"), facecolor="white")
    fig.savefig(base.with_suffix(".svg"), facecolor="white")
    svg = base.with_suffix(".svg")
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8")
    return {suffix: str(base.with_suffix(f".{suffix}").relative_to(ROOT)).replace("/", "\\") for suffix in ("png", "tiff", "pdf", "svg")}


def plot_figure1(ranking: list[dict], rho: float, output: Path) -> dict:
    fig = plt.figure(figsize=(7.205, 2.953), facecolor="white")
    layout = fig.add_gridspec(1, 2, width_ratios=[1.25, 0.88], left=0.10, right=0.955, top=0.88, bottom=0.22, wspace=0.30)
    scatter = fig.add_subplot(layout[0, 0])
    providers = fig.add_subplot(layout[0, 1])
    providers.set_axis_off()

    x = np.asarray([float(row["fdt_broadband_eta_plus1_score"]) for row in ranking])
    y = np.asarray([float(row["predicted_broadband_eta_plus1_score"]) for row in ranking])
    low = min(float(x.min()), float(y.min())) - 0.035
    high = max(float(x.max()), float(y.max())) + 0.055
    scatter.plot([low, high], [low, high], color="#777777", linewidth=0.75, zorder=1)
    scatter.scatter(x, y, s=17, color="#3B708F", edgecolor="white", linewidth=0.35, zorder=2)
    scatter.set(xlim=(low, high), ylim=(low, high), xlabel="FDTD broadband score", ylabel="Predicted broadband score")
    scatter.set_aspect("equal", adjustable="box")
    scatter.set_title("Held-out K6 geometry ranking", loc="left", pad=5, fontsize=6.7, fontweight="bold")
    scatter.text(-0.15, 1.10, "a", transform=scatter.transAxes, fontsize=8, fontweight="bold", va="top")

    placements = [(0.045, 0.93), (0.045, 0.24), (0.61, 0.93), (0.61, 0.24)]
    scores = []
    for px, py in placements:
        center = np.array([low + px * (high - low), low + py * (high - low)])
        point_distance = float(np.min(np.hypot(x - center[0], y - center[1])))
        line_distance = abs(center[1] - center[0]) / math.sqrt(2)
        scores.append((min(point_distance, line_distance), px, py))
    _, annotation_x, annotation_y = max(scores)
    scatter.text(annotation_x, annotation_y, f"22 geometries\nSpearman rho = {rho:.4f}", transform=scatter.transAxes, ha="left", va="top", fontsize=5.7, color="#333333")
    scatter.tick_params(length=2.3, pad=2.0)

    providers.text(0.00, 0.98, "Frozen provider components", ha="left", va="top", fontsize=6.7, fontweight="bold")
    providers.text(0.00, 0.73, "Ranking\nLF_only / ensemble_raw", ha="left", va="top", fontsize=5.8, linespacing=1.40)
    providers.text(0.00, 0.46, "Order-resolved spectra\nLF_ridge_residual / ensemble_raw", ha="left", va="top", fontsize=5.8, linespacing=1.40)
    providers.text(0.00, 0.20, "Scope\nu_x = 0; k_y = 0; explicit P/S; 445-455 nm", ha="left", va="top", fontsize=5.35, linespacing=1.35, color="#333333")
    providers.text(0.00, 0.00, "Distinct components; not a universal surrogate", ha="left", va="bottom", fontsize=5.35, color="#444444")

    paths = save_vector_and_raster(fig, output)
    plt.close(fig)
    return {"paths": paths, "annotation_placement_axes_fraction": [annotation_x, annotation_y]}


def plot_figure2(selected: list[dict], rows: list[dict], orders: list[int], eff_norm, err_norm, output: Path) -> dict:
    fig = plt.figure(figsize=(7.205, 6.50), facecolor="white")
    outer = fig.add_gridspec(3, 7, width_ratios=[0.62, 1.0, 1.0, 1.0, 0.10, 0.16, 0.16], left=0.045, right=0.940, top=0.840, bottom=0.105, hspace=0.38, wspace=0.10)
    labels = [fig.add_subplot(outer[row, 0]) for row in range(3)]
    heat_axes: dict[tuple[int, int], tuple[plt.Axes, plt.Axes]] = {}
    x_edges = np.arange(444.5, 456.0, 1.0)
    y_edges = np.arange(orders[0] - 0.5, orders[-1] + 1.0, 1.0)
    all_y_ticks = orders
    for row_index, info in enumerate(selected):
        label_ax = labels[row_index]
        label_ax.set_axis_off()
        label_ax.text(0.02, 0.50, f"{info['selection']}\nrank {info['rank_ascending_eta_plus1_mae']}/22\neta(+1) MAE {info['error_value']:.3f}", ha="left", va="center", fontsize=5.35, color="#333333", linespacing=1.25)
        for col_index, key in enumerate(("truth", "prediction", "error"), start=1):
            facets = outer[row_index, col_index].subgridspec(2, 1, hspace=0.22)
            pair: list[plt.Axes] = []
            for facet_index, polarization in enumerate(("P_XLIKE", "S_YLIKE")):
                axis = fig.add_subplot(facets[facet_index, 0])
                data = np.empty((len(orders), len(WAVELENGTHS)), dtype=float)
                subset = [record for record in rows if record["selection"] == info["selection"] and record["polarization"] == polarization]
                lookup = {(int(record["diffraction_order_m"]), int(record["wavelength_nm"])): record for record in subset}
                for order_index, order in enumerate(orders):
                    for wavelength_index, wavelength in enumerate(WAVELENGTHS):
                        record = lookup[(order, wavelength)]
                        field = {"truth": "fdt_absolute_order_efficiency", "prediction": "predicted_raw_order_efficiency", "error": "absolute_prediction_error"}[key]
                        data[order_index, wavelength_index] = float(record[field])
                axis.pcolormesh(x_edges, y_edges, data, cmap=plt.get_cmap("magma") if key == "error" else plt.get_cmap("coolwarm"), norm=err_norm if key == "error" else eff_norm, shading="flat", rasterized=False)
                axis.set_xlim(444.5, 455.5)
                axis.set_ylim(orders[0] - 0.5, orders[-1] + 0.5)
                axis.set_yticks(all_y_ticks)
                axis.set_yticklabels([format_order(order) for order in all_y_ticks] if col_index == 1 else [])
                axis.set_xticks([445, 450, 455])
                if row_index != 2 or facet_index != 1:
                    axis.set_xticklabels([])
                axis.set_title(polarization, loc="left", pad=2.2, fontsize=5.15, fontweight="normal")
                axis.tick_params(length=2.0, pad=1.4)
                pair.append(axis)
            heat_axes[(row_index, col_index)] = (pair[0], pair[1])

    fig.canvas.draw()
    for col_index, title in enumerate(("FDTD truth", "Prediction", "Absolute error"), start=1):
        top_axis = heat_axes[(0, col_index)][0]
        box = top_axis.get_position()
        fig.text((box.x0 + box.x1) / 2, box.y1 + 0.015, title, ha="center", va="bottom", fontsize=6.5, fontweight="bold")
    top_left = heat_axes[(0, 1)][0].get_position()
    bottom_left = heat_axes[(2, 1)][1].get_position()
    fig.text(0.018, top_left.y1 + 0.075, "Order-resolved broadband response on unseen K6 geometries", ha="left", va="bottom", fontsize=6.8, fontweight="bold")
    fig.text(0.018, top_left.y1 + 0.050, "Broadband trends are retained, while quantitative order allocation remains case dependent.", ha="left", va="bottom", fontsize=5.3, color="#444444")
    fig.text(top_left.x0 - 0.032, (top_left.y1 + bottom_left.y0) / 2, "Diffraction order m", ha="center", va="center", rotation=90, rotation_mode="anchor", fontsize=5.7)
    bottom_middle = heat_axes[(2, 2)][1].get_position()
    bottom_right = heat_axes[(2, 3)][1].get_position()
    bottom_truth = heat_axes[(2, 1)][1].get_position()
    for box in (bottom_truth, bottom_middle, bottom_right):
        fig.text((box.x0 + box.x1) / 2, box.y0 - 0.036, "Wavelength (nm)", ha="center", va="top", fontsize=5.6)
    fig.text(0.965, 0.018, "Screening/ranking only; final quantitative verification uses FDTD.", ha="right", va="bottom", fontsize=5.2, color="#444444")

    efficiency_axis = fig.add_subplot(outer[:, 5])
    error_axis = fig.add_subplot(outer[:, 6])
    efficiency_bar = fig.colorbar(ScalarMappable(norm=eff_norm, cmap=plt.get_cmap("coolwarm")), cax=efficiency_axis)
    efficiency_bar.set_ticks(colorbar_ticks(eff_norm.vmin, eff_norm.vmax, [eff_norm.vmin, 0.0, 0.2, 0.4, 0.6, eff_norm.vmax]))
    efficiency_bar.ax.yaxis.set_ticks_position("left")
    efficiency_bar.ax.tick_params(labelsize=5.1, length=2)
    error_bar = fig.colorbar(ScalarMappable(norm=err_norm, cmap=plt.get_cmap("magma")), cax=error_axis)
    error_bar.set_ticks(colorbar_ticks(err_norm.vmin, err_norm.vmax, [0.0, 0.1, 0.2, 0.3, 0.4, err_norm.vmax]))
    error_bar.ax.yaxis.set_ticks_position("right")
    error_bar.ax.tick_params(labelsize=5.1, length=2)
    efficiency_box = efficiency_axis.get_position()
    error_box = error_axis.get_position()
    fig.text((efficiency_box.x0 + efficiency_box.x1) / 2, efficiency_box.y0 - 0.020, "Order efficiency\neta_m\nraw OOF;\nnegatives retained", ha="center", va="top", fontsize=5.0, linespacing=1.15)
    fig.text((error_box.x0 + error_box.x1) / 2, error_box.y1 + 0.012, "Absolute\nprediction error", ha="center", va="bottom", fontsize=5.0, linespacing=1.15)

    paths = save_vector_and_raster(fig, output)
    plt.close(fig)
    return {"paths": paths, "heatmap_interpolation": "nearest-equivalent discrete pcolormesh", "colorbar_grid_height_shared": True}


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    hf_rows = read_csv(HF)
    oof_rows = read_csv(OOF)
    ranking_rows = [row for row in oof_rows if row["model"] == RANKING_MODEL and row["variant"] == VARIANT]
    spectral_rows = [row for row in oof_rows if row["model"] == SPECTRAL_MODEL and row["variant"] == VARIANT]
    if not (len(hf_rows) == len(ranking_rows) == len(spectral_rows) == 484):
        raise ValueError("frozen authority row count mismatch")
    orders = derive_orders(hf_rows[0], spectral_rows[0])
    if sorted({int(float(row["wavelength_nm"])) for row in hf_rows}) != WAVELENGTHS:
        raise ValueError("exact 445-455 nm support missing")
    if sorted({row["polarization"] for row in hf_rows}) != ["p", "s"]:
        raise ValueError("explicit P/S support missing")
    hf = {row_key(row): row for row in hf_rows}
    ranking = {row_key(row): row for row in ranking_rows}
    spectral = {row_key(row): row for row in spectral_rows}
    if len(hf) != 484 or set(hf) != set(ranking) or set(hf) != set(spectral):
        raise ValueError("truth/prediction key identity mismatch")

    def truth(record: dict[str, str], order: int) -> float:
        return float(record[f"eta_m{order:+d}"])

    def prediction(record: dict[str, str], order: int) -> float:
        return float(record[f"pred_eta_m{order:+d}"])

    geometry_ids = sorted({row["geometry_id"] for row in hf_rows})
    ranking_data: list[dict] = []
    selection: list[tuple[float, str]] = []
    for geometry in geometry_ids:
        keys = sorted(key for key in hf if key[0] == geometry)
        true_score = float(np.mean([truth(hf[key], 1) for key in keys]))
        predicted_score = float(np.mean([prediction(ranking[key], 1) for key in keys]))
        mae = float(np.mean([abs(truth(hf[key], 1) - prediction(spectral[key], 1)) for key in keys]))
        ranking_data.append({"geometry_id": geometry, "fdt_broadband_eta_plus1_score": true_score, "predicted_broadband_eta_plus1_score": predicted_score, "ranking_provider": f"{RANKING_MODEL}/{VARIANT}", "replicate_unit": "one held-out geometry"})
        selection.append((mae, geometry))
    selection.sort(key=lambda item: (item[0], item[1]))
    ranks = {"Best": 0, "Median": (len(selection) - 1) // 2, "Worst": len(selection) - 1}
    selected = [{"selection": label, "rank_ascending_eta_plus1_mae": index + 1, "geometry_count": len(selection), "geometry_id": selection[index][1], "selection_metric": "geometry-level mean absolute eta(+1) OOF error over explicit P/S and 445-455 nm", "error_value": selection[index][0], "prediction_source": f"{SPECTRAL_MODEL}/{VARIANT}", "truth_source": "HF22 formal held-out authority"} for label, index in ranks.items()]
    previous_selected = json.loads((PREVIOUS / "representative_cases.json").read_text(encoding="utf-8"))["selected_cases"]
    if [entry["geometry_id"] for entry in selected] != [entry["geometry_id"] for entry in previous_selected]:
        raise ValueError("representative selection differs from frozen v1 evidence")
    rho = spearman([float(row["fdt_broadband_eta_plus1_score"]) for row in ranking_data], [float(row["predicted_broadband_eta_plus1_score"]) for row in ranking_data])
    if not math.isclose(rho, 0.961603613777527, abs_tol=1e-12):
        raise ValueError(f"frozen ranking rho changed: {rho}")

    heat_data: list[dict] = []
    for info in selected:
        for polarization, label in (("p", "P_XLIKE"), ("s", "S_YLIKE")):
            for wavelength in WAVELENGTHS:
                key = (info["geometry_id"], polarization, wavelength)
                for order in orders:
                    true_value = truth(hf[key], order)
                    predicted_value = prediction(spectral[key], order)
                    heat_data.append({"selection": info["selection"], "rank": info["rank_ascending_eta_plus1_mae"], "geometry_id": info["geometry_id"], "polarization": label, "wavelength_nm": wavelength, "diffraction_order_m": order, "fdt_absolute_order_efficiency": true_value, "predicted_raw_order_efficiency": predicted_value, "absolute_prediction_error": abs(true_value - predicted_value), "spectral_provider": f"{SPECTRAL_MODEL}/{VARIANT}"})
    expected_rows = len(selected) * 2 * len(WAVELENGTHS) * len(orders)
    if len(heat_data) != expected_rows:
        raise ValueError("incomplete order-heatmap table")
    truth_values = [float(row["fdt_absolute_order_efficiency"]) for row in heat_data]
    prediction_values = [float(row["predicted_raw_order_efficiency"]) for row in heat_data]
    errors = [float(row["absolute_prediction_error"]) for row in heat_data]
    negative_predictions = [value for value in prediction_values if value < 0]
    negative_truth = [value for value in truth_values if value < 0]
    if negative_truth:
        raise ValueError("data-integrity failure: negative FDTD truth efficiency")
    efficiency_min = min(0.0, min(truth_values), min(prediction_values))
    efficiency_max = max(truth_values + prediction_values)
    error_max = max(errors)
    efficiency_norm = TwoSlopeNorm(vmin=efficiency_min, vcenter=0.0, vmax=efficiency_max) if efficiency_min < 0 else Normalize(vmin=0.0, vmax=efficiency_max)
    error_norm = Normalize(vmin=0.0, vmax=error_max)

    write_csv(OUT / "figure1_source_data.csv", ranking_data, list(ranking_data[0]))
    write_csv(OUT / "figure2_order_heatmap_data.csv", heat_data, list(heat_data[0]))
    write_json(OUT / "representative_cases.json", {"selection_policy": "frozen v1 programmatic selection retained without re-selection", "selection_metric": selected[0]["selection_metric"], "selected_cases": selected})
    write_json(OUT / "order_axis_mapping.json", {"source": "authority-derived formal transmitted-order columns", "tracked_order_vector": orders, "array_row_order": orders, "tick_labels": [format_order(order) for order in orders], "heatmap_origin": "lower; pcolormesh rows ascend from minimum to maximum m", "m_plus1_direction": "physical +x", "shared_for": ["FDTD truth", "raw OOF prediction", "P_XLIKE", "S_YLIKE"]})
    write_json(OUT / "negative_prediction_audit.json", {"raw_predictions_retained": True, "negative_prediction_count": len(negative_predictions), "negative_prediction_min": min(negative_predictions) if negative_predictions else None, "negative_truth_count": len(negative_truth), "negative_truth_min": min(negative_truth) if negative_truth else None, "truth_integrity": "PASS" if not negative_truth else "FAIL", "operations": {"clipping": False, "absolute_value_transform": False, "renormalization": False}})
    write_json(OUT / "color_scale_contract.json", {"truth_prediction": {"shared": True, "scale": [efficiency_min, efficiency_max], "zero_neutral": efficiency_min < 0, "colormap": "coolwarm restrained diverging", "label": "Order efficiency eta_m (raw OOF; negatives retained)"}, "absolute_error": {"shared_all_cases": True, "scale": [0.0, error_max], "colormap": "magma sequential", "label": "Absolute prediction error"}, "per_row_scales": False})

    mpl.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"], "font.size": 5.7, "axes.titlesize": 6.4, "axes.labelsize": 5.7, "xtick.labelsize": 5.1, "ytick.labelsize": 5.1, "axes.linewidth": 0.65, "axes.spines.top": False, "axes.spines.right": False, "xtick.direction": "out", "ytick.direction": "out", "xtick.major.width": 0.6, "ytick.major.width": 0.6, "svg.fonttype": "none", "pdf.fonttype": 42, "legend.frameon": False})
    figure1 = plot_figure1(ranking_data, rho, FIG / "np_k6_heldout_ranking_provider_v2")
    figure2 = plot_figure2(selected, heat_data, orders, efficiency_norm, error_norm, FIG / "np_k6_order_resolved_truth_prediction_error_v2")

    manifest = {"artifact_id": "NP_K6_FROZEN_FORWARD_SURROGATE_NATURE_FIGURE_LAYOUT_V2", "core_conclusion": "The frozen NP surrogate preserves useful held-out K6 ranking and order-resolved broadband response trends for rapid screening before full-wave FDTD verification.", "archetype": "quantitative grid split into ranking/provider and order-resolved evidence figures", "backend": "python/matplotlib", "providers": {"ranking": {"model": RANKING_MODEL, "variant": VARIANT}, "spectral": {"model": SPECTRAL_MODEL, "variant": VARIANT}, "components_are_distinct": True, "statement": "distinct frozen provider components; not a single universal surrogate"}, "scope": {"u_x": 0.0, "k_y": 0.0, "polarizations": ["P_XLIKE", "S_YLIKE"], "wavelengths_nm": WAVELENGTHS, "heldout_geometries": 22, "hf_rows": 484}, "figures": {"figure1": {"size_mm": [183.0, 75.0], **figure1}, "figure2": {"size_mm": [183.0, 165.1], **figure2}}, "tracked_order_vector": orders, "selected_cases": selected, "selection_metric": selected[0]["selection_metric"], "ranking_rho": rho, "negative_prediction_audit": "negative_prediction_audit.json", "color_scale_contract": "color_scale_contract.json", "source_artifacts": {"hf_truth": {"path": str(HF.relative_to(ROOT)).replace("/", "\\"), "sha256": sha256(HF)}, "oof_predictions": {"path": str(OOF.relative_to(ROOT)).replace("/", "\\"), "sha256": sha256(OOF)}, "v1_representative_cases": {"path": str((PREVIOUS / "representative_cases.json").relative_to(ROOT)).replace("/", "\\"), "sha256": sha256(PREVIOUS / "representative_cases.json")}}, "script_sha256": sha256(SCRIPT), "data_integrity": {"source_data_recomputed": False, "interpolation": False, "smoothing": False, "clipping": False, "renormalization": False, "P_S_averaging": False, "representative_reselection": False}, "zero_compute_audit": {"new_fdtd": 0, "new_rcwa": 0, "new_training": 0, "external_hf": 0, "inverse": 0, "data_regeneration": 0}, "generation_timestamp_utc": datetime.now(timezone.utc).isoformat()}
    write_json(OUT / "figure_manifest.json", manifest)
    write_json(OUT / "visual_qa.json", {"source_preflight": "PENDING", "pdf_glyph_audit": "PENDING", "figure1_scatter_provider_alignment": "PENDING", "figure1_annotation_clearance": "PENDING", "figure2_grid_alignment": "PENDING", "figure2_colorbar_alignment": "PENDING", "facet_label_clearance": "PENDING", "footer_clearance": "PENDING", "clipping": "PENDING", "typography": "PENDING", "raster_600dpi": "PENDING", "editable_vector_text": "PENDING"})
    DOC.write_text(f"""# NP K6 frozen forward-surrogate Nature figure layout v2

## Caption

**Held-out K6 ranking and order-resolved spectral evidence from distinct frozen provider components.** Figure 1 shows a 22-geometry held-out ranking comparison using `LF_only / ensemble_raw` (Spearman rho = {rho:.3f}). Figure 2 compares FDTD truth, `LF_ridge_residual / ensemble_raw` raw prediction and absolute error for programmatically retained Best, Median and Worst geometries. The selection metric is geometry-level mean absolute eta(+1) OOF error over explicit P/S and 445-455 nm. Each P_XLIKE and S_YLIKE heatmap uses the authority-derived transmitted-order vector `m = {orders}`; `m = +1` corresponds to physical +x. Truth and raw prediction share a global zero-centred scale. Negative predicted values are retained to expose physics-consistency violations and are not clipped. Absolute error uses a separate, global scale shared by all cases.

The provider components are distinct and do not form a single universal surrogate. Scope is normal incidence only (`u_x = 0`, `k_y = 0`), with 22 held-out geometries, 484 HF rows, explicit P/S, and 445-455 nm support. These figures support screening/ranking before FDTD; they do not support FDTD replacement, angular generalization, Jones-matrix prediction or integrated MDC-NP truth.

## Compute audit

No new FDTD, RCWA, training, external-HF access, inverse design or data regeneration was performed. PNG/TIFF are 600 dpi; PDF/SVG retain editable text.
""", encoding="utf-8")
    print(json.dumps({"status": "GENERATED", "orders": orders, "rho": rho, "selected": selected, "negative_prediction_count": len(negative_predictions), "negative_prediction_min": min(negative_predictions) if negative_predictions else None, "negative_truth_count": len(negative_truth), "heatmap_rows": len(heat_data), "zero_compute": manifest["zero_compute_audit"]}, indent=2))


if __name__ == "__main__":
    main()
