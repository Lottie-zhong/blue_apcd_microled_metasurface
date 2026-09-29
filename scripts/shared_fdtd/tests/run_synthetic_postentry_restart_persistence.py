from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_snapshot(path: Path) -> dict:
    return {
        "path": str(path),
        "exists": path.is_file(),
        "size_bytes": path.stat().st_size if path.is_file() else None,
        "sha256": sha256_file(path) if path.is_file() else None,
    }


def load_backend(backend_root: Path):
    scripts = backend_root / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from shared_fdtd.control_v3.allocator import Allocator
    from shared_fdtd.control_v3.db import ControlDB
    from shared_fdtd.engine.dispatcher import enqueue
    from shared_fdtd.engine.event_log import append_event, read_events
    from shared_fdtd.engine.reconciler import closeout_owned_postentry_no_truth
    return Allocator, ControlDB, enqueue, append_event, read_events, closeout_owned_postentry_no_truth


def run_phase_entry(root: Path, backend_root: Path, case_id: str, attempt_id: str) -> dict:
    Allocator, ControlDB, enqueue, append_event, read_events, _ = load_backend(backend_root)
    db_path = root / "control.sqlite3"
    attempt_root = root / "cases" / case_id / attempt_id
    attempt_root.mkdir(parents=True, exist_ok=True)
    db = ControlDB(db_path)
    payload = {
        "attempt_root": str(attempt_root),
        "synthetic_postentry_restart": True,
        "production_science": False,
        "solver_invocations": 0,
    }
    enqueue(db, "coupling_ml", case_id, attempt_id, payload)
    lease = Allocator(db).acquire("coupling_ml", case_id, attempt_id)
    launch_identity = {
        "launch_id": "synthetic-postentry-" + case_id.lower(),
        "host_pid": 0,
        "solver_pid": 0,
        "process_identity": "synthetic-postentry-marker",
        "command_hash": "synthetic-no-solver",
        "executable_path": "SYNTHETIC_NO_FDTD",
        "synthetic": True,
    }
    entry_result = Allocator(db).mark_entered(lease, launch_identity=launch_identity)
    events = attempt_root / "events.jsonl"
    append_event(
        events,
        "SCIENTIFIC_SOLVER_ENTERED",
        launch_identity=launch_identity,
        synthetic=True,
        solver_invocations=0,
        scientific_entry_count=1,
        replay=0,
    )
    append_event(
        events,
        "SYNTHETIC_POSTENTRY_MARKER",
        marker="R1_ENTRY_AFTER",
        launch_identity=launch_identity,
        synthetic=True,
        solver_invocations=0,
        scientific_entry_count=1,
        replay=0,
    )
    append_event(events, "SOLVER_RETURNED", synthetic=True, solver_invocations=0, replay=0)
    append_event(
        events,
        "POSTENTRY_FAILURE_ADJUDICATED",
        synthetic=True,
        reason="SYNTHETIC_RESTART_R6",
        replay=0,
    )
    append_event(
        events,
        "TRUTH_PRESERVATION_COMPLETE",
        synthetic=True,
        truth_durable=False,
        replay=0,
    )
    append_event(
        events,
        "CONTROLLER_TERMINATED_SYNTHETIC",
        synthetic=True,
        restart_required=True,
        replay=0,
    )
    with db.connect(readonly=True) as con:
        slot = dict(con.execute("SELECT * FROM slots WHERE slot_id=?", (lease.slot_id,)).fetchone())
        queue = dict(
            con.execute(
                "SELECT logical_case_id,attempt_id,state,slot_id,fencing_generation "
                "FROM branch_queue WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
                ("coupling_ml", case_id, attempt_id),
            ).fetchone()
        )
        entry_count = con.execute(
            "SELECT COUNT(*) FROM lease_events WHERE branch_id=? AND logical_case_id=? "
            "AND attempt_id=? AND event_type='SCIENTIFIC_SOLVER_ENTERED'",
            ("coupling_ml", case_id, attempt_id),
        ).fetchone()[0]
    return {
        "phase": "entry",
        "returncode": 0,
        "entry_result": entry_result,
        "case_id": case_id,
        "attempt_id": attempt_id,
        "attempt_root": str(attempt_root),
        "lease_slot_id": lease.slot_id,
        "lease_fencing_generation": lease.fencing_generation,
        "slot_after_entry": slot,
        "queue_after_entry": queue,
        "db_scientific_entry_events": entry_count,
        "event_types": [row["event_type"] for row in read_events(events)],
        "solver_invocations": 0,
        "replay": 0,
    }


