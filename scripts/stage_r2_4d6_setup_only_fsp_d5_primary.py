#!/usr/bin/env python3
"""R2-4D6 setup-only FSP generation for D5_BASE_13461 x-line x-dipole cases.

Allowed Lumerical actions: build layout and save .fsp. Forbidden: solve/run,
runanalysis, far-field extraction, .ldf/.mat/.h5/raw monitor creation.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4d6_setup_only_fsp_d5_primary"
RUNTIME_FSP = OUT / "runtime_fsp"
INDEX = ROOT / "reports" / "rcled_mdc_workspace_index.md"
D5 = ROOT / "outputs" / "r2_4d5_focused_cavity_termination_phase_optimization"
D5A = ROOT / "outputs" / "r2_4d5a_shortlist_te_tm_offaxis_risk_review"
LUMAPI_DIR = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")

STAGE = "R2-4D6 setup-only FSP generation for D5_BASE_13461"
CANDIDATE_ID = "D5_BASE_13461"
ROLE = "D5_PRIMARY"
WAVELENGTH_NM = 453.0
TOP_PAIR_COUNT = 10
BOTTOM_PAIR_COUNT = 12
CAVITY_SPACER_NM = 182.0
TOP_TERMINATION_NM = 0.0
BOTTOM_TERMINATION_NM = 113.0
X_POSITIONS_UM = [-1.4, -1.05, -0.70, -0.35, 0.0, 0.35, 0.70, 1.05, 1.4]

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
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
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


def load_layers() -> dict[str, list[dict[str, object]]]:
    path = D5 / "r2_4d5_candidate_layer_thicknesses.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    stacks: dict[str, list[dict[str, object]]] = {"top": [], "bottom": []}
    for row in read_csv(path):
        if row.get("candidate_id") != CANDIDATE_ID:
            continue
        stacks[row["stack"]].append({
            "layer_index": int(row["layer_index"]),
            "material": row["material"],
            "thickness_nm": float(row["thickness_nm"]),
        })
    for stack in stacks:
        stacks[stack].sort(key=lambda r: int(r["layer_index"]))
    if len(stacks["top"]) != TOP_PAIR_COUNT * 2 or len(stacks["bottom"]) != BOTTOM_PAIR_COUNT * 2 + 1:
        raise RuntimeError(f"unexpected layer counts: top={len(stacks['top'])}, bottom={len(stacks['bottom'])}")
    return stacks


def build_layout(fdtd: Any, x_um: float, stacks: dict[str, list[dict[str, object]]]) -> dict[str, object]:
    fdtd.switchtolayout()
    fdtd.deleteall()
    for name, (n, color) in MATERIALS.items():
        ensure_material(fdtd, name, n, color)

    top_total_nm = sum(float(r["thickness_nm"]) for r in stacks["top"])
    bottom_total_nm = sum(float(r["thickness_nm"]) for r in stacks["bottom"])
    top_max_nm = CAVITY_SPACER_NM + top_total_nm
    bottom_min_nm = -bottom_total_nm
    y_min_um = bottom_min_nm / 1000.0 - AIR_BELOW_BOTTOM_UM
    y_max_um = top_max_nm / 1000.0 + AIR_ABOVE_TOP_UM
    monitor_y_um = min(y_max_um - 0.35, top_max_nm / 1000.0 + MONITOR_CLEARANCE_UM)
    source_y_nm = CAVITY_SPACER_NM / 2.0

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
    for r in stacks["bottom"]:
        th = float(r["thickness_nm"])
        y_next = y - th
        add_rect(fdtd, f"bottom_{int(r['layer_index']):02d}_{r['material']}_{th:g}nm", MAT_MAP[str(r["material"])], DBR_X_SPAN_UM, y_next, y)
        y = y_next
    fdtd.groupscope("::model")

    fdtd.addstructuregroup(); fdtd.set("name", "RCLED_GaN_cavity_group")
    fdtd.groupscope("::model::RCLED_GaN_cavity_group")
    add_rect(fdtd, "GaN_cavity_device_aperture", "GaN_450nm_n2p56_custom", DEVICE_X_SPAN_UM, 0.0, CAVITY_SPACER_NM)
    fdtd.groupscope("::model")

    fdtd.addstructuregroup(); fdtd.set("name", "RCLED_top_DBR_group")
    fdtd.groupscope("::model::RCLED_top_DBR_group")
    y = CAVITY_SPACER_NM
    for r in stacks["top"]:
        th = float(r["thickness_nm"])
        add_rect(fdtd, f"top_{int(r['layer_index']):02d}_{r['material']}_{th:g}nm", MAT_MAP[str(r["material"])], DBR_X_SPAN_UM, y, y + th)
        y += th
    fdtd.groupscope("::model")

    case_suffix = f"x{x_um:+.2f}um".replace("+", "p").replace("-", "m").replace(".", "p")
    case_id = f"R2_4D6_{CANDIDATE_ID}_453_{case_suffix}_xdipole"
    source_name = f"src_{case_suffix}_x"
    fdtd.adddipole()
    fdtd.set("name", source_name)
    fdtd.set("x", x_um * UM)
    fdtd.set("y", source_y_nm * NM)
    fdtd.set("theta", 90.0)
    fdtd.set("phi", 0.0)
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
    fsp_path = RUNTIME_FSP / f"{case_id}_setup_only.fsp"
    fdtd.save(str(fsp_path))

    source_inside_x = abs(x_um) <= DEVICE_X_SPAN_UM / 2.0
    source_inside_y = 0.0 < source_y_nm < CAVITY_SPACER_NM
    monitor_above = monitor_y_um > top_max_nm / 1000.0
    row = {
        "case_id": case_id,
        "candidate_id": CANDIDATE_ID,
        "role": ROLE,
        "wavelength_nm": WAVELENGTH_NM,
        "source_x_um": x_um,
        "source_y_nm": source_y_nm,
        "dipole_orientation": "x",
        "theta_requested_deg": 90.0,
        "phi_requested_deg": 0.0,
        "theta_readback_deg": theta,
        "phi_readback_deg": phi,
        "physical_x_dipole_verified": abs(theta - 90.0) < 1e-9 and abs(phi) < 1e-9,
        "top_pair_count": TOP_PAIR_COUNT,
        "bottom_pair_count": BOTTOM_PAIR_COUNT,
        "cavity_spacer_nm": CAVITY_SPACER_NM,
        "top_termination_nm": TOP_TERMINATION_NM,
        "bottom_termination_nm": BOTTOM_TERMINATION_NM,
        "top_layer_count": len(stacks["top"]),
        "bottom_layer_count": len(stacks["bottom"]),
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
        "monitor_above_top_dbr": monitor_above,
        "monitor_in_homogeneous_air": True,
        "monitor_inside_pml": False,
        "source_inside_cavity_x": source_inside_x,
        "source_inside_cavity_y": source_inside_y,
        "source_inside_cavity": source_inside_x and source_inside_y,
        "bottom_dbr_top_equals_cavity_bottom": True,
        "top_dbr_bottom_equals_cavity_top": True,
        "setup_only": True,
        "solved": False,
        "no_run_called": True,
        "no_farfield_extraction": True,
        "fsp_path": str(fsp_path),
        "fsp_file_exists": fsp_path.exists(),
        "fsp_file_size_bytes": fsp_path.stat().st_size if fsp_path.exists() else 0,
        "git_stage_allowed": "no",
    }
    row["geometry_pass"] = all([
        row["physical_x_dipole_verified"], row["source_inside_cavity"], monitor_above,
        not row["monitor_inside_pml"], row["bottom_dbr_top_equals_cavity_bottom"], row["top_dbr_bottom_equals_cavity_top"],
    ])
    return row


def build_all(stacks: dict[str, list[dict[str, object]]]) -> list[dict[str, object]]:
    lumapi = import_lumapi()
    RUNTIME_FSP.mkdir(parents=True, exist_ok=True)
    rows = []
    for x_um in X_POSITIONS_UM:
        fdtd = lumapi.FDTD(hide=True)
        try:
            rows.append(build_layout(fdtd, x_um, stacks))
        finally:
            try:
                fdtd.close()
            except Exception:
                pass
    return rows


def update_index() -> None:
    marker = "<!-- R2-4D6_SETUP_ONLY_FSP_D5_PRIMARY -->"
    text = INDEX.read_text(encoding="utf-8") if INDEX.exists() else "# RCLED MDC Workspace Index\n"
    block = f"""
{marker}

