from metasurface.stage12_12a2_narrow_window_acceptance import recommend_window, weighted_metrics, window_metrics


def row(w, b, ratio, leak=0.01):
    return {"wavelength_nm": str(w), "bin_deg": str(b), "conversion_to_leakage_ratio": str(ratio), "blocked_y_total_leakage": str(leak)}


def step(w, rms=10, mx=20):
    return {"wavelength_nm": str(w), "rms_phase_step_error_deg": str(rms), "max_phase_step_error_deg": str(mx)}


def test_window_filtering_and_recommendation_picks_450_only_when_451_collapses():
    results = []
    for w in [449, 450, 451]:
        for b in [0, 60, 120, 180, 240, 300]:
            results.append(row(w, b, 8 if not (w == 451 and b == 240) else 3))
    metrics = window_metrics(results, [step(449), step(450), step(451)])
    assert next(r for r in metrics if r["window_nm"] == "449-451")["acceptable"] is False
    assert recommend_window(metrics)["window_nm"] == "449-450"


def test_weighted_metrics_normalize_and_detect_tail():
    results = []
    for w in [447, 448, 449, 450, 451, 452, 453]:
        for b in [0, 60, 120, 180, 240, 300]:
            results.append(row(w, b, 10, 1.0 if w >= 451 and b == 300 else 0.01))
    weighted = weighted_metrics(results)
    f6 = next(r for r in weighted if r["fwhm_nm"] == 6)
    assert 0 <= f6["long_wavelength_leakage_contribution_451_453"] <= 1
    assert f6["long_wavelength_tail_dominates_failure"] is True


def test_weakest_bin_detection_in_window_metrics():
    results = []
    for w in [450]:
        for b in [0, 60, 120, 180, 240, 300]:
            results.append(row(w, b, 7 if b == 240 else 20))
    metrics = window_metrics(results, [step(450)])
    m450 = next(r for r in metrics if r["window_nm"] == "450")
    assert m450["weakest_bin"] == 240
    assert m450["acceptable"] is True
