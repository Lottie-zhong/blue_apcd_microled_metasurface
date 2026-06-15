from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi
from metasurface.stage12_k6_fdtd import (
    ORDER_POWER_FIELDS,
    RESULT_FIELDS,
    RUN_PLAN_FIELDS,
    SELECTIVITY_FIELDS,
    Stage12Paths,
    build_run_plan,
    compute_selectivity_summary,
    read_csv_rows,
    run_one_fdtd,
    write_before_after,
    write_csv_rows,
    write_farfield_audit,
)


OUT = REPO_ROOT / "outputs/stage12_2_h500_lp_k6_forward_minimal_fdtd"
PATHS = Stage12Paths(
    layout_plan_csv=REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_layout_plan.csv",
    geometry_audit_csv=REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_geometry_audit.csv",
    phase_amplitude_audit_csv=REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_phase_amplitude_audit.csv",
    output_dir=OUT,
    fdtd_work_dir=OUT / "fdtd_work",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage12-2 minimal H500 LP-APCD K=6 forward full-FDTD validation.")
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--keep-fsp", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_plan = build_run_plan(PATHS)
    write_csv_rows(run_plan, OUT / "stage12_2_k6_forward_fdtd_run_plan.csv", RUN_PLAN_FIELDS)
    print(f"run_plan_csv={OUT / 'stage12_2_k6_forward_fdtd_run_plan.csv'}")
    print(f"planned_fdtd_runs={len(run_plan)}")
    for row in run_plan:
        print(f"planned={row['run_id']} polarization={row['polarization']} angle={row['polarization_angle_deg']}")
    if args.dry_run:
        return 0

    layout_rows = read_csv_rows(PATHS.layout_plan_csv)
    phase_rows = read_csv_rows(PATHS.phase_amplitude_audit_csv)
    runtime = load_runtime_config(args.runtime)
    lumapi = import_lumapi(runtime)
    result_rows = []
    order_rows = []
    for row in run_plan:
        result, orders = run_one_fdtd(lumapi, runtime, layout_rows, row, PATHS, keep_fsp=args.keep_fsp)
        result_rows.append(result)
        order_rows.extend(orders)
        write_csv_rows(result_rows, OUT / "stage12_2_k6_forward_fdtd_results.csv", RESULT_FIELDS)
        write_csv_rows(order_rows, OUT / "stage12_2_k6_forward_order_power.csv", ORDER_POWER_FIELDS)
        print(f"done={row['run_id']} status={result['fdtd_status']} dominant={result.get('dominant_order_n','')} plus1={result.get('target_plus1_power','')}")
    selectivity_rows = compute_selectivity_summary(result_rows, order_rows, phase_rows)
    write_csv_rows(selectivity_rows, OUT / "stage12_2_k6_forward_selectivity_summary.csv", SELECTIVITY_FIELDS)
    write_farfield_audit(OUT / "stage12_2_k6_forward_farfield_audit.md", result_rows, selectivity_rows)
    write_before_after(OUT / "stage12_2_before_after_vs_analytic.md", selectivity_rows)
    metrics = {row["metric"]: row["value"] for row in selectivity_rows}
    print(f"effective_target_power={metrics.get('effective_target_power')}")
    print(f"effective_blocked_leakage={metrics.get('effective_blocked_leakage')}")
    print(f"effective_selectivity_ratio={metrics.get('effective_selectivity_ratio')}")
    print(f"overall_farfield_audit_pass={metrics.get('overall_farfield_audit_pass')}")
    print("boundary=minimal_two_run_fdtd_no_sweep_no_reverse_no_h600_h700_no_cp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
