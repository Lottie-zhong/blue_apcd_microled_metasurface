import tempfile
import unittest
from pathlib import Path

import closeout_g024_load_only_v1 as closeout

class FakeObject:
    def __init__(self, name, typ): self.values = {"name": name, "type": typ}
    def __getitem__(self, key): return self.values[key]

class FakeFDTD:
    def __init__(self, **kwargs): self.calls = []; self.closed = False
    def load(self, path): self.calls.append(("load", path))
    def selectall(self): self.calls.append(("selectall",))
    def getAllSelectedObjects(self):
        return [FakeObject(n, "DFTMonitor") for n in closeout.EXPECTED_MONITORS]
    def getnamed(self, name, prop):
        return {"monitor type": "2D Z-normal", "z": 0.0, "x span": 1.0e-6,
                "y span": 2.0e-7, "use wavelength spacing": 1.0,
                "frequency points": 21.0}[prop]
    def getresult(self, name, result):
        self.calls.append(("getresult", name, result))
        raise RuntimeError("Can not find result '" + result + "' in the result provider '" + name + "'")
    def close(self): self.closed = True

class FakeLumapi:
    def __init__(self): self.session = None
    def FDTD(self, **kwargs): self.session = FakeFDTD(**kwargs); return self.session

class G024LoadOnlyCloseoutTests(unittest.TestCase):
    def test_load_only_confirms_setup_but_no_saved_monitor_truth(self):
        with tempfile.TemporaryDirectory() as temp:
            fsp = Path(temp) / "run.fsp"
            fsp.write_bytes(b"fixture bytes")
            # Override only the exact production pin for this synthetic unit fixture.
            old = closeout._sha
            old_expected = closeout._EXPECTED_FSP_SHA
            try:
                fake = FakeLumapi()
                original_sha = closeout._sha(fsp)
                closeout.EXPECTED_TEST_FSP_SHA = original_sha
                closeout._EXPECTED_FSP_SHA = original_sha
                probe = closeout.perform_load_only_probe(fsp, lumapi_module=fake)
            finally:
                closeout._sha = old
                closeout._EXPECTED_FSP_SHA = old_expected
            self.assertEqual(probe["result"], "LOAD_ONLY_PASS")
            self.assertEqual(probe["recoverability"], "NOT_RECOVERABLE_NO_SAVED_MONITOR_RESULTS")
            self.assertFalse(probe["solver_run_called"])
            self.assertFalse(probe["save_called"])
            self.assertTrue(fake.session.closed)
            self.assertEqual(closeout._sha(fsp), original_sha)
            self.assertFalse(any(call[0] in {"run", "save"} for call in fake.session.calls))

    def test_terminal_evidence_requires_entry_consumed_and_no_replay(self):
        evidence = {
            "runner_status": {"case_id": closeout.CASE_ID, "attempt_id": closeout.ATTEMPT_ID,
                              "run_id": closeout.RUN_ID, "state": "FAILED_POSTENTRY",
                              "solver_entered": True, "solver_invocations": 1, "replay_count": 0},
            "runner_result": {"state": "TERMINAL", "result": {"request_id": closeout.REQUEST_ID,
                              "exit_code": 2, "solver_entered": True}},
            "registry_row": {"case_id": closeout.CASE_ID, "attempt_id": closeout.ATTEMPT_ID,
                              "run_id": closeout.RUN_ID, "state": "FAILED_POSTENTRY"},
            "load_probe": {"recoverability": "NOT_RECOVERABLE_NO_SAVED_MONITOR_RESULTS"},
            "process_census": {"related_processes": [], "engine_processes": [], "queue_execution_processes": []},
            "runner_markers_absent": True,
            "controller_query": {"state": "CONTROLLER_EXITED_NEEDS_RECONCILIATION", "task": {"State": "Ready"}},
            "coupling_ledger": {"sha256": closeout.EXPECTED_LEDGER_SHA256, "entered_count": 35,
                                "automatic_replay_count": 0, "g024_row": {"run_id": closeout.RUN_ID}},
        }
        disposition = closeout.validate_terminal_evidence(evidence)
        self.assertEqual(disposition["result"], "FAILED_POSTENTRY_NO_TRUTH")
        self.assertEqual(disposition["solver_invocations"], 1)
        self.assertFalse(disposition["scientific_valid"])
        evidence["runner_status"]["solver_invocations"] = 2
        with self.assertRaisesRegex(closeout.CloseoutBlocked, "RUNNER_POSTENTRY_TERMINAL_STATE_INVALID"):
            closeout.validate_terminal_evidence(evidence)

    def test_terminal_evidence_rejects_any_related_live_process(self):
        evidence = {
            "runner_status": {"case_id": closeout.CASE_ID, "attempt_id": closeout.ATTEMPT_ID,
                              "run_id": closeout.RUN_ID, "state": "FAILED_POSTENTRY",
                              "solver_entered": True, "solver_invocations": 1, "replay_count": 0},
            "runner_result": {"state": "TERMINAL", "result": {"request_id": closeout.REQUEST_ID,
                              "exit_code": 2, "solver_entered": True}},
            "registry_row": {"case_id": closeout.CASE_ID, "attempt_id": closeout.ATTEMPT_ID,
                              "run_id": closeout.RUN_ID, "state": "FAILED_POSTENTRY"},
            "load_probe": {"recoverability": "NOT_RECOVERABLE_NO_SAVED_MONITOR_RESULTS"},
            "process_census": {"related_processes": [{"pid": 45644}], "engine_processes": [], "queue_execution_processes": []},
            "runner_markers_absent": True,
            "controller_query": {"state": "CONTROLLER_EXITED_NEEDS_RECONCILIATION", "task": {"State": "Ready"}},
            "coupling_ledger": {"sha256": closeout.EXPECTED_LEDGER_SHA256, "entered_count": 35,
                                "automatic_replay_count": 0, "g024_row": {"run_id": closeout.RUN_ID}},
        }
        with self.assertRaisesRegex(closeout.CloseoutBlocked, "RELATED_PROCESS_OR_ENGINE_PRESENT"):
            closeout.validate_terminal_evidence(evidence)

if __name__ == "__main__":
    unittest.main()
