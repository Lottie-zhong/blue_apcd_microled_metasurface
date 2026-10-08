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
import numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adapter as adapter_module
from adapter import NativeAdapter, PRODUCTION_RUNNER_ROOT, main, run_cli
from recover_s35_postentry_truth_v1 import json_safe, zero_solver_guard
from runner import CONTRACT_SHA256, EXPANSION_SHA256, MANIFEST_KEYS, RunnerError, run_one

# Historical-case values are fixtures only; production geometry comes from Coupling authority.
GEOMETRIES = {"K6V1_S35": [110,145,225,105,185,215],
              "K6V1_S39": [175,100,125,120,100,230]}

def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def _stage1_case(case_id):
    attempt_id = "attempt_001"
    case_dir = adapter_module.SETUP_AUTHORITY_ROOT / case_id / attempt_id
    authority_path = case_dir / "authority_input_manifest.json"
    load_only_path = case_dir / "load_only_validation.json"
    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    manifest = {
        "case_id": case_id, "attempt_id": attempt_id,
        "geometry": authority["ordered_D_nm"],
        "physical_contract_sha256": authority["physical_contract_hash"],
        "expansion_manifest_sha256": authority["stage1_expansion_manifest_sha256"],
        "pre_fsp_path": authority["canonical_pre_fsp_path"],
        "pre_fsp_sha256": authority["canonical_pre_fsp_sha256"],
    }
    setup_authority = {
        "authority_manifest_path": str(authority_path),
        "authority_manifest_sha256": _sha256_file(authority_path),
        "load_only_validation_path": str(load_only_path),
        "load_only_validation_sha256": _sha256_file(load_only_path),
    }
    return manifest, setup_authority

