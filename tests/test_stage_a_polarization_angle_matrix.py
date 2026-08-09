from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from apcd_coupling.incident_state import IncidentState, air_angle_states, transversality_residual
from apcd_coupling.result_schema import validate_result
OUTPUT_ROOT = ROOT / "outputs/coupling/stage_a_polarization_angle_450_v1"
REPORT = ROOT / "reports/coupling/stage_a_polarization_angle_matrix_450_v1.json"
REGISTRY = ROOT / "registries/coupling/solver_budget_registry.json"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_angle_contract_and_real_kx_sign():
    p = IncidentState.from_air_angle(5.0, "P_XLIKE")
    m = IncidentState.from_air_angle(-5.0, "P_XLIKE")
    assert math.isclose(p.ux, math.sin(math.radians(5.0)))
    assert math.isclose(m.ux, -p.ux)
    assert p.real_kx == -m.real_kx
    assert p.uy == 0.0


def test_p_and_s_branches_are_distinct_and_transverse():
    p = IncidentState.from_air_angle(10.0, "P_XLIKE")
    s = IncidentState.from_air_angle(10.0, "S_YLIKE")
    assert p.polarization_angle_deg == 0.0
    assert s.polarization_angle_deg == 90.0
    assert p.linear_polarization == "x"
    assert s.linear_polarization == "y"
    assert transversality_residual(2.415 + 0.084j, p) < 1e-12
    assert transversality_residual(2.415 + 0.084j, s) < 1e-12


def test_setup_outputs_have_frozen_spacer_and_no_solver_entry_before_run():
    registry = read(REGISTRY)
    ids = registry["authorized_incident_state_case_order"]
    assert len(ids) == 9
    for case_id in ids:
        setup = read(OUTPUT_ROOT / case_id / "setup_manifest.json")
        assert setup["case"]["spacer_nm"] == 237.0
        assert setup["case"]["coordinates"]["total_sio2_separation_nm"] == 316.0
        assert setup["case"]["control_group"] == "POL_ANGLE_MATRIX"
        assert setup["setup_gate"]["pass"] is True
        assert setup["case"]["source_contract_id"] == "OBLIQUE_REAL_KX_SOURCE_CONTRACT_V1"


def test_all_new_results_validate_and_have_single_attempt():
    registry = read(REGISTRY)
    ids = registry["authorized_incident_state_case_order"]
    for case_id in ids:
        out = OUTPUT_ROOT / case_id
        result = read(out / "results/result.json")
        validate_result(result)
        assert result["no_polarization_averaging"] is True
        assert result["source_kx_contract"]["pass"] is True
        assert result["order_equation_audit"]["all_rows_pass"] is True
        assert result["sign_audit"]["pass"] is True
        assert len(list((out / "runtime").glob("attempt_*"))) == 1


def test_matrix_report_reuses_x0_and_has_5x2_rows():
    report = read(REPORT)
    assert report["decision"] == "POLARIZATION_ANGLE_450NM_MATRIX_VALIDATED"
    assert report["matrix_shape"]["rows"] == 10
    assert report["validation"]["x0_rerun"] is False
    assert report["validation"]["no_polarization_averaging"] is True
    assert report["x0_reuse"]["solver_reused"] is True
    assert len(report["matrix_rows"]) == 10
    assert sorted({row["theta_air_in_deg"] for row in report["matrix_rows"]}) == [-10.0, -5.0, 0.0, 5.0, 10.0]
    assert {row["polarization_branch"] for row in report["matrix_rows"]} == {"P_XLIKE", "S_YLIKE"}


def test_registry_counts_and_replay_gate():
    registry = read(REGISTRY)
    assert registry["budgets"]["FDTD"] == 12
    assert registry["entered_runs"] == 12
    assert registry["new_physical_cases_entered"] == 9
    assert registry["new_physical_cases_completed"] == 9
    assert registry["next_solver_requires_new_authorization"] is True
    assert registry["incident_state_entered_case_ids"] == registry["authorized_incident_state_case_order"]
    assert registry["incident_state_completed_case_ids"] == registry["authorized_incident_state_case_order"]


def test_state_hash_is_deterministic():
    a = air_angle_states()
    assert len(a) == 10
    assert a[0].sha256() == IncidentState.from_air_angle(-10.0, "P_XLIKE").sha256()
