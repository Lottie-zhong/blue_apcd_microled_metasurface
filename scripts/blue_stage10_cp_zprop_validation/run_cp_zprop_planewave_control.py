from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi

NM = 1e-9
OUT_DIR = Path("outputs/blue_stage10_cp_zprop_validation/planewave_control")
SAVED_FSP_DIR = OUT_DIR / "_saved_fsp"
WAVELENGTH_NM = 450.0
PERIOD_X_NM = 431.907786
PERIOD_Y_NM = 432.0
HEIGHT_NM = 525.0
MATERIAL_INDEX = 2.6
SOURCE_Z_NM = -250.0
MONITOR_Z_NM = HEIGHT_NM + 350.0
Z_MIN_NM = -500.0
Z_MAX_NM = HEIGHT_NM + 700.0
SIM_TIME_FS = 300.0
FIELD_MONITOR = "field_monitor"
POWER_MONITOR = "T"

PILLARS = [
    {"label": "A", "length_nm": 180.0, "width_nm": 90.0, "height_nm": 525.0, "rotation_deg": 37.5, "center_x_nm": -31.20933807846728, "center_y_nm": -85.74695164671414},
    {"label": "B", "length_nm": 230.0, "width_nm": 100.0, "height_nm": 525.0, "rotation_deg": -7.5, "center_x_nm": 31.20933807846728, "center_y_nm": 85.74695164671414},
]
CASES = [
    {"case_id": "EMPTY_XIN_ZPROP", "structure": "empty", "linear_input": "x", "polarization_angle_deg": 0.0},
    {"case_id": "EMPTY_YIN_ZPROP", "structure": "empty", "linear_input": "y", "polarization_angle_deg": 90.0},
    {"case_id": "DIMER_XIN_ZPROP", "structure": "frozen_dimer", "linear_input": "x", "polarization_angle_deg": 0.0},
    {"case_id": "DIMER_YIN_ZPROP", "structure": "frozen_dimer", "linear_input": "y", "polarization_angle_deg": 90.0},
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run +z periodic plane-wave x/y controls for frozen CP dimer and empty cell.")
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--output-dir", default=str(OUT_DIR))
    parser.add_argument("--simulation-time-fs", type=float, default=SIM_TIME_FS)
    parser.add_argument("--mesh-accuracy", type=int, default=3)
    parser.add_argument("--show-gui", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def ensure_dirs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "_saved_fsp").mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def add_pillars(fdtd: object) -> None:
    for pillar in PILLARS:
        fdtd.addrect()
        fdtd.set("name", f"frozen_dimer_pillar_{pillar['label']}")
        fdtd.set("x", float(pillar["center_x_nm"]) * NM)
        fdtd.set("y", float(pillar["center_y_nm"]) * NM)
        fdtd.set("x span", float(pillar["length_nm"]) * NM)
        fdtd.set("y span", float(pillar["width_nm"]) * NM)
        fdtd.set("z min", 0)
        fdtd.set("z max", float(pillar["height_nm"]) * NM)
        if float(pillar["rotation_deg"]):
            fdtd.set("first axis", "z")
            fdtd.set("rotation 1", float(pillar["rotation_deg"]))
        fdtd.set("material", "<Object defined dielectric>")
        fdtd.set("index", MATERIAL_INDEX)


def build_model(fdtd: object, case: dict[str, Any], sim_time_fs: float, mesh_accuracy: int) -> None:
    fdtd.switchtolayout()
    fdtd.deleteall()
    fdtd.addfdtd()
    fdtd.set("dimension", "3D")
    fdtd.set("x span", PERIOD_X_NM * NM)
    fdtd.set("y span", PERIOD_Y_NM * NM)
    fdtd.set("z min", Z_MIN_NM * NM)
    fdtd.set("z max", Z_MAX_NM * NM)
    fdtd.set("x min bc", "Periodic")
    fdtd.set("x max bc", "Periodic")
    fdtd.set("y min bc", "Periodic")
    fdtd.set("y max bc", "Periodic")
    fdtd.set("z min bc", "PML")
    fdtd.set("z max bc", "PML")
    fdtd.set("mesh accuracy", int(mesh_accuracy))
    fdtd.set("simulation time", sim_time_fs * 1e-15)

    if case["structure"] == "frozen_dimer":
        add_pillars(fdtd)

    fdtd.addplane()
    fdtd.set("name", "source")
    fdtd.set("injection axis", "z")
    fdtd.set("direction", "Forward")
    fdtd.set("x span", PERIOD_X_NM * NM)
    fdtd.set("y span", PERIOD_Y_NM * NM)
    fdtd.set("z", SOURCE_Z_NM * NM)
    fdtd.set("wavelength start", WAVELENGTH_NM * NM)
    fdtd.set("wavelength stop", WAVELENGTH_NM * NM)
    fdtd.set("polarization angle", float(case["polarization_angle_deg"]))

    fdtd.addpower()
    fdtd.set("name", POWER_MONITOR)
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", PERIOD_X_NM * NM)
    fdtd.set("y span", PERIOD_Y_NM * NM)
    fdtd.set("z", MONITOR_Z_NM * NM)

    fdtd.addprofile()
    fdtd.set("name", FIELD_MONITOR)
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", PERIOD_X_NM * NM)
    fdtd.set("y span", PERIOD_Y_NM * NM)
    fdtd.set("z", MONITOR_Z_NM * NM)


def run_case(lumapi: Any, runtime: Any, case: dict[str, Any], out_dir: Path, sim_time_fs: float, mesh_accuracy: int, show_gui: bool, dry_run: bool) -> dict[str, Any]:
    fsp_path = out_dir / "_saved_fsp" / f"{case['case_id']}.fsp"
    if dry_run:
        return {"case_id": case["case_id"], "structure": case["structure"], "linear_input": case["linear_input"], "fdtd_status": "not_run", "result_fsp": str(fsp_path), "note": "dry run"}
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not show_gui) and runtime.hide_gui)
        build_model(fdtd, case, sim_time_fs, mesh_accuracy)
        fdtd.save(str(fsp_path.resolve()))
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not show_gui) and runtime.hide_gui)
        fdtd.load(str(fsp_path.resolve()))
        fdtd.run()
        fdtd.save(str(fsp_path.resolve()))
        return {"case_id": case["case_id"], "structure": case["structure"], "linear_input": case["linear_input"], "fdtd_status": "ok", "result_fsp": str(fsp_path), "note": "setup/save/load/run/save lifecycle complete"}
    except Exception as exc:
        return {"case_id": case["case_id"], "structure": case["structure"], "linear_input": case["linear_input"], "fdtd_status": "failed", "result_fsp": str(fsp_path), "note": f"{type(exc).__name__}: {exc}"}
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass


def write_debug(out_dir: Path, rows: list[dict[str, Any]], sim_time_fs: float, mesh_accuracy: int) -> None:
    data = {
        "purpose": "+z plane-wave CP handedness and reciprocity control",
        "method": "Run x/y linear plane-wave inputs for empty cell and frozen periodic dimer, then construct CP Jones matrix by superposition.",
        "cp_convention": "R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2)",
        "geometry": {"period_x_nm": PERIOD_X_NM, "period_y_nm": PERIOD_Y_NM, "height_nm": HEIGHT_NM, "metasurface_plane": "x-y", "height_axis": "z", "source_z_nm": SOURCE_Z_NM, "monitor_z_nm": MONITOR_Z_NM},
        "simulation_time_fs": sim_time_fs,
        "mesh_accuracy": mesh_accuracy,
        "run_rows": rows,
    }
    (out_dir / "cp_zprop_planewave_control_debug.json").write_text(json.dumps(data, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    ensure_dirs(out_dir)
    runtime = load_runtime_config(args.runtime)
    lumapi = import_lumapi(runtime)
    rows = [run_case(lumapi, runtime, case, out_dir, args.simulation_time_fs, args.mesh_accuracy, args.show_gui, args.dry_run) for case in CASES]
    write_csv(out_dir / "cp_zprop_planewave_control_run_status.csv", rows)
    write_debug(out_dir, rows, args.simulation_time_fs, args.mesh_accuracy)
    print(json.dumps({"rows": rows}, indent=2))
    return 0 if all(row["fdtd_status"] in {"ok", "not_run"} for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
