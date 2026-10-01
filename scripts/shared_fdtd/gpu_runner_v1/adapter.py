# -*- coding: utf-8 -*-
"""Thin native adapter for the filesystem-authoritative GPU runner V1."""
import argparse
import csv
import io
import hashlib
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
                    RunnerError, run_one)

LAUNCHER_PATH = Path(r"D:\apcd_runtime\shared_v3_backend\01e2320ebf237bdbcd52573665520d57705d2800_gitblob\scripts\shared_fdtd\tools\pw_scientific_launcher.py")
LAUNCHER_SHA256 = "e4de8da6a824c02b3d0425c3e3c76f45111e369ad6a20237e464b0e6f7dce908"


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


def load_pinned_launcher(path=LAUNCHER_PATH):
    if not Path(path).is_file() or _sha256(path) != LAUNCHER_SHA256:
        raise RunnerError("PINNED_LAUNCHER_HASH_MISMATCH")
    spec = importlib.util.spec_from_file_location("apcd_pw_scientific_launcher_v1", str(path))
    if spec is None or spec.loader is None:
        raise RunnerError("PINNED_LAUNCHER_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NativeAdapter:
    """Production callbacks over the immutable standalone GPU launcher."""
    def __init__(self, contract_path, launcher=None, fdtd_exe=None, gpu_resource_name=None):
        self.launcher = launcher or load_pinned_launcher()
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

    def fresh_load_validate(self, manifest, run_dir):
        try:
            import lumapi
            import h5py
        except ImportError as exc:
            raise RunnerError("NATIVE_FRESH_LOAD_DEPENDENCY_MISSING:" + str(exc)) from exc
        cfg = self._cfg(manifest, run_dir)
        with lumapi.FDTD(hide=True) as fd:
            fd.load(cfg["run_fsp"])
            self.launcher.load_only_validate(fd, cfg)
            raw, metrics, paths = self.launcher.postprocess(fd, cfg, str(run_dir))
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
        # Preserve postprocessed evidence and bind its HDF5 container to this run.
        raw_path = Path(run_dir) / "raw" / (manifest["case_id"] + "__" + manifest["attempt_id"] + "_raw.json")
        if raw_path.is_file():
            raw["run_id"] = manifest["run_id"]
            raw_path.write_text(json.dumps(raw, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        truth_path = Path(run_dir) / "truth.h5"
        with h5py.File(truth_path, "w") as h5:
            h5.attrs["run_id"] = manifest["run_id"]
            h5.attrs["case_id"] = manifest["case_id"]
            h5.attrs["attempt_id"] = manifest["attempt_id"]
            h5.attrs["launcher_id"] = "pw_scientific_launcher.py@" + LAUNCHER_SHA256
            h5.create_dataset("raw_json", data=json.dumps(raw, sort_keys=True), dtype=h5py.string_dtype("utf-8"))
            h5.create_dataset("metrics_json", data=json.dumps(metrics, sort_keys=True, default=str), dtype=h5py.string_dtype("utf-8"))
        return {"fresh_load_verified": True, "monitors_valid": True,
                "state_valid": state_valid, "scientific_valid": scientific_valid,
                "run_id": manifest["run_id"], "truth_h5": str(truth_path),
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
        # Only inspect PIDs recorded by this runner after the pinned launcher
        # observed a new process for the exact run.fsp. No OS-wide census.
        for status_path in (root / "runs").glob("*/*/*/status.json"):
            status = json.loads(status_path.read_text(encoding="utf-8"))
            if status.get("state") not in {"SOLVER_ENTERED", "SOLVER_RETURNED", "FAILED_POSTENTRY"}:
                continue
            lineage = status.get("solver_process_lineage")
            if (not isinstance(lineage, dict)
                    or lineage.get("run_id") != status.get("run_id")
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
    output_root = (PRODUCTION_RUNNER_ROOT if test_output_root is None
                   else Path(test_output_root))
    return run_one(manifest, output_root, adapter.solver, adapter.fresh_load_validate,
                   adapter.gpu_snapshot, adapter.runner_owner_probe)


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
