from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/stage_h1f2_k6_frontier_level1"
MANIFEST_PATH = REPORT / "h1f2_candidate_manifest.json"
CASE_ROOT = ROOT / "outputs/lp_h1f2_k6_frontier_level1/cases"
ACCOUNTING_PATH = REPORT / "h1f2_solver_accounting.json"
REGISTRY_PATH = Path(r"D:\project\apcd_global_fdtd_slot_registry_v1.json")
BRANCH = "work/lp-global-h-manifold-v1"
GRID = [450.0 + 0.5 * i for i in range(9)]
POLS = ("x", "y")
PROCESSES = 4
THREADS = 1


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


H1D1 = load_module(ROOT / "scripts/lp_h1d1_pure_detour_k6.py", "h1d1_reference")
SCHEDULER = load_module(ROOT / "scripts/apcd_global_fdtd_slot_v1.py", "h1f1_scheduler")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()


def sha256_obj(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha256_file(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def candidates(manifest_data):
    value = manifest_data["candidates"]
    return list(value.values()) if isinstance(value, dict) else value


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or ["status"])
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def manifest():
    m = read_json(MANIFEST_PATH)
    if m.get("status") != "FROZEN_READY_FOR_SOLVER" or m.get("candidate_count") != 3:
        raise RuntimeError("HARD_GATE_MANIFEST_NOT_FROZEN")
    if m.get("processes") != PROCESSES or m.get("threads") != THREADS or m.get("max_new_formal_cases") != 6:
        raise RuntimeError("HARD_GATE_SOLVER_BUDGET_DRIFT")
    if m.get("wavelength_grid_nm") != GRID or m.get("ml_admitted") is not False:
        raise RuntimeError("HARD_GATE_MANIFEST_CONTRACT_DRIFT")
    if len(candidates(m)) != 3 or any(not c.get("no_position_shift") for c in candidates(m)):
        raise RuntimeError("HARD_GATE_CANDIDATE_CONTRACT_DRIFT")
    return m


def live_accounting():
    live = SCHEDULER.live_job_snapshot()
    return {
        "active_fdtd_jobs": live.get("active_fdtd_jobs", 0),
        "active_rcwa_jobs": live.get("active_rcwa_jobs", 0),
        "unknown_solver_jobs": live.get("unknown_solver_jobs", []),
        "lp_active_fdtd_jobs": sum(1 for j in live.get("jobs", []) if j.get("solver_type_token") == "FDTD" and str(j.get("branch_token", "")) == BRANCH),
        "jobs": live.get("jobs", []),
        "processes_per_job": PROCESSES,
        "threads_per_job": THREADS,
    }


def build(fdtd, candidate, pol):
    from metasurface.lumerical_native_materials import ensure_apcd_native_materials, get_lumerical_material_name
    nm = 1e-9
    px, py = candidate["P_supercell_nm"] * nm, candidate["P_y_nm"] * nm
    h = candidate["H_global_nm"] * nm
    fdtd.switchtolayout()
    fdtd.deleteall()
    ensure_apcd_native_materials(fdtd)
    material = get_lumerical_material_name(candidate["material"])
    fdtd.addfdtd()
    for key, value in (("dimension", "3D"), ("x", 0.0), ("y", 0.0), ("x span", px), ("y span", py), ("z min", -500 * nm), ("z max", 1200 * nm), ("x min bc", "Periodic"), ("x max bc", "Periodic"), ("y min bc", "Periodic"), ("y max bc", "Periodic"), ("z min bc", "PML"), ("z max bc", "PML"), ("mesh accuracy", 2), ("simulation time", 1000e-15), ("background material", "<Object defined dielectric>"), ("index", 1.0)):
        fdtd.set(key, value)
    fdtd.setglobalmonitor("frequency points", len(GRID))
    fdtd.setglobalmonitor("use wavelength spacing", True)
    fdtd.setglobalmonitor("use source limits", True)
    for site, (geo, pos) in enumerate(zip(candidate["local_geometries"], candidate["site_positions_nm"])):
        xbase = float(pos["x_nm"]) - candidate["P_supercell_nm"] / 2.0
        for suffix, cx, cy, xs, ys, rot in (("pillar_1", geo["J1_center_x_nm"], geo["J1_center_y_nm"], geo["J1_side_nm"], geo["J1_side_nm"], geo.get("J1_rotation_deg", 0.0)), ("pillar_2", geo["J2_center_x_nm"], geo["J2_center_y_nm"], geo["J2_length_nm"], geo["J2_width_nm"], geo.get("J2_rotation_deg", 0.0))):
            fdtd.addrect()
            fdtd.set("name", f"{candidate['candidate_uid']}_site_{site}_{suffix}")
            fdtd.set("x", (xbase + float(cx)) * nm)
            fdtd.set("y", (float(pos["y_nm"]) + float(cy)) * nm)
            fdtd.set("x span", float(xs) * nm)
            fdtd.set("y span", float(ys) * nm)
            fdtd.set("z min", 0.0)
            fdtd.set("z max", h)
            fdtd.set("first axis", "z")
            fdtd.set("rotation 1", float(rot))
            fdtd.set("material", material)
    fdtd.addplane()
    fdtd.set("name", "source")
    fdtd.set("injection axis", "z")
    fdtd.set("direction", "Forward")
    fdtd.set("x", 0.0)
    fdtd.set("y", 0.0)
    fdtd.set("x span", px)
    fdtd.set("y span", py)
    fdtd.set("z", -250 * nm)
    fdtd.set("wavelength start", GRID[0] * nm)
    fdtd.set("wavelength stop", GRID[-1] * nm)
    fdtd.set("polarization angle", 0 if pol == "x" else 90)
    fdtd.addpower()
    fdtd.set("name", "T")
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x", 0.0)
    fdtd.set("y", 0.0)
    fdtd.set("x span", px)
    fdtd.set("y span", py)
    fdtd.set("z", 1000 * nm)
    fdtd.set("override global monitor settings", True)
    fdtd.set("use wavelength spacing", True)
    fdtd.set("frequency points", len(GRID))
    fdtd.set("use source limits", True)
    return {"material_name": material, "polarization": pol, "wavelength_grid_nm": GRID, "supercell_nm": [candidate["P_supercell_nm"], candidate["P_y_nm"]], "monitor_z_nm": 1000.0, "pillar_count": 12, "H_global_nm": candidate["H_global_nm"], "site_positions_nm": candidate["site_positions_nm"]}


def gate(fdtd, candidate, pol):
    from metasurface.lumerical_native_materials import get_lumerical_material_name
    material = get_lumerical_material_name(candidate["material"])
    vals = {"source_start_nm": float(fdtd.getnamed("source", "wavelength start")) * 1e9, "source_stop_nm": float(fdtd.getnamed("source", "wavelength stop")) * 1e9, "monitor_z_nm": float(fdtd.getnamed("T", "z")) * 1e9, "frequency_points": float(fdtd.getnamed("T", "frequency points"))}
    expected = {"source_start_nm": GRID[0], "source_stop_nm": GRID[-1], "monitor_z_nm": 1000.0, "frequency_points": 9.0}
    passed = all(abs(vals[k] - v) < 1e-7 for k, v in expected.items()) and pol in POLS and material == candidate["material"]
    return {"pass": bool(passed), "checks": vals, "expected": expected, "material_contract": material, "polarization": pol, "one_broadband_run_returns_all_9_points": True}


def extract(fdtd, pol):
    rows = H1D1.extract_orders(fdtd, pol)
    for row in rows:
        row["extraction_basis"] = "transverse Cartesian Ex,Ey from authoritative gratingvector; x/y input columns"
        row["target_order_convention"] = "order_n=+1, order_m=0 is physical +x supercell order"
    return rows


def identity(candidate, pol):
    return {"case_uid": f"H1F2_{candidate['candidate_uid']}_{pol}", "candidate_uid": candidate["candidate_uid"], "candidate_hash": candidate["candidate_hash"], "polarization": pol, "manifest_freeze_sha256": manifest()["freeze_sha256"], "wavelength_grid_nm": GRID, "solver_runs_for_spectrum": 1}


def update_accounting(case_uid, **changes):
    accounting = read_json(ACCOUNTING_PATH)
    cases = accounting.setdefault("cases", [])
    item = next((x for x in cases if x.get("case_uid") == case_uid), None)
    if item is None:
        item = {"case_uid": case_uid}
        cases.append(item)
    item.update(changes)
    accounting["entered_formal_cases"] = sum(bool(x.get("solver_entered")) for x in cases)
    accounting["accepted_formal_cases"] = sum(x.get("status") == "ACCEPTED" for x in cases)
    accounting["quarantine_cases"] = sum(bool(x.get("quarantined")) for x in cases)
    accounting["replay_cases"] = sum(bool(x.get("solver_replay")) for x in cases)
    write_json(ACCOUNTING_PATH, accounting)


def run_case(candidate, pol, scheduler, runtime):
    ident = identity(candidate, pol)
    case_dir = CASE_ROOT / ident["case_uid"] / "attempt_001"
    case_dir.mkdir(parents=True, exist_ok=True)
    provenance = case_dir / "attempt_provenance.json"
    checkpoint = case_dir / "checkpoint.json"
    if checkpoint.exists() and read_json(checkpoint).get("status") == "ACCEPTED":
        return read_json(checkpoint)
    if provenance.exists() and read_json(provenance).get("solver_entered") is True:
        result = {"status": "QUARANTINED_ENTERED_NO_REPLAY", "case_uid": ident["case_uid"], "solver_entered": True, "solver_replay": False}
        update_accounting(ident["case_uid"], status=result["status"], solver_entered=True, quarantined=True, solver_replay=False)
        return result
    record = {"schema": "H1F1_ATTEMPT_PROVENANCE_V1", "case_id": ident["case_uid"], "attempt_id": "attempt_001", "case_identity": ident, "case_identity_sha256": sha256_obj(ident), "physical_contract_sha256": candidate["candidate_hash"], "solver_entered": False, "entered_solver": False, "processes": PROCESSES, "threads": THREADS, "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "wavelength_grid_nm": GRID, "solver_runs_for_spectrum": 1}
    write_json(provenance, record)
    f = None
    lease = None
    try:
        f = runtime.lumapi.FDTD(hide=runtime.hide_gui)
        setup = build(f, candidate, pol)
        pre_fsp = case_dir / "case_pre.fsp"
        f.save(str(pre_fsp))
        record.update({"setup": setup, "pre_fsp_path": str(pre_fsp), "pre_fsp_sha256": sha256_file(pre_fsp), "status": "PREPARED"})
        f.close(); f = None
        write_json(provenance, record)
        lease = scheduler.acquire_wait(branch=BRANCH, worktree=str(ROOT), task_id="H1F1_K6_L0", case_uid=ident["case_uid"], pid=os.getpid(), metadata={"task_class": "H1F1_K6_COUPLING_AWARE_FORMAL_FDTD", "attempt_id": "attempt_001", "polarization": pol, "candidate_uid": candidate["candidate_uid"], "processes": PROCESSES, "threads": THREADS}, timeout_s=21600.0, poll_s=15.0)
        record.update({"slot_acquired": True, "slot_id": lease.slot_id, "admission_snapshot": lease.record.get("admission_snapshot"), "status": "SLOT_ACQUIRED"})
        lease.start_heartbeat(); write_json(provenance, record)
        f = runtime.lumapi.FDTD(hide=runtime.hide_gui); f.load(str(pre_fsp))
        config_gate = gate(f, candidate, pol)
        record.update({"configuration_gate": config_gate, "status": "PREFLIGHT_GATED"}); write_json(provenance, record)
        if not config_gate["pass"]:
            lease.release("QUARANTINED_PREFLIGHT_GATE"); lease = None
            record.update({"status": "QUARANTINED_PREFLIGHT_GATE", "quarantined": True}); update_accounting(ident["case_uid"], **record); return record
        entered = dt.datetime.now(dt.timezone.utc).isoformat()
        lease.mark_solver_entered(entered)
        record.update({"solver_entered": True, "entered_solver": True, "entered_utc": entered, "status": "ENTERED"})
        entry = {"case_id": ident["case_uid"], "attempt_id": "attempt_001", "solver_entered": True, "entered_solver": True, "entered_utc": entered, "pre_fsp_sha256": record["pre_fsp_sha256"], "physical_contract_sha256": candidate["candidate_hash"], "case_identity_sha256": sha256_obj(ident), "slot_id": lease.slot_id, "processes": PROCESSES, "threads": THREADS, "polarization": pol}
        write_json(provenance, record); update_accounting(ident["case_uid"], **record, solver_entry=entry)
        f.run()
        record["solver_complete"] = dt.datetime.now(dt.timezone.utc).isoformat()
        run_fsp = case_dir / "case_run.fsp"
        try:
            f.save(str(run_fsp)); record.update({"run_fsp_path": str(run_fsp), "run_fsp_sha256": sha256_file(run_fsp)})
        except Exception as exc:
            record["run_fsp_save_error"] = f"{type(exc).__name__}: {exc}"
        rows = extract(f, pol)
        lease.release("SOLVER_COMPLETED", record["solver_complete"]); lease = None
        result = {"schema": "H1F1_CASE_CHECKPOINT_V1", "status": "ACCEPTED", "case_uid": ident["case_uid"], "case_identity": ident, "case_identity_sha256": sha256_obj(ident), "candidate_uid": candidate["candidate_uid"], "polarization": pol, "solver_entered": True, "solver_replay": False, "setup": setup, "configuration_gate": config_gate, "rows": rows, "provenance_path": str(provenance), "attempt_id": "attempt_001"}
        write_json(checkpoint, result); record.update({"status": "ACCEPTED", "checkpoint_path": str(checkpoint), "checkpoint_sha256": sha256_file(checkpoint)})
        accepted_record = dict(record)
        accepted_record.update({"status": "ACCEPTED", "accepted": True, "solver_replay": False})
        update_accounting(ident["case_uid"], **accepted_record)
        return result
    except Exception as exc:
        record.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc(), "retained_data_status": "entered_evidence_preserved_no_replay" if record.get("solver_entered") else "pre_entry_failure_evidence_preserved"})
        update_accounting(ident["case_uid"], **record, solver_replay=False)
        return record
    finally:
        if lease is not None:
            try: lease.release("FAILED_ENTERED" if record.get("solver_entered") else "FAILED_PRE_ENTRY")
            except Exception: pass
        if f is not None:
            try: f.close()
            except Exception: pass
        write_json(provenance, record)


