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
from contextlib import contextmanager
from functools import wraps
import hashlib
import json
import os
import re
import subprocess
import threading
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
TASK_EXECUTION_LIMIT = "PT0S"
LEGACY_TASK_EXECUTION_LIMIT = "PT72H"
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
SCHEMA_CONTROLLER_RETIREMENT = "APCD_GPU_RUNNER_V1_CONTROLLER_RETIREMENT_RECEIPT_V1"
SCHEMA_CONTROLLER_QUEUE_SNAPSHOT = "APCD_COUPLING_SERIAL_QUEUE_STATE_SNAPSHOT_V1"
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
    temp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    raw = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    try:
        with temp.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temp, path)
        except FileExistsError:
            return False
        return True
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


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
                                 expected_resume_receipt_sha256=None, require_no_triggers=False,
                                 expected_execution_time_limit=TASK_EXECUTION_LIMIT):
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
    limit_value = limit[0].text if limit else LEGACY_TASK_EXECUTION_LIMIT
    if len(limit) > 1 or limit_value != expected_execution_time_limit:
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


def verify_worker_task(*, xml_text=None, expected_script=None, expected_principal=None,
                       expected_execution_time_limit=TASK_EXECUTION_LIMIT):
    xml_text = _query_task_xml() if xml_text is None else xml_text
    principal = _expected_principal() if expected_principal is None else expected_principal
    validated = validate_task_definition_xml(
        xml_text, expected_script=expected_script, expected_principal=principal,
        expected_execution_time_limit=expected_execution_time_limit)
    if xml_text is not None and os.name == "nt":
        info = _task_info()
        if str(info.get("UserId", "")).upper() != OWNER_ACCOUNT:
            raise SchedulerRunnerError("SCHEDULER_TASK_WRONG_PRINCIPAL")
        if int(info.get("LogonType", -1)) != 3 or int(info.get("RunLevel", -1)) != 0:
            raise SchedulerRunnerError("SCHEDULER_TASK_PRINCIPAL_SETTINGS_INVALID")
        multiple = info.get("MultipleInstances")
        if multiple not in (2, "2", "IgnoreNew"):
            raise SchedulerRunnerError("SCHEDULER_TASK_MULTIPLE_INSTANCE_POLICY_INVALID")
        if str(info.get("ExecutionTimeLimit")) != expected_execution_time_limit:
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


def _task_state_value(task):
    if not isinstance(task, dict):
        return ""
    states = {str(value or "").strip().lower()
              for key, value in task.items() if str(key).casefold() == "state"}
    if len(states) > 1:
        raise SchedulerRunnerError("SCHEDULER_TASK_STATE_AMBIGUOUS")
    return next(iter(states), "")


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


