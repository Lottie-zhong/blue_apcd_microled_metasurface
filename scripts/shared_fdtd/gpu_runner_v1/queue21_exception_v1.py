"""Narrow validator for the unrecoverable queue21 lineage disposition draft."""

SCHEMA = "APCD_GPU_RUNNER_QUEUE21_UNRECOVERABLE_EXCEPTION_DISPOSITION_V1"
CASE_ID = "K6_5X3_SP237_X_CENTER_ORIGIN_PLUS1"
ATTEMPT_ID = "attempt_001"
HOLD_ID = "hold-4a6eab94af3b4a6d8510ba2fe32a5b66"
HOLD_GENERATION = 26
ENTRY_EVENT_IDS = [1499, 1506]


class DispositionError(ValueError):
    pass


def validate_disposition(record):
    """Accept only a pending owner-review record; no generic hold-waiver path exists."""
    if not isinstance(record, dict) or record.get("schema") != SCHEMA:
        raise DispositionError("SCHEMA_INVALID")
    if record.get("case_id") != CASE_ID or record.get("attempt_id") != ATTEMPT_ID:
        raise DispositionError("CASE_IDENTITY_INVALID")
    if record.get("physical_solver_entry_count") != "UNKNOWN":
        raise DispositionError("PHYSICAL_ENTRY_COUNT_MUST_REMAIN_UNKNOWN")
    if record.get("classification") != "C_EVIDENCE_INSUFFICIENT_LINEAGE_NOT_RECOVERABLE":
        raise DispositionError("CLASSIFICATION_INVALID")
    if record.get("entry_event_ids") != ENTRY_EVENT_IDS:
        raise DispositionError("ENTRY_EVENT_SET_INVALID")
    hold = record.get("applicable_hold")
    if not isinstance(hold, dict) or hold.get("hold_id") != HOLD_ID or hold.get("generation") != HOLD_GENERATION:
        raise DispositionError("HOLD_BINDING_INVALID")
    if hold.get("status") != "ACTIVE":
        raise DispositionError("HOLD_STATUS_INVALID")
    quarantine = record.get("quarantine")
    required_quarantine = {
        "status": "QUARANTINED",
        "exclude_from_training": True,
        "exclude_from_ranking": True,
        "exclude_from_scientific_conclusions": True,
        "exclude_from_formal_truth_handoff": True,
        "historical_attempt_restart_allowed": False,
        "replacement_attempt_allowed": False,
        "raw_events_and_truth_preserved": True,
    }
    if quarantine != required_quarantine:
        raise DispositionError("QUARANTINE_POLICY_INVALID")
    owner = record.get("owner_decision")
    if not isinstance(owner, dict) or owner.get("status") != "OWNER_DECISION_REQUIRED":
        raise DispositionError("OWNER_DECISION_STATE_INVALID")
    if owner.get("owner_identity") is not None or owner.get("authority_source") is not None:
        raise DispositionError("UNVERIFIED_OWNER_MUST_NOT_BE_SELF_ASSIGNED")
    if owner.get("release_authority") is not None or owner.get("signature_sha256") is not None:
        raise DispositionError("DRAFT_CANNOT_CARRY_RELEASE_AUTHORITY")
    recovery = record.get("recovery")
    if not isinstance(recovery, dict) or recovery.get("state") != "BLOCKED_PENDING_OWNER_DECISION":
        raise DispositionError("RECOVERY_STATE_INVALID")
    if recovery.get("new_entry_authorized") is not False:
        raise DispositionError("NEW_ENTRY_MUST_REMAIN_BLOCKED")
    diagnostic = record.get("diagnostic")
    if not isinstance(diagnostic, dict):
        raise DispositionError("DIAGNOSTIC_POLICY_MISSING")
    if (diagnostic.get("case_id") != "K6V1_EXT02_TWO_AIR_PLANES_DIAG"
            or diagnostic.get("attempt_id") != "attempt_001"
            or diagnostic.get("solver_entry_authorized") is not False
            or diagnostic.get("max_solver_entries") != 0
            or diagnostic.get("automatic_replay_allowed") is not False
            or diagnostic.get("training_dataset_eligible") is not False):
        raise DispositionError("DIAGNOSTIC_AUTHORIZATION_INVALID")
    return {"valid": True, "release_authorized": False, "new_entry_authorized": False}
