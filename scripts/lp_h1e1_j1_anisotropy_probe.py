from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import itertools
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/stage_h1e1_j1_anisotropy"
OUT = ROOT / "outputs/lp_extended_j1_h1e1"
RUNTIME = OUT / "runtime"
STRICT_BANK = ROOT / "reports/stage_h1c1b1_sixbin_closure/h1c1b1_strict_bank_v1.json"
MANIFEST = REPORT / "h1e1_candidate_manifest.json"
ACCOUNTING = REPORT / "h1e1_solver_accounting.json"
GRID = [450.0 + 0.5 * i for i in range(9)]
H = 550.0
PERIOD = 432.0
MATERIAL = "APCD_TIO2_NATIVE_M1"
PROJECTOR_ERROR_MAX = 0.1864961370084426
BRANCH = "work/lp-global-h-manifold-v1"
POLARIZATIONS = ("x", "y")
MAX_SUBRUNS = 16


def sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()).hexdigest()


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for row in rows for k in row)) or ["status"]
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    os.replace(tmp, path)


def wrap(v: float) -> float:
    return v % 360.0


def cdiff(a: float, b: float) -> float:
    return (a - b + 180.0) % 360.0 - 180.0


def coverage(vals: list[float]) -> dict[str, Any]:
    x = sorted(set(wrap(v) for v in vals))
    if len(x) < 2:
        return {"coverage_deg": 0.0, "largest_gap_deg": 360.0, "gaps_deg": []}
    gaps = [b - a for a, b in zip(x, x[1:])] + [x[0] + 360.0 - x[-1]]
    return {"coverage_deg": 360.0 - max(gaps), "largest_gap_deg": max(gaps), "gaps_deg": gaps, "wrapped_values_deg": x}


def six_bin_optimize(geometries: list[dict[str, Any]]) -> dict[str, Any]:
    """Exhaustive six-geometry/common-offset screen over saved trajectories only."""
    if len(geometries) < 6:
        return {"status": "INSUFFICIENT_STRICT_GEOMETRIES", "candidate_count": len(geometries)}
    best = None
    for combo in itertools.combinations(sorted(geometries, key=lambda x: x["geometry_uid"]), 6):
        phases = [[float(v) for v in g["phase_trajectory_deg"]] for g in combo]
        for bins in itertools.permutations(range(6)):
            offsets = []
            for traj, k in zip(phases, bins):
                offsets.extend(wrap(phi - 60.0 * k) for phi in traj)
            sx = sum(math.cos(math.radians(v)) for v in offsets)
            sy = sum(math.sin(math.radians(v)) for v in offsets)
            phi0 = wrap(math.degrees(math.atan2(sy, sx)))
            errors = [cdiff(phi, phi0 + 60.0 * k) for traj, k in zip(phases, bins) for phi in traj]
            worst = max(abs(v) for v in errors)
            rms = math.sqrt(sum(v * v for v in errors) / len(errors))
            order_450 = tuple(sorted(range(6), key=lambda i: phases[i][0]))
            crossing_wavelengths = [GRID[j] for j in range(1, len(GRID)) if tuple(sorted(range(6), key=lambda i: phases[i][j])) != order_450]
            key = (round(worst, 12), round(rms, 12), tuple(g["geometry_uid"] for g in combo), bins)
            if best is None or key < best[0]:
                best = (key, {"geometry_uids": [g["geometry_uid"] for g in combo], "bin_assignment": list(bins), "phi0_deg": phi0, "worst_broadband_bin_error_deg": worst, "rms_bin_error_deg": rms, "phase_order_crossing": bool(crossing_wavelengths), "phase_order_crossing_wavelengths_nm": crossing_wavelengths, "evaluated_wavelengths_nm": GRID, "error_sample_count": len(errors), "optimization": "exhaustive_combinations_and_bin_permutations_with_circular_mean_common_offset"})
    return {"status": "EXHAUSTIVE_OFFLINE_COMPLETE", "candidate_count": len(geometries), "combination_count": math.comb(len(geometries), 6), "best": best[1] if best else None}


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def parent_center(coords: dict[str, Any]) -> tuple[float, float]:
    d = float(coords["D_nm"]); psi = math.radians(float(coords["Psi_deg"]))
    return round(d * math.cos(psi) / 2.0 * 2.0) / 2.0, round(d * math.sin(psi) / 2.0 * 2.0) / 2.0


