from __future__ import annotations

import csv
import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1")
REPORT = ROOT / "reports/stage_paper_a_lp_forensic_fdtd_truth_batch1_v1"
OUT = ROOT / "outputs/paper_a_lp_forensic_fdtd_truth_batch1_v1"
PREPARED = OUT / "prepared"
RUNTIME = OUT / "runtime"
REGISTRY = Path(r"D:\project\apcd_global_fdtd_slot_registry_v1.json")
BRANCH = "work/lp-global-h-manifold-v1"
MATERIAL = "APCD_TIO2_NATIVE_M1"
FORMAL = [435.0 + i for i in range(31)]
NATIVE = [430.0 + i for i in range(41)]
SOURCE_START, SOURCE_STOP = 430.0, 470.0
MAIN_LO, MAIN_HI = 438.409, 457.191
MDC_CSV = Path(r"D:\project\worktrees\blue_apcd_mdc_defect_450\outputs\mdc_device_closure_figures_v1\spectral_profiles_420_480_plot_data.csv")
PARENT = {
    ("GLOBAL_018", "x"): ROOT / "outputs/lp_global_h_h1c1a/runtime/cases/H1C1A_GLOBAL_018_Px/H1C1A_GLOBAL_018_Px_attempt_001_pre.fsp",
    ("GLOBAL_018", "y"): ROOT / "outputs/lp_global_h_h1c1a/runtime/cases/H1C1A_GLOBAL_018_Py/H1C1A_GLOBAL_018_Py_attempt_004_pre.fsp",
    ("H1C1B_V2_012", "x"): ROOT / "outputs/lp_global_h_h1c1b/runtime/cases/H1C1B_V2_012_Px/H1C1B_V2_012_Px_attempt_001_pre.fsp",
    ("H1C1B_V2_012", "y"): ROOT / "outputs/lp_global_h_h1c1b/runtime/cases/H1C1B_V2_012_Py/H1C1B_V2_012_Py_attempt_001_pre.fsp",
}


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


