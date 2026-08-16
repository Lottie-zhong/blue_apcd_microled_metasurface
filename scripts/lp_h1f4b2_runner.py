from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/stage_h1f4b2_grouped_d_j1_combined_local_validation"
MANIFEST_PATH = REPORT / "h1f4b2_combined_candidate_manifest.json"
CASE_ROOT = ROOT / "outputs/lp_h1f4b2_grouped_d_j1_combined_local_validation/cases"
ACCOUNTING_PATH = REPORT / "h1f4b2_solver_accounting.json"
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


def build(fdtd, candidate, pol):
    from metasurface.lumerical_native_materials import ensure_apcd_native_materials, get_lumerical_material_name
    nm = 1e-9
    px, py = candidate["P_supercell_nm"] * nm, candidate["P_y_nm"] * nm
    h = candidate["H_global_nm"] * nm
    fdtd.switchtolayout(); fdtd.deleteall(); ensure_apcd_native_materials(fdtd)
    material = get_lumerical_material_name(candidate["material"])
    fdtd.addfdtd()
    for key, value in (("dimension", "3D"), ("x", 0.0), ("y", 0.0), ("x span", px), ("y span", py), ("z min", -500*nm), ("z max", 1200*nm), ("x min bc", "Periodic"), ("x max bc", "Periodic"), ("y min bc", "Periodic"), ("y max bc", "Periodic"), ("z min bc", "PML"), ("z max bc", "PML"), ("mesh accuracy", 2), ("simulation time", 1000e-15), ("background material", "<Object defined dielectric>"), ("index", 1.0)):
        fdtd.set(key, value)
    fdtd.setglobalmonitor("frequency points", len(GRID)); fdtd.setglobalmonitor("use wavelength spacing", True); fdtd.setglobalmonitor("use source limits", True)
    for site, (geo, pos) in enumerate(zip(candidate["local_geometries"], candidate["site_positions_nm"])):
        xbase = float(pos["x_nm"]) - candidate["P_supercell_nm"] / 2.0
        for suffix, cx, cy, xs, ys, rot in (("pillar_1", geo["J1_center_x_nm"], geo["J1_center_y_nm"], geo["J1_length_nm"], geo["J1_width_nm"], geo.get("J1_rotation_deg", 0.0)), ("pillar_2", geo["J2_center_x_nm"], geo["J2_center_y_nm"], geo["J2_length_nm"], geo["J2_width_nm"], geo.get("J2_rotation_deg", 0.0))):
            fdtd.addrect(); fdtd.set("name", f"{candidate['candidate_uid']}_site_{site}_{suffix}"); fdtd.set("x", (xbase+float(cx))*nm); fdtd.set("y", (float(pos["y_nm"])+float(cy))*nm); fdtd.set("x span", float(xs)*nm); fdtd.set("y span", float(ys)*nm); fdtd.set("z min", 0.0); fdtd.set("z max", h); fdtd.set("first axis", "z"); fdtd.set("rotation 1", float(rot)); fdtd.set("material", material)
    fdtd.addplane(); fdtd.set("name", "source"); fdtd.set("injection axis", "z"); fdtd.set("direction", "Forward"); fdtd.set("x", 0.0); fdtd.set("y", 0.0); fdtd.set("x span", px); fdtd.set("y span", py); fdtd.set("z", -250*nm); fdtd.set("wavelength start", GRID[0]*nm); fdtd.set("wavelength stop", GRID[-1]*nm); fdtd.set("polarization angle", 0 if pol == "x" else 90)
    fdtd.addpower(); fdtd.set("name", "T"); fdtd.set("monitor type", "2D Z-normal"); fdtd.set("x", 0.0); fdtd.set("y", 0.0); fdtd.set("x span", px); fdtd.set("y span", py); fdtd.set("z", 1000*nm); fdtd.set("override global monitor settings", True); fdtd.set("use wavelength spacing", True); fdtd.set("frequency points", len(GRID)); fdtd.set("use source limits", True)
    return {"material_name": material, "polarization": pol, "wavelength_grid_nm": GRID, "supercell_nm": [candidate["P_supercell_nm"], candidate["P_y_nm"]], "monitor_z_nm": 1000.0, "pillar_count": 12, "H_global_nm": candidate["H_global_nm"], "site_positions_nm": candidate["site_positions_nm"]}


