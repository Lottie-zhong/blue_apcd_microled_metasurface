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
from metasurface.stage12_k6_gui_inspection import FSP_FILENAME, Stage12GuiPaths, run_stage12_3b


OUT = REPO_ROOT / "outputs/stage12_3b_h500_lp_k6_gui_inspection"
PATHS = Stage12GuiPaths(
    layout_plan_csv=REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_layout_plan.csv",
    geometry_audit_csv=REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_geometry_audit.csv",
    phase_amplitude_audit_csv=REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_phase_amplitude_audit.csv",
    output_dir=OUT,
    fsp_path=OUT / FSP_FILENAME,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage12-3B setup-only GUI inspection .fsp export for H500 LP-APCD K=6 forward layout.")
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runtime = load_runtime_config(args.runtime)
    lumapi = import_lumapi(runtime)
    result = run_stage12_3b(PATHS, lumapi, runtime)
    print(f"fsp_path={result['fsp_path']}")
    print(f"fsp_generated={result['fsp_generated']}")
    print(f"marker_csv={result['marker_csv']}")
    print(f"summary_md={result['summary_md']}")
    print(f"marker_count={result['marker_count']}")
    print("boundary=setup_only_no_fdtd_run_no_optimization")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
