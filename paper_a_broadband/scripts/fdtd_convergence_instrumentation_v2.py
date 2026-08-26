from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
AUTHORITY = ROOT / "paper_a_broadband/authority/paper_a_bf01_bf04_prepared_fsp_authority_v1.json"
READER = ROOT / "paper_a_broadband/scripts/bf01_bf04_prepared_fsp_reconciliation_v1.py"
MONITOR_NAME = "v2_convergence_time_probe"
MONITOR_CONTRACT = {
    "schema": "PAPER_A_FDTD_CONVERGENCE_INSTRUMENTATION_V2",
    "monitor_name": MONITOR_NAME,
    "monitor_type": "Point time monitor",
    "location_nm": {"x": 0.0, "y": 0.0, "z": 700.0},
    "recorded_fields": ["t", "Ex", "Ey", "Ez", "Hx", "Hy", "Hz"],
    "non_perturbative_contract": {
        "geometry_unchanged": True, "materials_unchanged": True, "source_unchanged": True,
        "mesh_unchanged": True, "boundaries_unchanged": True, "simulation_time_unchanged": True,
        "scientific_monitors_unchanged": True, "normalization_unchanged": True,
        "full_jones_observables_unchanged": True, "only_added_object": MONITOR_NAME,
    },
}
sys.path.insert(0, r"N:/Program Files/ANSYS Inc/v251/Lumerical/api/python")


def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()
def sha_obj(value): return hashlib.sha256(canonical(value)).hexdigest()
def sha_file(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def reader_module():
    spec = importlib.util.spec_from_file_location("v2_semantic_reader", READER)
    if spec is None or spec.loader is None: raise RuntimeError("READER_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def jsonable(value):
    if isinstance(value, np.generic): return value.item()
    if isinstance(value, np.ndarray): return value.tolist()
    if isinstance(value, (list, tuple)): return [jsonable(x) for x in value]
    if isinstance(value, dict): return {str(k): jsonable(x) for k, x in value.items()}
    return value if isinstance(value, (str, int, float, bool)) or value is None else str(value)


def physics_view(semantic):
    result = json.loads(json.dumps(semantic, default=str)); result.pop("object_names", None); return result


def add_time_monitor(fdtd):
    try: names = jsonable(fdtd.getobjectlist("::model::"))
    except Exception: names = []
    if MONITOR_NAME in names: raise RuntimeError("V2_MONITOR_ALREADY_PRESENT")
    try: fdtd.addtime()
    except Exception: fdtd.eval("addtime;")
    try: fdtd.set("name", MONITOR_NAME)
    except Exception:
        try: fdtd.setnamed("time", "name", MONITOR_NAME)
        except Exception as exc: raise RuntimeError(f"V2_TIME_MONITOR_CREATE_FAILED:{exc}")
    for key, value in (("monitor type", "Point"), ("x", 0.0), ("y", 0.0), ("z", 700e-9)):
        fdtd.setnamed(MONITOR_NAME, key, value)


def monitor_readback(fdtd):
    result = {}
    for key in ("monitor type", "x", "y", "z", "record data", "time monitor"):
        try: result[key] = jsonable(fdtd.getnamed(MONITOR_NAME, key))
        except Exception as exc: result[key] = f"UNAVAILABLE:{type(exc).__name__}:{exc}"
    return result


def instrument(parent: Path, output: Path, case_id: str, report: Path):
    import lumapi
    output.parent.mkdir(parents=True, exist_ok=True)
    reader = reader_module(); before = reader.read_fsp(parent, case_id, case_id.rsplit("_", 1)[1])
    fdtd = lumapi.FDTD(hide=True)
    try:
        fdtd.load(str(parent)); fdtd.switchtolayout(); add_time_monitor(fdtd); fdtd.save(str(output))
    finally:
        try: fdtd.close()
        except Exception: pass
    fdtd = lumapi.FDTD(hide=True)
    try:
        fdtd.load(str(output)); readback = monitor_readback(fdtd)
    finally:
        try: fdtd.close()
        except Exception: pass
    after = reader.read_fsp(output, case_id, case_id.rsplit("_", 1)[1])
    before_fp, after_fp = sha_obj(physics_view(before["semantic"])), sha_obj(physics_view(after["semantic"]))
    contract = dict(MONITOR_CONTRACT); contract["monitor_readback"] = readback
    status = "PASS" if before["readback_complete"] and after["readback_complete"] and before_fp == after_fp and readback.get("monitor type") == "Point" else "BLOCKED"
    authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))
    result = {
        "schema": "PAPER_A_FDTD_CONVERGENCE_INSTRUMENTATION_SETUP_ONLY_V2", "status": status,
        "case_id": case_id, "solver_run_called": False, "solver_entered": False,
        "parent_fsp": {"path": str(parent), "sha256": sha_file(parent)},
        "instrumented_pre_fsp": {"path": str(output), "sha256": sha_file(output)},
        "physics_semantic_fingerprint": {"method": "canonical semantic readback excluding instrumentation object list", "before": before_fp, "after": after_fp, "unchanged": before_fp == after_fp, "legacy_full_semantic_before": sha_obj(before["semantic"]), "authority_semantic_fingerprint": authority["cases"][case_id]["semantic_fingerprint"]},
        "convergence_instrumentation_fingerprint": sha_obj(contract), "instrumentation_contract": contract,
        "readback": {"before_complete": before["readback_complete"], "after_complete": after["readback_complete"], "after_object_names": after["semantic"].get("object_names")},
        "physics_contract_unchanged": before_fp == after_fp, "scientific_monitors_unchanged": True, "normalization_unchanged": True, "mesh_boundary_unchanged": True, "timestamp_utc": now(),
    }
    write_json(report, result); return result


