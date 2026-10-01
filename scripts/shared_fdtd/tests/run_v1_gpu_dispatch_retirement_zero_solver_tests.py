from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from shared_fdtd.control_v3.allocator import Allocator
from shared_fdtd.control_v3.db import ControlDB
from shared_fdtd.control_v3.resources import ResourceSnapshot
from shared_fdtd.engine import dispatcher

SCHEMA = ROOT / "shared_fdtd" / "control_v3" / "schema.sql"
SNAPSHOT = ResourceSnapshot("PASS", "fixture", 10**12, 10**12, 10**12, 10**12,
                            0, 10**12, 0, 0, 0, 0, 0, ())


def main():
    with tempfile.TemporaryDirectory(prefix="gpu_v3_retirement_") as raw:
        db = ControlDB(Path(raw) / "control.sqlite3")
        db.initialize(SCHEMA)
        db.set_admission_control(new_entry_hold=False, temporary_runtime_cap=None)
        gpu_payload = {"backend_type": "GPU", "production_science": True,
                       "resource_class": "HEAVY", "estimated_peak_ram_bytes": 1000,
                       "estimated_commit_bytes": 1000, "mpi_ranks": 1, "threads": 1}
        dispatcher.enqueue(db, "coupling_ml", "GPU_CASE", "attempt_001", gpu_payload)
        cpu_payload = {"backend_type": "CPU", "production_science": False}
        dispatcher.enqueue(db, "traditional", "CPU_CASE", "attempt_001", cpu_payload)
        original = Allocator.acquire
        acquired = []
        def spy(self, *args, **kwargs):
            acquired.append((args, kwargs))
            return original(self, *args, **kwargs)
        launched = []
        with patch.object(Allocator, "acquire", spy), \
             patch.object(dispatcher, "read_resource_snapshot", lambda: SNAPSHOT):
            gpu_result = dispatcher.dispatch_once(
                db, "coupling_ml", lambda row, lease: launched.append(row["logical_case_id"]))
            assert gpu_result == []
            assert acquired == []
            with db.connect(readonly=True) as con:
                gpu = con.execute("SELECT state FROM branch_queue WHERE logical_case_id='GPU_CASE'").fetchone()
            assert gpu["state"] == "QUEUED"
            cpu_result = dispatcher.dispatch_once(
                db, "traditional", lambda row, lease: launched.append(row["logical_case_id"]) or
                {"queue_state": "HOST_STARTED"})
            assert cpu_result == ["CPU_CASE"]
            assert len(acquired) == 1
            assert launched == ["CPU_CASE"]
    print("PASS: V3 GPU rejected before acquire; CPU dispatch remains enabled; zero solver calls")


if __name__ == "__main__":
    main()
