from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/stage_h1f3b_k6_position_mode_level2"
MANIFEST_PATH = REPORT / "h1f3b_candidate_manifest.json"
CASE_ROOT = ROOT / "outputs/lp_h1f3b_k6_position_mode_level2/cases"
ACCOUNTING_PATH = REPORT / "h1f3b_solver_accounting.json"
POLS = ("x", "y")
GRID = [450.0 + 0.5 * i for i in range(9)]
BRANCH = "work/lp-global-h-manifold-v1"
PROCESSES = 4
THREADS = 1
REGISTRY_PATH = Path(r"D:\project\apcd_global_fdtd_slot_registry_v1.json")


def load_base():
    path = ROOT / "scripts/lp_h1f2_k6_runner.py"
    spec = importlib.util.spec_from_file_location("h1f3b_base_runner", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


BASE = load_base()
BASE.REPORT = REPORT
BASE.MANIFEST_PATH = MANIFEST_PATH
BASE.CASE_ROOT = CASE_ROOT
BASE.ACCOUNTING_PATH = ACCOUNTING_PATH
BASE.BRANCH = BRANCH
BASE.REGISTRY_PATH = REGISTRY_PATH


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def candidates(manifest):
    value = manifest["candidates"]
    return list(value.values()) if isinstance(value, dict) else value


def manifest():
    m = read_json(MANIFEST_PATH)
    if m.get("status") != "FROZEN_READY_FOR_SOLVER" or m.get("candidate_count") != 4:
        raise RuntimeError("HARD_GATE_H1F3B_MANIFEST_NOT_FROZEN")
    if m.get("max_new_formal_cases") != 8 or m.get("processes") != 4 or m.get("threads") != 1:
        raise RuntimeError("HARD_GATE_H1F3B_BUDGET_DRIFT")
    if m.get("wavelength_grid_nm") != GRID or m.get("ml_admitted") is not False:
        raise RuntimeError("HARD_GATE_H1F3B_CONTRACT_DRIFT")
    cs = candidates(m)
    if len(cs) != 4 or {c.get("A_nm") for c in cs} != {-10.0, 10.0}:
        raise RuntimeError("HARD_GATE_H1F3B_CANDIDATE_COUNT_OR_AMPLITUDE")
    for c in cs:
        if c.get("position_mode") != "delta_x_n=A*cos(2*pi*n/6), phi=0":
            raise RuntimeError("HARD_GATE_H1F3B_MODE_DRIFT")
        if c.get("P_supercell_nm") != 2591.446716 or c.get("P_y_nm") != 432.0:
            raise RuntimeError("HARD_GATE_H1F3B_PERIOD_DRIFT")
        if c.get("local_geometries") != next(x["local_geometries"] for x in cs if x["candidate_uid"].startswith(c["base_candidate_uid"] + "_POS")):
            raise RuntimeError("HARD_GATE_H1F3B_LOCAL_GEOMETRY_MUTATION")
    return m


def identity(candidate, pol):
    m = manifest()
    return {"case_uid": f"H1F3B_{candidate['candidate_uid']}_{pol}", "candidate_uid": candidate["candidate_uid"], "candidate_hash": candidate["candidate_hash"], "base_candidate_uid": candidate["base_candidate_uid"], "A_nm": candidate["A_nm"], "polarization": pol, "manifest_freeze_sha256": m["freeze_sha256"], "wavelength_grid_nm": GRID, "solver_runs_for_spectrum": 1}


BASE.manifest = manifest
BASE.identity = identity
BASE.candidates = candidates


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
    BASE.write_json(ACCOUNTING_PATH, accounting)


BASE.update_accounting = update_accounting


def live_accounting():
    live = BASE.SCHEDULER.live_job_snapshot()
    return {"active_fdtd_jobs": live.get("active_fdtd_jobs", 0), "active_rcwa_jobs": live.get("active_rcwa_jobs", 0), "unknown_solver_jobs": live.get("unknown_solver_jobs", []), "lp_active_fdtd_jobs": sum(1 for j in live.get("jobs", []) if j.get("solver_type_token") == "FDTD" and str(j.get("branch_token", "")) == BRANCH), "jobs": live.get("jobs", []), "processes_per_job": PROCESSES, "threads_per_job": THREADS}


def preflight():
    m = manifest()
    snapshot = live_accounting()
    if snapshot["active_fdtd_jobs"] >= 2 or snapshot["lp_active_fdtd_jobs"] != 0 or snapshot["unknown_solver_jobs"]:
        raise RuntimeError(f"HARD_GATE_FDTD_ADMISSION:{snapshot}")
    return {"status": "READY", "manifest_freeze_sha256": m["freeze_sha256"], "candidate_count": 4, "planned_formal_cases": 8, "live_solver_accounting": snapshot, "solver_entered": False}


BASE.preflight = preflight


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or ["status"])
        writer.writeheader()
        writer.writerows(rows)


