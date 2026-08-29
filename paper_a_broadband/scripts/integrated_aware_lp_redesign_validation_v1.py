from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


REQUIRED = {
    "integrated_aware_lp_redesign_contract_v1.json",
    "integrated_baseline_metrics.json",
    "integrated_local_domain_authority.json",
    "integrated_feasible_pool.csv",
    "integrated_candidate_registry_initial.csv",
    "integrated_candidate_registry_conditional.csv",
    "integrated_mechanism_selection_audit.json",
    "future_solver_budget_plan.json",
    "final_report.md",
    "audit.json",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def num(row, key):
    return float(row[key])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir
    checks = {}

    missing = sorted(name for name in REQUIRED if not (out / name).is_file())
    checks["required_artifacts"] = {"pass": not missing, "missing": missing}
    contract = load_json(out / "integrated_aware_lp_redesign_contract_v1.json")
    domain = load_json(out / "integrated_local_domain_authority.json")
    selection = load_json(out / "integrated_mechanism_selection_audit.json")
    budget = load_json(out / "future_solver_budget_plan.json")
    baseline = load_json(out / "integrated_baseline_metrics.json")
    audit = load_json(out / "audit.json")

    checks["contract_status_and_scope"] = {"pass": contract.get("schema") == "PAPER_A_INTEGRATED_AWARE_LP_REDESIGN_CONTRACT_V1" and contract.get("status") == "INTEGRATED_LOCAL_SPACE_TOO_CONSTRAINED" and contract.get("design_space", {}).get("fixed", {}).get("finite_array") == "5x5" and contract.get("limitations", {}).get("W_emit") == "UNRESOLVED_FOR_PRODUCTION_CLOSURE" and contract.get("limitations", {}).get("incident_plane") == "INCIDENT_I03_FIELD_NOT_AVAILABLE"}
    current = budget["current_stage"]
    checks["zero_solver"] = {"pass": current == {"NEW_FDTD_BUDGET": 0, "solver_run_called": False, "solver_entered": 0, "RCWA": 0, "ML": 0, "new_MQW_wells": 0, "executed": False}, "accounting": current}
    checks["selection_audit"] = {"pass": selection.get("status") == "PASS" and selection.get("selection_is_geometry_only") is True and selection.get("no_optical_prediction") is True and selection.get("all_selected_geometry_valid") is True and selection.get("all_direct_clearance_ge_60") is True and selection.get("all_periodic_clearance_ge_60") is True and selection.get("all_hashes_unique") is True and selection.get("baseline_i03_excluded") is True and selection.get("all_geometry_hashes_recomputed_match") is True and selection.get("IAR1_requested_direction_feasible") is False and abs(selection.get("IAR1_max_pool_minus_I03", 1.0)) < 1e-12}

    pool = load_csv(out / "integrated_feasible_pool.csv")
    initial = load_csv(out / "integrated_candidate_registry_initial.csv")
    conditional = load_csv(out / "integrated_candidate_registry_conditional.csv")
    bounds = domain["narrow_bounds"]
    pool_valid = True
    for row in pool:
        for key in ("L1_nm", "W1_nm", "L2_nm", "W2_nm", "D_nm", "delta_theta_deg"):
            pool_valid &= bounds[key][0] <= num(row, key) <= bounds[key][1]
        pool_valid &= num(row, "direct_clearance_nm") >= 60.0 and num(row, "periodic_image_clearance_nm") >= 60.0
        pool_valid &= row["cell_containment_pass"].lower() == "true" and row["overlap_or_touching_pass"].lower() == "true" and row["geometry_hash_recomputed_match"].lower() == "true"
    checks["narrow_pool"] = {"pass": len(pool) == domain["pool_count"] and len(pool) == 2487 and pool_valid, "count": len(pool), "declared_count": domain["pool_count"]}
    selected = initial + conditional
    checks["candidate_counts_and_validity"] = {"pass": len(initial) == 4 and len(conditional) == 2 and all(row["geometry_valid"].lower() == "true" and row["direct_clearance_ge_60"].lower() == "true" and row["periodic_clearance_ge_60"].lower() == "true" and row["geometry_hash_recomputed_match"].lower() == "true" for row in selected) and len({row["geometry_hash_sha256"] for row in selected}) == 6, "initial_ids": [row["geometry_id"] for row in initial], "conditional_ids": [row["geometry_id"] for row in conditional]}
    checks["baseline_metrics"] = {"pass": math.isclose(baseline["pair_DoLP"], 0.037876844117608964, abs_tol=1e-12) and math.isclose(baseline["C_source"], 0.08854257161559786, abs_tol=1e-12) and math.isclose(baseline["C_angular"], 0.08612761641165362, abs_tol=1e-12) and math.isclose(baseline["xy_Poincare_separation_deg"], 100.45025108271777, abs_tol=1e-12)}
    report = (out / "final_report.md").read_text(encoding="utf-8")
    checks["report_boundaries"] = {"pass": "INTEGRATED_LOCAL_SPACE_TOO_CONSTRAINED" in report and "INCIDENT_I03_FIELD_NOT_AVAILABLE" in report and "UNRESOLVED_FOR_PRODUCTION_CLOSURE" in report and "no candidate is predicted" in report.lower()}
    checks["audit_consistency"] = {"pass": audit.get("status") == "PASS" and audit.get("solver_accounting") == current and audit.get("pool_count") == 2487 and audit.get("selected_initial_count") == 4 and audit.get("selected_conditional_count") == 2 and audit.get("all_selected_valid") is True and audit.get("all_hashes_unique") is True}
    result = {"schema": "PAPER_A_INTEGRATED_AWARE_LP_REDESIGN_VALIDATION_V1", "status": "PASS" if all(value["pass"] for value in checks.values()) else "FAIL", "checks": checks}
    (out / "integrated_validation_tests.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
