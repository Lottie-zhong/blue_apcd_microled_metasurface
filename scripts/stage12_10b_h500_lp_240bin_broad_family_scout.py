from __future__ import annotations
import argparse, sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from metasurface.stage12_10b_240bin_broad_family import OUTPUT_DIR_NAME, Stage12_10BPaths, run_stage12_10b, summarize_existing_stage12_10b
OUT = REPO_ROOT / "outputs" / OUTPUT_DIR_NAME
PATHS = Stage12_10BPaths(output_dir=OUT, stage11_freeze_dir=REPO_ROOT / "outputs/stage11_2i_h500_lp_actual_dimer_6bin_freeze", stage12_10a_dir=REPO_ROOT / "outputs/stage12_10a_h500_lp_240bin_single_dimer_refinement", fdtd_work_dir=OUT / "fdtd_single_dimer_240bin_broad_family")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--summarize-existing", action="store_true")
    args = parser.parse_args()
    if args.summarize_existing:
        result = summarize_existing_stage12_10b(PATHS)
    else:
        result = run_stage12_10b(REPO_ROOT, PATHS, args.runtime)
    for key, value in result.items():
        print(f"{key}={value}")
    print("boundary=single_dimer_only_no_k6_no_dipoles_no_cp_no_ygradient_no_h600_h700")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())