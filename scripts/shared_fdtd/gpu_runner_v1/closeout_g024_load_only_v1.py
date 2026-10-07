from __future__ import annotations

"""One-run, zero-solver G024 closeout after LOAD-only truth recovery failed.

This fixed Runner-owner tool only writes a new receipt directory. It never edits
status.json, registry.json, the Coupling ledger, controller status, or slot files.
"""

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CASE_ID = "K6GDP2_DEV_G024"
ATTEMPT_ID = "attempt_001"
RUN_ID = "K6V2_G024_20261007T123943Z_713590ad"
REQUEST_ID = "cd1c1a59118d2b78510df82906e75d77"
CONTROLLER_ID = "f0aeb35290a77db5c05c0346f1a40f81"
QUEUE_ID = "K6V2V128REMAINING20261007105811Z"
EXPECTED_REQUEST_SHA256 = "643d3c38215efd48ac98b12d2cfbacc9b5e22a63aa34e7eeb4d74da12a4f655d"
EXPECTED_ENVELOPE_SHA256 = "f35ef183a85a525d7155691d18d06e6333e57d9cdde2bd62b2e9a2d8a76503eb"
EXPECTED_LEDGER_SHA256 = "dbb9883e32b533330c90b3d4eff08b0988468eaf50f49081753e95e92de0d54b"
RUNNER_ROOT = Path(r"D:\apcd_runtime\gpu_production_runner_v1")
COUPLING_ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
COUPLING_REPORT = COUPLING_ROOT / "reports" / "coupling" / "COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1"
COUPLING_LEDGER = COUPLING_REPORT / "QUEUE_EXECUTION_LEDGER_V1.json"
CONTROLLER_STATUS = COUPLING_REPORT / "CONTROLLER_STATUS_K6V2SERIAL20261007T105811Z_ce8009d2.json"
CONTROL_DB = Path(r"D:\apcd_runtime\global_fdtd_control_v3\control.sqlite3")
LUMERICAL_API_DIR = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
EXPECTED_MONITORS = ("MON_IN", "MON_PRENP", "MON_POSTNP", "MON_REFLECTION")
_EXPECTED_FSP_SHA = "be83e19c6c6a95ba42ba9c24a609b96cbafcc7f668ea653063c7dd1ccb9a445c"
ENGINE_NAMES = {"fdtd-engine.exe", "fdtd-engine-msmpi.exe", "fdtd-engine-mpich.exe",
                "fdtd-engine-hybrid.exe", "mpiexec.exe", "mpiexec.hydra.exe", "smpd.exe"}

class CloseoutBlocked(RuntimeError):
    pass

def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")

def _sha_bytes(data):
    return hashlib.sha256(data).hexdigest()

def _sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def _read_json(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise CloseoutBlocked("JSON_READ_FAILED:" + str(path)) from exc
    if not isinstance(value, dict):
        raise CloseoutBlocked("JSON_OBJECT_REQUIRED:" + str(path))
    return value

def _self_hashed(body, key):
    return dict(body, **{key: _sha_bytes(_canonical(body))})

def _write_exclusive(path, value):
    path = Path(path)
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2,
                     allow_nan=False).encode("utf-8") + b"\n"
    try:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise CloseoutBlocked("CLOSEOUT_FILE_ALREADY_EXISTS:" + path.name) from exc
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return _sha(path)

def _run_dir(root=RUNNER_ROOT):
    return Path(root) / "runs" / CASE_ID / ATTEMPT_ID / RUN_ID

def _request_dir(root=RUNNER_ROOT):
    return Path(root) / "requests" / "scheduled_run_one_v1" / REQUEST_ID

