"""Freeze the zero-solver Stage-B Level-1 physics resolution contracts."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
MDC_SOURCE = Path(r"D:\project\worktrees\blue_apcd_mdc_defect_450")
HF_SOURCE = Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2")
RUN = HF_SOURCE / "outputs" / "mdc_hf_surrogate_v2_doe96_joint_profile_database_v1" / "20260803T_doe96_joint_profile_6b6d7e2"
MDC_RUNTIME = MDC_SOURCE / "runtime" / "mdc_zl1_alternative_dipole_x5_incoherent_output_448_452_v1"
COUPLING = ROOT / "contracts" / "coupling"
REPORTS = ROOT / "reports" / "coupling"
OUT = ROOT / "outputs" / "mdc_np_coupling_v1"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git_head(path: Path) -> str:
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def evidence(path: Path, role: str, required: bool = True) -> dict[str, Any]:
    item: dict[str, Any] = {"path": str(path), "role": role, "required": required}
    if path.exists():
        item.update({"status": "READ_ONLY_HASHED", "sha256": sha256(path)})
    else:
        item.update({"status": "MISSING", "sha256": ""})
        if required:
            raise FileNotFoundError(path)
    return item


def trapz_weights(x: np.ndarray) -> np.ndarray:
    if x.ndim != 1 or len(x) < 2 or not np.all(np.diff(x) > 0):
        raise ValueError("quadrature_coordinate_must_be_strictly_increasing")
    w = np.empty_like(x, dtype=float)
    w[0] = 0.5 * (x[1] - x[0])
    w[-1] = 0.5 * (x[-1] - x[-2])
    w[1:-1] = 0.5 * (x[2:] - x[:-2])
    return w


def material_audit(path: Path) -> dict[str, Any]:
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    sio = [r for r in rows if r.get("material_name") == "sio222"]
    bracket = [r for r in sio if 400.0 <= float(r["wavelength_nm"]) <= 500.0]
    focus = [r for r in sio if 442.0 <= float(r["wavelength_nm"]) <= 460.0]
    return {
        "material_name": "sio222",
        "sample_count_total": len(sio),
        "sample_count_400_500_nm": len(bracket),
        "focus_samples_442_460_nm": [
            {"wavelength_nm": float(r["wavelength_nm"]), "n_real": float(r["n_real"]), "k_imag": float(r["k_imag"])}
            for r in focus
        ],
        "epsilon_imag_max_400_500_nm": max(float(r["epsilon_imag"]) for r in bracket),
        "k_imag_max_400_500_nm": max(float(r["k_imag"]) for r in bracket),
        "lossless_over_445_455_by_native_samples": all(float(r["k_imag"]) == 0.0 for r in bracket),
        "interpolation_rule": "linear complex epsilon versus frequency within native range; no extrapolation",
    }


def main() -> None:
    stage_a = load_json(COUPLING / "traditional_stage_a_baseline_lock_v1.json")
    identity = stage_a["physical_identity"]
    if identity["mdc_candidate_id"] != "P1_ZL1_ALTERNATIVE_G3_A3":
        raise AssertionError("stage_a_mdc_identity_changed")
    if identity["mdc_total_thickness_nm"] != 975 or identity["mdc_top_sio2_nm"] != 79:
        raise AssertionError("stage_a_mdc_thickness_changed")
    if identity["extra_spacer_nm"] != 237 or identity["total_continuous_sio2_separation_nm"] != 316:
        raise AssertionError("stage_a_spacer_identity_changed")
    if stage_a["evidence_package"]["broadband_matrix_110"]["rows"] != 110:
        raise AssertionError("stage_a_matrix_changed")

    profile_npz = RUN / "geometry_profiles" / "00d1a9ec132824f20a0ce77b6803eed5775d192431935bffb5f1f9f71ae5a24b__geometry_profile.npz"
    with np.load(profile_npz, allow_pickle=False) as profile:
        lam = np.asarray(profile["wavelength_nm"], dtype=float)
        theta_deg = np.asarray(profile["angle_deg"], dtype=float)
        normalized = np.asarray(profile["normalized_joint"], dtype=float)
    theta_rad = np.radians(theta_deg)
    w_lambda = trapz_weights(lam)
    w_theta = trapz_weights(theta_rad)
    trapz = np.trapezoid if hasattr(np, "trapezoid") else np.trapz
    closure = float(trapz(trapz(normalized, theta_rad, axis=1), lam))
    if normalized.shape != (301, 2000) or abs(closure - 1.0) > 1e-12:
        raise AssertionError("profile_grid_or_closure_invalid")
    grid_sha = sha_bytes(lam.tobytes() + theta_deg.tobytes())
    if grid_sha != "f3e2b786901c912240ea0267886d4ea9d9e5c62b78846bf1428dbed3c25a0ac9":
        raise AssertionError("frozen_grid_hash_changed")

    material_csv = ROOT / "outputs" / "material_reference" / "mdc_blue_oujizi_m" / "material_ref_native_sampled.csv"
    material = material_audit(material_csv)
    fsp_x = MDC_RUNTIME / "zl1_alternative_x_x+1000_a1_20260715_163849.fsp"
    fsp_z = MDC_RUNTIME / "zl1_alternative_z_x+1000_a1_20260715_163925.fsp"

    source_evidence = [
        evidence(MDC_SOURCE / "scripts" / "run_mdc_zl1_alternative_dipole_x5_incoherent_output_448_452_v1.py", "traditional MDC dipole setup and source contract"),
        evidence(MDC_SOURCE / "scripts" / "mdc_fdtd_2d_monitor_contract_v1.py", "traditional MDC 2D monitor coordinate contract"),
        evidence(MDC_SOURCE / "outputs" / "mdc_native_m1_2d_dipole_device_comparison_v1" / "dipole_field_channel_validation.csv", "existing field-family audit record; readback status remains unresolved", required=False),
        evidence(fsp_x, "read-only FSP metadata sample for x source"),
        evidence(fsp_z, "read-only FSP metadata sample for z source"),
        evidence(HF_SOURCE / "scripts" / "run_mdc_hf_surrogate_v2_doe96_joint_profile_v1.py", "fixed-v2 native joint profile exporter"),
        evidence(HF_SOURCE / "scripts" / "extract_mdc_hf_surrogate_v2_doe96_labels_v1.py", "fixed-v2 raw aggregation and quadrature implementation"),
        evidence(RUN / "joint_profile_grid_contract.json", "fixed-v2 grid contract"),
        evidence(RUN / "joint_profile_monitor_contract_resolved.json", "fixed-v2 monitor/export contract"),
        evidence(RUN / "joint_profile_export_contract_resolved.json", "fixed-v2 raw joint export contract"),
        evidence(RUN / "profile_quadrature_and_flattening_contract.json", "fixed-v2 quadrature and flattening contract"),
        evidence(RUN / "doe96_monitor_grid_lock.json", "fixed-v2 native grid lock"),
        evidence(RUN / "doe96_grid_consistency_audit.json", "fixed-v2 grid consistency audit"),
        evidence(RUN / "doe96_aggregation_audit_v1.json", "fixed-v2 raw-first aggregation audit"),
        evidence(RUN / "doe96_joint_profile_quality_audit.json", "fixed-v2 profile quality audit"),
        evidence(material_csv, "Native-M1 SiO2 material samples"),
        evidence(ROOT / "configs" / "material_reference_apcd_blue.yaml", "Native-M1 material policy"),
        evidence(COUPLING / "source_branch_lock_v1.json", "coupling source branch lock"),
    ]

    source_heads = {
        "traditional_mdc_current_head": git_head(MDC_SOURCE),
        "mdc_hf_current_head": git_head(HF_SOURCE),
        "coupling_head_before_resolution": "6d5e979f5b42668a2da5bbb6c33999154b3d9131",
        "frozen_hf_source_lock_commit": "489b54e43bbf2c08ce030a945b9d4b70ee7550f2",
    }

    basis = {
        "contract_id": "MDC_INTERFACE_POLARIZATION_BASIS_V1",
        "status": "RESOLVED_BY_2D_SETUP_AND_ANALYTIC_MAXWELL_DECOMPOSITION",
        "simulation_plane": "Lumerical solver x-y plane; project physical x-z plane",
        "solver_coordinates": {"in_plane": ["x_L", "y_L"], "invariant_axis": "z_L", "vertical_axis": "y_L"},
        "project_coordinates": {"in_plane": ["x_p", "z_p"], "invariant_axis": "y_p", "vertical_axis": "z_p"},
        "coordinate_mapping": {"x_p": "x_L", "z_p": "y_L", "y_p": "z_L"},
        "propagation": {"project_k": "(kx,0,kz)", "solver_k": "(kx,ky,0)", "ky_over_k0_project": 0.0, "u_x": "kx/k0", "theta_air": "asin(u_x) in radians; display labels may be degrees"},
        "source_position_semantics": {"setup_axis": "solver_y", "project_axis": "project_z", "source_z_nm_means": "vertical project-z position, not solver-z orientation"},
        "lumerical_dipole_readback": {
            "x": {"theta_deg": 90.0, "phi_deg": 0.0, "axis": "solver_x", "project_axis": "project_x"},
            "z": {"theta_deg": 0.0, "phi_deg": 0.0, "axis": "solver_z invariant", "project_axis": "project_y invariant"},
        },
        "field_families_solver": {"P_TM_like": ["E_x", "E_y", "H_z"], "S_TE_like": ["E_z", "H_x", "H_y"]},
        "field_families_project": {"P_TM_like": ["E_x", "E_z", "H_y"], "S_TE_like": ["E_y", "H_x", "H_z"]},
        "source_orientation_to_interface_branch": {"x_dipole": "P_XLIKE", "z_dipole": "S_YLIKE"},
        "branch_basis": {"P_XLIKE": {"E_components": ["E_x", "E_z"], "H_components": ["H_y"]}, "S_YLIKE": {"E_components": ["E_y"], "H_components": ["H_x", "H_z"]}},
        "source_orientation_is_not_polarization_label": True,
        "six_case_contains_independent_p_and_s": True,
        "field_component_readback": "NOT_AVAILABLE_IN_EXISTING_FSP_ASSETS; analytic 2D decoupling is the authoritative classification",
        "cross_family_mappings_forbidden": ["x_dipole_to_S_YLIKE", "z_dipole_to_P_XLIKE"],
        "evidence": source_evidence[:5],
        "official_api_reference": "https://optics.ansys.com/hc/en-us/articles/360034382794-Dipole-source-Simulation-object",
    }
    field_basis_audit = {**basis, "contract_id": "MDC_2D_FIELD_BASIS_AUDIT_V1", "audit_type": "2D plane, invariant-axis, source-orientation and field-component audit", "interface_basis_contract_id": "MDC_INTERFACE_POLARIZATION_BASIS_V1"}

    quadrature = {
        "contract_id": "MDC_LEVEL1_QUADRATURE_SEMANTICS_V1",
        "status": "RESOLVED_NATIVE_TRAPEZOID_DENSITY_IN_LAMBDA_THETA",
        "source_profile": {"tensor_shape": [301, 2000], "axis_order": ["wavelength_index", "angle_index"], "tensor_units": "raw native farfield2d intensity", "wavelength_nm": [420.0, 480.0, 301], "angle_deg": [-90.0, 90.0, 2000], "angle_grid_nonuniform": True, "grid_sha256": grid_sha},
        "raw_aggregation_order": ["raw x/z average at each position", "raw three-position average", "raw joint tensor marginals", "single normalization denominator", "derived metrics"],
        "raw_xz_weight": 0.5,
        "raw_geometry_weight": 1.0 / 3.0,
        "case_normalize_before_aggregation": False,
        "complex_field_interference": False,
        "density_semantics": "normalized density W(lambda,theta) with integral measure d_lambda_nm*d_theta_rad",
        "normalization": {"denominator": "Z=trapz_lambda(trapz_theta(raw_joint,theta_rad,axis=1),lambda_nm)", "profile": "W_theta=raw_joint/Z", "closure_identity": "SUM_i,j W_theta[i,j]*w_lambda[i]*w_theta[j]=1", "observed_closure": closure, "tolerance": 1e-12},
        "weights": {"lambda_units": "nm", "theta_units": "radians", "rule": "composite trapezoid on native coordinates", "endpoint_treatment": "half adjacent interval; interior half span of neighboring nodes", "w_lambda_sum": float(np.sum(w_lambda)), "w_theta_sum": float(np.sum(w_theta)), "w_lambda_hash": sha_bytes(w_lambda.tobytes()), "w_theta_hash": sha_bytes(w_theta.tobytes()), "theta_step_rad_min_max": [float(np.min(np.diff(theta_rad))), float(np.max(np.diff(theta_rad)))]},
        "marginals": {"spectral": "trapz_theta(raw_joint,theta_rad,axis=1)", "angular": "trapz_lambda(raw_joint,lambda_nm,axis=0)"},
        "no_implicit_2pi": True,
        "no_spectrum_times_angular_cut": True,
        "no_case_level_normalization": True,
        "numerical_consumption_authorized": False,
        "evidence": [x for x in source_evidence if "fixed-v2" in x["role"]],
    }

    fixture_theta_deg = np.asarray([-60.0, 0.0, 60.0])
    fixture_density = np.asarray([1.0, 2.0, 1.0])
    fixture_theta_edges = np.asarray([-60.0, -30.0, 30.0, 60.0])
    fixture_u_edges = np.sin(np.radians(np.asarray([-60.0, 0.0, 60.0])))
    fixture_expected_mass = [math.pi / 2.0, math.pi / 2.0]
    remap = {
        "contract_id": "MDC_THETA_TO_UX_CONSERVATIVE_REMAP_V1",
        "status": "RESOLVED_CONSERVATIVE_MONOTONIC_REMAP",
        "source_density": "W_theta(lambda,theta) per radian",
        "target_density": "W_u(lambda,u_x) per u_x",
        "coordinate_transform": "u_x=sin(theta_rad); theta_rad=asin(u_x); dtheta_du=1/sqrt(1-u_x^2)",
        "algorithm": "piecewise-constant source density with exact theta-overlap integration after inverse-sine target-edge mapping",
        "source_cell_edges": "native theta node endpoints with interior midpoint edges",
        "target_cell_edges": "declared monotonic u_x edges; inverse-sine mapped into theta before overlap",
        "requirements": {"total_mass_closure": True, "spectral_marginal_closure": True, "angular_ux_marginal_closure": True, "monotonic_mapping": True, "no_negative_weights": True, "no_extrapolation": True, "fresh_process_determinism": True},
        "support": {"native_theta_deg": [-90.0, 90.0], "native_u_x": [-1.0, 1.0], "air_side_propagating_domain": "|u_x|<=1", "target_support_must_be_subset_of_native": True, "out_of_support_mass": "reported and not silently discarded"},
        "fixture": {"theta_nodes_deg": fixture_theta_deg.tolist(), "theta_cell_edges_deg": fixture_theta_edges.tolist(), "source_density": fixture_density.tolist(), "target_u_edges": fixture_u_edges.tolist(), "expected_target_mass": fixture_expected_mass, "expected_total_mass": math.pi, "tolerance": 1e-12},
        "grid_evidence": {"angle_grid_sha256": sha_bytes(theta_deg.tobytes()), "combined_grid_sha256": grid_sha, "angle_points": 2000},
    }

    propagation = {
        "contract_id": "LEVEL1_INTERFACE_PROPAGATION_V1",
        "status": "RESOLVED_HOMOGENEOUS_NATIVE_M1_SIO2_FACTOR",
        "from_plane": {"id": "MDC_TOP_UPWARD_OUTPUT_PLANE", "project_z_nm": 975, "medium": "APCD_SIO2_NATIVE_M1"},
        "to_plane": {"id": "NP_PILLAR_BOTTOM", "project_z_nm": 1212, "medium": "APCD_SIO2_NATIVE_M1"},
        "distance_nm": 237,
        "role": "interface propagation operator, not MDC provider and not NP scattering provider",
        "material": {"material_id": "APCD_SIO2_NATIVE_M1", "source_config": str(ROOT / "configs" / "material_reference_apcd_blue.yaml"), "native_material_csv": str(material_csv), "audit": material},
        "operator": {"k0": "2*pi/lambda", "kz_sio2": "k0*sqrt(n_sio2(lambda)^2-u_x^2)", "amplitude": "exp(i*kz_sio2*d)", "power_factor": "abs(amplitude)^2", "lossless_445_455_power_factor": 1.0, "phase_retained_for_field_operator": True, "phase_ignored_by_incoherent_power_level1": True},
        "no_np_finite_spacer_double_count": True,
        "no_solver_required": True,
    }

    np_operator = {
        "contract_id": "LEVEL1_NP_SCATTERING_OPERATOR_V1",
        "status": "VALID_STANDALONE_OPERATOR_PARTIAL_GRID_POLARIZATION_COVERAGE",
        "operator_id": "ONE_WAY_NP_SCATTERING_OPERATOR",
        "input_plane": "NP_PILLAR_BOTTOM",
        "input_medium": "APCD_SIO2_NATIVE_M1",
        "output_medium": "Air",
        "reference_stack": "semi-infinite Native-M1 SiO2 substrate -> RUN3A Native-M1 TiO2 K6 -> Air",
        "finite_237nm_sio2_is_inside_np_provider": False,
        "finite_237nm_sio2_role": "LEVEL1_INTERFACE_PROPAGATION_V1",
        "branches": ["P_XLIKE", "S_YLIKE"],
        "existing_reusable_scope": {"wavelength_nm": [445, 455, 11], "u_x": [0.0], "branch": ["P_XLIKE"], "formal_np_source_scope": "RUN3A standalone x-pol normal response"},
        "full_convolution_requires": ["P and/or S direct eta on every exact remapped u_x support point requested by scope", "same wavelength grid", "same reference-plane and order-sign convention", "no extrapolation"],
        "stage_a_matrix_is_validation_only": True,
        "no_solver_called": True,
    }

    factorisation = {
        "contract_id": "MDC_LEVEL1_POWER_PROFILE_FACTORISATION_V1",
        "status": "RESOLVED_CONDITIONAL_ON_FORMAL_ZL1_MDC_PROFILE_AND_SCOPE_OPTION",
        "factor_chain": ["MDC provider ends at z=975", "237 nm homogeneous SiO2 propagation", "NP scattering provider starts at pillar bottom z=1212"],
        "formula_theta": "P_plus1_relative=P_MDC_up_FDTD*SUM[W_theta(lambda,theta,channel)*T_prop(lambda,u_x,pol)*eta_NP_plus1(lambda,u_x,pol)*d_lambda_nm*d_theta_rad]",
        "formula_ux": "P_plus1_relative=P_MDC_up_FDTD*SUM[W_u(lambda,u_x,channel)*T_prop(lambda,u_x,pol)*eta_NP_plus1(lambda,u_x,pol)*d_lambda_nm*d_u_x]",
        "profile_conversion": "W_theta -> W_u by MDC_THETA_TO_UX_CONSERVATIVE_REMAP_V1 before NP join",
        "p_mdc_definition": "source-normalized, raw-first, orientation-aggregated relative upward MDC output scalar; p_up_raw and p_box_raw remain separate until declared normalization",
        "source_aggregation": {"same_position": "0.5*raw_x+0.5*raw_z", "geometry": "(raw_top+raw_centroid+raw_bottom)/3", "meaning": "incoherent source-orientation aggregation, not P/S averaging"},
        "normalization_order": ["raw readback", "source orientation aggregation", "geometry aggregation", "source/near-field normalization", "joint profile normalization", "propagation and NP weighted sum"],
        "no_double_counting": ["Stage-A integrated matrix is not multiplied by W_MDC", "237 nm spacer is not embedded in NP operator", "P_MDC_up_FDTD is not normalized again by W", "phase is not reintroduced into incoherent power sum"],
        "absolute_claims_forbidden": ["absolute LEE", "EQE", "Purcell", "absolute optical power"],
    }

    # Update canonical equivalent contracts while retaining the frozen Stage-A identity.
    write_json(COUPLING / "mdc_2d_field_basis_audit_v1.json", field_basis_audit)
    write_json(COUPLING / "mdc_interface_polarization_basis_v1.json", basis)
    write_json(COUPLING / "mdc_level1_quadrature_semantics_v1.json", quadrature)
    write_json(COUPLING / "mdc_theta_to_ux_conservative_remap_v1.json", remap)
    write_json(COUPLING / "level1_interface_propagation_v1.json", propagation)
    write_json(COUPLING / "level1_np_scattering_operator_v1.json", np_operator)
    write_json(COUPLING / "mdc_level1_power_profile_factorisation_v1.json", factorisation)

    mapping = {
        "schema_version": "level1_polarization_mapping_v2",
        "status": "TRADITIONAL_STAGE_B_LEVEL1_POLARIZATION_MAPPING_RESOLVED",
        "direct_mapping_allowed": True,
        "mapping_basis_contract": "MDC_INTERFACE_POLARIZATION_BASIS_V1",
        "mdc_channel_type": "2D emission-source channels classified by exact solver-axis field family",
        "np_channel_type": "incident plane-wave polarization branches",
        "resolved_mappings": {"x_dipole": "P_XLIKE", "z_dipole": "S_YLIKE"},
        "prohibited_mappings": ["x_dipole_to_S_YLIKE", "z_dipole_to_P_XLIKE", "source_orientation_as_unqualified_polarization_label"],
        "source_aggregation_is_not_polarization_average": True,
        "x_y_averaging": "NOT_APPLICABLE_TO_FROZEN_X/Z_SOURCE_CONTRACT; no automatic y source addition",
        "field_readback_status": "NOT_AVAILABLE; setup plus analytic 2D Maxwell decomposition resolves the family",
        "six_case_contains_independent_p_s": True,
        "six_case_contains_independent_p_and_s": True,
        "new_source_contract_required": False,
    }
    write_json(COUPLING / "level1_polarization_mapping_v1.json", mapping)

    canonical_quad = {**quadrature, "schema_version": "level1_quadrature_contract_v2", "raw_first": True, "aggregation_order": ["raw power readback", "same-position P_position=0.5*P_x+0.5*P_z", "geometry P_geometry=(P_top+P_centroid+P_bottom)/3", "normalization", "derived metrics"], "case_normalize_before_average": False, "numerical_consumption_allowed": False, "integration_formula": factorisation["formula_theta"]}
    write_json(COUPLING / "level1_quadrature_contract_v1.json", canonical_quad)
    canonical_ref = load_json(COUPLING / "level1_reference_plane_mapping_v1.json")
    canonical_ref.update({"status": "RESOLVED_INTERFACE_PROPAGATION_FACTORISATION", "propagation_operator_contract": "LEVEL1_INTERFACE_PROPAGATION_V1", "np_operator_contract": "LEVEL1_NP_SCATTERING_OPERATOR_V1", "factorisation_contract": "MDC_LEVEL1_POWER_PROFILE_FACTORISATION_V1", "polarization_basis_contract": "MDC_INTERFACE_POLARIZATION_BASIS_V1", "source_z_coordinate_meaning": "project vertical coordinate mapped to solver y; solver z is invariant source orientation"})
    write_json(COUPLING / "level1_reference_plane_mapping_v1.json", canonical_ref)
    canonical_power = load_json(COUPLING / "level1_power_contract_v1.json")
    canonical_power.update({"status": "RESOLVED_RAW_PROFILE_FACTORISATION_WITH_CONDITIONAL_ZL1_PROVIDER", "factorisation_contract": "MDC_LEVEL1_POWER_PROFILE_FACTORISATION_V1", "p_mdc_and_w_separate": True, "no_double_normalization": True})
    write_json(COUPLING / "level1_power_contract_v1.json", canonical_power)

    handoff = load_json(COUPLING / "traditional_stage_b_level1_handoff_v1.json")
    handoff["status"] = "USER_DECISION_REQUIRED_LEVEL1_POLARIZATION_SCOPE"
    handoff["status_class"] = "USER_DECISION_REQUIRED"
    handoff["next_action"] = "USER_DECISION_REQUIRED_LEVEL1_POLARIZATION_SCOPE"
    handoff["physics_resolution"] = {"2d_plane": "RESOLVED_SOLVER_XY_PROJECT_XZ", "six_case_polarization": "P_AND_S_PRESENT", "quadrature": "RESOLVED_NATIVE_TRAPEZOID_DENSITY", "theta_to_ux": "RESOLVED_CONSERVATIVE_REMAP", "237nm_factorisation": "RESOLVED_INTERFACE_PROPAGATION", "np_operator": "VALID_STANDALONE_PARTIAL_SCOPE"}
    handoff["contracts"] = {
        "grid_alignment": "contracts/coupling/level1_grid_alignment_v1.json",
        "field_basis_audit": "contracts/coupling/mdc_2d_field_basis_audit_v1.json",
        "polarization_mapping": "contracts/coupling/level1_polarization_mapping_v1.json",
        "quadrature": "contracts/coupling/level1_quadrature_contract_v1.json",
        "reference_plane": "contracts/coupling/level1_reference_plane_mapping_v1.json",
        "power": "contracts/coupling/level1_power_contract_v1.json",
        "interface_polarization_basis": "contracts/coupling/mdc_interface_polarization_basis_v1.json",
        "quadrature_semantics": "contracts/coupling/mdc_level1_quadrature_semantics_v1.json",
        "theta_to_ux_remap": "contracts/coupling/mdc_theta_to_ux_conservative_remap_v1.json",
        "interface_propagation": "contracts/coupling/level1_interface_propagation_v1.json",
        "np_scattering_operator": "contracts/coupling/level1_np_scattering_operator_v1.json",
        "power_profile_factorisation": "contracts/coupling/mdc_level1_power_profile_factorisation_v1.json",
    }
    handoff["solver_budget_plan"] = {
        "status": "CONDITIONAL_NOT_AUTHORIZED",
        "current_turn_entries": 0,
        "minimum_authorization_unit": "one entered run per direct solver case; no authorization in this turn",
        "scope_options": {"A": "TRADITIONAL_LEVEL1_P_TM_ONLY", "B": "TRADITIONAL_LEVEL1_FULL_P_S_SOURCE_SCOPE_EXTENSION"},
        "minimum": {"MDC_formal_FDTD_cases": 6, "NP_option_A_new_states": "max(N_ux_required_P-1,0)", "NP_option_B_new_states": "max(N_ux_required_P-1,0)+N_ux_required_S", "N_ux_required_definition": "distinct exact remapped u_x support points declared by the formal ZL1 profile; no numeric grid invented before ZL1 profile exists"},
        "recommended": "minimum plus independently justified support-edge/grid-convergence response points; count only after scope decision",
        "optional": "integrated MDC+NP full-wave validation after one-way contract passes",
        "reusable_np_state": "P_XLIKE at u_x=0 over exact 445-455 nm",
        "do_not_count": ["Stage-A integrated 110 rows", "DOE96 historical 576 FDTD calls", "DOE96 576 historical solver calls", "legacy -400 nm diagnostics"],
        "authorization_blockers": ["user selects P/TM-only or full P/S scope", "formal ZL1 six-case MDC profile exists", "exact ZL1 u_x support derived before NP grid approval"],
    }
    handoff["solver_budget_plan"].update({"mdc_missing_formal_cases": 6, "np_existing_formal_states": 1, "np_full_stage_a_target_states": 10, "np_missing_full_stage_a_states": 9})
    handoff["evidence_assets"] = source_evidence
    handoff["source_heads"] = source_heads
    handoff["safety"] = {"FDTD": 0, "TMM": 0, "RCWA": 0, "FEM": 0, "training": 0, "ML_inference": 0, "this_turn_solver_entries": 0, "source_worktree_writes": 0, "stage_a_reruns": 0, "m1_model_consumption": 0}
    write_json(COUPLING / "traditional_stage_b_level1_handoff_v1.json", handoff)

    readiness = load_json(OUT / "traditional_stage_b_level1_readiness_v1.json")
    readiness.update({"status": handoff["status"], "status_class": handoff["status_class"], "next_action": handoff["next_action"], "polarization_mapping_status": mapping["status"], "quadrature_status": quadrature["status"], "reference_plane_status": canonical_ref["status"], "grid_status": "RESOLVED_NATIVE_THETA_WITH_CONSERVATIVE_UX_REMAP"})
    readiness["solver_budget_plan"] = handoff["solver_budget_plan"]
    readiness["physics_contracts"] = {"basis": "contracts/coupling/mdc_interface_polarization_basis_v1.json", "quadrature": "contracts/coupling/mdc_level1_quadrature_semantics_v1.json", "remap": "contracts/coupling/mdc_theta_to_ux_conservative_remap_v1.json", "propagation": "contracts/coupling/level1_interface_propagation_v1.json", "np_operator": "contracts/coupling/level1_np_scattering_operator_v1.json", "factorisation": "contracts/coupling/mdc_level1_power_profile_factorisation_v1.json"}
    readiness["safety"] = handoff["safety"]
    write_json(OUT / "traditional_stage_b_level1_readiness_v1.json", readiness)

    physics_readiness = {"schema_version": "traditional_stage_b_level1_physics_resolution_v1", "status": handoff["status"], "status_class": handoff["status_class"], "next_action": handoff["next_action"], "solver_entries_this_turn": 0, "training_entries_this_turn": 0, "ml_inference_entries_this_turn": 0, "decisions": {"simulation_plane": basis["simulation_plane"], "invariant_axis": basis["solver_coordinates"]["invariant_axis"], "x_source_family": "P_TM_like", "z_source_family": "S_TE_like", "six_case_has_P_and_S": True, "x_z_aggregation": "incoherent source-orientation aggregation, not P/S averaging", "profile_semantics": quadrature["density_semantics"], "theta_to_ux": remap["status"], "native_ux_support": remap["support"]["native_u_x"], "required_ux_support": "derive exact ZL1 mass support before fixing NP grid", "spacer_237nm_role": "interface propagation operator", "standalone_np_operator": np_operator["status"], "stage_a_matrix_np_provider": False}, "source_heads": source_heads, "source_evidence": source_evidence, "contracts": handoff["contracts"], "solver_budget_plan": handoff["solver_budget_plan"], "safety": handoff["safety"]}
    write_json(OUT / "traditional_stage_b_level1_physics_resolution_v1.json", physics_readiness)

    report = f"""# Traditional Stage-B Level-1 polarization, quadrature and factorisation resolution

