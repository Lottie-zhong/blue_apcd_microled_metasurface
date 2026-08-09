from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("lp_global_h_h0_audit", ROOT / "scripts/lp_global_h_h0_audit_v1.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_wrap_case_has_twenty_degree_coverage() -> None:
    result = MODULE.circular_phase_span([355.0, 5.0, 15.0])
    assert result["circular_coverage_deg"] == 20.0
    assert result["raw_min_deg"] == 5.0
    assert result["raw_max_deg"] == 355.0


def test_single_duplicate_and_zero_360_equivalence() -> None:
    assert MODULE.circular_phase_span([12.0])["circular_coverage_deg"] == 0.0
    assert MODULE.circular_phase_span([10.0, 10.0, 370.0])["circular_coverage_deg"] == 0.0
    assert MODULE.circular_phase_span([0.0, 360.0])["unique_wrapped_count"] == 1


def test_ordinary_and_out_of_range_values() -> None:
    assert MODULE.circular_phase_span([10.0, 20.0, 30.0])["circular_coverage_deg"] == 20.0
    assert MODULE.circular_phase_span([-5.0, 5.0, 365.0])["circular_coverage_deg"] == 10.0


def test_unified_h_contract_keeps_shared_height_and_fixed_planes() -> None:
    path = ROOT / "scripts/lp_ml_inverse_stage1_fdt_validation_runner_v1.py"
    runner = importlib.util.spec_from_file_location("lp_runner", path)
    module = importlib.util.module_from_spec(runner)
    assert runner and runner.loader
    runner.loader.exec_module(module)
    for height in (450.0, 500.0, 650.0):
        contract = module.unified_h_geometry_contract(height)
        assert contract["J1_H_nm"] == contract["J2_H_nm"] == height
        assert contract["bottom_plane_nm"] == 0.0
        assert contract["source_z_nm"] == -250.0
        assert contract["monitor_z_nm"] == 1000.0
        assert contract["period_x_nm"] == contract["period_y_nm"] == 432.0


def test_unified_h_contract_rejects_monitor_collision() -> None:
    path = ROOT / "scripts/lp_ml_inverse_stage1_fdt_validation_runner_v1.py"
    runner = importlib.util.spec_from_file_location("lp_runner_invalid", path)
    module = importlib.util.module_from_spec(runner)
    assert runner and runner.loader
    runner.loader.exec_module(module)
    try:
        module.unified_h_geometry_contract(1000.0)
    except ValueError:
        pass
    else:
        raise AssertionError("height at fixed monitor must be rejected")
