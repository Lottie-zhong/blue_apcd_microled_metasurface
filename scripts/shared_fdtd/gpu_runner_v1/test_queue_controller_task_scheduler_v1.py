import hashlib
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import task_scheduler_v1 as scheduler  # noqa: E402


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _bundle(tmp_path, *, script_source=None, queue_ids=None):
    coupling = tmp_path / "coupling"
    script = coupling / "scripts" / "coupling_ml" / "k6_v2_pipeline" / "serial_queue.py"
    script.parent.mkdir(parents=True)
    script.write_text(script_source or (
        'CONTROLLER_PROTOCOL = "' + scheduler.CONTROLLER_PROTOCOL + '"\n'
        'parser.add_argument("--runner-controller-manifest")\n'
        'parser.add_argument("--runner-controller-manifest-sha256")\n'
        'parser.add_argument("--runner-controller-request-id")\n'
        'parser.add_argument("--runner-resume-receipt")\n'
        'parser.add_argument("--runner-resume-receipt-sha256")\n'
    ), encoding="utf-8")
    reports = coupling / "reports" / "queue"
    reports.mkdir(parents=True)
    queue_path = reports / "queue_manifest.json"
    queue_path.write_text(json.dumps({
        "schema": "SYNTHETIC_QUEUE_V1",
        "ordered_case_ids": queue_ids or ["CASE_A", "CASE_B", "CASE_C"],
    }, sort_keys=True), encoding="utf-8")
    status_path = reports / "controller_status.json"
    manifest_path = reports / "controller_manifest.json"
    manifest = {
        "schema": scheduler.SCHEMA_CONTROLLER_MANIFEST,
        "controller_run_id": "controller-run-001",
        "queue_id": "queue-test-001",
        "controller_script_path": str(script),
        "controller_script_sha256": _sha(script),
        "queue_manifest_path": str(queue_path),
        "queue_manifest_sha256": _sha(queue_path),
        "case_ids": ["CASE_A", "CASE_B"],
        "max_cases": 2,
        "max_concurrent_cases": 1,
        "per_case_max_solver_entries": 1,
        "post_entry_automatic_replays": 0,
        "startup_reconcile_before_dispatch": True,
        "truth_before_next_case": True,
        "controller_protocol": scheduler.CONTROLLER_PROTOCOL,
        "status_path": str(status_path),
    }
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return {
        "coupling": coupling,
        "script": script,
        "queue_path": queue_path,
        "status_path": status_path,
        "manifest_path": manifest_path,
        "manifest": manifest,
    }


def _save_manifest(bundle, changes=None):
    manifest = dict(bundle["manifest"])
    if changes:
        manifest.update(changes)
    path = bundle["manifest_path"]
    path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return path


def _fake_scheduler():
    state = {
        "xml": None,
        "task_state": "Ready",
        "execution_time_limit": scheduler.TASK_EXECUTION_LIMIT,
        "create_calls": [],
        "start_calls": [],
    }

    def xml_query(name):
        assert name == scheduler.CONTROLLER_TASK_NAME
        if state["xml"] is None:
            raise scheduler.SchedulerRunnerError("SCHEDULER_CONTROLLER_TASK_NOT_INSTALLED")
        return state["xml"]

    def create_task(xml, force=False):
        state["xml"] = xml
        match = re.search(r"<ExecutionTimeLimit>([^<]+)</ExecutionTimeLimit>", xml)
        if match:
            state["execution_time_limit"] = match.group(1)
        state["task_state"] = "Disabled" if "<Enabled>false</Enabled>" in xml else "Ready"
        state["create_calls"].append({"xml": xml, "force": force})

    def task_info(name):
        assert name == scheduler.CONTROLLER_TASK_NAME
        return {
            "state": state["task_state"],
            "UserId": "DELL",
            "LogonType": 3,
            "RunLevel": 0,
            "MultipleInstances": 2,
            "ExecutionTimeLimit": state["execution_time_limit"],
            "RestartCount": 0,
            "LastTaskResult": 0,
        }

    def start(name):
        assert name == scheduler.CONTROLLER_TASK_NAME
        state["start_calls"].append(name)

    return state, xml_query, create_task, task_info, start


def _prepare_and_install(bundle, runner_root):
    prepared = scheduler.prepare_controller_task(bundle["manifest_path"], root=runner_root,
        coupling_root=bundle["coupling"], install_task=False)
    state, xml_query, create_task, task_info, start = _fake_scheduler()
    installed = scheduler.install_controller_task(prepared["request_id"], root=runner_root,
        coupling_root=bundle["coupling"], xml_query_fn=xml_query, task_info_fn=task_info,
        create_task_fn=create_task, expected_principal="dell")
    assert installed["result"] == "INSTALLED"
    return prepared, state, xml_query, create_task, task_info, start


def test_valid_bounded_manifest_is_hash_bound_and_staged_without_start(tmp_path):
    bundle = _bundle(tmp_path)
    root = tmp_path / "runner"
    prepared = scheduler.prepare_controller_task(bundle["manifest_path"], root=root,
        coupling_root=bundle["coupling"], install_task=False)
    request_dir, request_path, binding_path, claim_path = scheduler._controller_request_files(
        root, prepared["request_id"])
    assert request_path.read_bytes() == bundle["manifest_path"].read_bytes()
    assert _sha(request_path) == prepared["request_manifest_sha256"]
    assert prepared["case_ids"] == ["CASE_A", "CASE_B"]
    assert prepared["max_cases"] == 2
    assert prepared["max_concurrent_cases"] == 1
    assert prepared["automatic_replays"] == 0
    assert binding_path.is_file()
    assert not claim_path.exists()
    assert not (root / "scheduler_controller_v1" / "task_binding.json").exists()


