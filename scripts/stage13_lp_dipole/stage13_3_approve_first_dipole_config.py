from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.stage13_lp_dipole import write_csv_rows
from metasurface.stage13_lp_first_dipole_config import (
    CASE_FIELDS,
    build_blocker_status,
    build_cases,
    build_config,
    build_manual_approval_record,
    build_readme,
    load_and_validate_inputs,
)


STAGE13_2_DIR = REPO_ROOT / "outputs/stage13_2_lp_finite_patch_definition"
PATCH_CSV = STAGE13_2_DIR / "finite_patch_options.csv"
Q_CSV = STAGE13_2_DIR / "q_decision_table.csv"
STAGE13_2_CONFIG = STAGE13_2_DIR / "stage13_2_finite_patch_config_candidates.json"
STAGE12_FDTD_CODE = REPO_ROOT / "src/metasurface/stage12_k6_fdtd.py"
DEFAULT_OUTPUT = REPO_ROOT / "outputs/stage13_3_lp_first_dipole_manual_config"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage13-3 first no-DBR LP dipole approval/config generation. No FDTD.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    evidence = load_and_validate_inputs(PATCH_CSV, Q_CSV, STAGE13_2_CONFIG, STAGE12_FDTD_CODE)
    cases = build_cases()
    config = build_config(evidence, cases)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv_rows(cases, args.output_dir / "stage13_3_first_no_dbr_minimal_cases.csv", CASE_FIELDS)
    (args.output_dir / "stage13_3_first_no_dbr_config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (args.output_dir / "manual_approval_record.md").write_text(build_manual_approval_record(evidence), encoding="utf-8")
    (args.output_dir / "fdtd_blocker_status.md").write_text(build_blocker_status(), encoding="utf-8")
    (args.output_dir / "README.md").write_text(build_readme(), encoding="utf-8")
    print(f"output_dir={args.output_dir}")
    print(f"case_count={len(cases)}")
    print("patch_approval=manually_approved_for_first_no_dbr_diagnostic")
    print("q_approval=manually_approved_for_first_no_dbr_diagnostic")
    print("source_z_status=diagnostic_manual_placeholder")
    print("next_fdtd_cases=center_x,center_y")
    print("configuration_blockers=0")
    print("run_fdtd=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