- Stage: R2-4D6 setup-only FSP generation for D5_BASE_13461.
- Worktree: `D:\\project\\worktrees\\blue_apcd_rcled_mdc`.
- Candidate: `D5_BASE_13461`, role `D5_PRIMARY`, 453 nm.
- Generated: 9 x-line x-dipole setup-only FSP files at x = -1.4 to +1.4 um.
- Output: `outputs/r2_4d6_setup_only_fsp_d5_primary`.
- Runtime FSPs: `outputs/r2_4d6_setup_only_fsp_d5_primary/runtime_fsp`; do not stage/commit.
- FDTD solve: not run.
""".strip()
    if marker in text:
        text = text[:text.index(marker)].rstrip()
    INDEX.write_text(text.rstrip() + "\n\n" + block + "\n", encoding="utf-8")


def write_reports(rows: list[dict[str, object]], stacks: dict[str, list[dict[str, object]]]) -> None:
    manifest = [{
        "case_id": r["case_id"], "candidate_id": r["candidate_id"], "role": r["role"],
        "wavelength_nm": r["wavelength_nm"], "source_x_um": r["source_x_um"],
        "dipole_orientation": r["dipole_orientation"], "theta_deg": r["theta_readback_deg"],
        "phi_deg": r["phi_readback_deg"], "fsp_path": r["fsp_path"], "status": "setup_only_saved",
        "setup_only": True, "solved": False,
    } for r in rows]
    write_csv(OUT / "r2_4d6_case_manifest.csv", manifest)
    (OUT / "r2_4d6_case_manifest.json").write_text(json.dumps({"stage": STAGE, "expected_cases": 9, "actual_cases": len(rows), "cases": manifest}, indent=2), encoding="utf-8")
    write_csv(OUT / "r2_4d6_fsp_inventory.csv", [{"case_id": r["case_id"], "fsp_path": r["fsp_path"], "fsp_file_exists": r["fsp_file_exists"], "fsp_file_size_bytes": r["fsp_file_size_bytes"], "git_stage_allowed": "no"} for r in rows])
    write_csv(OUT / "r2_4d6_geometry_audit.csv", [{k: r[k] for k in ["case_id", "top_pair_count", "bottom_pair_count", "cavity_spacer_nm", "top_termination_nm", "bottom_termination_nm", "top_layer_count", "bottom_layer_count", "fdtd_dimension", "fdtd_x_span_um", "fdtd_y_min_um", "fdtd_y_max_um", "device_width_um", "dbr_lateral_span_um", "bottom_dbr_top_equals_cavity_bottom", "top_dbr_bottom_equals_cavity_top", "geometry_pass"]} for r in rows])
    write_csv(OUT / "r2_4d6_source_position_audit.csv", [{k: r[k] for k in ["case_id", "source_x_um", "source_y_nm", "dipole_orientation", "theta_requested_deg", "phi_requested_deg", "theta_readback_deg", "phi_readback_deg", "physical_x_dipole_verified", "source_inside_cavity_x", "source_inside_cavity_y", "source_inside_cavity"]} for r in rows])
    write_csv(OUT / "r2_4d6_monitor_audit.csv", [{k: r[k] for k in ["case_id", "monitor_x_span_um", "monitor_y_um", "monitor_y_to_top_pml_um", "monitor_y_above_top_structure_um", "monitor_above_top_dbr", "monitor_in_homogeneous_air", "monitor_inside_pml"]} for r in rows])

    checklist = f"""