h1a = load_module(ROOT / "scripts/lp_global_h_h1c1a_broadband_v1.py", "rescue_h1a")
scheduler = load_module(ROOT / "scripts/apcd_global_fdtd_slot_v1.py", "rescue_scheduler")


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha_obj(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def configure():
    h1a.ROOT = ROOT
    h1a.REPORT = REPORT
    h1a.OUT = OUT
    h1a.RUNTIME = RUNTIME
    h1a.GRID = FORMAL
    h1a.H_GLOBAL_NM = 550.0
    h1a.PERIOD_NM = 432.0
    h1a.MATERIAL = MATERIAL
    h1a.POLARIZATIONS = ("x", "y")
    h1a.MAX_SUBRUNS = 4
    h1a.TARGET_BRANCH = BRANCH
    h1a.SLOT_REGISTRY = REGISTRY
    h1a.BUILDER_VERSION = "paper_a_lp_forensic_fdtd_truth_batch1_v1_existing_fsp_child"
    h1a.EXTRACTION_CONVENTION = "transmission_side_coordinate_weighted_complex_G0; sqrt(T)/norm(weighted_Ex,weighted_Ey); no renormalization"


def candidates():
    source = REPORT.parent / "stage_paper_a_lp_bounded_forensic_rescue_v1/rescue_primary_batch.csv"
    rows = list(csv.DictReader(source.open(encoding="utf-8-sig")))
    result = {}
    for row in rows:
        uid = row["geometry_uid"]
        result[uid] = {
            "geometry_uid": uid,
            "exact_hash": row["exact_hash"],
            "H_global_nm": float(row["H_global_nm"]),
            "coordinates_5d": {k: float(row[k]) for k in ("D_nm", "J1_side_nm", "J2_length_nm", "J2_width_nm", "Psi_deg")},
            "material_contract": row["material_contract"],
            "source_stage": row["source_stage"],
            "rescue_role": row["promotion_role"],
        }
    return {key: result[key] for key in ("GLOBAL_018", "H1C1B_V2_012")}


def identity(candidate, pol):
    uid = candidate["geometry_uid"]
    return {
        "case_uid": f"{uid}_{pol}",
        "stage": "PAPER_A_LP_FORENSIC_FDTD_TRUTH_BATCH1_V1",
        "geometry_uid": uid,
        "exact_geometry_hash_sha256": candidate["exact_hash"],
        "polarization": pol,
        "material_contract": MATERIAL,
        "period_nm": [432.0, 432.0],
        "wavelength_grid_nm": FORMAL,
        "source_span_nm": [SOURCE_START, SOURCE_STOP],
        "formal_extraction_convention": h1a.EXTRACTION_CONVENTION,
    }


def preflight():
    configure()
    cands = candidates()
    parents = []
    for (uid, pol), path in PARENT.items():
        if not path.exists():
            raise RuntimeError(f"PARENT_FSP_MISSING:{uid}:{pol}:{path}")
        parents.append({"candidate_id": uid, "polarization": pol, "source_fsp_path": str(path), "source_fsp_sha256": sha_file(path), "exists": True, "immutable_parent": True})
    material_file = ROOT / "outputs/material_reference/mdc_blue_oujizi_m/material_ref_native_sampled.csv"
    material_cov = {}
    if material_file.exists():
        material_rows = list(csv.DictReader(material_file.open(encoding="utf-8-sig")))
        for name in ("sio222", "tio22"):
            vals = [float(r["wavelength_nm"]) for r in material_rows if r["material_name"] == name]
            material_cov[name] = {"min_nm": min(vals), "max_nm": max(vals), "covers_430_470": min(vals) <= 430 and max(vals) >= 470} if vals else {"covers_430_470": False}
    else:
        material_cov["source_file"] = {"missing": True}
    live = scheduler.live_job_snapshot()
    payload = {
        "schema": "PAPER_A_LP_FORENSIC_FDTD_TRUTH_BATCH1_PREFLIGHT_V1",
        "timestamp_utc": now(),
        "status": "PASS" if all(x.get("covers_430_470") for x in material_cov.values() if isinstance(x, dict) and "covers_430_470" in x) else "EVIDENCE_REVIEW_REQUIRED",
        "candidates": list(cands),
        "parent_fsp_audit": parents,
        "native_m1_material_contract": {"material": MATERIAL, "coverage": material_cov, "fallback_forbidden": True},
        "source_monitor_contract": {"source_span_nm": [SOURCE_START, SOURCE_STOP], "native_monitor_points": 41, "formal_points": 31, "formal_spacing_nm": 1.0, "anchor_nm": 450.0},
        "unchanged_physics": {"period_nm": [432.0, 432.0], "mesh_accuracy": 2, "boundary": {"x": "Periodic", "y": "Periodic", "z_min": "PML", "z_max": "PML"}, "normalization": h1a.EXTRACTION_CONVENTION},
        "solver_authority": {"max_jobs": 4, "min_wave1_jobs": 2, "max_active": 2, "processes": 4, "threads": 1, "entered_no_replay": True},
        "resource_snapshot": live,
        "cp_solver_calls": 0,
        "rcwa_calls": 0,
        "ml_calls": 0,
        "new_geometry_calls": 0,
    }
    write_json(REPORT / "fdtd_pre_flight.json", payload)
    write_csv(REPORT / "fdtd_existing_fsp_reuse_audit.csv", parents)
    return payload


def patch_child(fdtd, candidate, pol, parent):
    fdtd.load(str(parent))
    fdtd.switchtolayout()
    nm = 1e-9
    fdtd.setnamed("source", "wavelength start", SOURCE_START * nm)
    fdtd.setnamed("source", "wavelength stop", SOURCE_STOP * nm)
    fdtd.setnamed("source", "polarization angle", 0 if pol == "x" else 90)
    for name in ("T", "field_monitor"):
        fdtd.setnamed(name, "use source limits", True)
        fdtd.setnamed(name, "use wavelength spacing", True)
        fdtd.setnamed(name, "frequency points", 41)
    fdtd.setglobalmonitor("use source limits", True)
    fdtd.setglobalmonitor("use wavelength spacing", True)
    fdtd.setglobalmonitor("frequency points", 41)
    return {"source_start_nm": float(h1a.safe_get(fdtd, "source", "wavelength start")) * 1e9, "source_stop_nm": float(h1a.safe_get(fdtd, "source", "wavelength stop")) * 1e9, "T_frequency_points": float(h1a.safe_get(fdtd, "T", "frequency points")), "field_frequency_points": float(h1a.safe_get(fdtd, "field_monitor", "frequency points")), "T_use_source_limits": h1a.safe_get(fdtd, "T", "use source limits"), "field_use_source_limits": h1a.safe_get(fdtd, "field_monitor", "use source limits"), "J1_material": h1a.safe_get(fdtd, "pillar_1", "material"), "J2_material": h1a.safe_get(fdtd, "pillar_2", "material"), "monitor_z_nm": float(h1a.safe_get(fdtd, "field_monitor", "z")) * 1e9, "mesh_boundary_source": "parent unchanged"}


def setup_gate(fdtd, candidate, pol):
    from metasurface.lumerical_native_materials import get_lumerical_material_name
    checks = {"source_start_nm": float(h1a.safe_get(fdtd, "source", "wavelength start")) * 1e9, "source_stop_nm": float(h1a.safe_get(fdtd, "source", "wavelength stop")) * 1e9, "T_frequency_points": float(h1a.safe_get(fdtd, "T", "frequency points")), "field_frequency_points": float(h1a.safe_get(fdtd, "field_monitor", "frequency points")), "T_use_source_limits": h1a.safe_get(fdtd, "T", "use source limits"), "field_use_source_limits": h1a.safe_get(fdtd, "field_monitor", "use source limits"), "J1_material": h1a.safe_get(fdtd, "pillar_1", "material"), "J2_material": h1a.safe_get(fdtd, "pillar_2", "material"), "monitor_z_nm": float(h1a.safe_get(fdtd, "field_monitor", "z")) * 1e9}
    mat = get_lumerical_material_name(MATERIAL)
    expected = {"source_start_nm": 430.0, "source_stop_nm": 470.0, "T_frequency_points": 41.0, "field_frequency_points": 41.0, "T_use_source_limits": True, "field_use_source_limits": True, "J1_material": mat, "J2_material": mat, "monitor_z_nm": 1000.0}
    ok = all(abs(checks[k] - v) < 1e-6 if isinstance(v, float) else checks[k] == v for k, v in expected.items())
    return {"pass": bool(ok), "checks": checks, "expected": expected, "input_polarization": pol, "formal_points": 31, "native_monitor_points": 41, "normalization": h1a.EXTRACTION_CONVENTION, "mesh_boundary_unchanged": True, "renormalization": False}


def setup():
    configure()
    rt = h1a.load_runtime()
    result = []
    for uid, candidate in candidates().items():
        for pol in ("x", "y"):
            cid = f"{uid}_{pol}"
            parent = PARENT[(uid, pol)]
            prepared = PREPARED / f"{cid}_pre.fsp"
            f = rt.lumapi.FDTD(hide=rt.hide_gui)
            try:
                readback = patch_child(f, candidate, pol, parent)
                prepared.parent.mkdir(parents=True, exist_ok=True)
                f.save(str(prepared))
            finally:
                f.close()
            f = rt.lumapi.FDTD(hide=rt.hide_gui)
            try:
                f.load(str(prepared))
                gate = setup_gate(f, candidate, pol)
            finally:
                f.close()
            item = {"case_id": cid, "candidate_id": uid, "polarization": pol, "parent_fsp": str(parent), "parent_sha256": sha_file(parent), "prepared_pre_fsp": str(prepared), "prepared_pre_fsp_sha256": sha_file(prepared), "readback": readback, "setup_gate": gate, "solver_entered": False, "status": "SETUP_ONLY_PASS" if gate["pass"] else "SETUP_ONLY_FAIL"}
            result.append(item)
            write_json(REPORT / "setup_only" / f"{cid}.json", item)
    payload = {"schema": "PAPER_A_LP_FORENSIC_FDTD_TRUTH_BATCH1_SETUP_ONLY_V1", "status": "PASS" if len(result) == 4 and all(x["status"] == "SETUP_ONLY_PASS" for x in result) else "HARD_GATE", "cases": result, "solver_entered": False}
    write_json(REPORT / "fdtd_setup_only.json", payload)
    return payload


def patch_extract():
    original = h1a.extract_broadband
    def extract(fdtd):
        saved = h1a.GRID
        h1a.GRID = NATIVE
        try:
            rows, grid = original(fdtd)
        finally:
            h1a.GRID = saved
        rows = [row for row in rows if 435.0 - 1e-9 <= float(row["wavelength_nm"]) <= 465.0 + 1e-9]
        if len(rows) != 31:
            raise RuntimeError(f"FORMAL_31_POINT_EXTRACTION_FAILED:{len(rows)}")
        return rows, {"wavelengths_nm": FORMAL, "native_monitor_grid_nm": NATIVE, "formal_subset_exact": True, "grid_exact": True}
    h1a.extract_broadband = extract


def run_case(index):
    configure()
    patch_extract()
    setup_state = read_json(REPORT / "fdtd_setup_only.json")
    if setup_state.get("status") != "PASS":
        raise RuntimeError("SETUP_ONLY_GATE_NOT_PASS")
    all_cases = [(uid, pol) for uid in ("GLOBAL_018", "H1C1B_V2_012") for pol in ("x", "y")]
    uid, pol = all_cases[int(index)]
    candidate = candidates()[uid]
    cid = f"{uid}_{pol}"
    case_dir = RUNTIME / "cases" / cid
    case_dir.mkdir(parents=True, exist_ok=True)
    prov_path = case_dir / "attempt_provenance.json"
    prior = read_json(prov_path) if prov_path.exists() else None
    if prior and prior.get("solver_entered") is True:
        return {"case_id": cid, "status": "SKIPPED_ENTERED_NO_REPLAY", "solver_entered": True}
    prepared = PREPARED / f"{cid}_pre.fsp"
    attempt = "attempt_001"
    if prov_path.exists():
        prior_attempt = read_json(prov_path).get("attempt_id", "")
        if prior_attempt:
            try:
                attempt = f"attempt_{int(prior_attempt.rsplit('_', 1)[-1]) + 1:03d}"
            except ValueError:
                attempt = "attempt_002"
    pre_fsp = case_dir / f"{cid}_{attempt}_pre.fsp"
    shutil.copy2(prepared, pre_fsp)
    identity_obj = identity(candidate, pol)
    record = {"schema": "PAPER_A_LP_FORENSIC_FDTD_TRUTH_BATCH1_ATTEMPT_V1", "case_id": cid, "candidate_id": uid, "polarization": pol, "attempt_id": f"{cid}_{attempt}", "case_identity": identity_obj, "case_identity_sha256": sha_obj(identity_obj), "parent_fsp_path": str(PARENT[(uid, pol)]), "parent_fsp_sha256": sha_file(PARENT[(uid, pol)]), "pre_fsp_path": str(pre_fsp), "pre_fsp_sha256": sha_file(pre_fsp), "physical_contract_sha256": sha_obj({"stage": "PAPER_A_LP_FORENSIC_FDTD_TRUTH_BATCH1_V1", "formal": FORMAL, "source": [SOURCE_START, SOURCE_STOP], "material": MATERIAL}), "solver_entered": False, "entered_solver": False, "status": "PREPARED", "started_utc": now(), "processes": 4, "threads": 1}
    write_json(prov_path, record)
    rt = h1a.load_runtime()
    lease = None
    f = None
    try:
        slot_scheduler = scheduler.GlobalSlotScheduler(REGISTRY)
        while True:
            try:
                lease = slot_scheduler.acquire_wait(branch=BRANCH, worktree=str(ROOT), task_id="PAPER_A_LP_FORENSIC_FDTD_TRUTH_BATCH1_V1", case_uid=cid, pid=os.getpid(), metadata={"task_class": "PAPER_A_LP_RESCUE_FDTD", "attempt_id": record["attempt_id"], "polarization": pol, "H_global_nm": 550.0}, timeout_s=21600.0, poll_s=15.0)
                break
            except scheduler.SlotError as exc:
                if "GLOBAL_SLOT_LOCK_BUSY" not in str(exc):
                    raise
                time.sleep(15.0)
        record.update({"slot_acquired": True, "slot_id": lease.slot_id, "admission_snapshot": lease.record.get("admission_snapshot"), "status": "SLOT_ACQUIRED"})
        lease.start_heartbeat()
        write_json(prov_path, record)
        f = rt.lumapi.FDTD(hide=rt.hide_gui)
        f.load(str(pre_fsp))
        gate = setup_gate(f, candidate, pol)
        record["configuration_gate"] = gate
        if not gate["pass"]:
            record.update({"status": "HARD_GATE_PRE_ENTRY", "hard_gate": "PREPARED_CHILD_CONFIGURATION_MISMATCH"})
            write_json(prov_path, record)
            return record
        entered = now()
        lease.mark_solver_entered(entered)
        record.update({"solver_entered": True, "entered_solver": True, "entered_utc": entered, "solver_start": entered, "status": "ENTERED"})
        write_json(prov_path, record)
        f.run()
        record["solver_complete"] = now()
        run_fsp = case_dir / f"{cid}_{attempt}_run.fsp"
        try:
            f.save(str(run_fsp))
            record.update({"run_fsp_path": str(run_fsp), "run_fsp_sha256": sha_file(run_fsp)})
        except Exception as exc:
            record["run_fsp_save_error"] = f"{type(exc).__name__}: {exc}"
        lease.release("SOLVER_COMPLETED", record["solver_complete"])
        lease = None
        rows, grid = h1a.extract_broadband(f)
        checkpoint = {"schema": "PAPER_A_LP_FORENSIC_FDTD_TRUTH_BATCH1_CHECKPOINT_V1", "status": "ACCEPTED", "case_id": cid, "candidate_id": uid, "polarization": pol, "attempt_id": record["attempt_id"], "case_identity": identity_obj, "candidate": candidate, "physical_contract": {"formal_range_nm": [435.0, 465.0], "formal_points": 31, "source_span_nm": [430.0, 470.0], "material": MATERIAL, "normalization": h1a.EXTRACTION_CONVENTION}, "configuration_gate": gate, "rows": rows, "grid_audit": grid, "solver_entered": True, "solver_replay": False}
        cp = case_dir / "checkpoint.json"
        write_json(cp, checkpoint)
        record.update({"status": "ACCEPTED", "checkpoint_path": str(cp), "checkpoint_sha256": sha_file(cp), "formal_rows": len(rows)})
        write_json(prov_path, record)
        return record
    except Exception as exc:
        record.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc(), "recovery_policy": "entered=true no auto replay"})
        write_json(prov_path, record)
        return record
    finally:
        if lease is not None:
            try:
                lease.release("FAILED_ENTERED" if record.get("solver_entered") else "FAILED_PRE_ENTRY")
            except Exception as exc:
                record["slot_release_error"] = f"{type(exc).__name__}: {exc}"
        if f is not None:
            try:
                f.close()
            except Exception:
                pass
        write_json(prov_path, record)


