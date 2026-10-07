import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import task_scheduler_v1 as scheduler


class ControllerStartClaimAtomicityTests(unittest.TestCase):
    def test_concurrent_publish_exposes_only_one_complete_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "start_claim.json"
            barrier = threading.Barrier(2)
            real_link = scheduler.os.link

            def synchronized_link(source, destination):
                barrier.wait(timeout=10)
                return real_link(source, destination)

            with patch.object(scheduler.os, "link", side_effect=synchronized_link):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [pool.submit(scheduler._create_exclusive_json, path,
                               {"schema": "claim-v1", "writer": n}) for n in (1, 2)]
                    results = [future.result(timeout=15) for future in futures]

            self.assertEqual(sorted(results), [False, True])
            claim = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(claim["schema"], "claim-v1")
            self.assertIn(claim["writer"], (1, 2))
            self.assertEqual(list(Path(temp).glob("start_claim.json.tmp-*")), [])

    def test_existing_claim_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "start_claim.json"
            original = {"schema": "existing-claim", "writer": "first"}
            path.write_text(json.dumps(original), encoding="utf-8")
            self.assertFalse(scheduler._create_exclusive_json(
                path, {"schema": "replacement", "writer": "second"}))
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), original)


if __name__ == "__main__":
    unittest.main()
