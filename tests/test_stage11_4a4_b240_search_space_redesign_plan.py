from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "stage11_lp_b240_search_space_redesign_plan_stage11_4a4.py"
spec = importlib.util.spec_from_file_location("stage11_4a4", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def test_plan_budget_and_groups():
    rows = mod.plan_rows()
    assert len(rows) == 3
    assert mod.total_cases(rows) == 72
    assert mod.total_cases(rows) <= 72


def test_plan_keeps_b300_blocked_and_targets_b240():
    rows = mod.plan_rows()
    assert {r["target_bin_deg"] for r in rows} == {"240"}
    assert all("B300" not in r["group_id"] for r in rows)
    manifest = mod.build_manifest(rows, {"best_candidate": {}})
    assert manifest["no_b300_phase_pull"] is True
    assert manifest["b300_blocked_reason"]


def test_heights_are_h600_plus_small_h650_escape_only():
    rows = mod.plan_rows()
    assert [r["height_nm"] for r in rows] == ["600", "600", "650"]
    assert "H650" in rows[-1]["group_id"]
    assert rows[-1]["planned_cases"] == "18"


def test_thresholds_define_near_miss():
    assert mod.PASS_THRESHOLDS["near_miss"]["ratio_min"] == 2.0
    assert mod.PASS_THRESHOLDS["loose"]["ratio_min"] == 3.0
    assert mod.PASS_THRESHOLDS["strict"]["ratio_min"] == 6.0


def test_diagnosis_uses_a3_evidence():
    d = mod.diagnose_a3()
    assert d["ok_rows"] == 24
    assert d["near_miss_candidates"] == 0
    assert d["best_candidate"]["failed_gates"] == "ratio;matrix;phase"
