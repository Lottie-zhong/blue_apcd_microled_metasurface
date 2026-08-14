from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEDULER_PATH = ROOT / "scripts/apcd_global_fdtd_slot_v1.py"
REGISTRY = Path(r"D:\project\apcd_global_fdtd_slot_registry_v1.json")
CASE = "H1E1_A_small_N_GLOBAL_015_x"
SLOT = "FDTD_SLOT_2"
CASE_DIR = ROOT / "outputs/lp_extended_j1_h1e1/runtime/cases" / CASE
PROVENANCE = CASE_DIR / "attempt_provenance_attempt_003.json"
RUN_FSP = CASE_DIR / f"{CASE}_attempt_003_run.fsp"


def load_scheduler():
    spec = importlib.util.spec_from_file_location("safe_release_scheduler", SCHEDULER_PATH)
    mod = importlib.util.module_from_spec(spec); assert spec and spec.loader
    spec.loader.exec_module(mod); return mod


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""): h.update(chunk)
    return h.hexdigest()


def main() -> int:
    scheduler = load_scheduler(); now = dt.datetime.now(dt.timezone.utc).isoformat()
    if not PROVENANCE.exists() or not RUN_FSP.exists(): raise RuntimeError("HARD_GATE_COMPLETION_EVIDENCE_MISSING")
    prov = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    if not prov.get("solver_entered") or not prov.get("solver_complete") or prov.get("run_fsp_sha256") != sha256_file(RUN_FSP): raise RuntimeError("HARD_GATE_ENTERED_COMPLETION_PROVENANCE_INVALID")
    live = scheduler.live_job_snapshot(); forbidden = [j for j in live.get("jobs", []) if CASE.lower() in json.dumps(j, sort_keys=True).lower() or (j.get("branch") == "work/lp-global-h-manifold-v1" and j.get("solver_type") == "FDTD")]
    if forbidden: raise RuntimeError("HARD_GATE_EXACT_ENTERED_OWNER_STILL_LIVE")
    with scheduler.registry_lock(REGISTRY):
        data = scheduler._read(REGISTRY); rows = data.get("active_slots", []); row = next((x for x in rows if x.get("slot_id") == SLOT), None)
        if row is None: raise RuntimeError("SLOT_ALREADY_RELEASED_OR_MISSING")
        if row.get("case_uid") != CASE or row.get("branch") != "work/lp-global-h-manifold-v1" or not row.get("entered_solver"): raise RuntimeError("HARD_GATE_EXACT_OWNERSHIP_MISMATCH")
        history = dict(row)
        history.update({"completion_release_state": "RECOVERED_SOLVER_COMPLETED_RELEASE", "solver_complete": prov["solver_complete"], "slot_release_time": now, "heartbeat": now, "reconciliation_version": "APCD_GLOBAL_SCHEDULER_OWNERSHIP_RECONCILIATION_V1", "recovery_reason": "release write failed after solver completion; exact run FSP and provenance verified; owner engine group absent", "run_fsp_path": str(RUN_FSP), "run_fsp_sha256": prov["run_fsp_sha256"], "previous_owner_label": row.get("branch"), "previous_state": row.get("completion_release_state")})
        data["active_slots"] = [x for x in rows if x.get("slot_id") != SLOT]; data.setdefault("history", []).append(history); data["updated_utc"] = now; scheduler._write(REGISTRY, data)
    print(json.dumps({"released_slot": SLOT, "case_uid": CASE, "solver_replay": False, "run_fsp_sha256": prov["run_fsp_sha256"], "history_appended": True}, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
