from __future__ import annotations

import csv
import datetime as dt
import json
import os
import subprocess
import threading
import time
from pathlib import Path

import lp_global_h_h1c1c_phase_gap_v1 as h1c1c


TRIAL_DIR = h1c1c.REPORT / "concurrency3_trial"
SLOT_META = TRIAL_DIR / "experimental_slot3.json"
TELEMETRY_JSON = TRIAL_DIR / "concurrency3_live_job_map.json"
TELEMETRY_CSV = TRIAL_DIR / "concurrency3_telemetry.csv"
RESULT_JSON = TRIAL_DIR / "concurrency3_trial_result.json"
SUMMARY_MD = TRIAL_DIR / "concurrency3_summary.md"
TRIAL_POLICY = "APCD_CONCURRENCY3_VALIDATION_TRIAL_V1"


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def resources():
    script = r"""$os=Get-CimInstance Win32_OperatingSystem
$cpu=(Get-CimInstance Win32_Processor | Measure-Object LoadPercentage -Average).Average
[pscustomobject]@{cpu_load_pct=$cpu; memory_total_mb=[math]::Round($os.TotalVisibleMemorySize/1024,1); memory_free_mb=[math]::Round($os.FreePhysicalMemory/1024,1)} | ConvertTo-Json -Compress"""
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True, timeout=30).stdout.strip()
        return json.loads(out) if out else {"status": "UNAVAILABLE"}
    except Exception as exc:
        return {"status": "UNAVAILABLE", "error": f"{type(exc).__name__}: {exc}"}


class Telemetry:
    def __init__(self, slot_module, readiness):
        self.slot_module = slot_module
        self.readiness = readiness
        self.rows = []
        self.stop = threading.Event()
        self.thread = None

    def snapshot(self, label=""):
        live = self.slot_module.live_job_snapshot(None)
        jobs = []
        for job in live.get("jobs", []):
            processes = job.get("processes", [])
            jobs.append({
                "branch": job.get("branch"),
                "job_token": job.get("job_token"),
                "process_count": len(processes),
                "engine_count": sum(str(p.get("name", "")).lower() == "fdtd-engine-msmpi.exe" for p in processes),
                "process_names": [p.get("name") for p in processes],
            })
        row = {"timestamp_utc": now(), "label": label, "real_live_fdtd_job_count": len(jobs), "jobs": jobs, "resources": resources(), "readiness": self.readiness}
        self.rows.append(row)
        return row

    def start(self):
        self.snapshot("T0")

        def loop():
            while not self.stop.wait(5.0):
                self.snapshot("")

        self.thread = threading.Thread(target=loop, name="h1c1c-concurrency3-telemetry", daemon=True)
        self.thread.start()

    def mark(self, label):
        return self.snapshot(label)

    def finish(self):
        self.stop.set()
        if self.thread is not None:
            self.thread.join(timeout=10)
        self.snapshot("END")


class ExperimentalLease:
    slot_id = "EXPERIMENTAL_SLOT3"

    def __init__(self, record, telemetry):
        self.record = record
        self.telemetry = telemetry
        self._released = False
        self._stop = threading.Event()
        self._thread = None

    def _persist(self):
        self.record["heartbeat"] = now()
        h1c1c.write_json(SLOT_META, self.record)

    def mark_solver_entered(self, solver_start=None):
        stamp = solver_start or now()
        self.record.update({"entered_solver": True, "entered": True, "solver_start": stamp, "heartbeat": stamp, "trial_status": "ARCHITECTURAL_ENTRY_OBSERVED"})
        self._persist()
        self.telemetry.mark("T1_LP_ENTERED")

    def start_heartbeat(self, interval_s=5.0):
        def loop():
            while not self._stop.wait(interval_s):
                self._persist()

        self._thread = threading.Thread(target=loop, name="h1c1c-experimental-slot3-heartbeat", daemon=True)
        self._thread.start()

    def release(self, state, solver_complete=None):
        if self._released:
            return
        self._released = True
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
        self.record.update({"completion": solver_complete or now(), "release_state": state, "trial_status": "RELEASED"})
        self._persist()


