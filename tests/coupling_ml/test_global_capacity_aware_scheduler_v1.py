import importlib.util
import json
import os
import threading
from pathlib import Path

import pytest


SOURCE = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_v1\scripts\coupling\apcd_global_fdtd_slot_v1.py")
SPEC = importlib.util.spec_from_file_location("capacity_scheduler_under_test", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def scheduler(path):
    return MODULE.GlobalSlotScheduler(path, process_provider=lambda: [])


def row(slot_id, branch, case_uid, *, pid=None, entered=False, evidence=None):
    pid = os.getpid() if pid is None else pid
    return {
        "schema": "APCD_GLOBAL_FDTD_SLOT_V1",
        "slot_id": slot_id,
        "branch": branch,
        "case_uid": case_uid,
        "attempt_id": "test_attempt",
        "pid": pid,
        "controller_pid": pid,
        "entered": entered,
        "entered_solver": entered,
        "completion_release_state": "ACTIVE",
        "completion_evidence": evidence or {},
    }


def registry(path, rows=()):
    path.write_text(
        json.dumps(
            {
                "schema": "APCD_GLOBAL_FDTD_SLOT_REGISTRY_V1",
                "global_capacity": 3,
                "max_active_fdtd_per_branch": 3,
                "active_slots": list(rows),
                "history": [],
            }
        ),
        encoding="utf-8",
    )


def acquire(sched, branch, case_uid):
    return sched.acquire(
        branch,
        r"D:\sandbox\worktree",
        "scheduler-test",
        case_uid,
        pid=os.getpid(),
        metadata={"attempt_id": "test_attempt"},
    )


def test_a_traditional_one_allows_two_ml(tmp_path):
    path = tmp_path / "registry.json"
    registry(path)
    sched = scheduler(path)
    traditional = acquire(sched, "work/mdc-np-coupling-v1", "traditional")
    ml1 = acquire(sched, "work/mdc-np-coupling-ml-v1", "ml-1")
    ml2 = acquire(sched, "work/mdc-np-coupling-ml-v1", "ml-2")
    with pytest.raises(MODULE.SlotUnavailable, match="WAIT_BRANCH_ACTIVE_FDTD"):
        acquire(sched, "work/mdc-np-coupling-ml-v1", "ml-3")
    for lease in (ml2, ml1, traditional):
        lease.release("TEST_RELEASE")


def test_b_two_ml_allows_one_traditional(tmp_path):
    path = tmp_path / "registry.json"
    registry(path)
    sched = scheduler(path)
    ml1 = acquire(sched, "work/mdc-np-coupling-ml-v1", "ml-1")
    ml2 = acquire(sched, "work/mdc-np-coupling-ml-v1", "ml-2")
    traditional = acquire(sched, "work/mdc-np-coupling-v1", "traditional")
    for lease in (traditional, ml2, ml1):
        lease.release("TEST_RELEASE")


def test_c_global_cap_rejects_fourth(tmp_path):
    path = tmp_path / "registry.json"
    registry(
        path,
        [
            row("GLOBAL_SLOT_1", "work/existing-a", "a"),
            row("GLOBAL_SLOT_2", "work/existing-b", "b"),
            row("GLOBAL_SLOT_3", "work/existing-c", "c"),
        ],
    )
    with pytest.raises(MODULE.SlotUnavailable, match="WAIT_GLOBAL_FDTD_CAPACITY"):
        acquire(scheduler(path), "work/new", "new")


def test_d_race_for_final_slot_is_single_winner(tmp_path):
    path = tmp_path / "registry.json"
    registry(
        path,
        [
            row("GLOBAL_SLOT_1", "work/existing-a", "a"),
            row("GLOBAL_SLOT_2", "work/existing-b", "b"),
        ],
    )
    results = []
    barrier = threading.Barrier(2)

    def contender(branch, case_uid):
        barrier.wait()
        try:
            lease = acquire(scheduler(path), branch, case_uid)
            results.append(("ok", lease))
        except MODULE.SlotError as exc:
            results.append(("error", str(exc)))

    threads = [
        threading.Thread(target=contender, args=("work/race-a", "race-a")),
        threading.Thread(target=contender, args=("work/race-b", "race-b")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert len(results) == 2
    assert sum(result[0] == "ok" for result in results) == 1
    assert sum(result[0] == "error" and "WAIT_GLOBAL" in result[1] for result in results) == 1
    for kind, value in results:
        if kind == "ok":
            value.release("TEST_RELEASE")


def test_e_stale_pre_entry_does_not_block_two_free_slots(tmp_path):
    path = tmp_path / "registry.json"
    registry(path, [row("GLOBAL_SLOT_1", "work/stale", "stale", pid=999999)])
    sched = scheduler(path)
    first = acquire(sched, "work/mdc-np-coupling-ml-v1", "ml")
    second = acquire(sched, "work/mdc-np-coupling-v1", "traditional")
    snapshot = sched.capacity_snapshot()
    assert snapshot["global_live_or_reserved"] == 2
    assert snapshot["active_slots"][0]["case_uid"] in {"ml", "traditional"}
    second.release("TEST_RELEASE")
    first.release("TEST_RELEASE")


def test_f_ambiguous_slot_is_quarantined_but_other_slots_work(tmp_path):
    path = tmp_path / "registry.json"
    registry(path, [row("GLOBAL_SLOT_1", "work/unknown", "ambiguous", pid=999999, entered=True)])
    sched = scheduler(path)
    first = acquire(sched, "work/mdc-np-coupling-ml-v1", "ml")
    second = acquire(sched, "work/mdc-np-coupling-v1", "traditional")
    rows = {item["case_uid"]: item for item in sched.capacity_snapshot()["active_slots"]}
    assert rows["ambiguous"]["slot_state"] == "AMBIGUOUS_QUARANTINED"
    second.release("TEST_RELEASE")
    first.release("TEST_RELEASE")


def test_g_release_contention_does_not_block_other_slot(tmp_path, monkeypatch):
    path = tmp_path / "registry.json"
    registry(path)
    sched = scheduler(path)
    held = acquire(sched, "work/mdc-np-coupling-ml-v1", "held")
    lock = Path(str(path) + ".lock")
    lock.write_text(json.dumps({"pid": os.getpid(), "created_utc": "test"}), encoding="utf-8")
    monkeypatch.setattr(MODULE, "RELEASE_LOCK_TIMEOUT_S", 0.01)
    monkeypatch.setattr(MODULE, "RELEASE_RETRY_ATTEMPTS", 1)
    with pytest.raises(MODULE.SlotError, match="GLOBAL_SLOT_LOCK_BUSY"):
        held.release("TEST_RELEASE")
    lock.unlink()
    other = acquire(sched, "work/mdc-np-coupling-v1", "other")
    other.release("TEST_RELEASE")
    held._released = False
    held.release("TEST_RELEASE")


def test_h_branch_cap_reached_while_global_capacity_remains(tmp_path):
    path = tmp_path / "registry.json"
    registry(path)
    sched = scheduler(path)
    ml1 = acquire(sched, "work/mdc-np-coupling-ml-v1", "ml-1")
    ml2 = acquire(sched, "work/mdc-np-coupling-ml-v1", "ml-2")
    assert sched.capacity_snapshot()["global_live_or_reserved"] == 2
    with pytest.raises(MODULE.SlotUnavailable, match="WAIT_BRANCH_ACTIVE_FDTD"):
        acquire(sched, "work/mdc-np-coupling-ml-v1", "ml-3")
    ml2.release("TEST_RELEASE")
    ml1.release("TEST_RELEASE")


def test_i_release_is_idempotent(tmp_path):
    path = tmp_path / "registry.json"
    registry(path)
    sched = scheduler(path)
    lease = acquire(sched, "work/mdc-np-coupling-v1", "one")
    lease.release("TEST_RELEASE")
    lease.release("TEST_RELEASE")
    assert len(json.loads(path.read_text(encoding="utf-8"))["history"]) == 1


def test_j_stale_reconciliation_requires_and_records_evidence(tmp_path):
    path = tmp_path / "registry.json"
    registry(path, [row("GLOBAL_SLOT_1", "work/stale", "stale", pid=999999, entered=True)])
    released = scheduler(path).reconcile_stale_slot(
        "GLOBAL_SLOT_1",
        expected_case_uid="stale",
        evidence={
            "solver_completed": True,
            "owner_processes_absent": True,
            "actual_completion_utc": "2026-09-16T00:00:00Z",
        },
    )
    assert released["reconciliation_type"] == "ADDITIVE_STALE_SLOT_RECONCILIATION"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["active_slots"] == []
    assert data["history"][0]["completion_evidence"]["solver_completed"] is True


def test_k_registry_corruption_is_global_hard_stop(tmp_path):
    path = tmp_path / "registry.json"
    registry(
        path,
        [
            row("GLOBAL_SLOT_1", "work/a", "duplicate"),
            row("GLOBAL_SLOT_2", "work/b", "duplicate"),
        ],
    )
    with pytest.raises(MODULE.RegistryCorrupt, match="duplicate case ownership"):
        scheduler(path).capacity_snapshot()