Status: `{handoff['status']}`

## MDC polarization basis

- The authoritative setup and read-only FSP metadata show `dimension=2D`, solver x-y coordinates, solver z invariant, source position on solver y, and upward propagation toward +y.
- Project coordinates map solver x -> project x, solver y -> project z, solver z -> project y invariant. Therefore project propagation is `k=(kx,0,kz)` while the Lumerical solver sees `(kx,ky,0)`.
- `theta=90 deg, phi=0` is the solver-x source used by the x case: P/TM-like family `(Ex,Ey,Hz)` in solver coordinates.
- `theta=0 deg, phi=0` is the solver-z invariant source used by the z case: S/TE-like family `(Ez,Hx,Hy)` in solver coordinates.
- The six frozen top/centroid/bottom x/z cases therefore contain independent P and S families. The source z position is vertical project-z position; the z source orientation is solver-z/project-y invariant. These are different fields.
- Existing field-component readback is not available in the legacy FSP assets; the classification is resolved by the exact setup plus analytic 2D Maxwell decoupling, not by a guessed label.

## Quadrature / ux

- The fixed-v2 authoritative native profile is raw `farfield2d(upward_monitor, wavelength_index)` intensity with shape `301 x 2000`, axis order `[wavelength_index, angle_index]`.
- Wavelength grid: 420--480 nm, 301 points, 0.2 nm spacing. Native angle grid: -90--90 deg, 2000 nonuniform points, converted to radians before integration.
- Raw aggregation is x/z average at each position, then three-position average; no case normalization occurs before aggregation.
- Normalization is `Z=trapz_lambda(trapz_theta(raw_joint,theta_rad),lambda_nm)` and `W_theta=raw_joint/Z`. The observed normalized integral is `{closure:.16g}`.
- Theta-to-ux is a conservative monotonic remap with `u_x=sin(theta_rad)`, inverse-sine overlap, no extrapolation, no negative weights, and explicit mass/marginal closure tests. Native support is `[-1,1]`; the exact ZL1 relevant support must be derived after the formal ZL1 profile exists.

