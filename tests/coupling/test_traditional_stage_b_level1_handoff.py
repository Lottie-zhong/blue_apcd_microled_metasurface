"""Replay and contract tests for the traditional Stage-B Level-1 handoff."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts" / "coupling"
READINESS = ROOT / "outputs" / "mdc_np_coupling_v1" / "traditional_stage_b_level1_readiness_v1.json"


def load(name: str) -> dict:
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


def test_handoff_is_hard_gated_and_stage_a_identity_is_frozen():
    handoff = load("traditional_stage_b_level1_handoff_v1.json")
    assert handoff["status"] == "USER_DECISION_REQUIRED_LEVEL1_POLARIZATION_SCOPE"
    assert handoff["coupling_level"] == "ONE_WAY_INCOHERENT_POWER_COUPLING"
    stage_a = handoff["stage_a_baseline_immutable"]
    assert stage_a["mdc_candidate_id"] == "P1_ZL1_ALTERNATIVE_G3_A3"
    assert stage_a["extra_spacer_nm"] == 237
    assert stage_a["total_continuous_sio2_separation_nm"] == 316
    assert stage_a["matrix_rows"] == 110
    assert stage_a["matrix_sha256"] == "d400c51cfa557aeffdefb09567dbe20705c50d915bc9a5ddd570281535265bf6"
    assert stage_a["closure_head"] == "25e78936afca7387f71bda244545efed64cbe702"


def test_mdc_provider_requires_real_six_case_fdtd_and_excludes_surrogates():
    provider = load("level1_mdc_real_fdtd_provider_v1.json")
    assert provider["provider_status"] == "REQUIRES_DIRECT_SOLVER"
    assert provider["m1_surrogate_prohibited"] is True
    cases = {(c["position"], c["dipole"], c["source_z_nm"]) for c in provider["required_source_cases"]}
    assert cases == {
        ("top", "x", -171.5), ("top", "z", -171.5),
        ("centroid", "x", -276.0), ("centroid", "z", -276.0),
        ("bottom", "x", -380.5), ("bottom", "z", -380.5),
    }
    legacy = provider["existing_assets"]["legacy_zl1_x5"]
    assert legacy["formal_case_membership"] is False
    assert legacy["source_y_nm"] == -400
    assert legacy["positions_nm"] == [-1000.0, -500.0, 0.0, 500.0, 1000.0]
    assert provider["existing_assets"]["single_x_dipole_978nm_stack"]["formal_case_membership"] is False
    doe96 = provider["existing_assets"]["doe96_joint_database"]
    assert doe96["joint_tensor_shape"] == [301, 2000]
    assert doe96["z_l1_geometry_hash_match"] is False
    assert doe96["usable_as_zl1_formal_provider"] is False


def test_np_provider_is_partial_normal_x_only_and_stage_a_matrix_is_not_eta():
    provider = load("level1_np_response_provider_v1.json")
    assert provider["provider_status"] == "PARTIAL_EXISTING_ASSET"
    assert provider["formal_outcome"] == "NP_LEVEL1_PROVIDER_PARTIAL_NORMAL_X_ONLY"
    assert provider["existing_scope"]["wavelength_nm"] == list(range(445, 456))
    assert provider["existing_scope"]["u_x"] == [0.0]
    assert provider["existing_scope"]["polarization"] == ["x"]
    assert provider["existing_scope"]["stack"] == "SiO2 substrate -> Native-M1 TiO2 K6 pillars -> Air"
    assert provider["stage_a_integrated_matrix_is_not_eta_provider"] is True
    assert provider["missing_for_full_stage_a_target"]


def test_reference_plane_and_grid_contracts_are_explicit():
    ref = load("level1_reference_plane_mapping_v1.json")
    assert ref["mdc_reference_plane"]["z_nm"] == 975
    assert ref["np_reference_plane"]["id"] == "NP_PILLAR_BOTTOM"
    assert ref["np_reference_plane"]["incident_medium"] == "APCD_SIO2_NATIVE_M1"
    assert ref["np_reference_plane"]["output_medium"] == "Air"
    assert ref["conserved_variable"]["primary"] == "u_x=kx/k0"
    assert ref["conserved_variable"]["theta_air"] == "derived label only"
    assert ref["conserved_variable"]["no_internal_theta_substitution"] is True
    grid = load("level1_grid_alignment_v1.json")
    assert grid["status"] == "PARTIAL_ALIGNMENT_NO_EXTRAPOLATION"
    assert any("no interpolation or extrapolation" in rule for rule in grid["alignment_rules"])
    assert any("no spectrum-times-angular-cut outer product" in rule for rule in grid["alignment_rules"])
    assert grid["canonical_wavelength_nm"] == list(range(445, 456))
    assert grid["existing_np_ux"] == [0.0]


def test_polarization_mapping_is_not_inferred_and_quadrature_is_raw_first():
    mapping = load("level1_polarization_mapping_v1.json")
    assert mapping["status"] == "TRADITIONAL_STAGE_B_LEVEL1_POLARIZATION_MAPPING_RESOLVED"
    assert mapping["direct_mapping_allowed"] is True
    assert mapping["resolved_mappings"] == {"x_dipole": "P_XLIKE", "z_dipole": "S_YLIKE"}
    assert "x_dipole_to_S_YLIKE" in mapping["prohibited_mappings"]
    assert "z_dipole_to_P_XLIKE" in mapping["prohibited_mappings"]
    quadrature = load("level1_quadrature_contract_v1.json")
    assert quadrature["raw_first"] is True
    assert "same-position P_position=0.5*P_x+0.5*P_z" in quadrature["aggregation_order"]
    assert "geometry P_geometry=(P_top+P_centroid+P_bottom)/3" in quadrature["aggregation_order"]
    assert quadrature["case_normalize_before_average"] is False
    assert quadrature["numerical_consumption_allowed"] is False
    assert quadrature["status"] == "RESOLVED_NATIVE_TRAPEZOID_DENSITY_IN_LAMBDA_THETA"


def test_power_contract_is_one_way_and_does_not_claim_absolute_metrics():
    power = load("level1_power_contract_v1.json")
    assert power["raw_power_first"] is True
    assert power["formal_p_mdc"] == "P_MDC_up_FDTD"
    assert power["formal_provider_required"] is True
    assert "absolute LEE" in power["forbidden_labels"]
    assert "EQE" in power["forbidden_labels"]


def test_provider_statuses_budget_and_safety_are_replayable():
    allowed = {"READY_EXISTING_ASSET", "PARTIAL_EXISTING_ASSET", "REQUIRES_DIRECT_SOLVER", "BLOCKED_PHYSICS_MAPPING", "NOT_APPLICABLE"}
    handoff = load("traditional_stage_b_level1_handoff_v1.json")
    assert handoff["providers"]["mdc"]["provider_status"] in allowed
    assert handoff["providers"]["np"]["provider_status"] in allowed
    budget = handoff["solver_budget_plan"]
    assert budget["mdc_missing_formal_cases"] == 6
    assert budget["np_missing_full_stage_a_states"] == 9
    assert budget["current_turn_entries"] == 0
    assert "Stage-A integrated 110 rows" in budget["do_not_count"]
    assert "DOE96 576 historical solver calls" in budget["do_not_count"]
    assert handoff["future_ml_provider"]["inference_run"] is False
    assert handoff["future_ml_provider"]["status"] == "NOT_ACTIVATED_TRADITIONAL_STAGE_B"
    readiness = json.loads(READINESS.read_text(encoding="utf-8"))
    assert readiness["safety"]["this_turn_solver_entries"] == 0
    assert all(value == 0 for key, value in readiness["safety"].items() if key != "source_worktree_writes")


def test_fresh_process_replay_has_identical_readiness_bytes():
    payload = READINESS.read_bytes()
    expected = hashlib.sha256(payload).hexdigest()
    code = "from pathlib import Path; import hashlib; print(hashlib.sha256(Path(r'%s').read_bytes()).hexdigest())" % READINESS
    observed = subprocess.check_output([sys.executable, "-c", code], text=True).strip()
    assert observed == expected
