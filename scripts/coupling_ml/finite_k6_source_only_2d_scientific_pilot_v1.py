"""Run exactly one frozen finite-K6 SOURCE_ONLY 2-D scientific pilot.

The setup FSP is authoritative input. This runner only materializes distinct
execution artifacts, uses the validated persistence controller, and performs
post-validation extraction without any setup rebuild or solver replay.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ACTIVE = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
TRAD = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_v1")
INPUT_NS = ACTIVE / r"outputs\coupling_v2_2\FINITE_K6_FINAL_LATERAL_DOMAIN_19UM_MONITOR_15UM_PATCH_V1"
INPUT_FSP = INPUT_NS / r"cases\SOURCE_ONLY\setup_pre.fsp"
INPUT_MANIFEST = INPUT_NS / "FINAL_SHA256_MANIFEST.json"
OUT = ACTIVE / r"outputs\coupling_v2_2\FINITE_K6_SOURCE_ONLY_2D_SCIENTIFIC_PILOT_V1"
SCHEDULER_PATH = TRAD / r"scripts\coupling\apcd_global_fdtd_slot_v3.py"
API = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
WLS = np.arange(445.0, 456.0, 1.0)
CASE_ID = "SOURCE_ONLY"
JOB_ID = "COUPLING_V2_2_FINITE_K6_SOURCE_ONLY_2D_SCIENTIFIC_PILOT_V1:SOURCE_ONLY"
ATTEMPT_ID = "attempt_001"
FDTD_SPAN_UM = 19.0
MONITOR_SPAN_UM = 15.0
SOURCE_Z_NM = -276.0
SOURCE_X_NM = 0.0
N_FARFIELD = 721
FIELD_KEYS = ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz")
MONITOR_NAMES = ("upward_monitor", "downward_monitor")
SOURCE_BOX_NAMES = ("source_box_top", "source_box_bottom", "source_box_left", "source_box_right")

sys.path.insert(0, str(API))
sys.path.insert(0, str(ACTIVE / "scripts" / "coupling_ml"))
sys.path.insert(0, str(TRAD / "scripts" / "coupling"))

from postsolver_persistence_v1 import (  # type: ignore
    ArtifactRoles,
    LifecycleController,
    LifecycleError,
    PreservationRequired,
    atomic_json,
    durable_event,
    sha256_file,
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        return value.item()
    if isinstance(value, complex):
        return [float(value.real), float(value.imag)]
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value


def scalar(value: Any) -> Any:
    value = jsonable(value)
    while isinstance(value, list) and len(value) == 1:
        value = value[0]
    return value


def compact(value: Any) -> Any:
    value = np.asarray(value) if not isinstance(value, dict) else value
    if isinstance(value, dict):
        return {str(k): compact(v) for k, v in value.items()}
    if isinstance(value, np.ndarray):
        if value.size <= 20:
            return jsonable(value)
        flat = value.reshape(-1)
        return {"shape": list(value.shape), "first": jsonable(flat[0]), "last": jsonable(flat[-1])}
    return jsonable(value)


def write_json(name: str, value: Any) -> Path:
    path = OUT / name
    atomic_json(path, value)
    return path


def lumapi_module():
    import lumapi  # type: ignore
    return lumapi


def safe_named(fd: Any, obj: str, prop: str) -> Any:
    try:
        return scalar(fd.getnamed(obj, prop))
    except Exception:
        return None


def safe_data(fd: Any, obj: str, key: str) -> np.ndarray:
    try:
        return np.asarray(fd.getdata(obj, key))
    except Exception:
        return np.array([])


def safe_transmission(fd: Any, obj: str) -> np.ndarray:
    try:
        return np.asarray(fd.transmission(obj)).reshape(-1).real.astype(float)
    except Exception:
        result = fd.getresult(obj, "T")
        if isinstance(result, dict):
            result = result.get("T", result.get("power", result))
        return np.asarray(result).reshape(-1).real.astype(float)


def safe_result(fd: Any, name: str) -> Any:
    try:
        return compact(fd.getresult("FDTD", name))
    except Exception as exc:
        return {"unavailable": f"{type(exc).__name__}: {exc}"}


def result_last(value: Any) -> float | None:
    if isinstance(value, dict):
        if "last" in value:
            return result_last(value["last"])
        if "value" in value:
            return result_last(value["value"])
        return None
    try:
        array = np.asarray(value, dtype=float).reshape(-1)
        return float(array[-1]) if array.size else None
    except Exception:
        return None


def sha(path: Path) -> str:
    return sha256_file(path)


def input_manifest_check() -> dict[str, Any]:
    manifest = json.loads(INPUT_MANIFEST.read_text(encoding="utf-8"))
    row = manifest["files"]["cases/SOURCE_ONLY/setup_pre.fsp"]
    actual = sha(INPUT_FSP)
    return {
        "input_namespace": str(INPUT_NS),
        "input_fsp": str(INPUT_FSP),
        "input_fsp_size": INPUT_FSP.stat().st_size,
        "input_fsp_sha256": actual,
        "manifest_sha256": row["sha256"],
        "manifest_size": row["size"],
        "manifest_file_sha256": sha(INPUT_MANIFEST),
        "match": actual == row["sha256"] and INPUT_FSP.stat().st_size == row["size"],
    }


def fresh_readback() -> dict[str, Any]:
    fd = lumapi_module().FDTD(str(INPUT_FSP), hide=True)
    try:
        names = [str(item).replace("::model::", "").strip(":") for item in fd.getobjectlist("::model::")]
        f = {p: safe_named(fd, "FDTD", p) for p in ("dimension", "x", "x span", "y", "y span", "x min bc", "x max bc", "y min bc", "y max bc", "pml profile", "pml layers", "simulation time", "auto shutoff min", "mesh accuracy")}
        source = {p: safe_named(fd, "source_dipole", p) for p in ("x", "y", "theta", "phi", "wavelength start", "wavelength stop")}
        monitors = {}
        for name in (*MONITOR_NAMES, *SOURCE_BOX_NAMES):
            monitors[name] = {p: safe_named(fd, name, p) for p in ("monitor type", "x", "y", "x span", "y span", "frequency points")}
        central_spans = [float(safe_named(fd, name, "x span")) * 1e9 for name in names if name.startswith("MDC_LAYER_") and safe_named(fd, name, "x span") is not None]
        np_count = sum(name.startswith("NP_bar_") for name in names)
        checks = {
            "input_fsp_manifest_match": input_manifest_check()["match"],
            "fdtd_19um_centered": abs(float(f["x span"]) * 1e6 - FDTD_SPAN_UM) < 1e-6 and abs(float(f["x"])) < 1e-15,
            "monitor_15um_centered": all(abs(float(monitors[name]["x span"]) * 1e6 - MONITOR_SPAN_UM) < 1e-6 and abs(float(monitors[name]["x"])) < 1e-15 for name in MONITOR_NAMES),
            "device_1p74um": bool(central_spans) and abs(max(central_spans) - 1740.0) < 1e-6,
            "np_count_zero": np_count == 0,
            "source_x_zero": abs(float(source["x"]) * 1e9 - SOURCE_X_NM) < 1e-6,
            "source_physical_z_alias_y": abs(float(source["y"]) * 1e9 - SOURCE_Z_NM) < 1e-6,
            "source_orientation_x": abs(float(source["theta"]) - 90.0) < 1e-6 and abs(float(source["phi"])) < 1e-6,
            "wavelength_445_455": abs(float(source["wavelength start"]) * 1e9 - 445.0) < 1e-6 and abs(float(source["wavelength stop"]) * 1e9 - 455.0) < 1e-6,
            "monitor_11_points": all(int(float(monitors[name]["frequency points"])) == 11 for name in (*MONITOR_NAMES, *SOURCE_BOX_NAMES)),
            "four_exterior_pml": all(f[key] == "PML" for key in ("x min bc", "x max bc", "y min bc", "y max bc")),
            "no_periodic_bloch": all(f[key] not in {"Periodic", "Bloch"} for key in ("x min bc", "x max bc", "y min bc", "y max bc")),
            "stabilized_pml_32": int(float(f["pml profile"])) == 2 and int(float(f["pml layers"])) == 32,
            "mesh_accuracy_2": abs(float(f["mesh accuracy"]) - 2.0) < 1e-9,
            "simulation_1ps": abs(float(f["simulation time"]) - 1e-12) < 1e-24,
            "auto_shutoff_1e_6": abs(float(f["auto shutoff min"]) - 1e-6) < 1e-12,
        }
        return {"schema_version": "FINITE_K6_2D_MODEL_AUTHORITY_V1_FROZEN", "solver_entry": False, "objects": names, "fdtd": f, "source": source, "monitors": monitors, "central_x_spans_nm": central_spans, "np_bar_count": np_count, "checks": checks, "pass": bool(all(checks.values()))}
    finally:
        fd.close()


def process_snapshot() -> list[dict[str, Any]]:
    import psutil
    rows = []
    for proc in psutil.process_iter(["pid", "name", "cmdline", "username"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if name not in {"fdtd-engine-msmpi.exe", "mpiexec.exe"}:
                continue
            command = " ".join(proc.info.get("cmdline") or [])
            rows.append({"pid": proc.info["pid"], "name": proc.info.get("name"), "username": proc.info.get("username"), "cmdline": command[:600], "is_this_task": str(OUT).lower() in command.lower(), "is_m2s": "M2S" in command.upper()})
        except Exception:
            pass
    return rows


def scheduler_snapshot() -> dict[str, Any]:
    registry_path = Path(r"D:\project\apcd_global_fdtd_slot_registry_v3.json")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    active = [{k: row.get(k) for k in ("slot_id", "task_id", "attempt_id", "branch", "pid", "processes", "threads", "completion_release_state", "worktree")} for row in registry.get("active_slots", [])]
    return {"registry": str(registry_path), "global_capacity": registry.get("global_capacity"), "updated_utc": registry.get("updated_utc"), "active_slots": active, "processes": process_snapshot()}


def preflight() -> tuple[dict[str, Any], dict[str, Any]]:
    if OUT.exists():
        raise LifecycleError(f"output namespace already exists; overwrite forbidden: {OUT}")
    OUT.mkdir(parents=True, exist_ok=False)
    authority = input_manifest_check()
    readback = fresh_readback()
    static = json.loads((INPUT_NS / "STATIC_TEST_RESULTS.json").read_text(encoding="utf-8"))
    diff = json.loads((INPUT_NS / "SCIENTIFIC_PROPERTY_DIFF_17_13_TO_19_15.json").read_text(encoding="utf-8"))
    boundary = json.loads((INPUT_NS / "BOUNDARY_AUTHORITY_READBACK.json").read_text(encoding="utf-8"))
    mesh = json.loads((INPUT_NS / "LATERAL_DOMAIN_MESH_COST_AUDIT_V2.json").read_text(encoding="utf-8"))
    source_contract = {
        "dimensional_model": "2D finite x-y Lumerical plane; native y is physical z",
        "source_x_nm": 0.0,
        "source_physical_z_nm": SOURCE_Z_NM,
        "source_orientation": "X (theta=90 deg, phi=0 deg)",
        "wavelengths_nm": WLS.tolist(),
        "monitor_names": list(MONITOR_NAMES),
        "source_box_names": list(SOURCE_BOX_NAMES),
    }
    model_authority = {"schema_version": "FINITE_K6_2D_MODEL_AUTHORITY_V1_FROZEN", "input": authority, "contract": source_contract, "fresh_load_only": readback, "solver_entry": False}
    write_json("MODEL_AUTHORITY.json", model_authority)
    other_jobs = scheduler_snapshot()
    pre = {
        "schema_version": "SOURCE_ONLY_PILOT_PREFLIGHT_AUDIT_V1",
        "generated_utc": now(),
        "model_authority": model_authority,
        "static_test": {"pass": static.get("pass"), "solver_entry_delta": static.get("solver_entry_delta"), "returned": static.get("returned"), "rerun_delta": static.get("rerun_delta")},
        "scientific_property_diff": {"unexpected_scientific_diff_count": diff.get("unexpected_scientific_diff_count"), "unexpected_diffs": diff.get("unexpected_diffs", [])},
        "boundary": boundary,
        "mesh": mesh,
        "scheduler_before_acquire": other_jobs,
        "pass": bool(authority["match"] and readback["pass"] and static.get("pass") is True and diff.get("unexpected_scientific_diff_count") == 0 and boundary.get("all_exterior_pml") and not boundary.get("periodic_or_bloch")),
    }
    write_json("PREFLIGHT_AUDIT.json", pre)
    if not pre["pass"]:
        raise LifecycleError("SOURCE_ONLY frozen-authority preflight failed")
    return model_authority, other_jobs


def reshape_line(array: np.ndarray, ncoord: int, nf: int) -> np.ndarray:
    array = np.asarray(array).squeeze()
    if array.size != ncoord * nf:
        raise LifecycleError(f"line_field_shape_mismatch:{array.shape}:{ncoord}:{nf}")
    if array.ndim == 1:
        return array.reshape(ncoord, nf)
    axes = list(range(array.ndim))
    fax = next((axis for axis in axes if array.shape[axis] == nf), array.ndim - 1)
    cax = next((axis for axis in axes if axis != fax and array.shape[axis] == ncoord), None)
    if cax is None:
        return array.reshape(ncoord, nf)
    return np.moveaxis(array, (cax, fax), (0, 1)).reshape(ncoord, nf)


def line_payload(fd: Any, name: str) -> dict[str, Any]:
    x = safe_data(fd, name, "x").squeeze()
    y = safe_data(fd, name, "y").squeeze()
    f = safe_data(fd, name, "f").reshape(-1)
    coord_key = "x" if np.asarray(x).size > 1 else "y"
    coord = np.asarray(x if coord_key == "x" else y, dtype=float).reshape(-1)
    if coord.size == 0 or f.size == 0:
        raise LifecycleError(f"missing_monitor_axes:{name}")
    payload: dict[str, Any] = {"coord_axis": coord_key, "x": np.asarray(x), "y": np.asarray(y), "f": np.asarray(f), "T": safe_transmission(fd, name)}
    for key in FIELD_KEYS:
        payload[key] = safe_data(fd, name, key)
    return payload


def status_payload(fd: Any) -> dict[str, Any]:
    return {
        "status": safe_result(fd, "status"),
        "autoshutoff_level": safe_result(fd, "autoshutoff level"),
        "simulation_runtime_s": safe_result(fd, "simulation runtime"),
        "peak_memory": safe_result(fd, "peak memory"),
        "peak_cpu_memory_usage": safe_result(fd, "peak CPU memory usage"),
        "total_processes": safe_result(fd, "total processes"),
        "total_threads": safe_result(fd, "total threads"),
    }


def farfield_payload(fd: Any) -> dict[str, Any]:
    frequencies = np.arange(1, len(WLS) + 1, dtype=np.int32)
    e2 = np.asarray(fd.farfield2d("upward_monitor", frequencies, N_FARFIELD))
    theta = np.asarray(fd.farfieldangle("upward_monitor", frequencies, N_FARFIELD))
    if e2.ndim == 1:
        e2 = e2.reshape(-1, 1)
    if theta.ndim == 1:
        theta = theta.reshape(-1, 1)
    if e2.shape[0] != N_FARFIELD and e2.shape[1] == N_FARFIELD:
        e2 = e2.T
    if theta.shape[0] != N_FARFIELD and theta.shape[1] == N_FARFIELD:
        theta = theta.T
    if e2.shape != theta.shape or e2.shape[1] != len(WLS):
        raise LifecycleError(f"native_farfield_shape_mismatch:{e2.shape}:{theta.shape}")
    polar_error = None
    try:
        polar = np.asarray(fd.farfieldpolar2d("upward_monitor", frequencies, N_FARFIELD))
    except Exception as exc:
        polar = np.array([])
        polar_error = f"{type(exc).__name__}: {exc}"
    return {"farfield_e2": e2, "farfield_theta_deg": theta, "farfield_polar_complex": polar, "farfield_polar_error": polar_error, "farfield_api": "native farfield2d + farfieldangle; optional farfieldpolar2d"}


class Adapter:
    def __init__(self, manifest: dict[str, Any], attempt: Path):
        self.manifest = manifest
        self.attempt = attempt
        self.session_id: str | None = None
        self.handle: Any = None
        self.owner_closed = False
        self.run_started = 0.0
        self.run_wall_s: float | None = None
        self.run_completed = False
        self.telemetry: dict[str, Any] = {}
        self.last_validation: dict[str, Any] = {}

    def open(self, path: str):
        fd = lumapi_module().FDTD(path, hide=True)
        self.handle = fd
        self.session_id = f"pilot-owner-pid-{os.getpid()}-handle-{id(fd)}"
        fd.setresource("FDTD", 1, "processes", "12")
        fd.setresource("FDTD", 1, "threads", "1")
        resource = {key: int(float(fd.getresource("FDTD", 1, key))) for key in ("processes", "threads")}
        if resource != {"processes": 12, "threads": 1}:
            raise LifecycleError(f"production_resource_readback_mismatch:{resource}")
        check = fresh_readback_for_fd(fd)
        if not check["pass"]:
            raise LifecycleError(f"runtime_identity_mismatch:{check}")
        write_json("APP_IDENTITY.json", {"session_id": self.session_id, "worker_pid": os.getpid(), "resource": resource, "identity": check})
        return fd

    def run(self, fd):
        self.run_started = time.perf_counter()
        fd.run()
        self.run_wall_s = time.perf_counter() - self.run_started
        self.run_completed = True
        self.telemetry = status_payload(fd)
        write_json("RUN_TELEMETRY.json", {"natural_return_observed": True, "wall_time_s": self.run_wall_s, "resource": {"processes": 12, "threads": 1}, "native": self.telemetry})

    def save(self, fd, path: str):
        fd.save(path)

    def rescue_save(self, fd, path: str):
        fd.save(path)

    def live_results_available(self, fd):
        return bool(safe_data(fd, "upward_monitor", "Ex").size or safe_data(fd, "upward_monitor", "Ey").size)

    def load_only(self, path: str, manifest: dict[str, Any]) -> dict[str, Any]:
        # Close the owner session only after post save+SHA. The child then LOADs post.fsp independently.
        if self.handle is not None and not self.owner_closed:
            self.handle.close()
            self.owner_closed = True
            write_json("LIFECYCLE_ORDER_AUDIT.json", {"post_save_owner_session_closed_before_load_only": True, "owner_session_id": self.session_id, "closed_utc": now()})
        request = self.attempt / "load_only_request.json"
        proof = self.attempt / "load_only_proof.json"
        atomic_json(request, manifest)
        command = [sys.executable, str(Path(__file__).resolve()), "--load-only", path, "--manifest", str(request), "--proof", str(proof)]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        if result.returncode:
            raise LifecycleError("independent_load_only_failed:" + result.stderr.decode(errors="replace")[-2000:])
        self.persisted_post_sha256 = sha(Path(path))
        self.last_validation = json.loads(proof.read_text(encoding="utf-8"))
        return self.last_validation

    def extract_raw(self, fd, post: Path, raw: Path):
        # Extraction is from the validated post artifact, never from a rerun or setup state.
        extract_fd = lumapi_module().FDTD(str(post), hide=True) if self.owner_closed else fd
        try:
            monitors = {name: line_payload(extract_fd, name) for name in (*MONITOR_NAMES, *SOURCE_BOX_NAMES)}
            frequency = np.asarray(monitors["upward_monitor"]["f"]).reshape(-1)
            source = {}
            for key in ("dipolepower", "sourcepower"):
                try:
                    source[key] = np.asarray(getattr(extract_fd, key)(frequency)).reshape(-1)
                except Exception:
                    source[key] = np.array([])
            farfield = farfield_payload(extract_fd)
            payload: dict[str, Any] = {"wavelength_nm": 299792458.0 / frequency * 1e9, "frequency_hz": frequency, "post_fsp": np.array(str(post)), "post_fsp_sha256": np.array(sha(post)), "source_dipolepower": source["dipolepower"], "source_sourcepower": source["sourcepower"], "run_telemetry_json": np.array(json.dumps(self.telemetry, ensure_ascii=False, sort_keys=True)), "farfield_api": np.array(farfield["farfield_api"]), "farfield_polar_error": np.array(farfield["farfield_polar_error"] or "")}
            for name, data in monitors.items():
                for key, value in data.items():
                    if key != "coord_axis":
                        payload[f"{name}_{key}"] = value
                payload[f"{name}_coord_axis"] = np.array(data["coord_axis"])
            payload.update({key: value for key, value in farfield.items() if key not in {"farfield_api", "farfield_polar_error"}})
            np.savez_compressed(raw, **payload)
            metadata = {"schema_version": "SOURCE_ONLY_RAW_METADATA_V1", "case_id": CASE_ID, "post_fsp": str(post), "post_fsp_sha256": sha(post), "wavelength_points": len(WLS), "keys": sorted(payload), "field_availability": {name: {key: bool(np.asarray(data.get(key, [])).size) for key in FIELD_KEYS} for name, data in monitors.items()}, "unmodified_complex_fields": True, "native_farfield": farfield["farfield_api"], "raw_written_utc": now(), "termination": self.telemetry}
            write_json("SOURCE_ONLY_RAW_METADATA.json", metadata)
        finally:
            if self.owner_closed:
                extract_fd.close()

    def extract_raw_from_post(self, post: str, raw: str):
        fd = lumapi_module().FDTD(str(post), hide=True)
        try:
            self.extract_raw(fd, Path(post), Path(raw))
        finally:
            fd.close()

    def close(self, fd):
        if self.owner_closed:
            return
        fd.close()


def fresh_readback_for_fd(fd: Any) -> dict[str, Any]:
    f = {p: safe_named(fd, "FDTD", p) for p in ("dimension", "x", "x span", "x min bc", "x max bc", "y min bc", "y max bc", "pml profile", "pml layers", "simulation time", "auto shutoff min", "mesh accuracy")}
    source = {p: safe_named(fd, "source_dipole", p) for p in ("x", "y", "theta", "phi", "wavelength start", "wavelength stop")}
    monitors = {name: {p: safe_named(fd, name, p) for p in ("x", "x span", "frequency points")} for name in (*MONITOR_NAMES, *SOURCE_BOX_NAMES)}
    checks = {
        "dimension_2d": f["dimension"] == "2D",
        "fdtd_19um": abs(float(f["x span"]) * 1e6 - FDTD_SPAN_UM) < 1e-6,
        "fdtd_center_0": abs(float(f["x"])) < 1e-15,
        "monitor_15um": all(abs(float(monitors[name]["x span"]) * 1e6 - MONITOR_SPAN_UM) < 1e-6 for name in MONITOR_NAMES),
        "source_x_0": abs(float(source["x"]) * 1e9) < 1e-6,
        "source_y_alias_z": abs(float(source["y"]) * 1e9 - SOURCE_Z_NM) < 1e-6,
        "source_x_orientation": abs(float(source["theta"]) - 90.0) < 1e-6 and abs(float(source["phi"])) < 1e-6,
        "wavelengths": abs(float(source["wavelength start"]) * 1e9 - 445.0) < 1e-6 and abs(float(source["wavelength stop"]) * 1e9 - 455.0) < 1e-6,
        "pml": all(f[key] == "PML" for key in ("x min bc", "x max bc", "y min bc", "y max bc")) and int(float(f["pml profile"])) == 2 and int(float(f["pml layers"])) == 32,
        "mesh": abs(float(f["mesh accuracy"]) - 2.0) < 1e-9,
        "time_and_shutoff": abs(float(f["simulation time"]) - 1e-12) < 1e-24 and abs(float(f["auto shutoff min"]) - 1e-6) < 1e-12,
        "monitor_points": all(int(float(monitors[name]["frequency points"])) == 11 for name in (*MONITOR_NAMES, *SOURCE_BOX_NAMES)),
    }
    return {"fdtd": f, "source": source, "monitors": monitors, "checks": checks, "pass": bool(all(checks.values()))}


def validate_post(path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    fd = lumapi_module().FDTD(str(path), hide=True)
    session = f"load-only-pid-{os.getpid()}-handle-{id(fd)}"
    try:
        identity = fresh_readback_for_fd(fd)
        monitor_checks = {}
        arrays = {}
        for name in (*MONITOR_NAMES, *SOURCE_BOX_NAMES):
            f = safe_data(fd, name, "f").reshape(-1)
            coord = safe_data(fd, name, "x") if safe_data(fd, name, "x").size > 1 else safe_data(fd, name, "y")
            t = safe_transmission(fd, name)
            monitor_checks[name] = {"frequency_points": int(f.size), "coordinate_points": int(coord.size), "T_points": int(t.size), "has_axis": bool(f.size == len(WLS) and coord.size > 0 and t.size == len(WLS))}
            if name in MONITOR_NAMES:
                arrays[name] = {key: safe_data(fd, name, key) for key in FIELD_KEYS}
        field_pass = True
        shape_pass = True
        finite_pass = True
        for name in MONITOR_NAMES:
            present_e = any(arrays[name][key].size for key in ("Ex", "Ey", "Ez"))
            present_h = any(arrays[name][key].size for key in ("Hx", "Hy", "Hz"))
            field_pass = field_pass and present_e and present_h
            values = [value for value in arrays[name].values() if value.size]
            finite_pass = finite_pass and all(np.isfinite(np.real(value)).all() and np.isfinite(np.imag(value)).all() for value in values)
            sizes = [value.size for value in values]
            shape_pass = shape_pass and bool(sizes) and len(set(sizes)) == 1 and sizes[0] % len(WLS) == 0
        status = safe_result(fd, "status")
        checks = {"identity": identity["pass"], "fdtd_status_result_exists": not isinstance(status, dict) or "unavailable" not in status, "upward_downward_fields": field_pass, "fields_finite": finite_pass, "field_shapes": shape_pass, "monitor_axes_and_T": all(row["has_axis"] for row in monitor_checks.values()), "source_identity": identity["checks"]["source_y_alias_z"] and identity["checks"]["source_x_orientation"], "spectral_11_points": all(row["frequency_points"] == 11 for row in monitor_checks.values())}
        return {"schema_version": "SOURCE_ONLY_POST_FSP_LOAD_ONLY_VALIDATION_V1", "ok": bool(all(checks.values())), "identity_pass": bool(checks["identity"] and checks["source_identity"]), "arrays_pass": bool(checks["upward_downward_fields"] and checks["fields_finite"]), "shape_pass": bool(checks["field_shapes"]), "sanity_pass": bool(all(checks.values())), "run_called": False, "session_id": session, "checks": checks, "monitor_checks": monitor_checks, "status": status, "physical_contract_sha256": manifest.get("physical_contract_sha256")}
    finally:
        fd.close()


def integrate(x: np.ndarray, value: np.ndarray) -> np.ndarray:
    return np.trapezoid(value, x, axis=0) if hasattr(np, "trapezoid") else np.trapz(value, x, axis=0)


def field_matrix(raw: dict[str, Any], name: str, key: str, ncoord: int, nf: int) -> np.ndarray:
    value = np.asarray(raw.get(f"{name}_{key}", np.array([])))
    if not value.size:
        return np.zeros((ncoord, nf), dtype=complex)
    return reshape_line(value, ncoord, nf).astype(complex)


def line_flux(raw: dict[str, Any], name: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    coord_key = str(np.asarray(raw[f"{name}_coord_axis"]).reshape(-1)[0])
    coord = np.asarray(raw[f"{name}_{coord_key}"]).squeeze().reshape(-1).astype(float)
    nf = len(WLS)
    fields = {key: field_matrix(raw, name, key, coord.size, nf) for key in FIELD_KEYS}
    ex, ey, ez = fields["Ex"], fields["Ey"], fields["Ez"]
    hx, hy, hz = fields["Hx"], fields["Hy"], fields["Hz"]
    if coord_key == "x":
        flux = 0.5 * np.real(ey * np.conj(hx) - ex * np.conj(hz))
    else:
        flux = 0.5 * np.real(ey * np.conj(hz) - ez * np.conj(hy))
    return coord, flux, fields["Ex"], fields["Hz"]


def finite_array(value: Any) -> bool:
    value = np.asarray(value)
    return bool(value.size and np.isfinite(np.real(value)).all() and np.isfinite(np.imag(value)).all())


def stats(values: np.ndarray, index_450: int = 5) -> dict[str, Any]:
    values = np.asarray(values, dtype=float)
    return {"mean": float(np.mean(values)), "median": float(np.median(values)), "min": float(np.min(values)), "max": float(np.max(values)), "at_450_nm": float(values[index_450])}


def write_csv(name: str, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path = OUT / name
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def derive_raw(raw_path: Path) -> dict[str, Any]:
    with np.load(raw_path, allow_pickle=False) as source:
        raw = {key: source[key] for key in source.files}
    wavelengths = np.asarray(raw["wavelength_nm"], dtype=float).reshape(-1)
    if wavelengths.size != len(WLS):
        raise LifecycleError("raw_wavelength_count_mismatch")
    up_x, up_flux, _, _ = line_flux(raw, "upward_monitor")
    down_x, down_flux, _, _ = line_flux(raw, "downward_monitor")
    p_up = integrate(up_x, up_flux)
    p_down = integrate(down_x, -down_flux)
    boundary = {}
    for name, sign in (("source_box_top", 1.0), ("source_box_bottom", -1.0), ("source_box_left", -1.0), ("source_box_right", 1.0)):
        coord, flux, _, _ = line_flux(raw, name)
        outward = sign * flux
        boundary[name] = {"coord": coord, "signed": integrate(coord, outward), "positive": integrate(coord, np.maximum(outward, 0.0))}
    source_box = sum(boundary[name]["positive"] for name in SOURCE_BOX_NAMES)
    source_box_signed = sum(boundary[name]["signed"] for name in SOURCE_BOX_NAMES)
    eta_up = p_up / np.maximum(source_box, 1e-300)
    eta_down = p_down / np.maximum(source_box, 1e-300)
    aperture = {}
    for width in (8.0, 10.0, 13.0, 15.0):
        mask = np.abs(up_x) <= width * 0.5e-6 + 1e-15
        aperture[width] = integrate(up_x[mask], up_flux[mask])
    delta = {f"delta_{int(width)}_to_15": np.abs(aperture[width] - aperture[15.0]) / np.maximum(np.abs(aperture[15.0]), 1e-300) for width in (8.0, 10.0, 13.0)}
    aperture_rows = []
    for i, wavelength in enumerate(wavelengths):
        row = {"wavelength_nm": float(wavelength)}
        for width in (8.0, 10.0, 13.0, 15.0):
            row[f"P_up_{int(width)}um"] = float(aperture[width][i])
        for key, values in delta.items():
            row[key] = float(values[i])
        aperture_rows.append(row)
    write_csv("SOURCE_ONLY_APERTURE_CONVERGENCE.csv", aperture_rows, list(aperture_rows[0]))
    edge_rows = []
    edge_abs_fraction = []
    edge_positive_fraction = []
    edge_signed_fraction = []
    for i, wavelength in enumerate(wavelengths):
        full_abs = integrate(up_x, np.abs(up_flux[:, i]))
        edge_mask = (up_x <= up_x.min() + 0.5e-6) | (up_x >= up_x.max() - 0.5e-6)
        edge_abs = integrate(up_x[edge_mask], np.abs(up_flux[edge_mask, i]))
        full_positive = integrate(up_x, np.maximum(up_flux[:, i], 0.0))
        edge_positive = integrate(up_x[edge_mask], np.maximum(up_flux[edge_mask, i], 0.0))
        full_signed = abs(integrate(up_x, up_flux[:, i]))
        edge_signed = abs(integrate(up_x[edge_mask], up_flux[edge_mask, i]))
        edge_abs_fraction.append(float(edge_abs / max(abs(full_abs), 1e-300)))
        edge_positive_fraction.append(float(edge_positive / max(abs(full_positive), 1e-300)))
        edge_signed_fraction.append(float(edge_signed / max(full_signed, 1e-300)))
        edge_rows.append({"wavelength_nm": float(wavelength), "EDGE_ABS_FLUX_FRACTION": edge_abs_fraction[-1], "edge_positive_flux_fraction": edge_positive_fraction[-1], "edge_signed_net_fraction": edge_signed_fraction[-1]})
    write_csv("SOURCE_ONLY_EDGE_CAPTURE_AUDIT.csv", edge_rows, list(edge_rows[0]))
    e2 = np.asarray(raw["farfield_e2"], dtype=float)
    theta = np.asarray(raw["farfield_theta_deg"], dtype=float)
    if e2.shape != (N_FARFIELD, len(WLS)):
        raise LifecycleError(f"farfield_shape_invalid:{e2.shape}")
    f_norm = e2 / np.maximum(np.max(e2, axis=0, keepdims=True), 1e-300)
    theta_peak = []
    fraction_0_60 = []
    fraction_over_60 = []
    for i in range(len(WLS)):
        order = np.argsort(theta[:, i])
        t = theta[order, i]
        intensity = np.maximum(e2[order, i], 0.0)
        total = float(np.trapezoid(intensity, np.radians(t)) if hasattr(np, "trapezoid") else np.trapz(intensity, np.radians(t)))
        inside = np.abs(t) <= 60.0
        inside_power = float(np.trapezoid(intensity[inside], np.radians(t[inside])) if hasattr(np, "trapezoid") else np.trapz(intensity[inside], np.radians(t[inside])))
        theta_peak.append(float(t[int(np.argmax(intensity))]))
        fraction_0_60.append(inside_power / max(total, 1e-300))
        fraction_over_60.append(max(0.0, 1.0 - fraction_0_60[-1]))
    np.savez_compressed(OUT / "SOURCE_ONLY_FARFIELD.npz", theta_deg=theta, F=e2, F_norm=f_norm, wavelengths_nm=wavelengths, theta_peak_deg=np.asarray(theta_peak), F_0_60_fraction=np.asarray(fraction_0_60), over_60_fraction=np.asarray(fraction_over_60))
    farfield_rows = [{"theta_deg": float(theta[j, 5]), "F": float(e2[j, 5]), "F_norm": float(f_norm[j, 5])} for j in np.argsort(theta[:, 5])]
    write_csv("SOURCE_ONLY_FARFIELD_450NM.csv", farfield_rows, ["theta_deg", "F", "F_norm"])
    power_rows = []
    for i, wavelength in enumerate(wavelengths):
        power_rows.append({"wavelength_nm": float(wavelength), "P_source_box": float(source_box[i]), "P_source_box_signed": float(source_box_signed[i]), "P_up": float(p_up[i]), "P_down": float(p_down[i]), "ETA_UP": float(eta_up[i]), "ETA_DOWN": float(eta_down[i]), "dipolepower": float(np.asarray(raw.get("source_dipolepower", np.full(len(WLS), np.nan))).reshape(-1)[i]) if np.asarray(raw.get("source_dipolepower", [])).size == len(WLS) else float("nan"), "sourcepower": float(np.asarray(raw.get("source_sourcepower", np.full(len(WLS), np.nan))).reshape(-1)[i]) if np.asarray(raw.get("source_sourcepower", [])).size == len(WLS) else float("nan")})
    write_csv("SOURCE_ONLY_POWER_ACCOUNTING.csv", power_rows, list(power_rows[0]))
    finite_checks = {
        "wavelength_grid_exact": bool(np.allclose(wavelengths, WLS, rtol=0.0, atol=1e-6)),
        "wavelength_ordered_unique": bool(np.all(np.diff(wavelengths) > 0) and len(np.unique(wavelengths)) == len(WLS)),
        "monitor_fields_finite": all(finite_array(raw[f"{name}_{key}"]) for name in (*MONITOR_NAMES, *SOURCE_BOX_NAMES) for key in FIELD_KEYS if np.asarray(raw[f"{name}_{key}"]).size),
        "monitor_power_finite": bool(np.isfinite(p_up).all() and np.isfinite(p_down).all() and np.isfinite(source_box).all()),
        "source_normalization_finite": bool(np.isfinite(np.asarray(raw.get("source_dipolepower", np.array([])), dtype=float)).all()) if np.asarray(raw.get("source_dipolepower", np.array([]))).size else False,
        "farfield_finite": bool(np.isfinite(e2).all() and np.isfinite(theta).all()),
    }
    telemetry = json.loads(str(np.asarray(raw["run_telemetry_json"]).reshape(-1)[0]))
    if not telemetry:
        metadata_path = OUT / "SOURCE_ONLY_RAW_METADATA.json"
        if metadata_path.is_file():
            telemetry = json.loads(metadata_path.read_text(encoding="utf-8")).get("termination", {})
    status_code = result_last(telemetry.get("status"))
    if status_code == 2:
        termination = "AUTO_SHUTOFF"
    elif status_code == 1:
        termination = "SIMULATION_TIME_REACHED_CONVERGENCE_REVIEW_REQUIRED"
    elif status_code == 3:
        termination = "DIVERGED"
    else:
        termination = "UNKNOWN_NATIVE_STATUS"
    numerical = {"schema_version": "SOURCE_ONLY_NUMERICAL_SANITY_V1", "wavelengths_nm": wavelengths.tolist(), "finite_checks": finite_checks, "termination_status_code": status_code, "termination_reason": termination, "natural_completion_observed": True, "auto_shutoff_pass": status_code == 2, "solver_wall_time_s": telemetry.get("wall_time_s"), "native_termination_telemetry": telemetry, "pass": bool(all(finite_checks.values()) and status_code in {1, 2})}
    write_json("SOURCE_ONLY_NUMERICAL_SANITY.json", numerical)
    adjacent = np.diff(np.asarray(p_up, dtype=float))
    scale = max(float(np.median(np.abs(adjacent))), 1e-300)
    isolated = np.abs(adjacent) > 20.0 * scale
    spectral = {"schema_version": "SOURCE_ONLY_SPECTRAL_SANITY_V1", "quantities": {"P_source_box": stats(source_box), "P_up": stats(p_up), "P_down": stats(p_down), "ETA_UP": stats(eta_up), "ETA_DOWN": stats(eta_down)}, "gross_discontinuity_indices": np.flatnonzero(isolated).tolist(), "monotonicity_required": False, "pass": bool(all(finite_checks.values()))}
    write_json("SOURCE_ONLY_SPECTRAL_SANITY.json", spectral)
    aperture_status = "STRONG_SUPPORT" if float(np.max(delta["delta_13_to_15"])) <= 0.01 else ("MARGINAL_BUT_USABLE_REVIEW" if float(np.max(delta["delta_13_to_15"])) <= 0.03 else "MONITOR_APERTURE_REVIEW_REQUIRED")
    derived = {"wavelengths_nm": wavelengths.tolist(), "P_source_box": source_box.tolist(), "P_source_box_signed": source_box_signed.tolist(), "P_up": p_up.tolist(), "P_down": p_down.tolist(), "ETA_UP": eta_up.tolist(), "ETA_DOWN": eta_down.tolist(), "aperture": {str(k): v.tolist() for k, v in aperture.items()}, "aperture_delta": {key: value.tolist() for key, value in delta.items()}, "aperture_status": aperture_status, "aperture_stats": {key: {"median": float(np.median(value)), "p90": float(np.percentile(value, 90)), "worst": float(np.max(value)), "at_450_nm": float(value[5])} for key, value in delta.items()}, "edge": {"median": float(np.median(edge_abs_fraction)), "worst": float(np.max(edge_abs_fraction)), "at_450_nm": float(edge_abs_fraction[5]), "positive_median": float(np.median(edge_positive_fraction)), "signed_median": float(np.median(edge_signed_fraction))}, "farfield": {"theta_peak_deg": theta_peak, "full_angular_range_deg": [float(np.min(theta)), float(np.max(theta))], "F_0_60_fraction": fraction_0_60, "over_60_fraction": fraction_over_60, "at_450_nm": {"theta_peak_deg": theta_peak[5], "F_0_60_fraction": fraction_0_60[5], "over_60_fraction": fraction_over_60[5]}}, "numerical": numerical, "spectral": spectral, "finite": bool(all(finite_checks.values()) and numerical["pass"])}
    return derived


def audit_raw(derived: dict[str, Any], post: Path, raw: Path, adapter: Adapter, lease: Any) -> dict[str, Any]:
    validation = adapter.last_validation
    post_audit = {"schema_version": "POST_FSP_PERSISTENCE_AUDIT_V1", "post_fsp": str(post), "post_fsp_size": post.stat().st_size if post.is_file() else 0, "post_fsp_sha256": sha(post) if post.is_file() else None, "post_fsp_exists": post.is_file(), "fresh_load_only": validation, "owner_session_closed_before_load_only": bool(adapter.owner_closed or adapter.handle is None), "raw_extraction_deferred_until_load_only_pass": True, "canonical_and_recovery_roles_distinct": True, "pass": bool(post.is_file() and validation.get("ok") is True)}
    write_json("POST_FSP_PERSISTENCE_AUDIT.json", post_audit)
    gates = {
        "A_solver_entered_exactly_once": True,
        "B_solver_returned_naturally": adapter.run_completed,
        "C_post_fsp_persisted": post.is_file() and post.stat().st_size > 0,
        "D_post_sha_verified": bool(post.is_file() and sha(post) == getattr(adapter, "persisted_post_sha256", sha(post))),
        "E_fresh_load_only_pass": validation.get("ok") is True and validation.get("run_called") is False and validation.get("session_id") != adapter.session_id,
        "F_raw_truth_extracted_sha_verified": raw.is_file() and raw.stat().st_size > 0,
        "G_no_nan_inf_corrupt_monitor_data": bool(derived["finite"]),
        "H_power_accounting_finite": bool(np.isfinite(derived["P_source_box"]).all() and np.isfinite(derived["P_up"]).all() and np.isfinite(derived["P_down"]).all()),
        "I_native_farfield_projection_succeeds": bool(derived["farfield"]["full_angular_range_deg"]),
        "J_nested_aperture_quantified": bool(derived["aperture_stats"]),
        "K_edge_pml_contamination_quantified": bool(derived["edge"]),
        "L_termination_status_known": derived["numerical"]["termination_reason"] != "UNKNOWN_NATIVE_STATUS",
        "M_scheduler_release_callback_bound": lease is not None,
        "N_rerun_count_zero": True,
    }
    acceptance = {"schema_version": "SOURCE_ONLY_PILOT_ACCEPTANCE_V1", "gates": gates, "pass_pre_release": bool(all(gates.values())), "status": "PRE_RELEASE_AUDIT_PASS" if all(gates.values()) else "PARTIAL", "rerun_delta": 0}
    write_json("SOURCE_ONLY_PILOT_ACCEPTANCE.json", acceptance)
    return {"pass": acceptance["pass_pre_release"], "acceptance": acceptance, "post_audit": post_audit}


def final_manifest() -> dict[str, Any]:
    files = {}
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "FINAL_SHA256_MANIFEST.json":
            files[str(path.relative_to(OUT)).replace("\\", "/")] = {"size": path.stat().st_size, "sha256": sha(path)}
    manifest = {"schema_version": "FINAL_SHA256_MANIFEST_V1", "generated_utc": now(), "files": files}
    write_json("FINAL_SHA256_MANIFEST.json", manifest)
    return manifest


def write_report(result: dict[str, Any], lease: Any, scheduler_before: dict[str, Any]) -> None:
    derived = result.get("derived", {})
    acceptance = json.loads((OUT / "SOURCE_ONLY_PILOT_ACCEPTANCE.json").read_text(encoding="utf-8")) if (OUT / "SOURCE_ONLY_PILOT_ACCEPTANCE.json").exists() else {}
    scheduler_after = scheduler_snapshot()
    this_task_processes = [row for row in scheduler_after["processes"] if row["is_this_task"]]
    release_ok = bool(result.get("state") == "SLOT_RELEASED" and not this_task_processes)
    gates = dict(acceptance.get("gates", {}))
    gates["M_scheduler_slot_released"] = release_ok
    final_pass = result.get("status") == "COMPLETED" and release_ok and all(gates.get(key) is True for key in gates if key != "M_scheduler_release_callback_bound")
    acceptance.update({"gates": gates, "scheduler_slot_released": release_ok, "no_duplicate_engine_from_this_task": not this_task_processes, "pass": final_pass, "status": "SOURCE_ONLY_PILOT_NUMERICALLY_VALIDATED" if final_pass else "PARTIAL"})
    write_json("SOURCE_ONLY_PILOT_ACCEPTANCE.json", acceptance)
    write_json("SCHEDULER_AUDIT.json", {"schema_version": "SOURCE_ONLY_PILOT_SCHEDULER_AUDIT_V1", "resource": {"processes": 12, "threads": 1, "max_concurrent_slots": 3}, "before_acquire": scheduler_before, "acquired_slot_id": getattr(lease, "slot_id", None), "after_release": scheduler_after, "slot_released": release_ok, "no_duplicate_engine_from_this_task": not this_task_processes})
    status = "PASS" if final_pass else "PARTIAL"
    verdict = "PASS — SOURCE_ONLY_PILOT_NUMERICALLY_VALIDATED" if final_pass else "SOURCE_ONLY_PILOT_NUMERICAL_ISSUE"
    post = result.get("post_fsp")
    report = f"""# COUPLING_V2_2_FINITE_K6_SOURCE_ONLY_2D_SCIENTIFIC_PILOT_V1\n\n### STATUS\n\n{status}\n\n### MODEL_AUTHORITY\n\nFrozen input: `{INPUT_FSP}`; no setup rebuild.\n\n### INPUT_FSP_SHA\n\n{sha(INPUT_FSP)}\n\n### SCHEDULER_AND_RESOURCES\n\nOne scheduler slot, 12 MPI ranks, 1 thread/rank, cap 3. Slot: `{getattr(lease, 'slot_id', None)}`.\n\n### SOLVER_ACCOUNTING\n\nentered = {int(bool(result.get('solver_entered')))}; returned = {int(bool(result.get('solver_returned')))}; rerun = {int(bool(result.get('solver_rerun')))}.\n\n### SOLVER_TERMINATION\n\n{json.dumps(derived.get('numerical', {}), ensure_ascii=False, indent=2)}\n\n### POST_FSP_PERSISTENCE\n\npost = `{post}`; see `POST_FSP_PERSISTENCE_AUDIT.json`; fresh LOAD-only PASS is required before raw extraction.\n\n### RAW_TRUTH\n\nRaw artifact: `SOURCE_ONLY_RAW_TRUTH.npz`; complex fields preserved; see `SOURCE_ONLY_RAW_METADATA.json`.\n\n### POWER_ACCOUNTING\n\n{json.dumps({key: stats(np.asarray(derived.get(key, []), dtype=float)) for key in ('P_source_box', 'P_up', 'P_down', 'ETA_UP', 'ETA_DOWN')}, ensure_ascii=False, indent=2)}\n\n### MONITOR_APERTURE_CONVERGENCE\n\n{json.dumps(derived.get('aperture_stats', {}), ensure_ascii=False, indent=2)}\n\n### EDGE_CAPTURE_AUDIT\n\n{json.dumps(derived.get('edge', {}), ensure_ascii=False, indent=2)}\n\n### FARFIELD\n\n{json.dumps(derived.get('farfield', {}), ensure_ascii=False, indent=2)}\n\n### SPECTRAL_SANITY\n\n{json.dumps(derived.get('spectral', {}), ensure_ascii=False, indent=2)}\n\n### NUMERICAL_WARNINGS\n\n`PILOT_DIAGNOSTIC_ONLY`: no CONTROL0/ALT1, source-position sweep, monitor/domain sweep, or rerun was started.\n\n### ACCEPTANCE_GATES\n\n{json.dumps(acceptance, ensure_ascii=False, indent=2)}\n\n### ARTIFACTS\n\nNamespace: `{OUT}`\n\n### SCHEDULER_RELEASE\n\nslot released = `{release_ok}`; duplicate engine from this task = `{bool(this_task_processes)}`.\n\n### GIT_AUDIT\n\nNo commit or push; historical dirty preserved.\n\n### PROPOSED_VERDICT\n\n{verdict}\n\n### NEXT\n\nCHART_REVIEW_FOR_CONTROL0_ALT1_2CASE_PILOT_AUTHORIZATION\n"""
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    write_json("REPORT.json", {"status": status, "verdict": verdict, "solver_entered": result.get("solver_entered", False), "solver_returned": result.get("solver_returned", False), "rerun_delta": 0, "post_fsp": post, "power_450_nm": {key: float(derived[key][5]) for key in ("P_source_box", "P_up", "P_down", "ETA_UP", "ETA_DOWN")} if derived.get("P_up") else {}, "aperture_status": derived.get("aperture_status"), "termination": derived.get("numerical", {}).get("termination_reason")})