BASE.build = build


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def candidates(manifest):
    value = manifest["children"]
    return list(value.values()) if isinstance(value, dict) else value


def manifest():
    m = read_json(MANIFEST_PATH)
    if m.get("status") != "FROZEN_READY_FOR_SOLVER" or m.get("candidate_count") != 2:
        raise RuntimeError("HARD_GATE_H1F4B2_MANIFEST_NOT_FROZEN")
    if m.get("max_new_formal_cases") != 4 or m.get("processes") != 4 or m.get("threads") != 1:
        raise RuntimeError("HARD_GATE_H1F4B2_BUDGET_DRIFT")
    if m.get("wavelength_grid_nm") != GRID or m.get("ml_admitted") is not False or m.get("A_D_abs_nm") != 4.0:
        raise RuntimeError("HARD_GATE_H1F4B2_CONTRACT_DRIFT")
    cs = candidates(m)
    if len(cs) != 2 or not {c.get("candidate_uid") for c in cs} == {"H1F4B2_K6_L1_C_POS_PLUS10_COMBINED_PLUS", "H1F4B2_K6_L1_C_POS_PLUS10_COMBINED_MINUS"}:
        raise RuntimeError("HARD_GATE_H1F4B2_CHILDREN")
    for c in cs:
        if c.get("A_D_nm") not in (4.0, -4.0) or c.get("delta_J1_nm") not in (-0.3714949866125559, 0.3714949866125559) or c.get("j1_anisotropy_mode") != "J1_length=J1_side+delta_nm; J1_width=J1_side-delta_nm; preserve mean dimension and all six-site local-axis convention":
            raise RuntimeError("HARD_GATE_H1F4B2_MODE_DRIFT")
        if c.get("P_supercell_nm") != 2591.446716 or c.get("P_y_nm") != 432.0:
            raise RuntimeError("HARD_GATE_H1F4B2_PERIOD_DRIFT")
        if not c.get("geometry_legality", {}).get("pass"):
            raise RuntimeError("HARD_GATE_H1F4B2_ILLEGAL_CHILD")
        if c.get("base_candidate_uid") != "K6_L1_C_POS_PLUS10" or c.get("base_candidate_hash") != "a8606d8f44a4675db08493c3dd95c8ea43f30882d3a9bbb18a65b59c2ba45198":
            raise RuntimeError("HARD_GATE_H1F4B2_PARENT_HASH_DRIFT")
    if m.get("parent_hash") != "a8606d8f44a4675db08493c3dd95c8ea43f30882d3a9bbb18a65b59c2ba45198":
        raise RuntimeError("HARD_GATE_H1F4B2_PRIMARY_HASH_DRIFT")
    return m


def identity(candidate, pol):
    m = manifest()
    return {"case_uid": f"{candidate['candidate_uid']}_{pol}", "candidate_uid": candidate["candidate_uid"], "candidate_hash": candidate["candidate_hash"], "base_candidate_uid": candidate["base_candidate_uid"], "A_D_nm": candidate["A_D_nm"], "j1_delta_nm": candidate["delta_J1_nm"], "j1_anisotropy_mode": candidate["j1_anisotropy_mode"], "grouped_d_perturbation_nm": candidate["grouped_d_perturbation_nm"], "polarization": pol, "manifest_freeze_sha256": m["freeze_sha256"], "wavelength_grid_nm": GRID, "solver_runs_for_spectrum": 1}


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
    accounting["solver_entered_delta"] = accounting["entered_formal_cases"]
    accounting["solver_accepted_delta"] = accounting["accepted_formal_cases"]
    BASE.write_json(ACCOUNTING_PATH, accounting)