@pytest.mark.parametrize("changes,error", [
    ({"max_cases": 3}, "CONTROLLER_CASE_BOUND_INVALID"),
    ({"max_concurrent_cases": 2}, "CONTROLLER_CONCURRENCY_MUST_BE_ONE"),
    ({"per_case_max_solver_entries": 2}, "CONTROLLER_PER_CASE_ENTRY_BUDGET_INVALID"),
    ({"post_entry_automatic_replays": 1}, "CONTROLLER_AUTOMATIC_REPLAY_FORBIDDEN"),
    ({"startup_reconcile_before_dispatch": False}, "CONTROLLER_RECOVERY_OR_TRUTH_BARRIER_REQUIRED"),
    ({"truth_before_next_case": False}, "CONTROLLER_RECOVERY_OR_TRUTH_BARRIER_REQUIRED"),
    ({"case_ids": ["CASE_A", "NOT_AUTHORIZED"]}, "CONTROLLER_CASES_OUTSIDE_QUEUE_MANIFEST"),
])
def test_controller_manifest_rejects_unbounded_or_unauthorized_requests(tmp_path, changes, error):
    bundle = _bundle(tmp_path)
    path = _save_manifest(bundle, changes)
    with pytest.raises(scheduler.SchedulerRunnerError, match=error):
        scheduler._controller_manifest(path, coupling_root=bundle["coupling"])


def test_controller_manifest_rejects_script_queue_hash_and_protocol_drift(tmp_path):
    bundle = _bundle(tmp_path)
    with pytest.raises(scheduler.SchedulerRunnerError, match="ENTRYPOINT_HASH_MISMATCH"):
        scheduler._controller_manifest(_save_manifest(bundle, {
            "controller_script_sha256": "0" * 64}), coupling_root=bundle["coupling"])
    bundle = _bundle(tmp_path / "queue_hash")
    with pytest.raises(scheduler.SchedulerRunnerError, match="QUEUE_MANIFEST_HASH_MISMATCH"):
        scheduler._controller_manifest(_save_manifest(bundle, {
            "queue_manifest_sha256": "0" * 64}), coupling_root=bundle["coupling"])
    bundle = _bundle(tmp_path / "protocol", script_source="print('legacy unbounded execute')\n")
    manifest = dict(bundle["manifest"], controller_script_sha256=_sha(bundle["script"]))
    bundle["manifest_path"].write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(scheduler.SchedulerRunnerError, match="ENTRYPOINT_PROTOCOL_UNSUPPORTED"):
        scheduler._controller_manifest(bundle["manifest_path"], coupling_root=bundle["coupling"])


def test_controller_task_calls_coupling_directly_with_manual_single_instance_policy(tmp_path):
    bundle = _bundle(tmp_path)
    request = scheduler.prepare_controller_task(bundle["manifest_path"], root=tmp_path / "runner",
        coupling_root=bundle["coupling"], install_task=False)
    request_path = Path(request["request_manifest_path"])
    xml = scheduler.controller_task_xml(script_path=bundle["script"], manifest_path=request_path,
        manifest_sha256=request["request_manifest_sha256"], request_id=request["request_id"])
    result = scheduler.validate_task_definition_xml(xml, expected_script=bundle["script"],
        expected_principal="dell", task_name=scheduler.CONTROLLER_TASK_NAME,
        expected_argument="--runner-controller-manifest", expected_manifest=request_path,
        expected_manifest_sha256=request["request_manifest_sha256"],
        expected_request_id=request["request_id"], require_no_triggers=True)
    assert result["multiple_instances"] == "IgnoreNew"
    assert result["execution_time_limit"] == "PT0S"
    assert result["automatic_restart"] is False
    assert result["task_name"] == scheduler.CONTROLLER_TASK_NAME
    assert "task_scheduler_v1.py" not in result["arguments"].lower()
    assert "<Triggers/>" in xml
    for trigger in ("LogonTrigger", "TimeTrigger"):
        bad_xml = xml.replace("<Triggers/>", "<Triggers><" + trigger + "/></Triggers>")
        with pytest.raises(scheduler.SchedulerRunnerError, match="TRIGGERS_FORBIDDEN"):
            scheduler.validate_task_definition_xml(bad_xml, expected_script=bundle["script"],
                expected_principal="dell", task_name=scheduler.CONTROLLER_TASK_NAME,
                expected_argument="--runner-controller-manifest", expected_manifest=request_path,
                expected_manifest_sha256=request["request_manifest_sha256"],
                expected_request_id=request["request_id"], require_no_triggers=True)


def test_install_and_start_are_singleton_and_duplicate_start_is_idempotent(tmp_path):
    bundle = _bundle(tmp_path)
    root = tmp_path / "runner"
    prepared, state, xml_query, create_task, task_info, start = _prepare_and_install(bundle, root)
    again = scheduler.install_controller_task(prepared["request_id"], root=root,
        coupling_root=bundle["coupling"], xml_query_fn=xml_query, task_info_fn=task_info,
        create_task_fn=create_task, expected_principal="dell")
    assert again["result"] == "ALREADY_INSTALLED"
    request_two = _save_manifest(bundle, {"controller_run_id": "controller-run-002"})
    prepared_two = scheduler.prepare_controller_task(request_two, root=root,
        coupling_root=bundle["coupling"], install_task=False)
    with pytest.raises(scheduler.SchedulerRunnerError, match="ALREADY_BOUND"):
        scheduler.install_controller_task(prepared_two["request_id"], root=root,
            coupling_root=bundle["coupling"], xml_query_fn=xml_query, task_info_fn=task_info,
            create_task_fn=create_task, expected_principal="dell")
    started = scheduler.start_controller_task(prepared["request_id"], root=root,
        coupling_root=bundle["coupling"], xml_query_fn=xml_query, task_info_fn=task_info,
        start_fn=start, expected_principal="dell")
    repeated = scheduler.start_controller_task(prepared["request_id"], root=root,
        coupling_root=bundle["coupling"], xml_query_fn=xml_query, task_info_fn=task_info,
        start_fn=start, expected_principal="dell")
    assert started["result"] == "START_REQUESTED"
    assert repeated["result"] == "START_ALREADY_REQUESTED_RECONCILE_BEFORE_RESUME"
    assert state["start_calls"] == [scheduler.CONTROLLER_TASK_NAME]


