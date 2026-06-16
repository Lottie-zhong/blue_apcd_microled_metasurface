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
from metasurface.stage12_k6_ygrad_fdtd import FSP_FILENAME, Stage12YGradPaths, write_all_outputs

OUT = REPO_ROOT / "outputs/stage12_4_h500_lp_k6_ygrad_minimal_fdtd"
PATHS = Stage12YGradPaths(
    source_layout_csv=REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_layout_plan.csv",
    source_geometry_csv=REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_geometry_audit.csv",
    source_phase_csv=REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_phase_amplitude_audit.csv",
    xgrad_results_csv=REPO_ROOT / "outputs/stage12_2_h500_lp_k6_forward_minimal_fdtd/stage12_2_k6_forward_fdtd_results.csv",
    xgrad_selectivity_csv=REPO_ROOT / "outputs/stage12_2_h500_lp_k6_forward_minimal_fdtd/stage12_2_k6_forward_selectivity_summary.csv",
    output_dir=OUT,
    fdtd_work_dir=OUT / "fdtd_work",
    gui_fsp_path=OUT / FSP_FILENAME,
)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage12-4 official H500 LP-APCD K=6 y-gradient minimal FDTD validation.")
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    return parser.parse_args()

def main() -> int:
    args = parse_args()
    runtime = load_runtime_config(args.runtime)
    lumapi = import_lumapi(runtime)
    result = write_all_outputs(PATHS, lumapi, runtime)
    print(f"fsp_path={result['fsp_path']}")
    print(f"fsp_generated={result['fsp_generated']}")
    print(f"geometry_legal={result['geometry_legal']}")
    print(f"minimum_clearance_nm={result['minimum_clearance_nm']}")
    print(f"minimum_neighbor_clearance_nm={result['minimum_neighbor_clearance_nm']}")
    print(f"fdtd_runs={result['fdtd_runs']}")
    print(f"target_order_selectivity_ratio={result['target_order_selectivity_ratio']}")
    print(f"overall_stage12_4_pass={result['overall_stage12_4_pass']}")
    print("boundary=official_y_gradient_two_run_minimal_no_sweep_no_reverse_no_h600_h700_no_cp")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
