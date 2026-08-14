import importlib.util
from pathlib import Path


PATH = Path(__file__).parents[1] / "scripts" / "lp_h1c0_audit_v1.py"
spec = importlib.util.spec_from_file_location("h1c0", PATH)
h1c0 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(h1c0)


def test_exact_frozen_grid_and_450_not_sole_acceptance():
    assert h1c0.GRID == [450.0, 450.5, 451.0, 451.5, 452.0, 452.5, 453.0, 453.5, 454.0]
    assert len(h1c0.GRID) != 1


def test_circular_phase_trajectory_and_relative_spacing():
    assert h1c0.circular_diff(1.0, 359.0) == 2.0
    assert abs(h1c0.circular_coverage([355.0, 5.0, 15.0]) - 20.0) < 1e-12
    assert h1c0.relative_phase_spacing([[10.0], [70.0], [130.0]]) == [60.0, 60.0]


def test_phi0_lambda_is_free_and_spacing_is_circular():
    phases = [[350.0, 355.0], [50.0, 55.0], [110.0, 115.0]]
    assert h1c0.common_offset_error(phases, [0, 1, 2]) == 0.0


def test_c_seed_is_not_promoted_from_450_nm_only():
    text = PATH.read_text(encoding="utf-8")
    assert "GLOBAL_SIX_BIN_CANDIDATE_SEED" in text
    assert "BROADBAND_SIX_BIN_CANDIDATE_PENDING_AUDIT" in text


def test_zero_solver_and_no_entered_replay_in_source():
    text = PATH.read_text(encoding="utf-8")
    assert "lumapi" not in text
    assert ".run(" not in text
    assert "solver_replay" in text
    assert "entered_replay_forbidden" in text
