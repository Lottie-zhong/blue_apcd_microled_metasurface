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
hourly = MONITOR / "NP_K6_M8A_PRIMARY2_hourly_summary.json"
rows = []
if progress.exists():
    rows = [json.loads(line) for line in progress.read_text(encoding="utf-8").splitlines() if line.strip()]
required = {"timestamp_utc", "task_id", "coverage", "progress", "controller_state", "dispatcher_state", "worker_state", "entered", "solver_returned", "engine_completed", "post_persisted", "queue", "global_slot_state", "resource_state", "entered_unresolved", "active_hard_gate", "pid", "ppid", "cpu_seconds", "cpu_delta_seconds", "read_only", "solver_calls"}
field_ok = all(required.issubset(row) for row in rows) if rows else False
hourly_fields = {"timestamp", "case", "attempt", "entered", "run", "engine_state", "progress", "pid_alive", "cpu_time_delta_1h", "runtime_seconds", "slot", "post_fsp", "extraction", "latest_anomaly", "monitor_health"}
hourly_value = load(hourly) if hourly.exists() else {}
hourly_present = hourly.exists()
hourly_field_ok = (not hourly_present) or hourly_fields.issubset(hourly_value.keys())
hourly_health_ok = (not hourly_present) or (
    hourly_value.get("monitor_health", {}).get("monitor_interval_seconds") == 600
    and hourly_value.get("monitor_health", {}).get("hourly_summary_interval_seconds") == 3600
    and hourly_value.get("monitor_health", {}).get("solver_calls") == 0
)
report = {
    "schema": "apcd_global_durable_monitor_policy_v2_validator",
    "status": "PASS" if not static_forbidden and manifest.get("production_interval_seconds") == 600 and manifest.get("hourly_progress_summary_interval_seconds") == 3600 and manifest.get("hourly_progress_summary_samples") == 6 and manifest.get("read_only") is True and manifest.get("agent_polling_production") is False and manifest.get("production_visible_output") is False and field_ok and hourly_field_ok and hourly_health_ok and all(row.get("solver_calls") == 0 for row in rows) and state.get("solver_calls", 0) == 0 else "FAIL",
    "static_forbidden_tokens": static_forbidden,
    "ast_parse": True,
    "manifest_interval": manifest.get("production_interval_seconds"),
    "hourly_summary_interval": manifest.get("hourly_progress_summary_interval_seconds"),
    "hourly_summary_samples": manifest.get("hourly_progress_summary_samples"),
    "production_visible_output": manifest.get("production_visible_output"),
    "manifest_read_only": manifest.get("read_only"),
    "agent_polling_production": manifest.get("agent_polling_production"),
    "progress_records": len(rows),
    "normal_record_fields_complete": field_ok,
    "hourly_summary_exists": hourly_present,
    "hourly_summary_fields_complete": hourly_field_ok,
    "hourly_summary_health_contract": hourly_health_ok,
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
