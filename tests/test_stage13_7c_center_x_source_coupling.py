from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path: sys.path.insert(0, str(SRC))

from metasurface.stage13_4_center_dipole import build_patch_inventory, load_approved_plan
from metasurface.stage13_7c_center_x_source_coupling import bool_value, build_shift_candidates, selected_shift


CONFIG = REPO_ROOT / "outputs/stage13_3_lp_first_dipole_manual_config/stage13_3_first_no_dbr_config.json"
CASES = REPO_ROOT / "outputs/stage13_3_lp_first_dipole_manual_config/stage13_3_first_no_dbr_minimal_cases.csv"
LAYOUT = REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_layout_plan.csv"


def test_shift_selection_uses_actual_patch_and_selects_minus_50_nm() -> None:
    plan = load_approved_plan(CONFIG, CASES, LAYOUT); inventory = build_patch_inventory(plan)
    rows = build_shift_candidates(inventory, plan["layout_rows"])
    assert len(rows) == 8
    assert selected_shift(rows) == -50.0
    selected = next(row for row in rows if row["shift_x_nm"] == -50.0)
    assert selected["safe_for_case3"] is True
    assert float(selected["nearest_pillar_distance_nm"]) > 115.953893


def test_no_candidate_uses_stage13_q_position() -> None:
    plan = load_approved_plan(CONFIG, CASES, LAYOUT); inventory = build_patch_inventory(plan)
    rows = build_shift_candidates(inventory, plan["layout_rows"])
    assert all(abs(float(row["shift_x_nm"])) <= 100.0 for row in rows)
    assert all(abs(abs(float(row["shift_x_nm"])) - 107.9769465) > 1e-6 for row in rows)


def test_csv_false_string_is_not_truthy() -> None:
    assert bool_value(False) is False
    assert bool_value("False") is False
    assert bool_value("True") is True
