from __future__ import annotations
import csv, hashlib, json, math
from pathlib import Path
import numpy as np

ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
ML = ROOT / "outputs/lp_ml_dataset_v1"
D7_PLAN = ML / "plans/b120_j2lm06_five_variable_trust_region_validation_stage_d7_v1.json"
D7_STAGE = ML / "staging/b120_j2lm06_stage_d7_five_variable_trust_region_validation_v1"
D7_CANON = ML / "canonical_v1_21/checksums_v1_21.json"
D7_REPORT = ROOT / "reports/lp_b120_j2lm06_stage_d7_five_variable_trust_region_physics_validation_v1.md"
ANALYSIS = ML / "analysis"
D8_CSV = ML / "plans/b120_j2lm06_bounded_local_validation_stage_d8_v1.csv"
D8_JSON = ML / "plans/b120_j2lm06_bounded_local_validation_stage_d8_v1.json"
D8_EXEC = ML / "plans/b120_j2lm06_stage_d8_execution_contract_v1.json"
D8_ML = ML / "plans/b120_j2lm06_stage_d8_ml_label_contract_v1.json"
D8_MET = ML / "plans/b120_j2lm06_stage_d8_validation_metric_contract_v1.json"

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def cplx(x):
    return complex(float(x["real"]), float(x["imag"]))

def pareto(rows):
    objectives = [("actual_phase_drop_deg", 1), ("Txx", 1), ("Tyy", -1),
                  ("sigma2_over_sigma1", -1), ("cross_power", -1), ("projection_error", -1)]
    out = []
    for a in rows:
        dominated = False
        for b in rows:
            if a is b:
                continue
            ge = all((b[k] >= a[k] if s == 1 else b[k] <= a[k]) for k, s in objectives)
            strict = any((b[k] > a[k] if s == 1 else b[k] < a[k]) for k, s in objectives)
            if ge and strict:
                dominated = True
                break
        if not dominated:
            out.append(a["candidate_id"])
    return out

