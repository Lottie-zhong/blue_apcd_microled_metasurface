"""One-shot persistent controller for one M4 Primary4 P/S case.

The controller has exactly one solver call site.  It updates the entered ledger
atomically immediately before that call and never retries or creates another
attempt.  It is launched by a case-specific Windows Task Scheduler task.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, r"N:/Program Files/ANSYS Inc/v251/Lumerical/api/python")
import lumapi  # type: ignore


ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / r"outputs\np_k6_m4_batch2_primary4_hf_acquisition_v1"
PYTHON = r"N:\anaconda_envs\RCP_LCP\python.exe"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


class Heartbeat:
    def __init__(self, path: Path, case_id: str, attempt_id: str) -> None:
        self.path = path
        self.case_id = case_id
        self.attempt_id = attempt_id
        self.started = time.time()
        self.stop_flag = threading.Event()
        self.thread: threading.Thread | None = None
        self.state = "controller_started"

    def write(self, **extra) -> None:
        atomic(self.path, {"case_id": self.case_id, "attempt_id": self.attempt_id, "controller_pid": os.getpid(), "heartbeat_utc": now(), "elapsed_s": time.time() - self.started, "state": self.state, **extra})

    def loop(self) -> None:
        while not self.stop_flag.is_set():
            self.write()
            self.stop_flag.wait(10)

    def start(self) -> None:
        self.write()
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def set_state(self, state: str, **extra) -> None:
        self.state = state
        self.write(**extra)

    def stop(self, state: str, **extra) -> None:
        self.state = state
        self.stop_flag.set()
        self.write(**extra)
        if self.thread:
            self.thread.join(timeout=3)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--task-name", default="")
    args = parser.parse_args()
    case_id = args.case
    case_dir = OUT / "cases" / case_id
    ledger_path = case_dir / "attempt_ledger.json"
    contract_path = case_dir / "setup_contract.json"
    run_dir = OUT / "runtime_runs" / case_id / "attempt_001"
    run_ledger_path = run_dir / "entered_ledger.json"
    status_path = run_dir / "controller_status.json"
    events_path = run_dir / "controller_events.jsonl"
    heartbeat_path = run_dir / "heartbeat.json"
    contract = read_json(contract_path)
    ledger = read_json(ledger_path)
    source = Path(contract["source_prefsp_path"])
    run_copy = run_dir / f"{case_id}_attempt_001_run.fsp"
    post = run_dir / f"{case_id}_attempt_001_post.fsp"

    def save_ledger() -> None:
        atomic(ledger_path, ledger)
        atomic(run_ledger_path, ledger)

    def event(state: str, **extra) -> None:
        record = {"case_id": case_id, "attempt_id": "attempt_001", "state": state, "timestamp_utc": now(), "controller_pid": os.getpid(), **extra}
        atomic(status_path, record)
        events_path.parent.mkdir(parents=True, exist_ok=True)
        with events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")

    def open_fdtd_with_retry() -> object:
        """Open the pre-FSP session with bounded pre-entry messaging backoff.

        This helper is strictly before the atomic entered transition below;
        a constructor failure therefore consumes zero solver invocations.
        """
        errors = []
        for init_attempt in range(1, 4):
            event("fdtd_session_requested", init_attempt=init_attempt)
            try:
                fdtd = lumapi.FDTD(str(run_copy), hide=True)
                event("fdtd_session_created", init_attempt=init_attempt)
                return fdtd
            except Exception as exc:
                errors.append({"init_attempt": init_attempt, "error": repr(exc), "timestamp_utc": now()})
                event("fdtd_session_init_failed", init_attempt=init_attempt, error=repr(exc))
                if init_attempt == 3:
                    raise RuntimeError(f"LumAPI constructor failed after bounded pre-entry retries: {errors}") from exc
                time.sleep(20 * init_attempt)
        raise AssertionError("unreachable")

    if ledger.get("case_id") != case_id or contract.get("case_id") != case_id:
        raise RuntimeError("case identity mismatch")
    if ledger.get("entered") or ledger.get("run_invocation_count", 0) != 0 or post.exists():
        raise RuntimeError("attempt_001 already consumed or post exists; refusing repeat")
    if not source.exists() or sha256(source) != contract.get("source_prefsp_sha256"):
        raise RuntimeError("source pre-FSP checksum mismatch")
    run_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, run_copy)
    run_sha = sha256(run_copy)
    if run_sha != contract["source_prefsp_sha256"]:
        raise RuntimeError("run-copy checksum mismatch")
    ledger.update({"status": "prepared", "controller_pid": os.getpid(), "task_name": args.task_name, "run_copy_path": str(run_copy), "run_copy_sha256": run_sha, "controller_started": True, "controller_started_timestamp_utc": now()})
    save_ledger()
    event("controller_started", source_prefsp_path=str(source), source_prefsp_sha256=contract["source_prefsp_sha256"], run_copy_path=str(run_copy), run_copy_sha256=run_sha, task_name=args.task_name)
    fd = None
    heartbeat = Heartbeat(heartbeat_path, case_id, "attempt_001")
    try:
        fd = open_fdtd_with_retry()
        ledger.update({"status": "prefsp_opened", "prefsp_opened": True, "prefsp_opened_timestamp_utc": now()})
        save_ledger(); event("prefsp_opened")
        heartbeat.start(); heartbeat.set_state("prefsp_opened")
        # The only solver entry.  Ledger transition is atomic and immediately
        # precedes this single call; no retry path exists below.
        ledger.update({"status": "entered", "entered": True, "run_invocation_count": 1, "solver_entered": True, "solver_entered_timestamp_utc": now(), "entered_timestamp_utc": now(), "execution_lineage": f"{case_id}/attempt_001"})
        save_ledger(); event("solver_entered", run_invocation_count=1); heartbeat.set_state("solver_entered")
        fd.run()
        ledger.update({"status": "engine_completed", "engine_completed": True, "engine_completed_timestamp_utc": now(), "engine_exit_code": 0})
        save_ledger(); event("engine_completed"); heartbeat.set_state("engine_completed")
        fd.save(str(post))
        last_size = -1
        stable_count = 0
        for _ in range(1800):
            if post.exists() and post.stat().st_size > 0:
                size = post.stat().st_size
                stable_count = stable_count + 1 if size == last_size else 0
                last_size = size
                if stable_count >= 3:
                    break
            time.sleep(1)
        if not post.exists() or stable_count < 3:
            raise RuntimeError("post-FSP did not stabilize")
        post_sha = sha256(post)
        ledger.update({"status": "post_persisted", "post_saved": True, "post_save_completed": True, "post_fsp_path": str(post), "post_fsp_sha256": post_sha, "post_fsp_size_bytes": post.stat().st_size, "post_saved_timestamp_utc": now()})
        save_ledger(); event("post_persisted", post_fsp_sha256=post_sha, post_fsp_size_bytes=post.stat().st_size); heartbeat.set_state("post_persisted", post_fsp_sha256=post_sha)
    except Exception as exc:
        ledger.update({"status": "controller_failed", "failure_type": "controller_or_persistence_failure", "failure": repr(exc), "failure_timestamp_utc": now()})
        save_ledger(); event("controller_failed", error=repr(exc)); heartbeat.stop("controller_failed", error=repr(exc))
        raise
    finally:
        if fd is not None:
            fd.close()
    if ledger.get("post_saved"):
        ledger.update({"status": "controller_returned", "controller_returned": True, "controller_returned_timestamp_utc": now()})
        save_ledger(); event("controller_returned", post_saved=True); heartbeat.stop("controller_returned")
        atomic(run_dir / "completion.json", {"case_id": case_id, "attempt_id": "attempt_001", "post_fsp_sha256": ledger["post_fsp_sha256"], "completed_utc": now()})
    print(json.dumps(ledger, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
