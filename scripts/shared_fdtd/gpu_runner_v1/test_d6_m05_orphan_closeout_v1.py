import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import closeout_d6_m05_orphan_v1 as closeout


class D6M05OrphanCloseoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name).resolve()
        self.run_dir = closeout._run_dir(self.root)
        self.run_dir.mkdir(parents=True)
        self.control = self.root / "control.sqlite3"
        self.control.write_bytes(b"test-control-snapshot")
        self.ledger = self.root / "ledger.json"
        self._write_ledger(as_list=False)
        (self.run_dir / "run.fsp").write_bytes(b"setup")
        fsp_sha = closeout._sha(self.run_dir / "run.fsp")
        self._write_json(self.run_dir / "setup_validation.json", {"result": "PASS"})
        setup_sha = closeout._sha(self.run_dir / "setup_validation.json")
        self.lock = {
            "pid": 101,
            "run_id": closeout.RUN_ID,
            "case_id": closeout.CASE_ID,
            "attempt_id": closeout.ATTEMPT_ID,
        }
        self.active = dict(self.lock, state="SOLVER_ENTERED")
        self.status = {
            "schema": "APCD_GPU_RUN_STATUS_V1",
            "case_id": closeout.CASE_ID,
            "attempt_id": closeout.ATTEMPT_ID,
            "run_id": closeout.RUN_ID,
            "state": "SOLVER_ENTERED",
            "solver_entered": True,
            "solver_invocations": 1,
            "solver_process_lineage": {
                "run_id": closeout.RUN_ID,
                "child_pid": 202,
                "processes": [{"pid": 202}],
            },
            "pre_entry_revalidation_sha256": None,
            "global_entry_control_generation": 27,
            "pre_fsp_sha256": fsp_sha,
            "source_pre_fsp_sha256": fsp_sha,
            "staged_pre_fsp_sha256": fsp_sha,
            "setup_validation_sha256": setup_sha,
        }
        self.manifest = {
            "case_id": closeout.CASE_ID,
            "attempt_id": closeout.ATTEMPT_ID,
            "run_id": closeout.RUN_ID,
            "pre_fsp_sha256": fsp_sha,
            "physical_contract_sha256": "c" * 64,
        }
        self._write_json(self.run_dir / "pre_entry_revalidation.json", {
            "run_id": closeout.RUN_ID, "result": "PASS", "global_entry_control": {"generation": 27},
            "source_fsp_sha256": fsp_sha, "staged_fsp_sha256": fsp_sha,
            "physical_contract_sha256": "c" * 64,
        })
        self.status["pre_entry_revalidation_sha256"] = closeout._sha(self.run_dir / "pre_entry_revalidation.json")
        self._write_json(self.run_dir / "manifest.json", self.manifest)
        self._write_json(self.run_dir / "status.json", self.status)
        self._write_json(self.run_dir / "validation.json", {"state": "PENDING"})
        self._write_json(self.run_dir / "hashes.json", {"state": "PENDING"})
        (self.run_dir / "run_p0.log").write_text("entered once", encoding="utf-8")
        (self.run_dir / "solver.log").write_text("{\"event\":\"ADAPTER_LAUNCH\"}", encoding="utf-8")
        (self.run_dir / "run").mkdir()
        (self.run_dir / "run" / "run_output.h5").write_bytes(b"fixture-h5")
        (self.root / ".runner.lock").write_text(json.dumps(self.lock), encoding="utf-8")
        (self.root / "active_run.json").write_text(json.dumps(self.active), encoding="utf-8")
        self._write_json(self.root / "registry.json", {
            "schema": "APCD_GPU_RUNNER_REGISTRY_V1",
            "runs": [{
                "case_id": closeout.CASE_ID, "attempt_id": closeout.ATTEMPT_ID,
                "run_id": closeout.RUN_ID, "state": "SOLVER_ENTERED",
                "run_dir": str(self.run_dir),
            }],
        })
        self.hold = {
            "new_entry_hold": 0, "health_status": "PASS", "control_generation": 27,
            "active_hold_count": 0, "active_hold_ids": [], "files": {"control.sqlite3": {"sha256": "x"}},
        }

    def tearDown(self):
        self.tmp.cleanup()

    def _write_json(self, path, value):
        pathlib.Path(path).write_text(json.dumps(value, sort_keys=True, indent=2), encoding="utf-8")

    def _write_ledger(self, as_list):
        row = {
            "case_id": closeout.CASE_ID, "run_id": closeout.RUN_ID,
            "phase": "RUN_ONE_IN_PROGRESS",
        }
        records = [row] if as_list else {closeout.CASE_ID: row}
        ledger = {
            "case_records": records,
            "current_case": {"case_id": closeout.CASE_ID, "run_id": closeout.RUN_ID},
            "entered_count": 11, "automatic_replay_count": 0,
            "truth_valid_case_ids": [], "labels_valid_case_ids": [],
        }
        self.ledger.write_text(json.dumps(ledger, sort_keys=True), encoding="utf-8")

    def _process_probe(self, live=False):
        return lambda status, lock, active, run_dir: {
            "available": True,
            "live_related": [{"pid": 202, "reason": "fixture"}] if live else [],
            "census_count": 0,
        }

    def _hold_probe(self, active=False):
        def probe(_):
            value = dict(self.hold)
            if active:
                value["new_entry_hold"] = 1
            return value
        return probe

    def _truth_probe(self, available=False):
        def probe(run_dir, ledger_path):
            raw = pathlib.Path(ledger_path).read_bytes()
            return {
                "truth_available": available, "truth_valid_case": False, "labels_valid_case": False,
                "coupling_ledger_sha256": closeout._sha_bytes(raw),
                "fixture": True,
            }
        return probe

    def _run(self, *, process=None, hold=None, truth=None, fault_after=None):
        return closeout._closeout_one_run(
            self.root, self.control, self.ledger,
            process_probe=process or self._process_probe(),
            hold_probe=hold or self._hold_probe(),
            truth_probe=truth or self._truth_probe(),
            fault_after=fault_after,
        )

    def test_live_target_descendant_engine_blocks(self):
        rows = [
            {"ProcessId": 300, "ParentProcessId": 202, "Name": "python.exe", "CommandLine": "python unrelated"},
            {"ProcessId": 301, "ParentProcessId": 300, "Name": "fdtd-engine-msmpi.exe", "CommandLine": "engine"},
        ]
        proc = type("Proc", (), {"returncode": 0, "stdout": json.dumps(rows), "stderr": ""})()
        with patch.object(closeout.subprocess, "run", return_value=proc):
            result = closeout._process_probe(self.status, self.lock, self.active, self.run_dir)
        self.assertEqual([row["pid"] for row in result["live_related"]], [300, 301])
        with self.assertRaisesRegex(closeout.CloseoutBlocked, "RELATED_CONTROLLER_OR_ENGINE"):
            self._run(process=lambda *args: result)
        self.assertFalse(closeout._closeout_dir(self.root).exists())

    def test_identity_mismatch_blocks_before_claim(self):
        bad = dict(self.active, run_id="another-run")
        (self.root / "active_run.json").write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaisesRegex(closeout.CloseoutBlocked, "IDENTITY_MISMATCH:active"):
            self._run()
        self.assertTrue((self.root / ".runner.lock").exists())
        self.assertFalse(closeout._closeout_dir(self.root).exists())

    def test_active_hold_blocks_before_claim(self):
        with self.assertRaisesRegex(closeout.CloseoutBlocked, "ACTIVE_OR_UNHEALTHY_GLOBAL_HOLD"):
            self._run(hold=self._hold_probe(active=True))
        self.assertTrue((self.root / "active_run.json").exists())
        self.assertFalse(closeout._closeout_dir(self.root).exists())

    def test_truth_available_blocks_before_claim(self):
        with self.assertRaisesRegex(closeout.CloseoutBlocked, "TRUTH_STATE_CHANGED_OR_UNVERIFIED"):
            self._run(truth=self._truth_probe(available=True))
        self.assertTrue((self.root / ".runner.lock").exists())
        self.assertFalse(closeout._closeout_dir(self.root).exists())

    def test_recovery_fence_hash_mismatch_blocks_resume(self):
        with self.assertRaises(closeout.InjectedCloseoutCrash):
            self._run(fault_after="after_disposition_write")
        claim_path = closeout._closeout_dir(self.root) / "claim.json"
        claim = closeout._read_json(claim_path)
        claim["recovery_fence_id"] = "forged-fence"
        self._write_json(claim_path, claim)
        with self.assertRaisesRegex(closeout.CloseoutBlocked, "RECOVERY_CLAIM_HASH_MISMATCH"):
            self._run()
        self.assertTrue((self.root / ".runner.lock").exists())

    def test_lock_hash_mismatch_blocks_resume_without_release(self):
        with self.assertRaises(closeout.InjectedCloseoutCrash):
            self._run(fault_after="after_disposition_write")
        (self.root / ".runner.lock").write_text(json.dumps(dict(self.lock, extra="tampered")), encoding="utf-8")
        with self.assertRaisesRegex(closeout.CloseoutBlocked, "ORPHAN_MARKER_HASH_MISMATCH"):
            self._run()
        self.assertTrue((self.root / ".runner.lock").exists())
        self.assertTrue((self.root / "active_run.json").exists())

    def test_active_marker_hash_mismatch_blocks_resume(self):
        with self.assertRaises(closeout.InjectedCloseoutCrash):
            self._run(fault_after="after_disposition_write")
        (self.root / "active_run.json").write_text(json.dumps(self.active) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(closeout.CloseoutBlocked, "ORPHAN_MARKER_HASH_MISMATCH:active"):
            self._run()

    def test_status_hash_mismatch_blocks_resume(self):
        with self.assertRaises(closeout.InjectedCloseoutCrash):
            self._run(fault_after="after_disposition_write")
        status_path = self.run_dir / "status.json"
        status = closeout._read_json(status_path)
        status["unrelated_change"] = True
        self._write_json(status_path, status)
        with self.assertRaisesRegex(closeout.CloseoutBlocked, "STATUS_HASH_MISMATCH_BEFORE_TERMINALIZATION"):
            self._run()
        self.assertTrue((self.root / ".runner.lock").exists())

    def test_registry_hash_mismatch_blocks_resume(self):
        with self.assertRaises(closeout.InjectedCloseoutCrash):
            self._run(fault_after="after_disposition_write")
        registry_path = self.root / "registry.json"
        registry = closeout._read_json(registry_path)
        registry["unrelated_change"] = True
        self._write_json(registry_path, registry)
        with self.assertRaisesRegex(closeout.CloseoutBlocked, "REGISTRY_HASH_CHANGED_FROM_FRESH_CLAIM"):
            self._run()
        self.assertTrue((self.root / ".runner.lock").exists())

    def test_manifest_hash_mismatch_blocks_resume(self):
        with self.assertRaises(closeout.InjectedCloseoutCrash):
            self._run(fault_after="after_disposition_write")
        manifest_path = self.run_dir / "manifest.json"
        manifest = closeout._read_json(manifest_path)
        manifest["unrelated_change"] = True
        self._write_json(manifest_path, manifest)
        with self.assertRaisesRegex(closeout.CloseoutBlocked, "MANIFEST_HASH_CHANGED_FROM_FRESH_CLAIM"):
            self._run()
        self.assertTrue((self.root / ".runner.lock").exists())

    def test_partial_status_write_resumes_idempotently(self):
        with self.assertRaises(closeout.InjectedCloseoutCrash):
            self._run(fault_after="after_status_write")
        self.assertEqual(closeout._read_json(self.run_dir / "status.json")["state"], "FAILED_POSTENTRY")
        result = self._run()
        self.assertEqual(result["result"], "CLOSED")
        self.assertEqual(result["solver_entry_count"], 1)
        self.assertEqual(result["automatic_replay_count"], 0)
        self.assertFalse((self.root / ".runner.lock").exists())

    def test_partial_registry_write_resumes_without_duplicate_entry(self):
        with self.assertRaises(closeout.InjectedCloseoutCrash):
            self._run(fault_after="after_registry_write")
        result = self._run()
        self.assertEqual(result["result"], "CLOSED")
        row = closeout._read_json(self.root / "registry.json")["runs"][0]
        self.assertEqual(row["state"], "FAILED_POSTENTRY")
        self.assertEqual(row["solver_invocations"], 1)
        self.assertEqual(row["automatic_replay_count"], 0)

    def test_success_archives_exact_markers_and_repeated_call_never_replays(self):
        original_lock_sha = closeout._sha(self.root / ".runner.lock")
        original_active_sha = closeout._sha(self.root / "active_run.json")
        original_fsp_sha = closeout._sha(self.run_dir / "run.fsp")
        original_h5_sha = closeout._sha(self.run_dir / "run" / "run_output.h5")
        result = self._run()
        self.assertEqual(result["result"], "CLOSED")
        cd = closeout._closeout_dir(self.root)
        self.assertEqual(closeout._sha(cd / "released_runner.lock"), original_lock_sha)
        self.assertEqual(closeout._sha(cd / "released_active_run.json"), original_active_sha)
        self.assertFalse((self.root / ".runner.lock").exists())
        self.assertFalse((self.root / "active_run.json").exists())
        status = closeout._read_json(self.run_dir / "status.json")
        self.assertEqual(status["state"], "FAILED_POSTENTRY")
        self.assertEqual(status["solver_invocations"], 1)
        self.assertEqual(closeout._sha(self.run_dir / "run.fsp"), original_fsp_sha)
        self.assertEqual(closeout._sha(self.run_dir / "run" / "run_output.h5"), original_h5_sha)
        second = self._run(process=self._process_probe(live=True))
        self.assertEqual(second["result"], "ALREADY_CLOSED")
        self.assertEqual(second["solver_entry_count"], 1)
        self.assertEqual(second["automatic_replay_count"], 0)

    def test_truth_probe_accepts_list_shaped_case_records_fixture(self):
        try:
            import h5py
            import numpy as np
        except ImportError:
            self.skipTest("h5py/numpy not installed")
        self._write_ledger(as_list=True)
        h5_path = self.run_dir / "run" / "run_output.h5"
        with h5py.File(h5_path, "w") as h5:
            group = h5.create_group("Monitor0")
            group.create_dataset("x", data=np.arange(3))
            group.create_dataset("y", data=np.arange(2))
            group.create_dataset("z", data=np.arange(1))
        result = closeout._truth_probe(self.run_dir, self.ledger)
        self.assertFalse(result["truth_available"])
        self.assertEqual(result["coupling_ledger_sha256"], closeout._sha(self.ledger))


if __name__ == "__main__":
    unittest.main()
