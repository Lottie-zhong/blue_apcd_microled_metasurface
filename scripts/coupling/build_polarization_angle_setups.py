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

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from apcd_coupling.incident_state import IncidentState, transversality_residual
from apcd_coupling.joint_case_schema import canonical_hash
from apcd_coupling.joint_stack_builder import build_joint_case

DEFAULT_CONFIG = ROOT / "configs/coupling/stage_a_polarization_angle_450_v1.json"
DEFAULT_OUTPUT_ROOT = ROOT / "outputs/coupling/stage_a_polarization_angle_450_v1"
DEFAULT_HELPER_ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2")
LUMAPI_ROOT = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
MDC_COMMIT = "489b54e43bbf2c08ce030a945b9d4b70ee7550f2"
NP_COMMIT = "7a8588f6b5a1c96d88813f60406d418b488135fd"
CALIBRATION_AIR_ANGLE_DEG = 5.0
REAL_KX_TOLERANCE = 1e-9


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


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
    value = scalar(value)
    return complex(value)


def one(fdtd: Any, object_name: str, prop: str) -> Any:
    return scalar(fdtd.getnamed(object_name, prop))


def maybe_one(fdtd: Any, object_name: str, prop: str) -> Any:
    try:
        return one(fdtd, object_name, prop)
    except Exception:
        return None


def material_names(fdtd: Any) -> list[str]:
    raw = fdtd.getmaterial()
    raw = scalar(raw)
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


def build_geometry(fdtd: Any, case: dict[str, Any], wavelength_nm: float, state: IncidentState) -> tuple[float, float]:
    x_span_nm = float(case["np_candidate"]["period_x_nm"])
    y_span_nm = float(case["np_candidate"]["period_y_nm"])
    stack_top_nm = float(case["coordinates"]["stack_top_nm"])
    pillar_top_nm = float(case["coordinates"]["np_pillar_top_nm"])
    monitor_z_nm = pillar_top_nm + 400.0
    fdtd.addfdtd()
    fdtd.set("dimension", "3D")
    fdtd.set("x span", x_span_nm * 1e-9)
    fdtd.set("y span", y_span_nm * 1e-9)
    fdtd.set("z min", -600e-9)
    fdtd.set("z max", (monitor_z_nm + 300.0) * 1e-9)
    transverse_bc = "Bloch" if abs(state.ux) > 0.0 else "Periodic"
    for prop, value in (("x min bc", transverse_bc), ("x max bc", transverse_bc), ("y min bc", "Periodic"), ("y max bc", "Periodic"), ("z min bc", "PML"), ("z max bc", "PML")):
        fdtd.set(prop, value)
    for prop, value in (("mesh accuracy", 2), ("pml layers", 8), ("simulation time", 1e-12), ("auto shutoff min", 1e-5), ("dt stability factor", 0.99)):
        fdtd.set(prop, value)
    substrate = next(item for item in case["objects"] if item["role"] == "gan_substrate")
    add_rect(fdtd, "GaN_substrate", x_span_nm, y_span_nm, substrate["z_min_nm"], substrate["z_max_nm"], substrate["material_id"])
    for item in case["objects"]:
        if item["role"] in {"mdc_layer", "extra_spacer", "interface_support_layer"}:
            add_rect(fdtd, f"{item['role']}_{int(item['index']) if 'index' in item else 1:02d}", x_span_nm, y_span_nm, item["z_min_nm"], item["z_max_nm"], item["material_id"])
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
    fdtd.set("injection axis", "z-axis")
    fdtd.set("direction", "Forward")
    fdtd.set("plane wave type", "Bloch/periodic")
    fdtd.set("x span", x_span_nm * 1e-9)
    fdtd.set("y span", y_span_nm * 1e-9)
    fdtd.set("z", -250e-9)
    fdtd.set("wavelength start", wavelength_nm * 1e-9)
    fdtd.set("wavelength stop", wavelength_nm * 1e-9)
    fdtd.set("angle phi", 0.0)
    fdtd.set("polarization angle", state.polarization_angle_deg)
    reflection_z_nm = -300.0
    add_monitor(fdtd, "reflection_monitor", reflection_z_nm, x_span_nm, y_span_nm)
    add_monitor(fdtd, "transmission_monitor", monitor_z_nm, x_span_nm, y_span_nm)
    add_monitor(fdtd, "order_monitor", monitor_z_nm, x_span_nm, y_span_nm)
    add_monitor(fdtd, "field_450_monitor", monitor_z_nm, x_span_nm, y_span_nm)
    fdtd.setglobalmonitor("use source limits", 1)
    fdtd.setglobalmonitor("use wavelength spacing", 1)
    fdtd.setglobalmonitor("frequency points", 1)
    return x_span_nm, monitor_z_nm


