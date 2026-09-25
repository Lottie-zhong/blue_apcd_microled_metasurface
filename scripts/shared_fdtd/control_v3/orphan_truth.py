from __future__ import annotations

import hashlib
import json
import re
import secrets
from collections.abc import Mapping
from typing import Any

from .db import ControlDB, utc_now


RECOVERY_TERMINAL_STATE = "RECOVERED_ADOPTED"
_IDENTITY = ("coupling_ml", "K6V1_S14", "attempt_004")
_ACTIVE_RESOURCE_STATES = ("RESERVED", "LIVE", "RELEASE_PENDING", "OWNER_QUARANTINED")
_REQUIRED_EVIDENCE = (
    "scientific_entry_count", "solver_invocation_count", "replay_count",
    "duplicate_scientific_entry_count", "newer_attempt_exists", "live_process",
    "persistence_active", "truth_valid", "conflicting_truth", "autofill_enabled",
    "s15_s16_non_entered", "foreign_mutation_count", "runtime_owner_created",
    "evidence_manifest_sha256", "artifact_identity_sha256", "artifact_hashes",
)


class RecoveryBlocked(RuntimeError):
    def __init__(self, reason: str, details: Mapping[str, Any] | None = None):
        self.reason = reason
        self.details = dict(details or {})
        super().__init__(reason)


def artifact_identity_sha256(artifact_hashes: Mapping[str, str]) -> str:
    canonical = {str(k): str(v).lower() for k, v in sorted(artifact_hashes.items())}
    return hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _hex64(value: Any) -> bool:
    text = str(value or "").lower()
    return len(text) == 64 and all(char in "0123456789abcdef" for char in text)


def _attempt_number(attempt_id: str) -> int | None:
    match = re.fullmatch(r"attempt_(\d+)", str(attempt_id))
    return int(match.group(1)) if match else None


