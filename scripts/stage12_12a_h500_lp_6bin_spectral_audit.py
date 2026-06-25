from __future__ import annotations
import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.stage12_12a_spectral_audit import OUTPUT_DIR_NAME, Stage12_12APaths, run_stage12_12a, summarize_existing_stage12_12a

OUT = REPO_ROOT / "outputs" / OUTPUT_DIR_NAME
PATHS = Stage12_12APaths(
    freeze_library_csv=REPO_ROOT / "outputs/stage11_2i_h500_lp_actual_dimer_6bin_freeze/stage12_handoff_phase_library.csv",
    layout_plan_csv=REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_layout_plan.csv",
    output_dir=OUT,
    fdtd_work_dir=OUT / "fdtd_single_dimer_spectral_points",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage12-12A H500 LP-APCD six-bin spectral tolerance audit")
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--keep-fsp", action="store_true", help="Keep generated setup/run .fsp files in outputs for debugging; default deletes them after extraction.")
    parser.add_argument("--postprocess-only", action="store_true", help="Regenerate derived tables and markdown from existing spectral results without running FDTD.")
    args = parser.parse_args()
    result = summarize_existing_stage12_12a(PATHS) if args.postprocess_only else run_stage12_12a(REPO_ROOT, PATHS, runtime_path=args.runtime, cleanup_fsp=not args.keep_fsp, dry_run=args.dry_run)
    for key, value in result.items():
        print(f"{key}={value}")
    print("boundary=single_dimer_spectral_audit_only_no_k6_no_dbr_no_rcled_no_dipoles_no_finite_patch_no_optimization")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