# R2-4D6 GUI Inspection Checklist

Open only the nine setup-only FSPs under `runtime_fsp/`.

Confirm for every file:

- Candidate is `{CANDIDATE_ID}` only.
- Source is x-oriented only: theta=90 deg, phi=0 deg.
- Source x position matches the manifest row.
- Source is inside the 3.0 um GaN/device cavity aperture and at y={CAVITY_SPACER_NM/2:g} nm.
- Top DBR group, bottom reflector group, and GaN cavity group exist.
- Top DBR bottom touches GaN cavity top; bottom DBR top touches GaN cavity bottom.
- Monitor is above top DBR, in air, and outside PML.
- No y dipole, z_outofplane dipole, broadband case, backup candidate, or old failed candidate is present.
- Do not solve during GUI inspection.
"""
    write_text(OUT / "r2_4d6_gui_inspection_checklist.md", checklist)

    summary = f"""
# R2-4D6 Setup-Only FSP Generation for D5_BASE_13461

Generated nine setup-only 2D FDTD FSP files for GUI inspection.

- Candidate: `{CANDIDATE_ID}` only.
- Role: `{ROLE}`.
- Wavelength: {WAVELENGTH_NM:g} nm.
- Top pairs: {TOP_PAIR_COUNT}; bottom pairs: {BOTTOM_PAIR_COUNT}.
- Cavity spacer: {CAVITY_SPACER_NM:g} nm.
- Top termination: {TOP_TERMINATION_NM:g} nm; bottom termination: {BOTTOM_TERMINATION_NM:g} nm.
- Dipole cases: x-oriented only, theta=90 deg, phi=0 deg.
- x positions: {', '.join(str(x) for x in X_POSITIONS_UM)} um.
- FSP count: {len(rows)} / 9.
- Setup only: true.
- Solved: false.
- No far-field extraction, no `.ldf`, no `.mat`, no `.h5`, no raw monitor files.

