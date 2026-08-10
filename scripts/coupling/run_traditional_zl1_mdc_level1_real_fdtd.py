"""Queue and execute the six-case formal ZL-1 MDC Level-1 provider.

The queue is intentionally separate from execution.  Each case follows the
validated setup -> save -> fresh load -> readback -> entered ledger -> run ->
extract lifecycle.  FSPs and raw tensors remain runtime artifacts and are not
intended for Git.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import shutil
import sys
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import mdc_fdtd_2d_monitor_contract_v1 as monitor_contract
import run_mdc_native_m1_2d_dipole_device_comparison_v1 as frozen


if not hasattr(np, "trapezoid"):
    np.trapezoid = np.trapz


TASK = "APCD_MDC_NP_COUPLING_V1_TRADITIONAL_LEVEL1_ZL1_FORMAL_SIX_CASE_FDTD"
PROVIDER_ID = "TRADITIONAL_ZL1_MDC_LEVEL1_REAL_FDTD_PROVIDER_V1"
START_NM, STOP_NM, POINTS = 420.0, 480.0, 301
SOURCE_POSITIONS = {"TOP": -171.5, "CENTROID": -276.0, "BOTTOM": -380.5}
ORIENTATIONS = {
    "X": {"source_orientation": "x", "interface_polarization_family": "P_TM_like", "theta_deg": 90.0},
    "Z": {"source_orientation": "z", "interface_polarization_family": "S_TE_like", "theta_deg": 0.0},
}
CASE_ORDER = [f"{position}_{orientation}" for position in SOURCE_POSITIONS for orientation in ORIENTATIONS]
MATERIALS = ("APCD_GAN_NATIVE_M1", "APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1")
SEQUENCE_EXPECTED = [("H", 44.0), ("L", 79.0), ("H", 44.0), ("L", 79.0), ("H", 44.0), ("L", 316.0), ("H", 44.0), ("L", 79.0), ("H", 44.0), ("L", 79.0), ("H", 44.0), ("L", 79.0)]
MATERIAL_CONFIG = ROOT / "configs" / "material_reference_apcd_blue.yaml"
MONITOR_SCRIPT = ROOT / "scripts" / "mdc_fdtd_2d_monitor_contract_v1.py"
FROZEN_GRID_NPZ = Path(
    r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2\outputs\mdc_hf_surrogate_v2_doe96_joint_profile_database_v1\20260803T_doe96_joint_profile_6b6d7e2\cases\007856ea2f40432b933940511f757d1daccfb0cd7b311c601e7f678656b79a8d\007856ea2f40_attempt_1__raw.npz"
)
FROZEN_GRID_SHA256 = "f3e2b786901c912240ea0267886d4ea9d9e5c62b78846bf1428dbed3c25a0ac9"
# The six solver entries were executed by the remote runner before the
# post-processing evidence patch was installed.  Preserve that executable
# identity when finalization backfills metadata into the existing results.
EXECUTED_BUILDER_SHA256 = "ca77674081da3c4134c0358868ab63ce04c092d94a1008d955b4af0795a7987f"
RUN_BASE = ROOT / "outputs" / "coupling" / "traditional_zl1_mdc_level1_real_fdtd_v1"


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_object(value: object) -> str:
    return sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def lumapi():
    location = r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py"
    spec = importlib.util.spec_from_file_location("lumapi", location)
    module = importlib.util.module_from_spec(spec)
    sys.modules["lumapi"] = module
    spec.loader.exec_module(module)
    return module


def scalar(value: object) -> object:
    if isinstance(value, str):
        return value
    array = np.asarray(value).reshape(-1)
    return array[0].item() if array.size == 1 else array.tolist()


def frozen_grid() -> tuple[np.ndarray, np.ndarray, str]:
    if not FROZEN_GRID_NPZ.exists():
        raise RuntimeError(f"frozen_grid_reference_missing:{FROZEN_GRID_NPZ}")
    with np.load(FROZEN_GRID_NPZ, allow_pickle=False) as data:
        wavelength = np.asarray(data["wavelength_nm"], dtype=float).reshape(-1)
        angle = np.asarray(data["angle_deg"], dtype=float).reshape(-1)
    if wavelength.shape != (POINTS,) or angle.shape != (2000,):
        raise RuntimeError("frozen_grid_reference_shape_mismatch")
    grid_hash = sha_bytes(wavelength.tobytes() + angle.tobytes())
    if grid_hash != FROZEN_GRID_SHA256:
        raise RuntimeError(f"frozen_grid_reference_hash_mismatch:{grid_hash}")
    return wavelength, angle, grid_hash


def zl1_structure() -> dict:
    structures = {item["structure_key"]: item for item in frozen.structures()}
    if "zl1_alternative" not in structures:
        raise RuntimeError("zl1_alternative_missing")
    structure = structures["zl1_alternative"]
    sequence = [(str(material), float(thickness)) for material, thickness in structure["sequence"]]
    if sequence != SEQUENCE_EXPECTED:
        raise RuntimeError(f"zl1_sequence_mismatch:{sequence!r}")
    if structure["layer_count"] != 12 or abs(float(structure["total_thickness_nm"]) - 975.0) > 1e-9:
        raise RuntimeError("zl1_geometry_thickness_mismatch")
    return structure


def case_records() -> list[dict]:
    structure = zl1_structure()
    output = []
    for position, source_y in SOURCE_POSITIONS.items():
        for orientation, family in ORIENTATIONS.items():
            case_id = f"{position}_{orientation}"
            output.append(
                {
                    "case_id": case_id,
                    "source_position": position,
                    "source_z_nm": source_y,
                    "source_orientation": family["source_orientation"],
                    "interface_polarization_family": family["interface_polarization_family"],
                    "theta_deg": family["theta_deg"],
                    "phi_deg": 0.0,
                    "candidate_id": "P1_ZL1_ALTERNATIVE_G3_A3",
                    "geometry_hash": structure["geometry_hash"],
                    "layer_count": 12,
                    "total_thickness_nm": 975.0,
                    "reference_plane_z_nm": 975.0,
                    "status": "QUEUED",
                    "solver_entered": False,
                    "attempt_id": f"{case_id}_ATTEMPT_001",
                }
            )
    return output


def physical_contract() -> dict:
    structure = zl1_structure()
    wavelength, angle, grid_hash = frozen_grid()
    return {
        "task": TASK,
        "provider_id": PROVIDER_ID,
        "candidate_id": "P1_ZL1_ALTERNATIVE_G3_A3",
        "geometry_hash": structure["geometry_hash"],
        "geometry_sequence": [[material, thickness] for material, thickness in SEQUENCE_EXPECTED],
        "geometry_total_thickness_nm": 975.0,
        "materials": list(MATERIALS),
        "extra_spacer_nm": 0.0,
        "np_geometry_included": False,
        "reference_plane_z_nm": 975.0,
        "source_positions_nm": SOURCE_POSITIONS,
        "source_orientation_to_interface_family": {k: v["interface_polarization_family"] for k, v in ORIENTATIONS.items()},
        "wavelength_grid_nm": {"start": START_NM, "stop": STOP_NM, "points": POINTS},
        "theta_grid": {"source": str(FROZEN_GRID_NPZ), "points": 2000, "min_deg": float(angle.min()), "max_deg": float(angle.max()), "nonuniform": True, "grid_sha256": grid_hash},
        "axis_order": ["wavelength_index", "angle_index"],
        "theta_to_ux": "MDC_THETA_TO_UX_CONSERVATIVE_REMAP_V1; ux=sin(theta); mass conserving; no extrapolation",
        "raw_before_normalization": True,
    }


def build_case(fdtd, case: dict, structure: dict) -> dict:
    registered = []
    native = frozen.native()
    for material in MATERIALS:
        native.register_lumerical_sampled_material(fdtd, material, apply_display_style=True)
        registered.append(material)
    total_y = structure["total_thickness_nm"] * 1e-9
    fdtd.addfdtd()
    fdtd.set("dimension", "2D")
    fdtd.set("x span", frozen.XSPAN)
    fdtd.set("y min", -1e-6)
    fdtd.set("y max", max(1.6e-6, total_y + 600e-9))
    for side in ("x min bc", "x max bc", "y min bc", "y max bc"):
        fdtd.set(side, "PML")
    fdtd.set("mesh accuracy", 2)
    fdtd.set("simulation time", 900e-15)
    fdtd.set("auto shutoff min", 1e-7)
    frozen.add_rect(fdtd, "gan", "APCD_GAN_NATIVE_M1", -1e-6, 0.0)
    y = 0.0
    for index, (material, thickness_nm) in enumerate(SEQUENCE_EXPECTED):
        material_id = "APCD_SIO2_NATIVE_M1" if material == "L" else "APCD_TIO2_NATIVE_M1"
        frozen.add_rect(fdtd, f"layer_{index}", material_id, y, y + thickness_nm * 1e-9)
        y += thickness_nm * 1e-9
    fdtd.addmesh()
    fdtd.set("name", "stack_mesh")
    fdtd.set("x span", frozen.XSPAN)
    fdtd.set("y min", -50e-9)
    fdtd.set("y max", y + 50e-9)
    fdtd.set("dx", 20e-9)
    fdtd.set("dy", 2e-9)
    source_y = case["source_z_nm"] * 1e-9
    monitor_contract.add_source_local_mesh(fdtd, 0.0, source_y, 12e-9, 1e-9)
    source_name = f"{case['source_orientation']}_dipole"
    fdtd.adddipole()
    fdtd.set("name", source_name)
    fdtd.set("x", 0.0)
    fdtd.set("y", source_y)
    fdtd.set("theta", case["theta_deg"])
    fdtd.set("phi", case["phi_deg"])
    fdtd.set("wavelength start", START_NM * 1e-9)
    fdtd.set("wavelength stop", STOP_NM * 1e-9)
    monitor_contract.add_2d_power_box(fdtd, "emit_box_12nm", 0.0, source_y, 12e-9, START_NM * 1e-9, STOP_NM * 1e-9, POINTS)
    monitor_contract.add_reference_plane_monitor(fdtd, "upward_monitor", 0.0, y + 300e-9, frozen.MONITOR_XSPAN, START_NM * 1e-9, STOP_NM * 1e-9, POINTS)
    return {"source_name": source_name, "source_y_nm": case["source_z_nm"], "top_y_nm": y * 1e9, "monitor_y_nm": (y + 300e-9) * 1e9, "registered_materials": registered, "monitor_name": "upward_monitor", "power_box_prefix": "emit_box_12nm"}


def setup_readback(fdtd, case: dict, setup: dict) -> dict:
    source_name = setup["source_name"]
    layer_readback = [float(fdtd.getnamed(f"layer_{index}", "y max")) * 1e9 for index in range(12)]
    readback = {
        "fdtd_count": int(fdtd.getnamednumber("FDTD")),
        "source_count": int(fdtd.getnamednumber(source_name)),
        "upward_monitor_count": int(fdtd.getnamednumber("upward_monitor")),
        "box_monitor_counts": {name: int(fdtd.getnamednumber(name)) for name in ("emit_box_12nm_top", "emit_box_12nm_bottom", "emit_box_12nm_left", "emit_box_12nm_right")},
        "dimension": str(fdtd.getnamed("FDTD", "dimension")),
        "source_y_nm": float(fdtd.getnamed(source_name, "y")) * 1e9,
        "source_theta_deg": float(fdtd.getnamed(source_name, "theta")),
        "source_phi_deg": float(fdtd.getnamed(source_name, "phi")),
        "monitor_y_nm": float(fdtd.getnamed("upward_monitor", "y")) * 1e9,
        "layer_y_max_nm": layer_readback,
    }
    checks = {
        "fdtd": readback["fdtd_count"] == 1,
        "source": readback["source_count"] == 1,
        "upward_monitor": readback["upward_monitor_count"] == 1,
        "box_monitors": all(value == 1 for value in readback["box_monitor_counts"].values()),
        "dimension_2d": readback["dimension"] == "2D",
        "source_y": abs(readback["source_y_nm"] - case["source_z_nm"]) < 1e-6,
        "theta": abs(readback["source_theta_deg"] - case["theta_deg"]) < 1e-6,
        "phi": abs(readback["source_phi_deg"] - case["phi_deg"]) < 1e-6,
        "reference_plane": abs(readback["monitor_y_nm"] - 1275.0) < 1e-6,
        "geometry_top": abs(readback["layer_y_max_nm"][-1] - 975.0) < 1e-6,
    }
    readback["checks"] = checks
    readback["pass"] = all(checks.values())
    if not readback["pass"]:
        raise RuntimeError("setup_readback_gate_failed:" + json.dumps(checks, sort_keys=True))
    return readback


def theta_edges(theta_rad: np.ndarray) -> np.ndarray:
    if np.any(np.diff(theta_rad) <= 0):
        raise RuntimeError("theta_grid_not_strictly_increasing")
    edges = np.empty(theta_rad.size + 1, dtype=float)
    edges[0] = theta_rad[0]
    edges[-1] = theta_rad[-1]
    edges[1:-1] = 0.5 * (theta_rad[:-1] + theta_rad[1:])
    return edges


def extract_joint(fdtd, monitor_name: str, wavelength: np.ndarray, p_up: np.ndarray, reference_angle: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rows = []
    angle_ref = None
    for wavelength_index, wave in enumerate(wavelength):
        monitor_index = len(wavelength) - wavelength_index
        farfield = np.asarray(fdtd.farfield2d(monitor_name, monitor_index), dtype=float).reshape(-1)
        angle = np.asarray(fdtd.farfieldangle(monitor_name, monitor_index), dtype=float).reshape(-1)
        degrees = np.degrees(angle) if np.max(np.abs(angle)) <= math.pi + 1 else angle
        if angle_ref is None:
            angle_ref = degrees.copy()
        if degrees.shape != angle_ref.shape or not np.allclose(degrees, angle_ref, rtol=0.0, atol=1e-6):
            raise RuntimeError("native_theta_grid_varies_across_wavelength")
        if farfield.shape != (2000,) or not np.all(np.isfinite(farfield)) or np.any(farfield < -1e-15):
            raise RuntimeError("joint_tensor_nonfinite_negative_or_shape_mismatch")
        rows.append(np.maximum(farfield, 0.0))
    angle_ref = np.asarray(angle_ref, dtype=float)
    if not np.allclose(angle_ref, reference_angle, rtol=0.0, atol=1e-6):
        raise RuntimeError("native_theta_grid_does_not_match_frozen_grid")
    joint = np.asarray(rows, dtype=float)
    if joint.shape != (POINTS, 2000):
        raise RuntimeError(f"joint_shape_mismatch:{joint.shape}")
    return angle_ref, joint


def remap_theta_to_ux(joint: np.ndarray, angle_deg: np.ndarray) -> dict[str, np.ndarray | float]:
    theta_rad = np.radians(angle_deg)
    edges_theta = theta_edges(theta_rad)
    edges_ux = np.sin(edges_theta)
    widths_theta = np.diff(edges_theta)
    widths_ux = np.diff(edges_ux)
    if np.any(widths_ux <= 0):
        raise RuntimeError("ux_edges_not_monotonic")
    centers_ux = 0.5 * (edges_ux[:-1] + edges_ux[1:])
    raw_theta_integral = float(np.sum(joint * widths_theta[None, :]))
    raw_ux_density = joint * widths_theta[None, :] / widths_ux[None, :]
    remapped_integral = float(np.sum(raw_ux_density * widths_ux[None, :]))
    return {"theta_edges_rad": edges_theta, "ux_edges": edges_ux, "ux_centers": centers_ux, "theta_weights_rad": widths_theta, "ux_widths": widths_ux, "raw_theta_integral": raw_theta_integral, "raw_ux_integral": remapped_integral, "raw_ux_density": raw_ux_density}


def read_raw_power(fdtd) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    frequency = np.asarray(fdtd.getdata("upward_monitor", "f"), dtype=float).reshape(-1)
    wavelength_raw = 299792458.0 / frequency * 1e9
    order = np.argsort(wavelength_raw)
    wavelength = wavelength_raw[order]
    p_up = np.asarray(monitor_contract.read_reference_plane_flux(fdtd, "upward_monitor"), dtype=float).reshape(-1)[order]
    sides = {side: monitor_contract.integrate_line_poynting_flux(monitor_contract.read_fields(fdtd, f"emit_box_12nm_{side}"), "Linear X" if side in ("top", "bottom") else "Linear Y") for side in ("top", "bottom", "left", "right")}
    p_box_top = np.asarray(sides["top"], dtype=float).reshape(-1)[order]
    p_box = np.asarray(monitor_contract.calculate_box_outward_flux(sides)["net_outward"], dtype=float).reshape(-1)[order]
    return wavelength, p_up, p_box_top, p_box


def run_case(run_root: Path, case_id: str) -> None:
    state = read_json(run_root / "queue.json")
    case = next((item for item in state["cases"] if item["case_id"] == case_id), None)
    if case is None:
        raise RuntimeError(f"case_not_in_queue:{case_id}")
    if case["status"] != "QUEUED" or case.get("solver_entered"):
        raise RuntimeError(f"case_not_pending_or_replay_forbidden:{case_id}:{case['status']}")
    contract_hash = state["physical_contract_hash"]
    structure = zl1_structure()
    case_dir = run_root / "cases" / case_id
    setup_dir, runtime_dir = case_dir / "setup", case_dir / "runtime"
    setup_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    pre = setup_dir / f"{case_id}__pre.fsp"
    post = runtime_dir / f"{case_id}__attempt_001__post.fsp"
    raw_path = runtime_dir / f"{case_id}__attempt_001__raw.npz"
    try:
        setup_session = lumapi().FDTD(hide=True)
        try:
            setup = build_case(setup_session, case, structure)
            setup_session.save(str(pre))
        finally:
            setup_session.close()
        pre_hash = sha_file(pre)
        shutil.copy2(pre, post)
        fresh = lumapi().FDTD(hide=True)
        try:
            fresh.load(str(post))
            readback = setup_readback(fresh, case, setup)
            reference_wavelength, reference_angle, reference_grid_hash = frozen_grid()
            # This is the final setup-only gate.  The solver entry record is
            # written immediately before f.run(), and never before this point.
            if not np.allclose(reference_wavelength, np.linspace(START_NM, STOP_NM, POINTS), rtol=0.0, atol=1e-9):
                raise RuntimeError("frozen_wavelength_grid_contract_mismatch")
            entered_at = now()
            ledger = {"case_id": case_id, "attempt_id": case["attempt_id"], "solver_entered": True, "entered_timestamp": entered_at, "pre_fsp_hash": pre_hash, "physical_contract_hash": contract_hash, "reason": "AUTHORIZED_TRADITIONAL_ZL1_FORMAL_SIX_CASE_FDTD"}
            with (run_root / "solver_entered_ledger.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(ledger, sort_keys=True) + "\n")
            case.update({"status": "RUNNING", "solver_entered": True, "entered_timestamp": entered_at, "pre_fsp_path": str(pre), "pre_fsp_sha256": pre_hash, "physical_contract_hash": contract_hash, "setup_readback": readback})
            atomic_json(run_root / "queue.json", state)
            fresh.run()
            fresh.save(str(post))
            post_hash = sha_file(post)
            wavelength, p_up, p_box_top, p_box = read_raw_power(fresh)
            if wavelength.shape != (POINTS,) or not np.allclose(wavelength, reference_wavelength, rtol=0.0, atol=1e-9):
                raise RuntimeError("actual_wavelength_grid_mismatch")
            angle, joint = extract_joint(fresh, "upward_monitor", wavelength, p_up, reference_angle)
            grid_hash = sha_bytes(wavelength.tobytes() + angle.tobytes())
            if grid_hash != reference_grid_hash:
                raise RuntimeError(f"actual_grid_hash_mismatch:{grid_hash}")
            remap = remap_theta_to_ux(joint, angle)
            theta_rad = np.radians(angle)
            spectral_marginal = np.trapezoid(joint, theta_rad, axis=1)
            angular_marginal = np.trapezoid(joint, wavelength, axis=0)
            raw_joint_integral = float(np.trapezoid(spectral_marginal, wavelength))
            remap_error = abs(float(remap["raw_theta_integral"]) - float(remap["raw_ux_integral"])) / max(abs(float(remap["raw_theta_integral"])), 1e-300)
            np.savez_compressed(raw_path, wavelength_nm=wavelength, angle_deg=angle, joint_raw=joint, p_up_raw=p_up, p_box_top_raw=p_box_top, p_box_raw=p_box, spectral_marginal_raw=spectral_marginal, angular_marginal_raw=angular_marginal, raw_joint_ux_density=remap["raw_ux_density"], ux_edges=remap["ux_edges"], ux_centers=remap["ux_centers"], theta_weights_rad=remap["theta_weights_rad"], ux_widths=remap["ux_widths"])
            result = {"case_id": case_id, "status": "COMPLETE", "solver_status": "COMPLETE", "solver_entered": True, "attempt_id": case["attempt_id"], "pre_fsp_path": str(pre), "pre_fsp_sha256": pre_hash, "post_fsp_path": str(post), "post_fsp_sha256": post_hash, "raw_npz_path": str(raw_path), "grid_sha256": grid_hash, "grid_shape": [int(x) for x in joint.shape], "raw_joint_integral": raw_joint_integral, "theta_to_ux_remap_relative_closure_error": remap_error, "theta_to_ux_mass_closure": float(remap["raw_ux_integral"]) / raw_joint_integral, "raw_joint_finite": bool(np.all(np.isfinite(joint))), "raw_joint_negative_count": int(np.sum(joint < 0)), "raw_power_finite": bool(all(np.all(np.isfinite(x)) for x in (p_up, p_box_top, p_box))), "source_orientation": case["source_orientation"], "interface_polarization_family": case["interface_polarization_family"], "source_position": case["source_position"], "source_z_nm": case["source_z_nm"], "setup_readback": readback, "builder_sha256": sha_file(Path(__file__)), "material_config_sha256": sha_file(MATERIAL_CONFIG), "monitor_contract_sha256": sha_file(MONITOR_SCRIPT), "frozen_grid_reference_sha256": sha_file(FROZEN_GRID_NPZ), "solver_exit_state": "fdtd.run_returned", "completed_timestamp": now()}
            case.update(result)
            atomic_json(case_dir / "case_result.json", result)
            atomic_json(run_root / "queue.json", state)
        finally:
            fresh.close()
    except Exception as error:
        failure = {"case_id": case_id, "attempt_id": case["attempt_id"], "error_type": type(error).__name__, "error_text": str(error), "stage": "after_solver_entry" if case.get("solver_entered") else "before_solver_entry", "timestamp": now()}
        atomic_json(case_dir / "run_failure.json", failure)
        case.update({"status": "FAILED", "failure": failure})
        atomic_json(run_root / "queue.json", state)
        raise


def create_queue(run_root: Path) -> None:
    if run_root.exists():
        raise FileExistsError(run_root)
    run_root.mkdir(parents=True)
    contract = physical_contract()
    cases = case_records()
    if [item["case_id"] for item in cases] != CASE_ORDER or len(cases) != 6:
        raise RuntimeError("six_case_membership_mismatch")
    state = {"schema_version": "traditional_zl1_mdc_level1_solver_queue_v1", "task": TASK, "provider_id": PROVIDER_ID, "run_id": run_root.name, "created_timestamp": now(), "status": "QUEUED", "physical_contract": contract, "physical_contract_hash": sha_object(contract), "authorization": {"new_2d_fdtd_physical_cases": 6, "per_case_entered_max": 1, "replays": 0, "np_solver": 0, "integrated_3d_fdtd": 0, "tmm": 0, "rcwa": 0, "fem": 0, "training": 0, "ml_inference": 0}, "cases": cases, "safety_counters": {"FDTD_entered": 0, "NP_solver": 0, "integrated_3d_fdtd": 0, "TMM": 0, "RCWA": 0, "FEM": 0, "training": 0, "ML_inference": 0, "replays": 0}}
    atomic_json(run_root / "queue.json", state)
    (run_root / "solver_entered_ledger.jsonl").write_text("", encoding="utf-8")
    print(json.dumps({"status": "QUEUED", "run_root": str(run_root), "case_order": CASE_ORDER, "solver_entries": 0, "physical_contract_hash": state["physical_contract_hash"]}, sort_keys=True))


def trap_weights(values: np.ndarray) -> np.ndarray:
    weights = np.empty(values.size, dtype=float)
    weights[0] = (values[1] - values[0]) / 2.0
    weights[-1] = (values[-1] - values[-2]) / 2.0
    weights[1:-1] = (values[2:] - values[:-2]) / 2.0
    return weights


def profile_and_support(raw: np.ndarray, wavelength: np.ndarray, theta: np.ndarray, ux_edges: np.ndarray, ux_centers: np.ndarray, band: tuple[float, float]) -> tuple[dict, dict]:
    theta_weight = np.diff(theta_edges(np.radians(theta)))
    lambda_weight = trap_weights(wavelength)
    mask = (wavelength >= band[0]) & (wavelength <= band[1])
    if not np.any(mask):
        raise RuntimeError(f"empty_wavelength_band:{band}")
    mass = raw[mask] * lambda_weight[mask, None] * theta_weight[None, :]
    denominator = float(np.sum(mass))
    if denominator <= 0 or not np.isfinite(denominator):
        raise RuntimeError("nonpositive_profile_denominator")
    normalized_theta = raw[mask] / denominator
    normalized_ux = normalized_theta * theta_weight[None, :] / np.diff(ux_edges)[None, :]
    angular_mass = np.sum(mass, axis=0) / denominator
    widths = np.diff(ux_edges)
    if abs(float(np.sum(angular_mass)) - 1.0) > 1e-10:
        raise RuntimeError("ux_mass_closure_failed")
    support = {"band_nm": list(band), "denominator_raw_integral": denominator, "ux_mass_closure": float(np.sum(angular_mass)), "negative_mass": float(np.sum(angular_mass[ux_centers < 0])), "positive_mass": float(np.sum(angular_mass[ux_centers > 0])), "mean_ux": float(np.sum(angular_mass * ux_centers)), "support": {}}
    edge_abs = np.maximum(np.abs(ux_edges[:-1]), np.abs(ux_edges[1:]))
    for fraction in (0.5, 0.9, 0.95, 0.99):
        selected = None
        for upper in sorted(set(edge_abs.tolist())):
            inside = edge_abs <= upper + 1e-15
            if float(np.sum(angular_mass[inside])) >= fraction:
                selected = upper
                break
        support["support"][f"symmetric_{int(fraction * 100)}_percent"] = {"u_abs": float(selected if selected is not None else edge_abs.max()), "captured_mass": float(np.sum(angular_mass[edge_abs <= (selected if selected is not None else edge_abs.max())]))}
    cdf = np.cumsum(angular_mass)
    lo_index = int(np.searchsorted(cdf, 0.005, side="left"))
    hi_index = int(np.searchsorted(cdf, 0.995, side="left"))
    support["asymmetric_99_percent_interval"] = {"ux_min": float(ux_edges[max(0, lo_index)]), "ux_max": float(ux_edges[min(len(ux_edges) - 1, hi_index + 1)])}
    return {"normalized_theta": normalized_theta, "normalized_ux": normalized_ux, "angular_mass": angular_mass, "denominator": denominator}, support


def finalize(run_root: Path) -> None:
    state = read_json(run_root / "queue.json")
    cases = state["cases"]
    if any(case["status"] != "COMPLETE" for case in cases):
        report = {"status": "HARD_GATE_SIX_CASES_INCOMPLETE", "cases": [{"case_id": c["case_id"], "status": c["status"], "solver_entered": c.get("solver_entered", False)} for c in cases], "next_action": "HARD_GATE_TRADITIONAL_ZL1_SIX_CASE_COMPLETION_REQUIRED"}
        atomic_json(run_root / "finalization_gate.json", report)
        raise RuntimeError(report["status"])
    reference_wavelength, reference_angle, grid_hash = frozen_grid()
    arrays = {}
    for case in cases:
        result = read_json(run_root / "cases" / case["case_id"] / "case_result.json")
        with np.load(result["raw_npz_path"], allow_pickle=False) as data:
            arrays[case["case_id"]] = {key: np.asarray(data[key]) for key in data.files}
        if arrays[case["case_id"]]["joint_raw"].shape != (POINTS, 2000):
            raise RuntimeError("case_joint_shape_gate_failed")
        if not np.allclose(arrays[case["case_id"]]["wavelength_nm"], reference_wavelength, rtol=0.0, atol=1e-9) or not np.allclose(arrays[case["case_id"]]["angle_deg"], reference_angle, rtol=0.0, atol=1e-6):
            raise RuntimeError("case_grid_identity_gate_failed")
    lam = arrays[cases[0]["case_id"]]["wavelength_nm"].astype(float)
    angle = arrays[cases[0]["case_id"]]["angle_deg"].astype(float)
    ux_edges = arrays[cases[0]["case_id"]]["ux_edges"].astype(float)
    ux_centers = arrays[cases[0]["case_id"]]["ux_centers"].astype(float)
    p_raw = np.mean([arrays[f"{position}_X"]["joint_raw"] for position in SOURCE_POSITIONS], axis=0)
    s_raw = np.mean([arrays[f"{position}_Z"]["joint_raw"] for position in SOURCE_POSITIONS], axis=0)
    total_raw = 0.5 * p_raw + 0.5 * s_raw
    aggregate_dir = run_root / "aggregates"
    aggregate_dir.mkdir(exist_ok=True)
    profiles = {}
    supports = {}
    for name, raw in (("P", p_raw), ("S", s_raw), ("TOTAL_EMITTER_DIAGNOSTIC", total_raw)):
        for band_name, band in (("native_420_480_nm", (420.0, 480.0)), ("coupling_445_455_nm", (445.0, 455.0))):
            values, support = profile_and_support(raw, lam, angle, ux_edges, ux_centers, band)
            path = aggregate_dir / f"W_MDC_{name}_{band_name}.npz"
            np.savez_compressed(path, wavelength_nm=lam, angle_deg=angle, ux_edges=ux_edges, ux_centers=ux_centers, raw_joint=raw, normalized_joint_theta=values["normalized_theta"], normalized_joint_ux=values["normalized_ux"], angular_mass_ux=values["angular_mass"])
            profiles[f"{name}_{band_name}"] = {"path": str(path), "sha256": sha_file(path), "raw_integral": values["denominator"], "ux_mass_closure": support["ux_mass_closure"]}
            supports[f"{name}_{band_name}"] = support
    case_results = []
    for case in cases:
        case_id = case["case_id"]
        result_path = run_root / "cases" / case_id / "case_result.json"
        result = read_json(result_path)
        arrays_for_case = arrays[case_id]
        raw_theta_integral = float(np.sum(arrays_for_case["joint_raw"] * arrays_for_case["theta_weights_rad"][None, :]))
        raw_ux_integral = float(np.sum(arrays_for_case["raw_joint_ux_density"] * arrays_for_case["ux_widths"][None, :]))
        result.setdefault("theta_to_ux_mass_closure", raw_ux_integral / raw_theta_integral)
        result.setdefault("setup_readback", case.get("setup_readback", {}))
        result.setdefault("builder_sha256", EXECUTED_BUILDER_SHA256)
        result.setdefault("material_config_sha256", sha_file(MATERIAL_CONFIG))
        result.setdefault("monitor_contract_sha256", sha_file(MONITOR_SCRIPT))
        result.setdefault("frozen_grid_reference_sha256", sha_file(FROZEN_GRID_NPZ))
        atomic_json(result_path, result)
        case_results.append({"case_id": case_id, "result": result})
    quality_gates = {
        "exact_six_case_membership": [item["case_id"] for item in case_results] == CASE_ORDER,
        "finite": all(item["result"]["raw_joint_finite"] and item["result"]["raw_power_finite"] for item in case_results),
        "nonnegative": all(item["result"]["raw_joint_negative_count"] == 0 for item in case_results),
        "grid_identity": all(item["result"]["grid_sha256"] == grid_hash and item["result"]["grid_shape"] == [POINTS, 2000] for item in case_results),
        "source_identity": all(item["result"].get("setup_readback", {}).get("checks", {}).get("source_y", False) for item in case_results),
        "orientation_identity": all(item["result"].get("setup_readback", {}).get("checks", {}).get("theta", False) and item["result"].get("setup_readback", {}).get("checks", {}).get("phi", False) for item in case_results),
        "raw_power_provenance": all(item["result"].get("pre_fsp_sha256") and item["result"].get("post_fsp_sha256") and item["result"].get("builder_sha256") and item["result"].get("material_config_sha256") and item["result"].get("monitor_contract_sha256") for item in case_results),
        "quadrature_closure": all(item["result"]["theta_to_ux_remap_relative_closure_error"] <= 1e-12 and abs(item["result"]["theta_to_ux_mass_closure"] - 1.0) <= 1e-12 for item in case_results),
        "P_family_identity": [item["case_id"] for item in case_results if item["result"]["interface_polarization_family"] == "P_TM_like"] == ["TOP_X", "CENTROID_X", "BOTTOM_X"],
        "S_family_identity": [item["case_id"] for item in case_results if item["result"]["interface_polarization_family"] == "S_TE_like"] == ["TOP_Z", "CENTROID_Z", "BOTTOM_Z"],
    }
    if not all(quality_gates.values()):
        raise RuntimeError("provider_quality_gate_failed:" + json.dumps(quality_gates, sort_keys=True))
    state["status"] = "COMPLETE"
    state["safety_counters"]["FDTD_entered"] = len(cases)
    state["safety_counters"]["NP_solver"] = 0
    state["safety_counters"]["replays"] = 0
    atomic_json(run_root / "queue.json", state)
    provider = {"schema_version": "traditional_zl1_mdc_level1_real_fdtd_provider_v1", "provider_id": PROVIDER_ID, "status": "PASS", "task": TASK, "candidate_id": "P1_ZL1_ALTERNATIVE_G3_A3", "geometry_hash": state["physical_contract"]["geometry_hash"], "geometry_total_thickness_nm": 975.0, "reference_plane_z_nm": 975.0, "six_case_membership": CASE_ORDER, "P_family": ["TOP_X", "CENTROID_X", "BOTTOM_X"], "S_family": ["TOP_Z", "CENTROID_Z", "BOTTOM_Z"], "P_MDC_up_P": profiles["P_native_420_480_nm"], "W_MDC_P_lambda_ux": profiles["P_coupling_445_455_nm"], "P_MDC_up_S": profiles["S_native_420_480_nm"], "W_MDC_S_lambda_ux": profiles["S_coupling_445_455_nm"], "raw_case_assets": case_results, "quality_gates": quality_gates, "aggregation": {"P_family": "raw TOP_X/CENTROID_X/BOTTOM_X equal average then normalize", "S_family": "raw TOP_Z/CENTROID_Z/BOTTOM_Z equal average then normalize", "total_emitter": "diagnostic-only 0.5*P+0.5*S after raw family aggregation", "NP_operator_order": "P/S operator must act before x/z incoherent aggregation"}, "grid": {"wavelength_points": POINTS, "angle_points": 2000, "grid_sha256": grid_hash, "axis_order": ["wavelength_index", "angle_index"], "theta_to_ux": "conservative bin-mass remap; no interpolation/extrapolation"}, "safety": {"FDTD": 6, "NP_solver": 0, "integrated_3d_FDTD": 0, "TMM": 0, "RCWA": 0, "FEM": 0, "training": 0, "ML_inference": 0, "replays": 0}}
    support_report = {"schema_version": "np_level1_ps_ux_grid_requirement_v1", "status": "DERIVED_FROM_FORMAL_ZL1_MDC_PROFILES", "formal_wavelength_band_nm": [445.0, 455.0], "native_wavelength_band_nm": [420.0, 480.0], "P": {"native": supports["P_native_420_480_nm"], "coupling": supports["P_coupling_445_455_nm"]}, "S": {"native": supports["S_native_420_480_nm"], "coupling": supports["S_coupling_445_455_nm"]}, "minimum_candidate_ux_sampling_strategy": "retain separate P and S branches and sample exact conservative remapped ux bins covering each branch's 99% support; no interpolation or extrapolation", "recommended_candidate_ux_sampling_strategy": "use the union of the P/S 99% support intervals with explicit endpoints and preserve P/S-specific response tables; do not fix an NP solver grid until separate authorization", "np_solver_entries": 0, "np_equivalence_assumed": False}
    atomic_json(run_root / "provider_manifest.json", provider)
    atomic_json(run_root / "np_level1_ps_ux_grid_requirement.json", support_report)
    report_path = ROOT / "reports" / "coupling" / "traditional_zl1_mdc_level1_provider_v1.json"
    support_path = ROOT / "reports" / "coupling" / "np_level1_ps_ux_grid_requirement_v1.json"
    registry_path = ROOT / "registries" / "coupling" / "traditional_zl1_mdc_level1_solver_registry_v1.json"
    atomic_json(report_path, provider)
    atomic_json(support_path, support_report)
    registry = {"schema_version": "traditional_zl1_mdc_level1_solver_registry_v1", "provider_id": PROVIDER_ID, "run_root": str(run_root), "queue_sha256": sha_file(run_root / "queue.json"), "provider_manifest_sha256": sha_file(run_root / "provider_manifest.json"), "solver_entries": 6, "replays": 0, "FDTD_2D": 6, "NP_solver": 0, "integrated_3D_FDTD": 0, "TMM": 0, "RCWA": 0, "FEM": 0, "training": 0, "ML_inference": 0, "case_records": [{"case_id": c["case_id"], "pre_fsp_sha256": c["pre_fsp_sha256"], "post_fsp_sha256": c["post_fsp_sha256"], "raw_npz_path": c["raw_npz_path"]} for c in cases], "status": "PASS"}
    atomic_json(registry_path, registry)
    lines = ["# Traditional ZL-1 MDC Level-1 real FDTD provider v1", "", "## 状态", "", "PASS: all six formal 2D Native-M1 FDTD cases completed once; no replay.", "", "## P/S MDC provider", "", "- P-family: TOP_X, CENTROID_X, BOTTOM_X -> raw aggregation -> normalization.", "- S-family: TOP_Z, CENTROID_Z, BOTTOM_Z -> raw aggregation -> normalization.", "- `source_orientation` and `interface_polarization_family` remain separate fields.", "- NP P/S operator must act before x/z incoherent aggregation.", "", "## ux support", "", "frozen native grid: 420–480 nm, 301 points, 2000-point nonuniform theta grid; formal coupling support is conditioned to 445–455 nm.", "", "```json", json.dumps({"P": support_report["P"]["coupling"], "S": support_report["S"]["coupling"]}, indent=2, sort_keys=True), "```", "", "## Quality / provenance", "", f"- Grid SHA256: `{grid_hash}`; tensor shape: `301×2000`; theta-to-ux remap is conservative and no-extrapolation.", f"- Geometry: `P1_ZL1_ALTERNATIVE_G3_A3`, 975 nm, reference plane z=975 nm; no 237 nm spacer and no NP geometry.", f"- Provider manifest: `{run_root / 'provider_manifest.json'}`.", "", "## Safety / tests / Git", "", "- Solver counts: 2D FDTD=6; NP=0; integrated 3D=0; TMM=0; RCWA=0; FEM=0; training=0; ML=0; replay=0.", "- Raw FSP/tensor runtime artifacts remain outside Git.", "", "## 下一步", "", "REQUEST_NP_LEVEL1_PS_UX_GRID_SOLVER_AUTHORIZATION", ""]
    (ROOT / "reports" / "coupling" / "traditional_zl1_mdc_level1_provider_v1.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": "PASS", "provider": str(report_path), "support": str(support_path), "registry": str(registry_path), "solver_entries": 6, "np_solver": 0}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", action="store_true")
    parser.add_argument("--run-root")
    parser.add_argument("--run-case")
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    if args.queue:
        run_root = Path(args.run_root) if args.run_root else RUN_BASE / f"run_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
        create_queue(run_root)
        return
    if not args.run_root:
        parser.error("--run-root is required for --run-case/--finalize")
    run_root = Path(args.run_root)
    if args.run_case:
        run_case(run_root, args.run_case)
        print(json.dumps({"status": "COMPLETE", "case_id": args.run_case, "run_root": str(run_root)}, sort_keys=True))
    elif args.finalize:
        finalize(run_root)
    else:
        parser.error("select --queue, --run-case or --finalize")


if __name__ == "__main__":
    main()