def run_phase_resume(root: Path, backend_root: Path, case_id: str, attempt_id: str, phase: str) -> dict:
    Allocator, ControlDB, _, append_event, read_events, closeout = load_backend(backend_root)
    db = ControlDB(root / "control.sqlite3")
    attempt_root = root / "cases" / case_id / attempt_id
    events = attempt_root / "events.jsonl"
    before = read_events(events)
    result = closeout(
        db,
        "coupling_ml",
        {(case_id, attempt_id): attempt_root},
        process_probe=lambda _state: [],
        reason="SYNTHETIC_RESTART_R6_NO_TRUTH",
    )
    after = read_events(events)
    with db.connect(readonly=True) as con:
        slot_rows = [dict(row) for row in con.execute("SELECT * FROM slots ORDER BY slot_id")]
        queue = dict(
            con.execute(
                "SELECT logical_case_id,attempt_id,state,slot_id,fencing_generation "
                "FROM branch_queue WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
                ("coupling_ml", case_id, attempt_id),
            ).fetchone()
        )
        entry_count = con.execute(
            "SELECT COUNT(*) FROM lease_events WHERE branch_id=? AND logical_case_id=? "
            "AND attempt_id=? AND event_type='SCIENTIFIC_SOLVER_ENTERED'",
            ("coupling_ml", case_id, attempt_id),
        ).fetchone()[0]
        release_count = con.execute(
            "SELECT COUNT(*) FROM lease_events WHERE branch_id=? AND logical_case_id=? "
            "AND attempt_id=? AND event_type='LEASE_RELEASED'",
            ("coupling_ml", case_id, attempt_id),
        ).fetchone()[0]
    terminal_path = attempt_root / "terminal.json"
    terminal = json.loads(terminal_path.read_text(encoding="utf-8")) if terminal_path.is_file() else None
    return {
        "phase": phase,
        "returncode": 0,
        "closeout_result": result,
        "events_before": len(before),
        "events_after": len(after),
        "event_types_after": [row["event_type"] for row in after],
        "entry_count": entry_count,
        "release_count": release_count,
        "slot_rows": slot_rows,
        "queue": queue,
        "terminal": terminal,
        "solver_invocations": 0,
        "replay": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--production-db", required=True)
    parser.add_argument("--backend-root", required=True)
    parser.add_argument("--isolated-root", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--child", choices=("entry", "resume", "repeat"))
    parser.add_argument("--case-id")
    parser.add_argument("--attempt-id", default="attempt_001")
    args = parser.parse_args()

    production_db = Path(args.production_db)
    backend_root = Path(args.backend_root)
    isolated_root = Path(args.isolated_root)
    report_path = Path(args.report)

    if args.child:
        if not args.case_id:
            raise SystemExit("--case-id is required for child phases")
        if args.child == "entry":
            result = run_phase_entry(isolated_root, backend_root, args.case_id, args.attempt_id)
        else:
            result = run_phase_resume(isolated_root, backend_root, args.case_id, args.attempt_id, args.child)
        print(json.dumps(result, ensure_ascii=True, default=str))
        return 0

    isolated_root.mkdir(parents=True, exist_ok=False)
    production_before = file_snapshot(production_db)
    production_snapshot = isolated_root / "production_snapshot.sqlite3"
    shutil.copy2(production_db, production_snapshot)
    if sha256_file(production_snapshot) != production_before["sha256"]:
        raise RuntimeError("production DB snapshot hash mismatch")
    isolated_db = isolated_root / "control.sqlite3"
    _, ControlDB, _, _, _, _ = load_backend(backend_root)
    schema_path = backend_root / "scripts" / "shared_fdtd" / "control_v3" / "schema.sql"
    ControlDB(isolated_db).initialize(schema_path)
    case_id = "SYNTH_POSTENTRY_RESTART_" + time.strftime("%Y%m%d_%H%M%S")
    attempt_id = args.attempt_id
    child_results = []
    for phase in ("entry", "resume", "repeat"):
        child = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--production-db",
                str(production_db),
                "--backend-root",
                str(backend_root),
                "--isolated-root",
                str(isolated_root),
                "--report",
                str(report_path),
                "--child",
                phase,
                "--case-id",
                case_id,
                "--attempt-id",
                attempt_id,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        child_results.append(
            {
                "phase": phase,
                "returncode": child.returncode,
                "stdout": child.stdout,
                "stderr": child.stderr,
            }
        )
        if child.returncode != 0:
            break
    production_after = file_snapshot(production_db)
    entry = child_results[0] if child_results else {}
    resume = child_results[1] if len(child_results) > 1 else {}
    repeat = child_results[2] if len(child_results) > 2 else {}
    try:
        entry_json = json.loads(entry.get("stdout", "{}"))
    except json.JSONDecodeError:
        entry_json = {}
    try:
        resume_json = json.loads(resume.get("stdout", "{}"))
    except json.JSONDecodeError:
        resume_json = {}
    try:
        repeat_json = json.loads(repeat.get("stdout", "{}"))
    except json.JSONDecodeError:
        repeat_json = {}
    isolated_db_after = file_snapshot(isolated_db)
    terminal_path = isolated_root / "cases" / case_id / attempt_id / "terminal.json"
    events_path = isolated_root / "cases" / case_id / attempt_id / "events.jsonl"
    event_rows = []
    if events_path.is_file():
        _, _, _, _, read_events, _ = load_backend(backend_root)
        event_rows = read_events(events_path)
    with (isolated_root / "control.sqlite3").open("rb"):
        pass
    report = {
        "schema": "SHARED_V3_SYNTHETIC_POSTENTRY_RESTART_V1",
        "classification": "ISOLATED_SYNTHETIC_POSTENTRY_RESTART_NO_SOLVER",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "backend": {
            "root": str(backend_root),
            "manifest": str(backend_root / "manifest.json"),
            "manifest_sha256": sha256_file(backend_root / "manifest.json"),
            "commit_dir": backend_root.name,
        },
        "production_db_before": production_before,
        "production_db_after": production_after,
        "production_db_unchanged": production_before == production_after,
        "isolated_root": str(isolated_root),
        "isolated_db_mode": "fresh_schema_fixture_after_production_snapshot",
        "isolated_db_note": "The production DB is copied to production_snapshot.sqlite3 and never mutated; the test control.sqlite3 is initialized from the deployed backend schema so historical global hold/duplicate health blockers cannot be treated as a restart failure.",
        "production_db_snapshot": file_snapshot(isolated_root / "production_snapshot.sqlite3"),
        "isolated_db_after": isolated_db_after,
        "case_id": case_id,
        "attempt_id": attempt_id,
        "child_processes": child_results,
        "entry_phase": entry_json,
        "resume_phase": resume_json,
        "repeat_phase": repeat_json,
        "event_types": [row["event_type"] for row in event_rows],
        "scientific_solver_entered_event_count": sum(
            row.get("event_type") == "SCIENTIFIC_SOLVER_ENTERED" for row in event_rows
        ),
        "replay_event_count": sum(
            int(row.get("replay", 0) or 0) for row in event_rows
        ),
        "lease_released_event_count": int(resume_json.get("release_count", 0)),
        "terminal_path": str(terminal_path),
        "terminal_exists": terminal_path.is_file(),
        "terminal": json.loads(terminal_path.read_text(encoding="utf-8")) if terminal_path.is_file() else None,
        "solver_invocations": 0,
        "gpu_or_fdtd_launched": False,
        "pass_conditions": {
            "production_db_unchanged": production_before == production_after,
            "production_snapshot_matches": sha256_file(isolated_root / "production_snapshot.sqlite3") == production_before["sha256"],
            "entry_count_exactly_one": sum(row.get("event_type") == "SCIENTIFIC_SOLVER_ENTERED" for row in event_rows) == 1,
            "replay_count_zero": sum(int(row.get("replay", 0) or 0) for row in event_rows) == 0,
            "lease_release_once": int(resume_json.get("release_count", 0)) == 1,
            "terminal_postentry_no_truth": bool(terminal_path.is_file() and json.loads(terminal_path.read_text(encoding="utf-8")).get("status") == "POSTENTRY_NO_TRUTH"),
            "repeat_has_no_new_release": bool(repeat_json.get("release_count") == 1),
            "all_child_processes_passed": bool(child_results) and all(x["returncode"] == 0 for x in child_results),
        },
    }
    report["status"] = "PASS" if all(report["pass_conditions"].values()) else "FAIL"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": str(report_path), "case_id": case_id}, ensure_ascii=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