def _validate_gpu_resource_name(value):
    if value is None or value == "":
        raise SchedulerRunnerError("GPU_RESOURCE_NAME_REQUIRED")
    if (not isinstance(value, str) or len(value) > 128 or value != value.strip()
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise SchedulerRunnerError("GPU_RESOURCE_NAME_INVALID")
    return value


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
    _validate_gpu_resource_name(request.get("gpu_resource_name"))
    manifest_path = Path(request["manifest_path"]).resolve(strict=True)
    if _sha(manifest_path) != request.get("manifest_sha256"):
        raise SchedulerRunnerError("SCHEDULED_REQUEST_MANIFEST_HASH_CHANGED")
    if _sha(Path(__file__).resolve()) != request.get("worker_module_sha256"):
        raise SchedulerRunnerError("SCHEDULED_REQUEST_WORKER_MODULE_CHANGED")
    adapter_path = Path(request["adapter_path"]).resolve(strict=True)
    if _sha(adapter_path) != request.get("adapter_sha256"):
        raise SchedulerRunnerError("SCHEDULED_REQUEST_ADAPTER_CHANGED")
    return request


def _serialize_controller_lifecycle(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        root = kwargs.get("root", PRODUCTION_ROOT)
        with _controller_lifecycle_lock(root):
            return function(*args, **kwargs)
    return wrapped

def submit_one(manifest_path, *, root=PRODUCTION_ROOT, adapter_module=None, start_task=True,
               gpu_resource_name=None):
    adapter_module = adapter_module or _adapter_module()
    if gpu_resource_name is None:
        gpu_resource_name = os.environ.get("APCD_GPU_RESOURCE_NAME")
    gpu_resource_name = _validate_gpu_resource_name(gpu_resource_name)
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
    body = dict(stable, request_id=request_id, created_utc=_now(),
                gpu_resource_name=gpu_resource_name)
    request = dict(body, request_sha256=_sha_bytes(_canonical(body)))
    request_dir = _request_paths(root, request_id)
    request_dir.mkdir(parents=True, exist_ok=True)
    request_path = request_dir / "request.json"
    if request_path.exists():
        existing = _read_and_verify_request(request_path)
        for key, value in stable.items():
            if existing.get(key) != value:
                raise SchedulerRunnerError("SCHEDULED_REQUEST_ID_COLLISION")
        if existing.get("gpu_resource_name") != gpu_resource_name:
            raise SchedulerRunnerError("SCHEDULED_REQUEST_ID_COLLISION")
    else:
        if not _create_exclusive_json(request_path, request):
            existing = _read_and_verify_request(request_path)
            for key, value in stable.items():
                if existing.get(key) != value:
                    raise SchedulerRunnerError("SCHEDULED_REQUEST_ID_COLLISION")
            if existing.get("gpu_resource_name") != gpu_resource_name:
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
        if task and _task_state_value(task) in ("running", "queued"):
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
        state = "RUNNING" if task and _task_state_value(task) in ("running", "queued") else "NEEDS_RECONCILIATION"
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
    production_run_cli = run_cli is None
    run_cli = adapter_module.run_cli if production_run_cli else run_cli
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
        if production_run_cli:
            native_adapter = getattr(adapter_module, "NativeAdapter", None)
            if not callable(native_adapter):
                raise SchedulerRunnerError("SCHEDULED_WORKER_NATIVE_ADAPTER_MISSING")

            def request_bound_adapter(contract_path):
                return native_adapter(
                    contract_path, gpu_resource_name=request["gpu_resource_name"])

            result = run_cli(request["manifest_path"], adapter_factory=request_bound_adapter)
        else:
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
        task_state = _task_state_value(state.get("task"))
        if task_state in ("running", "queued"):
            saw_running = True
        elif state["state"] == "PENDING" and task_state in ("ready", ""):
            if not started_once or saw_running:
                with _controller_lifecycle_lock(root):
                    start_fn()
                started_once = True
                saw_running = False
        if time.monotonic() >= deadline:
            raise SchedulerRunnerError("SCHEDULED_WORKER_WAIT_TIMEOUT_NO_CANCEL")
        time.sleep(max(0.05, float(poll_interval_s)))


def worker_task_xml(*, principal=None, script_path=None, python_path=TASK_PYTHON):
    principal = principal or OWNER_ACCOUNT
    script_path = str(script_path or _task_script_path())
    def esc(value):
        return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        '<?xml version="1.0" encoding="UTF-16"?>'
        '<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">'
        '<RegistrationInfo><Author>APCD GPU Runner V1</Author><Description>Single request worker; no automatic solver replay.</Description></RegistrationInfo>'
        '<Triggers/>'
        '<Principals><Principal id="Author"><UserId>' + esc(principal) + '</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>'
        '<Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>'
        '<StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><AllowHardTerminate>true</AllowHardTerminate>'
        '<StartWhenAvailable>false</StartWhenAvailable><Enabled>true</Enabled><Hidden>true</Hidden>'
        '<ExecutionTimeLimit>' + TASK_EXECUTION_LIMIT + '</ExecutionTimeLimit><Priority>7</Priority></Settings>'
        '<Actions Context="Author"><Exec><Command>' + esc(python_path) + '</Command><Arguments>"' + esc(script_path) + '" worker-once</Arguments>'
        '<WorkingDirectory>' + esc(str(Path(script_path).parent)) + '</WorkingDirectory></Exec></Actions></Task>'
    )


def _write_worker_task_xml(xml_text, *, force=False):
    if os.name != "nt":
        raise SchedulerRunnerError("SCHEDULER_TASK_INSTALL_REQUIRES_WINDOWS")
    import tempfile
    with tempfile.NamedTemporaryFile("w", encoding="utf-16", suffix=".xml", delete=False) as stream:
        stream.write(xml_text)
        xml_path = stream.name
    try:
        command = ["schtasks.exe", "/Create", "/TN", TASK_NAME, "/XML", xml_path]
        if force:
            command.append("/F")
        proc = subprocess.run(command, text=True, capture_output=True, encoding="utf-8",
                              errors="replace", timeout=30, check=False)
        if proc.returncode != 0:
            raise SchedulerRunnerError("SCHEDULER_TASK_CREATE_FAILED:" + proc.stderr.strip()[:500])
    finally:
        try:
            Path(xml_path).unlink()
        except OSError:
            pass


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
        try:
            verify_worker_task(xml_text=existing.stdout, expected_script=script_path,
                               expected_principal=_expected_principal())
        except SchedulerRunnerError as exc:
            if str(exc) != "SCHEDULER_TASK_EXECUTION_TIME_LIMIT_INVALID":
                raise
            # Upgrade only the exact prior V1 task definition, and only while
            # the one-slot Runner and both scheduled owners are idle.
            verify_worker_task(
                xml_text=existing.stdout, expected_script=script_path,
                expected_principal=_expected_principal(),
                expected_execution_time_limit=LEGACY_TASK_EXECUTION_LIMIT)
            _assert_runner_slot_free(PRODUCTION_ROOT, _task_info)
            controller = _task_info(CONTROLLER_TASK_NAME)
            if _task_state_value(controller) in ("running", "queued"):
                raise SchedulerRunnerError("SCHEDULER_TASK_UPGRADE_CONTROLLER_ACTIVE")
            _assert_no_controller_or_solver_processes(
                _controller_process_inventory(), "worker-task-time-limit-upgrade")
            _write_worker_task_xml(xml_text, force=True)
            verify_worker_task(expected_script=script_path,
                               expected_principal=_expected_principal())
            return {"result": "UPDATED_EXECUTION_TIME_LIMIT", "task_name": task_name,
                    "execution_time_limit": TASK_EXECUTION_LIMIT}
        return {"result": "ALREADY_INSTALLED", "task_name": task_name}
    _write_worker_task_xml(xml_text, force=False)
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
    def esc(value):
        return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
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



_CONTROLLER_LIFECYCLE_THREAD_GUARD = threading.Lock()
_CONTROLLER_LIFECYCLE_THREAD_LOCKS = {}

@contextmanager
def _controller_lifecycle_lock(root):
    path = Path(root) / CONTROLLER_TASK_DIR.name / "lifecycle.lock"
    key = os.path.normcase(os.path.abspath(str(path)))
    with _CONTROLLER_LIFECYCLE_THREAD_GUARD:
        thread_lock = _CONTROLLER_LIFECYCLE_THREAD_LOCKS.setdefault(key, threading.RLock())
    with thread_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        token = json.dumps({"pid": os.getpid(), "token": uuid.uuid4().hex},
                           sort_keys=True, separators=(",", ":")).encode("utf-8")
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise SchedulerRunnerError("CONTROLLER_LIFECYCLE_LOCKED") from exc
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(token)
                stream.flush()
                os.fsync(stream.fileno())
            yield
        finally:
            try:
                if path.read_bytes() == token:
                    path.unlink()
            except OSError:
                pass


def _set_controller_task_enabled(enabled):
    if os.name != "nt":
        raise SchedulerRunnerError("SCHEDULER_TASK_REBIND_REQUIRES_WINDOWS")
    proc = subprocess.run(
        ["schtasks.exe", "/Change", "/TN", CONTROLLER_TASK_NAME,
         "/Enable" if enabled else "/Disable"],
        text=True, capture_output=True, encoding="utf-8", errors="replace",
        timeout=30, check=False)
    if proc.returncode != 0:
        raise SchedulerRunnerError("SCHEDULER_CONTROLLER_TASK_ENABLE_CHANGE_FAILED:"
                                   + proc.stderr.strip()[:400])



def _controller_task_is_enabled(xml_text, *, missing_default=None):
    try:
        root = ET.fromstring(xml_text.lstrip("\ufeff"))
    except ET.ParseError as exc:
        raise SchedulerRunnerError("SCHEDULER_TASK_XML_INVALID") from exc
    settings = _xml_children(root, "Settings")
    if len(settings) != 1:
        raise SchedulerRunnerError("SCHEDULER_TASK_ENABLED_STATE_INVALID")
    enabled = _xml_children(settings[0], "Enabled")
    if len(enabled) == 0 and missing_default is not None:
        return bool(missing_default)
    if len(enabled) != 1 or (
            (enabled[0].text or "").strip().lower() not in ("true", "false")):
        raise SchedulerRunnerError("SCHEDULER_TASK_ENABLED_STATE_INVALID")
    return (enabled[0].text or "").strip().lower() == "true"


def _validate_controller_task_scheduler_info(task_info, *,
                                             expected_execution_time_limit,
                                             expected_enabled=None):
    if not isinstance(task_info, dict):
        raise SchedulerRunnerError("CONTROLLER_REBIND_SCHEDULER_TASK_INFO_INVALID")
    state = _task_state_value(task_info)
    if state == "ready":
        actual_enabled = True
    elif state == "disabled":
        actual_enabled = False
    else:
        raise SchedulerRunnerError("CONTROLLER_REBIND_SCHEDULER_TASK_STATE_UNSUPPORTED")
    if expected_enabled is not None and actual_enabled is not bool(expected_enabled):
        raise SchedulerRunnerError("CONTROLLER_REBIND_SCHEDULER_TASK_ENABLED_MISMATCH")
    account = str(task_info.get("UserId", "")).strip().lower().rsplit("\\", 1)[-1]
    if account != OWNER_ACCOUNT.lower():
        raise SchedulerRunnerError("SCHEDULER_TASK_WRONG_PRINCIPAL")
    if str(task_info.get("LogonType", "")).strip().lower() not in ("3", "interactivetoken"):
        raise SchedulerRunnerError("SCHEDULER_TASK_LOGON_TYPE_UNSUPPORTED")
    if str(task_info.get("RunLevel", "")).strip().lower() not in ("0", "leastprivilege"):
        raise SchedulerRunnerError("SCHEDULER_TASK_RUNLEVEL_UNSUPPORTED")
    if str(task_info.get("MultipleInstances", "")).strip().lower() not in ("2", "ignorenew"):
        raise SchedulerRunnerError("SCHEDULER_TASK_MULTIPLE_INSTANCE_POLICY_INVALID")
    if str(task_info.get("ExecutionTimeLimit", "")).strip() != expected_execution_time_limit:
        raise SchedulerRunnerError("SCHEDULER_TASK_EXECUTION_TIME_LIMIT_INVALID")
    if task_info.get("RestartCount") not in (None, 0, "0"):
        raise SchedulerRunnerError("SCHEDULER_TASK_AUTOMATIC_RESTART_FORBIDDEN")
    return actual_enabled


def _controller_process_inventory():
    if os.name != "nt":
        raise SchedulerRunnerError("CONTROLLER_PROCESS_CENSUS_REQUIRES_WINDOWS")
    command = ("$ErrorActionPreference='Stop'; "
               "@(Get-CimInstance Win32_Process | "
               "Select-Object ProcessId,ParentProcessId,Name,CommandLine | "
               "ConvertTo-Json -Compress)")
    proc = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive",
                           "-Command", command],
                          text=True, capture_output=True, encoding="utf-8",
                          errors="replace", timeout=30, check=False)
    if proc.returncode != 0:
        raise SchedulerRunnerError("CONTROLLER_PROCESS_CENSUS_FAILED:"
                                   + proc.stderr.strip()[:400])
    try:
        value = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise SchedulerRunnerError("CONTROLLER_PROCESS_CENSUS_INVALID") from exc
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise SchedulerRunnerError("CONTROLLER_PROCESS_CENSUS_INVALID")
    return value