def _input_paths(root=RUNNER_ROOT):
    run = _run_dir(root)
    request = _request_dir(root)
    return {
        "request": request / "request.json",
        "worker_claim": request / "worker_claim.json",
        "result": request / "result.json",
        "status": run / "status.json",
        "registry": Path(root) / "registry.json",
        "run_manifest": run / "manifest.json",
        "pre_entry_revalidation": run / "pre_entry_revalidation.json",
        "setup_validation": run / "setup_validation.json",
        "run_fsp": run / "run.fsp",
        "validation": run / "validation.json",
        "hashes": run / "hashes.json",
        "process_exit_provenance": run / "gpu_standalone" / "forensics" / "process_exit_provenance.json",
        "runtime_timeline": run / "gpu_standalone" / "forensics" / "runtime_timeline.jsonl",
        "child_log": run / "gpu_standalone" / "child.log",
        "final_log_tail": run / "gpu_standalone" / "forensics" / "final_log_tail.json",
        "coupling_ledger": COUPLING_LEDGER,
        "coupling_controller_manifest": Path(root) / "requests" / "scheduled_queue_controller_v1" / CONTROLLER_ID / "controller_manifest.json",
        "coupling_controller_binding": Path(root) / "requests" / "scheduled_queue_controller_v1" / CONTROLLER_ID / "binding.json",
        "coupling_controller_status": CONTROLLER_STATUS,
    }

def _process_census():
    command = r"""$p=Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CreationDate,CommandLine; ConvertTo-Json -InputObject @($p) -Compress -Depth 3"""
    proc = subprocess.run(["powershell.exe", "-NoProfile", "-Command", command],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=45)
    if proc.returncode != 0:
        raise CloseoutBlocked("PROCESS_CENSUS_FAILED")
    try:
        rows = json.loads(proc.stdout)
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list):
            raise ValueError("list required")
    except Exception as exc:
        raise CloseoutBlocked("PROCESS_CENSUS_JSON_INVALID") from exc
    target_tokens = (RUN_ID.casefold(), REQUEST_ID.casefold(), CONTROLLER_ID.casefold(), QUEUE_ID.casefold())
    related, engines, queue = [], [], []
    api_servers = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("Name") or "")
        low_name = name.casefold()
        cmd = str(row.get("CommandLine") or "")
        low_cmd = cmd.casefold()
        if low_name == "fdtd-solutions.exe" and "-server" in low_cmd:
            api_servers += 1
        if low_name in ENGINE_NAMES or "fdtd-engine" in low_name:
            engines.append({"pid": row.get("ProcessId"), "name": name, "command_line": cmd[:1000]})
        is_target = any(token in low_cmd for token in target_tokens)
        if "fdtd-solutions.exe" in low_name and "-run" in low_cmd:
            is_target = True
        if low_name == "python.exe" and "task_scheduler_v1.py" in low_cmd and "worker-once" in low_cmd:
            is_target = True
        if is_target:
            related.append({"pid": row.get("ProcessId"), "name": name,
                            "creation_date": row.get("CreationDate"), "command_line": cmd[:1000]})
        if "serial_queue.py" in low_cmd and ("--execute" in low_cmd or QUEUE_ID.casefold() in low_cmd):
            queue.append({"pid": row.get("ProcessId"), "name": name, "command_line": cmd[:1000]})
    return {"schema": "APCD_GPU_RUNNER_V1_G024_PROCESS_CENSUS_V1", "captured_utc": _now(),
            "process_count": len(rows), "related_processes": related, "engine_processes": engines,
            "queue_execution_processes": queue, "unrelated_fdtd_server_count": api_servers}

