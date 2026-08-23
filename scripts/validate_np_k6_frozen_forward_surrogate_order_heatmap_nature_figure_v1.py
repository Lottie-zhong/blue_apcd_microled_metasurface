from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from PIL import Image


ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / "outputs/np_k6_frozen_forward_surrogate_order_heatmap_nature_figure_v1"
FIG = ROOT / "figures/np_k6_frozen_forward_surrogate_order_heatmap_nature_figure_v1"
BASE = FIG / "np_k6_frozen_forward_surrogate_order_heatmap_nature_figure_v1"
ORDERS = [-3, -2, -1, 0, 1, 2, 3]
WAVELENGTHS = list(range(445, 456))
POLARIZATIONS = ["P_XLIKE", "S_YLIKE"]
SELECTIONS = ["Best", "Median", "Worst"]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def add(checks: list[dict], name: str, passed: bool, detail: object) -> None:
    checks.append({"check": name, "passed": bool(passed), "detail": detail})


def validate(root: Path = ROOT) -> dict:
    out = root / OUT.relative_to(ROOT)
    fig = root / FIG.relative_to(ROOT)
    base = fig / BASE.name
    checks: list[dict] = []
    manifest = read_json(out / "figure_manifest.json")
    representatives = read_json(out / "representative_cases.json")
    ranking = read_csv(out / "heldout_ranking_data.csv")
    heat = read_csv(out / "representative_order_heatmap_data.csv")
    qa = read_json(out / "visual_qa.json")

    add(checks, "artifact identity", manifest.get("artifact_id") == "NP_K6_FROZEN_FORWARD_SURROGATE_ORDER_HEATMAP_NATURE_FIGURE_V1", manifest.get("artifact_id"))
    scope = manifest["scope"]
    add(checks, "frozen normal-incidence scope", scope == {"heldout_geometries": 22, "hf_rows": 484, "k_y": 0.0, "polarizations": POLARIZATIONS, "u_x": 0.0, "wavelengths_nm": WAVELENGTHS}, scope)
    providers = manifest["providers"]
    provider_ok = providers["ranking"] == {"model": "LF_only", "variant": "ensemble_raw"} and providers["spectral"] == {"model": "LF_ridge_residual", "variant": "ensemble_raw"} and providers["components_are_distinct"] is True
    add(checks, "distinct frozen providers", provider_ok, providers)
    add(checks, "authority-derived order vector", manifest["tracked_order_vector"] == ORDERS, manifest["tracked_order_vector"])

    ranking_ids = [row["geometry_id"] for row in ranking]
    add(checks, "one ranking point per held-out geometry", len(ranking) == 22 and len(set(ranking_ids)) == 22 and all(row["replicate_unit"] == "one held-out geometry" for row in ranking), {"rows": len(ranking), "unique": len(set(ranking_ids))})
    rho = float(manifest["metrics"]["geometry_ranking_spearman"])
    add(checks, "exact frozen ranking rho", math.isclose(rho, 0.961603613777527, abs_tol=1e-12), rho)

    keys = {(row["selection"], row["polarization"], int(row["wavelength_nm"]), int(row["diffraction_order_m"])) for row in heat}
    expected = {(selection, pol, wavelength, order) for selection in SELECTIONS for pol in POLARIZATIONS for wavelength in WAVELENGTHS for order in ORDERS}
    numeric_finite = all(math.isfinite(float(row[field])) for row in heat for field in ("fdt_absolute_order_efficiency", "predicted_absolute_order_efficiency", "absolute_prediction_error"))
    add(checks, "complete exact order heatmap grid", len(heat) == 462 and keys == expected and numeric_finite, {"rows": len(heat), "unique_keys": len(keys), "expected": len(expected), "finite": numeric_finite})
    add(checks, "raw negative predictions preserved", any(float(row["predicted_absolute_order_efficiency"]) < 0 for row in heat) and manifest["metrics"]["negative_raw_spectral_predictions_preserved"] > 0, manifest["metrics"]["negative_raw_spectral_predictions_preserved"])
    integrity = manifest["data_integrity"]
    add(checks, "no interpolation or value alteration", all(integrity[name] is False for name in ("interpolation", "smoothing", "clipping", "renormalization", "P_S_averaging", "wavelength_rows_as_independent_geometries")), integrity)
    selected = representatives["selected_cases"]
    add(checks, "programmatic best median worst", [row["selection"] for row in selected] == SELECTIONS and [int(row["rank_ascending_eta_plus1_mae"]) for row in selected] == [1, 11, 22], selected)

    efficiency_scale = manifest["metrics"]["efficiency_common_scale"]
    error_scale = manifest["metrics"]["absolute_error_scale"]
    add(checks, "common truth prediction and independent error scales", efficiency_scale[0] < 0 < efficiency_scale[1] and error_scale[0] == 0 and error_scale[1] > 0 and efficiency_scale != error_scale, {"efficiency": efficiency_scale, "error": error_scale})
    zero = manifest["zero_compute_audit"]
    add(checks, "zero-compute contract", zero == {"data_regeneration": 0, "external_hf": 0, "inverse": 0, "new_fdtd": 0, "new_rcwa": 0, "new_training": 0}, zero)

    formats = ["png", "tiff", "pdf", "svg"]
    add(checks, "all required figure formats", all(base.with_suffix(f".{suffix}").is_file() and base.with_suffix(f".{suffix}").stat().st_size > 0 for suffix in formats), {suffix: base.with_suffix(f".{suffix}").stat().st_size if base.with_suffix(f".{suffix}").exists() else None for suffix in formats})
    raster = {}
    for suffix in ("png", "tiff"):
        with Image.open(base.with_suffix(f".{suffix}")) as image:
            raster[suffix] = {"size_px": list(image.size), "dpi": [float(v) for v in image.info.get("dpi", (0, 0))]}
    raster_ok = all(item["size_px"] == [4323, 3870] and min(item["dpi"]) >= 599 for item in raster.values())
    add(checks, "183 mm raster exports at 600 dpi", raster_ok, raster)
    required_qa = ("source_preflight", "pdf_glyph_audit", "panel_a_annotation_overlap", "panel_b_facet_overlap", "clipping", "color_scale_contract", "typography", "raster_600dpi")
    add(checks, "visual QA complete", all(qa.get(name) == "PASS" for name in required_qa), qa)

    report = {"validator": "NP_K6_FROZEN_FORWARD_SURROGATE_ORDER_HEATMAP_NATURE_FIGURE_V1", "status": "PASS" if all(item["passed"] for item in checks) else "FAIL", "passed": sum(item["passed"] for item in checks), "total": len(checks), "checks": checks}
    (out / "figure_validator_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    result = validate()
    print(json.dumps({"status": result["status"], "passed": result["passed"], "total": result["total"]}))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
