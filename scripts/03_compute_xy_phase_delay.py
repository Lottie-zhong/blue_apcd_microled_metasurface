from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.phase_delay import compute_xy_phase_delay_from_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute wrapped x/y nanofin phase delay.")
    parser.add_argument(
        "--x-summary",
        default="outputs/nanofin_single_x/single_nanofin_x_summary.csv",
        help="Path to solved x-polarized single nanofin summary CSV.",
    )
    parser.add_argument(
        "--y-summary",
        default="outputs/nanofin_single_y/single_nanofin_y_summary.csv",
        help="Path to solved y-polarized single nanofin summary CSV.",
    )
    parser.add_argument(
        "--output",
        default="outputs/nanofin_xy_phase_delay/nanofin_xy_phase_delay.csv",
        help="Output CSV path for wrapped phase delay.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = compute_xy_phase_delay_from_files(
        x_summary_path=args.x_summary,
        y_summary_path=args.y_summary,
        output_path=args.output,
    )
    print(f"output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
