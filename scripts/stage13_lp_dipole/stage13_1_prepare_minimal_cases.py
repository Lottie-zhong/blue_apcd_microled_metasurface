from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.stage13_lp_dipole import CASE_FIELDS, build_config, build_minimal_cases, build_readme, load_single_audit, write_csv_rows


DEFAULT_OUTPUT = REPO_ROOT / "outputs/stage13_0_lp_dipole_geometry_audit"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage13-1 minimal LP dipole config preparation. No FDTD.")
    parser.add_argument("--audit-csv", type=Path, default=DEFAULT_OUTPUT / "geometry_audit.csv")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = load_single_audit(args.audit_csv)
    cases = build_minimal_cases(audit)
    config = build_config(audit, cases)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv_rows(cases, args.output_dir / "stage13_1_minimal_dipole_cases.csv", CASE_FIELDS)
    (args.output_dir / "stage13_1_minimal_dipole_config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (args.output_dir / "README.md").write_text(build_readme(audit), encoding="utf-8")
    print(f"output_dir={args.output_dir}")
    print(f"case_count={len(cases)}")
    print(f"q_status={config['q_status']}")
    print(f"q_nm={config['q_nm']}")
    print("statuses=prepared_not_run")
    print("run_fdtd=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
