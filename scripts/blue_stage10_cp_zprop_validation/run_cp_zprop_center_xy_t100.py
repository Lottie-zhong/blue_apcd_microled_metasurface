from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi

NM = 1e-9
WAVELENGTH_NM = 450.0
MATERIAL_INDEX = 2.6
GAN_INDEX = 2.56
OUT_DIR = Path("outputs/blue_stage10_cp_zprop_validation")
SETUP_FSP_NAME = "cp_zprop_finite_patch_center_xy_t100_setup.fsp"
SIM_TIME_FS = 100.0

PILLARS = [
    {"label": "A", "length_nm": 180.0, "width_nm": 90.0, "height_nm": 525.0, "rotation_deg": 37.5, "center_x_nm": -31.20933807846728, "center_y_nm": -85.74695164671414},
    {"label": "B", "length_nm": 230.0, "width_nm": 100.0, "height_nm": 525.0, "rotation_deg": -7.5, "center_x_nm": 31.20933807846728, "center_y_nm": 85.74695164671414},
]
ARRAY_NX = 7
ARRAY_NY = 3
PERIOD_X_NM = 431.907786
PERIOD_Y_NM = 432.0
IX_VALUES = list(range(-3, 4))
IY_VALUES = list(range(-1, 2))
X_CENTERS_NM = [ix * PERIOD_X_NM for ix in IX_VALUES]
Y_CENTERS_NM = [iy * PERIOD_Y_NM for iy in IY_VALUES]