def test_concurrent_controller_starts_create_one_owner_and_one_task_run(tmp_path):
    bundle = _bundle(tmp_path)
    root = tmp_path / "runner"
    prepared, state, xml_query, _create_task, task_info, start = _prepare_and_install(bundle, root)
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda _: scheduler.start_controller_task(
            prepared["request_id"], root=root, coupling_root=bundle["coupling"],
            xml_query_fn=xml_query, task_info_fn=task_info, start_fn=start,
            expected_principal="dell"), range(6)))
    assert sum(x["result"] == "START_REQUESTED" for x in results) == 1
    assert len(state["start_calls"]) == 1


def test_install_controller_uses_verified_sid_as_task_principal(tmp_path):
    bundle = _bundle(tmp_path)
    root = tmp_path / "runner"
    prepared = scheduler.prepare_controller_task(bundle["manifest_path"], root=root,
        coupling_root=bundle["coupling"], install_task=False)
    state, xml_query, create_task, task_info, _start = _fake_scheduler()
    sid = "S-1-5-21-111-222-333-1001"
    result = scheduler.install_controller_task(prepared["request_id"], root=root,
        coupling_root=bundle["coupling"], xml_query_fn=xml_query, task_info_fn=task_info,
        create_task_fn=create_task, expected_principal=sid)
    assert result["result"] == "INSTALLED"
    assert "<UserId>" + sid + "</UserId>" in state["xml"]
    scheduler.validate_task_definition_xml(state["xml"], expected_script=bundle["script"],
        expected_principal=sid, task_name=scheduler.CONTROLLER_TASK_NAME,
        expected_argument="--runner-controller-manifest",
        expected_manifest=prepared["request_manifest_path"],
        expected_manifest_sha256=prepared["request_manifest_sha256"],
        expected_request_id=prepared["request_id"], require_no_triggers=True)


def test_start_controller_validates_task_xml_even_if_scheduler_reports_running(tmp_path):
    bundle = _bundle(tmp_path)
    root = tmp_path / "runner"
    prepared, state, xml_query, _create_task, task_info, start = _prepare_and_install(bundle, root)
    state["task_state"] = "Running"
    state["xml"] = state["xml"].replace("<Triggers/>", "<Triggers><TimeTrigger/></Triggers>")
    with pytest.raises(scheduler.SchedulerRunnerError, match="TRIGGERS_FORBIDDEN"):
        scheduler.start_controller_task(prepared["request_id"], root=root,
            coupling_root=bundle["coupling"], xml_query_fn=xml_query,
            task_info_fn=task_info, start_fn=start, expected_principal="dell")
    assert state["start_calls"] == []


def test_stopped_legacy_controller_definition_is_readable_but_not_startable(tmp_path):
    bundle = _bundle(tmp_path)
    root = tmp_path / "runner"
    prepared, state, xml_query, create_task, task_info, start = _prepare_and_install(bundle, root)
    scheduler.start_controller_task(prepared["request_id"], root=root,
        coupling_root=bundle["coupling"], xml_query_fn=xml_query, task_info_fn=task_info,
        start_fn=start, expected_principal="dell")
    state["task_state"] = "Ready"
    state["xml"] = state["xml"].replace(
        "<ExecutionTimeLimit>PT0S</ExecutionTimeLimit>",
        "<ExecutionTimeLimit>PT72H</ExecutionTimeLimit>")
    old_info = lambda _name: {"state": "Ready", "ExecutionTimeLimit": "PT72H"}
    observed = scheduler.query_controller_task(prepared["request_id"], root=root,
        coupling_root=bundle["coupling"], xml_query_fn=xml_query, task_info_fn=old_info,
        expected_principal="dell")
    assert observed["state"] == "CONTROLLER_EXITED_NEEDS_RECONCILIATION"
    with pytest.raises(scheduler.SchedulerRunnerError, match="EXECUTION_TIME_LIMIT_INVALID"):
        scheduler.start_controller_task(prepared["request_id"], root=root,
            coupling_root=bundle["coupling"], xml_query_fn=xml_query, task_info_fn=old_info,
            start_fn=start, expected_principal="dell")
    assert state["start_calls"] == [scheduler.CONTROLLER_TASK_NAME]


def test_controller_process_loss_is_reported_and_never_auto_restarted(tmp_path):
    bundle = _bundle(tmp_path)
    root = tmp_path / "runner"
    prepared, state, xml_query, _create_task, task_info, start = _prepare_and_install(bundle, root)
    scheduler.start_controller_task(prepared["request_id"], root=root, coupling_root=bundle["coupling"],
        xml_query_fn=xml_query, task_info_fn=task_info, start_fn=start, expected_principal="dell")
    state["task_state"] = "Ready"
    result = scheduler.query_controller_task(prepared["request_id"], root=root,
        coupling_root=bundle["coupling"], xml_query_fn=xml_query, task_info_fn=task_info,
        expected_principal="dell")
    assert result["state"] == "CONTROLLER_EXITED_NEEDS_RECONCILIATION"
    assert len(state["start_calls"]) == 1
    receipt_path = bundle["coupling"] / "reports" / "missing_status_receipt.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text("{}", encoding="utf-8")
    with pytest.raises(scheduler.SchedulerRunnerError, match="STATUS_MISSING"):
        scheduler.resume_controller_task(prepared["request_id"], receipt_path,
            root=root, coupling_root=bundle["coupling"], xml_query_fn=xml_query,
            task_info_fn=task_info, create_task_fn=_create_task, start_fn=start,
            expected_principal="dell")


def _valid_synthetic_truth(root, request_id="c" * 32):
    case_id, attempt_id, run_id = "CASE_A", "attempt_001", "SYNTH_RUN_CASE_A"
    run_dir = root / "runs" / case_id / attempt_id / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "status.json").write_text(json.dumps({
        "case_id": case_id, "attempt_id": attempt_id, "run_id": run_id,
        "state": "DONE", "solver_entered": True, "solver_invocations": 1,
        "replay_count": 0,
    }), encoding="utf-8")
    (run_dir / "run.fsp").write_bytes(b"SYNTHETIC_FSP")
    (run_dir / "truth.h5").write_bytes(b"SYNTHETIC_H5")
    (run_dir / "hashes.json").write_text("{}", encoding="utf-8")
    (run_dir / "validation.json").write_text(json.dumps({
        "fresh_load_verified": True, "monitors_valid": True,
        "state_valid": True, "scientific_valid": True,
    }), encoding="utf-8")
    request = {"identity": {"case_id": case_id, "attempt_id": attempt_id, "run_id": run_id}}
    return request_id, request, run_dir


