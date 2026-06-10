from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.nanofin_sweep import (
    build_xy_sweep_plan_rows,
    collect_xy_sweep_result_rows,
    load_xy_sweep_config,
    write_xy_sweep_results,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect and rank completed nanofin x/y sweep results.")
    parser.add_argument("--config", default="configs/nanofin_xy_sweep.yaml", help="Path to sweep YAML config.")
    parser.add_argument("--output", default=None, help="Optional output CSV path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_xy_sweep_config(args.config)
    plan_rows = build_xy_sweep_plan_rows(config)
    result_rows = collect_xy_sweep_result_rows(plan_rows)
    output_path = Path(args.output) if args.output else config.result_dir / "xy_sweep_results.csv"
    written_path = write_xy_sweep_results(result_rows, output_path)

    completed = sum(1 for row in result_rows if row["status"] == "ok")
    print(f"completed={completed}")
    print(f"total={len(result_rows)}")
    print(f"output={written_path}")
    if completed:
        best = next(row for row in result_rows if row["status"] == "ok")
        print(
            "best="
            f"{best['case_id']} "
            f"phase_delay_rad={best['phase_delay_rad']} "
            f"error_to_pi={best['phase_delay_error_to_pi']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
