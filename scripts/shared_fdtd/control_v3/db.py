from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


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
