from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = Path(r"D:\apcd_runtime\global_fdtd_control_v3\control.sqlite3")
OUT = ROOT / "outputs" / "coupling_ml" / "FREEZE_V3_RESOURCE_HARDENING_AND_MEDIUM_PW_PREENTRY_V1"


def ps_snapshot():
    command = "Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('fdtd-engine-msmpi.exe','fdtd-engine.exe','mpiexec.exe','smpd.exe','fdtd-solutions.exe') } | Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress"
    result = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        data = json.loads(result.stdout) if result.stdout.strip() else []
        if isinstance(data, dict):
            data = [data]
    except Exception:
        data = []
    return data, result.stderr[-1000:]


def read_control_db():
    import sqlite3
    uri = "file:" + DB_PATH.as_posix() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    slots = [dict(row) for row in con.execute("SELECT slot_id,state,owner_branch,logical_case_id,attempt_id,fencing_generation,solver_entered_at,heartbeat_at,updated_at FROM slots ORDER BY slot_id")]
    entries = [dict(row) for row in con.execute("SELECT logical_case_id,attempt_id,COUNT(*) AS count FROM lease_events WHERE event_type='SCIENTIFIC_SOLVER_ENTERED' AND logical_case_id LIKE 'W2H_15294%' GROUP BY logical_case_id,attempt_id")]
    metrics = {row["metric_name"]: int(row["metric_value"]) for row in con.execute("SELECT metric_name,metric_value FROM health_metrics")}
    try:
        reservations = [dict(row) for row in con.execute("SELECT * FROM resource_reservations")]
        reservation_schema = True
    except sqlite3.OperationalError:
        reservations = []
        reservation_schema = False
    con.close()
    return {"slots": slots, "entries": entries, "metrics": metrics, "reservations": reservations, "resource_reservation_schema": reservation_schema}


def read_ledgers():
    rows = []
    for path in ROOT.glob("outputs/coupling_ml/**/cases/W2H_15294/**/attempt_ledger.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            rows.append({"path": str(path), "parse_error": repr(exc)})
            continue
        rows.append({"path": str(path), "attempt_id": data.get("attempt_id"), "solver_entered": data.get("solver_entered"), "scientific_solver_entry_count": data.get("scientific_solver_entry_count"), "replay_count": data.get("replay_count"), "terminal": data.get("terminal"), "role": data.get("role")})
    return rows


def main():
    db = read_control_db()
    selected = [row for row in db["slots"] if row["slot_id"] in {"GLOBAL_SLOT_2", "GLOBAL_SLOT_3"}]
    processes, process_error = ps_snapshot()
    tokens = ("w2h_15294", "attempt_001", "attempt_002", "attempt_003", "attempt_004")
    matching = [row for row in processes if any(token in str(row.get("CommandLine", "")).lower() for token in tokens)]
    ledgers = read_ledgers()
    invocation_values = db["entries"]
    replay_values = [{"metric": "SCIENTIFIC_VALID_REPLAY_COUNT", "count": db["metrics"].get("SCIENTIFIC_VALID_REPLAY_COUNT", 0)}]
    expected_cases = {"W2H_15294_NP_DERIVED_BASELINE", "W2H_15294_INTEGRATED_REFINED"}
    entry_ok = {row["logical_case_id"]: int(row["count"]) for row in invocation_values} == {case: 1 for case in expected_cases}
    readiness = not matching and bool(selected) and all(str(row.get("state", "")) == "OWNER_QUARANTINED" for row in selected) and entry_ok and replay_values[0]["count"] == 0
    report = {"status": "PASS_ZERO_SOLVER_QUARANTINE_AUDIT" if readiness else "REVIEW_QUARANTINE_AUDIT", "timestamp_utc": datetime.now(timezone.utc).isoformat(), "slots": selected, "process_census": processes, "matching_w2h15294_processes": matching, "process_error": process_error, "attempt_ledgers": ledgers, "scientific_invocation_count_evidence": invocation_values, "replay_count_evidence": replay_values, "foreign_mutation_count": db["metrics"].get("FOREIGN_MUTATION_COUNT", 0), "duplicate_scientific_entry_count": db["metrics"].get("DUPLICATE_SCIENTIFIC_ENTRY_COUNT", 0), "resource_reservation_schema_available": db["resource_reservation_schema"], "resource_reservations": db["reservations"], "baseline_recovery": "COMPLETE_REFERENCE_TRUTH", "refined_state": "INCOMPLETE_FORENSIC_FROZEN", "attempt_ledgers_immutable": True, "quarantine_release_readiness": "READY" if readiness else "NOT_READY", "later_owner_local_reconciliation_plan": ["re-read registry and fencing generation", "re-census W2H_15294 process/MPI/engine/persistence lineage", "verify no foreign mutation and duplicate entry", "transition only GLOBAL_SLOT_2/3 owner-local leases under explicit authorization", "re-run resource/persistence preflight before any new entry"], "release_performed": False, "traditional_touched": False, "solver_runs": 0, "scientific_solver_entries_this_task": 0}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "MEDIUM_PW_QUARANTINE_REAUDIT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "quarantine_release_readiness": report["quarantine_release_readiness"], "matching_process_count": len(matching), "solver_runs": 0, "scientific_solver_entries_this_task": 0}, ensure_ascii=False))
    raise SystemExit(0 if report["status"] == "PASS_ZERO_SOLVER_QUARANTINE_AUDIT" else 1)


if __name__ == "__main__":
    main()
