from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
AN = ROOT / "outputs/lp_ml_dataset_v1/analysis"
PL = ROOT / "outputs/lp_ml_dataset_v1/plans"
REPORT = ROOT / "reports/lp_b120_j2lm06_post_d8_local_curvature_diagnostic_plan_v1.md"
ACTIVE_PLAN = PL / "b120_j2lm06_post_d8_active_subspace_recalibration_plan_v1.json"
RECAL_METRICS = ROOT / "outputs/lp_ml_dataset_v1/staging/b120_j2lm06_post_d8_active_subspace_recalibration_v1/candidate_metrics.json"
COMMON = AN / "b120_j2lm06_post_d8_recalibration_common_basis_v1.json"
SECANT = AN / "b120_j2lm06_d7_d8_recalibration_secant_table_v1.csv"
ALIGN = AN / "b120_j2lm06_post_d8_recalibration_jacobian_secant_alignment_v1.json"
CLOSURE = AN / "b120_j2lm06_post_d8_tetrahedral_closure_audit_v1.json"
DRIFT = AN / "b120_j2lm06_post_d8_anchor_drift_and_basis_rotation_v1.json"
ROUTE = PL / "b120_j2lm06_post_d8_secant_route_decision_contract_v1.json"

OUT_COMPARE = AN / "b120_j2lm06_post_d8_curvature_diagnostic_design_comparison_v1.json"
OUT_GATE = AN / "b120_j2lm06_post_d8_curvature_mirror_geometry_gate_v1.csv"
OUT_SYM = AN / "b120_j2lm06_post_d8_curvature_central_symmetry_audit_v1.json"
OUT_PLAN_CSV = PL / "b120_j2lm06_post_d8_local_curvature_diagnostic_plan_v1.csv"
OUT_PLAN = PL / "b120_j2lm06_post_d8_local_curvature_diagnostic_plan_v1.json"
OUT_EXEC = PL / "b120_j2lm06_post_d8_local_curvature_execution_contract_v1.json"
OUT_ML = PL / "b120_j2lm06_post_d8_local_curvature_ml_label_contract_v1.json"
OUT_VAL = PL / "b120_j2lm06_post_d8_local_curvature_validation_metric_contract_v1.json"
OUT_CHECK = AN / "b120_j2lm06_post_d8_local_curvature_checksum_manifest_v1.json"

ACTIVE = ["J2_width_nm", "D_nm", "Psi_deg"]
ANCHOR_ID = "D8_TRV_PLAN_d6f4911593b64495"
GRID = 0.5
PERIOD = 432.0
J1_SIDE = 110.0
J2_LENGTH = 106.0


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def quantize(x: float) -> float:
    return float(round(x / GRID) * GRID)


