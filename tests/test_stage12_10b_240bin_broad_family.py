from metasurface.stage12_10b_240bin_broad_family import (
    cluster_existing,
    enforce_candidate_limit,
    in_extended_window,
    in_phase_window,
    parse_family,
    rank_results,
)
from metasurface.stage12_10a_240bin_refinement import classify_candidate


def test_stage12_10b_phase_window_filtering():
    assert in_phase_window(240) is True
    assert in_phase_window(219.9) is False
    assert in_extended_window(210) is True
    assert in_extended_window(270.1) is False


def test_stage12_10b_family_parsing():
    assert parse_family({"candidate_id": "X_x_pair_noswap_G80"}) == "x_pair_noswap"
    assert parse_family({"candidate_id": "X_diag_pair_swap_G80"}) == "diag_pair_swap"


def test_stage12_10b_candidate_limit():
    assert len(enforce_candidate_limit([{"i": i} for i in range(20)], 12)) == 12


def test_stage12_10b_pass_fail_classification():
    c = classify_candidate({"nearest_bin_deg": 240, "phase_error_deg": 8, "Tx": 0.76, "conversion_to_leakage_ratio": 22, "matrix_error": 0.27, "estimated_leakage": 0.034, "geometry_legal": True})
    assert c["hard_pass"] is True and c["preferred_pass"] is True and c["stretch_pass"] is False


def test_stage12_10b_ranking_cluster_shape(tmp_path):
    from metasurface.stage12_10b_240bin_broad_family import Stage12_10BPaths
    paths = Stage12_10BPaths(tmp_path, tmp_path, tmp_path, tmp_path)
    rows = [
        {"candidate_id": "a_x_pair_swap", "phase_deg": 238, "geometry_family": "x_pair_swap", "conversion_to_leakage_ratio": 8, "Tx": 0.7, "phase_error_deg": 2, "matrix_error": 0.3, "estimated_leakage": 0.08, "strict": False},
        {"candidate_id": "b_y_pair_noswap", "phase_deg": 250, "geometry_family": "y_pair_noswap", "conversion_to_leakage_ratio": 6, "Tx": 0.6, "phase_error_deg": 10, "matrix_error": 0.4, "estimated_leakage": 0.1, "strict": False},
    ]
    clusters = cluster_existing(rows, paths)
    assert len(clusters) == 2

def test_stage12_10b_ranking_prioritizes_240_phase(tmp_path):
    from metasurface.stage12_10b_240bin_broad_family import Stage12_10BPaths, write_csv, PLAN_FIELDS
    paths = Stage12_10BPaths(tmp_path, tmp_path, tmp_path, tmp_path)
    write_csv(tmp_path / "stage12_10b_240bin_candidate_plan.csv", [
        {"dimer_case_id": "wrong", "geometry_family": "y_pair_swap", "minimum_clearance_nm": "70"},
        {"dimer_case_id": "near240", "geometry_family": "x_pair_swap", "minimum_clearance_nm": "70"},
    ], PLAN_FIELDS)
    rows = [
        {"dimer_case_id": "wrong", "target_x_power": "1", "y_input_total_leak_power": "0.004", "dimer_selectivity_ratio": "250", "dimer_output_phase_deg": "151", "x_input_cross_leak_power": "0", "geometry_legal": "true", "fdtd_status": "ok"},
        {"dimer_case_id": "near240", "target_x_power": "0.8", "y_input_total_leak_power": "0.09", "dimer_selectivity_ratio": "8", "dimer_output_phase_deg": "224", "x_input_cross_leak_power": "0", "geometry_legal": "true", "fdtd_status": "ok"},
    ]
    assert rank_results(rows, paths)[0]["candidate_id"] == "near240"
