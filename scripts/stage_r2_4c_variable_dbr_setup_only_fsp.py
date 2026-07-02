#!/usr/bin/env python3
"""Generate R2-4C setup-only 2D FDTD files for R2-4B top candidates.

Allowed Lumerical actions: build layout and save .fsp. Forbidden: run,
runanalysis, far-field extraction, .ldf/raw monitor creation.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "r2_4c_variable_dbr_setup_only_fsp"
RUNTIME_FSP = OUT / "runtime_fsp"
R2B = ROOT / "outputs" / "r2_4b_normal_rcled_variable_dbr_tmm_optimize"
INDEX = ROOT / "reports" / "rcled_mdc_workspace_index.md"
LUMAPI_DIR = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")

STAGE = "R2_4C_variable_DBR_setup_only_FSP"
WAVELENGTH_NM = 453.0
TOP_IDS = ["R2_4B_OPT_06361", "R2_4B_OPT_06176", "R2_4B_OPT_06024", "R2_4B_OPT_02167", "R2_4B_OPT_06129"]
VALID_DIPOLES = [
    {"suffix": "center_x", "dipole_orientation": "simulation_x", "theta": 90.0, "phi": 0.0},
    {"suffix": "center_z_outofplane", "dipole_orientation": "simulation_z_outofplane", "theta": 0.0, "phi": 0.0},
]

N_GAN = 2.56
N_TIO2 = 2.60
N_SIO2 = 1.46
UM = 1e-6
NM = 1e-9
FDTD_X_SPAN_UM = 20.0
DEVICE_X_SPAN_UM = 3.0
DBR_X_SPAN_UM = 8.0
MONITOR_X_SPAN_UM = 16.0
AIR_ABOVE_TOP_UM = 0.8
AIR_BELOW_BOTTOM_UM = 0.8
MONITOR_CLEARANCE_UM = 0.35
SIM_TIME_FS = 250.0

MATERIALS = {
    "GaN_450nm_n2p56_custom": (N_GAN, [0.45, 0.70, 1.0, 0.45]),
    "TiO2_n2p6_custom": (N_TIO2, [1.0, 0.0, 0.0, 0.45]),
    "SiO2_n1p46_custom": (N_SIO2, [1.0, 0.85, 0.0, 0.45]),
}
MAT_MAP = {
    "TiO2": "TiO2_n2p6_custom",
    "SiO2": "SiO2_n1p46_custom",
    "SiO2_termination": "SiO2_n1p46_custom",
    "TiO2_termination": "TiO2_n2p6_custom",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def import_lumapi() -> Any:
    sys.path.insert(0, str(LUMAPI_DIR))
    import lumapi  # type: ignore[import-not-found]
    return lumapi


def ensure_material(fdtd: Any, name: str, n: float, color: list[float]) -> None:
    existing = {line.strip() for line in str(fdtd.getmaterial()).splitlines() if line.strip()}
    if name in existing:
        return
    mid = fdtd.addmaterial("(n,k) Material")
    fdtd.setmaterial(mid, "name", name)
    fdtd.setmaterial(name, "Refractive Index", n)
    fdtd.setmaterial(name, "Imaginary Refractive Index", 0)
    fdtd.setmaterial(name, "Mesh order", 3)
    try:
        fdtd.setmaterial(name, "color", np.array(color))
    except Exception:
        pass


def add_rect(fdtd: Any, name: str, mat: str, x_span_um: float, y_min_nm: float, y_max_nm: float) -> None:
    if y_max_nm <= y_min_nm:
        raise ValueError(f"non-positive layer thickness for {name}: {y_min_nm}..{y_max_nm} nm")
    fdtd.addrect()
    fdtd.set("name", name)
    fdtd.set("material", mat)
    fdtd.set("x", 0)
    fdtd.set("x span", x_span_um * UM)
    fdtd.set("y min", y_min_nm * NM)
    fdtd.set("y max", y_max_nm * NM)


def load_inputs() -> tuple[list[dict[str, str]], dict[tuple[str, str], list[dict[str, object]]]]:
    shortlist = [r for r in read_csv(R2B / "r2_4b_fdtd_shortlist.csv") if r["candidate_id"] in TOP_IDS]
    by_id = {r["candidate_id"]: r for r in shortlist}
    if set(by_id) != set(TOP_IDS):
        missing = sorted(set(TOP_IDS) - set(by_id))
        raise RuntimeError(f"missing R2-4B shortlist rows: {missing}")
    layer_rows = read_csv(R2B / "r2_4b_top_candidate_layer_thicknesses.csv")
    layers: dict[tuple[str, str], list[dict[str, object]]] = {}
    for r in layer_rows:
        cid, stack = r["candidate_id"], r["stack"]
        if cid not in TOP_IDS:
            continue
        layers.setdefault((cid, stack), []).append({
            "candidate_id": cid,
            "stack": stack,
            "layer_index": int(r["layer_index"]),
            "material": r["material"],
            "thickness_nm": float(r["thickness_nm"]),
        })
    for cid in TOP_IDS:
        for stack in ("top", "bottom"):
            if (cid, stack) not in layers:
                raise RuntimeError(f"missing layer manifest for {cid} {stack}")
            layers[(cid, stack)].sort(key=lambda x: int(x["layer_index"]))
    return [by_id[cid] for cid in TOP_IDS], layers


def build_layout(fdtd: Any, cand: dict[str, str], layers: dict[tuple[str, str], list[dict[str, object]]], dip: dict[str, object]) -> dict[str, object]:
    cid = cand["candidate_id"]
    cavity_nm = float(cand["cavity_spacer_nm"])
    top_layers = layers[(cid, "top")]
    bottom_layers = layers[(cid, "bottom")]
    fdtd.switchtolayout()
    fdtd.deleteall()
    for name, (n, color) in MATERIALS.items():
        ensure_material(fdtd, name, n, color)

    top_total_nm = sum(float(r["thickness_nm"]) for r in top_layers)
    bottom_total_nm = sum(float(r["thickness_nm"]) for r in bottom_layers)
    top_max_nm = cavity_nm + top_total_nm
    bottom_min_nm = -bottom_total_nm
    y_min_um = bottom_min_nm / 1000.0 - AIR_BELOW_BOTTOM_UM
    y_max_um = top_max_nm / 1000.0 + AIR_ABOVE_TOP_UM
    monitor_y_um = min(y_max_um - 0.35, top_max_nm / 1000.0 + MONITOR_CLEARANCE_UM)
    source_y_nm = cavity_nm / 2.0

    fdtd.addfdtd()
    fdtd.set("dimension", "2D")
    fdtd.set("x span", FDTD_X_SPAN_UM * UM)
    fdtd.set("y min", y_min_um * UM)
    fdtd.set("y max", y_max_um * UM)
    fdtd.set("x min bc", "PML")
    fdtd.set("x max bc", "PML")
    fdtd.set("y min bc", "PML")
    fdtd.set("y max bc", "PML")
    fdtd.set("mesh accuracy", 3)
    fdtd.set("simulation time", SIM_TIME_FS * 1e-15)

    fdtd.addstructuregroup(); fdtd.set("name", "RCLED_bottom_reflector_group")
    fdtd.groupscope("::model::RCLED_bottom_reflector_group")
    y = 0.0
    for r in bottom_layers:
        th = float(r["thickness_nm"])
        y_next = y - th
        add_rect(fdtd, f"bottom_{int(r['layer_index']):02d}_{r['material']}_{th:g}nm", MAT_MAP[str(r["material"])], DBR_X_SPAN_UM, y_next, y)
        y = y_next
    fdtd.groupscope("::model")

    fdtd.addstructuregroup(); fdtd.set("name", "RCLED_GaN_cavity_group")
    fdtd.groupscope("::model::RCLED_GaN_cavity_group")
    add_rect(fdtd, "GaN_cavity_device_aperture", "GaN_450nm_n2p56_custom", DEVICE_X_SPAN_UM, 0.0, cavity_nm)
    fdtd.groupscope("::model")

    fdtd.addstructuregroup(); fdtd.set("name", "RCLED_top_DBR_group")
    fdtd.groupscope("::model::RCLED_top_DBR_group")
    y = cavity_nm
    for r in top_layers:
        th = float(r["thickness_nm"])
        add_rect(fdtd, f"top_{int(r['layer_index']):02d}_{r['material']}_{th:g}nm", MAT_MAP[str(r["material"])], DBR_X_SPAN_UM, y, y + th)
        y += th
    fdtd.groupscope("::model")

    source_name = f"{dip['suffix']}_dipole"
    fdtd.adddipole()
    fdtd.set("name", source_name)
    fdtd.set("x", 0)
    fdtd.set("y", source_y_nm * NM)
    fdtd.set("theta", float(dip["theta"]))
    fdtd.set("phi", float(dip["phi"]))
    fdtd.set("wavelength start", WAVELENGTH_NM * NM)
    fdtd.set("wavelength stop", WAVELENGTH_NM * NM)

    fdtd.addpower()
    fdtd.set("name", "top_farfield_monitor")
    fdtd.set("monitor type", "Linear X")
    fdtd.set("x", 0)
    fdtd.set("x span", MONITOR_X_SPAN_UM * UM)
    fdtd.set("y", monitor_y_um * UM)

    theta = float(fdtd.getnamed(source_name, "theta"))
    phi = float(fdtd.getnamed(source_name, "phi"))
    fsp = RUNTIME_FSP / f"R2_4C_{cid}_453_{dip['suffix']}_setup_only.fsp"
    fdtd.save(str(fsp))

    return {
        "case_id": f"R2_4C_{cid}_453_{dip['suffix']}",
        "candidate_id": cid,
        "dipole_case": dip["suffix"],
        "dipole_orientation": dip["dipole_orientation"],
        "theta_requested_deg": dip["theta"],
        "phi_requested_deg": dip["phi"],
        "theta_readback_deg": theta,
        "phi_readback_deg": phi,
        "source_axis_verified": abs(theta - float(dip["theta"])) < 1e-9 and abs(phi - float(dip["phi"])) < 1e-9,
        "wavelength_nm": WAVELENGTH_NM,
        "top_pair_count": int(float(cand["top_pair_count"])),
        "bottom_pair_count": int(float(cand["bottom_pair_count"])),
        "cavity_spacer_nm": cavity_nm,
        "top_termination_nm": float(cand["top_termination_nm"]),
        "bottom_termination_nm": float(cand["bottom_termination_nm"]),
        "source_y_nm": source_y_nm,
        "source_centered_in_cavity": abs(source_y_nm - cavity_nm / 2.0) <= 1e-9,
        "source_on_material_interface": False,
        "source_distance_to_bottom_interface_nm": source_y_nm,
        "source_distance_to_top_interface_nm": cavity_nm - source_y_nm,
        "fdtd_dimension": "2D",
        "fdtd_x_span_um": FDTD_X_SPAN_UM,
        "fdtd_y_min_um": y_min_um,
        "fdtd_y_max_um": y_max_um,
        "device_width_um": DEVICE_X_SPAN_UM,
        "dbr_lateral_span_um": DBR_X_SPAN_UM,
        "monitor_x_span_um": MONITOR_X_SPAN_UM,
        "monitor_y_um": monitor_y_um,
        "monitor_y_to_top_pml_um": y_max_um - monitor_y_um,
        "monitor_y_above_top_structure_um": monitor_y_um - top_max_nm / 1000.0,
        "monitor_inside_pml": False,
        "monitor_above_top_dbr": monitor_y_um > top_max_nm / 1000.0,
        "monitor_in_homogeneous_air": True,
        "bottom_dbr_top_equals_cavity_bottom": True,
        "top_dbr_bottom_equals_cavity_top": True,
        "no_center_y_case": True,
        "no_solve_was_run": True,
        "fsp_path": str(fsp),
        "fsp_file_exists": fsp.exists(),
        "fsp_file_size_bytes": fsp.stat().st_size if fsp.exists() else 0,
        "git_stage_allowed": "no",
    }


def build_all(cands: list[dict[str, str]], layers: dict[tuple[str, str], list[dict[str, object]]]) -> list[dict[str, object]]:
    lumapi = import_lumapi()
    rows: list[dict[str, object]] = []
    RUNTIME_FSP.mkdir(parents=True, exist_ok=True)
    for cand in cands:
        for dip in VALID_DIPOLES:
            fdtd = lumapi.FDTD(hide=True)
            try:
                rows.append(build_layout(fdtd, cand, layers, dip))
            finally:
                try:
                    fdtd.close()
                except Exception:
                    pass
    return rows


def write_reports(cands: list[dict[str, str]], layers: dict[tuple[str, str], list[dict[str, object]]], rows: list[dict[str, object]]) -> None:
    manifest = [{
        "case_id": r["case_id"], "candidate_id": r["candidate_id"], "dipole_case": r["dipole_case"],
        "dipole_orientation": r["dipole_orientation"], "wavelength_nm": r["wavelength_nm"],
        "fsp_path": r["fsp_path"], "status": "setup_only_saved", "no_solve_was_run": True,
    } for r in rows]
    write_csv(OUT / "r2_4c_setup_manifest.csv", manifest)
    (OUT / "r2_4c_setup_manifest.json").write_text(json.dumps({"stage": STAGE, "expected_fsp_count": 10, "actual_fsp_count": len(rows), "cases": manifest}, indent=2), encoding="utf-8")

    geom_rows = []
    for cand in cands:
        cid = cand["candidate_id"]
        geom_rows.append({
            "candidate_id": cid,
            "top_pair_count": int(float(cand["top_pair_count"])),
            "bottom_pair_count": int(float(cand["bottom_pair_count"])),
            "cavity_spacer_nm": float(cand["cavity_spacer_nm"]),
            "top_termination_nm": float(cand["top_termination_nm"]),
            "bottom_termination_nm": float(cand["bottom_termination_nm"]),
            "top_layer_count_manifest": len(layers[(cid, "top")]),
            "bottom_layer_count_manifest": len(layers[(cid, "bottom")]),
            "proxy_peak_abs_angle_deg_453": cand.get("peak_angle_abs_deg_453", ""),
            "proxy_angular_fwhm_deg_453": cand.get("angular_fwhm_deg_453", ""),
            "proxy_normal_offaxis_ratio": cand.get("normal_offaxis_ratio", ""),
            "proxy_spectral_peak_nm": cand.get("spectral_peak_nm_normal_window", ""),
            "proxy_spectral_fwhm_nm": cand.get("spectral_fwhm_nm_normal_window", ""),
        })
    write_csv(OUT / "r2_4c_candidate_geometry_summary.csv", geom_rows)

    layer_out = []
    for cid in TOP_IDS:
        for stack in ("bottom", "top"):
            for r in layers[(cid, stack)]:
                layer_out.append(r)
    write_csv(OUT / "r2_4c_layer_thickness_manifest.csv", layer_out)

    audit_cols = [
        "case_id", "candidate_id", "dipole_case", "dipole_orientation", "theta_requested_deg", "phi_requested_deg",
        "theta_readback_deg", "phi_readback_deg", "source_axis_verified", "source_y_nm", "source_centered_in_cavity",
        "source_on_material_interface", "source_distance_to_bottom_interface_nm", "source_distance_to_top_interface_nm",
        "monitor_y_um", "monitor_y_to_top_pml_um", "monitor_y_above_top_structure_um", "monitor_inside_pml",
        "monitor_above_top_dbr", "monitor_in_homogeneous_air", "no_center_y_case", "no_solve_was_run",
    ]
    write_csv(OUT / "r2_4c_source_monitor_audit.csv", [{k: r[k] for k in audit_cols} for r in rows])
    write_csv(OUT / "r2_4c_runtime_fsp_manifest.csv", [{"case_id": r["case_id"], "candidate_id": r["candidate_id"], "dipole_case": r["dipole_case"], "fsp_path": r["fsp_path"], "fsp_file_exists": r["fsp_file_exists"], "fsp_file_size_bytes": r["fsp_file_size_bytes"], "git_stage_allowed": "no"} for r in rows])

    checklist = """
