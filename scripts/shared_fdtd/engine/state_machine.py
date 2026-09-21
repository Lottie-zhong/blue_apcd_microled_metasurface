STATES = (
    "QUEUED", "ATTEMPT_CREATED", "SETUP_READY", "WAITING_FOR_SLOT",
    "SLOT_ACQUIRED", "HOST_START_INTENT", "HOST_STARTED",
    "SOLVER_ENTRY_INTENT", "SCIENTIFIC_SOLVER_ENTERED",
    "SCIENTIFIC_SOLVER_RUNNING", "STALE_CONTROL_PLANE_STATE",
    "SOLVER_RETURNED", "NATIVE_TRUTH_PERSISTING", "NATIVE_TRUTH_DURABLE",
    "POSTPROCESSING", "POST_FSP_VALID", "RAW_VALID", "SCIENTIFIC_VALID",
    "HF_ARCHIVED", "RELEASE_PENDING", "RELEASED", "FAILED_PREENTRY",
    "FAILED_AFTER_ENTRY", "POSTENTRY_NO_TRUTH", "AMBIGUOUS_QUARANTINED",
    "TERMINAL_QUARANTINED", "CONTROL_PLANE_DEGRADED", "PENDING_RECONCILE",
)
TERMINAL = {
    "RELEASED", "FAILED_PREENTRY", "FAILED_AFTER_ENTRY",
    "POSTENTRY_NO_TRUTH", "TERMINAL_QUARANTINED", "AMBIGUOUS_QUARANTINED",
}

def replay_allowed(events):
    kinds = {e.get("event_type") for e in events}
    return "SCIENTIFIC_SOLVER_ENTERED" not in kinds and "SCIENTIFIC_VALID" not in kinds

def release_allowed(events):
    kinds = {e.get("event_type") for e in events}
    return "HF_ARCHIVED" in kinds and "SCIENTIFIC_VALID" in kinds

def truth_durable(events):
    kinds = {e.get("event_type") for e in events}
    return "NATIVE_TRUTH_DURABLE" in kinds or "SCIENTIFIC_VALID" in kinds

def scientific_entry_count(events):
    return sum(e.get("event_type") == "SCIENTIFIC_SOLVER_ENTERED" for e in events)

def release_count(events):
    return sum(e.get("event_type") == "LEASE_RELEASED" for e in events)

def postentry_no_truth_allowed(events):
    kinds = {e.get("event_type") for e in events}
    return (
        scientific_entry_count(events) == 1
        and "SCIENTIFIC_VALID" not in kinds
        and "NATIVE_TRUTH_DURABLE" not in kinds
        and "HF_ARCHIVED" not in kinds
        and "LEASE_RELEASED" not in kinds
        and not replay_allowed(events)
    )
