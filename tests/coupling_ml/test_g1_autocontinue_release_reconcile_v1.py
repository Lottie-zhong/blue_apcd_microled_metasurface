import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = Path(r"D:/project/worktrees/blue_apcd_mdc_np_coupling_ml_v1/scripts/coupling_ml/apcd_coupling_2d3d_g1_matched_4case_3d_cylinder_phase_a_v1.py")
SPEC = importlib.util.spec_from_file_location("g1_runner_under_test", SOURCE)
G1 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(G1)


class FakeLease:
    def __init__(self, result):
        self.result = result

    def release(self, *args, **kwargs):
        return dict(self.result)


class FakeScheduler:
    def __init__(self, retries=()):
        self.retries = list(retries)
        self.release_calls = 0
        self.reconcile_calls = 0

    def release(self, *args, **kwargs):
        self.release_calls += 1
        return dict(self.retries.pop(0)) if self.retries else {"status": "PENDING_RECONCILE"}

    def reconcile_pending(self, evidence_provider=None):
        self.reconcile_calls += 1
        assert evidence_provider is G1.pending_scientific_evidence
        return [{"status": "RECONCILED", "slot_id": "GLOBAL_SLOT_1"}]


class FakeOwnedLease:
    def __init__(self, scheduler, row):
        self.scheduler = scheduler
        self.record = row
        self.slot_id = row["slot_id"]

    def release(self, *args, **kwargs):
        self.scheduler.owner_release_calls += 1
        result = dict(self.scheduler.owner_results.pop(0)) if self.scheduler.owner_results else {"status": "RELEASED"}
        if result.get("status") in {"RELEASED", "ALREADY_RELEASED"}:
            path = G1.REGISTRY
            data = json.loads(path.read_text(encoding="utf-8"))
            data["active_slots"] = [
                row for row in data.get("active_slots", []) if row.get("slot_id") != self.slot_id
            ]
            path.write_text(json.dumps(data), encoding="utf-8")
        return result


class OwnerScheduler:
    def __init__(self, owner_results=None, live_jobs=()):
        self.owner_results = list(owner_results or [{"status": "RELEASED"}])
        self.owner_release_calls = 0
        self.live_jobs = list(live_jobs)
        self.reconcile_calls = 0

    def capacity_snapshot(self):
        return {"live_jobs": self.live_jobs}

    def release(self, lease, *args, **kwargs):
        return lease.release(*args, **kwargs)

    def reconcile_pending(self, evidence_provider=None):
        self.reconcile_calls += 1
        return []


