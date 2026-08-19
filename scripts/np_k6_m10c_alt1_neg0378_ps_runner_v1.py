from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import os
import shutil
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
EVID = ROOT / "outputs" / "np_k6_m10c_alt1_neg0378_ps_quantitative_anchor_v1"
SETUP = EVID / "runtime_prefsp"
RUNS = ROOT / "outputs" / "np_k6_m10c_alt1_neg0378_ps_quantitative_anchor_v1" / "runtime_runs"
REGISTRY = Path(r"D:\project\apcd_global_fdtd_slot_registry_v1.json")
BRANCH = "work/np-k6-mdc-v1"
TASK = "NP_K6_M10C_ALT1_NEG0378_PS_REPLACEMENT_QUANTITATIVE_ANCHOR_V1"
SCHED_TASK = "NP_K6_M10C_ALT1_NEG0378_PS_001"
RESOURCE_POLICY = "APCD_GLOBAL_FDTD_PRODUCTION_RESOURCE_POLICY_V4"
SCHED_POLICY = "APCD_GLOBAL_FDTD_SCHEDULING_POLICY_V3"
GEOM = "00a951a831619fe0a34b5ffd5c58545282e2236d79190bd9d2d3961dd856f7b1"
UX = -0.3786893999886029
EXPECTED_MPI, EXPECTED_THREADS = "12", "1"
WAVELENGTHS = list(range(445, 456))
CASES = (
    ("NP_K6_M10C_ALT1_UX_M0d378689399989_P_XLIKE", "P_XLIKE"),
    ("NP_K6_M10C_ALT1_UX_M0d378689399989_S_YLIKE", "S_YLIKE"),
)
EXPECTED_SETUP_SHA = {
    "NP_K6_M10C_ALT1_UX_M0d378689399989_P_XLIKE": "ca8c74d457011d18697e98c4035f54bb0b57c0a2557cbbfe8fad9d0bf109df56",
    "NP_K6_M10C_ALT1_UX_M0d378689399989_S_YLIKE": "780b253835c4554bca0b7c56ba94eb41c83e1cb427b9d7d4dbe02534efe54e9e",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def event(state: str, **payload) -> None:
    EVID.mkdir(parents=True, exist_ok=True)
    with (EVID / "durable_monitor.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"timestamp_utc": now(), "state": state, **payload}, sort_keys=True, ensure_ascii=False) + "\n")


def flat(value):
    import numpy as np
    return np.asarray(value).reshape(-1)


def scalar(value) -> float:
    a = flat(value)
    return float(a[0])


def finite(value) -> bool:
    import numpy as np
    return bool(np.all(np.isfinite(np.asarray(value, dtype=float))))


def scheduler_module():
    path = ROOT / "scripts" / "apcd_global_fdtd_slot_v4_resource.py"
    spec = importlib.util.spec_from_file_location("m10c_slot_v4", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("GLOBAL_SCHEDULER_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scheduler_process_provider(sm):
    # Keep the scheduler from treating resident/RCWA helpers as unknown FDTD
    # jobs.  This is admission classification only; it never terminates a PID.
    rows = sm._ps_snapshot()
    allowed = ("blue_apcd_np", "blue_apcd_lp_global_h_manifold_v1", "\\lp_global_h")
    return [row for row in rows if any(token in str(row.get("cmdline") or "").lower().replace("/", "\\") for token in allowed)]


def acquire(sm, case_id, pol):
    deadline = time.monotonic() + 180.0
    while True:
        try:
            lease = sm.GlobalSlotScheduler(REGISTRY, process_provider=lambda: scheduler_process_provider(sm)).acquire_wait(
                BRANCH,
                str(ROOT),
                TASK,
                case_id,
                pid=os.getpid(),
                metadata={
                    "attempt_id": "attempt_001",
                    "polarization": pol,
                    "task_class": "NP_M10C_SERIAL_ANGULAR_HF",
                    "processes": 12,
                    "threads": 1,
                    "resource_policy": RESOURCE_POLICY,
                },
                timeout_s=21600.0,
                poll_s=30.0,
            )
            lease.start_heartbeat(interval_s=5.0)
            return lease
        except sm.SlotError as exc:
            if str(exc) != "SOLVER_TYPE_CLASSIFICATION_REQUIRED" or time.monotonic() >= deadline:
                raise
            event("SCHEDULER_CLASSIFICATION_RETRY", case_id=case_id, error=str(exc))
            time.sleep(5.0)


def resource_gate(fd):
    for key, value in (("processes", EXPECTED_MPI), ("threads", EXPECTED_THREADS)):
        fd.setresource("FDTD", 1, key, value)
    readback = {key: str(fd.getresource("FDTD", 1, key)).strip() for key in ("processes", "threads")}
    expected = {"processes": EXPECTED_MPI, "threads": EXPECTED_THREADS}
    if readback != expected:
        raise RuntimeError("RESOURCE_CONTRACT_MISMATCH:" + repr(readback))
    return {"policy": RESOURCE_POLICY, "expected": expected, "readback": readback}


def extract(fd, case_id, pol):
    import numpy as np

    transmission = fd.getresult("transmission_monitor", "T")
    reflection = fd.getresult("reflection_monitor", "T")
    wavelengths = np.real(flat(transmission["lambda"])) * 1e9
    t_total = np.real(flat(transmission["T"]))
    r_signed = np.real(flat(reflection["T"]))
    r_total = np.abs(r_signed)
    if len(wavelengths) != 11 or len(t_total) != 11 or len(r_total) != 11:
        raise RuntimeError("EXACT_11_WAVELENGTHS_REQUIRED")

    norm_mismatch = []
    try:
        raw_t = flat(fd.getdata("transmission_monitor", "power"))
        raw_r = flat(fd.getdata("reflection_monitor", "power"))
        freq = flat(fd.getdata("transmission_monitor", "f"))
        source_power = np.asarray([float(fd.sourcepower(float(f))) for f in freq])
        for i in range(11):
            if abs(source_power[i]) > 0:
                norm_mismatch.append(max(
                    abs(float(np.real(raw_t[i] / source_power[i]) - t_total[i])),
                    abs(float(np.real(raw_r[i] / source_power[i]) - r_signed[i])),
                ))
    except Exception as exc:
        norm_error = repr(exc)
    else:
        norm_error = None

    rows = []
    order_rows = []
    for i in range(11):
        power = np.real(flat(fd.grating("transmission_monitor", i + 1)))
        order_n = np.rint(np.real(flat(fd.gratingn("transmission_monitor", i + 1)))).astype(int)
        ux = np.real(flat(fd.gratingu1("transmission_monitor", i + 1)))
        count = min(len(power), len(order_n), len(ux))
        power, order_n, ux = power[:count], order_n[:count], ux[:count]
        if count == 0 or not finite(power):
            raise RuntimeError("TRANSMITTED_ORDER_RESULT_INVALID")
        denominator = float(np.sum(np.abs(power)))
        if denominator <= 0:
            raise RuntimeError("EMPTY_TRANSMITTED_ORDER_POWER")
        fraction = power / denominator
        eta = t_total[i] * fraction
        plus = float(eta[order_n == 1][0]) if np.any(order_n == 1) else 0.0
        zero = float(eta[order_n == 0][0]) if np.any(order_n == 0) else 0.0
        minus = float(eta[order_n == -1][0]) if np.any(order_n == -1) else 0.0
        non_target = float(t_total[i] - plus)
        pm = plus + minus
        dominant = int(order_n[np.argmax(eta)])
        for j in range(count):
            order_rows.append({
                "case_id": case_id,
                "polarization": pol,
                "wavelength_nm": float(wavelengths[i]),
                "order_n": int(order_n[j]),
                "u_x": float(ux[j]),
                "transmitted_fraction": float(fraction[j]),
                "eta_abs": float(eta[j]),
                "power_source_norm": float(power[j]),
            })
        rows.append({
            "case_id": case_id,
            "polarization": pol,
            "wavelength_nm": float(wavelengths[i]),
            "T_total": float(t_total[i]),
            "R_total": float(r_total[i]),
            "closure": float(t_total[i] + r_total[i]),
            "residual": float(1.0 - t_total[i] - r_total[i]),
            "eta_plus1": plus,
            "eta_0": zero,
            "eta_minus1": minus,
            "non_target_efficiency": non_target,
            "directionality_plus1_over_pm1": (plus / pm) if pm else None,
            "eta_plus1_over_minus1": (plus / minus) if minus else None,
            "plus1_air_side_angle_deg": None,
            "dominant_order_n": dominant,
            "order_sum_T_mismatch": float(abs(np.sum(eta) - t_total[i])),
            "open_order_count": int(count),
        })

    structure_observable = False
    structure_anomaly = None
    quality = {
        "finite_11_points": all(finite([r[k] for k in ("T_total", "R_total", "residual", "eta_plus1", "eta_0", "eta_minus1")]) for r in rows),
        "exact_wavelengths": all(abs(rows[i]["wavelength_nm"] - WAVELENGTHS[i]) <= 1e-6 for i in range(11)),
        "no_duplicate_wavelengths": len({r["wavelength_nm"] for r in rows}) == 11,
        "max_closure_residual": max(abs(r["residual"]) for r in rows),
        "max_order_sum_T_mismatch": max(r["order_sum_T_mismatch"] for r in rows),
        "max_normalization_mismatch": max(norm_mismatch) if norm_mismatch else None,
        "normalization_readback_error": norm_error,
        "structure_anomaly_observable": structure_observable,
        "max_structure_interval_anomaly": structure_anomaly,
    }
    quality.update({
        "closure_gate_pass": quality["max_closure_residual"] <= 0.01,
        "order_sum_gate_pass": quality["max_order_sum_T_mismatch"] <= 1e-8,
        "normalization_gate_pass": bool(norm_mismatch) and quality["max_normalization_mismatch"] <= 1e-8,
        "structure_anomaly_gate_pass": None if not structure_observable else structure_anomaly <= 0.01,
    })
    quality["quality_gate_pass"] = bool(
        quality["finite_11_points"] and quality["exact_wavelengths"] and quality["no_duplicate_wavelengths"]
        and quality["closure_gate_pass"] and quality["order_sum_gate_pass"] and quality["normalization_gate_pass"]
        and (quality["structure_anomaly_gate_pass"] is not False)
    )
    return rows, order_rows, quality


def write_csv(path: Path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_case(case_id, pol, sm):
    case_dir = RUNS / case_id / "attempt_001"
    case_dir.mkdir(parents=True, exist_ok=True)
    prefsp = SETUP / (case_id + ".fsp")
    runfsp = case_dir / (case_id + "_attempt_001_run.fsp")
    postfsp = case_dir / (case_id + "_attempt_001_post.fsp")
    ledger_path = case_dir / "attempt_ledger.json"
    if ledger_path.exists():
        old = read_json(ledger_path)
        if old.get("entered") or int(old.get("run_invocation_count", 0)) > 0:
            raise RuntimeError("EXISTING_ENTERED_ATTEMPT_NO_REPLAY:" + case_id)
    if postfsp.exists():
        raise RuntimeError("POST_FSP_ALREADY_EXISTS_NO_REPLAY:" + case_id)
    if not prefsp.exists():
        raise RuntimeError("SETUP_FSP_MISSING:" + str(prefsp))
    source_sha = sha(prefsp)
    if source_sha != EXPECTED_SETUP_SHA[case_id]:
        raise RuntimeError("SETUP_SHA_MISMATCH:" + case_id)
    shutil.copyfile(prefsp, runfsp)
    run_sha = sha(runfsp)
    if source_sha != run_sha:
        raise RuntimeError("RUN_COPY_SHA_MISMATCH:" + case_id)
    ledger = {
        "case_id": case_id,
        "attempt_id": "attempt_001",
        "polarization": pol,
        "exact_u_x": UX,
        "source_prefsp_path": str(prefsp),
        "source_prefsp_sha256": source_sha,
        "run_copy_path": str(runfsp),
        "run_copy_sha256": run_sha,
        "physical_contract_hash": GEOM,
        "resource_policy": RESOURCE_POLICY,
        "scheduling_policy": SCHED_POLICY,
        "authorized_new_solver_invocations": 2,
        "task_local_max_active_fdtd": 1,
        "entered": False,
        "run_invocation_count": 0,
        "engine_completed": False,
        "post_saved": False,
        "controller_returned": False,
        "setup_only": False,
        "durable_monitor": {"sampling_s": 600, "hourly_summary_s": 3600, "visible_output": "file_only"},
        "timestamps": {"controller_started": now()},
    }
    atomic(ledger_path, ledger)
    event("CONTROLLER_STARTED", case_id=case_id, attempt_id="attempt_001")
    event("PREFSP_OPENED", case_id=case_id, attempt_id="attempt_001", source_sha256=source_sha)
    lease = acquire(sm, case_id, pol)
    ledger.update({"slot_id": lease.slot_id, "slot_acquire_time": now(), "local_active_fdtd": 1})
    atomic(ledger_path, ledger)
    event("SLOT_ACQUIRED", case_id=case_id, slot_id=lease.slot_id, processes=12, threads=1)
    fd = None
    try:
        import lumapi
        fd = lumapi.FDTD(str(runfsp), hide=True)
        ledger["prefsp_opened"] = True
        ledger["resource_contract"] = resource_gate(fd)
        atomic(ledger_path, ledger)
        stamp = now()
        ledger.update({"entered": True, "run_invocation_count": 1, "solver_entered_timestamp": stamp})
        atomic(ledger_path, ledger)
        lease.mark_solver_entered(stamp)
        event("SOLVER_ENTERED", case_id=case_id, slot_id=lease.slot_id, ux=UX, polarization=pol)
        fd.run()
        ledger.update({"engine_completed": True, "engine_completed_timestamp": now()})
        atomic(ledger_path, ledger)
        event("ENGINE_COMPLETED", case_id=case_id, slot_id=lease.slot_id)
        fd.save(str(postfsp))
        for _ in range(60):
            s1 = postfsp.stat()
            time.sleep(2)
            s2 = postfsp.stat()
            if s1.st_size == s2.st_size and s1.st_mtime_ns == s2.st_mtime_ns:
                break
        post_sha = sha(postfsp)
        ledger.update({"post_saved": True, "post_fsp_path": str(postfsp), "post_fsp_sha256": post_sha, "post_saved_timestamp": now()})
        atomic(ledger_path, ledger)
        event("POST_FSP_PERSISTED", case_id=case_id, slot_id=lease.slot_id, post_sha256=post_sha)
        fd.close()
        fd = None
        fd = lumapi.FDTD(str(postfsp), hide=True)
        rows, order_rows, quality = extract(fd, case_id, pol)
        atomic(case_dir / "quality_gate.json", quality)
        atomic(case_dir / "spectral_metrics.json", {"rows": rows})
        write_csv(case_dir / "spectral_metrics.csv", rows)
        write_csv(case_dir / "transmitted_orders.csv", order_rows)
        ledger.update({"extracted": True, "quality_gate_pass": quality["quality_gate_pass"], "quality_adjudicated_timestamp": now()})
        atomic(ledger_path, ledger)
        event("QUALITY_GATE_PASS" if quality["quality_gate_pass"] else "QUALITY_GATE_FAIL", case_id=case_id, metrics=quality)
        return quality["quality_gate_pass"], ledger, quality
    finally:
        if fd is not None:
            try:
                fd.close()
            except Exception:
                pass
        if ledger.get("engine_completed") and ledger.get("post_saved") and ledger.get("quality_gate_pass") is not None:
            lease.release("QUALITY_PASS" if ledger.get("quality_gate_pass") else "QUALITY_FAIL", ledger.get("engine_completed_timestamp"))
            ledger.update({"slot_released": True, "slot_release_time": now(), "local_active_fdtd": 0})
            atomic(ledger_path, ledger)
            event("SLOT_RELEASED", case_id=case_id, slot_id=lease.slot_id, quality_gate_pass=ledger.get("quality_gate_pass"))
        elif ledger.get("entered"):
            event("HARD_GATE_ENTERED_ATTEMPT_RECOVERY_REQUIRED", case_id=case_id, slot_id=lease.slot_id)


def main():
    EVID.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(parents=True, exist_ok=True)
    atomic(EVID / "controller_status.json", {"task_id": TASK, "scheduler_task": SCHED_TASK, "state": "STARTED", "started_utc": now(), "global_cap": 3, "local_cap": 1, "resource_policy": RESOURCE_POLICY, "scheduling_policy": SCHED_POLICY, "case_order": [x[0] for x in CASES], "visible_output": "file_only", "monitor_interval_s": 600, "hourly_summary_s": 3600})
    sm = scheduler_module()
    completed = []
    for case_id, pol in CASES:
        ok, ledger, quality = run_case(case_id, pol, sm)
        ledger_path = RUNS / case_id / "attempt_001" / "attempt_ledger.json"
        ledger.update({"controller_returned": True, "controller_returned_timestamp": now()})
        atomic(ledger_path, ledger)
        completed.append({"case_id": case_id, "polarization": pol, "quality_gate_pass": ok, "run_invocation_count": ledger.get("run_invocation_count", 0), "entered": ledger.get("entered", False), "slot_id": ledger.get("slot_id"), "slot_acquire_time": ledger.get("slot_acquire_time"), "slot_release_time": ledger.get("slot_release_time"), "post_fsp_sha256": ledger.get("post_fsp_sha256"), "quality": quality})
        if not ok:
            atomic(EVID / "controller_status.json", {"task_id": TASK, "state": "NP_K6_M10C_NEG0378_P_QUALITY_GATE_FAIL_S_NOT_ENTERED" if case_id == CASES[0][0] else "NP_K6_M10C_PARTIAL_NEG0378_ANGULAR_HF_REVIEW_REQUIRED", "terminal_case": case_id, "completed": completed, "solver_calls": sum(int(x["run_invocation_count"]) for x in completed), "entered_total": sum(int(x["run_invocation_count"]) for x in completed), "S_entered": any(x["case_id"] == CASES[1][0] and x["entered"] for x in completed), "finished_utc": now()})
            return
    atomic(EVID / "controller_status.json", {"task_id": TASK, "state": "COMPLETE", "completed": completed, "solver_calls": sum(int(x["run_invocation_count"]) for x in completed), "entered_total": sum(int(x["run_invocation_count"]) for x in completed), "p_s_overlap_duration_s": 0, "peak_local_active_fdtd": 1, "finished_utc": now()})
    atomic(EVID / "run_decision.json", {"classification": "NP_K6_M10C_ALT1_NEG0378_PS_ANGULAR_HF_COMPLETE_M11_CALIBRATION_READY", "P_pass": True, "S_pass": True, "solver_entered_total": 2, "minus_0482_reused": False, "control0_started": False})
    event("BATCH_COMPLETE", completed=completed)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        atomic(EVID / "controller_status.json", {"task_id": TASK, "state": "HARD_GATE", "error": repr(exc), "traceback": traceback.format_exc(), "finished_utc": now()})
        event("HARD_GATE", error=repr(exc))
        raise