GAN_X_SPAN_NM = 3000.0
GAN_Y_SPAN_NM = 1200.0
GAN_TOP_Z_NM = 0.0
GAN_ACTUAL_BOTTOM_Z_NM = -1100.0
SOURCE_X_NM = 0.0
SOURCE_Y_NM = 0.0
SOURCE_Z_NM = -200.0
FDTD_X_SPAN_NM = 20000.0
FDTD_Y_SPAN_NM = 20000.0
FDTD_Z_MIN_NM = -900.0
FDTD_Z_MAX_NM = 1800.0
MONITOR_Z_NM = 1000.0
MONITOR_X_SPAN_NM = 22000.0
MONITOR_Y_SPAN_NM = 22000.0
FIELD_MONITOR = "top_field_monitor_zprop"
POWER_MONITOR = "top_power_monitor_zprop"
X_SOURCE = "center_x_dipole_zprop"
Y_SOURCE = "center_y_dipole_zprop"
CASES = [
    {"case_id": "CP_ZPROP_CENTER_X_T100FS", "orientation": "x", "enabled_source": X_SOURCE, "disabled_source": Y_SOURCE, "theta_deg": 90.0, "phi_deg": 0.0},
    {"case_id": "CP_ZPROP_CENTER_Y_T100FS", "orientation": "y", "enabled_source": Y_SOURCE, "disabled_source": X_SOURCE, "theta_deg": 90.0, "phi_deg": 90.0},
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and run +z propagation center x/y dipole T100 finite CP patch validation.")
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--output-dir", default=str(OUT_DIR))
    parser.add_argument("--simulation-time-fs", type=float, default=SIM_TIME_FS)
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


def safe_set(fdtd: object, prop: str, value: Any, warnings: list[str]) -> None:
    try:
        fdtd.set(prop, value)
    except Exception as exc:
        warnings.append(f"set skipped {prop}={value!r}: {type(exc).__name__}: {exc}")


def try_create_gan_material(fdtd: object, warnings: list[str]) -> str:
    name = "GaN_450nm_n2p56_custom"
    try:
        fdtd.addrect(); fdtd.set("name", "tmp_gan_material_probe"); fdtd.set("material", name); fdtd.delete()
        return name
    except Exception:
        try:
            fdtd.delete()
        except Exception:
            pass
    try:
        fdtd.eval('mat = addmaterial("(n,k) Material"); setmaterial(mat, "name", "GaN_450nm_n2p56_custom"); setmaterial("GaN_450nm_n2p56_custom", "Refractive Index", 2.56); setmaterial("GaN_450nm_n2p56_custom", "Imaginary Refractive Index", 0); setmaterial("GaN_450nm_n2p56_custom", "Mesh order", 3); setmaterial("GaN_450nm_n2p56_custom", "color", [1,0.35,0.75,1]);')
        return name
    except Exception as exc:
        warnings.append(f"Could not create/assign {name}; fallback to object-defined n=2.56: {type(exc).__name__}: {exc}")
        return ""


def add_gan(fdtd: object, warnings: list[str]) -> None:
    mat = try_create_gan_material(fdtd, warnings)
    fdtd.addrect()
    fdtd.set("name", "GaN_continuous_block_zprop_extends_into_bottom_PML")
    fdtd.set("x", 0); fdtd.set("y", 0)
    fdtd.set("x span", GAN_X_SPAN_NM * NM)
    fdtd.set("y span", GAN_Y_SPAN_NM * NM)
    fdtd.set("z min", GAN_ACTUAL_BOTTOM_Z_NM * NM)
    fdtd.set("z max", GAN_TOP_Z_NM * NM)
    if mat:
        fdtd.set("material", mat)
    else:
        fdtd.set("material", "<Object defined dielectric>"); fdtd.set("index", GAN_INDEX)


def add_uniform_patch(fdtd: object) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    parent = "CP_zprop_uniform_patch_7x3_group"
    fdtd.addstructuregroup(); fdtd.set("name", parent)
    fdtd.groupscope(f"::model::{parent}")
    for ix, x0 in zip(IX_VALUES, X_CENTERS_NM):
        for iy, y0 in zip(IY_VALUES, Y_CENTERS_NM):
            group = f"CP_zprop_dimer_ix{ix}_iy{iy}_group"
            fdtd.addstructuregroup(); fdtd.set("name", group)
            fdtd.groupscope(f"::model::{parent}::{group}")
            for pillar in PILLARS:
                x_nm = x0 + float(pillar["center_x_nm"])
                y_nm = y0 + float(pillar["center_y_nm"])
                fdtd.addrect(); fdtd.set("name", f"pillar_{pillar['label']}")
                fdtd.set("x", x_nm * NM); fdtd.set("y", y_nm * NM)
                fdtd.set("x span", float(pillar["length_nm"]) * NM)
                fdtd.set("y span", float(pillar["width_nm"]) * NM)
                fdtd.set("z min", 0); fdtd.set("z max", float(pillar["height_nm"]) * NM)
                if float(pillar["rotation_deg"]):
                    fdtd.set("first axis", "z"); fdtd.set("rotation 1", float(pillar["rotation_deg"]))
                fdtd.set("material", "<Object defined dielectric>"); fdtd.set("index", MATERIAL_INDEX)
                inventory.append({"object_name": f"{parent}/{group}/pillar_{pillar['label']}", "dimer_ix": ix, "dimer_iy": iy, "pillar_role": pillar["label"], "x_center_nm": f"{x_nm:.6f}", "y_center_nm": f"{y_nm:.6f}", "z_min_nm": "0.0", "z_max_nm": f"{float(pillar['height_nm']):.1f}", "rotation_axis": "z", "rotation_deg": f"{float(pillar['rotation_deg']):.6g}"})
            fdtd.groupscope(f"::model::{parent}")
    fdtd.groupscope("::model")
    return inventory


def add_dipoles(fdtd: object, warnings: list[str]) -> None:
    for name, theta, phi in [(X_SOURCE, 90.0, 0.0), (Y_SOURCE, 90.0, 90.0)]:
        fdtd.adddipole(); fdtd.set("name", name)
        fdtd.set("x", SOURCE_X_NM * NM); fdtd.set("y", SOURCE_Y_NM * NM); fdtd.set("z", SOURCE_Z_NM * NM)
        fdtd.set("wavelength start", WAVELENGTH_NM * NM); fdtd.set("wavelength stop", WAVELENGTH_NM * NM)
        safe_set(fdtd, "theta", theta, warnings); safe_set(fdtd, "phi", phi, warnings)
        fdtd.set("enabled", 0)


def add_monitors(fdtd: object) -> None:
    for add, name in [(fdtd.addprofile, FIELD_MONITOR), (fdtd.addpower, POWER_MONITOR)]:
        add(); fdtd.set("name", name); fdtd.set("monitor type", "2D Z-normal")
        fdtd.set("x span", MONITOR_X_SPAN_NM * NM); fdtd.set("y span", MONITOR_Y_SPAN_NM * NM); fdtd.set("z", MONITOR_Z_NM * NM)


def build_setup(fdtd: object, sim_time_fs: float) -> tuple[list[str], list[dict[str, Any]]]:
    warnings: list[str] = []
    fdtd.switchtolayout(); fdtd.deleteall(); fdtd.addfdtd()
    fdtd.set("dimension", "3D")
    fdtd.set("x span", FDTD_X_SPAN_NM * NM); fdtd.set("y span", FDTD_Y_SPAN_NM * NM)
    fdtd.set("z min", FDTD_Z_MIN_NM * NM); fdtd.set("z max", FDTD_Z_MAX_NM * NM)
    for prop in ["x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc"]:
        fdtd.set(prop, "PML")
    fdtd.set("mesh accuracy", 3); fdtd.set("simulation time", sim_time_fs * 1e-15)
    add_gan(fdtd, warnings)
    inventory = add_uniform_patch(fdtd)
    add_dipoles(fdtd, warnings); add_monitors(fdtd)
    return warnings, inventory


def configure_case(fdtd: object, case: dict[str, Any], sim_time_fs: float) -> None:
    fdtd.select("FDTD"); fdtd.set("simulation time", sim_time_fs * 1e-15)
    for source, enabled in [(case["enabled_source"], 1), (case["disabled_source"], 0)]:
        fdtd.select(source); fdtd.set("enabled", enabled)
        fdtd.set("x", SOURCE_X_NM * NM); fdtd.set("y", SOURCE_Y_NM * NM); fdtd.set("z", SOURCE_Z_NM * NM)
    fdtd.select(case["enabled_source"]); fdtd.set("theta", case["theta_deg"]); fdtd.set("phi", case["phi_deg"])


def preflight(fdtd: object) -> tuple[bool, list[str]]:
    errors: list[str] = []
    for name in ["FDTD", X_SOURCE, Y_SOURCE, FIELD_MONITOR, POWER_MONITOR]:
        try: fdtd.select(name)
        except Exception as exc: errors.append(f"missing object {name}: {type(exc).__name__}: {exc}")
    for prop in ["x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc"]:
        try:
            val = fdtd.getnamed("FDTD", prop)
            if str(val).strip().upper() != "PML": errors.append(f"{prop}={val}, expected PML")
        except Exception as exc: errors.append(f"could not read {prop}: {type(exc).__name__}: {exc}")
    return not errors, errors


def write_plan(out_dir: Path, inventory: list[dict[str, Any]], warnings: list[str]) -> None:
    write_csv(out_dir / "cp_zprop_center_cases.csv", [{"case_id": c["case_id"], "orientation": c["orientation"], "x_nm": SOURCE_X_NM, "y_nm": SOURCE_Y_NM, "z_nm": SOURCE_Z_NM, "theta_deg": c["theta_deg"], "phi_deg": c["phi_deg"], "simulation_time_fs": SIM_TIME_FS, "run_enabled": "true", "notes": "+z center x/y only; no sweep/DBR/K6/steering"} for c in CASES])
    write_csv(out_dir / "cp_zprop_patch_inventory.csv", inventory)
    debug_path = out_dir / "cp_zprop_center_debug.json"
    existing = {}
    if debug_path.exists():
        try: existing = json.loads(debug_path.read_text(encoding="utf-8"))
        except Exception: existing = {}
    existing.update({"adapted_from": ["scripts/stage10_cp_microled_center_dipole_time_convergence.py", "scripts/stage10_cp_microled_uniform_patch_setup_only.py", "scripts/stage10_cp_microled_simplified_gan_clean_setup_only.py"], "coordinate_change": "old +y x-z plane -> new +z x-y plane; old local/array z remapped to y; pillar height y -> z; rotation axis y -> z", "setup_warnings": warnings, "setup_fsp": str(out_dir / SETUP_FSP_NAME), "field_monitor": FIELD_MONITOR, "power_monitor": POWER_MONITOR})
    debug_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def run_case(lumapi: Any, runtime: Any, setup_fsp: Path, case: dict[str, Any], out_dir: Path, sim_time_fs: float, show_gui: bool) -> dict[str, Any]:
    fsp_path = out_dir / "_saved_fsp" / f"{case['case_id']}.fsp"
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not show_gui) and runtime.hide_gui)
        fdtd.load(str(setup_fsp.resolve()))
        ok, errors = preflight(fdtd)
        if not ok:
            return {"case_id": case["case_id"], "orientation": case["orientation"], "fdtd_status": "preflight_failed", "result_fsp": str(fsp_path), "notes": " | ".join(errors)}
        configure_case(fdtd, case, sim_time_fs)
        fdtd.save(str(fsp_path.resolve())); fdtd.run(); fdtd.save(str(fsp_path.resolve()))
        return {"case_id": case["case_id"], "orientation": case["orientation"], "fdtd_status": "ok", "result_fsp": str(fsp_path), "notes": "setup/save/load/run/save lifecycle complete"}
    except Exception as exc:
        return {"case_id": case["case_id"], "orientation": case["orientation"], "fdtd_status": "failed", "result_fsp": str(fsp_path), "notes": f"{type(exc).__name__}: {exc}"}
    finally:
        if fdtd is not None:
            try: fdtd.close()
            except Exception: pass


