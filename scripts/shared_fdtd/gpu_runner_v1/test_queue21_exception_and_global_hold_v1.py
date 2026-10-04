# -*- coding: utf-8 -*-
"""Offline queue21 quarantine and global-hold guard tests; no solver or Lumerical entry."""
import copy
import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adapter
import runner
from queue21_exception_v1 import DispositionError, validate_disposition


def _make_control_db(path, hold_flag=0, generation=27, active_hold=None, health_status="PASS"):
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE admission_control (control_id INTEGER PRIMARY KEY, new_entry_hold INTEGER, control_generation INTEGER, health_status TEXT)")
    connection.execute("CREATE TABLE hold_lifecycle (hold_id TEXT, scope TEXT, status TEXT)")
    connection.execute("INSERT INTO admission_control VALUES (1, ?, ?, ?)", (hold_flag, generation, health_status))
    if active_hold:
        connection.execute("INSERT INTO hold_lifecycle VALUES (?, 'GLOBAL', 'ACTIVE')", (active_hold,))
    connection.commit()
    connection.close()
    return Path(path)


def _manifest(tmp):
    source = Path(tmp) / "source.fsp"
    source.write_bytes(b"offline FSP fixture")
    contract = Path(tmp) / "contract.json"
    contract.write_bytes(b"offline contract fixture")
    return ({
        "case_id": "K6V1_S35", "attempt_id": "attempt_001", "run_id": "guard-test",
        "geometry": [110,145,225,105,185,215],
        "physical_contract_sha256": hashlib.sha256(contract.read_bytes()).hexdigest(),
        "expansion_manifest_sha256": runner.EXPANSION_SHA256,
        "pre_fsp_path": str(source),
        "pre_fsp_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }, contract, source)


class FakeAdapter:
    def __init__(self, _contract):
        self.postprocess_dependency_preflight = {"result": "PASS"}
        self.setup_structural_validate = lambda *_args: {"result": "PASS", "solver_run_called": False}
        self.solver = lambda *_args: (_ for _ in ()).throw(AssertionError("solver must not run in this test"))
        self.fresh_load_validate = lambda *_args: {"scientific_valid": False}
        self.gpu_snapshot = lambda: {"free_mib": 8192}
        self.runner_owner_probe = lambda _root: False
        self.controlled_pre_entry_revalidate = lambda *_args: {
            "schema": "TEST_CONTROLLED_PRE_ENTRY", "result": "PASS",
            "control_generation_sha256": "a" * 64}


class GlobalHoldTests(unittest.TestCase):
    def test_clear_global_control_returns_hashed_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            path = _make_control_db(Path(temp) / "control.sqlite3", 0, 27)
            evidence = adapter.read_global_entry_control(path)
            self.assertEqual(evidence["result"], "PASS")
            self.assertEqual(evidence["control_generation"], 27)
            self.assertEqual(evidence["new_entry_hold"], 0)
            self.assertEqual(len(evidence["snapshot_sha256"]), 64)

    def test_blocked_control_health_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = _make_control_db(Path(temp) / "control.sqlite3", 0, 27, health_status="BLOCKED")
            with self.assertRaisesRegex(runner.RunnerError, "GLOBAL_ENTRY_CONTROL_HEALTH_BLOCKED"):
                adapter.read_global_entry_control(path)

    def test_legacy_boolean_hold_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = _make_control_db(Path(temp) / "control.sqlite3", 1, 26)
            with self.assertRaisesRegex(runner.RunnerError, "GLOBAL_NEW_ENTRY_HOLD_ACTIVE"):
                adapter.read_global_entry_control(path)

    def test_active_global_lifecycle_hold_fails_closed_even_if_boolean_clear(self):
        with tempfile.TemporaryDirectory() as temp:
            path = _make_control_db(Path(temp) / "control.sqlite3", 0, 27, "hold-test")
            with self.assertRaisesRegex(runner.RunnerError, "hold-test"):
                adapter.read_global_entry_control(path)

    def test_missing_or_wrong_schema_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(runner.RunnerError, "GLOBAL_ENTRY_CONTROL_UNREADABLE"):
                adapter.read_global_entry_control(Path(temp) / "missing.sqlite3")
            path = Path(temp) / "wrong.sqlite3"
            sqlite3.connect(path).close()
            with self.assertRaisesRegex(runner.RunnerError, "GLOBAL_ENTRY_CONTROL_SCHEMA_MISSING"):
                adapter.read_global_entry_control(path)

    def _run_cli_capture_guard(self, temp, control_path, controlled=False):
        manifest, contract, source = _manifest(temp)
        if controlled:
            manifest["_controlled_admission"] = {
                "physical_contract_sha256": manifest["physical_contract_sha256"]}
        staged = Path(temp) / "staged.fsp"
        staged.write_bytes(source.read_bytes())
        output = Path(temp) / "output"
        with patch.object(adapter, "GLOBAL_ENTRY_CONTROL_DB_PATH", control_path), \
             patch.object(adapter, "read_cli_manifest", return_value=(manifest, contract)), \
             patch.object(adapter, "NativeAdapter", FakeAdapter), \
             patch.object(adapter, "run_one", return_value={"solver_entered": False}) as run:
            adapter.run_cli("manifest.json", adapter_factory=FakeAdapter, test_output_root=output)
        self.assertIn("pre_entry_guard", run.call_args.kwargs)
        guard = run.call_args.kwargs["pre_entry_guard"]
        return guard, manifest, staged, output

    def test_run_cli_installs_guard_that_blocks_active_hold(self):
        with tempfile.TemporaryDirectory() as temp:
            control = _make_control_db(Path(temp) / "control.sqlite3", 1, 26, "hold-4a6eab94af3b4a6d8510ba2fe32a5b66")
            guard, manifest, staged, output = self._run_cli_capture_guard(temp, control)
            with self.assertRaisesRegex(runner.RunnerError, "GLOBAL_NEW_ENTRY_HOLD_ACTIVE"):
                guard(manifest, output / "run", staged, {"result": "PASS", "solver_run_called": False})

    def test_controlled_route_also_blocks_active_global_hold(self):
        with tempfile.TemporaryDirectory() as temp:
            control = _make_control_db(Path(temp) / "control.sqlite3", 1, 26,
                "hold-4a6eab94af3b4a6d8510ba2fe32a5b66")
            guard, manifest, staged, output = self._run_cli_capture_guard(temp, control, controlled=True)
            with self.assertRaisesRegex(runner.RunnerError, "GLOBAL_NEW_ENTRY_HOLD_ACTIVE"):
                guard(manifest, output / "run", staged, {"result": "PASS", "solver_run_called": False})

    def test_run_cli_guard_records_clear_control_and_rechecks_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            control = _make_control_db(Path(temp) / "control.sqlite3", 0, 27)
            guard, manifest, staged, output = self._run_cli_capture_guard(temp, control)
            evidence = guard(manifest, output / "run", staged, {"result": "PASS", "solver_run_called": False})
            self.assertEqual(evidence["global_entry_control"]["control_generation"], 27)
            self.assertEqual(evidence["global_entry_control_sha256"], evidence["global_entry_control"]["snapshot_sha256"])
            staged.write_bytes(b"changed after setup validation")
            with self.assertRaisesRegex(runner.RunnerError, "STAGED_FSP_CHANGED_BEFORE_SOLVER_ENTRY"):
                guard(manifest, output / "run", staged, {"result": "PASS", "solver_run_called": False})


class Queue21DispositionTests(unittest.TestCase):
    def valid_disposition(self):
        return {
            "schema": "APCD_GPU_RUNNER_QUEUE21_UNRECOVERABLE_EXCEPTION_DISPOSITION_V1",
            "case_id": "K6_5X3_SP237_X_CENTER_ORIGIN_PLUS1",
            "attempt_id": "attempt_001",
            "classification": "C_EVIDENCE_INSUFFICIENT_LINEAGE_NOT_RECOVERABLE",
            "entry_event_ids": [1499, 1506],
            "physical_solver_entry_count": "UNKNOWN",
            "applicable_hold": {"hold_id": "hold-4a6eab94af3b4a6d8510ba2fe32a5b66", "generation": 26, "status": "ACTIVE"},
            "quarantine": {
                "status": "QUARANTINED", "exclude_from_training": True,
                "exclude_from_ranking": True, "exclude_from_scientific_conclusions": True,
                "exclude_from_formal_truth_handoff": True,
                "historical_attempt_restart_allowed": False,
                "replacement_attempt_allowed": False,
                "raw_events_and_truth_preserved": True,
            },
            "owner_decision": {"status": "OWNER_DECISION_REQUIRED", "owner_identity": None,
                "authority_source": None, "signature_sha256": None, "release_authority": None},
            "recovery": {"state": "BLOCKED_PENDING_OWNER_DECISION", "new_entry_authorized": False},
            "diagnostic": {"case_id": "K6V1_EXT02_TWO_AIR_PLANES_DIAG", "attempt_id": "attempt_001",
                "solver_entry_authorized": False, "max_solver_entries": 0,
                "automatic_replay_allowed": False, "training_dataset_eligible": False},
        }

    def test_valid_draft_is_never_release_authority(self):
        result = validate_disposition(self.valid_disposition())
        self.assertEqual(result, {"valid": True, "release_authorized": False, "new_entry_authorized": False})

    def test_physical_count_cannot_be_fabricated(self):
        record = self.valid_disposition(); record["physical_solver_entry_count"] = 1
        with self.assertRaisesRegex(DispositionError, "MUST_REMAIN_UNKNOWN"):
            validate_disposition(record)

    def test_draft_cannot_add_release_authority_or_disable_quarantine(self):
        record = self.valid_disposition(); record["owner_decision"]["release_authority"] = {"signed": True}
        with self.assertRaisesRegex(DispositionError, "DRAFT_CANNOT_CARRY_RELEASE_AUTHORITY"):
            validate_disposition(record)
        record = self.valid_disposition(); record["quarantine"]["exclude_from_training"] = False
        with self.assertRaisesRegex(DispositionError, "QUARANTINE_POLICY_INVALID"):
            validate_disposition(record)

    def test_production_root_requires_pre_entry_guard(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "input.fsp"; source.write_bytes(b"fixture")
            root = Path(temp) / "production-root"
            manifest = {"case_id": "K6V1_S35", "attempt_id": "attempt_001", "run_id": "no-guard",
                "geometry": [110,145,225,105,185,215],
                "physical_contract_sha256": runner.CONTRACT_SHA256,
                "expansion_manifest_sha256": runner.EXPANSION_SHA256,
                "pre_fsp_path": str(source), "pre_fsp_sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
            with patch.object(runner, "PRODUCTION_RUNNER_ROOT", root):
                with self.assertRaisesRegex(runner.RunnerError, "PRODUCTION_PRE_ENTRY_GUARD_REQUIRED"):
                    runner.run_one(manifest, root, lambda *_: None, lambda *_: {},
                        lambda: {"free_mib": 8192}, lambda _root: False)
            self.assertFalse(root.exists())

    def test_v1_manifest_rejects_legacy_or_stale_lease_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "input.fsp"; source.write_bytes(b"fixture")
            base = {"case_id": "K6V1_S35", "attempt_id": "attempt_001", "run_id": "strict-fields",
                "geometry": [110,145,225,105,185,215],
                "physical_contract_sha256": runner.CONTRACT_SHA256,
                "expansion_manifest_sha256": runner.EXPANSION_SHA256,
                "pre_fsp_path": str(source), "pre_fsp_sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
            for field in ("lease_token", "fencing_generation"):
                manifest = dict(base); manifest[field] = "stale"
                with self.subTest(field=field), self.assertRaisesRegex(runner.RunnerError, "MANIFEST_KEYS_INVALID"):
                    runner.validate_manifest(manifest)

    def test_historical_case_is_blocked_for_every_attempt_before_run_dir(self):
        for attempt in ("attempt_001", "attempt_002"):
            with self.subTest(attempt=attempt), tempfile.TemporaryDirectory() as temp:
                source = Path(temp) / "input.fsp"; source.write_bytes(b"fixture")
                manifest = {"case_id": "K6_5X3_SP237_X_CENTER_ORIGIN_PLUS1", "attempt_id": attempt,
                    "run_id": "queue21-retry-" + attempt, "geometry": [1,2,3,4,5,6],
                    "physical_contract_sha256": runner.CONTRACT_SHA256,
                    "expansion_manifest_sha256": runner.EXPANSION_SHA256,
                    "pre_fsp_path": str(source), "pre_fsp_sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
                run_root = Path(temp) / "runner"
                solver_calls = []
                with self.assertRaisesRegex(runner.RunnerError, "HISTORICAL_EXCEPTION_QUARANTINED"):
                    runner.run_one(manifest, run_root, lambda *_: solver_calls.append(True), lambda *_: {},
                        lambda: {"free_mib": 8192}, lambda _root: False)
                self.assertFalse(run_root.exists())
                self.assertEqual(solver_calls, [])


if __name__ == "__main__":
    unittest.main()
