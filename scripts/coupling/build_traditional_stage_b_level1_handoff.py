from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STAGE_A_CLOSURE_HEAD = "25e78936afca7387f71bda244545efed64cbe702"
MATRIX_SHA = "d400c51cfa557aeffdefb09567dbe20705c50d915bc9a5ddd570281535265bf6"
MDC_ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_defect_450")
MDC_HF_ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2")
NP_ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def asset(path: Path, role: str, status: str, notes: str = ""):
    return {
        "path": str(path),
        "sha256": sha(path) if path.exists() else None,
        "role": role,
        "status": status,
        "notes": notes,
    }


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    source_lock_path = ROOT / "contracts/coupling/source_branch_lock_v1.json"
    stage_a_lock_path = ROOT / "contracts/coupling/traditional_stage_a_baseline_lock_v1.json"
    stage_a_summary_path = ROOT / "reports/coupling/traditional_stage_a_baseline_summary_v1.json"
    matrix_path = ROOT / "reports/coupling/stage_a_frozen_spacer_polarization_angle_broadband_matrix_v1.json"
    source_lock = load(source_lock_path)
    stage_a_lock = load(stage_a_lock_path)
    stage_a_summary = load(stage_a_summary_path)
    matrix = load(matrix_path)

    legacy_root = MDC_ROOT / "outputs/mdc_zl1_alternative_dipole_x5_incoherent_output_448_452_v1"
    legacy_manifest_path = legacy_root / "manifest.json"
    legacy_audit_path = legacy_root / "existing_data_audit.json"
    legacy_cases_path = legacy_root / "source_cases.csv"
    legacy_validation_path = legacy_root / "validation.json"
    legacy_manifest = load(legacy_manifest_path)
    legacy_audit = load(legacy_audit_path)
    legacy_validation = load(legacy_validation_path)

    center_sim_manifest_path = MDC_ROOT / "outputs/mdc_native_m1_2d_dipole_device_comparison_v1/simulation_manifest.csv"
    orientation_path = MDC_ROOT / "outputs/mdc_native_m1_2d_dipole_device_comparison_v1/dipole_orientation_readback.csv"
    mdc1d2_manifest_path = MDC_ROOT / "outputs/mdc1d2_native_m1_zl1_2d_validation/run_manifest.json"
    mdc1d2_comparison_path = MDC_ROOT / "outputs/mdc1d2_native_m1_zl1_2d_validation/three_case_comparison.csv"
    plane_wave_manifest_path = MDC_ROOT / "outputs/mdc_zl1_alternative_2d_fdtd_transmission_448_452_v1/manifest.json"
    mdc1d2_manifest = load(mdc1d2_manifest_path)
    doe96_root = MDC_HF_ROOT / "outputs/mdc_hf_surrogate_v2_doe96_joint_profile_database_v1/20260803T_doe96_joint_profile_6b6d7e2"
    doe96_completion_path = doe96_root / "doe96_completion_manifest.json"
    doe96_quality_path = doe96_root / "doe96_joint_profile_quality_audit.json"
    doe96_grid_path = doe96_root / "doe96_monitor_grid_lock.json"
    doe96_case_matrix_path = MDC_HF_ROOT / "contracts/mdc_hf_surrogate_v2/fixed_v2_initial_doe96_case_matrix.csv"
    doe96_completion = load(doe96_completion_path)
    doe96_quality = load(doe96_quality_path)
    doe96_grid = load(doe96_grid_path)
    doe96_case_matrix_text = doe96_case_matrix_path.read_text(encoding="utf-8", errors="replace")

    np_scope_path = NP_ROOT / "outputs/np_k6_formal_source_scope_v1/formal_source_scope_v1.json"
    np_handoff_path = NP_ROOT / "outputs/np_k6_formal_source_scope_v1/coupling_handoff_manifest_v1.json"
    np_scope = load(np_scope_path)
    np_handoff = load(np_handoff_path)

    stage_a_identity = stage_a_lock["physical_identity"]
    assert stage_a_identity["mdc_candidate_id"] == "P1_ZL1_ALTERNATIVE_G3_A3"
    assert stage_a_identity["mdc_total_thickness_nm"] == 975
    assert stage_a_identity["mdc_top_sio2_nm"] == 79
    assert stage_a_identity["extra_spacer_nm"] == 237
    assert stage_a_identity["total_continuous_sio2_separation_nm"] == 316
    assert sha(matrix_path) == MATRIX_SHA
    assert len(matrix["rows"]) == 110
    assert STAGE_A_CLOSURE_HEAD == "25e78936afca7387f71bda244545efed64cbe702"

    formal_mdc_cases = [
        {"position": "top", "source_z_nm": -171.5, "dipole": "x"},
        {"position": "top", "source_z_nm": -171.5, "dipole": "z"},
        {"position": "centroid", "source_z_nm": -276.0, "dipole": "x"},
        {"position": "centroid", "source_z_nm": -276.0, "dipole": "z"},
        {"position": "bottom", "source_z_nm": -380.5, "dipole": "x"},
        {"position": "bottom", "source_z_nm": -380.5, "dipole": "z"},
    ]
    legacy_mdc = {
        "provider_status": "REQUIRES_DIRECT_SOLVER",
        "formal_outcome": "MDC_LEVEL1_PROVIDER_REQUIRES_FORMAL_SIX_CASE_FDTD",
        "formal_case_membership": False,
        "source_y_nm": legacy_manifest["source_y_nm"],
        "positions_nm": legacy_manifest["positions_nm"],
        "dipoles": legacy_manifest["dipoles"],
        "wavelength_scope": {"start_nm": 448.0, "stop_nm": 452.0, "step_nm": 0.1, "points": 41},
        "normalization": legacy_audit["contract"],
        "legacy_diagnostic_only": True,
        "reason": "Legacy source plane is y=-400 nm with x-offset positions, not the formal top/centroid/bottom z contract; source-normalized dipole power is not formally verified.",
    }
    doe96_mdc = {
        "joint_tensor_available": True,
        "joint_tensor_shape": doe96_completion["joint_tensor_shape"],
        "geometry_count": doe96_completion["geometry_count"],
        "case_count": doe96_completion["joint_tensor_case_count"],
        "quality_status": doe96_quality["status"],
        "raw_before_normalization": doe96_quality["raw_before_normalization_all"],
        "z_l1_geometry_hash_match": "2743ba872a6865519e555f99131220415afb076d653db11f1fe2ef658286c7d8" in doe96_case_matrix_text,
        "usable_as_zl1_formal_provider": False,
        "exclusion_reason": "DOE96 geometry database is not the frozen P1_ZL1_ALTERNATIVE_G3_A3 geometry; no ZL1 geometry hash match.",
    }
    mdc_provider = {
        "provider_id": "MDC_LEVEL1_TRADITIONAL_ZL1_REAL_FDTD",
        "provider_status": "REQUIRES_DIRECT_SOLVER",
        "formal_outcome": "MDC_LEVEL1_PROVIDER_REQUIRES_FORMAL_SIX_CASE_FDTD",
        "candidate_id": "P1_ZL1_ALTERNATIVE_G3_A3",
        "required_source_cases": formal_mdc_cases,
        "required_outputs": [
            "raw_upward_power(lambda,u_x,position,dipole)",
            "P_MDC_up_FDTD(lambda,u_x)",
            "W_MDC_FDTD(lambda,u_x,channel)",
            "native joint tensor S(lambda,u_x) or an explicitly equivalent raw-power profile",
            "exact source/grid/provenance identity",
        ],
        "existing_assets": {
            "legacy_zl1_x5": legacy_mdc,
            "single_x_dipole_978nm_stack": {
                "compiled_sequence": mdc1d2_manifest["compiled_sequence"],
                "layers": mdc1d2_manifest["layers"],
                "thickness_nm": mdc1d2_manifest["thickness_nm"],
                "formal_case_membership": False,
                "reason": "978 nm stack and x-dipole-only; not the frozen 975 nm six-case source contract.",
            },
            "doe96_joint_database": doe96_mdc,
        },
        "missing_dimensions": [
            "six formal cases at z=-171.5/-276.0/-380.5 nm with x/z dipoles",
            "975 nm P1_ZL1_ALTERNATIVE_G3_A3 exact geometry",
            "raw upward-power and source-normalization contract for the formal cases",
            "native joint tensor/profile identity for the ZL1 geometry",
        ],
        "m1_surrogate_prohibited": True,
        "m1_model_id": "MDC_HF_M1_GEOMETRY_CONDITIONED_DIRECT_FINAL_5SEED_V1",
    }

    np_provider = {
        "provider_id": "NP_LEVEL1_TRADITIONAL_RUN3A_MODULAR_RESPONSE",
        "provider_status": "PARTIAL_EXISTING_ASSET",
        "formal_outcome": "NP_LEVEL1_PROVIDER_PARTIAL_NORMAL_X_ONLY",
        "candidate_id": np_scope["candidate_id"],
        "geometry": np_scope["geometry_scope"],
        "existing_scope": {
            "wavelength_nm": np_scope["wavelength_scope"]["values_nm"],
            "u_x": np_scope["kx_over_k0_scope"]["allowed_values"],
            "ky_over_k0": np_scope["kx_over_k0_scope"]["ky_over_k0"],
            "polarization": np_scope["polarization_scope"]["formally_validated"],
            "stack": np_scope["interface_stack_scope"]["stack"],
            "response": np_scope["response_scope"]["supported_fields"],
        },
        "reference_stack_class": "STANDALONE_SEMI_INFINITE_SIO2_NP_RESPONSE",
        "missing_for_full_stage_a_target": [
            "P/X-like response at u_x=sin(-10), sin(-5), sin(+5), sin(+10)",
            "S/Y-like response at u_x=0 and the four oblique u_x values",
            "formal finite-SiO2 termination transfer to the frozen MDC interface",
            "formal polarization mapping from MDC x/z source channels to NP P/S inputs",
        ],
        "no_extrapolation": True,
        "stage_a_integrated_matrix_is_not_eta_provider": True,
        "stage_a_matrix_exclusion_reason": "Integrated MDC+spacer+NP response already includes reflection, interference, and joint feedback.",
        "source_scope_sha256": sha(np_scope_path),
        "handoff_manifest_sha256": sha(np_handoff_path),
    }

    reference_plane = {
        "schema_version": "level1_reference_plane_mapping_v1",
        "status": "FROZEN_CONCEPTUAL_MAPPING_PROVIDER_INPUT_PENDING",
        "mdc_reference_plane": {
            "id": "MDC_TOP_UPWARD_OUTPUT_PLANE",
            "coordinate_system": "coupling_stage_a_coordinate_convention_v1",
            "z_nm": 975,
            "medium_above": "APCD_SIO2_NATIVE_M1",
            "role": "raw upward MDC power enters the continuous SiO2 separation region",
            "legacy_monitor_transfer_allowed": False,
        },
        "np_reference_plane": {
            "id": "NP_PILLAR_BOTTOM",
            "z_nm": 1212,
            "incident_medium": "APCD_SIO2_NATIVE_M1",
            "reference_medium": "APCD_SIO2_NATIVE_M1",
            "output_medium": "Air",
            "role": "NP modular response input plane at the pillar bottom",
        },
        "conserved_variable": {
            "primary": "u_x=kx/k0",
            "ky_over_k0": 0.0,
            "theta_air": "derived label only",
            "no_internal_theta_substitution": True,
        },
        "provider_classes": {
            "A": "standalone semi-infinite SiO2 NP response",
            "B": "finite-support NP response",
            "C": "integrated MDC+NP Stage-A response",
            "mixing_forbidden": True,
        },
        "normalization": "eta_NP,+1 is normalized to incident power at the NP pillar-bottom reference plane; absolute LEE/EQE claims are forbidden.",
        "consumption_gate": "blocked until formal MDC profile and polarization mapping are available",
    }

    polarization_mapping = {
        "schema_version": "level1_polarization_mapping_v1",
        "status": "HARD_GATE_LEVEL1_POLARIZATION_MAPPING_INPUT_INSUFFICIENT",
        "mdc_channels": ["x_dipole", "z_dipole"],
        "mdc_channel_type": "2D emission-source channels",
        "np_channels": ["P_XLIKE", "S_YLIKE"],
        "np_channel_type": "incident plane-wave polarization branches",
        "direct_mapping_allowed": False,
        "prohibited_mappings": ["x_dipole_to_P_XLIKE", "z_dipole_to_S_YLIKE", "x_dipole_to_S_YLIKE", "z_dipole_to_P_XLIKE"],
        "evidence_gap": [
            "legacy MDC assets provide scalar raw upward monitor power, not polarization-resolved interface fields",
            "formal ZL1 six-case raw profile is absent",
            "NP y/S response is not validated in the frozen NP source scope",
        ],
        "required_resolution": [
            "formal TE-like/TM-like or equivalent interface-polarization-resolved MDC power channels",
            "a documented transformation to NP P/S branches",
            "formal similarity evidence before any P/S aggregation",
        ],
        "x_y_averaging": "NOT_JUSTIFIED",
    }

    grid_alignment = {
        "schema_version": "level1_grid_alignment_v1",
        "status": "PARTIAL_ALIGNMENT_NO_EXTRAPOLATION",
        "stage_a_closure_head": STAGE_A_CLOSURE_HEAD,
        "canonical_wavelength_nm": list(range(445, 456)),
        "wavelength_policy": "exact 1 nm points only",
        "canonical_stage_a_ux": [
            -0.17364817766693033,
            -0.08715574274765817,
            0.0,
            0.08715574274765817,
            0.17364817766693033,
        ],
        "existing_np_ux": [0.0],
        "existing_np_polarization": ["x"],
        "mdc_native_joint_tensor_shape_observed_elsewhere": [301, 2000],
        "mdc_native_joint_tensor_axis_order": ["wavelength_index", "angle_index"],
        "alignment_rules": [
            "use conserved u_x, not theta_air, as the primary join coordinate",
            "intersect exact source support before integration",
            "no interpolation or extrapolation of NP data",
            "no spectrum-times-angular-cut outer product for a joint MDC tensor",
            "theta labels are derived metadata only",
        ],
        "current_consumable_intersection": {
            "wavelength_nm": list(range(445, 456)),
            "u_x": [0.0],
            "polarization": ["x"],
            "status": "NP_STANDALONE_ONLY; MDC FORMAL PROVIDER MISSING",
        },
        "full_stage_a_validation_requires": {
            "state_count": 10,
            "new_np_state_count": 9,
            "state_definition": "5 u_x values x 2 P/S branches",
        },
    }

    quadrature = {
        "schema_version": "level1_quadrature_contract_v1",
        "status": "BLOCKED_UNRESOLVED_MDC_WEIGHT_SEMANTICS",
        "raw_first": True,
        "aggregation_order": [
            "raw power readback",
            "same-position P_position=0.5*P_x+0.5*P_z",
            "geometry P_geometry=(P_top+P_centroid+P_bottom)/3",
            "normalization",
            "derived metrics",
        ],
        "case_normalize_before_average": False,
        "y_dipole_auto_addition": False,
        "allowed_weight_semantics": [
            "raw density requiring explicit d_lambda*d_u_x quadrature",
            "raw probability mass already including quadrature",
        ],
        "resolved_weight_semantics": None,
        "required_identity": "sum(W_MDC_FDTD(lambda,u_x,channel)*quadrature)=1 per normalized profile",
        "joint_tensor_policy": "integrate the native joint tensor after exact axis readback; never synthesize an outer product",
        "integration_formula": "P_plus1_relative=P_MDC_up_FDTD*SUM[W_MDC_FDTD(lambda,u_x,channel)*eta_NP_plus1(lambda,u_x,polarization)*quadrature]",
        "numerical_consumption_allowed": False,
        "blocking_reason": "formal ZL1 profile asset must declare whether W contains Jacobian/quadrature or is a normalized density",
    }

    power_contract = {
        "schema_version": "level1_power_contract_v1",
        "status": "PARTIAL_LEGACY_DIAGNOSTIC_NOT_FORMAL",
        "formal_p_mdc": "P_MDC_up_FDTD",
        "formal_mdc_metric_name": "2D fixed-near-source-surface-normalized relative upward-output metric",
        "raw_power_first": True,
        "relative_normalization": "fixed physical R12 nm box / project-canonical equivalent, only after formal provider declaration",
        "legacy_status": {
            "source_normalized_power": "pending_no_verified_dipolepower_readback",
            "absolute_extraction": "forbidden",
            "absolute_LEE_EQE_Purcell": "forbidden",
        },
        "forbidden_labels": ["absolute LEE", "EQE", "Purcell", "absolute optical power", "3D extraction efficiency"],
        "no_case_normalize_then_average": True,
        "formal_provider_required": True,
    }

    evidence_assets = [
        asset(source_lock_path, "coupling source identity lock", "READ_ONLY"),
        asset(stage_a_lock_path, "immutable Stage-A baseline lock", "READ_ONLY"),
        asset(matrix_path, "immutable Stage-A integrated matrix", "READ_ONLY"),
        asset(legacy_manifest_path, "legacy MDC diagnostic manifest", "LEGACY_DIAGNOSTIC"),
        asset(legacy_audit_path, "legacy MDC diagnostic audit", "LEGACY_DIAGNOSTIC"),
        asset(legacy_cases_path, "legacy MDC source cases", "LEGACY_DIAGNOSTIC"),
        asset(legacy_validation_path, "legacy MDC validation", "LEGACY_DIAGNOSTIC"),
        asset(center_sim_manifest_path, "center MDC dipole simulation manifest", "LEGACY_DIAGNOSTIC"),
        asset(orientation_path, "center dipole orientation readback", "LEGACY_DIAGNOSTIC"),
        asset(mdc1d2_manifest_path, "978 nm single x-dipole validation", "EXCLUDED_WRONG_GEOMETRY"),
        asset(mdc1d2_comparison_path, "978 nm comparison", "EXCLUDED_WRONG_GEOMETRY"),
        asset(plane_wave_manifest_path, "ZL1 plane-wave transmission", "EXCLUDED_NOT_DIPOLE_INPUT"),
        asset(doe96_completion_path, "DOE96 joint tensor completion", "EXCLUDED_WRONG_GEOMETRY"),
        asset(doe96_quality_path, "DOE96 raw/aggregation quality audit", "EXCLUDED_WRONG_GEOMETRY"),
        asset(doe96_grid_path, "DOE96 native grid lock", "EXCLUDED_WRONG_GEOMETRY"),
        asset(np_scope_path, "NP formal source scope", "PARTIAL_FORMAL_ASSET"),
        asset(np_handoff_path, "NP coupling handoff", "PARTIAL_FORMAL_ASSET"),
    ]

    safety = {
        "this_turn_solver_entries": 0,
        "FDTD": 0,
        "TMM": 0,
        "RCWA": 0,
        "FEM": 0,
        "training": 0,
        "ML_inference": 0,
        "source_worktree_writes": 0,
        "sealed_reads": 0,
        "stage_a_reruns": 0,
        "integrated_level1_numerical_result": 0,
        "m1_model_consumption": 0,
    }

    handoff = {
        "schema_version": "traditional_stage_b_level1_handoff_v1",
        "task_id": "APCD_MDC_NP_COUPLING_V1_TRADITIONAL_STAGE_B_LEVEL1_HANDOFF_AND_INPUT_AUDIT",
        "status_class": "HARD_GATE",
        "status": "TRADITIONAL_STAGE_B_LEVEL1_HANDOFF_BLOCKED_LEVEL1_POLARIZATION_MAPPING_INPUT_INSUFFICIENT",
        "stage_a_baseline_immutable": {
            "closure_head": STAGE_A_CLOSURE_HEAD,
            "mdc_candidate_id": stage_a_identity["mdc_candidate_id"],
            "np_candidate_id": stage_a_identity["np_candidate_id"],
            "matrix_sha256": MATRIX_SHA,
            "matrix_rows": 110,
            "extra_spacer_nm": 237,
            "total_continuous_sio2_separation_nm": 316,
        },
        "coupling_level": "ONE_WAY_INCOHERENT_POWER_COUPLING",
        "formula": quadrature["integration_formula"],
        "providers": {
            "mdc": mdc_provider,
            "np": np_provider,
        },
        "contracts": {
            "reference_plane": reference_plane,
            "polarization_mapping": polarization_mapping,
            "grid_alignment": grid_alignment,
            "quadrature": quadrature,
            "power": power_contract,
        },
        "stage_a_matrix_np_provider_prohibition": {
            "prohibited": True,
            "reason": "Stage-A integrated matrix includes MDC reflection, MDC transmission, MDC-NP interference, and joint feedback; multiplying it by W_MDC would double count physics.",
        },
        "solver_budget_plan": {
            "status": "CONDITIONAL_NOT_AUTHORIZED",
            "current_turn_entries": 0,
            "mdc_missing_formal_cases": 6,
            "np_existing_formal_states": 1,
            "np_full_stage_a_target_states": 10,
            "np_missing_full_stage_a_states": 9,
            "np_case_definition": "one broadband direct response case per (u_x, polarization) over exact 445-455 nm points",
            "budget_not_authorized_until": [
                "polarization mapping hard gate resolved",
                "NP reference stack/plane transfer decision resolved",
                "formal MDC six-case source contract accepted",
            ],
            "do_not_count": ["Stage-A integrated 110 rows", "DOE96 576 historical solver calls", "legacy -400 nm diagnostics"],
        },
        "future_ml_provider": {
            "model_id": "MDC_HF_M1_GEOMETRY_CONDITIONED_DIRECT_FINAL_5SEED_V1",
            "status": "NOT_ACTIVATED_TRADITIONAL_STAGE_B",
            "checkpoint_loaded": False,
            "inference_run": False,
        },
        "evidence_assets": evidence_assets,
        "safety": safety,
        "next_action": "HARD_GATE_LEVEL1_POLARIZATION_MAPPING_INPUT_INSUFFICIENT",
    }

    report = f"""# Traditional Stage-B Level-1 Input Audit

Status: {handoff["status"]}

## Frozen Stage-A baseline

- Closure HEAD: {STAGE_A_CLOSURE_HEAD}
- MDC: P1_ZL1_ALTERNATIVE_G3_A3, 975 nm, top SiO2 79 nm
- Extra spacer: 237 nm; continuous SiO2 separation: 316 nm
- NP: NP_K6X_125_135_150_175_190_210
- Integrated matrix: 445-455 nm exact 1 nm, 5 angles, P/S branches, 110 rows
- Matrix SHA256: {MATRIX_SHA}

## MDC Level-1 provider

Decision: REQUIRES_DIRECT_SOLVER.

The only ZL1 dipole package found is legacy diagnostic data with source y=-400 nm, five x-offset positions (-1000, -500, 0, 500, 1000 nm), x/z dipoles, and 448-452 nm at 0.1 nm spacing. It is not the formal top/centroid/bottom z contract. A separate native-M1 ZL1 result is x-dipole only and uses a 978 nm stack. DOE96 contains 301x2000 joint tensors, but for 96 new DOE geometries and no frozen ZL1 geometry hash match.

Required formal MDC input: six real 2D FDTD cases at z=-171.5/-276.0/-380.5 nm, x/z dipoles, raw upward power, exact source/grid identity, and normalized W/P semantics.

## NP Level-1 provider

Decision: PARTIAL_EXISTING_ASSET.

Existing formal scope is standalone SiO2 substrate -> Native-M1 TiO2 K6 -> Air, exact 445-455 nm, u_x=0, x-pol only. It does not support y/S, oblique u_x, finite-SiO2 termination transfer, or the final MDC-NP stack. The Stage-A integrated 110-row matrix is excluded as an eta provider.

## Interface / mapping

- MDC conceptual output plane: z=975 nm, upward into Native-M1 SiO2.
- NP input plane: pillar bottom z=1212 nm, incident/reference medium Native-M1 SiO2.
- Primary variable: conserved u_x=kx/k0; theta_air is derived only.
- Raw-first aggregation: 0.5 x + 0.5 z per position, then top/centroid/bottom geometry average, then normalization.
- Polarization mapping is a hard gate: MDC x/z source channels are not NP P/S branches. No x->P or z->S mapping is permitted.
- Quadrature weight semantics remain unresolved until formal MDC profile metadata is supplied.

## Solver budget planning

No solver was run. Conditional minimum planning is 6 MDC formal FDTD cases plus 9 missing NP (u_x, polarization) broadband response states for the full Stage-A 5-angle/P-S target. These are planning numbers only and are not authorization.

## Safety

FDTD/TMM/RCWA/FEM/training/ML/integrated Level-1 numerical entries this turn: all zero. Source worktrees were read-only and unchanged.
"""
    out = {
        "contracts/coupling/traditional_stage_b_level1_handoff_v1.json": handoff,
        "contracts/coupling/level1_mdc_real_fdtd_provider_v1.json": mdc_provider,
        "contracts/coupling/level1_np_response_provider_v1.json": np_provider,
        "contracts/coupling/level1_reference_plane_mapping_v1.json": reference_plane,
        "contracts/coupling/level1_polarization_mapping_v1.json": polarization_mapping,
        "contracts/coupling/level1_grid_alignment_v1.json": grid_alignment,
        "contracts/coupling/level1_quadrature_contract_v1.json": quadrature,
        "contracts/coupling/level1_power_contract_v1.json": power_contract,
        "reports/coupling/traditional_stage_b_level1_input_audit_v1.md": report,
        "outputs/mdc_np_coupling_v1/traditional_stage_b_level1_readiness_v1.json": {
            "schema_version": "traditional_stage_b_level1_readiness_v1",
            "status": handoff["status"],
            "status_class": handoff["status_class"],
            "stage_a_closure_head": STAGE_A_CLOSURE_HEAD,
            "mdc_provider_status": mdc_provider["provider_status"],
            "np_provider_status": np_provider["provider_status"],
            "polarization_mapping_status": polarization_mapping["status"],
            "reference_plane_status": reference_plane["status"],
            "grid_status": grid_alignment["status"],
            "quadrature_status": quadrature["status"],
            "solver_budget_plan": handoff["solver_budget_plan"],
            "safety": safety,
            "next_action": handoff["next_action"],
            "contract_paths": list(handoff["contracts"].keys()),
        },
    }
    for rel, data in out.items():
        path = ROOT / rel
        if path.suffix == ".md":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(data, encoding="utf-8")
        else:
            write_json(path, data)
    print(json.dumps({"status": handoff["status"], "files": list(out), "mdc": mdc_provider["provider_status"], "np": np_provider["provider_status"], "solver_entries": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