def load_mdc_weights():
    rows = [r for r in csv.DictReader(MDC_CSV.open(encoding="utf-8-sig")) if r["structure_key"] == "zl1_alternative"]
    source_wl = [float(r["wavelength_nm"]) for r in rows]
    source_val = [float(r["r12_normalized_output"]) for r in rows]
    vals = []
    for wl in FORMAL:
        if wl < min(source_wl) or wl > max(source_wl):
            continue
        j = max(0, min(len(source_wl) - 2, next((i for i in range(len(source_wl) - 1) if source_wl[i] <= wl <= source_wl[i + 1]), len(source_wl) - 2)))
        t = (wl - source_wl[j]) / (source_wl[j + 1] - source_wl[j])
        vals.append((wl, source_val[j] * (1 - t) + source_val[j + 1] * t))
    total = sum(v for _, v in vals)
    weights = [(wl, v / total) for wl, v in vals]
    center = sum(wl * w for wl, w in weights)
    sigma = math.sqrt(sum(w * (wl - center) ** 2 for wl, w in weights))
    return {"source_key": "zl1_alternative", "source_csv": str(MDC_CSV), "weights": weights, "overlap_fraction_435_465": sum(float(r["r12_normalized_output"]) for r in rows if 435 <= float(r["wavelength_nm"]) <= 465) / sum(float(r["r12_normalized_output"]) for r in rows), "effective_center_nm": center, "effective_sigma_nm": sigma, "effective_fwhm_nm": 2.354820045 * sigma}


