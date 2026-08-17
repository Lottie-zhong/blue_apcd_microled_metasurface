from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(r"D:\\project\\worktrees\\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / "outputs" / "np_k6_m10a_angular_handoff_preparation_v1"
M9A = ROOT / "outputs" / "np_k6_m9a_normal_incidence_plateau_reassessment_v1"
REPORT = OUT / "m10a_validator_report.json"


def load(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    checks: dict[str, bool] = {}
    failures: list[str] = []

    def check(name: str, value: bool, detail: str = "") -> None:
        checks[name] = bool(value)
        if not value:
            failures.append(f"{name}: {detail}" if detail else name)

    decision = load("decision.json")
    solver = load("solver_zero_audit.json")
    prov = load("provenance_audit.json")
    registry = load("NP_EXISTING_NONZERO_UX_HF_PROVENANCE_REGISTRY_V1.json")
    prereg = load("NP_ANGULAR_HF_SELECTION_METHOD_PREREG_V1.json")
    prereg_hash = load("selection_preregistration_sha256.json")
    schema = load("NP_ANGULAR_PROVIDER_DATA_SCHEMA_V1.json")
    checklist = load("NP_ANGULAR_PROVIDER_HANDOFF_READINESS_CHECKLIST_V1.json")

    actual_prereg_hash = sha(OUT / "NP_ANGULAR_HF_SELECTION_METHOD_PREREG_V1.json")
    check("selection_prereg_hash", actual_prereg_hash == prereg_hash["sha256"], actual_prereg_hash)
    check("m9a_prereg_hash", prereg["m9a_prereg_sha256"] == "0ee8251bff8ca4b6c3cdb982f1fc9a2387caf6e3cd370ccfe9dc6e551080bf91")
    check("m9a_decision_present", (M9A / "decision.json").exists())
    if (M9A / "decision.json").exists():
        m9a_decision = json.loads((M9A / "decision.json").read_text(encoding="utf-8"))
        check("m9a_status_unchanged", "NP_K6_M9A" in str(m9a_decision.get("status", "")))

    check("decision_status", decision["status"] == "NP_K6_M10A_ANGULAR_HANDOFF_PREPARATION_COMPLETE_WAIT_COUPLING_B")
    check("nonzero_u_x_empty", registry["nonzero_u_x_formal_cases"] == [])
    audit = registry["reported_plus_0224_audit"]
    check("plus_0224_unresolved", audit["classification"] == "NOT_FOUND_IN_NP_AUTHORITY" and audit["reusable_for_future_angular_calibration"] == "no")
    check("no_control_label", audit["control0_alt1_or_b_identity"].startswith("UNRESOLVED"))

    rows = registry["rows"]
    keys = [tuple(row[k] for k in ("geometry_hash", "exact_u_x", "polarization", "wavelength_contract", "physics_contract_id")) for row in rows]
    check("historical_rows_present", len(rows) == 6)
    check("historical_unique", len(keys) == len(set(keys)))
    check("normal_only_rows", all(row["exact_u_x"] == 0.0 for row in rows))
    check("ordered_geometry_preserved", all(row["ordered_D1_D6"] for row in rows))

    check("schema_id", schema["schema_id"] == "NP_ANGULAR_PROVIDER_DATA_SCHEMA_V1")
    check("schema_inputs", schema["inputs"][:6] == ["D1", "D2", "D3", "D4", "D5", "D6"])
    check("schema_normal_only", schema["current_domain"]["u_x"] == [0.0] and schema["current_domain"]["k_y"] == [0.0])
    check("no_numeric_promotion_threshold", "no absolute promotion threshold" in prereg["threshold_policy"])
    check("selection_order_frozen", prereg["future_candidate_order"] == ["raw RCWA", "constant/local bias", "affine calibration", "Ridge residual", "compact residual MLP only if justified"])

    with (OUT / "NP_COUPLING_RELEVANT_ANGULAR_HF_PRIMARY_BATCH_TEMPLATE_V1.csv").open(newline="", encoding="utf-8") as f:
        template_rows = list(csv.DictReader(f))
    check("future_batch_empty", template_rows == [])

    zero_keys = ["FDTD", "RCWA", "TMM", "BFAST", "new_HF", "external_HF", "ML_training", "inverse", "replay", "coupling_B_read", "coupling_B_polling", "coupling_worktree_writes"]
    check("solver_zero", all(solver.get(k) == 0 for k in zero_keys), str({k: solver.get(k) for k in zero_keys}))
    check("coupling_untouched", prov["coupling_B_read"] is False and prov["coupling_B_polled"] is False and prov["coupling_worktree_modified"] is False)
    check("m9a_unchanged", prov["m9a_artifacts_unchanged"] is True)
    check("readiness_waits_for_b", checklist["current_status"] == "WAIT_COUPLING_B_TERMINAL_EVIDENCE")

    scaffold_path = ROOT / "scripts" / "np_k6_m10a_angular_provider_scaffold_v1.py"
    text = scaffold_path.read_text(encoding="utf-8")
    for forbidden in ("lumapi", ".run(", "fdtd.run", "torch", "tensorflow", "sklearn"):
        check(f"scaffold_no_{forbidden.replace('.', '').replace('(', '')}", forbidden.lower() not in text.lower())
    spec = importlib.util.spec_from_file_location("m10a_scaffold", scaffold_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    key = module.make_angular_unique_key({"geometry_hash": "g", "u_x_identity": "ux0", "polarization": "P", "wavelength_contract": "445-455", "physics_contract_id": "p"})
    check("scaffold_key", key == ("g", "ux0", "P", "445-455", "p"))
    check("scaffold_metric", module.E_MDC_weighted({"eta_plus1": 2.0, "T_total": 1.0}, {"eta_plus1": 0.5, "T_total": 0.8, "eta_m+1": 0.5}, {"eta_plus1": 0.6, "T_total": 0.7, "eta_m+1": 0.4})["weighted_total"] > 0.0)
    check("scaffold_margin_zero", module.provider_error_to_candidate_margin_ratio(0.1, 0.0) is None)

    bad_suffixes = {".fsp", ".npz", ".log"}
    bad = [str(p.relative_to(OUT)) for p in OUT.rglob("*") if p.is_file() and (p.suffix.lower() in bad_suffixes or "runtime" in p.parts)]
    check("no_runtime_or_solver_artifacts", bad == [], str(bad))

    report = {"validator": "validate_np_k6_m10a_angular_handoff_preparation_v1", "passed": not failures, "checks": checks, "failures": failures, "solver_calls": 0, "coupling_B_read": 0}
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