Runtime FSP files are in `outputs/r2_4d6_setup_only_fsp_d5_primary/runtime_fsp/` and must remain untracked/unstaged.
"""
    write_text(OUT / "r2_4d6_summary.md", summary)
    write_text(OUT / "r2_4d6_next_steps.md", """
# R2-4D6 Next Steps

1. Manually inspect all nine setup-only FSPs in the Lumerical GUI.
2. Confirm source positions, x-dipole orientation, DBR/GaN interfaces, and monitor placement.
3. If GUI inspection passes, approve a separate R2-4D7 x-line x-dipole FDTD solve stage.
4. Do not solve or commit runtime FSP files in this stage.
""")
    debug = {
        "stage": STAGE,
        "candidate_id": CANDIDATE_ID,
        "d5a_summary_exists": (D5A / "r2_4d5a_summary.md").exists(),
        "expected_fsp_count": 9,
        "actual_fsp_count": len(rows),
        "all_geometry_pass": all(bool(r["geometry_pass"]) for r in rows),
        "setup_only": True,
        "solved": False,
        "no_heavy_result_files_expected": True,
        "top_layers": stacks["top"],
        "bottom_layers": stacks["bottom"],
    }
    (OUT / "r2_4d6_debug.json").write_text(json.dumps(debug, indent=2), encoding="utf-8")
    update_index()


def check_no_result_files() -> list[str]:
    bad = []
    for ext in ("*.ldf", "*.mat", "*.h5"):
        bad += [str(p) for p in OUT.rglob(ext)]
    return bad


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if not (D5A / "r2_4d5a_summary.md").exists():
        raise RuntimeError("D5A outputs are missing")
    stacks = load_layers()
    rows = build_all(stacks)
    write_reports(rows, stacks)
    bad = check_no_result_files()
    if bad:
        raise RuntimeError("forbidden result files created: " + ", ".join(bad))
    print(json.dumps({"output": str(OUT), "runtime_fsp_dir": str(RUNTIME_FSP), "fsp_count": len(rows), "all_geometry_pass": all(bool(r["geometry_pass"]) for r in rows)}, indent=2))
    for row in rows:
        print(row["fsp_path"])


if __name__ == "__main__":
    main()