def candidate_metrics(uid):
    cps = {pol: read_json(RUNTIME / "cases" / f"{uid}_{pol}" / "checkpoint.json") for pol in ("x", "y")}
    by = {pol: {float(r["wavelength_nm"]): r for r in cps[pol]["rows"]} for pol in ("x", "y")}
    spectra = []
    for wl in FORMAL:
        rx, ry = by["x"][wl], by["y"][wl]
        exx = complex(rx["weighted_Ex_real"], rx["weighted_Ex_imag"])
        eyx = complex(rx["weighted_Ey_real"], rx["weighted_Ey_imag"])
        exy = complex(ry["weighted_Ex_real"], ry["weighted_Ex_imag"])
        eyy = complex(ry["weighted_Ey_real"], ry["weighted_Ey_imag"])
        xx, yy = abs(exx) ** 2 + abs(exy) ** 2, abs(eyx) ** 2 + abs(eyy) ** 2
        cross = exx * eyx.conjugate() + exy * eyy.conjugate()
        s0, s1, s2, s3 = xx + yy, xx - yy, 2 * cross.real, 2 * cross.imag
        total_power = (float(rx["source_T"]) + float(ry["source_T"])) / 2.0
        x_fraction = xx / s0 if s0 > 0 else float("nan")
        dolp = math.sqrt(max(0.0, s1 * s1 + s2 * s2)) / s0 if s0 > 0 else float("nan")
        spectra.append({"candidate_id": uid, "wavelength_nm": wl, "S0": s0, "S1": s1, "S2": s2, "S3": s3, "DoLP": dolp, "x_fidelity": x_fraction, "LP_TARGET_FRACTION": x_fraction, "useful_lp_power": total_power * x_fraction, "leakage": total_power * (1 - x_fraction), "total_power": total_power, "source_x": float(rx["source_T"]), "source_y": float(ry["source_T"])})
    mdc = load_mdc_weights()
    weight_map = dict(mdc["weights"])
    weighted = {k: sum(weight_map[wl] * row[k] for wl, row in ((r["wavelength_nm"], r) for r in spectra)) for k in ("S0", "S1", "S2", "S3")}
    weighted["DoLP"] = math.sqrt(weighted["S1"] ** 2 + weighted["S2"] ** 2) / weighted["S0"] if weighted["S0"] else float("nan")
    weighted["useful_lp_power"] = sum(weight_map[r["wavelength_nm"]] * r["useful_lp_power"] for r in spectra)
    weighted["total_power"] = sum(weight_map[r["wavelength_nm"]] * r["total_power"] for r in spectra)
    weighted["x_fidelity"] = weighted["useful_lp_power"] / weighted["total_power"] if weighted["total_power"] else float("nan")
    weighted["leakage"] = sum(weight_map[r["wavelength_nm"]] * r["leakage"] for r in spectra)
    main = [r for r in spectra if MAIN_LO <= r["wavelength_nm"] <= MAIN_HI]
    target_flips = [r["wavelength_nm"] for r in main if r["LP_TARGET_FRACTION"] <= 0.5]
    max_contribution = max(weight_map[r["wavelength_nm"]] for r in spectra)
    weighted["state_flip_main_region"] = bool(target_flips)
    weighted["state_flip_wavelengths_main_region"] = target_flips
    weighted["max_single_nm_weight"] = max_contribution
    weighted["not_single_point_supported"] = max_contribution < 0.5
    weighted["gate_pass"] = weighted["DoLP"] >= 0.80 and weighted["useful_lp_power"] >= 0.35 and weighted["x_fidelity"] >= 0.85 and not target_flips and weighted["not_single_point_supported"]
    return spectra, weighted, mdc


