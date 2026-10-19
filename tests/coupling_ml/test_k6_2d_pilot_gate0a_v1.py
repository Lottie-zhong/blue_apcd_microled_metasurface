import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("k6_2d_pilot", HERE.parent.parent / "scripts" / "coupling_ml" / "k6_2d_fdtd_pilot_gate0a_v1.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FakeAdapter:
    def __init__(self, fail_canonical=False):
        self.fail_canonical = fail_canonical
        self.session_id = "fake-session"
        self.calls = []

    def open(self, path):
        self.calls.append(("open", path))
        return object()

    def run(self, handle):
        self.calls.append(("run",))

    def save(self, handle, path):
        self.calls.append(("save", path))
        if self.fail_canonical and Path(path).name == "canonical.fsp":
            raise PermissionError("controlled test save failure")
        Path(path).write_bytes(b"post-fsp-scientific-truth")

    def rescue_save(self, handle, path):
        self.calls.append(("rescue_save", path))
        Path(path).write_bytes(b"post-fsp-scientific-truth-recovered")

    def live_results_available(self, handle):
        return True

    def load_only(self, path, manifest):
        self.calls.append(("load_only", path))
        return {"ok": True, "identity_pass": True, "arrays_pass": True,
                "shape_pass": True, "sanity_pass": True, "run_called": False,
                "session_id": "independent-session"}

    def close(self, handle):
        self.calls.append(("close",))


class K6PilotTests(unittest.TestCase):
    def test_static_contract(self):
        self.assertTrue(MODULE.static_contract_audit()["pass"])

    def test_geometry_contracts(self):
        source = MODULE.case_contract("SOURCE_ONLY_CENTROID_X")
        control = MODULE.case_contract("CONTROL0_CENTROID_X")
        alt = MODULE.case_contract("ALT1_CENTROID_X")
        self.assertEqual(source["ordered_k6_positions_nm"], [])
        self.assertEqual(control["ordered_k6_positions_nm"], [-725, -435, -145, 145, 435, 725])
        self.assertEqual(control["ordered_widths_nm"], [125, 135, 150, 175, 190, 210])
        self.assertEqual(alt["ordered_widths_nm"], [100, 115, 130, 145, 155, 185])
        self.assertEqual(control["boundary"]["x"].split(";")[0], "finite isolated 2D supercell with PML at +/-870 nm")
        self.assertEqual(control["mapping_flag"], "BAR_WIDTH_EQUALS_DIAMETER_PROVISIONAL_MAPPING")

    def test_lifecycle_normal_and_rescue(self):
        for fail_canonical in (False, True):
            with self.subTest(fail_canonical=fail_canonical), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                setup = root / "setup_pre.fsp"
                setup.write_bytes(b"frozen-setup")
                roles = MODULE.ArtifactRoles(root / "frozen_pre.fsp", root / "runtime.fsp", root / "canonical.fsp", root / "recovery_post.fsp")
                released = []
                adapter = FakeAdapter(fail_canonical)
                controller = MODULE.LifecycleController(
                    job_id="test", attempt_id="attempt_001", roles=roles,
                    events_path=root / "events.jsonl", completion_path=root / "completion.json",
                    raw_path=root / "raw.bin", release_slot=lambda state: released.append(state),
                    on_solver_entered=lambda: None, save_timeout_s=1,
                )
                manifest = {"setup_pre_fsp": str(setup), "physical_contract_sha256": "test"}
                result = controller.execute(
                    adapter, manifest,
                    lambda handle, post, raw: raw.write_bytes(b"raw"),
                    lambda raw: {"derived": True},
                    lambda derived, post, raw: {"pass": True},
                )
                self.assertEqual(result["status"], "COMPLETED")
                self.assertEqual(released, ["COMPLETED"])
                self.assertEqual(roles.frozen_pre.read_bytes(), b"frozen-setup")
                self.assertNotEqual(roles.frozen_pre.resolve(), roles.runtime_fsp.resolve())
                states = roles.event_order(root / "events.jsonl")
                self.assertLess(states.index("SOLVER_RETURNED"), states.index("POST_FSP_SAVE_REQUESTED"))
                self.assertIn("POST_FSP_LOAD_ONLY_VALIDATED", states)
                if fail_canonical:
                    self.assertTrue(any(x[0] == "rescue_save" for x in adapter.calls))
                    self.assertTrue(str(result["post_fsp"]).endswith("recovery_post.fsp"))

    def test_illegal_transition_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            roles = MODULE.ArtifactRoles(root / "a", root / "b", root / "c", root / "d")
            c = MODULE.LifecycleController(job_id="x", attempt_id="a", roles=roles,
                                           events_path=root / "events", completion_path=root / "completion",
                                           raw_path=root / "raw", release_slot=lambda _: None)
            with self.assertRaises(MODULE.LifecycleError):
                c.transition(MODULE.LifecycleState.COMPLETED)


if __name__ == "__main__":
    unittest.main()
