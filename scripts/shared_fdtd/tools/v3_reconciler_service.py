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
    from shared_fdtd.engine.reconciler import reconcile_owned, closeout_owned_postentry_no_truth
    from shared_fdtd.engine.process_identity import snapshot
    db = ControlDB(DB_PATH)
    roots = {}
    with db.connect(readonly=True) as con:
        for row in con.execute("SELECT logical_case_id,attempt_id,payload_json FROM branch_queue WHERE branch_id='coupling_ml'"):
            payload = json.loads(row["payload_json"])
            roots[(row["logical_case_id"], row["attempt_id"])] = Path(
                payload.get("attempt_root") or payload.get("case_root") or payload["runtime"]
            )
    def process_probe(state):
        rows = snapshot(state["logical_case_id"])
        attempt = state["attempt_id"].lower()
        return [row for row in rows if attempt in str(row.get("CommandLine", row.get("command_line", ""))).lower()]
    closeout = closeout_owned_postentry_no_truth(
        db, "coupling_ml", roots, process_probe=process_probe,
        reason="RECONCILER_POSTENTRY_NO_TRUTH_CLOSEOUT",
    )
    result = reconcile_owned(db, "coupling_ml", roots)
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps({"timestamp_utc": datetime.now(timezone.utc).isoformat(), "branch": "coupling_ml", "closeout": closeout, "result": result}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "closeout": closeout, "result": result}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
