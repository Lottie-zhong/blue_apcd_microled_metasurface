from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.stage13_5_order_diagnosis import (
    TARGET_UX,
    cone_rows,
    incoherent_rows,
    intensity_components,
    mechanism_classification,
    peak_rows,
)


def gaussian(xx: np.ndarray, yy: np.ndarray, ux0: float, uy0: float, sigma: float = 0.025) -> np.ndarray:
    return np.exp(-((xx - ux0) ** 2 + (yy - uy0) ** 2) / (2 * sigma**2)).astype(np.complex128)


def synthetic_fields(leakage_at_target: bool = False) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    u = np.linspace(-0.4, 0.4, 101)
    xx, yy = np.meshgrid(u, u, indexing="ij")
    ex = gaussian(xx, yy, TARGET_UX, 0.0)
    ey_center = TARGET_UX if leakage_at_target else 0.0
    ey = gaussian(xx, yy, ey_center, 0.0)
    ez = np.zeros_like(ex)
    return ex, ey, ez, xx, yy


def test_peak_finds_plus_target_and_zero_leakage() -> None:
    ex, ey, ez, xx, yy = synthetic_fields(False)
    maps = intensity_components(ex, ey, ez)
    rows = peak_rows("center_x", maps, xx, yy)
    ex_peak = next(row for row in rows if row["component"] == "Ex_target")
    ey_peak = next(row for row in rows if row["component"] == "Ey_leakage")

    assert ex_peak["nearest_expected_order"] == "plus_target_order"
    assert ex_peak["steering_present_within_3deg"] is True
    assert ey_peak["nearest_expected_order"] == "zero_order"


def test_order_cones_and_incoherent_sum() -> None:
    ex, ey, ez, xx, yy = synthetic_fields(False)
    xrows = cone_rows("center_x", intensity_components(ex, ey * 0.2, ez), xx, yy)
    yrows = cone_rows("center_y", intensity_components(ex * 0.15, ey * 0.5, ez), xx, yy)
    averages = incoherent_rows(xrows + yrows)
    plus3 = next(row for row in averages if row["order_id"] == "plus_target_order" and row["cone_deg"] == 3.0)

    assert plus3["LP_fraction_incoherent"] > 0.90
    assert plus3["pass_lp_fraction_gt_0p60"] is True


def test_classification_angle_separated_vs_contaminated() -> None:
    ex, ey, ez, xx, yy = synthetic_fields(False)
    xmaps = intensity_components(ex, ey * 0.1, ez)
    ymaps = intensity_components(ex * 0.1, ey * 0.4, ez)
    peaks = peak_rows("center_x", xmaps, xx, yy) + peak_rows("center_y", ymaps, xx, yy)
    orders = cone_rows("center_x", xmaps, xx, yy) + cone_rows("center_y", ymaps, xx, yy)
    classification = mechanism_classification(peaks, orders, incoherent_rows(orders))
    assert classification["primary_class"] == "class_A_angle_separated_leakage"

    ex2, ey2, ez2, xx2, yy2 = synthetic_fields(True)
    xmaps2 = intensity_components(ex2, ey2 * 0.1, ez2)
    ymaps2 = intensity_components(ex2 * 0.1, ey2, ez2)
    peaks2 = peak_rows("center_x", xmaps2, xx2, yy2) + peak_rows("center_y", ymaps2, xx2, yy2)
    orders2 = cone_rows("center_x", xmaps2, xx2, yy2) + cone_rows("center_y", ymaps2, xx2, yy2)
    classification2 = mechanism_classification(peaks2, orders2, incoherent_rows(orders2))
    assert classification2["primary_class"] == "class_B_target_order_contaminated"


def test_no_steering_does_not_invent_actual_order_or_contamination() -> None:
    ex, ey, ez, xx, yy = synthetic_fields(False)
    maps = intensity_components(ex, ey, ez)
    x_peaks = peak_rows("center_x", maps, xx, yy)
    ex_peak = next(row for row in x_peaks if row["component"] == "Ex_target")
    ex_peak["nearest_expected_order"] = "other"
    ex_peak["steering_present_within_3deg"] = False
    peaks = x_peaks + peak_rows("center_y", maps, xx, yy)
    orders = cone_rows("center_x", maps, xx, yy) + cone_rows("center_y", maps, xx, yy)
    result = mechanism_classification(peaks, orders, incoherent_rows(orders))
    assert result["primary_class"] == "class_C_no_steering"
    assert result["actual_target_order"] == "unresolved"
    assert result["target_order_contaminated"] is None
    assert result["actual_target_incoherent_lp_fraction"] == {}
    assert result["order_resolved_center_failed"] is None
