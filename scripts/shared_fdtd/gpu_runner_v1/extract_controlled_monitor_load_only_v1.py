from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path

import numpy as np


ROUTE_VERSION = "APCD_GPU_RUNNER_VERSIONED_CONTROLLED_ADMISSION_V1"
CASE_ID = "K6V1_EXT02_TWO_AIR_PLANES_DIAG"
ATTEMPT_ID = "attempt_001"
MONITOR_NAME = "EXT02_POSTNP_DIAG_Z2000"
EXISTING_MONITOR_NAME = "MON_POSTNP"
REFERENCE_PLANE_NM = 1722.0
CONFIGURED_MONITOR_Z_NM = 2000.0
EXPECTED_WAVELENGTH_NM = np.arange(440.0, 461.0, 1.0)
COMPONENTS = ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz")
VECTOR_COMPONENTS = {"Ex": 0, "Ey": 1, "Ez": 2, "Hx": 0, "Hy": 1, "Hz": 2}


class MonitorExtractionError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise MonitorExtractionError("BUNDLE_JSON_INVALID:" + str(path)) from exc
    if not isinstance(value, dict):
        raise MonitorExtractionError("BUNDLE_JSON_SCHEMA_INVALID:" + str(path))
    return value


def validate_bundle_identity(manifest: dict, status: dict, validation: dict,
                             pre_entry: dict, process: dict) -> str:
    if (manifest.get("case_id"), manifest.get("attempt_id")) != (CASE_ID, ATTEMPT_ID):
        raise MonitorExtractionError("BUNDLE_CASE_ATTEMPT_MISMATCH")
    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise MonitorExtractionError("BUNDLE_RUN_ID_MISSING")
    if any(record.get(key) != expected for record, key, expected in (
        (status, "case_id", CASE_ID), (status, "attempt_id", ATTEMPT_ID),
        (status, "run_id", run_id), (validation, "run_id", run_id),
        (pre_entry, "run_id", run_id),
        (process, "case_id", CASE_ID), (process, "attempt_id", ATTEMPT_ID),
    )):
        raise MonitorExtractionError("BUNDLE_PROVENANCE_IDENTITY_MISMATCH")
    return run_id


def _finite_numeric(value, label: str) -> np.ndarray:
    array = np.asarray(value)
    if array.size == 0 or not np.issubdtype(array.dtype, np.number):
        raise MonitorExtractionError("MONITOR_ARRAY_INVALID:" + label)
    if not np.all(np.isfinite(array)):
        raise MonitorExtractionError("MONITOR_ARRAY_NONFINITE:" + label)
    return array


def validate_lumerical_results(e_result: dict, h_result: dict) -> dict:
    """Validate named-monitor E/H API data and normalize its axes without changing values."""
    if not isinstance(e_result, dict) or not isinstance(h_result, dict):
        raise MonitorExtractionError("MONITOR_RESULT_NOT_A_DATASET")
    if "E" not in e_result or "H" not in h_result:
        raise MonitorExtractionError("MONITOR_E_OR_H_RESULT_MISSING")

    coords = {}
    for key in ("x", "y", "z", "lambda", "f"):
        if key not in e_result or key not in h_result:
            raise MonitorExtractionError("MONITOR_COORDINATE_MISSING:" + key)
        e_coord = _finite_numeric(e_result[key], "E." + key).reshape(-1)
        h_coord = _finite_numeric(h_result[key], "H." + key).reshape(-1)
        if e_coord.shape != h_coord.shape or not np.allclose(e_coord, h_coord, rtol=0.0, atol=1e-15):
            raise MonitorExtractionError("E_H_COORDINATE_MISMATCH:" + key)
        coords[key] = e_coord

    fields_e = _finite_numeric(e_result["E"], "E")
    fields_h = _finite_numeric(h_result["H"], "H")
    expected_shape = (coords["x"].size, coords["y"].size, coords["z"].size,
                      coords["f"].size, 3)
    if fields_e.shape != expected_shape or fields_h.shape != expected_shape:
        raise MonitorExtractionError("MONITOR_FIELD_SHAPE_MISMATCH")
    if coords["z"].size != 1:
        raise MonitorExtractionError("MONITOR_NOT_SINGLE_Z_PLANE")
    if coords["f"].size != 21 or coords["lambda"].size != 21:
        raise MonitorExtractionError("MONITOR_SPECTRUM_LENGTH_MISMATCH")
    wavelength_nm = coords["lambda"] * 1e9
    if not np.allclose(np.sort(wavelength_nm), EXPECTED_WAVELENGTH_NM,
                       rtol=0.0, atol=1e-6):
        raise MonitorExtractionError("MONITOR_WAVELENGTH_GRID_MISMATCH")
    if np.any(coords["f"] <= 0.0) or np.any(coords["lambda"] <= 0.0):
        raise MonitorExtractionError("MONITOR_SPECTRUM_NONPOSITIVE")
    for key in ("x", "y"):
        if coords[key].size < 2 or np.any(np.diff(coords[key]) <= 0.0):
            raise MonitorExtractionError("MONITOR_SPATIAL_GRID_INVALID:" + key)

    fields = {}
    for name, component_index in VECTOR_COMPONENTS.items():
        source = fields_e if name.startswith("E") else fields_h
        fields[name] = np.asarray(source[..., component_index], dtype=np.complex128)
    return {
        "coordinates_m": {key: coords[key] for key in ("x", "y", "z")},
        "wavelength_m": coords["lambda"],
        "frequency_hz": coords["f"],
        "fields": fields,
        "field_shape": list(fields_e.shape),
    }


