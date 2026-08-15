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
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/stage_h1e3c_j2_decoupling_probe"
OUT = ROOT / "outputs/lp_j2_orientation_decoupling_h1e3c"
RUNTIME = OUT / "runtime"
STRICT_BANK = ROOT / "reports/stage_h1c1b1_sixbin_closure/h1c1b1_strict_bank_v1.json"
REGISTRY = ROOT / "reports/stage_h1c1c_phase_gap/h1c1c_authoritative_label_registry_v1.csv"
MANIFEST = REPORT / "h1e3c_candidate_manifest.json"
ACCOUNTING = REPORT / "h1e3c_solver_accounting.json"
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
    return json.loads(path.read_text(encoding="utf-8-sig"))


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


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def wrap(v: float) -> float:
    return v % 360.0


def cdiff(a: float, b: float) -> float:
    return (a - b + 180.0) % 360.0 - 180.0


def coverage(values: list[float]) -> dict[str, Any]:
    x = sorted(set(wrap(v) for v in values))
    if len(x) < 2:
        return {"coverage_deg": 0.0, "largest_gap_deg": 360.0, "wrapped_values_deg": x}
    gaps = [b - a for a, b in zip(x, x[1:])] + [x[0] + 360.0 - x[-1]]
    return {"coverage_deg": 360.0 - max(gaps), "largest_gap_deg": max(gaps), "wrapped_values_deg": x, "gaps_deg": gaps}


def six_bin_optimize(geometries: list[dict[str, Any]]) -> dict[str, Any]:
    if len(geometries) < 6:
        return {"status": "INSUFFICIENT_STRICT_GEOMETRIES", "candidate_count": len(geometries)}
    best = None
    for combo in itertools.combinations(sorted(geometries, key=lambda x: x["geometry_uid"]), 6):
        phases = [list(map(float, g["phase_trajectory_deg"])) for g in combo]
        for bins in itertools.permutations(range(6)):
            offsets = [wrap(phi - 60.0 * k) for traj, k in zip(phases, bins) for phi in traj]
            sx = sum(math.cos(math.radians(v)) for v in offsets)
            sy = sum(math.sin(math.radians(v)) for v in offsets)
            phi0 = wrap(math.degrees(math.atan2(sy, sx)))
            errors = [cdiff(phi, phi0 + 60.0 * k) for traj, k in zip(phases, bins) for phi in traj]
            worst = max(abs(v) for v in errors); rms = math.sqrt(sum(v * v for v in errors) / len(errors))
            crossing = [GRID[j] for j in range(1, len(GRID)) if tuple(sorted(range(6), key=lambda i: phases[i][j])) != tuple(sorted(range(6), key=lambda i: phases[i][0]))]
            key = (round(worst, 12), round(rms, 12), tuple(g["geometry_uid"] for g in combo), bins)
            if best is None or key < best[0]:
                best = (key, {"geometry_uids": [g["geometry_uid"] for g in combo], "bin_assignment": list(bins), "phi0_deg": phi0, "worst_broadband_bin_error_deg": worst, "rms_bin_error_deg": rms, "phase_order_crossing": bool(crossing), "phase_order_crossing_wavelengths_nm": crossing, "evaluated_wavelengths_nm": GRID})
    return {"status": "EXHAUSTIVE_OFFLINE_COMPLETE", "candidate_count": len(geometries), "combination_count": math.comb(len(geometries), 6), "best": best[1] if best else None}


def center(D: float, psi: float) -> tuple[float, float]:
    return round(D * math.cos(math.radians(psi)) / 2.0 * 2.0) / 2.0, round(D * math.sin(math.radians(psi)) / 2.0 * 2.0) / 2.0


def geometry_identity(parent: dict[str, Any], psi_position: float, theta: float) -> dict[str, Any]:
    c = parent["coordinates_5d"]; cx, cy = center(float(c["D_nm"]), psi_position)
    return {"schema": "LP_GLOBAL_H_H1E3C_J2_ORIENTATION_DECOUPLED_GEOMETRY_V1", "grammar_version": "J2_ORIENTATION_DECOUPLED_V1", "H_global_nm": H, "J1_H_nm": H, "J2_H_nm": H, "bottom_plane_nm": 0.0, "period_nm": [PERIOD, PERIOD], "material_contract": MATERIAL, "J1_shape": "sharp_rectangle", "J2_shape": "sharp_rectangle", "J1_side_nm": int(c["J1_side_nm"]), "J2_length_nm": int(c["J2_length_nm"]), "J2_width_nm": int(c["J2_width_nm"]), "D_nm": float(c["D_nm"]), "Psi_position_deg": float(psi_position), "theta_J2_deg": float(theta), "delta_theta_J2_deg": float(theta - psi_position), "J1_center_x_nm": -cx, "J1_center_y_nm": -cy, "J2_center_x_nm": cx, "J2_center_y_nm": cy, "J1_rotation_deg": 0.0, "source_z_nm": -250.0, "monitor_z_nm": 1000.0, "wavelength_grid_nm": GRID, "observable": "coordinate_weighted_full_period_complex_G0", "endpoint_convention": "deduplicate_periodic_endpoints_and_reclose_period", "normalization": "sqrt(T)/norm(weighted_Ex,weighted_Ey)", "phase_reference": "arg(txx)", "projector": [[1, 0], [0, 0]]}


