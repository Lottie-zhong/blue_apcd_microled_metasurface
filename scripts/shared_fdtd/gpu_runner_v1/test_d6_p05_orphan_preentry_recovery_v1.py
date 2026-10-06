# -*- coding: utf-8 -*-
"""Synthetic zero-solver tests for the fixed P05 orphan-preentry recovery."""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d6_p05_recovery as recovery
import runner


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class P05RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.case = recovery.CASE_ID
        self.attempt = recovery.ATTEMPT_ID
        self.run_id = recovery.RUN_ID
        self.root = self.base / "runner"
        self.run_dir = self.root / "runs" / self.case / self.attempt / self.run_id
        self.run_dir.mkdir(parents=True)
        self.external = self.base / "external"
        self.external.mkdir()
        self.pins = {
            "case_id": self.case, "attempt_id": self.attempt, "run_id": self.run_id,
            "lock_pid": 34072, "control_generation": 27,
        }

        def write_bytes(name, payload):
            path = self.external / name
            path.write_bytes(payload)
            return {"path": str(path), "sha256": sha(path)}

        self.authority = write_bytes("authority.json", b"authority")
        self.source = write_bytes("source_manifest.json", b"source manifest")
        self.contract = write_bytes("contract.json", b"contract")
        self.pre_fsp = write_bytes("runtime.fsp", b"fixture fsp")
        self.pins.update({
            "contract_sha256": self.contract["sha256"],
            "expansion_sha256": "1" * 64,
            "pre_fsp_sha256": self.pre_fsp["sha256"],
            "source_manifest_sha256": self.source["sha256"],
            "authority_sha256": self.authority["sha256"],
            "control_db_sha256": "2" * 64,
        })
        env_path = self.external / "envelope.json"
        envelope = {
            "case_id": self.case, "attempt_id": self.attempt, "run_id": self.run_id,
            "physical_contract_path": self.contract["path"],
            "physical_contract_sha256": self.contract["sha256"],
            "expansion_manifest_sha256": self.pins["expansion_sha256"],
            "pre_fsp_path": self.pre_fsp["path"], "pre_fsp_sha256": self.pre_fsp["sha256"],
            "controlled_admission": {
                "route_version": "APCD_GPU_RUNNER_VERSIONED_CONTROLLED_ADMISSION_V1",
                "case_class": "K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1",
                "source_manifest_path": self.source["path"],
                "source_manifest_sha256": self.source["sha256"],
                "authority_path": self.authority["path"],
                "authority_sha256": self.authority["sha256"],
            },
        }
        runner.atomic_json(env_path, envelope)
        self.envelope = {"path": str(env_path), "sha256": sha(env_path)}
        ledger_path = self.external / "ledger.json"
        ledger = {
            "entered_count": 11, "truth_valid_count": 10,
            "automatic_replay_count": 0,
            "case_records": {self.case: {
                "phase": "RUN_ONE_IN_PROGRESS", "run_id": self.run_id,
                "sequence_index": 12, "run_envelope_sha256": self.envelope["sha256"],
            }},
            "current_case": {"case_id": self.case, "run_id": self.run_id},
        }
        runner.atomic_json(ledger_path, ledger)
        self.ledger = {"path": str(ledger_path), "sha256": sha(ledger_path)}
        self.ledger_sha256 = self.ledger["sha256"]
        self.pins["envelope_sha256"] = self.envelope["sha256"]
        self.pins["external_artifacts"] = {
            "envelope": self.envelope, "ledger": self.ledger,
            "source_manifest": self.source, "authority": self.authority,
            "contract": self.contract, "pre_fsp": self.pre_fsp,
        }

        manifest = {
            "case_id": self.case, "attempt_id": self.attempt, "run_id": self.run_id,
            "geometry": [220, 195, 210, 150, 140, 215],
            "physical_contract_sha256": self.pins["contract_sha256"],
            "expansion_manifest_sha256": self.pins["expansion_sha256"],
            "pre_fsp_path": self.pre_fsp["path"],
            "pre_fsp_sha256": self.pre_fsp["sha256"],
        }
        runner.atomic_json(self.run_dir / "manifest.json", manifest)
        self.pins["manifest_sha256"] = sha(self.run_dir / "manifest.json")
        self.status = {
            "schema": "APCD_GPU_RUN_STATUS_V1", "case_id": self.case,
            "attempt_id": self.attempt, "run_id": self.run_id,
            "state": "PENDING", "solver_entered": False,
            "solver_invocations": 0, "created_unix": 1.0,
        }
        runner.atomic_json(self.run_dir / "status.json", self.status)
        self.pins["pending_status_sha256"] = sha(self.run_dir / "status.json")
        runner.atomic_json(self.run_dir / "validation.json", {"state": "PENDING"})
        runner.atomic_json(self.run_dir / "hashes.json", {"state": "PENDING"})
        self.pins["pending_doc_sha256"] = sha(self.run_dir / "validation.json")
        self.pins["empty_sha256"] = hashlib.sha256(b"").hexdigest()
        (self.run_dir / "solver.log").write_bytes(b"")

        registry = {"schema": "APCD_GPU_RUNNER_REGISTRY_V1", "runs": [{
            "case_id": self.case, "attempt_id": self.attempt, "run_id": self.run_id,
            "state": "PENDING", "run_dir": str(self.run_dir),
        }]}
        runner.atomic_json(self.root / "registry.json", registry)
        self.pins["registry_sha256"] = sha(self.root / "registry.json")
        lock = {"pid": self.pins["lock_pid"], "run_id": self.run_id,
                "case_id": self.case, "attempt_id": self.attempt}
        (self.root / ".runner.lock").write_bytes(json.dumps(lock).encode("utf-8"))
        self.pins["lock_sha256"] = sha(self.root / ".runner.lock")
        self.controls = [{
            "schema": "APCD_GPU_RUNNER_GLOBAL_ENTRY_HOLD_SNAPSHOT_V1",
            "result": "PASS", "control_db_sha256": self.pins["control_db_sha256"],
            "control_generation": self.pins["control_generation"],
            "health_status": "PASS", "new_entry_hold": 0,
            "active_global_hold_ids": [], "snapshot_sha256": "3" * 64,
        }]
        self.processes = [[{
            "ProcessId": 999, "ParentProcessId": 1,
            "Name": "fdtd-solutions.exe", "CommandLine": 'fdtd-solutions.exe -server -hide ""',
        }]]

    def tearDown(self):
        self.temp.cleanup()

    def recover(self, failpoint=None):
        return recovery._recover_fixed_run(
            self.root, self.pins, lambda: list(self.processes[-1]),
            lambda: dict(self.controls[-1]), failpoint=failpoint)

    def test_recovers_exact_orphan_to_failed_preentry_and_archives_lock(self):
        result = self.recover()
        self.assertEqual(result["result"], "RECOVERED_FAILED_PREENTRY")
        self.assertFalse(result["solver_entered"])
        self.assertEqual(result["solver_invocations"], 0)
        self.assertEqual(result["automatic_replay_count"], 0)
        self.assertFalse((self.root / ".runner.lock").exists())
        archive = Path(result["archived_lock_path"])
        self.assertEqual(sha(archive), self.pins["lock_sha256"])
        status = runner.read_json(self.run_dir / "status.json")
        self.assertEqual(status["state"], "FAILED_PREENTRY")
        self.assertFalse(status["solver_entered"])
        self.assertEqual(status["solver_invocations"], 0)
        registry = runner.read_json(self.root / "registry.json")
        self.assertEqual(registry["runs"][0]["state"], "FAILED_PREENTRY")
        self.assertFalse((self.root / "active_run.json").exists())
        disposition = runner.read_json(self.run_dir / recovery._RECOVERY_DIR_NAME / recovery._DISPOSITION_NAME)
        self.assertFalse(disposition["attempt_budget_consumed"])
        self.assertFalse(disposition["same_run_id_reuse_supported"])

    def test_repeat_call_is_idempotent(self):
        first = self.recover()
        second = self.recover()
        self.assertEqual(second["result"], "ALREADY_RECOVERED")
        self.assertEqual(first["status_sha256"], second["status_sha256"])
        self.assertEqual(first["registry_sha256"], second["registry_sha256"])
        self.assertEqual(first["archived_lock_sha256"], second["archived_lock_sha256"])
        journal = runner.read_json(self.run_dir / recovery._RECOVERY_DIR_NAME / recovery._JOURNAL_NAME)
        event_types = [event["event_type"] for event in journal["events"]]
        self.assertEqual(len(event_types), len(set(event_types)))

    def test_resume_after_status_write_finishes_without_retransition(self):
        def failpoint(step):
            if step == "AFTER_STATUS_WRITE":
                raise RuntimeError("simulated interruption")
        with self.assertRaisesRegex(RuntimeError, "simulated interruption"):
            self.recover(failpoint)
        self.assertEqual(runner.read_json(self.run_dir / "status.json")["state"], "FAILED_PREENTRY")
        self.assertEqual(runner.read_json(self.root / "registry.json")["runs"][0]["state"], "PENDING")
        result = self.recover()
        self.assertEqual(result["result"], "RECOVERED_FAILED_PREENTRY")
        self.assertEqual(runner.read_json(self.root / "registry.json")["runs"][0]["state"], "FAILED_PREENTRY")

    def test_resume_after_registry_write_finishes_lock_release(self):
        def failpoint(step):
            if step == "AFTER_REGISTRY_WRITE":
                raise RuntimeError("simulated interruption")
        with self.assertRaisesRegex(RuntimeError, "simulated interruption"):
            self.recover(failpoint)
        self.assertEqual(runner.read_json(self.root / "registry.json")["runs"][0]["state"], "FAILED_PREENTRY")
        self.assertTrue((self.root / ".runner.lock").exists())
        self.assertEqual(self.recover()["result"], "RECOVERED_FAILED_PREENTRY")
        self.assertFalse((self.root / ".runner.lock").exists())

    def test_resume_after_atomic_lock_archive_is_idempotent(self):
        def failpoint(step):
            if step == "AFTER_LOCK_ARCHIVE":
                raise RuntimeError("simulated interruption")
        with self.assertRaisesRegex(RuntimeError, "simulated interruption"):
            self.recover(failpoint)
        result = self.recover()
        self.assertEqual(result["result"], "ALREADY_RECOVERED")
        self.assertFalse((self.root / ".runner.lock").exists())

    def test_fails_closed_for_target_pid_or_descendant(self):
        self.processes.append([{"ProcessId": 34072, "ParentProcessId": 1,
                                "Name": "python.exe", "CommandLine": "unrelated"}])
        with self.assertRaisesRegex(recovery.RecoveryError, "TARGET_PROCESS_OR_ENGINE_PRESENT"):
            self.recover()
        self.assertTrue((self.root / ".runner.lock").exists())
        self.assertFalse((self.run_dir / recovery._RECOVERY_DIR_NAME).exists())

    def test_fails_closed_for_target_descendant_or_any_live_engine(self):
        self.processes.append([{"ProcessId": 77, "ParentProcessId": 34072,
                                "Name": "python.exe", "CommandLine": "unrelated"}])
        with self.assertRaisesRegex(recovery.RecoveryError, "TARGET_PROCESS_OR_ENGINE_PRESENT"):
            self.recover()
        self.processes.append([{"ProcessId": 88, "ParentProcessId": 1,
                                "Name": "fdtd-engine-msmpi.exe", "CommandLine": "engine"}])
        with self.assertRaisesRegex(recovery.RecoveryError, "TARGET_PROCESS_OR_ENGINE_PRESENT"):
            self.recover()

    def test_fails_closed_while_coupling_serial_queue_is_executing(self):
        self.processes.append([{"ProcessId": 204, "ParentProcessId": 1,
                                "Name": "python.exe",
                                "CommandLine": r"python D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\scripts\coupling_ml\k6_v2_pipeline\serial_queue.py --execute"}])
        with self.assertRaisesRegex(recovery.RecoveryError, "COUPLING_SERIAL_QUEUE_EXECUTION_PRESENT"):
            self.recover()
        self.assertTrue((self.root / ".runner.lock").exists())

    def test_fails_closed_for_active_marker_or_extra_solver_output(self):
        (self.root / "active_run.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(recovery.RecoveryError, "ACTIVE_RUN_MARKER_PRESENT"):
            self.recover()
        (self.root / "active_run.json").unlink()
        (self.run_dir / "run.fsp").write_bytes(b"unexpected output")
        with self.assertRaisesRegex(recovery.RecoveryError, "TARGET_RUN_DIRECTORY_CONTENTS_CHANGED"):
            self.recover()

    def test_fails_closed_for_changed_registry_status_ledger_or_control(self):
        self.controls.append(dict(self.controls[-1], new_entry_hold=1))
        with self.assertRaisesRegex(recovery.RecoveryError, "CONTROL_STATE_NOT_PINNED_HEALTHY"):
            self.recover()
        self.controls.pop()
        self.pins["external_artifacts"]["ledger"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(recovery.RecoveryError, "EXTERNAL_ARTIFACT_CHANGED:ledger"):
            self.recover()
        self.pins["external_artifacts"]["ledger"]["sha256"] = self.ledger_sha256
        bad_status = dict(self.status, solver_entered=True)
        runner.atomic_json(self.run_dir / "status.json", bad_status)
        with self.assertRaisesRegex(recovery.RecoveryError, "TARGET_RUN_ARTIFACT_HASH_MISMATCH|TARGET_NOT_FRESH_PENDING"):
            self.recover()

    def test_fails_closed_for_concurrent_recovery(self):
        recovery_dir = self.run_dir / recovery._RECOVERY_DIR_NAME
        recovery_dir.mkdir()
        mutex = recovery_dir / recovery._MUTEX_NAME
        with mutex.open("wb") as stream:
            stream.write(b"\0")
        hold = recovery._lock_recovery_mutex(mutex)
        try:
            with self.assertRaisesRegex(recovery.RecoveryError, "RECOVERY_ALREADY_RUNNING"):
                self.recover()
        finally:
            recovery._unlock_recovery_mutex(hold)


class RunnerSameAttemptFreshRunIdTests(unittest.TestCase):
    """Runner-level serial semantics: pre-entry failure consumes no entry budget."""
    def test_same_case_attempt_new_run_id_waits_without_entry_and_old_id_is_not_reusable(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            source = base / "prefsp.fsp"
            source.write_bytes(b"fixture setup")
            case = "K6LDA1_DEV_D6_P05"
            old_id = "orphan-run-001"
            new_id = "reconciled-run-002"
            case_dir = base / "runner" / "runs" / case / "attempt_001"
            old_dir = case_dir / old_id
            old_dir.mkdir(parents=True)
            manifest = {
                "case_id": case, "attempt_id": "attempt_001", "run_id": old_id,
                "geometry": [220, 195, 210, 150, 140, 215],
                "physical_contract_sha256": runner.CONTRACT_SHA256,
                "expansion_manifest_sha256": runner.EXPANSION_SHA256,
                "pre_fsp_path": str(source), "pre_fsp_sha256": sha(source),
            }
            runner.atomic_json(old_dir / "manifest.json", manifest)
            old_status = {"schema": "APCD_GPU_RUN_STATUS_V1", "case_id": case,
                          "attempt_id": "attempt_001", "run_id": old_id,
                          "state": "FAILED_PREENTRY", "solver_entered": False,
                          "solver_invocations": 0, "automatic_replay_count": 0}
            runner.atomic_json(old_dir / "status.json", old_status)
            runner.atomic_json(base / "runner" / "registry.json", {
                "schema": "APCD_GPU_RUNNER_REGISTRY_V1",
                "runs": [{"case_id": case, "attempt_id": "attempt_001", "run_id": old_id,
                          "state": "FAILED_PREENTRY", "run_dir": str(old_dir)}],
            })
            manifest["run_id"] = new_id
            calls = []
            result = runner.run_one(
                manifest, base / "runner", lambda *_: calls.append("solver"),
                lambda *_: {"fresh_load_verified": True, "monitors_valid": True,
                            "state_valid": True, "scientific_valid": True},
                lambda: {"free_mib": 0, "processes": []}, lambda _root: False)
            self.assertEqual(result["result"], "WAIT_GPU_CAPACITY")
            self.assertEqual(calls, [])
            rows = runner.read_json(base / "runner" / "registry.json")["runs"]
            target = [row for row in rows if row["case_id"] == case and row["attempt_id"] == "attempt_001"]
            self.assertEqual([(row["run_id"], row["state"]) for row in target],
                             [(old_id, "FAILED_PREENTRY"), (new_id, "PENDING")])
            self.assertEqual(sum(row["state"] in runner.ENTRY_STATES for row in target), 0)
            self.assertEqual(runner.read_json(Path(result["run_dir"]) / "status.json")["solver_invocations"], 0)
            with self.assertRaisesRegex(runner.RunnerError, "DUPLICATE_RUN_ID"):
                runner.run_one(dict(manifest, run_id=old_id), base / "runner",
                               lambda *_: calls.append("old"), lambda *_: {},
                               lambda: {"free_mib": 8192, "processes": []}, lambda _root: False)
            with self.assertRaisesRegex(runner.RunnerError, "PENDING_RUN_ID_CONFLICT"):
                runner.run_one(dict(manifest, run_id="third-run"), base / "runner",
                               lambda *_: calls.append("third"), lambda *_: {},
                               lambda: {"free_mib": 8192, "processes": []}, lambda _root: False)
            self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