def test_query_controller_treats_windows_uppercase_state_as_running(tmp_path):
    bundle = _bundle(tmp_path)
    root = tmp_path / "runner"
    prepared, _state, xml_query, _create_task, _task_info, start = _prepare_and_install(bundle, root)
    scheduler.start_controller_task(prepared["request_id"], root=root,
        coupling_root=bundle["coupling"], xml_query_fn=xml_query,
        task_info_fn=lambda _name: {"state": "Ready"}, start_fn=start,
        expected_principal="dell")
    manifest = json.loads(Path(prepared["request_manifest_path"]).read_text(encoding="utf-8"))
    status_path = Path(manifest["status_path"])
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps({
        "schema": scheduler.SCHEMA_CONTROLLER_STATUS,
        "request_id": prepared["request_id"],
        "controller_manifest_sha256": prepared["request_manifest_sha256"],
        "queue_id": manifest["queue_id"],
        "state": "RUNNING",
        "current_case_id": "CASE_A",
        "runner_request_ids": [],
        "unresolved_runner_request_ids": [],
        "post_entry_automatic_replays": 0,
    }), encoding="utf-8")
    result = scheduler.query_controller_task(prepared["request_id"], root=root,
        coupling_root=bundle["coupling"], xml_query_fn=xml_query,
        task_info_fn=lambda _name: {"State": "Running", "LastTaskResult": 267009},
        expected_principal="dell")
    assert result["state"] == "RUNNING"
    assert result["task"]["State"] == "Running"


def test_resume_refuses_windows_uppercase_running_task_state(tmp_path):
    bundle = _bundle(tmp_path)
    root = tmp_path / "runner"
    prepared, _state, xml_query, _create_task, _task_info, start = _prepare_and_install(bundle, root)
    scheduler.start_controller_task(prepared["request_id"], root=root,
        coupling_root=bundle["coupling"], xml_query_fn=xml_query,
        task_info_fn=lambda _name: {"state": "Ready"}, start_fn=start,
        expected_principal="dell")
    with pytest.raises(scheduler.SchedulerRunnerError, match="CONTROLLER_RESUME_TASK_STILL_ACTIVE"):
        scheduler.resume_controller_task(prepared["request_id"], tmp_path / "not-read.json",
            root=root, coupling_root=bundle["coupling"], xml_query_fn=xml_query,
            task_info_fn=lambda _name: {"State": "Running", "LastTaskResult": 267009},
            create_task_fn=_create_task, start_fn=start, expected_principal="dell")


def test_resume_requires_reconciliation_and_proves_durable_truth_handoff(tmp_path):
    bundle = _bundle(tmp_path)
    root = tmp_path / "runner"
    prepared, state, xml_query, create_task, task_info, start = _prepare_and_install(bundle, root)
    scheduler.start_controller_task(prepared["request_id"], root=root, coupling_root=bundle["coupling"],
        xml_query_fn=xml_query, task_info_fn=task_info, start_fn=start, expected_principal="dell")
    request_id, runner_request, run_dir = _valid_synthetic_truth(root)
    status = {
        "schema": scheduler.SCHEMA_CONTROLLER_STATUS, "state": "STOPPED_RECONCILED",
        "request_id": prepared["request_id"],
        "controller_manifest_sha256": prepared["request_manifest_sha256"],
        "queue_id": "queue-test-001", "current_case_id": None,
        "unresolved_runner_request_ids": [], "runner_request_ids": [request_id],
        "post_entry_automatic_replays": 0,
    }
    bundle["status_path"].write_text(json.dumps(status, sort_keys=True), encoding="utf-8")
    status_sha = _sha(bundle["status_path"])
    receipt = {
        "schema": scheduler.SCHEMA_CONTROLLER_RESUME, "request_id": prepared["request_id"],
        "controller_manifest_sha256": prepared["request_manifest_sha256"],
        "queue_id": "queue-test-001", "previous_status_sha256": status_sha,
        "resume_generation": 1, "safe_to_resume": True, "startup_reconciled": True,
        "current_case_id": None, "unresolved_runner_request_ids": [],
        "post_entry_automatic_replays": 0, "runner_request_ids": [request_id],
    }
    receipt_path = bundle["coupling"] / "reports" / "queue" / "resume_receipt.json"
    receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
    query_calls = []

    def query_one(request_id_arg, *, root, task_info_fn):
        query_calls.append(request_id_arg)
        return {"state": "TERMINAL", "request": runner_request,
                "result": {"exit_code": 0}}

    state["task_state"] = "Ready"
    result = scheduler.resume_controller_task(prepared["request_id"], receipt_path,
        root=root, coupling_root=bundle["coupling"], xml_query_fn=xml_query,
        task_info_fn=task_info, create_task_fn=create_task, start_fn=start,
        query_one_fn=query_one, expected_principal="dell")
    assert result["result"] == "RESUME_START_REQUESTED"
    assert result["resume_generation"] == 1
    assert query_calls == [request_id]
    assert all((run_dir / name).is_file() for name in ("run.fsp", "truth.h5", "validation.json", "hashes.json"))
    assert len(state["start_calls"]) == 2
    assert "--runner-resume-receipt" in state["xml"]
    repeated = scheduler.resume_controller_task(prepared["request_id"], receipt_path,
        root=root, coupling_root=bundle["coupling"], xml_query_fn=xml_query,
        task_info_fn=task_info, create_task_fn=create_task, start_fn=start,
        query_one_fn=query_one, expected_principal="dell")
    assert repeated["result"] == "RESUME_ALREADY_REQUESTED"
    assert len(state["start_calls"]) == 2