## Interface / NP factorisation

- MDC ends at project z=975 nm; NP starts at pillar bottom project z=1212 nm.
- The 237 nm homogeneous Native-M1 SiO2 region is an interface propagation operator, not part of the MDC provider and not part of the NP scattering provider.
- Native SiO2 data are lossless over the frozen 445--455 nm material bracket (`k=0` in the native samples), so the Level-1 propagating-channel power factor is 1; the coherent phase operator is retained only for a field-level extension.
- Standalone SiO2 -> RUN3A -> Air is valid as a one-way NP scattering operator at the pillar-bottom reference plane. Current NP coverage remains partial: P/X-like at `u_x=0`, exact 445--455 nm only.
- Stage-A's integrated 110-row matrix remains validation/reference data and is not an NP eta provider.

## Solver implications / Git

- No solver was run. Minimum future MDC input remains six formal real 2D FDTD cases.
- Option A (`TRADITIONAL_LEVEL1_P_TM_ONLY`) and Option B (`TRADITIONAL_LEVEL1_FULL_P_S_SOURCE_SCOPE_EXTENSION`) are both frozen without selecting either. NP state counts remain conditional on the exact remapped ZL1 support; no NP grid was invented.
- Contracts: `MDC_INTERFACE_POLARIZATION_BASIS_V1`, `MDC_LEVEL1_QUADRATURE_SEMANTICS_V1`, `MDC_THETA_TO_UX_CONSERVATIVE_REMAP_V1`, `LEVEL1_INTERFACE_PROPAGATION_V1`, `LEVEL1_NP_SCATTERING_OPERATOR_V1`, `MDC_LEVEL1_POWER_PROFILE_FACTORISATION_V1`.
- This report's source audit is read-only; source worktree writes, FDTD, TMM, RCWA, FEM, training and ML inference entries are all zero.
"""
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "traditional_stage_b_level1_polarization_quadrature_resolution_v1.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": handoff["status"], "solver_entries": 0, "profile_shape": [301, 2000], "profile_closure": closure, "source_heads": source_heads}, sort_keys=True))


if __name__ == "__main__":
    main()
