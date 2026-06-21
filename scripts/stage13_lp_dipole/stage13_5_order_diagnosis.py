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
from metasurface.stage13_5_order_diagnosis import (
    CASES,
    COMPONENTS,
    GRID_N,
    INCOHERENT_FIELDS,
    ORDER_FIELDS,
    PEAK_FIELDS,
    build_extraction_notes,
    build_readme,
    build_report,
    component_arrays,
    cone_rows,
    direction_grid,
    incoherent_rows,
    intensity_components,
    mechanism_classification,
    peak_rows,
    save_map,
    write_csv_rows,
)
from metasurface.stage13_4_center_dipole import FIELD_MONITOR


STAGE13_4 = REPO_ROOT / "outputs/stage13_4_lp_no_dbr_center_dipole"
DEFAULT_OUTPUT = REPO_ROOT / "outputs/stage13_5_lp_no_dbr_center_order_diagnosis"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage13-5 read-only order-centered diagnosis of Stage13-4 center dipoles. No FDTD run.")
    parser.add_argument("--runtime", default=str(REPO_ROOT / "configs/runtime.yaml"))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--show-gui", action="store_true")
    return parser.parse_args()


def extract_case(lumapi: object, runtime: object, case_id: str, show_gui: bool) -> tuple[dict[str, object], dict[str, object]]:
    fsp = STAGE13_4 / "_saved_fsp" / f"stage13_4_{case_id}.fsp"
    if not fsp.is_file():
        raise FileNotFoundError(f"required Stage13-4 FSP missing: {fsp}")
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not show_gui) and runtime.hide_gui)
        fdtd.load(str(fsp.resolve()))
        vector = fdtd.farfieldvector3d(FIELD_MONITOR, 1, GRID_N, GRID_N)
        ex, ey, ez, vector_info = component_arrays(vector)
        ux = fdtd.farfieldux(FIELD_MONITOR, 1, GRID_N, GRID_N)
        uy = fdtd.farfielduy(FIELD_MONITOR, 1, GRID_N, GRID_N)
        xx, yy = direction_grid(ux, uy, ex.shape)
        data = {"ex": ex, "ey": ey, "ez": ez, "xx": xx, "yy": yy, "maps": intensity_components(ex, ey, ez)}
        debug = {
            "fsp": str(fsp),
            "fsp_size_bytes": fsp.stat().st_size,
            "farfieldvector3d": vector_info,
            "ux_shape": list(__import__("numpy").asarray(ux).shape),
            "uy_shape": list(__import__("numpy").asarray(uy).shape),
            "read_only": True,
            "run_called": False,
            "raw_arrays_saved": False,
        }
        return data, debug
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    runtime = load_runtime_config(args.runtime)
    lumapi = import_lumapi(runtime)
    all_peaks: list[dict[str, object]] = []
    all_orders: list[dict[str, object]] = []
    extraction_debug: dict[str, object] = {}
    for case_id in CASES:
        data, debug = extract_case(lumapi, runtime, case_id, args.show_gui)
        extraction_debug[case_id] = debug
        case_peaks = peak_rows(case_id, data["maps"], data["xx"], data["yy"])
        all_peaks.extend(case_peaks)
        all_orders.extend(cone_rows(case_id, data["maps"], data["xx"], data["yy"]))
        peak_by_component = {row["component"]: row for row in case_peaks}
        suffixes = {
            "Ex_target": "target_Ex2_map",
            "Ey_leakage": "leakage_Ey2_map",
            "transverse_total": "transverse_total_map",
            "vector_total": "vector_total_map",
        }
        for component in COMPONENTS:
            save_map(
                args.output_dir / f"{case_id}_{suffixes[component]}.png",
                f"{case_id}: {component}",
                data["maps"][component],
                data["xx"],
                data["yy"],
                peak_by_component[component],
            )
    averages = incoherent_rows(all_orders)
    classification = mechanism_classification(all_peaks, all_orders, averages)
    write_csv_rows(args.output_dir / "stage13_5_peak_metrics.csv", all_peaks, PEAK_FIELDS)
    write_csv_rows(args.output_dir / "stage13_5_order_cone_metrics.csv", all_orders, ORDER_FIELDS)
    write_csv_rows(args.output_dir / "stage13_5_order_incoherent_average.csv", averages, INCOHERENT_FIELDS)
    (args.output_dir / "stage13_5_mechanism_report.md").write_text(build_report(classification, all_peaks, averages), encoding="utf-8")
    (args.output_dir / "stage13_5_extraction_notes.md").write_text(build_extraction_notes(extraction_debug), encoding="utf-8")
    (args.output_dir / "README.md").write_text(build_readme(classification), encoding="utf-8")
    (args.output_dir / "stage13_5_classification.json").write_text(json.dumps(classification, indent=2), encoding="utf-8")
    print(json.dumps(classification, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