BASE.update_accounting = update_accounting


def live_accounting():
    live = BASE.SCHEDULER.live_job_snapshot()
    return {"active_fdtd_jobs": live.get("active_fdtd_jobs", 0), "active_rcwa_jobs": live.get("active_rcwa_jobs", 0), "unknown_solver_jobs": live.get("unknown_solver_jobs", []), "lp_active_fdtd_jobs": sum(1 for j in live.get("jobs", []) if j.get("solver_type") == "FDTD" and j.get("branch") in {"LP", BRANCH}), "jobs": live.get("jobs", []), "processes_per_job": PROCESSES, "threads_per_job": THREADS, "permanent_global_capacity": read_json(Path(r"D:\project\apcd_global_fdtd_slot_registry_v1.json")).get("global_capacity") if Path(r"D:\project\apcd_global_fdtd_slot_registry_v1.json").exists() else None, "effective_stage_capacity": 3}


def fresh_concurrency_audit(case_uid, pol):
    snapshot = live_accounting()
    fdtd = [j for j in snapshot["jobs"] if j.get("solver_type") == "FDTD"]
    audit = {"captured_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(), "case_uid": case_uid, "polarization": pol, "active_fdtd_groups": fdtd, "active_fdtd_group_count": len(fdtd), "active_rcwa_groups": [j for j in snapshot["jobs"] if j.get("solver_type") == "RCWA"], "active_rcwa_group_count": snapshot["active_rcwa_jobs"], "mpi_child_process_count": sum(len(j.get("processes", [])) for j in fdtd), "permanent_global_capacity": snapshot["permanent_global_capacity"], "effective_stage_capacity": 3, "lp_active_fdtd_groups": snapshot["lp_active_fdtd_jobs"], "entry_authorized": snapshot["permanent_global_capacity"] == 2 and snapshot["active_fdtd_jobs"] < 3 and snapshot["lp_active_fdtd_jobs"] == 0 and not snapshot["unknown_solver_jobs"], "rcwa_consumes_fdtd_slot": False, "fourth_fdtd_authorized": False}
    BASE.write_json(REPORT / f"scheduler_audit_before_{case_uid}.json", audit)
    if not audit["entry_authorized"]:
        raise RuntimeError(f"WAIT_OR_BLOCKED_STAGE_CONCURRENCY3:{audit}")
    return audit


class StageTrialScheduler(BASE.SCHEDULER.GlobalSlotScheduler):
    def acquire(self, *args, **kwargs):
        metadata = kwargs.get("metadata") or {}
        case_uid = kwargs.get("case_uid", "UNKNOWN")
        pol = metadata.get("polarization", "unknown")
        audit = fresh_concurrency_audit(case_uid, pol)
        lease = super().acquire(*args, **kwargs)
        lease.record["stage_concurrency3_preentry_audit"] = audit
        return lease


def preflight():
    m = manifest()
    snapshot = live_accounting()
    if snapshot["permanent_global_capacity"] != 2 or snapshot["active_fdtd_jobs"] >= 3 or snapshot["lp_active_fdtd_jobs"] != 0 or snapshot["unknown_solver_jobs"]:
        raise RuntimeError(f"WAIT_STAGE_CONCURRENCY3_PREFLIGHT:{snapshot}")
    return {"status": "READY", "manifest_freeze_sha256": m["freeze_sha256"], "candidate_count": 2, "planned_formal_cases": 4, "live_solver_accounting": snapshot, "solver_entered": False}


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
            rows.append({"candidate_uid": result["candidate_uid"], "case_uid": result["case_uid"], "polarization": result["polarization"], "A_D_nm": result.get("case_identity", {}).get("A_D_nm"), "j1_delta_nm": result.get("case_identity", {}).get("j1_delta_nm"), "base_candidate_uid": result.get("case_identity", {}).get("base_candidate_uid"), "solver_entered": result.get("solver_entered", False), "solver_replay": result.get("solver_replay", False), **row})
    return rows


def postprocess(m):
    results = []
    for c in candidates(m):
        for pol in POLS:
            checkpoint = CASE_ROOT / f"{c['candidate_uid']}_{pol}" / "attempt_001" / "checkpoint.json"
            if checkpoint.exists():
                result = read_json(checkpoint)
                results.append(result)
    rows = fullwave_rows(results)
    write_csv(REPORT / "h1f4b2_order_resolved_fullwave.csv", rows)
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
            jrows.append({"candidate_uid": c["candidate_uid"], "base_candidate_uid": c["base_candidate_uid"], "A_D_nm": c["A_D_nm"], "j1_delta_nm": c["delta_J1_nm"], "wavelength_nm": wavelength, "target_order_n": 1, "target_order_m": 0, "basis": "Cartesian transverse Ex,Ey -> authoritative alpha/beta transform", "txx_re": J[0][0].real, "txx_im": J[0][0].imag, "txy_re": J[0][1].real, "txy_im": J[0][1].imag, "tyx_re": J[1][0].real, "tyx_im": J[1][0].imag, "tyy_re": J[1][1].real, "tyy_im": J[1][1].imag, "eta_x_plus1": xr["order_efficiency_source_norm"], "eta_y_plus1": yr["order_efficiency_source_norm"], "theta_deg": xr["theta_deg"], "alpha_star_from_alpha_re": aa.real, "alpha_star_from_alpha_im": aa.imag, "beta_star_from_alpha_re": ba.real, "beta_star_from_alpha_im": ba.imag, "alpha_star_from_beta_re": ab.real, "alpha_star_from_beta_im": ab.imag, "beta_star_from_beta_re": bb.real, "beta_star_from_beta_im": bb.imag, "target_projector_error": proj, "target_phase_deg": math.degrees(math.atan2(aa.imag, aa.real)) if abs(aa) > 1e-12 else None, "target_x_input_cross_power": abs(ba) ** 2, "target_y_input_leakage_power": abs(ab) ** 2, "target_alpha_star_from_alpha_power": abs(aa) ** 2})
    write_csv(REPORT / "h1f4b2_k6_order_jones.csv", jrows)
    accounting = read_json(ACCOUNTING_PATH)
    accounting["status"] = "FULLWAVE_POSTPROCESSED"
    BASE.write_json(ACCOUNTING_PATH, accounting)
    return {"status": "FULLWAVE_POSTPROCESSED", "accepted_cases": len(results), "fullwave_rows": len(rows), "jones_rows": len(jrows), "postfsp_recovered_cases": []}


def execute():
    m = manifest()
    preflight()
    runtime = BASE.H1D1.load_runtime()
    scheduler = StageTrialScheduler(REGISTRY_PATH)
    results = []
    for c in candidates(m):
        for pol in POLS:
            case_uid = f"{c['candidate_uid']}_{pol}"
            accounting = read_json(ACCOUNTING_PATH)
            prior = next((row for row in accounting.get("cases", []) if row.get("case_uid") == case_uid), None)
            if prior and prior.get("solver_entered") and prior.get("status") == "ACCEPTED":
                print(json.dumps({"case": case_uid, "status": "SKIPPED_ALREADY_ACCEPTED", "solver_entered": True}), flush=True)
                continue
            result = BASE.run_case(c, pol, scheduler, runtime)
            results.append(result)
            BASE.write_json(REPORT / f"scheduler_audit_after_{result.get('case_uid','unknown')}.json", live_accounting())
            ledger = read_json(REPORT / "h1f4b2_solver_ledger.json")
            if result.get("solver_entered"):
                ledger["solver_entered"].append({"case_uid": result.get("case_uid"), "attempt_id": result.get("attempt_id"), "solver_entered": True, "status": result.get("status")})
                ledger["solver_entered_count"] = len(ledger["solver_entered"])
            BASE.write_json(REPORT / "h1f4b2_solver_ledger.json", ledger)
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