def identity(parent: dict[str, Any], L: int, W: int, cx: float, cy: float) -> dict[str, Any]:
    c = parent["coordinates_5d"]
    return {"schema": "LP_GLOBAL_H_H1E1_J1_ANISOTROPY_GEOMETRY_V1", "grammar_version": "J1_INDEPENDENT_ANISOTROPY_V1", "H_global_nm": H, "J1_H_nm": H, "J2_H_nm": H, "bottom_plane_nm": 0.0, "period_nm": [PERIOD, PERIOD], "material_contract": MATERIAL, "J1_shape": "sharp_rectangle", "J2_shape": "sharp_rectangle", "J1_length_nm": L, "J1_width_nm": W, "J1_center_x_nm": -cx, "J1_center_y_nm": -cy, "J1_rotation_deg": 0.0, "J2_length_nm": int(c["J2_length_nm"]), "J2_width_nm": int(c["J2_width_nm"]), "J2_center_x_nm": cx, "J2_center_y_nm": cy, "J2_rotation_deg": float(c["Psi_deg"]), "source_z_nm": -250.0, "monitor_z_nm": 1000.0, "wavelength_grid_nm": GRID, "observable": "coordinate_weighted_full_period_complex_G0", "endpoint_convention": "deduplicate_periodic_endpoints_and_reclose_period", "normalization": "sqrt(T)/norm(weighted_Ex,weighted_Ey)", "phase_reference": "arg(txx)", "projector": [[1, 0], [0, 0]]}


def legality(parent: dict[str, Any], L: int, W: int, seen: set[str]) -> dict[str, Any]:
    c = parent["coordinates_5d"]; cx, cy = parent_center(c)
    j2l, j2w = int(c["J2_length_nm"]), int(c["J2_width_nm"])
    direct = 2 * math.hypot(cx, cy) - max(L, W, j2l, j2w)
    periodic_x = PERIOD - 2 * abs(cx) - max(L, W, j2w)
    periodic_y = PERIOD - 2 * abs(cy) - max(L, W, j2l)
    ident = identity(parent, L, W, cx, cy); h = sha(ident)
    checks = {"bounds_L": 102 <= L <= 114, "bounds_W": 102 <= W <= 114, "integer_dimensions": isinstance(L, int) and isinstance(W, int), "constant_mean": (L + W) / 2 == int(c["J1_side_nm"]), "H_unified_550": True, "period_432": True, "native_material": True, "half_grid_centers": all(abs(2 * v - round(2 * v)) < 1e-9 for v in (cx, cy)), "direct_gap_ge_60": direct >= 60.0, "periodic_gap_x_ge_60": periodic_x >= 60.0, "periodic_gap_y_ge_60": periodic_y >= 60.0, "no_overlap": direct > 0.0, "unique_hash": h not in seen}
    return {"pass": all(checks.values()), "checks": checks, "exact_hash": h, "geometry_identity": ident, "center_nm": {"x": cx, "y": cy}, "direct_gap_nm": direct, "periodic_gap_x_nm": periodic_x, "periodic_gap_y_nm": periodic_y}


