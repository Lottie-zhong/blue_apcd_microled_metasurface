from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.stage12_k6_order_audit import (
    ORDER_RESOLVED_FIELDS,
    SELECTIVITY_METRIC_FIELDS,
    build_interpretation_summary,
    build_order_resolved_table,
    compute_stage12_3_metrics,
    read_csv_rows,
    write_csv_rows,
)


INPUT_DIR = REPO_ROOT / "outputs/stage12_2_h500_lp_k6_forward_minimal_fdtd"
OUTPUT_DIR = REPO_ROOT / "outputs/stage12_3_h500_lp_k6_order_resolved_audit"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage12-3 read-only order-resolved audit of Stage12-2 outputs. No FDTD.")
    parser.add_argument("--input-dir", type=Path, default=INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result_rows = read_csv_rows(args.input_dir / "stage12_2_k6_forward_fdtd_results.csv")
    order_rows = read_csv_rows(args.input_dir / "stage12_2_k6_forward_order_power.csv")
    # Load available Stage12-2 metric/run-plan CSVs as read-only inputs for completeness.
    read_csv_rows(args.input_dir / "stage12_2_k6_forward_selectivity_summary.csv")
    read_csv_rows(args.input_dir / "stage12_2_k6_forward_fdtd_run_plan.csv")

    x_table = build_order_resolved_table(order_rows, "x")
    y_table = build_order_resolved_table(order_rows, "y")
    metrics = compute_stage12_3_metrics(result_rows, order_rows)
    summary = build_interpretation_summary(metrics)

    write_csv_rows(x_table, args.output_dir / "stage12_3_order_resolved_x_lp.csv", ORDER_RESOLVED_FIELDS)
    write_csv_rows(y_table, args.output_dir / "stage12_3_order_resolved_y_lp.csv", ORDER_RESOLVED_FIELDS)
    write_csv_rows(metrics, args.output_dir / "stage12_3_selectivity_metrics.csv", SELECTIVITY_METRIC_FIELDS)
    (args.output_dir / "stage12_3_interpretation_summary.md").parent.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "stage12_3_interpretation_summary.md").write_text(summary, encoding="utf-8")

    metric_map = {row["metric"]: row["value"] for row in metrics}
    print(f"output_dir={args.output_dir}")
    print(f"target_order_selectivity_ratio={metric_map['target_order_selectivity_ratio']}")
    print(f"total_transmission_selectivity_ratio={metric_map['total_transmission_selectivity_ratio']}")
    print(f"y_dominant_leakage_order={metric_map['y_dominant_leakage_order']}")
    print(f"final_interpretation={metric_map['final_interpretation']}")
    print("boundary=read_only_no_fdtd_no_fsp_no_optimization")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