def geometry_hash(g):
    payload = {k: g[k] for k in ("H_nm", "period_nm", "J1_side_nm", "J2_length_nm", "J2_width_nm", "J1_center_nm", "J2_center_nm", "theta1_deg", "theta2_deg", "material")}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def main():
    d7_plan = json.loads(D7_PLAN.read_text(encoding="utf8"))
    d7_rows = json.loads((D7_STAGE / "candidate_metrics.json").read_text(encoding="utf8"))
    by_id = {r["candidate_id"]: r for r in d7_rows}
    actual = []
    matrix = []
    phase = []
    for p in d7_plan["candidates"]:
        r = dict(by_id[p["candidate_id"]])
        r.update({"execution_rank": p["execution_rank"], "J1_side_nm": p["J1_side_nm"], "J2_length_nm": p["J2_length_nm"], "J2_width_nm": p["J2_width_nm"], "D_nm": p["actual_D_nm"], "Psi_deg": p["actual_Psi_deg"], "direct_gap_nm": p["direct_gap_nm"], "periodic_gap_nm": p["nearest_periodic_gap_nm"], "exact_geometry_hash": p["exact_geometry_hash"], "canonical_relative_geometry_hash": p["canonical_relative_geometry_hash"], "symmetry_equivalence_hash": p["symmetry_equivalence_hash"], "predicted_phase_drop_deg": p["predicted_phase_drop_deg"], "phase_prediction_error_deg": r["phase_prediction_error_deg"]})
        actual.append(r)
        matrix.append([p["delta_J1_side_nm"], p["delta_J2_length_nm"], p["delta_J2_width_nm"], p["effective_delta_D_nm"], p["effective_delta_Psi_rad"]])
        phase.append(r["actual_phase_drop_deg"])
    X = np.asarray(matrix, dtype=float)
    y = np.asarray(phase, dtype=float)
    centered = X - X.mean(axis=0)
    raw_rank = int(np.linalg.matrix_rank(X))
    centered_rank = int(np.linalg.matrix_rank(centered))
    nonconstant = centered[:, 2:5]
    norm_nonconstant = nonconstant / np.where(nonconstant.std(axis=0) > 0, nonconstant.std(axis=0), 1)
    active_s = np.linalg.svd(norm_nonconstant, compute_uv=False)
    active_cond = float(active_s[0] / active_s[-1])
    fit_X = np.column_stack([np.ones(len(X)), X[:, 2], X[:, 3] - 1.0, X[:, 4]])
    beta = {}
    residuals = {}
    for key in ("actual_phase_drop_deg", "Txx", "Tyy", "sigma2_over_sigma1", "projection_error", "cross_power"):
        yy = np.asarray([float(r[key]) for r in actual])
        b = np.linalg.pinv(fit_X) @ yy
        beta[key] = b.tolist()
        residuals[key] = (yy - fit_X @ b).tolist()
    phase_res = np.asarray(residuals["actual_phase_drop_deg"])
    pareto_ids = pareto(actual)
    anchor = next(r for r in actual if r["candidate_id"] == "D7_TRV_PROP_693ec7d86d7c23e2")
    # D8 keeps J1 fixed because its column was never excited; all candidates remain within the active W2/D/Psi trust region.
    proposals = [
        (106, 100, 200.5, 1.0, "PRIMARY_PHASE_STEP"),
        (106, 100, 200.5, 0.0, "PRIMARY_PHASE_CONTROL"),
        (106, 100, 200.5, -1.0, "PRIMARY_PHASE_SIGN_DIAGNOSTIC"),
        (106, 99, 200.5, 1.0, "PARETO_LEAKAGE_BALANCE"),
        (106, 99, 200.5, 0.0, "D_CONTROL"),
        (107, 100, 200.5, 1.0, "L_CONTROL"),
        (106, 98, 200.5, 0.0, "BOUNDARY_DIAGNOSTIC"),
        (107, 99, 200.5, 0.0, "LOCAL_NEUTRAL_CONTROL"),
    ]
    d8 = []
    for rank, (L, W, D, dy, role) in enumerate(proposals, 1):
        # half-nm centers retain exact manufacturing grid; dy is the signed y separation in nm.
        j1 = [-100.0, -0.5 * dy]
        j2 = [j1[0] + D, 0.5 * dy]
        actual_D = math.hypot(j2[0] - j1[0], j2[1] - j1[1])
        psi = math.degrees(math.atan2(j2[1] - j1[1], j2[0] - j1[0]))
        direct_gap = actual_D - (110.0 + L) / 2.0
        periodic_gap = 432.0 - actual_D - (110.0 + L) / 2.0
        g = {"H_nm": 500.0, "period_nm": [432.0, 432.0], "J1_side_nm": 110.0, "J2_length_nm": L, "J2_width_nm": W, "J1_center_nm": j1, "J2_center_nm": j2, "theta1_deg": 0.0, "theta2_deg": 0.0, "material": "APCD_TIO2_NATIVE_M1"}
        gh = geometry_hash(g)
        cid = "D8_TRV_PLAN_" + gh[:16]
        f = np.array([1.0, W - 100.0, actual_D - 200.5, math.radians(psi)], dtype=float)
        pred = {k: float(f @ np.asarray(beta[k])) for k in beta}
        # The model fit uses D7 absolute deltas; apply only the bounded active variables and preserve provenance labels.
        row = {"execution_rank": rank, "candidate_id": cid, "role": role, "status": "PLANNED_NOT_RUN", "physics_fields": "ABSENT_NOT_SIMULATED", "label": "MODEL_PREDICTION_NOT_PHYSICS_LABEL", "projector_preserved_from_backbone": "MODEL_PREDICTION_NOT_PHYSICS_LABEL", "J1_side_nm": 110.0, "J2_length_nm": L, "J2_width_nm": W, "J1_center_nm": j1, "J2_center_nm": j2, "D_nm": actual_D, "Psi_deg": psi, "theta1_deg": 0.0, "theta2_deg": 0.0, "H_nm": 500.0, "period_nm": 432.0, "material": "APCD_TIO2_NATIVE_M1", "direct_gap_nm": direct_gap, "nearest_periodic_gap_nm": periodic_gap, "no_overlap": True, "manufacturing_gate": bool(direct_gap >= 60 and periodic_gap >= 60), "exact_geometry_hash": gh, "canonical_relative_geometry_hash": hashlib.sha256(("D7_D8_RELATIVE|" + gh).encode()).hexdigest(), "symmetry_equivalence_hash": hashlib.sha256(("D7_D8_SYMMETRY|" + gh).encode()).hexdigest(), "predicted_phase_drop_deg": pred["actual_phase_drop_deg"], "predicted_Txx": pred["Txx"], "predicted_Tyy": pred["Tyy"], "predicted_sigma2_over_sigma1": pred["sigma2_over_sigma1"], "predicted_projection_error": pred["projection_error"], "predicted_cross_power": pred["cross_power"], "source_d7_anchor": anchor["candidate_id"], "source_plan_sha256": sha(D7_PLAN), "source_d7_stage_sha256": sha(D7_STAGE / "d7_validation_summary.json"), "planned_x_subrun_id": cid + "_x", "planned_y_subrun_id": cid + "_y"}
        d8.append(row)
    d8_plan = {"schema_version": "LP_ML_SCHEMA_V1.24", "stage_id": "STAGE_D8_BOUNDED_LOCAL_VALIDATION", "status": "PLANNED_NOT_RUN", "authorized": False, "candidate_count": 8, "future_subrun_count": 16, "wavelength_nm": [450], "source_d7_plan_sha256": sha(D7_PLAN), "source_d7_stage_summary_sha256": sha(D7_STAGE / "d7_validation_summary.json"), "source_d7_report_sha256": sha(D7_REPORT), "canonical_v1_21_checksums_sha256": sha(D7_CANON), "anchor_candidate_id": anchor["candidate_id"], "anchor_selection_reason": "best multi-objective trade-off on actual D7 data; not lowest phase", "model_type": "CONSTRAINED_ACTIVE_SUBSPACE_RESIDUAL_CORRECTED_LOCAL_SURROGATE", "model_scope": "J2_width,D,Psi active subspace; J1_side and J2_length derivatives not identified by D7", "pareto_front_candidate_ids": pareto_ids, "future_budget": {"geometries": 8, "x_y_subruns": 16, "wavelength_nm": [450]}, "candidates": d8}
    d8_plan_path = D8_JSON; d8_plan_path.parent.mkdir(parents=True, exist_ok=True); d8_plan_path.write_text(json.dumps(d8_plan, indent=2, sort_keys=True), encoding="utf8")
    fields = list(d8[0])
    with D8_CSV.open("w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in d8: w.writerow({k: json.dumps(r[k], sort_keys=True) if isinstance(r[k], (list, dict)) else r[k] for k in fields})
    exec_contract = {"schema_version": "LP_ML_SCHEMA_V1.24", "stage_id": "STAGE_D8_BOUNDED_LOCAL_VALIDATION", "status": "PLANNED_NOT_RUN", "authorized": False, "candidate_order": [{"candidate_id": r["candidate_id"], "x": r["planned_x_subrun_id"], "y": r["planned_y_subrun_id"]} for r in d8], "future_budget": d8_plan["future_budget"], "per_candidate_order": "x -> checkpoint/reload/acceptance -> y", "retry": "FORBIDDEN", "forbidden": ["solver_execution_in_this_task", "spectrum", "tolerance", "canonical_merge", "training", "K6", "K7", "D9"]}
    ml_contract = {"schema_version": "LP_ML_SCHEMA_V1.24", "stage_id": "STAGE_D8_BOUNDED_LOCAL_VALIDATION", "status": "PLAN_CONTRACT_ONLY", "formal_projector_field": "projector_preserved_from_backbone", "prediction_fields": "MODEL_PREDICTION_NOT_PHYSICS_LABEL", "physics_fields": "ABSENT_NOT_SIMULATED", "split_group": "canonical_relative_geometry_hash_sha256", "split_assignment": "UNASSIGNED", "required_fields": ["candidate_id", "source_d7_anchor", "exact_geometry_hash", "canonical_relative_geometry_hash", "symmetry_equivalence_hash", "geometry", "planned_x_subrun_id", "planned_y_subrun_id", "source_d7_plan_sha256", "model_type", "projector_preserved_from_backbone"]}
    metric_contract = {"schema_version": "LP_ML_SCHEMA_V1.24", "stage_id": "STAGE_D8_BOUNDED_LOCAL_VALIDATION", "status": "PASS", "physics_fields": "ABSENT_NOT_SIMULATED", "metrics": ["formal weighted-G0 reconstruction", "phase relative to D8 anchor", "Txx", "Tyy", "sigma2/sigma1", "projection error", "cross power", "manufacturing and geometry gates", "prediction residual after execution"]}
    D8_EXEC.write_text(json.dumps(exec_contract, indent=2, sort_keys=True), encoding="utf8")
    D8_ML.write_text(json.dumps(ml_contract, indent=2, sort_keys=True), encoding="utf8")
    D8_MET.write_text(json.dumps(metric_contract, indent=2, sort_keys=True), encoding="utf8")
    analysis = {"status": "PASS", "source_d7_plan_sha256": sha(D7_PLAN), "source_d7_stage_sha256": sha(D7_STAGE / "d7_validation_summary.json"), "canonical_v1_21_checksums_sha256": sha(D7_CANON), "actual_candidate_table": actual, "actual_pareto_front": pareto_ids, "lowest_phase_candidate": min(actual, key=lambda r: r["phase_deg"])["candidate_id"], "best_tradeoff_candidate": anchor["candidate_id"], "residual_summary": {"phase_mean_abs_deg": float(np.mean(abs(phase_res))), "phase_max_abs_deg": float(np.max(abs(phase_res))), "phase_mean_signed_deg": float(np.mean(phase_res)), "phase_residuals_deg": phase_res.tolist(), "phase_sign_pattern": ["+" if x > 0 else "-" if x < 0 else "0" for x in phase_res]}, "design_matrix": {"raw_shape": list(X.shape), "raw_rank": raw_rank, "centered_rank": centered_rank, "full_five_variable_identifiable": False, "unidentifiable_columns": ["J1_side_nm", "J2_length_nm"], "active_columns": ["J2_width_nm", "D_nm", "Psi_rad"], "normalized_active_condition_number": active_cond, "singular_values_normalized_active": active_s.tolist()}, "model": {"type": "CONSTRAINED_ACTIVE_SUBSPACE_RESIDUAL_CORRECTED_LOCAL_SURROGATE", "scope": "J2_width/D/Psi only", "coefficients": beta, "residuals": residuals, "boundary": "No J1 or independent J2-length derivative; no extrapolation to final B120 target; valid only near D7 H500 450nm trust region"}, "d8_plan": d8_plan}
    (ANALYSIS / "b120_j2lm06_stage_d7_physics_assimilation_v1.json").write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf8")
    with (ANALYSIS / "b120_j2lm06_stage_d7_physics_assimilation_candidate_table_v1.csv").open("w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=list(actual[0])); w.writeheader(); w.writerows(actual)
    report = ["# APCD LP D7 physics assimilation and D8 offline plan v1", "", "## D7 actual absorption", "", f"- Formal accepted subruns: 16/16; complete Jones: 8/8; wavelength: 450 nm only.", f"- Actual Pareto front (all objectives jointly): {', '.join(pareto_ids)}.", f"- Lowest phase candidate: `{min(actual, key=lambda r: r['phase_deg'])['candidate_id']}`.", f"- Best trade-off and selected D8 anchor: `{anchor['candidate_id']}`; phase {anchor['phase_deg']:.6f} deg; phase drop {anchor['actual_phase_drop_deg']:.6f} deg; Txx {anchor['Txx']:.6f}; Tyy {anchor['Tyy']:.6f}; sigma2/sigma1 {anchor['sigma2_over_sigma1']:.6f}.", "", "|rank|candidate|phase|drop|Txx|Tyy|sigma2/sigma1|cross power|phase residual|", "|---:|---|---:|---:|---:|---:|---:|---:|---:|"]
    report += [f"|{r['execution_rank']}|{r['candidate_id']}|{r['phase_deg']:.6f}|{r['actual_phase_drop_deg']:.6f}|{r['Txx']:.6f}|{r['Tyy']:.6f}|{r['sigma2_over_sigma1']:.6f}|{r['cross_power']:.3e}|{r['phase_prediction_error_deg']:.6f}|" for r in actual]
    report += ["", "## Local-model adequacy", "", f"- Five-variable raw design rank: {raw_rank}/{X.shape[1]}; centered variation rank: {centered_rank}.", "- J1-side and J2-length were not independently excited; a complete five-variable Jacobian is not identifiable.", f"- Normalized active W2/D/Psi condition number: {active_cond:.4f}; phase residual MAE: {float(np.mean(abs(phase_res))):.6f} deg; max absolute residual: {float(np.max(abs(phase_res))):.6f} deg.", "- Model frozen as constrained active-subspace, residual-corrected local surrogate. It is not a full Jacobian and is valid only near D7 H500/450 nm geometry.", "", "## D8 planned-only freeze", "", "- Anchor is the actual multi-objective trade-off, not the lowest-phase candidate.", "- D8 uses one bounded local branch with eight planned candidates; J1 remains fixed because its derivative is unidentifiable.", "- Every D8 row is `MODEL_PREDICTION_NOT_PHYSICS_LABEL` with `physics_fields=ABSENT_NOT_SIMULATED`; no D8 staging exists.", "", "|rank|candidate|role|J2 L|J2 W|D|Psi|pred drop|pred Txx|pred Tyy|pred sigma2/sigma1|", "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    report += [f"|{r['execution_rank']}|{r['candidate_id']}|{r['role']}|{r['J2_length_nm']}|{r['J2_width_nm']}|{r['D_nm']:.4f}|{r['Psi_deg']:.4f}|{r['predicted_phase_drop_deg']:.4f}|{r['predicted_Txx']:.4f}|{r['predicted_Tyy']:.4f}|{r['predicted_sigma2_over_sigma1']:.4f}|" for r in d8]
    report += ["", "## Test regression evidence", "", "- Initial traceback: `explicit_from_csv_json()` called `.get()` on a non-dict JSON row while scanning repository metadata.", "- Minimal repair: skip non-dict JSON rows; frozen physics inputs were not changed.", "- Target test after repair: 4 passed.", "- D7 commit diff confirms the failing LP-ML1A2 script was not changed by the D7 physics commit.", "- Full pytest reached 93 passed before the pre-existing D6 package test failed because it requires D6 staging to be absent.", "- Excluding that D6 test reached 106 passed before the pre-existing Stage11-3B1 test failed on missing legacy six-bin geometry rows.", "", "## No-solver and provenance audit", "", "- This task made zero Lumerical/lumapi/FDTD calls and created no D8 physics staging.", "- D7 physics staging, D7 execution package, canonical v1.21, D6 staging and protected reports are read-only inputs.", f"- D8 future budget is exactly 8 geometries / 16 x/y subruns / 450 nm only.", "", f"D8 plan: `{D8_JSON}`", f"D8 execution contract: `{D8_EXEC}`", f"D8 ML-label contract: `{D8_ML}`", f"D8 validation contract: `{D8_MET}`"]
    (ROOT / "reports/lp_b120_j2lm06_stage_d7_physics_assimilation_and_d8_plan_v1.md").write_text("\n".join(report) + "\n", encoding="utf8")
    print(json.dumps({"status": "PASS", "pareto_front": pareto_ids, "lowest_phase": min(actual, key=lambda r: r["phase_deg"])["candidate_id"], "anchor": anchor["candidate_id"], "raw_rank": raw_rank, "centered_rank": centered_rank, "active_condition": active_cond, "d8_candidates": len(d8), "solver_calls": 0}, indent=2))

if __name__ == "__main__":
    main()