def test_resume_refuses_unresolved_or_nonterminal_runner_request(tmp_path):
    bundle = _bundle(tmp_path)
    root = tmp_path / "runner"
    prepared, state, xml_query, create_task, task_info, start = _prepare_and_install(bundle, root)
    scheduler.start_controller_task(prepared["request_id"], root=root, coupling_root=bundle["coupling"],
        xml_query_fn=xml_query, task_info_fn=task_info, start_fn=start, expected_principal="dell")
    status = {
        "schema": scheduler.SCHEMA_CONTROLLER_STATUS, "state": "STOPPED_RECONCILED",
        "request_id": prepared["request_id"],
        "controller_manifest_sha256": prepared["request_manifest_sha256"],
        "queue_id": "queue-test-001", "current_case_id": None,
        "unresolved_runner_request_ids": [], "runner_request_ids": ["d" * 32],
        "post_entry_automatic_replays": 0,
    }
    bundle["status_path"].write_text(json.dumps(status, sort_keys=True), encoding="utf-8")
    receipt = {
        "schema": scheduler.SCHEMA_CONTROLLER_RESUME, "request_id": prepared["request_id"],
        "controller_manifest_sha256": prepared["request_manifest_sha256"],
        "queue_id": "queue-test-001", "previous_status_sha256": _sha(bundle["status_path"]),
        "resume_generation": 1, "safe_to_resume": True, "startup_reconciled": True,
        "current_case_id": None, "unresolved_runner_request_ids": [],
        "post_entry_automatic_replays": 0, "runner_request_ids": ["d" * 32],
    }
    receipt_path = bundle["coupling"] / "reports" / "queue" / "unsafe_receipt.json"
    receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
    state["task_state"] = "Ready"
    with pytest.raises(scheduler.SchedulerRunnerError, match="RUNNER_REQUEST_UNRESOLVED"):
        scheduler.resume_controller_task(prepared["request_id"], receipt_path,
            root=root, coupling_root=bundle["coupling"], xml_query_fn=xml_query,
            task_info_fn=task_info, create_task_fn=create_task, start_fn=start,
            query_one_fn=lambda *_a, **_k: {"state": "RUNNING"},
            expected_principal="dell")
    assert len(state["start_calls"]) == 1


def _rebind_fixture(tmp_path, *, postentry_failure=False, quarantined=True,
                    predecessor_execution_time_limit=scheduler.LEGACY_TASK_EXECUTION_LIMIT,
                    predecessor_xml_limit=None, predecessor_enabled_present=False):
    bundle = _bundle(tmp_path)
    root = tmp_path / "runner"
    prepared, state, xml_query, create_task, task_info, start = _prepare_and_install(bundle, root)
    scheduler.start_controller_task(
        prepared["request_id"], root=root, coupling_root=bundle["coupling"],
        xml_query_fn=xml_query, task_info_fn=task_info, start_fn=start,
        expected_principal="dell")
    state["task_state"] = "Ready"
    state["execution_time_limit"] = predecessor_execution_time_limit
    if predecessor_xml_limit is None:
        state["xml"] = state["xml"].replace(
            "<ExecutionTimeLimit>" + scheduler.TASK_EXECUTION_LIMIT + "</ExecutionTimeLimit>", "")
    else:
        state["xml"] = state["xml"].replace(
            "<ExecutionTimeLimit>" + scheduler.TASK_EXECUTION_LIMIT + "</ExecutionTimeLimit>",
            "<ExecutionTimeLimit>" + predecessor_xml_limit + "</ExecutionTimeLimit>")
    if not predecessor_enabled_present:
        state["xml"] = state["xml"].replace("<Enabled>true</Enabled>", "", 1)
    old_request_id = prepared["request_id"]
    old_task_sha = _sha(scheduler._task_controller_binding_path(root))
    old_request_binding_sha = _sha(scheduler._controller_request_files(root, old_request_id)[2])
    runner_id = "c" * 32
    identity = {"case_id": "CASE_A", "attempt_id": "attempt_001", "run_id": "RUN_CASE_A"}
    runner_ids = [runner_id] if postentry_failure else []
    if postentry_failure:
        run_dir = root / "runs" / "CASE_A" / "attempt_001" / "RUN_CASE_A"
        run_dir.mkdir(parents=True)
        (run_dir / "status.json").write_text(json.dumps({
            **identity, "state": "FAILED_POSTENTRY_NO_TRUTH", "solver_entered": True,
            "solver_invocations": 1, "replay_count": 0, "failure": "POSTENTRY_NO_TRUTH",
        }), encoding="utf-8")
    status = {
        "schema": scheduler.SCHEMA_CONTROLLER_STATUS, "state": "STOPPED_RECONCILED",
        "request_id": old_request_id, "controller_manifest_sha256": prepared["request_manifest_sha256"],
        "queue_id": bundle["manifest"]["queue_id"], "current_case_id": None,
        "runner_request_ids": runner_ids, "unresolved_runner_request_ids": [],
        "post_entry_automatic_replays": 0,
    }
    bundle["status_path"].write_text(json.dumps(status, sort_keys=True), encoding="utf-8")
    bundle["script"].write_text(bundle["script"].read_text(encoding="utf-8") + "# source revision\n",
                                encoding="utf-8")
    new_cases = ["CASE_B"] if postentry_failure else list(bundle["manifest"]["case_ids"])
    manifest = dict(bundle["manifest"])
    manifest.update({
        "controller_run_id": "controller-run-002",
        "controller_script_sha256": _sha(bundle["script"]),
        "status_path": str(bundle["coupling"] / "reports" / "queue" / "controller_status_v2.json"),
        "case_ids": new_cases, "max_cases": len(new_cases),
    })
    new_manifest_path = bundle["coupling"] / "reports" / "queue" / "controller_manifest_v2.json"
    new_manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    queue_state = {
        "schema": scheduler.SCHEMA_CONTROLLER_QUEUE_SNAPSHOT,
        "queue_id": bundle["manifest"]["queue_id"],
        "queue_manifest_sha256": bundle["manifest"]["queue_manifest_sha256"],
        "authorized_case_ids": list(bundle["manifest"]["case_ids"]),
        "remaining_case_ids": new_cases, "completed_case_ids": [],
        "solver_entered_case_ids": ["CASE_A"] if postentry_failure else [],
        "quarantined_case_ids": ["CASE_A"] if postentry_failure and quarantined else [],
        "active_case_count": 0, "active_case_id": None,
        "unresolved_runner_request_ids": [], "pending_replay_count": 0,
        "max_concurrent_cases": 1, "per_case_max_solver_entries": 1,
        "post_entry_automatic_replays": 0,
    }
    queue_path = bundle["coupling"] / "reports" / "queue" / "queue_state_snapshot.json"
    queue_path.write_text(json.dumps(queue_state, sort_keys=True, indent=2), encoding="utf-8")
    owner_path = bundle["coupling"] / "reports" / "queue" / "OWNER_REBIND_DECISION.md"
    owner_path.write_text("Synthetic owner decision for offline API validation.\n", encoding="utf-8")
    receipt = {
        "schema": scheduler.SCHEMA_CONTROLLER_RETIREMENT,
        "old_request_id": old_request_id,
        "old_manifest_sha256": prepared["request_manifest_sha256"],
        "old_request_binding_sha256": old_request_binding_sha,
        "old_task_binding_sha256": old_task_sha,
        "old_status_sha256": _sha(bundle["status_path"]),
        "new_manifest_sha256": _sha(new_manifest_path),
        "queue_id": bundle["manifest"]["queue_id"],
        "queue_manifest_sha256": bundle["manifest"]["queue_manifest_sha256"],
        "safe_to_retire": True, "startup_reconciled": True,
        "approved_by": "synthetic-owner",
        "owner_decision_path": str(owner_path), "owner_decision_sha256": _sha(owner_path),
        "queue_state_path": str(queue_path), "queue_state_sha256": _sha(queue_path),
        "runner_request_ids": runner_ids,
    }
    receipt_path = bundle["coupling"] / "reports" / "queue" / "retirement_receipt.json"
    receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2), encoding="utf-8")
    def all_task_info(name):
        if name == scheduler.TASK_NAME:
            return {"state": "Ready"}
        return task_info(name)
    def set_enabled(enabled):
        before = "<Enabled>false</Enabled>" if enabled else "<Enabled>true</Enabled>"
        after = "<Enabled>true</Enabled>" if enabled else "<Enabled>false</Enabled>"
        if before in state["xml"]:
            state["xml"] = state["xml"].replace(before, after, 1)
        elif not enabled and "<Enabled>" not in state["xml"]:
            state["xml"] = state["xml"].replace("<Settings>", "<Settings><Enabled>false</Enabled>", 1)
        elif enabled and "<Enabled>" not in state["xml"]:
            pass  # Scheduler state is read back from task_info when XML omits this default.
        else:
            raise AssertionError("task enabled state cannot be changed")
        state["task_state"] = "Ready" if enabled else "Disabled"
    query_one_fn = None
    if postentry_failure:
        def query_one_fn(request_id, *, root, task_info_fn):
            assert request_id == runner_id
            return {"state": "TERMINAL", "request": {"identity": identity},
                    "result": {"exit_code": 2, "solver_entered": True}}
    return {
        "old_request_id": old_request_id, "new_manifest_path": new_manifest_path,
        "receipt_path": receipt_path, "root": root, "bundle": bundle,
        "state": state, "xml_query": xml_query, "create_task": create_task,
        "task_info": all_task_info, "start": start, "set_enabled": set_enabled,
        "query_one": query_one_fn, "old_task_sha": old_task_sha,
    }