def _assert_no_controller_or_solver_processes(processes, old_request_id):
    if not isinstance(processes, list) or any(not isinstance(item, dict) for item in processes):
        raise SchedulerRunnerError("CONTROLLER_PROCESS_CENSUS_INVALID")
    for process in processes:
        name = str(process.get("Name", process.get("name", ""))).lower()
        command = str(process.get("CommandLine", process.get("command_line", ""))).lower()
        if (old_request_id.lower() in command
                or "serial_queue.py" in command
                or ("task_scheduler_v1.py" in command and
                    ("worker-once" in command or old_request_id.lower() in command))
                or "fdtd-engine" in name or "fdtd-engine" in command):
            raise SchedulerRunnerError("CONTROLLER_OR_SOLVER_PROCESS_STILL_ACTIVE")


def _assert_runner_slot_free(root, task_info_fn):
    root = Path(root)
    for path in (root / "active_run.json", root / ".runner.lock",
                 root / TASK_LOCK.name):
        if path.exists():
            raise SchedulerRunnerError("RUNNER_SLOT_OR_LOCK_STILL_ACTIVE:" + path.name)
    worker = task_info_fn(TASK_NAME)
    if _task_state_value(worker) in ("running", "queued"):
        raise SchedulerRunnerError("RUNNER_WORKER_TASK_STILL_ACTIVE")


def _validate_controller_task_xml(xml_text, info, request_id, request_path,
                                  expected_principal, resume_path=None, resume_sha=None,
                                  expected_execution_time_limit=TASK_EXECUTION_LIMIT):
    return validate_task_definition_xml(
        xml_text, expected_script=info["controller_script_path"],
        expected_principal=expected_principal, task_name=CONTROLLER_TASK_NAME,
        expected_argument="--runner-controller-manifest", expected_manifest=request_path,
        expected_manifest_sha256=info["manifest_sha256"], expected_request_id=request_id,
        expected_resume_receipt=resume_path, expected_resume_receipt_sha256=resume_sha,
        require_no_triggers=True,
        expected_execution_time_limit=expected_execution_time_limit)


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


@_serialize_controller_lifecycle
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
        state = _task_state_value(task)
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


@_serialize_controller_lifecycle
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
    if _task_state_value(task) in ("running", "queued"):
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


@_serialize_controller_lifecycle
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
    if _task_state_value(task) in ("running", "queued"):
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
    task = (task_info_fn or _task_info)(CONTROLLER_TASK_NAME)
    # Read old bindings for reconciliation, but starts require the current PT0S definition.
    task_limit = task.get("ExecutionTimeLimit", TASK_EXECUTION_LIMIT) if isinstance(task, dict) else TASK_EXECUTION_LIMIT
    expected_limit = (LEGACY_TASK_EXECUTION_LIMIT
                      if str(task_limit) == LEGACY_TASK_EXECUTION_LIMIT else TASK_EXECUTION_LIMIT)
    _validate_controller_task_xml((xml_query_fn or _query_task_xml)(CONTROLLER_TASK_NAME),
        info, request_id, _controller_request_files(root, request_id)[1],
        _expected_principal() if expected_principal is None else expected_principal,
        current.get("resume_receipt_path"), current.get("resume_receipt_sha256"),
        expected_execution_time_limit=expected_limit)
    status = None
    if info["status_path"].is_file():
        status = _read_json(info["status_path"])
        if (status.get("schema") != SCHEMA_CONTROLLER_STATUS
                or status.get("request_id") != request_id
                or status.get("controller_manifest_sha256") != info["manifest_sha256"]
                or status.get("queue_id") != info["manifest"]["queue_id"]):
            raise SchedulerRunnerError("CONTROLLER_STATUS_IDENTITY_MISMATCH")
    if _task_state_value(task) in ("running", "queued"):
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




def _read_retirement_controller_request(request_id, *, root, coupling_root):
    directory, manifest_path, binding_path, start_claim = _controller_request_files(root, request_id)
    if not manifest_path.is_file() or not binding_path.is_file():
        raise SchedulerRunnerError("SCHEDULED_CONTROLLER_REQUEST_NOT_FOUND")
    raw = manifest_path.read_bytes()
    manifest_sha = _sha_bytes(raw)
    binding = _controller_body_with_verified_hash(
        _read_json(binding_path), SCHEMA_CONTROLLER_BINDING,
        "SCHEDULED_CONTROLLER_REQUEST_BINDING_INVALID")
    if manifest_sha[:32] != request_id or binding.get("request_id") != request_id:
        raise SchedulerRunnerError("SCHEDULED_CONTROLLER_REQUEST_HASH_INVALID")
    if binding.get("controller_manifest_sha256") != manifest_sha:
        raise SchedulerRunnerError("SCHEDULED_CONTROLLER_REQUEST_HASH_INVALID")
    try:
        manifest = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SchedulerRunnerError("CONTROLLER_RETIREMENT_OLD_MANIFEST_INVALID") from exc
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA_CONTROLLER_MANIFEST:
        raise SchedulerRunnerError("CONTROLLER_RETIREMENT_OLD_MANIFEST_INVALID")
    expected_script = (Path(coupling_root) / "scripts" / "coupling_ml" /
                       "k6_v2_pipeline" / "serial_queue.py").resolve(strict=True)
    script_path = _path_within(manifest.get("controller_script_path"), coupling_root)
    queue_path = _path_within(manifest.get("queue_manifest_path"), coupling_root)
    status_path = _path_within(manifest.get("status_path"), coupling_root, strict=False)
    if script_path != expected_script:
        raise SchedulerRunnerError("CONTROLLER_RETIREMENT_OLD_ENTRYPOINT_UNAPPROVED")
    if (not _is_sha256(manifest.get("controller_script_sha256"))
            or binding.get("controller_script_sha256") != manifest["controller_script_sha256"].lower()):
        raise SchedulerRunnerError("CONTROLLER_RETIREMENT_OLD_SCRIPT_PIN_INVALID")
    if (not _is_sha256(manifest.get("queue_manifest_sha256"))
            or _sha(queue_path) != manifest["queue_manifest_sha256"].lower()
            or binding.get("queue_manifest_sha256") != manifest["queue_manifest_sha256"].lower()):
        raise SchedulerRunnerError("CONTROLLER_QUEUE_MANIFEST_HASH_MISMATCH")
    if (manifest.get("max_concurrent_cases") != 1
            or manifest.get("per_case_max_solver_entries") != 1
            or manifest.get("post_entry_automatic_replays") != 0
            or manifest.get("startup_reconcile_before_dispatch") is not True
            or manifest.get("truth_before_next_case") is not True):
        raise SchedulerRunnerError("CONTROLLER_RETIREMENT_OLD_BUDGET_INVALID")
    if (binding.get("controller_run_id") != manifest.get("controller_run_id")
            or binding.get("queue_id") != manifest.get("queue_id")
            or binding.get("status_path") != str(status_path)):
        raise SchedulerRunnerError("SCHEDULED_CONTROLLER_REQUEST_BINDING_CONFLICT")
    info = {"manifest": manifest, "manifest_path": manifest_path, "raw": raw,
            "manifest_sha256": manifest_sha, "controller_script_path": script_path,
            "queue_manifest_path": queue_path, "status_path": status_path}
    return info, binding, _sha_bytes(binding_path.read_bytes()), start_claim


