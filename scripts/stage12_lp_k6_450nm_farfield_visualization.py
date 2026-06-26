from __future__ import annotations
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.stage12_lp_k6_farfield_visualization import OUTPUT_DIR_NAME, Stage12LPVizPaths, run_stage12_lp_k6_visualization

PATHS = Stage12LPVizPaths(
    stage12_2_dir=REPO_ROOT / "outputs/stage12_2_h500_lp_k6_forward_minimal_fdtd",
    stage12_6_dir=REPO_ROOT / "outputs/stage12_6_h500_lp_k6_official_result_package",
    output_dir=REPO_ROOT / "outputs" / OUTPUT_DIR_NAME,
)


def main() -> int:
    result = run_stage12_lp_k6_visualization(PATHS)
    for key, value in result.items():
        print(f"{key}={value}")
    print("boundary=read_only_postprocessing_no_fdtd_no_new_fsp_no_k6_rerun_no_dbr_no_rcled_no_dipole_no_finite_patch_no_optimization")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