def _run_rebind(args, **overrides):
    bundle = args["bundle"]
    kwargs = {
        "expected_old_task_binding_sha256": args["old_task_sha"],
        "expected_new_manifest_sha256": _sha(args["new_manifest_path"]),
        "expected_retirement_receipt_sha256": _sha(args["receipt_path"]),
        "root": args["root"], "coupling_root": bundle["coupling"],
        "xml_query_fn": args["xml_query"], "task_info_fn": args["task_info"],
        "create_task_fn": args["create_task"], "set_enabled_fn": args["set_enabled"],
        "process_inventory_fn": lambda: [], "query_one_fn": args["query_one"],
        "expected_principal": "dell",
    }
    kwargs.update(overrides)
    return scheduler.retire_rebind_controller_task(
        args["old_request_id"], args["new_manifest_path"], args["receipt_path"], **kwargs)



def test_retire_rebind_ignores_retire_cli_request_id_as_active_owner(tmp_path):
    args = _rebind_fixture(tmp_path)
    old_id = args["old_request_id"]
    process_inventory = [
        {"Name": "cmd.exe", "CommandLine":
         r"cmd.exe /c task_scheduler_v1.py retire-rebind-controller-task " + old_id},
        {"Name": "python.exe", "CommandLine":
         r"N:\anaconda_envs\RCP_LCP\python.exe D:\project\worktrees\runner\task_scheduler_v1.py retire-rebind-controller-task " + old_id},
    ]
    result = _run_rebind(args, process_inventory_fn=lambda: process_inventory)
    assert result["result"] == "REBOUND"
    assert result["started"] is False
    assert result["solver_entries"] == result["automatic_replays"] == 0


@pytest.mark.parametrize("process", [
    {"Name": "python.exe", "CommandLine": r"python.exe D:\coupling\serial_queue.py --runner-controller-request-id " + "b" * 32},
    {"Name": "python.exe", "CommandLine": r"python.exe D:\runner\task_scheduler_v1.py worker-once " + "c" * 32},
    {"Name": "fdtd-engine-msmpi.exe", "CommandLine": r"fdtd-engine-msmpi.exe -gpu"},
])
def test_retire_rebind_still_rejects_active_controller_worker_or_solver(tmp_path, process):
    args = _rebind_fixture(tmp_path)
    with pytest.raises(scheduler.SchedulerRunnerError,
                       match="CONTROLLER_OR_SOLVER_PROCESS_STILL_ACTIVE"):
        _run_rebind(args, process_inventory_fn=lambda: [process])


