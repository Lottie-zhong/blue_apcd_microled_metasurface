"""Strictly serial Scheduler supervisor for M4 Primary4 acquisition."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from np_k6_m4_batch2_primary4_worker_launcher_v1 import build_environment


ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / r"outputs\np_k6_m4_batch2_primary4_hf_acquisition_v1"
PYTHON = r"N:\anaconda_envs\RCP_LCP\python.exe"
RUNNER = ROOT / r"scripts\np_k6_m4_batch2_primary4_runner_v1.py"
LAUNCHER = ROOT / r"scripts\np_k6_m4_batch2_primary4_worker_launcher_v1.py"
EXTRACTOR = ROOT / r"scripts\np_k6_m4_batch2_primary4_extractor_v1.py"
ORDER = [f"NP_K6_M4_B2_G{slot:02d}_{pol}" for slot in range(1, 5) for pol in ("P", "S")]
STATE = OUT / "batch2_supervisor_state.json"
EXECUTION_LEDGER = OUT / "batch2_execution_ledger.json"
LOG = OUT / "batch2_supervisor.log"


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


def log(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"{now()} {message}\n")


def process_snapshot() -> list[dict]:
    ps = "Get-CimInstance Win32_Process | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"
    p = subprocess.run(["powershell", "-NoProfile", "-Command", ps], text=True, capture_output=True)
    try:
        rows = json.loads(p.stdout) if p.stdout.strip() else []
    except Exception:
        rows = []
    if isinstance(rows, dict): rows = [rows]
    return [{"ProcessId": row.get("ProcessId"), "Name": row.get("Name"), "CommandLine": row.get("CommandLine")} for row in rows if "fdtd-engine" in str(row).lower() or "mpiexec" in str(row).lower()]


def task_name(case_id: str) -> str:
    return rf"\APCD\NP\NP_K6_M4_B2_{case_id}_001"


def task_query(name: str) -> tuple[int, str]:
    p = subprocess.run(["schtasks.exe", "/Query", "/TN", name, "/FO", "LIST", "/V"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout


def task_running(name: str) -> bool:
    rc, text = task_query(name)
    return rc == 0 and ("Running" in text or "正在运行" in text)


def create_and_run_task(case_id: str) -> str:
    name = task_name(case_id)
    rc, text = task_query(name)
    if rc == 0:
        # A scheduler launch may fail before LumAPI opens and before the
        # atomic entered transition.  In that narrow, explicitly recorded
        # case we may relaunch the same attempt_001 task after a zero-solver
        # messaging smoke.  This is not a solver retry or a new attempt.
        case_dir, existing = load_case(case_id)
        if task_running(name):
            raise RuntimeError(f"scheduler task is still running for {case_id}: {name}")
        if not (existing.get("pre_entry_retry_authorized")
                and not existing.get("entered")
                and int(existing.get("run_invocation_count", 0)) == 0
                and not existing.get("post_saved")):
            raise RuntimeError(f"scheduler task already exists without pre-entry recovery authorization: {name}: {text[-1000:]}")
        run = subprocess.run(["schtasks.exe", "/Run", "/TN", name], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if run.returncode:
            raise RuntimeError(f"scheduler recovery run failed: {run.stdout}")
        log(f"re-launched pre-entry failed {case_id} same attempt_001 task={name}")
        return name
    start = datetime.now() + __import__("datetime").timedelta(minutes=1)
    # Keep the Scheduler /TR command below the Windows command-line length
    # limit; the launcher derives the canonical task name from case_id.
    command = f'"{PYTHON}" "{LAUNCHER}" --case {case_id}'
    create = subprocess.run(["schtasks.exe", "/Create", "/TN", name, "/TR", command, "/SC", "ONCE", "/SD", start.strftime("%Y/%m/%d"), "/ST", start.strftime("%H:%M"), "/RU", "SYSTEM", "/RL", "HIGHEST", "/F"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if create.returncode:
        raise RuntimeError(f"scheduler create failed: {create.stdout}")
    run = subprocess.run(["schtasks.exe", "/Run", "/TN", name], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if run.returncode:
        raise RuntimeError(f"scheduler run failed: {run.stdout}")
    log(f"scheduled and started {case_id} task={name}")
    return name


def load_case(case_id: str) -> tuple[Path, dict]:
    case_dir = OUT / "cases" / case_id
    return case_dir, read_json(case_dir / "attempt_ledger.json")


def update_execution(records: list[dict], state: dict) -> None:
    atomic(EXECUTION_LEDGER, {"schema_version": "np_k6_m4_batch2_execution_ledger_v1", "logical_case_count": 8, "records": records, "solver_run_invocations_total": sum(int(r.get("run_invocation_count", 0)) for r in records), "accepted_case_count": sum(1 for r in records if r.get("status") == "accepted"), "infrastructure_lost_count": sum(1 for r in records if r.get("status") == "infrastructure_lost"), "replacement_count": sum(int(r.get("replacement_count", 0)) for r in records), "sealed_target_reads": 0, "first6_first8_entered": False, "m5_training_started": False, "updated_timestamp_utc": now()})
    atomic(STATE, state)


def upsert_record(records: list[dict], record: dict) -> None:
    for index, existing in enumerate(records):
        if existing.get("case_id") == record.get("case_id"):
            records[index] = record
            return
    records.append(record)


def recover_stable_post(case_dir: Path, ledger: dict, run_dir: Path) -> bool:
    post = Path(ledger.get("post_fsp_path", ""))
    if not post.exists() or post.stat().st_size <= 0 or not ledger.get("engine_completed"):
        return False
    size1 = post.stat().st_size; time.sleep(10); size2 = post.stat().st_size
    if size1 != size2:
        return False
    post_sha = sha256(post)
    ledger.update({"status": "post_persisted", "post_saved": True, "post_save_completed": True, "post_fsp_sha256": post_sha, "post_fsp_size_bytes": size2, "post_save_recovered_by_existing_stable_post": True, "post_recovered_timestamp_utc": now()})
    atomic(case_dir / "attempt_ledger.json", ledger); atomic(run_dir / "entered_ledger.json", ledger)
    log(f"recovered existing stable post for {ledger['case_id']} sha={post_sha}")
    return True


def extract(case_id: str) -> dict:
    result = subprocess.run([PYTHON, str(EXTRACTOR), "--case", case_id], cwd=str(ROOT), env=build_environment(), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (OUT / "cases" / case_id / "extractor_stdout.log").write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"extractor failed for {case_id}: {result.stdout[-4000:]}")
    manifest = read_json(OUT / "cases" / case_id / "extraction_manifest.json")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--supervisor-task-name", default="")
    args = parser.parse_args()
    manifest = read_json(OUT / "batch2_setup_manifest.json")
    if manifest.get("case_count") != 8 or manifest.get("solver_entered") != 0:
        raise RuntimeError("setup manifest is not exact eight-case zero state")
    records = []
    state = {"schema_version": "np_k6_m4_batch2_supervisor_state_v1", "status": "running", "order": ORDER, "current_case": None, "supervisor_task_name": args.supervisor_task_name, "started_timestamp_utc": now(), "completed_cases": [], "errors": []}
    update_execution(records, state)
    try:
        for case_id in ORDER:
            case_dir, ledger = load_case(case_id)
            record = {"case_id": case_id, "attempt_id": "attempt_001", "geometry_id": ledger.get("geometry_id"), "geometry_hash": ledger.get("geometry_hash"), "polarization": ledger.get("polarization"), "role": ledger.get("role"), "task_name": task_name(case_id), "status": ledger.get("status", "planned"), "run_invocation_count": int(ledger.get("run_invocation_count", 0)), "entered": bool(ledger.get("entered")), "replacement_count": 0}
            state["current_case"] = case_id
            upsert_record(records, record)
            update_execution(records, state)
            if record["entered"] and record["run_invocation_count"] == 1:
                log(f"resuming existing entered case {case_id}")
                task = record["task_name"]
            elif record["run_invocation_count"] == 0:
                if process_snapshot():
                    raise RuntimeError("active fdtd-engine/mpiexec detected before new case; no task created")
                source = Path(ledger["source_prefsp_path"])
                preflight = {"case_id": case_id, "attempt_id": "attempt_001", "source_prefsp_sha256": ledger["source_prefsp_sha256"], "source_sha256_actual": sha256(source), "setup_diff_pass": read_json(case_dir / "setup_readback_audit.json").get("setup_diff_pass"), "entered_before": ledger.get("entered"), "run_invocation_count_before": ledger.get("run_invocation_count"), "active_heavy_processes": process_snapshot(), "task_name": record["task_name"], "preflight_pass": source.exists() and sha256(source) == ledger["source_prefsp_sha256"] and read_json(case_dir / "setup_readback_audit.json").get("setup_diff_pass") and not process_snapshot()}
                atomic(case_dir / "preflight_case_audit.json", preflight)
                if not preflight["preflight_pass"]:
                    raise RuntimeError(f"case preflight failed: {preflight}")
                task = create_and_run_task(case_id)
                record.update({"status": "scheduled", "task_name": task, "scheduled_timestamp_utc": now()})
                upsert_record(records, record)
                update_execution(records, state)
            else:
                raise RuntimeError(f"invalid ledger for {case_id}: {ledger}")
            run_dir = OUT / "runtime_runs" / case_id / "attempt_001"
            while True:
                _, current = load_case(case_id)
                record.update({"status": current.get("status"), "entered": bool(current.get("entered")), "run_invocation_count": int(current.get("run_invocation_count", 0)), "engine_completed": bool(current.get("engine_completed")), "post_saved": bool(current.get("post_saved")), "controller_returned": bool(current.get("controller_returned"))})
                upsert_record(records, record); update_execution(records, state)
                if current.get("failure") and not current.get("post_saved"):
                    raise RuntimeError(f"case failure {case_id}: {current.get('failure')}")
                if current.get("engine_completed") and not current.get("post_saved"):
                    recover_stable_post(case_dir, current, run_dir)
                    _, current = load_case(case_id)
                if current.get("engine_completed") and current.get("post_saved"):
                    if not current.get("controller_returned"):
                        current.update({"controller_returned": True, "status": "controller_returned_recovered", "controller_returned_recovered_timestamp_utc": now()})
                        atomic(case_dir / "attempt_ledger.json", current); atomic(run_dir / "entered_ledger.json", current)
                    manifest_case = extract(case_id)
                    if not manifest_case.get("quality_gate_pass"):
                        record.update({"status": "rejected", "quality_gate_pass": False, "extraction_manifest": manifest_case})
                        upsert_record(records, record); update_execution(records, state)
                        raise RuntimeError(f"quality gate failed for {case_id}: {manifest_case}")
                    record.update({"status": "accepted", "quality_gate_pass": True, "post_fsp_sha256": manifest_case.get("post_fsp_sha256"), "max_abs_closure_residual": manifest_case.get("max_abs_closure_residual"), "structure_interval_anomaly_max": manifest_case.get("structure_interval_anomaly_max"), "order_sum_mismatch_max": manifest_case.get("order_sum_mismatch_max"), "direct_raw_sourcepower_mismatch_max": manifest_case.get("direct_raw_sourcepower_mismatch_max")})
                    upsert_record(records, record); state["completed_cases"] = [r["case_id"] for r in records if r.get("status") == "accepted"]; update_execution(records, state)
                    log(f"accepted {case_id} post={record.get('post_fsp_sha256')}")
                    break
                if current.get("entered") and not current.get("engine_completed") and not task_running(task):
                    raise RuntimeError(f"entered case stopped before engine completion: {case_id}")
                if not current.get("entered") and not task_running(task):
                    raise RuntimeError(f"case scheduler stopped before solver entry: {case_id}")
                time.sleep(30)
        state.update({"status": "NP_K6_M4_BATCH2_PRIMARY4_HF_ACQUISITION_COMPLETE_M5_RETRAIN_READY", "current_case": None, "finished_timestamp_utc": now(), "accepted_case_count": 8, "formal_new_row_count": 88, "first6_first8_entered": False, "m5_training_started": False})
        update_execution(records, state)
    except Exception as exc:
        state.update({"status": "STOPPED_ON_CASE_FAILURE_OR_RECOVERY_REQUIRED", "error": repr(exc), "finished_timestamp_utc": now()})
        update_execution(records, state)
        log(f"STOPPED {exc!r}")
        raise


if __name__ == "__main__":
    main()
