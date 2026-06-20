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
from metasurface.stage13_lp_finite_patch import (
    CASE_FIELDS,
    PATCH_FIELDS,
    Q_FIELDS,
    Z_FIELDS,
    build_cases,
    build_config,
    build_patch_options,
    build_q_decisions,
    build_readme,
    build_report,
    build_source_z_decisions,
)
from stage13_2_define_finite_patch import DEFAULT_OUTPUT, LAYOUT, load_inputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage13-2 q/source-z decisions and prepared cases. No FDTD.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    meta = load_inputs()
    patches = build_patch_options(meta)
    q_rows = build_q_decisions(meta, LAYOUT.relative_to(REPO_ROOT).as_posix())
    z_rows = build_source_z_decisions()
    cases = build_cases(patches, q_rows)
    config = build_config(meta, patches, q_rows, z_rows, cases)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv_rows(patches, args.output_dir / "finite_patch_options.csv", PATCH_FIELDS)
    write_csv_rows(q_rows, args.output_dir / "q_decision_table.csv", Q_FIELDS)
    write_csv_rows(z_rows, args.output_dir / "source_z_decision_table.csv", Z_FIELDS)
    write_csv_rows(cases, args.output_dir / "stage13_2_minimal_dipole_cases.csv", CASE_FIELDS)
    (args.output_dir / "stage13_2_finite_patch_config_candidates.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (args.output_dir / "stage13_2_decision_report.md").write_text(build_report(meta, patches, q_rows, z_rows), encoding="utf-8")
    (args.output_dir / "README.md").write_text(build_readme(), encoding="utf-8")
    print(f"output_dir={args.output_dir}")
    print(f"case_count={len(cases)}")
    print(f"recommended_patch_option={config['recommended_patch_option_id']}")
    print(f"q_status={config['q_status']}")
    print(f"recommended_q_nm={config['recommended_q_nm']}")
    print(f"source_z_status={config['source_z_status']}")
    print("run_fdtd=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
