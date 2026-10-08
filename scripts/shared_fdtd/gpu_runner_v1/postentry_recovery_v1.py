"""Guarded zero-solver recovery of durable post-entry truth for GPU Runner V1."""
from __future__ import annotations
import datetime
import hashlib
import json
import math
import os
import shutil
import time
import traceback
import uuid
from pathlib import Path

SCHEMA_RECOVERY = "APCD_GPU_RUNNER_V1_POSTENTRY_TRUTH_RECOVERY_V1"
SCHEMA_PROOF = "APCD_GPU_RUNNER_V1_POSTENTRY_FRESH_LOAD_PROOF_V1"
SCHEMA_RECEIPT = "APCD_GPU_RUNNER_V1_POSTENTRY_TRUTH_RECOVERY_RECEIPT_V1"
ACTIVE_STATES = {"PENDING", "PRECHECK_PASS", "SOLVER_ENTERED", "SOLVER_RETURNED", "TRUTH_VALID"}

class RecoveryError(RuntimeError):
    pass

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()

def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")

def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def _atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    raw = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    try:
        with temporary.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(str(temporary), str(path))
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass

def _self_hashed(body, key):
    result = dict(body)
    result[key] = sha_bytes(canonical(body))
    return result

def validate_postentry_checkpoint(manifest, status, registry_rows, request, claim,
                                  *, case_id, attempt_id, run_id, request_id):
    identity = {"case_id": case_id, "attempt_id": attempt_id, "run_id": run_id}
    if any(manifest.get(key) != value for key, value in identity.items()):
        raise RecoveryError("MANIFEST_TARGET_IDENTITY_MISMATCH")
    if any(status.get(key) != value for key, value in identity.items()):
        raise RecoveryError("STATUS_TARGET_IDENTITY_MISMATCH")
    if status.get("state") != "SOLVER_ENTERED" or status.get("solver_entered") is not True:
        raise RecoveryError("TARGET_NOT_IN_RECOVERABLE_POSTENTRY_STATE")
    if status.get("solver_invocations") != 1:
        raise RecoveryError("TARGET_ENTRY_COUNT_NOT_ONE")
    matching = [row for row in registry_rows if isinstance(row, dict)
                and all(row.get(key) == value for key, value in identity.items())]
    if len(matching) != 1 or matching[0].get("state") != "SOLVER_ENTERED":
        raise RecoveryError("REGISTRY_TARGET_NOT_UNIQUE_ENTERED")
    if request.get("request_id") != request_id or request.get("identity") != identity:
        raise RecoveryError("REQUEST_TARGET_IDENTITY_MISMATCH")
    if claim.get("request_id") != request_id or claim.get("request_sha256") != request.get("request_sha256"):
        raise RecoveryError("WORKER_CLAIM_IDENTITY_OR_HASH_MISMATCH")
    if int(claim.get("pid", 0)) <= 0:
        raise RecoveryError("WORKER_CLAIM_PID_INVALID")
    return matching[0]

def _log_completion_evidence(log_path):
    text = Path(log_path).read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    markers = {
        "iterations": next((line.strip() for line in lines if "Completed " in line and "iterations" in line), None),
        "collection": next((line.strip() for line in lines if "Finished collecting data" in line), None),
        "completion": next((line.strip() for line in lines if "Simulation completed successfully at:" in line), None),
    }
    if not all(markers.values()):
        raise RecoveryError("FDTD_COMPLETION_LOG_MARKERS_INCOMPLETE")
    return {"path": str(Path(log_path).resolve()), "sha256": sha_file(log_path), "markers": markers}

def inventory(directory):
    root = Path(directory)
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise RecoveryError("SYMLINK_IN_RUN_EVIDENCE:" + str(path))
        if path.is_file():
            result[str(path.relative_to(root))] = {"size": path.stat().st_size, "sha256": sha_file(path)}
    return result

def _copy_file_durable(source, destination):
    source, destination = Path(source), Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    with destination.open("r+b") as stream:
        os.fsync(stream.fileno())
    if sha_file(source) != sha_file(destination):
        raise RecoveryError("ISOLATED_INPUT_COPY_HASH_MISMATCH:" + source.name)

def _assert_original_files_unchanged(run_dir, original_inventory):
    root = Path(run_dir)
    for relative, metadata in original_inventory.items():
        path = root / relative
        if not path.is_file() or path.is_symlink() or sha_file(path) != metadata["sha256"]:
            raise RecoveryError("ORIGINAL_RUN_EVIDENCE_CHANGED:" + relative)

def _text_attr(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="strict")
    return str(value)

