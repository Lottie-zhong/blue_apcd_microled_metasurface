from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

import numpy as np

ML = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
SOURCE = Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2")
BASE_PATH = SOURCE / r"scripts\run_mdc_hf_surrogate_v3_al64_joint_profile_v1.py"
MONITOR_PATH = SOURCE / r"scripts\mdc_fdtd_2d_monitor_contract_v1.py"
NATIVE_PATH = SOURCE / r"scripts\run_mdc_native_m1_2d_dipole_device_comparison_v1.py"
CONT = ML / r"outputs\coupling_ml\M0_LEVEL1_LEVEL2_CONTRACT_RECONCILIATION_V1\M0F_MINIMAL_LEVEL1_CONTRACT_REPAIR_ACQUISITION\M0F_CONTINUATION_AFTER_COMPONENT_RULING_V1"
sys.path.insert(0, str(SOURCE / "scripts"))
spec = importlib.util.spec_from_file_location("frozen_mdc_builder", BASE_PATH)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
if not hasattr(np, "trapezoid"):
    np.trapezoid = np.trapz


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + chr(10), encoding="utf-8")
    os.replace(tmp, path)


def powershell_json(command):
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    try:
        value = json.loads(proc.stdout) if proc.stdout.strip() else []
    except Exception:
        value = []
    return value if isinstance(value, list) else [value]


