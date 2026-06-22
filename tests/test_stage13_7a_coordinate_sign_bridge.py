from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from metasurface.stage13_7a_coordinate_sign_bridge import BRIDGE_STATUS, TARGET_UX, angular_distance_deg, read_csv, validate_bridge


def test_existing_stage12_rows_resolve_plus_to_positive_ux() -> None:
    rows = read_csv(REPO_ROOT / "outputs/stage12_2_h500_lp_k6_forward_minimal_fdtd/stage12_2_k6_forward_order_power.csv")
    apcd = (SRC / "metasurface/apcd_diffraction.py").read_text(encoding="utf-8")
    stage13 = (SRC / "metasurface/stage13_4_center_dipole.py").read_text(encoding="utf-8")
    result = validate_bridge(rows, apcd, stage13)
    assert result["bridge_status"] == BRIDGE_STATUS
    assert abs(float(result["plus_ux"]) - TARGET_UX) < 1e-12
    assert abs(float(result["minus_ux"]) + TARGET_UX) < 1e-12


def test_stage13_peak_is_not_near_either_expected_order() -> None:
    plus = angular_distance_deg(-0.34, -0.12, TARGET_UX)
    minus = angular_distance_deg(-0.34, -0.12, -TARGET_UX)
    assert plus > 3.0
    assert minus > 3.0
