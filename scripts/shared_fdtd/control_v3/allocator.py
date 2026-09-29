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
        if event == "SCIENTIFIC_SOLVER_ENTERED":
            ControlDB.refresh_entry_metrics(con)
        if event == "SCIENTIFIC_SOLVER_ENTERED":
            ControlDB.refresh_entry_metrics(con)

    @staticmethod
    def _health_blockers(con):
        bad = []
        for row in con.execute("SELECT metric_name,metric_value FROM health_metrics WHERE metric_value<>0"):
            bad.append({"metric_name": row["metric_name"], "metric_value": int(row["metric_value"])})
        return bad

    def arm_exact_launch_permit(self, branch: str, logical_case_id: str, attempt_id: str, *, metadata=None, authorization_generation=None) -> dict[str, Any]:
        with self.db.immediate() as con:
            control = self.db.ensure_admission_control(con)
            if int(control["new_entry_hold"]) != 1:
                raise RuntimeError("EXACT_PERMIT_REQUIRES_GLOBAL_HOLD")
            generation = int(control["control_generation"])
            if authorization_generation is not None and int(authorization_generation) != generation:
                raise RuntimeError("EXACT_PERMIT_GENERATION_MISMATCH")
            existing = con.execute(
                "SELECT * FROM exact_launch_permits WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
                (branch, logical_case_id, attempt_id),
            ).fetchone()
            if existing is not None:
                if existing["state"] == "ARMED" and int(existing["authorization_generation"]) == generation:
                    return dict(existing)
                raise RuntimeError("EXACT_PERMIT_ALREADY_TERMINAL")
            active = con.execute("SELECT COUNT(*) FROM exact_launch_permits WHERE state='ARMED'").fetchone()[0]
            if active:
                raise RuntimeError("EXACT_PERMIT_ALREADY_ARMED")
            permit_id = secrets.token_urlsafe(24)
            now = utc_now()
            con.execute(
                "INSERT INTO exact_launch_permits(permit_id,branch_id,logical_case_id,attempt_id,authorization_generation,state,created_at,metadata_json) VALUES(?,?,?,?,?,?,?,?)",
                (permit_id, branch, logical_case_id, attempt_id, generation, "ARMED", now, json.dumps(metadata or {}, sort_keys=True)),
            )
            return dict(con.execute("SELECT * FROM exact_launch_permits WHERE permit_id=?", (permit_id,)).fetchone())

    def _exact_permit_decision(self, con, permit_id, branch, logical_case_id, attempt_id, control, lease=None) -> dict[str, Any]:
        if not permit_id:
            return {"valid": False, "reason": "EXACT_PERMIT_MISSING"}
        row = con.execute("SELECT * FROM exact_launch_permits WHERE permit_id=?", (permit_id,)).fetchone()
        if row is None:
            return {"valid": False, "reason": "EXACT_PERMIT_NOT_FOUND"}
        if row["state"] != "ARMED":
            return {"valid": False, "reason": "EXACT_PERMIT_NOT_ARMED", "state": row["state"]}
        if (row["branch_id"], row["logical_case_id"], row["attempt_id"]) != (branch, logical_case_id, attempt_id):
            return {"valid": False, "reason": "EXACT_PERMIT_IDENTITY_MISMATCH"}
        if int(row["authorization_generation"]) != int(control["control_generation"]):
            return {"valid": False, "reason": "EXACT_PERMIT_GENERATION_STALE"}
        if int(control["new_entry_hold"]) != 1:
            return {"valid": False, "reason": "EXACT_PERMIT_REQUIRES_GLOBAL_HOLD"}
        entries = con.execute("SELECT COUNT(*) FROM lease_events WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND event_type='SCIENTIFIC_SOLVER_ENTERED'", (branch, logical_case_id, attempt_id)).fetchone()[0]
        gpu_entries = con.execute("SELECT COUNT(*) FROM lease_events WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND event_type='GPU_ENGINE_ENTRY_CONFIRMED'", (branch, logical_case_id, attempt_id)).fetchone()[0]
        if entries or gpu_entries:
            return {"valid": False, "reason": "EXACT_PERMIT_ENTRY_ALREADY_RECORDED", "scientific_entry_count": entries, "gpu_engine_entry_count": gpu_entries}
        if lease is None:
            if row["slot_id"] is not None or row["lease_token_hash"] is not None or row["fencing_generation"] is not None:
                return {"valid": False, "reason": "EXACT_PERMIT_ALREADY_BOUND"}
        else:
            if (row["slot_id"], row["lease_token_hash"], row["fencing_generation"]) != (lease.slot_id, lease.token_hash, lease.fencing_generation):
                return {"valid": False, "reason": "EXACT_PERMIT_OWNER_MISMATCH"}
        return {"valid": True, "permit_id": permit_id, "state": row["state"], "authorization_generation": int(row["authorization_generation"]) }

    @staticmethod
    def _bind_exact_launch_permit_in_con(con, permit_id, lease: Lease) -> None:
        if not permit_id:
            return
        row = con.execute("SELECT * FROM exact_launch_permits WHERE permit_id=?", (permit_id,)).fetchone()
        control = con.execute("SELECT * FROM admission_control WHERE control_id=1").fetchone()
        if row is None or control is None:
            raise RuntimeError("EXACT_PERMIT_NOT_FOUND")
        check = Allocator._exact_permit_static_check(row, control, lease)
        if not check["valid"]:
            raise RuntimeError(check["reason"])
        changed = con.execute(
            "UPDATE exact_launch_permits SET slot_id=?,lease_token_hash=?,fencing_generation=?,bound_at=? WHERE permit_id=? AND state='ARMED' AND slot_id IS NULL",
            (lease.slot_id, lease.token_hash, lease.fencing_generation, utc_now(), permit_id),
        ).rowcount
        if changed != 1:
            raise RuntimeError("EXACT_PERMIT_BIND_RACE")

    @staticmethod
    def _exact_permit_static_check(row, control, lease) -> dict[str, Any]:
        if row["state"] != "ARMED":
            return {"valid": False, "reason": "EXACT_PERMIT_NOT_ARMED"}
        if int(control["new_entry_hold"]) != 1:
            return {"valid": False, "reason": "EXACT_PERMIT_REQUIRES_GLOBAL_HOLD"}
        if int(row["authorization_generation"]) != int(control["control_generation"]):
            return {"valid": False, "reason": "EXACT_PERMIT_GENERATION_STALE"}
        return {"valid": True}

    @staticmethod
    def _cancel_armed_permit_in_con(con, lease: Lease) -> int:
        return con.execute(
            "UPDATE exact_launch_permits SET state='CANCELLED',cancelled_at=? WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND state='ARMED' AND (slot_id IS NULL OR (slot_id=? AND lease_token_hash=? AND fencing_generation=?))",
            (utc_now(), lease.owner_branch, lease.logical_case_id, lease.attempt_id, lease.slot_id, lease.token_hash, lease.fencing_generation),
        ).rowcount

    def cancel_exact_launch_permit(self, permit_id: str) -> dict[str, Any]:
        with self.db.immediate() as con:
            self.db.ensure_admission_control(con)
            row = con.execute("SELECT * FROM exact_launch_permits WHERE permit_id=?", (permit_id,)).fetchone()
            if row is None:
                return {"status": "NOT_FOUND", "permit_id": permit_id}
            if row["state"] == "ARMED":
                con.execute("UPDATE exact_launch_permits SET state='CANCELLED',cancelled_at=? WHERE permit_id=? AND state='ARMED'", (utc_now(), permit_id))
                row = con.execute("SELECT * FROM exact_launch_permits WHERE permit_id=?", (permit_id,)).fetchone()
            return {"status": "CANCELLED" if row["state"] == "CANCELLED" else "ALREADY_TERMINAL", **dict(row)}

    def cancel_exact_launch_permit_for_attempt(self, branch: str, logical_case_id: str, attempt_id: str) -> dict[str, Any]:
        with self.db.immediate() as con:
            self.db.ensure_admission_control(con)
            rows = con.execute(
                "SELECT * FROM exact_launch_permits WHERE branch_id=? AND logical_case_id=? AND attempt_id=? ORDER BY created_at",
                (branch, logical_case_id, attempt_id),
            ).fetchall()
            cancelled = con.execute(
                "UPDATE exact_launch_permits SET state='CANCELLED',cancelled_at=? WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND state='ARMED'",
                (utc_now(), branch, logical_case_id, attempt_id),
            ).rowcount
            final = con.execute(
                "SELECT * FROM exact_launch_permits WHERE branch_id=? AND logical_case_id=? AND attempt_id=? ORDER BY created_at",
                (branch, logical_case_id, attempt_id),
            ).fetchall()
            return {
                "status": "CANCELLED" if cancelled else ("ALREADY_TERMINAL" if rows else "NOT_FOUND"),
                "cancelled_count": cancelled,
                "permits": [dict(row) for row in final],
            }

    def _consume_exact_launch_permit_in_con(self, con, permit_id, lease: Lease) -> dict[str, Any]:
        control = self.db.ensure_admission_control(con)
        decision = self._exact_permit_decision(con, permit_id, lease.owner_branch, lease.logical_case_id, lease.attempt_id, control, lease=lease)
        if not decision["valid"]:
            return decision
        changed = con.execute(
            "UPDATE exact_launch_permits SET state='CONSUMED',consumed_at=? WHERE permit_id=? AND state='ARMED' AND slot_id=? AND lease_token_hash=? AND fencing_generation=? AND authorization_generation=?",
            (utc_now(), permit_id, lease.slot_id, lease.token_hash, lease.fencing_generation, lease.control_generation),
        ).rowcount
        if changed != 1:
            return {"valid": False, "reason": "EXACT_PERMIT_CONSUME_RACE"}
        self._event(con, lease, "EXACT_LAUNCH_PERMIT_CONSUMED", {"permit_id": permit_id, "control_generation": lease.control_generation})
        return {"valid": True, "permit_id": permit_id, "state": "CONSUMED"}

    def _admission_decision(self, con, branch: str, *, logical_case_id=None, attempt_id=None, lease=None, resource_request=None, resource_snapshot=None, resource_policy=None, backend_type=None, final=False, exact_permit_id=None):
        from .gpu_capacity import ensure_gpu_capacity_tables, gpu_capacity_status
        from .resources import backend_admission, read_resource_snapshot, resource_admission
        control = self.db.ensure_admission_control(con)
        branch_row = con.execute("SELECT * FROM branch_limits WHERE branch_id=?", (branch,)).fetchone()
        reasons = []
        if branch_row is None or not int(branch_row["enabled"]):
            reasons.append("BRANCH_DISABLED")
        permit = self._exact_permit_decision(
            con, exact_permit_id, branch, logical_case_id or (lease.logical_case_id if lease else ""),
            attempt_id or (lease.attempt_id if lease else ""), control, lease=lease,
        ) if exact_permit_id else {"valid": False, "reason": "EXACT_PERMIT_NOT_REQUESTED"}
        if bool(control["new_entry_hold"]) and not permit["valid"]:
            reasons.append("NEW_ENTRY_HOLD")
        if exact_permit_id and not permit["valid"]:
            reasons.append(permit["reason"])
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
            "exact_launch_permit": permit,
            "final_recheck": bool(final),
        }

    def acquire(self, branch: str, logical_case_id: str, attempt_id: str, *, resource_request=None, resource_snapshot=None, resource_policy=None, backend_type=None, exact_permit_id=None) -> Lease:
        try:
            with self.db.immediate() as con:
                from .resources import ResourceRequest, ensure_resource_tables, normalize_backend, read_resource_snapshot
                ensure_resource_tables(con)
                backend_type = normalize_backend(backend_type)
                if resource_request is not None and not isinstance(resource_request, ResourceRequest):
                    resource_request = ResourceRequest.from_payload(resource_request)
                if resource_request is not None or backend_type is not None:
                    resource_snapshot = resource_snapshot or read_resource_snapshot()
                decision = self._admission_decision(con, branch, logical_case_id=logical_case_id, attempt_id=attempt_id, resource_request=resource_request, resource_snapshot=resource_snapshot, resource_policy=resource_policy, backend_type=backend_type, exact_permit_id=exact_permit_id)
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
                        "exact_launch_permit_id": exact_permit_id,
                    },
                )
                if exact_permit_id:
                    self._bind_exact_launch_permit_in_con(con, exact_permit_id, lease)
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

    def final_admission(self, lease: Lease, *, resource_request=None, resource_snapshot=None, resource_policy=None, backend_type=None, exact_permit_id=None) -> dict[str, Any]:
        from .resources import ResourceRequest
        if resource_request is not None and not isinstance(resource_request, ResourceRequest):
            resource_request = ResourceRequest.from_payload(resource_request)
        with self.db.immediate() as con:
            decision = self._admission_decision(con, lease.owner_branch, logical_case_id=lease.logical_case_id, attempt_id=lease.attempt_id, lease=lease, resource_request=resource_request, resource_snapshot=resource_snapshot, resource_policy=resource_policy, backend_type=backend_type, final=True, exact_permit_id=exact_permit_id)
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
        exact_permit_id=None, consume_permit=True,
    ) -> dict[str, Any]:
        """Revalidate authority while holding the write lock through child start."""
        from .resources import ResourceRequest
        if resource_request is not None and not isinstance(resource_request, ResourceRequest):
            resource_request = ResourceRequest.from_payload(resource_request)
        with self.db.immediate() as con:
            decision = self._admission_decision(
                con, lease.owner_branch, logical_case_id=lease.logical_case_id, attempt_id=lease.attempt_id,
                lease=lease, resource_request=resource_request, resource_snapshot=resource_snapshot,
                resource_policy=resource_policy, backend_type=backend_type, final=True,
                exact_permit_id=exact_permit_id,
            )
            if lease.control_generation is None:
                decision = {**decision, "eligible": False, "reasons": sorted(set(decision["reasons"]) | {"ADMISSION_GENERATION_MISSING"})}
            permit_consumed = False
            if decision["eligible"] and exact_permit_id and consume_permit:
                consumed = self._consume_exact_launch_permit_in_con(con, exact_permit_id, lease)
                if not consumed["valid"]:
                    decision = {**decision, "eligible": False, "reasons": sorted(set(decision["reasons"]) | {consumed["reason"]}), "exact_launch_permit": consumed}
                else:
                    permit_consumed = True
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
                "exact_launch_permit_id": exact_permit_id,
                "exact_launch_permit_consumed": permit_consumed,
            }
            if not decision["eligible"]:
                self._event(con, lease, "FINAL_LAUNCH_REVALIDATION_BLOCKED", {"decision": decision, "provenance": provenance})
                owner = decision.get("owner_fencing_reservation") or {}
                permit_state = (decision.get("exact_launch_permit") or {}).get("state")
                released = (
                    {"status": "NOT_RELEASED_CONSUMED_PERMIT", "duplicate_side_effects": 0}
                    if exact_permit_id and permit_state == "CONSUMED"
                    else (
                        self._release_provisional_in_con(con, lease, "FINAL_LAUNCH_REVALIDATION_BLOCKED")
                        if owner.get("slot") else {"status": "NOT_RELEASED_OWNER_MISMATCH", "duplicate_side_effects": 0}
                    )
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

    def mark_entered(self, lease, *, launch_identity=None):
        """Record an observation once; this is not authorization to invoke a solver.

        Reconciliation and the returning worker may report the same entry. Keep
        the first timestamp and never move RELEASE_PENDING/quarantined owners
        back to LIVE. Historical duplicate rows remain immutable.
        """
        try:
            with self.db.immediate() as con:
                row = con.execute("SELECT * FROM slots WHERE slot_id=?", (lease.slot_id,)).fetchone()
                if row is None or row["state"] == "FREE" or (
                    row["owner_branch"], row["logical_case_id"], row["attempt_id"],
                    row["lease_token"], row["fencing_generation"]
                ) != (lease.owner_branch, lease.logical_case_id, lease.attempt_id,
                      lease.lease_token, lease.fencing_generation):
                    raise OwnershipMismatch(lease.slot_id)
                prior = con.execute(
                    "SELECT event_id,lease_token_hash,fencing_generation FROM lease_events "
                    "WHERE branch_id=? AND logical_case_id=? AND attempt_id=? "
                    "AND event_type='SCIENTIFIC_SOLVER_ENTERED' ORDER BY event_id",
                    (lease.owner_branch, lease.logical_case_id, lease.attempt_id),
                ).fetchall()
                if prior:
                    if any(r["lease_token_hash"] != lease.token_hash or
                           r["fencing_generation"] != lease.fencing_generation for r in prior):
                        raise OwnershipMismatch("SCIENTIFIC_ENTRY_AUTHORITY_CONFLICT")
                    return {"status": "IDEMPOTENT_REPLAY_OF_EVENT", "event_id": prior[0]["event_id"]}
                if row["state"] != "RESERVED":
                    raise OwnershipMismatch("SCIENTIFIC_ENTRY_STATE_CONFLICT")
                now = utc_now()
                con.execute("UPDATE slots SET state='LIVE',solver_entered_at=?,heartbeat_at=?,updated_at=?,version=version+1 WHERE slot_id=?",
                            (now, now, now, lease.slot_id))
                from .resources import ensure_resource_tables
                ensure_resource_tables(con)
                con.execute("UPDATE resource_reservations SET state='LIVE',updated_at=? WHERE slot_id=? AND branch_id=? AND logical_case_id=? AND attempt_id=?",
                            (now, lease.slot_id, lease.owner_branch, lease.logical_case_id, lease.attempt_id))
                from .gpu_capacity import mutate_gpu_capacity
                mutate_gpu_capacity(con, lease, "LIVE")
                key = hashlib.sha256(json.dumps([
                    lease.owner_branch, lease.logical_case_id, lease.attempt_id,
                    "SCIENTIFIC_SOLVER_ENTERED"
                ], separators=(",", ":")).encode()).hexdigest()
                self._event(con, lease, "SCIENTIFIC_SOLVER_ENTERED", {"semantic_event_key": key, "launch_identity": launch_identity})
                return {"status": "RECORDED", "semantic_event_key": key}
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc).lower():
                raise ControlPlaneDeferred(str(exc)) from exc
            raise

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
                    now = utc_now()
                    released_reservations = con.execute(
                        "UPDATE resource_reservations SET state='RELEASED',released_at=?,updated_at=? WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND state<>'RELEASED'",
                        (now, now, lease.owner_branch, lease.logical_case_id, lease.attempt_id),
                    ).rowcount
                    from .gpu_capacity import release_gpu_capacity
                    released_gpu = release_gpu_capacity(con, lease)
                    cancelled_permit = self._cancel_armed_permit_in_con(con, lease)
                    return {"status": "ALREADY_FREE", "duplicate_side_effects": 0, "released_reservations": released_reservations, "released_gpu_capacity": released_gpu, "cancelled_permit": cancelled_permit}
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
                    now = utc_now()
                    released_reservations = con.execute(
                        "UPDATE resource_reservations SET state='RELEASED',released_at=?,updated_at=? WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND state<>'RELEASED'",
                        (now, now, lease.owner_branch, lease.logical_case_id, lease.attempt_id),
                    ).rowcount
                    from .gpu_capacity import release_gpu_capacity
                    released_gpu = release_gpu_capacity(con, lease)
                    cancelled_permit = self._cancel_armed_permit_in_con(con, lease)
                    return {"status": "ALREADY_FREE", "duplicate_side_effects": 0, "released_reservations": released_reservations, "released_gpu_capacity": released_gpu, "cancelled_permit": cancelled_permit}
                con.execute(
                    "UPDATE resource_reservations SET state='RELEASED',released_at=?,updated_at=? WHERE slot_id=? AND branch_id=? AND logical_case_id=? AND attempt_id=?",
                    (utc_now(), utc_now(), lease.slot_id, lease.owner_branch, lease.logical_case_id, lease.attempt_id),
                )
                from .gpu_capacity import release_gpu_capacity
                released_gpu = release_gpu_capacity(con, lease)
                cancelled_permit = self._cancel_armed_permit_in_con(con, lease)
                self._event(con, lease, "LEASE_RELEASED", {"scientific_terminal": scientific_terminal, "cancelled_permit": cancelled_permit, **(metadata or {})})
                return {"status": "RELEASED", "duplicate_side_effects": 0, "released_gpu_capacity": released_gpu, "cancelled_permit": cancelled_permit}
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
