import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "coupling_ml" / "k6_v2_pipeline" / "serial_queue.py"
spec = importlib.util.spec_from_file_location("coupling_serial_queue_g024_test", SCRIPT)
serial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(serial)


class G024PostentryReconcileTests(unittest.TestCase):
    def test_registry_validation_is_case_scoped_but_strict_for_target_row(self):
        with tempfile.TemporaryDirectory() as temp:
            serial.RUN_ROOT = Path(temp)
            cid, attempt, run_id = "K6GDP2_DEV_G024", "attempt_001", "K6V2_G024_FIXED"
            run_dir = serial.RUN_ROOT / "runs" / cid / attempt / run_id
            run_dir.mkdir(parents=True)
            expected = {"case_id": cid, "attempt_id": attempt, "run_id": run_id,
                        "disposition_sha256": "a" * 64}
            row = {**expected, "state": "FAILED_POSTENTRY", "run_dir": str(run_dir),
                   "solver_invocations": 1, "automatic_replay_count": 0}
            registry = {"runs": [row, {"case_id": "K6GDP2_DEV_G025", "attempt_id": attempt,
                                      "run_id": "later-run", "state": "DONE"}]}
            self.assertEqual(serial.verify_case_scoped_postentry_registry_row(
                registry, expected, "TEST"), row)
            changed = {"runs": [dict(row, state="DONE"), registry["runs"][1]]}
            with self.assertRaisesRegex(serial.StopQueue, "REGISTRY_ROW_IDENTITY_INVALID"):
                serial.verify_case_scoped_postentry_registry_row(changed, expected, "TEST")

    def test_g024_terminalization_preserves_prior_preentry_record(self):
        cid = "K6GDP2_DEV_G024"
        auth = serial.G024_POSTENTRY_AUTHORITY
        ledger = {
            "entered_count": 35, "truth_valid_count": 33, "labels_valid_count": 33,
            "remaining_unentered_count": 93, "automatic_replay_count": 0,
            "training_fits": 0, "p_scale_fits": 0,
            "confirmation_response_access_count": 0,
            "entered_case_ids": ["already-entered"], "truth_valid_case_ids": ["truth-case"],
            "labels_valid_case_ids": ["label-case"],
            "remaining_unentered_case_ids": [cid],
            "case_records": {cid: {"run_id": auth["run_id"],
                "sequence_index": auth["sequence_index"],
                "run_envelope_sha256": auth["run_envelope_sha256"],
                "phase": "RUN_ONE_IN_PROGRESS"}},
            "failed_or_isolated_cases": [
                {"case_id": cid, "run_id": "earlier-preentry", "phase": "FAILED_PREENTRY_NO_ENTRY"},
                {"case_id": cid, "run_id": auth["run_id"], "phase": "FAILED_OR_ISOLATED",
                 "entry_consumed": False, "controller_state": "RUNNING"}],
            "current_case": {"case_id": cid, "run_id": auth["run_id"],
                "sequence_index": auth["sequence_index"], "phase": "FAILED_OR_ISOLATED"},
        }
        evidence = {"case_id": cid, "run_id": auth["run_id"],
            "entry_consumed": True, "solver_invocations": 1,
            "automatic_replay_count": 0, "truth_available": False,
            "quarantine": True, "phase": "FAILED_POSTENTRY_NO_TRUTH",
            "postentry_disposition_sha256": auth["disposition_sha256"],
            "postentry_journal_sha256": auth["journal_file_sha256"],
            "postentry_receipt_file_sha256": auth["receipt_file_sha256"],
            "runner_status_sha256": auth["status_sha256"]}
        current = dict(ledger["current_case"])
        serial.record_g024_failed_postentry_recovery(ledger, current, evidence)
        self.assertIsNone(ledger["current_case"])
        record = ledger["case_records"][cid]
        self.assertEqual(record["phase"], "FAILED_POSTENTRY_NO_TRUTH")
        self.assertTrue(record["entry_consumed"])
        self.assertEqual(record["solver_invocations"], 1)
        rows = ledger["failed_or_isolated_cases"]
        self.assertEqual(rows[0]["phase"], "FAILED_PREENTRY_NO_ENTRY")
        terminal = next(item for item in rows if item.get("run_id") == auth["run_id"])
        self.assertEqual(terminal["phase"], "FAILED_POSTENTRY_NO_TRUTH")
        self.assertEqual(terminal["prior_controller_observation"]["phase"], "FAILED_OR_ISOLATED")
        self.assertEqual(terminal["prior_controller_observation"]["entry_consumed"], False)


if __name__ == "__main__":
    unittest.main()
