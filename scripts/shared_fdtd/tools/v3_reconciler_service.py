from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
sys.path.insert(0, str(ROOT / "scripts"))
DB_PATH = Path(r"D:\apcd_runtime\global_fdtd_control_v3\control.sqlite3")
AUDIT = Path(r"D:\apcd_runtime\global_fdtd_control_v3\reconciler_last.json")


def main():
    from shared_fdtd.control_v3.db import ControlDB
    from shared_fdtd.engine.reconciler import reconcile_owned
    db = ControlDB(DB_PATH)
    roots = {}
    with db.connect(readonly=True) as con:
        for row in con.execute("SELECT logical_case_id,attempt_id,payload_json FROM branch_queue WHERE branch_id='coupling_ml'"):
            payload = json.loads(row["payload_json"])
            roots[(row["logical_case_id"], row["attempt_id"])] = Path(payload["runtime"])
    result = reconcile_owned(db, "coupling_ml", roots)
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps({"timestamp_utc": datetime.now(timezone.utc).isoformat(), "branch": "coupling_ml", "result": result}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "result": result}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
