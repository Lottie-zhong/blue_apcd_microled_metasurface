"""Windows Task Scheduler adapter for APCD GPU Runner V1.

Production Task Scheduler invokes exactly one durable request per task instance.
The SSH-side caller only submits or queries a request; it never owns the FDTD
worker process. The Windows Scheduler task is pinned to the DELL interactive
principal and is configured with IgnoreNew, a 72-hour execution limit, and no
automatic restart.
"""
from __future__ import annotations

import datetime as _dt
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

SCHEMA_REQUEST = "APCD_GPU_RUNNER_V1_SCHEDULED_REQUEST_V1"
SCHEMA_CLAIM = "APCD_GPU_RUNNER_V1_SCHEDULED_WORKER_CLAIM_V1"
SCHEMA_RESULT = "APCD_GPU_RUNNER_V1_SCHEDULED_RESULT_V1"
TASK_NAME = r"\APCD_GPU_RUNNER_V1_SINGLE_CASE_WORKER"
CONTROLLER_TASK_NAME = r"\APCD_GPU_RUNNER_V1_COUPLING_SERIAL_QUEUE_CONTROLLER"
TASK_PYTHON = r"N:\anaconda_envs\RCP_LCP\python.exe"
TASK_EXECUTION_LIMIT = "PT72H"
OWNER_ACCOUNT = "DELL"
EXPECTED_WHOAMI = "desktop-nne313k\\dell"
PRODUCTION_ROOT = Path(r"D:\apcd_runtime\gpu_production_runner_v1")
COUPLING_WORKTREE = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
REQUEST_ROOT = PRODUCTION_ROOT / "requests" / "scheduled_run_one_v1"
CONTROLLER_REQUEST_ROOT = PRODUCTION_ROOT / "requests" / "scheduled_queue_controller_v1"
CONTROLLER_TASK_DIR = PRODUCTION_ROOT / "scheduler_controller_v1"
TASK_LOCK = PRODUCTION_ROOT / "scheduler_worker_v1.lock"
REQUEST_ID_RE = re.compile(r"^[0-9a-f]{32}$")
CONTROLLER_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SCHEMA_CONTROLLER_MANIFEST = "APCD_GPU_RUNNER_V1_COUPLING_QUEUE_CONTROLLER_MANIFEST_V1"
SCHEMA_CONTROLLER_BINDING = "APCD_GPU_RUNNER_V1_QUEUE_CONTROLLER_BINDING_V1"
SCHEMA_CONTROLLER_STATUS = "APCD_GPU_RUNNER_V1_QUEUE_CONTROLLER_STATUS_V1"
SCHEMA_CONTROLLER_RESUME = "APCD_GPU_RUNNER_V1_QUEUE_CONTROLLER_RESUME_RECEIPT_V1"
CONTROLLER_PROTOCOL = "APCD_GPU_RUNNER_V1_QUEUE_CONTROLLER_CLI_V1"


class SchedulerRunnerError(RuntimeError):
    pass


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def _sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    raw = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    with temp.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def _create_exclusive_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    try:
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        return False
    return True


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _now():
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _adapter_module():
    try:
        import adapter
    except ImportError:
        from . import adapter
    return adapter


def _task_script_path():
    return Path(__file__).resolve()


def _expected_principal():
    if os.name != "nt":
        return OWNER_ACCOUNT.lower()
    proc = subprocess.run(["whoami.exe", "/user", "/fo", "csv", "/nh"],
                          text=True, capture_output=True, encoding="utf-8", errors="replace",
                          timeout=15, check=False)
    if proc.returncode != 0:
        raise SchedulerRunnerError("SCHEDULER_PRINCIPAL_SID_QUERY_FAILED")
    try:
        row = next(csv.reader(proc.stdout.splitlines()))
        sid = row[1].strip()
    except (StopIteration, IndexError) as exc:
        raise SchedulerRunnerError("SCHEDULER_PRINCIPAL_SID_QUERY_INVALID") from exc
    if not sid.startswith("S-"):
        raise SchedulerRunnerError("SCHEDULER_PRINCIPAL_SID_QUERY_INVALID")
    return sid.lower()


def _xml_children(node, name):
    return [child for child in node.iter() if child.tag.rsplit("}", 1)[-1] == name]


def validate_task_definition_xml(xml_text, *, expected_script=None, expected_principal=None,
                                 task_name=TASK_NAME, expected_argument="worker-once",
                                 expected_manifest=None, expected_manifest_sha256=None,
                                 expected_request_id=None, expected_resume_receipt=None,
                                 expected_resume_receipt_sha256=None, require_no_triggers=False):
    try:
        root = ET.fromstring(xml_text.lstrip("\ufeff"))
    except ET.ParseError as exc:
        raise SchedulerRunnerError("SCHEDULER_TASK_XML_INVALID") from exc
    trigger_containers = _xml_children(root, "Triggers")
    if require_no_triggers and (
            _xml_children(root, "Trigger")
            or any(list(container) for container in trigger_containers)):
        raise SchedulerRunnerError("SCHEDULER_TASK_TRIGGERS_FORBIDDEN")
    principals = _xml_children(root, "Principal")
    if len(principals) != 1:
        raise SchedulerRunnerError("SCHEDULER_TASK_PRINCIPAL_INVALID")
    principal = principals[0]
    user_ids = _xml_children(principal, "UserId")
    logon_types = _xml_children(principal, "LogonType")
    levels = _xml_children(principal, "RunLevel")
    if len(user_ids) != 1 or len(logon_types) != 1 or len(levels) > 1:
        raise SchedulerRunnerError("SCHEDULER_TASK_PRINCIPAL_INVALID")
    account = (user_ids[0].text or "").lower()
    if expected_principal and account != expected_principal.lower():
        raise SchedulerRunnerError("SCHEDULER_TASK_WRONG_PRINCIPAL")
    if logon_types[0].text != "InteractiveToken":
        raise SchedulerRunnerError("SCHEDULER_TASK_LOGON_TYPE_UNSUPPORTED")
    run_level = levels[0].text if levels else "LeastPrivilege"
    if run_level != "LeastPrivilege":
        raise SchedulerRunnerError("SCHEDULER_TASK_RUNLEVEL_UNSUPPORTED")
    settings = _xml_children(root, "Settings")
    if len(settings) != 1:
        raise SchedulerRunnerError("SCHEDULER_TASK_SETTINGS_INVALID")
    multiple = _xml_children(settings[0], "MultipleInstancesPolicy")
    limit = _xml_children(settings[0], "ExecutionTimeLimit")
    restart = _xml_children(settings[0], "RestartOnFailure")
    if len(multiple) != 1 or multiple[0].text != "IgnoreNew":
        raise SchedulerRunnerError("SCHEDULER_TASK_MULTIPLE_INSTANCE_POLICY_INVALID")
    limit_value = limit[0].text if limit else TASK_EXECUTION_LIMIT
    if len(limit) > 1 or limit_value != TASK_EXECUTION_LIMIT:
        raise SchedulerRunnerError("SCHEDULER_TASK_EXECUTION_TIME_LIMIT_INVALID")
    if restart:
        raise SchedulerRunnerError("SCHEDULER_TASK_AUTOMATIC_RESTART_FORBIDDEN")
    actions = _xml_children(root, "Exec")
    if len(actions) != 1:
        raise SchedulerRunnerError("SCHEDULER_TASK_ACTION_INVALID")
    commands = _xml_children(actions[0], "Command")
    arguments = _xml_children(actions[0], "Arguments")
    if len(commands) != 1 or len(arguments) != 1:
        raise SchedulerRunnerError("SCHEDULER_TASK_ACTION_INVALID")
    command = (commands[0].text or "").strip().replace("/", "\\").lower()
    args = (arguments[0].text or "").replace("/", "\\").lower()
    if command != TASK_PYTHON.lower():
        raise SchedulerRunnerError("SCHEDULER_TASK_EXECUTABLE_MISMATCH")
    script_path = Path(expected_script or _task_script_path())
    expected_arg = str(script_path).replace("/", "\\").lower()
    if expected_arg not in args or str(expected_argument).lower() not in args:
        raise SchedulerRunnerError("SCHEDULER_TASK_ACTION_MISMATCH")
    checks = (
        (expected_manifest, None),
        (expected_manifest_sha256, "--runner-controller-manifest-sha256"),
        (expected_request_id, "--runner-controller-request-id"),
        (expected_resume_receipt, "--runner-resume-receipt"),
        (expected_resume_receipt_sha256, "--runner-resume-receipt-sha256"),
    )
    for expected_value, option in checks:
        if expected_value is None:
            continue
        normalized = str(expected_value).replace("/", "\\\\").lower()
        if normalized not in args or (option and option not in args):
            raise SchedulerRunnerError("SCHEDULER_TASK_CONTROLLER_ARGUMENT_MISMATCH")
    return {
        "task_name": task_name,
        "principal": account,
        "logon_type": logon_types[0].text,
        "run_level": run_level,
        "multiple_instances": multiple[0].text,
        "execution_time_limit": limit_value,
        "automatic_restart": False,
        "command": commands[0].text,
        "arguments": arguments[0].text,
    }


