"""APCD durable, read-only monitor for NP_K6_M8A_PRIMARY2.

The monitor is deliberately separate from the dispatcher/supervisor.  It only
reads ledgers, recovery authority, process metadata, and the global registry;
it never acquires/releases a slot and never calls a solver API.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional


MONITOR_SCHEMA = "apcd_global_durable_monitor_policy_v2"
MONITOR_VERSION = "NP_K6_M8A_DURABLE_MONITOR_V2"
TASK_ID = "NP_K6_M8A_PRIMARY2"
MONITOR_INTERVAL_SECONDS = 600
DEFAULT_ROOT = Path(r"D:/project/worktrees/blue_apcd_np_k6_mdc_v1")
DEFAULT_OUTPUT = DEFAULT_ROOT / "outputs" / "np_k6_m8a_primary2_hf_acquisition_v1"
DEFAULT_REGISTRY = Path(r"D:/project/apcd_global_fdtd_slot_registry_v1.json")
CASES = (
    "NP_K6_M8A_PRIMARY2_G01_P",
    "NP_K6_M8A_PRIMARY2_G01_S",
    "NP_K6_M8A_PRIMARY2_G02_P",
    "NP_K6_M8A_PRIMARY2_G02_S",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    os.replace(str(tmp), str(path))


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, sort_keys=True, default=str) + "\n")


def sha256_text(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def process_snapshot() -> Dict[str, Any]:
    """Read process metadata without terminating or modifying any process."""
    script = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -match 'NP_K6_M8A_PRIMARY2' -or "
        " $_.Name -match 'fdtd-engine|mpiexec|python|supervisor' } | "
        "Select-Object ProcessId,ParentProcessId,Name,CommandLine,CreationDate,UserModeTime,KernelModeTime | "
        "ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=15,
        )
        parsed = json.loads(result.stdout) if result.stdout.strip() else []
        if isinstance(parsed, dict):
            parsed = [parsed]
        return {"ok": result.returncode == 0, "processes": parsed, "stderr": result.stderr[-500:]}
    except Exception as exc:
        return {"ok": False, "processes": [], "error": repr(exc)}


def _known_case_text(value: Any, case_id: str) -> bool:
    return case_id.lower() in str(value).lower()


def _case_recovery_facts(recovery_dir: Path, case_id: str) -> Dict[str, Any]:
    """Read only the small, named recovery authority files.

    No recursive repository scan is performed.  The recovery directory is a
    bounded evidence location created by the M8A recovery task.
    """
    facts: Dict[str, Any] = {}
    for name in (
        "recovery_adjudication.json",
        "independent_recovered_reload_audit.json",
        "recovery_manifest_summary.json",
        "recovery_summary.json",
        "recovery_authority_manifest.json",
    ):
        data = read_json(recovery_dir / name, {})
        if data:
            facts[name] = data
    for candidate in (
        recovery_dir / (case_id + "_manifest.json"),
        recovery_dir / (case_id.lower() + "_manifest.json"),
        recovery_dir / "cases" / case_id / "recovery_manifest.json",
        recovery_dir / "cases" / case_id / "extraction_manifest.json",
    ):
        data = read_json(candidate, {})
        if data:
            facts[candidate.name] = data
    return facts


def _find_case_value(value: Any, case_id: str) -> Optional[Dict[str, Any]]:
    if isinstance(value, dict):
        if _known_case_text(value.get("case_id"), case_id) or _known_case_text(value.get("case_uid"), case_id):
            return value
        for child in value.values():
            found = _find_case_value(child, case_id)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_case_value(child, case_id)
            if found is not None:
                return found
    return None


def case_authority(output_dir: Path, recovery_dir: Path, case_id: str) -> Dict[str, Any]:
    case_path = output_dir / "cases" / case_id
    ledger = read_json(case_path / "attempt_ledger.json", {})
    recovery = _case_recovery_facts(recovery_dir, case_id)
    recovered_record: Optional[Dict[str, Any]] = None
    for data in recovery.values():
        recovered_record = _find_case_value(data, case_id)
        if recovered_record is not None:
            break
    result_recovered = bool(
        ledger.get("result_recovered")
        or ledger.get("recovered")
        or ledger.get("recovery_status") in {"RESULTS_EMBEDDED_AND_QUERYABLE", "RECOVERED"}
        or recovered_record is not None
    )
    formal_accepted = bool(
        ledger.get("formal_accepted")
        or ledger.get("quality_gate_pass")
        or (recovered_record or {}).get("formal_accepted")
        or (recovered_record or {}).get("quality_gate_pass")
    )
    engine_complete = bool(ledger.get("engine_completed") or ledger.get("engine_physical_complete") or result_recovered)
    original_post_saved = bool(ledger.get("post_saved"))
    post_persisted = bool(ledger.get("post_saved") or result_recovered)
    return {
        "case_id": case_id,
        "attempt_id": ledger.get("attempt_id", "attempt_001"),
        "status": ledger.get("status"),
        "entered": bool(ledger.get("entered")),
        "run_invocation_count": int(ledger.get("run_invocation_count", 0) or 0),
        "engine_completed": engine_complete,
        "engine_physical_complete": engine_complete,
        "post_saved": original_post_saved,
        "post_persisted": post_persisted,
        "original_controller_post_saved": original_post_saved,
        "controller_returned": bool(ledger.get("controller_returned")),
        "result_recovered": result_recovered,
        "formal_accepted": formal_accepted,
        "quality_gate_pass": ledger.get("quality_gate_pass"),
        "post_fsp_sha256": ledger.get("post_fsp_sha256"),
        "failure": ledger.get("failure"),
        "ledger_path": str(case_path / "attempt_ledger.json"),
        "recovery_evidence_files": sorted(recovery.keys()),
    }


def registry_snapshot(registry_path: Path) -> Dict[str, Any]:
    data = read_json(registry_path, {})
    compact_slots = []
    for slot in data.get("active_slots", []) or []:
        admission = slot.get("admission_snapshot", {}) if isinstance(slot, dict) else {}
        slot_summary = {
            key: slot.get(key)
            for key in (
                "case_uid", "task_id", "branch", "slot_id", "fdtd_slot_id", "solver_type", "entered",
                "entered_solver", "completion_release_state", "pid", "controller_pid", "processes", "threads",
                "heartbeat", "start_time", "solver_start",
            )
            if isinstance(slot, dict) and key in slot
        }
        slot_summary["admission_counts"] = {
            key: admission.get(key)
            for key in ("active_fdtd_jobs", "active_rcwa_jobs", "registry_active_slots", "unknown_solver_jobs")
            if key in admission
        }
        compact_slots.append(slot_summary)
    return {
        "policy_id": data.get("policy_id"),
        "global_capacity": data.get("global_capacity"),
        "max_active_fdtd_per_branch": data.get("max_active_fdtd_per_branch"),
        "active_slots": compact_slots,
        "registry_path": str(registry_path),
    }


def collect_authoritative_snapshot(root: Path, output_dir: Path, registry_path: Path) -> Dict[str, Any]:
    recovery_dir = root / "outputs" / "np_k6_m8a_attempt001_result_state_recovery_v1"
    cases = [case_authority(output_dir, recovery_dir, case_id) for case_id in CASES]
    processes = process_snapshot()
    registry = registry_snapshot(registry_path)
    case_text = " ".join(json.dumps(case, sort_keys=True) for case in cases)
    lineage = [
        item
        for item in processes.get("processes", [])
        if any(case_id.lower() in str(item.get("CommandLine", "")).lower() for case_id in CASES)
    ]
    entered_unresolved = [
        case["case_id"]
        for case in cases
        if case["entered"] and case["run_invocation_count"] == 0
    ]
    controller_dead = [
        case["case_id"]
        for case in cases
        if case["entered"] and not case["controller_returned"] and not case["engine_physical_complete"] and not case["result_recovered"] and not any(
            case["case_id"].lower() in str(item.get("CommandLine", "")).lower() for item in lineage
        )
    ]
    cpu_seconds = sum(
        (float(item.get("UserModeTime", 0) or 0) + float(item.get("KernelModeTime", 0) or 0)) / 10_000_000.0
        for item in lineage
    )
    entered = [case["case_id"] for case in cases if case["entered"]]
    solver_returned = [case["case_id"] for case in cases if case["engine_physical_complete"]]
    engine_completed = [case["case_id"] for case in cases if case["engine_physical_complete"]]
    post_persisted = [case["case_id"] for case in cases if case["post_persisted"]]
    return {
        "timestamp_utc": utc_now(),
        "task_id": TASK_ID,
        "case_count": len(cases),
        "coverage": {
            "total_cases": len(CASES),
            "terminal_cases": sum(1 for case in cases if case["formal_accepted"] or case["failure"]),
            "pending_cases": sum(1 for case in cases if not case["entered"] and not case["formal_accepted"]),
        },
        "cases": cases,
        "controller_state": {
            "supervisor_state_path": str(output_dir / "m8a_supervisor_state.json"),
            "supervisor_state": read_json(output_dir / "m8a_supervisor_state.json", {}),
            "controller_lineage_count": len(lineage),
            "controller_dead_cases": controller_dead,
        },
        "dispatcher_state": {
            "execution_ledger_path": str(output_dir / "m8a_execution_ledger.json"),
            "execution_ledger": read_json(output_dir / "m8a_execution_ledger.json", {}),
        },
        "worker_state": {
            "entered": entered,
            "solver_returned": solver_returned,
            "engine_completed": engine_completed,
            "post_persisted": post_persisted,
        },
        "process_lineage": {
            "process_snapshot_ok": processes.get("ok", False),
            "matched_processes": lineage,
            "pid": [item.get("ProcessId") for item in lineage],
            "ppid": [item.get("ParentProcessId") for item in lineage],
            "cpu_seconds": cpu_seconds,
            "cpu_delta_seconds": None,
        },
        "progress": {
            "entered_count": len(entered),
            "engine_completed_count": len(engine_completed),
            "post_persisted_count": len(post_persisted),
            "formal_accepted_count": sum(1 for case in cases if case["formal_accepted"]),
        },
        "entered": entered,
        "solver_returned": solver_returned,
        "engine_completed": engine_completed,
        "post_persisted": post_persisted,
        "pid": [item.get("ProcessId") for item in lineage],
        "ppid": [item.get("ParentProcessId") for item in lineage],
        "cpu_seconds": cpu_seconds,
        "cpu_delta_seconds": None,
        "queue": {
            "pending": [case["case_id"] for case in cases if not case["entered"] and not case["formal_accepted"]],
            "free_global_slots": max(0, int(registry.get("global_capacity") or 0) - len(registry.get("active_slots") or [])),
        },
        "global_slot_state": registry,
        "resource_state": {
            "license_state": "not_mutated_read_only",
            "cpu_ram_io": "not_collected_by_monitor_v2",
        },
        "entered_unresolved": entered_unresolved,
        "active_hard_gate": [],
        "read_only": True,
        "solver_calls": 0,
        "case_text_hash": sha256_text(case_text),
    }


def last_jsonl(path: Path) -> Dict[str, Any]:
    try:
        with path.open("rb") as stream:
            stream.seek(0, os.SEEK_END)
            end = stream.tell()
            if not end:
                return {}
            size = min(end, 65536)
            stream.seek(-size, os.SEEK_END)
            lines = stream.read().decode("utf-8", errors="replace").splitlines()
        for line in reversed(lines):
            if line.strip():
                return json.loads(line)
    except Exception:
        return {}
    return {}


class DuplicateMonitor(RuntimeError):
    pass


class DurableMonitor:
    def __init__(
        self,
        monitor_dir: Path,
        task_id: str = TASK_ID,
        interval_seconds: int = MONITOR_INTERVAL_SECONDS,
        sample_provider: Optional[Callable[[], Dict[str, Any]]] = None,
        visible_output: bool = True,
    ) -> None:
        self.monitor_dir = Path(monitor_dir)
        self.task_id = task_id
        self.interval_seconds = int(interval_seconds)
        self.sample_provider = sample_provider
        self.visible_output = visible_output
        self.lock_path = self.monitor_dir / (task_id + "_monitor.lock")
        self.progress_path = self.monitor_dir / (task_id + "_progress.jsonl")
        self.state_path = self.monitor_dir / (task_id + "_monitor_state.json")
        self.success_path = self.monitor_dir / "terminal_success.json"
        self.failure_path = self.monitor_dir / "terminal_failure.json"
        self.owner_token = uuid.uuid4().hex
        self.state = read_json(self.state_path, {})
        self.state.setdefault("schema", MONITOR_SCHEMA)
        self.state.setdefault("monitor_version", MONITOR_VERSION)
        self.state.setdefault("task_id", task_id)
        self.state.setdefault("reported_fingerprints", [])
        self.state.setdefault("sample_count", 0)
        self.state.setdefault("started_timestamp_utc", utc_now())
        self.state.setdefault("read_only", True)
        self.state.setdefault("solver_calls", 0)
        self.state.setdefault("dispatcher_independent", True)
        self.state.setdefault("agent_polling_production", False)
        self.state.setdefault("last_visible_report_epoch", time.monotonic())
        self._lock_acquired = False

    def _lock_payload(self) -> Dict[str, Any]:
        return {
            "schema": MONITOR_SCHEMA,
            "monitor_version": MONITOR_VERSION,
            "task_id": self.task_id,
            "pid": os.getpid(),
            "process_identity": f"pid:{os.getpid()}",
            "owner_token": self.owner_token,
            "created_timestamp_utc": utc_now(),
            "read_only": True,
        }

    @staticmethod
    def _pid_alive(pid: Any) -> bool:
        try:
            pid_int = int(pid)
        except Exception:
            return False
        if pid_int == os.getpid():
            return True
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", f"Get-Process -Id {pid_int} -ErrorAction SilentlyContinue | Select-Object -First 1 Id"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=8,
            )
            return str(pid_int) in result.stdout
        except Exception:
            return False

    def acquire_lock(self) -> None:
        self.monitor_dir.mkdir(parents=True, exist_ok=True)
        payload = self._lock_payload()
        try:
            fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            existing = read_json(self.lock_path, {})
            if existing.get("task_id") != self.task_id:
                raise DuplicateMonitor("monitor lock belongs to another task identity")
            if self._pid_alive(existing.get("pid")):
                raise DuplicateMonitor("healthy durable monitor already owns lock")
            # Stale recovery is permitted only after identity and PID checks.
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass
            fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, sort_keys=True)
            stream.write("\n")
        self._lock_acquired = True

    def release_lock(self) -> None:
        if not self._lock_acquired:
            return
        current = read_json(self.lock_path, {})
        if current.get("owner_token") == self.owner_token:
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass
        self._lock_acquired = False

    def _record_alert(self, code: str, evidence: Dict[str, Any]) -> None:
        fingerprint = sha256_text({"code": code, "evidence": evidence})
        reported = set(self.state.get("reported_fingerprints", []))
        if fingerprint in reported:
            return
        reported.add(fingerprint)
        self.state["reported_fingerprints"] = sorted(reported)
        alert = {
            "schema": MONITOR_SCHEMA,
            "task_id": self.task_id,
            "alert_code": code,
            "alert_fingerprint": fingerprint,
            "first_detected_timestamp_utc": utc_now(),
            "reported": True,
            "read_only": True,
            "solver_calls": 0,
            "evidence": evidence,
        }
        existing = read_json(self.failure_path, {})
        alerts = existing.get("alerts", []) if isinstance(existing, dict) else []
        if not isinstance(alerts, list):
            alerts = []
        alerts.append(alert)
        artifact = {
            "schema": MONITOR_SCHEMA,
            "task_id": self.task_id,
            "reported": True,
            "read_only": True,
            "solver_calls": 0,
            "alert_count": len(alerts),
            "alert_fingerprint": alerts[0].get("alert_fingerprint"),
            "first_detected_timestamp_utc": alerts[0].get("first_detected_timestamp_utc"),
            "alerts": alerts,
        }
        atomic_json(self.failure_path, artifact)
        self.state["active_hard_gate"] = [code]
        self.state["last_alert"] = alert
        if self.visible_output:
            print(json.dumps({"event": "monitor_anomaly", "alert_code": code, "alert_fingerprint": fingerprint}, sort_keys=True), flush=True)

    def _detect_anomalies(self, sample: Dict[str, Any]) -> None:
        previous = self.state.get("last_sample", {})
        cases = sample.get("cases", [])
        active_codes = []
        if int(self.state.get("cpu_stall_count", 0) or 0) >= 2:
            active_codes.append("CPU_STALL_DEBOUNCED")
        for case in cases:
            cid = case.get("case_id")
            if case.get("entered") and int(case.get("run_invocation_count", 0) or 0) == 0:
                active_codes.append("ENTERED_UNRESOLVED")
                self._record_alert("ENTERED_UNRESOLVED", {"case_id": cid})
            if case.get("engine_completed") and not case.get("post_persisted") and not case.get("controller_returned"):
                active_codes.append("POST_ENGINE_CLOSURE_ANOMALY")
                self._record_alert(
                    "POST_ENGINE_CLOSURE_ANOMALY",
                    {"case_id": cid, "condition": "ENGINE_COMPLETED+POST_PERSISTENCE_MISSING+CONTROLLER_NOT_CLOSED"},
                )
            if case.get("formal_accepted") and case.get("entered"):
                active = [slot for slot in sample.get("global_slot_state", {}).get("active_slots", []) if slot.get("case_uid") == cid]
                if active:
                    active_codes.append("SLOT_OCCUPIED_AFTER_TERMINAL")
                    self._record_alert("SLOT_OCCUPIED_AFTER_TERMINAL", {"case_id": cid, "active_slots": active})
        lineage = sample.get("process_lineage", {})
        if any(case.get("entered") for case in cases) and not lineage.get("process_snapshot_ok", True):
            active_codes.append("MONITOR_PROCESS_METADATA_UNAVAILABLE")
            self._record_alert("MONITOR_PROCESS_METADATA_UNAVAILABLE", {"process_lineage": lineage})
        dead_cases = sample.get("controller_state", {}).get("controller_dead_cases", [])
        if dead_cases:
            active_codes.append("CONTROLLER_OR_SUPERVISOR_DEAD")
            self._record_alert("CONTROLLER_OR_SUPERVISOR_DEAD", {"cases": dead_cases})
        queue = sample.get("queue", {})
        active_slots = sample.get("global_slot_state", {}).get("active_slots", [])
        if queue.get("pending") and int(queue.get("free_global_slots", 0) or 0) > 0 and not active_slots:
            active_codes.append("QUEUE_IDLE_WITH_FREE_SLOT")
            self._record_alert("QUEUE_IDLE_WITH_FREE_SLOT", {"pending": queue.get("pending"), "free_slots": queue.get("free_global_slots")})
        policy = sample.get("global_slot_state", {})
        if policy.get("policy_id") not in (None, "APCD_GLOBAL_FDTD_SCHEDULING_POLICY_V3") or policy.get("global_capacity") not in (None, 3):
            active_codes.append("RESOURCE_OR_LICENSE_HARD_GATE")
            self._record_alert("RESOURCE_OR_LICENSE_HARD_GATE", {"global_slot_state": policy})
        for case in cases:
            if case.get("post_saved") and not case.get("post_fsp_sha256"):
                active_codes.append("FSP_LEDGER_CONTRADICTION")
                self._record_alert("FSP_LEDGER_CONTRADICTION", {"case_id": case.get("case_id"), "reason": "post_saved_without_post_fsp_sha256"})
        known = {case.get("case_id") for case in cases}
        unknown_slots = [slot for slot in active_slots if slot.get("case_uid") not in known]
        if unknown_slots:
            active_codes.append("REGISTRY_CONTROLLER_CONFLICT")
            self._record_alert("REGISTRY_CONTROLLER_CONFLICT", {"unknown_slots": unknown_slots})
        self.state["active_hard_gate"] = sorted(set(active_codes))
        if sample.get("entered_unresolved"):
            self._record_alert("ENTERED_UNRESOLVED", {"cases": sample["entered_unresolved"]})
        current_live = len(lineage.get("matched_processes", []))
        previous_live = len(previous.get("process_lineage", {}).get("matched_processes", [])) if previous else current_live
        if any(case.get("entered") for case in cases) and previous and current_live == 0 and previous_live > 0:
            self._record_alert("WORKER_LINEAGE_LOST", {"previous_live": previous_live, "current_live": current_live})

    def _terminal_success(self, sample: Dict[str, Any]) -> bool:
        cases = sample.get("cases", [])
        return len(cases) == len(CASES) and all(case.get("formal_accepted") for case in cases)

    def process_sample(self, sample: Dict[str, Any]) -> Dict[str, Any]:
        sample = dict(sample)
        sample.setdefault("timestamp_utc", utc_now())
        sample.setdefault("task_id", self.task_id)
        sample.setdefault("monitor_version", MONITOR_VERSION)
        sample.setdefault("monitor_interval_seconds", self.interval_seconds)
        sample.setdefault("read_only", True)
        sample.setdefault("solver_calls", 0)
        lineage = sample.get("process_lineage", {})
        current_cpu = lineage.get("cpu_seconds")
        previous_cpu = self.state.get("last_sample", {}).get("process_lineage", {}).get("cpu_seconds")
        if current_cpu is not None and previous_cpu is not None:
            delta = float(current_cpu) - float(previous_cpu)
            lineage["cpu_delta_seconds"] = delta
            sample["cpu_delta_seconds"] = delta
            unchanged = abs(delta) < 1e-9 and bool(lineage.get("matched_processes"))
            self.state["cpu_stall_count"] = int(self.state.get("cpu_stall_count", 0)) + 1 if unchanged else 0
            if self.state["cpu_stall_count"] >= 2:
                self.state.setdefault("active_hard_gate", []).append("CPU_STALL_DEBOUNCED")
                self._record_alert("CPU_STALL_DEBOUNCED", {"cpu_seconds": current_cpu, "samples": self.state["cpu_stall_count"]})
        self._detect_anomalies(sample)
        self.state["sample_count"] = int(self.state.get("sample_count", 0)) + 1
        self.state["last_sample"] = sample
        self.state["last_sample_timestamp_utc"] = sample["timestamp_utc"]
        self.state["status"] = "anomaly" if self.failure_path.exists() else "running"
        append_jsonl(self.progress_path, sample)
        atomic_json(self.state_path, self.state)
        if self.visible_output and not self.state.get("last_alert"):
            elapsed = time.monotonic() - float(self.state.get("last_visible_report_epoch", time.monotonic()))
            if elapsed >= self.interval_seconds:
                print(json.dumps({
                    "event": "monitor_heartbeat",
                    "task_id": self.task_id,
                    "sample_count": self.state["sample_count"],
                    "entered": sample.get("entered", []),
                    "engine_completed": sample.get("engine_completed", []),
                    "post_persisted": sample.get("post_persisted", []),
                    "solver_calls": 0,
                }, sort_keys=True), flush=True)
                self.state["last_visible_report_epoch"] = time.monotonic()
                atomic_json(self.state_path, self.state)
        if self._terminal_success(sample) and not self.success_path.exists():
            terminal = {
                "schema": MONITOR_SCHEMA,
                "task_id": self.task_id,
                "terminal": "success",
                "terminal_timestamp_utc": utc_now(),
                "reported": True,
                "read_only": True,
                "solver_calls": 0,
                "case_ids": [case.get("case_id") for case in sample.get("cases", [])],
            }
            atomic_json(self.success_path, terminal)
            self.state["status"] = "terminal_success"
            atomic_json(self.state_path, self.state)
            if self.visible_output:
                print(json.dumps({"event": "terminal_success", "task_id": self.task_id}, sort_keys=True), flush=True)
        return sample

    def run(self, max_samples: Optional[int] = None, once: bool = False) -> int:
        self.acquire_lock()
        try:
            self.state["status"] = "running"
            self.state["production_interval_seconds"] = MONITOR_INTERVAL_SECONDS
            self.state["test_interval_override_seconds"] = self.interval_seconds if self.interval_seconds != MONITOR_INTERVAL_SECONDS else None
            self.state["read_only"] = True
            self.state["agent_polling_production"] = False
            self.state["dispatcher_independent"] = True
            atomic_json(self.state_path, self.state)
            if self.visible_output:
                print(json.dumps({"event": "monitor_started", "task_id": self.task_id, "interval_seconds": self.interval_seconds}, sort_keys=True), flush=True)
            count = 0
            while True:
                sample = self.sample_provider() if self.sample_provider else collect_authoritative_snapshot(DEFAULT_ROOT, DEFAULT_OUTPUT, DEFAULT_REGISTRY)
                self.process_sample(sample)
                count += 1
                if once or (max_samples is not None and count >= max_samples) or self.success_path.exists():
                    return 0
                time.sleep(self.interval_seconds)
        except Exception as exc:
            try:
                self._record_alert("MONITOR_SELF_FAILURE", {"error": repr(exc)})
                atomic_json(self.state_path, self.state)
            finally:
                raise
        finally:
            self.release_lock()


def monitor_query(monitor_dir: Path) -> Dict[str, Any]:
    """Fast path: last JSONL record + canonical state, no repository scan."""
    progress = monitor_dir / (TASK_ID + "_progress.jsonl")
    state = monitor_dir / (TASK_ID + "_monitor_state.json")
    result = {
        "task_id": TASK_ID,
        "last_progress": last_jsonl(progress),
        "monitor_state": read_json(state, {}),
        "terminal_success": read_json(monitor_dir / "terminal_success.json", {}),
        "terminal_failure": read_json(monitor_dir / "terminal_failure.json", {}),
        "fast_path": True,
        "repository_scan": False,
    }
    return result


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="read-only APCD durable monitor")
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--monitor-dir", default="")
    parser.add_argument("--test-interval", type=int, default=0)
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--query", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    monitor_dir = Path(args.monitor_dir) if args.monitor_dir else Path(args.output_dir) / "monitor"
    if args.query:
        print(json.dumps(monitor_query(monitor_dir), indent=2, sort_keys=True, default=str))
        return 0
    interval = args.test_interval if args.test_interval > 0 else MONITOR_INTERVAL_SECONDS
    provider = lambda: collect_authoritative_snapshot(Path(args.root), Path(args.output_dir), Path(args.registry))
    monitor = DurableMonitor(monitor_dir, interval_seconds=interval, sample_provider=provider, visible_output=not args.quiet)
    return monitor.run(max_samples=args.max_samples, once=args.once)


if __name__ == "__main__":
    raise SystemExit(main())