def perform_load_only_probe(fsp, lumapi_module=None):
    fsp = Path(fsp).resolve(strict=True)
    before = _sha(fsp)
    if before != _EXPECTED_FSP_SHA:
        raise CloseoutBlocked("RUN_FSP_SHA_MISMATCH_BEFORE_LOAD")
    if lumapi_module is None:
        sys.path.insert(0, str(LUMERICAL_API_DIR))
        import lumapi as lumapi_module
    fdtd = None
    monitor_rows = []
    try:
        fdtd = lumapi_module.FDTD(hide=True)
        fdtd.load(str(fsp))
        fdtd.selectall()
        objects = fdtd.getAllSelectedObjects()
        object_types = {}
        for obj in objects:
            try:
                object_types[str(obj["name"])] = str(obj["type"])
            except Exception as exc:
                raise CloseoutBlocked("LOAD_ONLY_OBJECT_READBACK_INVALID") from exc
        if not set(EXPECTED_MONITORS).issubset(object_types):
            raise CloseoutBlocked("LOAD_ONLY_EXPECTED_MONITOR_MISSING")
        any_saved_result = False
        for name in EXPECTED_MONITORS:
            if object_types.get(name) != "DFTMonitor":
                raise CloseoutBlocked("LOAD_ONLY_MONITOR_TYPE_MISMATCH:" + name)
            row = {"name": name, "type": object_types[name]}
            for prop in ("monitor type", "z", "x span", "y span", "use wavelength spacing", "frequency points"):
                try:
                    value = fdtd.getnamed(name, prop)
                    if isinstance(value, (int, float, str, bool)):
                        row[prop] = value
                    else:
                        row[prop] = str(value)
                except Exception as exc:
                    row[prop + "_error"] = type(exc).__name__ + ":" + str(exc)
            result_checks = {}
            for result_name in ("E", "H", "T"):
                try:
                    value = fdtd.getresult(name, result_name)
                    keys = list(value.keys()) if isinstance(value, dict) else []
                    has_data = bool(keys) or (not isinstance(value, dict) and value is not None)
                    any_saved_result = any_saved_result or has_data
                    result_checks[result_name] = {"available": has_data, "keys": [str(k) for k in keys]}
                except Exception as exc:
                    message = str(exc)
                    if "can not find result" not in message.casefold():
                        raise CloseoutBlocked("LOAD_ONLY_RESULT_QUERY_FAILED:" + name + ":" + result_name) from exc
                    result_checks[result_name] = {"available": False,
                                                  "error": type(exc).__name__ + ":" + message}
            row["results"] = result_checks
            monitor_rows.append(row)
    finally:
        if fdtd is not None:
            fdtd.close()
    after = _sha(fsp)
    if after != before:
        raise CloseoutBlocked("RUN_FSP_CHANGED_DURING_LOAD_ONLY")
    recoverability = ("SAVED_RESULTS_PRESENT_REQUIRES_TRUTH_VALIDATOR" if any_saved_result
                      else "NOT_RECOVERABLE_NO_SAVED_MONITOR_RESULTS")
    return {"schema": "APCD_GPU_RUNNER_V1_G024_LOAD_ONLY_RECOVERABILITY_V1",
            "result": "LOAD_ONLY_PASS", "case_id": CASE_ID, "attempt_id": ATTEMPT_ID,
            "run_id": RUN_ID, "fsp_path": str(fsp), "fsp_sha256_before": before,
            "fsp_sha256_after": after, "monitor_readbacks": monitor_rows,
            "recoverability": recoverability, "solver_run_called": False,
            "save_called": False, "new_solver_entries": 0}