# R2-4C Manual GUI Inspection Checklist

For each setup-only FSP:

- Confirm 2D FDTD.
- Confirm each candidate has correct top/bottom pair count.
- Confirm variable layer thicknesses match `r2_4c_layer_thickness_manifest.csv`.
- Confirm cavity spacer thickness matches the R2-4B candidate.
- Confirm source is at cavity center and not on a material interface.
- Confirm `center_x` is theta=90, phi=0.
- Confirm `center_z_outofplane` is theta=0, phi=0.
- Confirm there is no `center_y` solve candidate.
- Confirm monitor is above top DBR, outside PML, in homogeneous air.
- Confirm x span is 20 um, device width is 3 um, DBR span is 8 um, and monitor span is 16 um.
- Do not solve until this checklist passes.
"""
    write_text(OUT / "r2_4c_manual_gui_inspection_checklist.md", checklist)

    summary = f"""
# R2-4C Variable DBR Setup-Only FSP Package

Generated setup-only 2D FDTD models for the top 5 R2-4B variable-thickness DBR candidates and the valid MQW dipole pair.

- Lumerical/lumapi was launched only to build layout and save FSP files.
- FDTD solve was not run.
- No `run`, `runanalysis`, far-field calculation, `.ldf`, or raw monitor export was performed.
- Runtime FSP count: {len(rows)} / 10.
- Valid dipoles: `center_x` and `center_z_outofplane`.
- Invalid omitted dipole: `center_y` / simulation-y cavity-normal.