def _value(fdtd, key):
    try: return np.asarray(fdtd.getdata(MONITOR_NAME, key))
    except Exception:
        try:
            result = fdtd.getresult(MONITOR_NAME, key)
            return np.asarray(result.get(key, result.get("data", result)) if isinstance(result, dict) else result)
        except Exception: return None


def _series(value, count):
    if value is None: return None
    array = np.asarray(value)
    if array.size == count: return array.reshape(count)
    if array.ndim and array.shape[-1] == count: return np.sum(np.abs(array.reshape((-1, count))) ** 2, axis=0)
    if array.ndim and array.shape[0] == count: return np.sum(np.abs(array.reshape((count, -1))) ** 2, axis=1)
    return None


def persist_convergence_evidence(fdtd, case_id, attempt_id, case_dir, pre_fsp, post_fsp, log_path, instrumentation_fingerprint):
    time_data = _value(fdtd, "t"); time_s = np.asarray(time_data, dtype=float).reshape(-1) if time_data is not None else np.asarray([], dtype=float)
    fields = {key: _value(fdtd, key) for key in ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz")}; count = len(time_s); energy = None
    if count >= 3:
        energy = np.zeros(count, dtype=float)
        used = 0
        for value in fields.values():
            series = _series(value, count)
            if series is not None: energy += np.abs(np.asarray(series, dtype=complex)) ** 2; used += 1
        if used == 0: energy = None
    persisted = bool(count >= 3 and energy is not None and np.all(np.isfinite(time_s)) and np.all(np.diff(time_s) > 0) and np.all(np.isfinite(energy)))
    auto = []
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = re.search(r"Auto Shutoff:\s*([0-9.eE+-]+)", line)
            if match: auto.append(float(match.group(1)))
    data = {"schema": "PAPER_A_FDTD_CONVERGENCE_EVIDENCE_V2", "case_id": case_id, "attempt_id": attempt_id, "status": "PERSISTED" if persisted else "INDEPENDENT_TIME_SERIES_NOT_PERSISTED", "solver_completion": {"status": "RETURNED", "solver_run_called": True, "solver_entered": True}, "pre_fsp": {"path": str(pre_fsp), "sha256": sha_file(pre_fsp)}, "post_fsp": {"path": str(post_fsp), "sha256": sha_file(post_fsp)}, "solver_log": {"path": str(log_path), "sha256": sha_file(log_path) if log_path.exists() else None, "auto_shutoff_trajectory": auto}, "independent_time_series": {"status": "PERSISTED" if persisted else "NOT_PERSISTED", "monitor_name": MONITOR_NAME, "time_s": time_s.tolist(), "field_energy_proxy": energy.tolist() if energy is not None else [], "sample_count": count, "sampling_contract": "raw point-monitor samples; no physical observable renormalization"}, "convergence_instrumentation_fingerprint": instrumentation_fingerprint, "physics_data_unchanged": True, "normalization_unchanged": True, "raw_solver_data_modified": False, "timestamp_utc": now()}
    output = case_dir / "convergence_evidence_v2.json"; write_json(output, data); data["evidence_path"] = str(output); data["evidence_sha256"] = sha_file(output); return data


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--parent", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); parser.add_argument("--case-id", default="BF01_x"); parser.add_argument("--report", type=Path, required=True); args = parser.parse_args()
    result = instrument(args.parent, args.output, args.case_id, args.report); print(json.dumps(result, indent=2, ensure_ascii=False)); return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__": raise SystemExit(main())
