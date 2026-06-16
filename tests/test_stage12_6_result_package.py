from __future__ import annotations

from pathlib import Path

from metasurface.stage13_0_result_package import (
    build_figure_manifest,
    official_xgrad_pass,
    ygrad_diagnostic_classification,
)


def test_stage13_official_xgrad_pass_classification() -> None:
    metrics = {"target_order_selectivity_ratio": 11.655, "x_LP_steering_angle_deg": 10.0}
    assert official_xgrad_pass(metrics) is True


def test_stage13_ygrad_diagnostic_classification() -> None:
    metrics = {"target_order_selectivity_ratio": 1.986, "steering_angle_deg": 10.0}
    assert ygrad_diagnostic_classification(metrics) == "STEERING_PASS_SELECTIVITY_FAIL"


def test_stage13_figure_manifest_generation() -> None:
    rows = build_figure_manifest(Path("out"))
    assert len(rows) == 5
    assert rows[0]["png"].endswith("figure_1_stage11_6bin_library.png")
    assert rows[-1]["svg"].endswith("figure_5_stage_flow_summary.svg")