def _validate_scheduler_task_name(task_name):
    if task_name not in (TASK_NAME, CONTROLLER_TASK_NAME):
        raise SchedulerRunnerError("SCHEDULER_TASK_NAME_OVERRIDE_FORBIDDEN")
    return task_name.lstrip("\\\\")


def _query_task_xml(task_name=TASK_NAME):
    if os.name != "nt":
        raise SchedulerRunnerError("SCHEDULER_TASK_REQUIRES_WINDOWS")
    _validate_scheduler_task_name(task_name)
    proc = subprocess.run(
        ["schtasks.exe", "/Query", "/TN", task_name, "/XML"],
        text=True, capture_output=True, encoding="utf-8", errors="replace", timeout=30, check=False,
    )
    if proc.returncode != 0:
        label = "SCHEDULER_WORKER_TASK_NOT_INSTALLED" if task_name == TASK_NAME else "SCHEDULER_CONTROLLER_TASK_NOT_INSTALLED"
        raise SchedulerRunnerError(label + ":" + proc.stderr.strip()[:400])
    return proc.stdout


def verify_worker_task(*, xml_text=None, expected_script=None, expected_principal=None):
    xml_text = _query_task_xml() if xml_text is None else xml_text
    principal = _expected_principal() if expected_principal is None else expected_principal
    validated = validate_task_definition_xml(
        xml_text, expected_script=expected_script, expected_principal=principal)
    if xml_text is not None and os.name == "nt":
        info = _task_info()
        if str(info.get("UserId", "")).upper() != OWNER_ACCOUNT:
            raise SchedulerRunnerError("SCHEDULER_TASK_WRONG_PRINCIPAL")
        if int(info.get("LogonType", -1)) != 3 or int(info.get("RunLevel", -1)) != 0:
            raise SchedulerRunnerError("SCHEDULER_TASK_PRINCIPAL_SETTINGS_INVALID")
        multiple = info.get("MultipleInstances")
        if multiple not in (2, "2", "IgnoreNew"):
            raise SchedulerRunnerError("SCHEDULER_TASK_MULTIPLE_INSTANCE_POLICY_INVALID")
        if str(info.get("ExecutionTimeLimit")) != TASK_EXECUTION_LIMIT:
            raise SchedulerRunnerError("SCHEDULER_TASK_EXECUTION_TIME_LIMIT_INVALID")
        if info.get("RestartCount") not in (None, 0, "0"):
            raise SchedulerRunnerError("SCHEDULER_TASK_AUTOMATIC_RESTART_FORBIDDEN")
    return validated


def _task_info(task_name=TASK_NAME):
    if os.name != "nt":
        return {"state": "UNAVAILABLE", "last_task_result": None}
    leaf = _validate_scheduler_task_name(task_name)
    ps = (
        "$ErrorActionPreference='Stop'; "
        "$t=Get-ScheduledTask -TaskName '" + leaf + "'; "
        "$i=Get-ScheduledTaskInfo -TaskName '" + leaf + "'; "
        "[pscustomobject]@{State=[string]$t.State;LastTaskResult=$i.LastTaskResult;LastRunTime=[string]$i.LastRunTime; "
        "UserId=$t.Principal.UserId;LogonType=$t.Principal.LogonType;RunLevel=$t.Principal.RunLevel; "
        "MultipleInstances=$t.Settings.MultipleInstances;ExecutionTimeLimit=[string]$t.Settings.ExecutionTimeLimit; "
        "RestartCount=$t.Settings.RestartCount} | ConvertTo-Json -Compress"
    )
    proc = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
        text=True, capture_output=True, encoding="utf-8", errors="replace", timeout=30, check=False,
    )
    if proc.returncode != 0:
        raise SchedulerRunnerError("SCHEDULER_TASK_QUERY_FAILED:" + proc.stderr.strip()[:400])
    try:
        raw = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise SchedulerRunnerError("SCHEDULER_TASK_QUERY_INVALID") from exc
    return raw


def _start_task(task_name):
    _validate_scheduler_task_name(task_name)
    proc = subprocess.run(
        ["schtasks.exe", "/Run", "/TN", task_name],
        text=True, capture_output=True, encoding="utf-8", errors="replace", timeout=30, check=False,
    )
    if proc.returncode != 0:
        label = "SCHEDULER_WORKER_START_FAILED" if task_name == TASK_NAME else "SCHEDULER_CONTROLLER_START_FAILED"
        raise SchedulerRunnerError(label + ":" + proc.stderr.strip()[:400])


def _start_worker_task():
    verify_worker_task()
    _start_task(TASK_NAME)


def _manifest_identity(manifest_path, adapter_module=None):
    adapter_module = adapter_module or _adapter_module()
    manifest_path = Path(manifest_path).resolve(strict=True)
    manifest, _contract_path = adapter_module.read_cli_manifest(manifest_path)
    required = ("case_id", "attempt_id", "run_id")
    if any(not isinstance(manifest.get(key), str) or not manifest[key] for key in required):
        raise SchedulerRunnerError("SCHEDULED_REQUEST_MANIFEST_IDENTITY_INVALID")
    identity = {key: manifest[key] for key in required}
    return manifest_path, manifest, identity


def _request_paths(root, request_id):
    return Path(root) / "requests" / "scheduled_run_one_v1" / request_id


def _read_and_verify_request(path):
    request = _read_json(path)
    if request.get("schema") != SCHEMA_REQUEST or not REQUEST_ID_RE.fullmatch(str(request.get("request_id", ""))):
        raise SchedulerRunnerError("SCHEDULED_REQUEST_SCHEMA_INVALID")
    body = dict(request)
    saved = body.pop("request_sha256", None)
    if saved != _sha_bytes(_canonical(body)):
        raise SchedulerRunnerError("SCHEDULED_REQUEST_HASH_INVALID")
    manifest_path = Path(request["manifest_path"]).resolve(strict=True)
    if _sha(manifest_path) != request.get("manifest_sha256"):
        raise SchedulerRunnerError("SCHEDULED_REQUEST_MANIFEST_HASH_CHANGED")
    if _sha(Path(__file__).resolve()) != request.get("worker_module_sha256"):
        raise SchedulerRunnerError("SCHEDULED_REQUEST_WORKER_MODULE_CHANGED")
    adapter_path = Path(request["adapter_path"]).resolve(strict=True)
    if _sha(adapter_path) != request.get("adapter_sha256"):
        raise SchedulerRunnerError("SCHEDULED_REQUEST_ADAPTER_CHANGED")
    return request


