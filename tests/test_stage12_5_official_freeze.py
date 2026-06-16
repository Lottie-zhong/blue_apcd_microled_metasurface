from __future__ import annotations

from metasurface.stage12_k6_official_freeze import classify_branch, choose_official_axis


def test_official_decision_prefers_x_when_x_passes_and_y_fails() -> None:
    assert classify_branch(11.65, True) == "PASS"
    assert classify_branch(1.98, True) == "STEERING_PASS_SELECTIVITY_FAIL"
    assert choose_official_axis(11.65, 1.98, True, False) == "x"


def test_official_decision_uses_ratio_only_when_both_have_same_pass_state() -> None:
    assert choose_official_axis(4.0, 5.0, False, False) == "y"
    assert choose_official_axis(8.0, 7.0, True, True) == "x"
