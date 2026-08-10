"""Independent, zero-solver validator for the NP K6 M3 pilot evidence.

This validator deliberately does not import the training implementation or lumapi;
it checks the persisted authority, derived training view, CV tables, and explicit
zero-solver/provenance assertions from the outside.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / r"outputs\np_k6_m3_pilot_retraining_v1"


def read_json(name: str) -> dict[str, Any]:
    with (OUT / name).open(encoding="utf-8-sig") as f:
        return json.load(f)


def read_csv(name: str) -> list[dict[str, str]]:
    with (OUT / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def truth(value: Any) -> bool:
    return value is True or str(value).strip().lower() in {"true", "1", "yes"}


def finite(value: str) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check(name: str, condition: bool, checks: dict[str, bool], errors: list[str]) -> None:
    checks[name] = bool(condition)
    if not condition:
        errors.append(name)


def main() -> int:
    checks: dict[str, bool] = {}
    errors: list[str] = []

    required_json = [
        "acquisition_ensemble_manifest.json",
        "batch1_runtime_cost_audit.json",
        "development_label_promotion_audit.json",
        "m1_m3_comparison_summary.json",
        "m3_oof_metrics_summary.json",
        "m3_training_state.json",
        "p_s_paired_diagnostic_summary.json",
        "pre_m3_acquisition_audit_summary.json",
        "pre_m3_authority_audit.json",
        "solver_zero_audit.json",
        "m3_live_process_audit.json",
        "m3_test_audit.json",
        "checksum_manifest.json",
    ]
    required_csv = [
        "development_hf_v2_training_view.csv",
        "m3_oof_fold_metrics.csv",
        "m3_oof_predictions_long.csv",
        "m3_oof_stratified_metrics.csv",
        "p_s_paired_diagnostic_long.csv",
        "pre_m3_acquisition_error_audit_132rows.csv",
    ]
    check(
        "required_evidence_files",
        all((OUT / name).is_file() for name in required_json + required_csv),
        checks,
        errors,
    )
    if errors:
        report = {"schema_version": "np_k6_m3_standalone_validator_v1", "status": "FAIL", "checks": checks, "errors": errors}
        print(json.dumps(report, indent=2))
        return 1

    training = read_csv("development_hf_v2_training_view.csv")
    authority = read_json("pre_m3_authority_audit.json")
    promotion = read_json("development_label_promotion_audit.json")
    check("training_view_198_rows", len(training) == 198, checks, errors)
    check("training_view_9_geometry_ids", len({r["geometry_id"] for r in training}) == 9, checks, errors)
    check("training_view_9_geometry_hashes", len({r["geometry_hash"] for r in training}) == 9, checks, errors)
    check("training_view_18_cases", len({r["case_id"] for r in training}) == 18, checks, errors)
    check("training_view_p_s_separate", {r["polarization"] for r in training} == {"p", "s"}, checks, errors)
    check("training_view_exact_wavelengths", {int(r["wavelength_nm"]) for r in training} == set(range(445, 456)), checks, errors)
    check("training_view_complete_geometry_pol_wavelength", len({(r["geometry_hash"], r["polarization"], int(r["wavelength_nm"])) for r in training}) == 198, checks, errors)
    check("training_view_quality_gate", all(truth(r["quality_gate_pass"]) for r in training), checks, errors)
    check("training_view_training_label", all(truth(r["training_label"]) for r in training), checks, errors)
    check("training_view_not_diagnostic", all(not truth(r["diagnostic_only"]) for r in training), checks, errors)
    check("training_view_generator_identity", {r["generator_id"] for r in training} == {"NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_3PS_V2"}, checks, errors)
    check("training_view_interface_identity", {r["interface_stack_id"] for r in training} == {"NP_K6_INDEPENDENT_STACK_PILOT_V1"}, checks, errors)
    numeric_fields = ["T_total", "R_total", "eta_plus1", "eta_0", "eta_minus1", "directionality", "non_target_efficiency"]
    check("training_view_numeric_finite", all(finite(r[k]) for r in training for k in numeric_fields), checks, errors)
    check("authority_label_gate", truth(authority.get("label_gate_pass")), checks, errors)
    check("authority_numeric_identity_unchanged", truth(authority.get("numeric_and_identity_unchanged")), checks, errors)
    check("authority_sealed_zero", authority.get("sealed_target_reads") == 0, checks, errors)
    check("promotion_historical_source_immutable", truth(promotion.get("historical_source_immutable")), checks, errors)
    check("promotion_zero_solver", truth(promotion.get("promotion_is_zero_solver")), checks, errors)
    check("promotion_digest_equal", promotion.get("numeric_and_identity_digest_source") == promotion.get("numeric_and_identity_digest_target"), checks, errors)
    check("promotion_promoted_batch1_132", promotion.get("promoted_batch1_rows") == 132, checks, errors)

    preacq = read_csv("pre_m3_acquisition_error_audit_132rows.csv")
    preacq_summary = read_json("pre_m3_acquisition_audit_summary.json")
    check("preacq_132_rows", len(preacq) == 132, checks, errors)
    check("preacq_selection_time_source_frozen", all("M2" in r.get("selection_prediction_source", "") and "M3" in r.get("selection_prediction_source", "") for r in preacq), checks, errors)
    check("preacq_individual_order_schema_explicit", all(r.get("individual_order_prediction_available") == "False" for r in preacq), checks, errors)
    check("preacq_summary_rows", preacq_summary.get("rows") == 132, checks, errors)
    check("preacq_sealed_zero", preacq_summary.get("sealed_target_reads") == 0, checks, errors)
    check("preacq_has_per_geometry_polarization", len(preacq_summary.get("per_geometry_polarization", [])) == 12, checks, errors)
    check("preacq_uncertainty_value_caveated", preacq_summary.get("aggregate", {}).get("individual_order_prediction_available") is False, checks, errors)

    ps = read_csv("p_s_paired_diagnostic_long.csv")
    ps_summary = read_json("p_s_paired_diagnostic_summary.json")
    check("ps_9_geometry_11_wavelength_13_metrics", len(ps) == 9 * 11 * 13, checks, errors)
    check("ps_not_merged", ps_summary.get("p_s_not_merged_for_training") is True, checks, errors)
    check("ps_equivalence_claim_false", ps_summary.get("final_p_s_equivalence_claim") is False, checks, errors)
    check("ps_pending_classification", ps_summary.get("classification") == "P_S_SIMILARITY_CANDIDATE_PENDING_MORE_HF_DATA", checks, errors)

    folds = read_csv("m3_oof_fold_metrics.csv")
    predictions = read_csv("m3_oof_predictions_long.csv")
    stratified = read_csv("m3_oof_stratified_metrics.csv")
    model_names = {"CNN", "MLP", "LF_DFT"}
    geometries = {r["geometry_id"] for r in training}
    check("oof_9_fold_metrics", len(folds) == 27 and {r["model"] for r in folds} == model_names, checks, errors)
    check("oof_594_prediction_rows", len(predictions) == 594, checks, errors)
    check("oof_378_stratified_rows", len(stratified) == 378, checks, errors)
    check("oof_geometry_grouped", all(r["held_out_geometry"] == r["geometry_id"] for r in predictions), checks, errors)
    check("oof_all_geometry_folds", all({r["held_out_geometry"] for r in predictions if r["model"] == model} == geometries for model in model_names), checks, errors)
    pred_keys = [(r["model"], r["geometry_id"], r["case_id"], r["wavelength_nm"]) for r in predictions]
    check("oof_no_duplicate_predictions", len(pred_keys) == len(set(pred_keys)), checks, errors)
    pred_numeric = [k for k in predictions[0] if k.startswith("pred_") or k.startswith("truth_")] if predictions else []
    check("oof_numeric_finite", all(finite(r[k]) for r in predictions for k in pred_numeric), checks, errors)
    check("oof_fold_no_nan_inf_or_negative", all(r.get("nan_inf_count") == "0" and r.get("negative_power_violations") == "0" for r in folds), checks, errors)
    oof_summary = read_json("m3_oof_metrics_summary.json")
    check("oof_summary_9_folds", oof_summary.get("fold_count") == 9, checks, errors)
    check("oof_summary_geometry_group_cv", str(oof_summary.get("geometry_group_cv", "")).lower() in {"leave_one_geometry_out", "leave-one-geometry-out"}, checks, errors)

    ensemble = read_json("acquisition_ensemble_manifest.json")
    check("ensemble_6_models", ensemble.get("model_count") == 6 and len(ensemble.get("models", [])) == 6, checks, errors)
    check("ensemble_training_rows", ensemble.get("training_rows") == 198, checks, errors)
    check("ensemble_solver_zero", ensemble.get("solver_run_invocations") == 0, checks, errors)
    check("ensemble_sealed_zero", ensemble.get("sealed_target_reads") == 0, checks, errors)
    check("ensemble_ps_separate", ensemble.get("p_s_inputs_kept_separate") is True, checks, errors)
    state = read_json("m3_training_state.json")
    check("state_complete", state.get("status") == "NP_K6_M3_PILOT_RETRAINING_COMPLETE_ACTIVE_LEARNING_REASSESSMENT_READY", checks, errors)
    check("state_real_training_false", state.get("real_training_started") is False, checks, errors)
    check("state_bulk_training_false", state.get("bulk_mdc_compatible_training_authorized") is False, checks, errors)
    check("state_solver_zero", state.get("solver_run_invocations") == 0, checks, errors)
    check("state_sealed_zero", state.get("sealed_target_reads") == 0, checks, errors)

    runtime = read_json("batch1_runtime_cost_audit.json")
    check("runtime_physical_13", runtime.get("physical_solver_invocation_count") == 13, checks, errors)
    check("runtime_accepted_12", runtime.get("accepted_execution_count") == 12, checks, errors)
    check("runtime_lost_infrastructure_1", runtime.get("lost_infrastructure_execution_count") == 1, checks, errors)
    check("runtime_replacement_1", runtime.get("replacement_execution_count") == 1, checks, errors)
    check("runtime_long_tail_present", len(runtime.get("long_tail_cases", [])) >= 3, checks, errors)

    zero = read_json("solver_zero_audit.json")
    check("solver_zero_fdtd", zero.get("fdtd_run_invocations") == 0, checks, errors)
    check("solver_zero_lumapi", zero.get("lumapi_run_invocations") == 0, checks, errors)
    check("solver_zero_sealed", zero.get("sealed_target_reads") == 0, checks, errors)
    check("solver_zero_batch2", zero.get("batch2_started") is False, checks, errors)
    check("solver_zero_no_lumerical_import", zero.get("lumerical_imported") is False, checks, errors)
    live = read_json("m3_live_process_audit.json")
    check("live_process_audit_read_only", live.get("read_only") is True and live.get("process_query_returncode") == 0, checks, errors)
    check("live_process_audit_m3_zero", live.get("m3_related_process_count") == 0 and live.get("solver_started_by_m3_stage") is False, checks, errors)
    check("live_process_audit_sealed_zero", live.get("sealed_access") == 0, checks, errors)
    test_audit = read_json("m3_test_audit.json")
    check("stage_specific_pytest_pass", test_audit.get("stage_specific_pytest", {}).get("status") == "PASS" and test_audit.get("stage_specific_pytest", {}).get("passed") == 5, checks, errors)
    check("frozen_m1_m2_pytest_pass", test_audit.get("frozen_m1_m2_relevant_pytest", {}).get("status") == "PASS" and test_audit.get("frozen_m1_m2_relevant_pytest", {}).get("passed") == 16, checks, errors)
    check("test_audit_solver_zero", test_audit.get("solver_run_invocations") == 0 and test_audit.get("sealed_target_reads") == 0, checks, errors)

    manifest = read_json("checksum_manifest.json")
    files_ok = True
    for item in manifest.get("files", []):
        p = OUT / item["path"]
        files_ok = files_ok and p.is_file() and sha256(p) == item["sha256"] and p.stat().st_size == item["size_bytes"]
    check("checksum_manifest_matches", files_ok, checks, errors)
    check("runtime_checkpoints_excluded", manifest.get("runtime_checkpoints_excluded") is True and not any(str(item.get("path", "")).endswith(".pt") and item.get("git_candidate") for item in manifest.get("files", [])), checks, errors)

    report = {
        "schema_version": "np_k6_m3_standalone_validator_v1",
        "status": "PASS" if not errors else "FAIL",
        "checks": checks,
        "errors": errors,
        "solver_run_invocations": 0,
        "sealed_target_reads": 0,
        "scope": "zero-solver independent evidence validation; no lumapi import",
    }
    (OUT / "m3_standalone_validator_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
