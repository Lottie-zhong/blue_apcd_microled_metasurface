from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "stage11_lp_true_b300_new_anchor_plan_stage11_4a9.py"
spec = importlib.util.spec_from_file_location("a9", SCRIPT)
a9 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a9)


def test_excluded_b60_family_detects_promoted_sources():
    rows = [
        {"candidate_id": "H600B300PULL_002_FROM_H500DIMER12D_004_B300_x_pair_swap_G80_O-40", "reassignment_recommendation": "candidate_for_B60"},
        {"candidate_id": "other", "reassignment_recommendation": "do_not_promote"},
    ]
    excluded = a9.excluded_b60_family(rows)
    assert "H600B300PULL_002_FROM_H500DIMER12D_004_B300_x_pair_swap_G80_O-40" in excluded["candidate_ids"]
    assert any("B300_x_pair_swap_G80_O-40" in family for family in excluded["families"])


def test_plan_groups_total_36_and_no_forbidden_scope():
    groups = a9.plan_groups("excluded")
    assert sum(int(g["planned_cases"]) for g in groups) == 36
    assert [int(g["planned_cases"]) for g in groups] == [18, 12, 6]
    assert all(int(g["height_nm"]) == 600 for g in groups)
    assert all(int(g["target_actual_bin_deg"]) == 300 for g in groups)
    assert not any("coverage" in g["purpose"].lower() for g in groups)


def test_write_outputs_keeps_b300_unsolved_and_planning_only():
    summary = a9.write_outputs()
    assert summary["planning_only"] is True
    assert summary["no_fdtd_lumerical"] is True
    assert summary["b300_still_unsolved"] is True
    assert summary["future_total_cases"] == 36
    assert summary["recommended_next_run_group"] == "S11_4A9_G1_TRUE_B300_DIFFERENT_ANCHOR_FAMILY"
    assert "coverage 0/60/120/180" in summary["excluded_scope"]
    assert a9.SPACE_CSV.exists()
    assert a9.PLAN_MD.exists()
