from __future__ import annotations
import argparse, sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi
from metasurface.stage12_9_xgrad_leakage_cancellation import OUTPUT_DIR_NAME, Stage12_9Paths, run_stage12_9, summarize_existing_results
OUT = REPO_ROOT / "outputs" / OUTPUT_DIR_NAME
PATHS = Stage12_9Paths(
    strict_pool_csv=REPO_ROOT / "outputs/stage11_2i_h500_lp_actual_dimer_6bin_freeze/all_strict_candidates_by_bin.csv",
    baseline_layout_csv=REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_layout_plan.csv",
    stage12_8_ranked_csv=REPO_ROOT / "outputs/stage12_8_h500_lp_k6_xgrad_selectivity_refinement/stage12_8_ranked_variants.csv",
    output_dir=OUT,
    fdtd_work_dir=OUT / "fdtd_work",
)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--summarize-existing", action="store_true", help="rebuild Stage12-9 ranking/MD outputs from completed FDTD CSVs without running FDTD")
    args = parser.parse_args()
    if args.summarize_existing:
        result = summarize_existing_results(PATHS, REPO_ROOT)
    else:
        runtime = load_runtime_config(args.runtime)
        lumapi = import_lumapi(runtime)
        result = run_stage12_9(PATHS, lumapi, runtime, REPO_ROOT)
    for key, value in result.items():
        print(f"{key}={value}")
    print("boundary=plane_wave_only_no_dipoles_no_cp_no_ygradient_no_h600_h700_no_reverse")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
