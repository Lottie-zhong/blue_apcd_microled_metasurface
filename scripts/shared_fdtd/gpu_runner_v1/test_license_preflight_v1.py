import hashlib
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from license_preflight_v1 import run_lumerical_license_preflight

class FakeSession:
    def __init__(self, calls, fail=False):
        self.calls = calls
        self.fail = fail
    def eval(self, script):
        self.calls.append(("eval", script))
        if self.fail:
            raise RuntimeError("checkout rejected")
    def close(self):
        self.calls.append(("close", None))

class LicensePreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.api = self.root / "lumapi.py"
        self.api.write_text("# pinned fake api\\n", encoding="utf-8")
        self.old_temp = tempfile.tempdir
    def tearDown(self):
        tempfile.tempdir = self.old_temp
        self.tmp.cleanup()
    def test_two_engine_checkouts_close_and_never_run(self):
        calls=[]
        module=types.SimpleNamespace(__file__=str(self.api), FDTD=lambda **kw: FakeSession(calls))
        with mock.patch.dict("os.environ", {}, clear=False):
            with mock.patch("license_preflight_v1.importlib.import_module", return_value=module):
                result=run_lumerical_license_preflight(
                    self.root/"run", self.api, hashlib.sha256(self.api.read_bytes()).hexdigest(),
                    self.root/"license-temp", port_range="6200:6299")
        self.assertEqual(result["result"], "PASS")
        self.assertEqual([x[0] for x in calls], ["eval","close","eval","close"])
        self.assertTrue(all(x[1] == "checkout('FDTD_Solutions_engine');" for x in calls if x[0]=="eval"))
        proof=json.loads(Path(result["path"]).read_text(encoding="utf-8"))
        self.assertFalse(proof["solver_run_called"])
        self.assertEqual(proof["solver_invocations"],0)
        self.assertTrue(all(x["closed"] and x["feature_checkout"] for x in proof["sessions"]))
    def test_checkout_failure_persists_fail_closed_proof(self):
        calls=[]
        module=types.SimpleNamespace(__file__=str(self.api), FDTD=lambda **kw: FakeSession(calls,fail=True))
        with mock.patch("license_preflight_v1.importlib.import_module", return_value=module):
            with self.assertRaisesRegex(RuntimeError,"checkout rejected"):
                run_lumerical_license_preflight(
                    self.root/"failed", self.api, hashlib.sha256(self.api.read_bytes()).hexdigest(),
                    self.root/"license-temp", session_factory=module.FDTD)
        proof=json.loads((self.root/"failed"/"license_api_preflight_v1.json").read_text(encoding="utf-8"))
        self.assertEqual(proof["result"],"FAIL")
        self.assertFalse(proof["sessions"][0]["feature_checkout"])
        self.assertTrue(proof["sessions"][0]["closed"])
        self.assertEqual([x[0] for x in calls],["eval","close"])

if __name__ == "__main__":
    unittest.main()
