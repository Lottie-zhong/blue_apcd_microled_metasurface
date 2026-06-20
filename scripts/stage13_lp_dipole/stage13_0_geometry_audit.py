from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.stage13_lp_dipole import AUDIT_FIELDS, build_geometry_audit, build_geometry_markdown, build_readme, write_csv_rows


DEFAULT_LAYOUT = REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_layout_plan.csv"
DEFAULT_GEOMETRY = REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_geometry_audit.csv"
DEFAULT_METRICS = REPO_ROOT / "outputs/stage12_6_h500_lp_k6_official_result_package/stage12_6_key_metrics.csv"
DEFAULT_GUI_FSP = REPO_ROOT / "outputs/stage12_3b_h500_lp_k6_gui_inspection/stage12_3b_h500_lp_k6_forward_gui_inspection.fsp"
DEFAULT_OUTPUT = REPO_ROOT / "outputs/stage13_0_lp_dipole_geometry_audit"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage13-0 read-only frozen LP K=6 geometry audit. No FDTD.")
    parser.add_argument("--layout-csv", type=Path, default=DEFAULT_LAYOUT)
    parser.add_argument("--geometry-csv", type=Path, default=DEFAULT_GEOMETRY)
    parser.add_argument("--official-metrics-csv", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--gui-fsp", type=Path, default=DEFAULT_GUI_FSP)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_geometry_audit(REPO_ROOT, args.layout_csv, args.geometry_csv, args.official_metrics_csv, args.gui_fsp)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv_rows([audit], args.output_dir / "geometry_audit.csv", AUDIT_FIELDS)
    (args.output_dir / "geometry_audit.md").write_text(build_geometry_markdown(audit), encoding="utf-8")
    (args.output_dir / "README.md").write_text(build_readme(audit), encoding="utf-8")
    print(f"output_dir={args.output_dir}")
    print(f"geometry_audit_pass={audit['geometry_audit_pass']}")
    print(f"has_true_center_dimer={audit['has_true_center_dimer']}")
    print(f"q_status={audit['q_status']}")
    print(f"q_nm={audit['q_nm']}")
    print("run_fdtd=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
