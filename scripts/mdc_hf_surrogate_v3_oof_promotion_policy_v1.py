"""Pre-registered, outcome-blind V3 OOF promotion policy.

This module freezes evaluation level, eligibility gates, selection hierarchy and
the final-training interface without reading AL64/V3-Test40 truth or dispatching
any solver/training operation.  Future OOF outcome records are plain mappings
validated by this policy; they are not loaded from any sealed data path here.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DIR = ROOT / "contracts" / "mdc_hf_surrogate_v2"
PLAN_DIR = CONTRACT_DIR / "v3_plan_freeze_v1"
POLICY_DIR = CONTRACT_DIR / "v3_oof_promotion_policy_v1"

TRAINING_CONTRACT = PLAN_DIR / "v3_training_contract_v1.json"
MODEL_CONTRACT = PLAN_DIR / "v3_model_candidate_contract_v1.json"
LOSS_CONTRACT = PLAN_DIR / "v3_profile_only_loss_contract_v1.json"
TEST40_LOCK = PLAN_DIR / "v3_test40_manifest_lock_v1.json"
TEST40_OVERLAP = PLAN_DIR / "v3_test40_overlap_audit_v1.json"
FIXED_V2_OOF_POLICY = (
    ROOT
    / "outputs"
    / "mdc_hf_surrogate_v2_oof_model_selection_v1"
    / "20260804T_oof_model_selection_08915e7"
    / "oof_model_selection_policy.json"
)
FIXED_V2_OOF_COMPLETION = (
    ROOT
    / "outputs"
    / "mdc_hf_surrogate_v2_oof_model_selection_v1"
    / "20260804T_oof_model_selection_08915e7"
    / "oof_completion_manifest.json"
)
FIXED_V2_FAILURE_SUMMARY = (
    ROOT
    / "outputs"
    / "mdc_hf_surrogate_v2_failure_mechanism_diagnostic_fixed_v3_v1"
    / "20260809T_failure_mechanism_diagnostic_exact_latent_4169274"
    / "train_oof_test40_gap_audit.json"
)

STATUS = "MDC_HF_SURROGATE_V3_OOF_PROMOTION_POLICY_PREREGISTERED_WAITING_FOR_AL64"
CANDIDATES = ("V3-A", "V3-B", "V3-C")
SEEDS = (20260810, 20260811, 20260812)
OUTER_FOLDS = (0, 1, 2, 3, 4)
TOPOLOGIES = ("Explicit", "ZL1", "ZL2")
PROFILE_WEIGHTS = {
    "profile": 0.4117647058823529,
    "JS": 0.23529411764705882,
    "spectral_CDF": 0.17647058823529413,
    "angular_CDF": 0.17647058823529413,
}
PROFILE_COMPONENTS = tuple(PROFILE_WEIGHTS)
COLLAPSE_COMPONENT_THRESHOLD = 0.25
KNOWN_FAILURE_JS = 0.22933
KNOWN_FAILURE_WEIGHTED_L1 = 1.15060
# Only a machine-equality tolerance is permitted; this is not a performance
# tolerance and cannot be changed after seeing an OOF result.
MACHINE_EQUALITY_TOL = 8.0 * sys.float_info.epsilon
COMPLEXITY_RANK = {"V3-A": 0, "V3-B": 1, "V3-C": 2}


class PolicyError(RuntimeError):
    """A preregistered policy violation."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def object_sha(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _machine_equal(a: float, b: float) -> bool:
    return math.isclose(float(a), float(b), rel_tol=MACHINE_EQUALITY_TOL, abs_tol=MACHINE_EQUALITY_TOL)


def _metric(metrics: Mapping[str, Any], key: str) -> float:
    value = metrics.get(key)
    if not _finite(value):
        raise PolicyError(f"missing/nonfinite metric: {key}")
    return float(value)


def profile_composite(metrics: Mapping[str, Any]) -> float:
    """Frozen four-component profile-only geometry-level objective."""
    if metrics.get("evaluation_level") != "geometry":
        raise PolicyError("formal selection requires geometry-level metrics")
    return sum(PROFILE_WEIGHTS[key] * _metric(metrics, key) for key in PROFILE_COMPONENTS)


