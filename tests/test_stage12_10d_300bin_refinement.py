from metasurface.stage12_10d_300bin_refinement import (
    classify_candidate_300,
    cluster_existing,
    in_extended_window,
    in_phase_window,
    phase_error_to_300,
)
from metasurface.stage12_10b_240bin_broad_family import enforce_candidate_limit


def test_stage12_10d_phase_window_filtering():
    assert in_phase_window(300) is True
    assert in_phase_window(284.9) is False
    assert in_extended_window(270) is True
    assert in_extended_window(330.1) is False
    assert phase_error_to_300(-52.5) == 7.5


def test_stage12_10d_candidate_limit():
    assert len(enforce_candidate_limit([{"i": i} for i in range(20)], 12)) == 12


def test_stage12_10d_pass_fail_classification():
    c = classify_candidate_300({"nearest_bin_deg": 300, "phase_error_deg": 7, "Tx": 0.88, "conversion_to_leakage_ratio": 35, "matrix_error": 0.21, "estimated_leakage": 0.025, "geometry_legal": True})
    assert c["hard_pass"] is True and c["preferred_pass"] is True and c["stretch_pass"] is False


def test_stage12_10d_stretch_classification():
    c = classify_candidate_300({"nearest_bin_deg": 300, "phase_error_deg": 4, "Tx": 0.9, "conversion_to_leakage_ratio": 55, "matrix_error": 0.19, "estimated_leakage": 0.02, "geometry_legal": True})
    assert c["stretch_pass"] is True


def test_stage12_10d_family_clustering(tmp_path):
    from metasurface.stage12_10d_300bin_refinement import Stage12_10DPaths
    paths = Stage12_10DPaths(tmp_path, tmp_path, tmp_path, tmp_path, tmp_path)
    rows = [
        {"candidate_id": "a", "phase_deg": 298, "geometry_family": "x_pair_swap", "conversion_to_leakage_ratio": 14, "Tx": 0.9, "phase_error_deg": 2, "matrix_error": 0.27, "estimated_leakage": 0.07, "strict": False},
        {"candidate_id": "b", "phase_deg": 315, "geometry_family": "y_pair_swap", "conversion_to_leakage_ratio": 20, "Tx": 0.8, "phase_error_deg": 15, "matrix_error": 0.25, "estimated_leakage": 0.04, "strict": False},
    ]
    assert len(cluster_existing(rows, paths)) == 2