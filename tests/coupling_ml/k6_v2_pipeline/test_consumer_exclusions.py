from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from scripts.coupling_ml.k6_v2_pipeline import contracts as C
from scripts.coupling_ml.k6_v2_pipeline.consumer_exclusions import (
    ConsumerExclusionError,
    assert_no_quarantine_linkage,
    load_consumer_exclusion_registry,
    validate_independent_truth_provenance,
)
from scripts.coupling_ml.k6_v2_pipeline.ingest import (
    load_confirmation_case,
    load_development_collection,
    load_old32_engineering_diagnostic,
    load_verified_runner_case,
)
from scripts.coupling_ml.k6_v2_pipeline.training import _validate_development_case_map

ROOT = Path(__file__).resolve().parents[3]
TARGET = "K6_5X3_SP237_X_CENTER_ORIGIN_PLUS1"


def _valid_unrelated_old32_case():
    collection = load_old32_engineering_diagnostic(root=ROOT)
    case = collection.cases[0]
    assert case.case_id != TARGET
    return case


def test_registry_pins_unknown_entry_count_and_active_hold():
    doc = load_consumer_exclusion_registry(ROOT)
    assert doc["case_identity"]["case_id"] == TARGET
    assert doc["case_identity"]["attempt_id"] == "attempt_001"
    assert doc["case_identity"]["physical_solver_entry_count"] == "UNKNOWN"
    assert doc["source_authorities"]["hold"]["status"] == "ACTIVE"
    assert doc["source_authorities"]["hold"]["released"] is False
    assert doc["source_authorities"]["gpu_runner_worktree_head"] == "88c8ba7afe99ab8e58a4f41f0698b56f65bc0b35"
    assert doc["decision"]["owner_v2_quarantine_status"] == "QUARANTINED_PENDING_COUPLING_CONSUMER_ENFORCEMENT"
    assert doc["decision"]["conditional_hold_release_performed"] is False
    assert set(doc["decision"]["exclude_from"]) == {
        "training", "candidate_ranking", "candidate_evaluation",
        "scientific_conclusions", "formal_truth_handoff",
    }


@pytest.mark.parametrize("attempt", ["attempt_001", "attempt_002"])
def test_exact_queue21_case_is_rejected_before_truth_artifact_access(attempt):
    record = {
        "case_id": TARGET,
        "attempt_id": attempt,
        "branch_id": "traditional",
        "role": C.ROLE_GLOBAL_DEV,
        "state_npz": {"path": "not-opened.npz", "sha256": "0" * 64},
    }
    with pytest.raises(ConsumerExclusionError, match="queue21_linked_artifact_excluded"):
        load_verified_runner_case(record, expected_role=C.ROLE_GLOBAL_DEV, root=ROOT)
    with pytest.raises(ConsumerExclusionError, match="queue21_linked_artifact_excluded"):
        load_development_collection(new_case_records=[record], root=ROOT)


def test_unregistered_linked_artifact_and_missing_provenance_fail_closed():
    linked_record = {
        "case_id": "UNREGISTERED_CASE",
        "attempt_id": "attempt_001",
        "source_manifest": {
            "path": "unresolved/manifest.json",
            "provenance": {"source_case_id": TARGET, "source_disposition_sha256":
                           "5e2ba9d6de8c94e2f4fe0af89ba9fc7b5a523763d35b863e083888f3f06c5065"},
        },
    }
    with pytest.raises(ConsumerExclusionError, match="queue21_linked_artifact_excluded"):
        assert_no_quarantine_linkage(linked_record, consumer="truth_import", root=ROOT)

    trusted = _valid_unrelated_old32_case()
    weak = replace(trusted, provenance={})
    with pytest.raises(ConsumerExclusionError, match="independent_truth_provenance_missing_or_invalid"):
        validate_independent_truth_provenance([weak], consumer="training", root=ROOT)


def test_training_and_candidate_evaluation_reject_linked_collection():
    trusted = _valid_unrelated_old32_case()
    linked = replace(trusted, provenance={**trusted.provenance, "source_case_id": TARGET})
    collection = C.CaseCollection("development", (linked,), "fixture", {})
    with pytest.raises(ConsumerExclusionError, match="queue21_linked_artifact_excluded"):
        collection.training_cases()

    from scripts.coupling_ml.k6_v2_pipeline.validation import evaluate_learning_curve_oof
    with pytest.raises(ConsumerExclusionError, match="queue21_linked_artifact_excluded"):
        evaluate_learning_curve_oof(collection, None, ())


def test_event_only_linkage_and_diagnostic_import_are_blocked():
    with pytest.raises(ConsumerExclusionError, match="queue21_linked_artifact_excluded"):
        assert_no_quarantine_linkage(
            {"case_id": "OTHER_CASE", "provenance": {"entry_event_ids": [1499, 1506]}},
            consumer="truth_import", root=ROOT,
        )
    from scripts.coupling_ml.k6_v2_pipeline.ingest import load_diagnostic_case
    with pytest.raises(ConsumerExclusionError, match="queue21_linked_artifact_excluded"):
        load_diagnostic_case({
            "case_id": TARGET, "attempt_id": "attempt_001",
            "role": C.ROLE_DIAGNOSTIC, "protocol_sha256": C.TWO_PLANE_PROTOCOL_SHA256,
        })


def test_truth_handoff_rejects_queue21_before_reveal_consumption():
    record = {
        "case_id": TARGET,
        "attempt_id": "attempt_001",
        "branch_id": "traditional",
        "role": C.ROLE_GLOBAL_CORE_CONFIRM,
        "state_npz": {"path": "must-not-open.npz", "sha256": "0" * 64},
    }
    with pytest.raises(ConsumerExclusionError, match="queue21_linked_artifact_excluded"):
        load_confirmation_case(record, reveal_authorization=None, root=ROOT)


def test_valid_independent_old32_provenance_is_not_overblocked():
    trusted = _valid_unrelated_old32_case()
    validate_independent_truth_provenance([trusted], consumer="training", root=ROOT)
    collection = C.CaseCollection("development", (trusted,), "old32-fixture", {})
    assert collection.training_cases() == (trusted,)

    plan = SimpleNamespace(
        development_case_ids=(trusted.case_id,),
        development_role_by_id={trusted.case_id: trusted.role},
        geometry_by_id={trusted.case_id: trusted.ordered_D_nm},
    )
    assert _validate_development_case_map({trusted.case_id: trusted}, plan)[trusted.case_id] is trusted


def test_unrelated_valid_import_identity_is_not_queue21():
    doc = load_consumer_exclusion_registry(ROOT)
    trusted = _valid_unrelated_old32_case()
    assert trusted.case_id != doc["case_identity"]["case_id"]
    assert_no_quarantine_linkage(trusted, consumer="candidate_evaluation", root=ROOT)
    assert trusted.provenance["dataset_npz_sha256"] == "fefc09bbd06d0da06664105540c4f5e0659a51b68b06a07df8c44ed413891d28"

def test_direct_local_affine_fit_rejects_quarantine_and_unprovenanced_truth():
    from scripts.coupling_ml.k6_v2_pipeline.local_affine import (
        _fit_train_cases, fit_local_affine,
    )

    trusted = _valid_unrelated_old32_case()
    queued = replace(trusted, case_id=TARGET)
    with pytest.raises(ConsumerExclusionError, match="queue21_linked_artifact_excluded"):
        fit_local_affine(queued, ())

    weak = replace(trusted, provenance={})
    with pytest.raises(ConsumerExclusionError, match="independent_truth_provenance_missing_or_invalid"):
        _fit_train_cases((weak,))
