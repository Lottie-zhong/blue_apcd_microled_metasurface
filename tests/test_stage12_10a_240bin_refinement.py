from metasurface.stage12_10a_240bin_refinement import (
    classify_candidate,
    clearance_ok,
    enforce_candidate_limit,
    estimated_leakage,
    nearest_bin,
    phase_error_to_bin,
)


def test_stage12_10a_240_filter_helpers():
    assert nearest_bin(-127.0) == 240
    assert phase_error_to_bin(-127.0, 240) == 7.0


def test_stage12_10a_pass_fail_classification():
    row = {"nearest_bin_deg": 240, "phase_error_deg": 8, "Tx": 0.76, "conversion_to_leakage_ratio": 22, "matrix_error": 0.27, "estimated_leakage": 0.034, "geometry_legal": True}
    c = classify_candidate(row)
    assert c["hard_pass"] is True
    assert c["preferred_pass"] is True
    assert c["stretch_pass"] is False


def test_stage12_10a_candidate_limit():
    assert len(enforce_candidate_limit([{"i": i} for i in range(20)], 16)) == 16


def test_stage12_10a_clearance_threshold():
    assert clearance_ok(15.0, 5.0) is True
    assert clearance_ok(14.9, 5.0) is False


def test_stage12_10a_estimated_leakage():
    assert estimated_leakage(0.75, 15.0) == 0.05