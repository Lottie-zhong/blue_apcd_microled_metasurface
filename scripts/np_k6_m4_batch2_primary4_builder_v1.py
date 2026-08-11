"""Build and independently audit the eight NP K6 M4 Primary4 setup files.

This is setup-only.  It opens the frozen 3PS Native-M1 source, changes only
the six pillar radii and source polarization angle for each logical case, and
never calls FDTD.run().  FSP files remain runtime artifacts.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, r"N:/Program Files/ANSYS Inc/v251/Lumerical/api/python")
import lumapi  # type: ignore


ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / r"outputs\np_k6_m4_batch2_primary4_hf_acquisition_v1"
PREFSP = OUT / "runtime_prefsp"
SOURCE = ROOT / r"outputs\np_k6_hf_p0_anchor_generator_v2_setup_v1\runtime_prefsp\RUN3A_P_PILOT_HF_V1.fsp"
SOURCE_EXPECTED_SHA = "d62db443982c13264e2e6a216a376c64b480135176c24700b73da1481cdcd063"
GENERATOR = "NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_3PS_V2"
STACK = "NP_K6_INDEPENDENT_STACK_PILOT_V1"
MESH_ID = "NP_K6_PILOT_FIXED_GRID_V1"
WAVELENGTHS = list(range(445, 456))
REQUIRED_OBJECTS = [
    "reflection_monitor", "transmission_monitor", "order_monitor", "field_450_monitor",
    "N1_DIAG_PML_LOWER", "N1_DIAG_LOWER_OUTSIDE", "N1_DIAG_LOWER_INSIDE",
    "N1_DIAG_UPPER_INSIDE", "N1_DIAG_UPPER_OUTSIDE", "N1_DIAG_PML_UPPER",
    "N1_DIAG_XZ_INDEX_449",
]
PILLAR_POSITIONS_NM = [-725, -435, -145, 145, 435, 725]
PRIMARY = [
    {
        "slot": 1, "role": "exploitation_1", "geometry_id": "K6X_D110_D125_D135_D150_D175_D190",
        "geometry_hash": "e599c908c3befb142dacc503b37f1aefc68655082078b987ae553e49f60ec84f",
        "diameters_nm": [110, 125, 135, 150, 175, 190],
    },
    {
        "slot": 2, "role": "exploitation_2", "geometry_id": "K6X_D120_D125_D180_D185_D190_D195",
        "geometry_hash": "50ad4213fdfa1bf1b1a353c55769ade406e6fdebf5a82de63c4bd7e0c7fc3e7c",
        "diameters_nm": [120, 125, 180, 185, 190, 195],
    },
    {
        "slot": 3, "role": "coverage_exploration", "geometry_id": "K6X_D120_D145_D200_D215_D220_D230",
        "geometry_hash": "269b86c19099935a4fe83452d0a05faf6296e1ec0d4b4f38325d07863d571033",
        "diameters_nm": [120, 145, 200, 215, 220, 230],
    },
    {
        "slot": 4, "role": "model_conflict_physics_stress", "geometry_id": "K6X_D140_D160_D165_D170_D180_D190",
        "geometry_hash": "0ac97060e42705949d81140172fb178bb0fee693903982773db4697ba86e5d0d",
        "diameters_nm": [140, 160, 165, 170, 180, 190],
    },
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def get_named(fd, name: str, prop: str):
    value = fd.getnamed(name, prop)
    return value.tolist() if hasattr(value, "tolist") else value


def object_names(fd) -> list[str]:
    fd.eval("groupscope('::model'); unselectall; selectall;")
    names: list[str] = []
    for obj in fd.getAllSelectedObjects():
        try:
            names.append(str(obj.name))
        except Exception:
            pass
    return sorted(names)


def material_readback(fd, name: str) -> dict:
    result = {"name": name, "type": str(fd.getmaterial(name, "type"))}
    try:
        sampled = fd.getmaterial(name, "sampled data")
        result["sampled_rows"] = len(sampled)
        result["sampled_data_sha256"] = digest(sampled.tolist() if hasattr(sampled, "tolist") else sampled)
    except Exception as exc:
        result["sampled_rows"] = 0
        result["sampled_data_error"] = repr(exc)
    return result


def monitor_readback(fd, name: str) -> dict:
    props = [
        "type", "monitor type", "x", "y", "z", "x span", "y span", "z span",
        "frequency points", "spatial interpolation", "override global monitor settings",
        "wavelength center", "wavelength span", "down sample X", "down sample Y", "down sample Z",
    ]
    result = {}
    for prop in props:
        try:
            result[prop] = get_named(fd, name, prop)
        except Exception as exc:
            result[prop] = f"UNAVAILABLE:{exc}"
    return result


def source_contract(fd) -> dict:
    return {prop: get_named(fd, "source_x_forward", prop) for prop in (
        "direction", "injection axis", "x", "y", "z", "x span", "y span",
        "wavelength start", "wavelength stop", "polarization angle")}


def fdtd_contract(fd) -> dict:
    return {prop: get_named(fd, "FDTD", prop) for prop in (
        "simulation time", "auto shutoff min", "mesh accuracy", "x span", "y span", "z span")}


def fixed_mesh_contract(fd) -> dict:
    props = ("x", "y", "z", "x span", "y span", "z span", "dx", "dy", "dz")
    return {prop: get_named(fd, "RUN3C_FIXED_NESTED_N2", prop) for prop in props}


def pillar_contract(fd, diameters: list[int]) -> list[dict]:
    result = []
    for index, diameter in enumerate(diameters):
        name = f"TiO2_pillar_{index}"
        result.append({
            "name": name,
            "x_nm": float(get_named(fd, name, "x") * 1e9),
            "y_nm": float(get_named(fd, name, "y") * 1e9),
            "z_min_nm": float(get_named(fd, name, "z min") * 1e9),
            "z_max_nm": float(get_named(fd, name, "z max") * 1e9),
            "diameter_nm": float(get_named(fd, name, "radius") * 2e9),
            "expected_diameter_nm": diameter,
            "expected_x_nm": PILLAR_POSITIONS_NM[index],
        })
    return result


def assert_frozen_contract(contract: dict, source: dict, case: dict, pol: str) -> list[str]:
    errors: list[str] = []
    fdt = contract["fdtd"]
    if abs(float(fdt["simulation time"]) - 3e-12) > 1e-18:
        errors.append("simulation_time_not_3ps")
    if abs(float(fdt["auto shutoff min"]) - 1e-5) > 1e-12:
        errors.append("auto_shutoff_not_1e-5")
    mesh = contract["fixed_mesh"]
    for prop, expected in (("dx", 5e-9), ("dy", 5e-9), ("dz", 5e-9)):
        if abs(float(mesh[prop]) - expected) > 1e-15:
            errors.append(f"{prop}_not_5nm")
    if contract["objects_missing"]:
        errors.append("required_objects_missing")
    if contract["source"]["direction"] != source["direction"] or contract["source"]["injection axis"] != source["injection axis"]:
        errors.append("source_direction_drift")
    for prop in ("wavelength start", "wavelength stop"):
        if abs(float(contract["source"][prop]) - float(source[prop])) > 1e-18:
            errors.append(f"{prop}_drift")
    expected_pol = 0.0 if pol == "p" else 90.0
    if abs(float(contract["source"]["polarization angle"]) - expected_pol) > 1e-9:
        errors.append("polarization_mapping")
    for material in contract["materials"].values():
        if material["type"] != "Sampled 3D data" or material.get("sampled_rows") != 101:
            errors.append("native_m1_material_drift")
    for pillar, expected in zip(contract["pillars"], case["diameters_nm"]):
        if abs(pillar["diameter_nm"] - expected) > 1e-6 or abs(pillar["x_nm"] - pillar["expected_x_nm"]) > 1e-6:
            errors.append("pillar_geometry_readback")
        if abs(pillar["z_min_nm"]) > 1e-6 or abs(pillar["z_max_nm"] - 500.0) > 1e-6:
            errors.append("pillar_height_readback")
    return errors


def main() -> None:
    if OUT.exists():
        raise RuntimeError(f"refusing to overwrite existing acquisition directory: {OUT}")
    if not SOURCE.exists() or sha256(SOURCE) != SOURCE_EXPECTED_SHA:
        raise RuntimeError(f"frozen source pre-FSP SHA mismatch: {SOURCE}")
    OUT.mkdir(parents=True, exist_ok=False)
    PREFSP.mkdir(parents=True, exist_ok=True)
    source_fd = lumapi.FDTD(str(SOURCE), hide=True)
    try:
        source_names = object_names(source_fd)
        missing = sorted(set(REQUIRED_OBJECTS) - set(source_names))
        source = {
            "path": str(SOURCE),
            "sha256": SOURCE_EXPECTED_SHA,
            "object_names": source_names,
            "objects_missing": missing,
            "fdtd": fdtd_contract(source_fd),
            "fixed_mesh": fixed_mesh_contract(source_fd),
            "source": source_contract(source_fd),
            "materials": {name: material_readback(source_fd, name) for name in ("APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1")},
            "monitors": {name: monitor_readback(source_fd, name) for name in REQUIRED_OBJECTS},
        }
    finally:
        source_fd.close()
    write_json(OUT / "source_lineage_audit.json", source)
    if source["objects_missing"]:
        raise RuntimeError(f"frozen source missing objects: {source['objects_missing']}")
    rows: list[dict] = []
    for case in PRIMARY:
        for pol in ("p", "s"):
            case_id = f"NP_K6_M4_B2_G{case['slot']:02d}_{pol.upper()}"
            setup_path = PREFSP / f"{case_id}.fsp"
            if setup_path.exists():
                raise RuntimeError(f"refusing setup overwrite: {setup_path}")
            fd = lumapi.FDTD(str(SOURCE), hide=True)
            changes = []
            try:
                for index, diameter in enumerate(case["diameters_nm"]):
                    name = f"TiO2_pillar_{index}"
                    old = float(get_named(fd, name, "radius"))
                    new = diameter * 0.5e-9
                    if abs(old - new) > 1e-20:
                        fd.setnamed(name, "radius", new)
                        changes.append({"object": name, "property": "radius", "from_m": old, "to_m": new})
                old_pol = float(get_named(fd, "source_x_forward", "polarization angle"))
                new_pol = 0.0 if pol == "p" else 90.0
                if abs(old_pol - new_pol) > 1e-12:
                    fd.setnamed("source_x_forward", "polarization angle", new_pol)
                    changes.append({"object": "source_x_forward", "property": "polarization angle", "from_deg": old_pol, "to_deg": new_pol})
                fd.save(str(setup_path))
            finally:
                fd.close()
            check = lumapi.FDTD(str(setup_path), hide=True)
            try:
                names = object_names(check)
                contract = {
                    "fdtd": fdtd_contract(check),
                    "fixed_mesh": fixed_mesh_contract(check),
                    "source": source_contract(check),
                    "materials": {name: material_readback(check, name) for name in ("APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1")},
                    "monitors": {name: monitor_readback(check, name) for name in REQUIRED_OBJECTS},
                    "pillars": pillar_contract(check, case["diameters_nm"]),
                    "objects_missing": sorted(set(REQUIRED_OBJECTS) - set(names)),
                }
            finally:
                check.close()
            errors = assert_frozen_contract(contract, source["source"], case, pol)
            setup_sha = sha256(setup_path)
            contract_core = {
                "schema_version": "np_k6_m4_batch2_primary4_case_contract_v1",
                "case_id": case_id,
                "attempt_id": "attempt_001",
                "logical_task_id": case_id,
                "case_slot": case["slot"],
                "role": case["role"],
                "geometry_id": case["geometry_id"],
                "geometry_hash": case["geometry_hash"],
                "diameters_nm": case["diameters_nm"],
                "polarization": pol,
                "u_x": 0.0,
                "k_y": 0.0,
                "generator_id": GENERATOR,
                "interface_stack_id": STACK,
                "production_mesh_id": MESH_ID,
                "source_lineage_path": str(SOURCE),
                "source_lineage_sha256": SOURCE_EXPECTED_SHA,
                "source_prefsp_path": str(setup_path),
                "source_prefsp_sha256": setup_sha,
                "setup_sha256": setup_sha,
                "wavelengths_nm": WAVELENGTHS,
                "fdtd_contract": contract["fdtd"],
                "fixed_mesh_contract": contract["fixed_mesh"],
                "source_contract": contract["source"],
                "material_contract": contract["materials"],
                "monitor_contract": contract["monitors"],
                "geometry_contract": contract["pillars"],
                "expected_changes": changes,
                "unexpected_differences": errors,
                "setup_only": True,
                "solver_authorized": True,
                "entered": False,
                "run_invocation_count": 0,
                "engine_completed": False,
                "controller_returned": False,
                "post_saved": False,
                "training_label": False,
                "quality_gate_pass": False,
                "diagnostic_only": False,
                "candidate_performance_label": True,
                "created_timestamp_utc": now(),
            }
            contract_hash = digest(contract_core)
            case_dir = OUT / "cases" / case_id
            ledger = {
                "schema_version": "np_k6_m4_batch2_primary4_attempt_ledger_v1",
                "case_id": case_id,
                "attempt_id": "attempt_001",
                "logical_task_id": case_id,
                "geometry_id": case["geometry_id"],
                "geometry_hash": case["geometry_hash"],
                "polarization": pol,
                "role": case["role"],
                "source_prefsp_path": str(setup_path),
                "source_prefsp_sha256": setup_sha,
                "physical_contract_hash": contract_hash,
                "generator_id": GENERATOR,
                "interface_stack_id": STACK,
                "entered": False,
                "run_invocation_count": 0,
                "engine_completed": False,
                "controller_returned": False,
                "post_saved": False,
                "training_label": False,
                "quality_gate_pass": False,
                "diagnostic_only": False,
                "candidate_performance_label": False,
                "status": "planned",
                "created_timestamp_utc": now(),
                "host": "DESKTOP-NNE313K",
                "python_path": r"N:\anaconda_envs\RCP_LCP\python.exe",
                "lumerical_version": "Ansys Lumerical 2025 R1",
            }
            audit = {
                "schema_version": "np_k6_m4_batch2_primary4_setup_readback_audit_v1",
                "case_id": case_id,
                "source_lineage_sha256": SOURCE_EXPECTED_SHA,
                "setup_sha256": setup_sha,
                "expected_changes": changes,
                "modified_properties": changes,
                "added_objects": [],
                "removed_objects": [],
                "unexpected_differences": errors,
                "independent_reload": True,
                "run_called": False,
                "save_called_after_reload": False,
                "actual_solver_grid_equality_proven": False,
                "readback": contract,
                "setup_diff_pass": not errors,
            }
            write_json(case_dir / "setup_contract.json", {**contract_core, "contract_hash": contract_hash})
            write_json(case_dir / "setup_readback_audit.json", audit)
            write_json(case_dir / "setup_checksum.json", {"path": str(setup_path), "sha256": setup_sha, "size_bytes": setup_path.stat().st_size, "sha_stable": sha256(setup_path) == setup_sha})
            write_json(case_dir / "attempt_ledger.json", ledger)
            rows.append({"case_id": case_id, "attempt_id": "attempt_001", "slot": case["slot"], "role": case["role"], "geometry_id": case["geometry_id"], "geometry_hash": case["geometry_hash"], "polarization": pol, "source_prefsp_path": str(setup_path), "source_prefsp_sha256": setup_sha, "physical_contract_hash": contract_hash, "setup_diff_pass": not errors, "entered": False, "run_invocation_count": 0})
    write_json(OUT / "batch2_setup_manifest.json", {"schema_version": "np_k6_m4_batch2_primary4_setup_manifest_v1", "stage": "NP_K6_M4_BATCH2_PRIMARY4_HF_ACQUISITION", "policy_hash": "a0f46c2da1f653c8a3798ee97bc70e4e3da7598dda5bc9392b76fc4a2128d5d7", "generator_id": GENERATOR, "interface_stack_id": STACK, "production_mesh_id": MESH_ID, "source_lineage_path": str(SOURCE), "source_lineage_sha256": SOURCE_EXPECTED_SHA, "wavelengths_nm": WAVELENGTHS, "u_x": 0.0, "k_y": 0.0, "case_count": len(rows), "logical_case_count": len(rows), "cases": rows, "solver_entered": 0, "run_invocations": 0, "sealed_target_reads": 0, "setup_only": True, "created_timestamp_utc": now()})
    with (OUT / "primary4_case_registry.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    write_json(OUT / "solver_zero_audit.json", {"schema_version": "np_k6_m4_batch2_solver_zero_audit_v1", "fdtd_run_invocations": 0, "lumapi_run_invocations": 0, "sealed_target_reads": 0, "case_count": 8, "setup_only": True, "batch2_started": False})
    write_json(OUT / "state.json", {"schema_version": "np_k6_m4_batch2_state_v1", "status": "READY_FOR_NP_K6_M4_BATCH2_PRIMARY4_SERIAL_EXECUTION", "logical_case_count": 8, "accepted_case_count": 0, "solver_entered": 0, "run_invocations": 0, "sealed_target_reads": 0, "m5_training_started": False, "first6_first8_authorized": False, "setup_diff_all_pass": all(row["setup_diff_pass"] for row in rows)})
    if not all(row["setup_diff_pass"] for row in rows):
        raise RuntimeError("setup contract drift: " + json.dumps([row for row in rows if not row["setup_diff_pass"]], indent=2))
    print(json.dumps({"status": "READY_FOR_NP_K6_M4_BATCH2_PRIMARY4_SERIAL_EXECUTION", "cases": rows, "solver_entered": 0}, indent=2))


if __name__ == "__main__":
    main()
