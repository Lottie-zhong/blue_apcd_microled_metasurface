from __future__ import annotations
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.stage12_12a2_narrow_window_acceptance import OUTPUT_DIR_NAME, Stage12_12A2Paths, run_stage12_12a2

PATHS = Stage12_12A2Paths(
    input_dir=REPO_ROOT / "outputs/stage12_12a_h500_lp_6bin_spectral_audit",
    output_dir=REPO_ROOT / "outputs" / OUTPUT_DIR_NAME,
)


def main() -> int:
    result = run_stage12_12a2(PATHS)
    for key, value in result.items():
        print(f"{key}={value}")
    print("boundary=read_only_no_fdtd_no_k6_no_dbr_no_rcled_no_dipoles_no_finite_patch_no_optimization")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
