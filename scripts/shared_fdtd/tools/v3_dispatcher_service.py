from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
sys.path.insert(0, str(ROOT / "scripts"))
DB_PATH = Path(r"D:\apcd_runtime\global_fdtd_control_v3\control.sqlite3")
HOST_WRAPPER = r"D:\apcd_runtime\bin\v3g2h.cmd"


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def launch_factory(db_path):
    from shared_fdtd.engine.event_log import append_event
    def launch(row, lease):
        payload = json.loads(row["payload_json"])
        runtime = Path(payload["runtime"])
        runtime.mkdir(parents=True, exist_ok=True)
        config = runtime / "host_config.json"
        cfg = {
            "db": str(db_path), "runtime": str(runtime), "output_root": payload["output_root"],
            "attempt_root": payload["attempt_root"], "pre_fsp": payload["pre_fsp"],
            "pre_fsp_sha256": payload["pre_fsp_sha256"], "physical_contract_hash": payload["physical_contract_hash"],
            "branch": row["branch_id"], "case": row["logical_case_id"], "attempt": row["attempt_id"],
            "task": payload["task"], "slot_id": lease.slot_id, "lease_token": lease.lease_token,
            "fencing_generation": lease.fencing_generation, "task_name": payload["task_name"],
            "created_utc": now(),
            "production_science": bool(payload.get("production_science", False)),
            "resource_request": payload.get("resource_request"),
            "resource_class": payload.get("resource_class"),
            "estimated_peak_ram_bytes": payload.get("estimated_peak_ram_bytes"),
            "estimated_commit_bytes": payload.get("estimated_commit_bytes"),
            "mpi_ranks": payload.get("mpi_ranks", payload.get("processes", 12)),
            "threads": payload.get("threads", 1),
            "integrated_pw": bool(payload.get("integrated_pw", False)),
            "scientific_launcher": payload.get("scientific_launcher"),
            "pw_contract": payload.get("pw_contract"),
            "entry_confirmation_poll_s": payload.get("entry_confirmation_poll_s", 0.5),
            "resource_monitor_interval_s": payload.get("resource_monitor_interval_s", 30.0),
        }
        atomic(config, cfg)
        append_event(runtime / "events.jsonl", "HOST_START_INTENT", task_name=payload["task_name"], config=str(config), slot_id=lease.slot_id)
        command = f'{HOST_WRAPPER} "{config}"'
        create = subprocess.run(["schtasks.exe", "/Create", "/TN", payload["task_name"], "/TR", command, "/SC", "ONCE", "/SD", "2099/01/01", "/ST", "00:00", "/F"], capture_output=True, text=True)
        if create.returncode:
            raise RuntimeError(create.stderr or create.stdout)
        run = subprocess.run(["schtasks.exe", "/Run", "/TN", payload["task_name"]], capture_output=True, text=True)
        if run.returncode:
            raise RuntimeError(run.stderr or run.stdout)
    return launch


def main():
    from shared_fdtd.control_v3.db import ControlDB
    from shared_fdtd.engine.dispatcher import dispatch_once
    from shared_fdtd.engine.status import readonly_status
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--db", default=str(DB_PATH))
    parser.add_argument("--audit", default=r"D:\apcd_runtime\global_fdtd_control_v3\dispatcher_last.json")
    args = parser.parse_args()
    db = ControlDB(args.db)
    launched = dispatch_once(db, "coupling_ml", launch_factory(Path(args.db)))
    atomic(args.audit, {"timestamp_utc": now(), "branch": "coupling_ml", "launched": launched, "status": readonly_status(db)})
    print(json.dumps({"status": "PASS", "launched": launched}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