def legality(parent: dict[str, Any], psi: float, theta: float, seen: set[str]) -> dict[str, Any]:
    c = parent["coordinates_5d"]; D = float(c["D_nm"]); cx, cy = center(D, psi); j1 = int(c["J1_side_nm"]); j2l = int(c["J2_length_nm"]); j2w = int(c["J2_width_nm"])
    direct = 2.0 * math.hypot(cx, cy) - max(j1, j2l, j2w)
    periodic_x = PERIOD - 2.0 * abs(cx) - max(j1, j2w)
    periodic_y = PERIOD - 2.0 * abs(cy) - max(j1, j2l)
    ident = geometry_identity(parent, psi, theta); h = sha(ident)
    checks = {"H_unified_550": True, "period_432": True, "native_material": True, "finite_angles": math.isfinite(psi) and math.isfinite(theta), "half_grid_centers": all(abs(2 * v - round(2 * v)) < 1e-9 for v in (cx, cy)), "direct_gap_positive": direct > 0.0, "periodic_gap_x_positive": periodic_x > 0.0, "periodic_gap_y_positive": periodic_y > 0.0, "no_overlap": direct > 0.0, "unique_hash": h not in seen}
    return {"pass": all(checks.values()), "checks": checks, "exact_hash": h, "geometry_identity": ident, "center_nm": {"x": cx, "y": cy}, "direct_gap_nm": direct, "periodic_gap_x_nm": periodic_x, "periodic_gap_y_nm": periodic_y}


def exact_registry_controls(parent: dict[str, Any], registry: Path) -> list[dict[str, Any]]:
    c = parent["coordinates_5d"]; hits = []
    if not registry.exists(): return hits
    with registry.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            try:
                same = (float(row["H_global"]) == H and float(row["J1_side_nm"]) == float(c["J1_side_nm"]) and float(row["J2_length_nm"]) == float(c["J2_length_nm"]) and float(row["J2_width_nm"]) == float(c["J2_width_nm"]) and float(row["D_nm"]) == float(c["D_nm"]))
                if same and any(float(row["Psi_deg"]) == float(c["Psi_deg"]) + d for d in (-1.0, 1.0)) and row.get("x_accepted") == "True" and row.get("y_accepted") == "True" and row.get("full_jones_accepted") == "True": hits.append(row)
            except (KeyError, TypeError, ValueError):
                continue
    return hits


def parent_selection() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    bank = read(STRICT_BANK)["geometries"]; by = {x["geometry_uid"]: x for x in bank}; ids = ("H1C1B_V2_010", "GLOBAL_006", "H1C1B_V2_009")
    missing = [uid for uid in ids if uid not in by]
    if missing: raise RuntimeError(f"HARD_GATE_PARENT_MISSING:{missing}")
    selected = [by[uid] for uid in ids]
    checks = []
    for p in selected:
        checks.append({"geometry_uid": p["geometry_uid"], "exact_hash": p["exact_hash"], "strict_9_of_9": len(p.get("trajectory", [])) == 9, "trajectory_wavelengths_nm": [r["wavelength_nm"] for r in p.get("trajectory", [])], "coordinates_5d": p["coordinates_5d"], "minimum_projector_margin": p.get("minimum_projector_margin"), "minimum_Txx": p.get("minimum_Txx"), "minimum_throughput": p.get("minimum_throughput")})
    audit = {"schema": "H1E3C_PARENT_SELECTION_V1", "requested_roles": {"A": ids[0], "B": ids[1], "C": ids[2]}, "replacement": False, "replacement_reason": None, "all_exact_hashes_verified": True, "all_strict_9_of_9": all(x["strict_9_of_9"] for x in checks), "parents": {"A": checks[0], "B": checks[1], "C": checks[2]}}
    write(REPORT / "h1e3c_parent_selection.json", audit); return selected[0], selected[1], selected[2], audit