def configure_real_kx(fdtd: Any, state: IncidentState, x_span_nm: float) -> dict[str, Any]:
    source_name = "source_incident"
    fdtd.setnamed(source_name, "angle phi", 0.0)
    fdtd.setnamed(source_name, "polarization angle", state.polarization_angle_deg)
    fdtd.setnamed(source_name, "angle theta", CALIBRATION_AIR_ANGLE_DEG)
    fdtd.setnamed("FDTD", "x min bc", "Bloch")
    fdtd.setnamed("FDTD", "x max bc", "Bloch")
    fdtd.setnamed("FDTD", "y min bc", "Periodic")
    fdtd.setnamed("FDTD", "y max bc", "Periodic")
    fdtd.setnamed("FDTD", "bloch units", "bandstructure")
    fdtd.setnamed("FDTD", "set based on source angle", 1)
    calibration_kx_band = real_scalar(one(fdtd, "FDTD", "kx"))
    calibration_ux = math.sin(math.radians(CALIBRATION_AIR_ANGLE_DEG))
    calibration_ux_from_fdtd = calibration_kx_band * float(state.wavelength_nm) / x_span_nm
    n_eff = calibration_ux_from_fdtd / calibration_ux
    if not math.isfinite(n_eff) or n_eff <= 0.0:
        raise RuntimeError(f"invalid lossy-GaN source calibration n_eff={n_eff}")
    internal_theta = math.degrees(math.asin(max(-1.0, min(1.0, float(state.ux) / n_eff))))
    fdtd.setnamed(source_name, "angle theta", internal_theta)
    fdtd.setnamed(source_name, "angle phi", 0.0)
    fdtd.setnamed(source_name, "polarization angle", state.polarization_angle_deg)
    if abs(state.ux) > 0.0:
        fdtd.setnamed("FDTD", "x min bc", "Bloch")
        fdtd.setnamed("FDTD", "x max bc", "Bloch")
        fdtd.setnamed("FDTD", "y min bc", "Periodic")
        fdtd.setnamed("FDTD", "y max bc", "Periodic")
        fdtd.setnamed("FDTD", "bloch units", "SI")
        fdtd.setnamed("FDTD", "set based on source angle", 0)
        fdtd.setnamed("FDTD", "kx", state.real_kx)
        boundary_kx = real_scalar(one(fdtd, "FDTD", "kx"))
        boundary_ky = real_scalar(one(fdtd, "FDTD", "ky"))
    else:
        fdtd.setnamed("FDTD", "x min bc", "Periodic")
        fdtd.setnamed("FDTD", "x max bc", "Periodic")
        fdtd.setnamed("FDTD", "y min bc", "Periodic")
        fdtd.setnamed("FDTD", "y max bc", "Periodic")
        boundary_kx = 0.0
        boundary_ky = 0.0
    source_readback_kx = state.real_kx if abs(state.ux) > 0.0 else 0.0
    kx_difference = boundary_kx - state.real_kx
    return {
        "target_theta_air_deg": float(state.theta_air_in_deg),
        "target_ux": float(state.ux),
        "target_uy": float(state.uy),
        "target_real_kx": float(state.real_kx),
        "source_implementation": "Bloch/periodic plane wave",
        "boundary_implementation": "manual SI Bloch kx with y Periodic" if abs(state.ux) > 0.0 else "Periodic normal incidence",
        "source_medium_identity": "APCD_GAN_NATIVE_M1",
        "source_internal_theta_deg": float(internal_theta),
        "source_phi_deg": float(one(fdtd, source_name, "angle phi")),
        "source_calibration_air_angle_deg": CALIBRATION_AIR_ANGLE_DEG,
        "source_calibration_kx_bandstructure": float(calibration_kx_band),
        "source_calibration_ux_from_fdtd": float(calibration_ux_from_fdtd),
        "source_calibration_n_eff": float(n_eff),
        "source_readback_kx": float(source_readback_kx),
        "boundary_readback_kx": float(boundary_kx),
        "readback_kx_difference": float(kx_difference),
        "readback_ky": float(boundary_ky),
        "sign_convention": "positive real kx is physical +x; negative real kx is physical -x",
        "wavelength_nm": float(state.wavelength_nm),
        "reference_medium": "Air",
        "angle_convention_id": state.angle_convention_id,
        "source_boundary_consistent": abs(kx_difference) <= max(abs(state.real_kx), 1.0) * REAL_KX_TOLERANCE,
        "source_theta_not_air_angle": abs(state.ux) == 0.0 or abs(internal_theta - state.theta_air_in_deg) > 1e-12,
    }