def main() -> int:
    args = parse_args(); out_dir = Path(args.output_dir); ensure_dirs(out_dir)
    runtime = load_runtime_config(args.runtime); lumapi = import_lumapi(runtime)
    setup_status = "ok"; warnings: list[str] = []; inventory: list[dict[str, Any]] = []
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not args.show_gui) and runtime.hide_gui)
        warnings, inventory = build_setup(fdtd, args.simulation_time_fs)
        fdtd.save(str((out_dir / SETUP_FSP_NAME).resolve()))
    except Exception as exc:
        setup_status = f"failed: {type(exc).__name__}: {exc}"
    finally:
        if fdtd is not None:
            try: fdtd.close()
            except Exception: pass
    write_plan(out_dir, inventory, warnings)
    rows: list[dict[str, Any]] = []
    if setup_status == "ok" and not args.dry_run:
        for case in CASES:
            rows.append(run_case(lumapi, runtime, out_dir / SETUP_FSP_NAME, case, out_dir, args.simulation_time_fs, args.show_gui))
    else:
        for case in CASES:
            rows.append({"case_id": case["case_id"], "orientation": case["orientation"], "fdtd_status": "not_run" if args.dry_run else setup_status, "result_fsp": str(out_dir / "_saved_fsp" / f"{case['case_id']}.fsp"), "notes": "dry run setup only" if args.dry_run else setup_status})
    write_csv(out_dir / "cp_zprop_center_run_status.csv", rows)
    print(json.dumps({"setup_status": setup_status, "rows": rows, "setup_fsp": str(out_dir / SETUP_FSP_NAME)}, indent=2))
    return 0 if setup_status == "ok" and all(r["fdtd_status"] in {"ok", "not_run"} for r in rows) else 1

if __name__ == "__main__":
    raise SystemExit(main())

