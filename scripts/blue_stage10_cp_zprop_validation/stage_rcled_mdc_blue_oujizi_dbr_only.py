from __future__ import annotations

import argparse
import csv
import json
import math
import time
from pathlib import Path
from typing import Any

import numpy as np

from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi

import postprocess_rcled_dbr_only_farfield as ff
import stage10_cp_route_b2_finite_patch_xplus_test as b2


NM = 1e-9
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "stage_rcled_mdc_blue_oujizi_dbr_only"
LOG_DIR = OUT / "logs"
SAVED = OUT / "_saved_fsp"
SOURCE_DBR = Path(r"N:\zlt\DBR\MDC_blue_oujizi.fsp")
BASE_FSP = ROOT / "outputs" / "stage10_cp_dbr_1_gan_dbr_only" / "_setup_fsp" / "gan_dbr_only_grouped_setup.fsp"
FINAL_SETUP = OUT / "rcled_mdc_blue_oujizi_dbr_only_no_metasurface.fsp"
OLD_DBR_GROUP = "DBR1_MDC_blue_stack_group"
NEW_DBR_GROUP = "MDC_blue_oujizi_DBR_group"
FIELD_MONITOR = "top_field_monitor_zprop"
POWER_MONITOR = "top_power_monitor_zprop"
X_SOURCE = "gan_dbr_only_center_x_dipole"
Y_SOURCE = "gan_dbr_only_center_y_dipole"
SIM_TIME_FS = 100.0


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def inspect_source(lumapi: Any, runtime: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if not SOURCE_DBR.exists():
        raise FileNotFoundError(SOURCE_DBR)
    fdtd = lumapi.FDTD(hide=runtime.hide_gui)
    try:
        fdtd.load(str(SOURCE_DBR))
        if int(float(fdtd.getnamednumber("dbr"))) != 1:
            raise RuntimeError("source DBR structure group is not uniquely identifiable")
        script = str(fdtd.getnamed("dbr", "script"))
        d_sio2 = float(fdtd.getnamed("dbr", "d11")) / NM
        d_tio2 = float(fdtd.getnamed("dbr", "d22")) / NM
        pairs = int(float(fdtd.getnamed("dbr", "m")))
        evidence = ("set('material','tio22')", "set('material','sio222')", "for (i = 0:m-1)", "for (i = 0:m)")
        if not all(token in script for token in evidence):
            raise RuntimeError("source DBR ordering/material script is ambiguous")
        materials: dict[str, Any] = {}
        for name in ("tio22", "sio222"):
            materials[name] = {
                "sampled_3d_data": fdtd.getmaterial(name, "sampled 3d data"),
                "mesh_order": float(fdtd.getmaterial(name, "Mesh order")),
                "color": fdtd.getmaterial(name, "color"),
                "type": "Sampled 3D data",
            }
    finally:
        fdtd.close()
    audit = {
        "source_fsp": str(SOURCE_DBR),
        "source_fsp_bytes": SOURCE_DBR.stat().st_size,
        "dbr_object": "dbr",
        "dbr_object_type": "Structure Group",
        "SiO2_material": "sio222",
        "TiO2_material": "tio22",
        "SiO2_thickness_nm": d_sio2,
        "TiO2_thickness_nm": d_tio2,
        "pair_count": pairs,
        "SiO2_layer_count": pairs + 1,
        "TiO2_layer_count": pairs,
        "total_layer_count": 2 * pairs + 1,
        "total_thickness_nm": (pairs + 1) * d_sio2 + pairs * d_tio2,
        "source_group_x_span_nm": 6000.0,
        "source_group_transverse_span_nm": 5000.0,
        "source_axis": "y",
        "mapped_project_axis": "z",
        "bottom_to_top": "[sio222 100 nm -> tio22 52 nm] x 8 -> terminal sio222 100 nm",
    }
    return audit, materials


def layer_rows(audit: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    z = 0.0
    index = 0
    for pair in range(int(audit["pair_count"])):
        for role, material, thickness in (
            ("SiO2", "sio222", float(audit["SiO2_thickness_nm"])),
            ("TiO2", "tio22", float(audit["TiO2_thickness_nm"])),
        ):
            rows.append({
                "order_index": index,
                "object_name": f"OUJIZI_DBR_{pair:02d}_{role}",
                "material": material,
                "refractive_index_material_name": material,
                "z_min_nm": z,
                "z_max_nm": z + thickness,
                "thickness_nm": thickness,
                "source_x_span_nm": audit["source_group_x_span_nm"],
                "source_y_span_nm": audit["source_group_transverse_span_nm"],
                "model_x_span_nm": b2.GAN_X_SPAN_NM,
                "model_y_span_nm": b2.GAN_Y_SPAN_NM,
            })
            z += thickness
            index += 1
    rows.append({
        "order_index": index,
        "object_name": f"OUJIZI_DBR_{int(audit['pair_count']):02d}_SiO2_terminal",
        "material": "sio222",
        "refractive_index_material_name": "sio222",
        "z_min_nm": z,
        "z_max_nm": z + float(audit["SiO2_thickness_nm"]),
        "thickness_nm": float(audit["SiO2_thickness_nm"]),
        "source_x_span_nm": audit["source_group_x_span_nm"],
        "source_y_span_nm": audit["source_group_transverse_span_nm"],
        "model_x_span_nm": b2.GAN_X_SPAN_NM,
        "model_y_span_nm": b2.GAN_Y_SPAN_NM,
    })
    return rows


def ensure_sampled_material(fdtd: Any, name: str, info: dict[str, Any]) -> None:
    try:
        available = {line.strip() for line in str(fdtd.getmaterial()).splitlines() if line.strip()}
        if name in available:
            return
    except Exception:
        available = set()
    if name in available:
        return
    material_id = fdtd.addmaterial("Sampled 3D data")
    fdtd.setmaterial(material_id, "name", name)
    fdtd.setmaterial(name, "sampled 3d data", info["sampled_3d_data"])
    fdtd.setmaterial(name, "Mesh order", info["mesh_order"])
    fdtd.setmaterial(name, "color", info["color"])


def build_setup(lumapi: Any, runtime: Any, layers: list[dict[str, Any]], materials: dict[str, Any]) -> dict[str, Any]:
    if not BASE_FSP.exists():
        raise FileNotFoundError(BASE_FSP)
    fdtd = lumapi.FDTD(hide=runtime.hide_gui)
    try:
        fdtd.load(str(BASE_FSP.resolve()))
        fdtd.switchtolayout()
        if int(float(fdtd.getnamednumber(OLD_DBR_GROUP))):
            fdtd.select(OLD_DBR_GROUP)
            fdtd.delete()
        ensure_sampled_material(fdtd, "tio22", materials["tio22"])
        ensure_sampled_material(fdtd, "sio222", materials["sio222"])
        fdtd.addstructuregroup()
        fdtd.set("name", NEW_DBR_GROUP)
        fdtd.groupscope(f"::model::{NEW_DBR_GROUP}")
        for row in layers:
            fdtd.addrect()
            fdtd.set("name", row["object_name"])
            fdtd.set("x", 0)
            fdtd.set("y", 0)
            fdtd.set("x span", b2.GAN_X_SPAN_NM * NM)
            fdtd.set("y span", b2.GAN_Y_SPAN_NM * NM)
            fdtd.set("z min", float(row["z_min_nm"]) * NM)
            fdtd.set("z max", float(row["z_max_nm"]) * NM)
            fdtd.set("material", row["material"])
        fdtd.groupscope("::model")
        fdtd.save(str(FINAL_SETUP.resolve()))
        sanity = inspect_setup(fdtd, layers)
        return sanity
    finally:
        fdtd.close()


def inspect_setup(fdtd: Any, layers: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    required = ("FDTD", "GaN_continuous_block_zprop_extends_into_bottom_PML", X_SOURCE, Y_SOURCE, FIELD_MONITOR, POWER_MONITOR, NEW_DBR_GROUP)
    for name in required:
        if not int(float(fdtd.getnamednumber(name))):
            errors.append(f"missing {name}")
    if int(float(fdtd.getnamednumber(OLD_DBR_GROUP))):
        errors.append("old temporary DBR group remains")
    forbidden = (
        "CP_DBR1_B4INT_D194_T90_PSI97_uniform_patch_7x3",
        "CP_route_b4_D194_T90_PSI97_uniform_patch_7x3_group",
    )
    for name in forbidden:
        if int(float(fdtd.getnamednumber(name))):
            errors.append(f"forbidden metasurface object remains: {name}")
    for row in layers:
        path = f"::model::{NEW_DBR_GROUP}::{row['object_name']}"
        if not int(float(fdtd.getnamednumber(path))):
            errors.append(f"missing layer {path}")
    for prop in ("x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc"):
        if str(fdtd.getnamed("FDTD", prop)).upper() != "PML":
            errors.append(f"{prop} not PML")
    tio22_color = fdtd.getmaterial("tio22", "color")
    sio222_color = fdtd.getmaterial("sio222", "color")
    return {
        "errors": errors,
        "metasurface_absent": not any("metasurface" in e for e in errors),
        "old_dbr_absent": "old temporary DBR group remains" not in errors,
        "new_dbr_layer_count": len(layers),
        "source_x_nm": float(fdtd.getnamed(X_SOURCE, "x")) / NM,
        "source_y_nm": float(fdtd.getnamed(X_SOURCE, "y")) / NM,
        "source_z_nm": float(fdtd.getnamed(X_SOURCE, "z")) / NM,
        "x_theta_deg": float(fdtd.getnamed(X_SOURCE, "theta")),
        "x_phi_deg": float(fdtd.getnamed(X_SOURCE, "phi")),
        "y_theta_deg": float(fdtd.getnamed(Y_SOURCE, "theta")),
        "y_phi_deg": float(fdtd.getnamed(Y_SOURCE, "phi")),
        "monitor_name": FIELD_MONITOR,
        "monitor_type": str(fdtd.getnamed(FIELD_MONITOR, "monitor type")),
        "monitor_z_nm": float(fdtd.getnamed(FIELD_MONITOR, "z")) / NM,
        "prop_axis": 3,
        "mesh_accuracy": float(fdtd.getnamed("FDTD", "mesh accuracy")),
        "tio22_color": tio22_color.tolist() if hasattr(tio22_color, "tolist") else tio22_color,
        "sio222_color": sio222_color.tolist() if hasattr(sio222_color, "tolist") else sio222_color,
    }


def cases() -> list[dict[str, Any]]:
    return [
        {
            "case_id": f"RCLED_MDC_BLUE_OUJIZI_CENTER_{orientation.upper()}_T100FS",
            "orientation": orientation,
            "enabled": X_SOURCE if orientation == "x" else Y_SOURCE,
            "disabled": Y_SOURCE if orientation == "x" else X_SOURCE,
            "result_fsp": str(SAVED / f"RCLED_MDC_BLUE_OUJIZI_CENTER_{orientation.upper()}_T100FS.fsp"),
        }
        for orientation in ("x", "y")
    ]


def configure(fdtd: Any, case: dict[str, Any]) -> None:
    fdtd.select("FDTD")
    fdtd.set("simulation time", SIM_TIME_FS * 1e-15)
    for name, enabled in ((case["enabled"], 1), (case["disabled"], 0)):
        fdtd.select(name)
        fdtd.set("enabled", enabled)
        fdtd.set("x", 0)
        fdtd.set("y", 0)
        fdtd.set("z", b2.SOURCE_Z_NM * NM)


def run_case(lumapi: Any, runtime: Any, case: dict[str, Any], force: bool) -> dict[str, Any]:
    result = Path(case["result_fsp"])
    if result.exists() and result.stat().st_size > 10_000_000 and not force:
        return {**case, "status": "reused", "runtime_seconds": 0.0, "result_size_bytes": result.stat().st_size}
    fdtd = lumapi.FDTD(hide=runtime.hide_gui)
    started = time.perf_counter()
    try:
        fdtd.load(str(FINAL_SETUP.resolve()))
        configure(fdtd, case)
        fdtd.save(str(result.resolve()))
        fdtd.run()
        fdtd.save(str(result.resolve()))
        return {**case, "status": "ok", "runtime_seconds": time.perf_counter() - started, "result_size_bytes": result.stat().st_size}
    except Exception as exc:
        return {**case, "status": "failed", "runtime_seconds": time.perf_counter() - started, "error": f"{type(exc).__name__}: {exc}"}
    finally:
        fdtd.close()


def read_previous() -> list[dict[str, Any]]:
    path = ROOT / "outputs" / "stage_rcled_dbr_only_farfield_postprocess" / "farfield_incoherent_metrics.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def setup_report(audit: dict[str, Any], layers: list[dict[str, Any]], sanity: dict[str, Any]) -> None:
    lines = [
        "# MDC_blue_oujizi DBR-only RCLED setup sanity\n\n",
        f"- Project base FSP: `{BASE_FSP}`\n",
        f"- Read-only DBR reference: `{SOURCE_DBR}`\n",
        f"- Final setup model: `{FINAL_SETUP}`\n",
        f"- DBR order: {audit['bottom_to_top']}\n",
        f"- DBR layers: {len(layers)}; total thickness: {audit['total_thickness_nm']} nm.\n",
        f"- Metasurface/APCD/B4INT objects absent: {sanity['metasurface_absent']}\n",
        f"- Old temporary DBR group absent: {sanity['old_dbr_absent']}\n",
        f"- Sources: center=(0,0,{sanity['source_z_nm']} nm); x orientation theta/phi={sanity['x_theta_deg']}/{sanity['x_phi_deg']} deg; y orientation theta/phi={sanity['y_theta_deg']}/{sanity['y_phi_deg']} deg.\n",
        f"- Monitor: `{sanity['monitor_name']}`, type `{sanity['monitor_type']}`, z={sanity['monitor_z_nm']} nm, propagation axis +z (`prop_axis=3`).\n",
        f"- Mesh accuracy preserved: {sanity['mesh_accuracy']}; project GaN, boundaries, wavelength, monitor and source settings are retained.\n",
        f"- GUI colors: tio22 red `{sanity['tio22_color']}`; sio222 yellow `{sanity['sio222_color']}`.\n",
        "\n## Layer table\n\n",
        "| # | object | material | z min (nm) | z max (nm) | thickness (nm) |\n|---:|---|---|---:|---:|---:|\n",
    ]
    for row in layers:
        lines.append(f"| {row['order_index']} | {row['object_name']} | {row['material']} | {row['z_min_nm']} | {row['z_max_nm']} | {row['thickness_nm']} |\n")
    (OUT / "setup_sanity.md").write_text("".join(lines), encoding="utf-8")


def final_summary(new: dict[str, Any], previous: list[dict[str, Any]], comparison: list[dict[str, Any]], run_rows: list[dict[str, Any]]) -> None:
    no_dbr = next(row for row in previous if row["case_id"] == "no_dbr_xy_incoherent")
    old_dbr = next(row for row in previous if row["case_id"] == "dbr_only_xy_incoherent")
    lines = [
        "# Stage RCLED MDC_blue_oujizi DBR-only far-field\n\n",
        "- Exactly two new FDTD cases were run: center_x and center_y. No APCD/B4INT/metasurface objects or source-position sweeps were included.\n",
        f"- Source DBR: `{SOURCE_DBR}`; base model: `{BASE_FSP}`; final setup: `{FINAL_SETUP}`.\n",
        "- Far-field data use `farfield3d` from `top_field_monitor_zprop`; x/y dipole intensities are added incoherently. Values are API-normalized proxies, not absolute LEE.\n\n",
        "## New x/y incoherent metrics\n\n",
        f"- eta_5deg={float(new['eta_5deg']):.6g}, eta_10deg={float(new['eta_10deg']):.6g}, eta_20deg={float(new['eta_20deg']):.6g}, eta_30deg={float(new['eta_30deg']):.6g}.\n",
        f"- x-cut peak/FWHM={float(new['x_cut_peak_deg']):.6g}/{float(new['x_cut_fwhm_deg']):.6g} deg.\n",
        f"- y-cut peak/FWHM={float(new['y_cut_peak_deg']):.6g}/{float(new['y_cut_fwhm_deg']):.6g} deg.\n\n",
        "## Comparison\n\n",
        "| stack | eta5 | eta10 | eta20 | eta30 | x FWHM | y FWHM | P total proxy |\n|---|---:|---:|---:|---:|---:|---:|---:|\n",
    ]
    for label, row in (("no DBR", no_dbr), ("previous temporary DBR", old_dbr), ("MDC_blue_oujizi DBR", new)):
        lines.append(f"| {label} | {float(row['eta_5deg']):.6g} | {float(row['eta_10deg']):.6g} | {float(row['eta_20deg']):.6g} | {float(row['eta_30deg']):.6g} | {float(row['x_cut_fwhm_deg']):.6g} | {float(row['y_cut_fwhm_deg']):.6g} | {float(row['P_total_solid_angle_proxy']):.6g} |\n")
    better_x = float(new["x_cut_fwhm_deg"]) < float(old_dbr["x_cut_fwhm_deg"])
    better_y = float(new["y_cut_fwhm_deg"]) < float(old_dbr["y_cut_fwhm_deg"])
    lines += [
        "\n## Main answer\n\n",
        f"Compared with the previous temporary DBR-only result, the MDC_blue_oujizi DBR has a smaller x-cut FWHM: {better_x}; smaller y-cut FWHM: {better_y}. The conclusion must consider both axes and power, not one cut alone.\n",
        "\n## 中文\n\n",
        "本轮只运行 center_x/y 两个无超表面 RCLED case，并以功率非相干相加。是否优于旧临时 DBR，需要同时比较 x/y FWHM、窄角 cone 占比和总功率代理，不能只依据单一切线。\n",
    ]
    (OUT / "stage_rcled_mdc_blue_oujizi_summary.md").write_text("".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    for path in (OUT, LOG_DIR, SAVED):
        path.mkdir(parents=True, exist_ok=True)
    runtime = load_runtime_config("configs/runtime.yaml")
    lumapi = import_lumapi(runtime)
    audit, materials = inspect_source(lumapi, runtime)
    layers = layer_rows(audit)
    write_csv(OUT / "mdc_blue_oujizi_dbr_layers.csv", layers)
    sanity = build_setup(lumapi, runtime, layers, materials)
    setup_report(audit, layers, sanity)
    manifest = {"source_dbr": str(SOURCE_DBR), "base_fsp": str(BASE_FSP), "final_setup": str(FINAL_SETUP), "audit": audit, "sanity": sanity, "cases": cases(), "no_metasurface": True, "new_case_count": 2}
    (OUT / "run_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    if sanity["errors"]:
        raise RuntimeError("setup sanity failed: " + " | ".join(sanity["errors"]))
    if args.dry_run:
        print(json.dumps({"dry_run": True, **manifest}, indent=2, ensure_ascii=False))
        return 0

    run_rows = [run_case(lumapi, runtime, case, args.force) for case in cases()]
    write_csv(OUT / "run_results.csv", run_rows)
    if any(row["status"] not in {"ok", "reused"} for row in run_rows):
        print(json.dumps(run_rows, indent=2))
        return 1

    ff.OUT = OUT
    farfields: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    case_metrics: list[dict[str, Any]] = []
    pngs: list[str] = []
    for case in cases():
        ux, uy, e2, info = ff.get_farfield(lumapi, runtime, Path(case["result_fsp"]))
        row, cuts = ff.metrics(case["case_id"], ux, uy, e2)
        row.update({"orientation": case["orientation"], "fsp_path": case["result_fsp"], **info})
        case_metrics.append(row)
        farfields[case["orientation"]] = (ux, uy, e2)
        pngs += ff.save_plots(f"mdc_blue_oujizi_{case['orientation']}", ux, uy, e2, cuts)
    ux, uy, ex = farfields["x"]
    ux2, uy2, ey = farfields["y"]
    if not (np.allclose(ux, ux2) and np.allclose(uy, uy2)):
        raise RuntimeError("x/y far-field grids differ")
    combined, cuts = ff.metrics("mdc_blue_oujizi_xy_incoherent", ux, uy, ex + ey)
    combined["P_total_x"] = next(row["P_total_solid_angle_proxy"] for row in case_metrics if row["orientation"] == "x")
    combined["P_total_y"] = next(row["P_total_solid_angle_proxy"] for row in case_metrics if row["orientation"] == "y")
    combined["P_total_xy_incoherent"] = combined["P_total_solid_angle_proxy"]
    pngs += ff.save_plots("mdc_blue_oujizi_xy_incoherent", ux, uy, ex + ey, cuts)
    write_csv(OUT / "farfield_case_metrics.csv", case_metrics)
    write_csv(OUT / "farfield_xy_incoherent_metrics.csv", [combined])
    previous = read_previous()
    comparison = []
    for label, row in (("no_dbr", next(r for r in previous if r["case_id"] == "no_dbr_xy_incoherent")), ("temporary_dbr", next(r for r in previous if r["case_id"] == "dbr_only_xy_incoherent")), ("mdc_blue_oujizi_dbr", combined)):
        comparison.append({"stack": label, **{key: row[key] for key in ("P_total_solid_angle_proxy", "eta_5deg", "eta_10deg", "eta_20deg", "eta_30deg", "x_cut_peak_deg", "x_cut_fwhm_deg", "y_cut_peak_deg", "y_cut_fwhm_deg")}})
    write_csv(OUT / "farfield_comparison.csv", comparison)
    (OUT / "postprocess_debug.json").write_text(json.dumps({"pngs": pngs, "run_rows": run_rows, "audit": audit, "sanity": sanity}, indent=2, ensure_ascii=False), encoding="utf-8")
    final_summary(combined, previous, comparison, run_rows)
    print(json.dumps({"run_rows": run_rows, "case_metrics": case_metrics, "combined": combined, "comparison": comparison, "pngs": pngs}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