def find_h5_monitor_group(h5_path: Path, normalized_result: dict) -> str:
    """Match the named FSP result to exactly one durable H5 monitor group by coordinates."""
    try:
        import h5py
    except ImportError as exc:
        raise MonitorExtractionError("H5PY_MISSING") from exc

    xyz = normalized_result["coordinates_m"]
    nx, ny, nz = (xyz[axis].size for axis in ("x", "y", "z"))
    nf = normalized_result["frequency_hz"].size
    expected_shape = (nz, ny, nx, 2 * nf)
    matched = []
    matched_invalid = []
    try:
        with h5py.File(h5_path, "r") as h5:
            names = [name for name in h5.keys()
                     if re.fullmatch(r"Monitor\d+", str(name)) and isinstance(h5[name], h5py.Group)]
            if not names:
                raise MonitorExtractionError("H5_MONITOR_GROUPS_MISSING")
            for name in names:
                group = h5[name]
                if any(key not in group for key in ("x", "y", "z")):
                    continue
                # The production run_output.h5 sidecar stores x/y/z in micrometers;
                # FDTD API getresult returns SI meters. Verify the observed conversion.
                group_coords = {key: np.asarray(group[key][...]).reshape(-1) * 1e-6
                                for key in ("x", "y", "z")}
                if any(value.size == 0 or not np.all(np.isfinite(value))
                       for value in group_coords.values()):
                    continue
                same_grid = all(
                    group_coords[key].shape == xyz[key].shape
                    and np.allclose(group_coords[key], xyz[key], rtol=0.0, atol=1e-12)
                    for key in ("x", "y", "z")
                )
                if not same_grid:
                    continue
                problems = []
                for component in COMPONENTS:
                    if component not in group:
                        problems.append("MISSING:" + component)
                        continue
                    dataset = group[component]
                    if dataset.shape != expected_shape or not np.issubdtype(dataset.dtype, np.number):
                        problems.append("SHAPE_OR_DTYPE:" + component)
                        continue
                    values = np.asarray(dataset[...])
                    if not np.all(np.isfinite(values)):
                        problems.append("NONFINITE:" + component)
                if problems:
                    matched_invalid.append((name, problems))
                else:
                    matched.append(name)
    except MonitorExtractionError:
        raise
    except Exception as exc:
        raise MonitorExtractionError("H5_BUNDLE_CORRUPT_OR_UNREADABLE") from exc
    if matched_invalid:
        raise MonitorExtractionError("H5_MATCHED_MONITOR_SCHEMA_INVALID:" + repr(matched_invalid))
    if len(matched) != 1:
        raise MonitorExtractionError("H5_MONITOR_GRID_MATCH_COUNT:" + str(len(matched)))
    return matched[0]


