from __future__ import annotations

import argparse
import json
import sqlite3
import os
import shutil
import sys
import threading
import time
import uuid
import msvcrt
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
sys.path.insert(0, r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
import lumapi

from shared_fdtd.control_v3 import Allocator, ControlDB
from shared_fdtd.control_v3.allocator import Lease
from shared_fdtd.control_v3.db import utc_now
from shared_fdtd.engine.event_log import append_event
from shared_fdtd.engine.host_lifecycle import ScientificHostLifecycle, lifecycle_identity
from shared_fdtd.engine.persistence import atomic_json, sha256_file
from shared_fdtd.engine.process_identity import snapshot, write_identity


def build(fd, path, simulation_time, mesh_accuracy=1, span=0.6e-6, auto_shutoff=None):
    fd.addfdtd(); fd.set("dimension", "3D"); fd.set("x span", span); fd.set("y span", span); fd.set("z span", max(1.0e-6, span)); fd.set("mesh accuracy", mesh_accuracy); fd.set("simulation time", simulation_time)
    if auto_shutoff is not None: fd.set("auto shutoff min", auto_shutoff)
    for axis in ("x", "y"): fd.set(axis + " min bc", "Periodic"); fd.set(axis + " max bc", "Periodic")
    fd.set("z min bc", "PML"); fd.set("z max bc", "PML")
    fd.addplane(); fd.set("name", "tiny_source"); fd.set("injection axis", "z-axis"); fd.set("direction", "Forward"); fd.set("z", -0.2e-6); fd.set("x span", 0.6e-6); fd.set("y span", 0.6e-6); fd.set("wavelength start", 590e-9); fd.set("wavelength stop", 610e-9)
    fd.addpower(); fd.set("name", "tiny_monitor"); fd.set("monitor type", "2D Z-normal"); fd.set("z", 0.2e-6); fd.set("x span", 0.6e-6); fd.set("y span", 0.6e-6); fd.set("override global monitor settings", 1); fd.set("frequency points", 3); fd.save(str(path))


def maybe_inject_control_plane_fault(cfg, root, operation):
    if cfg.get("inject_control_plane_failure") != operation:
        return
    marker = root / "fault_injection.json"
    if marker.exists():
        return
    atomic_json(marker, {"timestamp": utc_now(), "operation": operation, "pid": os.getpid(), "mode": "INFRASTRUCTURE_ONLY"})
    raise sqlite3.OperationalError("INJECTED_CONTROL_PLANE_FAILURE")

def serialized_open(db_path, fsp=None):
    lock = Path(db_path).with_name("lumapi_open.lock"); lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a+b") as f:
        if f.tell() == 0: f.write(b"0"); f.flush()
        deadline = time.monotonic() + 180
        while True:
            try: f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1); break
            except OSError:
                if time.monotonic() > deadline: raise TimeoutError("lumapi appOpen lock timeout")
                time.sleep(1)
        try:
            while True:
                try: return lumapi.FDTD(str(fsp), hide=True) if fsp else lumapi.FDTD(hide=True)
                except lumapi.LumApiError as exc:
                    if time.monotonic() > deadline or "license sharing" not in str(exc).lower(): raise
                    time.sleep(5)
        finally: f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)