def validate_fresh_load_outputs(run_dir, validation, *, case_id, attempt_id, run_id,
                                expected_wavelengths_nm):
    import h5py
    import numpy as np
    root = Path(run_dir)
    flags = ("fresh_load_verified", "monitors_valid", "state_valid", "scientific_valid")
    if not isinstance(validation, dict) or any(validation.get(key) is not True for key in flags):
        raise RecoveryError("FRESH_LOAD_VALIDATION_FLAGS_NOT_ALL_PASS")
    if validation.get("run_id") not in (None, run_id):
        raise RecoveryError("FRESH_LOAD_RUN_ID_MISMATCH")
    stem = case_id + "__" + attempt_id
    raw_path = root / "raw" / (stem + "_raw.json")
    field_path = root / "raw" / (stem + "_raw_complex_fields.npz")
    truth_path = root / "truth.h5"
    state_npz = list((root / "state").glob("*.npz")) if (root / "state").is_dir() else []
    state_json = list((root / "state").glob("*.json")) if (root / "state").is_dir() else []
    order_files = list((root / "orders").glob("*.json")) if (root / "orders").is_dir() else []
    projection_files = list((root / "projection").glob("*.json")) if (root / "projection").is_dir() else []
    if not all(path.is_file() and path.stat().st_size > 0 for path in (raw_path, field_path, truth_path)):
        raise RecoveryError("FRESH_LOAD_REQUIRED_TRUTH_OR_RAW_MISSING")
    if not state_npz or not state_json or not order_files or not projection_files:
        raise RecoveryError("FRESH_LOAD_STATE_ORDERS_OR_PROJECTION_MISSING")
    raw = _json(raw_path)
    if any(raw.get(key) != value for key, value in
           (("case_id", case_id), ("attempt_id", attempt_id), ("run_id", run_id))):
        raise RecoveryError("RAW_IDENTITY_MISMATCH")
    fields = raw.get("raw_complex_fields")
    if not isinstance(fields, dict) or fields.get("schema") != "APCD_PW_RAW_COMPLEX_FIELDS_V1":
        raise RecoveryError("RAW_COMPLEX_FIELDS_SCHEMA_INVALID")
    if Path(fields.get("path", "")).resolve() != field_path.resolve():
        raise RecoveryError("RAW_COMPLEX_FIELDS_PATH_MISMATCH")
    if fields.get("sha256") != sha_file(field_path):
        raise RecoveryError("RAW_COMPLEX_FIELDS_HASH_MISMATCH")
    planes = fields.get("planes")
    expected_planes = {"IN": "MON_IN", "PRENP": "MON_PRENP", "POSTNP": "MON_POSTNP"}
    if not isinstance(planes, dict) or set(planes) != set(expected_planes):
        raise RecoveryError("RAW_MONITOR_SET_MISMATCH")
    if fields.get("field_names") != ["Ex", "Ey", "Ez", "Hx", "Hy", "Hz"]:
        raise RecoveryError("RAW_EH_COMPONENT_SET_MISMATCH")
    field_summary = {}
    wavelength_count = len(expected_wavelengths_nm)
    if wavelength_count != 21:
        raise RecoveryError("FROZEN_WAVELENGTH_CONTRACT_NOT_21")
    with np.load(field_path, allow_pickle=False) as arrays:
        for plane, monitor_name in expected_planes.items():
            plane_meta = planes[plane]
            if plane_meta.get("monitor") != monitor_name:
                raise RecoveryError("RAW_MONITOR_NAME_MISMATCH:" + plane)
            sample_nm = plane_meta.get("sample_nm")
            if not isinstance(sample_nm, (int, float)) or not math.isfinite(float(sample_nm)):
                raise RecoveryError("RAW_ACTUAL_SAMPLE_Z_INVALID:" + plane)
            fields_meta = plane_meta.get("fields", {})
            if set(fields_meta) != {"Ex", "Ey", "Ez", "Hx", "Hy", "Hz"}:
                raise RecoveryError("RAW_MONITOR_COMPONENTS_INCOMPLETE:" + plane)
            for component in ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz"):
                key = fields_meta[component].get("array_key")
                if key not in arrays.files:
                    raise RecoveryError("RAW_ARRAY_MISSING:" + str(key))
                data = arrays[key]
                if not np.iscomplexobj(data) or data.ndim < 1 or data.shape[-1] != wavelength_count:
                    raise RecoveryError("RAW_ARRAY_COMPLEX_OR_WAVELENGTH_SHAPE_INVALID:" + str(key))
                if not bool(np.isfinite(data.real).all() and np.isfinite(data.imag).all()):
                    raise RecoveryError("RAW_ARRAY_NONFINITE:" + str(key))
            for suffix in ("x", "y", "z", "f"):
                key = plane + "_" + suffix
                if key not in arrays.files or not np.isfinite(arrays[key]).all():
                    raise RecoveryError("RAW_COORDINATE_ARRAY_INVALID:" + key)
            if arrays[plane + "_f"].size != wavelength_count:
                raise RecoveryError("RAW_FREQUENCY_COUNT_MISMATCH:" + plane)
            wavelengths_nm = np.sort(299792458.0 / arrays[plane + "_f"].reshape(-1) * 1e9)
            if not np.allclose(wavelengths_nm, np.asarray(expected_wavelengths_nm, dtype=float), rtol=0, atol=1e-6):
                raise RecoveryError("RAW_WAVELENGTH_VALUES_MISMATCH:" + plane)
            field_summary[plane] = {
                "monitor": monitor_name, "actual_sample_z_nm": float(sample_nm),
                "shape": list(arrays[plane + "_Ex"].shape), "wavelength_count": wavelength_count,
                "actual_wavelengths_nm": [float(value) for value in wavelengths_nm],
            }
        for path in state_npz:
            with np.load(path, allow_pickle=False) as state_arrays:
                for key in state_arrays.files:
                    data = state_arrays[key]
                    if getattr(data, "dtype", None) is not None and data.dtype.kind in "biufc":
                        if not np.isfinite(data).all():
                            raise RecoveryError("STATE_ARRAY_NONFINITE:" + key)
    with h5py.File(truth_path, "r") as truth:
        attrs = {key: _text_attr(truth.attrs.get(key, "")) for key in ("case_id", "attempt_id", "run_id")}
        if attrs != {"case_id": case_id, "attempt_id": attempt_id, "run_id": run_id}:
            raise RecoveryError("TRUTH_H5_IDENTITY_MISMATCH")
        if "raw_json" not in truth or "metrics_json" not in truth:
            raise RecoveryError("TRUTH_H5_DATASETS_MISSING")
        embedded = json.loads(_text_attr(truth["raw_json"][()]))
        if embedded.get("raw_complex_fields", {}).get("sha256") != sha_file(field_path):
            raise RecoveryError("TRUTH_H5_RAW_HASH_MISMATCH")
        json.loads(_text_attr(truth["metrics_json"][()]))
    if validation.get("truth_h5_sha256") != sha_file(truth_path):
        raise RecoveryError("FRESH_LOAD_TRUTH_HASH_MISMATCH")
    return {
        "truth_h5": str(truth_path.resolve()), "truth_h5_sha256": sha_file(truth_path),
        "raw_json": str(raw_path.resolve()), "raw_json_sha256": sha_file(raw_path),
        "raw_complex_fields": str(field_path.resolve()), "raw_complex_fields_sha256": sha_file(field_path),
        "state_npz": [{"path": str(p.resolve()), "sha256": sha_file(p)} for p in state_npz],
        "state_metadata": [{"path": str(p.resolve()), "sha256": sha_file(p)} for p in state_json],
        "orders": [{"path": str(p.resolve()), "sha256": sha_file(p)} for p in order_files],
        "projection": [{"path": str(p.resolve()), "sha256": sha_file(p)} for p in projection_files],
        "monitor_fields": field_summary,
    }

