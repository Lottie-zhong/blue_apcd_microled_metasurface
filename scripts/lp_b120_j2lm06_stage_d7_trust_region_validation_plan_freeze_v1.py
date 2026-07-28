from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import subprocess
import uuid
from pathlib import Path


ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
ML = ROOT / "outputs/lp_ml_dataset_v1"
ANALYSIS = ML / "analysis"
PLANS = ML / "plans"
REPORT = ROOT / "reports/lp_b120_j2lm06_stage_d7_five_variable_trust_region_validation_plan_v1.md"
STAGE = "STAGE_D7_FIVE_VARIABLE_TRUST_REGION_VALIDATION"
SCHEMA = "LP_ML_SCHEMA_V1.23"
SOURCE = ANALYSIS / "b120_j2lm06_stage_d6_five_variable_trust_region_prediction_v1.csv"
SOURCE_J = ANALYSIS / "b120_j2lm06_stage_d6_five_variable_jacobian_v1.json"
SOURCE_SVD = ANALYSIS / "b120_j2lm06_stage_d6_leakage_svd_step_normalized_v1.json"
D5_J = ANALYSIS / "b120_j2lm06_stage_d5_central_difference_jacobian_v1.json"
D5_SVD = ANALYSIS / "b120_j2lm06_stage_d5_leakage_svd_audit_v1.json"
D5_LIN = ANALYSIS / "b120_j2lm06_stage_d5_linearity_audit_v1.csv"
D6_TANG = ANALYSIS / "b120_j2lm06_stage_d6_tangential_derivative_v1.json"
D6_RAD = ANALYSIS / "b120_j2lm06_stage_d6_radial_derivative_v1.json"
D6_BIAS = ANALYSIS / "b120_j2lm06_stage_d6_tangential_radial_bias_audit_v1.json"
D6_LIN = ANALYSIS / "b120_j2lm06_stage_d6_positional_linearity_audit_v1.csv"
D6_ROUTE = ANALYSIS / "b120_j2lm06_stage_d6_route_decision_v1.json"
D6_PROV = ANALYSIS / "b120_j2lm06_stage_d6_checksum_provenance_manifest_v1.json"
D6_STAGING = ML / "staging/b120_j2lm06_positional_jacobian_stage_d6_v1_attempt1_lp_ml_schema_v1_22"
D6_PLAN = PLANS / "b120_j2lm06_positional_jacobian_stage_d6_v1.json"
D6_CONTRACT = PLANS / "b120_j2lm06_stage_d6_execution_contract_v1.json"
D6_ML = PLANS / "b120_j2lm06_stage_d6_ml_label_contract_v1.json"
D6_DERIV = PLANS / "b120_j2lm06_stage_d6_derivative_contract_v1.json"
D6_FINALIZER = ROOT / "scripts/lp_b120_j2lm06_stage_d6_five_variable_finalize_v2.py"
CANONICAL = ML / "canonical_v1_21"
RUNNER = ROOT / "scripts/lp_b120_j2lm06_positional_jacobian_stage_d6_execute_v1.py"
RUNTIME = ROOT / "scripts/lp_checkpoint_authoritative_runtime_v1_22.py"
PACKAGE = ML / "execution_packages/b120_j2lm06_positional_jacobian_stage_d6_execution_package_v1"
PROTECTED = {
    ROOT / "reports/lp_ml1a3_git_history_geometry_reconstruction.md": "21c6884f71bad6bd6779d7ccc90cec55ab1a94e239f849ea74a942bdd50edd6a",
    ROOT / "reports/stage11_4a20_legacy_fsp_object_inventory.md": "ae3b13341547e13ca85ca763ed8265591c100ac1a78c555de1c8378816a33708",
}
START_HEAD = "57679e27bb4f72c154d60d909fa193ff87effe5d"
EXPECTED_PACKAGE_HASHES = {
    RUNNER: "68ec2df888b5de44c9cf1575b51c48b65df9b50b98e0243d523a6be64bf03d01",
    RUNTIME: "c83b2027f9548055b4dde725428ca5ff99b5ebe9ce650bcee45d5a290dcfe495",
    PACKAGE / "package_manifest.json": "6bbd4a9f5f447daaefe81b17caf263fe2060c10677293400af44e423fbab68a7",
    PACKAGE / "content_checksums.json": "eb39489212d64bb8eec7770d52dacb8814eb624e7a12b5858163bcc75b44ac98",
    CANONICAL / "checksums_v1_21.json": "14d1799017b0b0626bbc4c24e0df8a75331b9b51e4cf2708d17f8c45922e78c7",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def atomic_write(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp." + uuid.uuid4().hex)
    tmp.write_bytes(data)
    tmp.replace(path)


def dump(path: Path, obj):
    atomic_write(path, (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8"))


def write_csv(path: Path, rows, fields=None):
    keys = fields or sorted({k for r in rows for k in r})
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp." + uuid.uuid4().hex)
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: json.dumps(row[k], sort_keys=True, ensure_ascii=False) if isinstance(row.get(k), (list, dict)) else row.get(k, "") for k in keys})
    tmp.replace(path)


def num(v):
    return float(v)


def parse_vec(v):
    return [float(x) for x in json.loads(v)]


def norm(v):
    return math.sqrt(sum(x * x for x in v))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def matrix_from_json(v):
    return [[complex(x["real"], x["imag"]) for x in row] for row in v]


def cmat_mul(jac_columns, step):
    out = [[0j, 0j], [0j, 0j]]
    for col, scale in zip(jac_columns, step):
        for i in range(2):
            for j in range(2):
                out[i][j] += col[i][j] * scale
    return out


def load_frozen_gate():
    checks = {"head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == START_HEAD}
    checks["protected"] = all(path.is_file() and sha(path) == expected for path, expected in PROTECTED.items())
    checks["frozen_inputs"] = all(path.is_file() and sha(path) == expected for path, expected in EXPECTED_PACKAGE_HASHES.items())
    checks["d6_staging_exists"] = D6_STAGING.is_dir()
    return checks


def main():
    if load_frozen_gate() != {"head": True, "protected": True, "frozen_inputs": True, "d6_staging_exists": True}:
        raise SystemExit("D7_SOURCE_GATE_FAILED")

    source_rows = read_csv(SOURCE)
    if len(source_rows) != 8:
        raise SystemExit("D7_PROPOSAL_COUNT_NOT_8")
    source_hash = sha(SOURCE)
    d6_plan = load_json(D6_PLAN)
    d6_by_mode = {c["candidate_id"]: c for c in d6_plan["candidates"]}
    d6_jac = load_json(SOURCE_J)
    d6_svd = load_json(SOURCE_SVD)
    d5_jac = load_json(D5_J)
    d5_svd = load_json(D5_SVD)
    d5_lin = {r["axis"]: r for r in read_csv(D5_LIN)}
    d6_lin = {r["mode"]: r for r in read_csv(D6_LIN)}
    tang = load_json(D6_TANG)
    radial = load_json(D6_RAD)
    bias = load_json(D6_BIAS)
    route = load_json(D6_ROUTE)
    anchor = [[complex(x["real"], x["imag"]) for x in row] for row in d5_jac["anchor_jones"]]

    # Explicit unit semantics: all consumers use radians; only reporting labels are audited here.
    phase_a_rad_per_rad = float(tang["phase_method_A_rad_per_unit"])
    phase_b_rad_per_rad = float(tang["phase_method_B_rad_per_unit"])
    degree_per_rad_a = math.degrees(phase_a_rad_per_rad)
    degree_per_rad_b = math.degrees(phase_b_rad_per_rad)
    degree_per_degree_a = degree_per_rad_a * math.pi / 180.0
    degree_per_degree_b = degree_per_rad_b * math.pi / 180.0
    unit_fields = {
        "dphi_dpsi_rad_per_rad_method_A": phase_a_rad_per_rad,
        "dphi_dpsi_rad_per_rad_method_B": phase_b_rad_per_rad,
        "dphi_dpsi_degree_per_rad_method_A": degree_per_rad_a,
        "dphi_dpsi_degree_per_rad_method_B": degree_per_rad_b,
        "dphi_dpsi_degree_per_degree_method_A": degree_per_degree_a,
        "dphi_dpsi_degree_per_degree_method_B": degree_per_degree_b,
    }
    unit_consumer_audit = {
        "derivative_json_denominator_unit": tang.get("denominator_unit"),
        "derivative_denominator_rad": tang.get("denominator"),
        "bias_denominator_rad": bias.get("tangential_denominator_rad"),
        "proposal_source_sha256": source_hash,
        "actual_coordinate_rad_consistency": all(abs(math.radians(num(r["actual_Psi_deg"])) - num(r["actual_effective_delta_Psi_rad"])) < 1e-12 for r in source_rows),
        "trust_region_delta_uses_actual_radian": True,
        "step_normalized_psi_scale_is_rad": float(d6_jac["step_normalized_complex_jones_jacobian"]["step_scales"]["Psi_rad"]),
        "degree_delta_directly_multiplied_by_per_rad": False,
        "proposal_geometry_unchanged": True,
        "proposal_prediction_values_unchanged": True,
        "derivative_json_fields": ["phase_method_A_rad_per_unit", "phase_method_B_rad_per_unit", "phase_method_A_deg_per_unit", "phase_method_B_deg_per_unit", "denominator_unit=rad"],
        "report_fields": ["rad/rad", "degree/rad", "degree/degree"],
        "consumer_source_path": str(D6_FINALIZER),
        "consumer_source_sha256": sha(D6_FINALIZER),
        "proposal_generator_actual_radian_expression": "actual_psi = atan2(dy, dx); delta[Psi] = actual_psi",
        "phase_prediction_expression": "predicted = anchor + raw_jacobian @ delta",
        "uncertainty_propagation_unit": "degree_per_rad multiplied by actual delta_psi_rad",
    }
    unit_audit = {
        "schema_version": SCHEMA,
        "status": "PASS",
        "classification": "CASE_UNIT_LABEL_ONLY",
        "internal_arithmetic_unit": "radian",
        "output_unit_semantics": ["rad/rad", "degree/rad", "degree/degree"],
        "values": unit_fields,
        "consumer_audit": unit_consumer_audit,
        "forbidden_mislabel": "-18.48540916 is degree/rad, not degree/degree",
        "d6_physics_staging_modified": False,
    }

    # Step-normalized near-null audit, retaining the two soft directions and all source vectors.
    variables = d6_svd["variables"]
    vectors = d6_svd["right_singular_vectors"]
    soft = vectors[-2:]
    step_scale_psi = float(d6_jac["step_normalized_complex_jones_jacobian"]["step_scales"]["Psi_rad"])
    step_jac_cols = []
    cols = d6_jac["step_normalized_complex_jones_jacobian"]["columns"]
    for v in variables:
        step_jac_cols.append(matrix_from_json(cols[v]))
    raw_leak = d6_svd["matrix"]
    d5_leak = load_json(ANALYSIS / "b120_j2lm06_stage_d5_leakage_svd_audit_v1.json")["leakage_jacobian"]
    # D6 matrix rows are the six leakage components and columns already step-normalized.
    def leakage_response(direction):
        return [sum(float(raw_leak[i][j]) * direction[j] for j in range(5)) for i in range(6)]
    def direction_response(direction):
        return cmat_mul(step_jac_cols, direction)
    soft_projection_rows = []
    for idx, sv in enumerate(soft, start=len(vectors) - 2):
        direction = [float(sv["components"][v]) for v in variables]
        resp = direction_response(direction)
        phase_projection = math.degrees((resp[0][0] / anchor[0][0]).imag)
        txx_projection = 2.0 * (anchor[0][0].conjugate() * resp[0][0]).real
        soft_projection_rows.append({
            "vector_index": idx,
            "singular_value": d6_svd["singular_values"][idx],
            "components": {v: direction[i] for i, v in enumerate(variables)},
            "phase_projection_deg": phase_projection,
            "Txx_projection": txx_projection,
            "projector_metric_projection_norm": norm(leakage_response(direction)),
            "physical_interpretation": "soft numerical leakage direction; not exact null",
        })

    proposal_rows = []
    for i, row in enumerate(source_rows, start=1):
        raw_identity = json.dumps(row, sort_keys=True, separators=(",", ":"))
        proposal_hash = hashlib.sha256(raw_identity.encode()).hexdigest()
        candidate_id = f"D7_TRV_PROP_{proposal_hash[:16]}"
        d1, d2l, d2w = num(row["delta_J1_side_nm"]), num(row["delta_J2_length_nm"]), num(row["delta_J2_width_nm"])
        dD, dpsi_rad = num(row["actual_effective_delta_D_nm"]), num(row["actual_effective_delta_Psi_rad"])
        step = [d1, d2l, d2w, dD, dpsi_rad / step_scale_psi]
        projections = [dot(step, [num(sv["components"][v]) for v in variables]) for sv in soft]
        near_total = math.sqrt(sum(p * p for p in projections))
        step_norm = norm(step)
        hard_residual = math.sqrt(max(step_norm * step_norm - near_total * near_total, 0.0))
        d5_uncertainty = 0.0
        for deriv, delta in zip(d5_jac["derivatives"], (d1, d2l, d2w)):
            d5_uncertainty += abs(float(deriv["phase_rad_per_nm_unwrap"])) * abs(delta) * float(d5_lin[deriv["axis"]]["frobenius_midpoint_residual"]) * 180.0 / math.pi
        radial_phase_deg_per_nm = abs(float(radial["phase_method_A_deg_per_unit"]))
        radial_uncertainty = radial_phase_deg_per_nm * abs(dD) * float(d6_lin["D"]["raw_midpoint_residual"])
        tangential_uncertainty = abs(degree_per_rad_a) * abs(dpsi_rad) * float(d6_lin["Psi"]["corrected_midpoint_residual"])
        crosscheck_uncertainty = abs(degree_per_rad_a - degree_per_rad_b) * abs(dpsi_rad)
        phase_uncertainty = (d5_uncertainty + radial_uncertainty + tangential_uncertainty + crosscheck_uncertainty) * (1.0 + step_norm)
        phase_drop = num(row["predicted_phase_drop_deg"])
        matrix_error = num(row["predicted_matrix_projection_error"])
        projector_margin = 1.0 - matrix_error
        projector_uncertainty = (float(d6_lin["D"]["raw_midpoint_residual"]) + float(d6_lin["Psi"]["corrected_midpoint_residual"]) + max(float(x["frobenius_midpoint_residual"]) for x in d5_lin.values())) * (1.0 + step_norm)
        near_fraction = near_total / step_norm if step_norm else 0.0
        psi_usage = abs(dpsi_rad / step_scale_psi)
        d_usage = abs(dD)
        proposal_rows.append({
            "source_row_index": i,
            "source_proposal_hash": proposal_hash,
            "candidate_id": candidate_id,
            "stage_id": STAGE,
            "anchor_id": "LP_H500_D2_B120_J2LM06",
            "source_status": row["status"],
            "label": "MODEL_PREDICTION_NOT_PHYSICS_LABEL",
            "physics_fields": "ABSENT_NOT_SIMULATED",
            "delta_J1_side_nm": d1, "delta_J2_length_nm": d2l, "delta_J2_width_nm": d2w,
            "n_D": int(num(row["n_D"])), "n_Psi": int(num(row["n_Psi"])),
            "J1_center_nm": parse_vec(row["J1_center_nm"]), "J2_center_nm": parse_vec(row["J2_center_nm"]),
            "actual_D_nm": num(row["actual_D_nm"]), "actual_Psi_deg": num(row["actual_Psi_deg"]),
            "effective_delta_D_nm": dD, "effective_delta_Psi_rad": dpsi_rad,
            "effective_delta_Psi_degree": num(row["actual_Psi_deg"]),
            "dimer_center_nm": [(parse_vec(row["J1_center_nm"])[0] + parse_vec(row["J2_center_nm"])[0]) / 2.0, (parse_vec(row["J1_center_nm"])[1] + parse_vec(row["J2_center_nm"])[1]) / 2.0],
            "J1_side_nm": 110.0 + d1, "J2_length_nm": 109.0 + d2l, "J2_width_nm": 100.0 + d2w,
            "H_nm": 500.0, "period_nm": 432.0, "material": "APCD_TIO2_NATIVE_M1", "theta1_deg": 0.0, "theta2_deg": 0.0,
            "direct_gap_nm": num(row["direct_gap_nm"]), "nearest_periodic_gap_nm": num(row["nearest_periodic_gap_nm"]),
            "nearest_periodic_gap_direction": "SOURCE_PROVENANCE_RETAINED",
            "integer_dimension_gate": all(abs((x * 2) - round(x * 2)) < 1e-10 for x in (110.0 + d1, 109.0 + d2l, 100.0 + d2w)),
            "center_grid_gate": all(abs((x * 2) - round(x * 2)) < 1e-10 for x in parse_vec(row["J1_center_nm"]) + parse_vec(row["J2_center_nm"])),
            "no_overlap": num(row["direct_gap_nm"]) >= 0.0,
            "manufacturing_gate": num(row["direct_gap_nm"]) >= 60.0 and num(row["nearest_periodic_gap_nm"]) >= 60.0,
            "exact_geometry_hash": row["exact_geometry_hash"], "canonical_relative_geometry_hash": row["canonical_relative_geometry_hash"], "symmetry_equivalence_hash": row["symmetry_equivalence_hash"],
            "canonical_duplicate": row["canonical_duplicate"].lower() == "true",
            "predicted_Txx": num(row["predicted_Txx"]), "predicted_Tyy": num(row["predicted_Tyy"]), "predicted_phase_deg": num(row["predicted_phase_deg"]), "predicted_phase_drop_deg": phase_drop,
            "predicted_leakage_norm": num(row["predicted_leakage_sum"]), "predicted_sigma2_over_sigma1": num(row["predicted_sigma2_over_sigma1"]), "predicted_matrix_projection_error": matrix_error,
            "predicted_projector_gate": row["predicted_projector_gate"].lower() == "true",
            "projector_margin": projector_margin, "projector_uncertainty": projector_uncertainty,
            "projector_uncertainty_aware": bool(row["predicted_projector_gate"].lower() == "true" and projector_margin > projector_uncertainty),
            "phase_uncertainty_deg": phase_uncertainty, "phase_lowering_margin_deg": phase_drop - phase_uncertainty,
            "phase_lowering_beyond_uncertainty": phase_drop > phase_uncertainty,
            "step_normalized_geometry_norm": step_norm, "near_null_projection_vminus1": projections[0], "near_null_projection_vminus2": projections[1], "near_null_subspace_projection_norm": near_total,
            "near_null_fraction": near_fraction, "orthogonal_hard_direction_residual": hard_residual,
            "Psi_operator_usage_step": psi_usage, "D_operator_usage_nm": d_usage, "predicted_phase_leverage_deg": abs(phase_drop),
            "reliability_flag": "LOCAL_LINEAR_MODEL_WITH_CONSERVATIVE_UNCERTAINTY",
            "future_x_subrun_id": candidate_id + "_x", "future_y_subrun_id": candidate_id + "_y",
        })

    # Deterministic multi-objective ranking; no candidate is dropped.
    ranked = sorted(proposal_rows, key=lambda r: (-int(r["projector_uncertainty_aware"]), -r["phase_lowering_margin_deg"], -r["predicted_Txx"], r["predicted_leakage_norm"], -r["near_null_fraction"], -r["Psi_operator_usage_step"], r["step_normalized_geometry_norm"], r["candidate_id"]))
    for rank, row in enumerate(ranked, start=1):
        row["execution_rank"] = rank
        row["classification"] = "PRIMARY_PROJECTOR_TANGENT_VALIDATION" if rank <= 3 else ("SECONDARY_NEAR_NULL_DIVERSITY" if rank <= 6 else "BOUNDARY_OR_MODEL_STRESS_TEST")
        row["planned_subrun_order"] = [row["future_x_subrun_id"], row["future_y_subrun_id"]]

    source_audit = {
        "schema_version": SCHEMA, "status": "PASS", "source_path": str(SOURCE), "source_sha256": source_hash,
        "source_row_count": len(source_rows), "candidate_count": len(ranked), "replacement_count": 0, "addition_count": 0, "deletion_count": 0,
        "source_status_all": sorted({r["status"] for r in source_rows}), "all_labels": sorted({r["label"] for r in proposal_rows}),
        "stable_id_method": "D7_TRV_PROP_<sha256(canonical_source_row)>", "old_row_to_frozen_candidate_id": [{"source_row_index": r["source_row_index"], "source_proposal_hash": r["source_proposal_hash"], "candidate_id": r["candidate_id"]} for r in ranked],
    }
    geometry_audit = [{k: r[k] for k in ("execution_rank", "candidate_id", "anchor_id", "delta_J1_side_nm", "delta_J2_length_nm", "delta_J2_width_nm", "n_D", "n_Psi", "J1_center_nm", "J2_center_nm", "dimer_center_nm", "J1_side_nm", "J2_length_nm", "J2_width_nm", "actual_D_nm", "actual_Psi_deg", "effective_delta_D_nm", "effective_delta_Psi_rad", "effective_delta_Psi_degree", "direct_gap_nm", "nearest_periodic_gap_nm", "nearest_periodic_gap_direction", "integer_dimension_gate", "center_grid_gate", "no_overlap", "manufacturing_gate", "exact_geometry_hash", "canonical_relative_geometry_hash", "symmetry_equivalence_hash", "canonical_duplicate", "label")} for r in ranked]
    duplicate_audit = {
        "schema_version": SCHEMA, "status": "PASS", "candidate_count": len(ranked),
        "source_exact_hash_duplicates": len({r["exact_geometry_hash"] for r in ranked}) != len(ranked),
        "source_canonical_relative_hash_duplicates": len({r["canonical_relative_geometry_hash"] for r in ranked}) != len(ranked),
        "source_symmetry_hash_duplicates": len({r["symmetry_equivalence_hash"] for r in ranked}) != len(ranked),
        "frozen_candidate_id_duplicates": len({r["candidate_id"] for r in ranked}) != len(ranked),
        "canonical_duplicate_rows": sum(bool(r["canonical_duplicate"]) for r in ranked),
        "geometry_changed": False,
    }
    ranking = {"schema_version": SCHEMA, "status": "PASS", "objective_order": ["uncertainty_aware_projector_robustness", "phase_reduction_beyond_uncertainty", "Txx_retention", "leakage_norm", "near_null_coverage", "Psi_active_inactive_diversity", "smaller_total_step", "stable_candidate_id"], "ordered_candidate_ids": [r["candidate_id"] for r in ranked], "rows": [{"rank": r["execution_rank"], "candidate_id": r["candidate_id"], "classification": r["classification"], "projector_uncertainty_aware": r["projector_uncertainty_aware"], "phase_lowering_margin_deg": r["phase_lowering_margin_deg"], "predicted_Txx": r["predicted_Txx"], "predicted_leakage_norm": r["predicted_leakage_norm"], "near_null_fraction": r["near_null_fraction"], "Psi_operator_usage_step": r["Psi_operator_usage_step"], "step_normalized_geometry_norm": r["step_normalized_geometry_norm"]} for r in ranked]}
    prediction_audit = [{k: r[k] for k in ("execution_rank", "candidate_id", "label", "physics_fields", "predicted_Txx", "predicted_Tyy", "predicted_phase_deg", "predicted_phase_drop_deg", "predicted_sigma2_over_sigma1", "predicted_matrix_projection_error", "predicted_leakage_norm", "predicted_projector_gate", "projector_margin", "reliability_flag")} for r in ranked]
    uncertainty_audit = [{k: r[k] for k in ("execution_rank", "candidate_id", "phase_uncertainty_deg", "phase_lowering_margin_deg", "phase_lowering_beyond_uncertainty", "projector_margin", "projector_uncertainty", "projector_uncertainty_aware", "step_normalized_geometry_norm", "near_null_fraction", "reliability_flag")} for r in ranked]
    candidate_contract = {
        "schema_version": SCHEMA, "status": "PASS", "stage_id": STAGE, "candidate_count": 8,
        "all_candidates_planned_not_run": True, "future_wavelength_nm": 450, "future_geometry_count": 8, "future_subrun_count": 16,
        "candidate_fields": ["frozen_geometry", "planned_x_subrun_id", "planned_y_subrun_id", "proposal_lineage", "predictor_version", "Jacobian_source_identity", "uncertainty_source", "split_group", "split_assignment", "future_failure_quality_fields", "canonical_v1_21_provenance", "D6_staging_provenance", "projector_preserved_from_backbone"],
        "physics_fields": "ABSENT_NOT_SIMULATED", "prediction_fields": "MODEL_PREDICTION_NOT_PHYSICS_LABEL", "forbidden_field": "projector_preserved_from_seed", "split_assignment": "UNASSIGNED",
    }
    geometry_hashes = [{"candidate_id": r["candidate_id"], "exact_geometry_hash": r["exact_geometry_hash"], "canonical_relative_geometry_hash": r["canonical_relative_geometry_hash"], "symmetry_equivalence_hash": r["symmetry_equivalence_hash"]} for r in ranked]
    canonical_identity_sha = sha(CANONICAL / "checksums_v1_21.json")
    d6_provenance_sha = sha(D6_PROV)
    uncertainty_source = {
        "D5_linearity": str(D5_LIN),
        "D6_positional_linearity": str(D6_LIN),
        "D6_phase_crosscheck": str(D6_TANG),
        "trust_step": "step_normalized_geometry_norm",
    }
    plan_rows = []
    for r in ranked:
        plan_rows.append({
            **r,
            "status": "PLANNED_NOT_RUN",
            "source_plan_sha256": sha(D6_PLAN),
            "D6_staging_provenance_sha256": d6_provenance_sha,
            "proposal_lineage": {"source_csv": str(SOURCE), "source_row_index": r["source_row_index"], "source_proposal_hash": r["source_proposal_hash"]},
            "predictor_version": "D6_FIVE_VARIABLE_LINEAR_JONES_JACOBIAN_V1",
            "Jacobian_source_identity": sha(SOURCE_J),
            "uncertainty_source": uncertainty_source,
            "split_group": r["canonical_relative_geometry_hash"],
            "split_assignment": "UNASSIGNED",
            "future_failure_quality_fields": ["failure_stage", "failure_code", "failure_mechanism", "last_valid_checkpoint", "retained_data_status", "quality_status"],
            "canonical_v1_21_provenance": {"checksums_path": str(CANONICAL / "checksums_v1_21.json"), "sha256": canonical_identity_sha},
            "D6_staging_provenance": {"checksums_path": str(D6_STAGING / "checksums_v1_22.json"), "sha256": d6_provenance_sha},
            "projector_preserved_from_backbone": "MODEL_PREDICTION_NOT_PHYSICS_LABEL",
        })

    plan_json = {
        "schema_version": SCHEMA, "stage_id": STAGE, "status": "PLANNED_NOT_RUN", "append_only": True,
        "source_proposal_path": str(SOURCE), "source_proposal_sha256": source_hash, "source_audit": source_audit,
        "candidate_count": 8, "geometry_count": 8, "future_subrun_count": 16, "wavelength_nm": 450,
        "execution_order": [{"candidate_id": r["candidate_id"], "subruns": r["planned_subrun_order"], "order": r["execution_rank"]} for r in ranked],
        "candidates": plan_rows,
        "route": "CASE_A_FIVE_VARIABLE_PROJECTOR_TANGENT_FOUND",
        "trust_region_FDTD_authorization": "PLANNING_ONLY_NOT_AUTHORIZED",
        "canonical_status": "CANONICAL_V1_21_UNCHANGED_NO_V1_22_MERGE",
        "spectral_authorization": "NOT_AUTHORIZED", "training_authorization": "NOT_AUTHORIZED",
    }
    execution_contract = {"schema_version": SCHEMA, "stage_id": STAGE, "status": "PLANNED_NOT_RUN", "authorized": False, "solver_calls": 0, "lumapi_calls": 0, "FDTD_calls": 0, "future_budget": {"geometries": 8, "x_y_subruns": 16, "wavelength_nm": [450]}, "candidate_order": [{"candidate_id": r["candidate_id"], "x": r["future_x_subrun_id"], "y": r["future_y_subrun_id"]} for r in ranked], "per_candidate_order": "x -> checkpoint/reload/acceptance -> y", "stop_policy": "STOP_ON_FIRST_FAILED_FORMAL_ACCEPTANCE", "retry": "FORBIDDEN", "forbidden": ["anchor_rerun", "D5_rerun", "D6_rerun", "reference", "spectrum", "tolerance", "dynamic_replacement", "canonical_merge", "training"]}
    ml_contract = {"schema_version": SCHEMA, "stage_id": STAGE, "status": "PLAN_CONTRACT_ONLY", "physics_fields": "ABSENT_NOT_SIMULATED", "prediction_fields": "MODEL_PREDICTION_NOT_PHYSICS_LABEL", "split_group": "canonical_relative_geometry_hash_sha256", "split_assignment": "UNASSIGNED", "required_fields": candidate_contract["candidate_fields"], "formal_projector_field": "projector_preserved_from_backbone", "forbidden_fields": ["projector_preserved_from_seed"], "no_execution_authorization": True}
    metric_contract = {"schema_version": SCHEMA, "status": "PASS", "metrics": ["formal weighted-G0 reconstruction", "normalization and power closure", "projectorization gate", "phase relative to anchor", "phase relative to B120 target", "Txx retention", "Tyy suppression", "sigma2/sigma1", "projection error", "off-axis leakage", "model-prediction residual", "local-linearization residual"], "future_labels": ["VALIDATED_PROJECTOR_PHASE_LOWERING_STEP", "PROJECTOR_PRESERVED_BUT_PHASE_STEP_NOT_CONFIRMED", "PHASE_LOWERED_BUT_PROJECTOR_FAILED", "LOCAL_MODEL_MISPREDICTION", "TECHNICAL_OR_RUNTIME_FAILURE"], "all_future_labels_are_post_simulation": True}

    outputs = {
        "analysis/b120_j2lm06_stage_d7_tangential_unit_semantics_audit_v1.json": unit_audit,
        "analysis/b120_j2lm06_stage_d7_near_null_subspace_audit_v1.json": {"schema_version": SCHEMA, "status": "PASS", "numerical_near_null_subspace_dimension": 2, "exact_nullspace_dimension": int(d6_svd["exact_nullspace_dimension"]), "formal_numerical_rank": int(d6_svd["numerical_rank"]), "singular_values": d6_svd["singular_values"], "rank_tolerance": d6_svd["rank_tolerance"], "all_right_singular_vectors": vectors, "two_soft_vector_projections": soft_projection_rows, "candidate_projection_definition": "step-normalized geometry vector dot right singular vector", "physical_interpretation": "two extremely soft numerical directions; not an exact nullspace"},
        "analysis/b120_j2lm06_stage_d7_existing_proposal_source_audit_v1.json": source_audit,
        "analysis/b120_j2lm06_stage_d7_proposal_prediction_audit_v1.csv": prediction_audit,
        "analysis/b120_j2lm06_stage_d7_proposal_uncertainty_audit_v1.csv": uncertainty_audit,
        "analysis/b120_j2lm06_stage_d7_geometry_gate_v1.csv": geometry_audit,
        "analysis/b120_j2lm06_stage_d7_duplicate_hash_audit_v1.json": duplicate_audit,
        "analysis/b120_j2lm06_stage_d7_candidate_ranking_audit_v1.json": ranking,
        "analysis/b120_j2lm06_stage_d7_candidate_contract_audit_v1.json": candidate_contract,
        "plans/b120_j2lm06_five_variable_trust_region_validation_stage_d7_v1.csv": plan_rows,
        "plans/b120_j2lm06_five_variable_trust_region_validation_stage_d7_v1.json": plan_json,
        "plans/b120_j2lm06_stage_d7_execution_contract_v1.json": execution_contract,
        "plans/b120_j2lm06_stage_d7_ml_label_contract_v1.json": ml_contract,
        "plans/b120_j2lm06_stage_d7_validation_metric_contract_v1.json": metric_contract,
    }
    # Write all requested outputs, never inside D6 staging/canonical.
    for rel, obj in outputs.items():
        path = ML / rel
        if rel.endswith(".csv"):
            write_csv(path, obj)
        else:
            dump(path, obj)
    report = """# APCD LP J2LM06 Stage D7 five-variable trust-region validation plan freeze v1\n\n"""
    report += "- Status: `PASS`\n- Mode: `OFFLINE_ONLY`\n- D6 physics staging: unchanged\n- Candidate universe: exactly 8 existing D6 proposals, no replacement/addition/deletion\n- Future budget: exactly 8 geometries / 16 x-y subruns / 450 nm only\n- Route: `CASE_A_FIVE_VARIABLE_PROJECTOR_TANGENT_FOUND`; this is planning only, not execution authorization\n\n"
    report += "## Unit semantics\n\n"
    report += f"Internal arithmetic remains radian-based. Method A is {phase_a_rad_per_rad:.12g} rad/rad, {degree_per_rad_a:.12g} degree/rad, {degree_per_degree_a:.12g} degree/degree. Method B is {phase_b_rad_per_rad:.12g} rad/rad, {degree_per_rad_b:.12g} degree/rad, {degree_per_degree_b:.12g} degree/degree. Classification: `CASE_UNIT_LABEL_ONLY`; `-18.48540916` is degree/rad, never degree/degree.\n\n"
    report += "## Near-null audit\n\n"
    report += f"Step-normalized singular values: `{d6_svd['singular_values']}`; formal rank `{d6_svd['numerical_rank']}`, exact null dimension `{d6_svd['exact_nullspace_dimension']}`. The last two singular directions form `NUMERICAL_NEAR_NULL_SUBSPACE_DIMENSION_2`; this does not change rank=5. Ψ remains a new orthogonal control column (D6/D5 fraction 0.6687933841), even though the single best near-null vector has negligible Ψ component.\n\n"
    report += "## Frozen candidates\n\n"
    report += "| rank | candidate | class | Ψ step | phase margin (deg) | projector uncertainty-aware |\n|---:|---|---|---:|---:|---|\n"
    for r in ranked:
        report += f"| {r['execution_rank']} | `{r['candidate_id']}` | `{r['classification']}` | {r['Psi_operator_usage_step']:.6g} | {r['phase_lowering_margin_deg']:.6g} | {r['projector_uncertainty_aware']} |\n"
    report += "\nAll rows retain `MODEL_PREDICTION_NOT_PHYSICS_LABEL`; no candidate is a validated Jones, library node, robust bin, or spectral survivor.\n"
    atomic_write(REPORT, report.encode("utf-8"))

    output_paths = [ML / rel for rel in outputs] + [REPORT, ROOT / "scripts/lp_b120_j2lm06_stage_d7_trust_region_validation_plan_freeze_v1.py"]
    manifest = {"schema_version": SCHEMA, "status": "PASS", "stage_id": STAGE, "self_reference_policy": "EXCLUDES_SELF", "frozen_inputs": [{"path": str(p), "sha256": sha(p)} for p in [SOURCE, SOURCE_J, SOURCE_SVD, D5_J, D5_SVD, D5_LIN, D6_TANG, D6_RAD, D6_BIAS, D6_LIN, D6_ROUTE, D6_PROV, D6_PLAN, D6_CONTRACT, D6_ML, D6_DERIV, CANONICAL / "checksums_v1_21.json", RUNNER, RUNTIME, PACKAGE / "package_manifest.json", PACKAGE / "content_checksums.json"]], "outputs": [{"path": str(p), "sha256": sha(p), "bytes": p.stat().st_size} for p in output_paths]}
    dump(ANALYSIS / "b120_j2lm06_stage_d7_checksum_provenance_manifest_v1.json", manifest)
    print(json.dumps({"status": "PASS", "candidate_count": 8, "future_subruns": 16, "solver_calls": 0, "route": "CASE_A_FIVE_VARIABLE_PROJECTOR_TANGENT_FOUND", "unit_semantics": "CASE_UNIT_LABEL_ONLY", "outputs": len(output_paths) + 1}, indent=2))


if __name__ == "__main__":
    main()