def preflight():
    m = manifest()
    snapshot = live_accounting()
    if snapshot["active_fdtd_jobs"] >= 2 or snapshot["lp_active_fdtd_jobs"] != 0 or snapshot["unknown_solver_jobs"]:
        raise RuntimeError(f"HARD_GATE_FDTD_ADMISSION:{snapshot}")
    return {"status": "READY", "manifest_freeze_sha256": m["freeze_sha256"], "candidate_count": len(m["candidates"]), "planned_formal_cases": 6, "live_solver_accounting": snapshot, "solver_entered": False}


def fullwave_rows(results):
    rows = []
    for result in results:
        for row in result.get("rows", []):
            rows.append({"candidate_uid": result["candidate_uid"], "case_uid": result["case_uid"], "polarization": result["polarization"], "solver_entered": result.get("solver_entered", False), "solver_replay": result.get("solver_replay", False), **row})
    return rows


def recover_entered(m):
    runtime = H1D1.load_runtime()
    recovered = []
    for candidate in candidates(m):
        for pol in POLS:
            case_uid = f"H1F2_{candidate['candidate_uid']}_{pol}"
            case_dir = CASE_ROOT / case_uid / "attempt_001"
            checkpoint = case_dir / "checkpoint.json"
            provenance = case_dir / "attempt_provenance.json"
            if checkpoint.exists() or not provenance.exists():
                continue
            record = read_json(provenance)
            if not record.get("solver_entered"):
                continue
            run_path = Path(record.get("run_fsp_path", ""))
            if not run_path.exists():
                raise RuntimeError(f"HARD_GATE_ENTERED_CASE_MISSING_RUN_FSP:{case_uid}")
            f = runtime.lumapi.FDTD(hide=runtime.hide_gui)
            try:
                f.load(str(run_path))
                rows = extract(f, pol)
            finally:
                try: f.close()
                except Exception: pass
            result = {"schema": "H1F1_CASE_CHECKPOINT_V1", "status": "ACCEPTED", "case_uid": case_uid, "case_identity": record["case_identity"], "case_identity_sha256": record["case_identity_sha256"], "candidate_uid": candidate["candidate_uid"], "polarization": pol, "solver_entered": True, "solver_replay": False, "rows": rows, "provenance_path": str(provenance), "attempt_id": record["attempt_id"], "postfsp_recovery": True}
            write_json(checkpoint, result)
            recovered_record = dict(record)
            recovered_record.update({"status": "ACCEPTED", "accepted": True, "postfsp_recovery": True, "solver_replay": False, "checkpoint_path": str(checkpoint), "checkpoint_sha256": sha256_file(checkpoint)})
            write_json(provenance, recovered_record)
            update_accounting(case_uid, **recovered_record)
            recovered.append(case_uid)
    return recovered


