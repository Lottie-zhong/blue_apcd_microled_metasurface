from metasurface.stage12_11a_phase_origin_search import (
    construct_tuple,
    delta_target_phases,
    phase_distance_deg,
    recommendation,
    score_tuple,
)


def test_phase_wrap_distance():
    assert phase_distance_deg(358, 2) == 4
    assert phase_distance_deg(-52, 300) == 8


def test_delta_target_phase_generation():
    assert delta_target_phases(58) == [58.0, 118.0, 178.0, 238.0, 298.0, 358.0]


def test_tuple_construction_prefers_within_tolerance():
    pool = []
    for i, phase in enumerate([2, 62, 122, 182, 242, 302]):
        pool.append({"candidate_id": f"c{i}", "phase_mod_360_deg": phase, "ratio": 10+i, "Tx": 0.8, "matrix_error": 0.2, "leakage": 0.05, "geometry_family": "x_pair_swap"})
    chosen, mode = construct_tuple(pool, 0)
    assert len(chosen) == 6
    assert mode == "preferred"


def test_scoring_and_recommendation_logic():
    official = {"min_ratio": 10, "max_estimated_leakage": 0.1, "tuple_score": 20}
    best = {"min_ratio": 16, "max_estimated_leakage": 0.08, "tuple_score": 22}
    assert recommendation(best, official) is True


def test_score_tuple_orders_good_tuple_higher():
    good = [{"ratio": 20, "Tx": 0.9, "matrix_error": 0.2, "phase_error_deg": 2, "estimated_leakage": 0.04, "geometry_family": "a", "candidate_id": str(i)} for i in range(6)]
    bad = [{"ratio": 6, "Tx": 0.55, "matrix_error": 0.5, "phase_error_deg": 12, "estimated_leakage": 0.1, "geometry_family": "a", "candidate_id": str(i)} for i in range(6)]
    assert score_tuple(good, 0, "preferred")["tuple_score"] > score_tuple(bad, 0, "relaxed")["tuple_score"]