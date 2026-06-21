from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from metasurface.stage13_6_phase_coordinate_patch_audit import (
    PERIOD_X_NM,
    PITCH_X_NM,
    frozen_units,
    nearest_rows,
    phase_audit_rows,
    read_csv,
    tile_patch,
    unwrap_phase_degrees,
)


def inputs():
    root = REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout"
    layout = root / "stage12_1_k6_forward_layout_plan.csv"
    phase = root / "stage12_1_k6_forward_phase_amplitude_audit.csv"
    return frozen_units(read_csv(layout), read_csv(phase))


def test_unwrap_and_phase_sequence_are_monotonic() -> None:
    assert unwrap_phase_degrees([-3.2, 64.0, 128.6, 175.9, -127.4, -52.5])[-1] > 300
    rows = phase_audit_rows(inputs(), "layout.csv")
    assert len(rows) == 6
    assert all(row["layout_consistency"] == "pass" for row in rows)
    assert [row["phase_bin_deg"] for row in rows] == [0, 60, 120, 180, 240, 300]
    assert abs(PITCH_X_NM * 6 - PERIOD_X_NM) < 1e-9


def test_a_small_exact_counts_and_nearest_bias() -> None:
    dimers, pillars = tile_patch(inputs())
    assert len(dimers) == 342
    assert len(pillars) == 684
    nearest = nearest_rows(dimers, pillars)
    dimer_rows = [row for row in nearest if row["entity_type"] == "dimer"]
    pillar_rows = [row for row in nearest if row["entity_type"] == "pillar"]
    assert dimer_rows[0]["distance_to_source_nm"] == dimer_rows[1]["distance_to_source_nm"]
    assert {dimer_rows[0]["phase_bin_deg"], dimer_rows[1]["phase_bin_deg"]} == {120, 180}
    assert pillar_rows[0]["phase_bin_deg"] == 180
    assert pillar_rows[0]["pillar_role"] == "J2"
    assert abs(pillar_rows[0]["distance_to_source_nm"] - 115.953893) < 1e-6