def postprocess(m):
    recovered = recover_entered(m)
    results = []
    for c in candidates(m):
        for pol in POLS:
            checkpoint = CASE_ROOT / f"H1F2_{c['candidate_uid']}_{pol}" / "attempt_001" / "checkpoint.json"
            if checkpoint.exists():
                result = read_json(checkpoint)
                update_accounting(result["case_uid"], status="ACCEPTED", solver_entered=True, accepted=True, solver_replay=False, checkpoint_path=str(checkpoint), checkpoint_sha256=sha256_file(checkpoint))
                results.append(result)
    rows = fullwave_rows(results)
    write_csv(REPORT / "h1f2_order_resolved_fullwave.csv", rows)
    jrows = []
    for c in candidates(m):
        for wavelength in GRID:
            xr = next((r for r in rows if r["candidate_uid"] == c["candidate_uid"] and r["polarization"] == "x" and r["wavelength_nm"] == wavelength and r["order_n"] == 1 and r["order_m"] == 0), None)
            yr = next((r for r in rows if r["candidate_uid"] == c["candidate_uid"] and r["polarization"] == "y" and r["wavelength_nm"] == wavelength and r["order_n"] == 1 and r["order_m"] == 0), None)
            if xr and yr:
                jrows.append({"candidate_uid": c["candidate_uid"], "wavelength_nm": wavelength, "basis": "Cartesian transverse Ex,Ey from gratingvector", "target_order_n": 1, "target_order_m": 0, "txx_re": xr["Ex_real"], "txx_im": xr["Ex_imag"], "tyx_re": xr["Ey_real"], "tyx_im": xr["Ey_imag"], "txy_re": yr["Ex_real"], "txy_im": yr["Ex_imag"], "tyy_re": yr["Ey_real"], "tyy_im": yr["Ey_imag"], "eta_x_plus1": xr["order_efficiency_source_norm"], "eta_y_plus1": yr["order_efficiency_source_norm"], "theta_deg": xr["theta_deg"]})
    write_csv(REPORT / "h1f2_k6_order_jones.csv", jrows)
    return {"status": "FULLWAVE_POSTPROCESSED", "accepted_cases": len(results), "fullwave_rows": len(rows), "jones_rows": len(jrows), "postfsp_recovered_cases": recovered}


def execute():
    m = manifest()
    if not preflight()["status"] == "READY": raise RuntimeError("HARD_GATE_PREFLIGHT")
    runtime = H1D1.load_runtime()
    scheduler = SCHEDULER.GlobalSlotScheduler(REGISTRY_PATH)
    results = []
    for c in candidates(m):
        for pol in POLS:
            result = run_case(c, pol, scheduler, runtime)
            results.append(result)
            print(json.dumps({"case": result.get("case_uid"), "status": result.get("status"), "solver_entered": result.get("solver_entered", False)}), flush=True)
    return postprocess(m)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "execute", "postprocess"))
    args = parser.parse_args()
    if args.mode == "preflight": print(json.dumps(preflight(), indent=2, default=str))
    elif args.mode == "postprocess": print(json.dumps(postprocess(manifest()), indent=2, default=str))
    else: print(json.dumps(execute(), indent=2, default=str))
