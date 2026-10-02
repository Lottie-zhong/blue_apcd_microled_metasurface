"""One-shot LOAD-only recovery for the already-entered S35 attempt. Never calls run()."""
from pathlib import Path
from contextlib import contextmanager, ExitStack
import hashlib
import json
import math
import subprocess
import sys
from unittest.mock import patch

from adapter import NativeAdapter, _sha256
from runner import atomic_json

RUNNER_REPO = Path(r"D:\project\worktrees\blue_apcd_gpu_production_runner_v1")
RUNNER_ROOT = Path(r"D:\apcd_runtime\gpu_production_runner_v1")
RUN_DIR = RUNNER_ROOT / "runs" / "K6V1_S35" / "attempt_001" / "S35-20261002T044427Z-e702b2ac"
PREFLIGHT_DIR = RUNNER_ROOT / "preflight" / "K6V1_S35" / "S35-20261002T044427Z-e702b2ac"
CONTRACT_PATH = RUNNER_ROOT / "contracts" / "pw_contract_32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5.json"
RECOVERY_ROOT = RUNNER_ROOT / "recovery" / "K6V1_S35" / "attempt_001" / "S35-20261002T044427Z-e702b2ac" / "recovery_003"

RUN_ID = "S35-20261002T044427Z-e702b2ac"
CASE_ID = "K6V1_S35"
ATTEMPT_ID = "attempt_001"
ORIGINAL_RUNNER_COMMIT = "2a21c2cc4a40ceead252b084c380399e287e22b6"
CONTRACT_SHA256 = "32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5"
GPU_SNAPSHOT_SHA256 = "9e92555614c638d788a6c29d04cdc8b9f3262a5c0126ba4bdb3adf31eff19b08"

EXPECTED_INPUTS = {
    "source_pre_fsp": (None, "fc7b3f5dab639b7b8816f42438a6eba7c2090266570253e4da043e0bda25b892"),
    "post_run_fsp": (RUN_DIR / "run.fsp", "dfb680a8017262474625dd8cff10815e9d5c07efd13520a0bb165c48c57b445b"),
    "native_h5": (RUN_DIR / "run" / "run_output.h5", "f4d3b0b0845d7daae1af222cf69b6646f3586ec2b8c0ddb203ec1a1ac2eeabbe"),
    "solver_log": (RUN_DIR / "solver.log", "83478d021e52cf0c7357bb132330f8bdf99104798d33b5a91d211a57122e77f3"),
    "run_p0_log": (RUN_DIR / "run_p0.log", "111cbac0802f9c9a7e6900eacb80bc161f183d23d4892a4e81d052a2480b1ed3"),
    "run_manifest": (RUN_DIR / "manifest.json", "01cff16c85d097c568c94f54c7e548441941744e17b8fdb605e46063dccbcfc5"),
    "original_status": (RUN_DIR / "status.json", "5bb75d3cdfcb0aeb267103226b21f49bdbac39defa7deba8c02918f4600bd847"),
    "original_hashes_pending": (RUN_DIR / "hashes.json", "0edaf0a487f3182602585b0237ae771e42b0fc273f4901829ba0b17932f49bbc"),
    "original_validation_pending": (RUN_DIR / "validation.json", "0edaf0a487f3182602585b0237ae771e42b0fc273f4901829ba0b17932f49bbc"),
    "gpu_child_log": (RUN_DIR / "gpu_standalone" / "child.log", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    "gpu_run_script": (RUN_DIR / "gpu_standalone" / "run_gpu.lsf", "553f11060dda87ad4d33e509d91087d559a3982f9a7cd54186d6aa4f624c1631"),
    "gpu_process_exit_provenance": (RUN_DIR / "gpu_standalone" / "forensics" / "process_exit_provenance.json", "0d2dc344621fb57f3d71cdeeb174c456e14aae3deeb11b45549a1eaeafadef13"),
    "gpu_runtime_timeline": (RUN_DIR / "gpu_standalone" / "forensics" / "runtime_timeline.jsonl", "bb6b97a5ebc8ce954bca4b3ad12c6d7340493b897afd03d1d9b79217d0f3e876"),
    "gpu_final_log_tail": (RUN_DIR / "gpu_standalone" / "forensics" / "final_log_tail.json", "6bfa321937d193ad10ed6788f27553d45711ec3c5b22cab9cb5a58ba7b39fdb3"),
    "preflight_fresh_load_report": (PREFLIGHT_DIR / "S35_fresh_load_validation.json", "6668e31452db0081734d7edea259fb327813b8e8a017bb4c9f5b4ad1abd236d6"),
    "preflight_import_audit": (PREFLIGHT_DIR / "S35_preentry_import_audit.json", "e9866f9538d3740e7ad004398273b9dc44dcd994453e4aad7d182bf66de12c39"),
    "preflight_validator_spec": (PREFLIGHT_DIR / "S35_validator_spec.json", "4110ec95d288c7d73dd9784bbd390488f09876c263f7df645859b0fd0cebfd3c"),
    "physical_contract": (CONTRACT_PATH, CONTRACT_SHA256),
}

def file_sha(path):
    return _sha256(path)

def verify_originals(manifest):
    paths = dict(EXPECTED_INPUTS)
    paths["source_pre_fsp"] = (Path(manifest["pre_fsp_path"]), EXPECTED_INPUTS["source_pre_fsp"][1])
    results = {}
    for name, pair in paths.items():
        path, expected = pair
        if not path.is_file():
            raise RuntimeError("ORIGINAL_ARTIFACT_MISSING:" + name)
        actual = file_sha(path)
        if actual != expected:
            raise RuntimeError("ORIGINAL_ARTIFACT_HASH_MISMATCH:" + name)
        results[name] = {"path": str(path), "size_bytes": path.stat().st_size, "sha256": actual}
    return results

def finite(value):
    return isinstance(value, (int, float)) and math.isfinite(float(value))

def json_safe(value):
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if hasattr(value, "tolist"):
        return json_safe(value.tolist())
    if hasattr(value, "item"):
        return json_safe(value.item())
    return value

@contextmanager
def zero_solver_guard(fdtd_class, calls):
    """Block solver entry points without replacing lumapi.FDTD itself."""
    with ExitStack() as stack:
        for method_name in ("run", "runanalysis", "runsetup"):
            def blocked(_self, *args, _method=method_name, **kwargs):
                calls.append(_method)
                raise RuntimeError("ZERO_SOLVER_POLICY_BLOCKED:" + _method)
            stack.enter_context(patch.object(
                fdtd_class, method_name, blocked, create=True))
        yield

def recovery_git_head():
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(RUNNER_REPO),
        capture_output=True, text=True, check=True)
    return result.stdout.strip()

