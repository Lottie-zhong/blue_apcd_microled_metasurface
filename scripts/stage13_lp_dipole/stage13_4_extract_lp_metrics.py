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
    extract_case_fsp,
    load_approved_plan,
    resolved_setup,
    write_csv_rows,
)


CONFIG_JSON = REPO_ROOT / "outputs/stage13_3_lp_first_dipole_manual_config/stage13_3_first_no_dbr_config.json"
CASES_CSV = REPO_ROOT / "outputs/stage13_3_lp_first_dipole_manual_config/stage13_3_first_no_dbr_minimal_cases.csv"
LAYOUT_CSV = REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_layout_plan.csv"
DEFAULT_OUTPUT = REPO_ROOT / "outputs" / OUTPUT_DIR_NAME


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Re-extract Stage13-4 complex-vector LP cone metrics from saved FSP files.")
    parser.add_argument("--runtime", default=str(REPO_ROOT / "configs/runtime.yaml"))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--show-gui", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = load_approved_plan(CONFIG_JSON, CASES_CSV, LAYOUT_CSV)
    setup = resolved_setup(plan, build_patch_inventory(plan))
    runtime = load_runtime_config(args.runtime)
    lumapi = import_lumapi(runtime)
    rows: list[dict[str, object]] = []
    state: dict[str, object] = {}
    runtime_state: dict[str, object] = {}
    runtime_state_path = args.output_dir / "stage13_4_runtime_state.json"
    if runtime_state_path.is_file():
        runtime_state = json.loads(runtime_state_path.read_text(encoding="utf-8"))
    for case_id in ALLOWED_CASE_IDS:
        case_rows, case_state = extract_case_fsp(lumapi, runtime, case_id, setup, args.output_dir, args.show_gui)
        measured_runtime = runtime_state.get(case_id, {}).get("runtime_minutes", "")
        for row in case_rows:
            row["runtime_minutes"] = measured_runtime
        rows.extend(case_rows)
        state[case_id] = case_state
        if case_id == "center_x" and case_state.get("status") != "ok":
            state["center_y"] = {"status": "not_extracted_due_center_x_gate"}
            break
    write_csv_rows(args.output_dir / "stage13_4_case_metrics.csv", rows, CASE_METRIC_FIELDS)
    (args.output_dir / "stage13_4_extraction_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    (args.output_dir / "stage13_4_extraction_notes.md").write_text(build_extraction_notes(setup, state), encoding="utf-8")
    print(json.dumps(state, indent=2))
    return 0 if all(state.get(case_id, {}).get("status") == "ok" for case_id in ALLOWED_CASE_IDS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
