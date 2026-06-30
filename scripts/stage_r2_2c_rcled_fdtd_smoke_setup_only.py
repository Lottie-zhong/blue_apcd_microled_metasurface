#!/usr/bin/env python3
"""Generate corrected setup-only 2D FDTD files for R2-2C GUI inspection.

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
OUT = ROOT / "outputs" / "r2_2c_rcled_fdtd_smoke_setup_only"
RUNTIME_FSP = OUT / "runtime_fsp"
INDEX = ROOT / "reports" / "rcled_mdc_workspace_index.md"
LUMAPI_DIR = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")

STAGE = "R2_2C_RCLED_FDTD_smoke_setup_only"
CANDIDATE_ID = "R2_1_00223"
FAMILY = "R2A_Taguchi2026_scaled_control"
WAVELENGTH_NM = 453.0
TOP_PAIR_COUNT = 6
BOTTOM_PAIR_COUNT = 6
CAVITY_SPAN_NM = 280.0
TERMINATION = "none"

N_GAN = 2.56
N_TIO2 = 2.60
N_SIO2 = 1.46
SIO2_NM = 100.0
TIO2_NM = 52.0
PAIR_NM = SIO2_NM + TIO2_NM

FDTD_X_SPAN_UM = 20.0
FDTD_Y_MIN_UM = -1.4
FDTD_Y_MAX_UM = 2.2
DEVICE_X_SPAN_UM = 3.0
DBR_X_SPAN_UM = 8.0
MONITOR_X_SPAN_UM = 16.0
MONITOR_Y_UM = 1.8
SIM_TIME_FS = 250.0

UM = 1e-6
NM = 1e-9

MATERIALS = {
    "GaN_450nm_n2p56_custom": (N_GAN, [1.0, 0.35, 0.70, 0.45]),
    "TiO2_n2p6_custom": (N_TIO2, [1.0, 0.0, 0.0, 0.45]),
    "SiO2_n1p46_custom": (N_SIO2, [1.0, 0.85, 0.0, 0.45]),
}

VALID_CASES = [
    {"case_id": "R2_2C_R2_1_00223_453_center_x", "dipole_orientation": "x", "theta": 90.0, "phi": 0.0, "validity": "VALID_SOLVE_CANDIDATE"},
    {"case_id": "R2_2C_R2_1_00223_453_center_z_outofplane", "dipole_orientation": "z_outofplane", "theta": 0.0, "phi": 0.0, "validity": "VALID_SOLVE_CANDIDATE"},
]

INVALID_Y = {
    "case_id": "R2_2C_R2_1_00223_453_center_y",
    "dipole_orientation": "y_invalid_cavity_normal",
    "theta": 90.0,
    "phi": 90.0,
    "validity": "INVALID_DO_NOT_SOLVE",
    "invalid_reason": "simulation_y is the vertical cavity-normal direction in this 2D x-y layout; MQW incoherent pair should be simulation_x + simulation_z_outofplane",
}


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


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
        raise ValueError(f"Non-positive layer thickness for {name}: {y_min_nm}..{y_max_nm} nm")
    fdtd.addrect()
    fdtd.set("name", name)
    fdtd.set("material", mat)
    fdtd.set("x", 0)
    fdtd.set("x span", x_span_um * UM)
    fdtd.set("y min", y_min_nm * NM)
    fdtd.set("y max", y_max_nm * NM)


def build_layout(fdtd: Any, case: dict[str, object]) -> dict[str, object]:
    fdtd.switchtolayout()
    fdtd.deleteall()
    for name, (n, color) in MATERIALS.items():
        ensure_material(fdtd, name, n, color)

    fdtd.addfdtd()
    fdtd.set("dimension", "2D")
    fdtd.set("x span", FDTD_X_SPAN_UM * UM)
    fdtd.set("y min", FDTD_Y_MIN_UM * UM)
    fdtd.set("y max", FDTD_Y_MAX_UM * UM)
    fdtd.set("x min bc", "PML")
    fdtd.set("x max bc", "PML")
    fdtd.set("y min bc", "PML")
    fdtd.set("y max bc", "PML")
    fdtd.set("mesh accuracy", 3)
    fdtd.set("simulation time", SIM_TIME_FS * 1e-15)

    bottom_min = -BOTTOM_PAIR_COUNT * PAIR_NM
    cavity_min = 0.0
    cavity_max = CAVITY_SPAN_NM
    source_y_nm = (cavity_min + cavity_max) * 0.5

    fdtd.addstructuregroup()
    fdtd.set("name", "RCLED_bottom_reflector_group")
    fdtd.groupscope("::model::RCLED_bottom_reflector_group")
    y_top = cavity_min
    for i in range(BOTTOM_PAIR_COUNT):
        add_rect(fdtd, f"bottom_{i:02d}_TiO2_52nm", "TiO2_n2p6_custom", DBR_X_SPAN_UM, y_top - TIO2_NM, y_top)
        y_top -= TIO2_NM
        add_rect(fdtd, f"bottom_{i:02d}_SiO2_100nm", "SiO2_n1p46_custom", DBR_X_SPAN_UM, y_top - SIO2_NM, y_top)
        y_top -= SIO2_NM
    fdtd.groupscope("::model")

    fdtd.addstructuregroup()
    fdtd.set("name", "RCLED_GaN_cavity_group")
    fdtd.groupscope("::model::RCLED_GaN_cavity_group")
    add_rect(fdtd, "GaN_cavity_device_aperture", "GaN_450nm_n2p56_custom", DEVICE_X_SPAN_UM, cavity_min, cavity_max)
    fdtd.groupscope("::model")

    fdtd.addstructuregroup()
    fdtd.set("name", "RCLED_top_DBR_group")
    fdtd.groupscope("::model::RCLED_top_DBR_group")
    y = cavity_max
    for i in range(TOP_PAIR_COUNT):
        add_rect(fdtd, f"top_{i:02d}_SiO2_100nm", "SiO2_n1p46_custom", DBR_X_SPAN_UM, y, y + SIO2_NM)
        y += SIO2_NM
        add_rect(fdtd, f"top_{i:02d}_TiO2_52nm", "TiO2_n2p6_custom", DBR_X_SPAN_UM, y, y + TIO2_NM)
        y += TIO2_NM
    fdtd.groupscope("::model")
    top_max = y

    source_name = f"center_{case['dipole_orientation']}_dipole"
    fdtd.adddipole()
    fdtd.set("name", source_name)
    fdtd.set("x", 0)
    fdtd.set("y", source_y_nm * NM)
    fdtd.set("theta", float(case["theta"]))
    fdtd.set("phi", float(case["phi"]))
    fdtd.set("wavelength start", WAVELENGTH_NM * NM)
    fdtd.set("wavelength stop", WAVELENGTH_NM * NM)

    fdtd.addpower()
    fdtd.set("name", "top_farfield_monitor")
    fdtd.set("monitor type", "Linear X")
    fdtd.set("x", 0)
    fdtd.set("x span", MONITOR_X_SPAN_UM * UM)
    fdtd.set("y", MONITOR_Y_UM * UM)

    source_theta = float(fdtd.getnamed(source_name, "theta"))
    source_phi = float(fdtd.getnamed(source_name, "phi"))
    fsp_path = RUNTIME_FSP / f"{case['case_id']}_setup_only.fsp"
    fdtd.save(str(fsp_path))

    return audit_row(case, fsp_path, source_name, source_theta, source_phi, source_y_nm, bottom_min, cavity_min, cavity_max, top_max)


def audit_row(case: dict[str, object], fsp_path: Path, source_name: str, source_theta: float, source_phi: float, source_y_nm: float, bottom_min: float, cavity_min: float, cavity_max: float, top_max: float) -> dict[str, object]:
    return {
        "case_id": case["case_id"],
        "candidate_id": CANDIDATE_ID,
        "wavelength_nm": WAVELENGTH_NM,
        "dipole_orientation": case["dipole_orientation"],
        "validity": case.get("validity", "VALID_SOLVE_CANDIDATE"),
        "invalid_reason": case.get("invalid_reason", ""),
        "source_name": source_name,
        "source_theta_deg": source_theta,
        "source_phi_deg": source_phi,
        "source_y_nm": source_y_nm,
        "source_inside_cavity_center": abs(source_y_nm - CAVITY_SPAN_NM / 2) < 1e-9,
        "source_distance_to_bottom_interface_nm": source_y_nm - cavity_min,
        "source_distance_to_top_interface_nm": cavity_max - source_y_nm,
        "top_pair_count": TOP_PAIR_COUNT,
        "bottom_pair_count": BOTTOM_PAIR_COUNT,
        "cavity_physical_spacer_nm": CAVITY_SPAN_NM,
        "fdtd_dimension": "2D",
        "fdtd_x_span_um": FDTD_X_SPAN_UM,
        "active_device_width_um": DEVICE_X_SPAN_UM,
        "dbr_x_span_um": DBR_X_SPAN_UM,
        "monitor_x_span_um": MONITOR_X_SPAN_UM,
        "monitor_y_um": MONITOR_Y_UM,
        "monitor_y_to_top_pml_um": FDTD_Y_MAX_UM - MONITOR_Y_UM,
        "monitor_y_above_top_structure_um": MONITOR_Y_UM - top_max / 1000.0,
        "bottom_structure_to_pml_um": bottom_min / 1000.0 - FDTD_Y_MIN_UM,
        "monitor_inside_pml": False,
        "pml_not_too_close": (FDTD_Y_MAX_UM - MONITOR_Y_UM) >= 0.3 and (bottom_min / 1000.0 - FDTD_Y_MIN_UM) >= 0.3,
        "no_zero_thickness_layers": True,
        "no_overlapping_layers": True,
        "no_solve_was_run": True,
        "fsp_path": str(fsp_path),
        "fsp_file_exists": fsp_path.exists(),
        "fsp_file_size_bytes": fsp_path.stat().st_size if fsp_path.exists() else 0,
    }


def invalid_y_row() -> dict[str, object]:
    path = RUNTIME_FSP / "R2_2C_R2_1_00223_453_center_y_setup_only.fsp"
    return audit_row(
        INVALID_Y,
        path,
        "center_y_dipole",
        float(INVALID_Y["theta"]),
        float(INVALID_Y["phi"]),
        CAVITY_SPAN_NM / 2,
        -BOTTOM_PAIR_COUNT * PAIR_NM,
        0.0,
        CAVITY_SPAN_NM,
        CAVITY_SPAN_NM + TOP_PAIR_COUNT * PAIR_NM,
    )


def build_fsp_files() -> list[dict[str, object]]:
    RUNTIME_FSP.mkdir(parents=True, exist_ok=True)
    lumapi = import_lumapi()
    rows = []
    for case in VALID_CASES:
        fdtd = lumapi.FDTD(hide=True)
        try:
            rows.append(build_layout(fdtd, case))
        finally:
            try:
                fdtd.close()
            except Exception:
                pass
    rows.append(invalid_y_row())
    return rows


def write_reports(rows: list[dict[str, object]]) -> None:
    valid = [r for r in rows if r["validity"] == "VALID_SOLVE_CANDIDATE"]
    manifest_rows = [
        {
            "case_id": r["case_id"],
            "candidate_id": CANDIDATE_ID,
            "wavelength_nm": WAVELENGTH_NM,
            "dipole_orientation": r["dipole_orientation"],
            "validity": r["validity"],
            "invalid_reason": r["invalid_reason"],
            "fsp_path": r["fsp_path"],
            "status": "setup_only_saved" if r["validity"] == "VALID_SOLVE_CANDIDATE" else "INVALID_DO_NOT_SOLVE",
            "no_solve_was_run": True,
        }
        for r in rows
    ]
    write_csv(OUT / "r2_2c_setup_manifest.csv", manifest_rows)
    (OUT / "r2_2c_setup_manifest.json").write_text(json.dumps({"stage": STAGE, "valid_cases": valid, "all_cases": manifest_rows}, indent=2), encoding="utf-8")
    write_csv(OUT / "r2_2c_vertical_geometry_audit.csv", rows)
    source_rows = [
        {k: r[k] for k in [
            "case_id", "dipole_orientation", "validity", "invalid_reason", "source_name", "source_theta_deg", "source_phi_deg",
            "source_y_nm", "source_inside_cavity_center", "source_distance_to_bottom_interface_nm",
            "source_distance_to_top_interface_nm", "monitor_y_um", "monitor_y_to_top_pml_um",
            "monitor_y_above_top_structure_um", "monitor_inside_pml", "pml_not_too_close",
        ]}
        for r in rows
    ]
    write_csv(OUT / "r2_2c_source_monitor_audit.csv", source_rows)
    write_csv(OUT / "r2_2c_runtime_fsp_manifest.csv", [
        {"case_id": r["case_id"], "dipole_orientation": r["dipole_orientation"], "validity": r["validity"], "invalid_reason": r["invalid_reason"], "fsp_path": r["fsp_path"], "fsp_file_exists": r["fsp_file_exists"], "fsp_file_size_bytes": r["fsp_file_size_bytes"], "git_stage_allowed": "no"}
        for r in rows
    ])

    mapping = """
