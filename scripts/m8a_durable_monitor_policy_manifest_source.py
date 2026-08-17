from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(r"D:/project/worktrees/blue_apcd_np_k6_mdc_v1")
OUT = ROOT / "outputs" / "np_k6_m8a_primary2_hf_acquisition_v1" / "monitor"
DOC = ROOT / "docs" / "np_k6_m8a_global_durable_monitor_policy_v2.md"


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


manifest = {
    "schema": "apcd_global_durable_monitor_policy_v2",
    "policy_id": "APCD_GLOBAL_DURABLE_MONITOR_POLICY_V2",
    "task_id": "NP_K6_M8A_PRIMARY2",
    "monitor_executable": "scripts/np_k6_m8a_durable_monitor_v2.py",
    "query_helper": "scripts/np_k6_m8a_monitor_query_v2.py",
    "canonical_paths": {
        "progress_jsonl": "outputs/np_k6_m8a_primary2_hf_acquisition_v1/monitor/NP_K6_M8A_PRIMARY2_progress.jsonl",
        "monitor_state": "outputs/np_k6_m8a_primary2_hf_acquisition_v1/monitor/NP_K6_M8A_PRIMARY2_monitor_state.json",
        "lock": "outputs/np_k6_m8a_primary2_hf_acquisition_v1/monitor/NP_K6_M8A_PRIMARY2_monitor.lock",
        "terminal_success": "outputs/np_k6_m8a_primary2_hf_acquisition_v1/monitor/terminal_success.json",
        "terminal_failure": "outputs/np_k6_m8a_primary2_hf_acquisition_v1/monitor/terminal_failure.json",
    },
    "production_interval_seconds": 600,
    "one_monitor_per_task": True,
    "same_process_loop": True,
    "read_only": True,
    "dispatcher_independent": True,
    "agent_polling_production": False,
    "production_activation": {
        "implementation": "COMPLETE",
        "preferred_backend": "WINDOWS_TASK_SCHEDULER",
        "scheduler_task_name": "NP_K6_M8A_PRIMARY2_DURABLE_MONITOR_V2",
        "current_attachment_status": "CONTEXT_PATH_OR_TASK_ACL_REQUIRES_RECONCILIATION",
        "fallback_detached_ssh_process": False,
    },
    "normal_samples_file_only": True,
    "important_state_changes_immediate": True,
    "no_solver_calls": True,
    "no_slot_mutation": True,
    "no_fsp_mutation": True,
    "scheduler_policy": {
        "policy_id": "APCD_GLOBAL_FDTD_SCHEDULING_POLICY_V3",
        "global_capacity": 3,
        "branch_capacity": 3,
        "fdtd_resource": {"processes": 4, "threads": 1},
        "rcwa_consumes_fdtd_slot": False,
        "monitor_consumes_fdtd_slot": False,
    },
    "anomalies": [
        "WORKER_LINEAGE_LOST",
        "CPU_STALL_DEBOUNCED",
        "CONTROLLER_OR_SUPERVISOR_DEAD",
        "POST_ENGINE_CLOSURE_ANOMALY",
        "FSP_LEDGER_CONTRADICTION",
        "ENTERED_UNRESOLVED",
        "SLOT_OCCUPIED_AFTER_TERMINAL",
        "QUEUE_IDLE_WITH_FREE_SLOT",
        "REGISTRY_CONTROLLER_CONFLICT",
        "RESOURCE_OR_LICENSE_HARD_GATE",
        "MONITOR_SELF_FAILURE",
    ],
    "legacy_scripts": {
        "m8a_monitor_source.py": "NOT_PRODUCTION_DURABLE_MONITOR",
        "m8a_heartbeat_probe_source.py": "FORENSIC_ONLY",
        "m8a_failure_probe_source.py": "FORENSIC_ONLY",
        "m8a_case_state_probe_source.py": "FORENSIC_ONLY",
        "m8a_runtime_policy_probe_source.py": "FORENSIC_ONLY",
        "m8a_progress_ascii_source.py": "FORENSIC_ONLY",
        "m8a_log_probe_source.py": "FORENSIC_ONLY",
    },
    "current_m8a_authority": {
        "G01_P": {"engine_physical_complete": True, "original_controller_post_saved": False, "result_recovered": True, "formal_accepted": True},
        "G01_S": {"engine_physical_complete": True, "original_controller_post_saved": False, "result_recovered": True, "formal_accepted": True},
        "G02_P": {"engine_physical_complete": True, "original_controller_post_saved": False, "result_recovered": True, "formal_accepted": True},
        "G02_S": {"entered": False, "run_invocation_count": 0, "status": "pending"},
    },
    "monitor_contract": {
        "normal_jsonl_fields": [
            "timestamp_utc", "task_id", "coverage", "progress", "controller_state", "dispatcher_state",
            "worker_state", "entered", "solver_returned", "engine_completed", "post_persisted", "pid", "ppid",
            "cpu_seconds", "cpu_delta_seconds", "queue", "global_slot_state", "resource_state", "entered_unresolved",
            "active_hard_gate",
        ],
        "terminal_artifacts_written_once": True,
        "duplicate_alert_fingerprint_suppression": True,
        "stale_lock_recovery_identity_checked": True,
    },
}
manifest["manifest_sha256"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
atomic_json(OUT / "monitor_policy_v2_manifest.json", manifest)

DOC.parent.mkdir(parents=True, exist_ok=True)
DOC.write_text(
    """# APCD global durable monitor policy V2 — NP K6 M8A

This migration installs one server-side, read-only monitor for `NP_K6_M8A_PRIMARY2`.
The production interval is 600 seconds; internal state reads may be more frequent only inside the same monitor process.
Normal samples are appended to the canonical JSONL file without visible chatter. Important transitions, anomalies, and terminal state are reported once.

## Canonical artifacts

- `outputs/np_k6_m8a_primary2_hf_acquisition_v1/monitor/NP_K6_M8A_PRIMARY2_progress.jsonl`
- `outputs/np_k6_m8a_primary2_hf_acquisition_v1/monitor/NP_K6_M8A_PRIMARY2_monitor_state.json`
- `outputs/np_k6_m8a_primary2_hf_acquisition_v1/monitor/NP_K6_M8A_PRIMARY2_monitor.lock`
- `terminal_success.json` / `terminal_failure.json`

The monitor is independent of the dispatcher, never acquires or releases slots, never calls `run`, never saves or edits an FSP, and never kills, pauses, restarts, or replays a worker.
Task Scheduler and dispatcher remain the owners of queue progression, slot release, post-save, and G02-S admission.

## Current M8A authority

G01-P, G01-S, and G02-P are represented as engine-complete, result-recovered, and formally accepted while preserving the fact that their original controller `post_saved` flag was false. G02-S remains pending with `entered=0` and `run_invocation_count=0`.

Legacy polling/probe scripts are forensic-only and are not production durable monitors. The query helper reads only the last JSONL record and canonical monitor state.

This is a zero-solver control-plane migration: `solver_calls=0`, no new FDTD/RCWA, no slot mutation, and no sealed-HF access.
""",
    encoding="utf-8",
)
print(json.dumps({"manifest": str(OUT / "monitor_policy_v2_manifest.json"), "manifest_sha256": manifest["manifest_sha256"], "doc": str(DOC)}, sort_keys=True))