class OrphanTruthAdoption:
    """Dedicated recovery authority; it never constructs a normal Lease."""

    def __init__(self, db: ControlDB):
        self.db = db

    @staticmethod
    def _row(con, branch_id: str, case_id: str, attempt_id: str):
        return con.execute(
            "SELECT * FROM branch_queue WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
            (branch_id, case_id, attempt_id),
        ).fetchone()

    @staticmethod
    def _fail(reason: str, **details):
        raise RecoveryBlocked(reason, details)

    def _gate(self, con, evidence: Mapping[str, Any], row, control):
        values = dict(evidence or {})
        if (row["branch_id"], row["logical_case_id"], row["attempt_id"]) != _IDENTITY:
            self._fail("EXACT_RECOVERY_IDENTITY_REQUIRED")
        for key in _REQUIRED_EVIDENCE:
            if key not in values:
                self._fail("RECOVERY_EVIDENCE_FIELD_MISSING", field=key)
        if row["state"] != "AMBIGUOUS_QUARANTINED":
            self._fail("RECOVERY_QUEUE_NOT_QUARANTINED", state=row["state"])
        if row["slot_id"] is None or row["lease_token_hash"] is None or row["fencing_generation"] is None:
            self._fail("RECOVERY_HISTORICAL_SLOT_BINDING_MISSING")
        if int(control["new_entry_hold"]) != 1:
            self._fail("RECOVERY_REQUIRES_GLOBAL_HOLD")
        if int(values["scientific_entry_count"]) != 1:
            self._fail("SCIENTIFIC_ENTRY_COUNT_NOT_ONE", count=values["scientific_entry_count"])
        if int(values["solver_invocation_count"]) != 1:
            self._fail("SOLVER_INVOCATION_COUNT_NOT_ONE", count=values["solver_invocation_count"])
        for key in ("replay_count", "duplicate_scientific_entry_count", "foreign_mutation_count"):
            if int(values[key]) != 0:
                self._fail("RECOVERY_COUNT_NOT_ZERO", field=key, count=values[key])
        for key in ("newer_attempt_exists", "live_process", "persistence_active", "conflicting_truth", "autofill_enabled", "runtime_owner_created"):
            if values[key] is not False:
                self._fail("RECOVERY_BOOLEAN_GATE_FAILED", field=key, value=values[key])
        for key in ("truth_valid", "s15_s16_non_entered"):
            if values[key] is not True:
                self._fail("RECOVERY_BOOLEAN_GATE_FAILED", field=key, value=values[key])
        if not _hex64(values["evidence_manifest_sha256"]) or not _hex64(values["artifact_identity_sha256"]):
            self._fail("RECOVERY_HASH_FORMAT_INVALID")
        hashes = values["artifact_hashes"]
        if not isinstance(hashes, Mapping) or not hashes or any(not _hex64(v) for v in hashes.values()):
            self._fail("RECOVERY_ARTIFACT_HASHES_INVALID")
        if artifact_identity_sha256(hashes) != str(values["artifact_identity_sha256"]).lower():
            self._fail("RECOVERY_ARTIFACT_IDENTITY_MISMATCH")
        entries = int(con.execute(
            "SELECT COUNT(*) FROM lease_events WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND event_type='SCIENTIFIC_SOLVER_ENTERED'",
            _IDENTITY,
        ).fetchone()[0])
        if entries != 1:
            self._fail("CONTROL_ENTRY_COUNT_NOT_ONE", count=entries)
        duplicate_metric = con.execute(
            "SELECT metric_value FROM health_metrics WHERE metric_name='DUPLICATE_SCIENTIFIC_ENTRY_COUNT'"
        ).fetchone()
        if duplicate_metric is not None and int(duplicate_metric["metric_value"]) != 0:
            self._fail("CONTROL_DUPLICATE_METRIC_NONZERO", count=duplicate_metric["metric_value"])
        current_slot = con.execute("SELECT * FROM slots WHERE slot_id=?", (row["slot_id"],)).fetchone()
        if current_slot is None or current_slot["state"] != "FREE" or any(
            current_slot[key] is not None for key in ("owner_branch", "logical_case_id", "attempt_id", "lease_token")
        ):
            self._fail("RECOVERY_SLOT_NOT_FREE", slot_id=row["slot_id"])
        for table in ("resource_reservations", "gpu_capacity_leases"):
            active = con.execute(
                f"SELECT COUNT(*) FROM {table} WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND state IN ({','.join('?' for _ in _ACTIVE_RESOURCE_STATES)})",
                (*_IDENTITY, *_ACTIVE_RESOURCE_STATES),
            ).fetchone()[0]
            if active:
                self._fail("RECOVERY_RESOURCE_STILL_ACTIVE", table=table, count=active)
        newer = []
        for candidate in con.execute(
            "SELECT attempt_id FROM branch_queue WHERE branch_id=? AND logical_case_id=?",
            (_IDENTITY[0], _IDENTITY[1]),
        ):
            number = _attempt_number(candidate["attempt_id"])
            if number is not None and number > 4:
                newer.append(candidate["attempt_id"])
        if newer:
            self._fail("NEWER_S14_ATTEMPT_EXISTS", attempts=newer)
        for case_id in ("K6V1_S15", "K6V1_S16"):
            entered = con.execute(
                "SELECT COUNT(*) FROM lease_events WHERE branch_id=? AND logical_case_id=? AND event_type='SCIENTIFIC_SOLVER_ENTERED'",
                (_IDENTITY[0], case_id),
            ).fetchone()[0]
            if entered:
                self._fail("S15_S16_ALREADY_ENTERED", case=case_id, count=entered)
        if int(values["scientific_entry_count"]) != entries:
            self._fail("EVIDENCE_CONTROL_ENTRY_MISMATCH", evidence=values["scientific_entry_count"], control=entries)
        return current_slot

    def issue_fence(self, *, evidence: Mapping[str, Any], control_generation: int, metadata: Mapping[str, Any] | None = None,
                    branch_id: str = _IDENTITY[0], logical_case_id: str = _IDENTITY[1], attempt_id: str = _IDENTITY[2]):
        with self.db.immediate() as con:
            control = self.db.ensure_admission_control(con)
            self.db.ensure_recovery_adoption_fences(con)
            if int(control["control_generation"]) != int(control_generation):
                self._fail("RECOVERY_CONTROL_GENERATION_STALE", expected=control_generation, actual=control["control_generation"])
            if (branch_id, logical_case_id, attempt_id) != _IDENTITY:
                self._fail("EXACT_RECOVERY_IDENTITY_REQUIRED")
            row = self._row(con, branch_id, logical_case_id, attempt_id)
            if row is None:
                self._fail("RECOVERY_QUEUE_ROW_MISSING")
            self._gate(con, evidence, row, control)
            existing = con.execute(
                "SELECT * FROM recovery_adoption_fences WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
                _IDENTITY,
            ).fetchone()
            if existing is not None:
                if existing["state"] == "ARMED":
                    if (
                        existing["expected_queue_updated_at"] == row["updated_at"]
                        and existing["expected_control_generation"] == int(control["control_generation"])
                        and existing["evidence_manifest_sha256"] == str(evidence["evidence_manifest_sha256"]).lower()
                        and existing["artifact_identity_sha256"] == str(evidence["artifact_identity_sha256"]).lower()
                    ):
                        return {"status": "ALREADY_ARMED", **dict(existing)}
                if existing["state"] == "CONSUMED":
                    return {"status": "ALREADY_CONSUMED", **dict(existing)}
                self._fail("RECOVERY_FENCE_ALREADY_EXISTS", state=existing["state"])
            fence_id = "recovery-" + secrets.token_urlsafe(24)
            now = utc_now()
            con.execute(
                "INSERT INTO recovery_adoption_fences(fence_id,branch_id,logical_case_id,attempt_id,expected_queue_state,expected_queue_updated_at,expected_slot_id,expected_lease_token_hash,expected_fencing_generation,expected_control_generation,evidence_manifest_sha256,artifact_identity_sha256,state,created_at,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    fence_id, *_IDENTITY, row["state"], row["updated_at"], row["slot_id"],
                    row["lease_token_hash"], int(row["fencing_generation"]), int(control["control_generation"]),
                    str(evidence["evidence_manifest_sha256"]).lower(), str(evidence["artifact_identity_sha256"]).lower(),
                    "ARMED", now,
                    json.dumps({"recovery_authority": True, "runtime_owner_created": False, **dict(metadata or {})}, sort_keys=True),
                ),
            )
            return {
                "status": "ARMED", "fence_id": fence_id, "branch_id": _IDENTITY[0],
                "logical_case_id": _IDENTITY[1], "attempt_id": _IDENTITY[2],
                "expected_queue_state": row["state"], "expected_queue_updated_at": row["updated_at"],
                "expected_control_generation": int(control["control_generation"]),
                "expected_slot_id": row["slot_id"], "expected_fencing_generation": int(row["fencing_generation"]),
                "evidence_manifest_sha256": str(evidence["evidence_manifest_sha256"]).lower(),
                "artifact_identity_sha256": str(evidence["artifact_identity_sha256"]).lower(),
            }

    def adopt(self, *, fence_id: str, evidence: Mapping[str, Any], control_generation: int, metadata: Mapping[str, Any] | None = None,
              branch_id: str = _IDENTITY[0], logical_case_id: str = _IDENTITY[1], attempt_id: str = _IDENTITY[2],
              _test_failpoint: str | None = None):
        with self.db.immediate() as con:
            control = self.db.ensure_admission_control(con)
            self.db.ensure_recovery_adoption_fences(con)
            if (branch_id, logical_case_id, attempt_id) != _IDENTITY:
                self._fail("EXACT_RECOVERY_IDENTITY_REQUIRED")
            fence = con.execute("SELECT * FROM recovery_adoption_fences WHERE fence_id=?", (fence_id,)).fetchone()
            if fence is None:
                self._fail("RECOVERY_FENCE_NOT_FOUND")
            row = self._row(con, branch_id, logical_case_id, attempt_id)
            if row is None:
                self._fail("RECOVERY_QUEUE_ROW_MISSING")
            if fence["state"] == "CONSUMED":
                if row["state"] == RECOVERY_TERMINAL_STATE:
                    adopted = con.execute(
                        "SELECT COUNT(*) FROM lease_events WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND event_type='ORPHAN_TRUTH_ADOPTED'",
                        _IDENTITY,
                    ).fetchone()[0]
                    if adopted == 1:
                        return {"status": "ALREADY_CONSUMED", "fence_id": fence_id, "recovery_transaction_id": fence["recovery_transaction_id"]}
                self._fail("RECOVERY_FENCE_CONSUMED_WITHOUT_TERMINAL")
            if fence["state"] != "ARMED":
                self._fail("RECOVERY_FENCE_NOT_ARMED", state=fence["state"])
            if int(control["control_generation"]) != int(control_generation) or int(control["control_generation"]) != int(fence["expected_control_generation"]):
                self._fail("RECOVERY_CONTROL_GENERATION_STALE", expected=fence["expected_control_generation"], actual=control["control_generation"])
            if (fence["branch_id"], fence["logical_case_id"], fence["attempt_id"]) != _IDENTITY:
                self._fail("RECOVERY_FENCE_IDENTITY_MISMATCH")
            if (
                row["state"] != fence["expected_queue_state"] or row["updated_at"] != fence["expected_queue_updated_at"]
                or row["slot_id"] != fence["expected_slot_id"] or row["lease_token_hash"] != fence["expected_lease_token_hash"]
                or int(row["fencing_generation"]) != int(fence["expected_fencing_generation"])
            ):
                self._fail("RECOVERY_QUEUE_CAS_MISMATCH")
            if str(evidence.get("evidence_manifest_sha256", "")).lower() != fence["evidence_manifest_sha256"]:
                self._fail("RECOVERY_EVIDENCE_MANIFEST_MISMATCH")
            if str(evidence.get("artifact_identity_sha256", "")).lower() != fence["artifact_identity_sha256"]:
                self._fail("RECOVERY_ARTIFACT_IDENTITY_MISMATCH")
            self._gate(con, evidence, row, control)
            txid = "adopt-" + secrets.token_urlsafe(24)
            now = utc_now()
            if _test_failpoint == "before_commit":
                raise RuntimeError("TEST_FAIL_BEFORE_COMMIT")
            changed = con.execute(
                "UPDATE recovery_adoption_fences SET state='CONSUMED',consumed_at=?,recovery_transaction_id=? WHERE fence_id=? AND state='ARMED'",
                (now, txid, fence_id),
            ).rowcount
            if changed != 1:
                self._fail("RECOVERY_FENCE_CONSUME_RACE")
            if _test_failpoint == "after_fence_consumption":
                raise RuntimeError("TEST_FAIL_AFTER_FENCE_CONSUMPTION")
            payload = json.loads(row["payload_json"] or "{}")
            payload["recovery_adoption"] = {
                "status": RECOVERY_TERMINAL_STATE, "recovery_transaction_id": txid, "recovery_fence_id": fence_id,
                "evidence_manifest_sha256": fence["evidence_manifest_sha256"], "artifact_identity_sha256": fence["artifact_identity_sha256"],
                "artifact_hashes": dict(evidence["artifact_hashes"]), "original_runtime_owner_not_recreated": True,
                "runtime_owner_created": False, "original_slot_id": fence["expected_slot_id"],
                "original_fencing_generation": int(fence["expected_fencing_generation"]),
                "scientific_fact": "attempt_004 generated the validated truth through one real solver execution",
                "control_fact": "normal terminal ownership finalization failed after premature release; orphan truth was adopted by a strictly fenced recovery transaction",
            }
            changed = con.execute(
                "UPDATE branch_queue SET state=?,payload_json=?,slot_id=NULL,lease_token_hash=NULL,fencing_generation=NULL,updated_at=? WHERE queue_id=? AND state=? AND updated_at=?",
                (RECOVERY_TERMINAL_STATE, json.dumps(payload, sort_keys=True, ensure_ascii=False), utc_now(), row["queue_id"], fence["expected_queue_state"], fence["expected_queue_updated_at"]),
            ).rowcount
            if changed != 1:
                self._fail("RECOVERY_QUEUE_CAS_MISMATCH")
            if _test_failpoint == "after_queue_update":
                raise RuntimeError("TEST_FAIL_AFTER_QUEUE_UPDATE")
            event_metadata = {
                "recovery_authority": True, "recovery_fence_id": fence_id, "recovery_transaction_id": txid,
                "runtime_owner_created": False, "event_role": "RECOVERY_PROVENANCE_NOT_LEASE_OWNERSHIP",
                "original_runtime_owner_not_recreated": True, "terminal_state": RECOVERY_TERMINAL_STATE,
                "expected_queue_state": fence["expected_queue_state"], "expected_queue_updated_at": fence["expected_queue_updated_at"],
                "evidence_manifest_sha256": fence["evidence_manifest_sha256"], "artifact_identity_sha256": fence["artifact_identity_sha256"],
                "artifact_hashes": dict(evidence["artifact_hashes"]), **dict(metadata or {}),
            }
            con.execute(
                "INSERT INTO lease_events(timestamp,slot_id,branch_id,logical_case_id,attempt_id,event_type,lease_token_hash,fencing_generation,metadata_json) VALUES(?,?,?,?,?,?,?,?,?)",
                (now, fence["expected_slot_id"], fence["branch_id"], fence["logical_case_id"], fence["attempt_id"], "ORPHAN_TRUTH_ADOPTED", fence["expected_lease_token_hash"], fence["expected_fencing_generation"], json.dumps(event_metadata, sort_keys=True, ensure_ascii=False)),
            )
            if _test_failpoint == "after_provenance":
                raise RuntimeError("TEST_FAIL_AFTER_PROVENANCE")
            slot = con.execute("SELECT * FROM slots WHERE slot_id=?", (fence["expected_slot_id"],)).fetchone()
            if slot["state"] != "FREE" or any(slot[key] is not None for key in ("owner_branch", "logical_case_id", "attempt_id", "lease_token")):
                self._fail("RECOVERY_SLOT_CHANGED_DURING_ADOPTION")
            return {"status": "RECOVERED_ADOPTED", "recovery_transaction_id": txid, "recovery_fence_id": fence_id, "queue_state": RECOVERY_TERMINAL_STATE, "runtime_owner_created": False, "slot_state": slot["state"]}
