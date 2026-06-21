from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi
from metasurface.stage13_4_center_dipole import (
    ALLOWED_CASE_IDS,
    CASE_METRIC_FIELDS,
    OUTPUT_DIR_NAME,
    build_extraction_notes,
    build_patch_inventory,
    build_readme,
    build_run_summary,
    build_setup,
    incoherent_rows,
    load_approved_plan,
    resolved_setup,
    run_case,
    validate_case_selection,
    write_csv_rows,
    INCOHERENT_FIELDS,
)


CONFIG_JSON = REPO_ROOT / "outputs/stage13_3_lp_first_dipole_manual_config/stage13_3_first_no_dbr_config.json"
CASES_CSV = REPO_ROOT / "outputs/stage13_3_lp_first_dipole_manual_config/stage13_3_first_no_dbr_minimal_cases.csv"
LAYOUT_CSV = REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_layout_plan.csv"
DEFAULT_OUTPUT = REPO_ROOT / "outputs" / OUTPUT_DIR_NAME


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage13-4 gated LP center_x then center_y no-DBR FDTD diagnostic.")
    parser.add_argument("--runtime", default=str(REPO_ROOT / "configs/runtime.yaml"))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cases", nargs="+", required=True)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--show-gui", action="store_true")
    return parser.parse_args()


def print_preflight(setup: dict[str, object]) -> None:
    print(f"resolved_patch={setup['patch_option_id']} {setup['Nx']}x{setup['Ny']}")
    print(f"resolved_geometry={setup['estimated_dimers']} dimers / {setup['estimated_nanopillars']} nanopillars")
    print(f"source_nm=({setup['source_x_nm']}, {setup['source_y_nm']}, {setup['source_z_nm']})")
    print(f"monitor_direction={setup['monitor_direction']}")
    print(f"target_LP={setup['target_LP']} leakage_LP={setup['leakage_LP']}")
    print(f"DBR={str(setup['DBR']).lower()} RCLED={str(setup['RCLED']).lower()}")
    print(f"selected_cases={','.join(setup['selected_cases'])}")
    print(f"farfield_grid={setup['farfield_grid']} simulation_time_fs={setup['simulation_time_fs']}")
    print(f"solver_processes={setup['solver_processes']}")
    print(f"background_stack={setup['background_stack']}")


def main() -> int:
    args = parse_args()
    validate_case_selection(args.cases)
    plan = load_approved_plan(CONFIG_JSON, CASES_CSV, LAYOUT_CSV)
    inventory = build_patch_inventory(plan)
    setup = resolved_setup(plan, inventory)
    print_preflight(setup)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "_saved_fsp").mkdir(parents=True, exist_ok=True)
    (args.output_dir / "stage13_4_resolved_setup.json").write_text(json.dumps(setup, indent=2), encoding="utf-8")
    if not args.run:
        print("run_fdtd=false (preflight only; pass --run to execute)")
        return 0
    runtime = load_runtime_config(args.runtime)
    lumapi = import_lumapi(runtime)
    setup_fsp = args.output_dir / "_saved_fsp/stage13_4_A_small_center_setup.fsp"
    fdtd = None
    setup_state: dict[str, object] = {"status": "not_started"}
    try:
        fdtd = lumapi.FDTD(hide=(not args.show_gui) and runtime.hide_gui)
        build_setup(fdtd, setup, inventory)
        fdtd.save(str(setup_fsp.resolve()))
        setup_state = {"status": "ok", "lifecycle": ["build_setup", "save_setup", "close_setup"], "setup_fsp": str(setup_fsp)}
    except Exception as exc:
        setup_state = {"status": "failed", "error": f"{type(exc).__name__}: {exc}", "setup_fsp": str(setup_fsp)}
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass
    runtime_state: dict[str, object] = {"setup": setup_state}
    rows: list[dict[str, object]] = []
    if setup_state["status"] == "ok":
        center_x_rows, center_x_state = run_case(lumapi, runtime, setup_fsp, "center_x", setup, args.output_dir, args.show_gui)
        rows.extend(center_x_rows)
        runtime_state["center_x"] = center_x_state
        center_x_ok = center_x_state.get("status") == "ok" and all(row.get("extraction_status") == "complex_vector_ok" for row in center_x_rows)
        if center_x_ok:
            center_y_rows, center_y_state = run_case(lumapi, runtime, setup_fsp, "center_y", setup, args.output_dir, args.show_gui)
            rows.extend(center_y_rows)
            runtime_state["center_y"] = center_y_state
        else:
            runtime_state["center_y"] = {"status": "not_run_due_center_x_gate"}
    else:
        runtime_state["center_x"] = {"status": "not_run_due_setup_failure"}
        runtime_state["center_y"] = {"status": "not_run_due_setup_failure"}
    write_csv_rows(args.output_dir / "stage13_4_case_metrics.csv", rows, CASE_METRIC_FIELDS)
    incoherent = incoherent_rows(rows)
    write_csv_rows(args.output_dir / "stage13_4_center_incoherent_average.csv", incoherent, INCOHERENT_FIELDS)
    (args.output_dir / "stage13_4_runtime_state.json").write_text(json.dumps(runtime_state, indent=2), encoding="utf-8")
    (args.output_dir / "stage13_4_extraction_notes.md").write_text(build_extraction_notes(setup, runtime_state), encoding="utf-8")
    (args.output_dir / "stage13_4_run_summary.md").write_text(build_run_summary(setup, rows, incoherent, runtime_state), encoding="utf-8")
    (args.output_dir / "README.md").write_text(build_readme(setup), encoding="utf-8")
    print(json.dumps(runtime_state, indent=2))
    center_x_ok = runtime_state.get("center_x", {}).get("status") == "ok"
    center_y_ok = runtime_state.get("center_y", {}).get("status") == "ok"
    return 0 if center_x_ok and center_y_ok and len(incoherent) == 3 else 1


if __name__ == "__main__":
    raise SystemExit(main())
