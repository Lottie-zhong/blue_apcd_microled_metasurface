from __future__ import annotations

import hashlib
import json
import math
import subprocess
from pathlib import Path
from statistics import mean, pstdev

ROOT = Path(__file__).resolve().parents[2]
W = [float(x) for x in range(445, 456)]
MATRIX = ROOT / "reports/coupling/stage_a_frozen_spacer_polarization_angle_broadband_matrix_v1.json"
MATRIX_SHA = "d400c51cfa557aeffdefb09567dbe20705c50d915bc9a5ddd570281535265bf6"
COUPLING_COMMIT = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
MATERIALS = ["APCD_GAN_NATIVE_M1", "APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1"]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def file_asset(asset_id, path, role):
    return {
        "asset_id": asset_id,
        "role": role,
        "path": str(path),
        "relative_path": str(path.relative_to(ROOT)).replace("\\", "/") if path.is_relative_to(ROOT) else None,
        "sha256": sha(path),
        "source_commit": None,
        "coupling_commit": COUPLING_COMMIT,
        "read_only": True,
    }


def metric(path, label):
    value = load(path)
    return {
        "label": label,
        "case_id": value.get("case_id"),
        "control_group": value.get("control_group"),
        "result_path": str(path),
        "result_sha256": sha(path),
        **{key: value.get(key) for key in (
            "R_total", "T_total", "eta_plus1", "eta_zero", "eta_minus1",
            "eta_plus2", "directionality", "loss_or_residual",
            "residual_1_minus_R_minus_T", "theta_plus1_deg", "theta_out_plus1_deg"
        )},
    }


def broadband(path, label):
    value = load(path)
    rows = value["rows"]
    if len(rows) != 11 or any(
        not math.isclose(float(row["wavelength_nm"]), wavelength, abs_tol=1e-6)
        for row, wavelength in zip(rows, W)
    ):
        raise ValueError(f"{label}: invalid exact wavelength grid")
    eta = [float(row["eta_plus1"]) for row in rows]
    directionality = [float(row["directionality"]) for row in rows]
    return {
        "label": label,
        "case_id": value["case_id"],
        "result_path": str(path),
        "result_sha256": sha(path),
        "rows": 11,
        "eta_plus1_mean": mean(eta),
        "eta_plus1_min": min(eta),
        "eta_plus1_max": max(eta),
        "eta_plus1_std_population": pstdev(eta),
        "eta_plus1_range": max(eta) - min(eta),
        "mean_R": mean(float(row["R_total"]) for row in rows),
        "mean_T": mean(float(row["T_total"]) for row in rows),
        "mean_residual": mean(float(row["residual_1_minus_R_minus_T"]) for row in rows),
        "mean_directionality": mean(directionality),
        "min_directionality": min(directionality),
        "representative_445_450_455": [
            {
                "wavelength_nm": float(row["wavelength_nm"]),
                "eta_plus1": float(row["eta_plus1"]),
                "eta_zero": float(row["eta_zero"]),
                "eta_minus1": float(row["eta_minus1"]),
                "eta_plus2": float(row.get("eta_plus2", 0.0)),
                "R_total": float(row["R_total"]),
                "T_total": float(row["T_total"]),
                "residual": float(row["residual_1_minus_R_minus_T"]),
                "directionality": float(row["directionality"]),
            }
            for row in rows
            if float(row["wavelength_nm"]) in (445.0, 450.0, 455.0)
        ],
    }


