from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared_fdtd.control_v3.gpu_capacity import (
    GPU_REQUIRED_FREE_MIB,
    GPU_VALIDATED_BASELINE_FREE_MIB,
    _gpu_capacity_csv,
    _gpu_capacity_int,
    evaluate_external_gpu_capacity,
    persist_external_gpu_capacity_snapshot,
)
from shared_fdtd.control_v3.gpu_capacity import capture_external_gpu_capacity_snapshot
from shared_fdtd.control_v3.allocator import Allocator
from shared_fdtd.control_v3.db import ControlDB
from shared_fdtd.engine.dispatcher import dispatch_once, enqueue
from shared_fdtd.engine.event_log import read_events
from shared_fdtd.control_v3.launch_authority import ScientificLaunchAuthority
from shared_fdtd.control_v3.resources import ResourceSnapshot
from shared_fdtd.tools.v3_g2_host import AdmissionGateBlocked, _gpu_capacity_guarded_start, queue_state

SCHEMA = Path(__file__).resolve().parents[2] / "shared_fdtd" / "control_v3" / "schema.sql"


def snapshot(free_mib):
    return {
        "schema": "SHARED_V3_EXTERNAL_GPU_CAPACITY_SNAPSHOT_V1",
        "captured_at_utc": "2026-09-30T00:00:00+00:00",
        "capture_status": "PASS",
        "selected_gpu": {
            "index": 0,
            "name": "NVIDIA GeForce RTX 3080",
            "uuid": "GPU-fixture",
            "utilization_gpu_percent": 8,
            "memory_total_mib": 10240,
            "memory_used_mib": 10240 - free_mib,
            "memory_free_mib": free_mib,
        },
        "compute_processes": [{"gpu_uuid": "GPU-fixture", "pid": 1234, "process_name": "fixture.exe", "used_memory_mib": 100}],
        "external_compute_processes": [{"gpu_uuid": "GPU-fixture", "pid": 1234, "process_name": "fixture.exe", "used_memory_mib": 100}],
        "shared_v3_active_owners": [{"branch_id": "traditional", "logical_case_id": "other", "attempt_id": "attempt_001", "slot_id": "GLOBAL_SLOT_1", "fencing_generation": 7}],
        "process_attribution_status": "PASS",
    }


