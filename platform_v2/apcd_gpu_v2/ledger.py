import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


class Refused(RuntimeError):
    pass


class Ledger:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as db:
            db.executescript("""
CREATE TABLE IF NOT EXISTS tasks (
 case_id TEXT, attempt_id TEXT, request_sha TEXT UNIQUE NOT NULL,
 config_sha TEXT NOT NULL, payload TEXT NOT NULL,
 state TEXT NOT NULL, entered INTEGER NOT NULL DEFAULT 0 CHECK(entered IN (0,1)),
 entry_at REAL, pre_sha TEXT, contract_sha TEXT, error TEXT,
 bundle TEXT, labels TEXT, PRIMARY KEY(case_id,attempt_id));
CREATE TABLE IF NOT EXISTS slot (
 id INTEGER PRIMARY KEY CHECK(id=1), generation INTEGER NOT NULL,
 token TEXT, owner TEXT, request_sha TEXT);
INSERT OR IGNORE INTO slot(id,generation) VALUES(1,0);
CREATE TABLE IF NOT EXISTS events (
 seq INTEGER PRIMARY KEY AUTOINCREMENT, utc_unix REAL NOT NULL,
 request_sha TEXT, kind TEXT NOT NULL, payload TEXT NOT NULL);
""")

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        return db

    @contextmanager
    def transaction(self):
        db = self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def event(db, request_sha, kind, payload):
        db.execute(
            "INSERT INTO events(utc_unix,request_sha,kind,payload) VALUES(?,?,?,?)",
            (time.time(), request_sha, kind, json.dumps(payload, sort_keys=True)),
        )

    def register(self, request, config):
        if request.config_sha256 != config.sha256:
            raise Refused("CONFIG_REQUEST_MISMATCH")
        with self.transaction() as db:
            bound = db.execute("SELECT config_sha FROM tasks LIMIT 1").fetchone()
            if bound and bound["config_sha"] != config.sha256:
                raise Refused("LEDGER_CONFIG_CONFLICT")
            try:
                db.execute(
                    "INSERT INTO tasks(case_id,attempt_id,request_sha,config_sha,payload,state) VALUES(?,?,?,?,?,?)",
                    (
                        request.case_id,
                        request.attempt_id,
                        request.request_sha256,
                        config.sha256,
                        request.model_dump_json(),
                        "REGISTERED",
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise Refused("DUPLICATE_CASE_ATTEMPT_OR_REQUEST") from exc
            self.event(db, request.request_sha256, "REGISTERED", request.model_dump())

    def claim(self, request_sha, owner):
        with self.transaction() as db:
            task = db.execute(
                "SELECT * FROM tasks WHERE request_sha=?", (request_sha,)
            ).fetchone()
            if not task or task["entered"] or task["state"] != "REGISTERED":
                raise Refused("NOT_CLAIMABLE_NO_REPLAY")
            slot = db.execute("SELECT * FROM slot WHERE id=1").fetchone()
            if slot["token"] is not None:
                raise Refused("OTHER_OWNER_PRESENT")
            token = uuid.uuid4().hex
            db.execute(
                "UPDATE slot SET generation=generation+1,token=?,owner=?,request_sha=? WHERE id=1",
                (token, json.dumps(owner, sort_keys=True), request_sha),
            )
            db.execute(
                "UPDATE tasks SET state='CLAIMED' WHERE request_sha=?", (request_sha,)
            )
            self.event(db, request_sha, "CLAIMED", {"token": token, "owner": owner})
            return token

    @staticmethod
    def fence(db, request_sha, token):
        slot = db.execute("SELECT * FROM slot WHERE id=1").fetchone()
        if not token or slot["token"] != token or slot["request_sha"] != request_sha:
            raise Refused("FENCING_MISMATCH")

    def enter(self, request_sha, token, pre_sha, contract_sha):
        with self.transaction() as db:
            self.fence(db, request_sha, token)
            row = db.execute(
                "SELECT * FROM tasks WHERE request_sha=?", (request_sha,)
            ).fetchone()
            payload = json.loads(row["payload"])
            if row["entered"] or row["state"] != "CLAIMED":
                raise Refused("ENTRY_ALREADY_CONSUMED_OR_STATE_INVALID")
            if (
                pre_sha != payload["pre_fsp_sha256"]
                or contract_sha != payload["physical_contract_sha256"]
            ):
                raise Refused("ENTRY_HASH_MISMATCH")
            entered_at = time.time()
            db.execute(
                "UPDATE tasks SET entered=1,state='ENTRY_UNCERTAIN',entry_at=?,pre_sha=?,contract_sha=? WHERE request_sha=?",
                (entered_at, pre_sha, contract_sha, request_sha),
            )
            self.event(
                db,
                request_sha,
                "ENTRY_COMMITTED_BEFORE_CALL",
                {
                    "token": token,
                    "pre_sha": pre_sha,
                    "contract_sha": contract_sha,
                    "entry_timestamp": entered_at,
                    "scientific": False,
                },
            )

    def finish(
        self, request_sha, token, state, *, error=None, bundle=None, labels=None
    ):
        if state not in {"FAILED_PREENTRY", "FAILED_POSTENTRY", "DONE_OFFLINE"}:
            raise Refused("INVALID_TRANSITION")
        with self.transaction() as db:
            self.fence(db, request_sha, token)
            row = db.execute(
                "SELECT * FROM tasks WHERE request_sha=?", (request_sha,)
            ).fetchone()
            if state == "FAILED_PREENTRY" and (
                row["entered"] or row["state"] != "CLAIMED"
            ):
                raise Refused("CANNOT_REFUND_ENTRY")
            if state != "FAILED_PREENTRY" and (
                not row["entered"] or row["state"] != "ENTRY_UNCERTAIN"
            ):
                raise Refused("INVALID_ENTRY_STATE")
            if state == "DONE_OFFLINE" and (not bundle or not labels):
                raise Refused("TRUTH_REQUIRED_BEFORE_DONE")
            db.execute(
                "UPDATE tasks SET state=?,error=?,bundle=?,labels=? WHERE request_sha=?",
                (state, error, json.dumps(bundle), json.dumps(labels), request_sha),
            )
            self.event(
                db,
                request_sha,
                state,
                {"error": error, "bundle": bundle, "labels": labels},
            )
            # Unknown post-entry failures retain the slot until explicit read-only reconciliation.
            if state != "FAILED_POSTENTRY":
                db.execute(
                    "UPDATE slot SET token=NULL,owner=NULL,request_sha=NULL WHERE id=1"
                )

    def reconcile_dead_owner(self, token, state_reader):
        with self.transaction() as db:
            slot = db.execute("SELECT * FROM slot WHERE id=1").fetchone()
            if not token or slot["token"] != token:
                raise Refused("FENCING_MISMATCH")
            owner = json.loads(slot["owner"])
            status = state_reader(owner)
            if status not in {"dead", "reused"}:
                raise Refused("OWNER_LIVE_OR_UNKNOWN")
            row = db.execute(
                "SELECT * FROM tasks WHERE request_sha=?", (slot["request_sha"],)
            ).fetchone()
            if row["entered"]:
                db.execute(
                    "UPDATE tasks SET state='NEEDS_REVIEW_NO_REPLAY' WHERE request_sha=?",
                    (slot["request_sha"],),
                )
                self.event(
                    db,
                    slot["request_sha"],
                    "RECOVERY_HOLD",
                    {"owner": owner, "identity_state": status},
                )
                return "NEEDS_REVIEW_NO_REPLAY"  # never release: unobserved solver descendants may still live
            db.execute(
                "UPDATE tasks SET state='FAILED_PREENTRY' WHERE request_sha=?",
                (slot["request_sha"],),
            )
            self.event(
                db,
                slot["request_sha"],
                "PREENTRY_OWNER_RECONCILED",
                {"owner": owner, "identity_state": status},
            )
            db.execute(
                "UPDATE slot SET token=NULL,owner=NULL,request_sha=NULL WHERE id=1"
            )
            return "FAILED_PREENTRY"

    def audit(self):
        db = self.connect()
        try:
            return {
                "integrity": db.execute("PRAGMA integrity_check").fetchone()[0],
                "tasks": [
                    dict(r) for r in db.execute("SELECT * FROM tasks ORDER BY case_id")
                ],
                "slot": dict(db.execute("SELECT * FROM slot WHERE id=1").fetchone()),
                "events": [
                    dict(r) for r in db.execute("SELECT * FROM events ORDER BY seq")
                ],
                "scientific_solver_invocations": 0,
                "automatic_replays": 0,
                "mode": "OFFLINE_ONLY",
            }
        finally:
            db.close()
