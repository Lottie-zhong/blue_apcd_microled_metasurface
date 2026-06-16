from metasurface.stage12_9_xgrad_leakage_cancellation import (
    MAX_NEW_VARIANTS,
    clearance_rule_ok,
    enforce_candidate_limit,
    leakage_thresholds,
    rank_stage12_9_rows,
    validate_same_bin_substitution,
)
from metasurface.stage12_8_xgrad_refinement import classify_pass


def test_stage12_9_candidate_limit_keeps_references_plus_ten():
    variants = [
        {"variant_id": "variant_000_baseline", "status": "reference"},
        {"variant_id": "variant_001_sub_bin240_stage12_8_seed", "status": "reference"},
    ] + [{"variant_id": f"v{i}", "status": "planned"} for i in range(20)]
    limited = enforce_candidate_limit(variants, MAX_NEW_VARIANTS)
    assert len(limited) == 12
    assert sum(v["status"] != "reference" for v in limited) == 10


def test_stage12_9_same_bin_substitution_rule():
    assert validate_same_bin_substitution(240, {"bin_deg": "240"}) is True
    assert validate_same_bin_substitution(240, {"bin_deg": "300"}) is False


def test_stage12_9_clearance_threshold_rule():
    assert clearance_rule_ok({"geometry_legal": True, "minimum_clearance_nm": 15.0, "minimum_neighbor_clearance_nm": 76.0}) is True
    assert clearance_rule_ok({"geometry_legal": True, "minimum_clearance_nm": 14.9, "minimum_neighbor_clearance_nm": 76.0}) is False


def test_stage12_9_pass_fail_classification():
    row = {"x_LP_target_plus1_power": 0.31, "y_LP_target_plus1_leakage": 0.009, "target_order_selectivity_ratio": 34, "steering_angle_deg": 10.0, "x_LP_dominant_order": "+1", "geometry_legal": True}
    result = classify_pass(row)
    assert result["hard_pass"] is True
    assert result["preferred_pass"] is True
    assert result["stretch_pass"] is False


def test_stage12_9_leakage_thresholds():
    thresholds = leakage_thresholds(0.3)
    assert thresholds["ratio20"] == 0.015
    assert thresholds["ratio30"] == 0.01
    assert thresholds["ratio50"] == 0.006


def test_stage12_9_ranking_prefers_real_leakage_cancellation():
    rows = [
        {"variant_id": "high_ratio", "variant_type": "planned", "hard_pass": False, "improves_over_stage12_8_best": False, "y_LP_target_plus1_leakage": 0.031, "target_order_selectivity_ratio": 12.6, "x_LP_target_plus1_power": 0.39},
        {"variant_id": "cancel", "variant_type": "planned", "hard_pass": False, "improves_over_stage12_8_best": True, "y_LP_target_plus1_leakage": 0.028, "target_order_selectivity_ratio": 12.4, "x_LP_target_plus1_power": 0.35},
    ]
    assert rank_stage12_9_rows(rows)[0]["variant_id"] == "cancel"