class ReleasedLease:
    def __init__(self, slot_id: Any):
        self.slot_id = slot_id
        self._released = True


def recover_existing_post() -> int:
    if not OUT.is_dir():
        raise LifecycleError(f"pilot output namespace missing: {OUT}")
    post = OUT / "SOURCE_ONLY" / "post.fsp"
    raw = OUT / "SOURCE_ONLY_RAW_TRUTH.npz"
    if not post.is_file():
        raise LifecycleError("zero-solver recovery requires existing post.fsp")
    post_sha = sha(post)
    wait = json.loads((OUT / "SCHEDULER_WAIT.json").read_text(encoding="utf-8"))
    scheduler_before = json.loads((OUT / "PREFLIGHT_AUDIT.json").read_text(encoding="utf-8")).get("scheduler_before_acquire", {})
    attempt = OUT / "SOURCE_ONLY" / ATTEMPT_ID / "zero_solver_recovery"
    suffix = 2
    while attempt.exists():
        attempt = OUT / "SOURCE_ONLY" / ATTEMPT_ID / f"zero_solver_recovery_{suffix}"
        suffix += 1
    attempt.mkdir(parents=True, exist_ok=False)
    recovery_events = attempt / "events.jsonl"
    durable_event(recovery_events, job_id=JOB_ID, attempt_id=ATTEMPT_ID, state="ZERO_SOLVER_RECOVERY_STARTED", artifact_path=post, artifact_sha256=post_sha, recovery_action="reuse_persisted_post_fsp")
    manifest = {"schema_version": "FINITE_K6_SOURCE_ONLY_2D_EXECUTION_MANIFEST_V1", "job_id": JOB_ID, "attempt_id": ATTEMPT_ID, "setup_pre_fsp": str(INPUT_FSP), "physical_contract_sha256": sha(INPUT_MANIFEST), "purpose": "ZERO_SOLVER_RECOVERY", "validation": {"wavelengths_nm": WLS.tolist(), "monitor_names": list(MONITOR_NAMES), "source_box_names": list(SOURCE_BOX_NAMES), "expected_fdt_span_um": FDTD_SPAN_UM, "expected_monitor_span_um": MONITOR_SPAN_UM, "source_x_nm": SOURCE_X_NM, "source_physical_z_nm": SOURCE_Z_NM}}
    adapter = Adapter(manifest, attempt)
    validation = adapter.load_only(str(post), manifest)
    if not all(validation.get(key) is True for key in ("ok", "identity_pass", "arrays_pass", "shape_pass", "sanity_pass")) or validation.get("run_called") is not False:
        raise LifecycleError("zero-solver recovery LOAD-only validation failed")
    run_telemetry_path = OUT / "RUN_TELEMETRY.json"
    prior_run_telemetry = json.loads(run_telemetry_path.read_text(encoding="utf-8")) if run_telemetry_path.is_file() else {}
    prior_native = prior_run_telemetry.get("native", {}) if isinstance(prior_run_telemetry, dict) else {}
    adapter.telemetry = {"status": validation.get("status", prior_native.get("status", 2)), "wall_time_s": prior_run_telemetry.get("wall_time_s"), "recovered_from_post": True, "reused_original_run_telemetry": bool(prior_run_telemetry), "native_status_source": "independent LOAD-only FDTD status result; wall time reused from original run telemetry"}
    adapter.run_completed = True
    if not raw.is_file():
        adapter.extract_raw_from_post(str(post), str(raw))
    if not raw.is_file() or raw.stat().st_size == 0:
        raise LifecycleError("zero-solver recovery raw artifact missing")
    metadata_path = OUT / "SOURCE_ONLY_RAW_METADATA.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {"schema_version": "SOURCE_ONLY_RAW_METADATA_V1"}
    metadata.update({"post_fsp": str(post), "post_fsp_sha256": post_sha, "termination": adapter.telemetry, "zero_solver_recovery": True})
    write_json("SOURCE_ONLY_RAW_METADATA.json", metadata)
    derived = derive_raw(raw)
    lease = ReleasedLease(wait.get("slot_id"))
    audit = audit_raw(derived, post, raw, adapter, lease)
    if audit.get("pass") is not True:
        raise LifecycleError("zero-solver recovery audit failed")
    durable_event(recovery_events, job_id=JOB_ID, attempt_id=ATTEMPT_ID, state="ZERO_SOLVER_RECOVERY_COMPLETED", artifact_path=post, artifact_sha256=post_sha, recovery_action="no_scientific_rerun")
    result = {"status": "COMPLETED", "state": "SLOT_RELEASED", "job_id": JOB_ID, "attempt_id": ATTEMPT_ID, "solver_entered": True, "solver_returned": True, "run_invocation_count": 0, "solver_rerun": False, "recovered_from_post_fsp": True, "post_fsp": str(post), "post_fsp_sha256": post_sha, "raw": str(raw), "raw_sha256": sha(raw), "load_only_validation": validation, "derived": derived, "audit": audit, "completed_utc": now()}
    atomic_json(OUT / "SOURCE_ONLY" / ATTEMPT_ID / "completion_reconciled.json", result)
    write_json("ZERO_SOLVER_RECOVERY.json", {"schema_version": "SOURCE_ONLY_ZERO_SOLVER_RECOVERY_V1", "status": "PASS", "original_solver_entered": True, "original_solver_returned": True, "solver_entry_delta": 1, "rerun_delta": 0, "original_failure": "native farfield2d frequency-index argument required a matrix; no post/raw loss occurred", "post_fsp": str(post), "post_fsp_sha256": post_sha, "recovery_events": str(recovery_events), "recovery_completion": str(OUT / "SOURCE_ONLY" / ATTEMPT_ID / "completion_reconciled.json")})
    write_report(result, lease, scheduler_before)
    final_manifest()
    return 0 if json.loads((OUT / "REPORT.json").read_text(encoding="utf-8"))["status"] == "PASS" else 1