def validate_completed_bundle(run_dir: Path) -> dict:
    run_dir = Path(run_dir).resolve(strict=True)
    required = {
        "run_fsp": run_dir / "run.fsp",
        "run_output_h5": run_dir / "run" / "run_output.h5",
        "manifest": run_dir / "manifest.json",
        "status": run_dir / "status.json",
        "validation": run_dir / "validation.json",
        "hashes": run_dir / "hashes.json",
        "setup_validation": run_dir / "setup_validation.json",
        "pre_entry_revalidation": run_dir / "pre_entry_revalidation.json",
        "truth_h5": run_dir / "truth.h5",
        "solver_log": run_dir / "solver.log",
        "solver_stdout": run_dir / "run_p0.log",
        "process_exit_provenance": run_dir / "gpu_standalone" / "forensics" / "process_exit_provenance.json",
        "runtime_timeline": run_dir / "gpu_standalone" / "forensics" / "runtime_timeline.jsonl",
    }
    for label, path in required.items():
        if not path.is_file() or path.stat().st_size == 0:
            raise MonitorExtractionError("BUNDLE_FILE_MISSING_OR_EMPTY:" + label)
    manifest = read_json(required["manifest"])
    status = read_json(required["status"])
    validation = read_json(required["validation"])
    hashes = read_json(required["hashes"])
    setup = read_json(required["setup_validation"])
    pre_entry = read_json(required["pre_entry_revalidation"])
    process = read_json(required["process_exit_provenance"])
    run_id = validate_bundle_identity(manifest, status, validation, pre_entry, process)
    if (status.get("state") != "DONE" or status.get("solver_entered") is not True
            or status.get("solver_invocations") != 1):
        raise MonitorExtractionError("BUNDLE_NOT_ONE_COMPLETED_SOLVER_ENTRY")
    if any(validation.get(key) is not True for key in
           ("fresh_load_verified", "monitors_valid", "state_valid", "scientific_valid")):
        raise MonitorExtractionError("BUNDLE_TRUTH_NOT_VALIDATED")
    for key, path in (
        ("manifest_sha256", required["manifest"]),
        ("run_fsp_sha256", required["run_fsp"]),
        ("truth_h5_sha256", required["truth_h5"]),
        ("validation_sha256", required["validation"]),
        ("setup_validation_sha256", required["setup_validation"]),
        ("pre_entry_revalidation_sha256", required["pre_entry_revalidation"]),
        ("run_output_h5_sha256", required["run_output_h5"]),
    ):
        if hashes.get(key) != sha256_file(path):
            raise MonitorExtractionError("BUNDLE_HASH_MISMATCH:" + key)

    start = setup.get("start_time_revalidation")
    if (pre_entry.get("result") != "PASS"
            or pre_entry.get("route_version") != ROUTE_VERSION
            or pre_entry.get("case_id") != CASE_ID
            or pre_entry.get("attempt_id") != ATTEMPT_ID
            or pre_entry.get("control_generation_sha256") !=
                (start or {}).get("control_generation_sha256")
            or pre_entry.get("control_generation_sha256") !=
                status.get("pre_entry_control_generation_sha256")):
        raise MonitorExtractionError("BUNDLE_FINAL_PRE_ENTRY_REVALIDATION_INVALID")
    readback = setup.get("setup_readback")
    added = readback.get("added_monitor") if isinstance(readback, dict) else None
    if (setup.get("result") != "PASS" or not isinstance(start, dict)
            or start.get("result") != "PASS" or start.get("preflight_only") is not False
            or start.get("route_version") != ROUTE_VERSION
            or start.get("case_id") != CASE_ID or start.get("attempt_id") != ATTEMPT_ID
            or not isinstance(added, dict) or added.get("name") != MONITOR_NAME
            or added.get("actual_sampled_z_status") not in
                ("PENDING_POST_SOLVER_READBACK", "UNAVAILABLE_BEFORE_SOLVER")
            or added.get("components") != list(COMPONENTS)
            or float(added.get("z_nm", math.nan)) != CONFIGURED_MONITOR_Z_NM
            or float(added.get("reference_plane_nm", math.nan)) != REFERENCE_PLANE_NM):
        raise MonitorExtractionError("BUNDLE_CONTROLLED_SETUP_PROVENANCE_MISMATCH")

    child = process.get("child")
    descendants = process.get("descendants")
    if (process.get("reason") != "CHILD_RETURNED" or not isinstance(child, dict)
            or not isinstance(child.get("pid"), int) or child.get("return_code") != 0
            or not isinstance(descendants, list)):
        raise MonitorExtractionError("BUNDLE_SOLVER_PROCESS_LINEAGE_INVALID")
    engine_gpu_seen = False
    for row in descendants:
        if not isinstance(row, dict) or row.get("name") != "fdtd-engine-msmpi.exe":
            continue
        snapshots = [row.get("first"), row.get("last")]
        command_lines = [snap.get("CommandLine", "") for snap in snapshots if isinstance(snap, dict)]
        if any("-gpu" in str(command).lower() for command in command_lines):
            engine_gpu_seen = True
            break
    if not engine_gpu_seen:
        raise MonitorExtractionError("BUNDLE_GPU_ENGINE_LINEAGE_MISSING")

    return {
        "run_dir": run_dir,
        "files": required,
        "manifest": manifest,
        "status": status,
        "validation": validation,
        "hashes": hashes,
        "setup_validation": setup,
        "pre_entry_revalidation": pre_entry,
        "process_exit_provenance": process,
        "start_time_revalidation": start,
        "added_monitor": added,
        "run_id": run_id,
    }