def validate_terminal_evidence(snapshot):
    status = snapshot["runner_status"]
    result = snapshot["runner_result"]
    registry = snapshot["registry_row"]
    if (status.get("case_id"), status.get("attempt_id"), status.get("run_id")) != (CASE_ID, ATTEMPT_ID, RUN_ID):
        raise CloseoutBlocked("RUNNER_STATUS_IDENTITY_MISMATCH")
    if (status.get("state") != "FAILED_POSTENTRY" or status.get("solver_entered") is not True
            or status.get("solver_invocations") != 1 or status.get("replay_count", 0) != 0):
        raise CloseoutBlocked("RUNNER_POSTENTRY_TERMINAL_STATE_INVALID")
    if (registry.get("case_id"), registry.get("attempt_id"), registry.get("run_id"), registry.get("state")) != (
            CASE_ID, ATTEMPT_ID, RUN_ID, "FAILED_POSTENTRY"):
        raise CloseoutBlocked("RUNNER_REGISTRY_TERMINAL_STATE_INVALID")
    if (result.get("state") != "TERMINAL" or result.get("result", {}).get("request_id") != REQUEST_ID
            or result.get("result", {}).get("exit_code") != 2
            or result.get("result", {}).get("solver_entered") is not True):
        raise CloseoutBlocked("RUNNER_REQUEST_NOT_TERMINAL_FAILED_POSTENTRY")
    if snapshot["load_probe"].get("recoverability") != "NOT_RECOVERABLE_NO_SAVED_MONITOR_RESULTS":
        raise CloseoutBlocked("LOAD_ONLY_DID_NOT_PROVE_NO_RECOVERABLE_TRUTH")
    census_before = snapshot.get("process_census_before", {})
    if (census_before.get("related_processes") or census_before.get("engine_processes")
            or census_before.get("queue_execution_processes")):
        raise CloseoutBlocked("PRE_LOAD_PROCESS_CENSUS_NOT_CLEAR")
    if snapshot["process_census"].get("related_processes") or snapshot["process_census"].get("engine_processes"):
        raise CloseoutBlocked("RELATED_PROCESS_OR_ENGINE_PRESENT")
    if snapshot["process_census"].get("queue_execution_processes"):
        raise CloseoutBlocked("COUPLING_QUEUE_EXECUTION_PROCESS_PRESENT")
    if snapshot.get("runner_markers_absent") is not True:
        raise CloseoutBlocked("RUNNER_SLOT_MARKER_STILL_PRESENT")
    controller = snapshot["controller_query"]
    if (controller.get("state") != "CONTROLLER_EXITED_NEEDS_RECONCILIATION"
            or (controller.get("task") or {}).get("State") != "Ready"):
        raise CloseoutBlocked("CONTROLLER_NOT_STOPPED_FOR_RECONCILIATION")
    coupling = snapshot["coupling_ledger"]
    if (coupling.get("sha256") != EXPECTED_LEDGER_SHA256 or coupling.get("entered_count") != 35
            or coupling.get("automatic_replay_count") != 0
            or coupling.get("g024_row", {}).get("run_id") != RUN_ID):
        raise CloseoutBlocked("COUPLING_LEDGER_CHANGED_OR_TARGET_MISMATCH")
    return {"schema": "APCD_GPU_RUNNER_V1_G024_POSTENTRY_DISPOSITION_V1",
            "case_id": CASE_ID, "attempt_id": ATTEMPT_ID, "run_id": RUN_ID,
            "request_id": REQUEST_ID, "result": "FAILED_POSTENTRY_NO_TRUTH",
            "runner_terminal_state_already_recorded": True, "solver_entry_consumed": True,
            "solver_invocations": 1, "physical_gpu_engine_observed": False,
            "automatic_replay_count": 0, "truth_available": False,
            "load_only_recoverability": "NOT_RECOVERABLE_NO_SAVED_MONITOR_RESULTS",
            "root_cause": "LUMERICAL_LICENSE_STARTUP_FAILED_BEFORE_GPU_ENGINE_OBSERVATION",
            "runner_failure_code_at_execution": "SOLVER_PROCESS_OBSERVATION_INVALID",
            "runner_slot_state": "CLOSED_MARKERS_ABSENT",
            "controller_state": "CONTROLLER_EXITED_NEEDS_RECONCILIATION",
            "controller_queue_resumable": False, "coupling_ledger_modified": False,
            "training_admitted": False, "scientific_valid": False}

def _process_and_task_snapshot():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import task_scheduler_v1 as scheduler
    one = scheduler.query_one(REQUEST_ID, root=RUNNER_ROOT)
    controller = scheduler.query_controller_task(CONTROLLER_ID, root=RUNNER_ROOT)
    census = _process_census()
    return one, controller, census

