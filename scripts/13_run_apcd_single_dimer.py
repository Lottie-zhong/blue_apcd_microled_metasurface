from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.apcd_dimer import (
    APCDSingleDimerRunner,
    write_apcd_single_dimer_results,
    write_apcd_single_dimer_summary,
    write_jones_matrix_alpha_beta_basis_npy,
    write_jones_matrix_linear_basis_npy,
    write_jones_matrix_npy,
)
from metasurface.config import load_apcd_single_dimer_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Gate 1 single APCD dimer validation at 633 nm.")
    parser.add_argument("--config", default="configs/apcd_fig2_elliptical_633nm.yaml", help="APCD dimer YAML config.")
    parser.add_argument("--runtime", default="configs/runtime.yaml", help="Local runtime YAML.")
    parser.add_argument("--dry-run", action="store_true", help="Write planned outputs without importing lumapi.")
    parser.add_argument("--setup-only", action="store_true", help="Build and save the FDTD model without running it.")
    parser.add_argument(
        "--fsp-output",
        default=None,
        help="Optional .fsp output path for --setup-only.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_apcd_single_dimer_config(args.config)
    row = APCDSingleDimerRunner.from_runtime_file(
        config=config,
        runtime_path=args.runtime,
        dry_run=args.dry_run,
        setup_only=args.setup_only,
        fsp_output=args.fsp_output,
    ).run()

    result_dir = config.output.result_dir
    results_path = ""
    summary_path = ""
    if args.setup_only:
        summary_path = write_apcd_single_dimer_summary(row, result_dir / "summary.md")
    else:
        results_path = write_apcd_single_dimer_results(row, result_dir / "results.csv")
        summary_path = write_apcd_single_dimer_summary(row, result_dir / "summary.md")
        if not args.dry_run and row["status"] == "ok":
            if config.target.output_basis == "alpha_beta":
                write_jones_matrix_linear_basis_npy(row, result_dir / "jones_matrix_linear_basis.npy")
                write_jones_matrix_alpha_beta_basis_npy(row, result_dir / "jones_matrix_alpha_beta_basis.npy")
            else:
                write_jones_matrix_npy(row, result_dir / "jones_matrix_circular_basis.npy")

    print(f"status={row['status']}")
    print(f"gate_pass={row['gate_pass']}")
    print(f"target_conversion={row['target_conversion']}")
    print(f"opposite_spin_leakage={row['opposite_spin_leakage']}")
    print(f"spin_ER_dB={row['spin_ER_dB']}")
    if row.get("PD", "") != "":
        print(f"PD={row['PD']}")
    if results_path:
        print(f"results={results_path}")
    if summary_path:
        print(f"summary={summary_path}")
    if args.setup_only:
        print(row["note"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
