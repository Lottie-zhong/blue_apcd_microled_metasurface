"""Fail-closed, zero-solver Lumerical license/API readiness check."""
import hashlib
import importlib
import json
import os
import tempfile
import time
from pathlib import Path

ACL_PORT_RANGE_ENV = "ANSYS_LICENSING_DESKTOP_PORT_RANGE"
ACL_PORT_RANGE_DEFAULT = "6200:6299"
LICENSE_FEATURE = "FDTD_Solutions_engine"

def _sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def _atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(str(temp), str(path))

def run_lumerical_license_preflight(run_dir, api_file, expected_api_sha256,
                                    temp_root, port_range=None, session_factory=None):
    """Checkout and release the FDTD engine feature twice; never call run()."""
    run_dir = Path(run_dir)
    api_file = Path(api_file).resolve(strict=True)
    temp_root = Path(temp_root).resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    os.environ["TEMP"] = str(temp_root)
    os.environ["TMP"] = str(temp_root)
    tempfile.tempdir = str(temp_root)
    configured = os.environ.get(ACL_PORT_RANGE_ENV)
    selected_range = port_range or configured or ACL_PORT_RANGE_DEFAULT
    os.environ[ACL_PORT_RANGE_ENV] = selected_range
    record = {
        "schema": "APCD_GPU_RUNNER_V1_LICENSE_API_PREFLIGHT_V1",
        "result": "FAIL", "license_feature": LICENSE_FEATURE,
        "solver_run_called": False, "solver_invocations": 0,
        "api_file": str(api_file), "api_sha256": None,
        "temp_root": str(temp_root), "acl_port_range": selected_range,
        "sessions": [], "started_unix": time.time(),
    }
    proof_path = run_dir / "license_api_preflight_v1.json"
    try:
        actual_sha = _sha(api_file)
        record["api_sha256"] = actual_sha
        if actual_sha != expected_api_sha256:
            raise RuntimeError("PINNED_LUMAPI_HASH_MISMATCH")
        module = importlib.import_module("lumapi")
        if Path(module.__file__).resolve() != api_file:
            raise RuntimeError("LUMAPI_IMPORT_PATH_MISMATCH")
        factory = session_factory or module.FDTD
        for index in range(2):
            row = {"session_index": index + 1, "opened": False,
                   "feature_checkout": False, "closed": False}
            record["sessions"].append(row)
            fd = factory(hide=True)
            row["opened"] = True
            try:
                fd.eval("checkout('FDTD_Solutions_engine');")
                row["feature_checkout"] = True
            finally:
                fd.close()
                row["closed"] = True
        record["result"] = "PASS"
    except BaseException as exc:
        record["failure_type"] = type(exc).__name__
        record["failure"] = str(exc)[:1000]
        raise
    finally:
        record["finished_unix"] = time.time()
        _atomic_json(proof_path, record)
    return {"result": record["result"], "path": str(proof_path),
            "sha256": _sha(proof_path), "acl_port_range": selected_range,
            "license_feature": LICENSE_FEATURE, "solver_invocations": 0}
