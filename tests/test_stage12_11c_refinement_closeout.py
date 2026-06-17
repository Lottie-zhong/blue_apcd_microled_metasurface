from metasurface.stage12_11c_refinement_closeout import BASELINE_METRICS, choose_official_baseline, classify_k6_replacement


def test_replacement_worthy_classification_rejects_small_gain():
    baseline = BASELINE_METRICS
    assert classify_k6_replacement(0.365, 0.0296, 12.32, baseline) is False


def test_replacement_worthy_classification_accepts_large_leakage_drop():
    baseline = BASELINE_METRICS
    assert classify_k6_replacement(0.31, 0.020, 15.5, baseline) is True


def test_official_baseline_selection_keeps_baseline_without_replacement():
    baseline = dict(BASELINE_METRICS)
    attempts = [{"stage": "Stage12-8", "replacement_worthy": False}, {"stage": "Stage12-11B", "replacement_worthy": False}]
    assert choose_official_baseline(attempts, baseline)["label"] == "official_x_gradient_baseline"


def test_official_baseline_selection_can_select_replacement():
    baseline = dict(BASELINE_METRICS)
    attempts = [{"stage": "Stage12-X", "replacement_worthy": True, "label": "replacement"}]
    assert choose_official_baseline(attempts, baseline)["stage"] == "Stage12-X"