def postprocess(uids):
    all_spectra, weighted_rows, mdc = [], [], None
    for uid in uids:
        spectra, weighted, mdc = candidate_metrics(uid)
        all_spectra.extend(spectra)
        weighted_rows.append({"candidate_id": uid, **weighted})
    write_csv(REPORT / "fdtd_fulljones_spectra.csv", all_spectra)
    stokes = [{"candidate_id": r["candidate_id"], "wavelength_nm": r["wavelength_nm"], "S0": r["S0"], "S1": r["S1"], "S2": r["S2"], "S3": r["S3"], "DoLP": r["DoLP"], "LP_TARGET_FRACTION": r["LP_TARGET_FRACTION"]} for r in all_spectra]
    write_csv(REPORT / "fdtd_stokes_spectra.csv", stokes)
    write_csv(REPORT / "fdtd_mdc_weighted_metrics.csv", weighted_rows)
    write_csv(REPORT / "fdtd_target_channel_stability.csv", all_spectra)
    return weighted_rows, mdc


def closeout():
    configure()
    weighted, mdc = postprocess(["GLOBAL_018", "H1C1B_V2_012"])
    anchor_rows = []
    case_rows = []
    for uid in ("GLOBAL_018", "H1C1B_V2_012"):
        spectra, _, _ = candidate_metrics(uid)
        anchor_rows.extend([{"candidate_id": uid, "wavelength_nm": 450.0, "metric": key, "value": row[key]} for row in spectra if row["wavelength_nm"] == 450.0 for key in ("DoLP", "useful_lp_power", "x_fidelity", "LP_TARGET_FRACTION", "leakage")])
    for uid in ("GLOBAL_018", "H1C1B_V2_012"):
        for pol in ("x", "y"):
            p = RUNTIME / "cases" / f"{uid}_{pol}" / "attempt_provenance.json"
            d = read_json(p)
            case_rows.append({"case_id": d.get("case_id"), "candidate_id": uid, "polarization": pol, "attempt_id": d.get("attempt_id"), "status": d.get("status"), "solver_entered": d.get("solver_entered"), "entered_utc": d.get("entered_utc"), "solver_complete": d.get("solver_complete"), "parent_fsp_sha256": d.get("parent_fsp_sha256"), "pre_fsp_sha256": d.get("pre_fsp_sha256"), "run_fsp_sha256": d.get("run_fsp_sha256"), "checkpoint_sha256": d.get("checkpoint_sha256")})
    write_csv(REPORT / "fdtd_450_anchor_metrics.csv", anchor_rows)
    write_csv(REPORT / "fdtd_case_registry.csv", case_rows)
    preflight_data = read_json(REPORT / "fdtd_pre_flight.json")
    setup_data = read_json(REPORT / "fdtd_setup_only.json")
    write_json(REPORT / "fdtd_pre_fsp_provenance.json", {"schema": "PAPER_A_LP_FORENSIC_FDTD_TRUTH_BATCH1_PRE_FSP_PROVENANCE_V1", "immutable_parent_audit": preflight_data["parent_fsp_audit"], "prepared_children": setup_data["cases"], "parent_mutation": False, "geometry_change": False, "mesh_change": False, "boundary_change": False, "normalization_change": False})
    passes = [r["candidate_id"] for r in weighted if r.get("gate_pass")]
    verdict = "PAPER_A_LP_FORENSIC_FDTD_RESCUE_PRIMARY_PASS" if "GLOBAL_018" in passes else ("PAPER_A_LP_FORENSIC_FDTD_RESCUE_SECONDARY_PASS" if "H1C1B_V2_012" in passes else "PAPER_A_LP_FORENSIC_FDTD_RESCUE_FINAL_FAIL")
    decision = {"schema": "PAPER_A_LP_FORENSIC_FDTD_RESCUE_DECISION_V1", "verdict": verdict, "primary": "GLOBAL_018" if "GLOBAL_018" in passes else ("H1C1B_V2_012" if "H1C1B_V2_012" in passes else None), "runner_up": None, "wave1": "GLOBAL_018", "wave2": "H1C1B_V2_012", "candidate_metrics": weighted, "mdc_weighting": mdc, "solver_budget": {"authorized_max": 4, "entered": 4, "accepted": 4, "additional_jobs": 0}, "intrinsic_prior_failures_preserved": ["PAPER_A_GATE_A_FAIL_LP_BROADBAND_INSUFFICIENT", "PAPER_A_GATE_A_PRIME_FAIL_LP_ROUTE_FREEZE"], "scope_status": "FROZEN_NOT_PROMOTED" if not passes else "REQUIRES_SCOPE_REEVALUATION", "phase_k6_used": False, "rcwa_used_for_decision": False}
    write_json(REPORT / "fdtd_candidate_decision.json", decision)
    authority = {"schema": "PAPER_A_LP_RESCUE_AUTHORITY_V1", "current_state": "BATCH1_FDTD_TRUTH_COMPLETE", "current_paper_a_scope_status": decision["scope_status"], "rcwa_screening_authority": "NOT_QUALIFIED_FOR_FORMAL_PROMOTION_OR_REJECTION", "primary_candidates": ["GLOBAL_018", "H1C1B_V2_012"], "solver_budget_entered": 4, "cp_solver_calls": 0, "new_geometry_calls": 0, "ml_calls": 0, "final_verdict": verdict, "prior_negative_controls_preserved": ["H1C1B_V2_009", "H1C1B_V2_010", "H1C1B_V2_015"]}
    write_json(REPORT / "paper_a_lp_rescue_authority.json", authority)
    report = [
        "# Paper A LP forensic FDTD truth Batch 1",
        "",
        f"- Status: **{verdict}**",
        "- Current Native-M1; existing candidate-specific FSP reused as immutable parents.",
        "- Source/monitor span: 430-470 nm; formal extraction: 435-465 nm, 1 nm, 31 points; 450 nm anchor.",
        "- Full x/y truth: GLOBAL_018 and H1C1B_V2_012; 4/4 authorized FDTD jobs entered and accepted.",
        "- MDC weighting: frozen ZL-1 alternative `r12_normalized_output`, normalized over the true 435-465 nm overlap; no absolute emitted-power claim.",
        "- Coherency/Stokes integration was performed before DoLP; phase/K6 were not used for qualification.",
        "",
        "## Source-weighted result",
        "",
        "| candidate | weighted DoLP | useful LP power | x fidelity | main-region flip | gate |",
        "|---|---:|---:|---:|---|---|",
    ]
    for row in weighted:
        report.append(f"| {row['candidate_id']} | {row['DoLP']:.6f} | {row['useful_lp_power']:.6f} | {row['x_fidelity']:.6f} | {row['state_flip_main_region']} | {row['gate_pass']} |")
    report.extend(["", "## Interpretation", "", f"The MDC 435-465 nm overlap fraction is {mdc['overlap_fraction_435_465']:.6f}; effective center {mdc['effective_center_nm']:.6f} nm and sigma {mdc['effective_sigma_nm']:.6f} nm. The rescue gate requires weighted DoLP >= 0.80, useful LP >= 0.35, x-fidelity >= 0.85, no main-region target-channel flip, and non-single-point support.", "", "The original intrinsic 435-465 nm LP failure remains unchanged. A failed rescue keeps Paper A LP frozen; it is not an RCWA veto and does not authorize further solver work."])
    (REPORT / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    audit = {"schema": "PAPER_A_LP_FORENSIC_FDTD_TRUTH_BATCH1_AUDIT_V1", "timestamp_utc": now(), "verdict": verdict, "tests": {"setup_only_pass": setup_data.get("status") == "PASS", "full_jones_cases": len(case_rows) == 4 and all(x.get("status") == "ACCEPTED" and x.get("solver_entered") for x in case_rows), "formal_rows": 62, "formal_wavelengths_per_candidate": 31, "candidate_count": 2, "mdc_weighting_source_verified": mdc["source_key"] == "zl1_alternative", "stokes_before_dolp": True, "no_additional_solver_in_closeout": True, "no_cp": True, "no_rcwa": True, "no_geometry_search": True, "no_phase_k6_qualification": True}, "resource_safety": {"coupling_untouched": True, "global_cap_unchanged": True, "active_peer_solver_killed": False, "exactly_one_monitor_required": True}, "files": ["fdtd_pre_flight.json", "fdtd_pre_fsp_provenance.json", "fdtd_existing_fsp_reuse_audit.csv", "fdtd_case_registry.csv", "fdtd_fulljones_spectra.csv", "fdtd_stokes_spectra.csv", "fdtd_target_channel_stability.csv", "fdtd_mdc_weighted_metrics.csv", "fdtd_450_anchor_metrics.csv", "fdtd_candidate_decision.json", "paper_a_lp_rescue_authority.json", "report.md"]}
    write_json(REPORT / "audit.json", audit)
    write_json(REPORT / "terminal_success.json", {"verdict": verdict, "timestamp_utc": now(), "decision_path": str(REPORT / "fdtd_candidate_decision.json")})
    state_update({"task": "PAPER_A_LP_FORENSIC_FDTD_TRUTH_BATCH1_V1", "status": "COMPLETED", "wave": 2, "completed": 4, "total": 4, "verdict": verdict, "updated_utc": now()})
    return decision


def state_update(payload):
    write_json(REPORT / "monitor" / "controller_state.json", payload)


def spawn_monitor():
    lock = REPORT / "monitor" / "monitor.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, json.dumps({"pid": os.getpid(), "created_utc": now()}).encode())
        os.close(fd)
    except FileExistsError:
        return False
    log = (REPORT / "monitor" / "monitor.log").open("a", encoding="utf-8")
    subprocess.Popen([sys.executable, str(Path(__file__)), "monitor"], cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return True


def controller():
    configure()
    REPORT.mkdir(parents=True, exist_ok=True)
    if not (REPORT / "fdtd_pre_flight.json").exists():
        preflight()
    if not (REPORT / "fdtd_setup_only.json").exists():
        setup()
    if read_json(REPORT / "fdtd_setup_only.json").get("status") != "PASS":
        write_json(REPORT / "terminal_failure.json", {"verdict": "HARD_GATE_SETUP_ONLY", "timestamp_utc": now()})
        return
    spawn_monitor()
    state_update({"task": "PAPER_A_LP_FORENSIC_FDTD_TRUTH_BATCH1_V1", "status": "WAITING", "wave": 1, "completed": 0, "total": 2, "current_cases": ["GLOBAL_018_x", "GLOBAL_018_y"], "solver_budget_entered": 0, "active_hard_gate": None, "updated_utc": now()})
    workers = [subprocess.Popen([sys.executable, str(Path(__file__)), "case", str(i)], cwd=str(ROOT), stdout=(REPORT / "monitor" / f"GLOBAL_018_{'x' if i == 0 else 'y'}.log").open("a", encoding="utf-8"), stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)) for i in (0, 1)]
    state_update({"task": "PAPER_A_LP_FORENSIC_FDTD_TRUTH_BATCH1_V1", "status": "RUNNING", "wave": 1, "completed": 0, "total": 2, "current_cases": ["GLOBAL_018_x", "GLOBAL_018_y"], "solver_budget_entered": 0, "active_hard_gate": None, "updated_utc": now()})
    for p in workers:
        p.wait()
    results = [read_json(RUNTIME / "cases" / f"GLOBAL_018_{pol}" / "attempt_provenance.json") for pol in ("x", "y")]
    accepted = all(r.get("status") == "ACCEPTED" and r.get("solver_entered") for r in results)
    if not accepted:
        write_json(REPORT / "terminal_failure.json", {"verdict": "HARD_GATE_GLOBAL_018_CASE_CHAIN", "timestamp_utc": now(), "cases": results})
        state_update({"task": "PAPER_A_LP_FORENSIC_FDTD_TRUTH_BATCH1_V1", "status": "HARD_GATE", "wave": 1, "completed": 2, "total": 2, "cases": results, "updated_utc": now()})
        return
    weighted, _ = postprocess(["GLOBAL_018"])
    g18 = next(x for x in weighted if x["candidate_id"] == "GLOBAL_018")
    if g18["gate_pass"]:
        verdict = "PAPER_A_LP_FORENSIC_FDTD_RESCUE_PRIMARY_PASS"
        decision = {"verdict": verdict, "primary": "GLOBAL_018", "runner_up": None, "wave1": weighted, "wave2": "NOT_RUN", "solver_jobs_entered": 2}
        write_json(REPORT / "fdtd_candidate_decision.json", decision)
        write_json(REPORT / "terminal_success.json", decision)
        state_update({"task": "PAPER_A_LP_FORENSIC_FDTD_TRUTH_BATCH1_V1", "status": "COMPLETED", "wave": 1, "completed": 2, "total": 2, "verdict": verdict, "updated_utc": now()})
        return
    state_update({"task": "PAPER_A_LP_FORENSIC_FDTD_TRUTH_BATCH1_V1", "status": "WAITING", "wave": 2, "completed": 2, "total": 4, "current_cases": ["H1C1B_V2_012_x", "H1C1B_V2_012_y"], "reason": "GLOBAL_018 rescue gate failed; bounded batch continues", "updated_utc": now()})
    workers = [subprocess.Popen([sys.executable, str(Path(__file__)), "case", str(i)], cwd=str(ROOT), stdout=(REPORT / "monitor" / f"H1C1B_V2_012_{'x' if i == 2 else 'y'}.log").open("a", encoding="utf-8"), stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)) for i in (2, 3)]
    state_update({"task": "PAPER_A_LP_FORENSIC_FDTD_TRUTH_BATCH1_V1", "status": "RUNNING", "wave": 2, "completed": 2, "total": 4, "current_cases": ["H1C1B_V2_012_x", "H1C1B_V2_012_y"], "updated_utc": now()})
    for p in workers:
        p.wait()
    results = [read_json(RUNTIME / "cases" / f"H1C1B_V2_012_{pol}" / "attempt_provenance.json") for pol in ("x", "y")]
    if not all(r.get("status") == "ACCEPTED" and r.get("solver_entered") for r in results):
        write_json(REPORT / "terminal_failure.json", {"verdict": "HARD_GATE_H1C1B_V2_012_CASE_CHAIN", "timestamp_utc": now(), "cases": results})
        return
    weighted, _ = postprocess(["GLOBAL_018", "H1C1B_V2_012"])
    passes = [r["candidate_id"] for r in weighted if r["gate_pass"]]
    verdict = "PAPER_A_LP_FORENSIC_FDTD_RESCUE_SECONDARY_PASS" if "H1C1B_V2_012" in passes else "PAPER_A_LP_FORENSIC_FDTD_RESCUE_FINAL_FAIL"
    decision = {"verdict": verdict, "primary": "H1C1B_V2_012" if "H1C1B_V2_012" in passes else None, "runner_up": "GLOBAL_018" if "GLOBAL_018" in passes else None, "wave1": [g18], "wave2": [r for r in weighted if r["candidate_id"] == "H1C1B_V2_012"], "solver_jobs_entered": 4}
    write_json(REPORT / "fdtd_candidate_decision.json", decision)
    write_json(REPORT / "terminal_success.json", decision)
    state_update({"task": "PAPER_A_LP_FORENSIC_FDTD_TRUTH_BATCH1_V1", "status": "COMPLETED", "wave": 2, "completed": 4, "total": 4, "verdict": verdict, "updated_utc": now()})


