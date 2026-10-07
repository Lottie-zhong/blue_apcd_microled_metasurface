import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import task_scheduler_v1 as scheduler


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
    state = {"xml": None, "task_state": "Ready", "create_calls": [], "start_calls": []}

    def xml_query(name):
        assert name == scheduler.CONTROLLER_TASK_NAME
        if state["xml"] is None:
            raise scheduler.SchedulerRunnerError("SCHEDULER_CONTROLLER_TASK_NOT_INSTALLED")
        return state["xml"]

    def create_task(xml, force=False):
        state["xml"] = xml
        state["create_calls"].append({"xml": xml, "force": force})

    def task_info(name):
        assert name == scheduler.CONTROLLER_TASK_NAME
        return {
            "state": state["task_state"],
            "UserId": "DELL",
            "LogonType": 3,
            "RunLevel": 0,
            "MultipleInstances": 2,
            "ExecutionTimeLimit": scheduler.TASK_EXECUTION_LIMIT,
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
    assert result["execution_time_limit"] == "PT72H"
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