def monitor_setup_parameters(setup_validation: dict, monitor_name: str) -> dict:
    if monitor_name == MONITOR_NAME:
        readback = setup_validation.get("setup_readback", {}).get("added_monitor")
    elif monitor_name == EXISTING_MONITOR_NAME:
        readback = (setup_validation.get("setup_readback", {})
                    .get("existing_monitor_readbacks", {})
                    .get(EXISTING_MONITOR_NAME, {}).get("base"))
    else:
        raise MonitorExtractionError("MONITOR_NOT_AUTHORIZED:" + str(monitor_name))
    if (not isinstance(readback, dict) or readback.get("name") != monitor_name
            or readback.get("components") != list(COMPONENTS)
            or readback.get("enabled") != 1.0
            or readback.get("monitor_type") != "2D Z-normal"):
        raise MonitorExtractionError("MONITOR_SETUP_READBACK_INVALID:" + monitor_name)
    try:
        configured_z_nm = float(readback["z_nm"])
        reference_plane_nm = float(readback["reference_plane_nm"])
    except (KeyError, TypeError, ValueError) as exc:
        raise MonitorExtractionError("MONITOR_SETUP_COORDINATE_MISSING:" + monitor_name) from exc
    return {"configured_z_nm": configured_z_nm, "reference_plane_nm": reference_plane_nm}


def extraction_output_directory(run_dir: Path, output_subdir: str) -> Path:
    run_root = Path(run_dir).resolve(strict=True)
    relative = Path(output_subdir)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise MonitorExtractionError("EXTRACTION_OUTPUT_PATH_UNSAFE")
    output_dir = (run_root / relative).resolve()
    try:
        output_dir.relative_to(run_root)
    except ValueError as exc:
        raise MonitorExtractionError("EXTRACTION_OUTPUT_PATH_UNSAFE") from exc
    return output_dir


