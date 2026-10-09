import hashlib
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import task_scheduler_v1 as scheduler


def _fake_adapter(tmp_path):
    adapter_path = tmp_path / "adapter.py"
    adapter_path.write_text("# pinned fake adapter\n", encoding="utf-8")

    def read_manifest(path):
        return json.loads(Path(path).read_text(encoding="utf-8")), None

    class FakeNativeAdapter:
        def __init__(self, contract_path, *, gpu_resource_name):
            self.contract_path = contract_path
            self.gpu_resource_name = gpu_resource_name

    return SimpleNamespace(__file__=str(adapter_path), read_cli_manifest=read_manifest,
                           NativeAdapter=FakeNativeAdapter, run_cli=Mock())


@pytest.fixture(autouse=True)
def _set_gpu_resource_name(monkeypatch):
    monkeypatch.setenv("APCD_GPU_RESOURCE_NAME", "GPU license audit")


def _manifest(tmp_path):
    path = tmp_path / "case.json"
    path.write_text(json.dumps({"case_id": "TEST_CASE", "attempt_id": "attempt_001",
                                "run_id": "RUN_TEST_001"}), encoding="utf-8")
    return path


def test_request_identity_is_idempotent_and_manifest_hash_bound(tmp_path):
    adapter = _fake_adapter(tmp_path)
    manifest = _manifest(tmp_path)
    first = scheduler.submit_one(manifest, root=tmp_path / "runner", adapter_module=adapter, start_task=False)
    second = scheduler.submit_one(manifest, root=tmp_path / "runner", adapter_module=adapter, start_task=False)
    assert first["request_id"] == second["request_id"]
    assert first["request_sha256"] == second["request_sha256"]
    assert len(list((tmp_path / "runner" / "requests" / "scheduled_run_one_v1").iterdir())) == 1
    request = scheduler._read_and_verify_request(Path(first["request_path"]))
    assert request["identity"] == {"case_id": "TEST_CASE", "attempt_id": "attempt_001", "run_id": "RUN_TEST_001"}
    assert request["gpu_resource_name"] == "GPU license audit"



def test_gpu_resource_name_is_required_and_validated_before_request_creation(tmp_path, monkeypatch):
    adapter = _fake_adapter(tmp_path)
    manifest = _manifest(tmp_path)
    root = tmp_path / "runner"
    monkeypatch.delenv("APCD_GPU_RESOURCE_NAME")
    with pytest.raises(scheduler.SchedulerRunnerError, match="GPU_RESOURCE_NAME_REQUIRED"):
        scheduler.submit_one(manifest, root=root, adapter_module=adapter, start_task=False)
    monkeypatch.setenv("APCD_GPU_RESOURCE_NAME", "GPU" + chr(10) + "license")
    with pytest.raises(scheduler.SchedulerRunnerError, match="GPU_RESOURCE_NAME_INVALID"):
        scheduler.submit_one(manifest, root=root, adapter_module=adapter, start_task=False)
    assert not root.exists()


def test_resource_name_change_cannot_create_a_second_request_for_same_run(tmp_path, monkeypatch):
    adapter = _fake_adapter(tmp_path)
    manifest = _manifest(tmp_path)
    root = tmp_path / "runner"
    first = scheduler.submit_one(manifest, root=root, adapter_module=adapter, start_task=False)
    monkeypatch.setenv("APCD_GPU_RESOURCE_NAME", "another-gpu")
    with pytest.raises(scheduler.SchedulerRunnerError, match="SCHEDULED_REQUEST_ID_COLLISION"):
        scheduler.submit_one(manifest, root=root, adapter_module=adapter, start_task=False)
    dirs = list((root / "requests" / "scheduled_run_one_v1").iterdir())
    assert len(dirs) == 1
    assert scheduler._read_and_verify_request(Path(first["request_path"]))["gpu_resource_name"] == "GPU license audit"


def test_worker_persists_result_without_submitter_and_is_single_consumption(tmp_path):
    adapter = _fake_adapter(tmp_path)
    manifest = _manifest(tmp_path)
    root = tmp_path / "runner"
    request = scheduler.submit_one(manifest, root=root, adapter_module=adapter, start_task=False)
    bound_adapters = []
    adapter.run_cli.side_effect = lambda path, *, adapter_factory: (
        bound_adapters.append(adapter_factory("contract.json")) or
        {"status": {"state": "DONE", "solver_entered": True, "solver_invocations": 1}})
    result = scheduler.task_worker_once(root=root, adapter_module=adapter)
    assert result["result"] == "RECORDED"
    adapter.run_cli.assert_called_once()
    assert adapter.run_cli.call_args.args == (str(manifest.resolve()),)
    assert adapter.run_cli.call_args.kwargs.keys() == {"adapter_factory"}
    assert bound_adapters[0].contract_path == "contract.json"
    assert bound_adapters[0].gpu_resource_name == "GPU license audit"
    state = scheduler.query_one(request["request_id"], root=root, task_info_fn=lambda: {"state": "Ready"})
    assert state["state"] == "TERMINAL"
    assert state["result"]["exit_code"] == 0
    assert state["result"]["result"]["status"]["solver_invocations"] == 1
    assert scheduler.task_worker_once(root=root, adapter_module=adapter)["result"] == "NO_PENDING_REQUEST"
    assert not (root / scheduler.TASK_LOCK.name).exists()


