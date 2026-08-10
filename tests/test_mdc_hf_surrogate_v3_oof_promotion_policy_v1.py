from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import mdc_hf_surrogate_v3_oof_promotion_policy_v1 as policy


def _metrics(score: float, *, js: float | None = None, weighted_l1: float | None = None) -> dict[str, float | str]:
    return {
        "evaluation_level": "geometry",
        "profile": score,
        "JS": score,
        "spectral_CDF": score,
        "angular_CDF": score,
        "weighted_L1": score if weighted_l1 is None else weighted_l1,
    }


def good_record(candidate_id: str, *, score: float = 0.2, median: float = 0.8, collapsed: int = 0, diversity: float = 1.0, case_score: float = 0.2, worst_js: float | None = None, worst_l1: float | None = None) -> dict:
    fits = [
        {"outer_fold": fold, "seed": seed, "finite": True, "prediction_complete": True, "fold_leakage": False, "case_leakage": False, "pca_scaler_leakage": False, "outer_stop_contamination": False}
        for fold in policy.OUTER_FOLDS
        for seed in policy.SEEDS
    ]
    worst_js = score if worst_js is None else worst_js
    worst_l1 = score if worst_l1 is None else worst_l1
    return {
        "candidate_id": candidate_id,
        "fit_records": fits,
        "topology_coverage": {topology: True for topology in policy.TOPOLOGIES},
        "median_latent_variance_ratio": median,
        "collapsed_component_count": collapsed,
        "profile_pairwise_diversity_ratio": diversity,
        "global_geometry_metrics": _metrics(score),
        "worst_fold_metrics": _metrics(score, js=worst_js, weighted_l1=worst_l1),
        "worst_topology_metrics": _metrics(score, js=worst_js, weighted_l1=worst_l1),
        "topology_orientation_metrics": {topology: {} for topology in policy.TOPOLOGIES},
        "topology_source_position_metrics": {topology: {} for topology in policy.TOPOLOGIES},
        "case_level_metrics": {"mean_profile_composite": case_score},
    }


def test_policy_contract_is_frozen_and_profile_only():
    contract = policy.policy_contract()
    assert contract["evaluation_level"]["primary"] == "geometry"
    assert contract["evaluation_level"]["case_level_can_override_geometry_selection"] is False
    assert abs(sum(policy.PROFILE_WEIGHTS.values()) - 1.0) < 1e-12
    assert contract["power_target_in_primary_score"] is False
    assert contract["auxiliary_target_in_primary_score"] is False
    assert contract["tie_rule"]["no_statistical_tolerance"] is True


def test_collapse_threshold_is_inherited_and_reported():
    audit = policy.collapse_audit(0.249999, 29)
    assert audit["catastrophic_latent_collapse"] is True
    assert audit["per_component_threshold"] == 0.25
    assert audit["collapsed_component_fraction"] == 29 / 32


def test_power_and_auxiliary_fields_cannot_change_primary_score():
    metrics = _metrics(0.3)
    metrics["power_loss"] = 9999.0
    metrics["auxiliary_loss"] = 9999.0
    assert policy.profile_composite(metrics) == pytest.approx(0.3)


def test_geometry_level_selection_ignores_case_level_mean():
    records = [
        good_record("V3-A", score=0.10, case_score=99.0),
        good_record("V3-B", score=0.20, case_score=0.0),
        good_record("V3-C", score=0.30, case_score=0.0),
    ]
    result = policy.select_promoted_candidate(records)
    assert result["selected_architecture"] == "V3-A"
    assert result["selection"]["case_level_metrics_override_geometry_level"] is False


def test_tie_break_order_is_deterministic_worst_topology_before_other_fields():
    records = [
        good_record("V3-A", score=0.2, collapsed=0, median=0.9, diversity=2.0),
        good_record("V3-B", score=0.2, collapsed=0, median=0.9, diversity=2.0),
        good_record("V3-C", score=0.2, collapsed=0, median=0.9, diversity=2.0),
    ]
    records[0]["worst_topology_metrics"] = _metrics(0.30)
    records[1]["worst_topology_metrics"] = _metrics(0.20)
    records[2]["worst_topology_metrics"] = _metrics(0.10)
    result = policy.select_promoted_candidate(records)
    assert result["selected_architecture"] == "V3-C"


def test_catastrophic_candidate_cannot_be_promoted_over_eligible_candidate():
    records = [
        good_record("V3-A", score=0.01, median=0.1, collapsed=29),
        good_record("V3-B", score=0.2),
        good_record("V3-C", score=0.3),
    ]
    result = policy.select_promoted_candidate(records)
    assert result["selected_architecture"] == "V3-B"
    assert any(a["status"] == "INELIGIBLE_FOR_PROMOTION" for a in result["eligibility_audit"])


def test_all_catastrophic_candidates_return_none():
    records = [good_record(candidate, score=0.01, median=0.1, collapsed=32) for candidate in policy.CANDIDATES]
    result = policy.select_promoted_candidate(records)
    assert result["selected_architecture"] == "NONE"
    assert result["formal_result"] == "NO_V3_CANDIDATE_PROMOTABLE"


def test_incomplete_fit_matrix_cannot_be_selected():
    records = [good_record(candidate) for candidate in policy.CANDIDATES]
    for record in records:
        record["fit_records"] = record["fit_records"][:-1]
    result = policy.select_promoted_candidate(records)
    assert result["selected_architecture"] == "NONE"
    assert result["reason"] == "ALL_CANDIDATES_INELIGIBLE_OR_CATASTROPHIC"


def test_worst_strata_reference_emits_warning_without_automatic_rejection():
    records = [good_record("V3-A", score=0.2, worst_js=0.30, worst_l1=1.20), good_record("V3-B", score=0.3), good_record("V3-C", score=0.4)]
    result = policy.select_promoted_candidate(records)
    assert result["selected_architecture"] == "V3-A"
    assert result["known_failure_level_stratum_warnings"][0]["warning"] == "KNOWN_FAILURE_LEVEL_STRATUM_WARNING"
    assert result["known_failure_level_stratum_warnings"][0]["affects_eligibility"] is False


def test_global_contract_or_sealed_gate_returns_none():
    records = [good_record(candidate) for candidate in policy.CANDIDATES]
    result = policy.select_promoted_candidate(records, global_flags={"sealed_test_violation": True})
    assert result["selected_architecture"] == "NONE"
    assert result["formal_result"] == "NO_V3_CANDIDATE_PROMOTABLE"


def test_v3_test40_assertion_is_metadata_only_and_labels_zero():
    assertion = policy.sealed_test_assertion()
    assert assertion["status"] == "PASS"
    assert assertion["labels_read"] == 0
    assert assertion["truth_reads"] == 0
    assert assertion["target_reads"] == 0
    assert assertion["path_scanning"] is False


def test_known_failure_reference_is_fixed_v2_development_only():
    reference = policy.known_failure_reference()
    assert reference["JS"] == 0.22933
    assert reference["weighted_L1"] == 1.15060
    assert "not V3 external baseline" in reference["scope"]


def test_final_epoch_remains_explicitly_unfrozen_and_training_not_authorized():
    audit = policy.frozen_contract_audit()
    assert audit["status"] == "PASS"
    assert audit["training_authorized"] is False
    assert "NOT_FROZEN" in audit["final_epoch_policy"]
