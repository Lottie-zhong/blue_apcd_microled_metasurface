import importlib.util
from pathlib import Path

import numpy as np


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "diagnose_mdc_hf_surrogate_v2_failure_mechanism_fixed_v3_v1.py"
SPEC = importlib.util.spec_from_file_location("diag", SCRIPT)
diag = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diag)


def test_normalize_mass_and_profile_metrics_identity():
    a = np.arange(12, dtype=float).reshape(3, 4) + 1
    q = diag.normalize_mass(a)
    assert np.isclose(q.sum(), 1)
    metrics = diag.profile_metrics(q, q)
    assert all(abs(value) < 1e-14 for value in metrics.values())


def test_profile_metrics_detects_diversity():
    a = np.zeros((3, 4)); b = np.zeros((3, 4))
    a[0, 0] = 1; b[-1, -1] = 1
    metrics = diag.profile_metrics(a, b)
    assert np.isclose(metrics["joint_weighted_L1"], 2)
    assert metrics["joint_JS"] > 0.69
    assert metrics["spectral_CDF"] > 0
    assert metrics["angular_CDF"] > 0


def test_geometry_feature_matches_frozen_shape_and_scaling():
    families = [f"f{i}" for i in range(8)]
    mean = np.zeros(8); std = np.ones(8)
    feature = diag.geometry_feature("f3", 13, 904, 154, families, mean, std)
    assert feature.shape == (18,)
    assert feature[:8].sum() == 1
    assert feature[3] == 1
    assert np.all(feature[-2:] == 1)


def test_decision_contract_rules_are_predeclared_in_source():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "FROZEN_BEFORE_OUTCOME_READ" in text
    assert "at least 10/15 fits" in text
    assert "Spearman(distance-to-DOE96" in text
    assert "MDC_FIXED_V3_TARGETED_HF_EXPANSION_AND_RETRAINING_JUSTIFIED" in text


def test_safety_guards_have_zero_counters():
    text = SCRIPT.read_text(encoding="utf-8")
    for token in ["FDTD_calls\": 0", "TMM_calls\": 0", "RCWA_calls\": 0", "NP_solver_calls\": 0",
                  "neural_fits\": 0", "optimizer_calls\": 0", "backward_calls\": 0",
                  "PCA_fits\": 0", "scaler_fits\": 0", "HF15_reads\": 0", "sealed_reads\": 0"]:
        assert token in text
