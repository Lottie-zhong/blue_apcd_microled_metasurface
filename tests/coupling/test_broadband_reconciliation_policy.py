from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GRID = [float(x) for x in range(445, 456)]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_missing_tolerance_is_diagnostic_not_post_hoc_pass_fail():
    policy = load("contracts/coupling/stage_a_broadband_selection_policy_v1.json")
    reconciliation = load(
        "outputs/coupling/stage_a_nb_t79_445_455_xpol_normal_v1/results/reconciliation_450nm.json"
    )
    assert policy["reconciliation_mode"] == "CROSS_ACQUISITION_CONTRACT_DIAGNOSTIC"
    assert policy["formal_numerical_tolerance"] is None
    assert policy["post_hoc_tolerance_creation"] is False
    assert reconciliation["decision"] == "MEASURED_NO_FORMAL_TOLERANCE"
    assert reconciliation["formal_numerical_tolerance"] is None
    assert reconciliation["hard_gate"] is None


def test_monochromatic_reference_is_excluded_from_broadband_score():
    policy = load("contracts/coupling/stage_a_broadband_selection_policy_v1.json")
    reconciliation = load(
        "outputs/coupling/stage_a_nb_t79_445_455_xpol_normal_v1/results/reconciliation_450nm.json"
    )
    assert policy["monochromatic_reference_role"] == "DIAGNOSTIC_ONLY"
    assert policy["broadband_ranking_basis"] == "WITHIN_BROADBAND_CONTRACT_ONLY"
    assert reconciliation["monochromatic_reference_role"] == "DIAGNOSTIC_ONLY"
    assert reconciliation["broadband_ranking_basis"] == "WITHIN_BROADBAND_CONTRACT_ONLY"
    assert reconciliation["broadband_ranking_blocked_by_missing_tolerance"] is False


def test_broadband_ranking_policy_is_same_contract_and_frozen():
    policy = load("contracts/coupling/stage_a_broadband_selection_policy_v1.json")
    assert policy["status"] == "FROZEN_BEFORE_BROADBAND_RESULTS"
    assert policy["scope"]["cases"] == ["NB_T0", "NB_T79", "NB_T237"]
    assert policy["scope"]["wavelength_grid_nm"] == GRID
    assert policy["primary_metric"] == "mean_eta_plus1_445_455"
    assert policy["ranking_order"][:4] == [
        "higher_mean_eta_plus1",
        "higher_min_eta_plus1",
        "lower_eta_plus1_std",
        "higher_mean_directionality",
    ]
    assert "mean_eta_plus1" not in json.dumps(
        load("outputs/coupling/stage_a_nb_t79_445_455_xpol_normal_v1/results/reconciliation_450nm.json")
    ).split("broadband_ranking_basis")[0]


def test_physical_contract_same_acquisition_contract_different():
    reconciliation = load(
        "outputs/coupling/stage_a_nb_t79_445_455_xpol_normal_v1/results/reconciliation_450nm.json"
    )
    physical = reconciliation["physical_contract"]
    acquisition = reconciliation["acquisition_contract"]
    assert physical["same"] is True
    assert acquisition["same"] is False
    assert physical["groups"]["normalization"]["definition"] == "power_fraction_of_source"
    assert physical["groups"]["normalization"]["same"] is True
    assert physical["groups"]["monitor_physical_contract"]["reference_medium"]["match"] is True
    assert physical["groups"]["order_sign"]["both_pass"] is True
    assert any("spectral range" in item for item in acquisition["differences"])


def test_exact_450_diagnostic_and_relative_deltas():
    result = load(
        "outputs/coupling/stage_a_nb_t79_445_455_xpol_normal_v1/results/result.json"
    )
    row = [row for row in result["rows"] if row["wavelength_nm"] == 450.0]
    reconciliation = load(
        "outputs/coupling/stage_a_nb_t79_445_455_xpol_normal_v1/results/reconciliation_450nm.json"
    )
    assert len(row) == 1
    assert result["wavelength_grid_nm"] == GRID
    assert reconciliation["wavelength_nm"] == 450.0
    assert reconciliation["metrics"]["eta_plus1"]["absolute_delta_broadband_minus_monochromatic"] == -0.002519630609211343
    assert reconciliation["metrics"]["eta_plus1"]["relative_delta_over_abs_monochromatic"] < 0


def test_provenance_replay_and_no_interpolation():
    result = load(
        "outputs/coupling/stage_a_nb_t79_445_455_xpol_normal_v1/results/result.json"
    )
    manifest = load(
        "outputs/coupling/stage_a_nb_t79_445_455_xpol_normal_v1/results/extraction_manifest.json"
    )
    assert manifest["exact_grid"] == GRID
    assert manifest["readonly_session"] is True
    assert manifest["run_called"] is False
    assert manifest["save_called"] is False
    assert manifest["interpolation"] is False
    assert manifest["extrapolation"] is False
    assert result["standalone_reference"]["exact_grid"] is True
    assert result["standalone_reference"]["interpolation"] is False
    assert result["standalone_reference"]["extrapolation"] is False


def test_policy_freeze_requires_new_authorization_before_remaining_solver():
    contract = load("contracts/coupling/stage_a_direct_fullwave_contract_v1.json")
    budget = load("registries/coupling/solver_budget_registry.json")
    runner = (ROOT / "scripts/coupling/run_control_group_case.py").read_text(encoding="utf-8")
    assert contract["status"] == "BROADBAND_RECONCILIATION_POLICY_FROZEN_DIAGNOSTIC_ONLY"
    assert contract["solver_authorized"] is False
    assert contract["next_authorization_action"] == "REQUEST_REMAINING_NB_T237_T0_EXECUTION_AUTHORIZATION"
    assert budget["next_solver_requires_new_authorization"] is True
    assert "broadband solver execution requires new authorization" in runner
    assert budget["entered_case_ids"] == ["STAGE_A_NB_T79_445_455NM_X_UX0"]
    assert budget["completed_case_ids"] == budget["entered_case_ids"]