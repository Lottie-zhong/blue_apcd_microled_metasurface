from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.stage12_6_result_package import OUTPUT_DIR_NAME, Stage12_6Paths, run_stage12_6

OUT = REPO_ROOT / "outputs" / OUTPUT_DIR_NAME
PATHS = Stage12_6Paths(
    stage11_dir=REPO_ROOT / "outputs/stage11_2i_h500_lp_actual_dimer_6bin_freeze",
    stage12_0_dir=REPO_ROOT / "outputs/stage12_0_h500_lp_k6_analytic_handoff",
    stage12_1_dir=REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout",
    stage12_2_dir=REPO_ROOT / "outputs/stage12_2_h500_lp_k6_forward_minimal_fdtd",
    stage12_3_dir=REPO_ROOT / "outputs/stage12_3_h500_lp_k6_order_resolved_audit",
    stage12_4_dir=REPO_ROOT / "outputs/stage12_4_h500_lp_k6_ygrad_minimal_fdtd",
    stage12_5_dir=REPO_ROOT / "outputs/stage12_5_h500_lp_k6_official_xgrad_freeze",
    output_dir=OUT,
)

def main() -> int:
    result = run_stage12_6(PATHS)
    print(f"output_dir={result['output_dir']}")
    print(f"figure_count={result['figure_count']}")
    print(f"official_pass={result['official_pass']}")
    print(f"ygrad_classification={result['ygrad_classification']}")
    print("figures=" + ",".join(result["figures"]))
    print("boundary=read_only_no_fdtd_no_optimization_no_new_fsp")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