def choose_parent_roles(bank: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    by = {x["geometry_uid"]: x for x in bank}
    requested_a = by["H1C1B_V2_009"]
    ranked = sorted(bank, key=lambda x: float(x["trajectory"][0]["phi_deg"]))
    b = next(x for x in ranked if x["geometry_uid"] != requested_a["geometry_uid"])
    c = next(x for x in reversed(ranked) if x["geometry_uid"] != requested_a["geometry_uid"])
    audit = {"requested_A": requested_a["geometry_uid"], "B": b["geometry_uid"], "C": c["geometry_uid"], "rule": "A=H1C1B_V2_009; B=min 450 phase excluding A; C=max 450 phase excluding A", "all_strict_9_of_9": all(len(x["trajectory"]) == 9 for x in (requested_a, b, c))}
    # A has s=114 and therefore no nonzero constant-mean integer anisotropy.
    # The authorized fallback is the first canonical strict parent with four legal children.
    if min(int(requested_a["coordinates_5d"]["J1_side_nm"]) - 102, 114 - int(requested_a["coordinates_5d"]["J1_side_nm"])) < 1:
        fallback = next(x for x in bank if x["geometry_uid"] not in {b["geometry_uid"], c["geometry_uid"]} and min(int(x["coordinates_5d"]["J1_side_nm"]) - 102, 114 - int(x["coordinates_5d"]["J1_side_nm"])) >= 2)
        audit["A_fallback"] = fallback["geometry_uid"]
        audit["A_fallback_reason"] = "requested A has d_box=0 and cannot form four legal nonzero children"
        a = fallback
    else:
        a = requested_a
    audit["execution_A"] = a["geometry_uid"]
    return a, b, c, audit


def legal_ds(parent: dict[str, Any]) -> dict[str, Any]:
    s = int(parent["coordinates_5d"]["J1_side_nm"]); dbox = min(s - 102, 114 - s)
    seen: set[str] = set(); rows = []
    for d in range(-dbox, dbox + 1):
        if d == 0: continue
        L, W = s + d, s - d; audit = legality(parent, L, W, seen)
        if audit["pass"]: seen.add(audit["exact_hash"])
        rows.append({"d": d, "J1_length_nm": L, "J1_width_nm": W, **audit})
    return {"parent_uid": parent["geometry_uid"], "J1_side_nm": s, "d_box": dbox, "legal_signed_d": [x["d"] for x in rows if x["pass"]], "enumeration": rows}


def nearest(ds: list[int], target: float) -> int:
    # First round the continuous target onto the integer lattice.  Only if
    # that rounded magnitude is unavailable do we search inward toward zero;
    # this preserves the authorized nearest-integer rule for d_box=1,
    # 2/3*d_box=0.667 -> d=1.
    target_int = max(1, int(math.floor(target + 0.5)))
    nonzero = sorted({abs(d) for d in ds if d != 0})
    inward = [d for d in nonzero if d <= target_int]
    if not inward: raise RuntimeError(f"NO_LEGAL_D_INWARD:{target}:{ds}")
    return min(inward, key=lambda d: (abs(d - target_int), d))


def make_manifest() -> dict[str, Any]:
    bank = read(STRICT_BANK)["geometries"]
    a, b, c, role_audit = choose_parent_roles(bank)
    parents = {x["geometry_uid"]: x for x in (a, b, c)}
    ranges = {uid: legal_ds(p) for uid, p in parents.items()}
    children = []; seen = set()
    for role, parent, modes in (("A", a, ("small", "large")), ("B", b, ("large",)), ("C", c, ("large",))):
        legal = ranges[parent["geometry_uid"]]["legal_signed_d"]
        dbox = ranges[parent["geometry_uid"]]["d_box"]
        for mode in modes:
            target = dbox / 3.0 if mode == "small" else 2.0 * dbox / 3.0
            mag = nearest([d for d in legal if d > 0], target)
            for sign in (1, -1):
                d = sign * mag; s = int(parent["coordinates_5d"]["J1_side_nm"]); L, W = s + d, s - d
                la = legality(parent, L, W, seen)
                if not la["pass"]: raise RuntimeError(f"HARD_GATE_ILLEGAL_CHILD:{parent['geometry_uid']}:{d}:{la}")
                seen.add(la["exact_hash"]); cx, cy = parent_center(parent["coordinates_5d"])
                uid = f"H1E1_{role}_{mode}_{'P' if sign > 0 else 'N'}_{parent['geometry_uid']}"
                child = {"geometry_uid": uid, "role": role, "level": mode, "parent_uid": parent["geometry_uid"], "parent_exact_hash": parent["exact_hash"], "d_nm": d, "J1_side_nm": s, "J1_length_nm": L, "J1_width_nm": W, "coordinates_5d_parent": parent["coordinates_5d"], "center_nm": {"x": cx, "y": cy}, "exact_hash": la["exact_hash"], "geometry_identity": la["geometry_identity"], "legality": la, "grammar_version": "J1_INDEPENDENT_ANISOTROPY_V1"}
                child["broadband_case_identity"] = {pol: {"case_uid": f"{uid}_{pol}", "geometry_uid": uid, "exact_geometry_hash_sha256": la["exact_hash"], "polarization": pol, "grammar_version": child["grammar_version"]} for pol in POLARIZATIONS}
                children.append(child)
    if len(children) != 8 or len({x["exact_hash"] for x in children}) != 8: raise RuntimeError("HARD_GATE_NOT_EXACTLY_8_UNIQUE_CHILDREN")
    contract = {"schema": "H1E1_J1_ANISOTROPY_FULL_JONES_CONTRACT_V1", "H_global_nm": H, "period_nm": [PERIOD, PERIOD], "material": MATERIAL, "bounds_nm": {"J1_length": [102, 114], "J1_width": [102, 114]}, "wavelength_grid_nm": GRID, "projector": [[1, 0], [0, 0]], "phase": "arg(txx)", "projector_error_max": PROJECTOR_ERROR_MAX, "extraction": "transmission_side_full_period_coordinate_weighted_complex_G0_endpoint_dedup_periodic_reclosure_sqrtT_over_norm", "one_broadband_run_per_polarization": True}
    payload = {"schema": "H1E1_CANDIDATE_MANIFEST_V1", "stage": "H1E-1", "status": "FROZEN_READY", "branch": BRANCH, "worktree": str(ROOT), "contract": contract, "contract_sha256": sha(contract), "solver_authorization": {"new_geometries": 8, "formal_x_y_subruns": 16, "max_global_fdtd_concurrency": 2, "max_active_fdtd_per_branch": 1, "processes_per_job": 4, "threads_per_job": 1, "entered_no_replay": True}, "parent_selection": role_audit, "parents": {p["geometry_uid"]: p for p in (a, b, c)}, "legal_ranges": ranges, "candidates": children}
    payload["freeze_sha256"] = sha(payload)
    write(MANIFEST, payload)
    write(REPORT / "h1e1_parent_selection.json", {"schema": "H1E1_PARENT_SELECTION_V1", "roles": role_audit, "parents": {p["geometry_uid"]: {"exact_hash": p["exact_hash"], "coordinates_5d": p["coordinates_5d"], "phase_trajectory_deg": [r["phi_deg"] for r in p["trajectory"]], "strict_9_of_9": len(p["trajectory"]) == 9} for p in (a, b, c)}})
    write(REPORT / "h1e1_legal_anisotropy_ranges.json", {"schema": "H1E1_LEGAL_ANISOTROPY_RANGES_V1", "ranges": ranges})
    return payload


def initialize_accounting(manifest: dict[str, Any]) -> dict[str, Any]:
    cases = [{"case_id": c["broadband_case_identity"][p]["case_uid"], "geometry_uid": c["geometry_uid"], "exact_hash": c["exact_hash"], "polarization": p, "planned": True, "attempted": False, "solver_entered": False, "accepted": False, "quarantined": False} for c in manifest["candidates"] for p in POLARIZATIONS]
    payload = {"schema": "H1E1_SOLVER_ACCOUNTING_V1", "manifest_freeze_sha256": manifest["freeze_sha256"], "planned_formal_subruns": 16, "entered_formal_subruns": 0, "accepted_formal_subruns": 0, "quarantined_formal_subruns": 0, "max_global_fdtd_concurrency": 2, "max_active_fdtd_per_branch": 1, "processes_per_job": 4, "threads_per_job": 1, "cases": cases, "solver_entries": []}
    write(ACCOUNTING, payload); return payload


def patch_runner():
    base = load_module(ROOT / "scripts/lp_global_h_h1c1a_broadband_v1.py", "h1e1_h1c1a_base")
    base.REPORT = REPORT; base.OUT = OUT; base.RUNTIME = RUNTIME; base.ACCOUNTING_PATH = ACCOUNTING; base.MANIFEST_PATH = MANIFEST; base.GRID = GRID; base.H_GLOBAL_NM = H; base.PERIOD_NM = PERIOD; base.MATERIAL = MATERIAL; base.PROJECTOR_ERROR_MAX = PROJECTOR_ERROR_MAX; base.TARGET_BRANCH = BRANCH; base.MAX_SUBRUNS = MAX_SUBRUNS
    def build(fdtd: Any, candidate: dict[str, Any], pol: str) -> dict[str, Any]:
        from metasurface.lumerical_native_materials import ensure_apcd_native_materials, get_lumerical_material_name
        nm = 1e-9; fdtd.switchtolayout(); fdtd.deleteall(); ensure_apcd_native_materials(fdtd); px = py = PERIOD * nm; h = H * nm; mat = get_lumerical_material_name(MATERIAL)
        fdtd.addfdtd(); fdtd.set("dimension", "3D")
        for key, value in [("x span", px), ("y span", py), ("z min", -500*nm), ("z max", 1200*nm), ("x min bc", "Periodic"), ("x max bc", "Periodic"), ("y min bc", "Periodic"), ("y max bc", "Periodic"), ("z min bc", "PML"), ("z max bc", "PML"), ("mesh accuracy", 2), ("simulation time", 1000e-15), ("background material", "<Object defined dielectric>"), ("index", 1.0)]: fdtd.set(key, value)
        fdtd.setglobalmonitor("frequency points", len(GRID)); fdtd.setglobalmonitor("use wavelength spacing", True); fdtd.setglobalmonitor("use source limits", True)
        cx, cy = candidate["center_nm"]["x"]*nm, candidate["center_nm"]["y"]*nm; c = candidate["coordinates_5d_parent"]
        fdtd.addrect(); fdtd.set("name", "pillar_1"); fdtd.set("x span", candidate["J1_length_nm"]*nm); fdtd.set("y span", candidate["J1_width_nm"]*nm); fdtd.set("x", -cx); fdtd.set("y", -cy); fdtd.set("z min", 0); fdtd.set("z max", h); fdtd.set("first axis", "z"); fdtd.set("rotation 1", 0); fdtd.set("material", mat)
        fdtd.addrect(); fdtd.set("name", "pillar_2"); fdtd.set("x span", float(c["J2_length_nm"])*nm); fdtd.set("y span", float(c["J2_width_nm"])*nm); fdtd.set("x", cx); fdtd.set("y", cy); fdtd.set("z min", 0); fdtd.set("z max", h); fdtd.set("first axis", "z"); fdtd.set("rotation 1", float(c["Psi_deg"])); fdtd.set("material", mat)
        fdtd.addplane(); fdtd.set("name", "source"); fdtd.set("injection axis", "z"); fdtd.set("direction", "Forward"); fdtd.set("x span", px); fdtd.set("y span", py); fdtd.set("z", -250*nm); fdtd.set("wavelength start", GRID[0]*nm); fdtd.set("wavelength stop", GRID[-1]*nm); fdtd.set("polarization angle", 0 if pol == "x" else 90)
        for name in ("T", "field_monitor"):
            fdtd.addpower() if name == "T" else fdtd.addprofile(); fdtd.set("name", name); fdtd.set("monitor type", "2D Z-normal"); fdtd.set("x span", px); fdtd.set("y span", py); fdtd.set("z", 1000*nm); fdtd.set("override global monitor settings", True); fdtd.set("use wavelength spacing", True); fdtd.set("frequency points", len(GRID)); fdtd.set("use source limits", True)
        return {"J1_length_nm": candidate["J1_length_nm"], "J1_width_nm": candidate["J1_width_nm"], "J2_rotation_deg": c["Psi_deg"], "H_global_nm": H, "material_name": mat}
    base.build = build
    return base


def run_all(manifest: dict[str, Any]) -> None:
    base = patch_runner(); accounting = read(ACCOUNTING)
    runtime = base.load_runtime(); scheduler = base.load_module(ROOT / "scripts/apcd_global_fdtd_slot_v1.py", "h1e1_scheduler").GlobalSlotScheduler(Path(r"D:\project\apcd_global_fdtd_slot_registry_v1.json"))
    for child in manifest["candidates"]:
        for pol in POLARIZATIONS:
            # H1C1A's setup gate reads the historical coordinates_5d alias for
            # Psi.  Keep the frozen H1E1 manifest unchanged and provide that
            # compatibility view only to the lifecycle call; the actual J1
            # L/W dimensions remain the H1E1 child fields consumed by build().
            run_candidate = dict(child)
            run_candidate["coordinates_5d"] = child["coordinates_5d_parent"]
            result = base.run_case(runtime, run_candidate, pol, manifest, scheduler)
            print(json.dumps({"case_id": child["broadband_case_identity"][pol]["case_uid"], "status": result.get("status"), "solver_entered": result.get("solver_entered", False)}, ensure_ascii=False), flush=True)
    finalize_accounting()


def finalize_accounting() -> None:
    a = read(ACCOUNTING); cases = a["cases"]
    for c in cases:
        cp = RUNTIME / "cases" / c["case_id"] / "checkpoint.json"
        c["attempted"] = cp.exists() or c.get("solver_entered", False)
        if cp.exists(): c["accepted"] = True; c["solver_entered"] = True
    a["entered_formal_subruns"] = sum(bool(c.get("solver_entered")) for c in cases); a["accepted_formal_subruns"] = sum(bool(c.get("accepted")) for c in cases); a["quarantined_formal_subruns"] = sum(bool(c.get("quarantined")) for c in cases); write(ACCOUNTING, a)


def finalize(manifest: dict[str, Any]) -> None:
    base = patch_runner(); full = []; summaries = []; leverage = []
    for child in manifest["candidates"]:
        pol_rows = {}; missing = []
        for pol in POLARIZATIONS:
            path = RUNTIME / "cases" / child["broadband_case_identity"][pol]["case_uid"] / "checkpoint.json"
            if path.exists(): pol_rows[pol] = read(path)["rows"]
            else: missing.append(pol)
        if missing:
            summaries.append({"geometry_uid": child["geometry_uid"], "exact_hash": child["exact_hash"], "parent_uid": child["parent_uid"], "broadband_status": "INCONCLUSIVE_MISSING_POLARIZATION", "projector_pass_count": None, "failed_wavelengths": None, "worst_projector_error": None, "minimum_projector_margin": None, "min_Txx": None, "min_throughput": None, "phase_trajectory_deg": None, "missing_polarizations": missing, "solver_replay": False})
            continue
        rows = []
        for i, w in enumerate(GRID):
            x, y = pol_rows["x"][i], pol_rows["y"][i]
            jones = [[complex(x["weighted_Ex_real"], x["weighted_Ex_imag"]), complex(y["weighted_Ex_real"], y["weighted_Ex_imag"])], [complex(x["weighted_Ey_real"], x["weighted_Ey_imag"]), complex(y["weighted_Ey_real"], y["weighted_Ey_imag"])]]
            m = base.metrics(jones); row = {"geometry_uid": child["geometry_uid"], "exact_hash": child["exact_hash"], "parent_uid": child["parent_uid"], "role": child["role"], "d_nm": child["d_nm"], "J1_length_nm": child["J1_length_nm"], "J1_width_nm": child["J1_width_nm"], "wavelength_nm": w, **m, "throughput": (float(x["source_T"]) + float(y["source_T"])) / 2.0, "x_source_T": x["source_T"], "y_source_T": y["source_T"], "x_accepted": True, "y_accepted": True, "full_jones_accepted": m["full_jones_finite"], "broadband_status": "", "solver_replay": False, "ml_admitted": False}; rows.append(row); full.append(row)
        status = base.status_from_rows(rows)
        for row in rows: row.update(status)
        summaries.append({"geometry_uid": child["geometry_uid"], "exact_hash": child["exact_hash"], "parent_uid": child["parent_uid"], **status, "phase_trajectory_deg": [r["phi_txx"] for r in rows], "missing_polarizations": [], "solver_replay": False})
        parent = manifest["parents"][child["parent_uid"]]; pp = [r["phi_deg"] for r in parent["trajectory"]]; cp = [r["phi_txx"] for r in rows]; delta = [cdiff(a, b) for a, b in zip(cp, pp)]
        leverage.append({"geometry_uid": child["geometry_uid"], "parent_uid": child["parent_uid"], "delta_phi_deg": delta, "median_delta_phi_deg": sorted(delta)[len(delta)//2], "min_delta_phi_deg": min(delta), "max_delta_phi_deg": max(delta), "spectral_spread_deg": max(delta)-min(delta), "sign_consistent": all(x >= 0 for x in delta) or all(x <= 0 for x in delta)})
    write_csv(REPORT / "h1e1_broadband_full_jones.csv", full); write_csv(REPORT / "h1e1_geometry_summary.csv", summaries); write_csv(REPORT / "h1e1_parent_child_phase_leverage.csv", leverage)
    old = [{"geometry_uid": x["geometry_uid"], "phase_trajectory_deg": [r["phi_deg"] for r in x["trajectory"]], "broadband_status": "BROADBAND_PROJECTOR_COMPATIBLE_STRICT", "exact_hash": x["exact_hash"]} for x in read(STRICT_BANK)["geometries"]]
    strict_new = [x for x in summaries if x["broadband_status"] == "BROADBAND_PROJECTOR_COMPATIBLE_STRICT"]
    before = coverage([x["phase_trajectory_deg"][0] for x in old]); after = coverage([x["phase_trajectory_deg"][0] for x in old + strict_new])
    write(REPORT / "h1e1_strict_bank_updated.json", {"schema": "H1E1_STRICT_BANK_UPDATED_V1", "old_count": len(old), "new_strict_count": len(strict_new), "geometries": old + strict_new, "coverage_before": before, "coverage_after": after})
    six_before = six_bin_optimize(old)
    six_after = six_bin_optimize(old + strict_new)
    write(REPORT / "h1e1_six_bin_screening.json", {"schema": "H1E1_SIX_BIN_SCREENING_V1", "status": "OFFLINE_ONLY_NO_NEW_SOLVER", "old_strict_count": len(old), "new_strict_count": len(strict_new), "coverage_before": before, "coverage_after": after, "before": six_before, "after": six_after, "best_six_bin_tuple_before": six_before.get("best"), "best_six_bin_tuple_after": six_after.get("best"), "phase_bin_error_threshold": "NOT_FROZEN", "solver_replay": False})
    accepted = len(strict_new) * 9
    write(REPORT / "h1e1_extended_registry_audit.json", {"schema": "LP_HF_EXTENDED_REGISTRY_H1E1_V1", "old_local_dimer_rows": 488, "old_rows_grammar_version": "J1_ISOTROPIC_V1", "new_rows": accepted, "new_rows_grammar_version": "J1_INDEPENDENT_ANISOTROPY_V1", "ml_eligible": True, "ml_admitted": False, "split": "UNASSIGNED", "canonical_registry_unchanged": True})
    accounting = read(ACCOUNTING); complete_children = sum(x.get("phase_trajectory_deg") is not None for x in summaries)
    write(REPORT / "h1e1_final.json", {"schema": "H1E1_FINAL_V1", "status": "PASS" if complete_children == 8 else "PARTIAL", "physics_outcome": "INCONCLUSIVE" if complete_children < 8 else "PENDING_CLASSIFICATION", "planned_geometries": 8, "planned_formal_subruns": 16, "entered_formal_subruns": accounting["entered_formal_subruns"], "accepted_formal_subruns": accounting["accepted_formal_subruns"], "quarantined_formal_subruns": accounting["quarantined_formal_subruns"], "new_strict_children": len(strict_new), "complete_full_jones_children": complete_children, "missing_full_jones_children": [x["geometry_uid"] for x in summaries if x.get("phase_trajectory_deg") is None], "coverage_before": before, "coverage_after": after, "ml_admitted": False, "broader_6d_search": False})
    REPORT.mkdir(parents=True, exist_ok=True); (REPORT / "h1e1_summary.md").write_text(f"# H1E-1 J1 anisotropy\n\n- Children with complete full-Jones evidence: {complete_children}/8; formal subruns entered/accepted/quarantined: {accounting['entered_formal_subruns']}/{accounting['accepted_formal_subruns']}/{accounting['quarantined_formal_subruns']}.\n- New strict children: {len(strict_new)}.\n- ML admitted: false.\n- Incomplete evidence is preserved; no replay was performed.\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--prepare", action="store_true"); ap.add_argument("--run", action="store_true"); ap.add_argument("--finalize", action="store_true"); args = ap.parse_args()
    if args.prepare:
        m = make_manifest(); initialize_accounting(m); print(json.dumps({"status": m["status"], "children": len(m["candidates"]), "solver_entered": False}, indent=2)); return 0
    m = read(MANIFEST)
    if args.run: run_all(m); return 0
    if args.finalize: finalize(m); return 0
    ap.error("choose --prepare, --run, or --finalize")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
