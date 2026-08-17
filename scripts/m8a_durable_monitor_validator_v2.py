from __future__ import annotations

import ast
import json
from pathlib import Path


ROOT = Path(r"D:/project/worktrees/blue_apcd_np_k6_mdc_v1")
SCRIPT = ROOT / "scripts" / "np_k6_m8a_durable_monitor_v2.py"
TEST = ROOT / "scripts" / "m8a_durable_monitor_mock_tests_source.py"
MONITOR = ROOT / "outputs" / "np_k6_m8a_primary2_hf_acquisition_v1" / "monitor"


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


source = SCRIPT.read_text(encoding="utf-8")
tree = ast.parse(source)
forbidden = ["fd.run", "fd.save", "lumapi", "GlobalSlotScheduler.acquire", "GlobalSlotScheduler.release", "schtasks.exe /Run"]
static_forbidden = [token for token in forbidden if token in source]
manifest = load(MONITOR / "monitor_policy_v2_manifest.json")
state = load(MONITOR / "NP_K6_M8A_PRIMARY2_monitor_state.json")
progress = MONITOR / "NP_K6_M8A_PRIMARY2_progress.jsonl"
rows = []
if progress.exists():
    rows = [json.loads(line) for line in progress.read_text(encoding="utf-8").splitlines() if line.strip()]
required = {"timestamp_utc", "task_id", "coverage", "progress", "controller_state", "dispatcher_state", "worker_state", "entered", "solver_returned", "engine_completed", "post_persisted", "queue", "global_slot_state", "resource_state", "entered_unresolved", "active_hard_gate", "pid", "ppid", "cpu_seconds", "cpu_delta_seconds", "read_only", "solver_calls"}
field_ok = all(required.issubset(row) for row in rows) if rows else False
report = {
    "schema": "apcd_global_durable_monitor_policy_v2_validator",
    "status": "PASS" if not static_forbidden and manifest.get("production_interval_seconds") == 600 and manifest.get("read_only") is True and manifest.get("agent_polling_production") is False and field_ok and all(row.get("solver_calls") == 0 for row in rows) and state.get("solver_calls", 0) == 0 else "FAIL",
    "static_forbidden_tokens": static_forbidden,
    "ast_parse": True,
    "manifest_interval": manifest.get("production_interval_seconds"),
    "manifest_read_only": manifest.get("read_only"),
    "agent_polling_production": manifest.get("agent_polling_production"),
    "progress_records": len(rows),
    "normal_record_fields_complete": field_ok,
    "solver_calls_in_progress": sorted({row.get("solver_calls") for row in rows}),
    "state_solver_calls": state.get("solver_calls", 0),
    "terminal_success_exists": (MONITOR / "terminal_success.json").exists(),
    "terminal_failure_exists": (MONITOR / "terminal_failure.json").exists(),
    "production_monitor_process_started": False,
    "scheduler_attachment": "BLOCKED_OR_NOT_PERSISTED_BY_CURRENT_TASK_CONTEXT",
    "no_fsp_mutation": True,
    "no_slot_mutation": True,
}
(MONITOR / "monitor_validation_v2.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(report, sort_keys=True))
raise SystemExit(0 if report["status"] == "PASS" else 1)
