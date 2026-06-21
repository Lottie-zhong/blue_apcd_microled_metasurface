from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.stage13_4_center_dipole import (
    INCOHERENT_FIELDS,
    OUTPUT_DIR_NAME,
    build_patch_inventory,
    build_readme,
    build_run_summary,
    incoherent_rows,
    load_approved_plan,
    read_case_metrics,
    resolved_setup,
    write_csv_rows,
)


CONFIG_JSON = REPO_ROOT / "outputs/stage13_3_lp_first_dipole_manual_config/stage13_3_first_no_dbr_config.json"
CASES_CSV = REPO_ROOT / "outputs/stage13_3_lp_first_dipole_manual_config/stage13_3_first_no_dbr_minimal_cases.csv"
LAYOUT_CSV = REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_layout_plan.csv"
DEFAULT_OUTPUT = REPO_ROOT / "outputs" / OUTPUT_DIR_NAME


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize Stage13-4 center x/y dipole LP metrics incoherently.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    case_csv = args.output_dir / "stage13_4_case_metrics.csv"
    rows = read_case_metrics(case_csv)
    plan = load_approved_plan(CONFIG_JSON, CASES_CSV, LAYOUT_CSV)
    setup = resolved_setup(plan, build_patch_inventory(plan))
    incoherent = incoherent_rows(rows)
    runtime_state: dict[str, object] = {}
    state_path = args.output_dir / "stage13_4_runtime_state.json"
    if state_path.is_file():
        runtime_state = json.loads(state_path.read_text(encoding="utf-8"))
    write_csv_rows(args.output_dir / "stage13_4_center_incoherent_average.csv", incoherent, INCOHERENT_FIELDS)
    (args.output_dir / "stage13_4_run_summary.md").write_text(build_run_summary(setup, rows, incoherent, runtime_state), encoding="utf-8")
    (args.output_dir / "README.md").write_text(build_readme(setup), encoding="utf-8")
    print(json.dumps({"incoherent_rows": incoherent}, indent=2))
    return 0 if len(incoherent) == 3 else 1


if __name__ == "__main__":
    raise SystemExit(main())
