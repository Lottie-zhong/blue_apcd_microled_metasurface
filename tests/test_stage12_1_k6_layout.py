from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.stage12_k6_layout import audit_geometry, build_stage12_1_layout


HANDOFF = REPO_ROOT / "outputs/stage11_2i_h500_lp_actual_dimer_6bin_freeze/stage12_handoff_phase_library.csv"


def test_stage12_1_forward_layout_order_and_geometry_from_sources() -> None:
    bundle = build_stage12_1_layout(REPO_ROOT, HANDOFF)

    assert [row["phase_bin_deg"] for row in bundle.layout_rows] == [0, 60, 120, 180, 240, 300]
    assert [row["candidate_id"] for row in bundle.layout_rows] == [
        "H500DIMER2C_029_B240_x_pair_noswap_G60_O-20",
        "H500DIMER2B_006_B180_x_pair_swap_G60_O-20",
        "H500DIMER2D_040_B300_y_pair_noswap_G20_O-40",
        "H500DIMER2C_026_B240_x_pair_swap_G60_O-20",
        "H500DIMER2F_026_B240_x_pair_swap_G90_O-28",
        "H500DIMER2D_006_B240_x_pair_swap_G80_O-30",
    ]
    assert all(row["source_plan_file"] for row in bundle.layout_rows)
    assert all(str(row["geometry_legal"]).lower() == "true" for row in bundle.geometry_rows)
    assert min(float(row["internal_clearance_nm"]) for row in bundle.geometry_rows) == 20.0
    assert min(float(row["min_neighbor_clearance_nm"]) for row in bundle.geometry_rows) > 20.0


def test_clearance_audit_flags_neighbor_overlap() -> None:
    rows = [
        base_layout_row(0, 0.0, 0.0, 100.0, 100.0, 120.0, 0.0, 100.0, 100.0),
        base_layout_row(1, 190.0, 0.0, 100.0, 100.0, 210.0, 0.0, 100.0, 100.0),
    ]
    audit = audit_geometry(rows, pitch_x_nm=200.0, p_y_nm=400.0, supercell_period_nm=400.0)

    assert any(float(row["min_neighbor_clearance_nm"]) < 20.0 for row in audit)
    assert any(str(row["geometry_legal"]).lower() == "false" for row in audit)


def base_layout_row(index: int, j1x: float, j1y: float, j1w: float, j1h: float, j2x: float, j2y: float, j2w: float, j2h: float) -> dict[str, object]:
    return {
        "supercell_index": index,
        "phase_bin_deg": index * 60,
        "candidate_id": f"fixture_{index}",
        "geometry_legal": "true",
        "j1_abs_center_x_nm": j1x,
        "j1_abs_center_y_nm": j1y,
        "j1_footprint_x_nm": j1w,
        "j1_footprint_y_nm": j1h,
        "j2_abs_center_x_nm": j2x,
        "j2_abs_center_y_nm": j2y,
        "j2_footprint_x_nm": j2w,
        "j2_footprint_y_nm": j2h,
    }
