from __future__ import annotations

from pathlib import Path

import pytest

from metasurface.stage12_k6_fdtd import read_csv_rows
from metasurface.stage12_k6_gui_inspection import build_marker_table


REPO_ROOT = Path(__file__).resolve().parents[1]
STAGE12_1 = REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout"


def test_stage12_3b_marker_table_flags_forward_order_and_clearance_region() -> None:
    layout = read_csv_rows(STAGE12_1 / "stage12_1_k6_forward_layout_plan.csv")
    geometry = read_csv_rows(STAGE12_1 / "stage12_1_k6_forward_geometry_audit.csv")
    phase = read_csv_rows(STAGE12_1 / "stage12_1_k6_forward_phase_amplitude_audit.csv")

    markers = build_marker_table(layout, geometry, phase)

    assert [row["phase_bin_deg"] for row in markers] == [0, 60, 120, 180, 240, 300]
    risk_rows = [row for row in markers if row["is_240_risk_bin"] == "True"]
    assert len(risk_rows) == 1
    assert risk_rows[0]["phase_bin_deg"] == 240
    min_rows = [row for row in markers if row["is_20nm_min_clearance_dimer"] == "True"]
    assert len(min_rows) == 1
    assert min_rows[0]["phase_bin_deg"] == 120
    adjacent_bins = [row["phase_bin_deg"] for row in markers if row["adjacent_to_20nm_min_clearance_region"] == "True"]
    assert adjacent_bins == [60, 120, 180]


def test_stage12_3b_marker_table_rejects_non_forward_order() -> None:
    layout = read_csv_rows(STAGE12_1 / "stage12_1_k6_forward_layout_plan.csv")
    geometry = read_csv_rows(STAGE12_1 / "stage12_1_k6_forward_geometry_audit.csv")
    phase = read_csv_rows(STAGE12_1 / "stage12_1_k6_forward_phase_amplitude_audit.csv")
    swapped = list(reversed(layout))

    with pytest.raises(ValueError, match="forward bins"):
        build_marker_table(swapped, geometry, phase)