@pytest.fixture
def quiet(monkeypatch):
    monkeypatch.setattr(G1, "append_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(G1.time, "sleep", lambda _: None)


def finish(tmp_path, lease, scheduler):
    return G1.release_completed_with_reconcile(
        scheduler,
        lease,
        tmp_path,
        "2026-09-18T00:00:00Z",
        {"scientific_truth_valid": True, "solver_completed": True},
    )


def test_a_normal_release_allows_next_acquire(tmp_path, quiet):
    scheduler = FakeScheduler()
    result = finish(tmp_path, FakeLease({"status": "RELEASED"}), scheduler)
    assert G1.release_is_durable(result)
    assert scheduler.release_calls == 0


def test_b_pending_release_retries_then_reconciles(tmp_path, quiet):
    scheduler = FakeScheduler([{"status": "RELEASED"}])
    result = finish(tmp_path, FakeLease({"status": "PENDING_RECONCILE"}), scheduler)
    assert result["status"] == "RELEASED"
    assert result["recovery_action"] == "CANONICAL_RELEASE_RETRY"
    assert scheduler.release_calls == 1


def test_c_two_releases_are_independently_serialized(tmp_path, quiet):
    scheduler = FakeScheduler([{"status": "RELEASED"}, {"status": "RELEASED"}])
    first = finish(tmp_path, FakeLease({"status": "PENDING_RECONCILE"}), scheduler)
    second = finish(tmp_path, FakeLease({"status": "PENDING_RECONCILE"}), scheduler)
    assert [first["status"], second["status"]] == ["RELEASED", "RELEASED"]
    assert scheduler.release_calls == 2


def test_d_reconcile_before_acquire_is_canonical(tmp_path, quiet):
    scheduler = FakeScheduler()
    result = G1.reconcile_before_acquire(scheduler, tmp_path)
    assert result[0]["status"] == "RECONCILED"
    assert scheduler.reconcile_calls == 1


def test_e_foreign_branch_evidence_is_not_reconciled():
    assert G1.pending_scientific_evidence({"branch": "work/mdc-np-coupling-v1", "case_uid": "K6_NX5_NY1_Z"}) == {}


def test_f_pending_release_never_claims_completion_before_lease_release(tmp_path, quiet):
    scheduler = FakeScheduler()
    result = finish(tmp_path, FakeLease({"status": "PENDING_RECONCILE"}), scheduler)
    assert result["status"] == "PENDING_RECONCILE"
    assert not G1.release_is_durable(result)
    assert scheduler.reconcile_calls == 1


def test_g_ownership_mismatch_is_hard_gate(tmp_path, quiet):
    scheduler = FakeScheduler()
    result = finish(tmp_path, FakeLease({"status": "SLOT_OWNERSHIP_TOKEN_MISMATCH"}), scheduler)
    assert result["status"] == "SLOT_OWNERSHIP_TOKEN_MISMATCH"
    assert scheduler.release_calls == 0
    assert scheduler.reconcile_calls == 0


def test_h_already_released_is_idempotent(tmp_path, quiet):
    scheduler = FakeScheduler()
    result = finish(tmp_path, FakeLease({"status": "ALREADY_RELEASED"}), scheduler)
    assert result["status"] == "ALREADY_RELEASED"
    assert G1.release_is_durable(result)


def _owner_case(out, case_id, pid=None):
    case_dir = out / "cases" / case_id / "attempt_001"
    post = case_dir / "post" / f"{case_id}__attempt_001_post.fsp"
    raw = case_dir / "results" / "raw_field_payload.json"
    post.parent.mkdir(parents=True)
    raw.parent.mkdir(parents=True)
    post.write_bytes(b"post")
    raw.write_text("{}", encoding="utf-8")
    terminal = {
        "state": "COMPLETED", "status": "PHASE_A_3D_TRUTH_VALID",
        "post_fsp": str(post), "raw_result": str(raw),
        "completed_utc": "2026-09-18T00:00:00Z",
    }
    (case_dir / "terminal.json").write_text(json.dumps(terminal), encoding="utf-8")
    (case_dir / "scientific_validation.json").write_text(json.dumps({
        "status": "PASS", "load_only": "PASS", "projection": "PASS",
    }), encoding="utf-8")
    current_pid = pid or os.getpid()
    return {
        "slot_id": "GLOBAL_SLOT_1", "case_uid": case_id,
        "branch": G1.BRANCH, "attempt_id": "attempt_001",
        "pid": current_pid, "controller_pid": current_pid,
        "ownership_token": f"token-{case_id}",
        "entered_solver": True, "completion_release_state": "ACTIVE",
    }


def _write_registry(path, rows):
    path.write_text(json.dumps({"active_slots": rows}), encoding="utf-8")


@pytest.fixture
def owner_env(tmp_path, monkeypatch):
    out = tmp_path / "out"
    registry = tmp_path / "registry.json"
    monkeypatch.setattr(G1, "OUT", out)
    monkeypatch.setattr(G1, "REGISTRY", registry)
    monkeypatch.setattr(G1, "append_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(G1.time, "sleep", lambda _: None)
    monkeypatch.setattr(G1, "scheduler_module", lambda: SimpleNamespace(SlotLease=FakeOwnedLease))
    return out, registry


def test_i_owner_finalization_releases_completed_case_while_controller_lives(owner_env):
    out, registry = owner_env
    _write_registry(registry, [_owner_case(out, "W2H_A")])
    scheduler = OwnerScheduler()
    result = G1.finalize_owned_completed_leases(scheduler)
    assert result[0]["status"] == "RELEASED"
    assert scheduler.owner_release_calls == 1
    assert json.loads(registry.read_text())["active_slots"] == []


def test_j_owner_finalization_retries_lock_busy_without_reconcile_steal(owner_env):
    out, registry = owner_env
    _write_registry(registry, [_owner_case(out, "W2H_A")])
    scheduler = OwnerScheduler([{"status": "PENDING_RECONCILE"}, {"status": "RELEASED"}])
    result = G1.finalize_owned_completed_leases(scheduler)
    assert result[0]["status"] == "RELEASED"
    assert scheduler.owner_release_calls == 2
    assert scheduler.reconcile_calls == 0


def test_k_completed_case_frees_slot_for_next_case(owner_env):
    out, registry = owner_env
    scheduler = OwnerScheduler()
    _write_registry(registry, [_owner_case(out, "W2H_A")])
    assert G1.finalize_owned_completed_leases(scheduler)[0]["status"] == "RELEASED"
    _write_registry(registry, [_owner_case(out, "W2H_B")])
    assert G1.finalize_owned_completed_leases(scheduler)[0]["status"] == "RELEASED"
    assert scheduler.owner_release_calls == 2


def test_l_only_completed_case_is_finalized_when_other_case_is_live(owner_env):
    out, registry = owner_env
    _write_registry(registry, [_owner_case(out, "W2H_A"), _owner_case(out, "W2H_B")])
    scheduler = OwnerScheduler(live_jobs=[{"identity_text": "W2H_B", "case_uid": "W2H_B"}])
    result = G1.finalize_owned_completed_leases(scheduler)
    assert [x["case_uid"] for x in result] == ["W2H_A"]


def test_m_foreign_traditional_lease_is_untouched(owner_env):
    out, registry = owner_env
    row = _owner_case(out, "K6_TRADITIONAL")
    row["branch"] = "work/mdc-np-coupling-v1"
    _write_registry(registry, [row])
    scheduler = OwnerScheduler()
    assert G1.finalize_owned_completed_leases(scheduler) == []
    assert json.loads(registry.read_text())["active_slots"]


def test_n_owner_finalization_is_idempotent(owner_env):
    out, registry = owner_env
    _write_registry(registry, [_owner_case(out, "W2H_A")])
    scheduler = OwnerScheduler()
    assert G1.finalize_owned_completed_leases(scheduler)[0]["status"] == "RELEASED"
    assert G1.finalize_owned_completed_leases(scheduler) == []
    assert scheduler.owner_release_calls == 1


def test_o_token_or_scheduler_ownership_mismatch_never_claims_release(owner_env):
    out, registry = owner_env
    _write_registry(registry, [_owner_case(out, "W2H_A")])
    scheduler = OwnerScheduler([{"status": "SLOT_OWNERSHIP_TOKEN_MISMATCH"}])
    result = G1.finalize_owned_completed_leases(scheduler)
    assert result[0]["status"] == "SLOT_OWNERSHIP_TOKEN_MISMATCH"
    assert json.loads(registry.read_text())["active_slots"]


def test_p_ten_sequential_completed_cases_do_not_accumulate_active_leases(owner_env):
    out, registry = owner_env
    scheduler = OwnerScheduler()
    for i in range(10):
        _write_registry(registry, [_owner_case(out, f"W2H_SEQ_{i}")])
        result = G1.finalize_owned_completed_leases(scheduler)
        assert result[0]["status"] == "RELEASED"
        assert json.loads(registry.read_text())["active_slots"] == []
    assert scheduler.owner_release_calls == 10
