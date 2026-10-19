"""Server-owned two-slot continuation for the frozen W2V Stage-1 queue."""
from __future__ import annotations

import csv
import importlib.util
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path

PIPELINE_PATH = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\scripts\coupling_ml\apcd_coupling_v3a_w2v_pipeline_v1.py")
OUT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\APCD_COUPLING_V3A_W2V_WIDEBAND_BUILDER_RECONSTRUCTION_VALIDATION_AND_STAGE1_RESUME_V1")
W2U = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\APCD_COUPLING_V3A_W2U_NESTED_N24_QUEUE_STAGE1_N12_WIDEBAND_ACQUISITION_V1")
ROOT = OUT / "SERVER_CONTROLLER_TWO_SLOT"
MAX_WORKERS = 2


def load_pipeline():
    spec = importlib.util.spec_from_file_location("w2v_pipeline_server", PIPELINE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PIPELINE = load_pipeline()
_write_lock = threading.Lock()


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def append_event(state: str, **extra) -> None:
    record = {"timestamp": now(), "controller_pid": os.getpid(), "state": state, **extra}
    path = ROOT / "controller_events.jsonl"
    with _write_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def write_state(payload: dict) -> None:
    path = ROOT / "CONTROLLER_STATE.json"
    temp = path.with_suffix(".tmp")
    with _write_lock:
        with temp.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)


def queue_entries() -> list[dict]:
    queue = json.loads((W2U / "FINAL_NESTED_N24_ACQUISITION_QUEUE.json").read_text(encoding="utf-8"))
    return [row for row in queue["queue"] if 5 <= int(row.get("queue_index", 0)) <= 12]


def run_one(row: dict) -> dict:
    case = str(row["geometry_id"])
    case_root = OUT / "STAGE1" / case
    if case_root.exists() and any(case_root.iterdir()):
        events = case_root / "events.jsonl"
        text = events.read_text(encoding="utf-8", errors="replace") if events.exists() else ""
        if "COMPLETED" in text and "SLOT_RELEASED" in text and (case_root / "completion.json").is_file():
            return {"geometry_id": case, "result": "ALREADY_COMPLETED_NO_RERUN", "solver_rerun": False}
        return {"geometry_id": case, "result": "EXISTING_PARTIAL_NO_RERUN", "solver_rerun": False}
    geometry = [float(row[f"D{i}_nm"]) for i in range(1, 7)]
    result = PIPELINE.run_case(case, geometry, row["stage1_role"], case_root, "STAGE1", None)
    return {
        "geometry_id": case,
        "role": row["stage1_role"],
        "job_id": result.get("job_id"),
        "attempt_id": result.get("attempt_id"),
        "solver_entered": result.get("solver_entered"),
        "solver_returned": result.get("solver_returned"),
        "rerun_delta": 0,
        "post_fsp": result.get("post_fsp"),
        "post_sha256": result.get("post_fsp_sha256"),
        "raw": result.get("raw"),
        "raw_sha256": result.get("raw_sha256"),
        "load_only": result.get("load_only_validation", {}).get("ok"),
        "completion": result.get("status"),
        "slot_release_state": result.get("state"),
        "result": "PASS" if result.get("status") == "COMPLETED" and result.get("state") == "SLOT_RELEASED" else "FAIL",
        "solver_rerun": False,
    }


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    entries = queue_entries()
    append_event("CONTROLLER_STARTED", queue_indices=[int(row["queue_index"]) for row in entries], max_workers=MAX_WORKERS, no_rerun=True)
    completed: list[dict] = []
    failed: list[dict] = []
    write_state({"status": "RUNNING", "max_workers": MAX_WORKERS, "queue_indices": [int(row["queue_index"]) for row in entries], "completed": [], "failed": []})
    for offset in range(0, len(entries), MAX_WORKERS):
        wave = entries[offset : offset + MAX_WORKERS]
        cases = [str(row["geometry_id"]) for row in wave]
        append_event("WAVE_STARTED", queue_indices=[int(row["queue_index"]) for row in wave], cases=cases)
        with ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="w2v-stage1") as pool:
            futures = {pool.submit(run_one, row): row for row in wave}
            pending = set(futures)
            while pending:
                done, pending = wait(pending, timeout=60)
                if not done:
                    append_event("HEARTBEAT", active_cases=[str(futures[future]["geometry_id"]) for future in pending])
                    write_state({"status": "RUNNING", "max_workers": MAX_WORKERS, "active": [str(futures[future]["geometry_id"]) for future in pending], "completed": completed, "failed": failed})
                    continue
                for future in done:
                    row = futures[future]
                    case = str(row["geometry_id"])
                    try:
                        result = future.result()
                    except Exception as exc:
                        result = {"geometry_id": case, "queue_index": int(row["queue_index"]), "result": "CONTROLLER_OR_JOB_FAILURE", "error": repr(exc), "solver_rerun": False}
                    result["queue_index"] = int(row["queue_index"])
                    result["role"] = row["stage1_role"]
                    if result.get("result") == "PASS" or result.get("result") == "ALREADY_COMPLETED_NO_RERUN":
                        completed.append(result)
                        append_event("CASE_COMPLETED", case=case, result=result)
                    else:
                        failed.append(result)
                        append_event("CASE_FAILED", case=case, result=result)
                    write_state({"status": "RUNNING", "max_workers": MAX_WORKERS, "active": [str(futures[item]["geometry_id"]) for item in pending], "completed": completed, "failed": failed})
        append_event("WAVE_FINISHED", cases=cases)
    rows = completed + failed
    with (ROOT / "STAGE1_TWO_SLOT_RUN_LEDGER.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["queue_index", "geometry_id", "role", "job_id", "attempt_id", "solver_entered", "solver_returned", "rerun_delta", "post_fsp", "post_sha256", "raw", "raw_sha256", "load_only", "completion", "slot_release_state", "result", "solver_rerun", "error"]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
    summary = {"schema_version": "APCD_W2V_SERVER_CONTROLLER_TWO_SLOT_V1", "status": "PASS" if len(completed) == len(entries) else "PARTIAL", "max_workers": MAX_WORKERS, "requested_queue_indices": [int(row["queue_index"]) for row in entries], "completed_count": len(completed), "failed_count": len(failed), "solver_rerun_delta": 0, "parallel_waves": [[int(row["queue_index"]) for row in entries[i : i + MAX_WORKERS]] for i in range(0, len(entries), MAX_WORKERS)], "completed": completed, "failed": failed, "no_q1_q4_rerun": True, "training": False, "active_learning": False, "inverse_design": False}
    write_state(summary)
    (ROOT / "SERVER_CONTROLLER_SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_event("CONTROLLER_COMPLETED", status=summary["status"], completed_count=len(completed), failed_count=len(failed), solver_rerun_delta=0)
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