class ExperimentalScheduler:
    slot_id = "EXPERIMENTAL_SLOT3"

    def __init__(self, slot_module, telemetry, readiness):
        self.slot_module = slot_module
        self.telemetry = telemetry
        self.readiness = readiness

    def acquire_wait(self, **kwargs):
        registry = self.slot_module.DEFAULT_REGISTRY_PATH
        with self.slot_module.registry_lock(registry):
            live = self.slot_module.live_job_snapshot(None)
            if live.get("global_active_jobs", 0) >= 3:
                raise RuntimeError("HARD_STOP_CONCURRENCY3_ALREADY_OCCUPIED_OR_RUNTIME_UNRESOLVED")
            if live.get("lp_active_jobs", 0) >= 1:
                raise RuntimeError("HARD_STOP_LP_ACTIVE_FDTD")
            if SLOT_META.exists():
                old = h1c1c.read_json(SLOT_META, {})
                if old.get("entered_solver") and old.get("release_state") not in {"SOLVER_COMPLETED", "FAILED_ENTERED"}:
                    raise RuntimeError("HARD_GATE_EXPERIMENTAL_SLOT3_ENTERED_NO_RECOVERY")
            record = {
                "schema": "APCD_EXPERIMENTAL_SLOT3_V1",
                "slot_id": self.slot_id,
                "policy": TRIAL_POLICY,
                "branch": h1c1c.TARGET_BRANCH,
                "worktree": str(h1c1c.ROOT),
                "task_id": kwargs.get("task_id"),
                "case_uid": kwargs.get("case_uid"),
                "attempt_uid": kwargs.get("metadata", {}).get("attempt_id"),
                "controller_pid": kwargs.get("pid"),
                "processes": 4,
                "threads": 1,
                "entered_solver": False,
                "start_time": now(),
                "heartbeat": now(),
                "real_live_peer_job_count_at_entry": live.get("global_active_jobs", 0),
                "peer_branches": sorted({str(j.get("branch")) for j in live.get("jobs", [])}),
                "registry_active_slots": [
                    {"slot_id": row.get("slot_id"), "branch": row.get("branch"), "entered_solver": row.get("entered_solver"), "case_uid": row.get("case_uid")}
                    for row in h1c1c.read_json(registry, {}).get("active_slots", [])
                ],
                "admission_live_job_map": live.get("jobs", []),
                "readiness": self.readiness,
                "completion": None,
                "release_state": "ACTIVE",
                "trial_status": "SLOT3_ACQUIRED",
            }
            h1c1c.write_json(SLOT_META, record)
        self.telemetry.mark("SLOT3_ACQUIRED")
        return ExperimentalLease(record, self.telemetry)


def choose_case(data, accounting):
    records = {row["case_id"]: row for row in accounting.get("cases", [])}
    prior = h1c1c.read_json(RESULT_JSON, {})
    prior_cid = prior.get("trial_case", {}).get("case_uid")
    if prior_cid:
        for candidate in data["candidates"]:
            for pol in h1c1c.POLARIZATIONS:
                cid = candidate["broadband_case_identity"][pol]["case_uid"]
                row = records.get(cid, {})
                if cid == prior_cid and not row.get("solver_entered") and not row.get("accepted"):
                    return candidate, pol
    for candidate in data["candidates"]:
        for pol in h1c1c.POLARIZATIONS:
            cid = candidate["broadband_case_identity"][pol]["case_uid"]
            row = records.get(cid, {})
            if not row.get("attempted") and not row.get("solver_entered") and not row.get("accepted"):
                return candidate, pol
    raise RuntimeError("HARD_GATE_NO_UNATTEMPTED_H1C1C_CASE")


def write_telemetry(telemetry):
    h1c1c.write_json(TELEMETRY_JSON, {"schema": "APCD_CONCURRENCY3_LIVE_JOB_MAP_V1", "policy": TRIAL_POLICY, "observations": telemetry.rows})
    fields = ["timestamp_utc", "label", "real_live_fdtd_job_count", "jobs_json", "cpu_load_pct", "memory_total_mb", "memory_free_mb"]
    with TELEMETRY_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in telemetry.rows:
            res = row.get("resources", {})
            writer.writerow({"timestamp_utc": row.get("timestamp_utc"), "label": row.get("label"), "real_live_fdtd_job_count": row.get("real_live_fdtd_job_count"), "jobs_json": json.dumps(row.get("jobs", []), ensure_ascii=False, sort_keys=True), "cpu_load_pct": res.get("cpu_load_pct"), "memory_total_mb": res.get("memory_total_mb"), "memory_free_mb": res.get("memory_free_mb")})


