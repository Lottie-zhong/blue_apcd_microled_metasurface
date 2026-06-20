from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.stage13_lp_dipole import write_csv_rows
from metasurface.stage13_lp_finite_patch import PATCH_FIELDS, build_patch_options, parse_frozen_supercell


LAYOUT = REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_layout_plan.csv"
GEOMETRY = REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_geometry_audit.csv"
METRICS = REPO_ROOT / "outputs/stage12_6_h500_lp_k6_official_result_package/stage12_6_key_metrics.csv"
STAGE13_AUDIT = REPO_ROOT / "outputs/stage13_0_lp_dipole_geometry_audit/geometry_audit.csv"
LAYOUT_CODE = REPO_ROOT / "src/metasurface/stage12_k6_layout.py"
FDTD_CODE = REPO_ROOT / "src/metasurface/stage12_k6_fdtd.py"
DEFAULT_OUTPUT = REPO_ROOT / "outputs/stage13_2_lp_finite_patch_definition"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage13-2 finite-patch candidate definitions. No FDTD.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def load_inputs() -> dict[str, object]:
    sources = [LAYOUT, GEOMETRY, METRICS, STAGE13_AUDIT, LAYOUT_CODE, FDTD_CODE]
    for path in sources:
        if not path.is_file():
            raise FileNotFoundError(f"required Stage13-2 evidence file missing: {path}")
    return parse_frozen_supercell(LAYOUT, GEOMETRY, sources, REPO_ROOT)


def main() -> int:
    args = parse_args()
    meta = load_inputs()
    options = build_patch_options(meta)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv_rows(options, args.output_dir / "finite_patch_options.csv", PATCH_FIELDS)
    recommended = next(row for row in options if row["recommended_for_first_FDTD"] is True)
    print(f"output_dir={args.output_dir}")
    print(f"patch_option_count={len(options)}")
    print(f"recommended_patch_option={recommended['patch_option_id']}")
    print(f"supercell_period_x_nm={meta['supercell_period_x_nm']}")
    print(f"y_pitch_nm={meta['y_pitch_nm']}")
    print("run_fdtd=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
