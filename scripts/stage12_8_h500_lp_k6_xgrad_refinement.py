from __future__ import annotations
import argparse, sys
from pathlib import Path
REPO_ROOT=Path(__file__).resolve().parents[1]
SRC_DIR=REPO_ROOT/"src"
if str(SRC_DIR) not in sys.path: sys.path.insert(0,str(SRC_DIR))
from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi
from metasurface.stage12_8_xgrad_refinement import OUTPUT_DIR_NAME, Stage12_8Paths, run_stage12_8
OUT=REPO_ROOT/"outputs"/OUTPUT_DIR_NAME
PATHS=Stage12_8Paths(strict_pool_csv=REPO_ROOT/"outputs/stage11_2i_h500_lp_actual_dimer_6bin_freeze/all_strict_candidates_by_bin.csv",baseline_layout_csv=REPO_ROOT/"outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_layout_plan.csv",baseline_geometry_csv=REPO_ROOT/"outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_geometry_audit.csv",baseline_results_csv=REPO_ROOT/"outputs/stage12_2_h500_lp_k6_forward_minimal_fdtd/stage12_2_k6_forward_fdtd_results.csv",output_dir=OUT,fdtd_work_dir=OUT/"fdtd_work")
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--runtime",default="configs/runtime.yaml"); args=ap.parse_args(); runtime=load_runtime_config(args.runtime); lumapi=import_lumapi(runtime); res=run_stage12_8(PATHS,lumapi,runtime)
    for k,v in res.items(): print(f"{k}={v}")
    print("boundary=plane_wave_only_no_dipoles_no_cp_no_ygradient_no_h600_h700")
    return 0
if __name__=="__main__": raise SystemExit(main())
