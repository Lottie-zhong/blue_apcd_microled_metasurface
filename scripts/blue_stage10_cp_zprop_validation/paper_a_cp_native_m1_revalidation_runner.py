from __future__ import annotations

import hashlib
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(r"D:\project\worktrees\blue_apcd_cp_stage10_bw2a")
sys.path.insert(0, r"D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1\scripts")
sys.path.insert(0, r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
import apcd_global_fdtd_slot_v1 as SLOT
import lumapi

STAGE = "PAPER_A_CP_CURRENT_NATIVE_BROADBAND_REVALIDATION_V1"
BRANCH = "work/cp/stage10-bw2a-dipole-smoke"
PARENT = ROOT / "outputs/stage10_cp_dipole_bw2a_no_dbr_microled_xline_center_spectral_run/_runtime_fsp_artifacts_not_for_git/setup/BW2_J1J2_D194_T90_PSI99_H525_450NM_setup_prepared_not_run.fsp"
M1 = Path(r"F:\wc_312\MDC_blue_oujizi_m\m_1.fsp")
REPORT = ROOT / "reports/stage_paper_a_cp_current_native_broadband_revalidation_v1"
RUNTIME = ROOT / "_runtime/stage_paper_a_cp_current_native_broadband_revalidation_v1"
SETUP = RUNTIME / "setup/CP_NATIVE_M1_CENTER_XY_setup_prepared_not_run.fsp"
PARENT_GROUP = "::model::CP_route_b2_D195_T90_uniform_patch_7x3_group::"
GAN_OBJECT = "::model::GaN_continuous_block_zprop_extends_into_bottom_PML"
X_SOURCE = "route_b2_x_dipole_zprop"
Y_SOURCE = "route_b2_y_dipole_zprop"
FIELD = "top_field_monitor_zprop"
POWER = "top_power_monitor_zprop"
TIO2 = "APCD_TIO2_NATIVE_M1"
GAN = "APCD_GAN_NATIVE_M1"
LO, HI, POINTS = 400.0, 500.0, 101
CONTRACT = {
    "stage": STAGE,
    "candidate": "BW2_J1J2_D194_T90_PSI99_H525",
    "materials": {"TiO2": TIO2, "GaN": GAN, "source_fsp": str(M1), "constant_index_fallback": False},
    "source_monitor": {"span_nm": [LO, HI], "points": POINTS, "formal_window_nm": [420.0, 480.0]},
    "dipole": {"position_nm": [0.0, 0.0, -200.0], "orientations": ["x", "y"], "combination": "incoherent_power"},
    "resources": {"processes": 4, "threads": 1},
    "reuse": {"mesh_accuracy": 3, "boundaries": "all six PML", "geometry_change": False},
    "basis": "R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2)",
}
CONTRACT_HASH = hashlib.sha256(json.dumps(CONTRACT, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def utc(): return datetime.now(timezone.utc).isoformat()
def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()
def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)
def setp(f, name, prop, value): f.select(name); f.set(prop, value)
def resource(f):
    errors = {}
    for key, value in [("processes", "4"), ("threads", "1")]:
        try: f.setresource("FDTD", 1, key, value)
        except Exception as exc: errors[key] = f"{type(exc).__name__}: {exc}"
    return {"pass": not errors, "expected": {"processes": 4, "threads": 1}, "errors": errors}
def clone_material(target, source, src_name, dst_name):
    data = np.asarray(source.getmaterial(src_name, "sampled 3d data"))
    mid = target.addmaterial("Sampled 3D data")
    target.setmaterial(mid, "name", dst_name)
    target.setmaterial(dst_name, "sampled 3d data", data)
    target.setmaterial(dst_name, "Mesh order", float(source.getmaterial(src_name, "Mesh order")))
    target.setmaterial(dst_name, "color", np.asarray(source.getmaterial(src_name, "color")))
    wl = 299792458.0 / data[:, 0].real * 1e9
    return {"source_name": src_name, "target_name": dst_name, "rows": int(len(data)), "lambda_nm": [float(wl.min()), float(wl.max())], "data_sha256": hashlib.sha256(data.tobytes()).hexdigest()}
def prepare():
    REPORT.mkdir(parents=True, exist_ok=True); (RUNTIME / "setup").mkdir(parents=True, exist_ok=True)
    src = lumapi.FDTD(str(M1), hide=True); f = lumapi.FDTD(str(PARENT), hide=True)
    try:
        f.switchtolayout()
        mats = {"TiO2": clone_material(f, src, "tio22", TIO2), "GaN": clone_material(f, src, "GaN", GAN)}
        for dimer in f.getobjectlist(PARENT_GROUP):
            for pillar in f.getobjectlist(dimer): setp(f, pillar, "material", TIO2)
        setp(f, GAN_OBJECT, "material", GAN)
        for name, enabled in [(X_SOURCE, 1), (Y_SOURCE, 0)]:
            for prop, value in [("enabled", enabled), ("x", 0.0), ("y", 0.0), ("z", -200e-9), ("wavelength start", LO * 1e-9), ("wavelength stop", HI * 1e-9)]: setp(f, name, prop, value)
        f.eval(f'setglobalmonitor("frequency points",{POINTS}); setglobalmonitor("use source limits",1);')
        rg = resource(f); f.save(str(SETUP))
        pillars = [p for d in f.getobjectlist(PARENT_GROUP) for p in f.getobjectlist(d)]
        boundaries = {p: str(f.getnamed("FDTD", p)) for p in ["x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc"]}
        audit = {"schema": "PAPER_A_CP_NATIVE_M1_SETUP_AUDIT_V1", "stage": STAGE, "generated_utc": utc(), "solver_entered": False, "contract": CONTRACT, "contract_sha256": CONTRACT_HASH, "materials": mats, "prepared_fsp": {"path": str(SETUP), "sha256": sha(SETUP), "size_bytes": SETUP.stat().st_size}, "readback": {"pillar_count": len(pillars), "pillar_materials": sorted({str(f.getnamed(p, "material")) for p in pillars}), "gan_material": str(f.getnamed(GAN_OBJECT, "material")), "source_ranges_nm": {n: [float(f.getnamed(n, "wavelength start"))*1e9, float(f.getnamed(n, "wavelength stop"))*1e9] for n in [X_SOURCE, Y_SOURCE]}, "source_positions_nm": {n: [float(f.getnamed(n, "x"))*1e9, float(f.getnamed(n, "y"))*1e9, float(f.getnamed(n, "z"))*1e9] for n in [X_SOURCE, Y_SOURCE]}, "monitor_points": {n: int(float(f.getnamed(n, "frequency points"))) for n in [FIELD, POWER]}, "mesh_accuracy": float(f.getnamed("FDTD", "mesh accuracy")), "boundaries": boundaries, "resource_gate": rg}, "pass": len(pillars) == 42 and sorted({str(f.getnamed(p, "material")) for p in pillars}) == [TIO2] and str(f.getnamed(GAN_OBJECT, "material")) == GAN and rg["pass"] and all(abs(v[0]-LO) < 1e-6 and abs(v[1]-HI) < 1e-6 for v in {n: [float(f.getnamed(n, "wavelength start"))*1e9, float(f.getnamed(n, "wavelength stop"))*1e9] for n in [X_SOURCE, Y_SOURCE]}.values()) and all(int(float(f.getnamed(n, "frequency points"))) == POINTS for n in [FIELD, POWER]) and all(v == "PML" for v in boundaries.values())}
        atomic(REPORT / "setup_audit.json", audit); atomic(REPORT / "physics_contract.json", {"contract": CONTRACT, "contract_sha256": CONTRACT_HASH, "materials": mats, "prepared_fsp_sha256": sha(SETUP)})
        if not audit["pass"]: raise RuntimeError("SETUP_ONLY_AUDIT_FAILED")
        print("SETUP_PASS", flush=True)
    finally:
        try: f.close()
        except Exception: pass
        try: src.close()
        except Exception: pass
def run_case(axis):
    case = f"CP_NATIVE_M1_CENTER_{axis.upper()}"; attempt = RUNTIME / "cases" / case / "attempt_001"; attempt.mkdir(parents=True, exist_ok=True); prov = attempt / "provenance.json"
    if prov.exists() and json.loads(prov.read_text(encoding="utf-8")).get("solver_entered") is True: raise RuntimeError(f"NO_AUTO_REPLAY:{case}")
    result = attempt / f"{case}_run.fsp"; rec = {"schema": "PAPER_A_CP_ATTEMPT_PROVENANCE_V1", "stage": STAGE, "case_id": case, "attempt_id": "attempt_001", "axis": axis, "pre_fsp": str(SETUP), "pre_fsp_sha256": sha(SETUP), "physical_contract_sha256": CONTRACT_HASH, "processes": 4, "threads": 1, "solver_entered": False, "entered_solver": False, "status": "PREPARED", "created_utc": utc()}; atomic(prov, rec)
    lease = None; f = None; entered = False
    try:
        lease = SLOT.GlobalSlotScheduler(SLOT.DEFAULT_REGISTRY_PATH).acquire(branch=BRANCH, worktree=str(ROOT), task_id=STAGE, case_uid=case, pid=os.getpid(), metadata={"task_class": STAGE, "attempt_id": "attempt_001", "polarization": axis}); rec.update({"slot_acquired": True, "slot_id": lease.slot_id, "admission_snapshot": lease.record.get("admission_snapshot")}); lease.start_heartbeat(); atomic(prov, rec)
        f = lumapi.FDTD(hide=True); f.load(str(SETUP)); enabled, disabled = (X_SOURCE, Y_SOURCE) if axis == "x" else (Y_SOURCE, X_SOURCE)
        for name, state in [(enabled, 1), (disabled, 0)]:
            setp(f, name, "enabled", state); setp(f, name, "x", 0.0); setp(f, name, "y", 0.0); setp(f, name, "z", -200e-9)
        setp(f, enabled, "theta", 90.0); setp(f, enabled, "phi", 0.0 if axis == "x" else 90.0); rg = resource(f); errors = []
        if not rg["pass"]: errors.append("resource_gate")
        if int(float(f.getnamed(enabled, "enabled"))) != 1 or int(float(f.getnamed(disabled, "enabled"))) != 0: errors.append("source_enable_gate")
        if float(f.getnamed(enabled, "x")) != 0.0 or float(f.getnamed(enabled, "y")) != 0.0: errors.append("center_gate")
        if errors: raise RuntimeError("PREFLIGHT_GATE_FAILED:" + ";".join(errors))
        f.save(str(result)); rec.update({"configuration_gate": {"pass": True, "resource": rg}, "pre_run_result_fsp_sha256": sha(result)}); atomic(prov, rec)
        entered_at = utc(); lease.mark_solver_entered(entered_at); entered = True; rec.update({"status": "ENTERED", "solver_entered": True, "entered_solver": True, "entered_utc": entered_at}); atomic(prov, rec); print(f"EVENT {case} ENTERED_RUNNING", flush=True)
        f.run(); f.save(str(result)); rec.update({"status": "RETURNED", "solver_complete": utc(), "post_fsp_sha256": sha(result), "post_fsp_size_bytes": result.stat().st_size}); lease.release("SOLVER_COMPLETED", rec["solver_complete"]); lease = None; rec.update({"slot_released": True, "slot_release_time": utc()}); atomic(prov, rec); print(f"EVENT {case} RETURNED_COMPLETED", flush=True)
    except Exception as exc:
        rec.update({"status": "FAILED_ENTERED" if entered else "FAILED_PRE_ENTRY", "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()}); atomic(prov, rec); raise
    finally:
        if lease is not None:
            try: lease.release("FAILED_ENTERED" if entered else "FAILED_PRE_ENTRY")
            except Exception: pass
        if f is not None:
            try: f.close()
            except Exception: pass
        atomic(prov, rec)
    return rec
def main():
    prepare(); atomic(REPORT / "controller_state.json", {"stage": STAGE, "status": "SETUP_PASS", "updated_utc": utc(), "completed_cases": []}); x = run_case("x"); atomic(REPORT / "controller_state.json", {"stage": STAGE, "status": "X_COMPLETED", "updated_utc": utc(), "completed_cases": ["CP_NATIVE_M1_CENTER_X"], "x": x}); print("EVENT CP_NATIVE_M1_CENTER_X COMPLETED; CASE_BOUNDARY_SCHEDULER_RECHECK", flush=True); snap = SLOT.live_job_snapshot();
    if snap.get("active_fdtd_jobs", 0) > 0 or snap.get("unknown_solver_jobs"): atomic(REPORT / "controller_state.json", {"stage": STAGE, "status": "CASE_BOUNDARY_YIELD", "updated_utc": utc(), "completed_cases": ["CP_NATIVE_M1_CENTER_X"], "scheduler_snapshot": snap}); raise RuntimeError("CASE_BOUNDARY_YIELD_HIGH_PRIORITY_FDTD")
    print("EVENT CP_NATIVE_M1_CENTER_Y ADMISSION_LEGAL", flush=True); y = run_case("y"); atomic(REPORT / "controller_state.json", {"stage": STAGE, "status": "PHYSICS_COMPLETED_NEEDS_CLOSEOUT", "updated_utc": utc(), "completed_cases": ["CP_NATIVE_M1_CENTER_X", "CP_NATIVE_M1_CENTER_Y"], "x": x, "y": y}); print("EVENT CP_NATIVE_M1_CENTER_Y COMPLETED; TWO_CASES_READY_FOR_ZERO_SOLVER_CLOSEOUT", flush=True)
if __name__ == "__main__": main()
