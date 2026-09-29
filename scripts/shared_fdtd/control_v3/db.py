from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


_UNSET = object()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()


class ControlDB:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def connect(self, *, readonly: bool = False, timeout: float = 5.0) -> sqlite3.Connection:
        if readonly:
            con = sqlite3.connect(f"file:{self.path.as_posix()}?mode=ro", uri=True, timeout=timeout, factory=ClosingConnection)
            con.execute("PRAGMA query_only=ON")
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            con = sqlite3.connect(self.path, timeout=timeout, factory=ClosingConnection)
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA foreign_keys=ON")
            con.execute("PRAGMA synchronous=FULL")
        con.row_factory = sqlite3.Row
        return con

    def ensure_exact_launch_permits(self, con):
        con.execute(
            """CREATE TABLE IF NOT EXISTS exact_launch_permits (
                permit_id TEXT PRIMARY KEY,
                branch_id TEXT NOT NULL,
                logical_case_id TEXT NOT NULL,
                attempt_id TEXT NOT NULL,
                slot_id TEXT,
                lease_token_hash TEXT,
                fencing_generation INTEGER,
                authorization_generation INTEGER NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('ARMED','CONSUMED','CANCELLED')),
                created_at TEXT NOT NULL,
                bound_at TEXT,
                consumed_at TEXT,
                cancelled_at TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                UNIQUE(branch_id, logical_case_id, attempt_id)
            )"""
        )

    @staticmethod
    def refresh_entry_metrics(con) -> dict[str, int]:
        """Recompute entry anomalies from append-only canonical lease_events.

        The value is deliberately derived at read/write time rather than from
        a stale counter. Historical duplicate rows remain evidence and count as
        anomalies; idempotent replays do not append rows and therefore add zero.
        """
        row = con.execute("""
            SELECT COALESCE(SUM(extra), 0) AS duplicate_count,
                   COALESCE(SUM(CASE WHEN entries > 1 THEN 1 ELSE 0 END), 0) AS duplicate_attempts
            FROM (
              SELECT branch_id, logical_case_id, attempt_id,
                     COUNT(*) AS entries, COUNT(*) - 1 AS extra
              FROM lease_events
              WHERE event_type='SCIENTIFIC_SOLVER_ENTERED'
                AND branch_id IS NOT NULL AND logical_case_id IS NOT NULL AND attempt_id IS NOT NULL
              GROUP BY branch_id, logical_case_id, attempt_id
            )
        """).fetchone()
        now = utc_now()
        con.execute("UPDATE health_metrics SET metric_value=?,updated_at=? WHERE metric_name='DUPLICATE_SCIENTIFIC_ENTRY_COUNT'",
                    (int(row["duplicate_count"]), now))
        return {"duplicate_scientific_entry_count": int(row["duplicate_count"]),
                "duplicate_scientific_attempt_count": int(row["duplicate_attempts"])}

    def ensure_hold_lifecycle(self, con):
        con.execute("""CREATE TABLE IF NOT EXISTS hold_lifecycle (
            hold_id TEXT PRIMARY KEY, scope TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('ACTIVE','RELEASED','CANCELLED')),
            reason_code TEXT NOT NULL, free_text_reason TEXT NOT NULL DEFAULT '',
            linked_incident_ids_json TEXT NOT NULL DEFAULT '[]',
            linked_case_ids_json TEXT NOT NULL DEFAULT '[]',
            release_requirements_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL, created_by TEXT NOT NULL,
            released_at TEXT, released_by TEXT, release_authority_hash TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}'
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS hold_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT, hold_id TEXT NOT NULL,
            timestamp TEXT NOT NULL, event_type TEXT NOT NULL,
            actor TEXT NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}'
        )""")
        con.execute("CREATE INDEX IF NOT EXISTS idx_hold_lifecycle_active ON hold_lifecycle(status,scope)")
        con.execute("CREATE TRIGGER IF NOT EXISTS hold_events_no_update BEFORE UPDATE ON hold_events BEGIN SELECT RAISE(ABORT,'hold_events are append-only'); END")
        con.execute("CREATE TRIGGER IF NOT EXISTS hold_events_no_delete BEFORE DELETE ON hold_events BEGIN SELECT RAISE(ABORT,'hold_events are append-only'); END")

    def set_hold(self, *, scope, reason_code, free_text_reason='', created_by='unknown', linked_incident_ids=None, linked_case_ids=None, release_requirements=None, metadata=None):
        scope=str(scope).upper()
        if scope not in {'GLOBAL','TRADITIONAL','COUPLING_ML','CASE'}: raise ValueError('invalid hold scope')
        if not reason_code or not created_by: raise ValueError('hold reason and owner required')
        linked_incident_ids=list(linked_incident_ids or []); linked_case_ids=list(linked_case_ids or [])
        requirements=dict(release_requirements or {})
        with self.immediate() as con:
            self.ensure_admission_control(con); self.ensure_hold_lifecycle(con)
            hold_id='hold-'+uuid.uuid4().hex
            now=utc_now(); active=con.execute("SELECT hold_id FROM hold_lifecycle WHERE scope=? AND status='ACTIVE'",(scope,)).fetchall()
            if active: raise RuntimeError('ACTIVE_HOLD_ALREADY_EXISTS:'+scope)
            con.execute("INSERT INTO hold_lifecycle(hold_id,scope,status,reason_code,free_text_reason,linked_incident_ids_json,linked_case_ids_json,release_requirements_json,created_at,created_by,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(hold_id,scope,'ACTIVE',reason_code,str(free_text_reason),json.dumps(linked_incident_ids,sort_keys=True),json.dumps(linked_case_ids,sort_keys=True),json.dumps(requirements,sort_keys=True),now,created_by,json.dumps(metadata or {},sort_keys=True)))
            old=con.execute("SELECT control_generation FROM admission_control WHERE control_id=1").fetchone();generation=int(old['control_generation'])+1
            con.execute("UPDATE admission_control SET new_entry_hold=1,control_generation=?,updated_at=? WHERE control_id=1",(generation,now))
            con.execute("INSERT INTO hold_events(hold_id,timestamp,event_type,actor,metadata_json) VALUES(?,?,?,?,?)",(hold_id,now,'HOLD_SET',created_by,json.dumps({'scope':scope,'reason_code':reason_code,'generation':generation},sort_keys=True)))
            return {'hold_id':hold_id,'scope':scope,'status':'ACTIVE','generation':generation,'created_at':now}

    def release_hold(self, hold_id, *, released_by, release_authority_hash, evidence=None):
        if not released_by or not release_authority_hash: raise ValueError('release authority required')
        with self.immediate() as con:
            self.ensure_admission_control(con); self.ensure_hold_lifecycle(con)
            row=con.execute("SELECT * FROM hold_lifecycle WHERE hold_id=?",(hold_id,)).fetchone()
            if row is None: raise KeyError('HOLD_NOT_FOUND')
            if row['status']!='ACTIVE': return {'status':row['status'],'hold_id':hold_id}
            now=utc_now();old=con.execute("SELECT control_generation FROM admission_control WHERE control_id=1").fetchone();generation=int(old['control_generation'])+1
            con.execute("UPDATE hold_lifecycle SET status='RELEASED',released_at=?,released_by=?,release_authority_hash=?,metadata_json=? WHERE hold_id=? AND status='ACTIVE'",(now,released_by,release_authority_hash,json.dumps({'evidence':evidence or {}},sort_keys=True),hold_id))
            remaining=con.execute("SELECT COUNT(*) FROM hold_lifecycle WHERE status='ACTIVE' AND scope='GLOBAL'").fetchone()[0]
            con.execute("UPDATE admission_control SET new_entry_hold=?,control_generation=?,updated_at=? WHERE control_id=1",(1 if remaining else 0,generation,now))
            con.execute("INSERT INTO hold_events(hold_id,timestamp,event_type,actor,metadata_json) VALUES(?,?,?,?,?)",(hold_id,now,'HOLD_RELEASED',released_by,json.dumps({'authority_hash':release_authority_hash,'generation':generation,'evidence':evidence or {}},sort_keys=True)))
            return {'status':'RELEASED','hold_id':hold_id,'generation':generation,'global_hold':bool(remaining)}

    def list_holds_readonly(self):
        with self.connect(readonly=True) as con:
            try:return [dict(r) for r in con.execute("SELECT * FROM hold_lifecycle ORDER BY created_at")]
            except sqlite3.OperationalError:return []

    def ensure_admission_control(self, con):
        con.execute(
            """CREATE TABLE IF NOT EXISTS admission_control (
                control_id INTEGER PRIMARY KEY CHECK(control_id = 1),
                new_entry_hold INTEGER NOT NULL CHECK(new_entry_hold IN (0,1)),
                temporary_runtime_cap INTEGER CHECK(temporary_runtime_cap IS NULL OR temporary_runtime_cap >= 1),
                health_status TEXT NOT NULL CHECK(health_status IN ('PASS','BLOCKED')),
                control_generation INTEGER NOT NULL CHECK(control_generation >= 0),
                updated_at TEXT NOT NULL
            )"""
        )
        row = con.execute("SELECT * FROM admission_control WHERE control_id=1").fetchone()
        if row is None:
            hold = False
            legacy = self.path.parent / "PW_K6_PRODUCTION_NEW_ENTRY_HOLD.json"
            try:
                payload = json.loads(legacy.read_text(encoding="utf-8"))
                hold = bool(payload.get("hold", False))
            except (OSError, ValueError, TypeError):
                pass
            con.execute(
                "INSERT INTO admission_control(control_id,new_entry_hold,temporary_runtime_cap,health_status,control_generation,updated_at) VALUES(1,?,?,?,?,?)",
                (int(hold), None, "PASS", 0, utc_now()),
            )
            row = con.execute("SELECT * FROM admission_control WHERE control_id=1").fetchone()
        self.ensure_exact_launch_permits(con)
        self.ensure_hold_lifecycle(con)
        return dict(row)

    def ensure_recovery_adoption_fences(self, con):
        con.execute(
            """CREATE TABLE IF NOT EXISTS recovery_adoption_fences (
                fence_id TEXT PRIMARY KEY,
                branch_id TEXT NOT NULL,
                logical_case_id TEXT NOT NULL,
                attempt_id TEXT NOT NULL,
                expected_queue_state TEXT NOT NULL,
                expected_queue_updated_at TEXT NOT NULL,
                expected_slot_id TEXT NOT NULL,
                expected_lease_token_hash TEXT NOT NULL,
                expected_fencing_generation INTEGER NOT NULL,
                expected_control_generation INTEGER NOT NULL,
                evidence_manifest_sha256 TEXT NOT NULL,
                artifact_identity_sha256 TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('ARMED','CONSUMED','ABORTED')),
                created_at TEXT NOT NULL,
                consumed_at TEXT,
                recovery_transaction_id TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                UNIQUE(branch_id, logical_case_id, attempt_id)
            )"""
        )

    def set_admission_control(self, *, new_entry_hold=None, temporary_runtime_cap=_UNSET, health_status=None):
        if temporary_runtime_cap is not _UNSET and temporary_runtime_cap is not None and int(temporary_runtime_cap) < 1:
            raise ValueError("temporary_runtime_cap must be >= 1 or None")
        with self.immediate() as con:
            old = self.ensure_admission_control(con)
            hold = bool(old["new_entry_hold"] if new_entry_hold is None else new_entry_hold)
            temp = old["temporary_runtime_cap"] if temporary_runtime_cap is _UNSET else (None if temporary_runtime_cap is None else int(temporary_runtime_cap))
            health = old["health_status"] if health_status is None else str(health_status).upper()
            if health not in {"PASS", "BLOCKED"}:
                raise ValueError("health_status must be PASS or BLOCKED")
            changed = (int(hold) != int(old["new_entry_hold"]) or temp != old["temporary_runtime_cap"] or health != old["health_status"])
            generation = int(old["control_generation"]) + int(changed)
            con.execute(
                "UPDATE admission_control SET new_entry_hold=?,temporary_runtime_cap=?,health_status=?,control_generation=?,updated_at=? WHERE control_id=1",
                (int(hold), temp, health, generation, utc_now()),
            )
            result = self.ensure_admission_control(con)
        self._sync_legacy_hold(result)
        return result

    def _sync_legacy_hold(self, state):
        legacy = self.path.parent / "PW_K6_PRODUCTION_NEW_ENTRY_HOLD.json"
        if not legacy.exists():
            return
        try:
            payload = json.loads(legacy.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                payload = {}
        except (OSError, ValueError, TypeError):
            payload = {}
        payload.update({
            "hold": bool(state["new_entry_hold"]),
            "control_generation": int(state["control_generation"]),
            "temporary_runtime_cap": state["temporary_runtime_cap"],
            "admission_control_authority": "control.sqlite3:admission_control",
            "admission_control_updated_at": state["updated_at"],
        })
        tmp = legacy.with_name(legacy.name + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, legacy)

    def initialize(self, schema_path: str | Path) -> None:
        with self.connect() as con:
            con.executescript(Path(schema_path).read_text(encoding="utf-8"))
            if con.execute("SELECT COUNT(*) FROM schema_meta").fetchone()[0] == 0:
                con.execute("INSERT INTO schema_meta VALUES(3,3,?)", (utc_now(),))
            now = utc_now()
            for slot in ("GLOBAL_SLOT_1", "GLOBAL_SLOT_2", "GLOBAL_SLOT_3"):
                con.execute("INSERT OR IGNORE INTO slots(slot_id,state,updated_at) VALUES(?,'FREE',?)", (slot, now))
            limits = {
                "traditional": (1, ["GLOBAL_SLOT_1", "GLOBAL_SLOT_2", "GLOBAL_SLOT_3"]),
                "coupling_ml": (2, ["GLOBAL_SLOT_2", "GLOBAL_SLOT_3", "GLOBAL_SLOT_1"]),
            }
            import json
            for branch, (cap, order) in limits.items():
                con.execute("INSERT OR IGNORE INTO branch_limits VALUES(?,?,1,?,?)", (branch, cap, json.dumps(order), now))
            self.ensure_admission_control(con)
            self.ensure_recovery_adoption_fences(con)
            for metric in (
                "FOREIGN_MUTATION_COUNT","DUPLICATE_SCIENTIFIC_ENTRY_COUNT","GLOBAL_CAPACITY_VIOLATION_COUNT",
                "BRANCH_CAP_VIOLATION_COUNT","SCIENTIFIC_VALID_REPLAY_COUNT","TRUTH_LOSS_AFTER_SOLVER_RETURN_COUNT",
                "AUTO_REFILL_COUNT","PENDING_RECONCILE_COUNT","PENDING_RECONCILE_RECOVERED_COUNT",
                "DISPATCHER_CRASH_RECOVERY_COUNT","SCIENTIFIC_HOST_CRASH_COUNT","CONTROL_PLANE_DEFERRED_COUNT",
                "DISPATCHER_CRASH_KILLED_SOLVER_COUNT","SCHEDULER_FAILURE_KILLED_SOLVER_COUNT","SSH_DISCONNECT_KILLED_SOLVER_COUNT",
            ):
                con.execute("INSERT OR IGNORE INTO health_metrics VALUES(?,0,?)", (metric, now))

    @contextmanager
    def immediate(self, timeout: float = 5.0):
        con = self.connect(timeout=timeout)
        try:
            con.execute("BEGIN IMMEDIATE")
            yield con
            con.commit()
        except BaseException:
            con.rollback()
            raise
        finally:
            con.close()