def resource_snapshot(admitted_fdtd_slots):
    procs = powershell_json(
        "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine,CreationDate | ConvertTo-Json -Compress"
    )
    fluent_names = {"fluent.exe", "cx2510.exe", "fl2510.exe", "smpd.exe"}
    fluent = [
        p for p in procs
        if str(p.get("Name", "")).lower() in fluent_names
        or str(p.get("Name", "")).lower().startswith("fl_mpi")
    ]
    fdtd = [
        p for p in procs
        if str(p.get("Name", "")).lower().startswith("fdtd-engine")
        or str(p.get("Name", "")).lower() == "fdtd-solutions.exe"
    ]
    heavy = [
        p for p in procs
        if any(token in (str(p.get("Name", "")) + " " + str(p.get("CommandLine", ""))).lower()
               for token in ["matlab", "comsol", "lumerical", "fdtd", "fluent", "mathematica", "ansysedt"])
        and not str(p.get("Name", "")).lower().startswith("msedgewebview2")
        and p not in fluent and p not in fdtd
    ]
    os_info = powershell_json(
        "Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize,FreePhysicalMemory | ConvertTo-Json -Compress"
    )[0]
    cpu_info = powershell_json(
        "Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor | Where-Object Name -eq '_Total' | Select-Object PercentProcessorTime | ConvertTo-Json -Compress"
    )[0]
    total_mem = float(os_info.get("TotalVisibleMemorySize") or 0) / 1024 / 1024
    free_mem = float(os_info.get("FreePhysicalMemory") or 0) / 1024 / 1024
    logical_cpu = int(os.cpu_count() or 0)
    cpu_pct = float(cpu_info.get("PercentProcessorTime") or 0)
    registry_path = Path(r"D:\project\apcd_global_fdtd_slot_registry_v1.json")
    registry = {}
    if registry_path.exists():
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
        except Exception:
            registry = {}
    active = []
    if isinstance(registry, dict):
        for key in ("active_slots", "active", "leases", "entries", "jobs", "records"):
            value = registry.get(key)
            if isinstance(value, list):
                active.extend(value)
            elif isinstance(value, dict):
                active.extend(value.values())

    def active_item(item):
        text = json.dumps(item, ensure_ascii=False).lower()
        return any(key in text for key in ("active", "running", "entered")) and not any(
            key in text for key in ("complete", "finished", "closed", "released")
        )

    active = [item for item in active if active_item(item)]
    cap = 3
    active_registry_slots = len(active)
    slots_left = max(0, cap - active_registry_slots)
    threads = 12
    projected_cpu = cpu_pct + slots_left * threads / logical_cpu * 100 if logical_cpu else 100
    if logical_cpu >= threads and projected_cpu <= 80:
        cpu_supported = 3
    elif logical_cpu:
        cpu_supported = max(0, min(3, int((80 - cpu_pct) * logical_cpu / (threads * 100))))
    else:
        cpu_supported = 0
    reserve_gib = 32.0
    memory_supported = (
        3 if free_mem - slots_left * reserve_gib >= reserve_gib
        else max(0, min(3, int(free_mem / reserve_gib) - 1))
    )
    resource_headroom = max(0, min(slots_left, cpu_supported, memory_supported))
    safe_new_slots = min(max(0, cap - active_registry_slots), resource_headroom)
    return {
        "timestamp_utc": now(),
        "authority": "RESOURCE-AWARE MAXIMUM SAFE SLOT UTILIZATION",
        "fluent_detected": bool(fluent),
        "fluent_process_count": len(fluent),
        "fluent_processes": fluent,
        "system_logical_cpu": logical_cpu,
        "system_cpu_utilization_percent_total": cpu_pct,
        "available_memory_before_admission": free_mem,
        "available_memory_before_admission_gib": free_mem,
        "total_physical_memory_gib": total_mem,
        "active_apcd_fdtd_slots_before_admission": active_registry_slots,
        "observed_fdtd_engine_processes_before_admission": len(fdtd),
        "other_heavy_scientific_process_count": len(heavy),
        "other_heavy_scientific_processes": heavy,
        "production_hard_cap": cap,
        "job_slot_contract": "12 MPI x 1 thread = 1 APCD FDTD slot",
        "resource_policy": {
            "projected_cpu_ceiling_percent": 80.0,
            "per_slot_reserved_memory_gib": reserve_gib,
            "cpu_headroom_supported_slots": cpu_supported,
            "memory_headroom_supported_slots": memory_supported,
            "projected_cpu_percent_at_cap": projected_cpu,
        },
        "resource_headroom_supported_slots": resource_headroom,
        "safe_new_slots": safe_new_slots,
        "admitted_fdtd_slots": admitted_fdtd_slots,
        "fluent_protection": "NO_TERMINATE_NO_PAUSE_NO_AFFINITY_CHANGE_NO_PRIORITY_CHANGE_NO_INTERFERENCE",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()
    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    case_id = manifest["case_id"]
    case_dir = Path(manifest["output_root"])
    case_dir.mkdir(parents=True, exist_ok=True)
    pre_fsp = case_dir / "attempt_1__pre.fsp"
    post_fsp = case_dir / "attempt_1__post.fsp"
    raw_npz = case_dir / "attempt_1__raw.npz"
    entry_path = case_dir / "M0F_DIRECT_MDC_SOLVER_ENTRY_V1.json"
    failure_path = case_dir / "case_failure.json"
    if manifest.get("pilot") is True:
        raise RuntimeError("remaining_runner_rejects_pilot_manifest")
    if not manifest.get("solver_authorized") or manifest.get("attempt_budget") != 1 or manifest.get("retry_allowed"):
        raise RuntimeError("remaining_manifest_authorization_mismatch")
    if manifest.get("solver_entered") is True or entry_path.exists():
        raise RuntimeError("solver_already_entered_no_rerun")
    expected_geometry = "2743ba872a6865519e555f99131220415afb076d653db11f1fe2ef658286c7d8"
    contract = manifest["exact_contract"]
    if contract["geometry_hash"] != expected_geometry:
        raise RuntimeError("geometry_hash_mismatch")
    if raw_npz.exists() or (case_dir / "case_result.json").exists():
        raise RuntimeError("result_exists_no_rerun")
    sequence = [(str(pair[0]), float(pair[1])) for pair in contract["geometry_sequence_nm"]]
    structure = {
        "structure_key": expected_geometry[:16],
        "structure_id": "MDC_TARGET_GEOMETRY_2743",
        "kind": "target_mdc_stack",
        "sequence": sequence,
        "geometry_hash": expected_geometry,
        "total_thickness_nm": sum(item[1] for item in sequence),
        "layer_count": len(sequence),
        "realization_hash": hashlib.sha256(
            json.dumps({"geometry_hash": expected_geometry, "sequence": sequence, "material_policy": "MDC_NATIVE_M1"},
                       sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }
    case = {
        "case_id": case_id,
        "case_hash": manifest["physical_contract_hash"],
        "geometry_hash": expected_geometry,
        "geometry_id": "MDC_TARGET_GEOMETRY_2743",
        "source_position": contract["source_position"],
        "source_position_nm": str(contract["source_z_nm"]),
        "dipole_orientation": contract["source_orientation"],
        "case_uid": case_id,
    }
    base_sha = sha(BASE_PATH)
    monitor_sha = sha(MONITOR_PATH)
    native_sha = sha(NATIVE_PATH)
    material_sha = sha(base.MATERIAL_CONFIG)
    builder_contract = contract["builder_contract"]
    if (base_sha != builder_contract["builder_source_sha256"]
            or monitor_sha != builder_contract["monitor_source_sha256"]
            or native_sha != builder_contract["native_builder_source_sha256"]
            or material_sha != builder_contract["material_config_sha256"]):
        raise RuntimeError("frozen_source_sha_drift")
    physical_fields = {
        "case_id": case_id,
        "geometry_hash": expected_geometry,
        "geometry_sequence_nm": sequence,
        "source_position": contract["source_position"],
        "source_z_nm": float(contract["source_z_nm"]),
        "source_orientation": contract["source_orientation"],
        "source_lateral_condition": contract["source_lateral_condition"],
        "wavelength_grid_acquisition_nm": [420.0, 480.0, 301],
        "wavelength_grid_target_nm": contract["wavelength_grid_target_nm"],
        "interpolation": False,
        "normalization_contract": contract["normalization_contract"],
        "aggregation_contract": contract["aggregation_contract"],
        "reference_plane": contract["reference_plane"],
        "physical_order_mapping": contract["physical_order_mapping"],
        "source_class": contract["source_class"],
        "solver_contract": contract["solver_contract"],
        "builder_contract": {
            "builder_source_sha256": base_sha,
            "monitor_source_sha256": monitor_sha,
            "native_builder_source_sha256": native_sha,
            "material_config_sha256": material_sha,
        },
    }
    calculated_hash = hashlib.sha256(
        json.dumps(physical_fields, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if calculated_hash != manifest["physical_contract_hash"]:
        raise RuntimeError("physical_contract_hash_drift")

    lumapi = base.lumapi()
    session = None
    try:
        setup_session = lumapi.FDTD(hide=True)
        try:
            setup = base.build_case(setup_session, case, structure)
            setup_session.save(str(pre_fsp))
        finally:
            setup_session.close()
        pre_sha = sha(pre_fsp)
        session = lumapi.FDTD(hide=True)
        session.load(str(pre_fsp))
        readback = {
            "fdtd_count": int(session.getnamednumber("FDTD")),
            "upward_monitor_count": int(session.getnamednumber("upward_monitor")),
            "box_monitor_counts": {
                name: int(session.getnamednumber(name))
                for name in ("emit_box_12nm_top", "emit_box_12nm_bottom", "emit_box_12nm_left", "emit_box_12nm_right")
            },
            "fresh_load": "PASS",
        }
        if readback["fdtd_count"] != 1 or readback["upward_monitor_count"] != 1 or any(
            value != 1 for value in readback["box_monitor_counts"].values()
        ):
            raise RuntimeError("monitor_readback_failed")
        admission = resource_snapshot(admitted_fdtd_slots=1)
        admission_path = case_dir / "M0F_RESOURCE_ADMISSION_AT_SOLVER_ENTRY_V1.json"
        atomic_json(admission_path, admission)
        if admission["safe_new_slots"] < 1 or admission["active_apcd_fdtd_slots_before_admission"] >= 3:
            raise RuntimeError("resource_admission_blocked_before_solver_entry")
        entered_at = now()
        entry = {
            "schema_version": "M0F_DIRECT_MDC_SOLVER_ENTRY_V1",
            "case_id": case_id,
            "attempt_id": manifest["attempt_id"],
            "solver_entered": True,
            "solver_entered_at": entered_at,
            "pre_fsp_path": str(pre_fsp),
            "pre_fsp_sha256": pre_sha,
            "physical_contract_hash": manifest["physical_contract_hash"],
            "builder_source_sha256": base_sha,
            "adapter_script_path": str(Path(__file__)),
            "adapter_script_sha256": sha(Path(__file__)),
            "solver_contract": "12 MPI x 1 thread; one APCD FDTD slot",
            "resource_admission_path": str(admission_path),
            "resource_admission_sha256": sha(admission_path),
            "fluent_protection": admission["fluent_protection"],
            "source_worktrees_read_only": True,
            "no_raw_fsp_copy_from_source": True,
        }
        atomic_json(entry_path, entry)
        ledger = CONT / "M0F_DIRECT_MDC_CASE_ATTEMPT_LEDGER_V1.jsonl"
        with ledger.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + chr(10))
            stream.flush()
            os.fsync(stream.fileno())
        atomic_json(case_dir / "M0F_DIRECT_MDC_RUNTIME_STATE_V1.json", {
            "status": "RUNNING", "solver_entered": True, "case_id": case_id,
            "attempt_id": manifest["attempt_id"], "solver_entry_path": str(entry_path),
            "solver_entry_sha256": sha(entry_path),
        })
        session.run()
        session.save(str(post_fsp))
        post_sha = sha(post_fsp)
        monitor_name = "upward_monitor"
        freq = np.asarray(session.getdata(monitor_name, "f"), float).reshape(-1)
        wavelengths = 299792458.0 / freq * 1e9
        order = np.argsort(wavelengths)
        wavelengths = wavelengths[order]
        upward = base.monitor_contract.integrate_line_poynting_flux(
            base.monitor_contract.read_fields(session, monitor_name), "Linear X"
        )
        upward = np.asarray(upward, float).reshape(-1)[order]
        sides = {
            side: base.monitor_contract.integrate_line_poynting_flux(
                base.monitor_contract.read_fields(session, "emit_box_12nm_" + side),
                "Linear X" if side in ("top", "bottom") else "Linear Y",
            )
            for side in ("top", "bottom", "left", "right")
        }
        box = np.asarray(base.monitor_contract.calculate_box_outward_flux(sides)["net_outward"], float).reshape(-1)[order]
        if len(wavelengths) != base.POINTS or not np.all(np.isfinite(wavelengths)) or not np.all(np.isfinite(upward)) or not np.all(np.isfinite(box)):
            raise RuntimeError("raw_spectrum_invalid")
        angles, joint, _ = base.extract_joint(session, monitor_name, wavelengths, upward)
        spectral = np.trapezoid(joint, np.radians(angles), axis=1)
        angular = np.trapezoid(joint, np.radians(wavelengths), axis=0)
        np.savez_compressed(raw_npz, wavelength_nm=wavelengths, angle_deg=angles, joint_raw=joint,
                            spectral_marginal_raw=spectral, angular_marginal_raw=angular,
                            p_up_raw=upward, p_box_raw=box)
        target_grid = np.asarray(contract["wavelength_grid_target_nm"], float)
        target_indices = []
        target_mismatch = []
        for wavelength in target_grid:
            index = int(np.argmin(np.abs(wavelengths - wavelength)))
            target_indices.append(index)
            target_mismatch.append(float(wavelengths[index] - wavelength))
        if any(abs(value) > 1e-9 for value in target_mismatch):
            raise RuntimeError("target_grid_not_exact")
        result = {
            "schema_version": "M0F_DIRECT_MDC_CASE_RESULT_V1", "status": "COMPLETE", "case_id": case_id,
            "attempt_id": manifest["attempt_id"], "solver_entered": True, "solver_status": "COMPLETE",
            "solver_returned": True, "accepted": True, "geometry_hash": expected_geometry,
            "geometry_sequence_nm": sequence, "source_position": contract["source_position"],
            "source_position_nm": float(contract["source_z_nm"]), "dipole_orientation": contract["source_orientation"],
            "builder_source_path": str(BASE_PATH), "builder_source_sha256": base_sha,
            "adapter_script_path": str(Path(__file__)), "adapter_script_sha256": sha(Path(__file__)),
            "monitor_contract_path": str(MONITOR_PATH), "monitor_contract_sha256": monitor_sha,
            "native_builder_path": str(NATIVE_PATH), "native_builder_sha256": native_sha,
            "material_config_path": str(base.MATERIAL_CONFIG), "material_config_sha256": material_sha,
            "start_timestamp": entered_at, "end_timestamp": now(), "pre_fsp_path": str(pre_fsp),
            "pre_fsp_sha256": pre_sha, "post_fsp_path": str(post_fsp), "post_fsp_sha256": post_sha,
            "raw_npz_path": str(raw_npz), "raw_npz_sha256": sha(raw_npz), "fresh_load_status": "PASS",
            "object_readback": readback, "raw_spectral_output_status": "PASS",
            "raw_angular_output_status": "PASS", "joint_tensor_status": "PASS", "extraction_status": "PASS",
            "wavelength_points": int(len(wavelengths)), "wavelength_grid_min_nm": float(wavelengths.min()),
            "wavelength_grid_max_nm": float(wavelengths.max()),
            "wavelength_grid_step_nm": float(np.median(np.diff(wavelengths))),
            "target_wavelength_grid_nm": [float(value) for value in target_grid],
            "target_sample_indices": target_indices, "target_grid_mismatch_nm": target_mismatch,
            "angle_points": int(len(angles)), "joint_shape": [int(value) for value in joint.shape],
            "joint_nonfinite_ratio": float(np.mean(~np.isfinite(joint))),
            "joint_negative_count": int(np.sum(joint < 0)), "spectral_marginal_recovered_from_joint": True,
            "angular_marginal_recovered_from_joint": True, "p_up_raw_finite": bool(np.all(np.isfinite(upward))),
            "p_box_raw_finite": bool(np.all(np.isfinite(box))), "normalization_before_aggregation": False,
            "filter_identity": setup["filter_id"], "monitor_identity": setup["monitor_name"],
            "tensor_axis_order": setup["tensor_axis_order"], "tensor_units": setup["tensor_units"],
            "raw_upward_power_median": float(np.median(upward)), "raw_box_power_median": float(np.median(box)),
            "physical_contract_hash": manifest["physical_contract_hash"],
            "resource_admission_path": str(admission_path), "resource_admission_sha256": sha(admission_path),
            "solver_contract": "12 MPI x 1 thread; one entry; no retry", "retry_allowed": False,
            "source_worktrees_read_only": True, "no_raw_fsp_copy_from_source": True,
        }
        atomic_json(case_dir / "case_result.json", result)
        atomic_json(case_dir / "M0F_DIRECT_MDC_RUNTIME_STATE_V1.json", {
            "status": "COMPLETE", "solver_entered": True, "solver_returned": True,
            "solver_status": "COMPLETE", "case_id": case_id, "attempt_id": manifest["attempt_id"],
            "post_fsp_sha256": post_sha, "raw_npz_sha256": sha(raw_npz),
        })
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        solver_entered = entry_path.exists()
        failure = {
            "schema_version": "M0F_DIRECT_MDC_CASE_FAILURE_V1",
            "status": "FAILED_AFTER_ENTRY" if solver_entered else "FAILED_BEFORE_ENTRY",
            "case_id": case_id, "attempt_id": manifest["attempt_id"], "solver_entered": solver_entered,
            "error": repr(exc), "traceback": traceback.format_exc(),
            "pre_fsp_path": str(pre_fsp) if pre_fsp.exists() else "",
            "pre_fsp_sha256": sha(pre_fsp) if pre_fsp.exists() else "",
            "post_fsp_path": str(post_fsp) if post_fsp.exists() else "",
            "post_fsp_sha256": sha(post_fsp) if post_fsp.exists() else "",
        }
        atomic_json(failure_path, failure)
        print(json.dumps(failure, ensure_ascii=False, indent=2))
        raise
    finally:
        if session is not None:
            session.close()


if __name__ == "__main__":
    main()
