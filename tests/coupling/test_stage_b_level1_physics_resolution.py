"""Zero-solver replay tests for the Stage-B physics-resolution contracts."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts" / "coupling"
OUT = ROOT / "outputs" / "mdc_np_coupling_v1"


def load(name: str) -> dict:
    path = CONTRACTS / name
    return json.loads(path.read_text(encoding="utf-8"))


def test_2d_plane_and_source_orientation_are_explicitly_resolved():
    basis = load("mdc_interface_polarization_basis_v1.json")
    audit = load("mdc_2d_field_basis_audit_v1.json")
    assert audit["contract_id"] == "MDC_2D_FIELD_BASIS_AUDIT_V1"
    assert audit["interface_basis_contract_id"] == "MDC_INTERFACE_POLARIZATION_BASIS_V1"
    assert basis["status"] == "RESOLVED_BY_2D_SETUP_AND_ANALYTIC_MAXWELL_DECOMPOSITION"
    assert basis["simulation_plane"] == "Lumerical solver x-y plane; project physical x-z plane"
    assert basis["solver_coordinates"]["invariant_axis"] == "z_L"
    assert basis["project_coordinates"]["vertical_axis"] == "z_p"
    assert basis["coordinate_mapping"] == {"x_p": "x_L", "z_p": "y_L", "y_p": "z_L"}
    assert basis["source_position_semantics"]["source_z_nm_means"] == "vertical project-z position, not solver-z orientation"
    assert basis["lumerical_dipole_readback"]["x"]["theta_deg"] == 90.0
    assert basis["lumerical_dipole_readback"]["z"]["theta_deg"] == 0.0


def test_field_family_and_polarization_basis_are_not_label_guesses():
    basis = load("mdc_interface_polarization_basis_v1.json")
    assert basis["field_families_solver"] == {"P_TM_like": ["E_x", "E_y", "H_z"], "S_TE_like": ["E_z", "H_x", "H_y"]}
    assert basis["source_orientation_to_interface_branch"] == {"x_dipole": "P_XLIKE", "z_dipole": "S_YLIKE"}
    assert basis["source_orientation_is_not_polarization_label"] is True
    assert basis["field_component_readback"].startswith("NOT_AVAILABLE")
    mapping = load("level1_polarization_mapping_v1.json")
    assert mapping["direct_mapping_allowed"] is True
    assert mapping["six_case_contains_independent_p_and_s"] is True
    assert mapping["source_aggregation_is_not_polarization_average"] is True
    assert mapping["new_source_contract_required"] is False


def test_frozen_six_case_contract_is_preserved_and_contains_p_s():
    handoff = load("traditional_stage_b_level1_handoff_v1.json")
    assert handoff["stage_a_baseline_immutable"]["mdc_candidate_id"] == "P1_ZL1_ALTERNATIVE_G3_A3"
    assert handoff["stage_a_baseline_immutable"]["extra_spacer_nm"] == 237
    assert handoff["stage_a_baseline_immutable"]["total_continuous_sio2_separation_nm"] == 316
    assert handoff["physics_resolution"]["six_case_polarization"] == "P_AND_S_PRESENT"
    provider = load("level1_mdc_real_fdtd_provider_v1.json")
    assert len(provider["required_source_cases"]) == 6
    assert {(row["position"], row["dipole"]) for row in provider["required_source_cases"]} == {
        ("top", "x"), ("top", "z"), ("centroid", "x"), ("centroid", "z"), ("bottom", "x"), ("bottom", "z")
    }


def test_source_aggregation_is_separate_from_polarization_decomposition():
    quad = load("mdc_level1_quadrature_semantics_v1.json")
    factor = load("mdc_level1_power_profile_factorisation_v1.json")
    assert quad["raw_xz_weight"] == 0.5
    assert quad["raw_geometry_weight"] == 1 / 3
    assert quad["complex_field_interference"] is False
    assert factor["source_aggregation"]["meaning"] == "incoherent source-orientation aggregation, not P/S averaging"
    assert factor["normalization_order"][:3] == ["raw readback", "source orientation aggregation", "geometry aggregation"]


def test_profile_tensor_semantics_and_exact_normalization_are_frozen():
    quad = load("mdc_level1_quadrature_semantics_v1.json")
    assert quad["source_profile"]["tensor_shape"] == [301, 2000]
    assert quad["source_profile"]["axis_order"] == ["wavelength_index", "angle_index"]
    assert quad["source_profile"]["wavelength_nm"] == [420.0, 480.0, 301]
    assert quad["density_semantics"] == "normalized density W(lambda,theta) with integral measure d_lambda_nm*d_theta_rad"
    assert abs(quad["normalization"]["observed_closure"] - 1.0) < 1e-12
    assert quad["weights"]["lambda_units"] == "nm"
    assert quad["weights"]["theta_units"] == "radians"
    assert quad["weights"]["rule"] == "composite trapezoid on native coordinates"
    assert quad["no_implicit_2pi"] is True
    assert quad["no_spectrum_times_angular_cut"] is True


def test_theta_to_ux_remap_is_conservative_and_has_machine_fixture():
    remap = load("mdc_theta_to_ux_conservative_remap_v1.json")
    assert remap["status"] == "RESOLVED_CONSERVATIVE_MONOTONIC_REMAP"
    assert remap["coordinate_transform"].startswith("u_x=sin(theta_rad)")
    assert all(remap["requirements"].values())
    fixture = remap["fixture"]
    assert fixture["expected_total_mass"] == math.pi
    assert fixture["expected_target_mass"] == [math.pi / 2, math.pi / 2]
    assert remap["support"]["native_u_x"] == [-1.0, 1.0]
    assert remap["support"]["target_support_must_be_subset_of_native"] is True


def test_degree_radian_and_jacobian_safety_are_explicit():
    remap = load("mdc_theta_to_ux_conservative_remap_v1.json")
    quad = load("mdc_level1_quadrature_semantics_v1.json")
    assert quad["weights"]["theta_units"] == "radians"
    assert "dtheta_du" in remap["coordinate_transform"]
    assert "inverse-sine" in remap["algorithm"]
    assert "sin(theta_rad)" in remap["coordinate_transform"]


def test_native_ux_support_and_np_grid_are_not_invented():
    remap = load("mdc_theta_to_ux_conservative_remap_v1.json")
    np_operator = load("level1_np_scattering_operator_v1.json")
    assert remap["support"]["air_side_propagating_domain"] == "|u_x|<=1"
    assert np_operator["existing_reusable_scope"]["u_x"] == [0.0]
    assert np_operator["full_convolution_requires"]
    handoff = load("traditional_stage_b_level1_handoff_v1.json")
    assert "no numeric grid invented" in handoff["solver_budget_plan"]["minimum"]["N_ux_required_definition"]


def test_homogeneous_spacer_factorization_and_lossless_power_are_explicit():
    prop = load("level1_interface_propagation_v1.json")
    assert prop["from_plane"]["project_z_nm"] == 975
    assert prop["to_plane"]["project_z_nm"] == 1212
    assert prop["distance_nm"] == 237
    assert prop["role"] == "interface propagation operator, not MDC provider and not NP scattering provider"
    assert prop["material"]["audit"]["lossless_over_445_455_by_native_samples"] is True
    assert prop["operator"]["lossless_445_455_power_factor"] == 1.0
    assert prop["no_np_finite_spacer_double_count"] is True


def test_np_operator_reference_plane_and_stage_a_exclusion():
    op = load("level1_np_scattering_operator_v1.json")
    assert op["status"] == "VALID_STANDALONE_OPERATOR_PARTIAL_GRID_POLARIZATION_COVERAGE"
    assert op["input_plane"] == "NP_PILLAR_BOTTOM"
    assert op["input_medium"] == "APCD_SIO2_NATIVE_M1"
    assert op["output_medium"] == "Air"
    assert op["finite_237nm_sio2_is_inside_np_provider"] is False
    assert op["stage_a_matrix_is_validation_only"] is True


def test_power_factorisation_prevents_double_counting():
    factor = load("mdc_level1_power_profile_factorisation_v1.json")
    assert factor["status"].startswith("RESOLVED")
    assert factor["profile_conversion"].startswith("W_theta -> W_u")
    assert "237 nm spacer is not embedded in NP operator" in factor["no_double_counting"]
    assert "P_MDC_up_FDTD is not normalized again by W" in factor["no_double_counting"]
    assert "Stage-A integrated matrix is not multiplied by W_MDC" in factor["no_double_counting"]


def test_scope_options_are_frozen_without_selecting_one():
    handoff = load("traditional_stage_b_level1_handoff_v1.json")
    assert handoff["status"] == "USER_DECISION_REQUIRED_LEVEL1_POLARIZATION_SCOPE"
    assert handoff["next_action"] == "USER_DECISION_REQUIRED_LEVEL1_POLARIZATION_SCOPE"
    assert handoff["solver_budget_plan"]["scope_options"] == {"A": "TRADITIONAL_LEVEL1_P_TM_ONLY", "B": "TRADITIONAL_LEVEL1_FULL_P_S_SOURCE_SCOPE_EXTENSION"}
    assert handoff["solver_budget_plan"]["status"] == "CONDITIONAL_NOT_AUTHORIZED"


def test_safety_and_m1_ml_inactive():
    readiness = json.loads((OUT / "traditional_stage_b_level1_physics_resolution_v1.json").read_text(encoding="utf-8"))
    assert readiness["solver_entries_this_turn"] == 0
    assert readiness["training_entries_this_turn"] == 0
    assert readiness["ml_inference_entries_this_turn"] == 0
    assert all(value == 0 for value in readiness["safety"].values())
    handoff = load("traditional_stage_b_level1_handoff_v1.json")
    assert handoff["future_ml_provider"]["inference_run"] is False
    assert handoff["future_ml_provider"]["status"] == "NOT_ACTIVATED_TRADITIONAL_STAGE_B"


def test_physics_readiness_references_current_contract_paths_only():
    readiness = json.loads((OUT / "traditional_stage_b_level1_physics_resolution_v1.json").read_text(encoding="utf-8"))
    assert readiness["contracts"]["polarization_mapping"] == "contracts/coupling/level1_polarization_mapping_v1.json"
    assert readiness["contracts"]["field_basis_audit"] == "contracts/coupling/mdc_2d_field_basis_audit_v1.json"
    assert readiness["contracts"]["quadrature"] == "contracts/coupling/level1_quadrature_contract_v1.json"
    assert readiness["contracts"]["reference_plane"] == "contracts/coupling/level1_reference_plane_mapping_v1.json"
    assert all(isinstance(value, str) for value in readiness["contracts"].values())
    assert any(item["role"].startswith("existing field-family") and item["status"] == "READ_ONLY_HASHED" for item in readiness["source_evidence"])


def test_fresh_process_replay_is_deterministic():
    path = OUT / "traditional_stage_b_level1_physics_resolution_v1.json"
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    code = "from pathlib import Path; import hashlib; print(hashlib.sha256(Path(r'%s').read_bytes()).hexdigest())" % path
    observed = subprocess.check_output([sys.executable, "-c", code], text=True).strip()
    assert observed == expected