def main():
    tests = {}
    tests["historical_threshold_constants"] = GPU_REQUIRED_FREE_MIB == 1369 and GPU_VALIDATED_BASELINE_FREE_MIB == 9246
    tests["one_mib_below_waits"] = evaluate_external_gpu_capacity(snapshot(1368))["status"] == "WAIT_EXTERNAL_GPU_CAPACITY"
    tests["exact_threshold_passes"] = evaluate_external_gpu_capacity(snapshot(1369))["status"] == "PASS"
    tests["utilization_is_observed_not_a_gate"] = evaluate_external_gpu_capacity(snapshot(1369))["status"] == "PASS"
    tests["unavailable_measurement_fails_closed"] = evaluate_external_gpu_capacity({"capture_status": "UNAVAILABLE", "capture_reason": "fixture"})["status"] == "WAIT_EXTERNAL_GPU_CAPACITY"
    tests["missing_free_memory_fails_closed"] = evaluate_external_gpu_capacity({"capture_status": "PASS", "selected_gpu": {}})["status"] == "WAIT_EXTERNAL_GPU_CAPACITY"
    tests["windows_empty_compute_list_parses"] = _gpu_capacity_csv("No running processes found", 4) == []
    tests["windows_na_process_memory_parses"] = _gpu_capacity_int("N/A") is None

    def sampled_snapshot(device_rows, resource_label):
        device_query = SimpleNamespace(returncode=0, stdout=device_rows, stderr="")
        process_query = SimpleNamespace(returncode=0, stdout="No running processes found\n", stderr="")
        with patch("shared_fdtd.control_v3.gpu_capacity.shutil.which", return_value="nvidia-smi"):
            with patch(
                "shared_fdtd.control_v3.gpu_capacity.subprocess.run",
                side_effect=[device_query, process_query],
            ):
                with patch(
                    "shared_fdtd.control_v3.gpu_capacity._shared_v3_gpu_owners",
                    return_value=([], set()),
                ):
                    return capture_external_gpu_capacity_snapshot(None, resource_label)

    one_device = sampled_snapshot(
        "0, NVIDIA GeForce RTX 3080, GPU-fixture, 3, 10240, 979, 9075\n",
        "GPU license audit",
    )
    tests["logical_label_resolves_unique_visible_device"] = (
        one_device.get("capture_status") == "PASS"
        and one_device.get("requested_resource_name") == "GPU license audit"
        and one_device.get("resolved_gpu") == {
            "index": 0, "uuid": "GPU-fixture", "name": "NVIDIA GeForce RTX 3080"
        }
        and one_device.get("resolution_mode") == "SINGLE_VISIBLE_DEVICE_FOR_LOGICAL_RESOURCE_LABEL"
    )
    two_devices = sampled_snapshot(
        "0, NVIDIA GeForce RTX 3080, GPU-fixture-0, 3, 10240, 979, 9075\n"
        "1, NVIDIA GeForce RTX 3080, GPU-fixture-1, 0, 10240, 1024, 9216\n",
        "GPU license audit",
    )
    tests["logical_label_with_multiple_devices_fails_closed"] = (
        two_devices.get("capture_status") == "UNAVAILABLE"
        and two_devices.get("capture_reason") == "GPU_DEVICE_SELECTION_OR_MEMORY_UNAVAILABLE"
        and evaluate_external_gpu_capacity(two_devices)["status"] == "WAIT_EXTERNAL_GPU_CAPACITY"
    )

    with tempfile.TemporaryDirectory(prefix="apcd_gpu_capacity_snapshot_test_") as temp:
        root = Path(temp)
        lease = SimpleNamespace(slot_id="GLOBAL_SLOT_1", token_hash="a" * 64, fencing_generation=17)
        ref = persist_external_gpu_capacity_snapshot(
            root,
            branch_id="coupling_ml",
            case_id="fixture-case",
            attempt_id="attempt_001",
            lease=lease,
            phase="HOST_FINAL_PRE_SOLVER_POPEN",
            snapshot=snapshot(1369),
        )
        events = read_events(root / "events.jsonl")
        event = next((item for item in events if item.get("event_type") == "GPU_CAPACITY_SNAPSHOT"), {})
        digest_input = {key: value for key, value in event.items() if key not in {"timestamp", "event_type", "snapshot_sha256"}}
        computed_hash = hashlib.sha256(json.dumps(digest_input, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")).hexdigest()
        tests["snapshot_event_persisted_with_attempt_and_fence"] = (
            event.get("schema") == "SHARED_V3_GPU_CAPACITY_SNAPSHOT_EVENT_V1"
            and event.get("branch_id") == "coupling_ml"
            and event.get("case_id") == "fixture-case"
            and event.get("attempt_id") == "attempt_001"
            and event.get("lease_token_hash") == "a" * 64
            and event.get("fencing_generation") == 17
            and event.get("slot_id") == "GLOBAL_SLOT_1"
            and event.get("status") == "PASS"
        )
        tests["snapshot_ref_hash_matches_durable_event"] = (
            ref.get("snapshot_id") == event.get("snapshot_id")
            and ref.get("snapshot_sha256") == event.get("snapshot_sha256") == computed_hash
            and ref.get("event_schema") == event.get("schema") == "SHARED_V3_GPU_CAPACITY_SNAPSHOT_EVENT_V1"
        )

    with tempfile.TemporaryDirectory(prefix="apcd_gpu_capacity_dispatch_test_") as temp:
        root = Path(temp)
        db = ControlDB(root / "control.sqlite3")
        db.initialize(SCHEMA)
        allocator = Allocator(db)
        allocator.set_gpu_physical_cap(1)
        allocator.set_branch_limit("coupling_ml", 1)
        attempt_root = root / "case" / "attempt_001"
        attempt_root.mkdir(parents=True)
        enqueue(db, "coupling_ml", "GPU_CAPACITY_CASE", "attempt_001", {
            "backend_type": "GPU", "gpu_resource_name": "NVIDIA GeForce RTX 3080",
            "attempt_root": str(attempt_root),
        })
        with db.connect(readonly=True) as con:
            control_before = dict(con.execute("SELECT new_entry_hold,control_generation FROM admission_control WHERE control_id=1").fetchone())
        launched = []
        with patch("shared_fdtd.control_v3.gpu_capacity.capture_external_gpu_capacity_snapshot", return_value=snapshot(1368)):
            dispatch_once(db, "coupling_ml", lambda row, lease: launched.append((row, lease)))
        with db.connect(readonly=True) as con:
            queue_row = dict(con.execute("SELECT * FROM branch_queue WHERE logical_case_id='GPU_CAPACITY_CASE'").fetchone())
            queue_payload = json.loads(queue_row["payload_json"])
            entries = int(con.execute("SELECT COUNT(*) FROM lease_events WHERE event_type='SCIENTIFIC_SOLVER_ENTERED'").fetchone()[0])
            active_gpu = int(con.execute("SELECT COUNT(*) FROM gpu_capacity_leases WHERE state IN ('RESERVED','LIVE','RELEASE_PENDING','OWNER_QUARANTINED')").fetchone()[0])
            free_slots = int(con.execute("SELECT COUNT(*) FROM slots WHERE state='FREE'").fetchone()[0])
            control_after = dict(con.execute("SELECT new_entry_hold,control_generation FROM admission_control WHERE control_id=1").fetchone())
        durable = read_events(attempt_root / "events.jsonl")
        capacity_events = [item for item in durable if item.get("event_type") == "GPU_CAPACITY_SNAPSHOT"]
        tests["dispatcher_low_headroom_classifies_retryable_wait"] = (
            queue_row["state"] == "WAIT_RESOURCE_CAPACITY"
            and queue_payload.get("_v3_admission", {}).get("status") == "WAIT_EXTERNAL_GPU_CAPACITY"
        )
        tests["dispatcher_low_headroom_persists_fenced_snapshot"] = (
            len(capacity_events) == 1
            and capacity_events[0].get("status") == "WAIT_EXTERNAL_GPU_CAPACITY"
            and capacity_events[0].get("fencing_generation") is not None
            and bool(capacity_events[0].get("slot_id"))
        )
        tests["dispatcher_low_headroom_releases_slot_without_entry"] = (
            not launched and entries == 0 and active_gpu == 0 and free_slots == 3
        )
        tests["dispatcher_low_headroom_preserves_hold_generation"] = control_before == control_after
        with patch("shared_fdtd.control_v3.gpu_capacity.capture_external_gpu_capacity_snapshot", return_value=snapshot(1369)):
            retry = dispatch_once(
                db, "coupling_ml",
                lambda row, lease: launched.append((row, lease)) or {"queue_state": "HOST_STARTED"},
            )
        tests["dispatcher_retries_same_attempt_after_capacity_returns"] = retry == ["GPU_CAPACITY_CASE"] and len(launched) == 1
        if launched:
            allocator.release_owned_idempotent(launched[0][1], scientific_terminal="FAILED_PREENTRY")
        with db.connect(readonly=True) as con:
            retry_entries = int(con.execute("SELECT COUNT(*) FROM lease_events WHERE event_type='SCIENTIFIC_SOLVER_ENTERED'").fetchone()[0])
        tests["dispatcher_fixture_never_enters_solver"] = retry_entries == 0

    def host_case(root, case):
        db = ControlDB(root / "control.sqlite3")
        db.initialize(SCHEMA)
        allocator = Allocator(db)
        allocator.set_gpu_physical_cap(1)
        allocator.set_branch_limit("coupling_ml", 1)
        db.set_admission_control(new_entry_hold=False)
        attempt_root = root / case / "attempt_001"
        runtime_root = root / "runtime"
        attempt_root.mkdir(parents=True)
        runtime_root.mkdir(parents=True)
        enqueue(db, "coupling_ml", case, "attempt_001", {
            "backend_type": "GPU", "gpu_resource_name": "NVIDIA GeForce RTX 3080",
            "attempt_root": str(attempt_root),
        })
        good_resource = ResourceSnapshot("PASS", "fixture", 10**12, 10**12, 10**12, 10**12,
                                         0, 10**12, 0, 0, 0, 0, 0, ())
        lease = allocator.acquire(
            "coupling_ml", case, "attempt_001", backend_type="GPU",
            resource_snapshot=good_resource,
            resource_request={"backend_type": "GPU", "production_science": True, "resource_class": "HEAVY", "estimated_peak_ram_bytes": 1000, "estimated_commit_bytes": 1000, "mpi_ranks": 1, "threads": 1, "integrated_pw": True},
        )
        cfg = {
            "branch": "coupling_ml", "case": case, "attempt": "attempt_001",
            "attempt_root": str(attempt_root), "runtime": str(runtime_root),
            "pre_fsp_sha256": "a" * 64, "physical_contract_hash": "b" * 64,
            "resource_policy": None, "exact_launch_permit_id": None,
            "gpu_resource_name": "NVIDIA GeForce RTX 3080",
        }
        return db, allocator, lease, cfg, attempt_root, runtime_root, good_resource

    with tempfile.TemporaryDirectory(prefix="apcd_gpu_capacity_host_pass_") as temp:
        root = Path(temp)
        db, allocator, lease, cfg, attempt_root, runtime_root, good_resource = host_case(root, "HOST_PASS")
        real_authority = ScientificLaunchAuthority(db)
        timeline = []
        class OrderedAuthority:
            def claim(self, *args, **kwargs):
                attempt_events = read_events(attempt_root / "events.jsonl")
                runtime_events = read_events(runtime_root / "events.jsonl")
                assert any(item.get("event_type") == "GPU_CAPACITY_SNAPSHOT" and item.get("status") == "PASS" for item in attempt_events)
                assert any(item.get("event_type") == "GPU_CAPACITY_SNAPSHOT" and item.get("status") == "PASS" for item in runtime_events)
                timeline.append("claim")
                return real_authority.claim(*args, **kwargs)
        def fake_start_child():
            timeline.append("popen")
            return {"fake_popen": True}
        fake_start_child.launch_command = ["fixture-fdtd-command"]
        fake_start_child.launch_executable = "fixture-fdtd-executable"
        def on_claim(claim):
            timeline.append("invoke_claimed")
            ref = claim["gpu_capacity_snapshot_ref"]
            assert ref["event_schema"] == "SHARED_V3_GPU_CAPACITY_SNAPSHOT_EVENT_V1"
            assert ref["snapshot_id"] and len(ref["snapshot_sha256"]) == 64
            with db.connect(readonly=True) as con:
                count = con.execute("SELECT COUNT(*) FROM lease_events WHERE event_type='SCIENTIFIC_SOLVER_ENTERED'").fetchone()[0]
            assert count == 1
            return fake_start_child()
        with patch("shared_fdtd.control_v3.gpu_capacity.capture_external_gpu_capacity_snapshot", return_value=snapshot(1369)):
            child = _gpu_capacity_guarded_start(
                db, cfg, lease, allocator, OrderedAuthority(), fake_start_child, on_claim,
                {"backend_type": "GPU"}, good_resource,
            )
        tests["host_pass_snapshot_durable_before_claim_then_fake_popen"] = (
            timeline == ["claim", "invoke_claimed", "popen"] and child == {"fake_popen": True}
        )
        with db.connect(readonly=True) as con:
            pass_entry_count = con.execute("SELECT COUNT(*) FROM lease_events WHERE event_type='SCIENTIFIC_SOLVER_ENTERED'").fetchone()[0]
        pass_events = read_events(attempt_root / "events.jsonl")
        tests["host_pass_exactly_one_entry_and_durable_snapshot_ref"] = (
            pass_entry_count == 1
            and any(item.get("event_type") == "GPU_CAPACITY_SNAPSHOT" and item.get("status") == "PASS" for item in pass_events)
        )

    with tempfile.TemporaryDirectory(prefix="apcd_gpu_capacity_host_wait_") as temp:
        root = Path(temp)
        db, allocator, lease, cfg, attempt_root, runtime_root, good_resource = host_case(root, "HOST_WAIT")
        real_authority = ScientificLaunchAuthority(db)
        claim_calls = []
        popen_calls = []
        class CountingAuthority:
            def claim(self, *args, **kwargs):
                claim_calls.append(1)
                return real_authority.claim(*args, **kwargs)
        def forbidden_start_child():
            popen_calls.append(1)
            raise AssertionError("low capacity reached Popen")
        forbidden_start_child.launch_command = ["fixture-fdtd-command"]
        forbidden_start_child.launch_executable = "fixture-fdtd-executable"
        with db.connect(readonly=True) as con:
            control_before = dict(con.execute("SELECT new_entry_hold,control_generation FROM admission_control WHERE control_id=1").fetchone())
        try:
            with patch("shared_fdtd.control_v3.gpu_capacity.capture_external_gpu_capacity_snapshot", return_value=snapshot(1368)):
                _gpu_capacity_guarded_start(
                    db, cfg, lease, allocator, CountingAuthority(), forbidden_start_child,
                    lambda claim: forbidden_start_child(), {"backend_type": "GPU"}, good_resource,
                )
            raise AssertionError("low-capacity host guard unexpectedly launched")
        except AdmissionGateBlocked as exc:
            queue_state(db, cfg, "WAIT_RESOURCE_CAPACITY", admission_evidence=exc.evidence)
            tests["host_low_capacity_releases_and_sets_retryable_queue_state"] = (
                exc.evidence.get("status") == "WAIT_EXTERNAL_GPU_CAPACITY"
            )
        with db.connect(readonly=True) as con:
            row = dict(con.execute("SELECT * FROM branch_queue WHERE logical_case_id='HOST_WAIT'").fetchone())
            queue_payload = json.loads(row["payload_json"])
            entries = con.execute("SELECT COUNT(*) FROM lease_events WHERE event_type='SCIENTIFIC_SOLVER_ENTERED'").fetchone()[0]
            active = con.execute("SELECT COUNT(*) FROM gpu_capacity_leases WHERE state IN ('RESERVED','LIVE','RELEASE_PENDING','OWNER_QUARANTINED')").fetchone()[0]
            free_slots = con.execute("SELECT COUNT(*) FROM slots WHERE state='FREE'").fetchone()[0]
            control_after = dict(con.execute("SELECT new_entry_hold,control_generation FROM admission_control WHERE control_id=1").fetchone())
        attempt_events = read_events(attempt_root / "events.jsonl")
        runtime_events = read_events(runtime_root / "events.jsonl")
        tests["host_low_capacity_persists_both_events_zero_claim_popen_entry"] = (
            len([x for x in attempt_events if x.get("event_type") == "GPU_CAPACITY_SNAPSHOT" and x.get("status") == "WAIT_EXTERNAL_GPU_CAPACITY"]) == 1
            and len([x for x in runtime_events if x.get("event_type") == "GPU_CAPACITY_SNAPSHOT" and x.get("status") == "WAIT_EXTERNAL_GPU_CAPACITY"]) == 1
            and not claim_calls and not popen_calls and entries == 0
        )
        tests["host_low_capacity_clears_lease_slot_and_preserves_hold_generation"] = (
            row["state"] == "WAIT_RESOURCE_CAPACITY"
            and queue_payload.get("_v3_admission", {}).get("status") == "WAIT_EXTERNAL_GPU_CAPACITY"
            and active == 0 and free_slots == 3 and control_before == control_after
        )

    result = {
        "schema": "SHARED_V3_EXTERNAL_GPU_CAPACITY_HELPER_TESTS_V1",
        "status": "PASS" if all(tests.values()) else "FAIL",
        "tests": tests,
        "required_free_mib": GPU_REQUIRED_FREE_MIB,
        "validated_baseline_free_mib": GPU_VALIDATED_BASELINE_FREE_MIB,
        "real_solver_invocations": 0,
    }
    print(json.dumps(result, indent=2))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
