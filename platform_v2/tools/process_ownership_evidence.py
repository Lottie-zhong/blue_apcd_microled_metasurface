"""Offline evidence classification only. No process control or production state writes."""

from math import isfinite


def classify_identity(
    original,
    current,
    *,
    source_kind="UNVERIFIED",
    bound_source=False,
    lineage_verified=False,
    observation_error=None,
    audit_identity=None,
):
    if observation_error:
        return "UNRESOLVED", "OBSERVATION_ERROR"
    if current is None:
        return "STALE_INACTIVE", "IDENTITY_ABSENT_IN_CIM_AND_PSUTIL"
    required = (
        original.get("creation_time"),
        current.get("creation_time"),
        current.get("cim_creation_time"),
    )
    if any(not isinstance(x, (int, float)) or not isfinite(x) for x in required):
        return "UNRESOLVED", "MISSING_OR_INVALID_CREATION_TIME"
    if original.get("pid") != current.get("pid"):
        return "UNRESOLVED", "PID_MISMATCH"
    if abs(current["creation_time"] - current["cim_creation_time"]) >= 0.002:
        return "UNRESOLVED", "CIM_PSUTIL_IDENTITY_DISAGREEMENT"
    if abs(original["creation_time"] - current["creation_time"]) >= 0.002:
        return "STALE_INACTIVE", "ORIGINAL_PID_REUSED_REPLACEMENT_REMAINS_UNCLEARED"
    if audit_identity and original == audit_identity:
        return "UNRESOLVED", "SELF_MATCH_IS_NOT_OWNER_EVIDENCE"
    if not (bound_source and lineage_verified):
        return "UNRESOLVED", "LIVE_IDENTITY_WITHOUT_BOUND_SOURCE_AND_LINEAGE"
    if source_kind == "V1_SCIENCE":
        return "CONFIRMED_V1_ACTIVE", "BOUND_V1_SCIENCE_PROVENANCE"
    if source_kind == "OTHER_READONLY":
        return (
            "CONFIRMED_OTHER_ACTIVITY",
            "BOUND_READONLY_SOURCE_AND_OTHER_CASE_LINEAGE",
        )
    return "UNRESOLVED", "SOURCE_SCOPE_UNVERIFIED"
