from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.stage12_k6_official_freeze import OUTPUT_DIR_NAME, Stage12FreezePaths, build_freeze_outputs

OUT = REPO_ROOT / "outputs" / OUTPUT_DIR_NAME
PATHS = Stage12FreezePaths(
    stage12_2_dir=REPO_ROOT / "outputs/stage12_2_h500_lp_k6_forward_minimal_fdtd",
    stage12_3_dir=REPO_ROOT / "outputs/stage12_3_h500_lp_k6_order_resolved_audit",
    stage12_3b_dir=REPO_ROOT / "outputs/stage12_3b_h500_lp_k6_gui_inspection",
    stage12_4_dir=REPO_ROOT / "outputs/stage12_4_h500_lp_k6_ygrad_minimal_fdtd",
    stage11_freeze_dir=REPO_ROOT / "outputs/stage11_2i_h500_lp_actual_dimer_6bin_freeze",
    stage12_1_dir=REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout",
    output_dir=OUT,
)

def main() -> int:
    result = build_freeze_outputs(PATHS)
    print(f"output_dir={result['output_dir']}")
    print(f"official_axis={result['official_axis']}")
    print(f"x_classification={result['x_classification']}")
    print(f"y_classification={result['y_classification']}")
    print(f"x_ratio={result['x_ratio']}")
    print(f"y_ratio={result['y_ratio']}")
    print("boundary=read_only_no_fdtd_no_optimization_no_new_fsp")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
