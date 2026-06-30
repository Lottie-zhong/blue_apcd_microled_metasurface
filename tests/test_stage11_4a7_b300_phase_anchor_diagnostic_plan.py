from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "stage11_lp_b300_phase_anchor_diagnostic_plan_stage11_4a7.py"
spec = importlib.util.spec_from_file_location("a7", SCRIPT)
a7 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a7)


def test_circular_nearest_bin_helpers():
    assert a7.circ_diff(10, 350) == 20
    assert a7.nearest_bin(358) == 0
    assert a7.nearest_bin(287) == 300


def test_planned_groups_stay_under_36_cases():
    fake_stats = [{"source_candidate_id": "seed", "worst_ratio": 10, "worst_matrix_error": 0.3, "max_phase_error_to_300_deg": 120}]
    groups = a7.planned_groups(fake_stats)
    assert sum(int(g["planned_cases"]) for g in groups) == 36
    assert [int(g["planned_cases"]) for g in groups] == [18, 12, 6]
    assert all(int(g["height_nm"]) == 600 for g in groups)


def test_write_outputs_excludes_forbidden_scope():
    summary = a7.write_outputs()
    assert summary["planning_only"] is True
    assert summary["no_fdtd_lumerical"] is True
    assert summary["future_total_cases"] == 36
    assert "coverage" in summary["excluded"]
    assert "H650" in summary["excluded"]
    assert "K=6" in summary["excluded"]
    manifest = json.loads(a7.MANIFEST_JSON.read_text(encoding="utf-8"))
    assert sum(int(g["planned_cases"]) for g in manifest["run_groups"]) == 36
    text = a7.PLAN_MD.read_text(encoding="utf-8")
    forbidden = [".fsp", ".ldf", ".log", "monitor", "farfield"]
    assert not any(token in text for token in forbidden)
