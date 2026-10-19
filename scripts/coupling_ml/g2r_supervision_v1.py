"""Branch-local, zero-solver supervision guards for G2R.

This module only records durable state and classifies evidence. It never
releases a lease and never relaunches a solver.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fsync_replace(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def durable_json(path: Path, payload: dict) -> None:
    _fsync_replace(path, json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def durable_event(path: Path, event: str, **payload) -> dict:
    record = {"timestamp_utc": utc_now(), "event": event, **payload}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return record


def heartbeat(path: Path, *, controller_pid: int, worker_pid: int, state: str,
              solver_pids: list[int] | None = None) -> dict:
    payload = {"timestamp_utc": utc_now(), "controller_pid": controller_pid,
               "worker_pid": worker_pid, "state": state,
               "solver_pids": list(solver_pids or [])}
    durable_json(path, payload)
    return payload


def classify_after_exit(*, ledger: dict, process_alive: bool, post_exists: bool,
                        raw_exists: bool, load_only_status: str,
                        scientific_status: str) -> dict:
    entered = bool(ledger.get("solver_entered"))
    returned = bool(ledger.get("solver_returned"))
    persisted = post_exists and load_only_status == "PASS"
    scientific = scientific_status == "PASS"
    if not entered:
        return {"class": "FAILED_PRE_ENTRY", "stage": "CONTROLLER_OR_ADMISSION",
                "rerun_allowed_by_evidence": True, "reason": "solver_not_entered"}
    if returned and persisted and scientific:
        return {"class": "ZERO_SOLVER_RECOVERY_ALLOWED", "stage": "POST_RETURN_FINALIZATION",
                "rerun_allowed_by_evidence": False, "reason": "persisted_truth_exists"}
    if not process_alive and not returned and not post_exists and not raw_exists:
        return {"class": "FAILED_AFTER_ENTRY_NO_RECOVERABLE_TRUTH",
                "stage": "SOLVER_PROGRESS_ONLY", "rerun_allowed_by_evidence": True,
                "reason": "lineage_gone_before_return_and_no_payload"}
    return {"class": "FAILED_AFTER_ENTRY_AMBIGUOUS", "stage": "POSTSOLVER_UNRESOLVED",
            "rerun_allowed_by_evidence": False, "reason": "evidence_incomplete"}


def completion_gate(*, solver_entered: bool, solver_returned: bool,
                    post_exists: bool, load_only_status: str,
                    scientific_status: str) -> tuple[bool, str]:
    if solver_entered and not solver_returned:
        return False, "SOLVER_RETURN_REQUIRED"
    if not post_exists or load_only_status != "PASS":
        return False, "POST_FSP_LOAD_ONLY_REQUIRED"
    if scientific_status != "PASS":
        return False, "SCIENTIFIC_VALIDATION_REQUIRED"
    return True, "COMPLETION_ALLOWED"


def release_gate(*, terminal_state: str, ownership: str) -> tuple[bool, str]:
    if terminal_state != "SCIENTIFIC_VALID":
        return False, "SCIENCE_NOT_VALID"
    if ownership != "OWNER":
        return False, "OWNERSHIP_NOT_PROVEN"
    return True, "RELEASE_ALLOWED"


def resume_classification(events: list[dict]) -> str:
    if not events:
        return "NO_DURABLE_STATE"
    last = events[-1].get("event", "")
    if last == "SCIENTIFIC_SOLVER_ENTERED":
        return "FAILED_AFTER_ENTRY_REQUIRES_FORENSIC_RECOVERY"
    if last == "POST_FSP_LOAD_ONLY_VALIDATED":
        return "ZERO_SOLVER_RECOVERY_ALLOWED"
    return "RESUME_FROM_LAST_DURABLE_EVENT"


def replay_delta(ledger: dict) -> int:
    return max(0, int(ledger.get("run_invocation_count", 0)) - 1) if ledger.get("solver_entered") else 0
