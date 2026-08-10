from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
import traceback


ROOT = pathlib.Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
EVIDENCE = ROOT / "outputs" / "np_k6_m2_g04p_controlled_recompute_v1"
EXECUTION_ID = "G04_P_BATCH1_INFRA_RECOVERY_RECOMPUTE_V1"
LOGICAL_TASK_ID = "NP_K6_M2_BATCH1_G04_P"
ATTEMPT_ID = "attempt_001"
RUNTIME = EVIDENCE / "runtime_replacement" / EXECUTION_ID / ATTEMPT_ID
RUN_COPY = RUNTIME / f"{EXECUTION_ID}_{ATTEMPT_ID}_run.fsp"
POST = RUNTIME / f"{EXECUTION_ID}_{ATTEMPT_ID}_post.fsp"
LEDGER = EVIDENCE / "replacement_attempt_ledger.json"
EXPECTED_SHA = "db666c715fe430080f0013e1bdbb03c42286095f97c880bcf404304f5307377c"


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def process_snapshot() -> list[dict[str, object]]:
    script = (
        "$r=@();foreach($p in @(Get-Process -Name fdtd-engine,fdtd-engine-msmpi,fdtd-solutions,mpiexec -ErrorAction SilentlyContinue)){"
        "$c=Get-CimInstance Win32_Process -Filter ('ProcessId='+$p.Id);"
        "$r += [pscustomobject]@{pid=$p.Id;name=$p.ProcessName;cpu=[double]$p.CPU;parent=$c.ParentProcessId;cmd=$c.CommandLine}};"
        "$r|ConvertTo-Json -Depth 4"
    )
    result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if result.returncode:
        return [{"error": result.stderr.strip(), "returncode": result.returncode}]
    if not result.stdout.strip():
        return []
    rows = json.loads(result.stdout)
    return rows if isinstance(rows, list) else [rows]


def event(state: str, **extra: object) -> None:
    payload = {"execution_id": EXECUTION_ID, "logical_task_id": LOGICAL_TASK_ID, "attempt_id": ATTEMPT_ID, "state": state, "timestamp_utc": now(), "controller_pid": os.getpid()}
    payload.update(extra)
    with (RUNTIME / "controller_events.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    atomic(RUNTIME / "controller_status.json", payload)


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    ledger = read_json(LEDGER)
    if ledger.get("entered") is True or int(ledger.get("run_invocation_count", 0)) != 0:
        raise RuntimeError("replacement ledger already entered or consumed")
    if not RUN_COPY.exists() or sha(RUN_COPY) != EXPECTED_SHA:
        raise RuntimeError("replacement run copy missing or SHA mismatch")
    if POST.exists():
        raise RuntimeError("replacement post-FSP already exists; refusing duplicate execution")
    setup = read_json(EVIDENCE / "replacement_setup_identity.json")
    if setup.get("status") != "PASS" or setup.get("unexpected_physical_differences") != []:
        raise RuntimeError("replacement setup identity preflight is not PASS")
    processes = process_snapshot()
    active = [row for row in processes if row.get("name") in {"fdtd-engine", "fdtd-engine-msmpi", "fdtd-solutions", "mpiexec"}]
    if active:
        raise RuntimeError(f"active Ansys process before replacement entered: {active}")
    ledger.update({"controller_started": True, "controller_started_timestamp_utc": now(), "controller_pid": os.getpid(), "run_copy_path": str(RUN_COPY), "run_copy_sha256": sha(RUN_COPY)})
    atomic(LEDGER, ledger)
    event("controller_started", run_copy_sha256=sha(RUN_COPY))
    os.environ["AWP_LOCALE251"] = "en-us"
    sys.path.insert(0, r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
    import lumapi

    fd = None
    solver_calls = 0
    try:
        fd = lumapi.FDTD(str(RUN_COPY), hide=True)
        ledger.update({"prefsp_opened": True, "prefsp_opened_timestamp_utc": now()})
        atomic(LEDGER, ledger)
        event("prefsp_opened")
        latest = read_json(LEDGER)
        if latest.get("entered") is True or int(latest.get("run_invocation_count", 0)) != 0:
            raise RuntimeError("ledger changed before solver entry")
        # Atomic budget transition immediately before the sole solver call.
        solver_calls = 1
        latest.update({"entered": True, "solver_entered": True, "solver_authorized": True, "run_invocation_count": 1, "solver_entered_timestamp_utc": now(), "entered_timestamp_utc": now(), "run_called": True})
        atomic(LEDGER, latest)
        event("solver_entered", run_invocation_count=1)
        fd.run()
        latest.update({"engine_completed": True, "engine_completed_timestamp_utc": now(), "engine_exit_code": 0})
        atomic(LEDGER, latest)
        event("engine_completed")
        fd.save(str(POST))
        previous_size = -1
        stable = False
        for _ in range(900):
            if POST.exists() and POST.stat().st_size > 0:
                size = POST.stat().st_size
                if size == previous_size:
                    stable = True
                    break
                previous_size = size
            time.sleep(1)
        if not stable:
            raise RuntimeError("post-FSP did not stabilize")
        post_sha = sha(POST)
        latest.update({"post_saved": True, "post_save_completed": True, "post_fsp_path": str(POST), "post_fsp_sha256": post_sha, "post_fsp_size_bytes": POST.stat().st_size, "post_saved_timestamp_utc": now()})
        atomic(LEDGER, latest)
        atomic(EVIDENCE / "replacement_post_fsp_manifest.json", {"status": "PASS", "execution_id": EXECUTION_ID, "logical_task_id": LOGICAL_TASK_ID, "attempt_id": ATTEMPT_ID, "post_fsp_path": str(POST), "post_fsp_sha256": post_sha, "post_fsp_size_bytes": POST.stat().st_size, "captured_utc": now()})
        atomic(EVIDENCE / "checksum_manifest.json", {"source_prefsp_sha256": EXPECTED_SHA, "replacement_run_copy_sha256": sha(RUN_COPY), "replacement_post_fsp_sha256": post_sha, "post_fsp_size_bytes": POST.stat().st_size, "captured_utc": now()})
        event("post_fsp_saved", post_fsp_sha256=post_sha, post_fsp_size_bytes=POST.stat().st_size)
    except Exception as exc:
        latest = read_json(LEDGER)
        latest.update({"failure": repr(exc), "failure_timestamp_utc": now(), "solver_calls_in_controller": solver_calls})
        atomic(LEDGER, latest)
        event("controller_failed", error=repr(exc), solver_calls=solver_calls)
        raise
    finally:
        if fd is not None:
            fd.close()
    latest = read_json(LEDGER)
    if latest.get("post_saved") is True:
        latest.update({"controller_returned": True, "controller_returned_timestamp_utc": now()})
        atomic(LEDGER, latest)
        event("controller_returned")
    atomic(EVIDENCE / "replacement_execution_manifest.json", latest)
    atomic(EVIDENCE / "solver_invocation_audit.json", {"original_g04p_run_invocations": 1, "replacement_run_invocations": solver_calls, "total_g04p_invocations": 1 + solver_calls, "batch1_physical_invocations_before_replacement": 12, "batch1_physical_invocations_authorized_maximum": 13, "attempt_002": 0, "second_replacement": 0, "sealed_access": 0, "training_started": 0, "captured_utc": now()})


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
