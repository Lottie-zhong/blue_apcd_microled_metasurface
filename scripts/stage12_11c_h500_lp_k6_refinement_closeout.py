from __future__ import annotations
import sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from metasurface.stage12_11c_refinement_closeout import OUTPUT_DIR_NAME, Stage12_11CPaths, build_stage12_11c_closeout
OUT = REPO_ROOT / "outputs" / OUTPUT_DIR_NAME
PATHS = Stage12_11CPaths(
    stage12_2_dir=REPO_ROOT / "outputs/stage12_2_h500_lp_k6_forward_minimal_fdtd",
    stage12_8_dir=REPO_ROOT / "outputs/stage12_8_h500_lp_k6_xgrad_selectivity_refinement",
    stage12_9_dir=REPO_ROOT / "outputs/stage12_9_h500_lp_k6_xgrad_leakage_cancellation",
    stage12_10a_dir=REPO_ROOT / "outputs/stage12_10a_h500_lp_240bin_single_dimer_refinement",
    stage12_10b_dir=REPO_ROOT / "outputs/stage12_10b_h500_lp_240bin_broad_family_scout",
    stage12_10c_dir=REPO_ROOT / "outputs/stage12_10c_h500_lp_180bin_single_dimer_refinement",
    stage12_10d_dir=REPO_ROOT / "outputs/stage12_10d_h500_lp_300bin_single_dimer_refinement",
    stage12_11a_dir=REPO_ROOT / "outputs/stage12_11a_h500_lp_k6_phase_origin_search",
    stage12_11b_dir=REPO_ROOT / "outputs/stage12_11b_h500_lp_k6_shifted_tuple_fdtd",
    stage12_5_dir=REPO_ROOT / "outputs/stage12_5_h500_lp_k6_official_xgrad_freeze",
    output_dir=OUT,
)
def main() -> int:
    result = build_stage12_11c_closeout(PATHS)
    for key, value in result.items():
        print(f"{key}={value}")
    print("boundary=read_only_no_fdtd_no_optimization_no_new_fsp")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