def main():
    if RECOVERY_ROOT.exists():
        raise RuntimeError("RECOVERY_OUTPUT_ALREADY_EXISTS")
    if (RUNNER_ROOT / "active_run.json").exists():
        raise RuntimeError("RUNNER_ACTIVE_RUN_PRESENT")
    original_manifest = json.loads((RUN_DIR / "manifest.json").read_text(encoding="utf-8"))
    original_status = json.loads((RUN_DIR / "status.json").read_text(encoding="utf-8"))
    if (original_manifest.get("run_id") != RUN_ID or
            original_manifest.get("case_id") != CASE_ID or
            original_manifest.get("attempt_id") != ATTEMPT_ID):
        raise RuntimeError("ORIGINAL_MANIFEST_IDENTITY_MISMATCH")
    if (original_status.get("state") != "FAILED_POSTENTRY" or
            original_status.get("failure") != "No module named 'mdc_tmm_complex_incident_power_v1'" or
            original_status.get("solver_entered") is not True or
            original_status.get("solver_invocations") != 1):
        raise RuntimeError("ORIGINAL_POSTENTRY_STATE_MISMATCH")
    if original_status.get("gpu_snapshot_sha256") != GPU_SNAPSHOT_SHA256:
        raise RuntimeError("ORIGINAL_GPU_SNAPSHOT_HASH_MISMATCH")
    if (RUN_DIR / "truth.h5").exists():
        raise RuntimeError("ORIGINAL_TRUTH_ALREADY_EXISTS")
    if file_sha(CONTRACT_PATH) != CONTRACT_SHA256:
        raise RuntimeError("FROZEN_CONTRACT_HASH_MISMATCH")
    immutable_before = verify_originals(original_manifest)

    RECOVERY_ROOT.mkdir(parents=True)
    gpu_resource = original_status["gpu_snapshot"]["requested_resource_name"]
    if not isinstance(gpu_resource, str) or not gpu_resource:
        raise RuntimeError("ORIGINAL_GPU_RESOURCE_IDENTITY_MISSING")
    adapter = NativeAdapter(CONTRACT_PATH, gpu_resource_name=gpu_resource)
    preflight = adapter.postprocess_dependency_preflight
    if preflight.get("result") != "PASS" or preflight.get("solver_run_called") is not False:
        raise RuntimeError("POSTPROCESS_DEPENDENCY_PREFLIGHT_FAILED")

    manifest = {
        "case_id": CASE_ID,
        "attempt_id": ATTEMPT_ID,
        "run_id": RUN_ID,
    }
    import lumapi
    original_fdtd = lumapi.FDTD
    blocked_solver_calls = []
    with zero_solver_guard(original_fdtd, blocked_solver_calls):
        fresh_validation = adapter.fresh_load_validate(
            manifest, RUN_DIR, output_root=RECOVERY_ROOT)
    if lumapi.FDTD is not original_fdtd:
        raise RuntimeError("LUMAPI_FDTD_CLASS_IDENTITY_CHANGED")
    if blocked_solver_calls:
        raise RuntimeError("ZERO_SOLVER_ASSERTION_FAILED")

    native_h5 = RUN_DIR / "run" / "run_output.h5"
    import h5py
    import numpy as np
    with h5py.File(native_h5, "r") as native:
        native_h5_keys = sorted(native.keys())
        native_h5_readable = bool(native_h5_keys)

    prefix = CASE_ID + "__" + ATTEMPT_ID
    raw_path = RECOVERY_ROOT / "raw" / (prefix + "_raw.json")
    projection_path = RECOVERY_ROOT / "projection" / (prefix + "_projection.json")
    orders_path = RECOVERY_ROOT / "orders" / (prefix + "_orders.json")
    state_path = RECOVERY_ROOT / "state" / (prefix + "_pw_complex_floquet_state.npz")
    state_metadata_path = RECOVERY_ROOT / "state" / (prefix + "_pw_complex_floquet_state.json")
    field_path = RECOVERY_ROOT / "raw" / (prefix + "_raw_complex_fields.npz")
    truth_path = RECOVERY_ROOT / "truth.h5"

    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    metrics = raw["metrics"]
    field_meta = raw["raw_complex_fields"]
    state_meta = json.loads(state_metadata_path.read_text(encoding="utf-8"))
    with np.load(field_path, allow_pickle=False) as fields:
        field_keys = set(fields.files)
        required_field_keys = {
            plane + "_" + component
            for plane in ("IN", "PRENP", "POSTNP")
            for component in ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz")
        }
        raw_fields_present = required_field_keys.issubset(field_keys)
        raw_fields_finite = raw_fields_present and all(
            np.isfinite(np.asarray(fields[key])).all() for key in required_field_keys)
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    monitors = contract["monitors"]
    monitor_map = {"IN": monitors["input"], "PRENP": monitors["pre"], "POSTNP": monitors["output"]}
    required_monitor_set_present = (
        set(field_meta["planes"]) == set(monitor_map) and
        all(field_meta["planes"][plane]["monitor"] == monitor for plane, monitor in monitor_map.items())
    )

    state_arrays_ok = False
    state_schema_ok = (
        state_meta.get("schema_version") == "PW_COMPLEX_FLOQUET_STATE_V1" and
        state_meta.get("state_role") == "ML_LABEL_AND_FIDELITY_COMPARATOR_PRIMARY" and
        state_meta.get("axis_order") == ["plane", "wavelength", "order", "direction", "polarization"] and
        state_meta.get("relative_phase_preserved") is True
    )
    with np.load(state_path, allow_pickle=False) as state:
        required_state_keys = {
            "coefficients_real", "coefficients_imag", "wavelengths_nm", "orders",
            "propagating_mask", "mode_kz_real", "mode_kz_imag", "basis_condition",
        }
        state_arrays_ok = required_state_keys.issubset(set(state.files))
        if state_arrays_ok:
            coeff_shape = list(state["coefficients_real"].shape)
            state_arrays_ok = (
                coeff_shape == state_meta.get("coefficients_shape") and
                coeff_shape[0] == 3 and coeff_shape[1] == len(contract["wavelengths_nm"]) and
                coeff_shape[2] == len(state_meta.get("orders_mn", [])) and
                coeff_shape[3:] == [2, 2] and
                np.isfinite(state["coefficients_real"]).all() and
                np.isfinite(state["coefficients_imag"]).all()
            )
    c_pw_extraction_pass = state_schema_ok and state_arrays_ok and state_path.is_file()

    wavelengths = metrics.get("wavelengths_nm", [])
    rows = metrics.get("rows", [])
    expected_wavelengths = [float(value) for value in contract["wavelengths_nm"]]
    order_metrics = metrics.get("orders", {})
    rt_fields = ("R_FDTD", "T_FDTD", "A_FDTD", "R_TMM", "T_TMM", "A_TMM",
                 "input_incident_power_proxy", "input_reflected_power_proxy",
                 "output_transmitted_power_proxy", "closure")
    rt_extract_pass = (
        len(wavelengths) == len(expected_wavelengths) and
        all(abs(float(a) - b) < 1e-9 for a, b in zip(wavelengths, expected_wavelengths)) and
        len(rows) == len(expected_wavelengths) and
        all(all(finite(row.get(key)) for key in rt_fields) for row in rows) and
        all(finite(row.get("tmm", {}).get("power_entering")) for row in rows) and
        all(len(order_metrics.get(direction, [])) == len(expected_wavelengths)
            for direction in ("post", "input")) and
        projection_path.is_file() and orders_path.is_file()
    )
    power_scale_pass = rt_extract_pass
    if power_scale_pass:
        for index, row in enumerate(rows):
            for direction, total_key in (("post", "T_FDTD"), ("input", "R_FDTD")):
                total_power = abs(float(row[total_key]))
                for order_row in order_metrics[direction][index]:
                    source_fraction = order_row.get("power_fraction_of_source")
                    monitor_fraction = order_row.get("power_fraction_of_monitor_total")
                    if (not finite(source_fraction) or not finite(monitor_fraction) or
                            not math.isclose(float(source_fraction), total_power * float(monitor_fraction),
                                             rel_tol=1e-9, abs_tol=1e-12)):
                        power_scale_pass = False
                        break
                if not power_scale_pass:
                    break
            if not power_scale_pass:
                break
    closure_max = metrics.get("max_energy_closure", {}).get("max")
    energy_closure_pass = (
        finite(closure_max) and
        metrics.get("order_sign", {}).get("status") == "PASS" and
        metrics.get("reference_plane_deembedding", {}).get("status") == "PASS" and
        metrics.get("lossy_gan", {}).get("status") == "PASS"
    )
    with h5py.File(truth_path, "r") as truth:
        truth_h5_readable = (
            truth.attrs.get("run_id") == RUN_ID and
            truth.attrs.get("case_id") == CASE_ID and
            truth.attrs.get("attempt_id") == ATTEMPT_ID and
            "raw_json" in truth and "metrics_json" in truth
        )
    truth_hash = file_sha(truth_path)
    immutable_after = verify_originals(original_manifest)
    originals_unchanged = immutable_before == immutable_after

    checks = {
        "post_run_fsp_fresh_load": fresh_validation.get("fresh_load_verified") is True,
        "native_h5_readable": native_h5_readable,
        "required_raw_complex_EH_present_and_finite": raw_fields_present and raw_fields_finite,
        "required_monitor_set_present": required_monitor_set_present,
        "C_PW_extraction": c_pw_extraction_pass,
        "R_T_order_power_extraction": rt_extract_pass,
        "P_scale_total_power_semantics": power_scale_pass,
        "H2_compatible_state_schema": state_schema_ok and state_arrays_ok,
        "energy_closure_checks": energy_closure_pass,
        "truth_h5_durable_and_readable": truth_path.is_file() and truth_path.stat().st_size > 0 and truth_h5_readable,
        "original_S35_artifacts_unchanged": originals_unchanged,
        "zero_solver_assertion": not blocked_solver_calls,
        "solver_invocation_count_still_one": original_status.get("solver_invocations") == 1,
    }
    result = "PASS" if all(checks.values()) and fresh_validation.get("scientific_valid") is True else "FAIL"
    validation_record = {
        "schema": "APCD_GPU_RUNNER_V1_POSTENTRY_TRUTH_RECOVERY_VALIDATION_V1",
        "run_id": RUN_ID,
        "case_id": CASE_ID,
        "attempt_id": ATTEMPT_ID,
        "initial_execution_outcome": "FAILED_POSTENTRY_POSTPROCESS_DEPENDENCY",
        "recovery": "LOAD_ONLY_POSTENTRY_TRUTH_RECOVERY",
        "missing_dependency_classification": "PINNED_EXTERNAL_OR_CROSS_BRANCH_MODULE_NOT_PACKAGED",
        "dependency_required_by_frozen_truth_contract": "YES",
        "dependency_role": "contracted 5 nm TMM R/T/A reference and incident-power metrics; FDTD C_PW and FDTD R/T/order extraction remain launcher-derived",
        "missing_dependency_import_site": "pinned pw_scientific_launcher.py::analyze, invoked by postprocess after LOAD-only validation",
        "dependency_authority": {
            "branch": "work/mdc-np-coupling-ml-v1",
            "commit": "46af82357f269aea0c77105a03e7ca9da645ca8f",
            "module_sha256": "12d2d95bd99fc6e18fec9ac17ab066a5a1fc4a3ddf1a6e5a8c0a625da959ff4b",
        },
        "result": result,
        "checks": checks,
        "fresh_load_validation": fresh_validation,
        "postprocess_dependency_preflight": preflight,
        "max_energy_closure": closure_max,
        "truth_h5_path": str(truth_path),
        "truth_h5_sha256": truth_hash,
        "native_h5_keys": native_h5_keys,
        "original_runner_commit": ORIGINAL_RUNNER_COMMIT,
        "recovery_runner_commit": recovery_git_head(),
        "solver_invocations_after_recovery": original_status.get("solver_invocations"),
        "replay_count": 0,
    }
    validation_record = json_safe(validation_record)
    validation_path = RECOVERY_ROOT / "validation.json"
    atomic_json(validation_path, validation_record)
    validation_durable = (
        validation_path.is_file() and validation_path.stat().st_size > 0 and
        json.loads(validation_path.read_text(encoding="utf-8")).get("run_id") == RUN_ID
    )
    validation_record["checks"]["validation_artifact_durable"] = validation_durable
    if not validation_durable:
        result = "FAIL"
        validation_record["result"] = result
    atomic_json(validation_path, validation_record)
    validation_sha = file_sha(validation_path)
    recovery_status = {
        "schema": "APCD_GPU_RUNNER_V1_POSTENTRY_RECOVERY_STATUS_V1",
        "run_id": RUN_ID,
        "case_id": CASE_ID,
        "attempt_id": ATTEMPT_ID,
        "initial_runner_state": "FAILED_POSTENTRY",
        "initial_failure": "No module named 'mdc_tmm_complex_incident_power_v1'",
        "recovery_state": "LOAD_ONLY_POSTENTRY_TRUTH_RECOVERY",
        "scientific_truth_status": "TRUTH_VALID" if result == "PASS" else "RECOVERY_FAILED",
        "original_status_preserved": True,
        "solver_invocations_before": 1,
        "solver_invocations_after": 1,
        "replay_count": 0,
        "solver_run_called_during_recovery": False,
        "truth_h5_sha256": truth_hash,
        "validation_sha256": validation_sha,
        "original_runner_commit": ORIGINAL_RUNNER_COMMIT,
        "recovery_runner_commit": recovery_git_head(),
    }
    status_path = RECOVERY_ROOT / "recovery_status.json"
    atomic_json(status_path, recovery_status)
    recovery_outputs = [
        truth_path, raw_path, field_path, projection_path, orders_path,
        state_path, state_metadata_path, validation_path, status_path,
    ]
    output_hashes = {
        str(path): {"size_bytes": path.stat().st_size, "sha256": file_sha(path)}
        for path in recovery_outputs if path.is_file()
    }
    hash_record = {
        "schema": "APCD_GPU_RUNNER_V1_POSTENTRY_TRUTH_RECOVERY_HASHES_V1",
        "run_id": RUN_ID,
        "original_artifacts": immutable_after,
        "original_gpu_snapshot_sha256": GPU_SNAPSHOT_SHA256,
        "recovery_artifacts": output_hashes,
    }
    hashes_path = RECOVERY_ROOT / "hashes.json"
    atomic_json(hashes_path, hash_record)
    final = {
        "result": result,
        "scientific_truth_status": recovery_status["scientific_truth_status"],
        "run_id": RUN_ID,
        "truth_h5_sha256": truth_hash,
        "validation_sha256": validation_sha,
        "recovery_hashes_sha256": file_sha(hashes_path),
        "checks": checks,
        "solver_invocations_after_recovery": 1,
        "replay_count": 0,
        "solver_run_called": False,
        "s39_run": False,
        "recovery_root": str(RECOVERY_ROOT),
    }
    print(json.dumps(json_safe(final), sort_keys=True))
    return 0 if result == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