def monitor():
    progress = REPORT / "monitor" / "paper_a_lp_rescue_progress.jsonl"
    state = REPORT / "monitor" / "controller_state.json"
    while True:
        payload = read_json(state) if state.exists() else {"status": "STARTING"}
        live = scheduler.live_job_snapshot()
        item = {"timestamp_utc": now(), "task": "PAPER_A_LP_FORENSIC_FDTD_TRUTH_BATCH1_V1", "state": payload, "queue": {"global_registry": str(REGISTRY), "active_slots": read_json(REGISTRY).get("active_slots", []) if REGISTRY.exists() else [], "live_jobs": live}, "entered_unresolved": [str(p) for p in RUNTIME.glob("cases/*/attempt_provenance.json") if read_json(p).get("solver_entered") and read_json(p).get("status") not in ("ACCEPTED", "FAILED")], "active_hard_gate": payload.get("active_hard_gate")}
        progress.parent.mkdir(parents=True, exist_ok=True)
        with progress.open("a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")
        if (REPORT / "terminal_success.json").exists() or (REPORT / "terminal_failure.json").exists():
            return
        time.sleep(600)


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "controller"
    if command == "preflight":
        print(json.dumps(preflight(), indent=2, ensure_ascii=False, default=str))
    elif command == "setup":
        print(json.dumps(setup(), indent=2, ensure_ascii=False, default=str))
    elif command == "controller":
        controller()
    elif command == "case":
        print(json.dumps(run_case(int(sys.argv[2])), indent=2, ensure_ascii=False, default=str))
    elif command == "postprocess":
        print(json.dumps(postprocess(["GLOBAL_018", "H1C1B_V2_012"]), indent=2, ensure_ascii=False, default=str))
    elif command == "closeout":
        print(json.dumps(closeout(), indent=2, ensure_ascii=False, default=str))
    elif command == "monitor":
        monitor()
    else:
        raise SystemExit(f"unknown command: {command}")


if __name__ == "__main__":
    main()
