from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from apcd_coupling.incident_state import IncidentState, transversality_residual
from apcd_coupling.broadband_source_contract import fixed_ux_target_rows, validate_fixed_ux_rows
from apcd_coupling.joint_case_schema import canonical_hash
from apcd_coupling.joint_stack_builder import build_joint_case

DEFAULT_CONFIG = ROOT / "configs/coupling/stage_a_polarization_angle_broadband_445_455_v1.json"
DEFAULT_OUTPUT_ROOT = ROOT / "outputs/coupling/stage_a_polarization_angle_broadband_445_455_v1"
DEFAULT_HELPER_ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2")
LUMAPI_ROOT = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
MDC_COMMIT = "489b54e43bbf2c08ce030a945b9d4b70ee7550f2"
NP_COMMIT = "7a8588f6b5a1c96d88813f60406d418b488135fd"
CALIBRATION_AIR_ANGLE_DEG = 5.0
REAL_KX_TOLERANCE = 1e-9
GRID_TOLERANCE_NM = 1e-6


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False, default=str) + "\n", encoding="utf-8")


def scalar(value: Any) -> Any:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, (list, tuple)) and len(value) == 1:
        return scalar(value[0])
    return value


def real_scalar(value: Any) -> float:
    value = scalar(value)
    if isinstance(value, complex):
        value = value.real
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"non-finite scalar: {value!r}")
    return result


def complex_scalar(value: Any) -> complex:
    return complex(scalar(value))


