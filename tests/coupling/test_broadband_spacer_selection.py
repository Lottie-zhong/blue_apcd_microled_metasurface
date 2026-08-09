from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRID = [float(x) for x in range(445, 456)]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_three_candidate_broadband_selection_is_frozen():
    artifact = load("reports/coupling/stage_a_broadband_spacer_selection_v1.json")
    assert artifact["selection"]["status"] == "FINAL_SPACER_FREEZE_FOR_STAGE_A_XPOL_NORMAL"
    assert artifact["selection"]["winner_control_group"] == "NB_T237"
    assert artifact["selection"]["frozen_spacer_nm"] == 237
    assert artifact["selection"]["frozen_total_sio2_separation_nm"] == 316.0
    assert [row["label"] for row in artifact["candidates"]] == ["T237", "T79", "T0"]


def test_broadband_score_uses_exact_grid_and_no_mono_values():
    artifact = load("reports/coupling/stage_a_broadband_spacer_selection_v1.json")
    assert artifact["scope"]["wavelength_grid_nm"] == GRID
    assert artifact["selection_policy"]["monochromatic_values_used_for_score"] is False
    assert artifact["selection_policy"]["interpolation_used"] is False
    assert artifact["selection_policy"]["extrapolation_used"] is False
    assert len(artifact["spectra"]) == 33
    assert all(row["wavelength_nm"] in GRID for row in artifact["spectra"])
    assert all(row["order_closure_pass"] and row["power_closure_pass"] for row in artifact["spectra"])
    assert all(row["sign_pass"] and row["m_plus_1_physical_kx_sign"] == "+x" for row in artifact["spectra"])


def test_t237_broadband_metrics_are_a_clear_winner():
    artifact = load("reports/coupling/stage_a_broadband_spacer_selection_v1.json")
    summaries = {row["label"]: row["summary"] for row in artifact["candidates"]}
    assert summaries["T237"]["mean_eta_plus1_445_455"] > summaries["T79"]["mean_eta_plus1_445_455"] > summaries["T0"]["mean_eta_plus1_445_455"]
    assert summaries["T237"]["min_eta_plus1_445_455"] > summaries["T79"]["min_eta_plus1_445_455"] > summaries["T0"]["min_eta_plus1_445_455"]
    assert summaries["T237"]["eta_plus1_std_445_455"] < summaries["T79"]["eta_plus1_std_445_455"]
    assert summaries["T237"]["eta_plus1_at_450_nm"] == 0.376202552031929


def test_historical_t0_joint_hash_difference_is_diagnostic_only():
    reconciliation = load(
        "outputs/coupling/stage_a_nb_t0_445_455_xpol_normal_v1/reconciliation_450nm.json"
    )
    identity = reconciliation["physical_contract"]["groups"]["candidate_and_geometry"]
    assert reconciliation["decision"] == "MEASURED_NO_FORMAL_TOLERANCE"
    assert reconciliation["physical_contract"]["same"] is True
    assert identity["joint_geometry_hash"]["diagnostic_only"] is True
    assert identity["physical_object_geometry"]["same"] is True


def test_freeze_locks_future_solver_replay_and_declares_interface_provider():
    contract = load("contracts/coupling/stage_a_direct_fullwave_contract_v1.json")
    budget = load("registries/coupling/solver_budget_registry.json")
    interface = load("contracts/coupling/interface_stack_v1.json")
    runner = (ROOT / "scripts/coupling/run_control_group_case.py").read_text(encoding="utf-8")
    assert contract["solver_authorized"] is False
    assert contract["next_solver_requires_new_authorization"] is True
    assert budget["status"] == "FINAL_SPACER_FREEZE_FOR_STAGE_A_XPOL_NORMAL"
    assert budget["entered_case_ids"] == [
        "STAGE_A_NB_T79_445_455NM_X_UX0",
        "STAGE_A_NB_T237_445_455NM_X_UX0",
        "STAGE_A_NB_T0_445_455NM_X_UX0",
    ]
    assert "FINAL_SPACER_FREEZE_FOR_STAGE_A_XPOL_NORMAL" in runner
    assert interface["status"] == "STAGE_A_XPOL_NORMAL_SPACER_FROZEN"
    assert interface["stack"][2]["thickness_nm"] == 237
    assert interface["total_sio2_separation_nm"] == 316
