from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / "outputs/np_k6_frozen_forward_surrogate_nature_figure_layout_v2"
VALIDATOR = ROOT / "scripts/validate_np_k6_frozen_forward_surrogate_nature_figure_layout_v2.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("layout_v2_validator", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def csv_rows(name: str):
    with (OUT / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_frozen_membership_and_order_grid() -> None:
    assert len(csv_rows("figure1_source_data.csv")) == 22
    data = csv_rows("figure2_order_heatmap_data.csv")
    assert len(data) == 462
    assert {int(row["diffraction_order_m"]) for row in data} == set(range(-3, 4))


def test_explicit_polarizations_and_exact_wavelengths() -> None:
    data = csv_rows("figure2_order_heatmap_data.csv")
    assert {row["polarization"] for row in data} == {"P_XLIKE", "S_YLIKE"}
    assert {int(row["wavelength_nm"]) for row in data} == set(range(445, 456))


def test_provider_and_zero_compute_contract() -> None:
    manifest = json.loads((OUT / "figure_manifest.json").read_text(encoding="utf-8"))
    assert manifest["providers"]["ranking"]["model"] == "LF_only"
    assert manifest["providers"]["spectral"]["model"] == "LF_ridge_residual"
    assert manifest["providers"]["components_are_distinct"] is True
    assert set(manifest["zero_compute_audit"].values()) == {0}


def test_negative_predictions_are_retained_and_truth_is_nonnegative() -> None:
    data = csv_rows("figure2_order_heatmap_data.csv")
    assert min(float(row["predicted_raw_order_efficiency"]) for row in data) < 0
    assert min(float(row["fdt_absolute_order_efficiency"]) for row in data) >= 0


def test_axis_mapping_is_physical_plus_x() -> None:
    mapping = json.loads((OUT / "order_axis_mapping.json").read_text(encoding="utf-8"))
    assert mapping["tracked_order_vector"] == mapping["array_row_order"] == [-3, -2, -1, 0, 1, 2, 3]
    assert mapping["m_plus1_direction"] == "physical +x"


def test_standalone_validator_passes() -> None:
    report = load_validator().validate(ROOT)
    assert report["status"] == "PASS", [item for item in report["checks"] if not item["passed"]]
