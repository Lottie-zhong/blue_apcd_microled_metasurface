import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

ML = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
PRE = ML / r"outputs\coupling_ml\M0_LEVEL1_LEVEL2_CONTRACT_RECONCILIATION_V1\M0F_MINIMAL_LEVEL1_CONTRACT_REPAIR_ACQUISITION\DIRECT_MDC_HF\preflight"
CONT = ML / r"outputs\coupling_ml\M0_LEVEL1_LEVEL2_CONTRACT_RECONCILIATION_V1\M0F_MINIMAL_LEVEL1_CONTRACT_REPAIR_ACQUISITION\M0F_CONTINUATION_AFTER_COMPONENT_RULING_V1"
RUNNER = ML / r"scripts\coupling_ml\m0f_remaining_direct_mdc_runner_v1.py"
spec = importlib.util.spec_from_file_location("remaining_runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def pending():
    rows = []
    for path in sorted(PRE.glob("MDC_*__PRE_RUN_MANIFEST_V1.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("pilot") is False and data.get("solver_entered") is False:
            case_dir = Path(data["output_root"])
            if not (case_dir / "M0F_DIRECT_MDC_SOLVER_ENTRY_V1.json").exists():
                rows.append((data["case_id"], path))
    return rows


def append_batch(record):
    target = CONT / "M0F_RESOURCE_AWARE_BATCH_ADMISSION_V1.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + chr(10))


def main():
    completed_batches = 0
    while True:
        todo = pending()
        if not todo:
            print(json.dumps({"status": "NO_PENDING_CASES", "completed_batches": completed_batches}), flush=True)
            return 0
        snap = runner.resource_snapshot(admitted_fdtd_slots=0)
        safe = int(snap.get("safe_new_slots", 0))
        if safe < 1:
            print(json.dumps({"status": "WAITING_FOR_RESOURCE_HEADROOM", "snapshot": snap}, ensure_ascii=False), flush=True)
            time.sleep(30)
            continue
        batch = todo[:min(safe, len(todo))]
        batch_id = "batch_%02d_%d" % (completed_batches + 1, int(time.time()))
        admission = {
            "schema_version": "M0F_RESOURCE_AWARE_BATCH_ADMISSION_V1",
            "batch_id": batch_id,
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "fluent_detected": snap["fluent_detected"],
            "fluent_process_count": snap["fluent_process_count"],
            "system_logical_cpu": snap["system_logical_cpu"],
            "available_memory_before_admission": snap["available_memory_before_admission"],
            "active_apcd_fdtd_slots_before_admission": snap["active_apcd_fdtd_slots_before_admission"],
            "resource_safe_fdtd_slots": safe,
            "admitted_fdtd_slots": len(batch),
            "case_ids": [case_id for case_id, _ in batch],
            "production_hard_cap": 3,
            "fluent_protection": snap["fluent_protection"],
        }
        append_batch(admission)
        print(json.dumps({"status": "BATCH_ADMITTED", "admission": admission}, ensure_ascii=False), flush=True)
        processes = [
            (
                case_id,
                subprocess.Popen(
                    [sys.executable, str(RUNNER), "--manifest", str(manifest)],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                ),
            )
            for case_id, manifest in batch
        ]
        failures = []
        for case_id, process in processes:
            output, _ = process.communicate()
            print(json.dumps({"case_id": case_id, "returncode": process.returncode, "output_tail": output[-5000:]}, ensure_ascii=False), flush=True)
            if process.returncode:
                failures.append({"case_id": case_id, "returncode": process.returncode, "output_tail": output[-5000:]})
        if failures:
            print(json.dumps({"status": "BATCH_FAILURE_STOPPED", "failures": failures}, ensure_ascii=False), flush=True)
            return 2
        completed_batches += 1


if __name__ == "__main__":
    raise SystemExit(main())