def submit_one(manifest_path, *, root=PRODUCTION_ROOT, adapter_module=None, start_task=True):
    adapter_module = adapter_module or _adapter_module()
    manifest_path, _manifest, identity = _manifest_identity(manifest_path, adapter_module)
    manifest_sha = _sha(manifest_path)
    adapter_path = Path(adapter_module.__file__).resolve()
    stable = {
        "schema": SCHEMA_REQUEST,
        "identity": identity,
        "manifest_path": str(manifest_path),
        "manifest_sha256": manifest_sha,
        "adapter_path": str(adapter_path),
        "adapter_sha256": _sha(adapter_path),
        "worker_module_path": str(Path(__file__).resolve()),
        "worker_module_sha256": _sha(Path(__file__).resolve()),
    }
    request_id = _sha_bytes(_canonical(stable))[:32]
    body = dict(stable, request_id=request_id, created_utc=_now())
    request = dict(body, request_sha256=_sha_bytes(_canonical(body)))
    request_dir = _request_paths(root, request_id)
    request_dir.mkdir(parents=True, exist_ok=True)
    request_path = request_dir / "request.json"
    if request_path.exists():
        existing = _read_and_verify_request(request_path)
        for key, value in stable.items():
            if existing.get(key) != value:
                raise SchedulerRunnerError("SCHEDULED_REQUEST_ID_COLLISION")
    else:
        if not _create_exclusive_json(request_path, request):
            existing = _read_and_verify_request(request_path)
            for key, value in stable.items():
                if existing.get(key) != value:
                    raise SchedulerRunnerError("SCHEDULED_REQUEST_ID_COLLISION")
    if start_task and not (request_dir / "result.json").exists():
        _start_worker_task()
    return {
        "schema": SCHEMA_REQUEST,
        "request_id": request_id,
        "request_path": str(request_path),
        "request_sha256": _sha(request_path),
        "identity": identity,
        "state": "RESULT_READY" if (request_dir / "result.json").exists() else "PENDING",
    }


def _run_status_for(request, root):
    identity = request.get("identity", {})
    status_path = Path(root) / "runs" / identity.get("case_id", "") / identity.get("attempt_id", "") / identity.get("run_id", "") / "status.json"
    if not status_path.is_file():
        return None
    status = _read_json(status_path)
    if any(status.get(k) != identity.get(k) for k in ("case_id", "attempt_id", "run_id")):
        raise SchedulerRunnerError("SCHEDULED_REQUEST_RUN_STATUS_IDENTITY_MISMATCH")
    return {k: status.get(k) for k in ("state", "solver_entered", "solver_invocations", "failure")}


def query_one(request_id, *, root=PRODUCTION_ROOT, task_info_fn=None):
    if not REQUEST_ID_RE.fullmatch(str(request_id)):
        raise SchedulerRunnerError("SCHEDULED_REQUEST_ID_INVALID")
    request_dir = _request_paths(root, request_id)
    request_path = request_dir / "request.json"
    if not request_path.is_file():
        raise SchedulerRunnerError("SCHEDULED_REQUEST_NOT_FOUND")
    request = _read_json(request_path)
    body = dict(request)
    saved = body.pop("request_sha256", None)
    if request.get("schema") != SCHEMA_REQUEST or saved != _sha_bytes(_canonical(body)):
        raise SchedulerRunnerError("SCHEDULED_REQUEST_HASH_INVALID")
    result_path = request_dir / "result.json"
    if result_path.is_file():
        result = _read_json(result_path)
        body = dict(result)
        result_sha = body.pop("result_sha256", None)
        if (result.get("schema") != SCHEMA_RESULT or result.get("request_id") != request_id
                or result.get("request_sha256") != saved or result_sha != _sha_bytes(_canonical(body))):
            raise SchedulerRunnerError("SCHEDULED_RESULT_HASH_OR_IDENTITY_INVALID")
        return {"state": "TERMINAL", "request_id": request_id, "request": request,
                "result": result, "task": (task_info_fn or _task_info)() if task_info_fn else None}
    claim_path = request_dir / "worker_claim.json"
    if claim_path.is_file():
        claim = _read_json(claim_path)
        status = _run_status_for(request, root)
        task = (task_info_fn or _task_info)() if task_info_fn else None
        if task and str(task.get("state", "")).lower() in ("running", "queued"):
            state = "RUNNING"
        else:
            state = "NEEDS_RECONCILIATION"
        if status and status.get("solver_entered") is True:
            state = "NEEDS_POSTENTRY_RECOVERY"
        return {"state": state, "request_id": request_id, "request": request,
                "claim": claim, "run_status": status, "task": task}
    task = (task_info_fn or _task_info)() if task_info_fn else None
    task_lock = Path(root) / TASK_LOCK.name
    if task_lock.is_file():
        lock = _read_json(task_lock)
        state = "RUNNING" if task and str(task.get("state", "")).lower() in ("running", "queued") else "NEEDS_RECONCILIATION"
        return {"state": state, "request_id": request_id, "request": request,
                "worker_lock": lock, "task": task}
    return {"state": "PENDING", "request_id": request_id, "request": request, "task": task}


def _pending_request_dirs(root):
    base = Path(root) / "requests" / "scheduled_run_one_v1"
    if not base.is_dir():
        return []
    found = []
    for request_dir in base.iterdir():
        if not request_dir.is_dir() or not REQUEST_ID_RE.fullmatch(request_dir.name):
            continue
        request_path = request_dir / "request.json"
        if not request_path.is_file() or (request_dir / "result.json").exists() or (request_dir / "worker_claim.json").exists():
            continue
        request = _read_and_verify_request(request_path)
        found.append((request.get("created_utc", ""), request_dir.name, request_dir, request))
    return sorted(found, key=lambda row: (row[0], row[1]))


def task_worker_once(*, root=PRODUCTION_ROOT, run_cli=None, adapter_module=None):
    adapter_module = adapter_module or _adapter_module()
    run_cli = run_cli or adapter_module.run_cli
    pending = _pending_request_dirs(root)
    if not pending:
        return {"result": "NO_PENDING_REQUEST", "solver_invocations": 0}
    _created, request_id, request_dir, request = pending[0]
    request_path = request_dir / "request.json"
    lock_value = {"schema": SCHEMA_CLAIM, "request_id": request_id, "pid": os.getpid(), "created_utc": _now()}
    task_lock = Path(root) / TASK_LOCK.name
    if not _create_exclusive_json(task_lock, lock_value):
        raise SchedulerRunnerError("SCHEDULER_WORKER_LOCK_ALREADY_OWNED")
    claim_path = request_dir / "worker_claim.json"
    claim = dict(lock_value, request_sha256=request["request_sha256"], task_name=TASK_NAME)
    if not _create_exclusive_json(claim_path, claim):
        try:
            current_lock = _read_json(task_lock)
            if current_lock == lock_value:
                task_lock.unlink()
        except Exception:
            pass
        raise SchedulerRunnerError("SCHEDULED_REQUEST_ALREADY_CLAIMED")
    result_path = request_dir / "result.json"
    result_body = {
        "schema": SCHEMA_RESULT,
        "request_id": request_id,
        "request_sha256": request["request_sha256"],
        "claim_sha256": _sha_bytes(_canonical(claim)),
        "worker_pid": os.getpid(),
        "worker_started_utc": _now(),
    }
    try:
        _read_and_verify_request(request_path)
        if _sha(Path(adapter_module.__file__).resolve()) != request["adapter_sha256"]:
            raise SchedulerRunnerError("SCHEDULED_REQUEST_ADAPTER_CHANGED")
        result = run_cli(request["manifest_path"])
        result_body.update(exit_code=0, result=result, completed_utc=_now())
    except BaseException as exc:
        status = _run_status_for(request, root)
        result_body.update(
            exit_code=2, error_type=type(exc).__name__, error=str(exc)[:1000],
            run_status=status, completed_utc=_now(),
            solver_entered=(status or {}).get("solver_entered") is True,
        )
    result_body["result_sha256"] = _sha_bytes(_canonical(result_body))
    _atomic_json(result_path, result_body)
    try:
        if task_lock.exists() and _read_json(task_lock) == lock_value:
            task_lock.unlink()
    except Exception:
        # A stale lock is fail-closed and must be reconciled, never blindly removed.
        pass
    return {"result": "RECORDED", "request_id": request_id,
            "exit_code": result_body["exit_code"], "solver_entered": result_body.get("solver_entered")}