Runtime FSP files are under `outputs/r2_4c_variable_dbr_setup_only_fsp/runtime_fsp/` and must not be committed.
"""
    write_text(OUT / "r2_4c_summary.md", summary)
    write_text(OUT / "r2_4c_solve_readiness.md", """
# R2-4C Solve Readiness

Status: blocked pending manual GUI inspection.

The setup-only FSP files are intended for GUI inspection only. Solve may proceed in a later stage only after the checklist confirms geometry, variable layer thicknesses, source orientation, source placement, monitor placement, and PML clearance.
""")
    write_text(OUT / "r2_4c_next_steps.md", """
# R2-4C Next Steps

1. Open the ten setup-only FSP files in Lumerical GUI.
2. Compare each candidate stack against `r2_4c_layer_thickness_manifest.csv`.
3. Confirm center_x and center_z_outofplane source orientations.
4. If GUI inspection passes, approve a separate R2-4D smoke solve for only the top candidate first.
""")
    debug = {"stage": STAGE, "candidates": TOP_IDS, "actual_fsp_count": len(rows), "no_solve_was_run": True, "runtime_fsp_dir": str(RUNTIME_FSP)}
    (OUT / "r2_4c_debug.json").write_text(json.dumps(debug, indent=2), encoding="utf-8")

    marker = "## R2-4C Variable DBR Setup-Only FSPs"
    block = f"""
{marker}

- Output: `outputs/r2_4c_variable_dbr_setup_only_fsp`
- Runtime FSP files: 10 setup-only files for R2-4B top 5 candidates x center_x/center_z_outofplane.
- FDTD solve: not run.
- Lumerical/lumapi use: layout generation and save only.
- GUI inspection is required before any R2-4D solve.
""".strip()
    old = INDEX.read_text(encoding="utf-8") if INDEX.exists() else "# RCLED MDC Workspace Index\n"
    if marker in old:
        old = old.split(marker)[0].rstrip()
    write_text(INDEX, old.rstrip() + "\n\n" + block)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cands, layers = load_inputs()
    rows = build_all(cands, layers)
    write_reports(cands, layers, rows)
    print(json.dumps({"output": str(OUT), "runtime_fsp_dir": str(RUNTIME_FSP), "fsp_count": len(rows)}, indent=2))
    for row in rows:
        print(row["fsp_path"])


if __name__ == "__main__":
    main()
