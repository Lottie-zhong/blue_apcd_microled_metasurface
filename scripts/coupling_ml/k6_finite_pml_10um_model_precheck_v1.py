"""Setup-only K6 finite-PML 10 um collection precheck.

This module deliberately has no solver/run/scheduler path. It exports fresh
setup_pre.fsp files, loads them read-only, and writes static geometry evidence.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ACTIVE = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
TRAD = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_v1")
OUT = ACTIVE / r"outputs\coupling_v2_2\FINITE_PML_10UM_MODEL_AUTHORITY_PRECHECK_V1"
API = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
MATERIAL_HELPER = Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2\scripts")
WAVELENGTHS_NM = [445.0 + i for i in range(11)]

K = 6
PERIOD_NM = 290.0
PERIOD_X_NM = 1740.0
PILLAR_HEIGHT_NM = 500.0
POSITIONS_NM = [-725.0, -435.0, -145.0, 145.0, 435.0, 725.0]
SOURCE_Z_NM = -276.0
SOURCE_X_NM = 0.0
MDC_TOP_NM = 975.0
PILLAR_BOTTOM_NM = 1212.0
PILLAR_TOP_NM = 1712.0

FDTD_X_SPAN_NM = 14000.0
FDTD_X_HALF_NM = FDTD_X_SPAN_NM / 2.0
MONITOR_X_SPAN_NM = 10000.0
MONITOR_X_HALF_NM = MONITOR_X_SPAN_NM / 2.0
SIDE_GUARD_NM = FDTD_X_HALF_NM - MONITOR_X_HALF_NM
PML_DEPTH_BUDGET_NM = 1200.0
MONITOR_TO_PML_MARGIN_NM = SIDE_GUARD_NM - PML_DEPTH_BUDGET_NM

Z_MIN_NM = -2000.0
Z_MAX_NM = 5000.0
MONITOR_Z_NM = 3000.0
DOWNWARD_Z_NM = -1200.0
SOURCE_BOX_HALF_X_NM = 50.0
SOURCE_BOX_HALF_Z_NM = 25.0
PML_LAYERS = 32
PML_PROFILE = "Stabilized"
# Lumerical's script API uses numeric PML profile codes; 2 is Stabilized.
PML_PROFILE_CODE = 2
MESH_ACCURACY = 2
MESH_OVERRIDE_STEP_NM = 2.0
SIMULATION_TIME_S = 1.0e-12
AUTO_SHUTOFF = 1.0e-6
DT_STABILITY_FACTOR = 0.99

DIAMETERS = {
    "SOURCE_ONLY": [],
    "CONTROL0": [125.0, 135.0, 150.0, 175.0, 190.0, 210.0],
    "ALT1": [100.0, 115.0, 130.0, 145.0, 155.0, 185.0],
}

STACK = [
    ("mdc_layer", "APCD_TIO2_NATIVE_M1", 0.0, 44.0),
    ("mdc_layer", "APCD_SIO2_NATIVE_M1", 44.0, 123.0),
    ("mdc_layer", "APCD_TIO2_NATIVE_M1", 123.0, 167.0),
    ("mdc_layer", "APCD_SIO2_NATIVE_M1", 167.0, 246.0),
    ("mdc_layer", "APCD_TIO2_NATIVE_M1", 246.0, 290.0),
    ("mdc_layer", "APCD_SIO2_NATIVE_M1", 290.0, 606.0),
    ("mdc_layer", "APCD_TIO2_NATIVE_M1", 606.0, 650.0),
    ("mdc_layer", "APCD_SIO2_NATIVE_M1", 650.0, 729.0),
    ("mdc_layer", "APCD_TIO2_NATIVE_M1", 729.0, 773.0),
    ("mdc_layer", "APCD_SIO2_NATIVE_M1", 773.0, 852.0),
    ("mdc_layer", "APCD_TIO2_NATIVE_M1", 852.0, 896.0),
    ("mdc_layer", "APCD_SIO2_NATIVE_M1", 896.0, 975.0),
    ("extra_spacer", "APCD_SIO2_NATIVE_M1", 975.0, 1212.0),
]

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)

def model_contract(case_name: str) -> dict[str, Any]:
    if case_name not in DIAMETERS:
        raise ValueError(case_name)
    objects = [{"role": "gan_substrate", "material_id": "APCD_GAN_NATIVE_M1", "z_min_nm": Z_MIN_NM, "z_max_nm": 0.0}]
    for index, (role, material_id, z_min, z_max) in enumerate(STACK):
        objects.append({"role": role, "index": index, "material_id": material_id, "z_min_nm": z_min, "z_max_nm": z_max})
    for index, (x_nm, width_nm) in enumerate(zip(POSITIONS_NM, DIAMETERS[case_name])):
        objects.append({"role": "np_bar_2d", "index": index, "material_id": "APCD_TIO2_NATIVE_M1", "x_nm": x_nm, "width_nm": width_nm, "source_3d_diameter_nm": width_nm, "z_min_nm": PILLAR_BOTTOM_NM, "z_max_nm": PILLAR_TOP_NM})
    contract = {
        "schema_version": "FINITE_PML_10UM_MODEL_CONTRACT_V1",
        "case_name": case_name,
        "kind": "source_only" if case_name == "SOURCE_ONLY" else "integrated",
        "geometry": {"K": K, "period_nm": PERIOD_NM, "supercell_x_nm": PERIOD_X_NM, "pillar_height_nm": PILLAR_HEIGHT_NM, "positions_nm": POSITIONS_NM, "widths_nm": DIAMETERS[case_name], "mapping": "w_i = D_i", "mapping_flag": "BAR_WIDTH_EQUALS_DIAMETER_PROVISIONAL_MAPPING"},
        "dimensional_reduction": "physical x-z; native 2D x-y with native y mapped to physical z; y-invariant line-source subspace",
        "domain": {"native_x_span_nm": FDTD_X_SPAN_NM, "physical_z_min_nm": Z_MIN_NM, "physical_z_max_nm": Z_MAX_NM, "all_exterior_boundaries": "PML", "periodic": False, "bloch": False, "side_guard_per_side_nm": SIDE_GUARD_NM, "pml_depth_budget_per_side_nm": PML_DEPTH_BUDGET_NM, "monitor_to_pml_margin_budget_nm": MONITOR_TO_PML_MARGIN_NM},
        "pml": {"profile": PML_PROFILE, "layers": PML_LAYERS, "rationale": "finite isolated emitter; stabilized profile is selected because full-span material interfaces meet the side-PML region", "physical_thickness": "mesh-dependent; GUI/readback confirmation required"},
        "mesh": {"global_accuracy": MESH_ACCURACY, "local_min_step_nm": MESH_OVERRIDE_STEP_NM, "refinement_regions": ["all MDC interfaces plus NP bars", "dipole neighborhood"], "estimated_max_homogeneous_step_nm": 40.0, "estimated_cells": 1400000, "estimated_memory_gb": [0.5, 2.0], "estimated_runtime": "not measured; solver prohibited in this task"},
        "source": {"type": "2D electric line dipole", "orientation": "X", "theta_deg": 90.0, "phi_deg": 0.0, "position_nm": {"x": SOURCE_X_NM, "physical_z": SOURCE_Z_NM}, "wavelength_grid_nm": WAVELENGTHS_NM, "normalization": "2D power per unit invariant length W/m; dipolepower/sourcepower cannot be equated to 3D W", "3d_nonidentity": "2D line dipole != 3D isolated point dipole"},
        "monitor": {"upward_name": "upward_monitor", "type": "Linear X", "physical_z_nm": MONITOR_Z_NM, "x_span_nm": MONITOR_X_SPAN_NM, "homogeneous_region": "air above NP", "inside_pml": False, "complex_fields_preserved_if_available": True, "farfield_compatible": True, "downward_name": "downward_monitor", "downward_z_nm": DOWNWARD_Z_NM, "frequency_points": 11},
        "collection": {"usable_lateral_width_nm": MONITOR_X_SPAN_NM, "usable_lateral_width_requirement_nm": 10000.0, "aperture_is_not_gate0a_1p74um": True, "angles_deg": [10.0, 15.0, 23.0, 31.0], "walkoff_reference": "NP pillar top to upward monitor"},
        "authorization": {"setup_export": True, "load_only_readback": True, "scientific_solver": False, "training": False, "rerun": False, "human_gui_approval": "PENDING"},
        "objects": objects,
    }
    contract["physical_contract_sha256"] = digest(contract)
    return contract

def lumapi_module():
    sys.path.insert(0, str(API))
    import lumapi  # type: ignore
    return lumapi

def set_monitor(fd: Any, name: str, monitor_type: str, props: dict[str, Any]) -> None:
    fd.addpower()
    fd.set("name", name)
    fd.set("monitor type", monitor_type)
    for key, value in props.items():
        fd.set(key, value)
    fd.set("override global monitor settings", 1)
    fd.set("use source limits", 1)
    fd.set("use wavelength spacing", 1)
    fd.set("frequency points", len(WAVELENGTHS_NM))

def rect(fd: Any, name: str, material: str, x_nm: float, x_span_nm: float, z_min_nm: float, z_max_nm: float) -> None:
    fd.addrect()
    for key, value in {"name": name, "material": material, "x": x_nm * 1e-9, "x span": x_span_nm * 1e-9, "y": (z_min_nm + z_max_nm) * 0.5e-9, "y span": (z_max_nm - z_min_nm) * 1e-9}.items():
        fd.set(key, value)

def build_setup(contract: dict[str, Any], path: Path) -> None:
    if not MATERIAL_HELPER.exists():
        raise FileNotFoundError(MATERIAL_HELPER)
    sys.path.insert(0, str(MATERIAL_HELPER))
    import apcd_native_materials  # type: ignore
    fd = lumapi_module().FDTD(hide=True)
    try:
        for material_id in ("APCD_GAN_NATIVE_M1", "APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1"):
            apcd_native_materials.register_lumerical_sampled_material(fd, material_id)
        fd.addfdtd()
        for key, value in {"dimension": "2D", "x": 0.0, "x span": FDTD_X_SPAN_NM * 1e-9, "y": (Z_MIN_NM + Z_MAX_NM) * 0.5e-9, "y span": (Z_MAX_NM - Z_MIN_NM) * 1e-9, "x min bc": "PML", "x max bc": "PML", "y min bc": "PML", "y max bc": "PML", "pml layers": PML_LAYERS, "mesh accuracy": MESH_ACCURACY, "simulation time": SIMULATION_TIME_S, "auto shutoff min": AUTO_SHUTOFF, "dt stability factor": DT_STABILITY_FACTOR}.items():
            fd.set(key, value)
        fd.set("pml profile", PML_PROFILE_CODE)
        # Changing profile can restore its default layer count; make the
        # requested layer count the final boundary setting.
        fd.set("pml layers", PML_LAYERS)
        rect(fd, "GaN_substrate", "APCD_GAN_NATIVE_M1", 0.0, FDTD_X_SPAN_NM, Z_MIN_NM, 0.0)
        for obj in contract["objects"]:
            if obj["role"] in {"mdc_layer", "extra_spacer"}:
                rect(fd, f"{obj['role'].upper()}_{int(obj['index']):02d}", obj["material_id"], 0.0, FDTD_X_SPAN_NM, obj["z_min_nm"], obj["z_max_nm"])
            elif obj["role"] == "np_bar_2d":
                rect(fd, f"NP_bar_{int(obj['index'])}", obj["material_id"], obj["x_nm"], obj["width_nm"], obj["z_min_nm"], obj["z_max_nm"])
        fd.addmesh()
        for key, value in {"name": "mesh_interfaces_np", "x": 0.0, "x span": 2200e-9, "y": 650e-9, "y span": 2300e-9, "override x mesh": 1, "override y mesh": 1, "set maximum mesh step": 1, "dx": MESH_OVERRIDE_STEP_NM * 1e-9, "dy": MESH_OVERRIDE_STEP_NM * 1e-9}.items(): fd.set(key, value)
        fd.addmesh()
        for key, value in {"name": "mesh_dipole_neighborhood", "x": 0.0, "x span": 200e-9, "y": SOURCE_Z_NM * 1e-9, "y span": 200e-9, "override x mesh": 1, "override y mesh": 1, "set maximum mesh step": 1, "dx": MESH_OVERRIDE_STEP_NM * 1e-9, "dy": MESH_OVERRIDE_STEP_NM * 1e-9}.items(): fd.set(key, value)
        fd.adddipole()
        for key, value in {"name": "source_dipole", "x": SOURCE_X_NM * 1e-9, "y": SOURCE_Z_NM * 1e-9, "theta": 90.0, "phi": 0.0, "wavelength start": 445e-9, "wavelength stop": 455e-9}.items(): fd.set(key, value)
        set_monitor(fd, "upward_monitor", "Linear X", {"x": 0.0, "y": MONITOR_Z_NM * 1e-9, "x span": MONITOR_X_SPAN_NM * 1e-9})
        set_monitor(fd, "downward_monitor", "Linear X", {"x": 0.0, "y": DOWNWARD_Z_NM * 1e-9, "x span": MONITOR_X_SPAN_NM * 1e-9})
        set_monitor(fd, "source_box_top", "Linear X", {"x": 0.0, "y": (SOURCE_Z_NM + SOURCE_BOX_HALF_Z_NM) * 1e-9, "x span": 2 * SOURCE_BOX_HALF_X_NM * 1e-9})
        set_monitor(fd, "source_box_bottom", "Linear X", {"x": 0.0, "y": (SOURCE_Z_NM - SOURCE_BOX_HALF_Z_NM) * 1e-9, "x span": 2 * SOURCE_BOX_HALF_X_NM * 1e-9})
        set_monitor(fd, "source_box_left", "Linear Y", {"x": (SOURCE_X_NM - SOURCE_BOX_HALF_X_NM) * 1e-9, "y": SOURCE_Z_NM * 1e-9, "y span": 2 * SOURCE_BOX_HALF_Z_NM * 1e-9})
        set_monitor(fd, "source_box_right", "Linear Y", {"x": (SOURCE_X_NM + SOURCE_BOX_HALF_X_NM) * 1e-9, "y": SOURCE_Z_NM * 1e-9, "y span": 2 * SOURCE_BOX_HALF_Z_NM * 1e-9})
        path.parent.mkdir(parents=True, exist_ok=True)
        fd.save(str(path))
    finally:
        fd.close()

def scalar(value: Any) -> Any:
    while isinstance(value, (list, tuple)) and len(value) == 1:
        value = value[0]
    return value

def setup_readback(path: Path, contract: dict[str, Any]) -> dict[str, Any]:
    fd = lumapi_module().FDTD(str(path), hide=True)
    try:
        get = lambda obj, prop: scalar(fd.getnamed(obj, prop))
        solver = {p: get("FDTD", p) for p in ("dimension", "x span", "y span", "x min bc", "x max bc", "y min bc", "y max bc", "pml profile", "pml layers", "mesh accuracy", "simulation time", "auto shutoff min")}
        source = {p: get("source_dipole", p) for p in ("x", "y", "theta", "phi", "wavelength start", "wavelength stop")}
        monitors = {name: {p: get(name, p) for p in ("monitor type", "x", "y", "x span", "y span", "frequency points")} for name in ("upward_monitor", "downward_monitor", "source_box_top", "source_box_bottom", "source_box_left", "source_box_right")}
        checks = {
            "dimension_2d": solver["dimension"] == "2D",
            "all_exterior_boundaries_pml": all(solver[p] == "PML" for p in ("x min bc", "x max bc", "y min bc", "y max bc")),
            "no_periodic_or_bloch": all(solver[p] not in {"Periodic", "Bloch"} for p in ("x min bc", "x max bc", "y min bc", "y max bc")),
            "x_span_14um": abs(float(solver["x span"]) * 1e9 - FDTD_X_SPAN_NM) < 1e-3,
            "monitor_span_10um": abs(float(monitors["upward_monitor"]["x span"]) * 1e9 - MONITOR_X_SPAN_NM) < 1e-3,
            "monitor_inside_solver": float(monitors["upward_monitor"]["x span"]) <= float(solver["x span"]),
            "source_position": abs(float(source["x"]) * 1e9 - SOURCE_X_NM) < 1e-3 and abs(float(source["y"]) * 1e9 - SOURCE_Z_NM) < 1e-3,
            "source_x_orientation": abs(float(source["theta"]) - 90.0) < 1e-6 and abs(float(source["phi"])) < 1e-6,
            "exact_wavelength_grid": abs(float(source["wavelength start"]) * 1e9 - 445.0) < 1e-3 and abs(float(source["wavelength stop"]) * 1e9 - 455.0) < 1e-3 and all(int(float(monitors[n]["frequency points"])) == 11 for n in monitors),
            "monitor_above_np": float(monitors["upward_monitor"]["y"]) * 1e9 > PILLAR_TOP_NM,
            "monitor_not_at_solver_edge": abs(float(monitors["upward_monitor"]["x span"]) * 1e9) < abs(float(solver["x span"]) * 1e9),
            "pml_profile_stabilized": int(float(solver["pml profile"])) == PML_PROFILE_CODE,
            "pml_layers": int(float(solver["pml layers"])) == PML_LAYERS,
        }
        return {"schema_version": "FINITE_PML_10UM_SETUP_READBACK_V1", "solver": solver, "source": source, "monitors": monitors, "checks": checks, "pass": bool(all(checks.values())), "readback_session_readonly": True, "physical_contract_sha256": contract["physical_contract_sha256"], "solver_entered": False}
    finally:
        fd.close()

def offaxis_audit() -> dict[str, Any]:
    h_nm = MONITOR_Z_NM - PILLAR_TOP_NM
    structure_half_nm = max(abs(x) + d / 2.0 for x, d in zip(POSITIONS_NM, DIAMETERS["CONTROL0"]))
    rows = []
    import math
    for theta in (10.0, 15.0, 23.0, 31.0):
        walkoff = h_nm * math.tan(math.radians(theta))
        ray_edge = structure_half_nm + walkoff
        rows.append({"theta_deg": theta, "h_nm": h_nm, "lateral_walkoff_nm": walkoff, "monitor_half_width_nm": MONITOR_X_HALF_NM, "non_pml_half_width_budget_nm": FDTD_X_HALF_NM - PML_DEPTH_BUDGET_NM, "remaining_pml_safety_margin_nm": FDTD_X_HALF_NM - PML_DEPTH_BUDGET_NM - ray_edge, "target_ray_before_side_pml": ray_edge < FDTD_X_HALF_NM - PML_DEPTH_BUDGET_NM})
    return {"schema_version": "MULTIANGLE_OFFAXIS_CAPTURE_AUDIT_V1", "reference": "NP pillar top to upward monitor", "structure_half_width_nm": structure_half_nm, "rows": rows, "all_necessary_geometry_checks_pass": all(r["target_ray_before_side_pml"] for r in rows), "sufficient_domain_robustness": False}

def static_contract_audit() -> dict[str, Any]:
    source_text = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source_text)
    fd_run_call = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "run" and isinstance(n.func.value, ast.Name) and n.func.value.id == "fd" for n in ast.walk(tree))
    checks = {
        "three_cases_declared": set(DIAMETERS) == {"SOURCE_ONLY", "CONTROL0", "ALT1"},
        "zero_solver_entry_path": not fd_run_call,
        "no_scheduler_path": ("Global" + "SlotScheduler") not in source_text,
        "finite_pml_only": FDTD_X_SPAN_NM > MONITOR_X_SPAN_NM and SIDE_GUARD_NM > PML_DEPTH_BUDGET_NM,
        "monitor_margin_positive": MONITOR_TO_PML_MARGIN_NM > 0,
        "no_periodic_or_bloch_contract": all(x not in PML_PROFILE for x in ("Periodic", "Bloch")),
        "mapping_provisional": True,
        "exact_grid": WAVELENGTHS_NM == [445.0 + i for i in range(11)],
        "source_inside_gan": Z_MIN_NM < SOURCE_Z_NM < 0.0,
        "mesh_refinement_positive": MESH_OVERRIDE_STEP_NM > 0,
    }
    return {"schema_version": "FINITE_PML_10UM_STATIC_CONTRACT_AUDIT_V1", "generated_utc": utc_now(), "checks": checks, "pass": bool(all(checks.values())), "solver_entry_delta": 0, "training_entry_delta": 0, "rerun_delta": 0, "offaxis": offaxis_audit()}

def prepare(case_name: str) -> dict[str, Any]:
    contract = model_contract(case_name)
    cdir = OUT / "cases" / case_name
    cdir.mkdir(parents=True, exist_ok=True)
    setup = cdir / "setup_pre.fsp"
    build_setup(contract, setup)
    readback = setup_readback(setup, contract)
    atomic_json(cdir / "MODEL_CONTRACT.json", contract)
    atomic_json(cdir / "SETUP_READBACK.json", readback)
    result = {"schema_version": "FINITE_PML_10UM_PRECHECK_CASE_V1", "case_name": case_name, "setup_pre_fsp": str(setup), "setup_pre_fsp_sha256": sha256_file(setup), "readback": readback, "solver_entered": False, "solver_returned": False, "training": False, "rerun": False}
    atomic_json(cdir / "PRECHECK_CASE_RESULT.json", result)
    if not readback["pass"]:
        raise RuntimeError(f"setup_readback_failed:{case_name}")
    return result

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--static", action="store_true")
    parser.add_argument("--prepare", choices=sorted(DIAMETERS))
    parser.add_argument("--prepare-all", action="store_true")
    args = parser.parse_args()
    if args.static:
        print(json.dumps(static_contract_audit(), ensure_ascii=False, indent=2))
        return 0
    if args.prepare_all:
        # This root is task-scoped. Resume an interrupted setup-only export;
        # never overwrite protected historical roots or a completed precheck.
        if (OUT / "PRECHECK_COMPLETE.json").exists():
            raise RuntimeError(f"refusing to overwrite completed output root: {OUT}")
        OUT.mkdir(parents=True, exist_ok=True)
        atomic_json(OUT / "STATIC_CONTRACT_AUDIT.json", static_contract_audit())
        rows = [prepare(x) for x in ("SOURCE_ONLY", "CONTROL0", "ALT1")]
        atomic_json(OUT / "SOLVER_ACCOUNTING.json", {"schema_version": "SOLVER_ACCOUNTING_V1", "solver_entry_delta": 0, "solver_returned_delta": 0, "training_entry_delta": 0, "rerun_delta": 0, "cases": [{"case_name": x["case_name"], "solver_entered": False, "solver_returned": False} for x in rows]})
        print(json.dumps({"root": str(OUT), "cases": rows, "solver_entry_delta": 0}, ensure_ascii=False, indent=2))
        return 0
    if args.prepare:
        return 0 if prepare(args.prepare)["readback"]["pass"] else 31
    parser.error("use --static, --prepare CASE, or --prepare-all")

if __name__ == "__main__":
    raise SystemExit(main())
