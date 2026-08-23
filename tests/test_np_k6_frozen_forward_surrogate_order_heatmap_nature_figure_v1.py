from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / "outputs/np_k6_frozen_forward_surrogate_order_heatmap_nature_figure_v1"
VALIDATOR = ROOT / "scripts/validate_np_k6_frozen_forward_surrogate_order_heatmap_nature_figure_v1.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("order_heatmap_validator", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def rows(name: str):
    with (OUT / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_ranking_is_geometry_grouped() -> None:
    data = rows("heldout_ranking_data.csv")
    assert len(data) == 22
    assert len({row["geometry_id"] for row in data}) == 22
    assert {row["replicate_unit"] for row in data} == {"one held-out geometry"}


def test_exact_order_grid_and_polarizations() -> None:
    data = rows("representative_order_heatmap_data.csv")
    assert len(data) == 462
    assert {int(row["diffraction_order_m"]) for row in data} == set(range(-3, 4))
    assert {int(row["wavelength_nm"]) for row in data} == set(range(445, 456))
    assert {row["polarization"] for row in data} == {"P_XLIKE", "S_YLIKE"}


def test_distinct_provider_contract() -> None:
    manifest = json.loads((OUT / "figure_manifest.json").read_text(encoding="utf-8"))
    assert manifest["providers"]["ranking"]["model"] == "LF_only"
    assert manifest["providers"]["spectral"]["model"] == "LF_ridge_residual"
    assert manifest["providers"]["components_are_distinct"] is True


def test_no_value_altering_operations_and_zero_compute() -> None:
    manifest = json.loads((OUT / "figure_manifest.json").read_text(encoding="utf-8"))
    assert not any(manifest["data_integrity"].values())
    assert set(manifest["zero_compute_audit"].values()) == {0}


def test_raw_negative_predictions_are_not_clipped() -> None:
    data = rows("representative_order_heatmap_data.csv")
    assert min(float(row["predicted_absolute_order_efficiency"]) for row in data) < 0


def test_standalone_validator_passes() -> None:
    report = load_validator().validate(ROOT)
    assert report["status"] == "PASS", [item for item in report["checks"] if not item["passed"]]
