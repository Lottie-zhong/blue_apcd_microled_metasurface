from metasurface.stage12_8_xgrad_refinement import classify_pass, enforce_candidate_limit, validate_same_bin_substitution, metric_ratio

def test_stage12_8_pass_classification():
    row={"x_LP_target_plus1_power":0.31,"y_LP_target_plus1_leakage":0.009,"target_order_selectivity_ratio":34,"steering_angle_deg":10.1,"x_LP_dominant_order":"+1","geometry_legal":True}
    c=classify_pass(row)
    assert c["hard_pass"] is True and c["preferred_pass"] is True and c["stretch_pass"] is False

def test_stage12_8_metric_ratio():
    assert metric_ratio(0.3,0.03)==10

def test_stage12_8_candidate_limit_keeps_baseline_plus_eight():
    variants=[{"variant_id":"variant_000_baseline"}]+[{"variant_id":f"v{i}"} for i in range(20)]
    assert len(enforce_candidate_limit(variants,8))==9

def test_stage12_8_same_bin_rule():
    assert validate_same_bin_substitution(240,{"bin_deg":"240"}) is True
    assert validate_same_bin_substitution(240,{"bin_deg":"180"}) is False