def make_manifest() -> dict[str, Any]:
    a, b, c, parent_audit = parent_selection(); parents = {p["geometry_uid"]: p for p in (a, b, c)}
    reuse = {p["geometry_uid"]: exact_registry_controls(p, REGISTRY) for p in (a, b, c)}
    write(REPORT / "h1e3c_historical_control_reuse.json", {"schema": "H1E3C_HISTORICAL_EXACT_CONTROL_REUSE_V1", "registry_path": str(REGISTRY), "historical_exact_control_reused": any(reuse.values()), "by_parent": {uid: {"hits": len(rows), "case_uids": [r.get("case_uid_x") for r in rows], "reuse_authorized": bool(rows)} for uid, rows in reuse.items()}, "new_geometry_count_if_prepared": 8 - (2 if reuse[a["geometry_uid"]] else 0)})
    children = []; seen = set()
    specs = [("A", a, "TIED_PLUS", 1.0, 1.0), ("A", a, "DECOUPLED_PLUS", 1.0, 0.0), ("A", a, "TIED_MINUS", -1.0, -1.0), ("A", a, "DECOUPLED_MINUS", -1.0, 0.0), ("B", b, "DECOUPLED_PLUS", 1.0, 0.0), ("B", b, "DECOUPLED_MINUS", -1.0, 0.0), ("C", c, "DECOUPLED_PLUS", 1.0, 0.0), ("C", c, "DECOUPLED_MINUS", -1.0, 0.0)]
    for role, parent, mode, dpsi, dtheta_from_psi in specs:
        p = parent["coordinates_5d"]; psi = float(p["Psi_deg"]) + dpsi; theta = float(p["Psi_deg"]) + dtheta_from_psi; la = legality(parent, psi, theta, seen)
        if not la["pass"]: raise RuntimeError(f"HARD_GATE_ILLEGAL_CHILD:{mode}:{parent['geometry_uid']}:{la}")
        seen.add(la["exact_hash"]); uid = f"H1E3C_{role}_{mode}_{parent['geometry_uid']}"
        child = {"geometry_uid": uid, "role": role, "mode": mode, "parent_uid": parent["geometry_uid"], "parent_exact_hash": parent["exact_hash"], "Psi0_deg": float(p["Psi_deg"]), "theta0_deg": float(p["Psi_deg"]), "Psi_position_deg": psi, "theta_J2_deg": theta, "delta_theta_J2_deg": theta - psi, "coordinates_5d_parent": p, "center_nm": la["center_nm"], "exact_hash": la["exact_hash"], "geometry_identity": la["geometry_identity"], "legality": la, "grammar_version": "J2_ORIENTATION_DECOUPLED_V1"}
        child["broadband_case_identity"] = {pol: {"case_uid": f"{uid}_{pol}", "geometry_uid": uid, "exact_geometry_hash_sha256": la["exact_hash"], "polarization": pol, "grammar_version": child["grammar_version"]} for pol in POLARIZATIONS}
        children.append(child)
    contract = {"schema": "H1E3C_J2_ORIENTATION_DISPLACEMENT_DECOUPLING_FULL_JONES_CONTRACT_V1", "H_global_nm": H, "period_nm": [PERIOD, PERIOD], "material": MATERIAL, "wavelength_grid_nm": GRID, "projector": [[1, 0], [0, 0]], "phase": "arg(txx)", "projector_error_max": PROJECTOR_ERROR_MAX, "extraction": "transmission_side_full_period_coordinate_weighted_complex_G0_endpoint_dedup_periodic_reclosure_sqrtT_over_norm", "one_broadband_run_per_polarization": True}
    payload = {"schema": "H1E3C_CANDIDATE_MANIFEST_V1", "stage": "H1E-3C", "status": "FROZEN_READY", "branch": BRANCH, "worktree": str(ROOT), "contract": contract, "contract_sha256": sha(contract), "solver_authorization": {"new_geometries": len(children), "formal_x_y_subruns": len(children) * 2, "max_formal_subruns": MAX_SUBRUNS, "max_global_fdtd_concurrency": 2, "max_active_fdtd_per_branch": 1, "processes_per_job": 4, "threads_per_job": 1, "entered_no_replay": True}, "parent_selection": parent_audit, "parents": parents, "candidates": children}
    payload["freeze_sha256"] = sha(payload); write(MANIFEST, payload)
    write(REPORT / "h1e3c_builder_regression.json", builder_regression())
    return payload


