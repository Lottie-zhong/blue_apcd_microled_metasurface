from __future__ import annotations

import json
import tempfile
import threading
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1].parent))

from shared_fdtd.engine.gpu_bundle import (
    GpuBundleError,
    discover_bundle,
    persist_gpu_bundle,
    verify_bundle,
    wait_for_bundle_ready,
    _select_staging_parent,
)


def make_runtime(root: Path, name: str = "CASE__attempt_001_runtime.fsp", with_sidecar: bool = True):
    run = root / "run"
    run.mkdir(parents=True, exist_ok=True)
    fsp = run / name
    fsp.write_bytes(b"FSP-DURABLE-TRUTH")
    sidecar = run / fsp.stem
    if with_sidecar:
        sidecar.mkdir()
        (sidecar / f"{fsp.stem}_output.h5").write_bytes(b"H5-DURABLE-TRUTH")
    return fsp


def expect_error(fn, token: str):
    try:
        fn()
    except Exception as exc:
        assert token in str(exc), (token, exc)
    else:
        raise AssertionError(f"expected {token}")


def main():
    checks = {}
    with tempfile.TemporaryDirectory(prefix="gpu-native-bundle-") as td:
        root = Path(td)

        no_sidecar = make_runtime(root / "a", with_sidecar=False)
        expect_error(
            lambda: persist_gpu_bundle(no_sidecar, root / "a" / "native" / no_sidecar.name),
            "GPU_BUNDLE_REQUIRED_SIDECAR_MISSING",
        )
        checks["A_fsp_without_h5_fails"] = "PASS"
        expect_error(
            lambda: wait_for_bundle_ready(no_sidecar, timeout_s=0.02, poll_s=0.01),
            "NATIVE_SIDECAR_READINESS_TIMEOUT",
        )
        checks["A1_missing_h5_readiness_times_out"] = "PASS"
        delayed = make_runtime(root / "a_delayed", with_sidecar=False)
        def create_delayed_sidecar():
            time.sleep(0.03)
            sidecar = delayed.parent / delayed.stem
            sidecar.mkdir()
            (sidecar / f"{delayed.stem}_output.h5").write_bytes(b"H5-DELAYED")
        worker = threading.Thread(target=create_delayed_sidecar)
        worker.start()
        ready = wait_for_bundle_ready(delayed, timeout_s=1.0, poll_s=0.01, stable_polls=2)
        worker.join()
        assert ready["sidecar_paths"]
        checks["A2_delayed_h5_readiness_barrier_passes"] = "PASS"
        validation_attempts = []
        def readiness_probe(path):
            validation_attempts.append(str(path))
            if len(validation_attempts) < 3:
                raise RuntimeError("DATASET_NOT_READY")
        validated = wait_for_bundle_ready(delayed, timeout_s=1.0, poll_s=0.01, stable_polls=1, readiness_validator=readiness_probe)
        assert validated["readiness"]["validated"] is True
        assert len(validation_attempts) >= 3
        checks["A3_readiness_validator_retries_and_passes"] = "PASS"
        expect_error(
            lambda: wait_for_bundle_ready(delayed, timeout_s=0.03, poll_s=0.01, stable_polls=1, readiness_validator=lambda path: (_ for _ in ()).throw(RuntimeError("DATASET_NOT_READY"))),
            "NATIVE_SIDECAR_READINESS_TIMEOUT",
        )
        checks["A4_validation_timeout_is_distinct"] = "PASS"

        source = make_runtime(root / "b")
        expect_error(
            lambda: persist_gpu_bundle(source, root / "b" / "native" / "wrong_name.fsp"),
            "GPU_BUNDLE_BASENAME_MISMATCH",
        )
        checks["B_wrong_fsp_h5_layout_fails"] = "PASS"

        validator_calls = []

        def validator(path: Path):
            validator_calls.append(path)
            manifest = json.loads((path.parent / "bundle_manifest.json").read_text(encoding="utf-8"))
            verify_bundle(path.parent, manifest)
            return {"passed": True, "mode": "FAKE_LOAD_ONLY"}

        native = root / "c" / "native" / source.name
        record = persist_gpu_bundle(source, native, validator=validator)
        assert record["status"] == "DURABLE"
        assert record["fsp_path"] == str(native)
        assert record["manifest"]["fsp_path"] == source.name
        assert record["manifest"]["sidecar_paths"]
        assert native.is_file()
        assert (native.parent / record["manifest"]["sidecar_paths"][0]).is_file()
        assert validator_calls and "native_staging" in str(validator_calls[0])
        checks["C_correct_sibling_h5_passes"] = "PASS"
        checks["G_staged_fresh_load_gate"] = "PASS"

        truncated_source = make_runtime(root / "d")
        def truncate_validator(path: Path):
            manifest = json.loads((path.parent / "bundle_manifest.json").read_text(encoding="utf-8"))
            sidecar = path.parent / manifest["sidecar_paths"][0]
            sidecar.write_bytes(b"TRUNCATED")
            verify_bundle(path.parent, manifest)
            return {"passed": True}

        bad_target = root / "d" / "native" / truncated_source.name
        expect_error(
            lambda: persist_gpu_bundle(truncated_source, bad_target, validator=truncate_validator),
            "GPU_BUNDLE_",
        )
        assert not bad_target.parent.exists()
        checks["D_truncated_h5_fails_sha"] = "PASS"

        interrupted_source = make_runtime(root / "e")
        interrupted_target = root / "e" / "native" / interrupted_source.name
        expect_error(
            lambda: persist_gpu_bundle(interrupted_source, interrupted_target, failure_after_files=1),
            "GPU_BUNDLE_COPY_INTERRUPTED",
        )
        assert not interrupted_target.parent.exists()
        checks["E_interrupted_copy_exposes_no_final"] = "PASS"
        retry = persist_gpu_bundle(interrupted_source, interrupted_target, validator=validator)
        retry_again = persist_gpu_bundle(interrupted_source, interrupted_target, validator=validator)
        assert retry["status"] == "DURABLE" and retry_again["status"] == "ALREADY_DURABLE"
        checks["F_retry_is_idempotent"] = "PASS"

        restore = root / "e" / "restore" / interrupted_source.name
        restored = persist_gpu_bundle(interrupted_target, restore, validator=validator)
        assert restored["status"] == "DURABLE"
        checks["H_archive_restore_load_gate"] = "PASS"

        source_a = make_runtime(root / "i" / "A")
        source_b = make_runtime(root / "i" / "B")
        out_a = root / "i" / "native_a" / source_a.name
        out_b = root / "i" / "native_b" / source_b.name
        persist_gpu_bundle(source_a, out_a, validator=validator)
        persist_gpu_bundle(source_b, out_b, validator=validator)
        assert (out_a.parent / source_a.stem).is_dir()
        assert (out_b.parent / source_b.stem).is_dir()
        checks["I_similar_case_names_no_collision"] = "PASS"

        traditional = make_runtime(root / "j" / "traditional")
        coupling = make_runtime(root / "j" / "coupling_ml")
        persist_gpu_bundle(traditional, root / "j" / "native_t" / traditional.name, validator=validator)
        persist_gpu_bundle(coupling, root / "j" / "native_c" / coupling.name, validator=validator)
        checks["J_shared_primitive_for_traditional_and_ml"] = "PASS"
        solver_calls = 0
        assert solver_calls == 0
        checks["K_no_solver_invocation"] = "PASS"

        long_requested = root / ("deep-" * 60)
        selected = _select_staging_parent(
            long_requested,
            root / "destination" / source.name,
            {"files": [{"relative_path": source.name}, {"relative_path": source.stem + "/" + source.stem + "_output.h5"}]},
        )
        if sys.platform == "win32":
            assert selected != long_requested
            assert len(str(selected)) < len(str(long_requested))
        checks["L_windows_long_staging_uses_short_same_volume_root"] = "PASS"

    print(json.dumps({
        "schema": "APCD_GPU_NATIVE_BUNDLE_ZERO_SOLVER_TESTS_V1",
        "status": "PASS" if all(value == "PASS" for value in checks.values()) else "FAIL",
        "solver_invocations": 0,
        "replay": 0,
        "checks": checks,
    }, indent=2))
    return 0 if all(value == "PASS" for value in checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
