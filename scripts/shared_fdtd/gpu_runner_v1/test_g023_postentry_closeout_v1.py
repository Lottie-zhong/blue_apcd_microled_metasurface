import hashlib
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

import h5py

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import closeout_g023_postentry_v1 as g023


class G023TruthProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.run_dir = g023._run_dir(self.root)
        (self.run_dir / "run").mkdir(parents=True)
        for name in ("validation.json", "hashes.json"):
            (self.run_dir / name).write_text('{"state":"PENDING"}', encoding="utf-8")
        with h5py.File(self.run_dir / "run" / "run_output.h5", "w") as h5:
            monitor = h5.create_group("Monitor0")
            for name in ("x", "y", "z"):
                monitor.create_dataset(name, data=[0.0])
        self.ledger_path = self.root / "ledger.json"
        self.ledger = {
            "entered_count": g023.EXPECTED_ENTRY_COUNT,
            "automatic_replay_count": 0,
            "current_case": {"case_id": g023.CASE_ID, "run_id": g023.RUN_ID,
                             "phase": "RUN_ONE_IN_PROGRESS", "sequence_index": g023.EXPECTED_SEQUENCE_INDEX},
            "truth_valid_case_ids": [], "labels_valid_case_ids": [],
            "case_records": {g023.CASE_ID: {"case_id": g023.CASE_ID,
                "attempt_id": g023.ATTEMPT_ID, "run_id": g023.RUN_ID,
                "phase": "RUN_ONE_IN_PROGRESS", "sequence_index": g023.EXPECTED_SEQUENCE_INDEX}},
        }
        self._write_ledger()

    def tearDown(self):
        self.tmp.cleanup()

    def _write_ledger(self):
        self.ledger_path.write_text(json.dumps(self.ledger), encoding="utf-8")

    def _with_current_sha(self):
        digest = hashlib.sha256(self.ledger_path.read_bytes()).hexdigest()
        return patch.object(g023, "EXPECTED_LEDGER_SHA256", digest)

    def test_coordinates_only_h5_is_not_truth(self):
        with self._with_current_sha():
            result = g023._truth_probe(self.run_dir, self.ledger_path)
        self.assertIs(result["truth_available"], False)
        self.assertEqual(result["non_coordinate_dataset_paths"], [])
        self.assertEqual(result["expected_entered_count"], 35)

    def test_rejects_changed_or_nonzero_replay_ledger(self):
        self.ledger["automatic_replay_count"] = 1
        self._write_ledger()
        with self._with_current_sha():
            with self.assertRaisesRegex(g023.CloseoutBlocked, "ENTRY_OR_REPLAY_COUNT"):
                g023._truth_probe(self.run_dir, self.ledger_path)

    def test_rejects_unpinned_ledger_bytes(self):
        with patch.object(g023, "EXPECTED_LEDGER_SHA256", "0" * 64):
            with self.assertRaisesRegex(g023.CloseoutBlocked, "LEDGER_SHA256_CHANGED"):
                g023._truth_probe(self.run_dir, self.ledger_path)

    def test_rejects_field_data_in_truth_h5(self):
        with h5py.File(self.run_dir / "run" / "run_output.h5", "a") as h5:
            h5["Monitor0"].create_dataset("Ex", data=[1.0])
        with self._with_current_sha():
            with self.assertRaisesRegex(g023.CloseoutBlocked, "H5_CONTAINS_NON_COORDINATE"):
                g023._truth_probe(self.run_dir, self.ledger_path)


if __name__ == "__main__":
    unittest.main()
