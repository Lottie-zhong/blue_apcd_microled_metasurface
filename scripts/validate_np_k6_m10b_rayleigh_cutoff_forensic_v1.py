from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(r"D:\\project\\worktrees\\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / "outputs" / "np_k6_m10b_neg0482_rayleigh_cutoff_forensic_v1"
EXPECTED = {
    "attempt001": "60c6f668b0f9fdc64b00b10fa00699314d4f377ac711ed6142290ac7020e67fc",
    "attempt002": "8f5da182c892c3602b9e29c6ea221324d15bc853a7a0e2f59da5a7ff16497e46",
}


def load(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def rows(name):
    with (OUT / name).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def validate():
    checks = []

    def check(name, ok, detail=""):
        checks.append({"name": name, "pass": bool(ok), "detail": detail})

    required = [
        "order_cutoff_table.csv",
        "kz_cutoff_distance_table.csv",
        "NP_NEG0482_DIFFRACTION_CUTOFF_DISTANCE_TABLE_V1.csv",
        "near_cutoff_order_power.csv",
        "closure_vs_cutoff_audit.csv",
        "good_angular_case_comparison.csv",
        "order_api_convention_audit.json",
        "rayleigh_crossing_audit.json",
        "order_schema_audit.json",
        "order_schema_completeness_audit.json",
        "spatial_mesh_audit.json",
        "pml_grazing_order_audit.json",
        "reference_plane_monitor_audit.json",
        "rcwa_cutoff_crosscheck.json",
        "forensic_classification.json",
        "diagnostic_decision.json",
        "forensic_evidence_consistency_audit.json",
        "solver_budget_audit.json",
        "provenance_audit.json",
    ]
    check("required_evidence", all((OUT / name).exists() for name in required))
    cutoff = rows("order_cutoff_table.csv")
    dist = rows("kz_cutoff_distance_table.csv")
    closure = rows("closure_vs_cutoff_audit.csv")
    power = rows("near_cutoff_order_power.csv")
    api = load("order_api_convention_audit.json")
    crossing = load("rayleigh_crossing_audit.json")
    schema = load("order_schema_audit.json")
    schema2 = load("order_schema_completeness_audit.json")
    classification = load("forensic_classification.json")
    decision = load("diagnostic_decision.json")
    budget = load("solver_budget_audit.json")
    prov = load("provenance_audit.json")

    lambdas = sorted({round(float(r["lambda_nm"])) for r in cutoff})
    check("exact_11_wavelengths", lambdas == list(range(445, 456)), str(lambdas))
    check("cutoff_table_complete", len(cutoff) == 352, str(len(cutoff)))
    check("cutoff_fields_finite", all(r.get("propagation_state") in {"PROPAGATING", "EVANESCENT"} for r in cutoff))
    check("api_order_convention", api.get("api_identity_verified") is True and api.get("max_abs_api_formula_error", 1) <= 1e-12)
    check("no_in_band_crossing", crossing.get("crossings_in_445_455_nm") == [])
    check("m_minus2_hypothesis_rejected", crossing.get("m_minus2_hypothesis", {}).get("confirmed") is False)
    check("transmitted_schema_complete", schema2.get("transmitted_schema_complete") is True)
    check("transmitted_orders_exact", schema2.get("transmitted_formal_orders") == [-1, 0, 1, 2, 3, 4, 5, 6])
    check("closure_pair_complete", len(closure) == 11)
    check("good_case_comparison_present", len(rows("good_angular_case_comparison.csv")) >= 3)
    check("attempt_post_sha_immutable", prov.get("attempt001_post_sha_unchanged") is True and prov.get("attempt002_post_sha_unchanged") is True)
    check("attempt_post_sha_expected", prov.get("read_only_fsp_posts") == [EXPECTED["attempt001"], EXPECTED["attempt002"]])
    check("solver_zero", budget.get("new_solver_calls") == 0 and budget.get("fdtd_calls") == 0 and budget.get("rcwa_calls") == 0)
    check("S_not_entered", budget.get("S_entered") == 0 and prov.get("S_entered") == 0)
    check("no_threshold_change", budget.get("threshold_changed") is False)
    check("rcwa_read_only", prov.get("rcwa_read_only") is True and load("rcwa_cutoff_crosscheck.json").get("rcwa_rerun") is False)
    check("classification_allowed", classification.get("primary_classification") in classification.get("classification_allowed_set", []))
    check("anchor_stress_only", decision.get("anchor_role") == "RAYLEIGH_STRESS_TEST_ONLY" and decision.get("primary_quantitative_calibration_anchor") is False)
    check("no_attempt003", decision.get("no_attempt003") is True)
    check("no_fsp_in_evidence_dir", not any(OUT.rglob("*.fsp")))
    check("order_power_rows", sum(1 for r in power if r.get("kind") == "transmission") == 88)
    report = {
        "validator": "validate_np_k6_m10b_rayleigh_cutoff_forensic_v1",
        "checks": checks,
        "passed": all(item["pass"] for item in checks),
        "new_solver_calls": 0,
        "S_entered": 0,
        "classification": classification.get("primary_classification"),
    }
    (OUT / "rayleigh_cutoff_forensic_validator_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