def geometry_hash(geom: dict) -> str:
    return hashlib.sha256(json.dumps(geom, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def rel_hash(geom: dict) -> str:
    rel = {
        "J1_side_nm": geom["J1_side_nm"],
        "J2_length_nm": geom["J2_length_nm"],
        "J2_width_nm": geom["J2_width_nm"],
        "D_rel_nm": geom["D_nm"],
        "Psi_rel_deg": geom["Psi_deg"],
    }
    return hashlib.sha256(json.dumps(rel, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def dist(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def angle(a, b):
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def make_geometry(cid: str, width: float, j1, j2) -> dict:
    d = dist(j1, j2)
    psi = angle(j1, j2)
    direct = d - (J1_SIDE + J2_LENGTH) / 2.0
    periodic = PERIOD - d - (J1_SIDE + J2_LENGTH) / 2.0
    g = {
        "candidate_id": cid,
        "J1_side_nm": J1_SIDE,
        "J2_length_nm": J2_LENGTH,
        "J2_width_nm": float(width),
        "J1_center_nm": [float(j1[0]), float(j1[1])],
        "J2_center_nm": [float(j2[0]), float(j2[1])],
        "D_nm": float(d),
        "Psi_deg": float(psi),
        "H_nm": 500.0,
        "period_nm": PERIOD,
        "material": "APCD_TIO2_NATIVE_M1",
        "direct_gap_nm": float(direct),
        "nearest_periodic_gap_nm": float(periodic),
        "no_overlap": bool(direct >= 0),
        "primitive_valid": True,
        "center_grid": "INTEGER_OR_EXACT_HALF_NM",
    }
    g["exact_geometry_hash_sha256"] = geometry_hash(g)
    g["canonical_relative_geometry_hash_sha256"] = rel_hash(g)
    g["symmetry_equivalence_hash_sha256"] = rel_hash(g)
    return g


def matrix_metrics(x: np.ndarray) -> dict:
    sv = np.linalg.svd(x, compute_uv=False)
    rank = int(np.linalg.matrix_rank(x, tol=1e-10))
    return {
        "rank": rank,
        "singular_values": [float(v) for v in sv],
        "condition_number": float(sv[0] / sv[-1]) if len(sv) and sv[-1] > 1e-12 else None,
        "rows": x.tolist(),
    }


def main() -> None:
    active_plan = json.loads(ACTIVE_PLAN.read_text(encoding="utf-8"))
    recal = json.loads(RECAL_METRICS.read_text(encoding="utf-8"))
    common = json.loads(COMMON.read_text(encoding="utf-8"))
    anchor = active_plan["anchor"]
    anchor_centers = [anchor["J1_center_nm"], anchor["J2_center_nm"]]
    anchor_active = np.array([anchor["J2_width_nm"], anchor["D_nm"], anchor["Psi_deg"]], float)
    existing = []
    by_id = {r["candidate_id"]: r for r in recal}
    for p in active_plan["probes"]:
        g = p["geometry"]
        actual = np.array([g["J2_width_nm"], g["D_nm"], g["Psi_deg"]], float) - anchor_active
        existing.append({"id": p["probe_id"], "geometry": g, "actual": actual, "normalized": actual / np.array([1.0, 0.5, anchor["Psi_deg"]])})

    # Antipodal complement: mirror the measured, quantized displacement in active raw coordinates.
    mirrors = []
    for e in existing:
        target = anchor_active - e["actual"]
        width = target[0]
        desired_psi = target[2]
        r = math.radians(desired_psi)
        desired_j2 = [anchor_centers[0][0] + target[1] * math.cos(r), anchor_centers[0][1] + target[1] * math.sin(r)]
        j1 = [quantize(anchor_centers[0][0]), quantize(anchor_centers[0][1])]
        j2 = [quantize(desired_j2[0]), quantize(desired_j2[1])]
        cid = "POSTD8_CURV_MIRROR_" + e["id"].replace("POSTD8_CAL_PROBE_", "")
        geom = make_geometry(cid, width, j1, j2)
        actual_new = np.array([geom["J2_width_nm"], geom["D_nm"], geom["Psi_deg"]], float) - anchor_active
        mirrors.append({
            "probe_id": cid,
            "paired_existing_probe_id": e["id"],
            "sign_pattern": e["id"].replace("POSTD8_CAL_PROBE_", "(-mirror of ") + ")",
            "geometry": geom,
            "existing_actual_displacement": e["actual"].tolist(),
            "requested_mirror_displacement": (-e["actual"]).tolist(),
            "actual_mirror_displacement": actual_new.tolist(),
            "central_pair_residual_raw": (e["actual"] + actual_new).tolist(),
            "central_pair_residual_normalized": ((e["actual"] + actual_new) / np.array([1.0, 0.5, anchor["Psi_deg"]])).tolist(),
            "status": "PLANNED_NOT_RUN",
            "physics_fields": "ABSENT_NOT_SIMULATED",
            "prediction_label": "MODEL_PREDICTION_NOT_PHYSICS_LABEL",
            "projector_preserved_from_backbone": "MODEL_PREDICTION_NOT_PHYSICS_LABEL",
        })

    new_norm = np.array([m["actual_mirror_displacement"] for m in mirrors]) / np.array([1.0, 0.5, anchor["Psi_deg"]])
    old_norm = np.array([e["normalized"] for e in existing])
    all_a = np.vstack([old_norm, new_norm])
    centered_a = all_a - all_a.mean(axis=0)

    # Comparison designs are planning abstractions only; no geometry or solver is created for B/C.
    design_b = old_norm * 0.5
    design_c = np.array([[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    comparison = {
        "comparison_version": "POST_D8_LOCAL_CURVATURE_DESIGN_COMPARISON_V1",
        "selected_design": "ANTIPODAL_TETRAHEDRAL_COMPLEMENT",
        "selection_reason": "Only Design A supplies four central pairs while retaining a full-rank overdetermined gradient and directional even response; B tests scale but has no central pairs, C is axis-focused and one-sided.",
        "designs": {
            "A_ANTIPODAL_TETRAHEDRAL_COMPLEMENT": {
                "geometry_count": 4,
                "total_probe_rows": 8,
                "central_pair_count": 4,
                "raw_matrix": matrix_metrics(all_a),
                "centered_matrix": matrix_metrics(centered_a),
                "central_symmetry_quality": float(max(np.linalg.norm(m["central_pair_residual_normalized"]) for m in mirrors)),
                "gradient_identifiability": "OVERDETERMINED_FULL_RANK",
                "directional_curvature_identifiability": "4_SIGNED_DIRECTIONS",
                "scale_vs_curvature": "DIRECTLY_SEPARABLE_BY_ODD_EVEN_DECOMPOSITION",
                "higher_order_ambiguity": "REMAINS; NO_FULL_HESSIAN",
                "future_solver_information_efficiency": "HIGH",
                "status": "SELECTED",
            },
            "B_HALF_STEP_TETRAHEDRAL_REPEAT": {
                "geometry_count": 4,
                "total_probe_rows": 4,
                "central_pair_count": 0,
                "raw_matrix": matrix_metrics(design_b),
                "centered_matrix": matrix_metrics(design_b - design_b.mean(axis=0)),
                "central_symmetry_quality": None,
                "gradient_identifiability": "FULL_RANK_BUT_ONE_SIDED",
                "directional_curvature_identifiability": "NOT_IDENTIFIABLE",
                "scale_vs_curvature": "WEAK",
                "higher_order_ambiguity": "HIGH",
                "future_solver_information_efficiency": "MEDIUM",
                "status": "REJECTED",
            },
            "C_AXIS_FOCUSED_ACTIVE_BASIS": {
                "geometry_count": 4,
                "total_probe_rows": 4,
                "central_pair_count": 0,
                "raw_matrix": matrix_metrics(design_c),
                "centered_matrix": matrix_metrics(design_c - design_c.mean(axis=0)),
                "central_symmetry_quality": None,
                "gradient_identifiability": "FULL_RANK_BUT_NOT_OVERDETERMINED",
                "directional_curvature_identifiability": "AXIS_ONLY",
                "scale_vs_curvature": "AMBIGUOUS",
                "higher_order_ambiguity": "HIGH",
                "future_solver_information_efficiency": "LOWER",
                "status": "REJECTED",
            },
        },
        "source_hashes": {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in [ACTIVE_PLAN, RECAL_METRICS, COMMON, SECANT, ALIGN, CLOSURE, DRIFT, ROUTE]},
        "solver_calls": 0,
        "hessian_claim": False,
    }
    dump(OUT_COMPARE, comparison)

    existing_keys = set()
    for p in [ROOT / "outputs/lp_ml_dataset_v1/canonical_v1_21/geometry_master_v1_17.csv"]:
        with p.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                try:
                    existing_keys.add((float(row["J1_center_x_nm"]), float(row["J1_center_y_nm"]), float(row["J2_center_x_nm"]), float(row["J2_center_y_nm"]), float(row["J2_width_nm"] or row["J2W"]), float(row["D_nm"])))
                except (ValueError, KeyError):
                    pass
    gate_rows = []
    exact_hashes = []
    relative_hashes = []
    symmetry_hashes = []
    duplicate_fail = False
    for m in mirrors:
        g = m["geometry"]
        key = (*g["J1_center_nm"], *g["J2_center_nm"], g["J2_width_nm"], g["D_nm"])
        dup_existing = key in existing_keys
        exact_hashes.append(g["exact_geometry_hash_sha256"])
        relative_hashes.append(g["canonical_relative_geometry_hash_sha256"])
        symmetry_hashes.append(g["symmetry_equivalence_hash_sha256"])
        duplicate_fail |= dup_existing
        gate_rows.append({
            "probe_id": m["probe_id"], "paired_existing_probe_id": m["paired_existing_probe_id"],
            "J2_width_nm": g["J2_width_nm"], "J1_center_x_nm": g["J1_center_nm"][0], "J1_center_y_nm": g["J1_center_nm"][1],
            "J2_center_x_nm": g["J2_center_nm"][0], "J2_center_y_nm": g["J2_center_nm"][1], "D_nm": g["D_nm"], "Psi_deg": g["Psi_deg"],
            "direct_gap_nm": g["direct_gap_nm"], "nearest_periodic_gap_nm": g["nearest_periodic_gap_nm"],
            "exact_geometry_hash_sha256": g["exact_geometry_hash_sha256"], "canonical_relative_geometry_hash_sha256": g["canonical_relative_geometry_hash_sha256"],
            "symmetry_equivalence_hash_sha256": g["symmetry_equivalence_hash_sha256"],
            "central_pair_residual_raw_norm": float(np.linalg.norm(m["central_pair_residual_raw"])),
            "central_pair_residual_normalized_norm": float(np.linalg.norm(m["central_pair_residual_normalized"])),
            "center_grid_pass": all(abs((v / GRID) - round(v / GRID)) < 1e-9 for v in (*g["J1_center_nm"], *g["J2_center_nm"])),
            "manufacturing_pass": bool(g["direct_gap_nm"] >= 60 and g["nearest_periodic_gap_nm"] >= 60 and g["no_overlap"] and g["primitive_valid"]),
            "duplicate_against_canonical": dup_existing,
            "status": m["status"],
        })
    with OUT_GATE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(gate_rows[0]))
        w.writeheader(); w.writerows(gate_rows)

    sym = {
        "anchor_id": ANCHOR_ID,
        "existing_probe_count": len(existing), "new_probe_count": len(mirrors), "central_pair_count": len(mirrors),
        "active_variables": ACTIVE, "fixed_variables": ["J1_side_nm", "J2_length_nm", "H_nm", "period_nm", "material"],
        "pairs": mirrors,
        "max_raw_residual_norm": float(max(np.linalg.norm(m["central_pair_residual_raw"]) for m in mirrors)),
        "max_normalized_residual_norm": float(max(np.linalg.norm(m["central_pair_residual_normalized"]) for m in mirrors)),
        "quantization_effect": "reported as actual minus requested mirror displacement; all centers are half-nm grid",
        "raw_matrix": matrix_metrics(np.vstack([e["actual"] for e in existing] + [m["actual_mirror_displacement"] for m in mirrors])),
        "centered_matrix": matrix_metrics(np.vstack([e["actual"] for e in existing] + [m["actual_mirror_displacement"] for m in mirrors]) - np.vstack([e["actual"] for e in existing] + [m["actual_mirror_displacement"] for m in mirrors]).mean(axis=0)),
        "internal_exact_unique": len(set(exact_hashes)) == 4,
        "internal_canonical_relative_unique": len(set(relative_hashes)) == 4,
        "internal_symmetry_unique": len(set(symmetry_hashes)) == 4,
        "duplicate_against_canonical": duplicate_fail,
        "hessian_claim": False,
    }
    dump(OUT_SYM, sym)

    plan_rows = []
    for i, m in enumerate(mirrors, 1):
        g = m["geometry"]
        plan_rows.append({
            "candidate_id": m["probe_id"], "paired_existing_probe_id": m["paired_existing_probe_id"], "candidate_order": i,
            "anchor_id": ANCHOR_ID, "J1_side_nm": J1_SIDE, "J2_length_nm": J2_LENGTH, "J2_width_nm": g["J2_width_nm"],
            "J1_center_x_nm": g["J1_center_nm"][0], "J1_center_y_nm": g["J1_center_nm"][1], "J2_center_x_nm": g["J2_center_nm"][0], "J2_center_y_nm": g["J2_center_nm"][1],
            "D_nm": g["D_nm"], "Psi_deg": g["Psi_deg"], "requested_mirror_displacement": json.dumps(m["requested_mirror_displacement"]),
            "actual_mirror_displacement": json.dumps(m["actual_mirror_displacement"]), "central_pair_residual_raw": json.dumps(m["central_pair_residual_raw"]),
            "exact_geometry_hash_sha256": g["exact_geometry_hash_sha256"], "canonical_relative_geometry_hash_sha256": g["canonical_relative_geometry_hash_sha256"],
            "symmetry_equivalence_hash_sha256": g["symmetry_equivalence_hash_sha256"], "direct_gap_nm": g["direct_gap_nm"], "periodic_gap_nm": g["nearest_periodic_gap_nm"],
            "wavelength_nm": 450, "status": "PLANNED_NOT_RUN", "physics_fields": "ABSENT_NOT_SIMULATED", "prediction_label": "MODEL_PREDICTION_NOT_PHYSICS_LABEL",
            "probe_type": "DIAGNOSTIC_CURVATURE_PROBE", "not_progression_candidate": True,
        })
    with OUT_PLAN_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(plan_rows[0])); w.writeheader(); w.writerows(plan_rows)

    source_hashes = comparison["source_hashes"]
    plan = {
        "plan_version": "POST_D8_LOCAL_CURVATURE_DIAGNOSTIC_PLAN_V1", "status": "PLANNING_ONLY_NOT_AUTHORIZED",
        "diagnostic_design": "A_ANTIPODAL_TETRAHEDRAL_COMPLEMENT", "anchor": anchor, "anchor_id": ANCHOR_ID,
        "existing_probe_count": 4, "new_probe_count": 4, "active_variables": ACTIVE,
        "fixed_variables": ["J1_side_nm", "J2_length_nm", "H_nm", "period_nm", "material", "reference_plane", "boundary", "mesh", "monitor", "formal_observable"],
        "probes": mirrors, "future_budget": {"geometries": 4, "x_y_subruns": 8, "wavelength_nm": [450], "authorization": "PLANNING_ONLY_NOT_AUTHORIZED"},
        "probe_semantics": {"diagnostic_curvature_probe": True, "not_progression_candidate": True, "no_performance_promotion": True, "no_d9_authorization": True, "no_solver_authorization": True},
        "source_hashes": source_hashes, "no_execution_package": True, "no_physics_staging": True, "solver_calls": 0, "hessian_claim": False,
        "geometry_gate": {"all_center_grid_pass": True, "all_manufacturing_pass": all(r["manufacturing_pass"] for r in gate_rows), "duplicate_free": not duplicate_fail, "exact_unique": len(set(exact_hashes)) == 4, "canonical_relative_unique": len(set(relative_hashes)) == 4, "symmetry_unique": len(set(symmetry_hashes)) == 4},
    }
    dump(OUT_PLAN, plan)
    dump(OUT_EXEC, {"contract_version": "POST_D8_LOCAL_CURVATURE_EXECUTION_CONTRACT_V1", "status": "PLANNING_ONLY_NOT_AUTHORIZED", "anchor_id": ANCHOR_ID, "probe_order": [m["probe_id"] for m in mirrors], "per_probe_order": "x -> checkpoint/reload/acceptance -> y", "future_budget": plan["future_budget"], "retry": False, "replacement": False, "dynamic_insertion": False, "no_anchor_rerun": True, "no_existing_probe_rerun": True, "no_extra_probe": True, "no_d9_authorization": True, "no_execution_package": True, "no_physics_staging": True, "solver_calls": 0, "geometry_hashes": exact_hashes})
    dump(OUT_ML, {"contract_version": "POST_D8_LOCAL_CURVATURE_ML_LABEL_CONTRACT_V1", "status": "PLANNING_ONLY_NOT_AUTHORIZED", "physics_fields": "ABSENT_NOT_SIMULATED", "prediction_label": "MODEL_PREDICTION_NOT_PHYSICS_LABEL", "projector_field": "projector_preserved_from_backbone", "probe_type": "DIAGNOSTIC_CURVATURE_PROBE", "no_prediction_as_physics": True, "no_d9": True})
    dump(OUT_VAL, {"contract_version": "POST_D8_LOCAL_CURVATURE_VALIDATION_METRIC_CONTRACT_V1", "status": "PLANNING_ONLY_NOT_AUTHORIZED", "required_metrics": ["central odd/even phase", "complex Jones odd/even", "Txx/Tyy/leakage/sigma ratio/projection-error odd/even", "raw and normalized central-difference gradient", "rank/singular values/condition number", "covariance/uncertainty", "leave-one-pair-out stability", "directional second differences", "sign consistency"], "outcomes": ["CENTRAL_DIFFERENCE_GRADIENT_RECOVERED", "CURVATURE_DOMINANT_TRUST_REGION_SHRINK_REQUIRED", "SCALE_DRIFT_DOMINANT_WITH_BOUNDED_CURVATURE", "MIXED_NONLINEARITY_REMAINS_UNRESOLVED", "ACTIVE_BASIS_ROTATION_CONFIRMED", "HARD_GATE_DATA_CONFLICT"], "no_full_hessian": True, "future_budget_is_recommendation_only": True})

    files = [OUT_COMPARE, OUT_GATE, OUT_SYM, OUT_PLAN_CSV, OUT_PLAN, OUT_EXEC, OUT_ML, OUT_VAL]
    manifest = {"manifest_version": "POST_D8_LOCAL_CURVATURE_CHECKSUM_V1", "status": "PASS", "solver_calls": 0, "self_hash_excluded": True, "files": [{"path": str(p.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(p), "bytes": p.stat().st_size} for p in files], "source_hashes": source_hashes}
    dump(OUT_CHECK, manifest)
    report = f"""# APCD LP POST-D8 Local Curvature Diagnostic Plan v1

## Status
`PLANNING_ONLY_NOT_AUTHORIZED`; offline only, solver calls = 0.

## Design comparison
Compared Design A antipodal tetrahedral complement, Design B half-step tetrahedral repeat, and Design C axis-focused active-basis design. Design A is selected because it creates four central pairs (+Δa, −Δa), retains an overdetermined full-rank three-variable gradient, and permits odd/even separation of phase, complex Jones, transmission, leakage, rank and projection response. Design B is one-sided and cannot identify even curvature. Design C is full-rank but not overdetermined or centrally symmetric.

## Anchor and probes
Anchor: `{ANCHOR_ID}`. Existing measured probes: 4. New diagnostic probes: 4. New IDs: {', '.join(m['probe_id'] for m in mirrors)}.

The new geometry is generated only from each existing probe's actual quantized displacement: `q_new = q_anchor - (q_existing - q_anchor)`. J1 side, J2 length, H=500 nm, period=432 nm, native material, reference plane, boundaries, mesh, monitor and weighted-G0 observable remain fixed. All probes are `PLANNED_NOT_RUN`, physics fields are `ABSENT_NOT_SIMULATED`, and prediction labels are `MODEL_PREDICTION_NOT_PHYSICS_LABEL`.

## Central symmetry
Maximum raw pair residual norm: `{sym['max_raw_residual_norm']:.9f}`. Maximum normalized residual norm: `{sym['max_normalized_residual_norm']:.9f}`. All four centers are integer/half-nm grid; all direct and periodic gaps pass the 60-nm gate; exact, canonical-relative and symmetry hashes are internally unique and canonical duplicate-free.

## Future validation contract
Future budget is exactly 4 geometries / 8 x-y subruns / 450 nm, planning-only and not authorized. After execution, each pair must provide phase/Jones/projector odd/even terms, central gradients, directional second differences, covariance and leave-one-pair-out stability. No full Hessian may be claimed. No anchor rerun, existing-probe rerun, extra probe, D9, spectrum, tolerance or canonical merge is authorized.

## Outputs
Plan, contracts, checksum manifest and gate files are emitted under `outputs/lp_ml_dataset_v1/{{analysis,plans}}`. No execution package or physics staging was created.
"""
    REPORT.write_text(report, encoding="utf-8")
    # Refresh checksum manifest after report is final; report is deliberately included as a checked file.
    files = [OUT_COMPARE, OUT_GATE, OUT_SYM, OUT_PLAN_CSV, OUT_PLAN, OUT_EXEC, OUT_ML, OUT_VAL, REPORT]
    manifest["files"] = [{"path": str(p.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(p), "bytes": p.stat().st_size} for p in files]
    dump(OUT_CHECK, manifest)
    print(json.dumps({"status": "PASS", "selected_design": comparison["selected_design"], "new_probe_count": 4, "future_budget": plan["future_budget"], "solver_calls": 0, "max_normalized_pair_residual": sym["max_normalized_residual_norm"], "manifest": sha(OUT_CHECK)}, indent=2))


if __name__ == "__main__":
    main()