def build_one(case_spec: dict[str, Any], fixture: dict[str, Any], output_dir: Path, helper_root: Path) -> dict[str, Any]:
    if float(case_spec.get("wavelength_nm", 450.0)) != 450.0:
        raise ValueError("Stage-A polarization-angle builder is exact 450 nm only")
    state = IncidentState(
        wavelength_nm=float(case_spec.get("wavelength_nm", 450.0)),
        ux=float(case_spec["ux"]),
        uy=float(case_spec["uy"]),
        polarization_branch=str(case_spec["polarization_branch"]),
        theta_air_in_deg=float(case_spec["theta_air_in_deg"]),
        angle_convention_id="air_side_far_field_conserved_real_kx_v1",
    )
    case = build_joint_case(
        fixture["mdc_candidate"], fixture["np_candidate"], 237.0, 450.0,
        state.linear_polarization, state.ux, case_id=case_spec["case_id"],
        control_group="POL_ANGLE_MATRIX", incident_state=state.to_dict(),
    )
    case["source_contract_id"] = "OBLIQUE_REAL_KX_SOURCE_CONTRACT_V1"
    output_dir.mkdir(parents=True, exist_ok=True)
    prefsp = output_dir / "setup" / f"{state.state_id}_pre.fsp"
    prefsp.parent.mkdir(parents=True, exist_ok=True)
    helper = load_material_helper(helper_root)
    if not LUMAPI_ROOT.exists() and str(LUMAPI_ROOT) not in sys.path:
        sys.path.insert(0, str(LUMAPI_ROOT))
    import lumapi
    calibration_prefsp = output_dir / "setup" / f"{state.state_id}_calibration_pre.fsp"
    fdtd = lumapi.FDTD(hide=True)
    try:
        for material_id in ("APCD_GAN_NATIVE_M1", "APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1"):
            helper.register_lumerical_sampled_material(fdtd, material_id)
        x_span_nm, monitor_z_nm = build_geometry(fdtd, case, 450.0, state)
        fdtd.save(str(calibration_prefsp))
    finally:
        fdtd.close()
    fdtd = lumapi.FDTD(str(calibration_prefsp), hide=True)
    try:
        fdtd.switchtolayout()
        kx_contract = configure_real_kx(fdtd, state, x_span_nm)
        fdtd.save(str(prefsp))
    finally:
        fdtd.close()
    pre_sha = sha256(prefsp)
    fdtd = lumapi.FDTD(str(prefsp), hide=True)
    try:
        solver_props = {prop: maybe_one(fdtd, "FDTD", prop) for prop in ("dimension", "x span", "y span", "z min", "z max", "x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc", "bloch units", "set based on source angle", "kx", "ky", "mesh accuracy", "pml layers")}
        source_props = {prop: one(fdtd, "source_incident", prop) for prop in ("plane wave type", "injection axis", "direction", "polarization angle", "x span", "y span", "z", "wavelength start", "wavelength stop", "angle theta", "angle phi")}
        monitor_props = {name: {prop: one(fdtd, name, prop) for prop in ("monitor type", "z", "x span", "y span")} for name in ("reflection_monitor", "transmission_monitor", "order_monitor", "field_450_monitor")}
        material_identity = {}
        names = material_names(fdtd)
        for material_id in ("APCD_GAN_NATIVE_M1", "APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1"):
            sampled = fdtd.getmaterial(material_id, "sampled data")
            material_identity[material_id] = {"present": material_id in names, "type": str(fdtd.getmaterial(material_id, "type")), "sample_count": int(len(sampled))}
        source_frequency_hz = 299792458.0 / (450e-9)
        source_n = complex_scalar(fdtd.getfdtdindex("APCD_GAN_NATIVE_M1", source_frequency_hz, source_frequency_hz, 1))
    finally:
        fdtd.close()
    kx_contract["source_readback_kx"] = float(kx_contract["source_readback_kx"])
    readback_kx = 0.0 if solver_props["kx"] is None and state.ux == 0.0 else float(solver_props["kx"])
    readback_ky = 0.0 if solver_props["ky"] is None else float(solver_props["ky"])
    kx_contract["boundary_readback_kx"] = readback_kx
    kx_contract["readback_kx_difference"] = float(readback_kx - state.real_kx)
    kx_contract["readback_ky"] = readback_ky
    kx_contract["k_dot_E_residual"] = float(transversality_residual(source_n, state))
    readback = {"case_id": case["case_id"], "solver": solver_props, "source": source_props, "monitors": monitor_props, "materials": material_identity, "material_names": names, "source_medium": {"material_id": "APCD_GAN_NATIVE_M1", "n_complex_450nm": {"real": source_n.real, "imag": source_n.imag}}, "oblique_real_kx_source_contract": kx_contract, "reference_medium": "Air", "reference_plane": "NP pillar bottom", "readback_session_readonly": True}
    checks = {
        "case_id": case["case_id"] == case_spec["case_id"],
        "wavelength_450nm": state.wavelength_nm == 450.0,
        "dimension_3d": solver_props["dimension"] == "3D",
        "x_period_1740nm": abs(real_scalar(solver_props["x span"]) * 1e9 - 1740.0) < 1e-6,
        "y_period_290nm": abs(real_scalar(solver_props["y span"]) * 1e9 - 290.0) < 1e-6,
        "z_pml": solver_props["z min bc"] == "PML" and solver_props["z max bc"] == "PML",
        "oblique_bloch_or_normal_periodic": (abs(state.ux) > 0 and solver_props["x min bc"] == "Bloch" and solver_props["x max bc"] == "Bloch") or (state.ux == 0 and solver_props["x min bc"] == "Periodic" and solver_props["x max bc"] == "Periodic"),
        "y_periodic_ky0": solver_props["y min bc"] == "Periodic" and solver_props["y max bc"] == "Periodic" and abs(readback_ky) <= 1e-12,
        "bloch_si_for_oblique": abs(state.ux) == 0 or solver_props["bloch units"] == "SI",
        "source_bloch_periodic": source_props["plane wave type"] == "Bloch/periodic",
        "source_forward_z": source_props["injection axis"] == "z-axis" and source_props["direction"] == "Forward",
        "source_branch": abs(float(source_props["polarization angle"]) - state.polarization_angle_deg) < 1e-9,
        "source_phi_zero": abs(float(source_props["angle phi"])) < 1e-9,
        "source_wavelength": abs(float(source_props["wavelength start"]) - 450e-9) < 1e-15 and abs(float(source_props["wavelength stop"]) - 450e-9) < 1e-15,
        "geometry_mdc_975": abs(float(case["coordinates"]["mdc_top_nm"]) - 975.0) < 1e-9,
        "geometry_final_sio2_79": abs(float(case["mdc_candidate"]["layers"][-1]["thickness_nm"]) - 79.0) < 1e-9,
        "geometry_extra_spacer_237": abs(float(case["spacer_nm"]) - 237.0) < 1e-9,
        "geometry_total_sio2_316": abs(float(case["coordinates"]["total_sio2_separation_nm"]) - 316.0) < 1e-9,
        "geometry_np_height_500": abs(float(case["np_candidate"]["pillar_height_nm"]) - 500.0) < 1e-9,
        "native_materials": all(item["present"] and item["sample_count"] > 1 for item in material_identity.values()),
        "source_boundary_kx": abs(float(kx_contract["boundary_readback_kx"]) - state.real_kx) <= max(abs(state.real_kx), 1.0) * REAL_KX_TOLERANCE,
        "source_ky_zero": abs(float(kx_contract["readback_ky"])) <= 1e-12,
        "kx_sign": (state.ux == 0 and kx_contract["boundary_readback_kx"] == 0.0) or (state.ux > 0 and kx_contract["boundary_readback_kx"] > 0.0) or (state.ux < 0 and kx_contract["boundary_readback_kx"] < 0.0),
        "transversality": float(kx_contract["k_dot_E_residual"]) <= 1e-12,
        "no_solver_entry": True,
    }
    gate = {"schema_version": "stage_a_polarization_setup_gate_v1", "pass": all(checks.values()), "checks": checks, "hard_gate_if_fail": "HARD_GATE_LOSSY_GAN_REAL_KX_SOURCE_IMPLEMENTATION_UNRESOLVED" if not checks["source_boundary_kx"] or not checks["transversality"] else None}
    source_helper = helper_root / "scripts/apcd_native_materials.py"
    manifest = {
        "schema_version": "stage_a_polarization_setup_manifest_v1",
        "case_id": case["case_id"],
        "state": state.to_dict(),
        "case": case,
        "readback": readback,
        "setup_gate": gate,
        "pre_fsp_path": str(prefsp),
        "calibration_pre_fsp_path": str(calibration_prefsp),
        "calibration_pre_fsp_sha256": sha256(calibration_prefsp),
        "pre_fsp_sha256": pre_sha,
        "solver_entered": False,
        "solver_completed": False,
        "source_commits": {"mdc": MDC_COMMIT, "np": NP_COMMIT},
        "coupling_commit": git_head(),
        "material_helper_path": str(source_helper),
        "material_helper_sha256": sha256(source_helper),
        "incident_state_hash": state.sha256(),
        "physical_contract_hash": canonical_hash({"case": case, "source_contract": kx_contract}),
        "inherited_solver_settings": {"source": "RUN3A authoritative post-FSP readback", "mesh_accuracy": 2, "pml_layers": 8, "simulation_time_s": 1e-12, "auto_shutoff_min": 1e-5, "dt_stability_factor": 0.99},
        "overrides": {"wavelength": "450 nm exact single point", "spacer_nm": 237, "reason": "authorized Stage-A frozen-spacer polarization-angle matrix"},
    }
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
        output_dir = args.output_root / case_spec["case_id"]
        summary = build_one(case_spec, fixture, output_dir, args.material_helper_root)
        summaries.append(summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        if not summary["setup_gate"]["pass"]:
            raise SystemExit(f"SETUP_GATE_FAIL:{summary['case_id']}")
    json_write(args.output_root / "setup_set_manifest.json", {"schema_version": "stage_a_polarization_setup_set_manifest_v1", "config": str(args.config), "fixture_registry": str(args.fixture_registry), "case_order": [item["case_id"] for item in states], "solver_entered": False, "summaries": summaries})


if __name__ == "__main__":
    main()
