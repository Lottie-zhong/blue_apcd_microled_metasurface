import math

from metasurface.stage12_12a_spectral_audit import (
    adjacent_phase_steps,
    gaussian_weights,
    generate_wavelength_grid,
    phase_distance_deg,
    weak_bin_summary,
)


def test_gaussian_weights_normalize():
    weights = gaussian_weights([447, 448, 449, 450, 451, 452, 453], 6)
    assert abs(sum(weights) - 1.0) < 1e-12
    assert weights[3] == max(weights)
    assert math.isclose(weights[0], weights[-1])


def test_phase_wrap_distance():
    assert phase_distance_deg(358, 2) == 4
    assert phase_distance_deg(2, 358) == 4
    assert phase_distance_deg(240, 240) == 0


def test_adjacent_phase_steps_wrap_last_step():
    phases = {0: 1, 60: 61, 120: 121, 180: 181, 240: 241, 300: 301}
    rows = adjacent_phase_steps(phases)
    assert [row["phase_step_deg"] for row in rows] == [60, 60, 60, 60, 60, 60]
    assert all(row["phase_step_error_from_60_deg"] == 0 for row in rows)


def test_weak_bin_detection_uses_ratio_and_leakage():
    rows = [
        {"fdtd_status": "ok", "bin_deg": 0, "conversion_to_leakage_ratio": 100, "blocked_y_total_leakage": 0.01},
        {"fdtd_status": "ok", "bin_deg": 120, "conversion_to_leakage_ratio": 5, "blocked_y_total_leakage": 0.02},
        {"fdtd_status": "ok", "bin_deg": 240, "conversion_to_leakage_ratio": 7, "blocked_y_total_leakage": 0.08},
    ]
    weak = weak_bin_summary(rows)
    assert weak["weakest_bin_by_ratio"] == 120
    assert weak["weakest_bin_by_leakage"] == 240
    assert weak["bin120_warning"] is True
    assert weak["bin240_warning"] is False


def test_wavelength_grid_generation():
    assert generate_wavelength_grid() == [447, 448, 449, 450, 451, 452, 453]