def jsonable(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return jsonable(value.tolist())
    if isinstance(value, complex):
        return {"real": float(value.real), "imag": float(value.imag)}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    return value


def one(fdtd: Any, object_name: str, prop: str) -> Any:
    return scalar(fdtd.getnamed(object_name, prop))


def maybe_one(fdtd: Any, object_name: str, prop: str) -> Any:
    try:
        return one(fdtd, object_name, prop)
    except Exception:
        return None


def material_names(fdtd: Any) -> list[str]:
    raw = scalar(fdtd.getmaterial())
    if isinstance(raw, str):
        return [item.strip() for item in raw.splitlines() if item.strip()]
    return [str(item).strip() for item in raw if str(item).strip()]


def load_material_helper(helper_root: Path):
    sys.path.insert(0, str(helper_root / "scripts"))
    return importlib.import_module("apcd_native_materials")


def git_head() -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()


def add_rect(fdtd: Any, name: str, x_span_nm: float, y_span_nm: float, z_min_nm: float, z_max_nm: float, material: str) -> None:
    fdtd.addrect()
    fdtd.set("name", name)
    fdtd.set("x span", x_span_nm * 1e-9)
    fdtd.set("y span", y_span_nm * 1e-9)
    fdtd.set("z min", z_min_nm * 1e-9)
    fdtd.set("z max", z_max_nm * 1e-9)
    fdtd.set("material", material)


def add_monitor(fdtd: Any, name: str, z_nm: float, x_span_nm: float, y_span_nm: float) -> None:
    fdtd.addpower()
    fdtd.set("name", name)
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", x_span_nm * 1e-9)
    fdtd.set("y span", y_span_nm * 1e-9)
    fdtd.set("z", z_nm * 1e-9)


def build_geometry(fdtd: Any, case: dict[str, Any], config: dict[str, Any], state: IncidentState) -> tuple[float, float]:
    x_span_nm = float(case["np_candidate"]["period_x_nm"])
    y_span_nm = float(case["np_candidate"]["period_y_nm"])
    pillar_top_nm = float(case["coordinates"]["np_pillar_top_nm"])
    monitor_z_nm = pillar_top_nm + 400.0
    fdtd.addfdtd()
    for prop, value in (
        ("dimension", "3D"), ("x span", x_span_nm * 1e-9), ("y span", y_span_nm * 1e-9),
        ("z min", -600e-9), ("z max", (monitor_z_nm + 300.0) * 1e-9),
        ("x min bc", "Periodic"), ("x max bc", "Periodic"), ("y min bc", "Periodic"), ("y max bc", "Periodic"),
        ("z min bc", "PML"), ("z max bc", "PML"), ("mesh accuracy", 2), ("pml layers", 8),
        ("simulation time", 1e-12), ("auto shutoff min", 1e-5), ("dt stability factor", 0.99),
    ):
        fdtd.set(prop, value)
    substrate = next(item for item in case["objects"] if item["role"] == "gan_substrate")
    add_rect(fdtd, "GaN_substrate", x_span_nm, y_span_nm, substrate["z_min_nm"], substrate["z_max_nm"], substrate["material_id"])
    for item in case["objects"]:
        if item["role"] in {"mdc_layer", "extra_spacer", "interface_support_layer"}:
            index = int(item.get("index", 1))
            add_rect(fdtd, f"{item['role']}_{index:02d}", x_span_nm, y_span_nm, item["z_min_nm"], item["z_max_nm"], item["material_id"])
    for item in case["objects"]:
        if item["role"] != "np_pillar":
            continue
        fdtd.addcircle()
        fdtd.set("name", f"NP_pillar_{int(item['index'])}")
        fdtd.set("x", item["x_nm"] * 1e-9)
        fdtd.set("y", item["y_nm"] * 1e-9)
        fdtd.set("radius", item["diameter_nm"] * 0.5e-9)
        fdtd.set("z min", item["z_min_nm"] * 1e-9)
        fdtd.set("z max", item["z_max_nm"] * 1e-9)
        fdtd.set("material", item["material_id"])
    fdtd.addplane()
    fdtd.set("name", "source_incident")
    for prop, value in (
        ("injection axis", "z-axis"), ("direction", "Forward"), ("plane wave type", "Bloch/periodic"),
        ("x span", x_span_nm * 1e-9), ("y span", y_span_nm * 1e-9), ("z", -250e-9),
        ("wavelength start", float(config["wavelength_start_nm"]) * 1e-9),
        ("wavelength stop", float(config["wavelength_stop_nm"]) * 1e-9),
        ("angle phi", 0.0), ("polarization angle", state.polarization_angle_deg), ("angle theta", 0.0),
    ):
        fdtd.set(prop, value)
    for name, z_nm in (("reflection_monitor", -300.0), ("transmission_monitor", monitor_z_nm), ("order_monitor", monitor_z_nm), ("field_450_monitor", monitor_z_nm)):
        add_monitor(fdtd, name, z_nm, x_span_nm, y_span_nm)
    fdtd.setglobalmonitor("use source limits", 1)
    fdtd.setglobalmonitor("use wavelength spacing", 1)
    fdtd.setglobalmonitor("frequency points", int(config["frequency_points"]))
    return x_span_nm, monitor_z_nm


def calibrate_n_eff(fdtd: Any, state: IncidentState, x_span_nm: float, wavelength_nm: float, effective_n_eff_override: float | None = None) -> dict[str, float]:
    fdtd.setnamed("source_incident", "plane wave type", "Bloch/periodic")
    fdtd.setnamed("source_incident", "angle theta", CALIBRATION_AIR_ANGLE_DEG)
    fdtd.setnamed("FDTD", "x min bc", "Bloch")
    fdtd.setnamed("FDTD", "x max bc", "Bloch")
    fdtd.setnamed("FDTD", "y min bc", "Periodic")
    fdtd.setnamed("FDTD", "y max bc", "Periodic")
    fdtd.setnamed("FDTD", "bloch units", "bandstructure")
    fdtd.setnamed("FDTD", "set based on source angle", 1)
    kx_band = real_scalar(one(fdtd, "FDTD", "kx"))
    ux_calibration = math.sin(math.radians(CALIBRATION_AIR_ANGLE_DEG))
    ux_from_fdtd = kx_band * wavelength_nm / x_span_nm
    n_eff = ux_from_fdtd / ux_calibration
    if not math.isfinite(n_eff) or n_eff <= 0.0:
        raise RuntimeError(f"invalid lossy-GaN source calibration n_eff={n_eff}")
    result = {"source_calibration_air_angle_deg": CALIBRATION_AIR_ANGLE_DEG, "source_calibration_kx_bandstructure": kx_band, "source_calibration_ux_from_fdtd": ux_from_fdtd, "source_calibration_n_eff": n_eff}
    if effective_n_eff_override is not None:
        result["source_calibration_n_eff_observed_before_override"] = n_eff
        result["source_calibration_n_eff_override"] = float(effective_n_eff_override)
        result["source_calibration_n_eff"] = float(effective_n_eff_override)
        result["source_calibration_method"] = "diagnostic BFAST transmitted m=0 calibration override; requires explicit replay authorization"
    else:
        result["source_calibration_method"] = "reopened Bloch bandstructure calibration"
    return result


def configure_bfast(fdtd: Any, state: IncidentState, calibration: dict[str, float]) -> dict[str, Any]:
    n_eff = float(calibration["source_calibration_n_eff"])
    internal_theta = 0.0 if abs(state.ux) <= 1e-15 else math.degrees(math.asin(max(-1.0, min(1.0, state.ux / n_eff))))
    fdtd.setnamed("source_incident", "plane wave type", "BFAST")
    fdtd.setnamed("source_incident", "angle theta", internal_theta)
    fdtd.setnamed("source_incident", "angle phi", 0.0)
    fdtd.setnamed("source_incident", "polarization angle", state.polarization_angle_deg)
    fdtd.setnamed("FDTD", "bfast alpha", 1.0)
    fdtd.setnamed("FDTD", "x min bc", "Periodic")
    fdtd.setnamed("FDTD", "x max bc", "Periodic")
    fdtd.setnamed("FDTD", "y min bc", "Periodic")
    fdtd.setnamed("FDTD", "y max bc", "Periodic")
    return {
        "target_theta_air_deg": float(state.theta_air_in_deg),
        "target_ux": float(state.ux),
        "target_uy": float(state.uy),
        "source_internal_theta_deg": float(internal_theta),
        "source_phi_deg": 0.0,
        "source_medium_identity": "APCD_GAN_NATIVE_M1",
        "source_implementation": "BFAST plane wave",
        "boundary_implementation": "BFAST built-in transverse x boundary with periodic y and PML z",
        "bfast_alpha": 1.0,
        "sign_convention": "positive real kx is physical +x; negative real kx is physical -x",
        "reference_medium": "Air",
        "angle_convention_id": "air_side_far_field_conserved_real_kx_v1",
        "real_kx_rule": "real_kx(lambda)=(2*pi/lambda)*ux",
        "per_wavelength_target_real_kx": [2.0 * math.pi / (float(wavelength) * 1e-9) * state.ux for wavelength in (445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455)],
        "source_theta_not_air_angle": abs(state.ux) == 0.0 or abs(internal_theta - state.theta_air_in_deg) > 1e-12,
        **calibration,
    }


def source_angle_readback(fdtd: Any) -> dict[str, Any]:
    try:
        fdtd.eval("broadband_source_angle_probe=getsourceangle('source_incident',linspace(c/455e-9,c/445e-9,11));")
        value = fdtd.getv("broadband_source_angle_probe")
        values = np.asarray(value, dtype=float).reshape(-1).tolist()
        return {"available": True, "values_deg": values, "constant": bool(values and max(values) - min(values) <= 1e-9)}
    except Exception as exc:
        return {"available": False, "constant": False, "error": f"{type(exc).__name__}: {exc}"}


def build_one(case_spec: dict[str, Any], fixture: dict[str, Any], config: dict[str, Any], output_dir: Path, helper_root: Path) -> dict[str, Any]:
    wavelengths = [float(value) for value in config["exact_wavelength_grid_nm"]]
    if wavelengths != list(np.arange(445.0, 456.0, 1.0)):
        raise ValueError("broadband grid must be exact 445..455 nm at 1 nm")
    state = IncidentState(wavelength_nm=450.0, ux=float(case_spec["ux"]), uy=float(case_spec["uy"]), polarization_branch=str(case_spec["polarization_branch"]), theta_air_in_deg=float(case_spec["theta_air_in_deg"]), angle_convention_id="air_side_far_field_conserved_real_kx_v1")
    case = build_joint_case(fixture["mdc_candidate"], fixture["np_candidate"], 237.0, 450.0, state.linear_polarization, state.ux, case_id=case_spec["case_id"], control_group="POL_ANGLE_BROADBAND", incident_state=state.to_dict())
    case.update({"source_contract_id": config["source_contract_id"], "source_wavelength_start_nm": config["wavelength_start_nm"], "source_wavelength_stop_nm": config["wavelength_stop_nm"], "frequency_points": config["frequency_points"], "exact_wavelength_grid_nm": wavelengths, "broadband_fixed_ux": True})
    output_dir.mkdir(parents=True, exist_ok=True)
    prefsp = output_dir / "setup" / f"{state.state_id}_broadband_pre.fsp"
    calibration_prefsp = output_dir / "setup" / f"{state.state_id}_broadband_calibration_pre.fsp"
    prefsp.parent.mkdir(parents=True, exist_ok=True)
    helper = load_material_helper(helper_root)
    if not LUMAPI_ROOT.exists() and str(LUMAPI_ROOT) not in sys.path:
        sys.path.insert(0, str(LUMAPI_ROOT))
    import lumapi
    fdtd = lumapi.FDTD(hide=True)
    try:
        for material_id in ("APCD_GAN_NATIVE_M1", "APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1"):
            helper.register_lumerical_sampled_material(fdtd, material_id)
        x_span_nm, monitor_z_nm = build_geometry(fdtd, case, config, state)
        fdtd.save(str(calibration_prefsp))
    finally:
        fdtd.close()
    calibration_fdtd = lumapi.FDTD(str(calibration_prefsp), hide=True)
    try:
        calibration_fdtd.switchtolayout()
        calibration = calibrate_n_eff(calibration_fdtd, state, x_span_nm, 450.0, config.get("bfast_effective_n_eff_override"))
        kx_contract = configure_bfast(calibration_fdtd, state, calibration)
        calibration_fdtd.save(str(prefsp))
    finally:
        calibration_fdtd.close()
    pre_sha = sha256(prefsp)
    read_fdtd = lumapi.FDTD(str(prefsp), hide=True)
    try:
        solver_props = {prop: maybe_one(read_fdtd, "FDTD", prop) for prop in ("dimension", "x span", "y span", "z min", "z max", "x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc", "bfast alpha", "bloch units", "set based on source angle", "kx", "ky", "mesh accuracy", "pml layers", "simulation time", "auto shutoff min", "dt stability factor")}
        source_props = {prop: maybe_one(read_fdtd, "source_incident", prop) for prop in ("plane wave type", "polarization angle", "x span", "y span", "z", "wavelength start", "wavelength stop", "angle theta", "angle phi")}
        monitor_props = {name: {prop: maybe_one(read_fdtd, name, prop) for prop in ("monitor type", "z", "x span", "y span", "frequency points", "use source limits", "use wavelength spacing")} for name in ("reflection_monitor", "transmission_monitor", "order_monitor", "field_450_monitor")}
        source_angle = source_angle_readback(read_fdtd)
        names = material_names(read_fdtd)
        material_identity = {}
        for material_id in ("APCD_GAN_NATIVE_M1", "APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1"):
            sampled = read_fdtd.getmaterial(material_id, "sampled data")
            material_identity[material_id] = {"present": material_id in names, "type": str(read_fdtd.getmaterial(material_id, "type")), "sample_count": int(len(sampled))}
        source_n = {}
        for wavelength in wavelengths:
            freq = 299792458.0 / (wavelength * 1e-9)
            value = complex_scalar(read_fdtd.getfdtdindex("APCD_GAN_NATIVE_M1", freq, 299792458.0 / (445e-9), 299792458.0 / (455e-9)))
            source_n[str(wavelength)] = {"real": float(value.real), "imag": float(value.imag)}
    finally:
        read_fdtd.close()
    state_rows = []
    for wavelength in wavelengths:
        row_state = IncidentState(wavelength_nm=wavelength, ux=state.ux, uy=state.uy, polarization_branch=state.polarization_branch, theta_air_in_deg=state.theta_air_in_deg, angle_convention_id=state.angle_convention_id)
        n = complex(source_n[str(wavelength)]["real"], source_n[str(wavelength)]["imag"])
        state_rows.append({"wavelength_nm": wavelength, "target_ux": state.ux, "target_uy": state.uy, "target_real_kx": row_state.real_kx, "k_dot_E_residual": transversality_residual(n, row_state)})
    readback = {"case_id": case["case_id"], "solver": jsonable(solver_props), "source": jsonable(source_props), "monitors": jsonable(monitor_props), "source_angle_readback": source_angle, "materials": material_identity, "material_names": names, "source_medium": {"material_id": "APCD_GAN_NATIVE_M1", "z_nm": -250.0, "n_complex_by_wavelength": source_n}, "broadband_fixed_ux_source_contract": kx_contract, "per_wavelength_source_targets": state_rows, "reference_medium": "Air", "reference_plane": "NP pillar bottom", "readback_session_readonly": True}
    checks = {
        "case_id": case["case_id"] == case_spec["case_id"],
        "exact_wavelength_grid": case["exact_wavelength_grid_nm"] == wavelengths and abs(float(source_props["wavelength start"]) * 1e9 - 445.0) <= GRID_TOLERANCE_NM and abs(float(source_props["wavelength stop"]) * 1e9 - 455.0) <= GRID_TOLERANCE_NM and int(float(monitor_props["transmission_monitor"]["frequency points"])) == 11,
        "dimension_3d": solver_props["dimension"] == "3D",
        "period_1740x290": abs(float(solver_props["x span"]) * 1e9 - 1740.0) < 1e-6 and abs(float(solver_props["y span"]) * 1e9 - 290.0) < 1e-6,
        "z_pml": solver_props["z min bc"] == "PML" and solver_props["z max bc"] == "PML",
        "bfast_source": source_props["plane wave type"] == "BFAST",
        "bfast_alpha": solver_props["bfast alpha"] is not None and abs(float(solver_props["bfast alpha"]) - 1.0) < 1e-12,
        "single_forward_source": source_props["polarization angle"] == state.polarization_angle_deg and abs(float(source_props["angle phi"])) < 1e-9,
        "source_inside_native_gan": abs(float(source_props["z"]) * 1e9 + 250.0) < 1e-6 and -600.0 < -250.0 < 0.0,
        "source_angle_readback": source_angle.get("available") is True and source_angle.get("constant") is True,
        "native_materials": all(item["present"] and item["sample_count"] > 1 for item in material_identity.values()),
        "geometry_mdc_975": abs(float(case["coordinates"]["mdc_top_nm"]) - 975.0) < 1e-9,
        "geometry_final_sio2_79": abs(float(case["mdc_candidate"]["layers"][-1]["thickness_nm"]) - 79.0) < 1e-9,
        "geometry_extra_spacer_237": abs(float(case["spacer_nm"]) - 237.0) < 1e-9,
        "geometry_total_sio2_316": abs(float(case["coordinates"]["total_sio2_separation_nm"]) - 316.0) < 1e-9,
        "geometry_np_height_500": abs(float(case["np_candidate"]["pillar_height_nm"]) - 500.0) < 1e-9,
        "fixed_ux_targets": validate_fixed_ux_rows([{"wavelength_nm": row["wavelength_nm"], "ux": row["target_ux"], "real_kx": row["target_real_kx"]} for row in state_rows], state.ux, REAL_KX_TOLERANCE),
        "transversality": all(float(row["k_dot_E_residual"]) <= 1e-12 for row in state_rows),
        "no_solver_entry": True,
    }
    gate = {"schema_version": "stage_a_broadband_polarization_setup_gate_v1", "pass": all(checks.values()), "checks": checks, "hard_gate_if_fail": "HARD_GATE_BROADBAND_FIXED_UX_IMPLEMENTATION_UNRESOLVED" if not checks["bfast_source"] or not checks["source_angle_readback"] or not checks["fixed_ux_targets"] or not checks["transversality"] else None}
    source_helper = helper_root / "scripts/apcd_native_materials.py"
    manifest = {"schema_version": "stage_a_broadband_polarization_setup_manifest_v1", "case_id": case["case_id"], "state": state.to_dict(), "case": case, "readback": readback, "setup_gate": gate, "pre_fsp_path": str(prefsp), "calibration_pre_fsp_path": str(calibration_prefsp), "calibration_pre_fsp_sha256": sha256(calibration_prefsp), "pre_fsp_sha256": pre_sha, "solver_entered": False, "solver_completed": False, "source_commits": {"mdc": MDC_COMMIT, "np": NP_COMMIT}, "coupling_commit": git_head(), "material_helper_path": str(source_helper), "material_helper_sha256": sha256(source_helper), "incident_state_hash": canonical_hash(case["incident_state"]), "physical_contract_hash": canonical_hash({"case": case, "source_contract": kx_contract}), "inherited_solver_settings": {"source": "RUN3A authoritative post-FSP readback", "mesh_accuracy": 2, "pml_layers": 8, "simulation_time_s": 1e-12, "auto_shutoff_min": 1e-5, "dt_stability_factor": 0.99}, "overrides": {"wavelength_grid": "445-455 nm exact 1 nm", "spacer_nm": 237, "source": "BFAST fixed-angle broadband", "reason": "authorized Stage-A frozen-spacer polarization-angle broadband matrix"}}
    json_write(output_dir / "joint_case.json", case)
    json_write(output_dir / "setup_manifest.json", manifest)
    json_write(output_dir / "setup_readback.json", readback)
    json_write(output_dir / "setup_gate.json", gate)
    (output_dir / "pre_fsp.sha256").write_text(pre_sha + "  " + str(prefsp) + "\n", encoding="utf-8")
    return {"case_id": case["case_id"], "pre_fsp_path": str(prefsp), "pre_fsp_sha256": pre_sha, "setup_gate": gate}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--fixture-registry", type=Path, default=ROOT / "configs/coupling/stage_a_golden_fixture_v1.json")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--material-helper-root", type=Path, default=DEFAULT_HELPER_ROOT)
    parser.add_argument("--case-id", type=str, default=None)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    fixture = json.loads(args.fixture_registry.read_text(encoding="utf-8"))
    states = config["states"]
    if args.case_id:
        states = [state for state in states if state["case_id"] == args.case_id]
        if len(states) != 1:
            raise ValueError(f"unknown case id: {args.case_id}")
    summaries = []
    for case_spec in states:
        summary = build_one(case_spec, fixture, config, args.output_root / case_spec["case_id"], args.material_helper_root)
        summaries.append(summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        if not summary["setup_gate"]["pass"]:
            raise SystemExit(f"SETUP_GATE_FAIL:{summary['case_id']}")
    json_write(args.output_root / "setup_set_manifest.json", {"schema_version": "stage_a_broadband_polarization_setup_set_manifest_v1", "config": str(args.config), "fixture_registry": str(args.fixture_registry), "case_order": [item["case_id"] for item in states], "solver_entered": False, "summaries": summaries})


if __name__ == "__main__":
    main()
