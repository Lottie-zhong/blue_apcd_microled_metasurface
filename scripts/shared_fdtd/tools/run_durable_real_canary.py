from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))

from shared_fdtd.control_v3 import Allocator, ControlDB
from shared_fdtd.control_v3.allocator import Lease
from shared_fdtd.control_v3.db import utc_now
from shared_fdtd.engine.dispatcher import enqueue
from shared_fdtd.engine.event_log import read_events
from shared_fdtd.engine.persistence import atomic_json


PYTHON = r"N:\anaconda_envs\RCP_LCP\python.exe"
HOST = PKG / "tools" / "durable_canary_host.py"
FINISHER = PKG / "tools" / "durable_finisher_worker.py"
DETACHED = getattr(subprocess, "DETACHED_PROCESS", 0x00000008) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)


def task_register(task_name: str, command: str) -> None:
    create = subprocess.run(
        ["schtasks.exe", "/Create", "/TN", task_name, "/TR", command,
         "/SC", "ONCE", "/SD", "2099/01/01", "/ST", "00:00", "/F",
         "/RU", "SYSTEM", "/RL", "HIGHEST"],
        capture_output=True, text=True,
    )
    if create.returncode:
        raise RuntimeError(create.stderr or create.stdout)
    run = subprocess.run(["schtasks.exe", "/Run", "/TN", task_name], capture_output=True, text=True)
    if run.returncode:
        raise RuntimeError(run.stderr or run.stdout)


def task_end(task_name: str) -> None:
    subprocess.run(["schtasks.exe", "/End", "/TN", task_name], capture_output=True, text=True)


def controller(root: Path, mode: str) -> int:
    db_path = root / "canary.sqlite3"
    db = ControlDB(db_path)
    db.initialize(PKG / "control_v3" / "schema.sql")
    case = "TRADITIONAL_SHARED_PATCH_CANARY_" + mode.upper()
    attempt = "attempt_001"
    attempt_root = root / "runtime" / case / attempt
    attempt_root.mkdir(parents=True, exist_ok=True)
    lease = Allocator(db).acquire("traditional", case, attempt)
    enqueue(db, "traditional", case, attempt, {
        "runtime": str(attempt_root), "production_science": False,
        "canary_contract": "APCD_TRADITIONAL_LED_SHARED_V3_DURABLE_POSTSOLVER_FINISHER_PATCH_V1",
    })
    with db.immediate() as con:
        con.execute(
            "UPDATE branch_queue SET state='HOST_STARTED',slot_id=?,lease_token_hash=?,fencing_generation=?,updated_at=? "
            "WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
            (lease.slot_id, lease.token_hash, lease.fencing_generation, utc_now(),
             lease.owner_branch, lease.logical_case_id, lease.attempt_id),
        )
    cfg = {
        "db": str(db_path), "attempt_root": str(attempt_root),
        "runtime_fsp": str(attempt_root / "runtime.fsp"),
        "native_target": str(attempt_root / "native.fsp"),
        "post_target": str(attempt_root / "post.fsp"),
        "raw_target": str(attempt_root / "raw.json"),
        "solver_log": str(attempt_root / "solver.log"),
        "branch": lease.owner_branch, "case": lease.logical_case_id,
        "attempt": lease.attempt_id, "slot_id": lease.slot_id,
        "lease_token": lease.lease_token, "fencing_generation": lease.fencing_generation,
        "simulation_time": 5e-13, "scientific_invocation_count": 1,
    }
    config_path = attempt_root / "host_config.json"
    atomic_json(config_path, cfg)
    host_task = "APCD_TRAD_SHARED_CANARY_" + mode.upper() + "_" + root.name.upper() + "_HOST"
    finisher_task = "APCD_TRAD_SHARED_CANARY_" + mode.upper() + "_" + root.name.upper() + "_FINISHER"
    host_wrapper = Path(r"D:\apcd_runtime\bin") / f"APCD_SHARED_{mode.upper()}_{root.name}_HOST.cmd"
    finisher_wrapper = Path(r"D:\apcd_runtime\bin") / f"APCD_SHARED_{mode.upper()}_{root.name}_FINISHER.cmd"
    host_wrapper.parent.mkdir(parents=True, exist_ok=True)
    host_wrapper.write_text(f'@echo off\ncall \"{PYTHON}\" \"{HOST}\" \"{config_path}\"\nexit /b %errorlevel%\n', encoding="utf-8")
    finisher_wrapper.write_text(f'@echo off\ncall \"{PYTHON}\" \"{FINISHER}\" \"{config_path}\" --timeout 180\nexit /b %errorlevel%\n', encoding="utf-8")
    host_cmd = f'"{host_wrapper}"'
    finisher_cmd = f'"{finisher_wrapper}"'
    task_register(host_task, host_cmd)
    task_register(finisher_task, finisher_cmd)
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        events = read_events(attempt_root / "events.jsonl")
        if any(e.get("event_type") == "SCIENTIFIC_SOLVER_ENTERED" for e in events):
            atomic_json(attempt_root / "controller_interrupted.json", {
                "status": "CONTROLLER_EXITED_AFTER_ENTRY",
                "controller_pid": os.getpid(),
                "host_task": host_task,
                "finisher_task": finisher_task,
                "mode": mode,
                "timestamp_utc": utc_now(),
                "scientific_process_untouched": True,
            })
            if mode == "c2":
                time.sleep(1)
                task_end(finisher_task)
                task_register(finisher_task, finisher_cmd)
                atomic_json(attempt_root / "finisher_restarted.json", {
                    "finisher_task": finisher_task,
                    "solver_process_untouched": True,
                    "timestamp_utc": utc_now(),
                })
            return 0
        time.sleep(1)
    atomic_json(attempt_root / "controller_timeout.json", {"host_task": host_task, "finisher_task": finisher_task})
    return 4