def extract_ext02_monitor(run_dir: Path, monitor_name: str = MONITOR_NAME,
                          output_subdir: str = "monitor_extraction") -> tuple[Path, Path, dict]:
    bundle = validate_completed_bundle(run_dir)
    monitor_setup = monitor_setup_parameters(bundle["setup_validation"], monitor_name)
    output_dir = extraction_output_directory(bundle["run_dir"], output_subdir)
    run_fsp = bundle["files"]["run_fsp"]
    h5_path = bundle["files"]["run_output_h5"]
    fsp_sha_before = sha256_file(run_fsp)
    h5_sha_before = sha256_file(h5_path)

    api_path = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
    if str(api_path) not in sys.path:
        sys.path.insert(0, str(api_path))
    try:
        import lumapi
    except ImportError as exc:
        raise MonitorExtractionError("LUMAPI_MISSING") from exc

    try:
        with lumapi.FDTD(hide=True) as fd:
            fd.load(str(run_fsp))
            e_result = fd.getresult(monitor_name, "E")
            h_result = fd.getresult(monitor_name, "H")
    except Exception as exc:
        raise MonitorExtractionError("NAMED_MONITOR_LOAD_OR_RESULT_MISSING") from exc
    normalized = validate_lumerical_results(e_result, h_result)
    matched_h5_group = find_h5_monitor_group(h5_path, normalized)
    if sha256_file(run_fsp) != fsp_sha_before or sha256_file(h5_path) != h5_sha_before:
        raise MonitorExtractionError("BUNDLE_CHANGED_DURING_LOAD_ONLY_EXTRACTION")

    npz_path = output_dir / (monitor_name + "_complex_fields_v1.npz")
    metadata_path = output_dir / (monitor_name + "_complex_fields_v1.json")
    if npz_path.exists() or metadata_path.exists():
        raise MonitorExtractionError("EXTRACTION_OUTPUT_ALREADY_EXISTS")
    output_dir.mkdir(parents=True, exist_ok=True)

    coords = normalized["coordinates_m"]
    fields = normalized["fields"]
    tmp_npz = npz_path.with_name(npz_path.name + ".tmp")
    tmp_json = metadata_path.with_name(metadata_path.name + ".tmp")
    try:
        with tmp_npz.open("wb") as stream:
            np.savez(stream,
                x_nm=coords["x"] * 1e9,
                y_nm=coords["y"] * 1e9,
                z_actual_nm=coords["z"] * 1e9,
                wavelength_nm=normalized["wavelength_m"] * 1e9,
                frequency_hz=normalized["frequency_hz"],
                **fields)
            stream.flush()
            os.fsync(stream.fileno())
        metadata = {
            "schema": "APCD_GPU_RUNNER_EXT02_SECOND_PLANE_FIELDS_V1",
            "result": "PASS",
            "case_id": CASE_ID,
            "attempt_id": ATTEMPT_ID,
            "run_id": bundle["run_id"],
            "route_version": ROUTE_VERSION,
            "extractor_sha256": sha256_file(Path(__file__)),
            "monitor_name": monitor_name,
            "monitor_configured_z_nm": monitor_setup["configured_z_nm"],
            "monitor_actual_z_nm": (coords["z"] * 1e9).tolist(),
            "reference_plane_nm": monitor_setup["reference_plane_nm"],
            "field_shape_xyzfc": normalized["field_shape"],
            "components": list(COMPONENTS),
            "wavelength_nm": (normalized["wavelength_m"] * 1e9).tolist(),
            "coordinate_units": "nm",
            "field_units": "native Lumerical E/H values returned by getresult",
            "h5_sidecar_relative_path": str(h5_path.relative_to(bundle["run_dir"])),
            "h5_sidecar_sha256": h5_sha_before,
            "h5_coordinate_units": "micrometer",
            "h5_matched_monitor_group": matched_h5_group,
            "fsp_sha256": fsp_sha_before,
            "truth_h5_sha256": bundle["hashes"]["truth_h5_sha256"],
            "setup_validation_sha256": bundle["hashes"]["setup_validation_sha256"],
            "pre_entry_revalidation_sha256": bundle["hashes"]["pre_entry_revalidation_sha256"],
            "setup_contract_fingerprint_sha256": bundle["start_time_revalidation"]["setup_contract_fingerprint_sha256"],
            "physical_contract_sha256": bundle["start_time_revalidation"]["physical_contract_sha256"],
            "source_manifest_sha256": bundle["start_time_revalidation"]["source_manifest_sha256"],
            "pre_entry_setup_load_proof_sha256": bundle["start_time_revalidation"]["pre_entry_setup_load_proof_sha256"],
            "control_generation_sha256": bundle["start_time_revalidation"]["control_generation_sha256"],
            "extraction_only": True,
            "solver_calls_during_extraction": 0,
            "automatic_replay_performed": False,
        }
        metadata["npz_sha256"] = sha256_file(tmp_npz)
        with tmp_json.open("wb") as stream:
            stream.write((json.dumps(metadata, sort_keys=True, indent=2) + "\n").encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_npz, npz_path)
        os.replace(tmp_json, metadata_path)
    except Exception:
        for path in (tmp_npz, tmp_json):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        raise
    return npz_path, metadata_path, metadata


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Load-only extraction of the authorized EXT02 second E/H plane")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--monitor", choices=(EXISTING_MONITOR_NAME, MONITOR_NAME),
                        default=MONITOR_NAME)
    parser.add_argument("--output-subdir", default="monitor_extraction",
                        help="relative output directory below the immutable run directory")
    args = parser.parse_args(argv)
    try:
        npz_path, metadata_path, metadata = extract_ext02_monitor(
            Path(args.run_dir), monitor_name=args.monitor, output_subdir=args.output_subdir)
    except Exception as exc:
        print("MONITOR_EXTRACTION_FAIL:" + str(exc), file=sys.stderr)
        return 2
    print(json.dumps({
        "result": metadata["result"],
        "case_id": metadata["case_id"],
        "attempt_id": metadata["attempt_id"],
        "run_id": metadata["run_id"],
        "monitor_name": metadata["monitor_name"],
        "monitor_configured_z_nm": metadata["monitor_configured_z_nm"],
        "reference_plane_nm": metadata["reference_plane_nm"],
        "monitor_actual_z_nm": metadata["monitor_actual_z_nm"],
        "h5_matched_monitor_group": metadata["h5_matched_monitor_group"],
        "npz_path": str(npz_path),
        "metadata_path": str(metadata_path),
        "solver_calls_during_extraction": 0,
        "automatic_replay_performed": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
