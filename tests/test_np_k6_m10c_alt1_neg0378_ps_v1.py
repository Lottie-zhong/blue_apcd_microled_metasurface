from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
EVID = ROOT / "outputs" / "np_k6_m10c_alt1_neg0378_ps_quantitative_anchor_v1"
RUNS = EVID / "runtime_runs"
P = "NP_K6_M10C_ALT1_UX_M0d378689399989_P_XLIKE"
S = "NP_K6_M10C_ALT1_UX_M0d378689399989_S_YLIKE"


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def test_setup_preflight_and_material_readback():
    assert load(EVID / "m10c_run_preflight.json")["preflight_pass"] is True
    assert all(load(EVID / "m10c_material_readback_audit.json")["checks"].values())


def test_cases_exactly_once_and_serial():
    p = load(RUNS / P / "attempt_001" / "attempt_ledger.json")
    s = load(RUNS / S / "attempt_001" / "attempt_ledger.json")
    assert p["attempt_id"] == s["attempt_id"] == "attempt_001"
    assert p["entered"] and s["entered"]
    assert p["run_invocation_count"] == s["run_invocation_count"] == 1
    assert p["slot_release_time"] <= s["slot_acquire_time"]
    assert p["local_active_fdtd"] == s["local_active_fdtd"] == 0


def test_quality_gates_and_post_sha():
    for case in (P, S):
        d = RUNS / case / "attempt_001"
        ledger = load(d / "attempt_ledger.json")
        quality = load(d / "quality_gate.json")
        assert quality["quality_gate_pass"] is True
        assert ledger["engine_completed"] and ledger["post_saved"] and ledger["controller_returned"]
        assert ledger["post_fsp_sha256"]
        with (d / "spectral_metrics.csv").open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 11
        assert all(abs(float(r["wavelength_nm"]) - (445 + i)) <= 1e-6 for i, r in enumerate(rows))


def test_registry_55_rows_and_governance():
    reg = load(EVID / "m10c_angular_calibration_5case_55row_registry.json")
    assert reg["row_count"] == 55
    assert reg["logical_case_count"] == 5
    assert reg["training_label"] is False
    assert reg["candidate_performance_label"] is False
    budget = load(EVID / "solver_budget_audit_final.json")
    assert budget["solver_entered_total"] == 2
    assert budget["attempt_002"] == budget["attempt_003"] == 0
    assert budget["minus_0482_touched"] is False
    assert budget["control0_started"] is False


def test_decision_and_resource_audit():
    decision = load(EVID / "m10c_decision.json")
    resource = load(EVID / "m10c_resource_audit.json")
    assert decision["P_quality_gate"] and decision["S_quality_gate"]
    assert decision["five_case_registry_rows"] == 55
    assert resource["peak_local_active_fdtd"] == 1
    assert resource["P_S_overlap_duration_s"] == 0
    assert resource["active_slots_after_close"] == 0