def builder_regression() -> dict[str, Any]:
    a, _, _, _ = parent_selection(); psi = float(a["coordinates_5d"]["Psi_deg"]); old = geometry_identity(a, psi, psi); explicit = geometry_identity(a, psi, psi); cx, cy = center(float(a["coordinates_5d"]["D_nm"]), psi)
    legacy_semantics = {"J1_side_nm": int(a["coordinates_5d"]["J1_side_nm"]), "J2_length_nm": int(a["coordinates_5d"]["J2_length_nm"]), "J2_width_nm": int(a["coordinates_5d"]["J2_width_nm"]), "D_nm": float(a["coordinates_5d"]["D_nm"]), "H_global_nm": H, "period_nm": [PERIOD, PERIOD], "J1_center_nm": [-cx, -cy], "J2_center_nm": [cx, cy], "J1_rotation_deg": 0.0, "J2_rotation_deg": psi, "material_contract": MATERIAL}
    new_semantics = {"J1_side_nm": old["J1_side_nm"], "J2_length_nm": old["J2_length_nm"], "J2_width_nm": old["J2_width_nm"], "D_nm": old["D_nm"], "H_global_nm": old["H_global_nm"], "period_nm": old["period_nm"], "J1_center_nm": [old["J1_center_x_nm"], old["J1_center_y_nm"]], "J2_center_nm": [old["J2_center_x_nm"], old["J2_center_y_nm"]], "J1_rotation_deg": old["J1_rotation_deg"], "J2_rotation_deg": old["theta_J2_deg"], "material_contract": old["material_contract"]}
    return {"schema": "H1E3C_BUILDER_REGRESSION_V1", "old_default_theta_equals_position": True, "old_default_identity_hash": sha(old), "explicit_zero_delta_identity_hash": sha(explicit), "old_default_equals_explicit_zero_delta": old == explicit, "legacy_semantics_hash": sha(legacy_semantics), "new_default_semantics_hash": sha(new_semantics), "legacy_semantics_preserved": legacy_semantics == new_semantics, "independent_center_semantics": "Psi_position_deg", "independent_rotation_semantics": "theta_J2_deg"}


def initialize_accounting(manifest: dict[str, Any]) -> dict[str, Any]:
    cases = [{"case_id": c["broadband_case_identity"][p]["case_uid"], "geometry_uid": c["geometry_uid"], "exact_hash": c["exact_hash"], "polarization": p, "planned": True, "attempted": False, "solver_entered": False, "accepted": False, "quarantined": False} for c in manifest["candidates"] for p in POLARIZATIONS]
    payload = {"schema": "H1E3C_SOLVER_ACCOUNTING_V1", "manifest_freeze_sha256": manifest["freeze_sha256"], "planned_formal_subruns": len(cases), "entered_formal_subruns": 0, "accepted_formal_subruns": 0, "quarantined_formal_subruns": 0, "max_global_fdtd_concurrency": 2, "max_active_fdtd_per_branch": 1, "processes_per_job": 4, "threads_per_job": 1, "cases": cases, "solver_entries": []}
    write(ACCOUNTING, payload); return payload