def test_retire_rebind_preserves_history_is_single_owner_and_idempotent(tmp_path):
    args = _rebind_fixture(tmp_path)
    start_count = len(args["state"]["start_calls"])
    result = _run_rebind(args)
    assert result["result"] == "REBOUND" and result["started"] is False
    assert result["solver_entries"] == result["automatic_replays"] == 0
    assert len(args["state"]["start_calls"]) == start_count
    assert scheduler._read_controller_task_binding(args["root"])["request_id"] == result["request_id"]
    audit = args["root"] / scheduler.CONTROLLER_TASK_DIR.name / "rebind_transactions" / result["transaction_id"] / "audit"
    assert _sha(audit / "old_task_binding.json") == args["old_task_sha"]
    assert (audit / "old_task.xml").is_file()
    repeated = _run_rebind(args)
    assert repeated["result"] == "ALREADY_REBOUND"
    assert repeated["transaction_id"] == result["transaction_id"]
    assert len(args["state"]["start_calls"]) == start_count



@pytest.mark.parametrize("scheduler_limit,xml_limit,enabled_present", [
    (scheduler.LEGACY_TASK_EXECUTION_LIMIT, None, False),
    (scheduler.LEGACY_TASK_EXECUTION_LIMIT, scheduler.LEGACY_TASK_EXECUTION_LIMIT, True),
    (scheduler.TASK_EXECUTION_LIMIT, scheduler.TASK_EXECUTION_LIMIT, True),
])
def test_retire_rebind_accepts_only_approved_predecessor_execution_contracts(
        tmp_path, scheduler_limit, xml_limit, enabled_present):
    args = _rebind_fixture(
        tmp_path, predecessor_execution_time_limit=scheduler_limit,
        predecessor_xml_limit=xml_limit, predecessor_enabled_present=enabled_present)
    result = _run_rebind(args)
    assert result["result"] == "REBOUND"
    assert args["state"]["execution_time_limit"] == scheduler.TASK_EXECUTION_LIMIT
    assert args["state"]["task_state"] == "Ready"
    assert len(args["state"]["start_calls"]) == 1
    audit = (args["root"] / scheduler.CONTROLLER_TASK_DIR.name / "rebind_transactions" /
             result["transaction_id"] / "audit" / "old_task_scheduler_info.json")
    record = json.loads(audit.read_text(encoding="utf-8"))
    assert record["scheduler_execution_time_limit"] == scheduler_limit
    assert record["recognized_contract"] in (
        "LEGACY_CONTROLLER_PT72H_DEFAULTED_V1",
        "LEGACY_CONTROLLER_PT72H_EXPLICIT_V1",
        "CONTROLLER_PT0S_EXPLICIT_V1")


@pytest.mark.parametrize("scheduler_limit,xml_limit", [
    ("PT48H", "PT48H"),
    (scheduler.TASK_EXECUTION_LIMIT, None),
    (scheduler.LEGACY_TASK_EXECUTION_LIMIT, scheduler.TASK_EXECUTION_LIMIT),
])
def test_retire_rebind_rejects_unknown_or_scheduler_xml_mismatched_limits(
        tmp_path, scheduler_limit, xml_limit):
    args = _rebind_fixture(
        tmp_path, predecessor_execution_time_limit=scheduler_limit,
        predecessor_xml_limit=xml_limit)
    with pytest.raises(scheduler.SchedulerRunnerError,
                       match="CONTROLLER_REBIND_TASK_DEFINITION_MISMATCH"):
        _run_rebind(args)
    assert scheduler._read_controller_task_binding(args["root"])["request_id"] == args["old_request_id"]
    assert args["state"]["task_state"] == "Ready"


@pytest.mark.parametrize("mutation", ["action", "request", "manifest_sha256"])
def test_retire_rebind_rejects_predecessor_action_request_and_sha_mismatch(tmp_path, mutation):
    args = _rebind_fixture(tmp_path)
    xml = args["state"]["xml"]
    old_manifest_sha = scheduler._sha(args["bundle"]["manifest_path"])
    if mutation == "action":
        xml = xml.replace("serial_queue.py", "unapproved_queue.py")
    elif mutation == "request":
        xml = xml.replace(args["old_request_id"], "f" * 32)
    else:
        xml = xml.replace(old_manifest_sha, "e" * 64)
    args["state"]["xml"] = xml
    with pytest.raises(scheduler.SchedulerRunnerError,
                       match="CONTROLLER_REBIND_TASK_DEFINITION_MISMATCH"):
        _run_rebind(args)
    assert scheduler._read_controller_task_binding(args["root"])["request_id"] == args["old_request_id"]


def test_retire_rebind_reuses_prepared_successor_without_rewriting_binding(tmp_path):
    args = _rebind_fixture(tmp_path)
    prepared = scheduler.prepare_controller_task(
        args["new_manifest_path"], root=args["root"],
        coupling_root=args["bundle"]["coupling"], install_task=False)
    assert prepared["request_id"] != args["old_request_id"]
    binding_path = scheduler._controller_request_files(
        args["root"], prepared["request_id"])[2]
    binding_before = binding_path.read_bytes()
    result = _run_rebind(args)
    assert result["request_id"] == prepared["request_id"]
    assert binding_path.read_bytes() == binding_before
    assert not scheduler._controller_request_files(args["root"], prepared["request_id"])[3].exists()



def test_retire_rebind_accepts_scheduler_readback_when_enabled_xml_is_omitted(tmp_path):
    args = _rebind_fixture(tmp_path)
    original = args["create_task"]
    def install_without_enabled(xml, force=False):
        result = original(xml, force=force)
        state = args["state"]
        state["xml"] = state["xml"].replace("<Enabled>false</Enabled>", "")
        return result
    result = _run_rebind(args, create_task_fn=install_without_enabled)
    assert result["result"] == "REBOUND"
    assert args["state"]["execution_time_limit"] == scheduler.TASK_EXECUTION_LIMIT
    assert args["state"]["task_state"] == "Ready"
    assert "<Enabled>" not in args["state"]["xml"]
    assert args["state"]["start_calls"] == [scheduler.CONTROLLER_TASK_NAME]


