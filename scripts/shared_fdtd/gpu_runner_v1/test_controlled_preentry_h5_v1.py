import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import h5py
import numpy as np

import adapter
import runner


class FakeLauncher:
    def __init__(self):
        self._standalone_gpu_script = lambda resource, names: {"resource": resource, "names": list(names)}

    def run_standalone_gpu_and_confirm_completion(self, cfg, on_confirmed, launch_guard):
        return self._standalone_gpu_script("GPU", ["MON_IN", "MON_PRENP", "MON_POSTNP"])


def _manifest(tmp):
    source = Path(tmp) / "setup.fsp"
    source.write_bytes(b"synthetic setup; never sent to Lumerical")
    return {
        "case_id": "K6V1_EXT02",
        "attempt_id": "attempt_001",
        "run_id": "EXT02-PREENTRY-TEST-0001",
        "geometry": [220, 120, 155, 100, 105, 110],
        "physical_contract_sha256": runner.CONTRACT_SHA256,
        "expansion_manifest_sha256": runner.EXPANSION_SHA256,
        "pre_fsp_path": str(source),
        "pre_fsp_sha256": runner.sha256_file(source),
    }


class ControlledPreEntryAndH5Tests(unittest.TestCase):
    def test_pinned_launcher_receives_only_authorized_extra_monitor_and_restores_builder(self):
        launcher = FakeLauncher()
        original = launcher._standalone_gpu_script
        native = adapter.NativeAdapter.__new__(adapter.NativeAdapter)
        native.launcher = launcher
        result = native._run_standalone_gpu_with_extra_field_monitors(
            {}, ["EXT02_POSTNP_DIAG_Z2000"], lambda *_: None, lambda fn: fn())
        self.assertEqual(result["names"], [
            "MON_IN", "MON_PRENP", "MON_POSTNP", "EXT02_POSTNP_DIAG_Z2000"])
        self.assertIs(launcher._standalone_gpu_script, original)

    def test_h5_readiness_barrier_requires_five_complete_monitor_groups(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "run_output.h5"
            with h5py.File(path, "w") as h5:
                for index in range(5):
                    group = h5.create_group("Monitor" + str(index))
                    for axis, values in {
                        "x": np.array([-0.87, 0.87]),
                        "y": np.array([-0.145, 0.145]),
                        "z": np.array([2.0]),
                    }.items():
                        group.create_dataset(axis, data=values)
                    for field in ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz"):
                        group.create_dataset(field, data=np.ones((1, 2, 2, 42), dtype=np.float32))
            result = adapter._wait_for_durable_gpu_h5_sidecar(path, 5, timeout_seconds=2.0)
            self.assertEqual(result["result"], "PASS")
            self.assertEqual(len(result["monitor_groups"]), 5)
            self.assertEqual(result["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_h5_readiness_barrier_rejects_incomplete_monitor_set(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "run_output.h5"
            with h5py.File(path, "w") as h5:
                group = h5.create_group("Monitor0")
                group.create_dataset("Ex", data=np.ones((1, 2, 2, 42), dtype=np.float32))
            with self.assertRaisesRegex(runner.RunnerError, "GPU_H5_SIDECAR_NOT_DURABLE"):
                adapter._wait_for_durable_gpu_h5_sidecar(path, 5, timeout_seconds=0.01)

    def test_pre_entry_generation_change_terminalizes_before_solver_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = _manifest(temp)
            calls = []
            def reject(*_):
                raise runner.RunnerError("CONTROL_GENERATION_CHANGED_BEFORE_SOLVER_ENTRY")
            with self.assertRaisesRegex(runner.RunnerError, "CONTROL_GENERATION_CHANGED_BEFORE_SOLVER_ENTRY"):
                runner.run_one(
                    manifest, Path(temp) / "runner", lambda *_: calls.append("solver"),
                    fresh_load_validate=lambda *_: (_ for _ in ()).throw(AssertionError("fresh LOAD must not run")),
                    gpu_snapshot=lambda: {"free_mib": runner.MIN_GPU_FREE_MIB + 1},
                    runner_owner_probe=lambda _: False,
                    setup_structural_validate=lambda *_: {"result": "PASS", "solver_run_called": False},
                    admitted_contract_sha256=runner.CONTRACT_SHA256,
                    pre_entry_guard=reject,
                )
            run_dir = Path(temp) / "runner" / "runs" / manifest["case_id"] / manifest["attempt_id"] / manifest["run_id"]
            status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["state"], "FAILED_PREENTRY")
            self.assertIs(status["solver_entered"], False)
            self.assertEqual(status["solver_invocations"], 0)
            self.assertEqual(calls, [])
            self.assertFalse((run_dir / "pre_entry_revalidation.json").exists())

    def test_controlled_completion_inventories_h5_and_pre_entry_proof(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = _manifest(temp)
            root = Path(temp) / "runner"
            solver_calls = []
            def solver(_manifest, run_dir):
                solver_calls.append("synthetic callback only")
                bundle = Path(run_dir) / "run" / "run_output.h5"
                bundle.parent.mkdir(parents=True)
                bundle.write_bytes(b"synthetic h5 bundle for runner hash test")
                return "synthetic"
            def fresh_load(_manifest, run_dir):
                (Path(run_dir) / "truth.h5").write_bytes(b"synthetic truth")
                return {"fresh_load_verified": True, "monitors_valid": True,
                        "state_valid": True, "scientific_valid": True}
            guard = lambda *_: {"schema": "TEST_PRE_ENTRY", "result": "PASS",
                                "control_generation_sha256": "a" * 64}
            result = runner.run_one(
                manifest, root, solver, fresh_load,
                gpu_snapshot=lambda: {"free_mib": runner.MIN_GPU_FREE_MIB + 1},
                runner_owner_probe=lambda _: False,
                setup_structural_validate=lambda *_: {"result": "PASS", "solver_run_called": False},
                admitted_contract_sha256=runner.CONTRACT_SHA256,
                pre_entry_guard=guard,
            )
            run_dir = Path(result["run_dir"])
            status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
            hashes = json.loads((run_dir / "hashes.json").read_text(encoding="utf-8"))
            self.assertEqual(status["state"], "DONE")
            self.assertEqual(len(solver_calls), 1)
            self.assertEqual(hashes["pre_entry_revalidation_sha256"],
                             hashlib.sha256((run_dir / "pre_entry_revalidation.json").read_bytes()).hexdigest())
            self.assertEqual(hashes["run_output_h5_sha256"],
                             hashlib.sha256((run_dir / "run" / "run_output.h5").read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
