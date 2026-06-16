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
OUT_DIR = Path("outputs/blue_stage10_cp_zprop_validation/five_position_sweep")
SIM_TIME_FS = 100.0
FIELD_MONITOR = "top_field_monitor_zprop"
POWER_MONITOR = "top_power_monitor_zprop"
X_SOURCE = "fivepos_x_dipole_zprop"
Y_SOURCE = "fivepos_y_dipole_zprop"

PILLARS = [
    {"label": "A", "length_nm": 180.0, "width_nm": 90.0, "height_nm": 525.0, "rotation_deg": 37.5, "center_x_nm": -31.20933807846728, "center_y_nm": -85.74695164671414},
    {"label": "B", "length_nm": 230.0, "width_nm": 100.0, "height_nm": 525.0, "rotation_deg": -7.5, "center_x_nm": 31.20933807846728, "center_y_nm": 85.74695164671414},
]
ARRAY_NX = 7
ARRAY_NY = 3
PERIOD_X_NM = 431.907786
PERIOD_Y_NM = 432.0
OFFSET_NM = min(PERIOD_X_NM, PERIOD_Y_NM) / 4.0
IX_VALUES = list(range(-3, 4))
IY_VALUES = list(range(-1, 2))
X_CENTERS_NM = [ix * PERIOD_X_NM for ix in IX_VALUES]
Y_CENTERS_NM = [iy * PERIOD_Y_NM for iy in IY_VALUES]

GAN_X_SPAN_NM = 3000.0
GAN_Y_SPAN_NM = 1200.0
GAN_TOP_Z_NM = 0.0
GAN_ACTUAL_BOTTOM_Z_NM = -1100.0
SOURCE_Z_NM = -200.0
FDTD_X_SPAN_NM = 20000.0
FDTD_Y_SPAN_NM = 20000.0
FDTD_Z_MIN_NM = -900.0
FDTD_Z_MAX_NM = 1800.0
MONITOR_Z_NM = 1000.0
MONITOR_X_SPAN_NM = 22000.0
MONITOR_Y_SPAN_NM = 22000.0

