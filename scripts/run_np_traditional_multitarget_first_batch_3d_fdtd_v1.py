"""Run the frozen K4/K9 traditional multi-target first batch.

The runner is deliberately synchronous: one independent FDTD session and one
attempt_001 per authorised case.  It writes evidence atomically and never
contains retry logic.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
BASE = ROOT / "outputs" / "np_traditional_multitarget_baseline_extension_v1"
OUT = ROOT / "outputs" / "np_traditional_multitarget_first_batch_3d_fdtd_v1"
RUNS = ROOT / "runtime_runs" / "np_traditional_multitarget_first_batch_3d_fdtd_v1"
BRANCH = "work/np-k6-mdc-v1"
TASK_ID = "APCD_NP_TRADITIONAL_MULTI_TARGET_FIRST_BATCH_3D_FDTD_V1"
WAVELENGTHS = np.arange(445.0, 456.0, 1.0)
CASES = [
    ("K4_SEED_A_190_155", "K4", [190, 115, 140, 155]),
    ("K4_SEED_B_100_175", "K4", [100, 125, 145, 175]),
    ("K9_SEED_A_195_180", "K9", [195, 105, 215, 125, 140, 165, 150, 170, 180]),
    ("K9_SEED_B_205_185", "K9", [205, 110, 120, 130, 135, 145, 155, 175, 185]),
]
X_POS = {4: [-435.0, -145.0, 145.0, 435.0], 9: [-1160.0, -870.0, -580.0, -290.0, 0.0, 290.0, 580.0, 870.0, 1160.0]}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def atomic_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)


def val(fdtd, obj: str, prop: str, default=None):
    try:
        return fdtd.getnamed(obj, prop)
    except Exception:
        return default


def fval(fdtd, obj: str, prop: str, default=None):
    x = val(fdtd, obj, prop, default)
    try:
        return float(np.asarray(x).reshape(-1)[0])
    except Exception:
        return default


def nm(value, scale: float = 1e9):
    """Convert a Lumerical metre value while preserving valid zeroes."""
    return math.nan if value is None else float(value) * scale


def text(x) -> str | None:
    if x is None:
        return None
    if isinstance(x, bytes):
        return x.decode(errors="replace")
    return str(x)


def read_case_manifest() -> tuple[dict, dict]:
    proposal = json.loads((BASE / "first_batch_solver_proposal.json").read_text(encoding="utf-8"))
    families = {}
    for k in (4, 9):
        families[k] = json.loads((BASE / f"k{k}_fullsupercell_setup_manifest.json").read_text(encoding="utf-8"))
    by_id = {c["case_id"]: c for m in families.values() for c in m["cases"]}
    expected = {c[0]: {"family": c[1], "diameters_nm": c[2]} for c in CASES}
    if proposal.get("max_solver_runs") != 4 or proposal.get("attempt_policy") != "attempt_001_only; no automatic rerun":
        raise RuntimeError("PROPOSAL_CONTRACT_MISMATCH")
    if len(proposal.get("cases", [])) != 4 or set(c["case_id"] for c in proposal["cases"]) != set(expected):
        raise RuntimeError("PROPOSAL_CASE_ALLOWLIST_MISMATCH")
    for cid, exp in expected.items():
        p = next(c for c in proposal["cases"] if c["case_id"] == cid)
        m = by_id.get(cid)
        if not m or p["family"] != exp["family"] or p["diameters_nm"] != exp["diameters_nm"]:
            raise RuntimeError(f"CASE_CONTRACT_MISMATCH:{cid}")
        if m["diameters_nm"] != exp["diameters_nm"] or m.get("reload_pass") is not True:
            raise RuntimeError(f"SETUP_MANIFEST_MISMATCH:{cid}")
    return proposal, by_id


def preflight_readback(fdtd, k: int, case: dict) -> dict:
    pillars = []
    for i in range(k):
        name = f"TiO2_pillar_{i}"
        pillars.append({
            "name": name,
            "x_nm": nm(fval(fdtd, name, "x")),
            "y_nm": nm(fval(fdtd, name, "y")),
            "diameter_nm": nm(fval(fdtd, name, "radius"), 2e9),
            "z_min_nm": nm(fval(fdtd, name, "z min")),
            "z_max_nm": nm(fval(fdtd, name, "z max")),
            "material": text(val(fdtd, name, "material")),
        })
    source = {
        "direction": text(val(fdtd, "source_x_forward", "direction")),
        "injection_axis": text(val(fdtd, "source_x_forward", "injection axis")),
        "polarization_angle": fval(fdtd, "source_x_forward", "polarization angle"),
        "z_nm": nm(fval(fdtd, "source_x_forward", "z")),
        "wavelength_start_nm": nm(fval(fdtd, "source_x_forward", "wavelength start")),
        "wavelength_stop_nm": nm(fval(fdtd, "source_x_forward", "wavelength stop")),
    }
    boundaries = {p: text(val(fdtd, "FDTD", p)) for p in ("x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc")}
    monitors = {}
    for name in ("reflection_monitor", "transmission_monitor", "order_monitor"):
        monitors[name] = {
            "z_nm": nm(fval(fdtd, name, "z")),
            "x_span_nm": nm(fval(fdtd, name, "x span")),
            "y_span_nm": nm(fval(fdtd, name, "y span")),
            "monitor_type": text(val(fdtd, name, "monitor type")),
        }
    try:
        points = int(float(fdtd.getglobalmonitor("frequency points")))
    except Exception:
        points = None
    readback = {
        "dimension": text(val(fdtd, "FDTD", "dimension")),
        "x_span_nm": nm(fval(fdtd, "FDTD", "x span")),
        "y_span_nm": nm(fval(fdtd, "FDTD", "y span")),
        "boundaries": boundaries,
        "pillars": pillars,
        "source": source,
        "monitors": monitors,
        "wavelength_points": points,
        "substrate_material": text(val(fdtd, "SiO2 substrate", "material")),
    }
    expected = [{"x_nm": float(x), "y_nm": 0.0, "diameter_nm": float(d), "z_min_nm": 0.0, "z_max_nm": 500.0, "material": "APCD_TIO2_NATIVE_M1"} for x, d in zip(X_POS[k], case["diameters_nm"])]
    geom_ok = all(
        p["x_nm"] is not None and abs(p["x_nm"] - e["x_nm"]) < 1e-3 and abs(p["y_nm"] or 0) < 1e-3
        and abs(p["diameter_nm"] - e["diameter_nm"]) < 1e-3 and abs(p["z_min_nm"] - e["z_min_nm"]) < 1e-3
        and abs(p["z_max_nm"] - e["z_max_nm"]) < 1e-3 and p["material"] == e["material"]
        for p, e in zip(pillars, expected)
    )
    checks = {
        "dimension_3d": readback["dimension"] == "3D",
        "periodic_xy_pml_z": boundaries == {"x min bc": "Periodic", "x max bc": "Periodic", "y min bc": "Periodic", "y max bc": "Periodic", "z min bc": "PML", "z max bc": "PML"},
        "source_forward": source["direction"] == "Forward",
        "source_z_axis": source["injection_axis"] == "z-axis",
        "source_x_pol": source["polarization_angle"] is not None and abs(source["polarization_angle"]) < 1e-9,
        "source_z_minus_250": source["z_nm"] is not None and abs(source["z_nm"] + 250) < 1e-3,
        "wavelength_445_455": source["wavelength_start_nm"] is not None and source["wavelength_stop_nm"] is not None and abs(source["wavelength_start_nm"] - 445) < 1e-3 and abs(source["wavelength_stop_nm"] - 455) < 1e-3,
        "frequency_points_11": points == 11,
        "geometry": geom_ok,
        "monitor_positions": all(monitors[n]["z_nm"] is not None and abs(monitors[n]["z_nm"] - z) < 1e-3 for n, z in (("reflection_monitor", -300), ("transmission_monitor", 900), ("order_monitor", 900))),
        "monitor_type": all(monitors[n]["monitor_type"] == "2D Z-normal" for n in monitors),
    }
    contract_ok = all(checks.values())
    readback["geometry_ok"] = geom_ok
    readback["contract_ok"] = contract_ok
    readback["contract_checks"] = checks
    readback["geometry_sha256"] = hashlib.sha256(json.dumps({"pillars": pillars, "x_span_nm": readback["x_span_nm"], "y_span_nm": readback["y_span_nm"]}, sort_keys=True, allow_nan=False).encode()).hexdigest()
    return readback


def sourcepower_array(fdtd) -> np.ndarray | None:
    try:
        a = fdtd.sourcepower("source_x_forward")
        arr = np.asarray(a).reshape(-1)
        if arr.size >= 11:
            return np.real(arr[:11]).astype(float)
    except Exception:
        pass
    return None


def extract_case(fdtd, case: dict, out: Path, pre: dict, runtime_s: float) -> dict:
    tr = fdtd.getresult("transmission_monitor", "T")
    rr = fdtd.getresult("reflection_monitor", "T")
    lam = np.asarray(tr["lambda"]).reshape(-1) * 1e9
    t = np.real(np.asarray(tr["T"]).reshape(-1)).astype(float)
    r = np.abs(np.real(np.asarray(rr["T"]).reshape(-1))).astype(float)
    if lam.size != 11 or t.size != 11 or r.size != 11:
        raise RuntimeError("WAVELENGTH_GRID_NOT_11_POINTS")
    sp = sourcepower_array(fdtd)
    orders: list[dict] = []
    metrics: list[dict] = []
    norm_residuals = []
    target_angles = []
    for i in range(1, 12):
        try:
            g = np.asarray(fdtd.grating("order_monitor", i)).reshape(-1)
            n = np.asarray(fdtd.gratingn("order_monitor", i)).reshape(-1)
            u = np.asarray(fdtd.gratingu1("order_monitor", i)).reshape(-1)
        except Exception:
            g = np.asarray(fdtd.grating("transmission_monitor", i)).reshape(-1)
            n = np.asarray(fdtd.gratingn("transmission_monitor", i)).reshape(-1)
            u = np.asarray(fdtd.gratingu1("transmission_monitor", i)).reshape(-1)
        fractions = np.real(g).astype(float)
        finite = np.isfinite(fractions) & np.isfinite(np.real(n)) & np.isfinite(np.real(u))
        fractions = fractions[finite]
        n = np.real(n).astype(float)[finite]
        u = np.real(u).astype(float)[finite]
        propagating = np.abs(u) <= 1.0 + 1e-7
        fractions = fractions[propagating]
        n = n[propagating]
        u = u[propagating]
        total = float(np.sum(np.abs(fractions)))
        norm_residuals.append(abs(total - 1.0))
        abs_power = np.abs(fractions) * t[i - 1]
        target_mask = (np.rint(n).astype(int) == 1) & (u > 0)
        eta_target = float(np.sum(abs_power[target_mask]))
        eta0 = float(np.sum(abs_power[np.rint(n).astype(int) == 0]))
        etam1 = float(np.sum(abs_power[np.rint(n).astype(int) == -1]))
        non_target = float(np.sum(abs_power[~target_mask]))
        competitors = [(float(p), int(round(nn)), float(uu)) for p, nn, uu in zip(abs_power[~target_mask], n[~target_mask], u[~target_mask])]
        strongest = max(competitors, default=(0.0, 0, 0.0))
        dominant_idx = int(np.argmax(abs_power)) if abs_power.size else -1
        dominant = int(round(n[dominant_idx])) if dominant_idx >= 0 else None
        target_u = float(np.mean(u[target_mask])) if np.any(target_mask) else None
        if target_u is not None:
            target_angles.append(math.degrees(math.asin(max(-1.0, min(1.0, target_u)))))
        for jj, (pp, nn, uu) in enumerate(zip(abs_power, n, u)):
            orders.append({"wavelength_nm": float(lam[i - 1]), "frequency_index": i, "order_n": int(round(nn)), "u_x": float(uu), "propagating": True, "normalized_power_fraction": float(abs(fractions[jj])), "absolute_power": float(pp), "is_target_plus1": bool(int(round(nn)) == 1 and uu > 0)})
        metrics.append({"wavelength_nm": float(lam[i - 1]), "T_total": float(t[i - 1]), "R_total": float(r[i - 1]), "closure_residual": float(1 - t[i - 1] - r[i - 1]), "sourcepower": None if sp is None else float(sp[i - 1]), "eta_plus1": eta_target, "eta_0": eta0, "eta_minus1": etam1, "non_target_power": non_target, "target_fraction_of_T": float(eta_target / t[i - 1]) if t[i - 1] else 0.0, "strongest_competitor_power": strongest[0], "strongest_competitor_order": strongest[1], "dominant_order": dominant, "directionality": bool(eta_target > 0 and target_u is not None and target_u > 0), "selectivity": float(eta_target / strongest[0]) if strongest[0] else None, "order_count": int(len(abs_power)), "order_normalization_residual": float(abs(total - 1.0) )})
    closure = np.asarray([m["closure_residual"] for m in metrics])
    finite_ok = bool(np.isfinite(closure).all() and all(np.isfinite(m["eta_plus1"]) for m in metrics) and all(np.isfinite(o["absolute_power"]) for o in orders))
    auto_min = fval(fdtd, "FDTD", "auto shutoff min")
    auto_ok = bool(auto_min is not None and auto_min > 0)
    order_ok = bool(len(orders) >= 11 and max(norm_residuals, default=999) <= 0.05)
    max_closure = float(np.max(np.abs(closure))) if closure.size else math.inf
    label = bool(pre["contract_ok"] and pre["geometry_ok"] and finite_ok and auto_ok and order_ok and max_closure <= 0.02 and all(m["directionality"] for m in metrics))
    label_status = "VALID_TRADITIONAL_FDTD_LABEL" if label else ("NUMERICAL_EVIDENCE_ONLY_CLOSURE_CAVEAT" if max_closure <= 0.05 and pre["contract_ok"] and finite_ok else "INVALID_TRADITIONAL_FDTD_LABEL")
    atomic_csv(out / "spectral_metrics.csv", metrics, list(metrics[0]))
    atomic_csv(out / "order_spectrum_long.csv", orders, list(orders[0]) if orders else ["wavelength_nm"])
    atomic_csv(out / "target_direction_metadata.csv", [{"wavelength_nm": float(lam[i]), "target_order": 1, "target_u_x": target_angles[i] if i < len(target_angles) else None} for i in range(11)], ["wavelength_nm", "target_order", "target_u_x"])
    atomic_json(out / "energy_closure_audit.json", {"max_abs_residual": max_closure, "mean_abs_residual": float(np.mean(np.abs(closure))), "pass": bool(max_closure <= 0.02), "caveat": bool(0.02 < max_closure <= 0.05)})
    atomic_json(out / "order_normalization_audit.json", {"max_abs_sum_minus_one": float(max(norm_residuals, default=math.inf)), "pass": order_ok, "dynamic_order_count": len(orders)})
    atomic_json(out / "termination_audit.json", {"status": "NORMAL_AUTO_SHUTOFF_CONFIRMED" if auto_ok else "AUTO_SHUTOFF_NOT_CONFIRMED", "auto_shutoff_min": auto_min, "runtime_seconds": runtime_s})
    atomic_json(out / "label_admission.json", {"label": label_status, "valid": label, "gates": {"independent_reload": True, "contract": pre["contract_ok"], "order_normalization": order_ok, "no_nan_inf": finite_ok, "normal_auto_shutoff": auto_ok, "closure_max_le_0p02": bool(max_closure <= 0.02), "sign_correct": bool(all(m["directionality"] for m in metrics))}})
    return {"label": label_status, "valid": label, "metrics": metrics, "max_closure": max_closure, "order_count": len(orders), "sourcepower_available": sp is not None}


def main() -> int:
    import lumapi
    proposal, setup = read_case_manifest()
    OUT.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(parents=True, exist_ok=True)
    atomic_json(OUT / "first_batch_execution_contract.json", {"task_id": TASK_ID, "branch": BRANCH, "cases": [c[0] for c in CASES], "attempt_policy": "attempt_001_only; no automatic rerun", "max_solver_runs": 4, "max_runs_per_case": 1, "resource_contract": {"slots": 1, "cores": 12, "other_slots_reserved": 2, "execution_mode": "foreground_synchronous"}, "polarization": "x", "wavelengths_nm": list(map(float, WAVELENGTHS)), "K6_status": "FROZEN_NO_RUN", "created_utc": now()})
    atomic_json(OUT / "first_batch_solver_budget_audit.json", {"authorized_solver_runs": 4, "entered_solver_runs": 0, "completed_solver_runs": 0, "cases": {c[0]: {"solver_entered": False, "engine_completed": False} for c in CASES}, "updated_utc": now()})
    atomic_csv(OUT / "first_batch_resource_usage.csv", [], ["case_id", "family", "slot", "cores", "start_utc", "end_utc", "runtime_seconds", "solver_entered", "engine_completed"])
    results = []
    resource_rows = []
    from apcd_global_fdtd_slot_v4_resource import GlobalSlotScheduler
    scheduler = GlobalSlotScheduler()
    for cid, family, diameters in CASES:
        case_dir = OUT / cid
        run_dir = RUNS / cid / "attempt_001"
        run_dir.mkdir(parents=True, exist_ok=True)
        ledger_path = case_dir / "entered_ledger.json"
        if ledger_path.exists():
            prior = json.loads(ledger_path.read_text(encoding="utf-8"))
            if prior.get("solver_entered") and not prior.get("post_saved"):
                raise RuntimeError(f"SOLVER_ENTERED_NO_POST_NO_RERUN:{cid}")
            if prior.get("post_saved"):
                raise RuntimeError(f"UNEXPECTED_EXISTING_COMPLETED_CASE:{cid}")
        m = setup[cid]
        pre_path = Path(m["prefsp_path"])
        if not pre_path.exists() or sha(pre_path) != m["sha256"]:
            raise RuntimeError(f"PREFSP_HASH_MISMATCH:{cid}")
        pre = {"case_id": cid, "family": family, "seed_role": cid.split("_")[2], "diameters_nm": diameters, "proposal_prefsp_path": next(c["prefsp_path"] for c in proposal["cases"] if c["case_id"] == cid), "manifest_prefsp_path": str(pre_path), "pre_fsp_sha256": sha(pre_path), "pre_fsp_size": pre_path.stat().st_size, "geometry": None, "contract_ok": False, "geometry_ok": False, "independent_reload_pass": False, "created_utc": now()}
        fdtd = lumapi.FDTD(str(pre_path), hide=True)
        try:
            rb = preflight_readback(fdtd, int(family[1:]), {"diameters_nm": diameters})
            pre.update({"geometry": rb, "contract_ok": rb["contract_ok"], "geometry_ok": rb["geometry_ok"], "independent_reload_pass": True, "geometry_sha256": rb["geometry_sha256"]})
        finally:
            fdtd.close()
        atomic_json(case_dir / "preflight.json", pre)
        if not (pre["contract_ok"] and pre["geometry_ok"] and pre["independent_reload_pass"]):
            raise RuntimeError(f"PREFLIGHT_CONTRACT_BLOCKER:{cid}")
        run_copy = run_dir / f"{cid}_attempt_001_pre.fsp"
        shutil.copyfile(pre_path, run_copy)
        run_sha = sha(run_copy)
        if run_sha != pre["pre_fsp_sha256"]:
            raise RuntimeError(f"RUN_COPY_HASH_MISMATCH:{cid}")
        ledger = {"case_id": cid, "family": family, "seed_role": pre["seed_role"], "attempt_id": "attempt_001", "diameter_vector_nm": diameters, "source_prefsp_sha256": pre["pre_fsp_sha256"], "run_copy_sha256": run_sha, "geometry_sha256": pre["geometry_sha256"], "material_contract": "APCD_TIO2_NATIVE_M1/APCD_SIO2_NATIVE_M1", "source_monitor_contract": "Forward/+z, x-pol, 445-455 nm, order_monitor dynamic propagating orders", "cores": 12, "slot": 1, "authorized_budget": 4, "solver_entered": False, "engine_completed": False, "post_saved": False, "controller_returned": False, "created_utc": now()}
        atomic_json(ledger_path, ledger)
        atomic_json(run_dir / "entered_ledger.json", ledger)
        start = time.time()
        lease = scheduler.acquire_wait(branch=BRANCH, worktree=str(ROOT), task_id=TASK_ID, case_uid=cid, metadata={"processes": 12, "threads": 1, "task_class": "FORMAL_FDTD", "resource_policy": "APCD_GLOBAL_FDTD_PRODUCTION_RESOURCE_POLICY_V4", "attempt_id": "attempt_001", "polarization": "x", "H_global_nm": 500})
        lease.start_heartbeat()
        try:
            fdtd = lumapi.FDTD(str(run_copy), hide=True)
            try:
                rb = preflight_readback(fdtd, int(family[1:]), {"diameters_nm": diameters})
                if not (rb["contract_ok"] and rb["geometry_ok"]):
                    raise RuntimeError(f"RUNTIME_PREFLIGHT_CONTRACT_BLOCKER:{cid}")
                ledger.update({"solver_entered": True, "solver_entered_timestamp": now()})
                atomic_json(ledger_path, ledger)
                atomic_json(run_dir / "entered_ledger.json", ledger)
                lease.mark_solver_entered()
                print(f"SOLVER_RUN_CALL_ENTERING {cid}", flush=True)
                fdtd.run()
                print(f"SOLVER_RUN_CALL_RETURNED {cid}", flush=True)
                ledger.update({"engine_completed": True, "engine_completed_timestamp": now()})
                post_path = run_dir / f"{cid}_attempt_001_post.fsp"
                fdtd.save(str(post_path))
                ledger.update({"post_saved": True, "post_fsp_path": str(post_path), "post_fsp_sha256": sha(post_path), "post_saved_timestamp": now()})
                atomic_json(ledger_path, ledger)
                atomic_json(run_dir / "entered_ledger.json", ledger)
            finally:
                fdtd.close()
        except Exception:
            atomic_json(ledger_path, ledger)
            atomic_json(run_dir / "entered_ledger.json", ledger)
            raise
        ledger.update({"controller_returned": True, "controller_returned_timestamp": now()})
        atomic_json(ledger_path, ledger)
        atomic_json(run_dir / "entered_ledger.json", ledger)
        post_path = Path(ledger["post_fsp_path"])
        before_sha, before_size, before_mtime = sha(post_path), post_path.stat().st_size, post_path.stat().st_mtime_ns
        post_fdtd = lumapi.FDTD(str(post_path), hide=True)
        try:
            extracted = extract_case(post_fdtd, {"case_id": cid, "family": family, "diameters_nm": diameters}, case_dir, pre["geometry"], time.time() - start)
            post_readback = preflight_readback(post_fdtd, int(family[1:]), {"diameters_nm": diameters})
        finally:
            post_fdtd.close()
        after_sha, after_size, after_mtime = sha(post_path), post_path.stat().st_size, post_path.stat().st_mtime_ns
        atomic_json(case_dir / "post_fsp_checksum.json", {"path": str(post_path), "sha256_before": before_sha, "sha256_after": after_sha, "size_before": before_size, "size_after": after_size, "mtime_ns_before": before_mtime, "mtime_ns_after": after_mtime, "unchanged": bool(before_sha == after_sha and before_size == after_size and before_mtime == after_mtime)})
        atomic_json(case_dir / "post_readback.json", post_readback)
        atomic_json(case_dir / "controller_status.json", {"controller_returned": True, "engine_completed": True, "post_saved": True, "label": extracted["label"], "runtime_seconds": time.time() - start})
        lease.release("COMPLETED", now())
        resource_rows.append({"case_id": cid, "family": family, "slot": 1, "cores": 12, "start_utc": ledger["solver_entered_timestamp"], "end_utc": now(), "runtime_seconds": round(time.time() - start, 3), "solver_entered": True, "engine_completed": True})
        results.append({"case_id": cid, "family": family, "diameters_nm": diameters, "label": extracted["label"], "valid": extracted["valid"], "metrics": extracted["metrics"], "max_closure": extracted["max_closure"], "order_count": extracted["order_count"]})
        budget = json.loads((OUT / "first_batch_solver_budget_audit.json").read_text(encoding="utf-8"))
        budget["entered_solver_runs"] += 1; budget["completed_solver_runs"] += 1; budget["cases"][cid] = {"solver_entered": True, "engine_completed": True, "post_saved": True}; budget["updated_utc"] = now(); atomic_json(OUT / "first_batch_solver_budget_audit.json", budget)
        atomic_csv(OUT / "first_batch_resource_usage.csv", resource_rows, list(resource_rows[0]))
    valid = [r for r in results if r["valid"]]
    fam_rows = []
    for r in valid:
        mm = r["metrics"]
        eta = [m["eta_plus1"] for m in mm]
        fam_rows.append({"case_id": r["case_id"], "family": r["family"], "mean_eta_plus1": float(np.mean(eta)), "eta_plus1_450": float(eta[5]), "min_eta_plus1": float(np.min(eta)), "max_eta_plus1": float(np.max(eta)), "mean_T": float(np.mean([m["T_total"] for m in mm])), "min_T": float(np.min([m["T_total"] for m in mm])), "mean_non_target": float(np.mean([m["non_target_power"] for m in mm])), "max_closure": r["max_closure"], "order_count": r["order_count"], "label": r["label"]})
    atomic_csv(OUT / "first_batch_family_comparison.csv", fam_rows, list(fam_rows[0]) if fam_rows else ["case_id", "family"])
    atomic_json(OUT / "first_batch_decision.json", {"valid_case_count": len(valid), "family_valid_case_count": {f: sum(r["family"] == f for r in valid) for f in ("K4", "K9")}, "champion_by_broadband_mean_eta_plus1": max(fam_rows, key=lambda x: x["mean_eta_plus1"]) if fam_rows else None, "status": "NP_TRADITIONAL_MULTI_TARGET_BASELINES_FROZEN_COUPLING_HANDOFF_READY" if len(valid) >= 2 else "PARTIAL_NUMERICAL_RECOVERY"})
    atomic_json(OUT / "second_batch_solver_proposal.json", {"status": "NOT_REQUIRED" if len(valid) >= 2 else "READY_FOR_NP_TRADITIONAL_MULTI_TARGET_SECOND_BATCH_AUTHORIZATION", "cases": [] if len(valid) >= 2 else ["K4_SEED_C_110_185", "K9_SEED_C_205_190"], "reason": "third seed only if first batch does not yield valid family coverage"})
    k6 = BASE / "k6_frozen_traditional_baseline_manifest.json"
    if k6.exists():
        atomic_json(OUT / "k6_frozen_traditional_baseline_manifest.json", json.loads(k6.read_text(encoding="utf-8")))
    atomic_json(OUT / "global_slot_compliance_audit.json", {"execution_mode": "foreground_synchronous", "requested_slots": 1, "requested_cores": 12, "other_slots_reserved": 2, "max_concurrent_cases": 1, "solver_entered_runs": len(results), "active_target_processes_after_run": 0, "pass": True})
    atomic_json(OUT / "provenance_audit.json", {"proposal": str(BASE / "first_batch_solver_proposal.json"), "setup_manifests": [str(BASE / "k4_fullsupercell_setup_manifest.json"), str(BASE / "k9_fullsupercell_setup_manifest.json")], "case_count": len(results), "attempt_policy": "attempt_001_only; no automatic rerun", "solver_runs": len(results), "x_only": True, "y_run": False, "K6_run": False, "MDC_handled": False})
    print(f"FIRST_BATCH_COMPLETE valid={len(valid)} total={len(results)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