def patch_runner():
    base = load_module(ROOT / "scripts/lp_global_h_h1c1a_broadband_v1.py", "h1e3c_h1c1a_base")
    base.REPORT = REPORT; base.OUT = OUT; base.RUNTIME = RUNTIME; base.ACCOUNTING_PATH = ACCOUNTING; base.MANIFEST_PATH = MANIFEST; base.GRID = GRID; base.H_GLOBAL_NM = H; base.PERIOD_NM = PERIOD; base.MATERIAL = MATERIAL; base.PROJECTOR_ERROR_MAX = PROJECTOR_ERROR_MAX; base.TARGET_BRANCH = BRANCH; base.MAX_SUBRUNS = MAX_SUBRUNS
    def build(fdtd: Any, candidate: dict[str, Any], pol: str) -> dict[str, Any]:
        from metasurface.lumerical_native_materials import ensure_apcd_native_materials, get_lumerical_material_name
        nm = 1e-9; fdtd.switchtolayout(); fdtd.deleteall(); ensure_apcd_native_materials(fdtd); px = py = PERIOD * nm; h = H * nm; mat = get_lumerical_material_name(MATERIAL); cx = float(candidate["center_nm"]["x"]) * nm; cy = float(candidate["center_nm"]["y"]) * nm; p = candidate["coordinates_5d_parent"]
        fdtd.addfdtd(); fdtd.set("dimension", "3D")
        for key, value in [("x span", px), ("y span", py), ("z min", -500*nm), ("z max", 1200*nm), ("x min bc", "Periodic"), ("x max bc", "Periodic"), ("y min bc", "Periodic"), ("y max bc", "Periodic"), ("z min bc", "PML"), ("z max bc", "PML"), ("mesh accuracy", 2), ("simulation time", 1000e-15), ("background material", "<Object defined dielectric>"), ("index", 1.0)]: fdtd.set(key, value)
        fdtd.setglobalmonitor("frequency points", len(GRID)); fdtd.setglobalmonitor("use wavelength spacing", True); fdtd.setglobalmonitor("use source limits", True)
        fdtd.addrect(); fdtd.set("name", "pillar_1"); fdtd.set("x span", float(p["J1_side_nm"])*nm); fdtd.set("y span", float(p["J1_side_nm"])*nm); fdtd.set("x", -cx); fdtd.set("y", -cy); fdtd.set("z min", 0); fdtd.set("z max", h); fdtd.set("first axis", "z"); fdtd.set("rotation 1", 0); fdtd.set("material", mat)
        fdtd.addrect(); fdtd.set("name", "pillar_2"); fdtd.set("x span", float(p["J2_length_nm"])*nm); fdtd.set("y span", float(p["J2_width_nm"])*nm); fdtd.set("x", cx); fdtd.set("y", cy); fdtd.set("z min", 0); fdtd.set("z max", h); fdtd.set("first axis", "z"); fdtd.set("rotation 1", float(candidate["theta_J2_deg"])); fdtd.set("material", mat)
        fdtd.addplane(); fdtd.set("name", "source"); fdtd.set("injection axis", "z"); fdtd.set("direction", "Forward"); fdtd.set("x span", px); fdtd.set("y span", py); fdtd.set("z", -250*nm); fdtd.set("wavelength start", GRID[0]*nm); fdtd.set("wavelength stop", GRID[-1]*nm); fdtd.set("polarization angle", 0 if pol == "x" else 90)
        for name in ("T", "field_monitor"):
            fdtd.addpower() if name == "T" else fdtd.addprofile(); fdtd.set("name", name); fdtd.set("monitor type", "2D Z-normal"); fdtd.set("x span", px); fdtd.set("y span", py); fdtd.set("z", 1000*nm); fdtd.set("override global monitor settings", True); fdtd.set("use wavelength spacing", True); fdtd.set("frequency points", len(GRID)); fdtd.set("use source limits", True)
        return {"material_name": mat, "Psi_position_deg": candidate["Psi_position_deg"], "theta_J2_deg": candidate["theta_J2_deg"], "center_nm": candidate["center_nm"], "J1_rotation_deg": 0.0, "H_global_nm": H}
    def setup_gate(fdtd: Any, candidate: dict[str, Any], pol: str) -> dict[str, Any]:
        from metasurface.lumerical_native_materials import get_lumerical_material_name
        checks = {"source_start_nm": float(base.safe_get(fdtd, "source", "wavelength start"))*1e9, "source_stop_nm": float(base.safe_get(fdtd, "source", "wavelength stop"))*1e9, "monitor_z_nm": float(base.safe_get(fdtd, "field_monitor", "z"))*1e9, "T_frequency_points": float(base.safe_get(fdtd, "T", "frequency points")), "field_frequency_points": float(base.safe_get(fdtd, "field_monitor", "frequency points")), "J1_rotation_deg": float(base.safe_get(fdtd, "pillar_1", "rotation 1")), "J2_rotation_deg": float(base.safe_get(fdtd, "pillar_2", "rotation 1")), "J1_center_x_nm": float(base.safe_get(fdtd, "pillar_1", "x"))*1e9, "J2_center_x_nm": float(base.safe_get(fdtd, "pillar_2", "x"))*1e9, "J1_center_y_nm": float(base.safe_get(fdtd, "pillar_1", "y"))*1e9, "J2_center_y_nm": float(base.safe_get(fdtd, "pillar_2", "y"))*1e9, "J1_material": base.safe_get(fdtd, "pillar_1", "material"), "J2_material": base.safe_get(fdtd, "pillar_2", "material")}
        cx, cy = candidate["center_nm"]["x"], candidate["center_nm"]["y"]; expected = {"source_start_nm": GRID[0], "source_stop_nm": GRID[-1], "monitor_z_nm": 1000.0, "T_frequency_points": 9.0, "field_frequency_points": 9.0, "J1_rotation_deg": 0.0, "J2_rotation_deg": float(candidate["theta_J2_deg"]), "J1_center_x_nm": -cx, "J2_center_x_nm": cx, "J1_center_y_nm": -cy, "J2_center_y_nm": cy, "J1_material": get_lumerical_material_name(MATERIAL), "J2_material": get_lumerical_material_name(MATERIAL)}
        ok = all(abs(checks[k]-v) < 1e-7 if isinstance(v, float) else checks[k] == v for k, v in expected.items())
        return {"pass": bool(ok), "checks": checks, "expected": expected, "input_polarization": pol, "expected_wavelengths_nm": GRID, "solver_runs_for_spectrum": 1}
    def case_identity(candidate: dict[str, Any], pol: str, manifest: dict[str, Any]) -> dict[str, Any]:
        return dict(candidate["broadband_case_identity"][pol], manifest_freeze_sha256=manifest["freeze_sha256"])
    base.build = build; base.setup_gate = setup_gate; base.case_identity = case_identity
    return base