def closeout_g024_production():
    if RUNNER_ROOT.resolve() != Path(r"D:\apcd_runtime\gpu_production_runner_v1").resolve():
        raise CloseoutBlocked("PINNED_RUNNER_ROOT_MISMATCH")
    run_dir = _run_dir()
    closeout_dir = run_dir / "postentry_closeout_v1"
    if closeout_dir.exists():
        receipt = closeout_dir / "receipt.json"
        if receipt.is_file():
            current = _read_json(receipt)
            body = dict(current); saved = body.pop("receipt_sha256", None)
            if saved == _sha_bytes(_canonical(body)) and current.get("run_id") == RUN_ID:
                return {"result": "ALREADY_CLOSED", "receipt_path": str(receipt),
                        "receipt_sha256": _sha(receipt), "solver_invocations_after_closeout": 0}
        raise CloseoutBlocked("CLOSEOUT_DIRECTORY_ALREADY_EXISTS")
    paths = _input_paths()
    pinned = {
        "request": "ac2640a368a430cf3ea5a4cc26315325d6f779e4124ff00cb764ce162942ce79",
        "worker_claim": "11d2912bcb12cbd1768f4f9c18cc38ba0468f8907565092971333e2e36d70a11",
        "result": "579e18481cd3409937330d23644166f24cf4006405689866f9e53a8051b1f1ef",
        "status": "18e3bd3c1a40b4d839d6711802b425be25586881813895bc212ad2a20254bb02",
        "registry": "2ba5b25d6961a57296d91fc774f6d16e98ac9f270c2815cf42a9ba91306303d9",
        "run_manifest": "5fa2b33fb08e34f9d0d5e109bc6cd6f9088247c51e1f363172824e1cce0856fd",
        "pre_entry_revalidation": "395ec6a9676dd9c4a79bc6f1360b11f5b94db6668c84438e247bd56489429e27",
        "setup_validation": "d23c59a3ee06a6bd6137acf2bc878dc9b696bf80c2e185e44c18145f5d9b48f8",
        "run_fsp": _EXPECTED_FSP_SHA,
        "validation": "0edaf0a487f3182602585b0237ae771e42b0fc273f4901829ba0b17932f49bbc",
        "hashes": "0edaf0a487f3182602585b0237ae771e42b0fc273f4901829ba0b17932f49bbc",
        "process_exit_provenance": "94fa3d5913551a8ac862fd25a7b2c04367f94b44725a7d2eec2144901e38648b",
        "runtime_timeline": "e05834b5390aaa08126493e2760cdc9cee276ae2a5605c02ec72fb66da71c8fb",
        "child_log": "4ec37fcc2b851d34bf8fa3da9dc01d401edfad0db10c32112927232ec46bc215",
        "final_log_tail": "e28001a4d8253d9efa2c561c922d642fad100ec870f9268632dc734e58632ce0",
        "coupling_ledger": EXPECTED_LEDGER_SHA256,
        "coupling_controller_manifest": "f0aeb35290a77db5c05c0346f1a40f81a11f6fd9dab1a828a2ce7ab41f998edd",
        "coupling_controller_binding": "8453b306946393d016cafd8a881317db54e6aaf63d260b5e302cf34dbf5ddc3b",
        "coupling_controller_status": "0090880a1f0d5f6a34fbf1a557c0093e506276159c59c9b16c2fd89726eee400",
    }
    input_hashes = {}
    for label, expected in pinned.items():
        path = paths[label]
        if not path.is_file() or path.is_symlink() or _sha(path) != expected:
            raise CloseoutBlocked("PINNED_INPUT_MISMATCH:" + label)
        input_hashes[label] = expected
    run_status = _read_json(paths["status"])
    registry = _read_json(paths["registry"])
    registry_rows = [row for row in registry.get("runs", []) if isinstance(row, dict)
                     and row.get("case_id") == CASE_ID and row.get("attempt_id") == ATTEMPT_ID
                     and row.get("run_id") == RUN_ID]
    if len(registry_rows) != 1:
        raise CloseoutBlocked("RUNNER_REGISTRY_TARGET_NOT_UNIQUE")
    request = _read_json(paths["request"])
    result = _read_json(paths["result"])
    manifest = _read_json(paths["run_manifest"])
    provenance = _read_json(paths["process_exit_provenance"])
    if (request.get("request_id") != REQUEST_ID or request.get("request_sha256") != EXPECTED_REQUEST_SHA256
            or request.get("manifest_sha256") != EXPECTED_ENVELOPE_SHA256):
        raise CloseoutBlocked("REQUEST_IDENTITY_OR_HASH_INVALID")
    if (manifest.get("run_id") != RUN_ID or manifest.get("pre_fsp_sha256") != _sha(paths["run_fsp"])
            or manifest.get("physical_contract_sha256") != "32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5"):
        raise CloseoutBlocked("RUN_MANIFEST_FSP_OR_CONTRACT_MISMATCH")
    if (provenance.get("reason") != "CHILD_RETURNED" or provenance.get("child", {}).get("return_code") != 0
            or provenance.get("child", {}).get("pid") != 45644):
        raise CloseoutBlocked("PROCESS_EXIT_PROVENANCE_MISMATCH")
    if ("could not connect to ansys license server" not in paths["child_log"].read_text(encoding="utf-8", errors="replace").casefold()
            or _read_json(paths["validation"]) != {"state": "PENDING"}
            or _read_json(paths["hashes"]) != {"state": "PENDING"}):
        raise CloseoutBlocked("LICENSE_FAILURE_OR_PENDING_TRUTH_EVIDENCE_MISMATCH")
    source_fsp = Path(manifest.get("pre_fsp_path", ""))
    if not source_fsp.is_file() or _sha(source_fsp) != manifest.get("pre_fsp_sha256"):
        raise CloseoutBlocked("SOURCE_PRE_FSP_HASH_MISMATCH")
    if (run_dir / "run" / "run_output.h5").exists() or (run_dir / "truth.h5").exists():
        raise CloseoutBlocked("TRUTH_ARTIFACT_EXISTS_REQUIRES_VALIDATOR")
    if (RUNNER_ROOT / ".runner.lock").exists() or (RUNNER_ROOT / "active_run.json").exists():
        raise CloseoutBlocked("RUNNER_SLOT_MARKER_PRESENT")
    run_inventory = {str(p.relative_to(run_dir)): {"size": p.stat().st_size, "sha256": _sha(p)}
                     for p in sorted(run_dir.rglob("*")) if p.is_file()}
    one, controller, processes_before = _process_and_task_snapshot()
    if one.get("state") != "TERMINAL" or one.get("result", {}).get("exit_code") != 2:
        raise CloseoutBlocked("RUNNER_REQUEST_NOT_TERMINAL_FAILURE")
    if controller.get("state") != "CONTROLLER_EXITED_NEEDS_RECONCILIATION" or (controller.get("task") or {}).get("State") != "Ready":
        raise CloseoutBlocked("CONTROLLER_NOT_IDLE_FOR_OWNER_RECONCILIATION")
    if (processes_before.get("related_processes") or processes_before.get("engine_processes")
            or processes_before.get("queue_execution_processes")):
        raise CloseoutBlocked("PRE_LOAD_PROCESS_CENSUS_NOT_CLEAR")
    if (not run_dir.is_dir() or not (run_dir / "run.fsp").is_file()):
        raise CloseoutBlocked("RUN_FSP_MISSING")
    fsp_sha_before = _sha(run_dir / "run.fsp")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import adapter
    control = adapter.read_global_entry_control()
    if control.get("result") != "PASS":
        raise CloseoutBlocked("GLOBAL_CONTROL_READ_NOT_HEALTHY")
    sys.path.insert(0, str(LUMERICAL_API_DIR))
    import lumapi
    load_probe = perform_load_only_probe(run_dir / "run.fsp", lumapi_module=lumapi)
    if load_probe.get("recoverability") != "NOT_RECOVERABLE_NO_SAVED_MONITOR_RESULTS":
        raise CloseoutBlocked("LOAD_ONLY_FOUND_RESULTS_REQUIRING_SEPARATE_VALIDATION")
    processes_after = _process_census()
    if processes_after.get("related_processes") or processes_after.get("engine_processes") or processes_after.get("queue_execution_processes"):
        raise CloseoutBlocked("POST_LOAD_PROCESS_CENSUS_NOT_CLEAR")
    if (RUNNER_ROOT / ".runner.lock").exists() or (RUNNER_ROOT / "active_run.json").exists():
        raise CloseoutBlocked("RUNNER_SLOT_MARKER_APPEARED_DURING_LOAD_ONLY")
    if _sha(run_dir / "run.fsp") != fsp_sha_before or _sha(run_dir / "run.fsp") != pinned["run_fsp"]:
        raise CloseoutBlocked("RUN_FSP_CHANGED_AFTER_LOAD_ONLY")
    after_inventory = {str(p.relative_to(run_dir)): {"size": p.stat().st_size, "sha256": _sha(p)}
                       for p in sorted(run_dir.rglob("*")) if p.is_file()}
    if after_inventory != run_inventory:
        raise CloseoutBlocked("RUN_DIRECTORY_CHANGED_DURING_LOAD_ONLY")
    controller_status = _read_json(CONTROLLER_STATUS)
    ledger = _read_json(COUPLING_LEDGER)
    coupling = {"sha256": _sha(COUPLING_LEDGER), "entered_count": ledger.get("entered_count"),
                "automatic_replay_count": ledger.get("automatic_replay_count"),
                "current_case": ledger.get("current_case"),
                "g024_row": ledger.get("case_records", {}).get(CASE_ID)}
    snapshot = {"runner_status": run_status, "runner_result": one,
                "registry_row": registry_rows[0], "load_probe": load_probe,
                "process_census_before": processes_before, "process_census": processes_after,
                "runner_markers_absent": True,
                "controller_query": controller, "controller_status": controller_status,
                "coupling_ledger": coupling, "control_snapshot": control}
    disposition = validate_terminal_evidence(snapshot)
    current_input_hashes = {label: _sha(path) for label, path in paths.items()}
    for label, expected in pinned.items():
        if current_input_hashes[label] != expected:
            raise CloseoutBlocked("INPUT_CHANGED_DURING_CLOSEOUT:" + label)
    if _sha(COUPLING_LEDGER) != EXPECTED_LEDGER_SHA256 or _sha(CONTROLLER_STATUS) != pinned["coupling_controller_status"]:
        raise CloseoutBlocked("COUPLING_STATE_CHANGED_DURING_CLOSEOUT")
    closeout_dir.mkdir()
    claim_body = {"schema": "APCD_GPU_RUNNER_V1_G024_POSTENTRY_CLOSEOUT_CLAIM_V1",
                  "target": {"case_id": CASE_ID, "attempt_id": ATTEMPT_ID, "run_id": RUN_ID,
                             "request_id": REQUEST_ID}, "created_utc": _now(),
                  "runner_worktree_head": subprocess.run(["git", "rev-parse", "HEAD"],
                      cwd=str(Path(__file__).resolve().parents[3]), capture_output=True, text=True,
                      encoding="utf-8", errors="replace", check=True).stdout.strip(),
                  "input_hashes": input_hashes, "run_inventory_sha256": _sha_bytes(_canonical(run_inventory)),
                  "control_snapshot": control, "load_only_probe_sha256": _sha_bytes(_canonical(load_probe))}
    claim = _self_hashed(claim_body, "claim_sha256")
    claim_sha = _write_exclusive(closeout_dir / "claim.json", claim)
    probe = _self_hashed(load_probe, "probe_sha256")
    probe_sha = _write_exclusive(closeout_dir / "load_only_probe.json", probe)
    disposition_body = dict(disposition, claim_sha256=claim_sha, load_only_probe_sha256=probe_sha,
                            input_hashes=input_hashes, coupling_ledger_sha256=EXPECTED_LEDGER_SHA256,
                            controller_status_sha256=pinned["coupling_controller_status"])
    disp = _self_hashed(disposition_body, "disposition_sha256")
    disp_sha = _write_exclusive(closeout_dir / "disposition.json", disp)
    records, previous = [], None
    for sequence, (event, payload) in enumerate((
        ("LOAD_ONLY_RECOVERABILITY_CHECKED", {"probe_sha256": probe_sha, "recoverability": load_probe["recoverability"]}),
        ("FAILED_POSTENTRY_NO_TRUTH_CONFIRMED", {"disposition_sha256": disp_sha, "entry_consumed": True}),
        ("RUNNER_SLOT_CLOSED_AND_QUEUE_HELD", {"runner_status_sha256": pinned["status"], "registry_sha256": pinned["registry"], "controller_requires_reconciliation": True}),
        ("COUPLING_LEDGER_LEFT_UNCHANGED", {"coupling_ledger_sha256": EXPECTED_LEDGER_SHA256}),
    ), 1):
        body = {"sequence": sequence, "event": event, "recorded_utc": _now(),
                "previous_record_sha256": previous, "payload": payload}
        row = _self_hashed(body, "record_sha256")
        records.append(row); previous = row["record_sha256"]
    journal_body = {"schema": "APCD_GPU_RUNNER_V1_G024_POSTENTRY_CLOSEOUT_HASH_CHAIN_V1",
                    "claim_sha256": claim_sha, "records": records, "chain_head_sha256": previous}
    journal = _self_hashed(journal_body, "journal_sha256")
    journal_sha = _write_exclusive(closeout_dir / "journal.json", journal)
    receipt_body = {"schema": "APCD_GPU_RUNNER_V1_G024_POSTENTRY_CLOSEOUT_RECEIPT_V1",
                    "case_id": CASE_ID, "attempt_id": ATTEMPT_ID, "run_id": RUN_ID,
                    "request_id": REQUEST_ID, "result": "CLOSED",
                    "disposition": "FAILED_POSTENTRY_NO_TRUTH", "solver_entry_count": 1,
                    "solver_invocations": 1, "automatic_replay_count": 0,
                    "truth_available": False, "scientific_valid": False, "training_admitted": False,
                    "load_only_recoverability": load_probe["recoverability"],
                    "physical_gpu_engine_observed": False, "child_return_code": 0,
                    "failure_root_cause": "ANSYS_LICENSE_SHARING_STARTUP_FAILURE",
                    "runner_slot_closed": True, "controller_queue_resumable": False,
                    "coupling_ledger_modified": False,
                    "claim_sha256": claim_sha, "load_only_probe_sha256": probe_sha,
                    "disposition_sha256": disp_sha, "journal_sha256": journal_sha,
                    "status_sha256": pinned["status"], "registry_sha256": pinned["registry"],
                    "coupling_ledger_sha256": EXPECTED_LEDGER_SHA256,
                    "controller_status_sha256": pinned["coupling_controller_status"],
                    "input_hashes": input_hashes, "created_utc": _now()}
    receipt = _self_hashed(receipt_body, "receipt_sha256")
    receipt_sha = _write_exclusive(closeout_dir / "receipt.json", receipt)
    if _sha(paths["status"]) != pinned["status"] or _sha(paths["registry"]) != pinned["registry"]:
        raise CloseoutBlocked("RUNNER_TERMINAL_STATE_CHANGED_DURING_RECEIPT_WRITE")
    if _sha(COUPLING_LEDGER) != EXPECTED_LEDGER_SHA256:
        raise CloseoutBlocked("COUPLING_LEDGER_CHANGED_DURING_RECEIPT_WRITE")
    return {"result": "CLOSED_FAILED_POSTENTRY_NO_TRUTH", "receipt_path": str(closeout_dir / "receipt.json"),
            "receipt_sha256": receipt_sha, "disposition_sha256": disp_sha,
            "journal_sha256": journal_sha, "load_only_probe_sha256": probe_sha,
            "solver_invocations_after_recovery": 0, "automatic_replays": 0,
            "controller_queue_resumable": False, "coupling_ledger_modified": False}

def main():
    try:
        print(json.dumps(closeout_g024_production(), sort_keys=True, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"result": "BLOCKED", "error": type(exc).__name__ + ":" + str(exc),
                          "solver_invocations": 0, "automatic_replays": 0}, sort_keys=True, ensure_ascii=False))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