def _check_task_snapshot(tasks):
    for role in ("worker", "controller"):
        info = tasks.get(role) or {}
        state = str(info.get("state", info.get("State", "UNKNOWN"))).casefold()
        if state in {"running", "queued"}:
            raise RecoveryError("TASK_STILL_ACTIVE:" + role)
    worker = tasks.get("worker") or {}
    last = worker.get("last_task_result", worker.get("LastTaskResult"))
    if last not in (3221225786, "3221225786", "0xC000013A", "3221225786L"):
        raise RecoveryError("WORKER_STOP_REASON_NOT_CONFIRMED:" + str(last))

def _check_process_snapshot(process_snapshot):
    if not isinstance(process_snapshot, dict):
        raise RecoveryError("PROCESS_CENSUS_INVALID")
    if process_snapshot.get("blocking_processes"):
        raise RecoveryError("ACTIVE_RUNNER_OR_FDTD_PROCESS_PRESENT")
    if process_snapshot.get("prior_g025_worker_or_child_present"):
        raise RecoveryError("PRIOR_G025_PROCESS_IDENTITY_STILL_PRESENT")

def _archive_markers(root, archive_dir, marker_specs, *, case_id, attempt_id, run_id,
                     request_id, worker_pid):
    root, archive_dir = Path(root), Path(archive_dir)
    archive_dir.mkdir(parents=True, exist_ok=False)
    expected = {
        ".runner.lock": {"case_id": case_id, "attempt_id": attempt_id, "run_id": run_id, "pid": worker_pid},
        "active_run.json": {"case_id": case_id, "attempt_id": attempt_id, "run_id": run_id, "pid": worker_pid},
        "scheduler_worker_v1.lock": {"request_id": request_id, "pid": worker_pid},
    }
    archived = {}
    for name, wanted in expected.items():
        source, target = root / name, archive_dir / name
        if name not in marker_specs or not source.is_file() or source.is_symlink():
            raise RecoveryError("CONTROL_MARKER_MISSING_OR_UNPINNED:" + name)
        before_sha = sha_file(source)
        if before_sha != marker_specs[name]:
            raise RecoveryError("CONTROL_MARKER_HASH_CHANGED:" + name)
        value = _json(source)
        if any(value.get(key) != expected_value for key, expected_value in wanted.items()):
            raise RecoveryError("CONTROL_MARKER_IDENTITY_MISMATCH:" + name)
        os.replace(str(source), str(target))
        after_sha = sha_file(target)
        if after_sha != before_sha:
            raise RecoveryError("CONTROL_MARKER_ARCHIVE_HASH_MISMATCH:" + name)
        archived[name] = {"path": str(target), "sha256": after_sha}
    if any((root / name).exists() for name in expected):
        raise RecoveryError("RUNNER_CONTROL_MARKER_REMAINS_AFTER_ARCHIVE")
    return archived

