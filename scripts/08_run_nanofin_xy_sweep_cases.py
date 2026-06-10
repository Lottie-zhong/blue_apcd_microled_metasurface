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
    collect_xy_sweep_result_rows,
    filter_xy_sweep_rows,
    load_xy_sweep_config,
    write_xy_sweep_results,
)
from metasurface.phase_delay import compute_xy_phase_delay_from_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run solved x/y simulations for nanofin sweep cases.")
    parser.add_argument("--config", default="configs/nanofin_xy_sweep.yaml", help="Path to sweep YAML config.")
    parser.add_argument("--runtime", default="configs/runtime.yaml", help="Path to local runtime YAML.")
    parser.add_argument("--case-id", action="append", default=None, help="Case id to run. Can be used more than once.")
    parser.add_argument("--all", action="store_true", help="Run all planned cases.")
    parser.add_argument("--skip-completed", action="store_true", help="Skip cases that already have phase delay CSVs.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.all and not args.case_id:
        raise SystemExit("Provide --case-id one or more times, or use --all.")

    sweep_config = load_xy_sweep_config(args.config)
    plan_rows = build_xy_sweep_plan_rows(sweep_config)
    selected_rows = plan_rows if args.all else filter_xy_sweep_rows(plan_rows, case_ids=args.case_id)

    completed_cases = 0
    skipped_cases = 0
    failed_cases = 0
    for row in selected_rows:
        case_id = str(row["case_id"])
        phase_delay_summary = Path(row["phase_delay_summary"])
        if args.skip_completed and phase_delay_summary.exists():
            skipped_cases += 1
            print(f"skipped={case_id} reason=phase_delay_summary_exists")
            continue

        case_ok = True
        for polarization in ("x", "y"):
            status = _run_one_polarization(row, polarization, args.runtime)
            case_ok = case_ok and status == "ok"

        if case_ok:
            phase_delay_path = compute_xy_phase_delay_from_files(
                x_summary_path=row["x_summary"],
                y_summary_path=row["y_summary"],
                output_path=phase_delay_summary,
            )
            completed_cases += 1
            print(f"phase_delay={case_id} output={phase_delay_path}")
        else:
            failed_cases += 1
            print(f"phase_delay={case_id} skipped=simulation_status_not_ok")

    result_rows = collect_xy_sweep_result_rows(plan_rows)
    result_path = write_xy_sweep_results(result_rows, sweep_config.result_dir / "xy_sweep_results.csv")
    completed_total = sum(1 for row in result_rows if row["status"] == "ok")
    print(f"run_completed={completed_cases}")
    print(f"run_skipped={skipped_cases}")
    print(f"run_failed={failed_cases}")
    print(f"completed_total={completed_total}")
    print(f"total={len(result_rows)}")
    print(f"result_output={result_path}")
    if completed_total:
        best = next(row for row in result_rows if row["status"] == "ok")
        print(
            "best="
            f"{best['case_id']} "
            f"phase_delay_rad={best['phase_delay_rad']} "
            f"error_to_pi={best['phase_delay_error_to_pi']}"
        )
    return 0


def _run_one_polarization(row: dict[str, object], polarization: str, runtime_path: str) -> str:
    config = load_nanofin_single_config(row[f"{polarization}_config"])
    rows_out = SingleNanofinRunner.from_runtime_file(
        config=config,
        runtime_path=runtime_path,
        dry_run=False,
        load_fsp=row[f"{polarization}_fsp"],
    ).run()
    write_single_nanofin_summary(rows_out, row[f"{polarization}_summary"])
    status = str(rows_out[0]["status"])
    print(f"ran={row['case_id']} polarization={polarization} status={status}")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
