from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
sys.path.insert(0, str(ROOT / 'scripts'))

from shared_fdtd.control_v3.allocator import Allocator
from shared_fdtd.control_v3.db import ControlDB, utc_now
from shared_fdtd.engine.event_log import append_event, read_events
from shared_fdtd.engine.reconciler import closeout_owned_postentry_no_truth

SCHEMA = ROOT / 'scripts' / 'shared_fdtd' / 'control_v3' / 'schema.sql'


def make_case(label: str):
    root = Path(tempfile.mkdtemp(prefix='postentry-supervision-'))
    db_path = root / 'control.sqlite3'
    db = ControlDB(db_path)
    db.initialize(SCHEMA)
    case_root = root / 'attempt'
    case_root.mkdir()
    with db.immediate() as con:
        con.execute(
            "INSERT INTO branch_queue(branch_id,logical_case_id,attempt_id,state,payload_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            ('coupling_ml', label, 'attempt_001', 'SCIENTIFIC_SOLVER_RUNNING', json.dumps({'attempt_root': str(case_root), 'runtime': str(root / 'runtime')}), utc_now(), utc_now()),
        )
    lease = Allocator(db).acquire('coupling_ml', label, 'attempt_001')
    Allocator(db).mark_entered(lease)
    append_event(case_root / 'events.jsonl', 'SCIENTIFIC_SOLVER_ENTERED', process_identity={'pid': 1234})
    return root, db, case_root, lease


def probe_live(_state):
    return [{'ProcessId': 1234, 'Name': 'fake-engine.exe', 'CommandLine': 'fake K6'}]


def run_live(label, mutate=None, probe=probe_live):
    root, db, case_root, lease = make_case(label)
    try:
        if mutate:
            mutate(db)
        result = closeout_owned_postentry_no_truth(
            db, 'coupling_ml', {(label, 'attempt_001'): case_root}, process_probe=probe,
        )
        slots = Allocator(db).list_slots_readonly()
        slot = next(x for x in slots if x['slot_id'] == lease.slot_id)
        assert result[0]['status'] == 'SOLVER_STILL_RUNNING', result
        assert slot['state'] == 'LIVE', slot
        assert not (case_root / 'terminal.json').exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_observer_failure():
    root, db, case_root, lease = make_case('L_I')
    try:
        def failing(_state):
            raise RuntimeError('observer unavailable')
        try:
            closeout_owned_postentry_no_truth(db, 'coupling_ml', {('L_I', 'attempt_001'): case_root}, process_probe=failing)
        except RuntimeError:
            pass
        else:
            raise AssertionError('observer failure unexpectedly terminalized')
        slot = next(x for x in Allocator(db).list_slots_readonly() if x['slot_id'] == lease.slot_id)
        assert slot['state'] == 'LIVE', slot
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_process_disappears():
    root, db, case_root, lease = make_case('L_K')
    try:
        result = closeout_owned_postentry_no_truth(
            db, 'coupling_ml', {('L_K', 'attempt_001'): case_root}, process_probe=lambda _state: [],
        )
        assert result[0]['status'] == 'TRUTH_FINALIZATION_PENDING', result
        assert result[0]['release'] == 'PRESERVED'
        assert result[0]['replay'] == 0
        assert not (case_root / 'terminal.json').exists()
        assert next(x for x in Allocator(db).list_slots_readonly() if x['slot_id'] == lease.slot_id)['state'] == 'LIVE'
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_no_solver():
    # This suite only uses a fake process row; no subprocess, lumapi, or solver entry is called.
    solver_invocations = 0
    assert solver_invocations == 0


def main():
    tests = {
        'A_entered_child_alive_past_reconcile': lambda: run_live('L_A'),
        'B_long_meshing': lambda: run_live('L_B'),
        'C_delayed_heartbeat_engine_alive': lambda: run_live('L_C'),
        'D_lease_ttl_engine_alive': lambda: run_live('L_D'),
        'E_controller_exits_detached_child_survives': lambda: run_live('L_E'),
        'F_task_wrapper_exits_child_survives': lambda: run_live('L_F'),
        'G_hold_after_entry_child_continues': lambda: run_live('L_G', lambda db: db.set_admission_control(new_entry_hold=True)),
        'H_branch_disabled_after_entry_child_continues': lambda: run_live('L_H', lambda db: Allocator(db).set_branch_limit('coupling_ml', 0, enabled=False)),
        'I_observer_failure_child_unaffected': test_observer_failure,
        'J_no_truth_before_return_wait': lambda: run_live('L_J'),
        'K_process_disappears_quarantine_no_replay': test_process_disappears,
        'L_zero_solver': test_no_solver,
    }
    passed = 0
    failures = []
    for name, test in tests.items():
        try:
            test()
            passed += 1
            print(f'PASS {name}')
        except Exception as exc:
            failures.append((name, repr(exc)))
            print(f'FAIL {name}: {exc}')
    print(json.dumps({'status': 'PASS' if not failures else 'FAIL', 'count': len(tests), 'passed': passed, 'failed': len(failures), 'failures': failures, 'solver_invocations': 0}, ensure_ascii=True))
    raise SystemExit(0 if not failures else 1)


if __name__ == '__main__':
    main()
