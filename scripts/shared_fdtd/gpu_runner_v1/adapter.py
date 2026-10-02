# -*- coding: utf-8 -*-
"""Thin native adapter for the filesystem-authoritative GPU runner V1."""
import argparse
import csv
import io
import hashlib
import importlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from runner import (CONTRACT_SHA256, MIN_GPU_FREE_MIB, PRODUCTION_RUNNER_ROOT,
                    RunnerError, atomic_json, read_json, run_one)

LAUNCHER_PATH = Path(r"D:\apcd_runtime\shared_v3_backend\01e2320ebf237bdbcd52573665520d57705d2800_gitblob\scripts\shared_fdtd\tools\pw_scientific_launcher.py")
LAUNCHER_SHA256 = "e4de8da6a824c02b3d0425c3e3c76f45111e369ad6a20237e464b0e6f7dce908"
PINNED_BACKEND_ID = "01e2320ebf237bdbcd52573665520d57705d2800"
PINNED_SCRIPTS_ROOT = LAUNCHER_PATH.parents[2]
PINNED_TOOLS_DIR = LAUNCHER_PATH.parent
VENDOR_DIR = Path(__file__).resolve().parent / "vendor"
MDC_MODULE_NAME = "mdc_tmm_complex_incident_power_v1"
MDC_SOURCE_BRANCH = "work/mdc-np-coupling-ml-v1"
MDC_SOURCE_COMMIT = "46af82357f269aea0c77105a03e7ca9da645ca8f"
MDC_MODULE_SHA256 = "12d2d95bd99fc6e18fec9ac17ab066a5a1fc4a3ddf1a6e5a8c0a625da959ff4b"
STATE_MODULE_SHA256 = "31cb2b602b1fa74ff09404c8111239f9dcf4a8c4b5ac1944a9300b2c23efaafb"
GPU_OBSERVABILITY_SHA256 = "e6b01c985e79fa2adcb280ab0d6cca4609dcbefc23e7d781e3fba147cbd89861"
LUMERICAL_API_DIR = Path("N:/Program Files/ANSYS Inc/v251/Lumerical/api/python")
LUMERICAL_API_FILE = LUMERICAL_API_DIR / "lumapi.py"
LUMERICAL_API_SHA256 = "feb0f99c7e79c053def676a2ee97e24cd0994dc56e5815f52300804915ae55c9"
POSTPROCESS_PYTHON_VERSION = (3, 10, 20)
POSTPROCESS_NUMPY_VERSION = "2.2.5"
POSTPROCESS_H5PY_VERSION = "3.16.0"
COUPLING_AUTHORITY_ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
SETUP_VALIDATOR_PATH = COUPLING_AUTHORITY_ROOT / "scripts/coupling_ml/validate_pw_k6_5nm_full_period_prefsp_v1.py"
SETUP_VALIDATOR_SHA256 = "b694ecf692376a33673b785774a8ea734c452f11009aad1cfe553f444817e2a8"
SETUP_BUILDER_PATH = COUPLING_AUTHORITY_ROOT / "scripts/coupling_ml/build_pw_k6_5nm_full_period_prefsp_v1.py"
SETUP_BUILDER_SHA256 = "fbd3a3e73212568023c47d84223a41b32d5cb3cf8fd48a04d09bef7bb94eded1"
SETUP_CASE_SPEC_PATH = COUPLING_AUTHORITY_ROOT / "outputs/coupling_ml/PW_K6_FIXED_MDC_12G_STAGE1_HF_EXECUTION_V1/K6V1_S39/attempt_001/case.json"
SETUP_CASE_SPEC_SHA256 = "02171fd0fb45e6d2d604e8c99b73024ef22dcb426faa9f0109fb90e985ed8891"
SETUP_AUTHORITY_MANIFEST_PATH = COUPLING_AUTHORITY_ROOT / "outputs/coupling_ml/PW_K6_5NM_FULL_PERIOD_MESH_AUTHORITY_V1/K6V1_S39/attempt_001/authority_input_manifest.json"
SETUP_AUTHORITY_MANIFEST_SHA256 = "c083d946e833d38a56c3ee7f773898390530c0db69c9e3bd688438037afac82a"
SETUP_CANONICAL_FSP_PATH = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\PW_K6_5NM_FULL_PERIOD_MESH_AUTHORITY_V1\K6V1_S39\attempt_001\setup\runtime.fsp")
SETUP_CANONICAL_FSP_SHA256 = "23c7d66cf8a73dc838b772c1cae048464451b0cb1584f3305d10938a2ebafe0d"
SETUP_MONITOR_CONTRACT_PATH = COUPLING_AUTHORITY_ROOT / "contracts/coupling/medium_pw/MEDIUM_PW_MONITOR_CONTRACT_V1.json"
SETUP_MONITOR_CONTRACT_SHA256 = "a84d8526889084f2b3b09022402ca93b2947939cb744f071a4b19bc6eb09172f"


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_cli_manifest(path):
    """Read CLI envelope and verify frozen contract and FSP before any entry."""
    with open(path, "r", encoding="utf-8") as stream:
        envelope = json.load(stream)
    if not isinstance(envelope, dict):
        raise RunnerError("MANIFEST_INVALID")
    contract_path = envelope.get("physical_contract_path")
    if not isinstance(contract_path, str) or not contract_path:
        raise RunnerError("PHYSICAL_CONTRACT_PATH_MISSING")
    contract_file = Path(contract_path)
    if not contract_file.is_file():
        raise RunnerError("PHYSICAL_CONTRACT_MISSING")
    manifest = dict(envelope)
    manifest.pop("physical_contract_path", None)
    # Validate the small core schema before reading or importing solver runtime.
    from runner import validate_manifest
    validate_manifest(manifest)
    if _sha256(contract_file) != manifest["physical_contract_sha256"]:
        raise RunnerError("PHYSICAL_CONTRACT_FILE_HASH_MISMATCH")
    pre = Path(manifest["pre_fsp_path"])
    if not pre.is_file():
        raise RunnerError("PRE_FSP_MISSING")
    if _sha256(pre) != manifest["pre_fsp_sha256"]:
        raise RunnerError("PRE_FSP_HASH_MISMATCH")
    return manifest, contract_file


