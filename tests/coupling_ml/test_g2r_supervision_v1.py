import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts" / "coupling_ml"))
import g2r_supervision_v1 as s


class G2RSupervisionTests(unittest.TestCase):
    def test_a_durable_event_is_append_only(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "events.jsonl"
            s.durable_event(p, "A")
            s.durable_event(p, "B")
            self.assertEqual([json.loads(x)["event"] for x in p.read_text().splitlines()], ["A", "B"])

    def test_b_solver_return_is_not_completion(self):
        self.assertEqual(s.completion_gate(solver_entered=True, solver_returned=False, post_exists=False, load_only_status="UNVALIDATED", scientific_status="UNVALIDATED")[0], False)

    def test_c_entry_then_lineage_loss_is_failure_after_entry(self):
        x = s.classify_after_exit(ledger={"solver_entered": True, "solver_returned": False}, process_alive=False, post_exists=False, raw_exists=False, load_only_status="UNVALIDATED", scientific_status="UNVALIDATED")
        self.assertEqual(x["class"], "FAILED_AFTER_ENTRY_NO_RECOVERABLE_TRUTH")

    def test_d_live_process_is_not_declared_lost(self):
        x = s.classify_after_exit(ledger={"solver_entered": True}, process_alive=True, post_exists=False, raw_exists=False, load_only_status="UNVALIDATED", scientific_status="UNVALIDATED")
        self.assertEqual(x["class"], "FAILED_AFTER_ENTRY_AMBIGUOUS")

    def test_e_persisted_truth_allows_zero_solver_recovery(self):
        x = s.classify_after_exit(ledger={"solver_entered": True, "solver_returned": True}, process_alive=False, post_exists=True, raw_exists=True, load_only_status="PASS", scientific_status="PASS")
        self.assertEqual(x["class"], "ZERO_SOLVER_RECOVERY_ALLOWED")

    def test_f_pre_entry_failure_is_distinct(self):
        x = s.classify_after_exit(ledger={"solver_entered": False}, process_alive=False, post_exists=False, raw_exists=False, load_only_status="UNVALIDATED", scientific_status="UNVALIDATED")
        self.assertEqual(x["class"], "FAILED_PRE_ENTRY")

    def test_g_release_requires_scientific_validity_and_ownership(self):
        self.assertEqual(s.release_gate(terminal_state="SCIENTIFIC_VALID", ownership="FOREIGN")[0], False)
        self.assertEqual(s.release_gate(terminal_state="SCIENTIFIC_VALID", ownership="OWNER")[0], True)

    def test_h_resume_uses_last_durable_event(self):
        self.assertEqual(s.resume_classification([{"event": "SCIENTIFIC_SOLVER_ENTERED"}]), "FAILED_AFTER_ENTRY_REQUIRES_FORENSIC_RECOVERY")

    def test_i_heartbeat_is_durable(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "heartbeat.json"
            s.heartbeat(p, controller_pid=1, worker_pid=2, state="RUNNING", solver_pids=[3])
            self.assertEqual(json.loads(p.read_text())["state"], "RUNNING")

    def test_j_replay_delta_never_invents_a_run(self):
        self.assertEqual(s.replay_delta({"solver_entered": True, "run_invocation_count": 1}), 0)
        self.assertEqual(s.replay_delta({"solver_entered": False, "run_invocation_count": 0}), 0)


if __name__ == "__main__":
    unittest.main()