POSITIONS = [
    {"position_id": "x_minus_2qp", "x_nm": -2.0 * OFFSET_NM, "y_nm": 0.0},
    {"position_id": "x_minus_qp", "x_nm": -OFFSET_NM, "y_nm": 0.0},
    {"position_id": "center", "x_nm": 0.0, "y_nm": 0.0},
    {"position_id": "x_plus_qp", "x_nm": OFFSET_NM, "y_nm": 0.0},
    {"position_id": "x_plus_2qp", "x_nm": 2.0 * OFFSET_NM, "y_nm": 0.0},
]
ORIENTATIONS = [
    {"orientation": "x", "enabled_source": X_SOURCE, "disabled_source": Y_SOURCE, "theta_deg": 90.0, "phi_deg": 0.0},
    {"orientation": "y", "enabled_source": Y_SOURCE, "disabled_source": X_SOURCE, "theta_deg": 90.0, "phi_deg": 90.0},
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run calibrated +z 5-position x/y dipole finite-patch sweep only; no 41-position sweep.")
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--output-dir", default=str(OUT_DIR))
    parser.add_argument("--simulation-time-fs", type=float, default=SIM_TIME_FS)
    parser.add_argument("--show-gui", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Rerun cases even when saved FSP already exists.")
    parser.add_argument("--case", default="all", help="Run one x-line case by short name such as x_plus_qp_y, or full case_id. Default: all.")
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


def add_uniform_patch(fdtd: object, include_patch: bool = True) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    if not include_patch:
        return inventory
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
        fdtd.set("x", 0); fdtd.set("y", 0); fdtd.set("z", SOURCE_Z_NM * NM)
        fdtd.set("wavelength start", WAVELENGTH_NM * NM); fdtd.set("wavelength stop", WAVELENGTH_NM * NM)
        safe_set(fdtd, "theta", theta, warnings); safe_set(fdtd, "phi", phi, warnings)
        fdtd.set("enabled", 0)


def add_monitors(fdtd: object) -> None:
    for add, name in [(fdtd.addprofile, FIELD_MONITOR), (fdtd.addpower, POWER_MONITOR)]:
        add(); fdtd.set("name", name); fdtd.set("monitor type", "2D Z-normal")
        fdtd.set("x span", MONITOR_X_SPAN_NM * NM); fdtd.set("y span", MONITOR_Y_SPAN_NM * NM); fdtd.set("z", MONITOR_Z_NM * NM)


def build_setup(fdtd: object, sim_time_fs: float, include_patch: bool = True) -> tuple[list[str], list[dict[str, Any]]]:
    warnings: list[str] = []
    fdtd.switchtolayout(); fdtd.deleteall(); fdtd.addfdtd()
    fdtd.set("dimension", "3D")
    fdtd.set("x span", FDTD_X_SPAN_NM * NM); fdtd.set("y span", FDTD_Y_SPAN_NM * NM)
    fdtd.set("z min", FDTD_Z_MIN_NM * NM); fdtd.set("z max", FDTD_Z_MAX_NM * NM)
    for prop in ["x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc"]:
        fdtd.set(prop, "PML")
    fdtd.set("mesh accuracy", 3); fdtd.set("simulation time", sim_time_fs * 1e-15)
    add_gan(fdtd, warnings)
    inventory = add_uniform_patch(fdtd, include_patch=include_patch)
    add_dipoles(fdtd, warnings); add_monitors(fdtd)
    return warnings, inventory


def case_short_name(case: dict[str, Any]) -> str:
    return f"{case['position_id']}_{case['orientation']}"


def normalize_case_selector(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def filter_cases(cases: list[dict[str, Any]], selector: str) -> list[dict[str, Any]]:
    sel = normalize_case_selector(selector)
    if sel in {"", "all", "*"}:
        return cases
    selected = [c for c in cases if normalize_case_selector(case_short_name(c)) == sel or normalize_case_selector(c["case_id"]) == sel]
    if not selected:
        known = ", ".join(case_short_name(c) for c in cases)
        raise ValueError(f"Unknown --case {selector!r}; known x-line cases: {known}")
    return selected


def fsp_complete_enough(fsp_path: Path) -> tuple[bool, str]:
    if not fsp_path.exists():
        return False, "missing_fsp"
    size = fsp_path.stat().st_size
    if size < 10_000_000:
        return False, f"incomplete_setup_size_fsp:{size}"
    return True, f"existing_completed_size_fsp:{size}"


def build_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for pos in POSITIONS:
        for ori in ORIENTATIONS:
            case_id = f"CP_ZPROP_5POS_{pos['position_id'].upper()}_{ori['orientation'].upper()}_T100FS"
            merged = {**pos, **ori, "case_id": case_id, "z_nm": SOURCE_Z_NM}
            merged["short_name"] = case_short_name(merged)
            cases.append(merged)
    return cases


def configure_case(fdtd: object, case: dict[str, Any], sim_time_fs: float) -> None:
    fdtd.select("FDTD"); fdtd.set("simulation time", sim_time_fs * 1e-15)
    for source, enabled in [(case["enabled_source"], 1), (case["disabled_source"], 0)]:
        fdtd.select(source); fdtd.set("enabled", enabled)
        fdtd.set("x", float(case["x_nm"]) * NM)
        fdtd.set("y", float(case["y_nm"]) * NM)
        fdtd.set("z", float(case["z_nm"]) * NM)
    fdtd.select(case["enabled_source"]); fdtd.set("theta", case["theta_deg"]); fdtd.set("phi", case["phi_deg"])


def preflight(fdtd: object, case: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    for name in ["FDTD", X_SOURCE, Y_SOURCE, FIELD_MONITOR, POWER_MONITOR]:
        try:
            fdtd.select(name)
        except Exception as exc:
            errors.append(f"missing object {name}: {type(exc).__name__}: {exc}")
    for prop in ["x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc"]:
        try:
            val = fdtd.getnamed("FDTD", prop)
            if str(val).strip().upper() != "PML":
                errors.append(f"{prop}={val}, expected PML")
        except Exception as exc:
            errors.append(f"could not read {prop}: {type(exc).__name__}: {exc}")
    for source_name, expected in [(case["enabled_source"], 1), (case["disabled_source"], 0)]:
        try:
            enabled = int(float(fdtd.getnamed(source_name, "enabled")))
            if enabled != expected:
                errors.append(f"{source_name} enabled={enabled}, expected {expected}")
        except Exception as exc:
            errors.append(f"could not read enabled for {source_name}: {type(exc).__name__}: {exc}")
    return not errors, errors


def write_plan(out_dir: Path, cases: list[dict[str, Any]], inventory: list[dict[str, Any]], warnings: list[str], setup_fsp: Path) -> None:
    plan_rows = []
    for c in cases:
        plan_rows.append({
            "case_id": c["case_id"], "position_id": c["position_id"], "x_nm": f"{float(c['x_nm']):.6f}", "y_nm": f"{float(c['y_nm']):.6f}", "z_nm": f"{float(c['z_nm']):.6f}",
            "orientation": c["orientation"], "theta_deg": c["theta_deg"], "phi_deg": c["phi_deg"], "position_weight": 0.2, "orientation_weight": 0.5,
            "offset_basis": "quarter of local pitch", "offset_nm": f"{OFFSET_NM:.6f}", "sweep_type": "x-axis centerline only", "short_name": c["short_name"], "run_enabled": "true", "expected_fsp": str(out_dir / "_saved_fsp" / f"{c['case_id']}.fsp"),
            "notes": "x-axis centerline finite patch; y=0 fixed; calibrated +z convention; no full-plane/y-offset/41-position sweep",
        })
    write_csv(out_dir / "five_position_run_plan.csv", plan_rows)
    write_csv(out_dir / "five_position_patch_inventory.csv", inventory)
    debug = {"offset_nm": OFFSET_NM, "offset_basis": "x-axis centerline quarter local pitch = min(period_x,period_y)/4", "simulation_time_fs": SIM_TIME_FS, "setup_fsp": str(setup_fsp), "setup_warnings": warnings, "cases": plan_rows}
    (out_dir / "five_position_sweep_debug.json").write_text(json.dumps(debug, indent=2), encoding="utf-8")


def run_case(lumapi: Any, runtime: Any, setup_fsp: Path, case: dict[str, Any], out_dir: Path, sim_time_fs: float, show_gui: bool, force: bool) -> dict[str, Any]:
    fsp_path = out_dir / "_saved_fsp" / f"{case['case_id']}.fsp"
    if fsp_path.exists() and not force:
        complete, reason = fsp_complete_enough(fsp_path)
        if complete:
            return {"case_id": case["case_id"], "position_id": case["position_id"], "orientation": case["orientation"], "fdtd_status": "reused", "result_fsp": str(fsp_path), "notes": reason + "; saved FSP already exists; not rerun"}
        # Existing setup-size candidates are treated as incomplete and rerun.
        try:
            fsp_path.unlink()
        except Exception:
            pass
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not show_gui) and runtime.hide_gui)
        fdtd.load(str(setup_fsp.resolve()))
        configure_case(fdtd, case, sim_time_fs)
        ok, errors = preflight(fdtd, case)
        if not ok:
            return {"case_id": case["case_id"], "position_id": case["position_id"], "orientation": case["orientation"], "fdtd_status": "preflight_failed", "result_fsp": str(fsp_path), "notes": " | ".join(errors)}
        fdtd.save(str(fsp_path.resolve()))
        fdtd.run()
        fdtd.save(str(fsp_path.resolve()))
        return {"case_id": case["case_id"], "position_id": case["position_id"], "orientation": case["orientation"], "fdtd_status": "ok", "result_fsp": str(fsp_path), "notes": "setup/save/load/run/save lifecycle complete"}
    except Exception as exc:
        return {"case_id": case["case_id"], "position_id": case["position_id"], "orientation": case["orientation"], "fdtd_status": "failed", "result_fsp": str(fsp_path), "notes": f"{type(exc).__name__}: {exc}"}
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    ensure_dirs(out_dir)
    runtime = load_runtime_config(args.runtime)
    lumapi = import_lumapi(runtime)
    all_cases = build_cases()
    cases = filter_cases(all_cases, args.case)
    setup_fsp = out_dir / "five_position_zprop_patch_setup.fsp"
    setup_status = "ok"
    warnings: list[str] = []
    inventory: list[dict[str, Any]] = []
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not args.show_gui) and runtime.hide_gui)
        warnings, inventory = build_setup(fdtd, args.simulation_time_fs, include_patch=True)
        fdtd.save(str(setup_fsp.resolve()))
    except Exception as exc:
        setup_status = f"failed: {type(exc).__name__}: {exc}"
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass
    write_plan(out_dir, all_cases, inventory, warnings, setup_fsp)
    rows: list[dict[str, Any]] = []
    if setup_status == "ok" and not args.dry_run:
        for case in cases:
            rows.append(run_case(lumapi, runtime, setup_fsp, case, out_dir, args.simulation_time_fs, args.show_gui, args.force))
    else:
        for case in cases:
            rows.append({"case_id": case["case_id"], "position_id": case["position_id"], "orientation": case["orientation"], "fdtd_status": "not_run" if args.dry_run else setup_status, "result_fsp": str(out_dir / "_saved_fsp" / f"{case['case_id']}.fsp"), "notes": "dry run setup only" if args.dry_run else setup_status})
    write_csv(out_dir / "five_position_run_status.csv", rows)
    print(json.dumps({"setup_status": setup_status, "run_rows": rows, "setup_fsp": str(setup_fsp)}, indent=2))
    return 0 if setup_status == "ok" and all(r["fdtd_status"] in {"ok", "reused", "not_run"} for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