def _prepare_postprocess_import_paths():
    paths = (LUMERICAL_API_DIR, PINNED_SCRIPTS_ROOT, PINNED_TOOLS_DIR, VENDOR_DIR)
    normalized = {os.path.normcase(os.path.abspath(value)) for value in sys.path if value}
    for path in paths:
        if not path.is_dir():
            raise RunnerError("POSTPROCESS_IMPORT_PATH_MISSING:" + str(path))
        key = os.path.normcase(os.path.abspath(str(path)))
        if key not in normalized:
            sys.path.insert(0, str(path))
            normalized.add(key)


def _verify_pinned_module(module, expected_path, expected_sha256, required_callables):
    actual_value = getattr(module, "__file__", None)
    if not actual_value:
        raise RunnerError("POSTPROCESS_MODULE_PATH_MISSING:" + module.__name__)
    actual_path = Path(actual_value).resolve()
    expected_path = Path(expected_path).resolve()
    if os.path.normcase(str(actual_path)) != os.path.normcase(str(expected_path)):
        raise RunnerError("POSTPROCESS_MODULE_PATH_MISMATCH:" + module.__name__)
    actual_sha = _sha256(actual_path)
    if actual_sha != expected_sha256:
        raise RunnerError("POSTPROCESS_MODULE_HASH_MISMATCH:" + module.__name__)
    missing = [name for name in required_callables if not callable(getattr(module, name, None))]
    if missing:
        raise RunnerError("POSTPROCESS_CALLABLE_MISSING:" + module.__name__ + ":" + ",".join(missing))
    return {
        "module": module.__name__,
        "path": str(actual_path),
        "sha256": actual_sha,
        "callables": list(required_callables),
    }


def _load_pinned_module_from_file(module_name, expected_path, expected_sha256, required_callables):
    expected_path = Path(expected_path).resolve()
    parent_name, separator, child_name = module_name.rpartition(".")
    parent = importlib.import_module(parent_name) if separator else None
    module = sys.modules.get(module_name)
    loaded_path = Path(getattr(module, "__file__", "")).resolve() if module else None
    if (module is None or loaded_path is None or
            os.path.normcase(str(loaded_path)) != os.path.normcase(str(expected_path)) or
            _sha256(loaded_path) != expected_sha256):
        spec = importlib.util.spec_from_file_location(module_name, str(expected_path))
        if spec is None or spec.loader is None:
            raise RunnerError("POSTPROCESS_MODULE_IMPORT_FAILED:" + module_name)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(module_name, None)
            raise
    if parent is not None:
        setattr(parent, child_name, module)
    return _verify_pinned_module(module, expected_path, expected_sha256, required_callables)