def _verify_controller_retirement_evidence(receipt_path, receipt_sha256, *,
                                           old_request_id, old_info, old_request_binding_sha256,
                                           old_task_binding_sha256, new_info, coupling_root):
    receipt_path = _path_within(receipt_path, coupling_root)
    receipt_raw = receipt_path.read_bytes()
    if _sha_bytes(receipt_raw) != receipt_sha256:
        raise SchedulerRunnerError("CONTROLLER_RETIREMENT_RECEIPT_HASH_MISMATCH")
    try:
        receipt = json.loads(receipt_raw.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SchedulerRunnerError("CONTROLLER_RETIREMENT_RECEIPT_INVALID") from exc
    old_manifest = old_info["manifest"]
    status_path = old_info["status_path"]
    if not status_path.is_file():
        raise SchedulerRunnerError("CONTROLLER_RETIREMENT_STATUS_MISSING")
    status_raw = status_path.read_bytes()
    status = json.loads(status_raw.decode("utf-8-sig"))
    expected = {
        "schema": SCHEMA_CONTROLLER_RETIREMENT,
        "old_request_id": old_request_id,
        "old_manifest_sha256": old_info["manifest_sha256"],
        "old_request_binding_sha256": old_request_binding_sha256,
        "old_task_binding_sha256": old_task_binding_sha256,
        "old_status_sha256": _sha_bytes(status_raw),
        "new_manifest_sha256": new_info["manifest_sha256"],
        "queue_id": old_manifest["queue_id"],
        "queue_manifest_sha256": old_manifest["queue_manifest_sha256"],
        "safe_to_retire": True,
        "startup_reconciled": True,
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise SchedulerRunnerError("CONTROLLER_RETIREMENT_RECEIPT_NOT_SAFE")
    if not isinstance(receipt.get("approved_by"), str) or not receipt["approved_by"].strip():
        raise SchedulerRunnerError("CONTROLLER_RETIREMENT_OWNER_APPROVAL_MISSING")
    for path_key, sha_key in (("owner_decision_path", "owner_decision_sha256"),
                              ("queue_state_path", "queue_state_sha256")):
        raw_path = receipt.get(path_key)
        if not isinstance(raw_path, str) or not raw_path or not _is_sha256(receipt.get(sha_key)):
            raise SchedulerRunnerError("CONTROLLER_RETIREMENT_EVIDENCE_PATH_INVALID")
        evidence_path = _path_within(raw_path, coupling_root)
        if not evidence_path.is_file() or _sha(evidence_path) != receipt[sha_key].lower():
            raise SchedulerRunnerError("CONTROLLER_RETIREMENT_EVIDENCE_HASH_MISMATCH")
    queue_state_path = _path_within(receipt["queue_state_path"], coupling_root)
    try:
        queue_state = json.loads(queue_state_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SchedulerRunnerError("CONTROLLER_RETIREMENT_QUEUE_STATE_INVALID") from exc
    runner_ids = receipt.get("runner_request_ids")
    if not isinstance(runner_ids, list) or len(set(runner_ids)) != len(runner_ids):
        raise SchedulerRunnerError("CONTROLLER_RETIREMENT_RUNNER_INVENTORY_INVALID")
    if (status.get("schema") != SCHEMA_CONTROLLER_STATUS
            or status.get("state") != "STOPPED_RECONCILED"
            or status.get("request_id") != old_request_id
            or status.get("controller_manifest_sha256") != old_info["manifest_sha256"]
            or status.get("queue_id") != old_manifest["queue_id"]
            or status.get("current_case_id") is not None
            or status.get("unresolved_runner_request_ids") != []
            or status.get("post_entry_automatic_replays") != 0
            or status.get("runner_request_ids") != runner_ids):
        raise SchedulerRunnerError("CONTROLLER_RETIREMENT_STATUS_NOT_RECONCILED")
    completed = queue_state.get("completed_case_ids")
    entered = queue_state.get("solver_entered_case_ids")
    quarantined = queue_state.get("quarantined_case_ids")
    remaining = new_info["manifest"]["case_ids"]
    old_cases = old_manifest["case_ids"]
    arrays = (completed, entered, quarantined, queue_state.get("authorized_case_ids"),
              queue_state.get("remaining_case_ids"), queue_state.get("unresolved_runner_request_ids"))
    if any(not isinstance(items, list) or any(not isinstance(x, str) for x in items)
           for items in arrays):
        raise SchedulerRunnerError("CONTROLLER_RETIREMENT_QUEUE_STATE_INVALID")
    if (queue_state.get("schema") != SCHEMA_CONTROLLER_QUEUE_SNAPSHOT
            or queue_state.get("queue_id") != old_manifest["queue_id"]
            or queue_state.get("queue_manifest_sha256") != old_manifest["queue_manifest_sha256"]
            or queue_state.get("authorized_case_ids") != old_cases
            or queue_state.get("remaining_case_ids") != remaining
            or queue_state.get("active_case_count") != 0
            or queue_state.get("active_case_id") is not None
            or queue_state.get("unresolved_runner_request_ids") != []
            or queue_state.get("pending_replay_count") != 0
            or queue_state.get("max_concurrent_cases") != 1
            or queue_state.get("per_case_max_solver_entries") != 1
            or queue_state.get("post_entry_automatic_replays") != 0
            or not set(completed).issubset(old_cases)
            or not set(entered).issubset(old_cases)
            or not set(quarantined).issubset(old_cases)
            or set(remaining) & (set(completed) | set(entered) | set(quarantined))):
        raise SchedulerRunnerError("CONTROLLER_RETIREMENT_QUEUE_STATE_NOT_SAFE")
    return receipt, receipt_raw, status_raw, queue_state_path.read_bytes(), queue_state



def _verify_retired_request_ids(receipt, *, root, query_one_fn, allowed_case_ids, queue_state):
    quarantined = set(queue_state["quarantined_case_ids"])
    for request_id in receipt["runner_request_ids"]:
        if not REQUEST_ID_RE.fullmatch(str(request_id)):
            raise SchedulerRunnerError("CONTROLLER_RETIREMENT_RUNNER_REQUEST_ID_INVALID")
        state = query_one_fn(request_id, root=root, task_info_fn=lambda: {"state": "Ready"})
        if state.get("state") != "TERMINAL":
            raise SchedulerRunnerError("CONTROLLER_RETIREMENT_RUNNER_REQUEST_UNRESOLVED:" + request_id)
        request = state.get("request", {})
        identity = request.get("identity", {})
        case_id = identity.get("case_id")
        if case_id not in allowed_case_ids:
            raise SchedulerRunnerError("CONTROLLER_RETIREMENT_RUNNER_CASE_OUTSIDE_BOUND:" + request_id)
        run_dir = Path(root) / "runs" / case_id / identity.get("attempt_id", "") / identity.get("run_id", "")
        status_path = run_dir / "status.json"
        if not status_path.is_file():
            raise SchedulerRunnerError("CONTROLLER_RETIREMENT_RUN_STATUS_MISSING:" + request_id)
        status = _read_json(status_path)
        if any(status.get(key) != identity.get(key) for key in ("case_id", "attempt_id", "run_id")):
            raise SchedulerRunnerError("CONTROLLER_RETIREMENT_RUN_STATUS_IDENTITY_MISMATCH:" + request_id)
        entered = status.get("solver_entered") is True
        invocations = status.get("solver_invocations")
        if (status.get("replay_count", 0) != 0
                or (entered and invocations != 1)
                or (not entered and invocations != 0)):
            raise SchedulerRunnerError("CONTROLLER_RETIREMENT_ENTRY_COUNT_INVALID:" + request_id)
        if status.get("state") == "DONE":
            _verify_resume_request_ids(
                {"runner_request_ids": [request_id]}, root=root, query_one_fn=query_one_fn,
                allowed_case_ids=allowed_case_ids)
            continue
        if entered:
            if (case_id not in quarantined
                    or state.get("result", {}).get("solver_entered") is not True
                    or not status.get("failure")):
                raise SchedulerRunnerError("CONTROLLER_RETIREMENT_POSTENTRY_FAILURE_NOT_QUARANTINED:" + request_id)
        elif state.get("result", {}).get("solver_entered") is True:
            raise SchedulerRunnerError("CONTROLLER_RETIREMENT_ENTRY_EVIDENCE_MISMATCH:" + request_id)



def _validate_rebind_manifest_delta(old_manifest, new_manifest):
    allowed = {"controller_run_id", "controller_script_sha256", "status_path",
               "case_ids", "max_cases"}
    if set(old_manifest) != set(new_manifest):
        raise SchedulerRunnerError("CONTROLLER_REBIND_MANIFEST_SCHEMA_DRIFT")
    if any(old_manifest[key] != new_manifest[key] for key in old_manifest if key not in allowed):
        raise SchedulerRunnerError("CONTROLLER_REBIND_MANIFEST_UNAPPROVED_CHANGE")
    old_cases, new_cases = old_manifest["case_ids"], new_manifest["case_ids"]
    cursor = 0
    for case_id in new_cases:
        try:
            cursor = old_cases.index(case_id, cursor) + 1
        except ValueError as exc:
            raise SchedulerRunnerError("CONTROLLER_REBIND_CASE_BUDGET_EXPANSION") from exc
    if (not new_cases or len(new_cases) > len(old_cases)
            or new_manifest["max_cases"] != len(new_cases)
            or new_manifest["controller_run_id"] == old_manifest["controller_run_id"]
            or new_manifest["controller_script_sha256"] == old_manifest["controller_script_sha256"]
            or new_manifest["status_path"] == old_manifest["status_path"]):
        raise SchedulerRunnerError("CONTROLLER_REBIND_MANIFEST_CHANGE_INVALID")


def _ensure_rebind_request_files(root, info, request_id):
    directory, request_path, binding_path, claim_path = _controller_request_files(root, request_id)
    directory.mkdir(parents=True, exist_ok=True)
    if request_path.exists():
        if _sha(request_path) != info["manifest_sha256"]:
            raise SchedulerRunnerError("SCHEDULED_CONTROLLER_REQUEST_ID_COLLISION")
    elif not _write_exclusive_bytes(request_path, info["raw"]):
        if _sha(request_path) != info["manifest_sha256"]:
            raise SchedulerRunnerError("SCHEDULED_CONTROLLER_REQUEST_ID_COLLISION")
    value = {
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
    value["binding_sha256"] = _sha_bytes(_canonical(value))
    if binding_path.exists():
        old = _controller_body_with_verified_hash(
            _read_json(binding_path), SCHEMA_CONTROLLER_BINDING,
            "SCHEDULED_CONTROLLER_REQUEST_BINDING_INVALID")
        if any(old.get(key) != val for key, val in value.items()
               if key not in ("created_utc", "binding_sha256")):
            raise SchedulerRunnerError("SCHEDULED_CONTROLLER_REQUEST_BINDING_CONFLICT")
    elif not _create_exclusive_json(binding_path, value):
        raise SchedulerRunnerError("SCHEDULED_CONTROLLER_REQUEST_BINDING_CONFLICT")
    if claim_path.exists() or info["status_path"].exists():
        raise SchedulerRunnerError("CONTROLLER_REBIND_NEW_REQUEST_ALREADY_STARTED")
    return request_path, binding_path, claim_path



def _controller_task_xml_matches(xml_text, info, request_id, binding, root, principal, *,
                                 expected_execution_time_limit=TASK_EXECUTION_LIMIT,
                                 task_info=None, expected_enabled=None,
                                 missing_enabled_default=None):
    request_path = _controller_request_files(root, request_id)[1]
    _validate_controller_task_xml(
        xml_text, info, request_id, request_path, principal,
        binding.get("resume_receipt_path"), binding.get("resume_receipt_sha256"),
        expected_execution_time_limit=expected_execution_time_limit)
    enabled = _controller_task_is_enabled(xml_text, missing_default=missing_enabled_default)
    if task_info is not None:
        actual_enabled = _validate_controller_task_scheduler_info(
            task_info, expected_execution_time_limit=expected_execution_time_limit,
            expected_enabled=expected_enabled)
        if enabled != actual_enabled:
            raise SchedulerRunnerError("CONTROLLER_REBIND_SCHEDULER_TASK_ENABLED_MISMATCH")
    elif expected_enabled is not None and enabled is not bool(expected_enabled):
        raise SchedulerRunnerError("CONTROLLER_REBIND_SCHEDULER_TASK_ENABLED_MISMATCH")
    return enabled


def _controller_predecessor_task_xml_matches(xml_text, info, request_id, binding,
                                              root, principal, task_info):
    """Recognize only the PT72H default/explicit predecessor or explicit PT0S."""
    if not isinstance(task_info, dict):
        raise SchedulerRunnerError("CONTROLLER_REBIND_SCHEDULER_TASK_INFO_INVALID")
    actual_limit = str(task_info.get("ExecutionTimeLimit", "")).strip()
    if actual_limit not in (LEGACY_TASK_EXECUTION_LIMIT, TASK_EXECUTION_LIMIT):
        raise SchedulerRunnerError("SCHEDULER_TASK_EXECUTION_TIME_LIMIT_INVALID")
    actual_enabled = _validate_controller_task_scheduler_info(
        task_info, expected_execution_time_limit=actual_limit)
    return _controller_task_xml_matches(
        xml_text, info, request_id, binding, root, principal,
        expected_execution_time_limit=actual_limit, task_info=task_info,
        expected_enabled=actual_enabled, missing_enabled_default=actual_enabled)


def _controller_task_scheduler_audit_record(xml_text, task_info, *, request_id,
                                             manifest_sha256, binding_sha256,
                                             transaction_id):
    try:
        root = ET.fromstring(xml_text.lstrip("\ufeff"))
    except ET.ParseError as exc:
        raise SchedulerRunnerError("SCHEDULER_TASK_XML_INVALID") from exc
    settings = _xml_children(root, "Settings")
    if len(settings) != 1:
        raise SchedulerRunnerError("SCHEDULER_TASK_SETTINGS_INVALID")
    limits = _xml_children(settings[0], "ExecutionTimeLimit")
    enabled = _xml_children(settings[0], "Enabled")
    if len(limits) > 1 or len(enabled) > 1:
        raise SchedulerRunnerError("SCHEDULER_TASK_SETTINGS_INVALID")
    actual_limit = str(task_info.get("ExecutionTimeLimit", "")).strip()
    if actual_limit == LEGACY_TASK_EXECUTION_LIMIT:
        contract = ("LEGACY_CONTROLLER_PT72H_EXPLICIT_V1" if limits else
                    "LEGACY_CONTROLLER_PT72H_DEFAULTED_V1")
    elif actual_limit == TASK_EXECUTION_LIMIT:
        contract = "CONTROLLER_PT0S_EXPLICIT_V1"
    else:
        raise SchedulerRunnerError("SCHEDULER_TASK_EXECUTION_TIME_LIMIT_INVALID")
    return {
        "schema": "APCD_GPU_RUNNER_V1_CONTROLLER_TASK_CONTRACT_AUDIT_V1",
        "transaction_id": transaction_id, "task_name": CONTROLLER_TASK_NAME,
        "request_id": request_id, "manifest_sha256": manifest_sha256,
        "task_binding_sha256": binding_sha256, "recognized_contract": contract,
        "scheduler_execution_time_limit": actual_limit,
        "xml_execution_time_limit": (limits[0].text or "").strip() if limits else None,
        "xml_enabled": (enabled[0].text or "").strip().lower() if enabled else None,
        "xml_sha256": _sha_bytes(xml_text.encode("utf-8")),
        "scheduler_task_info": {
            key: task_info.get(key) for key in
            ("State", "LastTaskResult", "LastRunTime", "UserId", "LogonType",
             "RunLevel", "MultipleInstances", "ExecutionTimeLimit", "RestartCount")
        },
        "observed_utc": _now(),
    }


def _journal_rebind_phase(journal_path, current, phase):
    transitions = {
        "PREPARED": "OLD_TASK_DISABLED",
        "OLD_TASK_DISABLED": "NEW_TASK_DISABLED",
        "NEW_TASK_DISABLED": "BINDING_SWITCHED",
        "BINDING_SWITCHED": "COMPLETE",
        "COMPLETE": None,
    }
    disk = _read_json(journal_path)
    if (disk.get("schema") != "APCD_GPU_RUNNER_V1_CONTROLLER_REBIND_TRANSACTION_V1"
            or disk.get("transaction_id") != current.get("transaction_id")
            or disk.get("phase") != current.get("phase")):
        raise SchedulerRunnerError("CONTROLLER_REBIND_TRANSACTION_CONFLICT")
    if phase == disk.get("phase"):
        return disk
    if phase == "PREPARED" and disk.get("phase") in transitions:
        return disk
    if transitions.get(disk.get("phase")) != phase:
        raise SchedulerRunnerError("CONTROLLER_REBIND_PHASE_TRANSITION_INVALID")
    updated = dict(disk, phase=phase, updated_utc=_now())
    _atomic_json(journal_path, updated)
    return updated


@_serialize_controller_lifecycle
def retire_rebind_controller_task(old_request_id, new_manifest_path, retirement_receipt_path, *,
                                  expected_old_task_binding_sha256,
                                  expected_new_manifest_sha256,
                                  expected_retirement_receipt_sha256,
                                  root=PRODUCTION_ROOT, coupling_root=COUPLING_WORKTREE,
                                  xml_query_fn=None, task_info_fn=None, create_task_fn=None,
                                  set_enabled_fn=None, process_inventory_fn=None,
                                  query_one_fn=None, expected_principal=None):
    pins = (expected_old_task_binding_sha256, expected_new_manifest_sha256,
            expected_retirement_receipt_sha256)
    if any(not _is_sha256(value) for value in pins):
        raise SchedulerRunnerError("CONTROLLER_REBIND_EXPECTED_HASH_INVALID")
    old_info, _old_request_binding, request_binding_sha, _claim = (
        _read_retirement_controller_request(old_request_id, root=root, coupling_root=coupling_root))
    new_info = _controller_manifest(new_manifest_path, coupling_root=coupling_root)
    if new_info["manifest_sha256"] != expected_new_manifest_sha256.lower():
        raise SchedulerRunnerError("CONTROLLER_REBIND_NEW_MANIFEST_HASH_MISMATCH")
    new_request_id = new_info["manifest_sha256"][:32]
    if new_request_id == old_request_id:
        raise SchedulerRunnerError("CONTROLLER_REBIND_REQUEST_ID_NOT_NEW")
    _validate_rebind_manifest_delta(old_info["manifest"], new_info["manifest"])
    if (old_info["queue_manifest_path"] != new_info["queue_manifest_path"]
            or old_info["manifest"]["queue_manifest_sha256"] !=
               new_info["manifest"]["queue_manifest_sha256"]):
        raise SchedulerRunnerError("CONTROLLER_REBIND_QUEUE_MANIFEST_DRIFT")
    task_binding_path = _task_controller_binding_path(root)
    if not task_binding_path.is_file():
        raise SchedulerRunnerError("CONTROLLER_TASK_BINDING_MISSING")
    current_raw = task_binding_path.read_bytes()
    current_sha = _sha_bytes(current_raw)
    current = _read_controller_task_binding(root)
    old_task_sha = expected_old_task_binding_sha256.lower()
    txid = _sha_bytes(_canonical({
        "old_request_id": old_request_id, "old_task_binding_sha256": old_task_sha,
        "new_request_id": new_request_id, "new_manifest_sha256": new_info["manifest_sha256"],
        "retirement_receipt_sha256": expected_retirement_receipt_sha256.lower()}))
    txdir = Path(root) / CONTROLLER_TASK_DIR.name / "rebind_transactions" / txid
    journal_path = txdir / "journal.json"
    journal_exists = journal_path.is_file()
    if current.get("request_id") == old_request_id:
        if current_sha != old_task_sha:
            raise SchedulerRunnerError("CONTROLLER_REBIND_OLD_BINDING_HASH_MISMATCH")
    elif current.get("request_id") == new_request_id:
        if not journal_exists:
            raise SchedulerRunnerError("CONTROLLER_REBIND_UNJOURNALED_NEW_BINDING")
    else:
        raise SchedulerRunnerError("CONTROLLER_REBIND_CURRENT_BINDING_MISMATCH")
    receipt, receipt_raw, status_raw, queue_state_raw, queue_state = _verify_controller_retirement_evidence(
        retirement_receipt_path, expected_retirement_receipt_sha256.lower(),
        old_request_id=old_request_id, old_info=old_info,
        old_request_binding_sha256=request_binding_sha, old_task_binding_sha256=old_task_sha,
        new_info=new_info, coupling_root=coupling_root)
    if receipt["runner_request_ids"]:
        _verify_retired_request_ids(receipt, root=root, query_one_fn=query_one_fn or query_one,
                                    allowed_case_ids=old_info["manifest"]["case_ids"],
                                    queue_state=queue_state)
    task_info_fn = task_info_fn or _task_info
    _assert_runner_slot_free(root, task_info_fn)
    process_fn = process_inventory_fn or _controller_process_inventory
    _assert_no_controller_or_solver_processes(process_fn(), old_request_id)
    task = task_info_fn(CONTROLLER_TASK_NAME)
    if _task_state_value(task) in ("running", "queued"):
        raise SchedulerRunnerError("CONTROLLER_REBIND_OLD_TASK_STILL_ACTIVE")
    xml_query_fn = xml_query_fn or _query_task_xml
    current_xml = xml_query_fn(CONTROLLER_TASK_NAME)
    principal = _expected_principal() if expected_principal is None else expected_principal
    new_request_path, new_binding_path, new_claim_path = _ensure_rebind_request_files(
        root, new_info, new_request_id)
    new_request_binding = _controller_body_with_verified_hash(
        _read_json(new_binding_path), SCHEMA_CONTROLLER_BINDING,
        "SCHEDULED_CONTROLLER_REQUEST_BINDING_INVALID")
    old_xml_enabled = None
    new_xml_enabled = None
    try:
        old_xml_enabled = _controller_predecessor_task_xml_matches(
            current_xml, old_info, old_request_id, current, root, principal, task)
    except SchedulerRunnerError:
        pass
    try:
        new_xml_enabled = _controller_task_xml_matches(
            current_xml, new_info, new_request_id, new_request_binding, root, principal,
            task_info=task, expected_enabled=(_task_state_value(task) == "ready"))
    except SchedulerRunnerError:
        pass
    if old_xml_enabled is None and new_xml_enabled is None:
        raise SchedulerRunnerError("CONTROLLER_REBIND_TASK_DEFINITION_MISMATCH")
    if new_xml_enabled is not None and not journal_exists:
        raise SchedulerRunnerError("CONTROLLER_REBIND_UNJOURNALED_NEW_TASK")
    if current.get("request_id") == old_request_id and new_xml_enabled is True:
        raise SchedulerRunnerError("CONTROLLER_REBIND_TASK_ENABLED_BEFORE_BINDING")
    if current.get("request_id") == new_request_id and old_xml_enabled is not None:
        raise SchedulerRunnerError("CONTROLLER_REBIND_TASK_BINDING_XML_MISMATCH")
    if not journal_exists:
        txdir.mkdir(parents=True, exist_ok=True)
        journal = {"schema": "APCD_GPU_RUNNER_V1_CONTROLLER_REBIND_TRANSACTION_V1",
                   "transaction_id": txid, "old_request_id": old_request_id,
                   "old_task_binding_sha256": old_task_sha, "new_request_id": new_request_id,
                   "new_manifest_sha256": new_info["manifest_sha256"],
                   "retirement_receipt_sha256": expected_retirement_receipt_sha256.lower(),
                   "phase": "PREPARED", "created_utc": _now(), "updated_utc": _now()}
        _create_exclusive_json(journal_path, journal)
    else:
        journal = _read_json(journal_path)
        if (journal.get("schema") != "APCD_GPU_RUNNER_V1_CONTROLLER_REBIND_TRANSACTION_V1"
                or journal.get("transaction_id") != txid
                or journal.get("old_task_binding_sha256") != old_task_sha
                or journal.get("new_manifest_sha256") != new_info["manifest_sha256"]
                or journal.get("retirement_receipt_sha256") != expected_retirement_receipt_sha256.lower()):
            raise SchedulerRunnerError("CONTROLLER_REBIND_TRANSACTION_CONFLICT")
    audit = txdir / "audit"
    audit.mkdir(parents=True, exist_ok=True)
    old_binding_archive = audit / "old_task_binding.json"
    if current.get("request_id") == old_request_id:
        old_binding_raw = current_raw
    elif old_binding_archive.is_file():
        old_binding_raw = old_binding_archive.read_bytes()
    else:
        raise SchedulerRunnerError("CONTROLLER_REBIND_OLD_BINDING_AUDIT_MISSING")
    if _sha_bytes(old_binding_raw) != old_task_sha:
        raise SchedulerRunnerError("CONTROLLER_REBIND_OLD_BINDING_AUDIT_MISMATCH")
    if not old_binding_archive.exists():
        _write_exclusive_bytes(old_binding_archive, old_binding_raw)
    for name, raw in (("retirement_receipt.json", receipt_raw),
                      ("old_status.json", status_raw),
                      ("queue_state_snapshot.json", queue_state_raw)):
        target = audit / name
        if target.exists() and _sha(target) != _sha_bytes(raw):
            raise SchedulerRunnerError("CONTROLLER_REBIND_AUDIT_ARTIFACT_CONFLICT")
        if not target.exists():
            _write_exclusive_bytes(target, raw)
    if old_xml_enabled is not None and not (audit / "old_task.xml").exists():
        _write_exclusive_bytes(audit / "old_task.xml", current_xml.encode("utf-8"))
    if old_xml_enabled is not None:
        task_audit_path = audit / "old_task_scheduler_info.json"
        task_audit = _controller_task_scheduler_audit_record(
            current_xml, task, request_id=old_request_id,
            manifest_sha256=old_info["manifest_sha256"],
            binding_sha256=old_task_sha, transaction_id=txid)
        if task_audit_path.exists():
            prior = _read_json(task_audit_path)
            stable_keys = ("schema", "transaction_id", "task_name", "request_id",
                           "manifest_sha256", "task_binding_sha256", "recognized_contract",
                           "scheduler_execution_time_limit")
            if any(prior.get(key) != task_audit.get(key) for key in stable_keys):
                raise SchedulerRunnerError("CONTROLLER_REBIND_TASK_AUDIT_CONFLICT")
        else:
            _create_exclusive_json(task_audit_path, task_audit)
    if journal.get("phase") != "COMPLETE":
        journal = _journal_rebind_phase(journal_path, journal, "PREPARED")
    new_xml_enabled_true = controller_task_xml(
        script_path=new_info["controller_script_path"], manifest_path=new_request_path,
        manifest_sha256=new_info["manifest_sha256"], request_id=new_request_id,
        principal=principal)
    new_xml_disabled = new_xml_enabled_true.replace("<Enabled>true</Enabled>",
                                                     "<Enabled>false</Enabled>")
    if new_xml_disabled == new_xml_enabled_true:
        raise SchedulerRunnerError("CONTROLLER_REBIND_DISABLED_TASK_XML_INVALID")
    create_task_fn = create_task_fn or _write_controller_task_xml
    set_enabled_fn = set_enabled_fn or _set_controller_task_enabled
    if current.get("request_id") == old_request_id:
        if old_xml_enabled is not None:
            if old_xml_enabled:
                set_enabled_fn(False)
                task = task_info_fn(CONTROLLER_TASK_NAME)
                if _task_state_value(task) in ("running", "queued"):
                    raise SchedulerRunnerError("CONTROLLER_REBIND_TASK_BECAME_ACTIVE")
                current_xml = xml_query_fn(CONTROLLER_TASK_NAME)
                task = task_info_fn(CONTROLLER_TASK_NAME)
                old_xml_enabled = _controller_predecessor_task_xml_matches(
                    current_xml, old_info, old_request_id, current, root, principal, task)
            if old_xml_enabled is not False:
                raise SchedulerRunnerError("CONTROLLER_REBIND_OLD_TASK_NOT_DISABLED")
            journal = _journal_rebind_phase(journal_path, journal, "OLD_TASK_DISABLED")
        elif journal.get("phase") not in ("OLD_TASK_DISABLED", "NEW_TASK_DISABLED"):
            raise SchedulerRunnerError("CONTROLLER_REBIND_TASK_DEFINITION_MISMATCH")
        if new_xml_enabled is None:
            if old_xml_enabled is None:
                raise SchedulerRunnerError("CONTROLLER_REBIND_TASK_DEFINITION_MISMATCH")
            create_task_fn(new_xml_disabled, force=True)
        elif new_xml_enabled:
            raise SchedulerRunnerError("CONTROLLER_REBIND_NEW_TASK_NOT_DISABLED")
        current_xml = xml_query_fn(CONTROLLER_TASK_NAME)
        task = task_info_fn(CONTROLLER_TASK_NAME)
        if _task_state_value(task) in ("running", "queued"):
            raise SchedulerRunnerError("CONTROLLER_REBIND_TASK_BECAME_ACTIVE")
        _controller_task_xml_matches(
            current_xml, new_info, new_request_id, new_request_binding, root, principal,
            task_info=task, expected_enabled=False)
        if _controller_task_is_enabled(current_xml):
            raise SchedulerRunnerError("CONTROLLER_REBIND_NEW_TASK_NOT_DISABLED")
        if journal.get("phase") == "OLD_TASK_DISABLED":
            journal = _journal_rebind_phase(journal_path, journal, "NEW_TASK_DISABLED")
        _assert_runner_slot_free(root, task_info_fn)
        _assert_no_controller_or_solver_processes(process_fn(), old_request_id)
        if (_sha(new_info["manifest_path"]) != new_info["manifest_sha256"]
                or _sha(new_info["controller_script_path"]) !=
                   new_info["manifest"]["controller_script_sha256"].lower()
                or _sha(new_info["queue_manifest_path"]) !=
                   new_info["manifest"]["queue_manifest_sha256"].lower()
                or _sha(old_info["status_path"]) != _sha_bytes(status_raw)
                or _sha(_path_within(receipt["queue_state_path"], coupling_root)) !=
                   receipt["queue_state_sha256"].lower()
                or _sha(_path_within(receipt["owner_decision_path"], coupling_root)) !=
                   receipt["owner_decision_sha256"].lower()):
            raise SchedulerRunnerError("CONTROLLER_REBIND_PREFLIGHT_DRIFT")
        _write_controller_task_binding(root, {
            "request_id": new_request_id, "controller_manifest_sha256": new_info["manifest_sha256"],
            "controller_script_sha256": _sha(new_info["controller_script_path"]),
            "queue_manifest_sha256": _sha(new_info["queue_manifest_path"]),
            "queue_id": new_info["manifest"]["queue_id"], "resume_generation": 0,
            "resume_receipt_path": None, "resume_receipt_sha256": None, "updated_utc": _now(),
        })
        journal = _journal_rebind_phase(journal_path, journal, "BINDING_SWITCHED")
    current_xml = xml_query_fn(CONTROLLER_TASK_NAME)
    task = task_info_fn(CONTROLLER_TASK_NAME)
    _controller_task_xml_matches(
        current_xml, new_info, new_request_id, new_request_binding, root, principal,
        task_info=task, expected_enabled=(_task_state_value(task) == "ready"))
    if not _controller_task_is_enabled(current_xml):
        set_enabled_fn(True)
        current_xml = xml_query_fn(CONTROLLER_TASK_NAME)
        task = task_info_fn(CONTROLLER_TASK_NAME)
    _controller_task_xml_matches(
        current_xml, new_info, new_request_id, new_request_binding, root, principal,
        task_info=task, expected_enabled=True)
    if not _controller_task_is_enabled(current_xml):
        raise SchedulerRunnerError("CONTROLLER_REBIND_TASK_ENABLE_FAILED")
    if _task_state_value(task) in ("running", "queued"):
        raise SchedulerRunnerError("CONTROLLER_REBIND_MUST_NOT_START_TASK")
    current_binding = _read_controller_task_binding(root)
    if (current_binding.get("request_id") != new_request_id
            or current_binding.get("controller_manifest_sha256") != new_info["manifest_sha256"]):
        raise SchedulerRunnerError("CONTROLLER_REBIND_NEW_BINDING_VERIFY_FAILED")
    if journal.get("phase") == "NEW_TASK_DISABLED":
        if current_binding.get("request_id") != new_request_id:
            raise SchedulerRunnerError("CONTROLLER_REBIND_BINDING_SWITCH_UNRECORDED")
        journal = _journal_rebind_phase(journal_path, journal, "BINDING_SWITCHED")
    was_complete = journal.get("phase") == "COMPLETE"
    _journal_rebind_phase(journal_path, journal, "COMPLETE")
    return {"result": "ALREADY_REBOUND" if was_complete else "REBOUND",
            "transaction_id": txid, "old_request_id": old_request_id,
            "request_id": new_request_id, "task_name": CONTROLLER_TASK_NAME,
            "task_enabled": True, "started": False, "solver_entries": 0,
            "automatic_replays": 0}


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
    rebind_controller = sub.add_parser("retire-rebind-controller-task")
    rebind_controller.add_argument("old_request_id")
    rebind_controller.add_argument("new_controller_manifest")
    rebind_controller.add_argument("retirement_receipt")
    rebind_controller.add_argument("old_task_binding_sha256")
    rebind_controller.add_argument("new_manifest_sha256")
    rebind_controller.add_argument("retirement_receipt_sha256")
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
        elif args.command == "retire-rebind-controller-task":
            result = retire_rebind_controller_task(
                args.old_request_id, args.new_controller_manifest, args.retirement_receipt,
                expected_old_task_binding_sha256=args.old_task_binding_sha256,
                expected_new_manifest_sha256=args.new_manifest_sha256,
                expected_retirement_receipt_sha256=args.retirement_receipt_sha256)
        else:
            result = query_one(args.request_id)
    except Exception as exc:
        print(json.dumps({"result": "ERROR", "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