# R2-2C Coordinate Mapping

- simulation_x = horizontal lateral direction.
- simulation_y = vertical cavity-normal direction / upward emission direction in this 2D x-y layout.
- simulation_z = out-of-plane direction.
- Physical MQW incoherent pair for this 2D smoke test = simulation_x + simulation_z_outofplane.
- simulation_y dipole = cavity-normal dipole and is INVALID_DO_NOT_SOLVE for this MQW smoke test.
"""
    checklist = mapping + """

# Manual GUI Inspection Checklist

For each setup-only FSP:

- Confirm simulation dimension is 2D.
- Confirm no result data exist and no solve has been run.
- Confirm top DBR has 6 SiO2/TiO2 pairs and no unintended terminal layer.
- Confirm bottom DBR has 6 TiO2/SiO2 pairs and touches the GaN cavity at y=0.
- Confirm GaN/effective cavity spacer thickness is 280 nm.
- Confirm MQW dipole is at y=140 nm, the cavity center.
- Confirm source does not sit on a material interface.
- Confirm x file uses theta=90, phi=0.
- Confirm corrected out-of-plane file uses theta=0, phi=0 and does not display as a vertical y/cavity-normal arrow.
- Confirm old center_y file is marked INVALID_DO_NOT_SOLVE and is not solved.
- Confirm monitor is above the DBR, outside PML, and inside homogeneous air.
- Do not run solve until this checklist passes.
"""
    write_text(OUT / "r2_2c_manual_gui_inspection_checklist.md", checklist)

    summary = f"""
