from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.stage12_k6_layout import (
    GEOMETRY_AUDIT_FIELDS,
    LAYOUT_FIELDS,
    PHASE_AUDIT_FIELDS,
    build_stage12_1_layout,
    write_csv_rows,
)


DEFAULT_HANDOFF = REPO_ROOT / "outputs/stage11_2i_h500_lp_actual_dimer_6bin_freeze/stage12_handoff_phase_library.csv"
DEFAULT_OUT = REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage12-1 H500 LP-APCD K=6 forward layout preparation. No FDTD.")
    parser.add_argument("--handoff", type=Path, default=DEFAULT_HANDOFF)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle = build_stage12_1_layout(REPO_ROOT, args.handoff)
    out = args.output_dir
    write_csv_rows(bundle.layout_rows, out / "stage12_1_k6_forward_layout_plan.csv", LAYOUT_FIELDS)
    write_csv_rows(bundle.geometry_rows, out / "stage12_1_k6_forward_geometry_audit.csv", GEOMETRY_AUDIT_FIELDS)
    write_csv_rows(bundle.phase_rows, out / "stage12_1_k6_forward_phase_amplitude_audit.csv", PHASE_AUDIT_FIELDS)
    (out / "stage12_1_k6_forward_layout_summary.md").parent.mkdir(parents=True, exist_ok=True)
    (out / "stage12_1_k6_forward_layout_summary.md").write_text(bundle.summary_md, encoding="utf-8")
    (out / "stage12_2_single_fdfd_or_fdtd_run_plan.md").write_text(bundle.run_plan_md, encoding="utf-8")

    min_clearance = min(
        min(float(row["internal_clearance_nm"]), float(row["min_neighbor_clearance_nm"])) for row in bundle.geometry_rows
    )
    legal = all(str(row["geometry_legal"]).lower() == "true" for row in bundle.geometry_rows)
    print(f"output_dir={out}")
    print(f"layout_rows={len(bundle.layout_rows)}")
    print(f"geometry_legal={legal}")
    print(f"minimum_clearance_nm={min_clearance:.6f}")
    print("expected_plus1_angle_deg=10.000000")
    print(f"stage12_2_single_full_fdtd_can_proceed={legal}")
    print("boundary=no_fdtd_no_fsp_no_lp_steering_completion_claim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
