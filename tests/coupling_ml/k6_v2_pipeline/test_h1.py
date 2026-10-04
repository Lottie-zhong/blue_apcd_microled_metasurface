import numpy as np
from scripts.coupling_ml.k6_v2_pipeline.h1 import (
    evaluate_original_h1, load_h2_decoder, reconstruct_h2,
)

def test_frozen_h2_h1_identity_and_physical_pscale_seed_mean():
    rng = np.random.default_rng(17)
    c = rng.normal(size=(4, 21, 7, 2)) + 1j * rng.normal(size=(4, 21, 7, 2))
    p = np.stack([0.7 + 0.03 * i + 0.001 * np.arange(21) for i in range(4)])
    decoder = load_h2_decoder()
    truth = reconstruct_h2(c, p, decoder)
    p_by_seed = np.stack([0.8 * p, p, 1.2 * p])
    result = evaluate_original_h1(
        c, np.stack([c, c, c]), p, p_by_seed,
        truth["eta"], truth["absolute_order"], decoder,
    )
    assert result["aggregate"]["metrics"]["state_relative_rmse"]["max"] < 1e-15
    assert result["aggregate"]["metrics"]["total_power_relative_rmse"]["max"] < 1e-14
    assert result["all_applicable_numeric_gates_attained"]
    assert result["seed_stability_status"] == "PASS"
    assert result["production_admission"] is False
