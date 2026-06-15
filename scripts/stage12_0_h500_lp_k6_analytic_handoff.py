from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.stage12_k6_analytic import (
    ARRAY_FACTOR_FIELDS,
    COEFFICIENT_FIELDS,
    DEFAULT_DIMER_PITCH_X_NM,
    DEFAULT_WAVELENGTH_NM,
    FORWARD_BINS,
    LAYOUT_PLAN_FIELDS,
    REVERSE_BINS,
    Metadata,
    build_layout_plan_rows,
    build_order_coefficients,
    choose_preferred_order,
    compute_array_factor,
    diagnose,
    read_phase_library,
    write_csv_rows,
    write_summary,
)


DEFAULT_INPUT = REPO_ROOT / "outputs/stage11_2i_h500_lp_actual_dimer_6bin_freeze/stage12_handoff_phase_library.csv"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "outputs/stage12_0_h500_lp_k6_analytic_handoff"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage12-0 H500 LP-APCD K=6 analytic/layout handoff. No FDTD.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--wavelength-nm", type=float, default=DEFAULT_WAVELENGTH_NM)
    parser.add_argument("--dimer-pitch-x-nm", type=float, default=DEFAULT_DIMER_PITCH_X_NM)
    parser.add_argument("--symbolic-angle-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = Metadata(
        wavelength_nm=None if args.symbolic_angle_only else args.wavelength_nm,
        dimer_pitch_x_nm=None if args.symbolic_angle_only else args.dimer_pitch_x_nm,
    )
    entries = read_phase_library(args.input)

    forward_coeffs = build_order_coefficients(entries, FORWARD_BINS, "forward", metadata)
    reverse_coeffs = build_order_coefficients(entries, REVERSE_BINS, "reverse", metadata)
    forward_af = compute_array_factor(forward_coeffs, metadata)
    reverse_af = compute_array_factor(reverse_coeffs, metadata)
    forward_diag = diagnose(forward_coeffs, forward_af)
    reverse_diag = diagnose(reverse_coeffs, reverse_af)
    preferred_order = choose_preferred_order(forward_diag, reverse_diag)

    out = args.output_dir
    write_csv_rows(forward_coeffs, out / "k6_forward_order_coefficients.csv", COEFFICIENT_FIELDS)
    write_csv_rows(reverse_coeffs, out / "k6_reverse_order_coefficients.csv", COEFFICIENT_FIELDS)
    write_csv_rows(forward_af, out / "k6_forward_array_factor.csv", ARRAY_FACTOR_FIELDS)
    write_csv_rows(reverse_af, out / "k6_reverse_array_factor.csv", ARRAY_FACTOR_FIELDS)
    write_csv_rows(
        build_layout_plan_rows(forward_coeffs, reverse_coeffs),
        out / "stage12_1_candidate_layout_plan.csv",
        LAYOUT_PLAN_FIELDS,
    )
    write_summary(out / "stage12_0_k6_analytic_summary.md", args.input, metadata, forward_diag, reverse_diag, preferred_order)

    print(f"output_dir={out}")
    print(f"forward_dominant_order={forward_diag['dominant_order_m']}")
    print(f"forward_relative_strength={forward_diag['dominant_relative_strength']:.6f}")
    print(f"reverse_dominant_order={reverse_diag['dominant_order_m']}")
    print(f"reverse_relative_strength={reverse_diag['dominant_relative_strength']:.6f}")
    print(f"preferred_order={preferred_order}")
    print("boundary=no_fdtd_no_fsp_no_lp_steering_completion_claim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