def load_pinned_launcher(path=LAUNCHER_PATH):
    _prepare_postprocess_import_paths()
    _load_pinned_module_from_file(
        "shared_fdtd.engine.gpu_observability",
        PINNED_SCRIPTS_ROOT / "shared_fdtd" / "engine" / "gpu_observability.py",
        GPU_OBSERVABILITY_SHA256, ("GpuEngineObservability",))
    if not Path(path).is_file() or _sha256(path) != LAUNCHER_SHA256:
        raise RunnerError("PINNED_LAUNCHER_HASH_MISMATCH")
    spec = importlib.util.spec_from_file_location("apcd_pw_scientific_launcher_v1", str(path))
    if spec is None or spec.loader is None:
        raise RunnerError("PINNED_LAUNCHER_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_pinned_setup_validator():
    for path,digest,label in (
            (SETUP_BUILDER_PATH,SETUP_BUILDER_SHA256,"BUILDER"),
            (SETUP_CASE_SPEC_PATH,SETUP_CASE_SPEC_SHA256,"CASE_SPEC"),
            (SETUP_AUTHORITY_MANIFEST_PATH,SETUP_AUTHORITY_MANIFEST_SHA256,"AUTHORITY_MANIFEST"),
            (SETUP_MONITOR_CONTRACT_PATH,SETUP_MONITOR_CONTRACT_SHA256,"MONITOR_CONTRACT")):
        if not path.is_file() or _sha256(path)!=digest:
            raise RunnerError("SETUP_"+label+"_PIN_MISMATCH")
    if not SETUP_VALIDATOR_PATH.is_file() or _sha256(SETUP_VALIDATOR_PATH)!=SETUP_VALIDATOR_SHA256:
        raise RunnerError("SETUP_VALIDATOR_PIN_MISMATCH")
    module_spec=importlib.util.spec_from_file_location(
        "apcd_pinned_pw_k6_setup_validator",str(SETUP_VALIDATOR_PATH))
    if module_spec is None or module_spec.loader is None:
        raise RunnerError("SETUP_VALIDATOR_LOAD_FAILED")
    module=importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    if any(not callable(getattr(module,name,None)) for name in
           ("inspect_fsp","validate_expected","semantic_projection")):
        raise RunnerError("SETUP_VALIDATOR_CALLABLE_MISSING")
    return module


def postprocess_dependency_preflight(launcher=None):
    """Import and hash every lazy dependency needed after solver return."""
    _prepare_postprocess_import_paths()
    if tuple(sys.version_info[:3]) != POSTPROCESS_PYTHON_VERSION:
        raise RunnerError("POSTPROCESS_PYTHON_VERSION_MISMATCH:" + ".".join(map(str, sys.version_info[:3])))
    numpy = importlib.import_module("numpy")
    h5py = importlib.import_module("h5py")
    lumapi = importlib.import_module("lumapi")
    if getattr(numpy, "__version__", None) != POSTPROCESS_NUMPY_VERSION:
        raise RunnerError("POSTPROCESS_NUMPY_VERSION_MISMATCH")
    if getattr(h5py, "__version__", None) != POSTPROCESS_H5PY_VERSION:
        raise RunnerError("POSTPROCESS_H5PY_VERSION_MISMATCH")
    if not callable(getattr(h5py, "File", None)):
        raise RunnerError("POSTPROCESS_H5PY_FILE_MISSING")
    lumapi_info = _verify_pinned_module(
        lumapi, LUMERICAL_API_FILE, LUMERICAL_API_SHA256, ("FDTD",))
    if not Path(LAUNCHER_PATH).is_file() or _sha256(LAUNCHER_PATH) != LAUNCHER_SHA256:
        raise RunnerError("PINNED_LAUNCHER_HASH_MISMATCH")
    launcher = launcher or load_pinned_launcher()
    launcher_callables = ("load_only_validate", "analyze", "postprocess",
                          "run_standalone_gpu_and_confirm_completion")
    if any(not callable(getattr(launcher, name, None)) for name in launcher_callables):
        raise RunnerError("PINNED_LAUNCHER_CALLABLE_MISSING")
    tmm = importlib.import_module(MDC_MODULE_NAME)
    tmm_info = _verify_pinned_module(
        tmm, VENDOR_DIR / (MDC_MODULE_NAME + ".py"), MDC_MODULE_SHA256,
        ("normal_stack_power",))
    state_info = _load_pinned_module_from_file(
        "shared_fdtd.tools.pw_complex_floquet_state_v1",
        PINNED_TOOLS_DIR / "pw_complex_floquet_state_v1.py",
        STATE_MODULE_SHA256,
        ("read_fdtd_plane", "canonical_state_from_fdtd", "save_state_npz", "state_metadata"))
    gpu_module = importlib.import_module("shared_fdtd.engine.gpu_observability")
    gpu_info = _verify_pinned_module(
        gpu_module, PINNED_SCRIPTS_ROOT / "shared_fdtd" / "engine" / "gpu_observability.py",
        GPU_OBSERVABILITY_SHA256, ("GpuEngineObservability",))
    adapter_path = Path(__file__).resolve()
    return {
        "schema": "APCD_GPU_RUNNER_V1_POSTPROCESS_DEPENDENCY_PREFLIGHT_V1",
        "result": "PASS",
        "scientific_entry_performed": False,
        "solver_run_called": False,
        "runner_adapter_sha256": _sha256(adapter_path),
        "python": {"version": ".".join(map(str, sys.version_info[:3])),
                   "executable": str(Path(sys.executable).resolve())},
        "packages": {"numpy": numpy.__version__, "h5py": h5py.__version__},
        "lumerical": {"release": "2025 R1", **lumapi_info},
        "launcher": {"path": str(Path(LAUNCHER_PATH).resolve()),
                     "sha256": LAUNCHER_SHA256,
                     "callables": list(launcher_callables),
                     "pinned_backend_id": PINNED_BACKEND_ID},
        "dependencies": {
            MDC_MODULE_NAME: {
                **tmm_info,
                "authority_branch": MDC_SOURCE_BRANCH,
                "authority_commit": MDC_SOURCE_COMMIT,
            },
            "pw_complex_floquet_state_v1": {
                **state_info, "pinned_backend_id": PINNED_BACKEND_ID},
            "gpu_observability": {
                **gpu_info, "pinned_backend_id": PINNED_BACKEND_ID},
        },
    }


class NativeAdapter:
    """Production callbacks over the immutable standalone GPU launcher."""
    def __init__(self, contract_path, launcher=None, fdtd_exe=None, gpu_resource_name=None):
        _prepare_postprocess_import_paths()
        pinned_launcher = load_pinned_launcher()
        self.postprocess_dependency_preflight = postprocess_dependency_preflight(pinned_launcher)
        self.launcher = launcher or pinned_launcher
        self.contract_path = Path(contract_path)
        with self.contract_path.open("r", encoding="utf-8") as stream:
            self.contract = json.load(stream)
        resolver = getattr(self.launcher, "_resolve_contract", None)
        if resolver is not None:
            resolver({"pw_contract": self.contract})
        self.fdtd_exe = fdtd_exe or os.environ.get("APCD_FDTD_SOLUTIONS_EXE")
        self.gpu_resource_name = gpu_resource_name or os.environ.get("APCD_GPU_RESOURCE_NAME")
        if not self.gpu_resource_name:
            raise RunnerError("GPU_RESOURCE_NAME_REQUIRED")

    def _cfg(self, manifest, run_dir):
        cfg = {"pw_contract": self.contract, "run_fsp": str(Path(run_dir) / "run.fsp"),
               "case": manifest["case_id"], "attempt": manifest["attempt_id"],
               "task": manifest["run_id"], "gpu_resource_name": self.gpu_resource_name}
        if self.fdtd_exe:
            cfg["fdtd_solutions_exe"] = self.fdtd_exe
        return cfg

    def solver(self, manifest, run_dir):
        status_path = Path(run_dir) / "status.json"
        def launch_guard(start_child):
            status = json.loads(status_path.read_text(encoding="utf-8"))
            if (status.get("run_id") != manifest["run_id"] or
                    status.get("state") != "SOLVER_ENTERED" or
                    status.get("solver_entered") is not True or
                    status.get("solver_invocations") != 1):
                raise RunnerError("DURABLE_ENTRY_GUARD_FAILED")
            return start_child()
        cfg = self._cfg(manifest, run_dir)
        log_path = Path(run_dir) / "solver.log"
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"run_id": manifest["run_id"], "event": "ADAPTER_LAUNCH"}) + "\n")
            stream.flush()
        observed = []
        def on_confirmed(event):
            if event.get("observation") != "new_solver_process":
                raise RunnerError("SOLVER_PROCESS_OBSERVATION_INVALID")
            child_pid = event.get("child_pid")
            if not isinstance(child_pid, int) or child_pid <= 0:
                raise RunnerError("SOLVER_CHILD_PID_INVALID")
            identities = []
            for row in event.get("processes", []):
                if not isinstance(row, dict):
                    continue
                pid = row.get("pid")
                if not isinstance(pid, int) or pid <= 0:
                    continue
                identity = {"pid": pid}
                for key in ("create_time_unix", "created_unix", "creation_time"):
                    value = row.get(key)
                    if isinstance(value, (int, float)):
                        identity["creation_time_unix"] = float(value)
                        break
                identities.append(identity)
            if not any(row["pid"] == child_pid for row in identities):
                identities.append({"pid": child_pid})
            current = json.loads(status_path.read_text(encoding="utf-8"))
            if (current.get("run_id") != manifest["run_id"]
                    or current.get("state") != "SOLVER_ENTERED"
                    or current.get("solver_entered") is not True
                    or current.get("solver_invocations") != 1):
                raise RunnerError("SOLVER_LINEAGE_ENTRY_MISMATCH")
            current["solver_process_lineage"] = {
                "run_id": manifest["run_id"],
                "observation": "new_solver_process",
                "child_pid": child_pid,
                "processes": identities,
                "command": event.get("command"),
                "observed_unix": __import__("time").time(),
            }
            from runner import atomic_json
            atomic_json(status_path, current)
            observed.append(current["solver_process_lineage"])

        result = self.launcher.run_standalone_gpu_and_confirm_completion(
            cfg, on_confirmed=on_confirmed, launch_guard=launch_guard)
        if not observed:
            raise RunnerError("SOLVER_PROCESS_LINEAGE_UNCONFIRMED")
        child_log = result.get("child_log")
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"run_id": manifest["run_id"], "launcher_result": result},
                                    sort_keys=True, default=str) + "\n")
            if child_log and Path(child_log).is_file():
                stream.write(Path(child_log).read_text(encoding="utf-8", errors="replace"))
        return result

    def setup_structural_validate(self, manifest, source_fsp=None, staged_fsp=None):
        """Validate the frozen setup model without querying solved result d-cards."""
        source=Path(source_fsp or manifest["pre_fsp_path"]).resolve()
        staged=Path(staged_fsp or source).resolve()
        ordered=[175,100,125,120,100,230]
        if (manifest.get("case_id")!="K6V1_S39" or manifest.get("attempt_id")!="attempt_001"
                or manifest.get("geometry")!=ordered
                or manifest.get("physical_contract_sha256")!=CONTRACT_SHA256
                or manifest.get("expansion_manifest_sha256")!="4cf521c18576c34407c158a20f748fe560910909728bed5cdadf53ec9fbe2e7f"
                or manifest.get("pre_fsp_sha256")!=SETUP_CANONICAL_FSP_SHA256
                or os.path.normcase(str(source))!=os.path.normcase(str(SETUP_CANONICAL_FSP_PATH))):
            raise RunnerError("SETUP_CASE_OR_AUTHORITY_MISMATCH")
        if (not source.is_file() or _sha256(source)!=SETUP_CANONICAL_FSP_SHA256
                or not staged.is_file() or _sha256(staged)!=SETUP_CANONICAL_FSP_SHA256):
            raise RunnerError("SETUP_SOURCE_OR_STAGED_HASH_MISMATCH")
        if _sha256(self.contract_path)!=CONTRACT_SHA256:
            raise RunnerError("SETUP_PHYSICAL_CONTRACT_HASH_MISMATCH")
        authority=json.loads(SETUP_AUTHORITY_MANIFEST_PATH.read_text(encoding="utf-8"))
        spec=json.loads(SETUP_CASE_SPEC_PATH.read_text(encoding="utf-8"))
        if (authority.get("case_id")!="K6V1_S39" or authority.get("attempt_id")!="attempt_001"
                or authority.get("canonical_pre_fsp_sha256")!=SETUP_CANONICAL_FSP_SHA256
                or authority.get("physical_contract_hash")!=CONTRACT_SHA256
                or authority.get("ordered_D_nm")!=ordered
                or authority.get("geometry_hash_sha256")!="7c582e2c53da5394d6cdf446a1ee9e16a970264b1fc78312d3f304df52403729"
                or authority.get("stage1_expansion_manifest_sha256")!="4cf521c18576c34407c158a20f748fe560910909728bed5cdadf53ec9fbe2e7f"
                or authority.get("builder_source_sha256")!=SETUP_BUILDER_SHA256
                or authority.get("source_case_json_sha256")!=SETUP_CASE_SPEC_SHA256
                or authority.get("mesh_implementation_authority")!="PW_K6_5NM_FULL_PERIOD_MESH_AUTHORITY_V1"
                or authority.get("solver_run_called") is not False
                or authority.get("scientific_entry_count")!=0
                or spec.get("case_id")!="K6V1_S39" or spec.get("attempt_id")!="attempt_001"
                or spec.get("ordered_D_nm")!=ordered
                or spec.get("physical_contract_hash")!=CONTRACT_SHA256
                or spec.get("geometry_hash_sha256")!=authority.get("geometry_hash_sha256")):
            raise RunnerError("SETUP_AUTHORITY_SPEC_MISMATCH")
        validator=load_pinned_setup_validator()
        row=validator.inspect_fsp(staged,spec)
        validation=validator.validate_expected(row,spec)
        monitor_names=["MON_IN","MON_PRENP","MON_POSTNP","MON_REFLECTION"]
        if (not isinstance(validation,dict) or validation.get("status")!="PASS"
                or validation.get("errors") not in ([],None)
                or row.get("case_id")!="K6V1_S39" or row.get("attempt_id")!="attempt_001"
                or row.get("ordered_D_nm")!=ordered
                or row.get("fsp_sha256")!=SETUP_CANONICAL_FSP_SHA256
                or not set(monitor_names).issubset(set(row.get("object_names",[])))
                or row.get("run_called") is not False
                or row.get("save_called_by_validator") is not False):
            errors=validation.get("errors",[]) if isinstance(validation,dict) else []
            raise RunnerError("SETUP_STRUCTURAL_VALIDATION_FAILED:"+json.dumps(errors,default=str))
        return {
            "schema":"APCD_GPU_RUNNER_V1_SETUP_STRUCTURAL_VALIDATION_V1",
            "result":"PASS","solver_run_called":False,"scientific_entry_performed":False,
            "validator_path":str(SETUP_VALIDATOR_PATH),"validator_sha256":SETUP_VALIDATOR_SHA256,
            "authority_manifest_sha256":SETUP_AUTHORITY_MANIFEST_SHA256,
            "case_spec_sha256":SETUP_CASE_SPEC_SHA256,
            "case_id":"K6V1_S39","attempt_id":"attempt_001",
            "source_pre_fsp_sha256":_sha256(source),"staged_pre_fsp_sha256":_sha256(staged),
            "physical_contract_sha256":CONTRACT_SHA256,
            "geometry_hash_sha256":authority["geometry_hash_sha256"],
            "ordered_D_nm":ordered,"mesh_authority":"PW_K6_5NM_FULL_PERIOD_MESH_AUTHORITY_V1",
            "monitor_object_names":monitor_names,"validation":validation,
            "setup_readback":row,
        }

    def fresh_load_validate(self, manifest, run_dir, output_root=None):
        try:
            import lumapi
            import h5py
        except ImportError as exc:
            raise RunnerError("NATIVE_FRESH_LOAD_DEPENDENCY_MISSING:" + str(exc)) from exc
        source_root = Path(run_dir)
        destination_root = source_root if output_root is None else Path(output_root)
        if output_root is not None and os.path.normcase(str(destination_root.resolve())) == os.path.normcase(str(source_root.resolve())):
            raise RunnerError("RECOVERY_OUTPUT_MUST_BE_SEPARATE")
        destination_root.mkdir(parents=True, exist_ok=True)
        cfg = self._cfg(manifest, source_root)
        with lumapi.FDTD(hide=True) as fd:
            fd.load(cfg["run_fsp"])
            self.launcher.load_only_validate(fd, cfg)
            raw, metrics, paths = self.launcher.postprocess(fd, cfg, str(destination_root))
        state_valid = all(Path(paths[key]).is_file() for key in ("state_npz", "state_metadata"))
        closure = metrics.get("max_energy_closure", {}).get("max")
        scientific_valid = (
            isinstance(closure, (int, float)) and math.isfinite(float(closure)) and
            metrics.get("order_sign", {}).get("status") == "PASS" and
            metrics.get("reference_plane_deembedding", {}).get("status") == "PASS" and
            metrics.get("lossy_gan", {}).get("status") == "PASS"
        )
        if not state_valid:
            raise RunnerError("CANONICAL_STATE_ARTIFACT_MISSING")
        if not scientific_valid:
            raise RunnerError("SCIENTIFIC_VALIDATION_FAILED")
        raw_path = destination_root / "raw" / (manifest["case_id"] + "__" + manifest["attempt_id"] + "_raw.json")
        if raw_path.is_file():
            raw["run_id"] = manifest["run_id"]
            raw_path.write_text(json.dumps(raw, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        truth_path = destination_root / "truth.h5"
        temporary_truth_path = destination_root / "truth.h5.tmp"
        with h5py.File(temporary_truth_path, "w") as h5:
            h5.attrs["run_id"] = manifest["run_id"]
            h5.attrs["case_id"] = manifest["case_id"]
            h5.attrs["attempt_id"] = manifest["attempt_id"]
            h5.attrs["launcher_id"] = "pw_scientific_launcher.py@" + LAUNCHER_SHA256
            h5.create_dataset("raw_json", data=json.dumps(raw, sort_keys=True), dtype=h5py.string_dtype("utf-8"))
            h5.create_dataset("metrics_json", data=json.dumps(metrics, sort_keys=True, default=str), dtype=h5py.string_dtype("utf-8"))
            h5.flush()
        os.replace(str(temporary_truth_path), str(truth_path))
        return {"fresh_load_verified": True, "monitors_valid": True,
                "state_valid": state_valid, "scientific_valid": scientific_valid,
                "run_id": manifest["run_id"], "truth_h5": str(truth_path),
                "truth_h5_sha256": _sha256(truth_path),
                "max_energy_closure": float(closure)}


    def gpu_snapshot(self):
        """Capture read-only GPU inventory and optional visible compute consumers."""
        gpu_query = [
            "nvidia-smi",
            "--query-gpu=index,uuid,name,memory.total,memory.used,memory.free,utilization.gpu",
            "--format=csv,noheader,nounits",
        ]
        gpu_result = subprocess.run(
            gpu_query, capture_output=True, text=True, timeout=15, check=True)
        def as_int(value):
            value = str(value).strip()
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
        gpus = []
        for fields in csv.reader(io.StringIO(gpu_result.stdout)):
            fields = [value.strip() for value in fields]
            if not fields or not any(fields):
                continue
            if len(fields) < 7:
                raise RunnerError("GPU_SNAPSHOT_PARSE_FAILED")
            gpus.append({
                "index": as_int(fields[0]),
                "uuid": fields[1] or None,
                "name": fields[2] or None,
                "memory_total_mib": as_int(fields[3]),
                "memory_used_mib": as_int(fields[4]),
                "memory_free_mib": as_int(fields[5]),
                "utilization_gpu_percent": as_int(fields[6]),
            })
        if not gpus:
            raise RunnerError("GPU_SNAPSHOT_EMPTY")
        process_query = [
            "nvidia-smi",
            "--query-compute-apps=gpu_uuid,pid,process_name,used_memory",
            "--format=csv,noheader,nounits",
        ]
        process_status = "AVAILABLE"
        process_error = None
        processes = []
        try:
            process_result = subprocess.run(
                process_query, capture_output=True, text=True, timeout=10, check=True)
            for fields in csv.reader(io.StringIO(process_result.stdout)):
                fields = [value.strip() for value in fields]
                if not fields or not any(fields):
                    continue
                if len(fields) < 4 or as_int(fields[1]) is None:
                    process_status = "PARTIAL"
                    continue
                processes.append({
                    "gpu_uuid": fields[0] or None,
                    "pid": as_int(fields[1]),
                    "process_name": fields[2] or None,
                    "used_memory_mib": as_int(fields[3]),
                })
        except (OSError, subprocess.SubprocessError) as exc:
            process_status = "UNAVAILABLE"
            process_error = (type(exc).__name__ + ": " + str(exc))[:300]
            processes = None
        free_values = [gpu["memory_free_mib"] for gpu in gpus]
        free_mib = min(free_values) if all(value is not None for value in free_values) else -1
        external = None if processes is None else [
            dict(process, ownership="external_or_unattributed") for process in processes]
        return {
            "captured_unix": time.time(),
            "captured_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "requested_resource_name": self.gpu_resource_name,
            "minimum_free_mib_policy": MIN_GPU_FREE_MIB,
            "memory_unit": "MiB",
            "gpus": gpus,
            "free_mib": free_mib,
            "per_gpu_free_mib": free_values,
            "visible_compute_processes": processes,
            "compute_process_query_status": process_status,
            "compute_process_query_error": process_error,
            "external_consumers": external,
            "process_query_alone_blocks_launch": False,
        }

    @staticmethod
    def _process_identity_state(pid, creation_time_unix=None):
        """Return live/dead/unknown for one exact runner-observed PID."""
        if os.name != "nt":
            try:
                os.kill(int(pid), 0)
                return "live"
            except (ProcessLookupError, FileNotFoundError):
                return "dead"
            except OSError:
                return "unknown"
        try:
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            handle = kernel32.OpenProcess(0x1000, False, int(pid))
            if not handle:
                return "dead" if ctypes.get_last_error() == 87 else "unknown"
            creation = wintypes.FILETIME()
            exit_time = wintypes.FILETIME()
            kernel_time = wintypes.FILETIME()
            user_time = wintypes.FILETIME()
            try:
                if not kernel32.GetProcessTimes(handle, ctypes.byref(creation),
                        ctypes.byref(exit_time), ctypes.byref(kernel_time), ctypes.byref(user_time)):
                    return "unknown"
            finally:
                kernel32.CloseHandle(handle)
            actual = ((creation.dwHighDateTime << 32) | creation.dwLowDateTime) / 10000000.0 - 11644473600.0
            if creation_time_unix is None:
                return "live"
            return "live" if abs(actual - float(creation_time_unix)) < 1.0 else "dead"
        except Exception:
            return "unknown"

    @staticmethod
    def runner_owner_probe(root):
        root = Path(root)
        if (root / "active_run.json").exists():
            return True
        lock_path=root/".runner.lock"
        if lock_path.exists():
            lock_record=read_json(lock_path,{})
            if not isinstance(lock_record,dict) or lock_record.get("pid")!=os.getpid():
                return True
        # Only inspect PIDs recorded by this runner after the pinned launcher
        # observed a new process for the exact run.fsp. No OS-wide census.
        for status_path in (root / "runs").glob("*/*/*/status.json"):
            status = json.loads(status_path.read_text(encoding="utf-8"))
            if status.get("state") not in {"SOLVER_ENTERED", "SOLVER_RETURNED", "FAILED_POSTENTRY"}:
                continue
            lineage = status.get("solver_process_lineage")
            if not isinstance(lineage,dict):
                registry=read_json(root/"registry.json",{})
                rows=registry.get("runs",[]) if isinstance(registry,dict) else []
                from runner import s35_effective_predecessor
                recovered=s35_effective_predecessor(root,rows)
                if (status.get("case_id")=="K6V1_S35"
                        and status.get("attempt_id")=="attempt_001"
                        and status.get("run_id")=="S35-20261002T044427Z-e702b2ac"
                        and status.get("state")=="FAILED_POSTENTRY"
                        and isinstance(recovered,dict)
                        and recovered.get("effective_scientific_outcome")=="RECOVERED_TRUTH_VALID"):
                    continue
                return True
            if (lineage.get("run_id") != status.get("run_id")
                    or lineage.get("observation") != "new_solver_process"):
                return True
            identities = list(lineage.get("processes") or [])
            child_pid = lineage.get("child_pid")
            if isinstance(child_pid, int) and not any(
                    isinstance(row, dict) and row.get("pid") == child_pid for row in identities):
                identities.append({"pid": child_pid})
            if not identities:
                return True
            for row in identities:
                if not isinstance(row, dict) or not isinstance(row.get("pid"), int):
                    return True
                state = NativeAdapter._process_identity_state(
                    row["pid"], row.get("creation_time_unix"))
                if state != "dead":
                    return True
        return False


def run_cli(manifest_path, adapter_factory=NativeAdapter, test_output_root=None):
    manifest, contract_path = read_cli_manifest(manifest_path)
    adapter = adapter_factory(contract_path)
    preflight = getattr(adapter, "postprocess_dependency_preflight", None)
    if not isinstance(preflight, dict) or preflight.get("result") != "PASS":
        raise RunnerError("POSTPROCESS_DEPENDENCY_PREFLIGHT_FAILED")
    setup_validator=getattr(adapter,"setup_structural_validate",None)
    if not callable(setup_validator):
        raise RunnerError("SETUP_STRUCTURAL_VALIDATOR_MISSING")
    output_root = (PRODUCTION_RUNNER_ROOT if test_output_root is None
                   else Path(test_output_root))
    preflight_path = (output_root / "preflight" / manifest["case_id"] /
                      manifest["attempt_id"] / manifest["run_id"] /
                      "postprocess_dependency_preflight.json")
    preflight_record = {
        "schema": "APCD_GPU_RUNNER_V1_POSTPROCESS_PREFLIGHT_RECORD_V1",
        "result": "PASS",
        "case_id": manifest["case_id"],
        "attempt_id": manifest["attempt_id"],
        "run_id": manifest["run_id"],
        "preflight": preflight,
    }
    if preflight_path.exists():
        existing = json.loads(preflight_path.read_text(encoding="utf-8"))
        if existing != preflight_record:
            raise RunnerError("POSTPROCESS_PREFLIGHT_CONFLICT")
    else:
        atomic_json(preflight_path, preflight_record)
    return run_one(manifest, output_root, adapter.solver, adapter.fresh_load_validate,
                   adapter.gpu_snapshot, adapter.runner_owner_probe, setup_validator)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run one approved APCD GPU manifest")
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("run-one")
    one.add_argument("case_manifest")
    args = parser.parse_args(argv)
    try:
        result = run_cli(args.case_manifest)
    except Exception as exc:
        print("RUNNER_ERROR:" + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