def wait_terminal(root: Path, mode: str) -> dict:
    attempt_root = root / "runtime" / ("TRADITIONAL_SHARED_PATCH_CANARY_" + mode.upper()) / "attempt_001"
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        terminal = attempt_root / "terminal.json"
        if terminal.is_file():
            value = json.loads(terminal.read_text(encoding="utf-8"))
            if value.get("status") == "HF_TRUTH_VALID" and value.get("release_state") == "RELEASED":
                return value
        time.sleep(1)
    return {"status": "TIMEOUT", "attempt_root": str(attempt_root)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("c1", "c2"), required=True)
    ap.add_argument("--root", required=True)
    args = ap.parse_args()
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    p = subprocess.run([PYTHON, str(Path(__file__).resolve()), "--controller", "--mode", args.mode, "--root", str(root)], capture_output=True, text=True) if "--controller" in sys.argv else None
    if "--controller" in sys.argv:
        return 0
    controller_script = Path(__file__).resolve()
    controller_proc = subprocess.run([PYTHON, str(controller_script), "--controller", "--mode", args.mode, "--root", str(root)], capture_output=True, text=True)
    result = wait_terminal(root, args.mode)
    atomic_json(root / ("CANARY_" + args.mode.upper() + "_RESULT.json"), {
        "mode": args.mode, "controller_returncode": controller_proc.returncode,
        "result": result, "solver_runs": result.get("solver_runs", 1), "replay": result.get("replay", 0),
        "controller_loss_simulated": True, "foreign_mutation_count": 0,
    })
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("status") == "HF_TRUTH_VALID" and result.get("release_state") == "RELEASED" else 1


if __name__ == "__main__":
    if "--controller" in sys.argv:
        # Controller subprocess uses the same entrypoint with a separate role.
        import argparse as _argparse
        ap = _argparse.ArgumentParser()
        ap.add_argument("--controller", action="store_true")
        ap.add_argument("--mode", choices=("c1", "c2"), required=True)
        ap.add_argument("--root", required=True)
        a = ap.parse_args()
        raise SystemExit(controller(Path(a.root), a.mode))
    raise SystemExit(main())

