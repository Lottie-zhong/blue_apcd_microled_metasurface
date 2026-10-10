import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "closure_classifier",
    Path(__file__).parents[1] / "tools/process_ownership_evidence.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
classify = module.classify_identity
original = {"pid": 10, "creation_time": 100.0}
current = {"pid": 10, "creation_time": 100.0, "cim_creation_time": 100.0}


def test_reused_pid_never_clears_replacement():
    result = classify(
        original, {**current, "creation_time": 200.0, "cim_creation_time": 200.0}
    )
    assert result == (
        "STALE_INACTIVE",
        "ORIGINAL_PID_REUSED_REPLACEMENT_REMAINS_UNCLEARED",
    )


def test_absent_identity_is_stale_only_with_complete_observation():
    assert classify(original, None)[0] == "STALE_INACTIVE"
    assert classify(original, None, observation_error="AccessDenied")[0] == "UNRESOLVED"


def test_parent_absence_and_foreign_name_are_insufficient():
    assert (
        classify(original, current, source_kind="OTHER_READONLY", bound_source=True)[0]
        == "UNRESOLVED"
    )


def test_cwd_or_no_v1_match_alone_never_proves_other():
    assert classify(original, current, lineage_verified=True)[0] == "UNRESOLVED"


def test_verified_readonly_other_scope():
    assert (
        classify(
            original,
            current,
            source_kind="OTHER_READONLY",
            bound_source=True,
            lineage_verified=True,
        )[0]
        == "CONFIRMED_OTHER_ACTIVITY"
    )


def test_verified_v1_science_source():
    assert (
        classify(
            original,
            current,
            source_kind="V1_SCIENCE",
            bound_source=True,
            lineage_verified=True,
        )[0]
        == "CONFIRMED_V1_ACTIVE"
    )


@pytest.mark.parametrize("value", [None, float("nan"), "100"])
def test_invalid_creation_is_not_a_clearance(value):
    assert classify(original, {**current, "creation_time": value})[0] == "UNRESOLVED"


def test_two_identity_providers_disagree():
    assert (
        classify(original, {**current, "cim_creation_time": 105.0})[0] == "UNRESOLVED"
    )


def test_self_match_not_used_for_ownership():
    assert classify(original, current, audit_identity=original)[0] == "UNRESOLVED"
