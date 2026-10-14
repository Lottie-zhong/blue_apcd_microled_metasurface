"""Explicit, fail-closed rebind after a proven preflight-only controller failure."""
import json
import os
from pathlib import Path

from .ledger import Refused
from .processes import identity_state
from .serial import (CouplingBudget, SerialLedger, exclusive, process_gate,
                     validate_admission)


def reconcile_preentry(old_config, old_request, new_config, new_request):
    """Preserve failed lineage; no entry, launch, solver, or implicit retry."""
    if (old_request.config_sha256 != old_config.sha256
            or new_request.config_sha256 != new_config.sha256
            or old_request.admission_sha256 != new_request.admission_sha256
            or Path(old_config.runtime_root).resolve() != Path(new_config.runtime_root).resolve()
            or Path(old_config.coupling_ledger).resolve() != Path(new_config.coupling_ledger).resolve()
            or old_config.mode != new_config.mode):
        raise Refused("PREENTRY_REBIND_IDENTITY_CONFLICT")
    validate_admission(new_config, new_request)
    budget = CouplingBudget(new_config)
    with exclusive(Path(new_config.coupling_ledger).with_suffix(".v2_controller.lock")):
        process_gate(os.getpid())
        budget.validate(new_request)
        for request in (old_request, new_request):
            if (budget.receipt_path(request).exists()
                    or (Path(new_config.runtime_root) / "attempts" / request.request_sha256).exists()
                    or (Path(new_config.runtime_root) / "archives" / request.request_sha256).exists()):
                raise Refused("PREENTRY_DURABLE_ENTRY_OR_NATIVE_ARTIFACT_PRESENT")
        ledger = SerialLedger(Path(new_config.runtime_root) / "ledger.sqlite3")
        with ledger.transaction() as db:
            row = db.execute("SELECT * FROM tasks WHERE case_id=? AND attempt_id=?",
                             (old_request.case_id, old_request.attempt_id)).fetchone()
            if (not row or row["request_sha"] != old_request.request_sha256
                    or row["config_sha"] != old_config.sha256
                    or json.loads(row["payload"]) != old_request.model_dump(mode="json")
                    or row["state"] != "HOLD_NO_REPLAY" or row["entered"]
                    or any(row[k] is not None for k in ("entry_at", "pre_sha", "contract_sha"))
                    or json.loads(row["bundle"] or "null") is not None):
                raise Refused("PREENTRY_LOCAL_STATE_NOT_PROVEN")
            slot = db.execute("SELECT * FROM slot WHERE id=1").fetchone()
            if not slot["token"] or slot["request_sha"] != old_request.request_sha256:
                raise Refused("PREENTRY_OWNER_FENCE_MISMATCH")
            owner = json.loads(slot["owner"])
            owner_state = identity_state(owner)
            if owner_state not in ("dead", "reused"):
                raise Refused("PREENTRY_OWNER_LIVE_OR_UNKNOWN")
            events = [dict(e) for e in db.execute(
                "SELECT * FROM events WHERE request_sha=? ORDER BY seq",
                (old_request.request_sha256,))]
            # Only this earliest preflight failure is supported. Later stages need review.
            if ([e["kind"] for e in events] != ["REGISTERED", "CLAIMED", "HOLD_NO_REPLAY"]
                    or json.loads(events[1]["payload"]).get("owner") != owner
                    or json.loads(events[1]["payload"]).get("token") != slot["token"]):
                raise Refused("PREENTRY_EVENT_CHAIN_NOT_PREFLIGHT_ONLY")
            evidence = dict(schema="APCD_V2_PREFLIGHT_ONLY_REBIND_V1",
                            old_request_sha256=old_request.request_sha256,
                            new_request_sha256=new_request.request_sha256,
                            old_task=dict(row), old_slot=dict(slot), old_events=events,
                            owner_state=owner_state, entry_consumed=False,
                            solver_invocations=0, automatic_replays=0,
                            admission_sha256=new_request.admission_sha256)
            ledger.event(db, old_request.request_sha256, "PREENTRY_REBOUND", evidence)
            ledger.event(db, new_request.request_sha256, "PREENTRY_REBOUND_READY", evidence)
            db.execute("""UPDATE tasks SET request_sha=?,config_sha=?,payload=?,
                          state='REGISTERED',error=NULL,bundle=NULL
                          WHERE case_id=? AND attempt_id=?""",
                       (new_request.request_sha256, new_config.sha256,
                        new_request.model_dump_json(), new_request.case_id, new_request.attempt_id))
            db.execute("UPDATE slot SET token=NULL,owner=NULL,request_sha=NULL WHERE id=1")
            return evidence
