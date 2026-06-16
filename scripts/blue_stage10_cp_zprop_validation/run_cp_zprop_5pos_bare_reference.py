from __future__ import annotations

import argparse
import json
from pathlib import Path

from run_cp_zprop_5pos_xy_sweep import build_cases, ensure_dirs, write_csv, OFFSET_NM

OUT_DIR = Path("outputs/blue_stage10_cp_zprop_validation/five_position_sweep")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Optional bare-reference scaffold for calibrated +z 5-position x/y dipole cases. Default is plan-only; no FDTD run.")
    parser.add_argument("--output-dir", default=str(OUT_DIR))
    parser.add_argument("--run", action="store_true", help="Actually run bare-reference FDTD cases. Not used by default.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    ensure_dirs(out_dir)
    cases = build_cases()
    rows = []
    for c in cases:
        rows.append({
            "case_id": "BARE_" + c["case_id"],
            "position_id": c["position_id"],
            "x_nm": c["x_nm"],
            "y_nm": c["y_nm"],
            "z_nm": c["z_nm"],
            "orientation": c["orientation"],
            "offset_nm": OFFSET_NM,
            "run_status": "not_run" if not args.run else "unsupported_in_scaffold",
            "notes": "Plan-only bare reference scaffold. Implement/run only after user confirms extra 10 FDTD cases.",
        })
    write_csv(out_dir / "five_position_bare_reference_run_plan.csv", rows)
    report = {
        "bare_reference_run": bool(args.run),
        "status": "not_run_plan_only" if not args.run else "unsupported_in_scaffold",
        "reason": "User requested bare reference only if cheap/straightforward; this task keeps FDTD count to the 10 metasurface cases.",
        "planned_cases": len(rows),
    }
    (out_dir / "five_position_bare_reference_debug.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
