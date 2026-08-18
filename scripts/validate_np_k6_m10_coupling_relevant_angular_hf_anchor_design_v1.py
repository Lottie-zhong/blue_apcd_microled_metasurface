from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

NP = Path(r"D:\\project\\worktrees\\blue_apcd_np_k6_mdc_v1")
CP = Path(r"D:\\project\\worktrees\\blue_apcd_mdc_np_coupling_v1")
OUT = NP / "outputs" / "np_k6_m10_angular_hf_anchor_design_v1"
PKG = CP / "outputs" / "coupling" / "COUPLING_TO_NP_ANGULAR_HANDOFF_TERMINAL_PACKAGE_V1"
REPORT = OUT / "m10_anchor_validator_report.json"


def j(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def main() -> int:
    checks = {}
    failures = []

    def check(name, value, detail=""):
        checks[name] = bool(value)
        if not value:
            failures.append(f"{name}: {detail}" if detail else name)

    pin = j("NP_CONSUMED_COUPLING_B_TERMINAL_PACKAGE_PIN_V1.json")
    recheck = j("NP_CONSUMED_COUPLING_B_TERMINAL_PACKAGE_RECHECK_V1.json")
    manifest = json.loads((PKG / "COUPLING_TO_NP_ANGULAR_HANDOFF_TERMINAL_PACKAGE_V1.json").read_text(encoding="utf-8"))
    package_validator = json.loads((PKG / "COUPLING_TO_NP_ANGULAR_HANDOFF_VALIDATOR_V1.json").read_text(encoding="utf-8"))
    selection = j("NP_K6_M10_COUPLING_RELEVANT_ANGULAR_HF_SELECTION_PREREG_V1.json")
    selection_sha = j("selection_preregistration_sha256.json")
    gate = j("NP_M10_DECISION_STABILITY_GATE_PREREG_V1.json")
    score = j("NP_M10_ANGULAR_CANDIDATE_SCORECARD_V1.json")["rows"]
    mass = j("NP_M10_MDC_MISSINGNESS_AUDIT_V1.json")
    existing = j("NP_M10_EXISTING_HF_3OF4_AUDIT_V1.json")
    batch = j("NP_COUPLING_RELEVANT_ANGULAR_HF_PRIMARY_BATCH_V1.json")
    zero = j("solver_zero_audit.json")
    prov = j("provenance_audit.json")
    decision = j("decision.json")

    check("pin_id", pin["pin_id"] == "NP_CONSUMED_COUPLING_B_TERMINAL_PACKAGE_PIN_V1")
    check("pin_source_identity", pin["source_branch"] == "work/mdc-np-coupling-v1" and pin["source_head"].startswith("92ccb154"))
    check("pin_dirty_state_recorded", pin["source_worktree_dirty"] is True)
    check("pin_hash_status", pin["validator_status"] == "PASS_HASH_STABLE_AFTER_READ")
    check("pin_file_count", pin["package_file_count"] == 17)
    current_hashes = {}
    changed = []
    for item in pin["artifacts"]:
        p = PKG / item["relative_path"]
        current_hashes[item["relative_path"]] = sha(p)
        if current_hashes[item["relative_path"]] != item["sha256"] or p.stat().st_size != item["size"]:
            changed.append(item["relative_path"])
    check("package_hashes_stable", changed == [] and recheck["changed_files"] == [])
    check("package_validator_pass", package_validator["status"] == "PASS")
    check("package_status_ready", manifest["status"] == "COUPLING_TO_NP_ANGULAR_HANDOFF_TERMINAL_PACKAGE_V1_READY_FOR_NP_CONSUMPTION")
    check("package_no_intermediate_read", pin["coupling_intermediate_read"] is False and prov["coupling_intermediate_read"] is False)
    check("coupling_untouched", pin["coupling_worktree_modified"] is False and prov["coupling_worktree_modified"] is False)

    alt = manifest["identities"]["ALT1"]
    ctrl = manifest["identities"]["CONTROL0"]
    check("alt1_identity", alt["candidate_id"] == "NP_K6X_100_115_130_145_155_185" and alt["diameters_nm"] == [100, 115, 130, 145, 155, 185])
    check("control_identity", ctrl["candidate_id"] == "NP_K6X_125_135_150_175_190_210" and ctrl["diameters_nm"] == [125, 135, 150, 175, 190, 210])
    check("identity_audit", j("exact_geometry_identity_audit.json")["identity_match"] is True)
    check("scope_contract", manifest["exact_wavelengths_nm"] == list(range(445, 456)))
    check("order_convention", j("NP_M10_PROVIDER_EVIDENCE_AUDIT_V1.json")["order_convention"] == "m=+1 physical +x")

    check("selection_prereg_hash", sha(OUT / "NP_K6_M10_COUPLING_RELEVANT_ANGULAR_HF_SELECTION_PREREG_V1.json") == selection_sha["sha256"])
    check("selection_prereg_before_selection", selection["created_after_package_pin"] is True and gate["created_before_new_HF"] is True)
    check("missing_policy", "!= zero" in selection["missing_data_policy"] and mass["formal_available_nodes"] == 4 and mass["missing_nodes"] == 5)
    check("no_missing_fill", all(row["fill_policy"] == "NO_FILL" and (row["MDC_IMPORTANCE"] == "UNKNOWN" or row["MDC_IMPORTANCE"] == "AVAILABLE_PARTIAL_NODE_PROXY") for row in mass["rows"]))
    check("decision_gate_frozen", gate["categories"]["DECISION_STABLE"] == "ratio < 0.5" and gate["categories"]["PROVIDER_ERROR_DECISION_CHANGING"] == "ratio >= 1")

    check("hf_3of4", existing["coverage"] == "3/4" and existing["accepted_logical_cases"] == 3)
    check("p_0224_unresolved", existing["P_plus_0224"]["status"] == "UNRESOLVED_AFTER_TWO_ENTERED_FAILURES" and existing["P_plus_0224"]["attempt_003"] is False and existing["P_plus_0224"]["replay"] is False)
    reusable = {(round(float(r["ux_exact"]), 12), r["polarization"]) for r in existing["rows"] if r["reusable"]}
    check("exact_reuse_cases", (round(0.22413793103448276, 12), "S_YLIKE") in reusable and (round(0.37868939998860307, 12), "P_XLIKE") in reusable and (round(0.37868939998860307, 12), "S_YLIKE") in reusable)

    check("decision_status", decision["status"] == "NP_K6_M10_COUPLING_RELEVANT_ANGULAR_HF_PRIMARY_BATCH_READY_FOR_SOLVER_AUTHORIZATION" and decision["solver_authorized"] is False)
    new_rows = [r for r in batch["rows"] if r["existing_or_new"] == "new"]
    check("batch_new_count", len(new_rows) == 2 and batch["new_solver_invocation_count"] == 2)
    check("batch_within_hard_max", batch["new_solver_invocation_count"] <= 6)
    check("batch_preferred_reduced", batch["preferred_batch_reduced_from_4_by_exact_existing_HF_reuse"] is True)
    check("batch_ps_explicit", all(r["polarization"] in ("P_XLIKE", "S_YLIKE") for r in batch["rows"]))
    check("p_0224_not_queued", batch["P_plus_0224_not_queued"] is True and not any(abs(float(r["ux_exact"]) - 0.22413793103448276) < 1e-10 and r["existing_or_new"] == "new" for r in batch["rows"]))
    check("negative_0482_primary_pair", {(round(float(r["ux_exact"]), 12), r["polarization"]) for r in new_rows} == {(round(-0.48275862068965514, 12), "P_XLIKE"), (round(-0.48275862068965514, 12), "S_YLIKE")})
    check("negative_0954_deferred", all(r["existing_or_new"] == "deferred" for r in batch["rows"] if abs(float(r["ux_exact"]) + 0.9549788465408765) < 1e-10))
    check("scorecard_has_five_nodes", len(score) == 5)
    check("scorecard_unknown_preserved", any(r["MDC_IMPORTANCE"] == "UNKNOWN" and r["MDC_mass"] is None for r in score))
    check("scorecard_raw_and_normalized", all("MDC_normalized" in r and "RCWA_gradient_normalized" in r and "why_selected_or_rejected" in r for r in score))

    zero_keys = ["FDTD", "RCWA", "TMM", "BFAST", "ML_training", "new_HF", "external_HF", "inverse", "replay", "attempt_003", "coupling_worktree_writes", "coupling_intermediate_poll", "coupling_intermediate_read"]
    check("solver_zero", all(zero.get(k) == 0 for k in zero_keys), str({k: zero.get(k) for k in zero_keys}))
    check("provenance_zero", prov["solver_calls"] == 0 and prov["external_hf"] == 0 and prov["sealed_reads"] == 0)
    check("no_solver_artifacts", not any(p.is_file() and p.suffix.lower() in {".fsp", ".npz"} for p in OUT.rglob("*")))
    check("doc_present", (NP / "docs" / "np_k6_m10_coupling_relevant_angular_hf_anchor_design_v1.md").exists())

    report = {"validator": "validate_np_k6_m10_coupling_relevant_angular_hf_anchor_design_v1", "passed": not failures, "checks": checks, "failures": failures, "solver_calls": 0, "new_batch_solver_count": batch["new_solver_invocation_count"], "coupling_intermediate_read": 0, "coupling_worktree_writes": 0}
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