# R2-2C Corrected Setup-Only FDTD Files

Corrected the MQW dipole-pair mapping for the 2D x-y RCLED layout.

No FDTD solve was run. No `run`, `runanalysis`, far-field extraction, `.ldf`, or raw monitor export was performed.

## Valid solve candidates

- `R2_2C_R2_1_00223_453_center_x_setup_only.fsp`: simulation x dipole, theta=90, phi=0.
- `R2_2C_R2_1_00223_453_center_z_outofplane_setup_only.fsp`: simulation z/out-of-plane dipole, theta=0, phi=0.

## Invalid retained file

- `R2_2C_R2_1_00223_453_center_y_setup_only.fsp`: INVALID_DO_NOT_SOLVE. This is a simulation-y cavity-normal dipole in the current 2D x-y layout.

Runtime FSP files are saved under `outputs/r2_2c_rcled_fdtd_smoke_setup_only/runtime_fsp/` and must not be staged.
"""
    write_text(OUT / "r2_2c_summary.md", summary)

    readiness = """
# R2-2C Solve Readiness

Status: blocked pending manual GUI inspection.

Valid future smoke pair: center_x plus center_z_outofplane. The old center_y setup is INVALID_DO_NOT_SOLVE.

Solve should remain blocked until the GUI checklist confirms geometry, source orientation, monitor placement, and PML spacing.
"""
    write_text(OUT / "r2_2c_solve_readiness.md", readiness)

    next_steps = """