def test_retire_rebind_rejects_successor_without_actual_pt0s_readback(tmp_path):
    args = _rebind_fixture(tmp_path)
    original = args["create_task"]
    def install_with_actual_72h(xml, force=False):
        altered = xml.replace(
            "<ExecutionTimeLimit>" + scheduler.TASK_EXECUTION_LIMIT + "</ExecutionTimeLimit>",
            "<ExecutionTimeLimit>" + scheduler.LEGACY_TASK_EXECUTION_LIMIT + "</ExecutionTimeLimit>")
        return original(altered, force=force)
    with pytest.raises(scheduler.SchedulerRunnerError,
                       match="SCHEDULER_TASK_EXECUTION_TIME_LIMIT_INVALID"):
        _run_rebind(args, create_task_fn=install_with_actual_72h)
    assert scheduler._read_controller_task_binding(args["root"])["request_id"] == args["old_request_id"]
    assert args["state"]["task_state"] == "Disabled"


def test_retire_rebind_rejects_successor_with_unsafe_multiple_instance_policy(tmp_path):
    args = _rebind_fixture(tmp_path)
    original = args["create_task"]
    def install_unsafe(xml, force=False):
        return original(xml.replace(
            "<MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>",
            "<MultipleInstancesPolicy>Parallel</MultipleInstancesPolicy>"), force=force)
    with pytest.raises(scheduler.SchedulerRunnerError,
                       match="SCHEDULER_TASK_MULTIPLE_INSTANCE_POLICY_INVALID"):
        _run_rebind(args, create_task_fn=install_unsafe)
    assert scheduler._read_controller_task_binding(args["root"])["request_id"] == args["old_request_id"]
    assert args["state"]["task_state"] == "Disabled"


def test_retire_rebind_resumes_interrupted_transaction_without_start(tmp_path, monkeypatch):
    args = _rebind_fixture(tmp_path)
    original = scheduler._write_controller_task_binding
    failed = {"once": False}
    def write_then_fail(root, body):
        result = original(root, body)
        if body.get("request_id") != args["old_request_id"] and not failed["once"]:
            failed["once"] = True
            raise OSError("synthetic crash after binding replace")
        return result
    monkeypatch.setattr(scheduler, "_write_controller_task_binding", write_then_fail)
    with pytest.raises(OSError, match="synthetic crash"):
        _run_rebind(args)
    monkeypatch.setattr(scheduler, "_write_controller_task_binding", original)
    recovered = _run_rebind(args)
    assert recovered["request_id"] == scheduler._read_controller_task_binding(args["root"])["request_id"]
    assert args["state"]["xml"].count("<Enabled>true</Enabled>") == 1
    assert len(args["state"]["start_calls"]) == 1


def test_retire_rebind_recovers_after_successor_task_install_before_journal(tmp_path):
    args = _rebind_fixture(tmp_path)
    original = args["create_task"]
    failed = {"once": False}
    def install_then_fail(xml, force=False):
        result = original(xml, force=force)
        if "<Enabled>false</Enabled>" in xml and not failed["once"]:
            failed["once"] = True
            raise OSError("synthetic crash after successor task install")
        return result
    args["create_task"] = install_then_fail
    with pytest.raises(OSError, match="synthetic crash after successor task install"):
        _run_rebind(args)
    args["create_task"] = original
    recovered = _run_rebind(args)
    assert recovered["result"] == "REBOUND"
    assert recovered["started"] is False and recovered["solver_entries"] == 0
    assert len(args["state"]["start_calls"]) == 1


def test_retire_rebind_rejects_active_owner_lock_and_solver_process(tmp_path):
    args = _rebind_fixture(tmp_path)
    args["state"]["task_state"] = "Running"
    with pytest.raises(scheduler.SchedulerRunnerError, match="OLD_TASK_STILL_ACTIVE"):
        _run_rebind(args)
    args = _rebind_fixture(tmp_path / "slot")
    (args["root"] / ".runner.lock").write_text("active", encoding="utf-8")
    with pytest.raises(scheduler.SchedulerRunnerError, match="SLOT_OR_LOCK"):
        _run_rebind(args)
    args = _rebind_fixture(tmp_path / "process")
    with pytest.raises(scheduler.SchedulerRunnerError, match="PROCESS_STILL_ACTIVE"):
        _run_rebind(args, process_inventory_fn=lambda: [{"Name": "fdtd-engine-msmpi.exe"}])


def test_retire_rebind_rejects_status_drift_after_stop_receipt(tmp_path):
    args = _rebind_fixture(tmp_path)
    old_xml = args["state"]["xml"]
    status_path = args["bundle"]["status_path"]
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["state"] = "RUNNING"
    status["current_case_id"] = "CASE_A"
    status_path.write_text(json.dumps(status, sort_keys=True), encoding="utf-8")
    with pytest.raises(scheduler.SchedulerRunnerError,
                       match="CONTROLLER_RETIREMENT_RECEIPT_NOT_SAFE"):
        _run_rebind(args)
    assert scheduler._read_controller_task_binding(args["root"])["request_id"] == args["old_request_id"]
    assert args["state"]["xml"] == old_xml


def test_retire_rebind_requires_postentry_failure_quarantine(tmp_path):
    args = _rebind_fixture(tmp_path, postentry_failure=True, quarantined=True)
    result = _run_rebind(args)
    assert result["result"] == "REBOUND" and result["solver_entries"] == 0
    args = _rebind_fixture(tmp_path / "unquarantined", postentry_failure=True, quarantined=False)
    with pytest.raises(scheduler.SchedulerRunnerError, match="POSTENTRY_FAILURE_NOT_QUARANTINED"):
        _run_rebind(args)


def test_retire_rebind_rejects_expanded_queue_or_changed_policy(tmp_path):
    args = _rebind_fixture(tmp_path)
    manifest = json.loads(args["new_manifest_path"].read_text(encoding="utf-8"))
    manifest["case_ids"], manifest["max_cases"] = ["CASE_A", "CASE_C"], 2
    args["new_manifest_path"].write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    with pytest.raises(scheduler.SchedulerRunnerError, match="CASE_BUDGET_EXPANSION"):
        _run_rebind(args)
    args = _rebind_fixture(tmp_path / "policy")
    manifest = json.loads(args["new_manifest_path"].read_text(encoding="utf-8"))
    manifest["max_concurrent_cases"] = 2
    args["new_manifest_path"].write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    with pytest.raises(scheduler.SchedulerRunnerError, match="CONCURRENCY_MUST_BE_ONE"):
        _run_rebind(args)