def run_one_via_task_scheduler(manifest_path, *, run_cli=None, root=PRODUCTION_ROOT,
                               poll_interval_s=2.0, timeout_s=72 * 60 * 60,
                               task_info_fn=None, start_fn=None):
    verify_worker_task()
    request = submit_one(manifest_path, root=root, start_task=False)
    request_id = request["request_id"]
    start_fn = start_fn or _start_worker_task
    started_once = False
    saw_running = False
    deadline = time.monotonic() + float(timeout_s)
    while True:
        state = query_one(request_id, root=root, task_info_fn=task_info_fn)
        if state["state"] == "TERMINAL":
            result = state["result"]
            if result.get("exit_code") != 0:
                raise SchedulerRunnerError("SCHEDULED_WORKER_FAILED:" + str(result.get("error", result.get("error_type", "UNKNOWN"))))
            if not isinstance(result.get("result"), dict):
                raise SchedulerRunnerError("SCHEDULED_WORKER_RESULT_MISSING")
            return result["result"]
        if state["state"] in ("NEEDS_RECONCILIATION", "NEEDS_POSTENTRY_RECOVERY"):
            raise SchedulerRunnerError("SCHEDULED_WORKER_REQUIRES_RECONCILIATION:" + state["state"])
        task_state = str((state.get("task") or {}).get("state", "")).lower()
        if task_state in ("running", "queued"):
            saw_running = True
        elif state["state"] == "PENDING" and task_state in ("ready", ""):
            if not started_once or saw_running:
                start_fn()
                started_once = True
                saw_running = False
        if time.monotonic() >= deadline:
            raise SchedulerRunnerError("SCHEDULED_WORKER_WAIT_TIMEOUT_NO_CANCEL")
        time.sleep(max(0.05, float(poll_interval_s)))


