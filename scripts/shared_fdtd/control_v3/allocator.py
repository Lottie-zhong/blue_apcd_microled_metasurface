from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from dataclasses import dataclass
from typing import Any

from .db import ControlDB, utc_now

ACTIVE_STATES = ("RESERVED", "LIVE", "RELEASE_PENDING", "OWNER_QUARANTINED")


class OwnershipMismatch(RuntimeError): pass
class BranchCapReached(RuntimeError): pass
class NoFreeSlot(RuntimeError): pass
class ControlPlaneDeferred(RuntimeError): pass
class AdmissionGateBlocked(RuntimeError): pass


@dataclass(frozen=True)
class Lease:
    slot_id: str
    owner_branch: str
    logical_case_id: str
    attempt_id: str
    lease_token: str
    fencing_generation: int
    control_generation: int | None = None
    admission_provenance: dict[str, Any] | None = None

    @property
    def token_hash(self) -> str:
        return hashlib.sha256(self.lease_token.encode()).hexdigest()


class Allocator:
    def __init__(self, db: ControlDB): self.db = db

    @staticmethod
    def _event(con, lease: Lease, event: str, metadata=None):
        con.execute("INSERT INTO lease_events(timestamp,slot_id,branch_id,logical_case_id,attempt_id,event_type,lease_token_hash,fencing_generation,metadata_json) VALUES(?,?,?,?,?,?,?,?,?)",
                    (utc_now(), lease.slot_id, lease.owner_branch, lease.logical_case_id, lease.attempt_id, event, lease.token_hash, lease.fencing_generation, json.dumps(metadata or {}, sort_keys=True)))

    @staticmethod
    def _health_blockers(con):
        bad = []
        for row in con.execute("SELECT metric_name,metric_value FROM health_metrics WHERE metric_value<>0"):
            bad.append({"metric_name": row["metric_name"], "metric_value": int(row["metric_value"])})
        return bad

    def _admission_decision(self, con, branch: str, *, lease=None, resource_request=None, resource_snapshot=None, resource_policy=None, backend_type=None, final=False):
        from .gpu_capacity import ensure_gpu_capacity_tables, gpu_capacity_status
        from .resources import backend_admission, read_resource_snapshot, resource_admission
        control = self.db.ensure_admission_control(con)
        branch_row = con.execute("SELECT * FROM branch_limits WHERE branch_id=?", (branch,)).fetchone()
        reasons = []
        if branch_row is None or not int(branch_row["enabled"]):
            reasons.append("BRANCH_DISABLED")
        if bool(control["new_entry_hold"]):
            reasons.append("NEW_ENTRY_HOLD")
        formal_cap = int(branch_row["cap"]) if branch_row is not None else 0
        temporary_cap = control.get("temporary_runtime_cap")
        effective_cap = min(formal_cap, int(temporary_cap)) if temporary_cap is not None else formal_cap
        active_states = ACTIVE_STATES
        active_rows = [dict(row) for row in con.execute("SELECT slot_id,owner_branch,logical_case_id,attempt_id,state FROM slots WHERE state IN (?,?,?,?)", active_states)]
        if lease is not None:
            active_rows = [row for row in active_rows if row["slot_id"] != lease.slot_id]
        branch_active = sum(row["owner_branch"] == branch for row in active_rows)
        global_cap = int(con.execute("SELECT COUNT(*) FROM slots").fetchone()[0])
        global_active = len(active_rows)
        if branch_row is not None and branch_active >= effective_cap:
            reasons.append("BRANCH_EFFECTIVE_CAP_REACHED")
        if global_active >= global_cap:
            reasons.append("GLOBAL_CAP_REACHED")

        ensure_gpu_capacity_tables(con)
        gpu_status = gpu_capacity_status(con)
        gpu_active = int(con.execute("SELECT COUNT(*) FROM gpu_capacity_leases WHERE state IN (?,?,?,?)", active_states).fetchone()[0])
        if lease is not None:
            gpu_active -= int(con.execute("SELECT COUNT(*) FROM gpu_capacity_leases WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND state IN (?,?,?,?)", (lease.owner_branch, lease.logical_case_id, lease.attempt_id, *active_states)).fetchone()[0])
        backend = str(backend_type).upper() if backend_type is not None else None
        if backend == "GPU" and gpu_active >= int(gpu_status["GPU_PHYSICAL_CONCURRENCY_CAP"]):
            reasons.append("GPU_PHYSICAL_CAP_REACHED")

        if resource_request is not None or backend is not None:
            resource_snapshot = resource_snapshot or read_resource_snapshot()
        backend_evidence = None
        if backend is not None:
            backend_evidence = backend_admission(con, backend, branch=branch, logical_case_id=lease.logical_case_id if lease else "", attempt_id=lease.attempt_id if lease else "", snapshot=resource_snapshot)
            if backend_evidence["BACKEND_PREFLIGHT"] != "PASS":
                reasons.extend(backend_evidence.get("reasons") or ["BACKEND_PREFLIGHT_BLOCKED"])
        resource_evidence = None
        if resource_request is not None:
            exclude_key = None if lease is None else (lease.owner_branch, lease.logical_case_id, lease.attempt_id)
            resource_evidence = resource_admission(con, branch, resource_request, resource_snapshot, pw_integrated_max_concurrent=int((resource_policy or {}).get("pw_integrated_max_concurrent", 1)), exclude_key=exclude_key)
            if resource_evidence["RESOURCE_PREFLIGHT"] != "PASS":
                reasons.extend(resource_evidence.get("reasons") or ["RESOURCE_PREFLIGHT_BLOCKED"])

        health_blockers = self._health_blockers(con)
        if control["health_status"] != "PASS" or health_blockers:
            reasons.append("ADMISSION_HEALTH_BLOCKED")

        owner_evidence = None
        if final:
            owner_evidence = {"slot": False, "generation": False, "reservation": True, "gpu_reservation": True}
            slot = con.execute("SELECT * FROM slots WHERE slot_id=?", (lease.slot_id,)).fetchone() if lease is not None else None
            owner_evidence["slot"] = bool(slot and slot["state"] == "RESERVED" and slot["owner_branch"] == lease.owner_branch and slot["logical_case_id"] == lease.logical_case_id and slot["attempt_id"] == lease.attempt_id and slot["lease_token"] == lease.lease_token and int(slot["fencing_generation"]) == int(lease.fencing_generation))
            owner_evidence["generation"] = lease is not None and (lease.control_generation is None or int(lease.control_generation) == int(control["control_generation"]))
            if resource_request is not None:
                reservation = con.execute("SELECT state FROM resource_reservations WHERE branch_id=? AND logical_case_id=? AND attempt_id=?", (lease.owner_branch, lease.logical_case_id, lease.attempt_id)).fetchone()
                owner_evidence["reservation"] = bool(reservation and reservation["state"] == "RESERVED")
            if backend == "GPU":
                gpu_lease = con.execute("SELECT state FROM gpu_capacity_leases WHERE branch_id=? AND logical_case_id=? AND attempt_id=?", (lease.owner_branch, lease.logical_case_id, lease.attempt_id)).fetchone()
                owner_evidence["gpu_reservation"] = bool(gpu_lease and gpu_lease["state"] == "RESERVED")
            if not all(owner_evidence.values()):
                reasons.append("OWNER_FENCING_OR_RESERVATION_INVALID")

        return {
            "eligible": not reasons, "reasons": sorted(set(reasons)),
            "branch_enabled": bool(branch_row and int(branch_row["enabled"])),
            "new_entry_hold": bool(control["new_entry_hold"]),
            "formal_branch_cap": formal_cap, "temporary_runtime_cap": temporary_cap,
            "effective_branch_entry_limit": effective_cap,
            "branch_active_count": branch_active, "global_active_count": global_active, "global_cap": global_cap,
            "gpu_active_owner_count": gpu_active, "gpu_physical_concurrency_cap": int(gpu_status["GPU_PHYSICAL_CONCURRENCY_CAP"]),
            "health_status": control["health_status"], "health_blockers": health_blockers,
            "control_generation": int(control["control_generation"]),
            "backend": backend_evidence, "resource": resource_evidence, "owner_fencing_reservation": owner_evidence,
            "final_recheck": bool(final),
        }

    def acquire(self, branch: str, logical_case_id: str, attempt_id: str, *, resource_request=None, resource_snapshot=None, resource_policy=None, backend_type=None) -> Lease:
        try:
            with self.db.immediate() as con:
                from .resources import ResourceRequest, ensure_resource_tables, normalize_backend, read_resource_snapshot
                ensure_resource_tables(con)
                backend_type = normalize_backend(backend_type)
                if resource_request is not None and not isinstance(resource_request, ResourceRequest):
                    resource_request = ResourceRequest.from_payload(resource_request)
                if resource_request is not None or backend_type is not None:
                    resource_snapshot = resource_snapshot or read_resource_snapshot()
                decision = self._admission_decision(con, branch, resource_request=resource_request, resource_snapshot=resource_snapshot, resource_policy=resource_policy, backend_type=backend_type)
                if not decision["eligible"]:
                    branch_only = set(decision["reasons"]).issubset({"BRANCH_DISABLED", "BRANCH_EFFECTIVE_CAP_REACHED"})
                    if branch_only:
                        raise BranchCapReached(json.dumps(decision, sort_keys=True))
                    from .resources import ResourceCapacityWait
                    raise ResourceCapacityWait(decision)
                limit = con.execute("SELECT * FROM branch_limits WHERE branch_id=?", (branch,)).fetchone()
                slots = {r["slot_id"]: r for r in con.execute("SELECT * FROM slots WHERE state='FREE'")}
                chosen = next((s for s in json.loads(limit["preferred_slot_order"]) if s in slots), None)
                if not chosen:
                    raise NoFreeSlot("global capacity exhausted")
                row = slots[chosen]; generation = row["fencing_generation"] + 1; token = secrets.token_urlsafe(32); now = utc_now()
                changed = con.execute("UPDATE slots SET state='RESERVED',owner_branch=?,logical_case_id=?,attempt_id=?,lease_token=?,fencing_generation=?,acquired_at=?,solver_entered_at=NULL,heartbeat_at=?,updated_at=?,version=version+1 WHERE slot_id=? AND state='FREE'", (branch, logical_case_id, attempt_id, token, generation, now, now, now, chosen)).rowcount
                if changed != 1: raise NoFreeSlot("concurrent acquisition won")
                lease = Lease(
                    chosen, branch, logical_case_id, attempt_id, token, generation,
                    int(decision["control_generation"]),
                    {
                        "admission_timestamp": now,
                        "admission_generation": int(decision["control_generation"]),
                        "admission_new_entry_hold": bool(decision["new_entry_hold"]),
                        "admission_branch_enabled": bool(decision["branch_enabled"]),
                        "admission_effective_branch_cap": int(decision["effective_branch_entry_limit"]),
                    },
                )
                if resource_request is not None:
                    request = resource_request
                    reservation = con.execute("SELECT reservation_id,state FROM resource_reservations WHERE branch_id=? AND logical_case_id=? AND attempt_id=?", (branch, logical_case_id, attempt_id)).fetchone()
                    values = (chosen, request.resource_class, backend_type or "CPU", request.estimated_peak_ram_bytes, request.estimated_commit_bytes, request.mpi_ranks, request.threads, int(request.integrated_pw), request.safety_margin_ratio, now)
                    if reservation is None:
                        con.execute("INSERT INTO resource_reservations(branch_id,logical_case_id,attempt_id,slot_id,resource_class,backend_type,estimated_peak_ram_bytes,estimated_commit_bytes,mpi_ranks,threads,integrated_pw,safety_margin_ratio,state,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (branch, logical_case_id, attempt_id, *values[:-1], "RESERVED", values[-1], values[-1]))
                    elif reservation["state"] == "RELEASED":
                        con.execute("UPDATE resource_reservations SET slot_id=?,resource_class=?,backend_type=?,estimated_peak_ram_bytes=?,estimated_commit_bytes=?,mpi_ranks=?,threads=?,integrated_pw=?,safety_margin_ratio=?,state='RESERVED',released_at=NULL,updated_at=? WHERE reservation_id=?", (*values, reservation["reservation_id"]))
                    else:
                        raise RuntimeError("RESOURCE_RESERVATION_ALREADY_ACTIVE")
                if backend_type == "GPU":
                    from .gpu_capacity import reserve_gpu_capacity
                    decision = {**decision, "gpu_capacity_reserved": reserve_gpu_capacity(con, lease)}
                self._event(con, lease, "LEASE_ACQUIRED", {"admission": decision, "admission_control_generation": lease.control_generation})
                return lease
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc).lower(): raise ControlPlaneDeferred(str(exc)) from exc
            raise

    def final_admission(self, lease: Lease, *, resource_request=None, resource_snapshot=None, resource_policy=None, backend_type=None) -> dict[str, Any]:
        from .resources import ResourceRequest
        if resource_request is not None and not isinstance(resource_request, ResourceRequest):
            resource_request = ResourceRequest.from_payload(resource_request)
        with self.db.immediate() as con:
            decision = self._admission_decision(con, lease.owner_branch, lease=lease, resource_request=resource_request, resource_snapshot=resource_snapshot, resource_policy=resource_policy, backend_type=backend_type, final=True)
            self._event(con, lease, "FINAL_ADMISSION_PASS" if decision["eligible"] else "FINAL_ADMISSION_BLOCKED", decision)
            return decision

    @staticmethod
    def _release_provisional_in_con(con, lease: Lease, reason: str) -> dict[str, Any]:
        row = con.execute("SELECT * FROM slots WHERE slot_id=?", (lease.slot_id,)).fetchone()
        if row is None or row["state"] == "FREE":
            return {"status": "ALREADY_FREE", "duplicate_side_effects": 0}
        matches = (
            row["owner_branch"] == lease.owner_branch
            and row["logical_case_id"] == lease.logical_case_id
            and row["attempt_id"] == lease.attempt_id
            and row["lease_token"] == lease.lease_token
            and int(row["fencing_generation"]) == int(lease.fencing_generation)
        )
        if not matches:
            raise OwnershipMismatch(lease.slot_id)
        now = utc_now()
        con.execute(
            "UPDATE slots SET state='FREE',owner_branch=NULL,logical_case_id=NULL,attempt_id=NULL,"
            "lease_token=NULL,acquired_at=NULL,solver_entered_at=NULL,heartbeat_at=NULL,"
            "updated_at=?,version=version+1 WHERE slot_id=? AND state<>'FREE'",
            (now, lease.slot_id),
        )
        from .resources import ensure_resource_tables
        ensure_resource_tables(con)
        con.execute(
            "UPDATE resource_reservations SET state='RELEASED',released_at=?,updated_at=? "
            "WHERE slot_id=? AND branch_id=? AND logical_case_id=? AND attempt_id=?",
            (now, now, lease.slot_id, lease.owner_branch, lease.logical_case_id, lease.attempt_id),
        )
        from .gpu_capacity import release_gpu_capacity
        release_gpu_capacity(con, lease)
        return {"status": "RELEASED", "duplicate_side_effects": 0}

    def final_launch_revalidation(
        self, lease: Lease, *, resource_request=None, resource_snapshot=None,
        resource_policy=None, backend_type=None, admission_timestamp=None, start=None,
    ) -> dict[str, Any]:
        """Revalidate authority while holding the write lock through child start."""
        from .resources import ResourceRequest
        if resource_request is not None and not isinstance(resource_request, ResourceRequest):
            resource_request = ResourceRequest.from_payload(resource_request)
        with self.db.immediate() as con:
            decision = self._admission_decision(
                con, lease.owner_branch, lease=lease, resource_request=resource_request,
                resource_snapshot=resource_snapshot, resource_policy=resource_policy,
                backend_type=backend_type, final=True,
            )
            if lease.control_generation is None:
                decision = {**decision, "eligible": False, "reasons": sorted(set(decision["reasons"]) | {"ADMISSION_GENERATION_MISSING"})}
            admission = dict(lease.admission_provenance or {})
            provenance = {
                "admission_generation": lease.control_generation,
                "final_launch_generation": decision["control_generation"],
                "admission_timestamp": admission_timestamp or admission.get("admission_timestamp"),
                "final_revalidation_timestamp": utc_now(),
                "child_start_timestamp": None,
                "admission_new_entry_hold": admission.get("admission_new_entry_hold"),
                "admission_branch_enabled": admission.get("admission_branch_enabled"),
                "admission_effective_branch_cap": admission.get("admission_effective_branch_cap"),
                "final_new_entry_hold": decision["new_entry_hold"],
                "final_branch_enabled": decision["branch_enabled"],
                "final_effective_branch_cap": decision["effective_branch_entry_limit"],
            }
            if not decision["eligible"]:
                self._event(con, lease, "FINAL_LAUNCH_REVALIDATION_BLOCKED", {"decision": decision, "provenance": provenance})
                owner = decision.get("owner_fencing_reservation") or {}
                released = (
                    self._release_provisional_in_con(con, lease, "FINAL_LAUNCH_REVALIDATION_BLOCKED")
                    if owner.get("slot") else {"status": "NOT_RELEASED_OWNER_MISMATCH", "duplicate_side_effects": 0}
                )
                self._event(con, lease, "STALE_ADMISSION_REJECTED", {"decision": decision, "provenance": provenance, "release": released})
                return {"eligible": False, "decision": decision, "provenance": provenance, "release": released}
            self._event(con, lease, "FINAL_LAUNCH_REVALIDATION_PASS", {"decision": decision, "provenance": provenance})
            launch_result = None
            if start is not None:
                launch_result = start(provenance)
                provenance = {**provenance, "child_start_timestamp": utc_now()}
                self._event(con, lease, "CHILD_PROCESS_STARTED", {"provenance": provenance})
            return {"eligible": True, "decision": decision, "provenance": provenance, "launch_result": launch_result}

    def release_provisional(self, lease: Lease, reason: str) -> dict[str, Any]:
        with self.db.immediate() as con:
            released = self._release_provisional_in_con(con, lease, reason)
            self._event(con, lease, "PROVISIONAL_LEASE_RELEASED", {"reason": reason, "control_generation": lease.control_generation, "replay": 0})
            return released

    def _mutate(self, lease: Lease, sql_set: str, args: tuple, event: str, metadata=None, resource_state=None):
        try:
            with self.db.immediate() as con:
                changed = con.execute(f"UPDATE slots SET {sql_set},updated_at=?,version=version+1 WHERE slot_id=? AND owner_branch=? AND logical_case_id=? AND attempt_id=? AND lease_token=? AND fencing_generation=? AND state<>'FREE'",
                                      (*args, utc_now(), lease.slot_id, lease.owner_branch, lease.logical_case_id, lease.attempt_id, lease.lease_token, lease.fencing_generation)).rowcount
                if changed != 1: raise OwnershipMismatch(lease.slot_id)
                if resource_state is not None:
                    from .resources import ensure_resource_tables
                    ensure_resource_tables(con)
                    con.execute("UPDATE resource_reservations SET state=?,updated_at=? WHERE slot_id=? AND branch_id=? AND logical_case_id=? AND attempt_id=?",
                                (resource_state, utc_now(), lease.slot_id, lease.owner_branch, lease.logical_case_id, lease.attempt_id))
                    from .gpu_capacity import mutate_gpu_capacity
                    mutate_gpu_capacity(con, lease, resource_state)
                self._event(con, lease, event, metadata)
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc).lower(): raise ControlPlaneDeferred(str(exc)) from exc
            raise

    def mark_entered(self, lease): self._mutate(lease, "state='LIVE',solver_entered_at=?,heartbeat_at=?", (utc_now(), utc_now()), "SCIENTIFIC_SOLVER_ENTERED", resource_state="LIVE")
    def heartbeat(self, lease): self._mutate(lease, "heartbeat_at=?", (utc_now(),), "HEARTBEAT")
    def release_pending(self, lease, reason: str): self._mutate(lease, "state='RELEASE_PENDING'", (), "RELEASE_PENDING", {"reason": reason}, resource_state="RELEASE_PENDING")
    def quarantine_owned(self, lease, reason: str): self._mutate(lease, "state='OWNER_QUARANTINED'", (), "OWNER_QUARANTINED", {"reason": reason}, resource_state="OWNER_QUARANTINED")

    @staticmethod
    def _check_release_terminal(scientific_terminal: str) -> None:
        if scientific_terminal not in {"SCIENTIFIC_VALID", "FAILED_PREENTRY", "POSTENTRY_NO_TRUTH"}:
            raise ValueError("unsupported scientific terminal: " + str(scientific_terminal))

    def release_owned(self, lease: Lease, *, scientific_terminal: str):
        if scientific_terminal == "POSTENTRY_NO_TRUTH":
            raise ValueError("use release_postentry_no_truth for entered-no-truth closeout")
        result = self.release_owned_idempotent(lease, scientific_terminal=scientific_terminal)
        if result["status"] != "RELEASED":
            raise OwnershipMismatch(lease.slot_id)

    def release_owned_idempotent(self, lease: Lease, *, scientific_terminal: str) -> dict:
        if scientific_terminal == "POSTENTRY_NO_TRUTH":
            raise ValueError("use release_postentry_no_truth_idempotent for entered-no-truth closeout")
        return self._release_owned_idempotent(lease, scientific_terminal=scientific_terminal)

    def release_postentry_no_truth(self, lease: Lease, *, reason: str, provenance=None) -> dict:
        result = self.release_postentry_no_truth_idempotent(lease, reason=reason, provenance=provenance)
        if result["status"] not in {"RELEASED", "ALREADY_FREE"}:
            raise OwnershipMismatch(lease.slot_id)
        return result

    def release_postentry_no_truth_idempotent(self, lease: Lease, *, reason: str, provenance=None) -> dict:
        metadata = {"reason": reason, "replay": 0, "provenance": provenance or {}}
        return self._release_owned_idempotent(lease, scientific_terminal="POSTENTRY_NO_TRUTH", metadata=metadata)

    def _release_owned_idempotent(self, lease: Lease, *, scientific_terminal: str, metadata=None) -> dict:
        self._check_release_terminal(scientific_terminal)
        try:
            with self.db.immediate() as con:
                from .resources import ensure_resource_tables
                ensure_resource_tables(con)
                row = con.execute("SELECT * FROM slots WHERE slot_id=?", (lease.slot_id,)).fetchone()
                if row is None:
                    raise OwnershipMismatch(lease.slot_id)
                if row["state"] == "FREE":
                    return {"status": "ALREADY_FREE", "duplicate_side_effects": 0}
                matches = (
                    row["owner_branch"] == lease.owner_branch
                    and row["logical_case_id"] == lease.logical_case_id
                    and row["attempt_id"] == lease.attempt_id
                    and row["lease_token"] == lease.lease_token
                    and int(row["fencing_generation"]) == int(lease.fencing_generation)
                )
                if not matches:
                    raise OwnershipMismatch(lease.slot_id)
                changed = con.execute(
                    "UPDATE slots SET state='FREE',owner_branch=NULL,logical_case_id=NULL,attempt_id=NULL,lease_token=NULL,acquired_at=NULL,solver_entered_at=NULL,heartbeat_at=NULL,updated_at=?,version=version+1 WHERE slot_id=? AND state<>'FREE'",
                    (utc_now(), lease.slot_id),
                ).rowcount
                if changed != 1:
                    return {"status": "ALREADY_FREE", "duplicate_side_effects": 0}
                con.execute(
                    "UPDATE resource_reservations SET state='RELEASED',released_at=?,updated_at=? WHERE slot_id=? AND branch_id=? AND logical_case_id=? AND attempt_id=?",
                    (utc_now(), utc_now(), lease.slot_id, lease.owner_branch, lease.logical_case_id, lease.attempt_id),
                )
                from .gpu_capacity import release_gpu_capacity
                release_gpu_capacity(con, lease)
                self._event(con, lease, "LEASE_RELEASED", {"scientific_terminal": scientific_terminal, **(metadata or {})})
                return {"status": "RELEASED", "duplicate_side_effects": 0}
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc).lower():
                raise ControlPlaneDeferred(str(exc)) from exc
            raise

    def list_slots_readonly(self):
        with self.db.connect(readonly=True) as con:
            return [dict(r) for r in con.execute("SELECT slot_id,state,owner_branch,logical_case_id,attempt_id,fencing_generation,solver_entered_at,heartbeat_at,updated_at,version FROM slots ORDER BY slot_id")]

    def list_resource_reservations_readonly(self):
        with self.db.connect(readonly=True) as con:
            try:
                return [dict(row) for row in con.execute("SELECT * FROM resource_reservations ORDER BY reservation_id")]
            except sqlite3.OperationalError:
                return []

    def gpu_capacity_status_readonly(self):
        from .gpu_capacity import gpu_capacity_status
        with self.db.connect(readonly=True) as con:
            return gpu_capacity_status(con, ensure=False)

    def set_gpu_physical_cap(self, physical_cap: int) -> None:
        from .gpu_capacity import set_gpu_physical_cap
        with self.db.immediate() as con:
            set_gpu_physical_cap(con, physical_cap)

    def set_branch_limit(self, branch: str, cap: int, enabled=True, preferred=None):
        preferred = preferred or ["GLOBAL_SLOT_1","GLOBAL_SLOT_2","GLOBAL_SLOT_3"]
        with self.db.immediate() as con:
            control = self.db.ensure_admission_control(con)
            old = con.execute("SELECT * FROM branch_limits WHERE branch_id=?", (branch,)).fetchone()
            changed = old is None or int(old["cap"]) != int(cap) or int(old["enabled"]) != int(bool(enabled)) or old["preferred_slot_order"] != json.dumps(preferred)
            con.execute("INSERT INTO branch_limits VALUES(?,?,?,?,?) ON CONFLICT(branch_id) DO UPDATE SET cap=excluded.cap,enabled=excluded.enabled,preferred_slot_order=excluded.preferred_slot_order,updated_at=excluded.updated_at",
                        (branch, cap, int(enabled), json.dumps(preferred), utc_now()))
            if changed:
                con.execute("UPDATE admission_control SET control_generation=control_generation+1,updated_at=? WHERE control_id=1", (utc_now(),))
