from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.stage12_k6_order_audit import build_order_resolved_table, compute_stage12_3_metrics


def test_stage12_3_metrics_distinguish_target_and_global_selectivity() -> None:
    result_rows = [
        {"polarization": "x", "total_transmission": "0.63", "dominant_order_n": "1", "dominant_theta_deg": "10.0", "order_contrast_plus1_vs_next": "4.4"},
        {"polarization": "y", "total_transmission": "0.61", "dominant_order_n": "2", "dominant_theta_deg": "20.3", "order_contrast_plus1_vs_next": "0.2"},
    ]
    order_rows = [
        {"polarization": "x", "order_n": "1", "theta_deg": "10", "order_power_source_norm": "0.36"},
        {"polarization": "x", "order_n": "0", "theta_deg": "0", "order_power_source_norm": "0.08"},
        {"polarization": "y", "order_n": "1", "theta_deg": "10", "order_power_source_norm": "0.03"},
        {"polarization": "y", "order_n": "2", "theta_deg": "20", "order_power_source_norm": "0.14"},
    ]

    metrics = {row["metric"]: row["value"] for row in compute_stage12_3_metrics(result_rows, order_rows)}

    assert metrics["target_order_selectivity_ratio"] == 12.0
    assert round(metrics["total_transmission_selectivity_ratio"], 6) == round(0.63 / 0.61, 6)
    assert metrics["target_order_lp_selectivity_validated"] is True
    assert metrics["global_y_lp_blocking_validated"] is False
    assert metrics["y_dominant_leakage_order"] == 2
    assert metrics["final_interpretation"] == "partial pass"


def test_stage12_3_order_table_cumulative_power() -> None:
    rows = [
        {"polarization": "x", "order_n": "0", "theta_deg": "0", "order_power_source_norm": "0.2"},
        {"polarization": "x", "order_n": "1", "theta_deg": "10", "order_power_source_norm": "0.6"},
        {"polarization": "x", "order_n": "-1", "theta_deg": "-10", "order_power_source_norm": "0.2"},
    ]

    table = build_order_resolved_table(rows, "x")

    assert table[0]["diffraction_order"] == 1
    assert table[0]["relative_power"] == 0.6
    assert table[-1]["cumulative_power"] == 1.0
