from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.config import load_nanofin_single_config
from metasurface.nanofin_single import SingleNanofinRunner, write_single_nanofin_summary
from metasurface.nanofin_sweep import build_xy_sweep_plan_rows, filter_xy_sweep_rows, load_xy_sweep_config
from metasurface.phase_delay import compute_xy_phase_delay_from_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract solved x/y results and phase delay for one sweep case.")
    parser.add_argument("--config", default="configs/nanofin_xy_sweep.yaml", help="Path to sweep YAML config.")
    parser.add_argument("--runtime", default="configs/runtime.yaml", help="Path to local runtime YAML.")
    parser.add_argument("--case-id", required=True, help="Case id to extract, e.g. L160_W80_H350_R0.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sweep_config = load_xy_sweep_config(args.config)
    rows = build_xy_sweep_plan_rows(sweep_config)
    row = filter_xy_sweep_rows(rows, case_ids=[args.case_id])[0]

    for polarization in ("x", "y"):
        single_config = load_nanofin_single_config(row[f"{polarization}_config"])
        rows_out = SingleNanofinRunner.from_runtime_file(
            config=single_config,
            runtime_path=args.runtime,
            dry_run=False,
            load_fsp=row[f"{polarization}_fsp"],
            extract_only=True,
        ).run()
        write_single_nanofin_summary(rows_out, row[f"{polarization}_summary"])
        print(f"extracted={args.case_id} polarization={polarization} status={rows_out[0]['status']}")

    phase_delay_path = compute_xy_phase_delay_from_files(
        x_summary_path=row["x_summary"],
        y_summary_path=row["y_summary"],
        output_path=row["phase_delay_summary"],
    )
    print(f"phase_delay={phase_delay_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
