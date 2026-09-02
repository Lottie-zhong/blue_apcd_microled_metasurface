"""Synthetic regression tests for the read-only surrogate POC helpers."""
import importlib.util
from pathlib import Path
import numpy as np

SRC = Path(__file__).resolve().parents[1] / "scripts" / "mdc_surrogate_assisted_pareto_optimization_poc_v1.py"
spec = importlib.util.spec_from_file_location("poc", SRC)
poc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(poc)

def test_connected_fwhm_is_deterministic():
    x = np.arange(101, dtype=float)
    y = np.exp(-0.5 * ((x - 50.0) / 10.0) ** 2)
    a = poc.fwhm_connected(x, y)
    b = poc.fwhm_connected(x, y)
    assert np.isfinite(a) and a == b and 20.0 < a < 25.0

def test_pareto_mask_minimization():
    values = np.array([[1.0, 1.0], [2.0, 2.0], [1.0, 2.0], [2.0, 1.0]])
    mask = poc.pareto_mask(values)
    assert mask.tolist() == [True, False, False, False]

def test_feature_order_has_no_power_target():
    assert len(poc.FEATURE_ORDER) == 23
    assert not any("power" in x.lower() for x in poc.FEATURE_ORDER)

def test_source_case_matrix_is_six_fixed_cases():
    assert poc.SOURCE_CASES == (("top", "x"), ("top", "z"), ("centroid", "x"), ("centroid", "z"), ("bottom", "x"), ("bottom", "z"))