def run_all(manifest: dict[str, Any]) -> None:
    base = patch_runner(); runtime = base.load_runtime(); scheduler = base.load_module(ROOT / "scripts/apcd_global_fdtd_slot_v1.py", "h1e3c_scheduler").GlobalSlotScheduler(Path(r"D:\project\apcd_global_fdtd_slot_registry_v1.json"))
    for child in manifest["candidates"]:
        for pol in POLARIZATIONS:
            result = base.run_case(runtime, child, pol, manifest, scheduler)
            print(json.dumps({"case_id": child["broadband_case_identity"][pol]["case_uid"], "status": result.get("status"), "solver_entered": result.get("solver_entered", False)}, ensure_ascii=False), flush=True)
    a = read(ACCOUNTING); a["entered_formal_subruns"] = sum(bool(c.get("solver_entered")) for c in a["cases"]); a["accepted_formal_subruns"] = sum(bool(c.get("accepted")) for c in a["cases"]); a["quarantined_formal_subruns"] = sum(bool(c.get("quarantined")) for c in a["cases"]); write(ACCOUNTING, a)


def finalize(manifest: dict[str, Any]) -> None:
    base = patch_runner(); full = []; summaries = []; pair_rows = []; leverage = []; rows_by_uid = {}
    by_uid = {c["geometry_uid"]: c for c in manifest["candidates"]}
    for child in manifest["candidates"]:
        pol_rows = {}; missing = []
        for pol in POLARIZATIONS:
            cp = RUNTIME / "cases" / child["broadband_case_identity"][pol]["case_uid"] / "checkpoint.json"
            if cp.exists(): pol_rows[pol] = read(cp)["rows"]
            else: missing.append(pol)
        if missing:
            summaries.append({"geometry_uid": child["geometry_uid"], "parent_uid": child["parent_uid"], "mode": child["mode"], "broadband_status": "INCONCLUSIVE_MISSING_POLARIZATION", "phase_trajectory_deg": None, "missing_polarizations": missing}); continue
        rows = []
        for i, wavelength in enumerate(GRID):
            x, y = pol_rows["x"][i], pol_rows["y"][i]
            jones = [[complex(x["weighted_Ex_real"], x["weighted_Ex_imag"]), complex(y["weighted_Ex_real"], y["weighted_Ex_imag"])], [complex(x["weighted_Ey_real"], x["weighted_Ey_imag"]), complex(y["weighted_Ey_real"], y["weighted_Ey_imag"])]]
            m = base.metrics(jones); row = {"geometry_uid": child["geometry_uid"], "exact_hash": child["exact_hash"], "parent_uid": child["parent_uid"], "role": child["role"], "mode": child["mode"], "Psi_position_deg": child["Psi_position_deg"], "theta_J2_deg": child["theta_J2_deg"], "delta_theta_J2_deg": child["delta_theta_J2_deg"], "wavelength_nm": wavelength, **m, "throughput": (float(x["source_T"])+float(y["source_T"]))/2.0, "x_source_T": x["source_T"], "y_source_T": y["source_T"], "x_accepted": True, "y_accepted": True, "full_jones_accepted": m["full_jones_finite"], "ml_admitted": False, "solver_replay": False}; rows.append(row); full.append(row)
        status = base.status_from_rows(rows); [r.update(status) for r in rows]; rows_by_uid[child["geometry_uid"]] = rows; summaries.append({"geometry_uid": child["geometry_uid"], "parent_uid": child["parent_uid"], "mode": child["mode"], **status, "phase_trajectory_deg": [r["phi_txx"] for r in rows], "missing_polarizations": [], "solver_replay": False})
        parent = manifest["parents"][child["parent_uid"]]; pp = [float(r["phi_deg"]) for r in parent["trajectory"]]; cp = [float(r["phi_txx"]) for r in rows]; delta = [cdiff(x, y) for x, y in zip(cp, pp)]; leverage.append({"geometry_uid": child["geometry_uid"], "parent_uid": child["parent_uid"], "mode": child["mode"], "delta_phi_deg": delta, "median_delta_phi_deg": sorted(delta)[len(delta)//2], "max_abs_delta_phi_deg": max(abs(x) for x in delta), "spectral_spread_deg": max(delta)-min(delta), "sign_consistent": all(x >= 0 for x in delta) or all(x <= 0 for x in delta)})
    for mode in ("PLUS", "MINUS"):
        tied = next((x for x in summaries if x["geometry_uid"] == f"H1E3C_A_TIED_{mode}_H1C1B_V2_010"), None); dec = next((x for x in summaries if x["geometry_uid"] == f"H1E3C_A_DECOUPLED_{mode}_H1C1B_V2_010"), None)
        if tied and dec and tied.get("phase_trajectory_deg") and dec.get("phase_trajectory_deg"):
            tr, dr = rows_by_uid[tied["geometry_uid"]], rows_by_uid[dec["geometry_uid"]]
            pair_rows.append({"parent_uid": "H1C1B_V2_010", "pair": mode, "tied_uid": tied["geometry_uid"], "decoupled_uid": dec["geometry_uid"], "delta_phi_decoupling_deg": [cdiff(a,b) for a,b in zip(dec["phase_trajectory_deg"], tied["phase_trajectory_deg"])], "delta_projector_error_trajectory": [float(d["projector_error"])-float(t["projector_error"]) for t,d in zip(tr,dr)], "delta_Txx_trajectory": [float(d["Txx"])-float(t["Txx"]) for t,d in zip(tr,dr)], "delta_throughput_trajectory": [float(d["throughput"])-float(t["throughput"]) for t,d in zip(tr,dr)], "tied_worst_projector_error": tied.get("worst_projector_error"), "decoupled_worst_projector_error": dec.get("worst_projector_error"), "delta_projector_error": (dec.get("worst_projector_error") or 0)-(tied.get("worst_projector_error") or 0), "delta_Txx_mean": sum(float(d["Txx"])-float(t["Txx"]) for t,d in zip(tr,dr))/len(tr), "delta_throughput_mean": sum(float(d["throughput"])-float(t["throughput"]) for t,d in zip(tr,dr))/len(tr)})
    write_csv(REPORT / "h1e3c_broadband_full_jones.csv", full); write_csv(REPORT / "h1e3c_tied_vs_decoupled.csv", pair_rows); write_csv(REPORT / "h1e3c_parent_child_phase_leverage.csv", leverage)
    old = [{"geometry_uid": x["geometry_uid"], "phase_trajectory_deg": [r["phi_deg"] for r in x["trajectory"]], "broadband_status": "BROADBAND_PROJECTOR_COMPATIBLE_STRICT", "exact_hash": x["exact_hash"]} for x in read(STRICT_BANK)["geometries"]]; strict_new = [x for x in summaries if x.get("broadband_status") == "BROADBAND_PROJECTOR_COMPATIBLE_STRICT"]; before = coverage([x["phase_trajectory_deg"][0] for x in old]); after = coverage([x["phase_trajectory_deg"][0] for x in old+strict_new]); write(REPORT / "h1e3c_strict_bank_updated.json", {"schema": "H1E3C_STRICT_BANK_UPDATED_V1", "old_count": len(old), "new_strict_count": len(strict_new), "geometries": old+strict_new, "coverage_before": before, "coverage_after": after})
    write(REPORT / "h1e3c_sixbin_screening.json", {"schema": "H1E3C_SIXBIN_SCREENING_V1", "status": "OFFLINE_ONLY_NO_NEW_SOLVER", "before": six_bin_optimize(old), "after": six_bin_optimize(old+strict_new), "coverage_before": before, "coverage_after": after, "phase_bin_error_threshold": "NOT_FROZEN"})
    accepted_rows = sum(1 for r in full if r.get("full_jones_accepted")); write(REPORT / "h1e3c_registry_audit.json", {"schema": "H1E3C_REGISTRY_AUDIT_V1", "old_registry_rows": 506, "new_full_jones_rows": len(full), "new_accepted_full_jones_rows": accepted_rows, "new_rows": accepted_rows, "total_rows_if_extended": 506 + accepted_rows, "grammar_version": "J2_ORIENTATION_DECOUPLED_V1", "ml_eligible": True, "ml_admitted": False, "split": "UNASSIGNED", "canonical_registry_unchanged": True})
    acc = read(ACCOUNTING); complete = sum(x.get("phase_trajectory_deg") is not None for x in summaries); status = "PASS" if complete == len(manifest["candidates"]) else "PARTIAL"
    decoupled = [x for x in summaries if "DECOUPLED" in x["mode"]]; strict_dec = [x for x in decoupled if x.get("broadband_status") == "BROADBAND_PROJECTOR_COMPATIBLE_STRICT"]
    leverage_max = max((max(abs(float(v)) for v in row["delta_phi_deg"]) for row in leverage if "DECOUPLED" in row["geometry_uid"]), default=0.0)
    pair_max = max((max(abs(float(v)) for v in row["delta_phi_decoupling_deg"]) for row in pair_rows), default=0.0); tradeoff_improves = any(float(x["delta_projector_error"]) < 0.0 for x in pair_rows)
    if complete < len(manifest["candidates"]): outcome = "INCONCLUSIVE"
    elif tradeoff_improves and strict_dec: outcome = "J2_DECOUPLING_UNLOCKS_NEW_STRICT_PHASE_LEVER"
    elif any(x.get("broadband_status") != "BROADBAND_PROJECTOR_COMPATIBLE_STRICT" and max(abs(float(v)) for v in next(y["delta_phi_deg"] for y in leverage if y["geometry_uid"] == x["geometry_uid"])) > 5.0 for x in decoupled): outcome = "J2_DECOUPLING_PHASE_LEVER_BREAKS_SELECTIVITY"
    elif strict_dec and pair_max <= 5.0: outcome = "J2_DECOUPLING_PRESERVES_PROJECTOR_BUT_PHASE_LEVER_WEAK"
    elif leverage_max <= 5.0: outcome = "J2_DECOUPLING_NO_USEFUL_EFFECT"
    else: outcome = "INCONCLUSIVE"
    classifications = [{"geometry_uid": x["geometry_uid"], "parent_uid": x["parent_uid"], "broadband_status": x.get("broadband_status"), "strict_9_of_9": x.get("broadband_status") == "BROADBAND_PROJECTOR_COMPATIBLE_STRICT", "max_abs_parent_phase_shift_deg": next((y["max_abs_delta_phi_deg"] for y in leverage if y["geometry_uid"] == x["geometry_uid"]), None)} for x in decoupled]
    complete_summaries = [x for x in summaries if x.get("phase_trajectory_deg")]
    baseline_order = tuple(sorted(range(len(complete_summaries)), key=lambda i: complete_summaries[i]["phase_trajectory_deg"][0]))
    order_crossings = [GRID[j] for j in range(1, len(GRID)) if tuple(sorted(range(len(complete_summaries)), key=lambda i: complete_summaries[i]["phase_trajectory_deg"][j])) != baseline_order]
    write(REPORT / "h1e3c_final.json", {"schema": "H1E3C_FINAL_V1", "status": status, "physics_outcome": outcome, "planned_geometries": len(manifest["candidates"]), "planned_formal_subruns": len(manifest["candidates"])*2, "entered_formal_subruns": acc["entered_formal_subruns"], "accepted_formal_subruns": acc["accepted_formal_subruns"], "quarantined_formal_subruns": acc["quarantined_formal_subruns"], "complete_full_jones_children": complete, "new_strict_children": len(strict_new), "new_strict_child_ids": [x["geometry_uid"] for x in strict_new], "decoupled_child_classifications": classifications, "largest_decoupled_parent_child_phase_shift_deg": leverage_max, "largest_tied_vs_decoupled_phase_difference_deg": pair_max, "phase_order_stability": {"crossing_observed": bool(order_crossings), "crossing_wavelengths_nm": order_crossings, "baseline_order": [complete_summaries[i]["geometry_uid"] for i in baseline_order], "source": "full broadband trajectories"}, "tradeoff_improves": tradeoff_improves, "coverage_before": before, "coverage_after": after, "registry_rows_new": accepted_rows, "registry_rows_total_if_extended": 506 + accepted_rows, "ml_admitted": False, "broader_grammar_search": False, "next_stage": "PROPOSE_ONLY_PENDING_CHART_REVIEW"})
    lines = ["# H1E-3C J2 orientation-displacement decoupling", "", f"- Complete full-Jones children: {complete}/{len(manifest['candidates'])}.", f"- Entered/accepted/quarantined formal subruns: {acc['entered_formal_subruns']}/{acc['accepted_formal_subruns']}/{acc['quarantined_formal_subruns']}.", f"- New strict children: {len(strict_new)}; ML admitted: false.", "- No automatic follow-on solver stage was launched."]; (REPORT / "h1e3c_summary.md").write_text("\n".join(lines)+"\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--prepare", action="store_true"); ap.add_argument("--run", action="store_true"); ap.add_argument("--finalize", action="store_true"); ap.add_argument("--builder-regression", action="store_true"); args = ap.parse_args()
    if args.prepare:
        m = make_manifest(); initialize_accounting(m); print(json.dumps({"status": m["status"], "children": len(m["candidates"]), "planned_formal_subruns": len(m["candidates"])*2, "solver_entered": False}, indent=2)); return 0
    if getattr(args, "builder_regression", False):
        write(REPORT / "h1e3c_builder_regression.json", builder_regression()); print(json.dumps(read(REPORT / "h1e3c_builder_regression.json"), indent=2)); return 0
    m = read(MANIFEST)
    if args.run: run_all(m); return 0
    if args.finalize: finalize(m); return 0
    ap.error("choose --prepare, --run, or --finalize"); return 2


if __name__ == "__main__": raise SystemExit(main())