def recover_postentry_truth_v1(*, config, adapter_module, runner_module, scheduler_module,
                               process_census, task_snapshot, control_snapshot, external_snapshot):
    root = Path(config["runner_root"]).resolve()
    run_dir = Path(config["run_dir"]).resolve()
    request_dir = Path(config["request_dir"]).resolve()
    recovery_dir = Path(config["recovery_dir"]).resolve()
    case_id, attempt_id, run_id = config["case_id"], config["attempt_id"], config["run_id"]
    request_id, worker_pid = config["request_id"], int(config["worker_pid"])
    if recovery_dir.exists():
        raise RecoveryError("RECOVERY_EVIDENCE_DIRECTORY_ALREADY_EXISTS")
    if root not in run_dir.parents or (root / "requests" / "scheduled_run_one_v1") not in request_dir.parents:
        raise RecoveryError("RECOVERY_PATH_OUTSIDE_RUNNER_ROOT")
    request_path, claim_path = request_dir / "request.json", request_dir / "worker_claim.json"
    result_path = request_dir / "result.json"
    if result_path.exists():
        raise RecoveryError("SCHEDULED_REQUEST_ALREADY_TERMINAL")
    request = scheduler_module._read_and_verify_request(request_path)
    claim = _json(claim_path)
    manifest, contract_path = adapter_module.read_cli_manifest(request["manifest_path"])
    status_path, registry_path = run_dir / "status.json", root / "registry.json"
    status, registry = _json(status_path), _json(registry_path)
    registry_row = validate_postentry_checkpoint(
        manifest, status, registry.get("runs", []), request, claim,
        case_id=case_id, attempt_id=attempt_id, run_id=run_id, request_id=request_id)
    if sha_file(request_path) != config["expected_request_file_sha256"]:
        raise RecoveryError("REQUEST_FILE_HASH_MISMATCH")
    if request.get("request_sha256") != config["expected_request_sha256"]:
        raise RecoveryError("REQUEST_BODY_HASH_MISMATCH")
    if sha_file(claim_path) != config["expected_claim_file_sha256"]:
        raise RecoveryError("WORKER_CLAIM_HASH_MISMATCH")
    if sha_file(request["manifest_path"]) != config["expected_manifest_envelope_sha256"]:
        raise RecoveryError("MANIFEST_ENVELOPE_HASH_MISMATCH")
    if manifest.get("physical_contract_sha256") != config["physical_contract_sha256"]:
        raise RecoveryError("PHYSICAL_CONTRACT_HASH_MISMATCH")
    if sha_file(contract_path) != manifest.get("physical_contract_sha256"):
        raise RecoveryError("PHYSICAL_CONTRACT_FILE_HASH_MISMATCH")
    if sha_file(request["adapter_path"]) != request.get("adapter_sha256"):
        raise RecoveryError("PINNED_ADAPTER_VERSION_MISMATCH")
    if sha_file(request["worker_module_path"]) != request.get("worker_module_sha256"):
        raise RecoveryError("PINNED_SCHEDULER_VERSION_MISMATCH")
    if request.get("adapter_sha256") != config["adapter_sha256"] or request.get("worker_module_sha256") != config["worker_module_sha256"]:
        raise RecoveryError("REQUEST_CODE_PINS_MISMATCH")
    if manifest.get("pre_fsp_sha256") != config["pre_fsp_sha256"] or sha_file(manifest["pre_fsp_path"]) != config["pre_fsp_sha256"]:
        raise RecoveryError("SOURCE_PRE_FSP_HASH_MISMATCH")
    expected_paths = {
        "manifest.json": (run_dir / "manifest.json", config["run_manifest_sha256"]),
        "run.fsp": (run_dir / "run.fsp", config["run_fsp_sha256"]),
        "native_h5": (run_dir / "run" / "run_output.h5", config["run_output_h5_sha256"]),
        "run_p0.log": (run_dir / "run_p0.log", config["run_log_sha256"]),
        "status.json": (status_path, config["status_sha256"]),
    }
    for label, (path, expected_sha) in expected_paths.items():
        if sha_file(path) != expected_sha:
            raise RecoveryError("PINNED_INPUT_HASH_MISMATCH:" + label)
    for label, path, expected_sha in (("setup_validation.json", run_dir / "setup_validation.json", config["setup_validation_sha256"]), ("pre_entry_revalidation.json", run_dir / "pre_entry_revalidation.json", config["pre_entry_revalidation_sha256"])):
        if sha_file(path) != expected_sha:
            raise RecoveryError("PINNED_INPUT_HASH_MISMATCH:" + label)
    for label, path in (("run.fsp", run_dir / "run.fsp"), ("native_h5", run_dir / "run" / "run_output.h5")):
        if not runner_module._durable(path):
            raise RecoveryError("DURABLE_SOURCE_ARTIFACT_REQUIRED:" + label)
    if _json(run_dir / "validation.json") != {"state": "PENDING"} or _json(run_dir / "hashes.json") != {"state": "PENDING"}:
        raise RecoveryError("TARGET_VALIDATION_NOT_PENDING")
    if any((run_dir / name).exists() for name in ("truth.h5", "raw", "state", "orders", "projection")):
        raise RecoveryError("CANONICAL_OUTPUT_PATH_ALREADY_PRESENT")
    if not registry_row or sum(1 for row in registry.get("runs", []) if row.get("state") in ACTIVE_STATES) != 1:
        raise RecoveryError("ACTIVE_REGISTRY_STATE_NOT_EXCLUSIVE")
    forbidden = config.get("forbidden_case_id")
    if forbidden and (any(row.get("case_id") == forbidden for row in registry.get("runs", []))
                      or (root / "runs" / forbidden).exists()):
        raise RecoveryError("FORBIDDEN_NEXT_CASE_ALREADY_PRESENT")

    log_evidence = _log_completion_evidence(run_dir / "run_p0.log")
    initial_inventory = inventory(run_dir)
    marker_paths = {name: root / name for name in (".runner.lock", "active_run.json", "scheduler_worker_v1.lock")}
    marker_specs = {}
    for name, path in marker_paths.items():
        if not path.is_file() or path.is_symlink():
            raise RecoveryError("RUNNER_CONTROL_MARKER_NOT_PRESENT:" + name)
        marker_specs[name] = sha_file(path)
        expected = config["marker_sha256"].get(name)
        if expected and marker_specs[name] != expected:
            raise RecoveryError("RUNNER_CONTROL_MARKER_HASH_MISMATCH:" + name)
    for name in (".runner.lock", "active_run.json"):
        item = _json(root / name)
        if any(item.get(key) != value for key, value in
               (("case_id", case_id), ("attempt_id", attempt_id), ("run_id", run_id), ("pid", worker_pid))):
            raise RecoveryError("RUNNER_MARKER_TARGET_MISMATCH:" + name)
    worker_lock = _json(root / "scheduler_worker_v1.lock")
    if worker_lock.get("request_id") != request_id or worker_lock.get("pid") != worker_pid:
        raise RecoveryError("WORKER_LOCK_TARGET_MISMATCH")

    process_before, tasks_before = process_census(), task_snapshot()
    _check_process_snapshot(process_before)
    _check_task_snapshot(tasks_before)
    control_before = control_snapshot()
    if not isinstance(control_before, dict) or control_before.get("result") != "PASS":
        raise RecoveryError("GLOBAL_CONTROL_READ_UNHEALTHY")
    external_before = external_snapshot()
    active_rows = [row for row in registry.get("runs", []) if row.get("state") in ACTIVE_STATES]
    if len(active_rows) != 1 or active_rows[0].get("run_id") != run_id:
        raise RecoveryError("OTHER_ACTIVE_SCIENTIFIC_CASE_PRESENT")

    recovery_dir.mkdir(parents=True, exist_ok=False)
    phase = "RECOVERY_CLAIMED"
    try:
        claim_body = {
            "schema": SCHEMA_RECOVERY, "case_id": case_id, "attempt_id": attempt_id,
            "run_id": run_id, "request_id": request_id, "created_utc": now_utc(),
            "runner_head": config["runner_head"],
            "runner_source_hashes": config["runner_source_hashes"],
            "input_run_inventory": initial_inventory,
            "marker_sha256": marker_specs, "request_file_sha256": sha_file(request_path),
            "worker_claim_file_sha256": sha_file(claim_path),
        }
        recovery_claim = _self_hashed(claim_body, "claim_sha256")
        _atomic_json(recovery_dir / "claim.json", recovery_claim)
        evidence_dir = recovery_dir / "original_evidence"
        evidence_dir.mkdir()
        for source, relative in (
                (status_path, "status.json"), (run_dir / "validation.json", "validation.json"),
                (run_dir / "hashes.json", "hashes.json"), (registry_path, "registry.json"),
                (request_path, "request.json"), (claim_path, "worker_claim.json")):
            _copy_file_durable(source, evidence_dir / relative)
        stage_run = recovery_dir / "isolated_input"
        stage_run.mkdir()
        (stage_run / "run").mkdir()
        _copy_file_durable(run_dir / "run.fsp", stage_run / "run.fsp")
        _copy_file_durable(run_dir / "run" / "run_output.h5", stage_run / "run" / "run_output.h5")
        _copy_file_durable(run_dir / "manifest.json", stage_run / "manifest.json")
        phase = "FRESH_LOAD_ONLY"
        native_adapter = adapter_module.NativeAdapter(
            contract_path, gpu_resource_name=request["gpu_resource_name"])
        dependency_preflight = native_adapter.postprocess_dependency_preflight
        if not isinstance(dependency_preflight, dict) or dependency_preflight.get("result") != "PASS":
            raise RecoveryError("POSTPROCESS_DEPENDENCY_PREFLIGHT_NOT_PASS")
        fresh_validation = native_adapter.fresh_load_validate(manifest, stage_run, output_root=run_dir)
        phase = "TRUTH_OUTPUT_VALIDATION"
        output_summary = validate_fresh_load_outputs(
            run_dir, fresh_validation, case_id=case_id, attempt_id=attempt_id, run_id=run_id,
            expected_wavelengths_nm=config["expected_wavelengths_nm"])
        durable_outputs = [output_summary["truth_h5"], output_summary["raw_json"], output_summary["raw_complex_fields"]]
        for group in ("state_npz", "state_metadata", "orders", "projection"):
            durable_outputs.extend(item["path"] for item in output_summary[group])
        for output_path in durable_outputs:
            if not runner_module._durable(output_path):
                raise RecoveryError("DURABLE_TRUTH_OUTPUT_REQUIRED:" + str(output_path))
        _assert_original_files_unchanged(run_dir, initial_inventory)
        proof_body = {
            "schema": SCHEMA_PROOF, "result": "PASS", "mode": "FRESH_LOAD_ONLY",
            "solver_run_called": False, "solver_invocations_during_recovery": 0,
            "scientific_entry_performed": False, "case_id": case_id, "attempt_id": attempt_id,
            "run_id": run_id, "request_id": request_id, "created_utc": now_utc(),
            "source_run_fsp_sha256": config["run_fsp_sha256"],
            "source_native_h5_sha256": config["run_output_h5_sha256"],
            "runner_source_hashes": config["runner_source_hashes"],
            "postprocess_dependency_preflight": dependency_preflight,
            "fdtd_completion_log": log_evidence, "validation": fresh_validation,
            "output_summary": output_summary, "wavelengths_nm": config["expected_wavelengths_nm"],
            "original_run_evidence_unchanged": True,
        }
        proof = _self_hashed(proof_body, "proof_sha256")
        _atomic_json(recovery_dir / "fresh_load_proof.json", proof)
        proof_sha = proof["proof_sha256"]

        final_validation = dict(fresh_validation)
        final_validation.update(
            run_id=run_id, run_fsp_sha256=sha_file(run_dir / "run.fsp"),
            truth_h5_sha256=sha_file(run_dir / "truth.h5"), validated_unix=time.time(),
            recovered_postentry=True, recovery_mode="FRESH_LOAD_ONLY_NO_SOLVER",
            recovery_proof_sha256=proof_sha, solver_run_called_during_recovery=False,
            solver_invocations_during_recovery=0, original_solver_invocations=1,
        )
        _atomic_json(run_dir / "validation.json", final_validation)
        final_hashes = {
            "manifest_sha256": sha_file(run_dir / "manifest.json"),
            "pre_fsp_sha256": manifest["pre_fsp_sha256"],
            "run_fsp_sha256": sha_file(run_dir / "run.fsp"),
            "setup_validation_sha256": sha_file(run_dir / "setup_validation.json"),
            "truth_h5_sha256": sha_file(run_dir / "truth.h5"),
            "validation_sha256": sha_file(run_dir / "validation.json"),
            "pre_entry_revalidation_sha256": sha_file(run_dir / "pre_entry_revalidation.json"),
            "run_output_h5_sha256": sha_file(run_dir / "run" / "run_output.h5"),
            "postentry_recovery_proof_sha256": proof_sha,
        }
        if not runner_module._durable(run_dir / "validation.json"):
            raise RecoveryError("VALIDATION_ARTIFACT_NOT_DURABLE")
        _atomic_json(run_dir / "hashes.json", final_hashes)
        if not runner_module._durable(run_dir / "hashes.json"):
            raise RecoveryError("HASH_INVENTORY_NOT_DURABLE")
        phase = "RUNNER_TERMINAL_COMMIT"
        current_status, current_registry = _json(status_path), _json(registry_path)
        if current_status.get("state") != "SOLVER_ENTERED":
            raise RecoveryError("RUN_STATUS_CHANGED_BEFORE_TERMINAL_COMMIT")
        rows = current_registry.get("runs", [])
        row_matches = [row for row in rows if row.get("run_id") == run_id
                       and row.get("case_id") == case_id and row.get("attempt_id") == attempt_id]
        if len(row_matches) != 1 or row_matches[0].get("state") != "SOLVER_ENTERED":
            raise RecoveryError("REGISTRY_CHANGED_BEFORE_TERMINAL_COMMIT")
        recovered_fields = {
            "solver_returned_unix": time.time(),
            "solver_result": "RECOVERED_FROM_COMPLETED_FDTD_LOG_AND_DURABLE_NATIVE_H5",
            "solver_callback_return_observed": False, "postentry_truth_recovered": True,
            "postentry_recovery_proof_sha256": proof_sha, "automatic_replay_count": 0,
        }
        current_status = runner_module._transition(run_dir, current_status, "SOLVER_RETURNED", **recovered_fields)
        row_matches[0]["state"] = "SOLVER_RETURNED"
        _atomic_json(registry_path, current_registry)
        current_status = runner_module._transition(
            run_dir, current_status, "TRUTH_VALID",
            run_fsp_sha256=final_hashes["run_fsp_sha256"],
            truth_h5_sha256=final_hashes["truth_h5_sha256"],
            validation_sha256=final_hashes["validation_sha256"])
        row_matches[0]["state"] = "TRUTH_VALID"
        _atomic_json(registry_path, current_registry)
        current_status = runner_module._transition(run_dir, current_status, "DONE", done_unix=time.time())
        row_matches[0].update(
            state="DONE", solver_entered=True, solver_invocations=1,
            automatic_replay_count=0, postentry_recovery_proof_sha256=proof_sha)
        _atomic_json(registry_path, current_registry)

        phase = "RUNNER_MARKER_ARCHIVE"
        archived = _archive_markers(
            root, recovery_dir / "archived_control_markers", marker_specs,
            case_id=case_id, attempt_id=attempt_id, run_id=run_id,
            request_id=request_id, worker_pid=worker_pid)
        phase = "SCHEDULED_RESULT_COMMIT"
        result_body = {
            "schema": scheduler_module.SCHEMA_RESULT, "request_id": request_id,
            "request_sha256": request["request_sha256"],
            "claim_sha256": scheduler_module._sha_bytes(scheduler_module._canonical(claim)),
            "worker_pid": worker_pid, "worker_started_utc": claim.get("created_utc"),
            "exit_code": 0,
            "result": {
                "run_dir": str(run_dir), "state": "DONE", "recovered_postentry_truth": True,
                "recovery_directory": str(recovery_dir), "recovery_proof_sha256": proof_sha,
                "solver_entry_count": 1, "solver_invocations": 1,
                "solver_invocations_during_recovery": 0, "automatic_replay_count": 0,
            },
            "completed_utc": now_utc(), "recovered_by_pid": os.getpid(),
            "solver_entered": True, "solver_invocations": 1, "automatic_replay_count": 0,
        }
        result_body["result_sha256"] = scheduler_module._sha_bytes(scheduler_module._canonical(result_body))
        scheduler_module._atomic_json(result_path, result_body)
        query = scheduler_module.query_one(
            request_id, root=root, task_info_fn=lambda: tasks_before["worker"])
        if query.get("state") != "TERMINAL" or (query.get("result") or {}).get("exit_code") != 0:
            raise RecoveryError("SCHEDULED_REQUEST_DID_NOT_REACH_TERMINAL_SUCCESS")

        process_after, tasks_after = process_census(), task_snapshot()
        _check_process_snapshot(process_after)
        _check_task_snapshot(tasks_after)
        control_after, external_after = control_snapshot(), external_snapshot()
        if control_after.get("result") != "PASS":
            raise RecoveryError("GLOBAL_CONTROL_POSTCHECK_UNHEALTHY")
        if external_before != external_after:
            raise RecoveryError("COUPLING_READ_ONLY_EVIDENCE_CHANGED_DURING_RECOVERY")
        if any(path.exists() for path in marker_paths.values()):
            raise RecoveryError("RUNNER_SLOT_MARKER_REMAINS_AFTER_CLOSEOUT")
        final_status, final_registry = _json(status_path), _json(registry_path)
        final_row = [row for row in final_registry.get("runs", [])
                     if row.get("case_id") == case_id and row.get("attempt_id") == attempt_id
                     and row.get("run_id") == run_id]
        if final_status.get("state") != "DONE" or len(final_row) != 1 or final_row[0].get("state") != "DONE":
            raise RecoveryError("RUNNER_FINAL_STATE_NOT_DONE")
        receipt_body = {
            "schema": SCHEMA_RECEIPT, "result": "RECOVERED_AND_CLOSED",
            "case_id": case_id, "attempt_id": attempt_id, "run_id": run_id,
            "request_id": request_id, "created_utc": now_utc(),
            "solver_entry_count": 1, "solver_invocations": 1,
            "solver_invocations_during_recovery": 0, "automatic_replay_count": 0,
            "solver_callback_return_observed": False,
            "original_worker_stop_code": "0xC000013A",
            "original_interrupted_substep": "UNKNOWN_NO_RAW_EXCEPTION_OR_RESULT_RECORD",
            "fdtd_completion_log": log_evidence,
            "fresh_load_proof_path": str(recovery_dir / "fresh_load_proof.json"),
            "fresh_load_proof_sha256": proof_sha,
            "runner_source_hashes": config["runner_source_hashes"],
            "truth_h5_path": str(run_dir / "truth.h5"),
            "truth_h5_sha256": final_hashes["truth_h5_sha256"],
            "validation_path": str(run_dir / "validation.json"),
            "validation_sha256": final_hashes["validation_sha256"],
            "hashes_path": str(run_dir / "hashes.json"),
            "hashes_sha256": sha_file(run_dir / "hashes.json"),
            "run_fsp_sha256": final_hashes["run_fsp_sha256"],
            "native_h5_sha256": final_hashes["run_output_h5_sha256"],
            "raw_field_artifacts": output_summary,
            "process_before": process_before, "process_after": process_after,
            "tasks_before": tasks_before, "tasks_after": tasks_after,
            "global_control_before": control_before, "global_control_after": control_after,
            "archived_control_markers": archived,
            "scheduled_result_path": str(result_path),
            "scheduled_result_sha256": sha_file(result_path),
            "scheduled_query_state": query.get("state"),
            "runner_status_sha256": sha_file(status_path),
            "runner_registry_sha256": sha_file(registry_path),
            "external_coupling_read_only_snapshot": external_after,
            "coupling_ledger_modified_by_runner": False, "next_case_started": False,
        }
        _atomic_json(recovery_dir / "recovery_receipt.json",
                     _self_hashed(receipt_body, "receipt_sha256"))
        if sha_file(status_path) != receipt_body["runner_status_sha256"]:
            raise RecoveryError("RUNNER_STATUS_CHANGED_AFTER_RECEIPT")
        if sha_file(result_path) != receipt_body["scheduled_result_sha256"]:
            raise RecoveryError("SCHEDULED_RESULT_CHANGED_AFTER_RECEIPT")
        return {
            "result": "RECOVERED_AND_CLOSED", "recovery_directory": str(recovery_dir),
            "receipt_path": str(recovery_dir / "recovery_receipt.json"),
            "receipt_sha256": sha_file(recovery_dir / "recovery_receipt.json"),
            "truth_h5": str(run_dir / "truth.h5"),
            "truth_h5_sha256": final_hashes["truth_h5_sha256"],
            "solver_entry_count": 1, "solver_invocations": 1,
            "solver_invocations_during_recovery": 0, "automatic_replay_count": 0,
            "runner_slot_released": True, "scheduled_query_state": query.get("state"),
        }
    except BaseException as exc:
        failure = {
            "schema": "APCD_GPU_RUNNER_V1_POSTENTRY_RECOVERY_FAILURE_V1",
            "case_id": case_id, "attempt_id": attempt_id, "run_id": run_id,
            "request_id": request_id, "phase": phase, "observed_utc": now_utc(),
            "exception_type": type(exc).__name__, "exception": str(exc)[:2000],
            "traceback": traceback.format_exc(), "solver_invocations_during_recovery": 0,
            "runner_status_sha256": sha_file(status_path) if status_path.is_file() else None,
            "runner_registry_sha256": sha_file(registry_path) if registry_path.is_file() else None,
            "run_inventory_after_failure": inventory(run_dir),
        }
        try:
            _atomic_json(recovery_dir / "recovery_failure.json", failure)
        except BaseException:
            pass
        raise