def collapse_audit(median_latent_variance_ratio: Any, collapsed_component_count: Any, latent_dimension: int = 32) -> dict[str, Any]:
    median = float(median_latent_variance_ratio)
    count = int(collapsed_component_count)
    if not _finite(median) or count < 0 or count > latent_dimension:
        raise PolicyError("invalid latent collapse audit")
    return {
        "per_component_threshold": COLLAPSE_COMPONENT_THRESHOLD,
        "median_latent_variance_ratio": median,
        "collapsed_component_count": count,
        "collapsed_component_fraction": count / float(latent_dimension),
        "catastrophic_latent_collapse": median < COLLAPSE_COMPONENT_THRESHOLD,
        "provenance": "fixed-v2 failure diagnostic variance_collapse_rule; threshold frozen before V3 OOF outcome",
    }


def _expected_fit_identities() -> set[tuple[int, int]]:
    return {(fold, seed) for fold in OUTER_FOLDS for seed in SEEDS}


def _fit_matrix_audit(record: Mapping[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    identities = {(int(row["outer_fold"]), int(row["seed"])) for row in record.get("fit_records", [])}
    expected = _expected_fit_identities()
    if identities != expected or len(record.get("fit_records", [])) != len(expected):
        reasons.append("INCOMPLETE_15_OF_15_OOF_FIT_MATRIX")
    for row in record.get("fit_records", []):
        for key in ("finite", "prediction_complete", "fold_leakage", "case_leakage", "pca_scaler_leakage", "outer_stop_contamination"):
            if key not in row:
                reasons.append(f"MISSING_FIT_AUDIT_FIELD:{key}")
            elif key in {"finite", "prediction_complete"} and row[key] is not True:
                reasons.append(f"FIT_{key.upper()}_FAIL")
            elif key in {"fold_leakage", "case_leakage", "pca_scaler_leakage", "outer_stop_contamination"} and row[key] is not False:
                reasons.append(f"FIT_{key.upper()}_FAIL")
    return not reasons, sorted(set(reasons))


def _topology_coverage_audit(record: Mapping[str, Any]) -> tuple[bool, list[str]]:
    coverage = record.get("topology_coverage", {})
    reasons = [f"MISSING_TOPOLOGY_COVERAGE:{topology}" for topology in TOPOLOGIES if coverage.get(topology) is not True]
    return not reasons, reasons


def _required_metric_audit(record: Mapping[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    for scope in ("global_geometry_metrics", "worst_fold_metrics", "worst_topology_metrics"):
        metrics = record.get(scope)
        if not isinstance(metrics, Mapping) or metrics.get("evaluation_level") != "geometry":
            reasons.append(f"MISSING_GEOMETRY_LEVEL_SCOPE:{scope}")
            continue
        for key in PROFILE_COMPONENTS + ("weighted_L1",):
            if key not in metrics or not _finite(metrics[key]):
                reasons.append(f"MISSING_NONFINITE_METRIC:{scope}:{key}")
    if "profile_pairwise_diversity_ratio" not in record or not _finite(record["profile_pairwise_diversity_ratio"]):
        reasons.append("MISSING_PROFILE_PAIRWISE_DIVERSITY_RATIO")
    for scope in ("topology_orientation_metrics", "topology_source_position_metrics"):
        value = record.get(scope)
        if value is not None and not isinstance(value, Mapping):
            reasons.append(f"INVALID_STRATUM_SCOPE:{scope}")
    return not reasons, reasons


def evaluate_candidate_eligibility(record: Mapping[str, Any]) -> dict[str, Any]:
    candidate_id = str(record.get("candidate_id", ""))
    if candidate_id not in CANDIDATES:
        raise PolicyError(f"unknown V3 candidate: {candidate_id}")
    reasons: list[str] = []
    fit_ok, fit_reasons = _fit_matrix_audit(record)
    reasons.extend(fit_reasons)
    topology_ok, topology_reasons = _topology_coverage_audit(record)
    reasons.extend(topology_reasons)
    metric_ok, metric_reasons = _required_metric_audit(record)
    reasons.extend(metric_reasons)
    for flag, label in (
        ("metric_contract_drift", "PROFILE_METRIC_CONTRACT_DRIFT"),
        ("architecture_definition_drift", "V3_ARCHITECTURE_DEFINITION_DRIFT"),
        ("sealed_test_violation", "SEALED_TEST_VIOLATION"),
        ("execution_artifact_ambiguous", "EXECUTION_ARTIFACT_AMBIGUOUS"),
    ):
        if record.get(flag) is True:
            reasons.append(label)
    collapse = collapse_audit(record.get("median_latent_variance_ratio"), record.get("collapsed_component_count"))
    if collapse["catastrophic_latent_collapse"]:
        reasons.append("CATASTROPHIC_LATENT_COLLAPSE")
    eligibility = not reasons
    return {
        "candidate_id": candidate_id,
        "eligible_for_promotion": eligibility,
        "status": "ELIGIBLE_FOR_PROMOTION" if eligibility else "INELIGIBLE_FOR_PROMOTION",
        "reasons": sorted(set(reasons)),
        "fit_matrix": {"expected": 15, "observed": len(record.get("fit_records", [])), "complete": fit_ok},
        "topology_coverage_complete": topology_ok,
        "required_metric_scopes_complete": metric_ok,
        "collapse": collapse,
        "case_level_metrics_are_diagnostic_only": True,
    }


def _selection_metric(record: Mapping[str, Any], scope: str) -> float:
    return profile_composite(record[scope])


def _warn_known_failure_strata(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for scope, scope_label in (("worst_fold_metrics", "fold"), ("worst_topology_metrics", "topology")):
        metrics = record.get(scope, {})
        if not isinstance(metrics, Mapping):
            continue
        js = float(metrics.get("JS", 0.0))
        weighted_l1 = float(metrics.get("weighted_L1", 0.0))
        if js > KNOWN_FAILURE_JS or weighted_l1 > KNOWN_FAILURE_WEIGHTED_L1:
            warnings.append({
                "warning": "KNOWN_FAILURE_LEVEL_STRATUM_WARNING",
                "scope": scope_label,
                "source_scope": scope,
                "JS": js,
                "weighted_L1": weighted_l1,
                "reference_JS": KNOWN_FAILURE_JS,
                "reference_weighted_L1": KNOWN_FAILURE_WEIGHTED_L1,
                "affects_eligibility": False,
            })
    return warnings


def _compare_candidates(left: Mapping[str, Any], right: Mapping[str, Any]) -> int:
    """Return -1 when left wins, +1 when right wins, 0 for machine tie."""
    ordered = (
        ("global", lambda r: _selection_metric(r, "global_geometry_metrics"), False),
        ("worst_topology", lambda r: _selection_metric(r, "worst_topology_metrics"), False),
        ("worst_fold", lambda r: _selection_metric(r, "worst_fold_metrics"), False),
        ("collapsed_component_count", lambda r: int(r["collapsed_component_count"]), False),
        ("median_latent_variance_ratio", lambda r: float(r["median_latent_variance_ratio"]), True),
        ("profile_pairwise_diversity_ratio", lambda r: float(r["profile_pairwise_diversity_ratio"]), True),
        ("architecture_complexity", lambda r: COMPLEXITY_RANK[str(r["candidate_id"])], False),
    )
    for _, getter, higher_is_better in ordered:
        a = float(getter(left))
        b = float(getter(right))
        if _machine_equal(a, b):
            continue
        if higher_is_better:
            return -1 if a > b else 1
        return -1 if a < b else 1
    return 0


def select_promoted_candidate(records: Sequence[Mapping[str, Any]], *, global_flags: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Apply the frozen hierarchy to outcome records supplied by a future OOF run."""
    global_flags = dict(global_flags or {})
    if len(records) != 3 or {str(record.get("candidate_id")) for record in records} != set(CANDIDATES):
        return {"selected_architecture": "NONE", "formal_result": "NO_V3_CANDIDATE_PROMOTABLE", "reason": "FORMAL_OOF_CANDIDATE_SET_INCOMPLETE"}
    if any(global_flags.get(flag) is True for flag in ("profile_metric_contract_drift", "architecture_definition_drift", "sealed_test_violation", "execution_artifact_ambiguous")):
        return {"selected_architecture": "NONE", "formal_result": "NO_V3_CANDIDATE_PROMOTABLE", "reason": "GLOBAL_NO_PROMOTION_HARD_GATE"}
    audits = [evaluate_candidate_eligibility(record) for record in records]
    eligible = [record for record, audit in zip(records, audits) if audit["eligible_for_promotion"]]
    warnings = [warning for record in records for warning in _warn_known_failure_strata(record)]
    if not eligible:
        return {
            "selected_architecture": "NONE",
            "formal_result": "NO_V3_CANDIDATE_PROMOTABLE",
            "reason": "ALL_CANDIDATES_INELIGIBLE_OR_CATASTROPHIC",
            "eligibility_audit": audits,
            "known_failure_level_stratum_warnings": warnings,
        }
    winner = eligible[0]
    tie_trace = []
    for challenger in eligible[1:]:
        comparison = _compare_candidates(winner, challenger)
        tie_trace.append({"incumbent": winner["candidate_id"], "challenger": challenger["candidate_id"], "comparison": comparison})
        if comparison > 0:
            winner = challenger
    return {
        "selected_architecture": winner["candidate_id"],
        "formal_result": "V3_CANDIDATE_PROMOTABLE",
        "eligibility_audit": audits,
        "known_failure_level_stratum_warnings": warnings,
        "selection": {
            "evaluation_level": "geometry",
            "primary_objective": "frozen_profile_only_four_component_geometry_level_composite",
            "global_geometry_profile_composite": _selection_metric(winner, "global_geometry_metrics"),
            "worst_topology_profile_composite": _selection_metric(winner, "worst_topology_metrics"),
            "worst_fold_profile_composite": _selection_metric(winner, "worst_fold_metrics"),
            "tie_break_trace": tie_trace,
            "case_level_metrics_override_geometry_level": False,
        },
        "final_training_authorization": "CHART_SEPARATE_AUTHORIZATION_REQUIRED",
    }


def sealed_test_assertion() -> dict[str, Any]:
    """Read only identity metadata; no V3-Test40 truth/label path is opened."""
    lock = read_json(TEST40_LOCK)
    overlap = read_json(TEST40_OVERLAP)
    passed = (
        lock.get("test_id") == "MDC_HF_SURROGATE_V3_TEST40_V1"
        and lock.get("labels_generated") is False
        and lock.get("labels_read") == 0
        and lock.get("solver_calls") == 0
        and overlap.get("formal_numerical_value_reads") == 0
        and overlap.get("status") == "PASS"
    )
    return {
        "status": "PASS" if passed else "HARD_GATE_V3_TEST40_SEALED_ASSERTION_INVALID",
        "metadata_files_read": [TEST40_LOCK.name, TEST40_OVERLAP.name],
        "labels_read": 0,
        "truth_reads": 0,
        "target_reads": 0,
        "formal_numerical_value_reads": 0,
        "selection_periods_sealed": ["OOF architecture selection", "hyperparameter selection", "final epoch determination", "seed selection", "checkpoint selection"],
        "opening_condition": "architecture frozen + final-development model frozen + checkpoint hashes frozen + separate Chart authorization",
        "path_scanning": False,
    }


def frozen_contract_audit() -> dict[str, Any]:
    training = read_json(TRAINING_CONTRACT)
    model = read_json(MODEL_CONTRACT)
    loss = read_json(LOSS_CONTRACT)
    ids = [entry.get("id") for entry in model.get("candidates", [])]
    weights = {"profile": float(loss["components"]["L_profile"]["weight"]), "JS": float(loss["components"]["L_JS"]["weight"]), "spectral_CDF": float(loss["components"]["L_spectral_CDF"]["weight"]), "angular_CDF": float(loss["components"]["L_angular_CDF"]["weight"])}
    return {
        "candidate_ids": ids,
        "candidate_definition_unchanged": ids == list(CANDIDATES) and model.get("candidate_count") == 3,
        "profile_only_loss_unchanged": weights == {key: float(value) for key, value in PROFILE_WEIGHTS.items()} and loss.get("power_loss") == "REMOVED" and loss.get("auxiliary_loss") == "REMOVED_FROM_SHARED_BACKBONE",
        "profile_weights": PROFILE_WEIGHTS,
        "weights_sum": sum(PROFILE_WEIGHTS.values()),
        "training_contract_sha256": file_sha(TRAINING_CONTRACT),
        "model_contract_sha256": file_sha(MODEL_CONTRACT),
        "loss_contract_sha256": file_sha(LOSS_CONTRACT),
        "final_epoch_policy": "NOT_FROZEN_IN_V3_PLAN_FREEZE; must be frozen before OOF starts; no outcome-dependent rule added",
        "training_authorized": training.get("training_authorized") is True,
        "status": "PASS" if ids == list(CANDIDATES) and math.isclose(sum(PROFILE_WEIGHTS.values()), 1.0, rel_tol=0.0, abs_tol=1e-12) else "HARD_GATE_FROZEN_CONTRACT_DRIFT",
    }


def known_failure_reference() -> dict[str, Any]:
    summary = read_json(FIXED_V2_FAILURE_SUMMARY)
    test40 = next((item for item in summary.get("metrics", []) if item.get("scope") == "TEST40"), None)
    if not test40:
        raise PolicyError("fixed-v2 known-failure TEST40 summary missing")
    if not (_machine_equal(float(test40["joint_JS"]), 0.229326594293918) and _machine_equal(float(test40["joint_weighted_L1"]), 1.1506046187633405)):
        raise PolicyError("fixed-v2 known-failure summary drift")
    return {
        "status": "PASS",
        "reference_type": "PRE_EXISTING_DEVELOPMENT_FAILURE_REFERENCE",
        "source_run": "20260809T_failure_mechanism_diagnostic_exact_latent_4169274",
        "source_file": str(FIXED_V2_FAILURE_SUMMARY),
        "source_sha256": file_sha(FIXED_V2_FAILURE_SUMMARY),
        "scope": "fixed-v2 Test40 failure diagnostic summary only; not V3 external baseline or acceptance threshold",
        "JS": KNOWN_FAILURE_JS,
        "weighted_L1": KNOWN_FAILURE_WEIGHTED_L1,
        "exact_observed_summary": {"JS": float(test40["joint_JS"]), "weighted_L1": float(test40["joint_weighted_L1"])},
        "warning_rule": "worst fold/topology JS or weighted-L1 above corresponding reference emits KNOWN_FAILURE_LEVEL_STRATUM_WARNING; warning alone does not reject",
    }


def policy_contract() -> dict[str, Any]:
    return {
        "contract_id": "MDC_HF_SURROGATE_V3_OOF_PROMOTION_POLICY_V1",
        "formal_status": STATUS,
        "outcome_blind": True,
        "evaluation_level": {"primary": "geometry", "case_level": "diagnostic_only", "case_level_can_override_geometry_selection": False},
        "catastrophic_collapse": {"per_component_variance_ratio_lt": COLLAPSE_COMPONENT_THRESHOLD, "candidate_median_variance_ratio_lt": COLLAPSE_COMPONENT_THRESHOLD, "collapsed_count_and_fraction_reported": True, "profile_diversity_threshold": "NOT_DEFINED; secondary diagnostic only"},
        "candidate_eligibility": {"expected_fits": 15, "fit_matrix": "5 folds x 3 seeds", "topologies": list(TOPOLOGIES), "required_no_leakage": ["fold", "case", "PCA/scaler", "outer-fold early-stopping"], "incomplete_or_invalid": "INELIGIBLE_FOR_PROMOTION"},
        "selection_hierarchy": ["lowest global geometry-level profile composite", "lower worst-topology profile composite", "lower worst-fold profile composite", "lower collapsed-component count", "higher median latent variance ratio", "higher profile pairwise-diversity ratio", "lower architecture complexity V3-A > V3-B > V3-C"],
        "primary_weights": PROFILE_WEIGHTS,
        "power_target_in_primary_score": False,
        "auxiliary_target_in_primary_score": False,
        "tie_rule": {"equality": "machine/numerical equality only", "absolute_tolerance": MACHINE_EQUALITY_TOL, "relative_tolerance": MACHINE_EQUALITY_TOL, "no_statistical_tolerance": True},
        "no_promotion_conditions": ["all candidates catastrophic", "formal OOF incomplete", "any leakage", "profile metric contract drift", "A/B/C definition drift", "sealed-test violation", "execution artifact ambiguity"],
        "final_training_interface": {"selected_architecture": ["V3-A", "V3-B", "V3-C", "NONE"], "full_development_training_requires": "selected != NONE and separate Chart authorization", "no_post_oof_architecture_search": True, "final_epoch_policy": "NOT_FROZEN_IN_V3_PLAN_FREEZE; remaining pre-OOF policy item"},
    }


def run_policy(output_dir: Path = POLICY_DIR) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    contract_audit = frozen_contract_audit()
    sealed = sealed_test_assertion()
    failure = known_failure_reference()
    outputs = {
        "promotion_policy.json": policy_contract(),
        "eligibility_contract.json": {"contract_id": "MDC_HF_SURROGATE_V3_OOF_CANDIDATE_ELIGIBILITY_V1", "policy": policy_contract()["candidate_eligibility"], "collapse_definition": policy_contract()["catastrophic_collapse"], "status": "PASS"},
        "deterministic_selection_contract.json": {"contract_id": "MDC_HF_SURROGATE_V3_DETERMINISTIC_SELECTION_V1", "hierarchy": policy_contract()["selection_hierarchy"], "primary_weights": PROFILE_WEIGHTS, "tie_rule": policy_contract()["tie_rule"], "geometry_level_primary": True, "case_level_override": False, "status": "PASS"},
        "known_failure_reference.json": failure,
        "sealed_test_assertion.json": sealed,
        "frozen_contract_audit.json": contract_audit,
        "policy_execution_audit.json": {"status": STATUS, "AL64_truth_reads": 0, "V3_Test40_truth_reads": 0, "solver_calls": 0, "neural_fits": 0, "backward_calls": 0, "optimizer_calls": 0, "PCA_fits": 0, "scaler_fits": 0, "training_dispatched": False, "outcome_threshold_adjustments": 0, "outcome_records_loaded": 0},
        "completion_manifest.json": {"status": STATUS, "contract_id": "MDC_HF_SURROGATE_V3_OOF_PROMOTION_POLICY_V1", "policy_artifacts": 8, "training_authorized": False, "AL64_pending": True, "V3_Test40_labels_read": 0, "HF15_R12_reads": 0},
    }
    for name, value in outputs.items():
        write_json(output_dir / name, value)
    report = "\n".join([
        "# V3 OOF promotion policy preregistration",
        "",
        f"- Formal status: `{STATUS}`",
        "- Evaluation primary: geometry-level aggregated profile; case-level is diagnostic only.",
        "- Catastrophic collapse: median latent variance ratio < 0.25; collapsed count/fraction also reported.",
        "- Eligibility: complete 15/15 fits, no leakage/NaN/missing, all Explicit/ZL1/ZL2 coverage, no catastrophic collapse.",
        "- Selection: frozen profile/JS/spectral-CDF/angular-CDF composite, then fixed tie-break hierarchy.",
        f"- Inherited fixed-v2 failure reference: JS={KNOWN_FAILURE_JS:.5f}, weighted-L1={KNOWN_FAILURE_WEIGHTED_L1:.5f}; warning only.",
        "- V3-Test40: metadata-only sealed assertion; no truth/label/target reads.",
        "- Final-development training: selected architecture plus separate Chart authorization; final epoch policy remains the only pre-OOF item not frozen in plan contract.",
        "- Solver, training, optimizer, backward, PCA/scaler and AL64/V3-Test40 truth reads: all zero.",
        "",
    ])
    (output_dir / "completion_report.md").write_text(report, encoding="utf-8")
    hashes = {path.name: {"sha256": file_sha(path), "size": path.stat().st_size} for path in sorted(output_dir.iterdir()) if path.is_file() and path.name != "artifact_sha256.json"}
    write_json(output_dir / "artifact_sha256.json", {"status": "PASS", "files": hashes})
    return {"status": STATUS, "sealed": sealed, "known_failure_reference": failure, "frozen_contract_audit": contract_audit}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(POLICY_DIR))
    args = parser.parse_args()
    print(json.dumps(run_policy(Path(args.output_dir)), ensure_ascii=False, sort_keys=True))
