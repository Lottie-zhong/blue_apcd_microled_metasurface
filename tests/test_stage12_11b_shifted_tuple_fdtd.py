from pathlib import Path
from metasurface.stage12_11b_shifted_tuple_fdtd import BASELINE, build_run_matrix, compute_metrics, expected_theta_deg, load_best_tuple, replacement_decision

def test_load_best_tuple_validates_delta_sequence(tmp_path: Path):
    path = tmp_path / "best.csv"
    path.write_text("slot_index,target_phase_deg,candidate_id,geometry_family,phase_mod_360_deg,phase_error_deg,Tx,leakage,ratio,matrix_error,estimated_leakage,tolerance_mode,source_file\n" + "\n".join(f"{i},{1+60*i},c{i},x_pair,{1+60*i},1,0.8,0.04,20,0.2,0.04,preferred,source.csv" for i in range(6)) + "\n", encoding="utf-8")
    rows = load_best_tuple(path)
    assert [row["candidate_id"] for row in rows] == [f"c{i}" for i in range(6)]

def test_run_matrix_preserves_x_gradient_target():
    rows = build_run_matrix([{"lambda_nm": "450", "supercell_period_lambda_nm": "2592"}])
    assert len(rows) == 2
    assert {row["polarization"] for row in rows} == {"x", "y"}
    assert all(row["gradient_axis"] == "x" for row in rows)
    assert all(row["target_order"] == "x-order +1" for row in rows)
    assert abs(float(rows[0]["expected_theta_deg"]) - expected_theta_deg(450, 2592)) < 1e-12

def test_metric_calculation_and_replacement_decision():
    x_result = {"target_plus1_power": 0.36, "total_transmission": 0.5, "dominant_theta_deg": 10.0, "dominant_order_n": 1, "order_contrast_plus1_vs_next": 4.0}
    y_result = {"target_plus1_power": 0.02, "total_transmission": 0.6, "dominant_order_n": 2}
    metrics = compute_metrics(x_result, y_result, [], [], {"geometry_legal": True, "minimum_clearance_nm": 20, "minimum_neighbor_clearance_nm": 80})
    assert metrics["target_order_selectivity_ratio"] == 18
    decision = replacement_decision(metrics)
    assert decision["replacement_worthy"] is True
    assert decision["hard_preferred_target_met"] is False

def test_replacement_decision_rejects_modest_gain():
    metrics = {"x_LP_target_plus1_power": BASELINE["x_LP_target_plus1_power"], "y_LP_target_plus1_leakage": 0.029, "target_order_selectivity_ratio": 12.3}
    assert replacement_decision(metrics)["replacement_worthy"] is False

def test_replacement_decision_ratio_25pct_path():
    metrics = {"x_LP_target_plus1_power": 0.34, "y_LP_target_plus1_leakage": 0.022, "target_order_selectivity_ratio": BASELINE["target_order_selectivity_ratio"] * 1.26}
    assert replacement_decision(metrics)["criterion_ratio_improves_ge25pct"] is True
