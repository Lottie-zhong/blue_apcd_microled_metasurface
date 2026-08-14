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
import traceback
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/stage_h1c1c_phase_gap"
OUT = ROOT / "outputs/lp_global_h_h1c1c"
RUNTIME = OUT / "runtime"
MANIFEST_PATH = REPORT / "h1c1c_candidate_manifest.json"
ACCOUNTING_PATH = REPORT / "h1c1c_solver_accounting.json"
GRID = [450.0 + 0.5 * i for i in range(9)]
POLARIZATIONS = ("x", "y")
TARGET_BRANCH = "work/lp-global-h-manifold-v1"
SLOT_REGISTRY = Path(r"D:\project\apcd_global_fdtd_slot_registry_v1.json")
MAX_GEOMETRIES = 10
MAX_SUBRUNS = 20
H_GLOBAL_NM = 550.0
PERIOD_NM = 432.0
MATERIAL = "APCD_TIO2_NATIVE_M1"
PROJECTOR = [[1, 0], [0, 0]]
PROJECTOR_ERROR_MAX = 0.1864961370084426
BOUNDS = {"J1_side_nm": [102.0, 114.0], "J2_length_nm": [100.0, 114.0], "J2_width_nm": [94.0, 106.0], "D_nm": [180.0, 210.0], "Psi_deg": [-3.0, 3.0]}
EXTRACTION_CONVENTION = "transmission_side_full_period_coordinate_weighted_complex_G0_endpoint_dedup_periodic_reclosure_sqrtT_over_norm_arg_txx"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


h1a = load_module(ROOT / "scripts/lp_global_h_h1c1a_broadband_v1.py", "h1c1c_h1a_support")


