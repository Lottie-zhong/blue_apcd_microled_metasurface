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
TASK_PYTHON = r"N:\anaconda_envs\RCP_LCP\python.exe"
TASK_EXECUTION_LIMIT = "PT72H"
OWNER_ACCOUNT = "DELL"
EXPECTED_WHOAMI = "desktop-nne313k\\dell"
PRODUCTION_ROOT = Path(r"D:\apcd_runtime\gpu_production_runner_v1")
REQUEST_ROOT = PRODUCTION_ROOT / "requests" / "scheduled_run_one_v1"
TASK_LOCK = PRODUCTION_ROOT / "scheduler_worker_v1.lock"
REQUEST_ID_RE = re.compile(r"^[0-9a-f]{32}$")


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


def validate_task_definition_xml(xml_text, *, expected_script=None, expected_principal=None):
    try:
        root = ET.fromstring(xml_text.lstrip("\ufeff"))
    except ET.ParseError as exc:
        raise SchedulerRunnerError("SCHEDULER_TASK_XML_INVALID") from exc
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
    if expected_arg not in args or "worker-once" not in args:
        raise SchedulerRunnerError("SCHEDULER_TASK_ACTION_MISMATCH")
    return {
        "task_name": TASK_NAME,
        "principal": account,
        "logon_type": logon_types[0].text,
        "run_level": run_level,
        "multiple_instances": multiple[0].text,
        "execution_time_limit": limit_value,
        "automatic_restart": False,
        "command": commands[0].text,
        "arguments": arguments[0].text,
    }


def _query_task_xml():
    if os.name != "nt":
        raise SchedulerRunnerError("SCHEDULER_TASK_REQUIRES_WINDOWS")
    proc = subprocess.run(
        ["schtasks.exe", "/Query", "/TN", TASK_NAME, "/XML"],
        text=True, capture_output=True, encoding="utf-8", errors="replace", timeout=30, check=False,
    )
    if proc.returncode != 0:
        raise SchedulerRunnerError("SCHEDULER_WORKER_TASK_NOT_INSTALLED:" + proc.stderr.strip()[:400])
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


def _task_info():
    if os.name != "nt":
        return {"state": "UNAVAILABLE", "last_task_result": None}
    ps = (
        "$ErrorActionPreference='Stop'; "
        "$t=Get-ScheduledTask -TaskName 'APCD_GPU_RUNNER_V1_SINGLE_CASE_WORKER'; "
        "$i=Get-ScheduledTaskInfo -TaskName 'APCD_GPU_RUNNER_V1_SINGLE_CASE_WORKER'; "
        "[pscustomobject]@{State=[string]$t.State;LastTaskResult=$i.LastTaskResult; "
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


def _start_worker_task():
    verify_worker_task()
    proc = subprocess.run(
        ["schtasks.exe", "/Run", "/TN", TASK_NAME],
        text=True, capture_output=True, encoding="utf-8", errors="replace", timeout=30, check=False,
    )
    if proc.returncode != 0:
        raise SchedulerRunnerError("SCHEDULER_WORKER_START_FAILED:" + proc.stderr.strip()[:400])


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
    args = parser.parse_args(argv)
    try:
        if args.command == "install-task":
            result = install_worker_task()
        elif args.command == "worker-once":
            result = task_worker_once()
        elif args.command == "submit-one":
            result = submit_one(args.case_manifest)
        else:
            result = query_one(args.request_id)
    except Exception as exc:
        print(json.dumps({"result": "ERROR", "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
