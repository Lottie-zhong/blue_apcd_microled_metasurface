import importlib.util
import json
import os

import pytest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("lp_h1a_probe", ROOT / "scripts/lp_global_h_h1a_probe_v1.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MOD)


def test_h500_is_not_scheduled():
    anchors, _ = MOD.load_anchors()
    planned = MOD.planned_cases(anchors)
    assert len(anchors) == 6
    assert len(planned) == 48
    assert {row["H_global_nm"] for row in planned} == {400.0, 450.0, 550.0, 600.0}


def test_unified_height_contract_and_bottom_plane():
    contract = MOD.RUNNER.unified_h_geometry_contract(450.0)
    assert contract["J1_H_nm"] == contract["J2_H_nm"] == 450.0
    assert contract["bottom_plane_nm"] == 0.0
    assert contract["source_z_nm"] == -250.0
    assert contract["monitor_z_nm"] == 1000.0
    assert contract["period_x_nm"] == contract["period_y_nm"] == 432.0


def test_case_identity_binds_height_and_exact_hash():
    anchors, _ = MOD.load_anchors()
    left = MOD.case_identity(anchors[0], 400.0, "x", "head")
    right = MOD.case_identity(anchors[0], 450.0, "x", "head")
    assert left["H_global_nm"] == 400.0
    assert left["exact_geometry_hash_sha256"] == anchors[0]["exact_geometry_hash_sha256"]
    assert MOD.sha256_obj(left) != MOD.sha256_obj(right)


def test_circular_delta_and_central_residual():
    assert MOD.circ_diff(5.0, 355.0) == 10.0
    assert MOD.circ_diff(355.0, 5.0) == -10.0
    central = MOD.circular_central([359.0, 1.0])
    assert min(abs(MOD.circ_diff(central, 0.0)), abs(MOD.circ_diff(central, 360.0))) < 1e-9
    residuals = MOD.circular_residuals([359.0, 1.0], central)
    assert max(abs(value) for value in residuals) <= 1.0


def test_local_sensitivity_uses_circular_finite_difference():
    values = {400.0: 359.0, 450.0: 1.0, 500.0: 3.0, 550.0: 5.0, 600.0: 7.0}
    assert MOD.local_sensitivity(values, 400.0) == 0.04
    assert MOD.local_sensitivity(values, 500.0) == 0.04


def test_fixed_h_grouping_and_x_only_exclusion():
    anchors, _ = MOD.load_anchors()
    phi = []
    full = []
    for anchor in anchors[:2]:
        for height in MOD.ALL_HEIGHTS_NM:
            phi.append({"authoritative_id": anchor["authoritative_id"], "geometry_hash_sha256": anchor["exact_geometry_hash_sha256"], "H_global_nm": height, "delta_phi_vs_H500_deg": 0.0})
            full.append({"authoritative_id": anchor["authoritative_id"], "geometry_hash_sha256": anchor["exact_geometry_hash_sha256"], "H_global_nm": height, "Jones_complete": True, "phase_wrapped_deg": 10.0 + height / 100.0, "projection_error_apcd_v1": 0.01, "Txx": 0.9})
    _, spans = MOD.interaction_tables(phi, full, 2)
    assert [row["H_global_nm"] for row in spans] == list(MOD.ALL_HEIGHTS_NM)
    assert all(row["full_jones_count"] == 2 for row in spans)
    x = {"rows": [{"weighted_Ex_real": 1.0, "weighted_Ex_imag": 0.0}], "case_id": "x"}
    phase = MOD.phase_only_row(anchors[0], 400.0, x, "test")
    assert phase["Jones_complete"] is False
    assert phase["projector_eligible"] is False


def test_exact_hash_and_entered_case_protection(tmp_path):
    anchors, _ = MOD.load_anchors()
    anchor = anchors[0]
    identity = MOD.case_identity(anchor, 400.0, "x", "head")
    MOD.RUNTIME = tmp_path
    result = MOD.run_case(None, anchor, 400.0, "x", "head", MOD.physical_contract("head"), [{"solver_entered": True, "case_identity_sha256": MOD.sha256_obj(identity)}])
    assert result["status"] == "QUARANTINED_ENTERED_NO_RECOVERY"
    assert result["solver_entered"] is True


def test_duplicate_runner_guard_rejects_active_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(MOD, "OUT", tmp_path)
    guard = MOD.acquire_runner_guard("run-1", "branch-1", "execute", "head")
    try:
        with pytest.raises(RuntimeError, match="ACTIVE_H1A_RUNNER_ALREADY_EXISTS"):
            MOD.acquire_runner_guard("run-1", "branch-1", "execute", "head")
    finally:
        MOD.release_runner_guard(guard)


def test_stale_guard_known_ownership_recovered(tmp_path, monkeypatch):
    monkeypatch.setattr(MOD, "OUT", tmp_path)
    payload = {
        "stage": "H1A",
        "run_identity": "run-1",
        "owner_pid": 999999999,
        "worktree": str(MOD.ROOT),
        "branch": "branch-1",
    }
    MOD.atomic_json(MOD.runner_guard_path(), payload)
    guard = MOD.acquire_runner_guard("run-1", "branch-1", "readiness-only")
    MOD.release_runner_guard(guard)
    assert not MOD.runner_guard_path().exists()


def test_stale_guard_unknown_ownership_blocks(tmp_path, monkeypatch):
    monkeypatch.setattr(MOD, "OUT", tmp_path)
    MOD.atomic_json(MOD.runner_guard_path(), {
        "stage": "H1A",
        "run_identity": "other-run",
        "owner_pid": 999999999,
        "worktree": r"D:\other-worktree",
        "branch": "other-branch",
    })
    with pytest.raises(RuntimeError, match="HARD_GATE_STALE_H1A_RUNNER_GUARD_UNKNOWN_OWNERSHIP"):
        MOD.acquire_runner_guard("run-1", "branch-1", "execute")


def test_readiness_failure_is_not_ready(tmp_path, monkeypatch):
    monkeypatch.setattr(MOD, "OUT", tmp_path)

    def fail():
        raise RuntimeError("appOpen error: Failed to start messaging, check licenses")

    result = MOD.run_readiness_probe(fail, snapshot_fn=lambda: {"status": "PASS", "processes": []})
    assert result["latest_verdict"] == "LICENSE_OR_MESSAGING_UNAVAILABLE"
    assert result["license_readiness_probe_attempts"] == 1
    assert result["solver_entered"] is False
    assert result["physics_attempt"] is False
    assert result["fsp_created"] is False


def test_readiness_success_closes_session(tmp_path, monkeypatch):
    monkeypatch.setattr(MOD, "OUT", tmp_path)

    class Session:
        closed = False

        def close(self):
            self.closed = True

    session = Session()
    result = MOD.run_readiness_probe(lambda: session, snapshot_fn=lambda: {"status": "PASS", "processes": []})
    assert result["latest_verdict"] == "LUMERICAL_READY"
    assert result["attempts"][-1]["session_closed"] is True
    assert session.closed is True
    assert result["solver_entered"] is False


def test_global_infrastructure_failure_fails_fast():
    anchors = [{"authoritative_id": "a"}, {"authoritative_id": "b"}]
    calls = []

    def run_one(anchor, height, pol):
        calls.append((anchor["authoritative_id"], height, pol))
        return {"status": "FAILED", "solver_entered": False, "failure_scope": "GLOBAL_INFRASTRUCTURE"}

    scheduled = MOD.schedule_case_results(anchors, run_one)
    assert len(scheduled) == 1
    assert len(calls) == 1


def test_retry_uses_new_attempt_identity(tmp_path):
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    first = case_dir / "attempt_provenance.json"
    first.write_text(json.dumps({"attempt_id": "case_attempt_001"}), encoding="utf-8")
    attempt_id, provenance, pre_fsp = MOD.next_attempt_artifacts(case_dir, "case")
    assert attempt_id == "case_attempt_002"
    assert provenance.name == "attempt_provenance_attempt_002.json"
    assert pre_fsp.name == "case_attempt_002_pre.fsp"

def test_run_case_releases_slot_before_extraction(tmp_path, monkeypatch):
    events=[]
    monkeypatch.setattr(MOD, "OUT", tmp_path / "out")
    monkeypatch.setattr(MOD, "RUNTIME", tmp_path / "runtime")
    monkeypatch.setattr(MOD, "current_branch", lambda: "work/lp-global-h-manifold-v1")
    monkeypatch.setattr(MOD, "setup_gate", lambda *args: {"pass": True, "checks": {}})
    monkeypatch.setattr(MOD.RUNNER, "build", lambda *args, **kwargs: {"pass": True})
    monkeypatch.setattr(MOD.RUNNER, "extract_broadband", lambda f: (events.append("extract") or ([{"weighted_Ex_real": 1.0, "weighted_Ex_imag": 0.0, "weighted_Ey_real": 0.0, "weighted_Ey_imag": 0.0}], {"pass": True})))

    class FakeFDTD:
        count=0
        def __init__(self, *args, **kwargs):
            FakeFDTD.count += 1
            self.index=FakeFDTD.count
        def save(self, path): Path(path).write_text("pre", encoding="utf-8")
        def close(self): events.append(f"close{self.index}")
        def load(self, path): events.append("load")
        def setresource(self, *args): events.append(("setresource", args[-2:]))
        def run(self): events.append("run")

    class FakeLumapi:
        FDTD=FakeFDTD

    class Runtime:
        lumapi=FakeLumapi
        hide_gui=True

    class Lease:
        slot_id="GLOBAL_SLOT_1"
        record={"slot_acquire_time":"t-acquire", "concurrent_peer_branch":["NP"], "admission_snapshot":{"effective_global_active_jobs_before_acquire":1}}
        def start_heartbeat(self): events.append("heartbeat_start")
        def mark_solver_entered(self, stamp): events.append("entered_marker")
        def release(self, state, solver_complete=None): events.append(("release", state))

    class Scheduler:
        def acquire_wait(self, **kwargs): events.append("acquire"); return Lease()

    anchor={"authoritative_id":"A","anchor_role":"role","exact_geometry_hash_sha256":"a"*64}
    result=MOD.run_case(Runtime(), anchor, 400.0, "x", "head", {"contract": True}, [], scheduler=Scheduler())
    assert result["status"]=="ACCEPTED"
    assert result["solver_entered"] is True
    assert result["slot_id"]=="GLOBAL_SLOT_1"
    assert events.index("acquire") < events.index("entered_marker") < events.index("run")
    assert events.index(("release", "SOLVER_COMPLETED")) < events.index("extract")
    assert result["concurrent_peer_branch"]==["NP"]
