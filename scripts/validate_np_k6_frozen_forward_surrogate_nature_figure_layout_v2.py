from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from PIL import Image


ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / "outputs/np_k6_frozen_forward_surrogate_nature_figure_layout_v2"
FIG = ROOT / "figures/np_k6_frozen_forward_surrogate_nature_figure_layout_v2"
V1 = ROOT / "outputs/np_k6_frozen_forward_surrogate_order_heatmap_nature_figure_v1"
FORMATS = ("png", "tiff", "pdf", "svg")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def check(items: list[dict], name: str, passed: bool, detail: object) -> None:
    items.append({"check": name, "passed": bool(passed), "detail": detail})


def validate(root: Path = ROOT) -> dict:
    out = root / OUT.relative_to(ROOT)
    fig = root / FIG.relative_to(ROOT)
    items: list[dict] = []
    manifest = read_json(out / "figure_manifest.json")
    ranking = read_csv(out / "figure1_source_data.csv")
    heat = read_csv(out / "figure2_order_heatmap_data.csv")
    selected = read_json(out / "representative_cases.json")["selected_cases"]
    order_map = read_json(out / "order_axis_mapping.json")
    negative = read_json(out / "negative_prediction_audit.json")
    scales = read_json(out / "color_scale_contract.json")
    qa = read_json(out / "visual_qa.json")

    check(items, "artifact identity", manifest.get("artifact_id") == "NP_K6_FROZEN_FORWARD_SURROGATE_NATURE_FIGURE_LAYOUT_V2", manifest.get("artifact_id"))
    providers = manifest["providers"]
    provider_ok = providers["ranking"] == {"model": "LF_only", "variant": "ensemble_raw"} and providers["spectral"] == {"model": "LF_ridge_residual", "variant": "ensemble_raw"} and providers["components_are_distinct"] is True
    check(items, "distinct frozen providers", provider_ok, providers)
    scope = manifest["scope"]
    check(items, "frozen 22 geometry 484 row scope", scope == {"heldout_geometries": 22, "hf_rows": 484, "k_y": 0.0, "polarizations": ["P_XLIKE", "S_YLIKE"], "u_x": 0.0, "wavelengths_nm": list(range(445, 456))}, scope)
    check(items, "one ranking row per held-out geometry", len(ranking) == 22 and len({row["geometry_id"] for row in ranking}) == 22 and {row["replicate_unit"] for row in ranking} == {"one held-out geometry"}, {"rows": len(ranking), "unique": len({row["geometry_id"] for row in ranking})})
    check(items, "frozen rho", math.isclose(float(manifest["ranking_rho"]), 0.961603613777527, abs_tol=1e-12), manifest["ranking_rho"])
    orders = order_map["tracked_order_vector"]
    keys = {(row["selection"], row["polarization"], int(row["wavelength_nm"]), int(row["diffraction_order_m"])) for row in heat}
    expected = {(selection, polarization, wavelength, order) for selection in ("Best", "Median", "Worst") for polarization in ("P_XLIKE", "S_YLIKE") for wavelength in range(445, 456) for order in orders}
    check(items, "complete order-resolved grid", len(heat) == 462 and keys == expected, {"rows": len(heat), "keys": len(keys), "expected": len(expected)})
    check(items, "order-axis mapping and +x convention", orders == sorted(orders) and order_map["array_row_order"] == orders and order_map["m_plus1_direction"] == "physical +x", order_map)
    v1_selected = read_json(root / V1.relative_to(ROOT) / "representative_cases.json")["selected_cases"]
    check(items, "representatives retained from v1", [row["geometry_id"] for row in selected] == [row["geometry_id"] for row in v1_selected] and [int(row["rank_ascending_eta_plus1_mae"]) for row in selected] == [1, 11, 22], selected)
    check(items, "negative raw prediction integrity", negative["raw_predictions_retained"] is True and negative["negative_prediction_count"] == sum(float(row["predicted_raw_order_efficiency"]) < 0 for row in heat) and negative["negative_prediction_min"] == min(float(row["predicted_raw_order_efficiency"]) for row in heat) and negative["negative_truth_count"] == 0, negative)
    scale_ok = scales["truth_prediction"]["shared"] is True and scales["truth_prediction"]["zero_neutral"] is True and scales["absolute_error"]["shared_all_cases"] is True and scales["absolute_error"]["scale"][0] == 0.0 and scales["per_row_scales"] is False
    check(items, "global color-scale contract", scale_ok, scales)
    integrity = manifest["data_integrity"]
    check(items, "no data-altering operation", all(value is False for value in integrity.values()), integrity)
    check(items, "zero compute", manifest["zero_compute_audit"] == {"new_fdtd": 0, "new_rcwa": 0, "new_training": 0, "external_hf": 0, "inverse": 0, "data_regeneration": 0}, manifest["zero_compute_audit"])

    dimensions = {}
    for stem in ("np_k6_heldout_ranking_provider_v2", "np_k6_order_resolved_truth_prediction_error_v2"):
        present = all((fig / f"{stem}.{suffix}").is_file() and (fig / f"{stem}.{suffix}").stat().st_size > 0 for suffix in FORMATS)
        with Image.open(fig / f"{stem}.png") as image:
            dimensions[stem] = {"size_px": list(image.size), "dpi": list(image.info.get("dpi", (0, 0)))}
        check(items, f"{stem} export bundle", present, dimensions[stem])
    size_ok = all(data["size_px"][0] == 4323 and min(data["dpi"]) >= 599 for data in dimensions.values()) and dimensions["np_k6_heldout_ranking_provider_v2"]["size_px"][1] <= 1890 and dimensions["np_k6_order_resolved_truth_prediction_error_v2"]["size_px"][1] <= 4016
    check(items, "183 mm wide and <=170 mm high 600 dpi rasters", size_ok, dimensions)
    qa_fields = ("source_preflight", "pdf_glyph_audit", "figure1_scatter_provider_alignment", "figure1_annotation_clearance", "figure2_grid_alignment", "figure2_colorbar_alignment", "facet_label_clearance", "footer_clearance", "clipping", "typography", "raster_600dpi", "editable_vector_text")
    check(items, "visual QA complete", all(qa.get(name) == "PASS" for name in qa_fields), qa)
    report = {"validator": "NP_K6_FROZEN_FORWARD_SURROGATE_NATURE_FIGURE_LAYOUT_V2", "status": "PASS" if all(item["passed"] for item in items) else "FAIL", "passed": sum(item["passed"] for item in items), "total": len(items), "checks": items}
    (out / "figure_validator_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    report = validate()
    print(json.dumps({"status": report["status"], "passed": report["passed"], "total": report["total"]}))
    raise SystemExit(0 if report["status"] == "PASS" else 1)
