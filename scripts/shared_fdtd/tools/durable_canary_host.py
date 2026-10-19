from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
sys.path.insert(0, r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")

import lumapi

from shared_fdtd.control_v3 import Allocator, ControlDB
from shared_fdtd.control_v3.allocator import Lease
from shared_fdtd.control_v3.db import utc_now
from shared_fdtd.engine.attempt_state import write_durable_attempt_state
from shared_fdtd.engine.event_log import append_event
from shared_fdtd.engine.persistence import atomic_json


def build(fd, path: Path, simulation_time: float):
    fd.addfdtd()
    fd.set("dimension", "3D")
    fd.set("x span", 0.8e-6)
    fd.set("y span", 0.8e-6)
    fd.set("z span", 1.0e-6)
    fd.set("mesh accuracy", 1)
    fd.set("simulation time", simulation_time)
    fd.set("x min bc", "PML")
    fd.set("x max bc", "PML")
    fd.set("y min bc", "PML")
    fd.set("y max bc", "PML")
    fd.set("z min bc", "PML")
    fd.set("z max bc", "PML")
    fd.addplane()
    fd.set("name", "canary_source")
    fd.set("injection axis", "z-axis")
    fd.set("direction", "Forward")
    fd.set("z", -0.3e-6)
    fd.set("x span", 0.6e-6)
    fd.set("y span", 0.6e-6)
    fd.set("wavelength start", 590e-9)
    fd.set("wavelength stop", 610e-9)
    fd.addpower()
    fd.set("name", "canary_monitor")
    fd.set("monitor type", "2D Z-normal")
    fd.set("z", 0.3e-6)
    fd.set("x span", 0.6e-6)
    fd.set("y span", 0.6e-6)
    fd.set("override global monitor settings", 1)
    fd.set("frequency points", 3)
    fd.save(str(path))


def main() -> int:
    cfg = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    root = Path(cfg["attempt_root"])
    root.mkdir(parents=True, exist_ok=True)
    events = root / "events.jsonl"
    db = ControlDB(cfg["db"])
    allocator = Allocator(db)
    lease = Lease(cfg["slot_id"], cfg["branch"], cfg["case"], cfg["attempt"], cfg["lease_token"], int(cfg["fencing_generation"]))
    runtime = Path(cfg["runtime_fsp"])
    setup = root / "setup.fsp"
    native = Path(cfg["native_target"])
    post = Path(cfg["post_target"])
    raw = Path(cfg["raw_target"])
    log = Path(cfg["solver_log"])
    try:
        import lumapi
        fd = lumapi.FDTD(hide=True)
        build(fd, setup, float(cfg.get("simulation_time", 5e-13)))
        fd.close()
        fd = lumapi.FDTD(str(setup), hide=True)
        fd.save(str(runtime))
        expected = {"solver_pids": [os.getpid()], "host_pid": os.getpid(), "solver_creation_time_utc": ""}
        state = write_durable_attempt_state(
            root / "attempt_state.json",
            cfg=cfg,
            lease=lease,
            setup_path=setup,
            runtime_fsp=runtime,
            native_target=native,
            post_target=post,
            raw_target=raw,
            logs=[log],
            adapter_identity="TraditionalDurableCanaryAdapter",
            scientific_contract_hash="CANARY-CONTRACT-C1-C2",
            expected_process_identity=expected,
            persistence_preflight={"status": "PASS", "sandbox": True},
        )
        atomic_json(root / "host_started.json", {"pid": os.getpid(), "timestamp_utc": utc_now()})
        append_event(events, "SETUP_READY", setup=str(setup))
        allocator.mark_entered(lease)
        append_event(events, "SCIENTIFIC_SOLVER_ENTERED", process_identity=expected, run_invocation_count=1)
        with db.immediate() as con:
            con.execute(
                "UPDATE branch_queue SET state='SCIENTIFIC_SOLVER_RUNNING',updated_at=? WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
                (utc_now(), cfg["branch"], cfg["case"], cfg["attempt"]),
            )
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("FDTD canary entered; solver running\n", encoding="utf-8")
        fd.run()
        fd.save(str(runtime))
        fd.close()
        append_event(events, "SOLVER_RETURNED")
        log.write_text(log.read_text(encoding="utf-8") + "Simulation complete\nAutoshutoff level: canary\n", encoding="utf-8")
        atomic_json(root / "solver_returned.json", {"timestamp_utc": utc_now(), "solver_runs": 1, "replay": 0})
        return 0
    except BaseException as exc:
        append_event(events, "CANARY_HOST_ERROR", error=repr(exc))
        atomic_json(root / "host_failure.json", {"error": repr(exc), "timestamp_utc": utc_now()})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

