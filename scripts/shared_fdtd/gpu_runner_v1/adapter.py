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
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path

from runner import (CONTRACT_SHA256, ENTRY_STATES, EXPANSION_SHA256, MANIFEST_KEYS,
                    MIN_GPU_FREE_MIB, PRODUCTION_RUNNER_ROOT, RunnerError,
                    atomic_json, read_json, run_one)

LAUNCHER_PATH = Path(r"D:\apcd_runtime\shared_v3_backend\pw_powernorm_v1_aaaa25b53a9a3322\scripts\shared_fdtd\tools\pw_scientific_launcher.py")
LAUNCHER_SHA256 = "7639b9d07f041d5f8af3121286f6ce5aae4d8b18b66f5368052c627da219307f"
PINNED_BACKEND_ID = "pw_powernorm_v1_aaaa25b53a9a3322"
PINNED_SCRIPTS_ROOT = LAUNCHER_PATH.parents[2]
PINNED_TOOLS_DIR = LAUNCHER_PATH.parent
VENDOR_DIR = Path(__file__).resolve().parent / "vendor"
MDC_MODULE_NAME = "mdc_tmm_complex_incident_power_v1"
MDC_SOURCE_BRANCH = "work/mdc-np-coupling-ml-v1"
MDC_SOURCE_COMMIT = "46af82357f269aea0c77105a03e7ca9da645ca8f"
MDC_MODULE_SHA256 = "12d2d95bd99fc6e18fec9ac17ab066a5a1fc4a3ddf1a6e5a8c0a625da959ff4b"
STATE_MODULE_SHA256 = "31cb2b602b1fa74ff09404c8111239f9dcf4a8c4b5ac1944a9300b2c23efaafb"
GPU_OBSERVABILITY_SHA256 = "e6b01c985e79fa2adcb280ab0d6cca4609dcbefc23e7d781e3fba147cbd89861"
GLOBAL_ENTRY_CONTROL_DB_PATH = Path(r"D:\apcd_runtime\global_fdtd_control_v3\control.sqlite3")
GLOBAL_ENTRY_CONTROL_SCHEMA = "APCD_GPU_RUNNER_GLOBAL_ENTRY_HOLD_SNAPSHOT_V1"
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
SETUP_AUTHORITY_ROOT = COUPLING_AUTHORITY_ROOT / "outputs/coupling_ml/PW_K6_5NM_FULL_PERIOD_MESH_AUTHORITY_V1"
SETUP_STAGE1_CASE_ROOT = COUPLING_AUTHORITY_ROOT / "outputs/coupling_ml/PW_K6_FIXED_MDC_12G_STAGE1_HF_EXECUTION_V1"
SETUP_EXPANSION_MANIFEST_PATH = COUPLING_AUTHORITY_ROOT / "reports/coupling/PW_K6_FIXED_MDC_UNBIASED_EXPANSION_MANIFEST_V1.json"
SETUP_GEOMETRY_SEED_MANIFEST_PATH = COUPLING_AUTHORITY_ROOT / "reports/coupling/PW_K6_SEED_DB_V1_GEOMETRY_MANIFEST.json"
SETUP_GEOMETRY_SEED_MANIFEST_SHA256 = "463ceaece52121b1a968d22881944c082a26041c16b4489c25b6a0b8f44db62b"
SETUP_MONITOR_CONTRACT_PATH = COUPLING_AUTHORITY_ROOT / "contracts/coupling/medium_pw/MEDIUM_PW_MONITOR_CONTRACT_V1.json"
SETUP_MONITOR_CONTRACT_SHA256 = "a84d8526889084f2b3b09022402ca93b2947939cb744f071a4b19bc6eb09172f"
SETUP_AUTHORITY_MANIFEST_SCHEMA = "PW_K6_5NM_FULL_PERIOD_MESH_AUTHORITY_V1_INPUT_V1"
SETUP_LOAD_ONLY_SCHEMA = "PW_K6_5NM_FULL_PERIOD_MESH_LOAD_ONLY_VALIDATION_V1"
CONTROLLED_POLICY_PATH = Path(__file__).resolve().parent / "controlled_admission_policy_v1.json"
CONTROLLED_AUTHORITY_PATH = Path(__file__).resolve().parent / "controlled_admission_authority_v1.json"
CONTROLLED_POLICY_SHA256 = "b89924544fe506f8775058730d6f491bca4206c1f5f55f7d247e338f9d04dd45"
CONTROLLED_AUTHORITY_SHA256 = "a78274be660abf9d112f9c4a516cb647a00ebbb65069253abf38cca2e65efa35"


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()