def _production_contract():
    return Path(r"D:\apcd_runtime\gpu_production_runner_v1\contracts\pw_contract_32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5.json")


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

    def test_native_adapter_sets_supported_acl_range_without_overriding_explicit_value(self):
        key = adapter_module.ANSYS_ACL_PORT_RANGE_ENV
        with unittest.mock.patch.dict(adapter_module.os.environ):
            adapter_module.os.environ.pop(key, None)
            with unittest.mock.patch.object(adapter_module, "_prepare_postprocess_import_paths"), \
                 unittest.mock.patch.object(adapter_module, "load_pinned_launcher", return_value=FakeLauncher()), \
                 unittest.mock.patch.object(adapter_module, "postprocess_dependency_preflight", return_value={"result": "PASS"}):
                NativeAdapter(self.contract, gpu_resource_name="SETUP_PREFLIGHT_ONLY_NO_SLOT")
            self.assertEqual(adapter_module.os.environ[key], "6200:6299")
        with unittest.mock.patch.dict(adapter_module.os.environ, {key: "6210:6220"}):
            with unittest.mock.patch.object(adapter_module, "_prepare_postprocess_import_paths"), \
                 unittest.mock.patch.object(adapter_module, "load_pinned_launcher", return_value=FakeLauncher()), \
                 unittest.mock.patch.object(adapter_module, "postprocess_dependency_preflight", return_value={"result": "PASS"}):
                NativeAdapter(self.contract, gpu_resource_name="SETUP_PREFLIGHT_ONLY_NO_SLOT")
            self.assertEqual(adapter_module.os.environ[key], "6210:6220")

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

    def test_zero_solver_guard_preserves_fdtd_class_and_blocks_solver_methods(self):
        class FakeFDTD:
            def load(self):
                return "loaded"
            def run(self):
                return "ran"
            def runanalysis(self):
                return "ran"
            def runsetup(self):
                return "ran"
        original_class = FakeFDTD
        original_methods = {name: getattr(FakeFDTD, name)
                            for name in ("run", "runanalysis", "runsetup")}
        blocked = []
        with zero_solver_guard(FakeFDTD, blocked):
            self.assertIs(FakeFDTD, original_class)
            self.assertEqual(FakeFDTD().load(), "loaded")
            for name in ("run", "runanalysis", "runsetup"):
                with self.assertRaisesRegex(RuntimeError, "ZERO_SOLVER_POLICY_BLOCKED"):
                    getattr(FakeFDTD(), name)()
        self.assertEqual(blocked, ["run", "runanalysis", "runsetup"])
        for name, method in original_methods.items():
            self.assertIs(getattr(FakeFDTD, name), method)

    def test_recovery_json_safe_converts_numpy_scalars_and_arrays(self):
        payload = {"accepted": np.bool_(True), "values": np.asarray([1.0, 2.0])}
        converted = json_safe(payload)
        self.assertIs(type(converted["accepted"]), bool)
        self.assertEqual(converted, {"accepted": True, "values": [1.0, 2.0]})
        json.dumps(converted, allow_nan=False)

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
        with unittest.mock.patch.object(adapter_module, "run_one_scheduled",
                                        return_value={"ok": True}) as call:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["run-one", "manifest.json"]), 0)
        call.assert_called_once_with("manifest.json")
        self.assertEqual(PRODUCTION_RUNNER_ROOT, Path(r"D:\apcd_runtime\gpu_production_runner_v1"))
        with unittest.mock.patch.object(adapter_module, "run_one_scheduled") as call:
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
            def setup_structural_validate(self, *_):
                return {"result":"PASS","solver_run_called":False}
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


    def _run_setup_load_only(self, case_id):
        manifest, case_authority = _stage1_case(case_id)
        contract = _production_contract()
        adapter = object.__new__(NativeAdapter)
        adapter.contract_path = contract
        report = adapter.setup_structural_validate(manifest, case_authority=case_authority)
        self.assertEqual(report["result"], "PASS")
        self.assertFalse(report["solver_run_called"])
        self.assertEqual(report["solver_invocations"], 0)
        self.assertFalse(report["scientific_entry_performed"])
        self.assertEqual(report["case_id"], case_id)
        self.assertEqual(report["ordered_D_nm"], manifest["geometry"])
        self.assertEqual(report["setup_readback"]["run_called"], False)
        self.assertEqual(report["setup_readback"]["save_called_by_validator"], False)
        self.assertEqual(report["load_only_semantic_parity"]["status"], "PASS")
        return manifest, case_authority, report

    def test_setup_structural_validator_keeps_s39_generic_manifest_regression(self):
        source = adapter_module.SETUP_AUTHORITY_ROOT / "K6V1_S39/attempt_001/authority_input_manifest.json"
        if not source.is_file():
            self.skipTest("remote Coupling authority inputs are unavailable")
        _, _, report = self._run_setup_load_only("K6V1_S39")
        self.assertEqual(report["mesh_authority"], "PW_K6_5NM_FULL_PERIOD_MESH_AUTHORITY_V1")
        self.assertEqual(report["setup_readback"]["meshes"]["NP_DERIVED_BASELINE_N2"]["step_nm"], [5.0,5.0,5.0])

    def test_setup_structural_validator_accepts_s21_with_its_own_manifest(self):
        source = adapter_module.SETUP_AUTHORITY_ROOT / "K6V1_S21/attempt_001/authority_input_manifest.json"
        if not source.is_file():
            self.skipTest("remote Coupling authority inputs are unavailable")
        manifest, _, report = self._run_setup_load_only("K6V1_S21")
        self.assertEqual(report["setup_readback"]["ordered_D_nm"], manifest["geometry"])

    def test_cli_reader_consumes_generic_case_authority_outside_core_manifest(self):
        manifest, case_authority = _stage1_case("K6V1_S21")
        manifest["run_id"] = "manifest-parse-zero-solver"
        envelope = dict(manifest)
        envelope["physical_contract_path"] = str(_production_contract())
        envelope["setup_authority"] = case_authority
        path = self.base / "generic-case-envelope.json"
        path.write_text(json.dumps(envelope), encoding="utf-8")
        parsed, contract_path = adapter_module.read_cli_manifest(path)
        self.assertEqual(parsed["_setup_authority"], case_authority)
        self.assertEqual(set(parsed) - {"_setup_authority"}, MANIFEST_KEYS)
        self.assertEqual(contract_path, _production_contract())

    def test_s21_manifest_rejects_s39_authority_before_fsp_load(self):
        manifest, _ = _stage1_case("K6V1_S21")
        _, s39_authority = _stage1_case("K6V1_S39")
        adapter = object.__new__(NativeAdapter)
        adapter.contract_path = _production_contract()
        with unittest.mock.patch.object(adapter_module, "load_pinned_setup_validator") as load:
            with self.assertRaisesRegex(RunnerError, "SETUP_AUTHORITY_PATH_MISMATCH"):
                adapter.setup_structural_validate(manifest, case_authority=s39_authority)
        load.assert_not_called()

    def test_manifest_geometry_mismatch_fails_before_fsp_load(self):
        manifest, authority = _stage1_case("K6V1_S21")
        manifest["geometry"] = list(manifest["geometry"])
        manifest["geometry"][0] += 1
        adapter = object.__new__(NativeAdapter)
        adapter.contract_path = _production_contract()
        with unittest.mock.patch.object(adapter_module, "load_pinned_setup_validator") as load:
            with self.assertRaisesRegex(RunnerError, "SETUP_CASE_OR_AUTHORITY_MISMATCH"):
                adapter.setup_structural_validate(manifest, case_authority=authority)
        load.assert_not_called()

    def test_manifest_fsp_hash_mismatch_fails_before_fsp_load(self):
        manifest, authority = _stage1_case("K6V1_S21")
        manifest["pre_fsp_sha256"] = "0" * 64
        adapter = object.__new__(NativeAdapter)
        adapter.contract_path = _production_contract()
        with unittest.mock.patch.object(adapter_module, "load_pinned_setup_validator") as load:
            with self.assertRaisesRegex(RunnerError, "SETUP_SOURCE_OR_STAGED_HASH_MISMATCH"):
                adapter.setup_structural_validate(manifest, case_authority=authority)
        load.assert_not_called()

    def test_manifest_contract_hash_mismatch_fails_before_fsp_load(self):
        manifest, authority = _stage1_case("K6V1_S21")
        manifest["physical_contract_sha256"] = "0" * 64
        adapter = object.__new__(NativeAdapter)
        adapter.contract_path = _production_contract()
        with unittest.mock.patch.object(adapter_module, "load_pinned_setup_validator") as load:
            with self.assertRaisesRegex(RunnerError, "SETUP_PHYSICAL_CONTRACT_HASH_MISMATCH"):
                adapter.setup_structural_validate(manifest, case_authority=authority)
        load.assert_not_called()

    def test_manifest_case_and_attempt_identity_mismatches_fail_closed(self):
        for field, value in (("case_id", "K6V1_S39"), ("attempt_id", "attempt_002")):
            manifest, authority = _stage1_case("K6V1_S21")
            manifest[field] = value
            adapter = object.__new__(NativeAdapter)
            adapter.contract_path = _production_contract()
            with unittest.mock.patch.object(adapter_module, "load_pinned_setup_validator") as load:
                with self.assertRaises(RunnerError):
                    adapter.setup_structural_validate(manifest, case_authority=authority)
            load.assert_not_called()

    def test_postrun_truth_validator_still_rejects_setup_fsp_without_result_dcards(self):
        manifest, _ = _stage1_case("K6V1_S39")
        source_fsp = Path(manifest["pre_fsp_path"])
        if not source_fsp.is_file():
            self.skipTest("remote Lumerical authority input is unavailable")
        import shutil
        import sys
        run_dir = self.base / "postrun-strictness"
        run_dir.mkdir()
        shutil.copyfile(source_fsp, run_dir / "run.fsp")
        strict_launcher = adapter_module.load_pinned_launcher()
        adapter = object.__new__(NativeAdapter)
        adapter.contract_path = Path(r"D:\\apcd_runtime\\gpu_production_runner_v1\\contracts\\pw_contract_32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5.json")
        adapter.contract = json.loads(adapter.contract_path.read_text(encoding="utf-8"))
        adapter.gpu_resource_name = "GPU license audit"
        adapter.fdtd_exe = None
        adapter.launcher = strict_launcher
        manifest["run_id"] = "strictness-test"
        adapter_module._prepare_postprocess_import_paths()
        with self.assertRaises(Exception) as caught:
            adapter.fresh_load_validate(manifest, run_dir)
        self.assertIn("MON_IN", str(caught.exception))
        self.assertFalse((run_dir / "truth.h5").exists())

    def test_dependency_preflight_is_persisted_before_runner_entry_callback(self):
        manifest = {key:value for key,value in self.manifest.items() if key in MANIFEST_KEYS}
        events = []
        class Callbacks:
            postprocess_dependency_preflight = {
                "schema":"APCD_GPU_RUNNER_V1_POSTPROCESS_DEPENDENCY_PREFLIGHT_V1",
                "result":"PASS", "scientific_entry_performed":False, "solver_run_called":False}
            def setup_structural_validate(self, *_):
                events.append("setup")
                return {"result":"PASS","solver_run_called":False}
            def solver(self, *_): events.append("solver")
            def fresh_load_validate(self, *_): return {}
            def gpu_snapshot(self): return {"free_mib":8192}
            def runner_owner_probe(self, *_): return False
        callbacks = Callbacks()
        output = self.base / "ordered-preflight"
        def before_run_one(*args, **kwargs):
            record = output / "preflight" / manifest["case_id"] / manifest["attempt_id"] / manifest["run_id"] / "postprocess_dependency_preflight.json"
            self.assertTrue(record.is_file())
            self.assertEqual(json.loads(record.read_text())["result"],"PASS")
            self.assertTrue(callable(args[-1]))
            self.assertTrue(callable(kwargs.get("pre_entry_guard")))
            events.append("runner-entry-boundary")
            return {"state":"NOT_ENTERED"}
        with unittest.mock.patch.object(adapter_module,"read_cli_manifest",return_value=(manifest,self.contract)):
            with unittest.mock.patch.object(adapter_module,"run_one",side_effect=before_run_one) as run:
                result = run_cli("manifest.json",adapter_factory=lambda _p:callbacks,test_output_root=output)
        self.assertEqual(result,{"state":"NOT_ENTERED"})
        self.assertEqual(events,["runner-entry-boundary"])
        run.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