def test_concurrent_worker_invocation_cannot_create_a_second_owner(tmp_path):
    adapter = _fake_adapter(tmp_path)
    manifest = _manifest(tmp_path)
    root = tmp_path / "runner"
    request = scheduler.submit_one(manifest, root=root, adapter_module=adapter, start_task=False)
    entered = threading.Event()
    release = threading.Event()

    def slow_worker(_manifest_path):
        entered.set()
        assert release.wait(5)
        return {"status": {"state": "DONE", "solver_entered": True, "solver_invocations": 1}}

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(scheduler.task_worker_once, root=root, run_cli=slow_worker, adapter_module=adapter)
        assert entered.wait(5)
        second = scheduler.task_worker_once(root=root, run_cli=slow_worker, adapter_module=adapter)
        release.set()
        completed = first.result(timeout=10)
    assert second["result"] == "NO_PENDING_REQUEST"
    assert completed["result"] == "RECORDED"
    state = scheduler.query_one(request["request_id"], root=root, task_info_fn=lambda: {"state": "Ready"})
    assert state["state"] == "TERMINAL"
    assert state["result"]["result"]["status"]["solver_invocations"] == 1


def test_manifest_change_after_submission_fails_closed_before_runner_entry(tmp_path):
    adapter = _fake_adapter(tmp_path)
    manifest = _manifest(tmp_path)
    root = tmp_path / "runner"
    request = scheduler.submit_one(manifest, root=root, adapter_module=adapter, start_task=False)
    manifest.write_text(manifest.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(scheduler.SchedulerRunnerError, match="MANIFEST_HASH_CHANGED"):
        scheduler.task_worker_once(root=root, adapter_module=adapter)
    adapter.run_cli.assert_not_called()
    assert not (Path(request["request_path"]).parent / "result.json").exists()


def test_claimed_postentry_without_result_requires_recovery_not_replay(tmp_path):
    adapter = _fake_adapter(tmp_path)
    manifest = _manifest(tmp_path)
    root = tmp_path / "runner"
    request = scheduler.submit_one(manifest, root=root, adapter_module=adapter, start_task=False)
    request_dir = Path(request["request_path"]).parent
    (request_dir / "worker_claim.json").write_text("{}", encoding="utf-8")
    status_path = root / "runs" / "TEST_CASE" / "attempt_001" / "RUN_TEST_001" / "status.json"
    status_path.parent.mkdir(parents=True)
    status_path.write_text(json.dumps({"case_id": "TEST_CASE", "attempt_id": "attempt_001",
                                       "run_id": "RUN_TEST_001", "state": "SOLVER_ENTERED",
                                       "solver_entered": True, "solver_invocations": 1}), encoding="utf-8")
    state = scheduler.query_one(request["request_id"], root=root, task_info_fn=lambda: {"state": "Ready"})
    assert state["state"] == "NEEDS_POSTENTRY_RECOVERY"
    adapter.run_cli.assert_not_called()


def _task_xml(**settings):
    logon = settings.get("logon", "InteractiveToken")
    multiple = settings.get("multiple", "IgnoreNew")
    limit = settings.get("limit", "PT0S")
    restart = settings.get("restart", "")
    action = settings.get("action", f'"{scheduler._task_script_path()}" --worker-once')
    command = settings.get("command", scheduler.TASK_PYTHON)
    principal = settings.get("principal", "desktop-nne313k\\dell")
    return f'''<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"><Principals><Principal><UserId>{principal}</UserId><LogonType>{logon}</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals><Settings><MultipleInstancesPolicy>{multiple}</MultipleInstancesPolicy><ExecutionTimeLimit>{limit}</ExecutionTimeLimit>{restart}</Settings><Actions><Exec><Command>{command}</Command><Arguments>{action}</Arguments></Exec></Actions></Task>'''


def test_task_definition_pins_interactive_owner_ignore_new_unlimited_no_restart(tmp_path):
    result = scheduler.validate_task_definition_xml(
        _task_xml(), expected_script=scheduler._task_script_path(),
        expected_principal="desktop-nne313k\\dell")
    assert result["multiple_instances"] == "IgnoreNew"
    assert result["execution_time_limit"] == "PT0S"
    assert result["automatic_restart"] is False
    assert result["logon_type"] == "InteractiveToken"


def test_generated_worker_task_definition_matches_the_live_owner_and_is_unlimited(tmp_path):
    xml = scheduler.worker_task_xml(script_path=str(scheduler._task_script_path()))
    result = scheduler.validate_task_definition_xml(
        xml, expected_script=scheduler._task_script_path(), expected_principal="dell")
    assert result["principal"] == "dell"
    assert result["multiple_instances"] == "IgnoreNew"
    assert result["execution_time_limit"] == "PT0S"


def test_install_worker_task_upgrades_exact_idle_72h_definition_to_unlimited(tmp_path, monkeypatch):
    test_sid = "S-1-5-21-111-222-333-1001"
    old_xml = scheduler.worker_task_xml(script_path=str(scheduler._task_script_path())).replace(
        "<UserId>DELL</UserId>", "<UserId>" + test_sid + "</UserId>").replace(
        "<ExecutionTimeLimit>PT0S</ExecutionTimeLimit>",
        "<ExecutionTimeLimit>PT72H</ExecutionTimeLimit>")
    current = {"xml": old_xml, "limit": "PT72H"}
    calls = []

    class Proc:
        def __init__(self, returncode=0, stdout="", stderr=""):
            self.returncode, self.stdout, self.stderr = returncode, stdout, stderr

    def fake_run(args, **kwargs):
        calls.append(list(args))
        if args[0].lower().endswith("whoami.exe"):
            if len(args) > 1 and args[1] == "/user":
                return Proc(stdout='"DELL","' + test_sid + '"\n')
            return Proc(stdout=scheduler.EXPECTED_WHOAMI + "\n")
        if args[:3] == ["schtasks.exe", "/Query", "/TN"]:
            return Proc(stdout=current["xml"])
        raise AssertionError(args)

    def task_info(task_name=scheduler.TASK_NAME):
        return {"State": "Ready", "UserId": "DELL", "LogonType": 3, "RunLevel": 0,
                "MultipleInstances": 2, "ExecutionTimeLimit": current["limit"], "RestartCount": 0}

    def write_task(xml_text, *, force=False):
        assert force is True
        current["xml"] = xml_text.replace("<UserId>DELL</UserId>",
                                          "<UserId>" + test_sid + "</UserId>")
        current["limit"] = "PT0S"

    monkeypatch.setattr(scheduler.subprocess, "run", fake_run)
    monkeypatch.setattr(scheduler, "_task_info", task_info)
    monkeypatch.setattr(scheduler, "_assert_runner_slot_free", lambda *_args: None)
    monkeypatch.setattr(scheduler, "_controller_process_inventory", lambda: [])
    monkeypatch.setattr(scheduler, "_assert_no_controller_or_solver_processes", lambda *_args: None)
    monkeypatch.setattr(scheduler, "_write_worker_task_xml", write_task)

    result = scheduler.install_worker_task()
    assert result["result"] == "UPDATED_EXECUTION_TIME_LIMIT"
    assert result["execution_time_limit"] == "PT0S"
    assert "<ExecutionTimeLimit>PT0S</ExecutionTimeLimit>" in current["xml"]
    assert any(args[-1] == "/XML" for args in calls)


def test_scheduler_export_defaults_are_normalized_and_checked_from_live_settings(tmp_path):
    xml = _task_xml().replace("<RunLevel>LeastPrivilege</RunLevel>", "")
    xml = xml.replace("<ExecutionTimeLimit>PT0S</ExecutionTimeLimit>", "")
    result = scheduler.validate_task_definition_xml(
        xml, expected_script=scheduler._task_script_path(),
        expected_principal="desktop-nne313k\\dell",
        expected_execution_time_limit=scheduler.LEGACY_TASK_EXECUTION_LIMIT)
    assert result["run_level"] == "LeastPrivilege"
    assert result["execution_time_limit"] == "PT72H"


@pytest.mark.parametrize("changes,reason", [
    ({"multiple": "Parallel"}, "MULTIPLE_INSTANCE_POLICY"),
    ({"limit": "PT48H"}, "EXECUTION_TIME_LIMIT"),
    ({"limit": "PT72H"}, "EXECUTION_TIME_LIMIT"),
    ({"restart": "<RestartOnFailure><Interval>PT1M</Interval><Count>2</Count></RestartOnFailure>"}, "AUTOMATIC_RESTART"),
    ({"logon": "Password"}, "LOGON_TYPE"),
    ({"principal": "OTHER\\user"}, "WRONG_PRINCIPAL"),
    ({"action": '"C:\\temp\\wrong.py" --worker-once'}, "ACTION_MISMATCH"),
])
def test_task_definition_rejects_drift(tmp_path, changes, reason):
    with pytest.raises(scheduler.SchedulerRunnerError, match=reason):
        scheduler.validate_task_definition_xml(
            _task_xml(**changes), expected_script=scheduler._task_script_path(),
            expected_principal="desktop-nne313k\\dell")
