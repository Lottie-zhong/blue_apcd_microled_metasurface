from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from dataclasses import dataclass

from .db import ControlDB, utc_now

ACTIVE_STATES = ("RESERVED", "LIVE", "RELEASE_PENDING", "OWNER_QUARANTINED")


class OwnershipMismatch(RuntimeError): pass
class BranchCapReached(RuntimeError): pass
class NoFreeSlot(RuntimeError): pass
class ControlPlaneDeferred(RuntimeError): pass


@dataclass(frozen=True)
class Lease:
    slot_id: str
    owner_branch: str
    logical_case_id: str
    attempt_id: str
    lease_token: str
    fencing_generation: int

    @property
    def token_hash(self) -> str:
        return hashlib.sha256(self.lease_token.encode()).hexdigest()


class Allocator:
    def __init__(self, db: ControlDB): self.db = db

    @staticmethod
    def _event(con, lease: Lease, event: str, metadata=None):
        con.execute("INSERT INTO lease_events(timestamp,slot_id,branch_id,logical_case_id,attempt_id,event_type,lease_token_hash,fencing_generation,metadata_json) VALUES(?,?,?,?,?,?,?,?,?)",
                    (utc_now(), lease.slot_id, lease.owner_branch, lease.logical_case_id, lease.attempt_id, event, lease.token_hash, lease.fencing_generation, json.dumps(metadata or {}, sort_keys=True)))

    def acquire(self, branch: str, logical_case_id: str, attempt_id: str, *, resource_request=None, resource_snapshot=None, resource_policy=None) -> Lease:
        admission = None
        try:
            with self.db.immediate() as con:
                if resource_request is not None:
                    from .resources import ResourceCapacityWait, ResourceRequest, ensure_resource_tables, read_resource_snapshot, resource_admission
                    ensure_resource_tables(con)
                    if not isinstance(resource_request, ResourceRequest):
                        resource_request = ResourceRequest.from_payload(resource_request)
                    if resource_request is None:
                        raise ResourceCapacityWait({"RESOURCE_PREFLIGHT": "WAIT_RESOURCE_CAPACITY", "reasons": ["RESOURCE_ESTIMATE_REQUIRED"]})
                    resource_snapshot = resource_snapshot or read_resource_snapshot()
                    admission = resource_admission(con, branch, resource_request, resource_snapshot, pw_integrated_max_concurrent=int((resource_policy or {}).get("pw_integrated_max_concurrent", 1)))
                    if admission["RESOURCE_PREFLIGHT"] != "PASS":
                        raise ResourceCapacityWait(admission)
                limit = con.execute("SELECT * FROM branch_limits WHERE branch_id=? AND enabled=1", (branch,)).fetchone()
                if not limit: raise BranchCapReached(f"branch disabled or absent: {branch}")
                active = con.execute("SELECT COUNT(*) FROM slots WHERE owner_branch=? AND state IN (?,?,?,?)", (branch, *ACTIVE_STATES)).fetchone()[0]
                if active >= limit["cap"]: raise BranchCapReached(branch)
                slots = {r["slot_id"]: r for r in con.execute("SELECT * FROM slots WHERE state='FREE'")}
                chosen = next((s for s in json.loads(limit["preferred_slot_order"]) if s in slots), None)
                if not chosen: raise NoFreeSlot("global capacity exhausted")
                row = slots[chosen]; generation = row["fencing_generation"] + 1; token = secrets.token_urlsafe(32); now = utc_now()
                changed = con.execute("UPDATE slots SET state='RESERVED',owner_branch=?,logical_case_id=?,attempt_id=?,lease_token=?,fencing_generation=?,acquired_at=?,solver_entered_at=NULL,heartbeat_at=?,updated_at=?,version=version+1 WHERE slot_id=? AND state='FREE'",
                                      (branch, logical_case_id, attempt_id, token, generation, now, now, now, chosen)).rowcount
                if changed != 1: raise NoFreeSlot("concurrent acquisition won")
                lease = Lease(chosen, branch, logical_case_id, attempt_id, token, generation)
                if admission is not None:
                    request = resource_request
                    con.execute("INSERT INTO resource_reservations(branch_id,logical_case_id,attempt_id,slot_id,resource_class,estimated_peak_ram_bytes,estimated_commit_bytes,mpi_ranks,threads,integrated_pw,safety_margin_ratio,state,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                (branch, logical_case_id, attempt_id, chosen, request.resource_class, request.estimated_peak_ram_bytes, request.estimated_commit_bytes, request.mpi_ranks, request.threads, int(request.integrated_pw), request.safety_margin_ratio, "RESERVED", now, now))
                self._event(con, lease, "LEASE_ACQUIRED", {"resource_admission": admission} if admission else None)
                return lease
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc).lower(): raise ControlPlaneDeferred(str(exc)) from exc
            raise

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
                self._event(con, lease, event, metadata)
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc).lower(): raise ControlPlaneDeferred(str(exc)) from exc
            raise

    def mark_entered(self, lease): self._mutate(lease, "state='LIVE',solver_entered_at=?,heartbeat_at=?", (utc_now(), utc_now()), "SCIENTIFIC_SOLVER_ENTERED", resource_state="LIVE")
    def heartbeat(self, lease): self._mutate(lease, "heartbeat_at=?", (utc_now(),), "HEARTBEAT")
    def release_pending(self, lease, reason: str): self._mutate(lease, "state='RELEASE_PENDING'", (), "RELEASE_PENDING", {"reason": reason}, resource_state="RELEASE_PENDING")
    def quarantine_owned(self, lease, reason: str): self._mutate(lease, "state='OWNER_QUARANTINED'", (), "OWNER_QUARANTINED", {"reason": reason}, resource_state="OWNER_QUARANTINED")

    def release_owned(self, lease: Lease, *, scientific_terminal: str):
        if scientific_terminal not in {"SCIENTIFIC_VALID", "FAILED_PREENTRY"}:
            raise ValueError("release requires SCIENTIFIC_VALID or FAILED_PREENTRY")
        with self.db.immediate() as con:
            from .resources import ensure_resource_tables
            ensure_resource_tables(con)
            changed = con.execute("UPDATE slots SET state='FREE',owner_branch=NULL,logical_case_id=NULL,attempt_id=NULL,lease_token=NULL,acquired_at=NULL,solver_entered_at=NULL,heartbeat_at=NULL,updated_at=?,version=version+1 WHERE slot_id=? AND owner_branch=? AND logical_case_id=? AND attempt_id=? AND lease_token=? AND fencing_generation=? AND state<>'FREE'",
                                  (utc_now(), lease.slot_id, lease.owner_branch, lease.logical_case_id, lease.attempt_id, lease.lease_token, lease.fencing_generation)).rowcount
            if changed != 1: raise OwnershipMismatch(lease.slot_id)
            con.execute("UPDATE resource_reservations SET state='RELEASED',released_at=?,updated_at=? WHERE slot_id=? AND branch_id=? AND logical_case_id=? AND attempt_id=?",
                        (utc_now(), utc_now(), lease.slot_id, lease.owner_branch, lease.logical_case_id, lease.attempt_id))
            self._event(con, lease, "LEASE_RELEASED", {"scientific_terminal": scientific_terminal})

    def list_slots_readonly(self):
        with self.db.connect(readonly=True) as con:
            return [dict(r) for r in con.execute("SELECT slot_id,state,owner_branch,logical_case_id,attempt_id,fencing_generation,solver_entered_at,heartbeat_at,updated_at,version FROM slots ORDER BY slot_id")]

    def list_resource_reservations_readonly(self):
        with self.db.connect(readonly=True) as con:
            try:
                return [dict(row) for row in con.execute("SELECT * FROM resource_reservations ORDER BY reservation_id")]
            except sqlite3.OperationalError:
                return []

    def set_branch_limit(self, branch: str, cap: int, enabled=True, preferred=None):
        preferred = preferred or ["GLOBAL_SLOT_1","GLOBAL_SLOT_2","GLOBAL_SLOT_3"]
        with self.db.immediate() as con:
            con.execute("INSERT INTO branch_limits VALUES(?,?,?,?,?) ON CONFLICT(branch_id) DO UPDATE SET cap=excluded.cap,enabled=excluded.enabled,preferred_slot_order=excluded.preferred_slot_order,updated_at=excluded.updated_at",
                        (branch, cap, int(enabled), json.dumps(preferred), utc_now()))