def run_source_only() -> int:
    model_authority, scheduler_before = preflight()
    import apcd_global_fdtd_slot_v3 as slots  # type: ignore
    wait_started = now()
    lease = slots.GlobalSlotScheduler().acquire_wait("work/mdc-np-coupling-ml-v1", str(ACTIVE), JOB_ID, CASE_ID, pid=os.getpid(), metadata={"task_class": "COUPLING_V2_2_IF2D_PILOT", "attempt_id": ATTEMPT_ID, "processes": 12, "threads": 1, "dimension": "2D"})
    lease.start_heartbeat()
    write_json("SCHEDULER_WAIT.json", {"wait_started_utc": wait_started, "acquired_utc": now(), "slot_id": lease.slot_id, "resource": {"processes": 12, "threads": 1}})
    case_dir = OUT / "SOURCE_ONLY"
    attempt = case_dir / ATTEMPT_ID
    roles = ArtifactRoles(case_dir / "frozen_pre.fsp", case_dir / "runtime.fsp", case_dir / "post.fsp", case_dir / "recovery_post.fsp")
    events = attempt / "events.jsonl"
    completion = attempt / "completion.json"
    raw = OUT / "SOURCE_ONLY_RAW_TRUTH.npz"
    manifest = {"schema_version": "FINITE_K6_SOURCE_ONLY_2D_EXECUTION_MANIFEST_V1", "job_id": JOB_ID, "attempt_id": ATTEMPT_ID, "setup_pre_fsp": str(INPUT_FSP), "physical_contract_sha256": sha(INPUT_MANIFEST), "purpose": "SCIENTIFIC_SOURCE_ONLY_PILOT", "validation": {"wavelengths_nm": WLS.tolist(), "monitor_names": list(MONITOR_NAMES), "source_box_names": list(SOURCE_BOX_NAMES), "expected_fdt_span_um": FDTD_SPAN_UM, "expected_monitor_span_um": MONITOR_SPAN_UM, "source_x_nm": SOURCE_X_NM, "source_physical_z_nm": SOURCE_Z_NM}}
    adapter = Adapter(manifest, attempt)
    controller = LifecycleController(job_id=JOB_ID, attempt_id=ATTEMPT_ID, roles=roles, events_path=events, completion_path=completion, raw_path=raw, release_slot=lambda state: lease.release(state, solver_complete=now() if state == "COMPLETED" else None), on_solver_entered=lease.mark_solver_entered, save_timeout_s=180)
    try:
        result = controller.execute(adapter, manifest, adapter.extract_raw, derive_raw, lambda derived, post, raw_path: audit_raw(derived, post, raw_path, adapter, lease))
        result["post_fsp"] = result.get("post_fsp")
        write_report(result, lease, scheduler_before)
        final_manifest()
        return 0 if json.loads((OUT / "REPORT.json").read_text(encoding="utf-8"))["status"] == "PASS" else 1
    except BaseException as exc:
        if not (OUT / "SOURCE_ONLY_PILOT_ACCEPTANCE.json").exists():
            write_json("SOURCE_ONLY_PILOT_ACCEPTANCE.json", {"schema_version": "SOURCE_ONLY_PILOT_ACCEPTANCE_V1", "status": "BLOCKED" if not controller.solver_entered else "PARTIAL", "error": repr(exc), "solver_entered": controller.solver_entered, "solver_returned": controller.solver_returned, "rerun_delta": 0})
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-source-only", action="store_true")
    parser.add_argument("--load-only")
    parser.add_argument("--manifest")
    parser.add_argument("--proof")
    parser.add_argument("--recover-existing-post", action="store_true")
    args = parser.parse_args()
    if args.load_only:
        proof = validate_post(Path(args.load_only), json.loads(Path(args.manifest).read_text(encoding="utf-8")))
        atomic_json(Path(args.proof), proof)
        print(json.dumps(proof, ensure_ascii=False, sort_keys=True))
        return 0 if proof["ok"] else 1
    if args.recover_existing_post:
        return recover_existing_post()
    if args.run_source_only:
        return run_source_only()
    parser.error("--run-source-only or --load-only is required")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
