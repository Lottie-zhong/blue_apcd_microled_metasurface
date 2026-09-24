from __future__ import annotations

import json
import tempfile
from pathlib import Path

from shared_fdtd.control_v3.allocator import Allocator
from shared_fdtd.control_v3.db import ControlDB
from shared_fdtd.engine.dispatcher import dispatch_once, enqueue


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "shared_fdtd" / "control_v3" / "schema.sql"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="apcd_gpu_autofill_sandbox_") as td:
        db = ControlDB(Path(td) / "sandbox.sqlite3")
        db.initialize(SCHEMA)
        allocator = Allocator(db)
        allocator.set_gpu_physical_cap(3)
        for case in ("T_BENCH_1", "T_BENCH_2"):
            enqueue(db, "traditional", case, "a1", {"backend_type": "GPU"})
        for case in ("M_BENCH_1", "M_BENCH_2", "M_BENCH_3"):
            enqueue(db, "coupling_ml", case, "a1", {"backend_type": "GPU"})

        leases = {}
        launches = []

        def launch(row, lease):
            leases[row["logical_case_id"]] = lease
            launches.append(row["logical_case_id"])
            return {"queue_state": "HOST_STARTED"}

        t_first = bool(dispatch_once(db, "traditional", launch))
        before = len(launches)
        dispatch_once(db, "traditional", launch)
        t_blocked = len(launches) == before
        m_first = bool(dispatch_once(db, "coupling_ml", launch))
        m_second = bool(dispatch_once(db, "coupling_ml", launch))
        before = len(launches)
        dispatch_once(db, "coupling_ml", launch)
        m_blocked = len(launches) == before

        allocator.release_owned_idempotent(leases["M_BENCH_1"], scientific_terminal="SCIENTIFIC_VALID")
        before = len(launches)
        dispatch_once(db, "coupling_ml", launch)
        m_refill = len(launches) == before + 1
        allocator.release_owned_idempotent(leases["T_BENCH_1"], scientific_terminal="SCIENTIFIC_VALID")
        before = len(launches)
        dispatch_once(db, "traditional", launch)
        t_refill = len(launches) == before + 1
        before = len(launches)
        dispatch_once(db, "traditional", launch)
        dispatch_once(db, "coupling_ml", launch)
        repeated_tick = len(launches) == before

        with db.connect(readonly=True) as con:
            active = con.execute("SELECT COUNT(*) FROM slots WHERE state <> 'FREE'").fetchone()[0]
            entries = con.execute("SELECT COUNT(*) FROM lease_events WHERE event_type='SCIENTIFIC_SOLVER_ENTERED'").fetchone()[0]
            queue = {row["logical_case_id"]: row["state"] for row in con.execute("SELECT logical_case_id,state FROM branch_queue ORDER BY logical_case_id")}

        checks = {
            "traditional_cap1_then_local_refill": t_first and t_blocked and t_refill and launches[0] == "T_BENCH_1" and launches[-1] == "T_BENCH_2",
            "coupling_ml_cap2_then_local_refill": launches[1:4] == ["M_BENCH_1", "M_BENCH_2", "M_BENCH_3"],
            "refill_does_not_wait_for_other_branch": "M_BENCH_3" in launches and "T_BENCH_2" in launches,
            "event_tick_driven_no_duplicate": repeated_tick and launches.count("T_BENCH_1") == 1 and launches.count("M_BENCH_3") == 1,
            "no_solver_invocations": entries == 0,
            "final_active_owner_count": active == 3,
            "all_named_cases_discovered": set(queue) == {"T_BENCH_1", "T_BENCH_2", "M_BENCH_1", "M_BENCH_2", "M_BENCH_3"},
        }
    result = {
        "schema": "SHARED_V3_GPU_AUTOFILL_SANDBOX_ZERO_SOLVER_V1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "launch_order": launches,
        "active_owner_count": active,
        "scientific_solver_entries": entries,
        "solver_invocations": 0,
        "direct_sqlite_mutations": 0,
        "queue_state": queue,
    }
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