def read_global_entry_control(db_path=None):
    """Read-only fail-closed snapshot of global hold state; never allocates a V3 slot."""
    path = Path(GLOBAL_ENTRY_CONTROL_DB_PATH if db_path is None else db_path)
    try:
        path = path.resolve(strict=True)
        if not path.is_file():
            raise RunnerError("GLOBAL_ENTRY_CONTROL_DB_MISSING")
        def file_state(candidate):
            if not candidate.exists():
                return None
            stat = candidate.stat()
            return {"size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns,
                    "sha256": _sha256(candidate)}
        wal = Path(str(path) + "-wal")
        before = {"db": file_state(path), "wal": file_state(wal)}
        uri = "file:" + path.as_posix() + "?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=5.0)
        try:
            connection.execute("BEGIN")
            tables = {row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            if not {"admission_control", "hold_lifecycle"}.issubset(tables):
                raise RunnerError("GLOBAL_ENTRY_CONTROL_SCHEMA_MISSING")
            admission_columns = {row[1] for row in connection.execute(
                "PRAGMA table_info(admission_control)")}
            hold_columns = {row[1] for row in connection.execute(
                "PRAGMA table_info(hold_lifecycle)")}
            if not {"control_id", "new_entry_hold", "control_generation", "health_status"}.issubset(admission_columns):
                raise RunnerError("GLOBAL_ENTRY_CONTROL_SCHEMA_INVALID")
            if not {"hold_id", "scope", "status"}.issubset(hold_columns):
                raise RunnerError("GLOBAL_ENTRY_HOLD_SCHEMA_INVALID")
            rows = connection.execute(
                "SELECT new_entry_hold, control_generation, health_status FROM admission_control WHERE control_id=1"
            ).fetchall()
            if len(rows) != 1:
                raise RunnerError("GLOBAL_ENTRY_CONTROL_ROW_INVALID")
            hold_flag, generation, health_status = rows[0]
            if not isinstance(health_status, str) or health_status != "PASS":
                raise RunnerError("GLOBAL_ENTRY_CONTROL_HEALTH_BLOCKED")
            if type(hold_flag) is not int or hold_flag not in (0, 1):
                raise RunnerError("GLOBAL_ENTRY_HOLD_VALUE_INVALID")
            if type(generation) is not int or generation < 0:
                raise RunnerError("GLOBAL_ENTRY_CONTROL_GENERATION_INVALID")
            active_holds = sorted(row[0] for row in connection.execute(
                "SELECT hold_id FROM hold_lifecycle WHERE scope='GLOBAL' AND status='ACTIVE'"
            ).fetchall())
            connection.rollback()
        finally:
            connection.close()
        after = {"db": file_state(path), "wal": file_state(wal)}
        if before != after:
            raise RunnerError("GLOBAL_ENTRY_CONTROL_CHANGED_DURING_READ")
        if hold_flag == 1 or active_holds:
            ids = ",".join(active_holds) if active_holds else "none"
            raise RunnerError(
                "GLOBAL_NEW_ENTRY_HOLD_ACTIVE:hold_ids=" + ids + ";generation=" + str(generation))
        evidence = {
            "schema": GLOBAL_ENTRY_CONTROL_SCHEMA,
            "result": "PASS",
            "control_db_path": str(path),
            "control_db_sha256": after["db"]["sha256"],
            "control_wal_sha256": after["wal"]["sha256"] if after["wal"] else None,
            "control_generation": generation,
            "health_status": health_status,
            "new_entry_hold": 0,
            "active_global_hold_ids": [],
        }
        evidence["snapshot_sha256"] = hashlib.sha256(
            json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        return evidence
    except RunnerError:
        raise
    except (OSError, sqlite3.Error, ValueError) as exc:
        raise RunnerError("GLOBAL_ENTRY_CONTROL_UNREADABLE:" + type(exc).__name__) from exc


def _controlled_start_generation_sha256(context, manifest):
    import controlled_admission_v1 as controlled
    fields = {
        "schema": "APCD_GPU_RUNNER_CONTROLLED_START_GENERATION_V1",
        "route_version": context["route_version"], "case_class": context["case_class"],
        "case_id": manifest["case_id"], "attempt_id": manifest["attempt_id"],
        "run_id": manifest.get("run_id"),
        "route_policy_sha256": context["route_policy_sha256"],
        "route_authority_sha256": context["route_authority_sha256"],
        "source_manifest_path": context["source_manifest_path"],
        "source_manifest_sha256": context["source_manifest_sha256"],
        "physical_contract_path": context["physical_contract_path"],
        "physical_contract_sha256": context["physical_contract_sha256"],
        "physical_contract_semantic_sha256": context["physical_contract_semantic_sha256"],
        "setup_contract_fingerprint_sha256": context["setup_contract_fingerprint_sha256"],
        "source_fsp_path": context["source_fsp_path"],
        "staged_fsp_path": context["staged_fsp_path"],
        "staged_fsp_sha256": context["staged_fsp_sha256"],
        "pre_entry_setup_load_proof_path": context["pre_entry_setup_load_proof_path"],
        "pre_entry_setup_load_proof_sha256": context["pre_entry_setup_load_proof_sha256"],
    }
    return controlled.canonical_sha256(fields)


def _wait_for_durable_gpu_h5_sidecar(path, minimum_monitor_groups, timeout_seconds=45.0):
    import h5py
    path=Path(path); deadline=time.monotonic()+float(timeout_seconds)
    previous=None; stable=0; problem="SIDECAR_NOT_PRESENT"
    while time.monotonic()<deadline:
        try:
            stat=path.stat()
            if not path.is_file() or stat.st_size<=0:
                problem="SIDECAR_EMPTY"; time.sleep(0.25); continue
            signature=(stat.st_size,stat.st_mtime_ns)
            stable=stable+1 if signature==previous else 0
            previous=signature
            if stable>=2:
                with h5py.File(path,"r") as h5:
                    groups=sorted(n for n in h5.keys()
                        if re.fullmatch(r"Monitor\d+",str(n)) and isinstance(h5[n],h5py.Group))
                    if len(groups)<int(minimum_monitor_groups):
                        problem="MONITOR_GROUP_COUNT:"+str(len(groups))
                    else:
                        valid=True
                        for name in groups:
                            group=h5[name]
                            for component in ("Ex","Ey","Ez","Hx","Hy","Hz"):
                                ds=group.get(component)
                                if (not isinstance(ds,h5py.Dataset) or ds.ndim!=4
                                        or any(size<=0 for size in ds.shape) or ds.dtype.kind not in "uifc"):
                                    valid=False; problem="MONITOR_FIELD_SCHEMA:"+name+":"+component; break
                            if not valid: break
                        if valid:
                            with path.open("r+b") as stream:
                                stream.flush(); os.fsync(stream.fileno())
                            after=path.stat()
                            if (after.st_size,after.st_mtime_ns)==signature:
                                return {"result":"PASS","path":str(path.resolve()),
                                    "size_bytes":after.st_size,"sha256":_sha256(path),
                                    "monitor_groups":groups,
                                    "minimum_monitor_groups":int(minimum_monitor_groups),
                                    "stable_observations":stable}
                            previous=None; stable=0
            time.sleep(0.25)
        except Exception as exc:
            problem=type(exc).__name__+":"+str(exc); time.sleep(0.25)
    raise RunnerError("GPU_H5_SIDECAR_NOT_DURABLE:"+problem)



def read_cli_manifest(path):
    """Read the core run manifest plus the approved per-case setup authority."""
    with open(path, "r", encoding="utf-8") as stream:
        envelope = json.load(stream)
    if not isinstance(envelope, dict):
        raise RunnerError("MANIFEST_INVALID")
    if "controlled_admission" in envelope:
        from controlled_admission_v1 import validate_controlled_envelope
        envelope = __import__("controlled_admission_v1").read_json(Path(path))
        manifest, contract_file, controlled_context = validate_controlled_envelope(
            envelope, manifest_keys=MANIFEST_KEYS, preflight=False,
            policy_path=CONTROLLED_POLICY_PATH, authority_path=CONTROLLED_AUTHORITY_PATH,
            expected_policy_sha256=CONTROLLED_POLICY_SHA256,
            expected_authority_sha256=CONTROLLED_AUTHORITY_SHA256)
        from runner import validate_manifest
        validate_manifest(manifest, admitted_contract_sha256=controlled_context["physical_contract_sha256"])
        controlled_context["envelope_path"] = str(Path(path).resolve())
        manifest["_controlled_admission"] = controlled_context
        return manifest, contract_file
    contract_path = envelope.get("physical_contract_path")
    if not isinstance(contract_path, str) or not contract_path:
        raise RunnerError("PHYSICAL_CONTRACT_PATH_MISSING")
    contract_file = Path(contract_path)
    if not contract_file.is_file():
        raise RunnerError("PHYSICAL_CONTRACT_MISSING")
    manifest = {key: envelope[key] for key in MANIFEST_KEYS if key in envelope}
    from runner import validate_manifest
    validate_manifest(manifest)
    if _sha256(contract_file) != manifest["physical_contract_sha256"]:
        raise RunnerError("PHYSICAL_CONTRACT_FILE_HASH_MISMATCH")
    pre = Path(manifest["pre_fsp_path"])
    if not pre.is_file():
        raise RunnerError("PRE_FSP_MISSING")
    if _sha256(pre) != manifest["pre_fsp_sha256"]:
        raise RunnerError("PRE_FSP_HASH_MISMATCH")

    setup_authority = envelope.get("setup_authority")
    authority_keys = {
        "authority_manifest_path", "authority_manifest_sha256",
        "load_only_validation_path", "load_only_validation_sha256",
    }
    if not isinstance(setup_authority, dict) or set(setup_authority) != authority_keys:
        raise RunnerError("SETUP_AUTHORITY_MANIFEST_MISSING")
    for key in ("authority_manifest_path", "load_only_validation_path"):
        if not isinstance(setup_authority.get(key), str) or not setup_authority[key]:
            raise RunnerError("SETUP_AUTHORITY_PATH_MISSING:" + key)
    for key in ("authority_manifest_sha256", "load_only_validation_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", str(setup_authority.get(key, ""))):
            raise RunnerError("SETUP_AUTHORITY_HASH_INVALID:" + key)
    allowed_envelope_keys = set(MANIFEST_KEYS) | {"physical_contract_path", "setup_authority"}
    if set(envelope) != allowed_envelope_keys:
        raise RunnerError("MANIFEST_KEYS_INVALID")
    # This private value is removed before run_one persists the strict core manifest.
    manifest["_setup_authority"] = setup_authority
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
            (SETUP_EXPANSION_MANIFEST_PATH,EXPANSION_SHA256,"EXPANSION_MANIFEST"),
            (SETUP_GEOMETRY_SEED_MANIFEST_PATH,SETUP_GEOMETRY_SEED_MANIFEST_SHA256,"GEOMETRY_SEED_MANIFEST"),
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
           ("inspect_fsp","validate_expected","compare_semantics")):
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


_LICENSE_STARTUP_FAILURE_MARKERS = (
    "ansysli exited or could not read server port",
    "failed to set up ansys license sharing",
    "could not connect to ansys license server",
)


def solver_process_observation_failure(event, run_dir):
    """Classify a valid child-return observation without weakening entry guards."""
    if not isinstance(event, dict):
        return "SOLVER_PROCESS_OBSERVATION_INVALID"
    observation = event.get("observation")
    if observation == "new_solver_process":
        return None
    if observation == "standalone_child_returned":
        log_value = event.get("child_log")
        log_path = Path(log_value) if isinstance(log_value, str) and log_value else (Path(run_dir) / "gpu_standalone" / "child.log")
        try:
            child_log = log_path.read_text(encoding="utf-8", errors="replace").casefold()
        except OSError:
            child_log = ""
        if any(marker in child_log for marker in _LICENSE_STARTUP_FAILURE_MARKERS):
            return "LUMERICAL_LICENSE_STARTUP_FAILED"
        return "SOLVER_PROCESS_NOT_OBSERVED_CHILD_RETURNED"
    return "SOLVER_PROCESS_OBSERVATION_INVALID"


ANSYS_ACL_PORT_RANGE_ENV = "ANSYS_LICENSING_DESKTOP_PORT_RANGE"
ANSYS_ACL_PORT_RANGE_DEFAULT = "6200:6299"

def _configure_ansys_acl_port_range():
    """Keep Runner-launched Ansys ACL sessions off occupied desktop ports."""
    return os.environ.setdefault(ANSYS_ACL_PORT_RANGE_ENV, ANSYS_ACL_PORT_RANGE_DEFAULT)

class NativeAdapter:
    """Production callbacks over the immutable standalone GPU launcher."""
    def __init__(self, contract_path, launcher=None, fdtd_exe=None, gpu_resource_name=None):
        _configure_ansys_acl_port_range()
        _prepare_postprocess_import_paths()
        pinned_launcher = load_pinned_launcher()
        self.postprocess_dependency_preflight = postprocess_dependency_preflight(pinned_launcher)
        self.launcher = launcher or pinned_launcher
        self.contract_path = Path(contract_path)
        self._controlled_monitor_sessions = {}
        self._controlled_monitor_cache = {}
        self._controlled_persist_monitor_names = ()
        self._controlled_expected_h5_monitor_count = 0
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


    def _run_standalone_gpu_with_extra_field_monitors(self,cfg,extra_monitor_names,on_confirmed,launch_guard):
        extra=tuple(dict.fromkeys(extra_monitor_names))
        if not extra:
            return self.launcher.run_standalone_gpu_and_confirm_completion(
                cfg,on_confirmed=on_confirmed,launch_guard=launch_guard)
        if any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}",name) for name in extra):
            raise RunnerError("CONTROLLED_EXTRA_MONITOR_NAME_INVALID")
        builder=getattr(self.launcher,"_standalone_gpu_script",None)
        if not callable(builder):
            raise RunnerError("PINNED_LAUNCHER_GPU_SCRIPT_BUILDER_MISSING")
        def extended_builder(resource_name,monitor_names):
            combined=list(monitor_names)
            for name in extra:
                if name not in combined: combined.append(name)
            return builder(resource_name,combined)
        self.launcher._standalone_gpu_script=extended_builder
        try:
            return self.launcher.run_standalone_gpu_and_confirm_completion(
                cfg,on_confirmed=on_confirmed,launch_guard=launch_guard)
        finally:
            self.launcher._standalone_gpu_script=builder

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
            observation_failure = solver_process_observation_failure(event, run_dir)
            if observation_failure:
                raise RunnerError(observation_failure)
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

        extra_monitors=tuple(getattr(self,"_controlled_persist_monitor_names",()))
        if extra_monitors:
            result=self._run_standalone_gpu_with_extra_field_monitors(
                cfg,extra_monitors,on_confirmed,launch_guard)
            minimum_groups=int(getattr(self,"_controlled_expected_h5_monitor_count",0))
            h5_ready=_wait_for_durable_gpu_h5_sidecar(
                Path(run_dir)/"run"/"run_output.h5",minimum_groups)
            with log_path.open("a",encoding="utf-8") as stream:
                stream.write(json.dumps({"run_id":manifest["run_id"],
                    "event":"GPU_H5_SIDECAR_READY","h5_bundle":h5_ready},
                    sort_keys=True,default=str)+"\n")
            result=dict(result,h5_sidecar_ready=h5_ready,
                        persisted_extra_field_monitors=list(extra_monitors))
        else:
            result=self.launcher.run_standalone_gpu_and_confirm_completion(
                cfg,on_confirmed=on_confirmed,launch_guard=launch_guard)
        if not observed:
            raise RunnerError("SOLVER_PROCESS_LINEAGE_UNCONFIRMED")
        child_log = result.get("child_log")
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"run_id": manifest["run_id"], "launcher_result": result},
                                    sort_keys=True, default=str) + "\n")
            if child_log and Path(child_log).is_file():
                stream.write(Path(child_log).read_text(encoding="utf-8", errors="replace"))
        return result

    def _revalidate_controlled_setup_context(self, manifest, context):
        """Re-read every controlled authority and content hash immediately before entry."""
        import controlled_admission_v1 as controlled
        envelope_path = Path(context.get("envelope_path", "")).resolve(strict=True)
        envelope = controlled.read_json(envelope_path)
        preflight_only = context.get("preflight_only") is True
        core, contract_path, fresh_context = controlled.validate_controlled_envelope(
            envelope, manifest_keys=MANIFEST_KEYS, preflight=preflight_only,
            policy_path=CONTROLLED_POLICY_PATH, authority_path=CONTROLLED_AUTHORITY_PATH,
            expected_policy_sha256=CONTROLLED_POLICY_SHA256,
            expected_authority_sha256=CONTROLLED_AUTHORITY_SHA256)
        if core != manifest:
            raise RunnerError("CONTROLLED_MANIFEST_CHANGED_BEFORE_SETUP_LOAD")
        if (os.path.normcase(str(contract_path.resolve()))
                != os.path.normcase(str(self.contract_path.resolve()))
                or _sha256(self.contract_path) != fresh_context["physical_contract_sha256"]
                or self.contract != controlled.read_json(contract_path)):
            raise RunnerError("CONTROLLED_CONTRACT_CHANGED_AFTER_ADAPTER_INIT")
        fresh_context["envelope_path"] = str(envelope_path)
        fresh_context["preflight_only"] = preflight_only
        return fresh_context


    def controlled_pre_entry_revalidate(self, manifest, run_dir, staged_fsp,
                                        setup_validation, case_authority):
        """Re-read the controlled envelope and quota after LOAD, immediately before entry."""
        import controlled_admission_v1 as controlled
        initial=setup_validation.get("start_time_revalidation") if isinstance(setup_validation,dict) else None
        if (not isinstance(initial,dict) or initial.get("result")!="PASS"
                or initial.get("preflight_only") is not False or setup_validation.get("result")!="PASS"):
            raise RunnerError("CONTROLLED_PRE_ENTRY_SETUP_PROOF_MISSING")
        status=read_json(Path(run_dir)/"status.json")
        if (status.get("run_id")!=manifest.get("run_id") or status.get("state")!="PRECHECK_PASS"
                or status.get("solver_entered") is not False or status.get("solver_invocations")!=0):
            raise RunnerError("CONTROLLED_PRE_ENTRY_RUN_STATE_CHANGED")
        fresh=self._revalidate_controlled_setup_context(manifest,case_authority)
        generation=_controlled_start_generation_sha256(fresh,manifest)
        if generation!=initial.get("control_generation_sha256"):
            raise RunnerError("CONTROL_GENERATION_CHANGED_BEFORE_SOLVER_ENTRY")
        staged_fsp=Path(staged_fsp).resolve(strict=True)
        if (_sha256(staged_fsp)!=manifest.get("pre_fsp_sha256")
                or _sha256(staged_fsp)!=fresh.get("staged_fsp_sha256")):
            raise RunnerError("CONTROLLED_STAGED_FSP_CHANGED_BEFORE_ENTRY")
        k6_budget_revalidation=None
        if fresh.get("case_class")=="K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1":
            grant=fresh.get("k6_v2_solver_entry_budget")
            if not isinstance(grant,dict):
                raise RunnerError("K6_V2_RUNTIME_BUDGET_GRANT_MISSING")
            run_path=Path(run_dir).resolve(strict=True)
            try:
                runner_root=run_path.parents[3]
            except IndexError as exc:
                raise RunnerError("K6_V2_RUNNER_ROOT_UNRESOLVED") from exc
            registry_path=runner_root/"registry.json"
            if not registry_path.is_file():
                raise RunnerError("K6_V2_RUNNER_REGISTRY_MISSING")
            try:
                registry_bytes=registry_path.read_bytes()
                registry_sha=hashlib.sha256(registry_bytes).hexdigest()
                registry=json.loads(registry_bytes.decode("utf-8"))
            except (OSError,UnicodeError,ValueError) as exc:
                raise RunnerError("K6_V2_RUNNER_REGISTRY_READ_FAILED") from exc
            try:
                counts=controlled.validate_k6_v2_registry_entry_budget(
                    registry,grant=grant,case_id=manifest["case_id"],
                    attempt_id=manifest["attempt_id"],entry_states=ENTRY_STATES)
            except controlled.ControlledAdmissionError as exc:
                raise RunnerError(str(exc)) from exc
            k6_budget_revalidation={
                "budget_id":grant["budget_id"],
                "budget_sha256":grant["budget_sha256"],
                "authorization_task_id":grant["authorization_task_id"],
                "case_id":manifest["case_id"],"attempt_id":manifest["attempt_id"],
                "role":grant["role"],"runner_registry_path":str(registry_path),
                "runner_registry_sha256":registry_sha,**counts,
            }
        gpu_snapshot=self.gpu_snapshot()
        try: free_mib=int(gpu_snapshot.get("free_mib",-1))
        except (AttributeError,TypeError,ValueError): free_mib=-1
        if free_mib<MIN_GPU_FREE_MIB:
            raise RunnerError("CONTROLLED_START_GPU_QUOTA_UNAVAILABLE")
        extra=[]; minimum_groups=0
        readback=setup_validation.get("setup_readback",{})
        if fresh.get("case_class","").startswith("EXT02_"):
            expected=controlled._expected_monitor(fresh["policy"])
            added=readback.get("added_monitor"); existing=readback.get("existing_monitor_readbacks")
            if (not isinstance(added,dict) or added.get("name")!=expected["name"]
                    or added.get("components")!=["Ex","Ey","Ez","Hx","Hy","Hz"]
                    or not isinstance(existing,dict) or len(existing)!=4):
                raise RunnerError("CONTROLLED_GPU_H5_MONITOR_AUTHORITY_MISMATCH")
            extra=[expected["name"]]; minimum_groups=len(existing)+1
        self._controlled_persist_monitor_names=tuple(extra)
        self._controlled_expected_h5_monitor_count=minimum_groups
        return {
            "schema":"APCD_GPU_RUNNER_CONTROLLED_PRE_ENTRY_REVALIDATION_V1","result":"PASS",
            "case_id":manifest["case_id"],"attempt_id":manifest["attempt_id"],"run_id":manifest["run_id"],
            "route_version":fresh["route_version"],"route_policy_sha256":fresh["route_policy_sha256"],
            "route_authority_sha256":fresh["route_authority_sha256"],
            "source_manifest_sha256":fresh["source_manifest_sha256"],
            "physical_contract_sha256":fresh["physical_contract_sha256"],
            "setup_contract_fingerprint_sha256":fresh["setup_contract_fingerprint_sha256"],
            "source_fsp_sha256":fresh["staged_fsp_sha256"],"staged_fsp_sha256":_sha256(staged_fsp),
            "pre_entry_setup_load_proof_sha256":fresh["pre_entry_setup_load_proof_sha256"],
            "control_generation_sha256":generation,
            "initial_setup_load_generation_sha256":initial["control_generation_sha256"],
            "gpu_quota_minimum_free_mib":MIN_GPU_FREE_MIB,"gpu_snapshot":gpu_snapshot,
            "gpu_snapshot_sha256":hashlib.sha256(json.dumps(gpu_snapshot,sort_keys=True,default=str).encode("utf-8")).hexdigest(),
            "authorized_extra_field_monitors":extra,"minimum_h5_monitor_groups":minimum_groups,
            "k6_v2_solver_entry_budget_revalidation":k6_budget_revalidation,
            "owner_fence_checked_by_runner_core_before_and_after":True,
            "solver_run_called":False,"scientific_entry_performed":False,
        }

    def _controlled_monitor_readback(self, fsp_path, expected):
        """Return monitor properties from a fresh API LOAD; this function never runs FDTD."""
        _prepare_postprocess_import_paths()
        lumapi = importlib.import_module("lumapi")
        resolved = str(Path(fsp_path).resolve())
        name = expected["name"]
        cache_key = (resolved, name)
        if cache_key in self._controlled_monitor_cache:
            return dict(self._controlled_monitor_cache[cache_key])
        fd = self._controlled_monitor_sessions.get(resolved)
        if fd is None:
            fd = lumapi.FDTD(resolved, hide=True)
            self._controlled_monitor_sessions[resolved] = fd
        try:
            def get(prop):
                try:
                    value = fd.getnamed(name, prop)
                    if hasattr(value, "tolist"):
                        value = value.tolist()
                    if isinstance(value, (str, int, float, bool)) or value is None:
                        return value
                    return str(value)
                except Exception as exc:
                    raise RunnerError("CONTROLLED_MONITOR_READBACK_FAILED:" + name + ":" + prop) from exc
            nm = lambda prop: round(float(get(prop)) * 1e9, 9)
            component_props = ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz")
            components = [key for key in component_props
                          if get("output " + key) in (True, 1, 1.0, "1")]
            result = {
                "name": name, "type": get("type"), "enabled": get("enabled"),
                "monitor_type": get("monitor type"),
                "x_nm": nm("x"), "y_nm": nm("y"), "z_nm": nm("z"),
                "x_span_nm": nm("x span"), "y_span_nm": nm("y span"),
                "frequency_points": int(get("frequency points")),
                "wavelength_center_nm": nm("wavelength center"),
                "wavelength_span_nm": nm("wavelength span"),
                "components": components,
                "spatial_interpolation": get("spatial interpolation"),
                "down_sample": {axis: int(get("down sample " + axis)) for axis in ("x", "y", "z")},
                "use_source_limits": get("use source limits"),
                "override_global_monitor_settings": get("override global monitor settings"),
                "use_wavelength_spacing": get("use wavelength spacing"),
                "output_power": get("output power"),
                "reference_plane_nm": expected.get("reference_plane_nm", {
                    "MON_IN": -50.0, "MON_PRENP": 1202.0,
                    "MON_POSTNP": 1722.0, "MON_REFLECTION": None,
                }.get(name)),
                "actual_sampled_z_nm": None,
                "actual_sampled_z_status": "UNAVAILABLE_BEFORE_SOLVER",
            }
            self._controlled_monitor_cache[cache_key] = result
            return dict(result)
        except Exception:
            if self._controlled_monitor_sessions.pop(resolved, None) is not None:
                try:
                    fd.close()
                except Exception:
                    pass
            raise

    def _close_controlled_monitor_sessions(self):
        sessions = list(self._controlled_monitor_sessions.values())
        self._controlled_monitor_sessions.clear()
        self._controlled_monitor_cache.clear()
        for fd in sessions:
            try:
                fd.close()
            except Exception:
                pass

    def setup_structural_validate(self, manifest, source_fsp=None, staged_fsp=None,
                                  case_authority=None):
        """LOAD and compare one legacy or explicitly versioned controlled setup."""
        if (isinstance(case_authority, dict)
                and case_authority.get("route_version") == "APCD_GPU_RUNNER_VERSIONED_CONTROLLED_ADMISSION_V1"):
            import controlled_admission_v1 as controlled
            try:
                fresh_context = self._revalidate_controlled_setup_context(manifest, case_authority)
                structural = controlled.validate_real_readback(
                    fresh_context, case_authority=fresh_context,
                    source_fsp=source_fsp or fresh_context["source_fsp_path"],
                    staged_fsp=staged_fsp or fresh_context["staged_fsp_path"],
                    manifest=manifest, setup_validator=load_pinned_setup_validator(),
                    monitor_readback=self._controlled_monitor_readback)
                # Re-read all pinned controls and artifact hashes after LOAD validation.
                # This rejects a changed route, manifest, contract, proof, or FSP during the check.
                final_context = self._revalidate_controlled_setup_context(manifest, case_authority)
                start_generation_sha256 = _controlled_start_generation_sha256(fresh_context, manifest)
                if start_generation_sha256 != _controlled_start_generation_sha256(final_context, manifest):
                    raise RunnerError("CONTROL_GENERATION_CHANGED_DURING_SETUP_LOAD")
                preflight_only = final_context.get("preflight_only") is True
                gpu_snapshot = None
                if not preflight_only:
                    gpu_snapshot = self.gpu_snapshot()
                    try:
                        free_mib = int(gpu_snapshot.get("free_mib", -1))
                    except (AttributeError, TypeError, ValueError):
                        free_mib = -1
                    if free_mib < MIN_GPU_FREE_MIB:
                        raise RunnerError("CONTROLLED_START_GPU_QUOTA_UNAVAILABLE")
                structural["start_time_revalidation"] = {
                    "schema": "APCD_GPU_RUNNER_CONTROLLED_START_REVALIDATION_V1",
                    "result": "PASS",
                    "checked_after_setup_load": True,
                    "preflight_only": preflight_only,
                    "case_id": manifest["case_id"],
                    "attempt_id": manifest["attempt_id"],
                    "run_id": manifest.get("run_id"),
                    "control_generation_sha256": start_generation_sha256,
                    "route_version": final_context["route_version"],
                    "route_policy_sha256": final_context["route_policy_sha256"],
                    "route_authority_sha256": final_context["route_authority_sha256"],
                    "source_manifest_sha256": final_context["source_manifest_sha256"],
                    "physical_contract_sha256": final_context["physical_contract_sha256"],
                    "setup_contract_fingerprint_sha256": final_context["setup_contract_fingerprint_sha256"],
                    "source_fsp_sha256": final_context["staged_fsp_sha256"],
                    "staged_fsp_sha256": final_context["staged_fsp_sha256"],
                    "pre_entry_setup_load_proof_sha256": final_context["pre_entry_setup_load_proof_sha256"],
                    "gpu_quota_minimum_free_mib": MIN_GPU_FREE_MIB if not preflight_only else None,
                    "gpu_snapshot_sha256": (hashlib.sha256(json.dumps(
                        gpu_snapshot, sort_keys=True, default=str).encode("utf-8")).hexdigest()
                        if gpu_snapshot is not None else None),
                }
                structural["start_time_gpu_snapshot"] = gpu_snapshot
                return structural
            finally:
                self._close_controlled_monitor_sessions()
        token_pattern = r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}"
        case_id = manifest.get("case_id")
        attempt_id = manifest.get("attempt_id")
        if (not isinstance(case_id, str) or not re.fullmatch(token_pattern, case_id)
                or not isinstance(attempt_id, str) or not re.fullmatch(token_pattern, attempt_id)):
            raise RunnerError("SETUP_CASE_OR_AUTHORITY_MISMATCH")
        if not isinstance(case_authority, dict) or set(case_authority) != {
                "authority_manifest_path", "authority_manifest_sha256",
                "load_only_validation_path", "load_only_validation_sha256"}:
            raise RunnerError("SETUP_AUTHORITY_MANIFEST_MISSING")

        authority_path = Path(case_authority["authority_manifest_path"])
        load_only_path = Path(case_authority["load_only_validation_path"])
        authority_dir = SETUP_AUTHORITY_ROOT / case_id / attempt_id
        expected_authority_path = authority_dir / "authority_input_manifest.json"
        expected_load_only_path = authority_dir / "load_only_validation.json"
        same_path = lambda left, right: os.path.normcase(str(Path(left).resolve())) == os.path.normcase(str(Path(right).resolve()))
        if (not same_path(authority_path, expected_authority_path)
                or not same_path(load_only_path, expected_load_only_path)):
            raise RunnerError("SETUP_AUTHORITY_PATH_MISMATCH")
        for key in ("authority_manifest_sha256", "load_only_validation_sha256"):
            if not re.fullmatch(r"[0-9a-f]{64}", str(case_authority.get(key, ""))):
                raise RunnerError("SETUP_AUTHORITY_HASH_INVALID:" + key)
        if (not authority_path.is_file()
                or _sha256(authority_path) != case_authority["authority_manifest_sha256"]
                or not load_only_path.is_file()
                or _sha256(load_only_path) != case_authority["load_only_validation_sha256"]):
            raise RunnerError("SETUP_AUTHORITY_FILE_HASH_MISMATCH")
        try:
            authority = json.loads(authority_path.read_text(encoding="utf-8"))
            load_only = json.loads(load_only_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RunnerError("SETUP_AUTHORITY_JSON_INVALID:" + str(exc)) from exc

        source = Path(source_fsp or manifest.get("pre_fsp_path", "")).resolve()
        staged = Path(staged_fsp or source).resolve()
        expected_fsp = authority_dir / "setup" / "runtime.fsp"
        expected_spec = SETUP_STAGE1_CASE_ROOT / case_id / attempt_id / "case.json"
        if (not isinstance(authority, dict)
                or authority.get("schema") != SETUP_AUTHORITY_MANIFEST_SCHEMA
                or authority.get("authority") != "PW_K6_5NM_FULL_PERIOD_MESH_AUTHORITY_V1"
                or authority.get("case_id") != case_id
                or authority.get("attempt_id") != attempt_id
                or authority.get("ordered_D_nm") != manifest.get("geometry")
                or authority.get("physical_contract_hash") != CONTRACT_SHA256
                or authority.get("pw_contract_sha256") != CONTRACT_SHA256
                or authority.get("stage1_expansion_manifest_sha256") != manifest.get("expansion_manifest_sha256")
                or authority.get("mesh_implementation_authority") != "PW_K6_5NM_FULL_PERIOD_MESH_AUTHORITY_V1"
                or authority.get("solver_run_called") is not False
                or authority.get("scientific_entry_count") != 0):
            raise RunnerError("SETUP_CASE_OR_AUTHORITY_MISMATCH")
        if (manifest.get("physical_contract_sha256") != CONTRACT_SHA256
                or _sha256(self.contract_path) != CONTRACT_SHA256):
            raise RunnerError("SETUP_PHYSICAL_CONTRACT_HASH_MISMATCH")
        if (manifest.get("expansion_manifest_sha256") != EXPANSION_SHA256
                or authority.get("stage1_expansion_manifest_sha256") != EXPANSION_SHA256):
            raise RunnerError("SETUP_EXPANSION_MANIFEST_HASH_MISMATCH")
        if (not same_path(authority.get("canonical_pre_fsp_path", ""), expected_fsp)
                or not same_path(manifest.get("pre_fsp_path", ""), expected_fsp)
                or authority.get("canonical_pre_fsp_sha256") != manifest.get("pre_fsp_sha256")
                or not source.is_file()
                or _sha256(source) != authority.get("canonical_pre_fsp_sha256")
                or not staged.is_file()
                or _sha256(staged) != authority.get("canonical_pre_fsp_sha256")):
            raise RunnerError("SETUP_SOURCE_OR_STAGED_HASH_MISMATCH")

        pinned_assets = (
            (authority.get("builder_source_path"), authority.get("builder_source_sha256"),
             SETUP_BUILDER_PATH, SETUP_BUILDER_SHA256, "BUILDER"),
            (authority.get("stage1_expansion_manifest_path"), authority.get("stage1_expansion_manifest_sha256"),
             SETUP_EXPANSION_MANIFEST_PATH, EXPANSION_SHA256, "EXPANSION_MANIFEST"),
            (authority.get("geometry_seed_manifest_path"), authority.get("geometry_seed_manifest_sha256"),
             SETUP_GEOMETRY_SEED_MANIFEST_PATH, SETUP_GEOMETRY_SEED_MANIFEST_SHA256, "GEOMETRY_SEED_MANIFEST"),
        )
        for actual_path, actual_sha, expected_path, expected_sha, label in pinned_assets:
            if (not isinstance(actual_path, str) or not same_path(actual_path, expected_path)
                    or actual_sha != expected_sha or not expected_path.is_file()
                    or _sha256(expected_path) != expected_sha):
                raise RunnerError("SETUP_" + label + "_PIN_MISMATCH")

        case_spec_path = Path(authority.get("source_case_json_path", ""))
        if (not same_path(case_spec_path, expected_spec)
                or authority.get("source_case_json_sha256") is None
                or not case_spec_path.is_file()
                or _sha256(case_spec_path) != authority.get("source_case_json_sha256")):
            raise RunnerError("SETUP_CASE_SPEC_PIN_MISMATCH")
        try:
            spec = json.loads(case_spec_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RunnerError("SETUP_CASE_SPEC_INVALID:" + str(exc)) from exc
        pw_contract = spec.get("pw_contract", {}) if isinstance(spec, dict) else {}
        contract_payload = pw_contract.get("contract", {}) if isinstance(pw_contract, dict) else {}
        required_contract_fields = ("monitors", "samples_nm", "references_nm", "materials",
                                    "stack_layers", "wavelengths_nm")
        if (not isinstance(spec, dict)
                or spec.get("case_id") != case_id
                or spec.get("attempt_id") != attempt_id
                or spec.get("ordered_D_nm") != manifest.get("geometry")
                or spec.get("geometry_hash_sha256") != authority.get("geometry_hash_sha256")
                or spec.get("physical_contract_hash") != CONTRACT_SHA256
                or spec.get("extension_manifest_sha256") != EXPANSION_SHA256
                or spec.get("monitor_contract_sha256") != SETUP_MONITOR_CONTRACT_SHA256
                or spec.get("mesh_contract_sha256") != authority.get("legacy_stage1_mesh_contract_sha256")
                or pw_contract.get("contract_sha256") != CONTRACT_SHA256
                or any(key not in contract_payload for key in required_contract_fields)
                or not isinstance(pw_contract.get("wavelengths_nm"), list)
                or not isinstance(pw_contract.get("boundary_contract"), dict)):
            raise RunnerError("SETUP_AUTHORITY_SPEC_MISMATCH")

        if (not isinstance(load_only, dict)
                or load_only.get("schema") != SETUP_LOAD_ONLY_SCHEMA
                or load_only.get("authority_input_manifest_sha256") != case_authority["authority_manifest_sha256"]):
            raise RunnerError("SETUP_LOAD_ONLY_PROOF_MISMATCH")
        proof_case = load_only.get("case", {})
        proof_readback = load_only.get("full_readback", {})
        proof_validation = proof_case.get("validation", {}) if isinstance(proof_case, dict) else {}
        if (not isinstance(proof_case, dict)
                or proof_case.get("case_id") != case_id
                or proof_case.get("attempt_id") != attempt_id
                or proof_case.get("canonical_pre_fsp_path") != str(expected_fsp)
                or proof_case.get("canonical_pre_fsp_sha256") != authority.get("canonical_pre_fsp_sha256")
                or proof_case.get("physical_contract_hash") != CONTRACT_SHA256
                or proof_case.get("ordered_D_nm") != manifest.get("geometry")
                or proof_case.get("geometry_hash_sha256") != authority.get("geometry_hash_sha256")
                or proof_case.get("mesh_implementation_authority") != "PW_K6_5NM_FULL_PERIOD_MESH_AUTHORITY_V1"
                or proof_case.get("source_case_json_sha256") != authority.get("source_case_json_sha256")
                or proof_case.get("stage1_manifest_sha256") != EXPANSION_SHA256
                or proof_case.get("fresh_load_only") is not True
                or proof_case.get("solver_run_called") is not False
                or proof_case.get("scientific_entry_count") != 0
                or not isinstance(proof_validation, dict)
                or proof_validation.get("status") != "PASS"
                or proof_validation.get("errors") not in ([], None)):
            raise RunnerError("SETUP_LOAD_ONLY_PROOF_MISMATCH")
        if (not isinstance(proof_readback, dict)
                or proof_readback.get("case_id") != case_id
                or proof_readback.get("attempt_id") != attempt_id
                or proof_readback.get("ordered_D_nm") != manifest.get("geometry")
                or proof_readback.get("geometry_hash_sha256") != authority.get("geometry_hash_sha256")
                or proof_readback.get("fsp_sha256") != authority.get("canonical_pre_fsp_sha256")
                or proof_readback.get("run_called") is not False
                or proof_readback.get("save_called_by_validator") is not False):
            raise RunnerError("SETUP_LOAD_ONLY_READBACK_MISMATCH")

        validator = load_pinned_setup_validator()
        row = validator.inspect_fsp(staged, spec)
        validation = validator.validate_expected(row, spec)
        parity = validator.compare_semantics(proof_readback, row)
        if (not isinstance(validation, dict) or validation.get("status") != "PASS"
                or validation.get("errors") not in ([], None)
                or not isinstance(parity, dict) or parity.get("status") != "PASS"
                or row.get("case_id") != case_id or row.get("attempt_id") != attempt_id
                or row.get("ordered_D_nm") != manifest.get("geometry")
                or row.get("geometry_hash_sha256") != authority.get("geometry_hash_sha256")
                or row.get("fsp_sha256") != authority.get("canonical_pre_fsp_sha256")
                or row.get("object_names") != proof_readback.get("object_names")
                or row.get("object_types") != proof_readback.get("object_types")
                or row.get("run_called") is not False
                or row.get("save_called_by_validator") is not False):
            errors = validation.get("errors", []) if isinstance(validation, dict) else []
            mismatches = parity.get("mismatches", []) if isinstance(parity, dict) else []
            raise RunnerError("SETUP_STRUCTURAL_VALIDATION_FAILED:" + json.dumps(
                {"errors": errors, "load_only_parity": mismatches}, default=str))
        return {
            "schema": "APCD_GPU_RUNNER_V1_SETUP_STRUCTURAL_VALIDATION_V1",
            "result": "PASS", "solver_run_called": False, "solver_invocations": 0,
            "scientific_entry_performed": False,
            "case_id": case_id, "attempt_id": attempt_id,
            "authority_manifest_path": str(authority_path.resolve()),
            "authority_manifest_sha256": case_authority["authority_manifest_sha256"],
            "load_only_validation_path": str(load_only_path.resolve()),
            "load_only_validation_sha256": case_authority["load_only_validation_sha256"],
            "case_spec_path": str(case_spec_path.resolve()),
            "case_spec_sha256": authority["source_case_json_sha256"],
            "source_pre_fsp_path": str(source), "staged_pre_fsp_path": str(staged),
            "source_pre_fsp_sha256": _sha256(source),
            "staged_pre_fsp_sha256": _sha256(staged),
            "physical_contract_sha256": CONTRACT_SHA256,
            "geometry_hash_sha256": authority["geometry_hash_sha256"],
            "ordered_D_nm": manifest["geometry"],
            "mesh_authority": authority["mesh_implementation_authority"],
            "monitor_object_names": row["monitor_names"],
            "validation": validation, "load_only_semantic_parity": parity,
            "setup_readback": row,
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
    controlled_context = manifest.pop("_controlled_admission", None)
    case_authority = controlled_context or manifest.pop("_setup_authority", None)
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

    def validate_case_setup(core_manifest, source_fsp=None, staged_fsp=None):
        return setup_validator(core_manifest, source_fsp, staged_fsp, case_authority)

    run_kwargs = {}
    entry_control_path = Path(GLOBAL_ENTRY_CONTROL_DB_PATH)
    if controlled_context is not None:
        run_kwargs["admitted_contract_sha256"] = controlled_context["physical_contract_sha256"]

    def pre_entry_guard(core_manifest, run_dir, staged_fsp, setup_validation):
        if controlled_context is not None:
            evidence = adapter.controlled_pre_entry_revalidate(
                core_manifest, run_dir, staged_fsp, setup_validation, controlled_context)
        else:
            contract_file = Path(contract_path).resolve(strict=True)
            source_fsp = Path(core_manifest["pre_fsp_path"]).resolve(strict=True)
            staged_fsp = Path(staged_fsp).resolve(strict=True)
            if _sha256(contract_file) != core_manifest["physical_contract_sha256"]:
                raise RunnerError("PHYSICAL_CONTRACT_CHANGED_BEFORE_SOLVER_ENTRY")
            if _sha256(source_fsp) != core_manifest["pre_fsp_sha256"]:
                raise RunnerError("PRE_FSP_CHANGED_BEFORE_SOLVER_ENTRY")
            if _sha256(staged_fsp) != core_manifest["pre_fsp_sha256"]:
                raise RunnerError("STAGED_FSP_CHANGED_BEFORE_SOLVER_ENTRY")
            evidence = {
                "schema": "APCD_GPU_RUNNER_STATIC_PRE_ENTRY_REVALIDATION_V1",
                "result": "PASS",
                "case_id": core_manifest["case_id"],
                "attempt_id": core_manifest["attempt_id"],
                "run_id": core_manifest["run_id"],
                "physical_contract_path": str(contract_file),
                "physical_contract_sha256": _sha256(contract_file),
                "source_fsp_path": str(source_fsp),
                "source_fsp_sha256": _sha256(source_fsp),
                "staged_fsp_path": str(staged_fsp),
                "staged_fsp_sha256": _sha256(staged_fsp),
                "setup_validation_sha256": _sha256(Path(run_dir) / "setup_validation.json")
                    if (Path(run_dir) / "setup_validation.json").is_file() else None,
            }
        global_control = read_global_entry_control(entry_control_path)
        evidence["global_entry_control"] = global_control
        evidence["global_entry_control_sha256"] = global_control["snapshot_sha256"]
        return evidence

    run_kwargs["pre_entry_guard"] = pre_entry_guard
    return run_one(manifest, output_root, adapter.solver, adapter.fresh_load_validate,
                   adapter.gpu_snapshot, adapter.runner_owner_probe, validate_case_setup,
                   **run_kwargs)


def preflight_setup_cli(envelope_path, adapter_factory=NativeAdapter):
    """Production adapter preflight: immutable validation and LOAD only; no run_one."""
    import controlled_admission_v1 as controlled
    envelope = controlled.read_json(Path(envelope_path))
    core, contract_path, context = controlled.validate_controlled_envelope(
        envelope, manifest_keys=MANIFEST_KEYS, preflight=True,
        policy_path=CONTROLLED_POLICY_PATH, authority_path=CONTROLLED_AUTHORITY_PATH,
        expected_policy_sha256=CONTROLLED_POLICY_SHA256,
        expected_authority_sha256=CONTROLLED_AUTHORITY_SHA256)
    context["envelope_path"] = str(Path(envelope_path).resolve())
    context["preflight_only"] = True
    adapter = adapter_factory(contract_path, gpu_resource_name="SETUP_PREFLIGHT_ONLY_NO_SLOT")
    dependency = getattr(adapter, "postprocess_dependency_preflight", None)
    if not isinstance(dependency, dict) or dependency.get("result") != "PASS":
        raise RunnerError("POSTPROCESS_DEPENDENCY_PREFLIGHT_FAILED")
    validate_setup = getattr(adapter, "setup_structural_validate", None)
    if not callable(validate_setup):
        raise RunnerError("SETUP_STRUCTURAL_VALIDATOR_MISSING")
    structural = validate_setup(core, context["source_fsp_path"],
                                context["staged_fsp_path"], context)
    return {
        "schema": "APCD_GPU_RUNNER_VERSIONED_CONTROLLED_SETUP_PREFLIGHT_RESULT_V1",
        "result": "PASS", "route_version": context["route_version"],
        "case_class": context["case_class"], "case_id": context["case_id"],
        "attempt_id": context["attempt_id"],
        "source_manifest_path": context["source_manifest_path"],
        "source_manifest_sha256": context["source_manifest_sha256"],
        "physical_contract_path": str(contract_path),
        "physical_contract_sha256": context["physical_contract_sha256"],
        "setup_contract_fingerprint_sha256": context["setup_contract_fingerprint_sha256"],
        "pre_entry_setup_load_proof_path": context["pre_entry_setup_load_proof_path"],
        "pre_entry_setup_load_proof_sha256": context["pre_entry_setup_load_proof_sha256"],
        "dependency_preflight": dependency, "structural_setup_validation": structural,
        "solver_run_called": False, "solver_invocations": 0,
        "scientific_entry_count": 0, "post_entry_truth_proved": False,
        "post_entry_truth_required_after_solver": True,
    }



def run_one_scheduled(manifest_path):
    """Submit through the fixed Windows Task Scheduler worker and query durable state."""
    try:
        from task_scheduler_v1 import run_one_via_task_scheduler
    except ImportError:
        from .task_scheduler_v1 import run_one_via_task_scheduler
    return run_one_via_task_scheduler(manifest_path, run_cli=run_cli)


def main(argv=None):
    parser = argparse.ArgumentParser(description="APCD GPU Runner V1 submit/query API")
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("run-one", help="Submit one request and wait for its durable result")
    one.add_argument("case_manifest")
    submit = sub.add_parser("submit-one", help="Submit one request without waiting")
    submit.add_argument("case_manifest")
    query = sub.add_parser("query-one", help="Read a durable request receipt")
    query.add_argument("request_id")
    preflight_setup = sub.add_parser("preflight-setup")
    preflight_setup.add_argument("case_manifest")
    args = parser.parse_args(argv)
    try:
        if args.command == "preflight-setup":
            result = preflight_setup_cli(args.case_manifest)
        else:
            try:
                import task_scheduler_v1 as scheduler
            except ImportError:
                from . import task_scheduler_v1 as scheduler
            if args.command == "run-one":
                result = run_one_scheduled(args.case_manifest)
            elif args.command == "submit-one":
                result = scheduler.submit_one(args.case_manifest)
            else:
                result = scheduler.query_one(args.request_id)
    except Exception as exc:
        print("RUNNER_ERROR:" + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