def worker_task_xml(*, principal=None, script_path=None, python_path=TASK_PYTHON):
    principal = principal or OWNER_ACCOUNT
    script_path = str(script_path or _task_script_path())
    esc = lambda value: (str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    return (
        '<?xml version="1.0" encoding="UTF-16"?>'
        '<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">'
        '<RegistrationInfo><Author>APCD GPU Runner V1</Author><Description>Single request worker; no automatic solver replay.</Description></RegistrationInfo>'
        '<Triggers/>'
        '<Principals><Principal id="Author"><UserId>' + esc(principal) + '</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>'
        '<Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>'
        '<StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><AllowHardTerminate>true</AllowHardTerminate>'
        '<StartWhenAvailable>false</StartWhenAvailable><Enabled>true</Enabled><Hidden>true</Hidden>'
        '<ExecutionTimeLimit>PT72H</ExecutionTimeLimit><Priority>7</Priority></Settings>'
        '<Actions Context="Author"><Exec><Command>' + esc(python_path) + '</Command><Arguments>"' + esc(script_path) + '" worker-once</Arguments>'
        '<WorkingDirectory>' + esc(str(Path(script_path).parent)) + '</WorkingDirectory></Exec></Actions></Task>'
    )


def install_worker_task(*, task_name=TASK_NAME, python_path=TASK_PYTHON,
                        script_path=None):
    if os.name != "nt":
        raise SchedulerRunnerError("SCHEDULER_TASK_INSTALL_REQUIRES_WINDOWS")
    if task_name != TASK_NAME:
        raise SchedulerRunnerError("SCHEDULER_TASK_NAME_OVERRIDE_FORBIDDEN")
    actual = subprocess.run(["whoami.exe"], text=True, capture_output=True,
                            encoding="utf-8", errors="replace", timeout=10, check=False)
    if actual.returncode != 0 or actual.stdout.strip().lower() != EXPECTED_WHOAMI:
        raise SchedulerRunnerError("SCHEDULER_TASK_INSTALL_IDENTITY_MISMATCH")
    script_path = Path(script_path or _task_script_path()).resolve(strict=True)
    xml_text = worker_task_xml(script_path=str(script_path), python_path=python_path)
    existing = subprocess.run(["schtasks.exe", "/Query", "/TN", task_name, "/XML"],
                              text=True, capture_output=True, encoding="utf-8", errors="replace",
                              timeout=30, check=False)
    if existing.returncode == 0:
        verify_worker_task(xml_text=existing.stdout, expected_script=script_path,
                           expected_principal=_expected_principal())
        return {"result": "ALREADY_INSTALLED", "task_name": task_name}
    import tempfile
    with tempfile.NamedTemporaryFile("w", encoding="utf-16", suffix=".xml", delete=False) as stream:
        stream.write(xml_text)
        xml_path = stream.name
    try:
        proc = subprocess.run(["schtasks.exe", "/Create", "/TN", task_name, "/XML", xml_path],
                              text=True, capture_output=True, encoding="utf-8", errors="replace",
                              timeout=30, check=False)
        if proc.returncode != 0:
            raise SchedulerRunnerError("SCHEDULER_TASK_CREATE_FAILED:" + proc.stderr.strip()[:500])
    finally:
        try:
            Path(xml_path).unlink()
        except OSError:
            pass
    verify_worker_task(expected_script=script_path, expected_principal=_expected_principal())
    return {"result": "INSTALLED", "task_name": task_name}




def _controller_request_dir(root, request_id):
    if not REQUEST_ID_RE.fullmatch(str(request_id)):
        raise SchedulerRunnerError("SCHEDULED_CONTROLLER_REQUEST_ID_INVALID")
    return Path(root) / "requests" / "scheduled_queue_controller_v1" / request_id


def _path_within(path, root, *, strict=True):
    try:
        resolved = Path(path).resolve(strict=strict)
        resolved.relative_to(Path(root).resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise SchedulerRunnerError("CONTROLLER_PATH_OUTSIDE_APPROVED_ROOT") from exc
    return resolved


def _is_sha256(value):
    return isinstance(value, str) and SHA256_RE.fullmatch(value.lower()) is not None


def _controller_manifest(manifest_path, *, coupling_root=COUPLING_WORKTREE, require_inside_root=True):
    try:
        manifest_path = Path(manifest_path).resolve(strict=True)
        root = Path(coupling_root).resolve(strict=True)
        if require_inside_root:
            manifest_path.relative_to(root)
        raw = manifest_path.read_bytes()
        value = json.loads(raw.decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise SchedulerRunnerError("CONTROLLER_MANIFEST_UNREADABLE") from exc
    if not isinstance(value, dict) or value.get("schema") != SCHEMA_CONTROLLER_MANIFEST:
        raise SchedulerRunnerError("CONTROLLER_MANIFEST_SCHEMA_INVALID")
    required = (
        "controller_run_id", "queue_id", "controller_script_path", "controller_script_sha256",
        "queue_manifest_path", "queue_manifest_sha256", "case_ids", "max_cases",
        "max_concurrent_cases", "per_case_max_solver_entries", "post_entry_automatic_replays",
        "startup_reconcile_before_dispatch", "truth_before_next_case", "controller_protocol",
        "status_path",
    )
    if any(key not in value for key in required):
        raise SchedulerRunnerError("CONTROLLER_MANIFEST_FIELD_MISSING")
    if not CONTROLLER_RUN_ID_RE.fullmatch(str(value["controller_run_id"])):
        raise SchedulerRunnerError("CONTROLLER_RUN_ID_INVALID")
    if not isinstance(value["queue_id"], str) or not CONTROLLER_RUN_ID_RE.fullmatch(value["queue_id"]):
        raise SchedulerRunnerError("CONTROLLER_QUEUE_ID_INVALID")
    expected_script = (root / "scripts" / "coupling_ml" / "k6_v2_pipeline" / "serial_queue.py").resolve(strict=True)
    script_path = _path_within(value["controller_script_path"], root)
    queue_path = _path_within(value["queue_manifest_path"], root)
    status_path = _path_within(value["status_path"], root, strict=False)
    if script_path != expected_script or not script_path.is_file() or not queue_path.is_file():
        raise SchedulerRunnerError("CONTROLLER_ENTRYPOINT_OR_QUEUE_NOT_APPROVED")
    if not _is_sha256(value["controller_script_sha256"]) or _sha(script_path) != value["controller_script_sha256"].lower():
        raise SchedulerRunnerError("CONTROLLER_ENTRYPOINT_HASH_MISMATCH")
    if not _is_sha256(value["queue_manifest_sha256"]) or _sha(queue_path) != value["queue_manifest_sha256"].lower():
        raise SchedulerRunnerError("CONTROLLER_QUEUE_MANIFEST_HASH_MISMATCH")
    try:
        queue_manifest = json.loads(queue_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SchedulerRunnerError("CONTROLLER_QUEUE_MANIFEST_INVALID") from exc
    allowed_ids = queue_manifest.get("ordered_case_ids") if isinstance(queue_manifest, dict) else None
    case_ids = value["case_ids"]
    if (not isinstance(allowed_ids, list) or not allowed_ids
            or not isinstance(case_ids, list) or not case_ids
            or any(not isinstance(cid, str) or not CONTROLLER_RUN_ID_RE.fullmatch(cid) for cid in case_ids)
            or len(set(case_ids)) != len(case_ids)):
        raise SchedulerRunnerError("CONTROLLER_CASE_ALLOWLIST_INVALID")
    allowed_index = {cid: i for i, cid in enumerate(allowed_ids) if isinstance(cid, str)}
    positions = [allowed_index.get(cid) for cid in case_ids]
    if any(index is None for index in positions) or positions != sorted(positions):
        raise SchedulerRunnerError("CONTROLLER_CASES_OUTSIDE_QUEUE_MANIFEST")
    if isinstance(value["max_cases"], bool) or value["max_cases"] != len(case_ids):
        raise SchedulerRunnerError("CONTROLLER_CASE_BOUND_INVALID")
    if isinstance(value["max_concurrent_cases"], bool) or value["max_concurrent_cases"] != 1:
        raise SchedulerRunnerError("CONTROLLER_CONCURRENCY_MUST_BE_ONE")
    if isinstance(value["per_case_max_solver_entries"], bool) or value["per_case_max_solver_entries"] != 1:
        raise SchedulerRunnerError("CONTROLLER_PER_CASE_ENTRY_BUDGET_INVALID")
    if isinstance(value["post_entry_automatic_replays"], bool) or value["post_entry_automatic_replays"] != 0:
        raise SchedulerRunnerError("CONTROLLER_AUTOMATIC_REPLAY_FORBIDDEN")
    if value["startup_reconcile_before_dispatch"] is not True or value["truth_before_next_case"] is not True:
        raise SchedulerRunnerError("CONTROLLER_RECOVERY_OR_TRUTH_BARRIER_REQUIRED")
    if value["controller_protocol"] != CONTROLLER_PROTOCOL:
        raise SchedulerRunnerError("CONTROLLER_PROTOCOL_VERSION_UNSUPPORTED")
    source = script_path.read_text(encoding="utf-8-sig")
    required_tokens = (
        'CONTROLLER_PROTOCOL = "' + CONTROLLER_PROTOCOL + '"',
        "--runner-controller-manifest", "--runner-controller-manifest-sha256",
        "--runner-controller-request-id", "--runner-resume-receipt",
        "--runner-resume-receipt-sha256",
    )
    if any(token not in source for token in required_tokens):
        raise SchedulerRunnerError("CONTROLLER_ENTRYPOINT_PROTOCOL_UNSUPPORTED")
    return {"manifest": value, "manifest_path": manifest_path, "raw": raw,
            "manifest_sha256": _sha_bytes(raw), "controller_script_path": script_path,
            "queue_manifest_path": queue_path, "status_path": status_path,
            "queue_manifest": queue_manifest}


def _controller_body_with_verified_hash(value, schema, error):
    body = dict(value)
    saved = body.pop("binding_sha256", None)
    if value.get("schema") != schema or saved != _sha_bytes(_canonical(body)):
        raise SchedulerRunnerError(error)
    return body


def _controller_request_files(root, request_id):
    if not REQUEST_ID_RE.fullmatch(str(request_id)):
        raise SchedulerRunnerError("SCHEDULED_CONTROLLER_REQUEST_ID_INVALID")
    directory = Path(root) / "requests" / "scheduled_queue_controller_v1" / request_id
    return directory, directory / "controller_manifest.json", directory / "binding.json", directory / "start_claim.json"


def _read_controller_request(request_id, *, root=PRODUCTION_ROOT, coupling_root=COUPLING_WORKTREE):
    directory, manifest_path, binding_path, start_claim = _controller_request_files(root, request_id)
    if not manifest_path.is_file() or not binding_path.is_file():
        raise SchedulerRunnerError("SCHEDULED_CONTROLLER_REQUEST_NOT_FOUND")
    binding = _controller_body_with_verified_hash(_read_json(binding_path), SCHEMA_CONTROLLER_BINDING,
                                                   "SCHEDULED_CONTROLLER_REQUEST_BINDING_INVALID")
    raw = manifest_path.read_bytes()
    if (binding.get("request_id") != request_id
            or binding.get("controller_manifest_sha256") != _sha_bytes(raw)):
        raise SchedulerRunnerError("SCHEDULED_CONTROLLER_REQUEST_HASH_INVALID")
    info = _controller_manifest(manifest_path, coupling_root=coupling_root, require_inside_root=False)
    return info, binding, directory, start_claim


def controller_task_xml(*, script_path, manifest_path, manifest_sha256, request_id,
                        resume_receipt_path=None, resume_receipt_sha256=None,
                        principal=None, python_path=TASK_PYTHON):
    principal = principal or OWNER_ACCOUNT
    script_path = str(Path(script_path).resolve(strict=True))
    manifest_path = str(Path(manifest_path).resolve(strict=True))
    esc = lambda value: (str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    args = ('"' + esc(script_path) + '" --runner-controller-manifest "' + esc(manifest_path)
            + '" --runner-controller-manifest-sha256 ' + str(manifest_sha256)
            + ' --runner-controller-request-id ' + str(request_id))
    if resume_receipt_path is not None:
        receipt_path = str(Path(resume_receipt_path).resolve(strict=True))
        args += (' --runner-resume-receipt "' + esc(receipt_path)
                 + '" --runner-resume-receipt-sha256 ' + str(resume_receipt_sha256))
    return (
        '<?xml version="1.0" encoding="UTF-16"?>'
        '<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">'
        '<RegistrationInfo><Author>APCD GPU Runner V1</Author><Description>Coupling-owned bounded serial queue controller; explicit reconciliation on resume.</Description></RegistrationInfo>'
        '<Triggers/>'
        '<Principals><Principal id="Author"><UserId>' + esc(principal) + '</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>'
        '<Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>'
        '<StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><AllowHardTerminate>true</AllowHardTerminate>'
        '<StartWhenAvailable>false</StartWhenAvailable><Enabled>true</Enabled><Hidden>true</Hidden>'
        '<ExecutionTimeLimit>' + TASK_EXECUTION_LIMIT + '</ExecutionTimeLimit><Priority>7</Priority></Settings>'
        '<Actions Context="Author"><Exec><Command>' + esc(python_path) + '</Command><Arguments>' + args + '</Arguments>'
        '<WorkingDirectory>' + esc(str(Path(script_path).parent)) + '</WorkingDirectory></Exec></Actions></Task>'
    )


def _task_controller_binding_path(root):
    return Path(root) / "scheduler_controller_v1" / "task_binding.json"


def _read_controller_task_binding(root):
    path = _task_controller_binding_path(root)
    if not path.is_file():
        return None
    return _controller_body_with_verified_hash(_read_json(path), SCHEMA_CONTROLLER_BINDING,
                                                 "CONTROLLER_TASK_BINDING_INVALID")


def _write_controller_task_binding(root, body):
    value = dict(body, schema=SCHEMA_CONTROLLER_BINDING)
    value["binding_sha256"] = _sha_bytes(_canonical(value))
    _atomic_json(_task_controller_binding_path(root), value)
    return value


def _validate_controller_task_xml(xml_text, info, request_id, request_path,
                                  expected_principal, resume_path=None, resume_sha=None):
    return validate_task_definition_xml(
        xml_text, expected_script=info["controller_script_path"],
        expected_principal=expected_principal, task_name=CONTROLLER_TASK_NAME,
        expected_argument="--runner-controller-manifest", expected_manifest=request_path,
        expected_manifest_sha256=info["manifest_sha256"], expected_request_id=request_id,
        expected_resume_receipt=resume_path, expected_resume_receipt_sha256=resume_sha,
        require_no_triggers=True)


def _write_controller_task_xml(xml_text, *, force=False):
    if os.name != "nt":
        raise SchedulerRunnerError("SCHEDULER_TASK_INSTALL_REQUIRES_WINDOWS")
    import tempfile
    with tempfile.NamedTemporaryFile("w", encoding="utf-16", suffix=".xml", delete=False) as stream:
        stream.write(xml_text)
        xml_path = stream.name
    try:
        command = ["schtasks.exe", "/Create", "/TN", CONTROLLER_TASK_NAME, "/XML", xml_path]
        if force:
            command.append("/F")
        proc = subprocess.run(command, text=True, capture_output=True, encoding="utf-8",
                              errors="replace", timeout=30, check=False)
        if proc.returncode != 0:
            raise SchedulerRunnerError("SCHEDULER_CONTROLLER_TASK_CREATE_FAILED:" + proc.stderr.strip()[:500])
    finally:
        try:
            Path(xml_path).unlink()
        except OSError:
            pass


def _write_exclusive_bytes(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        return True
    except FileExistsError:
        return False


def prepare_controller_task(manifest_path, *, root=PRODUCTION_ROOT, coupling_root=COUPLING_WORKTREE,
                            install_task=True, xml_query_fn=None, task_info_fn=None,
                            create_task_fn=None, expected_principal=None):
    info = _controller_manifest(manifest_path, coupling_root=coupling_root)
    request_id = info["manifest_sha256"][:32]
    directory, request_path, binding_path, _claim = _controller_request_files(root, request_id)
    directory.mkdir(parents=True, exist_ok=True)
    if request_path.exists():
        if _sha(request_path) != info["manifest_sha256"]:
            raise SchedulerRunnerError("SCHEDULED_CONTROLLER_REQUEST_ID_COLLISION")
    elif not _write_exclusive_bytes(request_path, info["raw"]):
        if _sha(request_path) != info["manifest_sha256"]:
            raise SchedulerRunnerError("SCHEDULED_CONTROLLER_REQUEST_ID_COLLISION")
    request_binding = {
        "schema": SCHEMA_CONTROLLER_BINDING, "request_id": request_id,
        "controller_manifest_sha256": info["manifest_sha256"],
        "source_manifest_path": str(info["manifest_path"]),
        "controller_script_path": str(info["controller_script_path"]),
        "controller_script_sha256": _sha(info["controller_script_path"]),
        "queue_manifest_path": str(info["queue_manifest_path"]),
        "queue_manifest_sha256": _sha(info["queue_manifest_path"]),
        "queue_id": info["manifest"]["queue_id"],
        "controller_run_id": info["manifest"]["controller_run_id"],
        "status_path": str(info["status_path"]), "created_utc": _now(),
    }
    request_binding["binding_sha256"] = _sha_bytes(_canonical(request_binding))
    if binding_path.exists():
        old = _controller_body_with_verified_hash(_read_json(binding_path), SCHEMA_CONTROLLER_BINDING,
                                                   "SCHEDULED_CONTROLLER_REQUEST_BINDING_INVALID")
        for key in ("request_id", "controller_manifest_sha256", "controller_script_sha256",
                    "queue_manifest_sha256", "queue_id"):
            if old.get(key) != request_binding.get(key):
                raise SchedulerRunnerError("SCHEDULED_CONTROLLER_REQUEST_BINDING_CONFLICT")
    else:
        _create_exclusive_json(binding_path, request_binding)
    task_result = None
    if install_task:
        task_result = install_controller_task(request_id, root=root, coupling_root=coupling_root,
            xml_query_fn=xml_query_fn, task_info_fn=task_info_fn,
            create_task_fn=create_task_fn, expected_principal=expected_principal)
    return {"request_id": request_id, "request_manifest_path": str(request_path),
            "request_manifest_sha256": info["manifest_sha256"],
            "controller_script_sha256": _sha(info["controller_script_path"]),
            "queue_manifest_sha256": _sha(info["queue_manifest_path"]),
            "queue_id": info["manifest"]["queue_id"], "case_ids": list(info["manifest"]["case_ids"]),
            "max_cases": info["manifest"]["max_cases"], "max_concurrent_cases": 1,
            "automatic_replays": 0, "task": task_result}


def install_controller_task(request_id, *, root=PRODUCTION_ROOT, coupling_root=COUPLING_WORKTREE,
                            xml_query_fn=None, task_info_fn=None, create_task_fn=None,
                            expected_principal=None):
    info, request_binding, _directory, _claim = _read_controller_request(
        request_id, root=root, coupling_root=coupling_root)
    expected_principal = _expected_principal() if expected_principal is None else expected_principal
    current = _read_controller_task_binding(root)
    if current is not None and current.get("request_id") != request_id:
        raise SchedulerRunnerError("CONTROLLER_TASK_ALREADY_BOUND_TO_ANOTHER_REQUEST")
    request_path = _controller_request_files(root, request_id)[1]
    try:
        existing_xml = (xml_query_fn or _query_task_xml)(CONTROLLER_TASK_NAME)
        exists = True
    except SchedulerRunnerError as exc:
        if "CONTROLLER_TASK_NOT_INSTALLED" not in str(exc):
            raise
        existing_xml, exists = None, False
    if exists:
        if current is None or current.get("request_id") != request_id:
            raise SchedulerRunnerError("CONTROLLER_TASK_EXISTS_WITHOUT_BINDING")
        resume_path = current.get("resume_receipt_path")
        resume_sha = current.get("resume_receipt_sha256")
        _validate_controller_task_xml(existing_xml, info, request_id, request_path,
                                       expected_principal, resume_path, resume_sha)
        task = (task_info_fn or _task_info)(CONTROLLER_TASK_NAME)
        state = str(task.get("state", "")).lower()
        return {"result": "ALREADY_RUNNING" if state in ("running", "queued") else "ALREADY_INSTALLED",
                "task_name": CONTROLLER_TASK_NAME, "request_id": request_id}
    xml_text = controller_task_xml(script_path=info["controller_script_path"], manifest_path=request_path,
        manifest_sha256=info["manifest_sha256"], request_id=request_id,
        principal=expected_principal)
    _validate_controller_task_xml(xml_text, info, request_id, request_path, expected_principal)
    if create_task_fn is not None:
        create_task_fn(xml_text, force=False)
    else:
        if os.name != "nt":
            raise SchedulerRunnerError("SCHEDULER_TASK_INSTALL_REQUIRES_WINDOWS")
        who = subprocess.run(["whoami.exe"], text=True, capture_output=True, encoding="utf-8",
                             errors="replace", timeout=10, check=False)
        if who.returncode != 0 or who.stdout.strip().lower() != EXPECTED_WHOAMI:
            raise SchedulerRunnerError("SCHEDULER_TASK_INSTALL_IDENTITY_MISMATCH")
        _write_controller_task_xml(xml_text, force=False)
    checked_xml = (xml_query_fn or _query_task_xml)(CONTROLLER_TASK_NAME)
    _validate_controller_task_xml(checked_xml, info, request_id, request_path, expected_principal)
    _write_controller_task_binding(root, {
        "request_id": request_id, "controller_manifest_sha256": info["manifest_sha256"],
        "controller_script_sha256": _sha(info["controller_script_path"]),
        "queue_manifest_sha256": _sha(info["queue_manifest_path"]), "queue_id": info["manifest"]["queue_id"],
        "resume_generation": 0, "resume_receipt_path": None, "resume_receipt_sha256": None,
        "updated_utc": _now(),
    })
    return {"result": "INSTALLED", "task_name": CONTROLLER_TASK_NAME, "request_id": request_id}


def _start_task(task_name):
    _validate_scheduler_task_name(task_name)
    proc = subprocess.run(
        ["schtasks.exe", "/Run", "/TN", task_name],
        text=True, capture_output=True, encoding="utf-8", errors="replace", timeout=30, check=False,
    )
    if proc.returncode != 0:
        label = "SCHEDULER_WORKER_START_FAILED" if task_name == TASK_NAME else "SCHEDULER_CONTROLLER_START_FAILED"
        raise SchedulerRunnerError(label + ":" + proc.stderr.strip()[:400])


def _start_worker_task():
    verify_worker_task()
    _start_task(TASK_NAME)


def start_controller_task(request_id, *, root=PRODUCTION_ROOT, coupling_root=COUPLING_WORKTREE,
                          xml_query_fn=None, task_info_fn=None, start_fn=None,
                          expected_principal=None):
    info, _request_binding, _directory, claim_path = _read_controller_request(
        request_id, root=root, coupling_root=coupling_root)
    current = _read_controller_task_binding(root)
    if current is None or current.get("request_id") != request_id:
        raise SchedulerRunnerError("CONTROLLER_TASK_NOT_BOUND_TO_REQUEST")
    _validate_controller_task_xml((xml_query_fn or _query_task_xml)(CONTROLLER_TASK_NAME),
        info, request_id, _controller_request_files(root, request_id)[1],
        _expected_principal() if expected_principal is None else expected_principal,
        current.get("resume_receipt_path"), current.get("resume_receipt_sha256"))
    task = (task_info_fn or _task_info)(CONTROLLER_TASK_NAME)
    if str(task.get("state", "")).lower() in ("running", "queued"):
        return {"result": "ALREADY_RUNNING", "request_id": request_id, "task": task}
    if claim_path.exists():
        return {"result": "START_ALREADY_REQUESTED_RECONCILE_BEFORE_RESUME",
                "request_id": request_id, "start_claim": _read_json(claim_path), "task": task}
    claim = {"schema": "APCD_GPU_RUNNER_V1_CONTROLLER_START_CLAIM_V1",
        "request_id": request_id, "controller_manifest_sha256": info["manifest_sha256"],
        "queue_id": info["manifest"]["queue_id"], "created_utc": _now(),
        "task_name": CONTROLLER_TASK_NAME}
    if not _create_exclusive_json(claim_path, claim):
        return {"result": "START_ALREADY_REQUESTED_RECONCILE_BEFORE_RESUME",
                "request_id": request_id, "start_claim": _read_json(claim_path), "task": task}
    (start_fn or _start_task)(CONTROLLER_TASK_NAME)
    return {"result": "START_REQUESTED", "request_id": request_id,
            "start_claim_path": str(claim_path)}


def _verify_resume_request_ids(receipt, *, root, query_one_fn, allowed_case_ids):
    request_ids = receipt.get("runner_request_ids")
    if not isinstance(request_ids, list) or len(set(request_ids)) != len(request_ids):
        raise SchedulerRunnerError("CONTROLLER_RESUME_RUNNER_REQUEST_LIST_INVALID")
    for request_id in request_ids:
        if not REQUEST_ID_RE.fullmatch(str(request_id)):
            raise SchedulerRunnerError("CONTROLLER_RESUME_RUNNER_REQUEST_ID_INVALID")
        state = query_one_fn(request_id, root=root, task_info_fn=lambda: {"state": "Ready"})
        if state.get("state") != "TERMINAL" or state.get("result", {}).get("exit_code") != 0:
            raise SchedulerRunnerError("CONTROLLER_RESUME_RUNNER_REQUEST_UNRESOLVED:" + request_id)
        request = state.get("request", {})
        identity = request.get("identity", {})
        if identity.get("case_id") not in allowed_case_ids:
            raise SchedulerRunnerError("CONTROLLER_RESUME_RUNNER_CASE_OUTSIDE_BOUND:" + request_id)
        status = _run_status_for(request, root)
        if status is None or status.get("state") != "DONE":
            raise SchedulerRunnerError("CONTROLLER_RESUME_RUNNER_TRUTH_NOT_DONE:" + request_id)
        if status.get("solver_entered") is True and (
                status.get("solver_invocations") != 1 or status.get("replay_count", 0) != 0):
            raise SchedulerRunnerError("CONTROLLER_RESUME_RUNNER_ENTRY_COUNT_INVALID:" + request_id)
        run_dir = Path(root) / "runs" / identity["case_id"] / identity["attempt_id"] / identity["run_id"]
        for name in ("run.fsp", "truth.h5", "validation.json", "hashes.json"):
            if not (run_dir / name).is_file() or (run_dir / name).stat().st_size <= 0:
                raise SchedulerRunnerError("CONTROLLER_RESUME_TRUTH_ARTIFACT_MISSING:" + request_id)
        validation = _read_json(run_dir / "validation.json")
        if not all(validation.get(key) is True for key in
                   ("fresh_load_verified", "monitors_valid", "state_valid", "scientific_valid")):
            raise SchedulerRunnerError("CONTROLLER_RESUME_TRUTH_INVALID:" + request_id)
    return request_ids


def resume_controller_task(request_id, receipt_path, *, root=PRODUCTION_ROOT,
                           coupling_root=COUPLING_WORKTREE, xml_query_fn=None,
                           task_info_fn=None, create_task_fn=None, start_fn=None,
                           query_one_fn=None, expected_principal=None):
    info, _request_binding, directory, start_claim = _read_controller_request(
        request_id, root=root, coupling_root=coupling_root)
    current = _read_controller_task_binding(root)
    if current is None or current.get("request_id") != request_id or not start_claim.is_file():
        raise SchedulerRunnerError("CONTROLLER_RESUME_REQUEST_NOT_STARTED")
    task = (task_info_fn or _task_info)(CONTROLLER_TASK_NAME)
    if str(task.get("state", "")).lower() in ("running", "queued"):
        raise SchedulerRunnerError("CONTROLLER_RESUME_TASK_STILL_ACTIVE")
    receipt_path = _path_within(receipt_path, coupling_root)
    receipt_raw = receipt_path.read_bytes()
    receipt_sha = _sha_bytes(receipt_raw)
    if current.get("resume_receipt_sha256") == receipt_sha:
        return {"result": "RESUME_ALREADY_REQUESTED", "request_id": request_id,
                "resume_generation": current.get("resume_generation")}
    try:
        receipt = json.loads(receipt_raw.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SchedulerRunnerError("CONTROLLER_RESUME_RECEIPT_INVALID") from exc
    status_path = info["status_path"]
    if not status_path.is_file():
        raise SchedulerRunnerError("CONTROLLER_RESUME_STATUS_MISSING")
    status_raw = status_path.read_bytes()
    status = json.loads(status_raw.decode("utf-8-sig"))
    generation = int(current.get("resume_generation", 0)) + 1
    expected = {
        "schema": SCHEMA_CONTROLLER_RESUME,
        "request_id": request_id,
        "controller_manifest_sha256": info["manifest_sha256"],
        "queue_id": info["manifest"]["queue_id"],
        "previous_status_sha256": _sha_bytes(status_raw),
        "resume_generation": generation,
        "safe_to_resume": True,
        "startup_reconciled": True,
        "current_case_id": None,
        "unresolved_runner_request_ids": [],
        "post_entry_automatic_replays": 0,
    }
    if (status.get("schema") != SCHEMA_CONTROLLER_STATUS or status.get("state") != "STOPPED_RECONCILED"
            or status.get("request_id") != request_id
            or status.get("controller_manifest_sha256") != info["manifest_sha256"]
            or status.get("queue_id") != info["manifest"]["queue_id"]
            or status.get("current_case_id") is not None
            or status.get("unresolved_runner_request_ids") != []
            or status.get("post_entry_automatic_replays") != 0
            or any(receipt.get(key) != value for key, value in expected.items())):
        raise SchedulerRunnerError("CONTROLLER_RESUME_RECEIPT_NOT_SAFE")
    request_ids = receipt.get("runner_request_ids")
    if status.get("runner_request_ids") != request_ids:
        raise SchedulerRunnerError("CONTROLLER_RESUME_RUNNER_REQUEST_INVENTORY_MISMATCH")
    _verify_resume_request_ids(receipt, root=root, query_one_fn=query_one_fn or query_one,
                               allowed_case_ids=info["manifest"]["case_ids"])
    resume_dir = directory / "resume"
    resume_dir.mkdir(parents=True, exist_ok=True)
    saved_receipt = resume_dir / (str(generation) + "_" + receipt_sha + ".json")
    if not _write_exclusive_bytes(saved_receipt, receipt_raw) and _sha(saved_receipt) != receipt_sha:
        raise SchedulerRunnerError("CONTROLLER_RESUME_RECEIPT_COLLISION")
    manifest_path = _controller_request_files(root, request_id)[1]
    expected_principal = _expected_principal() if expected_principal is None else expected_principal
    xml_text = controller_task_xml(script_path=info["controller_script_path"],
        manifest_path=manifest_path, manifest_sha256=info["manifest_sha256"], request_id=request_id,
        resume_receipt_path=saved_receipt, resume_receipt_sha256=receipt_sha,
        principal=expected_principal)
    _validate_controller_task_xml(xml_text, info, request_id, manifest_path, expected_principal,
                                  saved_receipt, receipt_sha)
    if create_task_fn is not None:
        create_task_fn(xml_text, force=True)
    else:
        _write_controller_task_xml(xml_text, force=True)
    checked_xml = (xml_query_fn or _query_task_xml)(CONTROLLER_TASK_NAME)
    _validate_controller_task_xml(checked_xml, info, request_id, manifest_path, expected_principal,
                                  saved_receipt, receipt_sha)
    _write_controller_task_binding(root, {
        "request_id": request_id, "controller_manifest_sha256": info["manifest_sha256"],
        "controller_script_sha256": _sha(info["controller_script_path"]),
        "queue_manifest_sha256": _sha(info["queue_manifest_path"]),
        "queue_id": info["manifest"]["queue_id"], "resume_generation": generation,
        "resume_receipt_path": str(saved_receipt), "resume_receipt_sha256": receipt_sha,
        "updated_utc": _now(),
    })
    resume_claim = resume_dir / (str(generation) + "_start_claim.json")
    if not _create_exclusive_json(resume_claim, {
            "schema": "APCD_GPU_RUNNER_V1_CONTROLLER_RESUME_START_CLAIM_V1",
            "request_id": request_id, "resume_generation": generation,
            "resume_receipt_sha256": receipt_sha, "runner_request_ids": request_ids,
            "created_utc": _now()}):
        raise SchedulerRunnerError("CONTROLLER_RESUME_ALREADY_CLAIMED")
    (start_fn or _start_task)(CONTROLLER_TASK_NAME)
    return {"result": "RESUME_START_REQUESTED", "request_id": request_id,
            "resume_generation": generation, "resume_receipt_sha256": receipt_sha}


def query_controller_task(request_id, *, root=PRODUCTION_ROOT, coupling_root=COUPLING_WORKTREE,
                          xml_query_fn=None, task_info_fn=None, expected_principal=None):
    info, request_binding, _directory, claim_path = _read_controller_request(
        request_id, root=root, coupling_root=coupling_root)
    current = _read_controller_task_binding(root)
    if current is None or current.get("request_id") != request_id:
        return {"state": "NOT_CURRENT_TASK_BINDING", "request_id": request_id,
                "request_binding": request_binding}
    _validate_controller_task_xml((xml_query_fn or _query_task_xml)(CONTROLLER_TASK_NAME),
        info, request_id, _controller_request_files(root, request_id)[1],
        _expected_principal() if expected_principal is None else expected_principal,
        current.get("resume_receipt_path"), current.get("resume_receipt_sha256"))
    task = (task_info_fn or _task_info)(CONTROLLER_TASK_NAME)
    status = None
    if info["status_path"].is_file():
        status = _read_json(info["status_path"])
        if (status.get("schema") != SCHEMA_CONTROLLER_STATUS
                or status.get("request_id") != request_id
                or status.get("controller_manifest_sha256") != info["manifest_sha256"]
                or status.get("queue_id") != info["manifest"]["queue_id"]):
            raise SchedulerRunnerError("CONTROLLER_STATUS_IDENTITY_MISMATCH")
    if str(task.get("state", "")).lower() in ("running", "queued"):
        state = "RUNNING"
    elif not claim_path.is_file():
        state = "PREPARED"
    elif status and status.get("state") == "DONE":
        state = "COMPLETED"
    elif status and status.get("state") == "STOPPED_RECONCILED":
        state = "STOPPED_RECONCILED"
    else:
        state = "CONTROLLER_EXITED_NEEDS_RECONCILIATION"
    return {"state": state, "request_id": request_id, "task": task, "status": status,
            "controller_manifest_sha256": info["manifest_sha256"], "queue_id": info["manifest"]["queue_id"]}


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="APCD Runner V1 Task Scheduler request worker")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("install-task")
    sub.add_parser("worker-once")
    submit = sub.add_parser("submit-one")
    submit.add_argument("case_manifest")
    query = sub.add_parser("query-one")
    query.add_argument("request_id")
    install_controller = sub.add_parser("install-controller-task")
    install_controller.add_argument("controller_manifest")
    start_controller = sub.add_parser("start-controller-task")
    start_controller.add_argument("request_id")
    resume_controller = sub.add_parser("resume-controller-task")
    resume_controller.add_argument("request_id")
    resume_controller.add_argument("reconciliation_receipt")
    query_controller = sub.add_parser("query-controller-task")
    query_controller.add_argument("request_id")
    args = parser.parse_args(argv)
    try:
        if args.command == "install-task":
            result = install_worker_task()
        elif args.command == "worker-once":
            result = task_worker_once()
        elif args.command == "submit-one":
            result = submit_one(args.case_manifest)
        elif args.command == "install-controller-task":
            result = prepare_controller_task(args.controller_manifest)
        elif args.command == "start-controller-task":
            result = start_controller_task(args.request_id)
        elif args.command == "resume-controller-task":
            result = resume_controller_task(args.request_id, args.reconciliation_receipt)
        elif args.command == "query-controller-task":
            result = query_controller_task(args.request_id)
        else:
            result = query_one(args.request_id)
    except Exception as exc:
        print(json.dumps({"result": "ERROR", "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
