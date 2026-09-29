from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from shared_fdtd.control_v3 import ControlDB
from shared_fdtd.engine.dispatcher import enqueue, dispatch_once
from shared_fdtd.tools.v3_dispatcher_service import launch_factory
from shared_fdtd.control_v3.allocator import Allocator

SCHEMA = ROOT / "scripts" / "shared_fdtd" / "control_v3" / "schema.sql"


def main():
    with tempfile.TemporaryDirectory(prefix="same_launcher_preentry_zero_solver_") as raw:
        root = Path(raw)
        db = ControlDB(root / "control.sqlite3")
        db.initialize(SCHEMA)
        db.set_admission_control(new_entry_hold=False, temporary_runtime_cap=1)
        case = "SAME_LAUNCHER_PREENTRY"
        attempt_root = root / "outputs" / case / "attempt_001"
        runtime = root / "runtime" / case / "attempt_001"
        pre = attempt_root / "setup" / "runtime.fsp"
        pre.parent.mkdir(parents=True)
        pre.write_bytes(b"zero-solver setup only")
        payload = {
            "task": "ZERO_SOLVER_PREENTRY_HANDSHAKE",
            "task_name": "ZERO_SOLVER_PREENTRY_HANDSHAKE",
            "output_root": str(root / "outputs"),
            "attempt_root": str(attempt_root),
            "runtime": str(runtime),
            "pre_fsp": str(pre),
            "pre_fsp_sha256": hashlib.sha256(pre.read_bytes()).hexdigest(),
            "physical_contract_hash": "0" * 64,
            "production_science": False,
            "resource_class": "LIGHT",
            "estimated_commit_bytes": 1,
            "estimated_peak_ram_bytes": 1,
            "scientific_launcher": None,
            "processes": 1,
            "threads": 1,
        }
        enqueue(db, "coupling_ml", case, "attempt_001", payload)
        launched = dispatch_once(
            db, "coupling_ml", launch_factory(db.path, preentry_only=True),
            logical_case_id=case, attempt_id="attempt_001",
        )
        assert launched == []
        boundary_path = attempt_root / "scientific_entry_boundary.json"
        deadline = time.monotonic() + 5.0
        while not boundary_path.is_file() and time.monotonic() < deadline:
            time.sleep(0.05)
        if not boundary_path.is_file():
            with db.connect(readonly=True) as con:
                row_diag = con.execute("SELECT state,payload_json,slot_id FROM branch_queue WHERE logical_case_id=?", (case,)).fetchone()
            diagnostics = {
                "attempt_files": [str(p.relative_to(attempt_root)) for p in attempt_root.rglob("*")],
                "runtime_files": [str(p.relative_to(runtime)) for p in runtime.rglob("*")] if runtime.exists() else [],
                "stdout": (runtime / "host_stdout.log").read_text(errors="replace") if (runtime / "host_stdout.log").is_file() else "",
                "stderr": (runtime / "host_stderr.log").read_text(errors="replace") if (runtime / "host_stderr.log").is_file() else "",
                "queue": dict(row_diag) if row_diag else None,
            }
            raise AssertionError(json.dumps(diagnostics, ensure_ascii=False))
        boundary = json.loads(boundary_path.read_text(encoding="utf-8"))
        assert boundary["status"] == "PREENTRY_BOUNDARY_REACHED"
        assert boundary["solver_entered"] is False
        assert boundary["scientific_solver_entry_count"] == 0
        assert boundary["run_invocation_count"] == 0
        assert (runtime / "host_stdout.log").is_file()
        assert (runtime / "host_stderr.log").is_file()
        with db.connect(readonly=True) as con:
            row = con.execute("SELECT state,slot_id FROM branch_queue WHERE logical_case_id=?", (case,)).fetchone()
            entries = con.execute(
                "SELECT COUNT(*) FROM lease_events WHERE logical_case_id=? AND event_type='SCIENTIFIC_SOLVER_ENTERED'",
                (case,),
            ).fetchone()[0]
        assert row["state"] == "WAIT_RESOURCE_CAPACITY" and row["slot_id"] is None
        assert entries == 0
        print(json.dumps({
            "status": "PASS",
            "solver_runs": 0,
            "scientific_solver_entries": entries,
            "queue_state": row["state"],
            "owner_released": row["slot_id"] is None,
            "stdout_captured": True,
            "stderr_captured": True,
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
