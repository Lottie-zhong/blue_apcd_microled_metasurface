import importlib.util
import json
import os
import sys
import threading
from contextlib import contextmanager
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "coupling_ml"))
PERSIST = __import__("postsolver_persistence_v1")
SCHEDULER_PATH = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_v1\scripts\coupling\apcd_global_fdtd_slot_v3.py")
SPEC = importlib.util.spec_from_file_location("w2w_test_scheduler", SCHEDULER_PATH)
SCHED = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SCHED)


def make_scheduler(tmp_path):
    return SCHED.GlobalSlotScheduler(tmp_path / "registry.json", process_provider=lambda: [])


def test_a_normal_acquire_completed_release(tmp_path):
    scheduler = make_scheduler(tmp_path)
    lease = scheduler.acquire("test", str(tmp_path), "w2w", "case-a", pid=os.getpid())
    lease.release("COMPLETED", solver_complete="2026-09-16T00:00:00Z")
    data = json.loads((tmp_path / "registry.json").read_text())
    assert data["active_slots"] == []
    assert data["history"][-1]["completion_release_state"] == "COMPLETED"


def test_b_release_retries_transient_lock_contention(tmp_path, monkeypatch):
    scheduler = make_scheduler(tmp_path)
    lease = scheduler.acquire("test", str(tmp_path), "w2w", "case-b", pid=os.getpid())
    real_lock = SCHED._impl.registry_lock
    attempts = []

    @contextmanager
    def flaky_lock(path, timeout_s=30.0):
        attempts.append(1)
        if len(attempts) <= 2:
            raise SCHED.SlotError("GLOBAL_SLOT_LOCK_BUSY")
        with real_lock(path, timeout_s=timeout_s):
            yield

    monkeypatch.setattr(SCHED._impl, "registry_lock", flaky_lock)
    lease.release("COMPLETED")
    assert len(attempts) == 3
    assert lease._released is True
    assert json.loads((tmp_path / "registry.json").read_text())["active_slots"] == []


def test_c_repeated_release_is_idempotent(tmp_path):
    scheduler = make_scheduler(tmp_path)
    lease = scheduler.acquire("test", str(tmp_path), "w2w", "case-c", pid=os.getpid())
    lease.release("COMPLETED")
    lease.release("COMPLETED")
    data = json.loads((tmp_path / "registry.json").read_text())
    assert len(data["history"]) == 1
    assert data["active_slots"] == []


def test_d_stale_entered_reconcile_then_next_acquisition(tmp_path):
    scheduler = make_scheduler(tmp_path)
    stale = scheduler.acquire("test", str(tmp_path), "w2w", "case-d", pid=99999999)
    stale.mark_solver_entered("2026-09-16T00:00:00Z")
    released = scheduler.reconcile_stale_slot(
        stale.slot_id,
        expected_case_uid="case-d",
        evidence={
            "solver_completed": True,
            "owner_processes_absent": True,
            "actual_completion_utc": "2026-09-16T00:01:00Z",
            "evidence_source": "sandbox-durable-completion",
        },
    )
    assert released["completion_release_state"] == "STALE_SLOT_AFTER_NATURAL_SOLVER_COMPLETION_CONTROLLER_LOST"
    next_lease = scheduler.acquire("test", str(tmp_path), "w2w", "case-d-next", pid=os.getpid())
    next_lease.release("TEST_NO_SOLVER")
    data = json.loads((tmp_path / "registry.json").read_text())
    assert data["active_slots"] == []
    assert data["history"][0]["case_uid"] == "case-d"


def test_e_live_owner_is_not_reconciled(tmp_path):
    scheduler = make_scheduler(tmp_path)
    live = scheduler.acquire("test", str(tmp_path), "w2w", "case-e", pid=os.getpid())
    live.mark_solver_entered()
    with pytest.raises(SCHED.StaleEnteredSlot, match="OWNER_STILL_ALIVE"):
        scheduler.reconcile_stale_slot(
            live.slot_id,
            expected_case_uid="case-e",
            evidence={"solver_completed": True, "owner_processes_absent": True},
        )
    assert json.loads((tmp_path / "registry.json").read_text())["active_slots"][0]["case_uid"] == "case-e"
    live.release("TEST_NO_SOLVER")


def test_f_two_slot_simultaneous_finalization(tmp_path):
    scheduler = make_scheduler(tmp_path)
    leases = [scheduler.acquire("test", str(tmp_path), "w2w", f"case-f-{i}", pid=os.getpid()) for i in range(2)]
    for lease in leases:
        lease.mark_solver_entered()
    threads = [threading.Thread(target=lease.release, args=("COMPLETED",)) for lease in leases]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    data = json.loads((tmp_path / "registry.json").read_text())
    assert data["active_slots"] == []
    assert sorted(row["case_uid"] for row in data["history"]) == ["case-f-0", "case-f-1"]


def test_g_release_exception_keeps_scientific_completion_auditable(tmp_path):
    setup = tmp_path / "setup.fsp"
    setup.write_bytes(b"setup")
    roles = PERSIST.ArtifactRoles(tmp_path / "frozen.fsp", tmp_path / "runtime.fsp", tmp_path / "post.fsp", tmp_path / "recovery.fsp")

    class Adapter:
        session_id = "owner-session"

        def open(self, path):
            return object()

        def run(self, handle):
            return None

        def save(self, handle, path):
            Path(path).write_bytes(b"persisted")

        def load_only(self, path, manifest):
            return {"ok": True, "identity_pass": True, "arrays_pass": True, "shape_pass": True, "sanity_pass": True, "run_called": False, "session_id": "independent-session"}

        def extract_raw(self, handle, post, raw):
            Path(raw).write_bytes(b"raw")

        def close(self, handle):
            return None

    controller = PERSIST.LifecycleController(
        job_id="job-g",
        attempt_id="attempt-001",
        roles=roles,
        events_path=tmp_path / "events.jsonl",
        completion_path=tmp_path / "completion.json",
        raw_path=tmp_path / "raw.bin",
        release_slot=lambda state: (_ for _ in ()).throw(PERSIST.LifecycleError("GLOBAL_SLOT_LOCK_BUSY")),
    )
    with pytest.raises(PERSIST.LifecycleError, match="GLOBAL_SLOT_LOCK_BUSY"):
        controller.execute(
            Adapter(),
            {"setup_pre_fsp": str(setup), "physical_contract_sha256": "contract"},
            lambda handle, post, raw: Path(raw).write_bytes(b"raw"),
            lambda raw: {"finite": True},
            lambda derived, post, raw: {"pass": True},
        )
    completion = json.loads((tmp_path / "completion.json").read_text())
    states = [json.loads(line)["state"] for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert completion["status"] == "COMPLETED"
    assert completion["slot_release_pending"] is True
    assert completion["slot_release_state"] == "RECONCILE_REQUIRED"
    assert "SLOT_RELEASE_PENDING" in states and "CONTROLLER_FAILURE" in states
    assert controller.run_invocation_count == 1
