from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path: sys.path.insert(0, str(SRC))

from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi
from metasurface.stage13_4_center_dipole import build_patch_inventory, build_setup, load_approved_plan, resolved_setup
from metasurface.stage13_7c_center_x_source_coupling import (
    CASE_FIELDS, ORDER_FIELDS, OUTPUT_DIR_NAME, PEAK_FIELDS, SHIFT_FIELDS, build_extraction_notes,
    build_report, build_shift_candidates, mechanism_summary, reproducibility_check, run_case,
    selected_shift, write_csv,
)

CONFIG = REPO_ROOT / "outputs/stage13_3_lp_first_dipole_manual_config/stage13_3_first_no_dbr_config.json"
CASES = REPO_ROOT / "outputs/stage13_3_lp_first_dipole_manual_config/stage13_3_first_no_dbr_minimal_cases.csv"
LAYOUT = REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_layout_plan.csv"
BASE_CASES = REPO_ROOT / "outputs/stage13_4_lp_no_dbr_center_dipole/stage13_4_case_metrics.csv"
BASE_PEAKS = REPO_ROOT / "outputs/stage13_5_lp_no_dbr_center_order_diagnosis/stage13_5_peak_metrics.csv"
OPERATIONAL_NOTE = "Initial SSH client timeout left the original remote job running; a duplicate launch was detected and its newer process tree was terminated. Only the original job chain produced the reported CSVs. Exact repeat reproduction supports retained-run integrity."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--runtime", default=str(REPO_ROOT / "configs/runtime.yaml"))
    parser.add_argument("--show-gui", action="store_true")
    return parser.parse_args()


def read_csv(path: Path):
    import csv
    with path.open(encoding="utf-8-sig", newline="") as handle: return list(csv.DictReader(handle))


def main() -> int:
    args = parse_args(); output = REPO_ROOT / "outputs" / OUTPUT_DIR_NAME
    plan = load_approved_plan(CONFIG, CASES, LAYOUT); inventory = build_patch_inventory(plan); setup = resolved_setup(plan, inventory)
    shifts = build_shift_candidates(inventory, plan["layout_rows"]); shift = selected_shift(shifts)
    cases = [
        {"case_id": "center_x_repeat", "source_x_nm": 0.0, "source_y_nm": 0.0, "source_z_nm": -200.0, "purpose": "Stage13-4 reproducibility control"},
        {"case_id": "center_mid_120_180_x", "source_x_nm": 0.0, "source_y_nm": 0.0, "source_z_nm": -350.0, "purpose": "deeper diagnostic source to soften local coupling"},
    ]
    if shift is not None: cases.append({"case_id": "source_shift_to_cell_mid_x", "source_x_nm": shift, "source_y_nm": 0.0, "source_z_nm": -200.0, "purpose": "safe lateral shift maximizing nearest-pillar distance"})
    output.mkdir(parents=True, exist_ok=True); (output / "_saved_fsp").mkdir(exist_ok=True)
    write_csv(output / "stage13_7c_source_shift_candidates.csv", shifts, SHIFT_FIELDS)
    print(f"patch={setup['patch_option_id']} {setup['Nx']}x{setup['Ny']} geometry={setup['estimated_dimers']} dimers/{setup['estimated_nanopillars']} pillars")
    print(f"monitor={setup['monitor_direction']} target_LP={setup['target_LP']} DBR={setup['DBR']} RCLED={setup['RCLED']}")
    print("selected_cases=" + json.dumps(cases))
    if not args.run: print("run_fdtd=false"); return 0
    runtime = load_runtime_config(args.runtime); lumapi = import_lumapi(runtime)
    setup_fsp = output / "_saved_fsp/stage13_7c_A_small_setup.fsp"; fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not args.show_gui) and runtime.hide_gui); build_setup(fdtd, setup, inventory); fdtd.save(str(setup_fsp.resolve()))
    finally:
        if fdtd is not None:
            try: fdtd.close()
            except Exception: pass
    normal_rows=[]; order_rows=[]; peaks=[]; states={}; repeat=None
    for case in cases:
        nrows, orows, peak, state = run_case(lumapi, runtime, setup_fsp, output, setup, case, args.show_gui)
        normal_rows += nrows; order_rows += orows; peaks.append(peak); states[case["case_id"]] = state
        write_csv(output / "stage13_7c_case_metrics.csv", normal_rows, CASE_FIELDS); write_csv(output / "stage13_7c_order_cone_metrics.csv", order_rows, ORDER_FIELDS); write_csv(output / "stage13_7c_peak_metrics.csv", peaks, PEAK_FIELDS)
        if state.get("status") != "ok": break
        if case["case_id"] == "center_x_repeat":
            repeat = reproducibility_check(nrows, peak, read_csv(BASE_CASES), read_csv(BASE_PEAKS))
            if not repeat["passed"]: states["stop_reason"] = "repeat_reproducibility_failed"; break
    completed_cases = [case for case in cases if states.get(case["case_id"], {}).get("status") == "ok"]
    summary = mechanism_summary(cases, normal_rows, order_rows, peaks, states, repeat, shift)
    (output / "stage13_7c_mechanism_report.md").write_text(build_report(cases, shifts, normal_rows, order_rows, peaks, summary, repeat), encoding="utf-8")
    (output / "stage13_7c_extraction_notes.md").write_text(build_extraction_notes(states, OPERATIONAL_NOTE), encoding="utf-8")
    (output / "README.md").write_text("# Stage13-7C center_x source-coupling diagnostic\n\nOnly controlled x-dipole cases; no center_y, +/-q, DBR/RCLED, geometry change, or raw arrays.\n", encoding="utf-8")
    (output / "stage13_7c_runtime_state.json").write_text(json.dumps({"states": states, "summary": summary}, indent=2), encoding="utf-8")
    print(json.dumps({"states": states, "summary": summary}, indent=2))
    return 0 if summary["all_selected_cases_completed"] and summary["repeat_reproduced"] else 1


if __name__ == "__main__": raise SystemExit(main())