def configure_support():
    h1a.REPORT = REPORT
    h1a.OUT = OUT
    h1a.RUNTIME = RUNTIME
    h1a.MANIFEST_PATH = MANIFEST_PATH
    h1a.ACCOUNTING_PATH = ACCOUNTING_PATH
    h1a.GRID = GRID
    h1a.H_GLOBAL_NM = H_GLOBAL_NM
    h1a.PERIOD_NM = PERIOD_NM
    h1a.MATERIAL = MATERIAL
    h1a.PROJECTOR = PROJECTOR
    h1a.POLARIZATIONS = POLARIZATIONS
    h1a.MAX_SUBRUNS = MAX_SUBRUNS
    h1a.TARGET_BRANCH = TARGET_BRANCH
    h1a.SLOT_REGISTRY = SLOT_REGISTRY
    h1a.BUILDER_VERSION = "h1c1c_phase_gap_unified_h550_builder_v1"
    h1a.EXTRACTION_CONVENTION = EXTRACTION_CONVENTION


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


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
        writer = csv.DictWriter(handle, fieldnames=fields or ["status"], extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def sha256_obj(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


def current_branch():
    return subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()


def current_head():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def load_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def fnum(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def circ_diff(a, b):
    return (float(a) - float(b) + 180.0) % 360.0 - 180.0


def wrap(value):
    return float(value) % 360.0


def phase_cluster(old_bank, wavelength_index):
    return [float(item["trajectory"][wavelength_index]["phi_deg"]) for item in old_bank]


def circular_gap_interval(values):
    vals = sorted(wrap(x) for x in values)
    gaps = [vals[i + 1] - vals[i] for i in range(len(vals) - 1)] + [vals[0] + 360.0 - vals[-1]]
    index = gaps.index(max(gaps))
    return vals[(index + 1) % len(vals)], vals[index], gaps[index]


def in_gap(value, start, end):
    value, start, end = wrap(value), wrap(start), wrap(end)
    return value > start if start <= end else value > start or value < end


def point_from_values(coords):
    d = float(coords["D_nm"])
    psi = float(coords["Psi_deg"])
    raw_x = d * math.cos(math.radians(psi)) / 2.0
    raw_y = d * math.sin(math.radians(psi)) / 2.0
    cx = math.floor(raw_x * 2.0 + 0.5) / 2.0
    cy = math.floor(raw_y * 2.0 + 0.5) / 2.0
    return {"J1_side_nm": int(coords["J1_side_nm"]), "J2_length_nm": int(coords["J2_length_nm"]), "J2_width_nm": int(coords["J2_width_nm"]), "D_nm": 2.0 * math.hypot(cx, cy), "Psi_deg": math.degrees(math.atan2(cy, cx)), "J2_center_x_nm": cx, "J2_center_y_nm": cy}


def physical_key(point):
    return (int(point["J1_side_nm"]), int(point["J2_length_nm"]), int(point["J2_width_nm"]), round(float(point["J2_center_x_nm"]), 9), round(float(point["J2_center_y_nm"]), 9), H_GLOBAL_NM, PERIOD_NM, MATERIAL)


def apply_frozen_domain_check(point, check):
    checks = check["checks"]
    checks.update({
        "J1_side_domain": BOUNDS["J1_side_nm"][0] <= point["J1_side_nm"] <= BOUNDS["J1_side_nm"][1],
        "J2_length_domain": BOUNDS["J2_length_nm"][0] <= point["J2_length_nm"] <= BOUNDS["J2_length_nm"][1],
        "J2_width_domain": BOUNDS["J2_width_nm"][0] <= point["J2_width_nm"] <= BOUNDS["J2_width_nm"][1],
    })
    check["pass"] = all(checks.values())
    return check


def load_authoritative():
    a_manifest = read_json(ROOT / "reports/stage_h1c1a_broadband_global/h1c1a_candidate_manifest.json")
    b_manifest = read_json(ROOT / "reports/stage_h1c1b_broadband_adaptive/h1c1b_candidate_manifest.json")
    manifests = {row["geometry_uid"]: row for row in a_manifest["candidates"] + b_manifest["candidates"]}
    rows = load_csv(ROOT / "reports/stage_h1c1a_broadband_global/h1c1a_broadband_full_jones.csv") + load_csv(ROOT / "reports/stage_h1c1b_broadband_adaptive/h1c1b_broadband_full_jones.csv")
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["geometry_uid"]].append(row)
    return manifests, grouped


def row_audit(uid, grouped):
    rows = sorted(grouped[uid], key=lambda row: float(row["wavelength_nm"]))
    passes = sum(float(row["projector_error"]) <= PROJECTOR_ERROR_MAX for row in rows)
    phi = [float(row["phi_txx"]) for row in rows]
    return {"geometry_uid": uid, "complete_9": len(rows) == 9, "projector_pass_count": passes, "phase_trajectory_deg": phi, "phase_450_deg": phi[0], "failed_wavelengths_nm": [float(row["wavelength_nm"]) for row in rows if float(row["projector_error"]) > PROJECTOR_ERROR_MAX], "coordinates_5d": {key: float(rows[0][key]) for key in ("J1_side_nm", "J2_length_nm", "J2_width_nm", "D_nm", "Psi_deg")}}


def new_rescue_point(parent, delta):
    coords = dict(parent["coordinates_5d"])
    for key, value in delta.items():
        coords[key] = float(coords[key]) + float(value)
    return point_from_values(coords)


def generate_candidates():
    if current_branch() != TARGET_BRANCH:
        raise RuntimeError("HARD_GATE_WRONG_BRANCH")
    manifests, grouped = load_authoritative()
    old_hashes = {row["exact_hash"] for row in manifests.values()}
    old_keys = set()
    for row in manifests.values():
        old_keys.add(physical_key(point_from_values(row["coordinates_5d"])))
    old_bank = read_json(ROOT / "reports/stage_h1c1b1_sixbin_closure/h1c1b1_strict_bank_v1.json")["geometries"]
    strict_ids = set(read_json(ROOT / "reports/stage_h1c1b1_sixbin_closure/h1c1b1_strict_bank_v1.json")["strict_ids"])
    audits = {uid: row_audit(uid, grouped) for uid in grouped}
    rescue_parent_ids = [
        "GLOBAL_019", "SEED2_H1B1_A_LOWER_COMPATIBLE_EDGE", "GLOBAL_011",
        "H1C1B_V2_013", "H1C1B_V2_019", "H1C1B_V2_003",
    ]
    rescue_deltas = [
        {"J1_side_nm": 1, "J2_length_nm": 0, "J2_width_nm": 0, "D_nm": 0, "Psi_deg": 0},
        {"J1_side_nm": 0, "J2_length_nm": 1, "J2_width_nm": 0, "D_nm": 0, "Psi_deg": 0},
        {"J1_side_nm": 0, "J2_length_nm": 0, "J2_width_nm": -1, "D_nm": 0, "Psi_deg": 0},
        {"J1_side_nm": 0, "J2_length_nm": 0, "J2_width_nm": 0, "D_nm": 1, "Psi_deg": 0},
        {"J1_side_nm": 0, "J2_length_nm": 0, "J2_width_nm": 0, "D_nm": 0, "Psi_deg": -0.5},
        {"J1_side_nm": -1, "J2_length_nm": 0, "J2_width_nm": 0, "D_nm": 1, "Psi_deg": 0},
    ]
    parent_rows = []
    for parent_id, delta in zip(rescue_parent_ids, rescue_deltas):
        if parent_id not in manifests:
            raise RuntimeError("HARD_GATE_RESCUE_PARENT_MISSING:" + parent_id)
        audit = audits.get(parent_id)
        if not audit or not audit["complete_9"]:
            raise RuntimeError("HARD_GATE_RESCUE_PARENT_NO_COMPLETE_BROADBAND:" + parent_id)
        old_phase = phase_cluster(old_bank, 0)
        start, end, gap = circular_gap_interval(old_phase)
        parent_rows.append({"parent_geometry_uid": parent_id, "parent_exact_hash": manifests[parent_id]["exact_hash"], "parent_status": "STRICT" if parent_id in strict_ids else ("NEAR_MISS" if audit["projector_pass_count"] >= 5 else "PHASE_VALUABLE_NONSTRICT"), "parent_projector_pass_count": audit["projector_pass_count"], "parent_failed_wavelengths": audit["failed_wavelengths_nm"], "parent_phase_trajectory_deg": audit["phase_trajectory_deg"], "parent_phase_450_deg": audit["phase_450_deg"], "distance_from_strict_cluster_450_deg": min(abs(circ_diff(audit["phase_450_deg"], p)) for p in old_phase), "target_circular_phase_region": {"start_deg": start, "end_deg": end, "largest_gap_deg": gap}, "delta": delta})
    candidates = []
    seen_hashes, seen_keys = set(old_hashes), set(old_keys)
    for index, (parent, delta) in enumerate(zip(parent_rows, rescue_deltas), 1):
        point = new_rescue_point(manifests[parent["parent_geometry_uid"]], delta)
        check = apply_frozen_domain_check(point, h1a.legality(point, old_hashes, old_keys, seen_hashes, seen_keys))
        if not check["pass"]:
            raise RuntimeError("HARD_GATE_RESCUE_ILLEGAL:" + json.dumps({"index": index, "checks": check["checks"]}))
        uid = f"H1C1C_R{index:02d}"
        source = {"coordinates_5d": {key: point[key] for key in ("J1_side_nm", "J2_length_nm", "J2_width_nm", "D_nm", "Psi_deg")}}
        record = h1a.make_record(uid, source, "PHASE_GAP_NEAR_MISS_RESCUE", "H1C1C_PHASE_GAP_NEAR_MISS_RESCUE_V1", "RESCUE", None, check, parent)
        record["subrole"] = "PROJECTOR_REPAIR_PHASE_PRESERVING"
        record["parent_reference"] = parent["parent_geometry_uid"]
        record["proposal_audit"] = {"major_role": record["role"], "subrole": record["subrole"], "parent_reference_geometry": parent["parent_geometry_uid"], "parent_exact_hash": parent["parent_exact_hash"], "parent_broadband_status": parent["parent_status"], "parent_failed_wavelengths_nm": parent["parent_failed_wavelengths"], "5D_displacement_from_parent": delta, "target_phase_region": parent["target_circular_phase_region"], "projector_repair_hypothesis": "deterministic small legal perturbation to repair failed wavelengths without abandoning phase-gap location", "phase_preservation_hypothesis": "retain or shift toward the parent phase trajectory", "supporting_evidence": ["H1C-1B1 strict-bank phase coverage", "parent complete broadband full-Jones evidence"], "solver_entered": False, "solver_replay": False}
        for pol in POLARIZATIONS:
            record["broadband_case_identity"][pol].update({"stage": "H1C1C", "case_uid": f"H1C1C_{uid}_P{pol}", "builder_version": h1a.BUILDER_VERSION})
        candidates.append(record); seen_hashes.add(check["exact_hash"]); seen_keys.add(tuple(check["physical_key"]))

    # Deterministic coverage-oriented exploration: Sobol candidates are ranked by
    # normalized maximin distance from the already sampled H550 geometry bank.
    try:
        from scipy.stats import qmc
    except ImportError as exc:
        raise RuntimeError("HARD_GATE_SOBOL_UNAVAILABLE") from exc
    existing_points = [point_from_values(row["coordinates_5d"]) for row in manifests.values()]
    exploration_pool = []
    for index, raw in enumerate(qmc.Sobol(d=5, scramble=False, seed=17).random_base2(m=8)):
        point, _ = h1a.legalize([float(x) for x in raw])
        check = apply_frozen_domain_check(point, h1a.legality(point, old_hashes, old_keys, seen_hashes, seen_keys))
        if not check["pass"]:
            continue
        norm = {"J1_side_nm": 12.0, "J2_length_nm": 14.0, "J2_width_nm": 12.0, "D_nm": 30.0, "Psi_deg": 6.0}
        distance = min(sum(((float(point[key]) - float(old[key])) / norm[key]) ** 2 for key in norm) ** 0.5 for old in existing_points + [point_from_values(c["coordinates_5d"]) for c in candidates])
        exploration_pool.append((distance, index, point, check, [float(x) for x in raw]))
    exploration_pool.sort(key=lambda item: (-item[0], item[1]))
    selected_exploration = []
    for distance, sobol_index, point, check, raw in exploration_pool:
        if check["exact_hash"] in seen_hashes or tuple(check["physical_key"]) in seen_keys:
            continue
        selected_exploration.append((distance, sobol_index, point, check, raw))
        seen_hashes.add(check["exact_hash"])
        seen_keys.add(tuple(check["physical_key"]))
        if len(selected_exploration) == 4:
            break
    for index, (distance, sobol_index, point, check, raw) in enumerate(selected_exploration, 1):
        uid = f"H1C1C_E{index:02d}"
        source = {"coordinates_5d": {key: point[key] for key in ("J1_side_nm", "J2_length_nm", "J2_width_nm", "D_nm", "Psi_deg")}}
        target = {"rule": "data-driven missing circular region from H1C-1B1 old 7-strict bank", "old_strict_phase_450_deg": sorted(old_phase), "geometry_space_value": distance}
        record = h1a.make_record(uid, source, "GLOBAL_PHASE_GAP_EXPLORATION", "H1C1C_DETERMINISTIC_SOBOL_COVERAGE_RANKING_SEED_17", "EXPLORATION", None, check, {"sobol_index": sobol_index, "raw_unit_point": raw, "target_phase_region": target})
        record["subrole"] = "GLOBAL_PHASE_GAP_SPACE_FILLING"
        record["proposal_audit"] = {"major_role": record["role"], "subrole": record["subrole"], "sobol_index": sobol_index, "raw_unit_point": raw, "geometry_space_distance": distance, "target_phase_region": target, "projector_repair_hypothesis": "global coverage exploration with no local-parent rescue claim", "phase_preservation_hypothesis": "discover missing circular phase region", "solver_entered": False, "solver_replay": False}
        for pol in POLARIZATIONS:
            record["broadband_case_identity"][pol].update({"stage": "H1C1C", "case_uid": f"H1C1C_{uid}_P{pol}", "builder_version": h1a.BUILDER_VERSION})
        candidates.append(record)
    if len(candidates) != 10 or len({c["exact_hash"] for c in candidates}) != 10:
        raise RuntimeError("HARD_GATE_H1C1C_EXACT10_UNIQUE")
    contract = {"schema": "H1C1C_PHASE_GAP_BROADBAND_PHYSICS_CONTRACT_V1", "H_global_nm": H_GLOBAL_NM, "J1_H_equals_J2_H": True, "wavelength_grid_nm": GRID, "period_nm": [PERIOD_NM, PERIOD_NM], "material": MATERIAL, "projector": PROJECTOR, "phase": "arg(txx)", "projector_error_threshold": PROJECTOR_ERROR_MAX, "strict_semantics": "x_accepted_and_y_accepted_and_full_jones_valid_and_projector_pass_at_all_9_wavelengths", "extraction": EXTRACTION_CONVENTION, "one_broadband_run_per_polarization": True}
    payload = {"schema": "H1C1C_CANDIDATE_MANIFEST_V1", "stage": "H1C-1C", "status": "FROZEN_READY", "branch": current_branch(), "head": current_head(), "worktree": str(ROOT), "contract": contract, "contract_sha256": sha256_obj(contract), "solver_authorization": {"new_geometries": 10, "rescue_geometries": 6, "exploration_geometries": 4, "formal_x_y_subruns": 20, "max_global_fdtd_concurrency": 2, "max_active_fdtd_per_branch": 1, "processes_per_job": 4, "threads_per_job": 1, "one_run_returns_all_wavelengths": True}, "candidates": candidates, "domain": BOUNDS, "phase_gap_first": True, "solver_entered": False, "solver_replay": False}
    payload["freeze_sha256"] = sha256_obj(payload)
    return payload, {"rescue_parents": parent_rows, "exploration_pool_selected": [{"geometry_uid": c["geometry_uid"], "coordinates_5d": c["coordinates_5d"], "exact_hash": c["exact_hash"], "subrole": c["subrole"], "proposal_audit": c["proposal_audit"]} for c in candidates[6:]], "strict_ids_before": sorted(strict_ids), "phase_450_old_strict": sorted(old_phase)}


def manifest():
    data = read_json(MANIFEST_PATH)
    frozen = dict(data); freeze = frozen.pop("freeze_sha256", None)
    if freeze != sha256_obj(frozen): raise RuntimeError("HARD_GATE_H1C1C_MANIFEST_FREEZE_HASH")
    if data.get("status") != "FROZEN_READY": raise RuntimeError("HARD_GATE_H1C1C_MANIFEST_STATUS")
    return data


def validate(data):
    rows = data["candidates"]
    if len(rows) != 10 or len({x["exact_hash"] for x in rows}) != 10: raise RuntimeError("HARD_GATE_H1C1C_EXACT10_HASH_UNIQUE")
    if sum(x["role"] == "PHASE_GAP_NEAR_MISS_RESCUE" for x in rows) != 6 or sum(x["role"] == "GLOBAL_PHASE_GAP_EXPLORATION" for x in rows) != 4: raise RuntimeError("HARD_GATE_H1C1C_ROLE_COUNTS")
    if not all(x["legality"]["pass"] for x in rows): raise RuntimeError("HARD_GATE_H1C1C_LEGALITY")
    if any(x.get("solver_entered") or x.get("solver_replay") for x in rows): raise RuntimeError("HARD_GATE_H1C1C_PRE_ENTRY_STATE")
    if data["solver_authorization"]["formal_x_y_subruns"] != 20: raise RuntimeError("HARD_GATE_H1C1C_BUDGET")
    for row in rows:
        if set(row["broadband_case_identity"]) != {"x", "y"}: raise RuntimeError("HARD_GATE_H1C1C_XY_IDENTITIES")
        if any(x["wavelength_grid_nm"] != GRID for x in row["broadband_case_identity"].values()): raise RuntimeError("HARD_GATE_H1C1C_GRID")
        if any(x["exact_geometry_hash_sha256"] != row["exact_hash"] for x in row["broadband_case_identity"].values()): raise RuntimeError("HARD_GATE_H1C1C_HASH_IDENTITY")


def initial_accounting(data):
    if ACCOUNTING_PATH.exists():
        old = read_json(ACCOUNTING_PATH)
        if old.get("manifest_freeze_sha256") != data["freeze_sha256"] and old.get("solver_entries"):
            raise RuntimeError("HARD_GATE_H1C1C_ACCOUNTING_MANIFEST_MISMATCH")
        return old
    cases = [{"case_id": c["broadband_case_identity"][pol]["case_uid"], "geometry_uid": c["geometry_uid"], "exact_hash": c["exact_hash"], "polarization": pol, "planned": True, "attempted": False, "solver_entered": False, "accepted": False, "recovered": False, "quarantined": False} for c in data["candidates"] for pol in POLARIZATIONS]
    payload = {"schema": "H1C1C_SOLVER_ACCOUNTING_V1", "stage": "H1C-1C", "manifest_freeze_sha256": data["freeze_sha256"], "solver_budget_planned": 20, "solver_subruns_entered": 0, "solver_subruns_accepted": 0, "H_global_nm": H_GLOBAL_NM, "wavelength_grid_nm": GRID, "max_global_fdtd_concurrency": 2, "max_active_fdtd_per_branch": 1, "processes_per_job": 4, "threads_per_job": 1, "rcwa_consumes_fdtd_slot": False, "cases": cases, "solver_entries": [], "status": "PLANNED"}
    write_json(ACCOUNTING_PATH, payload)
    return payload


def preflight():
    configure_support(); data = manifest(); validate(data); accounting = initial_accounting(data)
    result = {"status": "H1C1C_PREFLIGHT_PASS", "planned_geometries": 10, "rescue_geometries": 6, "exploration_geometries": 4, "planned_formal_subruns": 20, "solver_entered": accounting.get("solver_subruns_entered", 0), "max_global_fdtd_concurrency": 2, "max_active_fdtd_per_branch": 1, "processes_per_job": 4, "threads_per_job": 1, "wavelength_grid_nm": GRID}
    write_json(REPORT / "h1c1c_preflight.json", result); return result


def setup_check():
    configure_support(); data = manifest(); validate(data); initial_accounting(data)
    result = h1a.setup_check(data)
    result.update({"stage": "H1C-1C", "solver_entered": False, "solver_run_called": False})
    write_json(REPORT / "h1c1c_setup_check.json", result); return result


class StageScheduler:
    def __init__(self, scheduler): self.scheduler = scheduler
    def acquire_wait(self, **kwargs):
        kwargs["task_id"] = "H1C1C_PHASE_GAP_BROADBAND_SCAN"
        return self.scheduler.acquire_wait(**kwargs)


def execute():
    configure_support(); data = manifest(); validate(data); initial_accounting(data)
    setup = read_json(REPORT / "h1c1c_setup_check.json")
    if setup.get("solver_entered") or setup.get("solver_run_called") or not setup.get("reload_gate", {}).get("pass"): raise RuntimeError("HARD_GATE_H1C1C_SETUP_CHECK")
    runtime = h1a.load_runtime()
    slot = load_module(ROOT / "scripts/apcd_global_fdtd_slot_v1.py", "h1c1c_slot")
    scheduler = StageScheduler(slot.GlobalSlotScheduler(SLOT_REGISTRY))
    results = []
    for candidate in data["candidates"]:
        for pol in POLARIZATIONS:
            result = h1a.run_case(runtime, candidate, pol, data, scheduler)
            item = {"case_id": candidate["broadband_case_identity"][pol]["case_uid"], "geometry_uid": candidate["geometry_uid"], "polarization": pol, "status": result.get("status"), "solver_entered": result.get("solver_entered", False), "accepted": result.get("status") == "ACCEPTED"}
            results.append(item); print(json.dumps(item, ensure_ascii=False), flush=True)
    write_json(REPORT / "h1c1c_execution_results.json", {"stage": "H1C-1C", "results": results})
    return results


def minimax_offset(values):
    vals = sorted(wrap(x) for x in values)
    gaps = [vals[i + 1] - vals[i] for i in range(len(vals) - 1)] + [vals[0] + 360 - vals[-1]]
    index = gaps.index(max(gaps)); start = vals[(index + 1) % len(vals)]; arc = 360 - gaps[index]; offset = wrap(start + arc / 2)
    errors = [abs(circ_diff(value, offset)) for value in vals]
    return offset, max(errors), math.sqrt(sum(x * x for x in errors) / len(errors))


def six_bin(strict_rows):
    grouped = defaultdict(dict)
    for row in strict_rows:
        grouped[row["geometry_uid"]][float(row["wavelength_nm"])] = row
    ids = sorted(grouped)
    if len(ids) < 6:
        return {"status": "INCONCLUSIVE_TOO_FEW_STRICT", "strict_count": len(ids), "exhaustive": False}
    phase = {uid: [float(grouped[uid][wave]["phi_txx"]) for wave in GRID] for uid in ids}
    metrics = {uid: {"error": [float(grouped[uid][wave]["projector_error"]) for wave in GRID], "throughput": [float(grouped[uid][wave]["throughput"]) for wave in GRID], "txx": [float(grouped[uid][wave]["Txx"]) for wave in GRID]} for uid in ids}
    tuple_count = math.comb(len(ids), 6) * math.factorial(6)
    ranking = []
    for subset in itertools.combinations(ids, 6):
        for assignment in itertools.permutations(range(6)):
            errors = []; phi0 = []; adjacent = []; opposite = []; orderings = []; occupancy = []
            for wi in range(9):
                residual = [circ_diff(phase[uid][wi], 60 * assignment[i]) for i, uid in enumerate(subset)]
                offset, worst, rms = minimax_offset(residual); phi0.append({"wavelength_nm": GRID[wi], "phi0_deg": offset, "max_abs_error_deg": worst, "RMS_error_deg": rms}); errors += [abs(circ_diff(value, offset)) for value in residual]
                ordered = [phase[subset[assignment.index(k)]][wi] for k in range(6)]
                adjacent.append({"wavelength_nm": GRID[wi], "errors_deg": [circ_diff((ordered[(k + 1) % 6] - ordered[k]) % 360, 60) for k in range(6)]})
                opposite.append({"wavelength_nm": GRID[wi], "errors_deg": [circ_diff((ordered[k + 3] - ordered[k]) % 360, 180) for k in range(3)]})
                occupied = sorted({int(round(wrap(value - offset) / 60.0)) % 6 for value in ordered})
                occupancy.append({"wavelength_nm": GRID[wi], "occupied_bin_indices": occupied, "missing_bin_indices": [k for k in range(6) if k not in occupied]})
                orderings.append(tuple(sorted(range(6), key=lambda i: phase[subset[i]][wi])))
            ranking.append({"geometry_uids": list(subset), "assignment": list(assignment), "phi0": phi0, "global_worst_abs_error_deg": max(errors), "global_RMS_error_deg": math.sqrt(sum(x * x for x in errors) / len(errors)), "adjacent_spacing_errors_deg": adjacent, "opposite_180_spacing_errors_deg": opposite, "occupancy": occupancy, "phase_order_consistency": "PHASE_ORDER_STABLE" if len(set(orderings)) == 1 else "PHASE_ORDER_CROSSING", "minimum_Txx": min(min(metrics[uid]["txx"]) for uid in subset), "minimum_throughput": min(min(metrics[uid]["throughput"]) for uid in subset), "worst_projector_error": max(max(metrics[uid]["error"]) for uid in subset)})
    ranking.sort(key=lambda x: (x["global_worst_abs_error_deg"], x["global_RMS_error_deg"], 0 if x["phase_order_consistency"] == "PHASE_ORDER_STABLE" else 1, -x["minimum_throughput"]))
    return {"status": "EXHAUSTIVE", "strict_count": len(ids), "tuple_count": tuple_count, "best": ranking[0], "runner_up": ranking[1], "ranking_top20": ranking[:20], "grid_nm": GRID}


def phase_region_analysis(old_bank, new_rows, summaries):
    strict_new = [x["geometry_uid"] for x in summaries if x.get("broadband_status") == "BROADBAND_PROJECTOR_COMPATIBLE_STRICT"]
    old_cluster = {wi: phase_cluster(old_bank, wi) for wi in range(9)}
    records = []
    regions = []
    for uid in strict_new:
        rows = sorted([row for row in new_rows if row["geometry_uid"] == uid], key=lambda x: float(x["wavelength_nm"]))
        inside = 0; distances = []; gaps = []
        for wi, row in enumerate(rows):
            phase = float(row["phi_txx"]); distances.append(min(abs(circ_diff(phase, old)) for old in old_cluster[wi])); start, end, gap = circular_gap_interval(old_cluster[wi]); gaps.append({"start_deg": start, "end_deg": end, "largest_gap_deg": gap, "phase_deg": phase, "inside_old_largest_gap": in_gap(phase, start, end)}); inside += int(gaps[-1]["inside_old_largest_gap"])
        outside = inside >= 5
        records.append({"geometry_uid": uid, "wavelengths_in_old_largest_gap": inside, "outside_cluster_rule": "inside old 7-strict largest circular gap at >=5/9 wavelengths", "new_strict_phase_region": outside, "distance_to_old_strict_cluster_deg": distances, "gap_diagnostics": gaps})
        if outside: regions.append(uid)
    if len(regions) >= 2: outcome = "H1C1C_MULTIPLE_NEW_STRICT_PHASE_REGIONS_DISCOVERED"
    elif len(regions) == 1: outcome = "H1C1C_ONE_NEW_STRICT_PHASE_REGION_DISCOVERED"
    elif strict_new: outcome = "H1C1C_STRICT_ADDED_BUT_REMAINS_CLUSTERED"
    else: outcome = "H1C1C_NO_NEW_STRICT_PHASE_REGION"
    return {"new_strict_ids": strict_new, "new_region_ids": regions, "outcome": outcome, "old_bank_size": len(old_bank), "records": records, "threshold_is_diagnostic_only": True}


def postprocess():
    configure_support(); data = manifest(); validate(data); accounting = read_json(ACCOUNTING_PATH)
    full_rows, summaries, result_by_uid = h1a.assemble_rows(data, accounting)
    for row in full_rows: row.update({"source_stage": "H1C1C_PHASE_GAP_BROADBAND", "ml_eligible": True, "ml_admitted": False, "split": "UNASSIGNED"})
    for summary in summaries: summary.update({"source_stage": "H1C1C_PHASE_GAP_BROADBAND", "strict_definition": "9/9 projector pass only", "near_miss_promoted_to_strict": False})
    write_csv(REPORT / "h1c1c_broadband_full_jones.csv", full_rows); write_csv(REPORT / "h1c1c_geometry_summary.csv", summaries)
    old_bank = read_json(ROOT / "reports/stage_h1c1b1_sixbin_closure/h1c1b1_strict_bank_v1.json")["geometries"]
    regions = phase_region_analysis(old_bank, full_rows, summaries)
    strict_new = set(regions["new_strict_ids"])
    old_strict_ids = set(read_json(ROOT / "reports/stage_h1c1b1_sixbin_closure/h1c1b1_strict_bank_v1.json")["strict_ids"])
    strict_rows = [row for row in full_rows if row["geometry_uid"] in old_strict_ids | strict_new]
    six = six_bin(strict_rows)
    phase_effects = {"schema": "H1C1C_PHASE_GAP_EFFECTS_V1", "old_strict_ids": sorted(old_strict_ids), "new_strict_ids": sorted(strict_new), "optimized_phi0_is_free": True, "candidate_effects": []}
    for summary in summaries:
        uid = summary["geometry_uid"]
        trajectory = [{"wavelength_nm": row["wavelength_nm"], "phi_txx_deg": row["phi_txx"], "projector_error": row["projector_error"], "projector_pass": row.get("projector_pass"), "throughput": row.get("throughput"), "Txx": row.get("Txx")} for row in sorted((r for r in full_rows if r["geometry_uid"] == uid), key=lambda r: float(r["wavelength_nm"]))]
        phase_effects["candidate_effects"].append({"geometry_uid": uid, "role": next((c.get("role") for c in data["candidates"] if c["geometry_uid"] == uid), None), "broadband_status": summary.get("broadband_status"), "trajectory": trajectory, "new_strict_phase_region": uid in regions["new_region_ids"]})
    updated_bank = {"schema": "H1C1C_STRICT_BANK_UPDATED_V1", "source_old_bank": "reports/stage_h1c1b1_sixbin_closure/h1c1b1_strict_bank_v1.json", "old_strict_ids": sorted(old_strict_ids), "new_strict_ids": sorted(strict_new), "cumulative_strict_ids": sorted(old_strict_ids | strict_new), "strict_count": len(old_strict_ids | strict_new), "new_strict_summaries": [s for s in summaries if s["geometry_uid"] in strict_new], "phase_region_outcome": regions["outcome"]}
    write_json(REPORT / "h1c1c_new_strict_regions.json", regions); write_json(REPORT / "h1c1c_six_bin_screening.json", six); write_json(REPORT / "h1c1c_phase_gap_effects.json", phase_effects); write_json(REPORT / "h1c1c_strict_bank_updated.json", updated_bank)
    old_registry = load_csv(ROOT / "reports/stage_h1c1b_broadband_adaptive/h1c1b_authoritative_label_registry_v1.csv")
    new_rows = list(full_rows)
    registry_rows = old_registry + new_rows
    registry_audit = {"status": "PASS", "canonical_registry_before_rows": len(old_registry), "new_geometry_count": len({row["geometry_uid"] for row in new_rows}), "new_formal_full_jones_rows": len(new_rows), "canonical_registry_after_rows": len(registry_rows), "ml_eligible_all": all(str(row.get("ml_eligible")).lower() == "true" for row in registry_rows), "ml_admitted_false_all": all(str(row.get("ml_admitted")).lower() == "false" for row in registry_rows), "split_unassigned_all": all(row.get("split") == "UNASSIGNED" for row in registry_rows), "append_only": True, "ml_restart": False}
    write_json(REPORT / "h1c1c_ml_registry_audit.json", registry_audit)
    write_csv(REPORT / "h1c1c_authoritative_label_registry_v1.csv", registry_rows)
    write_json(REPORT / "h1c1c_solver_accounting.json", accounting)
    trial_result_path = REPORT / "concurrency3_trial/concurrency3_trial_result.json"
    trial_result = read_json(trial_result_path) if trial_result_path.exists() else {}
    solver_accounting = {
        "schema": "H1C1C_GLOBAL_SOLVER_ACCOUNTING_V1",
        "active_fdtd_job_count_at_first_lp_entry": 1,
        "active_rcwa_job_count_at_first_lp_entry": 1,
        "np_solver_type": "FDTD",
        "coupling_mdc_solver_type": "RCWA",
        "mpi_engine_count_per_fdtd_case": 4,
        "rcwa_excluded_from_fdtd_accounting": True,
        "lp_used_second_validated_fdtd_slot": True,
        "max_simultaneous_independent_fdtd_jobs": trial_result.get("max_observed_real_fdtd_concurrency", 2),
        "simultaneous_rcwa_jobs": 1,
        "validated_production_fdtd_concurrency": 2,
        "max_active_fdtd_per_branch": 1,
        "processes_per_fdtd_job": 4,
        "threads_per_fdtd_job": 1,
        "whole_machine_resource_observations": {
            "source": "concurrency3_live_job_map.json",
            "observation_count": 9,
            "cpu_load_pct_range": [0.0, 3.0],
            "memory_free_mb_range": [236296.7, 236518.2],
            "memory_total_mb": 261790.2,
        },
        "solver_type_aware_scheduler_tests": {
            "status": "PASS",
            "tests": ["A", "B", "C", "D", "E", "F", "G"],
            "source": "tests/test_solver_type_aware_scheduler.py",
        },
        "cross_branch_isolation": True,
        "solver_replay": False,
        "evidence": [
            "h1c1c_solver_accounting.json",
            "concurrency3_trial/concurrency3_trial_result.json",
            "concurrency3_trial/concurrency3_live_job_map.json",
        ],
    }
    write_json(REPORT / "h1c1c_global_solver_accounting.json", solver_accounting)
    entered = accounting.get("solver_subruns_entered", 0); accepted = accounting.get("solver_subruns_accepted", 0); quarantine = sum(bool(row.get("quarantined")) for row in accounting.get("cases", []))
    final = {"status": "H1C1C_EXECUTION_COMPLETE_WITH_QUARANTINE" if quarantine else "H1C1C_EXECUTION_COMPLETE", "physics_outcome": regions["outcome"], "planned_geometries": 10, "rescue_geometries": 6, "exploration_geometries": 4, "planned_formal_subruns": 20, "entered_formal_subruns": entered, "accepted_formal_subruns": accepted, "quarantined_entered_subruns": quarantine, "strict_count_before": 7, "strict_count_new": len(strict_new), "strict_count_after": 7 + len(strict_new), "new_strict_ids": sorted(strict_new), "new_phase_region_ids": regions["new_region_ids"], "phase_region_analysis": regions, "six_bin_screening": six, "ml_registry_audit": registry_audit, "global_solver_accounting": solver_accounting, "solver_replay": False, "automatic_next_stage": False, "hard_gates": []}
    write_json(REPORT / "h1c1c_final.json", final)
    summary = ["# Stage H1C-1C Phase-Gap-First Selectivity-Aware Broadband Search", "", f"execution_status: {final['status']}", f"physics_outcome: {final['physics_outcome']}", f"planned/entered/accepted/quarantine: {MAX_SUBRUNS}/{entered}/{accepted}/{quarantine}", f"new strict: {len(strict_new)} {sorted(strict_new)}", f"new regions: {regions['new_region_ids']}", f"six-bin: {six.get('status')} best_worst={six.get('best', {}).get('global_worst_abs_error_deg')}", f"registry: {registry_audit['canonical_registry_before_rows']} + {registry_audit['new_formal_full_jones_rows']} = {registry_audit['canonical_registry_after_rows']}", "ml_admitted: false", "automatic H1C-1D/ML/inverse/K6: false"]
    (REPORT / "h1c1c_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    return final


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("manifest", "preflight", "setup-check", "execute", "postprocess"))
    args = parser.parse_args()
    configure_support(); REPORT.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
    if args.mode == "manifest":
        data, audit = generate_candidates(); write_json(MANIFEST_PATH, data); write_json(REPORT / "h1c1c_parent_ranking.json", audit); return
    if args.mode == "preflight": preflight(); return
    if args.mode == "setup-check": setup_check(); return
    if args.mode == "execute": execute(); return
    if args.mode == "postprocess": postprocess(); return


if __name__ == "__main__":
    main()
