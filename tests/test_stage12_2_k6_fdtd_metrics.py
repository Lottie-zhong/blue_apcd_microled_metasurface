from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.stage12_k6_fdtd import compute_selectivity_summary, dominant_order, order_contrast, order_power


def test_order_power_and_contrast_pick_plus_one() -> None:
    rows = [
        {"order_n": -1, "order_power_source_norm": 0.01},
        {"order_n": 0, "order_power_source_norm": 0.02},
        {"order_n": 1, "order_power_source_norm": 0.12},
    ]

    assert dominant_order(rows)["order_n"] == 1
    assert order_power(rows, 1) == 0.12
    assert order_contrast(rows, 1) == 6.0


def test_selectivity_summary_uses_y_plus_one_leakage() -> None:
    result_rows = [
        {"polarization": "x", "fdtd_status": "ok", "dominant_order_n": 1, "plus1_direction_consistent": True},
        {"polarization": "y", "fdtd_status": "ok", "dominant_order_n": 0},
    ]
    order_rows = [
        {"polarization": "x", "order_n": 1, "order_power_source_norm": 0.18, "total_transmission": 0.2},
        {"polarization": "x", "order_n": 0, "order_power_source_norm": 0.01, "total_transmission": 0.2},
        {"polarization": "y", "order_n": 1, "order_power_source_norm": 0.02, "total_transmission": 0.05},
        {"polarization": "y", "order_n": 0, "order_power_source_norm": 0.03, "total_transmission": 0.05},
    ]
    phase_rows = [
        {"phase_bin_deg": "0", "Tx": "1.0", "conversion_to_leakage_ratio": "10"},
        {"phase_bin_deg": "240", "Tx": "0.7", "conversion_to_leakage_ratio": "7"},
    ]

    metrics = {row["metric"]: row["value"] for row in compute_selectivity_summary(result_rows, order_rows, phase_rows)}

    assert metrics["effective_target_power"] == 0.18
    assert metrics["effective_blocked_leakage"] == 0.02
    assert metrics["effective_selectivity_ratio"] == 9.0
    assert metrics["key_risk_bin"] == "240"
    assert metrics["overall_farfield_audit_pass"] is True
