from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_cp_zprop_center_xy_t100 as base
from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi

OUT_DIR = Path("outputs/blue_stage10_cp_zprop_validation")
TIMES_FS = [150, 200]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run +z center x/y dipole time convergence cases T150/T200 only.")
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--output-dir", default=str(OUT_DIR))
    parser.add_argument("--time-fs", type=int, nargs="*", default=TIMES_FS)
    parser.add_argument("--show-gui", action="store_true")
    parser.add_argument("--skip-existing", action="store_true", default=True)
    return parser.parse_args()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def make_case(template: dict[str, Any], time_fs: int) -> dict[str, Any]:
    c = dict(template)
    c["case_id"] = f"CP_ZPROP_CENTER_{template['orientation'].upper()}_T{time_fs}FS"
    return c


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    base.ensure_dirs(out_dir)
    setup_fsp = out_dir / base.SETUP_FSP_NAME
    runtime = load_runtime_config(args.runtime)
    lumapi = import_lumapi(runtime)
    if not setup_fsp.exists():
        fdtd = None
        try:
            fdtd = lumapi.FDTD(hide=(not args.show_gui) and runtime.hide_gui)
            warnings, inventory = base.build_setup(fdtd, max(args.time_fs))
            fdtd.save(str(setup_fsp.resolve()))
            base.write_plan(out_dir, inventory, warnings)
        finally:
            if fdtd is not None:
                try:
                    fdtd.close()
                except Exception:
                    pass
    rows: list[dict[str, Any]] = []
    for time_fs in args.time_fs:
        for template in base.CASES:
            case = make_case(template, int(time_fs))
            target = out_dir / "_saved_fsp" / f"{case['case_id']}.fsp"
            if args.skip_existing and target.exists():
                rows.append({"case_id": case["case_id"], "orientation": case["orientation"], "simulation_time_fs": time_fs, "fdtd_status": "reused_existing", "result_fsp": str(target), "notes": "existing FSP reused; no new run"})
                continue
            row = base.run_case(lumapi, runtime, setup_fsp, case, out_dir, float(time_fs), args.show_gui)
            row["simulation_time_fs"] = time_fs
            rows.append(row)
    write_csv(out_dir / "cp_zprop_time_run_status.csv", rows)
    print(json.dumps({"rows": rows}, indent=2))
    return 0 if all(r["fdtd_status"] in {"ok", "reused_existing"} for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