def fullwave_rows(results):
    rows = []
    for result in results:
        for row in result.get("rows", []):
            rows.append({"candidate_uid": result["candidate_uid"], "case_uid": result["case_uid"], "polarization": result["polarization"], "A_nm": result.get("case_identity", {}).get("A_nm"), "base_candidate_uid": result.get("case_identity", {}).get("base_candidate_uid"), "solver_entered": result.get("solver_entered", False), "solver_replay": result.get("solver_replay", False), **row})
    return rows


def postprocess(m):
    recovered = BASE.recover_entered(m)
    results = []
    for c in candidates(m):
        for pol in POLS:
            checkpoint = CASE_ROOT / f"H1F3B_{c['candidate_uid']}_{pol}" / "attempt_001" / "checkpoint.json"
            if checkpoint.exists():
                result = read_json(checkpoint)
                results.append(result)
    rows = fullwave_rows(results)
    write_csv(REPORT / "h1f3b_order_resolved_fullwave.csv", rows)
    jrows = []
    for c in candidates(m):
        for wavelength in GRID:
            xr = next((r for r in rows if r["candidate_uid"] == c["candidate_uid"] and r["polarization"] == "x" and float(r["wavelength_nm"]) == wavelength and int(r["order_n"]) == 1 and int(r["order_m"]) == 0), None)
            yr = next((r for r in rows if r["candidate_uid"] == c["candidate_uid"] and r["polarization"] == "y" and float(r["wavelength_nm"]) == wavelength and int(r["order_n"]) == 1 and int(r["order_m"]) == 0), None)
            if not xr or not yr:
                continue
            z = lambda r, a, b: complex(float(r[a]), float(r[b]))
            J = [[z(xr, "Ex_real", "Ex_imag"), z(yr, "Ex_real", "Ex_imag")], [z(xr, "Ey_real", "Ey_imag"), z(yr, "Ey_real", "Ey_imag")]]
            T = BASE.H1D1.transform_xy(J)
            norm = math.sqrt(sum(abs(x) ** 2 for line in J for x in line))
            proj = math.sqrt(abs(J[0][1]) ** 2 + abs(J[1][0]) ** 2 + abs(J[1][1]) ** 2) / norm if norm else None
            aa, ba, ab, bb = T[0][0], T[1][0], T[0][1], T[1][1]
            jrows.append({"candidate_uid": c["candidate_uid"], "base_candidate_uid": c["base_candidate_uid"], "A_nm": c["A_nm"], "wavelength_nm": wavelength, "target_order_n": 1, "target_order_m": 0, "basis": "Cartesian transverse Ex,Ey -> authoritative alpha/beta transform", "txx_re": J[0][0].real, "txx_im": J[0][0].imag, "txy_re": J[0][1].real, "txy_im": J[0][1].imag, "tyx_re": J[1][0].real, "tyx_im": J[1][0].imag, "tyy_re": J[1][1].real, "tyy_im": J[1][1].imag, "eta_x_plus1": xr["order_efficiency_source_norm"], "eta_y_plus1": yr["order_efficiency_source_norm"], "theta_deg": xr["theta_deg"], "alpha_star_from_alpha_re": aa.real, "alpha_star_from_alpha_im": aa.imag, "beta_star_from_alpha_re": ba.real, "beta_star_from_alpha_im": ba.imag, "alpha_star_from_beta_re": ab.real, "alpha_star_from_beta_im": ab.imag, "beta_star_from_beta_re": bb.real, "beta_star_from_beta_im": bb.imag, "target_projector_error": proj, "target_phase_deg": math.degrees(math.atan2(aa.imag, aa.real)) if abs(aa) > 1e-12 else None, "target_x_input_cross_power": abs(ba) ** 2, "target_y_input_leakage_power": abs(ab) ** 2, "target_alpha_star_from_alpha_power": abs(aa) ** 2})
    write_csv(REPORT / "h1f3b_k6_order_jones.csv", jrows)
    accounting = read_json(ACCOUNTING_PATH)
    accounting["status"] = "FULLWAVE_POSTPROCESSED"
    BASE.write_json(ACCOUNTING_PATH, accounting)
    return {"status": "FULLWAVE_POSTPROCESSED", "accepted_cases": len(results), "fullwave_rows": len(rows), "jones_rows": len(jrows), "postfsp_recovered_cases": recovered}


def execute():
    m = manifest()
    preflight()
    runtime = BASE.H1D1.load_runtime()
    scheduler = BASE.SCHEDULER.GlobalSlotScheduler(REGISTRY_PATH)
    results = []
    for c in candidates(m):
        for pol in POLS:
            result = BASE.run_case(c, pol, scheduler, runtime)
            results.append(result)
            print(json.dumps({"case": result.get("case_uid"), "status": result.get("status"), "solver_entered": result.get("solver_entered", False)}), flush=True)
    return postprocess(m)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "execute", "postprocess"))
    args = parser.parse_args()
    if args.mode == "preflight":
        print(json.dumps(preflight(), indent=2, default=str))
    elif args.mode == "postprocess":
        print(json.dumps(postprocess(manifest()), indent=2, default=str))
    else:
        print(json.dumps(execute(), indent=2, default=str))