def main():
    a = argparse.ArgumentParser(); a.add_argument("config"); cfg = json.loads(Path(a.parse_args().config).read_text(encoding="utf-8"))
    root = Path(cfg["runtime"]); root.mkdir(parents=True, exist_ok=True); events = root / "events.jsonl"; db = ControlDB(cfg["db"]); alloc = Allocator(db)
    lease = Lease(cfg["slot_id"], cfg["branch"], cfg["case"], cfg["attempt"], cfg["lease_token"], cfg["fencing_generation"])
    identity = lifecycle_identity(cfg, lease); lifecycle = ScientificHostLifecycle(events, identity)
    atomic_json(root / "host_started.json", {"pid": os.getpid(), "timestamp": utc_now(), "task": cfg["task_name"]}); write_identity(root / "process_identity.json", cfg["case"], cfg["attempt"], lease)
    stop = threading.Event(); fd = None

    def queue_state(state):
        with db.immediate() as con: con.execute("UPDATE branch_queue SET state=?,updated_at=? WHERE branch_id=? AND logical_case_id=? AND attempt_id=?", (state, utc_now(), cfg["branch"], cfg["case"], cfg["attempt"]))

    def beat():
        while not stop.wait(15):
            atomic_json(root / "heartbeat.json", {"timestamp": utc_now(), "pid": os.getpid(), "processes": snapshot(cfg["case"]), "solver_log": log_state(root)})
            lifecycle.control_plane("heartbeat", lambda: alloc.heartbeat(lease), state="SCIENTIFIC_SOLVER_RUNNING" if lifecycle.entered else "PREENTRY")

    threading.Thread(target=beat, daemon=True).start()
    try:
        setup = root / "setup" / "setup.fsp"; native = root / "native" / "native.fsp"; post = root / "post" / (str(uuid.uuid4()) + "__post.fsp"); raw = root / "raw" / "monitor.json"
        for p in (setup.parent, native.parent, post.parent, raw.parent, root / "logs"): p.mkdir(parents=True, exist_ok=True)
        if not setup.exists():
            fd = serialized_open(cfg["db"]); build(fd, setup, float(cfg["simulation_time"]), int(cfg.get("mesh_accuracy", 1)), float(cfg.get("span", 0.6e-6)), cfg.get("auto_shutoff")); lifecycle.close(fd, "PREENTRY_SETUP_COMPLETE"); fd = None
        shutil.copyfile(setup, native); atomic_json(root / "setup_manifest.json", {"setup_fsp": str(setup), "setup_sha256": sha256_file(setup), "production_science": False})
        append_event(events, "SOLVER_ENTRY_INTENT", branch=cfg["branch"], logical_case_id=cfg["case"], attempt_id=cfg["attempt"], slot_id=lease.slot_id, fencing_generation=lease.fencing_generation)
        fd = serialized_open(cfg["db"], native); fd.setresource("FDTD", 1, "processes", "12"); fd.setresource("FDTD", 1, "threads", "1")
        lifecycle.mark_entered(run_invocation_count=1, process_evidence="heartbeat_thread")
        def queue_entry_state():
            maybe_inject_control_plane_fault(cfg, root, "queue_state:SCIENTIFIC_SOLVER_ENTERED")
            queue_state("SCIENTIFIC_SOLVER_ENTERED")
        lifecycle.control_plane("queue_state:SCIENTIFIC_SOLVER_ENTERED", queue_entry_state, state="SCIENTIFIC_SOLVER_ENTERED")
        lifecycle.control_plane("mark_solver_entered", lambda: alloc.mark_entered(lease), state="SCIENTIFIC_SOLVER_ENTERED")
        append_event(events, "SCIENTIFIC_SOLVER_RUNNING")
        try:
            fd.run()
        except BaseException as exc:
            lifecycle.mark_scientific_terminal(); append_event(events, "SCIENTIFIC_EXECUTION_ERROR", error=repr(exc)); raise
        append_event(events, "SOLVER_RETURNED")
        append_event(events, "NATIVE_TRUTH_PERSISTING")
        fd.save(str(native)); append_event(events, "NATIVE_TRUTH_DURABLE", artifact_path=str(native), sha256=sha256_file(native), size=native.stat().st_size); fd.save(str(post)); lifecycle.mark_truth_durable(); lifecycle.close(fd, "NATIVE_TRUTH_DURABLE"); fd = None
        append_event(events, "POST_FSP_VALID", artifact_path=str(post), sha256=sha256_file(post), size=post.stat().st_size)
        fresh = serialized_open(cfg["db"], post)
        try:
            import numpy as np
            T = np.asarray(fresh.transmission("tiny_monitor")).reshape(-1); proof = {"points": int(T.size), "finite": bool(np.isfinite(T).all()), "T": T.tolist()}
        finally: fresh.close()
        if proof["points"] != 3 or not proof["finite"]: raise RuntimeError("fresh load validation failed")
        atomic_json(raw, proof); append_event(events, "RAW_VALID", artifact_path=str(raw), sha256=sha256_file(raw)); append_event(events, "SCIENTIFIC_VALID"); append_event(events, "HF_ARCHIVED", role="INFRASTRUCTURE_CANARY")
        released = lifecycle.control_plane("release_owned", lambda: alloc.release_owned(lease, scientific_terminal="SCIENTIFIC_VALID"), state="HF_ARCHIVED")
        released = lifecycle.control_plane("queue_state:RELEASED", lambda: queue_state("RELEASED"), state="RELEASED") and released
        if not released: append_event(events, "RELEASE_PENDING", retry_state="PENDING_RECONCILE")
        atomic_json(root / "terminal.json", {"status": "PASS", "release_state": "RELEASED" if released else "PENDING_RECONCILE", "case": cfg["case"], "attempt": cfg["attempt"], "post_fsp": str(post), "post_sha256": sha256_file(post), "fresh_load": proof, "completed_at": utc_now()})
        return 0
    except BaseException as exc:
        if not lifecycle.entered:
            append_event(events, "FAILED_PREENTRY", error=repr(exc)); atomic_json(root / "failure.json", {"status": "FAIL", "state": "FAILED_PREENTRY", "error": repr(exc), "timestamp": utc_now()})
            lifecycle.control_plane("release_preentry", lambda: alloc.release_owned(lease, scientific_terminal="FAILED_PREENTRY"), state="FAILED_PREENTRY")
            lifecycle.control_plane("queue_state:QUEUED", lambda: queue_state("QUEUED"), state="FAILED_PREENTRY")
        elif lifecycle.scientific_terminal:
            append_event(events, "FAILED_AFTER_ENTRY", error=repr(exc)); atomic_json(root / "failure.json", {"status": "FAIL", "state": "FAILED_AFTER_ENTRY", "error": repr(exc), "timestamp": utc_now()})
            lifecycle.control_plane("quarantine_owned", lambda: alloc.quarantine_owned(lease, repr(exc)), state="FAILED_AFTER_ENTRY")
            lifecycle.control_plane("queue_state:FAILED_AFTER_ENTRY", lambda: queue_state("FAILED_AFTER_ENTRY"), state="FAILED_AFTER_ENTRY")
        else:
            append_event(events, "SCIENTIFIC_PERSISTENCE_ERROR" if lifecycle.phase != "CONTROL_PLANE_DEGRADED" else "CONTROL_PLANE_DEGRADED", error=repr(exc), cleanup="PRESERVED_AFTER_ENTRY"); atomic_json(root / "failure.json", {"status": "FAIL", "state": "PENDING_RECONCILE", "error": repr(exc), "timestamp": utc_now()})
            lifecycle.control_plane("release_pending", lambda: alloc.release_pending(lease, repr(exc)), state="PENDING_RECONCILE")
        return 1
    finally:
        stop.set()
        if fd is not None and lifecycle.can_close(): lifecycle.close(fd, "SCIENTIFIC_TERMINAL_OR_TRUTH_DURABLE")
        elif fd is not None: append_event(events, "CONTROL_PLANE_DEGRADED", cleanup="FD_CLOSE_DEFERRED_AFTER_ENTRY")


def log_state(root):
    logs = list((root / "native").glob("*_p0.log")) + list((root / "native").glob("*.log"))
    if not logs: return {}
    p = max(logs, key=lambda x: x.stat().st_mtime); lines = p.read_text(errors="replace").splitlines(); progress = [x for x in lines if "% complete" in x]
    return {"path": str(p), "size": p.stat().st_size, "mtime": p.stat().st_mtime, "progress": progress[-1] if progress else None}


if __name__ == "__main__": raise SystemExit(main())
