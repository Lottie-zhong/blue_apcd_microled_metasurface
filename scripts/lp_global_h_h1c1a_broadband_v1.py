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
import re
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/stage_h1c1a_broadband_global"
OUT = ROOT / "outputs/lp_global_h_h1c1a"
RUNTIME = OUT / "runtime"
MANIFEST_PATH = REPORT / "h1c1a_candidate_manifest.json"
ACCOUNTING_PATH = REPORT / "h1c1a_solver_accounting.json"
GRID = [450.0 + 0.5 * i for i in range(9)]
H_GLOBAL_NM = 550.0
PERIOD_NM = 432.0
MATERIAL = "APCD_TIO2_NATIVE_M1"
PROJECTOR = [[1, 0], [0, 0]]
PROJECTOR_ERROR_MAX = 0.1864961370084426
BOUNDS = {
    "J1_side_nm": [102.0, 114.0],
    "J2_length_nm": [100.0, 114.0],
    "J2_width_nm": [94.0, 106.0],
    "D_nm": [180.0, 210.0],
    "Psi_deg": [-3.0, 3.0],
}
POLARIZATIONS = ("x", "y")
EXTRACTION_CONVENTION = "transmission_side_full_period_coordinate_weighted_complex_G0_endpoint_dedup_periodic_reclosure_sqrtT_over_norm_arg_txx"
BUILDER_VERSION = "h1c1a_broadband_unified_h550_builder_v1"
TARGET_BRANCH = "work/lp-global-h-manifold-v1"
SLOT_REGISTRY = Path(r"D:\project\apcd_global_fdtd_slot_registry_v1.json")
MAX_GEOMETRIES = 24
MAX_SUBRUNS = 48
GLOBAL_GEOMETRIES = 20


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_obj(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
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


def current_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def current_branch() -> str:
    return subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()


def number(value: Any) -> float | None:
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def wrap_deg(value: float) -> float:
    return (float(value) % 360.0 + 360.0) % 360.0


def circular_diff(value: float, reference: float) -> float:
    return (float(value) - float(reference) + 180.0) % 360.0 - 180.0


def circular_coverage(values: list[float]) -> float:
    vals = sorted({wrap_deg(v) for v in values})
    if len(vals) < 2:
        return 0.0
    gaps = [b - a for a, b in zip(vals, vals[1:])]
    gaps.append(vals[0] + 360.0 - vals[-1])
    return 360.0 - max(gaps)


def circular_mean(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sum(math.sin(math.radians(v)) for v in values)
    c = sum(math.cos(math.radians(v)) for v in values)
    return wrap_deg(math.degrees(math.atan2(s, c)))


def geometry_identity(j1: float, length: float, width: float, cx: float, cy: float, psi: float) -> dict[str, Any]:
    return {
        # Preserve the established static geometry identity schema so seed
        # hashes remain byte-identical across H1B and H1C1A case contracts.
        "schema": "LP_GLOBAL_H_H1B1_GEOMETRY_IDENTITY_V1",
        "H_global_nm": H_GLOBAL_NM,
        "J1_H_nm": H_GLOBAL_NM,
        "J2_H_nm": H_GLOBAL_NM,
        "bottom_plane_nm": 0.0,
        "period_nm": [PERIOD_NM, PERIOD_NM],
        "material_contract": MATERIAL,
        "J1_shape": "sharp_rectangle",
        "J2_shape": "sharp_rectangle",
        "J1_side_nm": int(j1),
        "J2_length_nm": int(length),
        "J2_width_nm": int(width),
        "J1_center_x_nm": -float(cx),
        "J1_center_y_nm": -float(cy),
        "J2_center_x_nm": float(cx),
        "J2_center_y_nm": float(cy),
        "J1_rotation_deg": 0.0,
        "J2_rotation_deg": float(psi),
        "source_z_nm": -250.0,
        "monitor_z_nm": 1000.0,
        "wavelength_nm": 450.0,
        "observable": "coordinate_weighted_full_period_complex_G0",
        "endpoint_convention": "deduplicate_periodic_endpoints_and_reclose_period",
        "normalization": "sqrt(T)/norm(weighted_Ex,weighted_Ey)",
        "phase_reference": "arg(txx)",
        "projector": PROJECTOR,
    }


def physical_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        int(row["J1_side_nm"]), int(row["J2_length_nm"]), int(row["J2_width_nm"]),
        round(float(row["J2_center_x_nm"]), 9), round(float(row["J2_center_y_nm"]), 9),
        H_GLOBAL_NM, PERIOD_NM, MATERIAL,
    )


def legalize(raw_u: list[float]) -> tuple[dict[str, float], dict[str, Any]]:
    def integer(lo: float, hi: float, u: float) -> int:
        return int(math.floor(lo + (hi - lo) * u + 0.5))

    j1 = integer(BOUNDS["J1_side_nm"][0], BOUNDS["J1_side_nm"][1], raw_u[0])
    length = integer(BOUNDS["J2_length_nm"][0], BOUNDS["J2_length_nm"][1], raw_u[1])
    width = integer(BOUNDS["J2_width_nm"][0], BOUNDS["J2_width_nm"][1], raw_u[2])
    raw_d = BOUNDS["D_nm"][0] + (BOUNDS["D_nm"][1] - BOUNDS["D_nm"][0]) * raw_u[3]
    raw_psi = BOUNDS["Psi_deg"][0] + (BOUNDS["Psi_deg"][1] - BOUNDS["Psi_deg"][0]) * raw_u[4]
    raw_cx = raw_d * math.cos(math.radians(raw_psi)) / 2.0
    raw_cy = raw_d * math.sin(math.radians(raw_psi)) / 2.0
    cx = math.floor(raw_cx * 2.0 + 0.5) / 2.0
    cy = math.floor(raw_cy * 2.0 + 0.5) / 2.0
    d = 2.0 * math.hypot(cx, cy)
    psi = math.degrees(math.atan2(cy, cx))
    point = {"J1_side_nm": j1, "J2_length_nm": length, "J2_width_nm": width, "D_nm": d, "Psi_deg": psi, "J2_center_x_nm": cx, "J2_center_y_nm": cy}
    return point, {"raw_D_nm": raw_d, "raw_Psi_deg": raw_psi, "raw_center_x_nm": raw_cx, "raw_center_y_nm": raw_cy}


def legality(point: dict[str, Any], existing_hashes: set[str], existing_keys: set[tuple[Any, ...]], seen_hashes: set[str], seen_keys: set[tuple[Any, ...]]) -> dict[str, Any]:
    j1, length, width = int(point["J1_side_nm"]), int(point["J2_length_nm"]), int(point["J2_width_nm"])
    cx, cy, d, psi = float(point["J2_center_x_nm"]), float(point["J2_center_y_nm"]), float(point["D_nm"]), float(point["Psi_deg"])
    identity = geometry_identity(j1, length, width, cx, cy, psi)
    exact_hash = sha256_obj(identity)
    direct = d - max(j1, width)
    periodic_x = PERIOD_NM - 2.0 * abs(cx) - max(j1, width)
    periodic_y = PERIOD_NM - 2.0 * abs(cy) - max(width, length)
    key = physical_key(point)
    checks = {
        "H_global_550": True,
        "period_432": True,
        "native_material": True,
        "integer_lateral_dimensions": all(float(point[k]).is_integer() for k in ("J1_side_nm", "J2_length_nm", "J2_width_nm")),
        "half_grid_center": all(abs(2.0 * point[k] - round(2.0 * point[k])) < 1e-9 for k in ("J2_center_x_nm", "J2_center_y_nm")),
        "D_domain": BOUNDS["D_nm"][0] <= d <= BOUNDS["D_nm"][1],
        "Psi_domain": BOUNDS["Psi_deg"][0] <= psi <= BOUNDS["Psi_deg"][1],
        "direct_gap_ge_60": direct >= 60.0,
        "periodic_gap_x_ge_60": periodic_x >= 60.0,
        "periodic_gap_y_ge_60": periodic_y >= 60.0,
        "cell_containment": abs(cx) + max(j1, length) / 2.0 < PERIOD_NM / 2.0 and abs(cy) + max(width, length) / 2.0 < PERIOD_NM / 2.0,
        "no_overlap": direct > 0.0,
        "exact_hash_unique": exact_hash not in existing_hashes and exact_hash not in seen_hashes,
        "physical_key_unique": key not in existing_keys and key not in seen_keys,
    }
    return {"pass": all(checks.values()), "checks": checks, "exact_hash": exact_hash, "geometry_identity": identity, "physical_key": list(key), "direct_gap_nm": direct, "periodic_gap_x_nm": periodic_x, "periodic_gap_y_nm": periodic_y}


def load_bank() -> list[dict[str, Any]]:
    bank = read_json(ROOT / "reports/stage_h1c0_broadband_global/h1c0_global_candidate_bank.json")
    if len(bank.get("candidates", [])) != 20:
        raise RuntimeError("HARD_GATE_H1C0_BANK_COUNT")
    return bank["candidates"]


def seed_selection(bank: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_id = {row["geometry_id"]: row for row in bank}
    required = ["H1B2_C_UPPER_EDGE_LOCAL_CONTINUATION", "H1B1_A_LOWER_COMPATIBLE_EDGE", "H1B1_D_D_PSI_CONTRAST"]
    if any(key not in by_id for key in required):
        raise RuntimeError("HARD_GATE_SEED_PROVENANCE_MISSING")
    chosen = [by_id[key] for key in required]
    phases = [float(row["450nm_reference"]["phase_deg"]) for row in chosen]
    audit_rows = []
    for row in bank:
        ref = row["450nm_reference"]
        if row["geometry_id"] in {x["geometry_id"] for x in chosen} or not ref.get("projector_compatible"):
            continue
        phase = float(ref["phase_deg"])
        min_distance = min(abs(circular_diff(phase, p)) for p in phases)
        txx = float(ref["Txx"] or 0.0)
        reasonable = 0.8 <= txx <= 1.2
        audit_rows.append({"geometry_id": row["geometry_id"], "phase_deg": phase, "Txx": txx, "min_circular_distance_to_seeds_deg": min_distance, "reasonable_throughput": reasonable, "eligible": True})
    eligible = [row for row in audit_rows if row["reasonable_throughput"]]
    if not eligible:
        raise RuntimeError("HARD_GATE_SEED4_NO_REASONABLE_THROUGHPUT")
    seed4_audit = sorted(eligible, key=lambda x: (-x["min_circular_distance_to_seeds_deg"], -x["Txx"], x["geometry_id"]))
    seed4 = by_id[seed4_audit[0]["geometry_id"]]
    chosen.append(seed4)
    return chosen, {"schema": "H1C1A_SEED_SELECTION_AUDIT_V1", "rule": "fixed_seed1_seed2_then_best_450_projector_interior_seed3_then_maximin_circular_phase_seed4_with_Txx_0.8_to_1.2", "seed_ids": [x["geometry_id"] for x in chosen], "seed4_ranked_candidates": seed4_audit}


def make_record(uid: str, row: dict[str, Any], role: str, source: str, global_or_seed: str, seed_number: int | None, legality_data: dict[str, Any], history: dict[str, Any] | None) -> dict[str, Any]:
    coords = row["coordinates_5d"] if "coordinates_5d" in row else row
    d = float(coords["D_nm"])
    psi = float(coords["Psi_deg"])
    cx = round(d * math.cos(math.radians(psi))) / 2.0
    cy = round(d * math.sin(math.radians(psi))) / 2.0
    exact_hash = str(row.get("exact_hash") or legality_data["exact_hash"])
    case_base = f"H1C1A_{uid}"
    contract_hash = sha256_obj({"H_global_nm": H_GLOBAL_NM, "grid_nm": GRID, "period_nm": [PERIOD_NM, PERIOD_NM], "material": MATERIAL, "projector": PROJECTOR, "extraction": EXTRACTION_CONVENTION})
    identities = {}
    for pol in POLARIZATIONS:
        identities[pol] = {"stage": "H1C1A", "geometry_uid": uid, "exact_geometry_hash_sha256": exact_hash, "H_global_nm": H_GLOBAL_NM, "polarization": pol, "material_contract": MATERIAL, "period_nm": [PERIOD_NM, PERIOD_NM], "wavelength_grid_nm": GRID, "projector": PROJECTOR, "formal_extraction_convention": EXTRACTION_CONVENTION, "builder_version": BUILDER_VERSION, "physical_contract_sha256": contract_hash, "case_uid": f"{case_base}_P{pol}"}
    return {
        "geometry_uid": uid,
        "exact_hash": exact_hash,
        "coordinates_5d": {"J1_side_nm": float(coords["J1_side_nm"]), "J2_length_nm": float(coords["J2_length_nm"]), "J2_width_nm": float(coords["J2_width_nm"]), "D_nm": d, "Psi_deg": psi},
        "J2_center_x_nm": cx,
        "J2_center_y_nm": cy,
        "H_global_nm": H_GLOBAL_NM,
        "J1_H_nm": H_GLOBAL_NM,
        "J2_H_nm": H_GLOBAL_NM,
        "role": role,
        "source": source,
        "global_or_seed": global_or_seed,
        "seed_number": seed_number,
        "legality": legality_data,
        "prior_450nm_provenance": history,
        "broadband_case_identity": identities,
    }


def generate_manifest() -> dict[str, Any]:
    if current_branch() != TARGET_BRANCH:
        raise RuntimeError("HARD_GATE_WRONG_BRANCH")
    bank = load_bank()
    existing_hashes = {str(row["exact_hash"]) for row in bank}
    existing_keys: set[tuple[Any, ...]] = set()
    for row in bank:
        coords = row["coordinates_5d"]
        d, psi = float(coords["D_nm"]), float(coords["Psi_deg"])
        cx, cy = round(d * math.cos(math.radians(psi))) / 2.0, round(d * math.sin(math.radians(psi))) / 2.0
        existing_keys.add((int(coords["J1_side_nm"]), int(coords["J2_length_nm"]), int(coords["J2_width_nm"]), round(cx, 9), round(cy, 9), H_GLOBAL_NM, PERIOD_NM, MATERIAL))
    seeds, seed_audit = seed_selection(bank)
    seed_records = []
    for index, row in enumerate(seeds, 1):
        coords = row["coordinates_5d"]
        d, psi = float(coords["D_nm"]), float(coords["Psi_deg"])
        cx, cy = round(d * math.cos(math.radians(psi))) / 2.0, round(d * math.sin(math.radians(psi))) / 2.0
        point = {**coords, "J2_center_x_nm": cx, "J2_center_y_nm": cy}
        check = legality(point, set(), set(), set(), set())
        if check["exact_hash"] != row["exact_hash"]:
            # H1A used an earlier authoritative geometry-identity schema.  The
            # seed must retain that exact historical hash; do not silently
            # replace identity with a recomputed H1C1A hash.
            if row["source_stage"] != "H1A":
                raise RuntimeError(f"HARD_GATE_SEED_EXACT_HASH_RECOMPUTE:{row['geometry_id']}:{check['exact_hash']}:{row['exact_hash']}")
            check["recomputed_hash"] = check["exact_hash"]
            check["exact_hash"] = row["exact_hash"]
            check["hash_continuity"] = "AUTHORITATIVE_H1A_HASH_PRESERVED"
        seed_records.append(make_record(f"SEED{index}_{row['geometry_id']}", row, f"SEED{index}_450NM_COMPATIBLE_CONTROL", "H1C0_H550_AUTHORITATIVE_GEOMETRY", "SEED", index, check, {"source_stage": row["source_stage"], "geometry_id": row["geometry_id"], "exact_hash": row["exact_hash"], "reference_450": row["450nm_reference"]}))
    global_records = []
    generation_audit = []
    seen_hashes = set(existing_hashes)
    seen_keys = set(existing_keys)
    try:
        from scipy.stats import qmc
    except ImportError as exc:
        raise RuntimeError("HARD_GATE_SOBOL_UNAVAILABLE") from exc
    samples = qmc.Sobol(d=5, scramble=False, seed=0).random_base2(m=8)
    rejected_since_accept: list[int] = []
    for raw_index, raw in enumerate(samples):
        raw_u = [float(x) for x in raw]
        point, projection = legalize(raw_u)
        check = legality(point, existing_hashes, existing_keys, seen_hashes, seen_keys)
        audit = {"sobol_index": raw_index, "raw_unit_point": raw_u, "raw_physical_point": {"J1_side_nm": BOUNDS["J1_side_nm"][0] + (BOUNDS["J1_side_nm"][1] - BOUNDS["J1_side_nm"][0]) * raw_u[0], "J2_length_nm": BOUNDS["J2_length_nm"][0] + (BOUNDS["J2_length_nm"][1] - BOUNDS["J2_length_nm"][0]) * raw_u[1], "J2_width_nm": BOUNDS["J2_width_nm"][0] + (BOUNDS["J2_width_nm"][1] - BOUNDS["J2_width_nm"][0]) * raw_u[2], "D_nm": projection["raw_D_nm"], "Psi_deg": projection["raw_Psi_deg"]}, "legalized_point": point, "legality": check, "decision": "ACCEPTED_GLOBAL" if check["pass"] else "REJECTED", "replacement_provenance": {"replaces_rejected_sobol_indices": list(rejected_since_accept)} if check["pass"] and rejected_since_accept else None}
        generation_audit.append(audit)
        if not check["pass"]:
            rejected_since_accept.append(raw_index)
            continue
        uid = f"GLOBAL_{len(global_records) + 1:03d}"
        source_row = {"coordinates_5d": {k: point[k] for k in ("J1_side_nm", "J2_length_nm", "J2_width_nm", "D_nm", "Psi_deg")}}
        global_records.append(make_record(uid, source_row, "GLOBAL_SOBOL_SPACE_FILLING", "H1C1A_DETERMINISTIC_SOBOL_SCRAMBLE_FALSE_SEED_0", "GLOBAL", None, check, {"sobol_index": raw_index, "raw_unit_point": raw_u, "legalized_point": point, "replacement_provenance": audit["replacement_provenance"]}))
        seen_hashes.add(check["exact_hash"])
        seen_keys.add(tuple(check["physical_key"]))
        rejected_since_accept = []
        if len(global_records) == GLOBAL_GEOMETRIES:
            break
    if len(global_records) != GLOBAL_GEOMETRIES:
        raise RuntimeError(f"HARD_GATE_GLOBAL_SPACE_FILLING_COUNT:{len(global_records)}")
    candidates = global_records + seed_records
    if len(candidates) != MAX_GEOMETRIES or len({x["exact_hash"] for x in candidates}) != MAX_GEOMETRIES:
        raise RuntimeError("HARD_GATE_EXACTLY_24_UNIQUE_CASES")
    contract = {"schema": "H1C1A_BROADBAND_PHYSICS_CONTRACT_V1", "H_global_nm": H_GLOBAL_NM, "J1_H_equals_J2_H": True, "wavelength_grid_nm": GRID, "period_nm": [PERIOD_NM, PERIOD_NM], "material": MATERIAL, "projector": PROJECTOR, "phase": "arg(txx)", "throughput_gate": "NONE_INVENTED; min_median_max_only", "projector_error_threshold": PROJECTOR_ERROR_MAX, "strict_semantics": "x_accepted_and_y_accepted_and_full_jones_valid_and_projector_pass_at_all_9_wavelengths", "extraction": EXTRACTION_CONVENTION, "one_broadband_run_per_polarization": True}
    payload = {"schema": "H1C1A_CANDIDATE_MANIFEST_V1", "stage": "H1C-1A", "status": "FROZEN_READY", "branch": current_branch(), "head": current_head(), "worktree": str(ROOT), "contract": contract, "contract_sha256": sha256_obj(contract), "solver_authorization": {"new_geometries": MAX_GEOMETRIES, "global_geometries": GLOBAL_GEOMETRIES, "seed_geometries": 4, "formal_x_y_subruns": MAX_SUBRUNS, "max_global_fdtd_concurrency": 2, "max_active_fdtd_per_branch": 1, "processes_per_job": 4, "threads_per_job": 1, "one_run_returns_all_wavelengths": True}, "seed_selection_audit": seed_audit, "global_generation_audit": generation_audit, "candidates": candidates}
    payload["freeze_sha256"] = sha256_obj(payload)
    return payload


def ensure_manifest() -> dict[str, Any]:
    generated = generate_manifest()
    if MANIFEST_PATH.exists():
        existing = read_json(MANIFEST_PATH)
        frozen_payload = {key: value for key, value in existing.items() if key != "freeze_sha256"}
        if existing.get("freeze_sha256") != sha256_obj(frozen_payload):
            raise RuntimeError("HARD_GATE_FROZEN_MANIFEST_TAMPERED")
        existing_identity = [(row.get("geometry_uid"), row.get("exact_hash"), row.get("global_or_seed")) for row in existing.get("candidates", [])]
        generated_identity = [(row.get("geometry_uid"), row.get("exact_hash"), row.get("global_or_seed")) for row in generated.get("candidates", [])]
        if existing_identity != generated_identity:
            raise RuntimeError("HARD_GATE_FROZEN_MANIFEST_CHANGED")
        return existing
    write_json(MANIFEST_PATH, generated)
    write_json(REPORT / "h1c1a_seed_selection_audit.json", generated["seed_selection_audit"])
    return generated


def initial_accounting(manifest: dict[str, Any]) -> dict[str, Any]:
    cases = []
    for candidate in manifest["candidates"]:
        for pol in POLARIZATIONS:
            case_id = candidate["broadband_case_identity"][pol]["case_uid"]
            cases.append({"case_id": case_id, "geometry_uid": candidate["geometry_uid"], "exact_hash": candidate["exact_hash"], "polarization": pol, "planned": True, "attempted": False, "solver_entered": False, "accepted": False, "recovered": False, "quarantined": False})
    if ACCOUNTING_PATH.exists():
        old = read_json(ACCOUNTING_PATH)
        if old.get("manifest_freeze_sha256") != manifest["freeze_sha256"] and old.get("solver_entries"):
            raise RuntimeError("HARD_GATE_ACCOUNTING_MANIFEST_MISMATCH_AFTER_ENTRY")
        if old.get("manifest_freeze_sha256") == manifest["freeze_sha256"]:
            return old
    payload = {"schema": "H1C1A_SOLVER_ACCOUNTING_V1", "stage": "H1C-1A", "manifest_freeze_sha256": manifest["freeze_sha256"], "solver_budget_planned": MAX_SUBRUNS, "solver_subruns_entered": 0, "solver_subruns_accepted": 0, "H_global_nm": H_GLOBAL_NM, "max_global_fdtd_concurrency": 2, "max_active_fdtd_per_branch": 1, "processes_per_job": 4, "threads_per_job": 1, "cases": cases, "solver_entries": [], "status": "PLANNED"}
    write_json(ACCOUNTING_PATH, payload)
    return payload


def update_accounting(case_id: str, updates: dict[str, Any], entry: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = read_json(ACCOUNTING_PATH)
    for row in payload["cases"]:
        if row["case_id"] == case_id:
            row.update(updates)
            break
    else:
        raise RuntimeError(f"HARD_GATE_UNKNOWN_CASE:{case_id}")
    if entry is not None and not any(x.get("case_id") == case_id for x in payload["solver_entries"]):
        payload["solver_entries"].append(entry)
    payload["solver_subruns_entered"] = sum(bool(x.get("solver_entered")) for x in payload["cases"])
    payload["solver_subruns_accepted"] = sum(bool(x.get("accepted")) for x in payload["cases"])
    if payload["solver_subruns_entered"] >= MAX_SUBRUNS:
        payload["status"] = "COMPLETE" if payload["solver_subruns_accepted"] == MAX_SUBRUNS else "PARTIAL_DATA_PRESERVED"
    else:
        payload["status"] = "RUNNING"
    write_json(ACCOUNTING_PATH, payload)
    return payload


def load_runtime():
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))
    runner = load_module(ROOT / "scripts/lp_ml_inverse_stage1_fdt_validation_runner_v1.py", "h1c1a_legacy_support")
    from metasurface.config import load_runtime_config
    from metasurface.lumapi_runner import import_lumapi
    config = load_runtime_config(str(ROOT / "configs/runtime.yaml"))
    return type("Runtime", (), {"lumapi": import_lumapi(config), "hide_gui": getattr(config, "hide_gui", True), "runner": runner})()


def safe_get(fdtd: Any, object_name: str, key: str) -> Any:
    try:
        value = fdtd.getnamed(object_name, key)
        if hasattr(value, "item"):
            try:
                return value.item()
            except Exception:
                pass
        return value
    except Exception as exc:
        return f"UNAVAILABLE:{type(exc).__name__}:{exc}"


def build(fdtd: Any, candidate: dict[str, Any], pol: str) -> dict[str, Any]:
    import numpy as np
    from metasurface.lumerical_native_materials import ensure_apcd_native_materials, get_lumerical_material_name
    nm = 1e-9
    fdtd.switchtolayout()
    fdtd.deleteall()
    ensure_apcd_native_materials(fdtd)
    px = py = PERIOD_NM * nm
    h = H_GLOBAL_NM * nm
    mat = get_lumerical_material_name(MATERIAL)
    fdtd.addfdtd()
    fdtd.set("dimension", "3D")
    for key, value in [("x span", px), ("y span", py), ("z min", -500 * nm), ("z max", 1200 * nm), ("x min bc", "Periodic"), ("x max bc", "Periodic"), ("y min bc", "Periodic"), ("y max bc", "Periodic"), ("z min bc", "PML"), ("z max bc", "PML"), ("mesh accuracy", 2), ("simulation time", 1000e-15), ("background material", "<Object defined dielectric>"), ("index", 1.0)]:
        fdtd.set(key, value)
    fdtd.setglobalmonitor("frequency points", len(GRID))
    fdtd.setglobalmonitor("use wavelength spacing", True)
    fdtd.setglobalmonitor("use source limits", True)
    cx = float(candidate["J2_center_x_nm"]) * nm
    cy = float(candidate["J2_center_y_nm"]) * nm
    fdtd.addrect(); fdtd.set("name", "pillar_1"); fdtd.set("x span", float(candidate["coordinates_5d"]["J1_side_nm"]) * nm); fdtd.set("y span", float(candidate["coordinates_5d"]["J1_side_nm"]) * nm); fdtd.set("x", -cx); fdtd.set("y", -cy); fdtd.set("z min", 0); fdtd.set("z max", h); fdtd.set("first axis", "z"); fdtd.set("rotation 1", 0); fdtd.set("material", mat)
    fdtd.addrect(); fdtd.set("name", "pillar_2"); fdtd.set("x span", float(candidate["coordinates_5d"]["J2_length_nm"]) * nm); fdtd.set("y span", float(candidate["coordinates_5d"]["J2_width_nm"]) * nm); fdtd.set("x", cx); fdtd.set("y", cy); fdtd.set("z min", 0); fdtd.set("z max", h); fdtd.set("first axis", "z"); fdtd.set("rotation 1", float(candidate["coordinates_5d"]["Psi_deg"])); fdtd.set("material", mat)
    fdtd.addplane(); fdtd.set("name", "source"); fdtd.set("injection axis", "z"); fdtd.set("direction", "Forward"); fdtd.set("x span", px); fdtd.set("y span", py); fdtd.set("z", -250 * nm); fdtd.set("wavelength start", GRID[0] * nm); fdtd.set("wavelength stop", GRID[-1] * nm); fdtd.set("polarization angle", 0 if pol == "x" else 90)
    for name, monitor_type in (("T", "2D Z-normal"), ("field_monitor", "2D Z-normal")):
        if name == "T": fdtd.addpower()
        else: fdtd.addprofile()
        fdtd.set("name", name); fdtd.set("monitor type", monitor_type); fdtd.set("x span", px); fdtd.set("y span", py); fdtd.set("z", 1000 * nm); fdtd.set("override global monitor settings", True); fdtd.set("use wavelength spacing", True); fdtd.set("frequency points", len(GRID)); fdtd.set("use source limits", True)
    return {"material_name": mat, "geometry_readback": {"J1_center_x_nm": safe_get(fdtd, "pillar_1", "x"), "J1_center_y_nm": safe_get(fdtd, "pillar_1", "y"), "J2_center_x_nm": safe_get(fdtd, "pillar_2", "x"), "J2_center_y_nm": safe_get(fdtd, "pillar_2", "y"), "J1_material": safe_get(fdtd, "pillar_1", "material"), "J2_material": safe_get(fdtd, "pillar_2", "material")}, "config_readback": {"source_start_nm": float(safe_get(fdtd, "source", "wavelength start")) * 1e9, "source_stop_nm": float(safe_get(fdtd, "source", "wavelength stop")) * 1e9, "T_frequency_points": safe_get(fdtd, "T", "frequency points"), "field_frequency_points": safe_get(fdtd, "field_monitor", "frequency points"), "monitor_z_nm": float(safe_get(fdtd, "field_monitor", "z")) * 1e9, "H_global_nm": H_GLOBAL_NM}}


def setup_gate(fdtd: Any, candidate: dict[str, Any], pol: str) -> dict[str, Any]:
    from metasurface.lumerical_native_materials import get_lumerical_material_name
    checks = {"source_start_nm": float(safe_get(fdtd, "source", "wavelength start")) * 1e9, "source_stop_nm": float(safe_get(fdtd, "source", "wavelength stop")) * 1e9, "monitor_z_nm": float(safe_get(fdtd, "field_monitor", "z")) * 1e9, "T_frequency_points": float(safe_get(fdtd, "T", "frequency points")), "field_frequency_points": float(safe_get(fdtd, "field_monitor", "frequency points")), "J1_material": safe_get(fdtd, "pillar_1", "material"), "J2_material": safe_get(fdtd, "pillar_2", "material"), "J2_rotation_deg": float(safe_get(fdtd, "pillar_2", "rotation 1"))}
    expected = {"source_start_nm": GRID[0], "source_stop_nm": GRID[-1], "monitor_z_nm": 1000.0, "T_frequency_points": 9.0, "field_frequency_points": 9.0, "J1_material": get_lumerical_material_name(MATERIAL), "J2_material": get_lumerical_material_name(MATERIAL), "J2_rotation_deg": float(candidate["coordinates_5d"]["Psi_deg"])}
    checks_pass = all(abs(checks[key] - value) < 1e-7 if isinstance(value, float) else checks[key] == value for key, value in expected.items())
    return {"pass": bool(checks_pass), "checks": checks, "expected": expected, "input_polarization": pol, "expected_wavelengths_nm": GRID, "observable": "transmission_side_coordinate_weighted_complex_G0", "normalization": "sqrt(T)/norm(weighted_Ex,weighted_Ey)", "solver_runs_for_spectrum": 1}


def extract_broadband(fdtd: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    import numpy as np
    low = load_module(ROOT / "scripts/lp_legacy_h500_sixbin_formal_replay_450_v1.py", "h1c1a_grid_support")
    transmission = np.asarray(fdtd.transmission("T")).squeeze()
    transmission = np.real(np.asarray(transmission).reshape(-1))
    if len(transmission) != len(GRID):
        raise RuntimeError(f"BROADBAND_TRANSMISSION_GRID_MISMATCH:{len(transmission)}")
    x, y, ex, ey, grid = low.base.b.f1.grid_plane(fdtd, float(transmission[0]))
    ex, ey = np.asarray(ex).squeeze(), np.asarray(ey).squeeze()
    if ex.ndim == 2:
        ex, ey = ex[:, :, None], ey[:, :, None]
    if ex.shape[2] != len(GRID):
        raise RuntimeError(f"BROADBAND_FIELD_GRID_MISMATCH:{ex.shape}")
    rows = []
    for index, wavelength in enumerate(GRID):
        raw_x = low.base.b.f1.periodic_weighted(x, y, ex[:, :, index], grid["x_periodic_duplicate_endpoint"], grid["y_periodic_duplicate_endpoint"])
        raw_y = low.base.b.f1.periodic_weighted(x, y, ey[:, :, index], grid["x_periodic_duplicate_endpoint"], grid["y_periodic_duplicate_endpoint"])
        t_value = float(transmission[index])
        if t_value < 0:
            raise RuntimeError(f"NORMALIZATION_REVIEW_REQUIRED_NEGATIVE_T:{wavelength}:{t_value}")
        nx, ny = low.base.b.f1.normalize_pair(raw_x, raw_y, t_value)
        rows.append({"wavelength_nm": wavelength, "raw_weighted_Ex_real": float(raw_x.real), "raw_weighted_Ex_imag": float(raw_x.imag), "raw_weighted_Ey_real": float(raw_y.real), "raw_weighted_Ey_imag": float(raw_y.imag), "weighted_Ex_real": float(nx.real), "weighted_Ex_imag": float(nx.imag), "weighted_Ey_real": float(ny.real), "weighted_Ey_imag": float(ny.imag), "source_T": t_value, "normalization_scale": float(math.sqrt(t_value) / max(math.hypot(abs(raw_x), abs(raw_y)), 1e-30)), "selected_power": float(abs(nx) ** 2 + abs(ny) ** 2), "closure_residual": 0.0, "complex_normalization_residual": 0.0})
    return rows, {**grid, "wavelengths_nm": GRID, "grid_exact": True}


def case_identity(candidate: dict[str, Any], pol: str, manifest: dict[str, Any]) -> dict[str, Any]:
    return dict(candidate["broadband_case_identity"][pol], manifest_freeze_sha256=manifest["freeze_sha256"])


def next_attempt(case_dir: Path, case_id: str) -> tuple[str, Path, Path]:
    numbers = []
    for path in case_dir.glob("attempt_provenance*.json"):
        match = re.search(r"_attempt_(\d{3})\.json$", path.name)
        numbers.append(int(match.group(1)) if match else 1)
    index = max(numbers, default=0) + 1
    attempt = f"{case_id}_attempt_{index:03d}"
    suffix = "attempt_provenance.json" if index == 1 else f"attempt_provenance_attempt_{index:03d}.json"
    return attempt, case_dir / suffix, case_dir / f"{attempt}_pre.fsp"


def checkpoint_result(case_dir: Path, identity: dict[str, Any]) -> dict[str, Any] | None:
    path = case_dir / "checkpoint.json"
    if not path.exists():
        return None
    try:
        data = read_json(path)
    except Exception:
        return None
    if data.get("status") != "ACCEPTED" or data.get("case_identity_sha256") != sha256_obj(identity) or len(data.get("rows", [])) != len(GRID):
        return None
    return {"status": "ACCEPTED", "solver_entered": True, "recovered_from_checkpoint": True, "case_id": data.get("case_id"), "geometry_uid": data.get("geometry_uid"), "polarization": data.get("polarization"), "rows": data["rows"], "grid_audit": data.get("grid_audit"), "checkpoint_path": str(path), "checkpoint_sha256": sha256_file(path), "attempt_id": data.get("attempt_id"), "case_identity": identity, "case_identity_sha256": sha256_obj(identity)}


def run_case(runtime: Any, candidate: dict[str, Any], pol: str, manifest: dict[str, Any], scheduler: Any) -> dict[str, Any]:
    identity = case_identity(candidate, pol, manifest)
    cid = identity["case_uid"]
    case_dir = RUNTIME / "cases" / cid
    case_dir.mkdir(parents=True, exist_ok=True)
    recovered = checkpoint_result(case_dir, identity)
    if recovered:
        update_accounting(cid, {"attempted": True, "solver_entered": True, "accepted": True, "recovered": True, "status": "ACCEPTED"})
        return recovered
    accounting = read_json(ACCOUNTING_PATH)
    if any(entry.get("case_id") == cid and entry.get("solver_entered") is True for entry in accounting.get("solver_entries", [])):
        result = {"status": "QUARANTINED_ENTERED_NO_RECOVERY", "solver_entered": True, "case_id": cid, "geometry_uid": candidate["geometry_uid"], "error": "entered=true exact H1C1A case has no accepted checkpoint; replay forbidden"}
        update_accounting(cid, {"attempted": True, "solver_entered": True, "quarantined": True, "status": result["status"]})
        return result
    attempt_id, provenance_path, pre_fsp = next_attempt(case_dir, cid)
    contract_hash = manifest["contract_sha256"]
    record: dict[str, Any] = {"schema": "H1C1A_ATTEMPT_PROVENANCE_V1", "case_id": cid, "attempt_id": attempt_id, "geometry_uid": candidate["geometry_uid"], "exact_hash": candidate["exact_hash"], "case_identity": identity, "case_identity_sha256": sha256_obj(identity), "branch": current_branch(), "worktree": str(ROOT), "physical_contract_sha256": contract_hash, "solver_entered": False, "entered_solver": False, "slot_acquired": False, "processes": 4, "threads": 1, "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "wavelength_grid_nm": GRID, "solver_runs_for_spectrum": 1}
    write_json(provenance_path, record)
    update_accounting(cid, {"attempted": True, "status": "PREPARING", "attempt_id": attempt_id})
    f = None
    lease = None
    solver_completed = False
    try:
        f = runtime.lumapi.FDTD(hide=runtime.hide_gui)
        setup = build(f, candidate, pol)
        f.save(str(pre_fsp))
        record.update({"setup": setup, "pre_fsp_path": str(pre_fsp), "pre_fsp_sha256": sha256_file(pre_fsp), "status": "PREPARED"})
        f.close(); f = None
        write_json(provenance_path, record)
        lease = scheduler.acquire_wait(branch=TARGET_BRANCH, worktree=str(ROOT), task_id="H1C1A_BROADBAND_GLOBAL", case_uid=cid, pid=os.getpid(), metadata={"task_class": "H1C1A_FORMAL_BROADBAND_FDTD", "attempt_id": attempt_id, "polarization": pol, "H_global_nm": H_GLOBAL_NM}, timeout_s=21600.0, poll_s=15.0)
        record.update({"slot_acquired": True, "slot_id": lease.slot_id, "slot_acquire_time": lease.record.get("slot_acquire_time"), "concurrent_peer_branch": lease.record.get("concurrent_peer_branch", []), "admission_snapshot": lease.record.get("admission_snapshot"), "status": "SLOT_ACQUIRED"})
        lease.start_heartbeat()
        write_json(provenance_path, record)
        f = runtime.lumapi.FDTD(hide=runtime.hide_gui)
        f.load(str(pre_fsp))
        gate = setup_gate(f, candidate, pol)
        record.update({"configuration_gate": gate, "status": "PREFLIGHT_GATED"})
        write_json(provenance_path, record)
        if not gate["pass"]:
            update_accounting(cid, {"status": "QUARANTINED_PREFLIGHT_GATE", "quarantined": True})
            record.update({"status": "QUARANTINED_PREFLIGHT_GATE", "quarantined": True})
            return record
        entered_utc = dt.datetime.now(dt.timezone.utc).isoformat()
        lease.mark_solver_entered(entered_utc)
        entry = {"case_id": cid, "attempt_id": attempt_id, "geometry_uid": candidate["geometry_uid"], "exact_hash": candidate["exact_hash"], "polarization": pol, "solver_entered": True, "entered_solver": True, "entered_utc": entered_utc, "pre_fsp_sha256": record["pre_fsp_sha256"], "physical_contract_sha256": contract_hash, "case_identity_sha256": sha256_obj(identity), "slot_id": lease.slot_id, "processes": 4, "threads": 1}
        record.update({"solver_entered": True, "entered_solver": True, "entered_utc": entered_utc, "solver_start": entered_utc, "status": "ENTERED"})
        write_json(provenance_path, record)
        update_accounting(cid, {"solver_entered": True, "entered_utc": entered_utc, "status": "ENTERED"}, entry)
        f.run()
        solver_completed = True
        record["solver_complete"] = dt.datetime.now(dt.timezone.utc).isoformat()
        run_fsp = case_dir / f"{attempt_id}_run.fsp"
        try:
            f.save(str(run_fsp)); record["run_fsp_path"] = str(run_fsp); record["run_fsp_sha256"] = sha256_file(run_fsp)
        except Exception as save_exc:
            record["run_fsp_save_error"] = f"{type(save_exc).__name__}: {save_exc}"
        lease.release("SOLVER_COMPLETED", record["solver_complete"]); lease = None
        record["slot_release_time"] = dt.datetime.now(dt.timezone.utc).isoformat()
        rows, grid = extract_broadband(f)
        checkpoint = {"schema": "H1C1A_CHECKPOINT_V1", "status": "ACCEPTED", "case_id": cid, "attempt_id": attempt_id, "geometry_uid": candidate["geometry_uid"], "exact_hash": candidate["exact_hash"], "case_identity": identity, "case_identity_sha256": sha256_obj(identity), "geometry": candidate, "polarization": pol, "physical_contract": manifest["contract"], "physical_contract_sha256": contract_hash, "setup": setup, "configuration_gate": gate, "rows": rows, "grid_audit": grid, "solver_entered": True, "solver_replay": False}
        write_json(case_dir / "checkpoint.json", checkpoint)
        record.update({"status": "ACCEPTED", "rows": rows, "grid_audit": grid, "checkpoint_path": str(case_dir / "checkpoint.json"), "checkpoint_sha256": sha256_file(case_dir / "checkpoint.json")})
        update_accounting(cid, {"status": "ACCEPTED", "accepted": True, "solver_complete": record["solver_complete"], "checkpoint_path": record["checkpoint_path"]})
        return record
    except Exception as exc:
        record.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc(), "retained_data_status": "entered_evidence_preserved_no_replay" if record.get("solver_entered") else "pre_entry_failure_evidence_preserved"})
        update_accounting(cid, {"status": "FAILED", "quarantined": bool(record.get("solver_entered")), "solver_entered": bool(record.get("solver_entered"))})
        return record
    finally:
        if lease is not None:
            try:
                lease.release("FAILED_ENTERED" if record.get("solver_entered") else "FAILED_PRE_ENTRY")
            except Exception as release_exc:
                record["slot_release_error"] = f"{type(release_exc).__name__}: {release_exc}"
        if f is not None:
            try:
                f.close()
            except Exception as close_exc:
                record["close_error"] = f"{type(close_exc).__name__}: {close_exc}"
        write_json(provenance_path, record)


def complex_value(row: dict[str, Any], real: str, imag: str) -> complex:
    return complex(float(row[real]), float(row[imag]))


def metrics(jones: list[list[complex]]) -> dict[str, Any]:
    import numpy as np
    matrix = np.asarray(jones, dtype=complex)
    txx, txy, tyx, tyy = matrix[0, 0], matrix[0, 1], matrix[1, 0], matrix[1, 1]
    norm = float(np.linalg.norm(matrix))
    error = max(0.0, min(1.0, 1.0 - abs(txx) ** 2 / (norm ** 2))) if norm else 1.0
    return {"Re_txx": float(txx.real), "Im_txx": float(txx.imag), "Re_txy": float(txy.real), "Im_txy": float(txy.imag), "Re_tyx": float(tyx.real), "Im_tyx": float(tyx.imag), "Re_tyy": float(tyy.real), "Im_tyy": float(tyy.imag), "phi_txx": wrap_deg(math.degrees(math.atan2(txx.imag, txx.real))), "projector_error": error, "Txx": float(abs(txx) ** 2), "Txy": float(abs(txy) ** 2), "Tyx": float(abs(tyx) ** 2), "Tyy": float(abs(tyy) ** 2), "full_jones_frobenius_norm": norm, "full_jones_finite": bool(np.isfinite(matrix.real).all() and np.isfinite(matrix.imag).all())}


def status_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    accepted = [bool(row.get("x_accepted")) and bool(row.get("y_accepted")) and bool(row.get("full_jones_accepted")) for row in rows]
    passes = [bool(ok and float(row["projector_error"]) <= PROJECTOR_ERROR_MAX) for ok, row in zip(accepted, rows)]
    failed = [row["wavelength_nm"] for row, passed in zip(rows, passes) if not passed]
    pass_count = sum(passes)
    center_pass = bool(rows and passes[0])
    if pass_count == len(GRID) and len(rows) == len(GRID):
        status = "BROADBAND_PROJECTOR_COMPATIBLE_STRICT"
    elif center_pass and len(rows) == len(GRID):
        status = "CENTER_ONLY_COMPATIBLE"
    elif pass_count > 0:
        status = "PARTIALLY_COMPATIBLE"
    else:
        status = "INCOMPATIBLE"
    errors = [float(row["projector_error"]) for row in rows]
    txx = [float(row["Txx"]) for row in rows]
    throughput = [float(row["throughput"]) for row in rows]
    return {"broadband_status": status, "projector_pass_count": pass_count, "failed_wavelengths": failed, "worst_projector_error": max(errors, default=None), "median_projector_error": sorted(errors)[len(errors) // 2] if errors else None, "min_Txx": min(txx, default=None), "median_Txx": sorted(txx)[len(txx) // 2] if txx else None, "max_Txx": max(txx, default=None), "min_throughput": min(throughput, default=None), "median_throughput": sorted(throughput)[len(throughput) // 2] if throughput else None, "max_throughput": max(throughput, default=None)}


def assemble_rows(manifest: dict[str, Any], accounting: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    full_rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    result_by_uid: dict[str, dict[str, Any]] = {}
    for candidate in manifest["candidates"]:
        pol_results = {}
        for pol in POLARIZATIONS:
            cid = candidate["broadband_case_identity"][pol]["case_uid"]
            cp = RUNTIME / "cases" / cid / "checkpoint.json"
            if cp.exists():
                data = read_json(cp)
                if data.get("status") == "ACCEPTED" and len(data.get("rows", [])) == len(GRID):
                    pol_results[pol] = data
        rows = []
        for index, wavelength in enumerate(GRID):
            if set(pol_results) != set(POLARIZATIONS):
                break
            x, y = pol_results["x"]["rows"][index], pol_results["y"]["rows"][index]
            j = [[complex_value(x, "weighted_Ex_real", "weighted_Ex_imag"), complex_value(y, "weighted_Ex_real", "weighted_Ex_imag")], [complex_value(x, "weighted_Ey_real", "weighted_Ey_imag"), complex_value(y, "weighted_Ey_real", "weighted_Ey_imag")]]
            m = metrics(j)
            row = {"geometry_uid": candidate["geometry_uid"], "exact_hash": candidate["exact_hash"], **candidate["coordinates_5d"], "H_global": H_GLOBAL_NM, "wavelength_nm": wavelength, **m, "throughput_x": float(x["source_T"]), "throughput_y": float(y["source_T"]), "throughput": (float(x["source_T"]) + float(y["source_T"])) / 2.0, "x_accepted": True, "y_accepted": True, "full_jones_accepted": bool(m["full_jones_finite"]), "source_stage": "H1C1A_BROADBAND_GLOBAL", "case_uid_x": candidate["broadband_case_identity"]["x"]["case_uid"], "case_uid_y": candidate["broadband_case_identity"]["y"]["case_uid"], "attempt_uid_x": pol_results["x"].get("attempt_id"), "attempt_uid_y": pol_results["y"].get("attempt_id"), "solver_entered": True, "solver_replay": False, "model_fill": "NONE"}
            rows.append(row)
        if rows:
            summary = {"geometry_uid": candidate["geometry_uid"], "exact_hash": candidate["exact_hash"], "role": candidate["role"], "source": candidate["source"], "global_or_seed": candidate["global_or_seed"], "phase_trajectory_deg": [row["phi_txx"] for row in rows], **status_from_rows(rows), "x_case_uid": candidate["broadband_case_identity"]["x"]["case_uid"], "y_case_uid": candidate["broadband_case_identity"]["y"]["case_uid"], "solver_entered_x": True, "solver_entered_y": True}
            result_by_uid[candidate["geometry_uid"]] = {"candidate": candidate, "rows": rows, "summary": summary}
        else:
            entries = [x for x in accounting.get("cases", []) if x["geometry_uid"] == candidate["geometry_uid"]]
            summary = {"geometry_uid": candidate["geometry_uid"], "exact_hash": candidate["exact_hash"], "role": candidate["role"], "source": candidate["source"], "global_or_seed": candidate["global_or_seed"], "broadband_status": "INCOMPATIBLE", "projector_pass_count": 0, "failed_wavelengths": GRID, "solver_entered_x": any(x.get("polarization") == "x" and x.get("solver_entered") for x in entries), "solver_entered_y": any(x.get("polarization") == "y" and x.get("solver_entered") for x in entries)}
        summaries.append(summary)
        full_rows.extend(rows)
    return full_rows, summaries, result_by_uid


def phase_islands(summaries: list[dict[str, Any]], result_by_uid: dict[str, dict[str, Any]]) -> dict[str, Any]:
    strict = [summary for summary in summaries if summary.get("broadband_status") == "BROADBAND_PROJECTOR_COMPATIBLE_STRICT"]
    points = [{"geometry_uid": row["geometry_uid"], "phase_450_deg": float(row["phase_trajectory_deg"][0]), "phase_trajectory_deg": row["phase_trajectory_deg"]} for row in strict]
    phases = sorted(points, key=lambda x: x["phase_450_deg"])
    gaps = []
    for left, right in zip(phases, phases[1:]):
        gaps.append({"from_geometry_uid": left["geometry_uid"], "to_geometry_uid": right["geometry_uid"], "gap_deg": right["phase_450_deg"] - left["phase_450_deg"]})
    if phases:
        gaps.append({"from_geometry_uid": phases[-1]["geometry_uid"], "to_geometry_uid": phases[0]["geometry_uid"], "gap_deg": phases[0]["phase_450_deg"] + 360.0 - phases[-1]["phase_450_deg"]})
    threshold = 30.0
    clusters = []
    if phases:
        current = [phases[0]]
        for gap, point in zip(gaps[:-1], phases[1:]):
            if gap["gap_deg"] <= threshold:
                current.append(point)
            else:
                clusters.append(current); current = [point]
        clusters.append(current)
        if len(clusters) > 1 and gaps[-1]["gap_deg"] <= threshold:
            clusters[0] = clusters[-1] + clusters[0]; clusters.pop()
    return {"schema": "H1C1A_PHASE_ISLANDS_V1", "strict_candidate_count": len(strict), "phase_reference": "450.0_nm_display_anchor; all nine wavelength trajectories retained", "points": points, "circular_coverage_deg": circular_coverage([x["phase_450_deg"] for x in points]), "largest_uncovered_circular_gap_deg": max((x["gap_deg"] for x in gaps), default=360.0), "circular_gaps": gaps, "cluster_diagnostic_gap_threshold_deg": threshold, "clusters": [[x["geometry_uid"] for x in cluster] for cluster in clusters], "incomplete_bank": len(strict) < 6}


def six_bin_screening(summaries: list[dict[str, Any]], result_by_uid: dict[str, dict[str, Any]]) -> dict[str, Any]:
    strict_ids = [x["geometry_uid"] for x in summaries if x.get("broadband_status") == "BROADBAND_PROJECTOR_COMPATIBLE_STRICT"]
    if len(strict_ids) < 6:
        return {"schema": "H1C1A_SIX_BIN_SCREENING_V1", "status": "PROPOSED_ONLY_INCOMPLETE_STRICT_BANK", "strict_candidate_count": len(strict_ids), "best_tuple": None, "phase_bin_error_threshold": "NOT_FROZEN"}
    best = None
    for combo in itertools.combinations(strict_ids, 6):
        ordered = sorted(combo, key=lambda uid: result_by_uid[uid]["rows"][0]["phi_txx"])
        for shift in range(6):
            ids = ordered[shift:] + ordered[:shift]
            errors = []
            per_wavelength = []
            phi0 = []
            adjacent = []
            for index in range(len(GRID)):
                phases = [float(result_by_uid[uid]["rows"][index]["phi_txx"]) for uid in ids]
                offsets = [wrap_deg(phase - 60.0 * k) for k, phase in enumerate(phases)]
                center = circular_mean(offsets)
                phi0.append(center)
                residual = [circular_diff(offset, center) for offset in offsets]
                errors.extend(residual); per_wavelength.append(max(abs(x) for x in residual))
                adjacent.append([circular_diff(phases[(k + 1) % 6], phases[k]) for k in range(5)])
            worst = max(abs(x) for x in errors); rms = math.sqrt(sum(x * x for x in errors) / len(errors)); spacing_error = max(abs(x - 60.0) for row in adjacent for x in row)
            score = (worst, rms, spacing_error, tuple(ids))
            if best is None or score < best["score"]:
                best = {"score": score, "ids": ids, "phi0_lambda_deg": phi0, "worst_absolute_error_deg": worst, "rms_error_deg": rms, "per_wavelength_max_error_deg": per_wavelength, "adjacent_spacing_error_deg": adjacent}
    assert best is not None
    best.pop("score", None)
    return {"schema": "H1C1A_SIX_BIN_SCREENING_V1", "status": "OFFLINE_RANKING_ONLY", "strict_candidate_count": len(strict_ids), "phase_bin_error_threshold": "NOT_FROZEN", "best_tuple": best, "throughput_projector_robustness": [{"geometry_uid": uid, "worst_projector_error": next(x["worst_projector_error"] for x in summaries if x["geometry_uid"] == uid), "min_throughput": next(x["min_throughput"] for x in summaries if x["geometry_uid"] == uid)} for uid in best["ids"]]}


def load_historical_rows() -> dict[str, dict[str, Any]]:
    files = [("H1A", ROOT / "outputs/lp_global_h_h1a/complete_jones_table.csv"), ("H1B1", ROOT / "outputs/lp_global_h_h1b1/h1b1_full_jones.csv"), ("H1B2", ROOT / "outputs/lp_global_h_h1b2/h1b2_full_jones.csv"), ("H1B3", ROOT / "outputs/lp_global_h_h1b3/h1b3_full_jones.csv")]
    result = {}
    for stage, path in files:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                wavelength = number(row.get("wavelength_nm"))
                if wavelength is None and stage.startswith("H1B"):
                    wavelength = 450.0
                if number(row.get("H_global_nm")) != H_GLOBAL_NM or wavelength != 450.0:
                    continue
                key = row.get("exact_geometry_hash_sha256") or row.get("geometry_hash_sha256")
                if key and key not in result:
                    result[key] = {"stage": stage, "row": row}
    return result


def load_historical_cases() -> list[dict[str, Any]]:
    audit_path = ROOT / "reports/stage_h1c0_broadband_global/h1c0_h550_existing_salvage_audit.json"
    audit = read_json(audit_path)
    cases = audit.get("cases", [])
    if audit.get("case_count") != 20 or len(cases) != 20:
        raise RuntimeError(f"HARD_GATE_HISTORICAL_CASE_COUNT:{len(cases)}")
    if any(case.get("classification") != "450NM_ONLY_NOT_RECOVERABLE" for case in cases):
        raise RuntimeError("HARD_GATE_HISTORICAL_CLASSIFICATION")
    return cases


def first_number(*values: Any) -> float | None:
    for value in values:
        parsed = number(value)
        if parsed is not None:
            return parsed
    return None


def historical_registry_row(case: dict[str, Any], historical: dict[str, dict[str, Any]], manifest_by_hash: dict[str, dict[str, Any]]) -> dict[str, Any]:
    exact_hash = case.get("exact_hash")
    item = historical.get(exact_hash, {})
    if not item:
        raise RuntimeError(f"HARD_GATE_HISTORICAL_H550_ROW_MISSING:{exact_hash}")
    row = item.get("row", {})
    geometry = {}
    case_uids = {}
    for polarization in case.get("evidence", {}).get("polarizations", []):
        polarization_name = str(polarization.get("polarization", ""))[-1:].lower()
        case_uids[polarization_name] = Path(polarization["case_dir"]).name
        checkpoint_path = Path(polarization["case_dir"]) / "checkpoint.json"
        if not geometry and checkpoint_path.exists():
            geometry = read_json(checkpoint_path).get("geometry", {})
    coordinates = {
        "J1_side_nm": first_number(geometry.get("J1_side_nm"), row.get("J1_side_nm")),
        "J2_length_nm": first_number(geometry.get("J2_length_nm"), row.get("J2_length_nm")),
        "J2_width_nm": first_number(geometry.get("J2_width_nm"), row.get("J2_width_nm")),
        "D_nm": first_number(geometry.get("D_nm"), row.get("D_nm")),
        "Psi_deg": first_number(geometry.get("Psi_deg"), row.get("Psi_deg")),
    }
    if any(value is None for value in coordinates.values()):
        raise RuntimeError(f"HARD_GATE_HISTORICAL_COORDINATES_MISSING:{exact_hash}")
    candidate = manifest_by_hash.get(exact_hash)
    geometry_uid = candidate["geometry_uid"] if candidate and candidate["global_or_seed"] == "SEED" else f"HISTORICAL_{exact_hash[:12]}"
    projector_error = first_number(row.get("projector_error_apcd_v1"), row.get("projection_error_apcd_v1"))
    return {"geometry_uid": geometry_uid, "exact_hash": exact_hash, **coordinates, "H_global": H_GLOBAL_NM, "wavelength_nm": 450.0, "Re_txx": number(row.get("txx_real")), "Im_txx": number(row.get("txx_imag")), "Re_txy": number(row.get("txy_real")), "Im_txy": number(row.get("txy_imag")), "Re_tyx": number(row.get("tyx_real")), "Im_tyx": number(row.get("tyx_imag")), "Re_tyy": number(row.get("tyy_real")), "Im_tyy": number(row.get("tyy_imag")), "phi_txx": number(row.get("phase_wrapped_deg")), "projector_error": projector_error, "Txx": number(row.get("Txx")), "throughput": number(row.get("Txx")), "x_accepted": True, "y_accepted": True, "full_jones_accepted": True, "broadband_status": "450NM_ONLY_NOT_RECOVERABLE", "source_stage": case.get("stage", item.get("stage")), "case_uid_x": row.get("x_case_id") or case_uids.get("x"), "case_uid_y": row.get("y_case_id") or case_uids.get("y"), "attempt_uid_x": None, "attempt_uid_y": None, "solver_entered": True, "solver_replay": False, "ml_eligible": True, "ml_admitted": False, "split": "UNASSIGNED", "spectral_scope": "450NM_ONLY", "history_preserved": True}


def write_labels(manifest: dict[str, Any], full_rows: list[dict[str, Any]], summaries: list[dict[str, Any]]) -> dict[str, Any]:
    historical = load_historical_rows()
    manifest_by_hash = {candidate["exact_hash"]: candidate for candidate in manifest["candidates"]}
    historical_rows = [historical_registry_row(case, historical, manifest_by_hash) for case in load_historical_cases()]
    if len(historical_rows) != 20:
        raise RuntimeError(f"HARD_GATE_HISTORICAL_ROW_COUNT:{len(historical_rows)}")
    if len({row["exact_hash"] for row in historical_rows}) != 20:
        raise RuntimeError("HARD_GATE_HISTORICAL_HASH_UNIQUENESS")
    new_rows = []
    strict_ids = {summary["geometry_uid"] for summary in summaries if summary.get("broadband_status") == "BROADBAND_PROJECTOR_COMPATIBLE_STRICT"}
    summary_by_uid = {summary["geometry_uid"]: summary for summary in summaries}
    for row in full_rows:
        new = dict(row); new.update({"ml_eligible": True, "ml_admitted": False, "split": "UNASSIGNED", "spectral_scope": "BROADBAND_9NM_GRID", "broadband_status": summary_by_uid[row["geometry_uid"]]["broadband_status"], "strict_candidate": row["geometry_uid"] in strict_ids})
        new_rows.append(new)
    rows = historical_rows + new_rows
    fields = {key for row in rows for key in row}
    required = {"geometry_uid", "exact_hash", "wavelength_nm", "Re_txx", "Im_txx", "Re_txy", "Im_txy", "Re_tyx", "Im_tyx", "Re_tyy", "Im_tyy", "phi_txx", "projector_error", "Txx", "throughput", "full_jones_accepted", "broadband_status", "source_stage", "case_uid_x", "case_uid_y", "attempt_uid_x", "attempt_uid_y", "solver_entered", "solver_replay", "ml_eligible", "ml_admitted", "split"}
    if not required.issubset(fields):
        raise RuntimeError(f"HARD_GATE_LABEL_FIELDS_MISSING:{sorted(required - fields)}")
    write_csv(REPORT / "lp_hf_authoritative_label_registry_v1.csv", rows)
    payload = {"schema": "LP_HF_AUTHORITATIVE_LABEL_REGISTRY_V1", "historical_scope": "20 H550 geometries at 450.0 nm only; no fabricated broadband", "new_scope": "H1C1A full-Jones broadband rows only", "row_count": len(rows), "historical_450_only_rows": len(historical_rows), "new_broadband_rows": len(new_rows), "new_broadband_geometry_count": len({row["geometry_uid"] for row in new_rows}), "ml_eligible_all": all(row["ml_eligible"] for row in rows), "ml_admitted_false_all": all(not row["ml_admitted"] for row in rows), "split_unassigned_all": all(row["split"] == "UNASSIGNED" for row in rows), "rows": rows}
    write_json(REPORT / "lp_hf_authoritative_label_registry_v1.json", payload)
    return {key: payload[key] for key in ("row_count", "historical_450_only_rows", "new_broadband_rows", "new_broadband_geometry_count", "ml_eligible_all", "ml_admitted_false_all", "split_unassigned_all")}


def assemble(manifest: dict[str, Any]) -> dict[str, Any]:
    accounting = read_json(ACCOUNTING_PATH)
    if accounting.get("solver_subruns_entered", 0) >= MAX_SUBRUNS:
        accounting["status"] = "COMPLETE" if accounting.get("solver_subruns_accepted", 0) == MAX_SUBRUNS else "PARTIAL_DATA_PRESERVED"
        write_json(ACCOUNTING_PATH, accounting)
    full_rows, summaries, result_by_uid = assemble_rows(manifest, accounting)
    summary_by_uid = {summary["geometry_uid"]: summary for summary in summaries}
    full_rows = [{**row, "broadband_status": summary_by_uid[row["geometry_uid"]]["broadband_status"]} for row in full_rows]
    write_csv(REPORT / "h1c1a_broadband_full_jones.csv", full_rows)
    write_csv(REPORT / "h1c1a_geometry_broadband_summary.csv", summaries)
    islands = phase_islands(summaries, result_by_uid)
    screening = six_bin_screening(summaries, result_by_uid)
    write_json(REPORT / "h1c1a_phase_islands.json", islands)
    write_json(REPORT / "h1c1a_six_bin_screening.json", screening)
    bank = {"schema": "H550_GLOBAL_SIX_BIN_CANDIDATE_BANK", "stage": "H1C-1A", "manifest_freeze_sha256": manifest["freeze_sha256"], "candidate_count": len(manifest["candidates"]), "strict_candidate_count": sum(x.get("broadband_status") == "BROADBAND_PROJECTOR_COMPATIBLE_STRICT" for x in summaries), "candidates": [{**candidate, "broadband_result": next((x for x in summaries if x["geometry_uid"] == candidate["geometry_uid"]), None)} for candidate in manifest["candidates"]], "retention_rule": "retain all strict candidates across all circular phase regions; do not extremum-filter"}
    c_uid = next(x["geometry_uid"] for x in manifest["candidates"] if "H1B2_C_UPPER_EDGE_LOCAL_CONTINUATION" in x["source"] or (x["prior_450nm_provenance"] and x["prior_450nm_provenance"].get("geometry_id") == "H1B2_C_UPPER_EDGE_LOCAL_CONTINUATION"))
    c_summary = next((x for x in summaries if x["geometry_uid"] == c_uid), {"broadband_status": "INCOMPATIBLE"})
    c_status = c_summary.get("broadband_status")
    bank["C_broadband_status"] = c_status
    bank["C_upgrade"] = "BROADBAND_SIX_BIN_CANDIDATE" if c_status == "BROADBAND_PROJECTOR_COMPATIBLE_STRICT" else "GLOBAL_SIX_BIN_CANDIDATE_SEED_RETAINED_PENDING_BROADBAND"
    write_json(REPORT / "h1c1a_global_candidate_bank.json", bank)
    labels = write_labels(manifest, full_rows, summaries)
    accounting = read_json(ACCOUNTING_PATH)
    c_rows = result_by_uid.get(c_uid, {}).get("rows", [])
    final = {"schema": "H1C1A_FINAL_V1", "status": "H1C1A_COMPLETE" if accounting["solver_subruns_accepted"] == MAX_SUBRUNS else "H1C1A_PARTIAL_DATA_PRESERVED", "stage": "H1C-1A", "branch": current_branch(), "head": current_head(), "manifest_freeze_sha256": manifest["freeze_sha256"], "planned_geometries": MAX_GEOMETRIES, "planned_global_geometries": GLOBAL_GEOMETRIES, "planned_seed_geometries": 4, "planned_formal_subruns": MAX_SUBRUNS, "entered_formal_subruns": accounting["solver_subruns_entered"], "accepted_formal_subruns": accounting["solver_subruns_accepted"], "max_global_fdtd_concurrency": 2, "max_active_fdtd_per_branch": 1, "processes_per_job": 4, "threads_per_job": 1, "strict_candidate_count": islands["strict_candidate_count"], "center_only_count": sum(x.get("broadband_status") == "CENTER_ONLY_COMPATIBLE" for x in summaries), "partial_count": sum(x.get("broadband_status") == "PARTIALLY_COMPATIBLE" for x in summaries), "incompatible_count": sum(x.get("broadband_status") == "INCOMPATIBLE" for x in summaries), "C_broadband_status": c_status, "C_phi_lambda_deg": [row["phi_txx"] for row in c_rows], "C_projector_error_lambda": [row["projector_error"] for row in c_rows], "C_Txx_lambda": [row["Txx"] for row in c_rows], "phase_islands": islands, "six_bin_screening": screening, "label_registry": labels, "solver_replay": False, "next_adaptive_batch": {"status": "PROPOSED_ONLY", "automatic_start": False, "basis": "strict candidate occupied regions and largest circular gaps"}, "hard_gates": []}
    if accounting["solver_subruns_entered"] > MAX_SUBRUNS:
        final["hard_gates"].append("HARD_GATE_SOLVER_BUDGET_EXCEEDED")
    write_json(REPORT / "h1c1a_final.json", final)
    lines = ["# Stage H1C-1A — H550 Broadband Global Full-Dimer Phase-Island Discovery", "", f"- Status: `{final['status']}`", f"- Planned/entered/accepted formal subruns: `{MAX_SUBRUNS}/{final['entered_formal_subruns']}/{final['accepted_formal_subruns']}`.", f"- Exact geometries: `{MAX_GEOMETRIES}` (`{GLOBAL_GEOMETRIES}` global + `4` seed controls).", f"- Frozen grid: `{GRID}` nm; one broadband solve per polarization returns all 9 points.", f"- FDTD concurrency: global `2`, LP branch `1`; resources `4 MPI × 1 thread`.", f"- Strict / center-only / partial / incompatible: `{final['strict_candidate_count']}/{final['center_only_count']}/{final['partial_count']}/{final['incompatible_count']}`.", f"- C broadband status: `{c_status}`.", f"- Circular coverage: `{islands['circular_coverage_deg']}` deg; largest gap: `{islands['largest_uncovered_circular_gap_deg']}` deg.", f"- ML labels: `{labels['new_broadband_rows']}` new broadband rows + `{labels['historical_450_only_rows']}` historical 450-only rows; `ml_admitted=false` for all.", "- No throughput threshold was invented; no absolute phase-flatness gate was applied; six-bin phase-bin threshold remains unfrozen.", "- No automatic second batch, ML training, constituent solver, inverse design, or K6 was started.", "", "Artifacts: `h1c1a_candidate_manifest.json`, `h1c1a_solver_accounting.json`, `h1c1a_broadband_full_jones.csv`, `h1c1a_geometry_broadband_summary.csv`, `h1c1a_global_candidate_bank.json`, `h1c1a_phase_islands.json`, `h1c1a_six_bin_screening.json`, `lp_hf_authoritative_label_registry_v1.json/.csv`, `h1c1a_final.json`."]
    (REPORT / "h1c1a_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return final


def setup_check(manifest: dict[str, Any]) -> dict[str, Any]:
    runtime = load_runtime()
    candidate = manifest["candidates"][0]
    setup_dir = RUNTIME / "setup_check"
    setup_dir.mkdir(parents=True, exist_ok=True)
    fsp = setup_dir / "H1C1A_setup_check_pre.fsp"
    f = runtime.lumapi.FDTD(hide=runtime.hide_gui)
    try:
        setup = build(f, candidate, "x")
        f.save(str(fsp)); pre_hash = sha256_file(fsp); f.close(); f = runtime.lumapi.FDTD(hide=runtime.hide_gui); f.load(str(fsp)); gate = setup_gate(f, candidate, "x")
        result = {"schema": "H1C1A_SETUP_CHECK_V1", "solver_entered": False, "solver_run_called": False, "setup": setup, "reload_gate": gate, "pre_fsp_path": str(fsp), "pre_fsp_sha256": pre_hash, "wavelength_grid_nm": GRID, "solver_runs_for_spectrum": 1}
    finally:
        try: f.close()
        except Exception: pass
    write_json(REPORT / "h1c1a_setup_check.json", result)
    if not result["reload_gate"]["pass"]:
        raise RuntimeError("HARD_GATE_BROADBAND_SETUP_CHECK")
    return result


def execute(manifest: dict[str, Any]) -> dict[str, Any]:
    setup = read_json(REPORT / "h1c1a_setup_check.json")
    if setup.get("solver_entered") or setup.get("solver_run_called") or not setup.get("reload_gate", {}).get("pass"):
        raise RuntimeError("HARD_GATE_SETUP_CHECK_NOT_PASS")
    runtime = load_runtime()
    slot = load_module(ROOT / "scripts/apcd_global_fdtd_slot_v1.py", "h1c1a_slot")
    scheduler = slot.GlobalSlotScheduler(SLOT_REGISTRY)
    for candidate in manifest["candidates"]:
        for pol in POLARIZATIONS:
            result = run_case(runtime, candidate, pol, manifest, scheduler)
            print(json.dumps({"case_id": candidate["broadband_case_identity"][pol]["case_uid"], "status": result.get("status"), "solver_entered": result.get("solver_entered", False)}, ensure_ascii=False), flush=True)
    return assemble(manifest)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "setup-check", "execute", "postprocess"))
    args = parser.parse_args()
    if args.mode == "preflight":
        manifest = ensure_manifest(); initial_accounting(manifest); print(json.dumps({"status": manifest["status"], "freeze_sha256": manifest["freeze_sha256"], "candidate_count": len(manifest["candidates"]), "global_count": sum(x["global_or_seed"] == "GLOBAL" for x in manifest["candidates"]), "seed_count": sum(x["global_or_seed"] == "SEED" for x in manifest["candidates"]), "solver_entered": False}, indent=2)); return 0
    manifest = ensure_manifest(); initial_accounting(manifest)
    if args.mode == "setup-check":
        print(json.dumps(setup_check(manifest), indent=2, default=str)); return 0
    if args.mode == "postprocess":
        print(json.dumps(assemble(manifest), indent=2, default=str)); return 0
    print(json.dumps(execute(manifest), indent=2, default=str)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
