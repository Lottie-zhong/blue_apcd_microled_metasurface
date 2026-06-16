from metasurface.stage12_10c_180bin_refinement import (
    classify_candidate_180,
    cluster_existing,
    in_extended_window,
    in_phase_window,
    phase_error_to_180,
)
from metasurface.stage12_10b_240bin_broad_family import enforce_candidate_limit


def test_stage12_10c_phase_window_filtering():
    assert in_phase_window(180) is True
    assert in_phase_window(164.9) is False
    assert in_extended_window(150) is True
    assert in_extended_window(210.1) is False
    assert phase_error_to_180(151) == 29


def test_stage12_10c_candidate_limit():
    assert len(enforce_candidate_limit([{"i": i} for i in range(20)], 12)) == 12


def test_stage12_10c_pass_fail_classification():
    c = classify_candidate_180({"nearest_bin_deg": 180, "phase_error_deg": 7, "Tx": 0.85, "conversion_to_leakage_ratio": 35, "matrix_error": 0.24, "estimated_leakage": 0.024, "geometry_legal": True})
    assert c["hard_pass"] is True and c["preferred_pass"] is True and c["stretch_pass"] is False


def test_stage12_10c_stretch_classification():
    c = classify_candidate_180({"nearest_bin_deg": 180, "phase_error_deg": 4, "Tx": 0.9, "conversion_to_leakage_ratio": 55, "matrix_error": 0.19, "estimated_leakage": 0.02, "geometry_legal": True})
    assert c["stretch_pass"] is True


def test_stage12_10c_family_clustering(tmp_path):
    from metasurface.stage12_10c_180bin_refinement import Stage12_10CPaths
    paths = Stage12_10CPaths(tmp_path, tmp_path, tmp_path, tmp_path)
    rows = [
        {"candidate_id": "a", "phase_deg": 178, "geometry_family": "x_pair_swap", "conversion_to_leakage_ratio": 12, "Tx": 0.9, "phase_error_deg": 2, "matrix_error": 0.3, "estimated_leakage": 0.08, "strict": False},
        {"candidate_id": "b", "phase_deg": 151, "geometry_family": "y_pair_swap", "conversion_to_leakage_ratio": 200, "Tx": 1.0, "phase_error_deg": 29, "matrix_error": 0.06, "estimated_leakage": 0.004, "strict": False},
    ]
    assert len(cluster_existing(rows, paths)) == 2