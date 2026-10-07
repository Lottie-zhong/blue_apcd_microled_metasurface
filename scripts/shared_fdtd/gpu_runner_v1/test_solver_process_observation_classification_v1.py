import tempfile
import unittest
from pathlib import Path

import adapter

class SolverProcessObservationClassificationTests(unittest.TestCase):
    def test_license_startup_failure_is_not_reported_as_invalid_observation(self):
        with tempfile.TemporaryDirectory() as temp:
            log = Path(temp) / "child.log"
            log.write_text("Failed to set up Ansys license sharing. Could not connect to Ansys license server.", encoding="utf-8")
            event = {"observation": "standalone_child_returned", "child_log": str(log), "returncode": 0}
            self.assertEqual(adapter.solver_process_observation_failure(event, temp),
                             "LUMERICAL_LICENSE_STARTUP_FAILED")

    def test_clean_child_return_without_solver_process_has_specific_error(self):
        with tempfile.TemporaryDirectory() as temp:
            log = Path(temp) / "child.log"; log.write_text("", encoding="utf-8")
            self.assertEqual(adapter.solver_process_observation_failure(
                {"observation": "standalone_child_returned", "child_log": str(log)}, temp),
                "SOLVER_PROCESS_NOT_OBSERVED_CHILD_RETURNED")

    def test_unknown_observation_stays_fail_closed(self):
        self.assertEqual(adapter.solver_process_observation_failure({"observation": "unknown"}, "."),
                         "SOLVER_PROCESS_OBSERVATION_INVALID")

    def test_confirmed_solver_process_is_accepted(self):
        self.assertIsNone(adapter.solver_process_observation_failure(
            {"observation": "new_solver_process", "child_pid": 1}, "."))

if __name__ == "__main__":
    unittest.main()