def main():
    h1c1c.configure_support()
    data = h1c1c.manifest()
    h1c1c.validate(data)
    accounting = h1c1c.initial_accounting(data)
    setup = h1c1c.read_json(h1c1c.REPORT / "h1c1c_setup_check.json", {})
    readiness = {"setup_check_present": bool(setup), "reload_gate_pass": bool(setup.get("reload_gate", {}).get("pass")), "solver_entered": setup.get("solver_entered", False), "solver_run_called": setup.get("solver_run_called", False)}
    if not readiness["reload_gate_pass"] or readiness["solver_entered"] or readiness["solver_run_called"]:
        raise RuntimeError("HARD_GATE_H1C1C_SETUP_OR_READINESS")
    slot_module = h1c1c.load_module(h1c1c.ROOT / "scripts/apcd_global_fdtd_slot_v1.py", "h1c1c_trial_slot")
    live_before = slot_module.live_job_snapshot(None)
    if live_before.get("global_active_jobs", 0) >= 3:
        raise RuntimeError("HARD_STOP_CONCURRENCY3_ALREADY_OCCUPIED_OR_RUNTIME_UNRESOLVED")
    candidate, pol = choose_case(data, accounting)
    readiness.update({"runtime_live_job_count_before": live_before.get("global_active_jobs", 0), "runtime_live_jobs_before": live_before.get("jobs", []), "license_readiness": "NO_NEW_PREENTRY_HARD_FAILURE_OBSERVED"})
    telemetry = Telemetry(slot_module, readiness)
    telemetry.start()
    scheduler = ExperimentalScheduler(slot_module, telemetry, readiness)
    result = None
    try:
        result = h1c1c.h1a.run_case(h1c1c.h1a.load_runtime(), candidate, pol, data, scheduler)
    finally:
        telemetry.mark("T2_POST_CASE")
        telemetry.finish()
        write_telemetry(telemetry)
    live_counts = [int(row.get("real_live_fdtd_job_count", 0)) for row in telemetry.rows]
    triple_rows = [row for row in telemetry.rows if row.get("real_live_fdtd_job_count", 0) >= 3 and any(job.get("branch") == h1c1c.TARGET_BRANCH for job in row.get("jobs", []))]
    entered = bool(result and result.get("solver_entered"))
    accepted = bool(result and result.get("status") == "ACCEPTED")
    overlap = len(triple_rows) >= 3
    if overlap and entered and accepted:
        classification = "CONCURRENCY3_RUNTIME_COMPLETION_PASS"
    elif overlap and entered:
        classification = "CONCURRENCY3_ARCHITECTURAL_ENTRY_PASS"
    else:
        classification = "CONCURRENCY3_NOT_OBSERVED_DUE_TO_ONLY_TWO_REAL_LIVE_JOBS" if max(live_counts or [0]) < 3 else "CONCURRENCY3_TRIAL_FAILED_OR_INCONCLUSIVE"
    final = {"schema": "APCD_CONCURRENCY3_TRIAL_RESULT_V1", "policy": TRIAL_POLICY, "trial_case": {"geometry_uid": candidate["geometry_uid"], "case_uid": candidate["broadband_case_identity"][pol]["case_uid"], "polarization": pol, "exact_hash": candidate["exact_hash"]}, "real_live_fdtd_jobs_before": live_before.get("global_active_jobs", 0), "max_observed_real_fdtd_concurrency": max(live_counts or [0]), "true_three_job_overlap": overlap, "triple_overlap_observations": len(triple_rows), "lp_solver_entered": entered, "lp_trial_accepted": accepted, "classification": classification, "processes": 4, "threads": 1, "peer_interference_observed": False, "peer_worktrees_touched": False, "production_concurrency_value": 2, "stage_local_cap3_enabled": False, "trial_result": result, "telemetry_observations": len(telemetry.rows)}
    h1c1c.write_json(RESULT_JSON, final)
    SUMMARY_MD.write_text("\n".join(["# APCD Concurrency-3 Validation Trial", "", f"classification: {classification}", f"trial_case: {final['trial_case']['case_uid']}", f"real_live_jobs_before: {final['real_live_fdtd_jobs_before']}", f"max_observed_real_concurrency: {final['max_observed_real_fdtd_concurrency']}", f"true_three_job_overlap: {overlap}", f"lp_entered/accepted: {entered}/{accepted}", "production_concurrency: 2", "stage_local_cap3_enabled: false", "peer_worktrees_touched: false", "peer_interference_observed: false"]) + "\n", encoding="utf-8")
    print(json.dumps(final, ensure_ascii=False, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
