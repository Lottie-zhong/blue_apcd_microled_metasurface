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
from metasurface.nanofin_sweep import (
    build_xy_sweep_plan_rows,
    filter_xy_sweep_rows,
    load_xy_sweep_config,
    write_xy_case_configs,
    write_xy_sweep_plan,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build x/y .fsp files for selected nanofin sweep cases.")
    parser.add_argument("--config", default="configs/nanofin_xy_sweep.yaml", help="Path to sweep YAML config.")
    parser.add_argument("--runtime", default="configs/runtime.yaml", help="Path to local runtime YAML.")
    parser.add_argument("--case-id", action="append", default=[], help="Case id to build; repeat for multiple cases.")
    parser.add_argument("--all", action="store_true", help="Build every case in the sweep plan.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sweep_config = load_xy_sweep_config(args.config)
    rows = build_xy_sweep_plan_rows(sweep_config)
    selected_rows = filter_xy_sweep_rows(rows, case_ids=args.case_id, include_all=args.all)

    write_xy_sweep_plan(rows, sweep_config.result_dir / "xy_sweep_plan.csv")
    write_xy_case_configs(sweep_config, selected_rows)

    built = 0
    for row in selected_rows:
        for polarization in ("x", "y"):
            config_path = Path(row[f"{polarization}_config"])
            fsp_path = Path(row[f"{polarization}_fsp"])
            summary_path = Path(row[f"{polarization}_summary"])
            config = load_nanofin_single_config(config_path)
            rows_out = SingleNanofinRunner.from_runtime_file(
                config=config,
                runtime_path=args.runtime,
                dry_run=False,
                setup_only=True,
                fsp_output=fsp_path,
            ).run()
            write_single_nanofin_summary(rows_out, summary_path)
            print(f"built={row['case_id']} polarization={polarization} fsp={fsp_path}")
            built += 1

    print(f"cases={len(selected_rows)}")
    print(f"fsp_files={built}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
