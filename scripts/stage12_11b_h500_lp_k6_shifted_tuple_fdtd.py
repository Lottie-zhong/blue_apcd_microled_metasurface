from __future__ import annotations
import argparse, sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi
from metasurface.stage12_11b_shifted_tuple_fdtd import OUTPUT_DIR_NAME, RUN_MATRIX_FIELDS, Stage12_11BPaths, build_run_matrix, build_shifted_tuple_layout, run_stage12_11b, write_csv_rows
OUT = REPO_ROOT / "outputs" / OUTPUT_DIR_NAME
PATHS = Stage12_11BPaths(REPO_ROOT / "outputs/stage12_11a_h500_lp_k6_phase_origin_search/stage12_11a_best_tuple_library.csv", REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_layout_plan.csv", OUT, OUT / "fdtd_work")
def parse_args():
    p = argparse.ArgumentParser(description="Stage12-11B shifted phase-origin K=6 x-gradient FDTD validation.")
    p.add_argument("--runtime", default="configs/runtime.yaml")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--keep-fsp", action="store_true")
    return p.parse_args()
def main() -> int:
    args = parse_args()
    layout_rows, _geometry_rows, _phase_rows, geometry_audit = build_shifted_tuple_layout(REPO_ROOT, PATHS.baseline_layout_csv, PATHS.best_tuple_csv)
    OUT.mkdir(parents=True, exist_ok=True)
    run_matrix = build_run_matrix(layout_rows)
    write_csv_rows(run_matrix, OUT / "stage12_11b_fdtd_run_matrix.csv", RUN_MATRIX_FIELDS)
    print(f"output_dir={OUT}")
    print(f"planned_fdtd_runs={len(run_matrix)}")
    print(f"geometry_legal={geometry_audit['geometry_legal']}")
    print(f"minimum_clearance_nm={geometry_audit['minimum_clearance_nm']}")
    for row in run_matrix:
        print(f"planned={row['run_id']} polarization={row['polarization']} target={row['target_order']}")
    if args.dry_run:
        print("boundary=dry_run_no_fdtd_no_fsp")
        return 0
    runtime = load_runtime_config(args.runtime)
    lumapi = import_lumapi(runtime)
    result = run_stage12_11b(REPO_ROOT, PATHS, lumapi, runtime, keep_fsp=args.keep_fsp)
    for key, value in result.items():
        print(f"{key}={value}")
    print("boundary=k6_plane_wave_only_no_dipoles_no_cp_no_ygradient_no_h600_h700_no_reverse")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
