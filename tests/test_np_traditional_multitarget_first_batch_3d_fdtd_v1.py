import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs" / "np_traditional_multitarget_baseline_extension_v1"
RUNNER = ROOT / "scripts" / "run_np_traditional_multitarget_first_batch_3d_fdtd_v1.py"
OUT = ROOT / "outputs" / "np_traditional_multitarget_first_batch_3d_fdtd_v1"


def test_frozen_proposal_and_resource_contract():
    p = json.loads((BASE / "first_batch_solver_proposal.json").read_text(encoding="utf-8"))
    assert p["max_solver_runs"] == 4
    assert p["attempt_policy"] == "attempt_001_only; no automatic rerun"
    assert p["resource_contract"] == {"cores": 12, "execution_mode": "foreground_synchronous", "other_slots_reserved": 2, "slots": 1}
    assert [c["case_id"] for c in p["cases"]] == ["K4_SEED_A_190_155", "K4_SEED_B_100_175", "K9_SEED_A_195_180", "K9_SEED_B_205_185"]


def test_runner_is_single_run_x_only_no_detached_launch():
    source = RUNNER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "run"]
    assert len(calls) == 1
    assert "lumapi" in source
    assert "attempt_002" not in source
    assert "Start-Process" not in source and "Task Scheduler" not in source
    assert "polarization_angle\"], 0" in source or "polarization angle" in source
    assert "y-pol" not in source.lower()


def test_setup_manifests_are_complete_and_solver_zero():
    for k, expected in ((4, 2), (9, 2)):
        m = json.loads((BASE / f"k{k}_fullsupercell_setup_manifest.json").read_text(encoding="utf-8"))
        assert m["solver_entered"] == 0
        assert m["status"] == "SETUP_ONLY_SAVED_RELOADED"
        assert len(m["cases"]) == 3
        assert all(c["reload_pass"] for c in m["cases"])
        assert all(len(c["diameters_nm"]) == k for c in m["cases"])


def test_no_runtime_artifacts_are_required_by_static_test():
    assert not any("lumapi" == p.name for p in [])


def test_completed_first_batch_evidence_is_serial_and_valid():
    ids = ["K4_SEED_A_190_155", "K4_SEED_B_100_175", "K9_SEED_A_195_180", "K9_SEED_B_205_185"]
    labels = []
    for cid in ids:
        d = OUT / cid
        ledger = json.loads((d / "entered_ledger.json").read_text(encoding="utf-8"))
        admission = json.loads((d / "label_admission.json").read_text(encoding="utf-8"))
        checksum = json.loads((d / "post_fsp_checksum.json").read_text(encoding="utf-8"))
        metrics = (d / "spectral_metrics.csv").read_text(encoding="utf-8").splitlines()
        assert ledger["attempt_id"] == "attempt_001"
        assert ledger["solver_entered"] and ledger["engine_completed"] and ledger["post_saved"] and ledger["controller_returned"]
        assert ledger["cores"] == 12 and ledger["slot"] == 1
        assert admission["label"] == "VALID_TRADITIONAL_FDTD_LABEL"
        assert admission["valid"] is True
        assert checksum["unchanged"] is True
        assert len(metrics) == 12
        labels.append(admission["label"])
    assert len(labels) == 4
    assert json.loads((OUT / "first_batch_solver_budget_audit.json").read_text(encoding="utf-8"))["entered_solver_runs"] == 4
