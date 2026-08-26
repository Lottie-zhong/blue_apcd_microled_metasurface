from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
AUTHORITY = ROOT / "paper_a_broadband/authority/paper_a_fdtd_physics_validity_gate_v2_instrumented.json"
V1 = ROOT / "paper_a_broadband/scripts/fdtd_physics_validity_gate_v1.py"
sys.path.insert(0, r"N:/Program Files/ANSYS Inc/v251/Lumerical/api/python")


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha_file(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_authority():
    data = json.loads(AUTHORITY.read_text(encoding="utf-8"))
    if data.get("schema") != "PAPER_A_FDTD_PHYSICS_VALIDITY_GATE_V2_INSTRUMENTED":
        raise RuntimeError("V2_AUTHORITY_INVALID")
    if data.get("resource_safety", {}).get("NEW_FDTD_BUDGET") != 0:
        raise RuntimeError("V2_AUTHORITY_ZERO_SOLVER_CONFLICT")
    return data


def load_v1():
    spec = importlib.util.spec_from_file_location("gate_v1_readonly", V1)
    if spec is None or spec.loader is None:
        raise RuntimeError("V1_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def auto_shutoff(log: Path, authority):
    values = []
    if log.exists():
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            match = re.search(r"Auto Shutoff:\s*([0-9.eE+-]+)", line)
            if match:
                values.append(float(match.group(1)))
    out = {"path": str(log), "sha256": sha_file(log) if log.exists() else None, "sample_count": len(values), "trajectory": values}
    if not values:
        out.update(status="INSUFFICIENT_EVIDENCE_NOT_VALIDATED", reason="no Auto Shutoff trajectory in immutable solver log")
        return out
    ref = float(authority["late_time_classification"]["initial_auto_shutoff_reference"])
    count = max(3, math.ceil(len(values) / 3))
    tail = np.asarray(values[-count:], dtype=float)
    slope = float(np.polyfit(np.arange(count, dtype=float), tail, 1)[0])
    prior_min = min(values[:-count] or values)
    returned = bool(prior_min < ref and values[-1] > ref)
    positive = bool(tail[-1] > tail[0] and slope > 0.0)
    divergent = bool(returned and positive)
    out.update(
        status="INVALID_FOR_PHYSICS_TRUTH_NUMERICAL_DIVERGENCE" if divergent else "PASS",
        final_auto_shutoff=values[-1], peak_auto_shutoff=max(values), minimum_auto_shutoff=min(values),
        late_window={"count": count, "first": float(tail[0]), "last": float(tail[-1]), "linear_slope": slope},
        signals={"previous_decay_below_reference": prior_min < ref, "returned_above_reference": returned, "positive_late_window_growth": positive, "established_divergence": divergent},
        classification_rule="V1/BF08 established Auto Shutoff rule",
    )
    return out


def load_evidence(path, case_id):
    if path is None or not path.exists():
        return {"status": "INSUFFICIENT_EVIDENCE_NOT_VALIDATED", "reason": "V2 immutable convergence evidence unavailable", "path": str(path) if path else None}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "PAPER_A_FDTD_CONVERGENCE_EVIDENCE_V2" or data.get("case_id") != case_id:
        return {"status": "INSUFFICIENT_EVIDENCE_NOT_VALIDATED", "reason": "V2 evidence schema/case mismatch", "path": str(path), "sha256": sha_file(path)}
    data["_path"] = str(path)
    data["_sha256"] = sha_file(path)
    return data


def independent_series(evidence):
    series = evidence.get("independent_time_series", {}) if evidence.get("status") != "INSUFFICIENT_EVIDENCE_NOT_VALIDATED" else {}
    time_s = np.asarray(series.get("time_s", []), dtype=float)
    energy = np.asarray(series.get("field_energy_proxy", []), dtype=float)
    if len(time_s) < 3 or len(energy) != len(time_s):
        return {"status": "INSUFFICIENT_EVIDENCE_NOT_VALIDATED", "reason": "independent time-series field-energy proxy missing or shorter than 3 samples", "sample_count": int(len(time_s))}
    finite = bool(np.all(np.isfinite(time_s)) and np.all(np.isfinite(energy)))
    increasing = bool(np.all(np.diff(time_s) > 0.0))
    nonnegative = bool(np.all(energy >= 0.0) and np.any(energy > 0.0))
    count = max(3, math.ceil(len(energy) / 3))
    tail = energy[-count:]
    slope = float(np.polyfit(np.arange(count, dtype=float), tail, 1)[0])
    return {"status": "PASS" if finite and increasing and nonnegative else "INSUFFICIENT_EVIDENCE_NOT_VALIDATED", "sample_count": int(len(time_s),), "finite": finite, "strictly_increasing_time": increasing, "nonnegative_proxy": nonnegative, "time_start_s": float(time_s[0]), "time_end_s": float(time_s[-1]), "late_window": {"count": count, "first": float(tail[0]), "last": float(tail[-1]), "linear_slope": slope}, "positive_late_window_growth": bool(tail[-1] > tail[0] and slope > 0.0), "monitor_name": series.get("monitor_name"), "thresholds_not_invented": True}


def combine(case_id, post_fsp: Path, log: Path, evidence_path):
    authority = load_authority()
    v1 = load_v1()
    auto = auto_shutoff(log, authority)
    evidence = load_evidence(evidence_path, case_id)
    completed = v1.inspect_completed_fsp(post_fsp, v1.authority())
    transmission = completed["transmission"]
    source = completed["source_normalization"]
    series = independent_series(evidence)
    transmission_bad = (not transmission.get("finite", False)) or (auto.get("signals", {}).get("established_divergence", False) and (transmission.get("persistent_negative", False) or transmission.get("control_envelope_excess_count", 0) > 0))
    if not source.get("pass", False):
        status, root = "INVALID_FOR_PHYSICS_TRUTH_SOURCE_NORMALIZATION", "E_SOURCE_NORMALIZATION_INVALID"
    elif transmission_bad and not auto.get("signals", {}).get("established_divergence", False):
        status, root = "INVALID_FOR_PHYSICS_TRUTH_TRANSMISSION_SANITY", "E_TRANSMISSION_SANITY_INVALID"
    elif auto.get("signals", {}).get("established_divergence", False):
        status, root = "INVALID_FOR_PHYSICS_TRUTH_NUMERICAL_DIVERGENCE", "E_NUMERICAL_TIME_DOMAIN_DIVERGENCE_IN_STORED_SOLVER_ENERGY_RESULT"
    elif series.get("status") != "PASS":
        status, root = "INSUFFICIENT_EVIDENCE_NOT_VALIDATED", "E_INDEPENDENT_LATE_TIME_EVIDENCE_MISSING_OR_AMBIGUOUS"
    elif series.get("positive_late_window_growth", False):
        status, root = "INSUFFICIENT_EVIDENCE_NOT_VALIDATED", "E_LATE_TIME_PROXY_AMBIGUOUS_WITHOUT_ESTABLISHED_AUTOSHUTOFF_DIVERGENCE"
    elif transmission_bad:
        status, root = "INVALID_FOR_PHYSICS_TRUTH_TRANSMISSION_SANITY", "E_TRANSMISSION_SANITY_INVALID"
    else:
        status, root = "VALID_FOR_PHYSICS_TRUTH", None
    return {"schema": "PAPER_A_FDTD_PHYSICS_VALIDITY_GATE_RESULT_V2", "case_id": case_id, "status": status, "root_cause": root, "authority_path": str(AUTHORITY), "authority_sha256": sha_file(AUTHORITY), "post_fsp": completed, "solver_log": auto, "convergence_evidence": evidence, "gates": {"gate_1_solver_completion_and_auto_shutoff": auto, "gate_2_independent_time_series": series, "gate_3_transmission_sanity": {"status": "PASS" if not transmission_bad else "DIAGNOSTIC_NEGATIVE_WITH_NUMERICAL_DIVERGENCE" if auto.get("signals", {}).get("established_divergence", False) else "INVALID_FOR_PHYSICS_TRUTH_TRANSMISSION_SANITY", "finite": transmission.get("finite"), "negative_count": transmission.get("negative_count"), "control_envelope_excess_count": transmission.get("control_envelope_excess_count"), "no_transformation_applied": True}, "gate_4_source_normalization": {"status": "PASS" if source.get("pass", False) else "INVALID_FOR_PHYSICS_TRUTH_SOURCE_NORMALIZATION", **source}}, "classification": {"late_time_rule": authority["late_time_classification"], "thresholds_not_invented": True}, "resource_safety": {"NEW_FDTD_BUDGET": 0, "solver_run_called": False, "solver_entered": 0, "scheduler_admission": False, "rcwa": 0, "ml": 0}, "raw_solver_data_modified": False, "legacy_v1_not_rewritten": True, "timestamp_utc": now()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True); parser.add_argument("--post-fsp", type=Path, required=True); parser.add_argument("--solver-log", type=Path, required=True); parser.add_argument("--convergence-evidence", type=Path); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = combine(args.case_id, args.post_fsp, args.solver_log, args.convergence_evidence)
    write_json(args.output, result); print(json.dumps(result, ensure_ascii=False, default=str)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
