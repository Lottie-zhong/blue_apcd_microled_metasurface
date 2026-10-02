# -*- coding: utf-8 -*-
"""No-solver tests for the V1 native adapter barriers."""
import hashlib
import contextlib
import io
import json
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adapter as adapter_module
from adapter import NativeAdapter, PRODUCTION_RUNNER_ROOT, main, run_cli
from runner import CONTRACT_SHA256, EXPANSION_SHA256, GEOMETRIES, MANIFEST_KEYS, RunnerError, run_one


class FakeLauncher:
    def __init__(self):
        self.called = False
    def run_standalone_gpu_and_confirm_completion(self, cfg, on_confirmed, launch_guard=None):
        self.called = True
        class Child:
            pid = 11
        child = launch_guard(lambda: Child())
        on_confirmed({"observation":"new_solver_process","child_pid":child.pid,
                      "processes":[{"pid":child.pid,"create_time_unix":1.0}],
                      "command":["fdtd-solutions.exe"]})
        return {"run_id": cfg["task"], "child_pid": child.pid, "child_log": ""}


class AdapterBarrierTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.contract = self.base / "contract.json"
        self.contract.write_text("{}", encoding="utf-8")
        self.pre = self.base / "pre.fsp"
        self.pre.write_bytes(b"approved input")
        self.manifest = {
            "case_id": "K6V1_S35", "attempt_id": "attempt_adapter",
            "run_id": "run-adapter", "geometry": GEOMETRIES["K6V1_S35"],
            "physical_contract_sha256": CONTRACT_SHA256,
            "expansion_manifest_sha256": EXPANSION_SHA256,
            "pre_fsp_path": str(self.pre),
            "pre_fsp_sha256": hashlib.sha256(self.pre.read_bytes()).hexdigest(),
            "physical_contract_path": str(self.contract),
        }
    def tearDown(self):
        self.tmp.cleanup()

    def test_postprocess_dependency_preflight_is_pinned_and_zero_solver(self):
        report = adapter_module.postprocess_dependency_preflight()
        self.assertEqual(report["result"], "PASS")
        self.assertFalse(report["scientific_entry_performed"])
        self.assertFalse(report["solver_run_called"])
        tmm = report["dependencies"]["mdc_tmm_complex_incident_power_v1"]
        self.assertEqual(tmm["authority_commit"], "46af82357f269aea0c77105a03e7ca9da645ca8f")
        self.assertEqual(tmm["sha256"], "12d2d95bd99fc6e18fec9ac17ab066a5a1fc4a3ddf1a6e5a8c0a625da959ff4b")
        self.assertIn("normal_stack_power", tmm["callables"])
        self.assertIn("canonical_state_from_fdtd",
                      report["dependencies"]["pw_complex_floquet_state_v1"]["callables"])

    def test_cli_contract_hash_failure_happens_before_adapter_or_solver(self):
        p = self.base / "manifest.json"
        p.write_text(json.dumps(self.manifest), encoding="utf-8")
        built = []
        def factory(_path):
            built.append(True)
            raise AssertionError("adapter must not be constructed on hash mismatch")
        with self.assertRaisesRegex(RunnerError, "PHYSICAL_CONTRACT_FILE_HASH_MISMATCH"):
            run_cli(p, adapter_factory=factory, test_output_root=self.base / "runs")
        self.assertEqual(built, [])
        self.assertFalse((self.base / "runs").exists())

    def test_launch_requires_matching_durable_entered_run_id(self):
        launcher = FakeLauncher()
        adapter = NativeAdapter(self.contract, launcher=launcher, gpu_resource_name="gpu0")
        run_dir = self.base / "run"
        run_dir.mkdir()
        status = {"run_id": "wrong-run", "state": "SOLVER_ENTERED",
                  "solver_entered": True, "solver_invocations": 1}
        (run_dir / "status.json").write_text(json.dumps(status), encoding="utf-8")
        m = dict(self.manifest, run_id="expected-run")
        with self.assertRaisesRegex(RunnerError, "DURABLE_ENTRY_GUARD_FAILED"):
            adapter.solver(m, run_dir)
        self.assertTrue(launcher.called)

    def test_launch_guard_accepts_only_durable_single_entry(self):
        launcher = FakeLauncher()
        adapter = NativeAdapter(self.contract, launcher=launcher, gpu_resource_name="gpu0")
        run_dir = self.base / "run"
        run_dir.mkdir()
        m = dict(self.manifest, run_id="expected-run")
        (run_dir / "status.json").write_text(json.dumps({
            "run_id": m["run_id"], "state": "SOLVER_ENTERED",
            "solver_entered": True, "solver_invocations": 1}), encoding="utf-8")
        result = adapter.solver(m, run_dir)
        self.assertEqual(result["run_id"], m["run_id"])
        log = json.loads((run_dir / "solver.log").read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(log["run_id"], m["run_id"])



    def test_cli_manifest_parse_and_contract_path_fail_closed(self):
        p=self.base/"malformed.json"
        p.write_text("{",encoding="utf-8")
        built=[]
        with self.assertRaises(json.JSONDecodeError):
            run_cli(p,adapter_factory=lambda _p:built.append(True),test_output_root=self.base/"runs")
        self.assertEqual(built,[])
        p.write_text(json.dumps({"case_id":"K6V1_S35"}),encoding="utf-8")
        with self.assertRaisesRegex(RunnerError,"PHYSICAL_CONTRACT_PATH_MISSING"):
            run_cli(p,adapter_factory=lambda _p:built.append(True),test_output_root=self.base/"runs")
        self.assertEqual(built,[])
        self.assertFalse((self.base/"runs").exists())

    def test_attempt_002_blocked_while_prior_runner_solver_pid_is_live(self):
        runner_root = self.base / "runner-root"
        prior_dir = runner_root / "runs" / "K6V1_S35" / "attempt_001" / "prior-run"
        prior_dir.mkdir(parents=True)
        prior_status = {
            "run_id": "prior-run", "case_id": "K6V1_S35", "attempt_id": "attempt_001",
            "state": "FAILED_POSTENTRY", "solver_entered": True, "solver_invocations": 1,
            "solver_process_lineage": {
                "run_id": "prior-run", "observation": "new_solver_process", "child_pid": 4242,
                "processes": [{"pid": 4242, "creation_time_unix": 123.0}],
            },
        }
        (prior_dir / "manifest.json").write_text(json.dumps({
            "run_id": "prior-run", "case_id": "K6V1_S35", "attempt_id": "attempt_001"
        }), encoding="utf-8")
        (prior_dir / "status.json").write_text(json.dumps(prior_status), encoding="utf-8")
        manifest = dict(self.manifest, attempt_id="attempt_002", run_id="attempt-002-run")
        core_manifest = {key: value for key, value in manifest.items() if key in MANIFEST_KEYS}
        adapter = NativeAdapter(self.contract, launcher=FakeLauncher(), gpu_resource_name="gpu0")
        calls = []
        with unittest.mock.patch.object(NativeAdapter, "_process_identity_state", return_value="live"):
            with self.assertRaisesRegex(RunnerError, "RUNNER_OWNED_ACTIVITY_PRESENT"):
                run_one(core_manifest, runner_root, lambda *_: calls.append("solver"),
                        lambda *_: {"fresh_load_verified": True, "monitors_valid": True,
                                    "state_valid": True, "scientific_valid": True},
                        lambda: {"free_mib": 8192}, adapter.runner_owner_probe)
        self.assertEqual(calls, [])
        row = json.loads((runner_root / "registry.json").read_text())["runs"][-1]
        self.assertEqual(row["state"], "FAILED_PREENTRY")


    def test_missing_or_ambiguous_pid_lineage_fails_closed(self):
        statuses = [
            {
                "run_id": "missing-lineage", "case_id": "K6V1_S35",
                "attempt_id": "attempt_001", "state": "FAILED_POSTENTRY",
                "solver_entered": True, "solver_invocations": 1,
            },
            {
                "run_id": "ambiguous-pid", "case_id": "K6V1_S35",
                "attempt_id": "attempt_001", "state": "FAILED_POSTENTRY",
                "solver_entered": True, "solver_invocations": 1,
                "solver_process_lineage": {
                    "run_id": "ambiguous-pid", "observation": "new_solver_process",
                    "child_pid": 5150,
                    "processes": [{"pid": 5150, "creation_time_unix": 100.0}],
                },
            },
        ]
        for index, status in enumerate(statuses):
            root = self.base / f"uncertain-{index}"
            status_path = (root / "runs" / status["case_id"] /
                           status["attempt_id"] / status["run_id"] / "status.json")
            status_path.parent.mkdir(parents=True)
            status_path.write_text(json.dumps(status), encoding="utf-8")
            if index == 0:
                self.assertTrue(NativeAdapter.runner_owner_probe(root))
            else:
                with unittest.mock.patch.object(
                        NativeAdapter, "_process_identity_state", return_value="unknown"):
                    self.assertTrue(NativeAdapter.runner_owner_probe(root))


    def test_production_cli_uses_one_fixed_root_and_rejects_override(self):
        with unittest.mock.patch.object(adapter_module, "run_cli", return_value={"ok": True}) as call:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["run-one", "manifest.json"]), 0)
        call.assert_called_once_with("manifest.json")
        self.assertEqual(PRODUCTION_RUNNER_ROOT, Path(r"D:\apcd_runtime\gpu_production_runner_v1"))
        with unittest.mock.patch.object(adapter_module, "run_cli") as call:
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    main(["run-one", "manifest.json", "--output-root", str(self.base / "other")])
            call.assert_not_called()

    def test_run_cli_fails_closed_without_postprocess_preflight(self):
        manifest = {key: value for key, value in self.manifest.items() if key in MANIFEST_KEYS}
        adapter_without_preflight = object()
        with unittest.mock.patch.object(
                adapter_module, "read_cli_manifest", return_value=(manifest, self.contract)):
            with unittest.mock.patch.object(adapter_module, "run_one") as run:
                with self.assertRaisesRegex(RunnerError, "POSTPROCESS_DEPENDENCY_PREFLIGHT_FAILED"):
                    run_cli("manifest.json", adapter_factory=lambda _p: adapter_without_preflight,
                            test_output_root=self.base / "runs")
        run.assert_not_called()
        self.assertFalse((self.base / "runs").exists())

    def test_run_cli_defaults_to_fixed_root(self):
        manifest = {key: value for key, value in self.manifest.items() if key in MANIFEST_KEYS}
        class Callbacks:
            postprocess_dependency_preflight = {
                "schema": "APCD_GPU_RUNNER_V1_POSTPROCESS_DEPENDENCY_PREFLIGHT_V1",
                "result": "PASS", "scientific_entry_performed": False,
                "solver_run_called": False,
            }
            def solver(self, *_): return None
            def fresh_load_validate(self, *_): return {}
            def gpu_snapshot(self): return {"free_mib": 8192}
            def runner_owner_probe(self, *_): return False
        callbacks = Callbacks()
        with unittest.mock.patch.object(
                adapter_module, "read_cli_manifest", return_value=(manifest, self.contract)):
            with unittest.mock.patch.object(adapter_module, "run_one", return_value="ok") as run:
                self.assertEqual(run_cli("manifest.json", adapter_factory=lambda _p: callbacks,
                                         test_output_root=self.base / "runs"), "ok")
        self.assertEqual(run.call_args.args[1], self.base / "runs")
        record = self.base / "runs" / "preflight" / manifest["case_id"] / manifest["attempt_id"] / manifest["run_id"] / "postprocess_dependency_preflight.json"
        payload = json.loads(record.read_text(encoding="utf-8"))
        self.assertEqual(payload["result"], "PASS")
        self.assertEqual(payload["run_id"], manifest["run_id"])

    def test_gpu_snapshot_captures_device_and_visible_compute_processes(self):
        adapter = NativeAdapter(self.contract, launcher=FakeLauncher(), gpu_resource_name="logical-gpu-0")
        responses = [
            type("Result", (), {"stdout": "0, GPU-test-uuid, NVIDIA GeForce RTX 3080, 12288, 4096, 8192, 7\n"})(),
            type("Result", (), {"stdout": "GPU-test-uuid, 4242, fdtd-solutions.exe, 512\n"})(),
        ]
        with unittest.mock.patch.object(adapter_module.subprocess, "run", side_effect=responses):
            snapshot = adapter.gpu_snapshot()
        self.assertTrue(snapshot["captured_utc"].endswith("Z"))
        self.assertEqual(snapshot["requested_resource_name"], "logical-gpu-0")
        self.assertEqual(snapshot["gpus"][0], {
            "index": 0, "uuid": "GPU-test-uuid", "name": "NVIDIA GeForce RTX 3080",
            "memory_total_mib": 12288, "memory_used_mib": 4096,
            "memory_free_mib": 8192, "utilization_gpu_percent": 7})
        self.assertEqual(snapshot["visible_compute_processes"][0]["pid"], 4242)
        self.assertEqual(snapshot["external_consumers"][0]["ownership"], "external_or_unattributed")
        self.assertEqual(snapshot["free_mib"], 8192)

    def test_unavailable_process_query_does_not_block_nonzero_context_when_headroom_passes(self):
        adapter = NativeAdapter(self.contract, launcher=FakeLauncher(), gpu_resource_name="logical-gpu-0")
        def fake_run(command, **kwargs):
            if "--query-gpu=" in command[1]:
                return type("Result", (), {"stdout":
                    "0, GPU-test-uuid, NVIDIA GeForce RTX 3080, 12288, 4096, 8192, 7\n"})()
            raise adapter_module.subprocess.TimeoutExpired(command, 10)
        with unittest.mock.patch.object(adapter_module.subprocess, "run", side_effect=fake_run):
            snapshot = adapter.gpu_snapshot()
        self.assertEqual(snapshot["compute_process_query_status"], "UNAVAILABLE")
        self.assertIsNone(snapshot["visible_compute_processes"])
        self.assertIsNone(snapshot["external_consumers"])
        self.assertFalse(snapshot["process_query_alone_blocks_launch"])
        calls=[]
        core_manifest={key:value for key,value in self.manifest.items() if key in MANIFEST_KEYS}
        def injected_solver(_manifest,run_dir):
            calls.append("injected")
            (run_dir/"truth.h5").write_bytes(b"fixture truth")
        result=run_one(core_manifest,self.base/"snapshot-run",injected_solver,
            lambda *_:{"fresh_load_verified":True,"monitors_valid":True,
                       "state_valid":True,"scientific_valid":True},
            lambda:snapshot,adapter.runner_owner_probe)
        self.assertEqual(result["status"]["state"],"DONE")
        self.assertEqual(calls,["injected"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
