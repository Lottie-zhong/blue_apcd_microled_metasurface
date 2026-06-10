from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.config import load_nanofin_single_config
from metasurface.nanofin_single import SingleNanofinRunner, write_single_nanofin_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one 450 nm TiO2 rectangular nanofin case.")
    parser.add_argument("--config", required=True, help="Path to public single-nanofin YAML config.")
    parser.add_argument("--runtime", default="configs/runtime.yaml", help="Path to local runtime YAML.")
    parser.add_argument("--dry-run", action="store_true", help="Generate planned single-case CSV without lumapi.")
    parser.add_argument("--setup-only", action="store_true", help="Build and save the FDTD model without running it.")
    parser.add_argument("--fsp-output", default=None, help="Optional .fsp output path for --setup-only.")
    parser.add_argument("--load-fsp", default=None, help="Open an existing .fsp before run or extraction.")
    parser.add_argument("--extract-only", action="store_true", help="Extract results from --load-fsp without running.")
    parser.add_argument("--output", default=None, help="Optional output CSV path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_nanofin_single_config(args.config)
    runner = SingleNanofinRunner.from_runtime_file(
        config=config,
        runtime_path=args.runtime,
        dry_run=args.dry_run,
        setup_only=args.setup_only,
        fsp_output=args.fsp_output,
        load_fsp=args.load_fsp,
        extract_only=args.extract_only,
    )
    rows = runner.run()

    output_path = Path(args.output) if args.output else config.output.result_dir / "single_nanofin_summary.csv"
    written_path = write_single_nanofin_summary(rows, output_path)

    print(f"status={'dry_run' if args.dry_run else rows[0]['status']}")
    print(f"rows={len(rows)}")
    print(f"output={written_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