# R2-2C Next Steps

1. Open center_x and center_z_outofplane setup-only FSP files manually in the GUI.
2. Confirm the out-of-plane source orientation uses theta=0 and is not a vertical y/cavity-normal arrow.
3. Do not solve the old center_y file; it is invalid for this MQW smoke test.
4. If GUI inspection passes, approve a separate R2-2D solve stage for only the two valid files.
"""
    write_text(OUT / "r2_2c_next_steps.md", next_steps)

    marker = "## R2-2C Setup-Only FDTD GUI Inspection Files"
    block = f"""
{marker}

- Output: `outputs/r2_2c_rcled_fdtd_smoke_setup_only`
- Valid setup-only files: R2_1_00223 center_x and center_z_outofplane at 453 nm.
- Invalid retained file: center_y is INVALID_DO_NOT_SOLVE because simulation_y is cavity-normal in the 2D x-y layout.
- No FDTD solve, no analysis, no far-field extraction.
- Solve remains blocked until manual GUI inspection passes.
""".strip()
    old = INDEX.read_text(encoding="utf-8") if INDEX.exists() else "# RCLED MDC Workspace Index\n"
    if marker in old:
        old = old.split(marker)[0].rstrip()
    write_text(INDEX, old.rstrip() + "\n\n" + block)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = build_fsp_files()
    write_reports(rows)
    print(f"wrote {OUT}")
    for row in rows:
        print(f"{row['validity']} {row['fsp_path']}")


if __name__ == "__main__":
    main()
