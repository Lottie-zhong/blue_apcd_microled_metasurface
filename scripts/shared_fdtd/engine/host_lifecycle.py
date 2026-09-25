from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Any

from shared_fdtd.control_v3.db import utc_now
from shared_fdtd.engine.event_log import append_event, read_events
from shared_fdtd.engine.attempt_state import write_durable_attempt_state


@dataclass
class ScientificHostLifecycle:
    """Owns scientific cleanup; control-plane failures are local deferred events."""

    events: Path
    identity: dict[str, Any]
    entered: bool = False
    scientific_terminal: bool = False
    truth_durable: bool = False
    phase: str = "PREENTRY"
    _deferred: set[str] = field(default_factory=set, init=False)

    def __post_init__(self) -> None:
        try:
            self._deferred = {
                row.get("failed_control_plane_operation")
                for row in read_events(self.events)
                if row.get("event_type") == "CONTROL_PLANE_UPDATE_DEFERRED"
            }
            self._deferred.discard(None)
        except Exception:
            self._deferred = set()

    def persist_durable_state(self, path: str | Path, *, cfg: dict[str, Any], lease: Any, **paths: Any) -> dict[str, Any]:
        return write_durable_attempt_state(path, cfg=cfg, lease=lease, **paths)

    def mark_entered(self, **metadata: Any) -> None:
        self.entered = True
        self.phase = "SCIENTIFIC_EXECUTION"
        append_event(self.events, "SCIENTIFIC_SOLVER_ENTERED", process_identity=self.identity, **metadata)

    def control_plane(self, operation: str, callback: Callable[[], Any], *, state: str | None = None) -> bool:
        try:
            callback()
        except BaseException as exc:
            self.defer(operation, exc, state=state)
            self.phase = "CONTROL_PLANE_DEGRADED"
            return False
        if operation in self._deferred:
            self._deferred.remove(operation)
            append_event(self.events, "CONTROL_PLANE_UPDATE_RECONCILED", operation=operation)
        return True

    def defer(self, operation: str, exc: BaseException, *, state: str | None = None) -> None:
        if operation in self._deferred:
            return
        self._deferred.add(operation)
        append_event(
            self.events,
            "CONTROL_PLANE_UPDATE_DEFERRED",
            owner_branch=self.identity.get("owner_branch"),
            logical_case_id=self.identity.get("logical_case_id"),
            attempt_id=self.identity.get("attempt_id"),
            slot_id=self.identity.get("slot_id"),
            lease_token_hash=self.identity.get("lease_token_hash"),
            fencing_generation=self.identity.get("fencing_generation"),
            scientific_state=state or ("SCIENTIFIC_SOLVER_ENTERED" if self.entered else "PREENTRY"),
            failed_control_plane_operation=operation,
            exception_type=type(exc).__name__,
            retry_state="DEFERRED",
            process_identity={"pid": os.getpid(), **self.identity},
        )

    def mark_scientific_terminal(self) -> None:
        self.scientific_terminal = True
        self.phase = "SCIENTIFIC_TERMINAL"

    def mark_truth_durable(self) -> None:
        self.truth_durable = True
        self.phase = "TRUTH_DURABLE"

    def can_close(self) -> bool:
        return not self.entered or self.scientific_terminal or self.truth_durable

    def close(self, fd: Any, reason: str) -> None:
        if fd is None:
            return
        if not self.can_close():
            raise RuntimeError(f"scientific fd.close forbidden before terminal truth: {reason}")
        append_event(self.events, "SCIENTIFIC_OWNER_CLOSE", reason=reason, phase=self.phase)
        fd.close()


def lifecycle_identity(cfg: dict[str, Any], lease: Any) -> dict[str, Any]:
    return {
        "owner_branch": cfg["branch"],
        "logical_case_id": cfg["case"],
        "attempt_id": cfg["attempt"],
        "slot_id": lease.slot_id,
        "lease_token_hash": lease.token_hash,
        "fencing_generation": lease.fencing_generation,
    }