def matrix_summary(matrix):
    if sha(MATRIX) != MATRIX_SHA or matrix.get("status") != "VALIDATED_110_ROWS":
        raise ValueError("110-row matrix identity/status failure")
    if len(matrix.get("rows", [])) != 110:
        raise ValueError("110-row matrix completeness failure")
    if not matrix["closure"]["all_rows_no_polarization_averaging"]:
        raise ValueError("polarization averaging flag failure")
    grouped = {}
    for row in matrix["rows"]:
        grouped.setdefault(row["case_id"], []).append(row)
        if row["no_polarization_averaging"] is not True:
            raise ValueError("matrix row averaging flag failure")
    if len(grouped) != 10 or any(len(rows) != 11 for rows in grouped.values()):
        raise ValueError("matrix state dimension failure")
    state_summary = []
    for case_id, rows in sorted(grouped.items()):
        eta = [float(row["eta_plus1"]) for row in rows]
        directionality = [float(row["directionality"]) for row in rows]
        state_summary.append({
            "case_id": case_id,
            "polarization_branch": rows[0]["polarization_branch"],
            "theta_air_in_label_deg": rows[0]["theta_air_in_label_deg"],
            "wavelength_count": 11,
            "eta_plus1_mean": mean(eta),
            "eta_plus1_min": min(eta),
            "eta_plus1_max": max(eta),
            "eta_plus1_std_population": pstdev(eta),
            "eta_plus1_range": max(eta) - min(eta),
            "mean_R": mean(float(row["R_total"]) for row in rows),
            "mean_T": mean(float(row["T_total"]) for row in rows),
            "mean_residual": mean(float(row["residual_1_minus_R_minus_T"]) for row in rows),
            "mean_directionality": mean(directionality),
            "min_directionality": min(directionality),
            "representative_445_450_455": [
                {key: row[key] for key in (
                    "wavelength_nm", "eta_plus1", "eta_zero", "eta_minus1",
                    "eta_plus2", "R_total", "T_total",
                    "residual_1_minus_R_minus_T", "directionality"
                )}
                for row in rows if float(row["wavelength_nm"]) in (445.0, 450.0, 455.0)
            ],
        })
    leakage = {}
    for row in matrix["rows"]:
        for item in row["order_arrays"]["transmitted"]:
            if int(item.get("m_y", 0)) == 0 and item.get("physical_propagation_direction") in (None, "+z"):
                leakage.setdefault(int(item["m"]), []).append(float(item.get("power_fraction_of_source", 0.0)))
    leakage_rows = [
        {"m": order, "mean_power_fraction_of_source": mean(values),
         "max_power_fraction_of_source": max(values), "row_count": len(values)}
        for order, values in leakage.items() if order != 1
    ]
    leakage_rows.sort(key=lambda row: row["mean_power_fraction_of_source"], reverse=True)
    return {
        "matrix_path": str(MATRIX),
        "matrix_sha256": MATRIX_SHA,
        "status": matrix["status"],
        "rows": 110,
        "incident_states": 10,
        "wavelengths_per_state": 11,
        "closure": matrix["closure"],
        "by_incident_state": state_summary,
        "major_leakage_orders_global": leakage_rows[:8],
        "representative_wavelengths_nm": [445, 450, 455],
    }


def main():
    source_lock_path = ROOT / "contracts/coupling/source_branch_lock_v1.json"
    source_lock = load(source_lock_path)
    sources = {}
    source_assets = []
    for name, source in source_lock["sources"].items():
        selected = {key: source.get(key) for key in (
            "worktree", "branch", "commit", "model_id", "package_id",
            "candidate", "model_scope", "scope_decision", "normalized_scope_enum"
        ) if key in source}
        checks = []
        for key in ("artifact_registry", "completion_manifest", "model_manifest",
                    "package_manifest", "formal_scope_artifact", "handoff_manifest"):
            value = source.get(key)
            if not value:
                continue
            path = Path(value)
            expected = source.get(f"{key}_sha256")
            actual = sha(path) if path.exists() else None
            check = {"field": key, "path": str(path), "expected_sha256": expected,
                     "actual_sha256": actual, "pass": bool(actual and actual == expected)}
            checks.append(check)
            if not check["pass"]:
                raise ValueError(f"source SHA failure: {name}/{key}")
            source_assets.append({
                "asset_id": f"{name}_{key}", "role": "source_identity_artifact",
                "path": str(path), "sha256": actual, "source_commit": source.get("commit"),
                "coupling_commit": COUPLING_COMMIT, "read_only": True,
            })
        selected["sha_verification"] = checks
        selected["read_only"] = True
        sources[name] = selected

    interface_path = ROOT / "contracts/coupling/interface_stack_v1.json"
    coordinate_path = ROOT / "contracts/coupling/coordinate_convention_v1.json"
    grid_path = ROOT / "contracts/coupling/grid_alignment_contract_v1.json"
    one_way_path = ROOT / "contracts/coupling/one_way_power_interface_v1.json"
    interface = load(interface_path)
    coordinate = load(coordinate_path)
    grid = load(grid_path)
    one_way = load(one_way_path)
    mdc = next(item for item in interface["stack"] if item["role"] == "mdc")
    extra = next(item for item in interface["stack"] if item["role"] == "extra_spacer")
    expected_layers = ["TiO2:44nm", "SiO2:79nm", "TiO2:44nm", "SiO2:79nm",
                       "TiO2:44nm", "SiO2:316nm", "TiO2:44nm", "SiO2:79nm",
                       "TiO2:44nm", "SiO2:79nm", "TiO2:44nm", "SiO2:79nm"]
    if mdc["layers_from_gan_up"] != expected_layers or mdc["thickness_nm"] != 975:
        raise ValueError("MDC geometry identity failure")
    if mdc["top_termination"] != "APCD_SIO2_NATIVE_M1:79nm" or extra["thickness_nm"] != 237:
        raise ValueError("interface termination/spacer failure")
    if interface["total_sio2_separation_nm"] != 316 or coordinate["mdc_z_extent_nm"] != [0, 975]:
        raise ValueError("separation/coordinate identity failure")
    if grid["extrapolation"] != "forbidden" or grid["theta_air_policy"] != "derived metadata only":
        raise ValueError("grid contract failure")
    if one_way["complex_amplitude_feedback"] is not False:
        raise ValueError("complex feedback must remain disabled")

    t237_audit_path = ROOT / "outputs/coupling/stage_a_nb_t237_445_455_xpol_normal_v1/post_fsp_identity_audit.json"
    t237_audit = load(t237_audit_path)
    pillars = t237_audit["readback"]["np_pillars"]
    if {round(float(x["z_min_nm"]), 6) for x in pillars} != {1212.0} or {round(float(x["z_max_nm"]), 6) for x in pillars} != {1712.0}:
        raise ValueError("T237 coordinate readback failure")
    helper_manifest = load(ROOT / "outputs/coupling/stage_a_frozen_spacer_445_455_polarization_angle_broadband_v1/STAGE_A_BB_XP5_445_455NM_P_XLIKE/setup_manifest.json")
    helper_path = Path(helper_manifest["material_helper_path"])
    if not helper_path.exists() or sha(helper_path) != helper_manifest["material_helper_sha256"]:
        raise ValueError("native material helper SHA failure")
    if any(not t237_audit["readback"]["materials"].get(material, {}).get("present") for material in MATERIALS):
        raise ValueError("native material readback failure")

    matrix = load(MATRIX)
    matrix_data = matrix_summary(matrix)
    controls = {
        label: metric(ROOT / rel, label)
        for label, rel in {
            "B0": "outputs/coupling/stage_a_b0_450nm_xpol_normal_v1/results/result.json",
            "B1": "outputs/coupling/stage_a_b1_450nm_xpol_normal_v1/results/result.json",
            "B2": "outputs/coupling/stage_a_b2_450nm_xpol_normal_v1/results/result.json",
            "B3": "outputs/coupling/stage_a_450nm_xpol_normal_textra0_golden_fixture_v1/results/result.json",
        }.items()
    }
    spacer_paths = {
        "t_extra_0_B3": "outputs/coupling/stage_a_450nm_xpol_normal_textra0_golden_fixture_v1/results/result.json",
        "t_extra_79": "outputs/coupling/stage_a_s79_450nm_xpol_normal_v1/results/result.json",
        "t_extra_158": "outputs/coupling/stage_a_s158_450nm_xpol_normal_v1/results/result.json",
        "t_extra_237": "outputs/coupling/stage_a_s237_450nm_xpol_normal_v1/results/result.json",
    }
    spacer_rows = {label: metric(ROOT / rel, label) for label, rel in spacer_paths.items()}
    spacer_sequence = [spacer_rows[label]["eta_plus1"] for label in spacer_paths]
    if any(value is None for value in spacer_sequence):
        raise ValueError("spacer metric missing")
    selection_path = ROOT / "reports/coupling/stage_a_broadband_spacer_selection_v1.json"
    selection = load(selection_path)
    if selection["selection"]["frozen_spacer_nm"] != 237:
        raise ValueError("selection freeze mismatch")
    broadband_rows = {
        label: broadband(ROOT / rel, label)
        for label, rel in {
            "T0": "outputs/coupling/stage_a_nb_t0_445_455_xpol_normal_v1/results/result.json",
            "T79": "outputs/coupling/stage_a_nb_t79_445_455_xpol_normal_v1/results/result.json",
            "T237": "outputs/coupling/stage_a_nb_t237_445_455_xpol_normal_v1/results/result.json",
        }.items()
    }
    matrix450_path = ROOT / "reports/coupling/stage_a_polarization_angle_matrix_450_v1.json"
    matrix450 = load(matrix450_path)
    if matrix450["decision"] != "POLARIZATION_ANGLE_450NM_MATRIX_VALIDATED":
        raise ValueError("450 nm matrix validation failure")

    old_gate = ROOT / "reports/coupling/stage_a_polarization_angle_broadband_hard_gate_v1.json"
    old_replay = ROOT / "reports/coupling/stage_a_xp5_replay_hard_gate_v1.json"
    historical = {
        "invalid_historical_output_root": str(ROOT / "outputs/coupling/stage_a_polarization_angle_broadband_445_455_v1/STAGE_A_BB_XP5_445_455NM_P_XLIKE"),
        "hard_gate_report": file_asset("historical_xp5_hard_gate", old_gate, "historical_invalid_xp5_hard_gate"),
        "replay_failure_report": file_asset("historical_xp5_replay", old_replay, "historical_xp5_replay_failure"),
        "excluded_from_final_matrix": True,
        "final_valid_matrix_path": str(MATRIX),
        "replay_protection_preserved": True,
    }
    framework_paths = {
        "mdc_provider": "src/apcd_coupling/adapters.py",
        "np_provider": "src/apcd_coupling/adapters.py",
        "interface_provider": "src/apcd_coupling/joint_stack_builder.py",
        "incident_state_provider": "src/apcd_coupling/incident_state.py",
        "joint_builder": "src/apcd_coupling/joint_stack_builder.py",
        "solver_runner": "scripts/coupling/run_control_group_case.py",
        "order_extractor": "scripts/coupling/extract_broadband_polarization_angle_case.py",
        "result_schema": "src/apcd_coupling/result_schema.py",
        "broadband_result_schema": "src/apcd_coupling/broadband_result_schema.py",
        "comparison_engine": "src/apcd_coupling/comparison_engine.py",
        "provenance_registry": "src/apcd_coupling/provenance.py",
        "replay_registry": "registries/coupling/stage_a_frozen_spacer_broadband_phase_registry_v1.json",
    }
    framework = {}
    for name, rel in framework_paths.items():
        path = ROOT / rel
        if not path.exists():
            raise ValueError(f"framework path missing: {rel}")
        framework[name] = {"path": str(path), "relative_path": rel, "sha256": sha(path), "status": "FROZEN_REUSABLE_FRAMEWORK"}
    framework["provider_contract"] = {
        "traditional_mdc_provider": "ZL1",
        "traditional_np_provider": "RUN3A",
        "interface_provider": "MDC_ENDING_SIO2_79NM_PLUS_EXTRA_SIO2_237NM",
        "future_ml_replacement_rule": "replace MDC and/or NP provider only; preserve interface, solver and metric contracts",
    }
    phase = load(ROOT / "registries/coupling/stage_a_frozen_spacer_broadband_phase_registry_v1.json")
    if phase["status"] != "STAGE_A_FROZEN_SPACER_445_455_POLARIZATION_ANGLE_BROADBAND_COMPLETED" or phase["entered"] != 9 or phase["completed"] != 9:
        raise ValueError("broadband phase not completed")

    identity = {
        "mdc_candidate_id": "P1_ZL1_ALTERNATIVE_G3_A3",
        "mdc_name": "ZL-1 alternative",
        "mdc_layer_count": 12,
        "mdc_layer_sequence": expected_layers,
        "mdc_total_thickness_nm": 975,
        "mdc_top_sio2_nm": 79,
        "extra_spacer_nm": 237,
        "total_continuous_sio2_separation_nm": 316,
        "np_candidate_id": "NP_K6X_125_135_150_175_190_210",
        "np_name": "RUN3A phase-oriented K6-x",
        "np_K": 6,
        "np_period_x_nm": 1740,
        "np_period_y_nm": 290,
        "np_pillar_height_nm": 500,
        "np_diameters_nm": [125, 135, 150, 175, 190, 210],
        "interface_id": interface["interface_id"],
        "coordinate_contract_id": coordinate["schema_version"],
        "z_coordinates_nm": {"joint_z_zero": 0, "mdc_top": 975, "extra_spacer_top_and_pillar_bottom": 1212, "pillar_top": 1712},
        "layer_12_is_79_not_316": True,
        "316_is_continuous_separation_not_mdc_layer_12": True,
        "material_contract_id": "MDC_NATIVE_M1",
        "material_ids": MATERIALS,
        "material_helper": {"path": str(helper_path), "sha256": helper_manifest["material_helper_sha256"], "canonical_identity": "scripts/apcd_native_materials.py", "source_commit": sources["mdc"]["commit"]},
    }
    non_monotonic = not (
        all(a <= b for a, b in zip(spacer_sequence, spacer_sequence[1:]))
        or all(a >= b for a, b in zip(spacer_sequence, spacer_sequence[1:]))
    )
    summary = {
        "schema_version": "traditional_stage_a_baseline_summary_v1",
        "status": "TRADITIONAL_STAGE_A_BASELINE_FROZEN",
        "closure_state": "APCD_MDC_NP_TRADITIONAL_STAGE_A_BASELINE_CLOSED",
        "task_id": "APCD_MDC_NP_COUPLING_V1_TRADITIONAL_STAGE_A_BASELINE_CLOSURE",
        "coupling_worktree": str(ROOT),
        "branch": "work/mdc-np-coupling-v1",
        "coupling_commit": COUPLING_COMMIT,
        "identity": identity,
        "source_identities": sources,
        "validated_domain": {
            "wavelength_nm": W,
            "theta_air_labels_deg": [-10, -5, 0, 5, 10],
            "incident_ux_states": [math.sin(math.radians(-10)), math.sin(math.radians(-5)), 0.0, math.sin(math.radians(5)), math.sin(math.radians(10))],
            "polarization_branches": ["P_XLIKE", "S_YLIKE"],
            "ky_over_k0": 0.0,
            "angle_convention_id": "air_side_far_field_conserved_real_kx_v1",
            "theta_air_is_derived": True,
        },
        "evidence": {
            "B0_B1_B2_B3": controls,
            "spacer_sensitivity_450nm": {"selection_policy": file_asset("spacer_selection", selection_path, "broadband_spacer_selection_policy"), "selection": selection["selection"], "rows": spacer_rows, "non_monotonic": non_monotonic},
            "broadband_spacer_comparison": broadband_rows,
            "polarization_angle_matrix_450nm": {"path": str(matrix450_path), "sha256": sha(matrix450_path), "decision": matrix450["decision"], "rows": matrix450["matrix_rows"], "validation": matrix450["validation"]},
            "broadband_matrix_110": matrix_data,
        },
        "performance": {"controls_450nm": controls, "spacer_450nm": spacer_rows, "broadband_T0_T79_T237": broadband_rows, "broadband_110": matrix_data},
        "conclusions": {
            "finite_support_effect": {"standalone_eta_plus1": 0.7459706928105845, "B2_eta_plus1": controls["B2"]["eta_plus1"], "B3_eta_plus1": controls["B3"]["eta_plus1"], "statement": "Finite support/underlying joint stack changes the standalone RUN3A absolute eta(+1); no standalone value is transferred as a joint prediction."},
            "steering_directionality": {"state_minimum": min(x["min_directionality"] for x in matrix_data["by_incident_state"]), "state_mean_minimum": min(x["mean_directionality"] for x in matrix_data["by_incident_state"]), "statement": "The accepted m=+1 order remains physical +x; directionality is state-dependent and not uniformly ideal."},
            "spacer_response": {"eta_plus1_by_spacer_450nm": spacer_sequence, "non_monotonic": non_monotonic, "statement": "The 450 nm spacer response is non-monotonic, consistent with phase/interference sensitivity."},
            "freeze_scope": {"extra_spacer_nm": 237, "selection_scope": "445-455 nm x-pol normal-incidence selection", "later_use": "P/S and +/-5/+/-10 degree characterization/validation", "global_optimum_claim": False, "statement": "237 nm is a frozen traditional Stage-A interface parameter, not a full-domain optimized spacer."},
        },
        "framework": framework,
        "future_ml_handoff": {"MDC_LEVEL0_PROVIDER": "NOT_ACTIVATED_IN_THIS_TASK", "NP_LEVEL0_PROVIDER": "NOT_ACTIVATED_IN_THIS_TASK", "MDC_DIRECT_FDTD_PROVIDER": "NOT_ACTIVATED_IN_THIS_TASK", "NP_DIRECT_FULLWAVE_PROVIDER": "NOT_ACTIVATED_IN_THIS_TASK", "future_mdc_frozen_m1": "MDC_HF_M1_GEOMETRY_CONDITIONED_DIRECT_FINAL_5SEED_V1", "checkpoint_loaded": False, "inference_run": False},
        "level_1_preparation": {"schema_contract": "contracts/coupling/one_way_power_interface_v1.json", "numerical_result": "NOT_RUN", "mdc_real_fdtd_profile_used": False, "m1_profile_used": False, "future_formula": "P_plus1_relative = P_MDC,up,FDTD * integral/sum[W_MDC,FDTD * eta_NP,+1]"},
        "historical_provenance": historical,
        "verification": {"tests": {"status": "PENDING", "command": "N:\\anaconda_envs\\RCP_LCP\\python.exe -m pytest tests/coupling -q"}, "source_sha_valid": True, "matrix_identity_valid": True, "interface_identity_valid": True, "framework_identity_valid": True},
        "safety": {"this_closure_solver_entries": 0, "FDTD": 0, "TMM": 0, "RCWA": 0, "FEM": 0, "training": 0, "ML_inference": 0, "joint_screening": 0, "source_worktree_writes": 0, "sealed_reads": 0, "new_spacer_optimization": 0, "new_angle_wavelength_polarization_runs": 0},
    }
    lock = {
        "schema_version": "traditional_stage_a_baseline_lock_v1",
        "status": summary["status"],
        "closure_state": summary["closure_state"],
        "task_id": summary["task_id"],
        "coupling_worktree": str(ROOT),
        "branch": "work/mdc-np-coupling-v1",
        "coupling_commit": COUPLING_COMMIT,
        "source_identities": sources,
        "physical_identity": identity,
        "interface_contract": file_asset("interface", interface_path, "frozen_interface_contract"),
        "coordinate_contract": file_asset("coordinate", coordinate_path, "coordinate_contract"),
        "grid_contract": file_asset("grid", grid_path, "wavelength_kx_grid_contract"),
        "framework": framework,
        "evidence_package": summary["evidence"],
        "future_boundaries": {"stage_b_level_1_numerical_result": "NOT_RUN", "ml_inference": "NOT_ACTIVATED_IN_THIS_TASK", "micro_led_full_device": "NOT_IN_SCOPE", "global_spacer_optimization": "NOT_CLAIMED"},
        "historical_provenance": historical,
        "safety": summary["safety"],
    }
    out_lock = ROOT / "contracts/coupling/traditional_stage_a_baseline_lock_v1.json"
    out_summary = ROOT / "reports/coupling/traditional_stage_a_baseline_summary_v1.json"
    out_report = ROOT / "reports/coupling/traditional_stage_a_baseline_closure_v1.md"
    out_manifest = ROOT / "registries/coupling/traditional_stage_a_baseline_completion_manifest_v1.json"
    out_assets = ROOT / "registries/coupling/traditional_stage_a_asset_registry_v1.json"
    manifest = {
        "schema_version": "traditional_stage_a_baseline_completion_manifest_v1",
        "status": summary["status"],
        "closure_state": summary["closure_state"],
        "task_id": summary["task_id"],
        "coupling_commit": COUPLING_COMMIT,
        "required_checks": {"source_assets_resolved": True, "all_source_sha_verified": True, "mdc_top_sio2_79_nm": True, "extra_spacer_237_nm": True, "total_separation_316_nm": True, "layer_12_not_316_nm": True, "native_material_contract": True, "coordinate_contract": True, "B0_B1_B2_B3_evidence": True, "spacer_0_79_158_237_evidence": True, "T0_T79_T237_broadband_evidence": True, "450_matrix_validated": True, "110_row_matrix_validated": True, "framework_provider_contract": True, "future_ml_inactive": True, "level_1_numerical_result_not_run": True, "historical_invalid_xp5_excluded": True, "replay_protection_preserved": True},
        "artifact_paths": {"lock": str(out_lock), "summary": str(out_summary), "closure_report": str(out_report), "asset_registry": str(out_assets), "matrix_110": str(MATRIX)},
        "tests": summary["verification"]["tests"],
        "safety": summary["safety"],
        "replay_protection": {"enabled": True, "phase_registry_path": str(ROOT / "registries/coupling/stage_a_frozen_spacer_broadband_phase_registry_v1.json"), "historical_failure_retained": True},
    }
    write_json(out_lock, lock)
    write_json(out_summary, summary)
    out_report.write_text("# Traditional Stage-A Baseline Closure\n\nStatus: TRADITIONAL_STAGE_A_BASELINE_FROZEN\n\nClosure state: APCD_MDC_NP_TRADITIONAL_STAGE_A_BASELINE_CLOSED\n\nFrozen identity: ZL-1 alternative + 79 nm MDC top SiO2 + 237 nm extra SiO2 + RUN3A K6-x.\n\nThe 316 nm value is continuous separation, not MDC layer 12. The validated domain is 445-455 nm at 1 nm, five air-side angle labels, and separate P_XLIKE/S_YLIKE branches with no polarization averaging.\n\nEvidence and exact SHA values are in traditional_stage_a_baseline_summary_v1.json and traditional_stage_a_asset_registry_v1.json. Historical invalid XP5/replay-failure provenance is retained and excluded from the final matrix.\n\nLevel-1 numerical coupling, ML inference, training, joint screening, and full-device claims are NOT RUN in this closure.\n", encoding="utf-8")
    write_json(out_manifest, manifest)
    asset_paths = {
        "baseline_lock": (out_lock, "formal_traditional_baseline_lock"),
        "baseline_summary": (out_summary, "machine_readable_traditional_baseline_summary"),
        "closure_report": (out_report, "traditional_baseline_closure_report"),
        "completion_manifest": (out_manifest, "traditional_baseline_completion_manifest"),
        "source_branch_lock": (source_lock_path, "source_identity_lock"),
        "interface_stack": (interface_path, "interface_contract"),
        "coordinate_contract": (coordinate_path, "coordinate_contract"),
        "grid_contract": (grid_path, "grid_contract"),
        "one_way_power_interface": (one_way_path, "future_level_1_schema"),
        "control_registry": (ROOT / "registries/coupling/stage_a_control_groups_result_registry_v1.json", "B0_B1_B2_B3_registry"),
        "spacer_registry": (ROOT / "registries/coupling/stage_a_spacer_sensitivity_result_registry_v1.json", "spacer_registry"),
        "spacer_selection": (selection_path, "spacer_selection_policy"),
        "matrix_450": (matrix450_path, "450_nm_polarization_angle_matrix"),
        "matrix_110": (MATRIX, "110_row_broadband_matrix"),
        "matrix_110_csv": (ROOT / "reports/coupling/stage_a_frozen_spacer_polarization_angle_broadband_matrix_v1.csv", "110_row_broadband_matrix_csv"),
        "historical_xp5_hard_gate": (old_gate, "historical_invalid_xp5_gate"),
        "historical_xp5_replay": (old_replay, "historical_xp5_replay_failure"),
    }
    assets = [file_asset(asset_id, path, role) for asset_id, (path, role) in asset_paths.items()]
    assets.extend(source_assets)
    for name, data in framework.items():
        if name != "provider_contract":
            assets.append({"asset_id": "framework_" + name, "role": "reusable_framework", "path": data["path"], "relative_path": data["relative_path"], "sha256": data["sha256"], "source_commit": None, "coupling_commit": COUPLING_COMMIT, "read_only": True})
    control_paths = {
        "B0": "outputs/coupling/stage_a_b0_450nm_xpol_normal_v1/results/result.json",
        "B1": "outputs/coupling/stage_a_b1_450nm_xpol_normal_v1/results/result.json",
        "B2": "outputs/coupling/stage_a_b2_450nm_xpol_normal_v1/results/result.json",
        "B3": "outputs/coupling/stage_a_450nm_xpol_normal_textra0_golden_fixture_v1/results/result.json",
    }
    broadband_paths = {
        "T0": "outputs/coupling/stage_a_nb_t0_445_455_xpol_normal_v1/results/result.json",
        "T79": "outputs/coupling/stage_a_nb_t79_445_455_xpol_normal_v1/results/result.json",
        "T237": "outputs/coupling/stage_a_nb_t237_445_455_xpol_normal_v1/results/result.json",
    }
    for label, rel in {**control_paths, **spacer_paths, **broadband_paths}.items():
        assets.append(file_asset(label, ROOT / rel, "formal_result_asset"))
    assets.append(file_asset("T237_identity_audit", t237_audit_path, "T237_readback_identity_audit"))
    write_json(out_assets, {"schema_version": "traditional_stage_a_asset_registry_v1", "status": summary["status"], "closure_state": summary["closure_state"], "coupling_commit": COUPLING_COMMIT, "baseline_lock_path": str(out_lock), "baseline_summary_path": str(out_summary), "closure_report_path": str(out_report), "completion_manifest_path": str(out_manifest), "assets": assets, "asset_count": len(assets), "large_artifact_policy": {"fsp_committed": False, "raw_monitor_arrays_committed": False, "large_solver_assets_committed": False}})
    print(json.dumps({"status": summary["status"], "closure_state": summary["closure_state"], "coupling_commit": COUPLING_COMMIT, "lock": str(out_lock), "summary": str(out_summary), "report": str(out_report), "manifest": str(out_manifest), "asset_registry": str(out_assets)}, sort_keys=True))


if __name__ == "__main__":
    main()
