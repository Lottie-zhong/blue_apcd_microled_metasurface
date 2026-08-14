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
import traceback
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/lp_global_h_h1b2"
REPORT = ROOT / "reports/stage_h1b2_global_h"
RUNTIME = OUT / "runtime"
H_GLOBAL_NM = 550.0
POLARIZATIONS = ("x", "y")
MAX_GEOMETRIES = 5
MAX_SUBRUNS = 10
PERIOD_NM = 432.0
MATERIAL = "APCD_TIO2_NATIVE_M1"
MANUFACTURING_GAP_NM = 60.0
PROJECTOR_ERROR_MAX = 0.1864961370084426
BASELINE_COMPATIBLE_SPAN_DEG = 40.34742274657583
TARGET_BRANCH = "work/lp-global-h-manifold-v1"
ACCEPTED_H1B0_HEAD = "c7daf9350f72f44d69ac940b57278622c692eaf6"
H1B1_HEAD = "89c8112ade112caeb84c1373a432b3b97b37db75"
H1B1_FINAL = ROOT / "reports/stage_h1b1_global_h/h1b1_final.json"
H1B1_MANIFEST = ROOT / "outputs/lp_global_h_h1b1/h1b1_candidate_manifest.json"
H1B1_EFFECTS = ROOT / "outputs/lp_global_h_h1b1/h1b1_candidate_effects.csv"
H1B1_MERGED = ROOT / "outputs/lp_global_h_h1b1/h1b1_h550_merged_manifold.csv"
H1B1_FULL = ROOT / "outputs/lp_global_h_h1b1/h1b1_full_jones.csv"
H1A_FULL = ROOT / "outputs/lp_global_h_h1a/complete_jones_table.csv"
H0_ANCHORS = ROOT / "reports/stage_h0_global_h/anchor_manifest.json"
H1B0_PROPOSAL = ROOT / "reports/stage_h1b0_global_h/h1b0_proposed_next_probe.json"
H1B0_HYPOTHESES = ROOT / "reports/stage_h1b0_global_h/h1b0_lateral_hypotheses.json"
BOUNDS = ROOT / "outputs/lp_ml_dataset_v1/plans/lp_ml_dataset_v1_5d_design_space_contract_v1.json"
SLOT_REGISTRY = Path(r"D:\project\apcd_global_fdtd_slot_registry_v1.json")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


SUP = load_module(ROOT / "scripts/lp_global_h_h1b1_probe_v1.py", "lp_h1b2_h1b1_support")
SUP.H_GLOBAL_NM = H_GLOBAL_NM
SUP.MATERIAL = MATERIAL
SUP.PERIOD_NM = PERIOD_NM
SUP.TARGET_BRANCH = TARGET_BRANCH
SUP.SLOT_REGISTRY = SLOT_REGISTRY
RUNNER = SUP.RUNNER
SLOT = SUP.SLOT


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_obj(value: object) -> str:
    return sha256_bytes(canonical_bytes(value))


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_csv(path: Path, rows: list[dict]) -> None:
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


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def current_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def current_branch() -> str:
    return subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()


def number(value: object) -> float | None:
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def physical_key(row: dict) -> tuple:
    return (
        int(round(float(row["J1_side_nm"]))),
        int(round(float(row["J2_length_nm"]))),
        int(round(float(row["J2_width_nm"]))),
        round(float(row["J2_center_x_nm"]), 9),
        round(float(row["J2_center_y_nm"]), 9),
        H_GLOBAL_NM,
        PERIOD_NM,
        MATERIAL,
    )


def center_key(row: dict) -> tuple[float, float]:
    return round(float(row["J2_center_x_nm"]), 9), round(float(row["J2_center_y_nm"]), 9)


def candidate_row(
    candidate_id: str,
    role: str,
    rationale: str,
    parent_id: str,
    parent: dict,
    j: int,
    l: int,
    w: int,
    cx: float,
    cy: float,
    target_edge: str,
    displacement_basis: str,
    supporting_evidence: list[str],
    secondary_contrast: dict | None = None,
) -> dict:
    d = 2.0 * math.hypot(cx, cy)
    psi = math.degrees(math.atan2(cy, cx))
    row = {
        "candidate_id": candidate_id,
        "role": role,
        "rationale": rationale,
        "parent_reference_id": parent_id,
        "parent_reference_geometry": parent,
        "expected_edge_target": target_edge,
        "displacement_basis": displacement_basis,
        "supporting_authoritative_evidence": supporting_evidence,
        "secondary_contrast": secondary_contrast or {},
        "H_global_nm": H_GLOBAL_NM,
        "J1_H_nm": H_GLOBAL_NM,
        "J2_H_nm": H_GLOBAL_NM,
        "J1_side_nm": int(j),
        "J2_length_nm": int(l),
        "J2_width_nm": int(w),
        "J1_center_x_nm": -float(cx),
        "J1_center_y_nm": -float(cy),
        "J2_center_x_nm": float(cx),
        "J2_center_y_nm": float(cy),
        "D_nm": d,
        "Psi_deg": psi,
        "J1_rotation_deg": 0.0,
        "J2_rotation_deg": psi,
        "material_contract": MATERIAL,
        "period_nm": [PERIOD_NM, PERIOD_NM],
    }
    identity = SUP.geometry_identity(row)
    row["geometry_identity"] = identity
    row["exact_geometry_hash_sha256"] = sha256_obj(identity)
    row["canonical_relative_geometry_hash_sha256"] = sha256_obj({
        "J1_side_nm": int(j),
        "J2_length_nm": int(l),
        "J2_width_nm": int(w),
        "cx_abs_nm": abs(float(cx)),
        "cy_abs_nm": abs(float(cy)),
        "H_nm": H_GLOBAL_NM,
        "period_nm": PERIOD_NM,
    })
    row["symmetry_equivalence_geometry_hash_sha256"] = sha256_obj({
        "J1_side_nm": int(j),
        "J2_length_nm": int(l),
        "J2_width_nm": int(w),
        "radius_nm": round(math.hypot(cx, cy), 9),
        "H_nm": H_GLOBAL_NM,
        "period_nm": PERIOD_NM,
    })
    return row


def h1b1_candidates() -> dict[str, dict]:
    return {row["candidate_id"]: row for row in read_json(H1B1_MANIFEST)["candidates"]}


def evidence_rows() -> dict[str, dict]:
    old = {row.get("authoritative_id"): dict(row) for row in SUP.old_h550_rows()}
    for row in read_json(H0_ANCHORS).get("anchors", []):
        old.setdefault(row.get("authoritative_id"), {}).update(row)
    for row in read_csv(H1B1_EFFECTS):
        row = dict(row)
        row["phi_deg"] = number(row.get("phi_deg"))
        row["projector_error_apcd_v1"] = number(row.get("projector_error_apcd_v1"))
        row["selected_throughput_Txx"] = number(row.get("selected_throughput_Txx"))
        old[row["candidate_id"]] = row
    for row in h1b1_candidates().values():
        old.setdefault(row["candidate_id"], {}).update(row)
    return old


def parent_geometry(parent_id: str, evidence: dict[str, dict]) -> dict:
    row = dict(evidence[parent_id])
    if "J2_center_x_nm" not in row:
        d = float(row["D_nm"])
        psi = math.radians(float(row["Psi_deg"]))
        row["J2_center_x_nm"] = d * math.cos(psi) / 2.0
        row["J2_center_y_nm"] = d * math.sin(psi) / 2.0
        row["J1_center_x_nm"] = -row["J2_center_x_nm"]
        row["J1_center_y_nm"] = -row["J2_center_y_nm"]
    result = {key: row.get(key) for key in ("authoritative_id", "candidate_id", "exact_geometry_hash_sha256", "J1_side_nm", "J2_length_nm", "J2_width_nm", "J2_center_x_nm", "J2_center_y_nm", "D_nm", "Psi_deg", "H_global_nm", "projector_error_apcd_v1", "selected_throughput_Txx", "Txx", "projector_compatible")}
    result["phase_wrapped_deg"] = row.get("phase_wrapped_deg") or row.get("phi_deg")
    return result


def materialize_candidates() -> list[dict]:
    evidence = evidence_rows()
    a = h1b1_candidates()["H1B1_A_LOWER_COMPATIBLE_EDGE"]
    e = h1b1_candidates()["H1B1_E_INTERIOR_PROJECTOR_CONTROL"]
    high_parent = parent_geometry("LPML_R2_HIGH_UNCERTAINTY_007", evidence)
    a_parent = parent_geometry("H1B1_A_LOWER_COMPATIBLE_EDGE", evidence)
    e_parent = parent_geometry("H1B1_E_INTERIOR_PROJECTOR_CONTROL", evidence)
    return [
        candidate_row(
            "H1B2_A_A_EDGE_CONTINUATION",
            "A_successful_lower_edge_one_step_continuation",
            "Repeat the observed 038-to-H1B1-A lower-edge displacement once beyond the accepted H1B1-A point.",
            "H1B1_A_LOWER_COMPATIBLE_EDGE",
            a_parent,
            104, 103, 96, 94.5, 1.0,
            "lower",
            "H1A_038_to_H1B1_A_displacement_repeated_once",
            ["H1A H550 LPML_R1_GLOBAL_SOBOL_038", "H1B1 candidate effects A"],
        ),
        candidate_row(
            "H1B2_B_A_EDGE_CONSERVATIVE_CONTINUATION",
            "B_conservative_same_direction_continuation",
            "Use a smaller legal continuation in the same observed lower-edge direction to test whether A is a trend rather than an isolated point.",
            "H1B1_A_LOWER_COMPATIBLE_EDGE",
            a_parent,
            106, 104, 97, 96.5, 1.0,
            "lower",
            "H1A_038_to_H1B1_A_direction_half_scale_integer_grid",
            ["H1A H550 LPML_R1_GLOBAL_SOBOL_038", "H1B1 candidate effects A"],
        ),
        candidate_row(
            "H1B2_C_UPPER_EDGE_LOCAL_CONTINUATION",
            "C_other_upper_edge_local_continuation",
            "Continue the real H1A high007 compatible upper-edge reference along the accepted H1B1-D center-shift direction, with half-grid projection recorded explicitly.",
            "LPML_R2_HIGH_UNCERTAINTY_007",
            high_parent,
            112, 112, 102, 94.0, -3.5,
            "upper",
            "H1B1_126_to_D_center_shift_rebased_to_H1A_high007",
            ["H1A H550 LPML_R2_HIGH_UNCERTAINTY_007", "H1B1 candidate effects D", "H1B1 H550 merged manifold"],
        ),
        candidate_row(
            "H1B2_D_A_DIRECTION_J1_CONTRAST",
            "D_success_direction_secondary_J1_contrast",
            "Repeat the successful A continuation while changing only the secondary J1-side contrast by one nanometre.",
            "H1B1_A_LOWER_COMPATIBLE_EDGE",
            a_parent,
            105, 103, 96, 94.5, 1.0,
            "lower",
            "H1A_038_to_H1B1_A_direction_plus_J1_side_contrast",
            ["H1B1 candidate effects A", "H1B1 candidate effects C J1-side contrast"],
            {"J1_side_nm": 1},
        ),
        candidate_row(
            "H1B2_E_INTERIOR_PROJECTOR_CONTROL",
            "E_interior_projector_preserving_control",
            "Make a one-step interior center control adjacent to the accepted H1B1-E compatible region without chasing an edge.",
            "H1B1_E_INTERIOR_PROJECTOR_CONTROL",
            e_parent,
            111, 109, 101, 100.5, 1.0,
            "interior_control",
            "H1B1_E_local_center_step",
            ["H1B1 candidate effects D/E", "H1B1 H550 merged manifold"],
        ),
    ]


def existing_geometry_evidence() -> tuple[set[str], set[tuple]]:
    hashes: set[str] = set()
    keys: set[tuple] = set()
    for row in read_csv(H1A_FULL):
        h = row.get("exact_geometry_hash_sha256") or row.get("geometry_hash_sha256")
        if h:
            hashes.add(h)
    for row in h1b1_candidates().values():
        hashes.add(row["exact_geometry_hash_sha256"])
        keys.add(physical_key(row))
    for row in read_json(H0_ANCHORS).get("anchors", []):
        if row.get("J1_side_nm") is None:
            continue
        d = float(row["D_nm"])
        psi = math.radians(float(row["Psi_deg"]))
        copy = dict(row)
        copy["H_global_nm"] = H_GLOBAL_NM
        copy["J2_center_x_nm"] = d * math.cos(psi) / 2.0
        copy["J2_center_y_nm"] = d * math.sin(psi) / 2.0
        keys.add(physical_key(copy))
    return hashes, keys


def legality(candidate: dict, seen_hashes: set[str], seen_keys: set[tuple], existing_hashes: set[str], existing_keys: set[tuple]) -> dict:
    j = int(candidate["J1_side_nm"])
    l = int(candidate["J2_length_nm"])
    w = int(candidate["J2_width_nm"])
    cx = float(candidate["J2_center_x_nm"])
    cy = float(candidate["J2_center_y_nm"])
    d = float(candidate["D_nm"])
    psi = float(candidate["Psi_deg"])
    direct = d - max(j, w)
    periodic_x = PERIOD_NM - 2.0 * abs(cx) - max(j, w)
    periodic_y = PERIOD_NM - 2.0 * abs(cy) - max(w, l)
    bounds = read_json(BOUNDS)["ranges"]
    within_old_box = (
        bounds["J1_side_nm"][0] <= j <= bounds["J1_side_nm"][1]
        and bounds["J2_length_nm"][0] <= l <= bounds["J2_length_nm"][1]
        and bounds["J2_width_nm"][0] <= w <= bounds["J2_width_nm"][1]
        and bounds["D_nm"][0] <= d <= bounds["D_nm"][1]
        and bounds["Psi_deg"][0] <= psi <= bounds["Psi_deg"][1]
    )
    key = physical_key(candidate)
    checks = {
        "H_global_550": candidate["H_global_nm"] == H_GLOBAL_NM and candidate["J1_H_nm"] == H_GLOBAL_NM and candidate["J2_H_nm"] == H_GLOBAL_NM,
        "period_432": candidate["period_nm"] == [PERIOD_NM, PERIOD_NM],
        "native_material": candidate["material_contract"] == MATERIAL,
        "integer_lateral_dimensions": all(float(candidate[k]).is_integer() for k in ("J1_side_nm", "J2_length_nm", "J2_width_nm")),
        "half_grid_center": all(abs(2.0 * z - round(2.0 * z)) < 1e-9 for z in (cx, cy)),
        "direct_gap_ge_60": direct >= MANUFACTURING_GAP_NM,
        "periodic_gap_ge_60": min(periodic_x, periodic_y) >= MANUFACTURING_GAP_NM,
        "cell_containment": abs(cx) + max(j, l) / 2.0 < PERIOD_NM / 2.0 and abs(cy) + max(w, l) / 2.0 < PERIOD_NM / 2.0,
        "no_overlap": direct > 0.0,
        "exact_hash_unique_in_probe": candidate["exact_geometry_hash_sha256"] not in seen_hashes,
        "physical_geometry_unique_in_probe": key not in seen_keys,
        "no_previous_exact_physics_evidence": candidate["exact_geometry_hash_sha256"] not in existing_hashes and key not in existing_keys,
    }
    return {"pass": all(checks.values()), "checks": checks, "direct_gap_nm": direct, "periodic_gap_x_nm": periodic_x, "periodic_gap_y_nm": periodic_y, "outside_old_H500_search_box": not within_old_box, "within_old_H500_search_box": within_old_box, "physical_key": list(key)}


def compact_snapshot(snapshot: dict) -> dict:
    return {
        "timestamp_utc": snapshot.get("timestamp_utc"),
        "global_active_jobs": snapshot.get("global_active_jobs"),
        "lp_active_jobs": snapshot.get("lp_active_jobs"),
        "formal_process_count": snapshot.get("formal_process_count"),
        "jobs": [{"branch": row.get("branch"), "process_count": len(row.get("processes", []))} for row in snapshot.get("jobs", [])],
    }


def build_selection_audit() -> tuple[list[dict], dict]:
    candidates = materialize_candidates()
    existing_hashes, existing_keys = existing_geometry_evidence()
    seen_hashes, seen_keys = set(existing_hashes), set(existing_keys)
    audit_rows = []
    for candidate in candidates:
        check = legality(candidate, seen_hashes, seen_keys, existing_hashes, existing_keys)
        candidate["legality"] = check
        parent = candidate["parent_reference_geometry"]
        displacement = {
            key: round(float(candidate[key]) - float(parent[key]), 9)
            for key in ("J1_side_nm", "J2_length_nm", "J2_width_nm", "J2_center_x_nm", "J2_center_y_nm")
            if number(parent.get(key)) is not None
        }
        candidate["displacement_5d"] = displacement
        audit_rows.append({
            "candidate_id": candidate["candidate_id"],
            "role": candidate["role"],
            "expected_edge_target": candidate["expected_edge_target"],
            "parent_reference_id": candidate["parent_reference_id"],
            "parent_reference_geometry": parent,
            "displacement_5d": displacement,
            "supporting_authoritative_evidence": candidate["supporting_authoritative_evidence"],
            "exact_geometry_hash_sha256": candidate["exact_geometry_hash_sha256"],
            "canonical_relative_geometry_hash_sha256": candidate["canonical_relative_geometry_hash_sha256"],
            "outside_old_H500_search_box": check["outside_old_H500_search_box"],
            "legality": check,
            "previous_exact_physics_evidence": False,
            "status": "FROZEN_FOR_EXECUTION",
        })
        if not check["pass"]:
            raise RuntimeError(f"HARD_STOP_H1B2_CANDIDATE_LEGALITY:{candidate['candidate_id']}:{check}")
        seen_hashes.add(candidate["exact_geometry_hash_sha256"])
        seen_keys.add(physical_key(candidate))
    if len(candidates) != MAX_GEOMETRIES or len({c["exact_geometry_hash_sha256"] for c in candidates}) != MAX_GEOMETRIES:
        raise RuntimeError("HARD_GATE_H1B2_EXACTLY_FIVE_UNIQUE_GEOMETRIES")
    audit = {
        "schema": "LP_GLOBAL_H_H1B2_CANDIDATE_SELECTION_AUDIT_V1",
        "stage": "H1B-2",
        "status": "FROZEN_FOR_EXECUTION",
        "materialization_rule": "OBSERVED_SUCCESS -> ONE_STEP_LOCAL_CONTINUATION -> PROJECTOR_PRESERVING_CONTROL",
        "solver_budget": {"new_geometries": MAX_GEOMETRIES, "formal_x_y_subruns": MAX_SUBRUNS, "H_global_nm": H_GLOBAL_NM, "H500_scheduled": False},
        "candidate_count": len(candidates),
        "rows": audit_rows,
    }
    return candidates, audit


def build_manifest() -> tuple[dict, dict]:
    if current_branch() != TARGET_BRANCH:
        raise RuntimeError(f"HARD_GATE_WRONG_BRANCH:{current_branch()}")
    head = current_head()
    ancestry = subprocess.run(["git", "merge-base", "--is-ancestor", ACCEPTED_H1B0_HEAD, head], cwd=ROOT, capture_output=True)
    if ancestry.returncode != 0:
        raise RuntimeError(f"HARD_GATE_UNEXPECTED_PROVENANCE:{head}")
    final = read_json(H1B1_FINAL)
    if final.get("status") != "COMPLETE_ANALYSIS" or final.get("verdict") != "H1B1_TARGETED_EXPANSION_IMPROVED_BUT_BELOW_60":
        raise RuntimeError("HARD_GATE_H1B1_AUTHORITATIVE_FINAL")
    baseline_span = number(final.get("span_comparison", {}).get("new_merged_H550_projector_compatible_span_deg"))
    if baseline_span is None or abs(baseline_span - BASELINE_COMPATIBLE_SPAN_DEG) > 1e-9:
        raise RuntimeError("HARD_GATE_H1B1_BASELINE_SPAN")
    h1b1_accounting = final.get("solver_accounting", {})
    if h1b1_accounting.get("solver_subruns_entered") != 10 or h1b1_accounting.get("solver_subruns_accepted") != 10 or h1b1_accounting.get("H500_scheduled") is not False:
        raise RuntimeError("HARD_GATE_H1B1_ACCOUNTING")
    candidates, audit = build_selection_audit()
    OUT.mkdir(parents=True, exist_ok=True)
    audit_path = OUT / "h1b2_candidate_selection_audit.json"
    atomic_json(audit_path, audit)
    live = compact_snapshot(SLOT.live_job_snapshot())
    if live["global_active_jobs"] > SLOT.GLOBAL_CAPACITY or live["lp_active_jobs"] > SLOT.MAX_ACTIVE_FDTD_PER_BRANCH:
        raise RuntimeError(f"HARD_GATE_SCHEDULER_CAPACITY:{live}")
    contract = SUP.H1A.physical_contract(head)
    scheduler_path = ROOT / "scripts/apcd_global_fdtd_slot_v1.py"
    scheduler_log = subprocess.check_output(["git", "log", "-1", "--format=%H %s", "--", "scripts/apcd_global_fdtd_slot_v1.py"], cwd=ROOT, text=True).strip()
    payload = {
        "schema": "LP_GLOBAL_H_H1B2_CANDIDATE_MANIFEST_V1",
        "stage": "H1B-2",
        "status": "FROZEN_READY",
        "worktree": str(ROOT),
        "branch": current_branch(),
        "head": head,
        "accepted_h1b0_head": ACCEPTED_H1B0_HEAD,
        "accepted_h1b1_head": H1B1_HEAD,
        "candidate_selection_audit_sha256": sha256_file(audit_path),
        "h1b1_final_sha256": sha256_file(H1B1_FINAL),
        "h1b1_manifest_sha256": sha256_file(H1B1_MANIFEST),
        "h1b1_effects_sha256": sha256_file(H1B1_EFFECTS),
        "h1b1_merged_sha256": sha256_file(H1B1_MERGED),
        "h1b1_full_jones_sha256": sha256_file(H1B1_FULL),
        "h1b0_proposal_sha256": sha256_file(H1B0_PROPOSAL),
        "h1b0_hypotheses_sha256": sha256_file(H1B0_HYPOTHESES),
        "bounds_contract_sha256": sha256_file(BOUNDS),
        "scheduler_path": str(scheduler_path),
        "scheduler_sha256": sha256_file(scheduler_path),
        "scheduler_provenance_commit": scheduler_log,
        "solver_authorization": {"approved_new_geometries": MAX_GEOMETRIES, "approved_new_subruns": MAX_SUBRUNS, "H_global_nm_only": H_GLOBAL_NM, "polarizations": list(POLARIZATIONS), "H500_scheduled": False},
        "physical_contract": contract,
        "physical_contract_sha256": sha256_obj(contract),
        "baseline_H1B1": {"compatible_span_deg": BASELINE_COMPATIBLE_SPAN_DEG, "expected_remaining_sector_gap_deg": 60.0 - BASELINE_COMPATIBLE_SPAN_DEG, "single_point_dominated_lower_extension": True},
        "pre_execution_live_snapshot": live,
        "global_capacity": SLOT.GLOBAL_CAPACITY,
        "max_active_fdtd_per_branch": SLOT.MAX_ACTIVE_FDTD_PER_BRANCH,
        "processes_per_job": SLOT.PROCESSES_PER_JOB,
        "threads_per_job": SLOT.THREADS_PER_JOB,
        "candidates": candidates,
    }
    payload["freeze_sha256"] = sha256_obj(payload)
    return payload, audit


def case_identity(candidate: dict, pol: str, head: str) -> dict:
    return {"stage": "H1B-2", "candidate_id": candidate["candidate_id"], "exact_geometry_hash_sha256": candidate["exact_geometry_hash_sha256"], "geometry_identity": candidate["geometry_identity"], "H_global_nm": H_GLOBAL_NM, "polarization": pol, "material_contract": MATERIAL, "period_nm": [PERIOD_NM, PERIOD_NM], "builder_version": SUP.H1A.BUILDER_VERSION, "builder_commit": head, "formal_extraction_convention": SUP.H1A.EXTRACTION_CONVENTION, "diffraction_order": "G0"}


def case_name(candidate: dict, pol: str) -> str:
    return f"H1B2_{candidate['candidate_id']}_H550_P{pol}"


def accounting_path() -> Path:
    return OUT / "h1b2_solver_accounting.json"


def load_accounting() -> dict:
    return read_json(accounting_path()) if accounting_path().exists() else {"solver_entries": [], "cases": []}


def write_accounting(payload: dict) -> None:
    atomic_json(accounting_path(), payload)


def initialize_accounting(manifest: dict) -> dict:
    old = load_accounting()
    if old.get("manifest_freeze_sha256") not in (None, manifest["freeze_sha256"]) and old.get("solver_entries"):
        raise RuntimeError("HARD_GATE_ACCOUNTING_MANIFEST_MISMATCH_AFTER_ENTRY")
    planned = [{"case_id": case_name(c, p), "candidate_id": c["candidate_id"], "geometry_hash_sha256": c["exact_geometry_hash_sha256"], "H_global_nm": H_GLOBAL_NM, "polarization": p, "planned": True, "attempted": False, "solver_entered": False, "accepted": False, "phase_only": False, "quarantined": False, "recovered": False, "unentered_infrastructure_failure": False} for c in manifest["candidates"] for p in POLARIZATIONS]
    cases = old.get("cases") or planned
    if len(cases) != MAX_SUBRUNS:
        if old.get("solver_entries"):
            raise RuntimeError("HARD_GATE_H1B2_ACCOUNTING_CASE_COUNT_AFTER_ENTRY")
        cases = planned
    if len(cases) != MAX_SUBRUNS:
        raise RuntimeError("HARD_GATE_H1B2_ACCOUNTING_CASE_COUNT")
    payload = {"schema": "LP_GLOBAL_H_H1B2_SOLVER_ACCOUNTING_V1", "stage": "H1B-2", "manifest_freeze_sha256": manifest["freeze_sha256"], "solver_budget_planned": MAX_SUBRUNS, "H_global_nm_only": H_GLOBAL_NM, "H500_scheduled": False, "cases": cases, "solver_entries": old.get("solver_entries", []), "status": old.get("status", "PLANNED")}
    write_accounting(payload)
    return payload


def update_case(case_id: str, updates: dict, entry: dict | None = None) -> dict:
    payload = load_accounting()
    for row in payload.get("cases", []):
        if row.get("case_id") == case_id:
            row.update(updates)
            break
    else:
        raise RuntimeError(f"unknown case in accounting: {case_id}")
    if entry is not None and not any(x.get("case_id") == case_id for x in payload.get("solver_entries", [])):
        payload.setdefault("solver_entries", []).append(entry)
    write_accounting(payload)
    return payload


def next_attempt(case_dir: Path, case_id: str) -> tuple[str, Path, Path]:
    old = sorted(case_dir.glob("attempt_provenance*.json"))
    nums = []
    for path in old:
        match = re.search(r"_attempt_(\d{3})\.json$", path.name)
        nums.append(int(match.group(1)) if match else 1)
    n = max(nums, default=0) + 1
    attempt_id = f"{case_id}_attempt_{n:03d}"
    provenance = case_dir / ("attempt_provenance.json" if n == 1 else f"attempt_provenance_attempt_{n:03d}.json")
    return attempt_id, provenance, case_dir / f"{attempt_id}_pre.fsp"


def checkpoint_result(case_dir: Path, identity: dict) -> dict | None:
    path = case_dir / "checkpoint.json"
    if not path.exists():
        return None
    try:
        data = read_json(path)
    except Exception:
        return None
    if data.get("status") != "ACCEPTED" or data.get("case_identity_sha256") != sha256_obj(identity):
        return None
    return {"status": "ACCEPTED", "solver_entered": True, "recovered_from_checkpoint": True, "case_id": data.get("case_id"), "candidate_id": data.get("candidate_id"), "polarization": data.get("polarization"), "rows": data.get("rows", []), "grid_audit": data.get("grid_audit"), "checkpoint_path": str(path), "checkpoint_sha256": sha256_file(path), "geometry_hash_sha256": identity["exact_geometry_hash_sha256"], "case_identity_sha256": sha256_obj(identity)}


def run_case(runtime, candidate: dict, pol: str, manifest: dict, scheduler, entered: list[dict]) -> dict:
    identity = case_identity(candidate, pol, manifest["head"])
    identity_hash = sha256_obj(identity)
    cid = case_name(candidate, pol)
    case_dir = RUNTIME / "cases" / cid
    case_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = checkpoint_result(case_dir, identity)
    if checkpoint:
        update_case(cid, {"attempted": True, "solver_entered": True, "accepted": True, "recovered": True, "status": "ACCEPTED"})
        return checkpoint
    if any(row.get("case_id") == cid and row.get("solver_entered") is True for row in entered):
        result = {"status": "QUARANTINED_ENTERED_NO_RECOVERY", "solver_entered": True, "case_id": cid, "candidate_id": candidate["candidate_id"], "geometry_hash_sha256": candidate["exact_geometry_hash_sha256"], "error": "entered=true exact H1B2 case has no accepted checkpoint; replay forbidden"}
        update_case(cid, {"attempted": True, "solver_entered": True, "quarantined": True, "status": result["status"]})
        return result
    attempt_id, provenance_path, pre_fsp = next_attempt(case_dir, cid)
    record = {"schema": "LP_GLOBAL_H_H1B2_ATTEMPT_PROVENANCE_V1", "case_id": cid, "attempt_id": attempt_id, "candidate_id": candidate["candidate_id"], "case_identity": identity, "case_identity_sha256": identity_hash, "branch": current_branch(), "worktree": str(ROOT), "H_global_nm": H_GLOBAL_NM, "polarization": pol, "solver_entered": False, "entered_solver": False, "slot_acquired": False, "processes": SLOT.PROCESSES_PER_JOB, "threads": SLOT.THREADS_PER_JOB, "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "physical_contract_sha256": manifest["physical_contract_sha256"]}
    atomic_json(provenance_path, record)
    f = None
    lease = None
    solver_completed = False
    try:
        f = runtime.lumapi.FDTD(hide=getattr(runtime, "hide_gui", True))
        setup = RUNNER.build(f, candidate, pol, height_nm=H_GLOBAL_NM)
        f.save(str(pre_fsp))
        record.update({"setup": setup, "pre_fsp_path": str(pre_fsp), "pre_fsp_sha256": sha256_file(pre_fsp), "status": "PREPARED", "attempted": True})
        f.close()
        f = None
        atomic_json(provenance_path, record)
        update_case(cid, {"attempted": True, "status": "WAITING_SLOT"})
        lease = scheduler.acquire_wait(branch=TARGET_BRANCH, worktree=str(ROOT), task_id="H1B2_CONTINUATION", case_uid=cid, pid=os.getpid(), metadata={"task_class": "H1B2_FORMAL_FDTD", "attempt_id": attempt_id, "polarization": pol, "H_global_nm": H_GLOBAL_NM}, timeout_s=21600.0, poll_s=15.0)
        record.update({"slot_acquired": True, "slot_id": lease.slot_id, "slot_acquire_time": lease.record.get("slot_acquire_time"), "concurrent_peer_branch": lease.record.get("concurrent_peer_branch", []), "admission_snapshot": compact_snapshot(lease.record.get("admission_snapshot", {})), "status": "SLOT_ACQUIRED"})
        lease.start_heartbeat()
        atomic_json(provenance_path, record)
        f = runtime.lumapi.FDTD(hide=getattr(runtime, "hide_gui", True))
        f.load(str(pre_fsp))
        resource = SUP.H1A.resource_gate(f)
        gate = SUP.H1A.setup_gate(f, candidate, pol, H_GLOBAL_NM)
        record.update({"resource_gate": resource, "configuration_gate": gate, "status": "PREFLIGHT_GATED"})
        atomic_json(provenance_path, record)
        if not resource.get("pass") or not gate.get("pass"):
            record.update({"status": "QUARANTINED_PREFLIGHT_GATE", "quarantined": True, "error": "resource or configuration gate failed"})
            update_case(cid, {"status": record["status"], "quarantined": True})
            return record
        if len(entered) >= MAX_SUBRUNS:
            raise RuntimeError("HARD_GATE_H1B2_ENTERED_BUDGET")
        entered_utc = dt.datetime.now(dt.timezone.utc).isoformat()
        lease.mark_solver_entered(entered_utc)
        entry = {"case_id": cid, "attempt_id": attempt_id, "candidate_id": candidate["candidate_id"], "geometry_hash_sha256": candidate["exact_geometry_hash_sha256"], "case_identity_sha256": identity_hash, "H_global_nm": H_GLOBAL_NM, "polarization": pol, "solver_entered": True, "entered_solver": True, "entered_utc": entered_utc, "slot_id": lease.slot_id, "pre_fsp_sha256": record["pre_fsp_sha256"], "physical_contract_sha256": manifest["physical_contract_sha256"], "pid": os.getpid()}
        entered.append(entry)
        record.update({"solver_entered": True, "entered_solver": True, "entered_utc": entered_utc, "solver_start": entered_utc, "status": "ENTERED"})
        update_case(cid, {"solver_entered": True, "status": "ENTERED"}, entry)
        atomic_json(provenance_path, record)
        f.run()
        solver_completed = True
        completed = dt.datetime.now(dt.timezone.utc).isoformat()
        lease.release("SOLVER_COMPLETED", completed)
        lease = None
        record.update({"solver_complete": completed, "slot_release_time": dt.datetime.now(dt.timezone.utc).isoformat(), "status": "SOLVER_COMPLETED"})
        rows, grid = RUNNER.extract_broadband(f)
        checkpoint = {"schema": "LP_GLOBAL_H_H1B2_CHECKPOINT_V1", "status": "ACCEPTED", "case_id": cid, "candidate_id": candidate["candidate_id"], "polarization": pol, "case_identity": identity, "case_identity_sha256": identity_hash, "geometry": candidate, "H_global_nm": H_GLOBAL_NM, "physical_contract_sha256": manifest["physical_contract_sha256"], "setup": setup, "resource_gate": resource, "configuration_gate": gate, "rows": rows, "grid_audit": grid}
        atomic_json(case_dir / "checkpoint.json", checkpoint)
        record.update({"status": "ACCEPTED", "rows": rows, "grid_audit": grid, "checkpoint_path": str(case_dir / "checkpoint.json"), "checkpoint_sha256": sha256_file(case_dir / "checkpoint.json")})
        update_case(cid, {"status": "ACCEPTED", "accepted": True})
        return record
    except Exception as exc:
        if lease is not None:
            try:
                lease.release("FAILED_ENTERED" if record.get("solver_entered") else "FAILED_PRE_ENTRY")
                record["slot_release_time"] = dt.datetime.now(dt.timezone.utc).isoformat()
            except Exception as release_exc:
                record["slot_release_error"] = f"{type(release_exc).__name__}: {release_exc}"
            lease = None
        record.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc(), "failure_scope": "GLOBAL_INFRASTRUCTURE" if not record.get("solver_entered") else "CASE_OR_PHYSICS"})
        update_case(cid, {"status": "FAILED", "quarantined": bool(record.get("solver_entered")), "unentered_infrastructure_failure": not bool(record.get("solver_entered"))})
        return record
    finally:
        if lease is not None:
            try:
                lease.release("SOLVER_COMPLETED" if solver_completed else ("FAILED_ENTERED" if record.get("solver_entered") else "FAILED_PRE_ENTRY"))
            except Exception:
                pass
        if f is not None:
            try:
                f.close()
            except Exception:
                pass
        record["finished_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
        atomic_json(provenance_path, record)


def complex_value(row: dict, real: str, imag: str) -> complex:
    return complex(float(row[real]), float(row[imag]))


def full_jones_row(candidate: dict, x: dict, y: dict) -> dict:
    xr, yr = x["rows"][0], y["rows"][0]
    matrix = np.array([[complex_value(xr, "weighted_Ex_real", "weighted_Ex_imag"), complex_value(yr, "weighted_Ex_real", "weighted_Ex_imag")], [complex_value(xr, "weighted_Ey_real", "weighted_Ey_imag"), complex_value(yr, "weighted_Ey_real", "weighted_Ey_imag")]])
    return {"source_class": "H1B2_NEW_SOLVER_XY_FORMAL", "physics_scope": "FULL_JONES_H1B2_PHYSICS", "diffraction_order": "G0", "Jones_complete": True, "candidate_id": candidate["candidate_id"], "authoritative_id": candidate["candidate_id"], "anchor_role": candidate["role"], "geometry_hash_sha256": candidate["exact_geometry_hash_sha256"], "H_global_nm": H_GLOBAL_NM, "J1_side_nm": candidate["J1_side_nm"], "J2_length_nm": candidate["J2_length_nm"], "J2_width_nm": candidate["J2_width_nm"], "D_nm": candidate["D_nm"], "Psi_deg": candidate["Psi_deg"], "x_case_id": x.get("case_id"), "y_case_id": y.get("case_id"), "x_checkpoint_sha256": x.get("checkpoint_sha256"), "y_checkpoint_sha256": y.get("checkpoint_sha256"), **RUNNER.metrics(matrix)}


def phase_only_row(candidate: dict, x: dict) -> dict:
    txx = complex_value(x["rows"][0], "weighted_Ex_real", "weighted_Ex_imag")
    return {"source_class": "H1B2_X_FORMAL_ONLY", "physics_scope": "PHASE_ONLY_H1B2_PHYSICS", "diffraction_order": "G0", "Jones_complete": False, "projector_eligible": False, "candidate_id": candidate["candidate_id"], "authoritative_id": candidate["candidate_id"], "anchor_role": candidate["role"], "geometry_hash_sha256": candidate["exact_geometry_hash_sha256"], "H_global_nm": H_GLOBAL_NM, "phase_wrapped_deg": float(np.degrees(np.angle(txx)) % 360.0), "Txx": abs(txx) ** 2, "selected_throughput_Txx": abs(txx) ** 2, "txx_real": txx.real, "txx_imag": txx.imag, "x_case_id": x.get("case_id"), "x_checkpoint_sha256": x.get("checkpoint_sha256")}


def canonical_phase(value: float) -> float:
    return float(value) % 360.0


def ccw_distance(start: float, end: float) -> float:
    return (canonical_phase(end) - canonical_phase(start)) % 360.0


def circular_arc(values: list[float]) -> dict:
    if not values:
        return {"coverage_deg": 0.0, "arc_start_deg": None, "arc_end_deg": None, "largest_gap_deg": 360.0, "raw_min_deg": None, "raw_max_deg": None}
    vals = sorted(canonical_phase(v) for v in values)
    if len(vals) == 1:
        return {"coverage_deg": 0.0, "arc_start_deg": vals[0], "arc_end_deg": vals[0], "largest_gap_deg": 360.0, "raw_min_deg": vals[0], "raw_max_deg": vals[0]}
    gaps = [vals[i + 1] - vals[i] for i in range(len(vals) - 1)] + [vals[0] + 360.0 - vals[-1]]
    index = max(range(len(gaps)), key=lambda i: gaps[i])
    start = vals[(index + 1) % len(vals)]
    end = vals[index]
    return {"coverage_deg": 360.0 - gaps[index], "arc_start_deg": start, "arc_end_deg": end, "largest_gap_deg": gaps[index], "raw_min_deg": min(vals), "raw_max_deg": max(vals)}


def max_pairs(rows: list[dict]) -> tuple[float, list[str] | None]:
    best = (0.0, None)
    for a, b in itertools.combinations(rows, 2):
        separation = abs(SUP.H1A.circ_diff(canonical_phase(float(a["phase_wrapped_deg"])), canonical_phase(float(b["phase_wrapped_deg"]))))
        if separation > best[0]:
            best = (separation, [str(a.get("candidate_id") or a.get("authoritative_id")), str(b.get("candidate_id") or b.get("authoritative_id"))])
    return best


def old_h550_rows() -> list[dict]:
    rows = SUP.old_h550_rows()
    for row in rows:
        row["diffraction_order"] = "G0"
        row["physics_origin"] = "H1A_AUTHORITATIVE_FULL_JONES"
    return rows


def h1b1_h550_rows() -> list[dict]:
    rows = read_csv(H1B1_FULL)
    if len(rows) != 5:
        raise RuntimeError(f"HARD_GATE_H1B1_FULL_JONES_MERGE_COUNT:{len(rows)}")
    for row in rows:
        row["source_class"] = "H1B1_AUTHORITATIVE_FULL_JONES"
        row["physics_origin"] = "H1B1_AUTHORITATIVE_FULL_JONES"
        row["diffraction_order"] = "G0"
        row["phase_wrapped_deg"] = canonical_phase(float(row["phase_wrapped_deg"]))
        row["projector_error_apcd_v1"] = number(row.get("projection_error_apcd_v1") or row.get("projector_error_apcd_v1"))
        row["selected_throughput_Txx"] = number(row.get("Txx"))
        row["projector_compatible"] = row["projector_error_apcd_v1"] is not None and row["projector_error_apcd_v1"] <= PROJECTOR_ERROR_MAX + 1e-12
    return rows


def signed_phase_delta(value: float, parent: float) -> float:
    return ((canonical_phase(value) - canonical_phase(parent) + 180.0) % 360.0) - 180.0


def analyze(manifest: dict, results: dict[str, dict]) -> dict:
    full_new: list[dict] = []
    phase_new: list[dict] = []
    for candidate in manifest["candidates"]:
        x = results.get(case_name(candidate, "x"))
        y = results.get(case_name(candidate, "y"))
        if x and x.get("status") == "ACCEPTED":
            phase_new.append(phase_only_row(candidate, x))
        if x and y and x.get("status") == "ACCEPTED" and y.get("status") == "ACCEPTED":
            full_new.append(full_jones_row(candidate, x, y))
    old_h1a = old_h550_rows()
    old_h1b1 = h1b1_h550_rows()
    old = old_h1a + old_h1b1
    merged = old + full_new
    for row in merged:
        err = number(row.get("projection_error_apcd_v1") or row.get("projector_error_apcd_v1"))
        row["projector_error_apcd_v1"] = err
        row["projector_compatible"] = err is not None and err <= PROJECTOR_ERROR_MAX + 1e-12
        row["phase_wrapped_deg"] = canonical_phase(float(row["phase_wrapped_deg"]))
    compatible = [row for row in merged if row["projector_compatible"]]
    old_compatible = [row for row in old if row["projector_compatible"]]
    old_arc = circular_arc([row["phase_wrapped_deg"] for row in old_compatible])
    old_h1a_arc = circular_arc([row["phase_wrapped_deg"] for row in old_h1a if row["projector_compatible"]])
    new_arc = circular_arc([row["phase_wrapped_deg"] for row in compatible])
    lower_extension = ccw_distance(new_arc["arc_start_deg"], old_arc["arc_start_deg"]) if new_arc["arc_start_deg"] is not None and old_arc["arc_start_deg"] is not None else 0.0
    upper_extension = ccw_distance(old_arc["arc_end_deg"], new_arc["arc_end_deg"]) if new_arc["arc_end_deg"] is not None and old_arc["arc_end_deg"] is not None else 0.0
    new_rows = {row["candidate_id"]: row for row in full_new}
    lower_ids = [row["candidate_id"] for row in compatible if row["candidate_id"] in new_rows and abs(ccw_distance(row["phase_wrapped_deg"], new_arc["arc_start_deg"])) < 1e-8]
    upper_ids = [row["candidate_id"] for row in compatible if row["candidate_id"] in new_rows and abs(ccw_distance(new_arc["arc_end_deg"], row["phase_wrapped_deg"])) < 1e-8]
    pair, pair_ids = max_pairs(compatible)
    effects = []
    for row in full_new:
        candidate = next(c for c in manifest["candidates"] if c["candidate_id"] == row["candidate_id"])
        parent = parent_geometry(candidate["parent_reference_id"], evidence_rows())
        parent_phi = number(parent.get("phase_wrapped_deg"))
        parent_error = number(parent.get("projector_error_apcd_v1"))
        parent_txx = number(parent.get("selected_throughput_Txx") or parent.get("Txx"))
        effects.append({
            "candidate_id": row["candidate_id"],
            "role": candidate["role"],
            "expected_edge_target": candidate["expected_edge_target"],
            "geometry_hash_sha256": row["geometry_hash_sha256"],
            "parent_reference_id": candidate["parent_reference_id"],
            "parent_phase_deg": parent_phi,
            "phi_deg": row["phase_wrapped_deg"],
            "phase_gain_relative_parent_deg": signed_phase_delta(row["phase_wrapped_deg"], parent_phi) if parent_phi is not None else None,
            "projector_error_apcd_v1": row["projector_error_apcd_v1"],
            "projector_margin_to_compatibility_threshold": PROJECTOR_ERROR_MAX - row["projector_error_apcd_v1"] if row["projector_error_apcd_v1"] is not None else None,
            "parent_projector_error_apcd_v1": parent_error,
            "projector_change_relative_parent": row["projector_error_apcd_v1"] - parent_error if parent_error is not None and row["projector_error_apcd_v1"] is not None else None,
            "selected_throughput_Txx": row.get("Txx"),
            "parent_selected_throughput_Txx": parent_txx,
            "throughput_change_relative_parent": number(row.get("Txx")) - parent_txx if number(row.get("Txx")) is not None and parent_txx is not None else None,
            "projector_compatible": row["projector_compatible"],
            "new_compatible_lower_extremum": row["candidate_id"] in lower_ids,
            "new_compatible_upper_extremum": row["candidate_id"] in upper_ids,
            "actual_lower_edge_extension_deg": lower_extension if row["candidate_id"] in lower_ids else 0.0,
            "actual_upper_edge_extension_deg": upper_extension if row["candidate_id"] in upper_ids else 0.0,
            "new_compatible_extremum": row["candidate_id"] in lower_ids or row["candidate_id"] in upper_ids,
            "exact_5d": {key: candidate[key] for key in ("J1_side_nm", "J2_length_nm", "J2_width_nm", "D_nm", "Psi_deg")},
            "displacement_5d": candidate["displacement_5d"],
            "legality": candidate["legality"],
        })
    gain = new_arc["coverage_deg"] - BASELINE_COMPATIBLE_SPAN_DEG
    flag60 = pair >= 60.0
    flag120 = new_arc["coverage_deg"] >= 120.0
    edge_ids = sorted(set(lower_ids + upper_ids))
    single_point_dominated = len(edge_ids) == 1 and gain > 0.0
    if len(full_new) < MAX_GEOMETRIES:
        verdict = "H1B2_INCONCLUSIVE"
        route = "INSUFFICIENT_ACCEPTED_FULL_JONES_EVIDENCE"
    elif flag60:
        verdict = "H1B2_REACHED_60_SECTOR"
        route = "SYSTEMATIC_H550_MANIFOLD_MAPPING"
    elif gain > 1e-9 and edge_ids:
        verdict = "H1B2_CONTINUED_IMPROVEMENT_BELOW_60"
        route = "RETURN_TO_CHART_FOR_FINAL_EDGE_REFINEMENT_DECISION"
    else:
        verdict = "H1B2_LOCAL_EXPANSION_SATURATED"
        route = "TARGETED_CONSTITUENT_RECONNAISSANCE"
    span = {
        "baseline_H1B1_compatible_span_deg": BASELINE_COMPATIBLE_SPAN_DEG,
        "old_H1A_H550_compatible_arc": old_h1a_arc,
        "baseline_H1B1_compatible_arc": old_arc,
        "new_merged_H550_compatible_arc": new_arc,
        "new_merged_H550_raw_arc": circular_arc([row["phase_wrapped_deg"] for row in merged]),
        "new_merged_H550_projector_compatible_count": len(compatible),
        "new_merged_H550_projector_compatible_span_deg": new_arc["coverage_deg"],
        "incremental_gain_deg": gain,
        "lower_edge_extension_deg": lower_extension,
        "upper_edge_extension_deg": upper_extension,
        "max_compatible_pair_separation_deg": pair,
        "max_compatible_pair_ids": pair_ids,
        "new_sector_gap_deg": 60.0 - pair,
        "old_H1A_H550_count": len(old_h1a),
        "old_H1B1_H550_count": len(old_h1b1),
        "new_H1B2_full_jones_count": len(full_new),
        "merged_H550_count": len(merged),
        "new_lower_extremum_ids": lower_ids,
        "new_upper_extremum_ids": upper_ids,
        "H1B2_GAIN_SINGLE_POINT_DOMINATED": single_point_dominated,
        "FLAG_60_SECTOR": flag60,
        "FLAG_120_ML_RESTART": flag120,
    }
    return {"full_new": full_new, "phase_new": phase_new, "merged": merged, "effects": effects, "edge_decomposition": {"old": old_arc, "new": new_arc, "lower_edge_extension_deg": lower_extension, "upper_edge_extension_deg": upper_extension, "new_lower_extremum_ids": lower_ids, "new_upper_extremum_ids": upper_ids}, "span": span, "verdict": verdict, "route": route}


def make_runtime():
    config = RUNNER.load_runtime_config(str(ROOT / "configs/runtime.yaml"))
    lumapi = RUNNER.import_lumapi(config)
    return type("RuntimeProxy", (), {"lumapi": lumapi, "hide_gui": getattr(config, "hide_gui", True)})()


def write_analysis(manifest: dict, accounting: dict, analysis: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "candidate_selection_audit": OUT / "h1b2_candidate_selection_audit.json",
        "candidate_manifest": OUT / "h1b2_candidate_manifest.json",
        "solver_accounting": OUT / "h1b2_solver_accounting.json",
        "full_jones": OUT / "h1b2_full_jones.csv",
        "merged_manifold": OUT / "h1b2_merged_h550_manifold.csv",
        "edge_decomposition": OUT / "h1b2_edge_decomposition.json",
        "candidate_effects": OUT / "h1b2_candidate_effects.csv",
        "span_comparison": OUT / "h1b2_span_comparison.json",
        "final": OUT / "h1b2_final.json",
        "summary": OUT / "h1b2_summary.md",
    }
    write_csv(artifacts["full_jones"], analysis["full_new"])
    write_csv(OUT / "h1b2_phase_only.csv", analysis["phase_new"])
    write_csv(artifacts["merged_manifold"], analysis["merged"])
    write_csv(artifacts["candidate_effects"], analysis["effects"])
    atomic_json(artifacts["edge_decomposition"], analysis["edge_decomposition"])
    atomic_json(artifacts["span_comparison"], analysis["span"])
    h500_rows = [row for row in read_csv(H1A_FULL) if number(row.get("H_global_nm")) == 500.0]
    accounting["status"] = "COMPLETE_ANALYSIS"
    accounting["solver_subruns_entered"] = len(accounting.get("solver_entries", []))
    accounting["solver_subruns_accepted"] = sum(1 for row in accounting.get("cases", []) if row.get("accepted"))
    accounting["solver_subruns_quarantined"] = sum(1 for row in accounting.get("cases", []) if row.get("quarantined"))
    accounting["phase_only_cases"] = sum(1 for row in accounting.get("cases", []) if row.get("phase_only"))
    accounting["recovered_cases"] = sum(1 for row in accounting.get("cases", []) if row.get("recovered"))
    accounting["unentered_infrastructure_failures"] = sum(1 for row in accounting.get("cases", []) if row.get("unentered_infrastructure_failure"))
    accounting["H500_replay_check"] = {"scheduled": False, "authoritative_rows": len(h500_rows)}
    write_accounting(accounting)
    final = {"schema": "LP_GLOBAL_H_H1B2_FINAL_V1", "stage": "H1B-2", "status": "COMPLETE_ANALYSIS", "branch": current_branch(), "head": current_head(), "manifest_freeze_sha256": manifest["freeze_sha256"], "solver_accounting": accounting, "verdict": analysis["verdict"], "recommended_next_route": analysis["route"], "edge_decomposition": analysis["edge_decomposition"], "span_comparison": analysis["span"], "candidate_effects": analysis["effects"], "flags": {"FLAG_60_SECTOR": analysis["span"]["FLAG_60_SECTOR"], "FLAG_120_ML_RESTART": analysis["span"]["FLAG_120_ML_RESTART"], "H1B2_GAIN_SINGLE_POINT_DOMINATED": analysis["span"]["H1B2_GAIN_SINGLE_POINT_DOMINATED"]}, "H500_replay_check": {"scheduled": False, "authoritative_rows": len(h500_rows)}, "artifacts": {key: str(path) for key, path in artifacts.items()}}
    atomic_json(artifacts["final"], final)
    lines = ["# Stage H1B-2 Second-Generation H550 Compatible-Edge Continuation", "", f"- Status: `{final['status']}`", f"- Verdict: `{analysis['verdict']}`", f"- Route recommendation: `{analysis['route']}`", f"- Branch / HEAD: `{final['branch']}` / `{final['head']}`", f"- Planned / entered / accepted: `{MAX_SUBRUNS}` / `{accounting.get('solver_subruns_entered', 0)}` / `{accounting.get('solver_subruns_accepted', 0)}`", "", "## Frozen contract", "", "- H_global = J1_H = J2_H = 550 nm; x+y formal runs; period 432 nm; APCD_TIO2_NATIVE_M1.", "- Full Jones is the transmission-side coordinate-weighted complex G0 with endpoint deduplication, periodic reclosure and existing normalization.", "- H500 was not scheduled or replayed.", "", "## Circular edge decomposition", "", f"- Old H1B-1 compatible arc: `{analysis['edge_decomposition']['old']['arc_start_deg']:.12f} -> {analysis['edge_decomposition']['old']['arc_end_deg']:.12f}` deg; span `{analysis['edge_decomposition']['old']['coverage_deg']:.12f}` deg.", f"- New compatible arc: `{analysis['edge_decomposition']['new']['arc_start_deg']:.12f} -> {analysis['edge_decomposition']['new']['arc_end_deg']:.12f}` deg; span `{analysis['edge_decomposition']['new']['coverage_deg']:.12f}` deg.", f"- Lower / upper extension: `{analysis['edge_decomposition']['lower_edge_extension_deg']:.12f}` / `{analysis['edge_decomposition']['upper_edge_extension_deg']:.12f}` deg.", f"- Single-point dominated: `{analysis['span']['H1B2_GAIN_SINGLE_POINT_DOMINATED']}`.", "", "## Candidate effects", ""]
    lines += [f"- {row['candidate_id']}: phi={row.get('phi_deg')}, projector_error={row.get('projector_error_apcd_v1')}, margin={row.get('projector_margin_to_compatibility_threshold')}, Txx={row.get('selected_throughput_Txx')}, compatible={row.get('projector_compatible')}, lower_extremum={row.get('new_compatible_lower_extremum')}, upper_extremum={row.get('new_compatible_upper_extremum')}" for row in analysis["effects"]]
    lines += ["", "## Artifacts", ""] + [f"- {key}: `{path}`" for key, path in final["artifacts"].items()]
    summary = "\n".join(lines) + "\n"
    artifacts["summary"].write_text(summary, encoding="utf-8")
    for key, path in artifacts.items():
        if key == "summary":
            continue
        target = REPORT / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
    (REPORT / "h1b2_summary.md").write_text(summary, encoding="utf-8")


def preflight() -> int:
    manifest, audit = build_manifest()
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    old_path = OUT / "h1b2_candidate_manifest.json"
    if old_path.exists() and load_accounting().get("solver_entries"):
        old = read_json(old_path)
        if old.get("freeze_sha256") != manifest["freeze_sha256"]:
            raise RuntimeError("HARD_GATE_EXISTING_H1B2_MANIFEST_MISMATCH_AFTER_ENTRY")
    atomic_json(old_path, manifest)
    initialize_accounting(manifest)
    atomic_json(REPORT / "h1b2_candidate_selection_audit.json", audit)
    atomic_json(REPORT / "h1b2_candidate_manifest.json", manifest)
    atomic_json(REPORT / "h1b2_solver_accounting.json", load_accounting())
    print(json.dumps({"status": "FROZEN_READY", "freeze_sha256": manifest["freeze_sha256"], "candidates": [{"candidate_id": c["candidate_id"], "parent": c["parent_reference_id"], "role": c["role"], "D_nm": c["D_nm"], "Psi_deg": c["Psi_deg"], "legality": c["legality"]} for c in manifest["candidates"]], "live_snapshot": manifest["pre_execution_live_snapshot"]}, indent=2, ensure_ascii=False, default=str))
    return 0


def execute(manifest: dict) -> int:
    accounting = initialize_accounting(manifest)
    runtime = make_runtime()
    scheduler = SLOT.GlobalSlotScheduler(SLOT_REGISTRY)
    entered = list(accounting.get("solver_entries", []))
    results: dict[str, dict] = {}
    for candidate in manifest["candidates"]:
        for pol in POLARIZATIONS:
            results[case_name(candidate, pol)] = run_case(runtime, candidate, pol, manifest, scheduler, entered)
    analysis = analyze(manifest, results)
    write_analysis(manifest, load_accounting(), analysis)
    print(json.dumps({"status": "COMPLETE_ANALYSIS", "verdict": analysis["verdict"], "entered": len(entered), "accepted_full_jones": len(analysis["full_new"]), "span": analysis["span"]}, indent=2, ensure_ascii=False, default=str))
    return 0


def postprocess(manifest: dict) -> int:
    accounting = load_accounting()
    if len(accounting.get("solver_entries", [])) != MAX_SUBRUNS:
        raise RuntimeError("HARD_GATE_H1B2_POSTPROCESS_ENTRY_COUNT")
    results: dict[str, dict] = {}
    for candidate in manifest["candidates"]:
        for pol in POLARIZATIONS:
            identity = case_identity(candidate, pol, manifest["head"])
            recovered = checkpoint_result(RUNTIME / "cases" / case_name(candidate, pol), identity)
            if not recovered:
                raise RuntimeError(f"HARD_GATE_H1B2_POSTPROCESS_CHECKPOINT_MISSING:{candidate['candidate_id']}:{pol}")
            results[case_name(candidate, pol)] = recovered
    analysis = analyze(manifest, results)
    write_analysis(manifest, accounting, analysis)
    print(json.dumps({"status": "COMPLETE_ANALYSIS_POSTPROCESS_ONLY", "solver_replay": False, "verdict": analysis["verdict"], "entered": len(accounting.get("solver_entries", [])), "accepted_full_jones": len(analysis["full_new"]), "span": analysis["span"]}, indent=2, ensure_ascii=False, default=str))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--postprocess-only", action="store_true")
    args = parser.parse_args()
    if sum(bool(value) for value in (args.preflight_only, args.execute, args.postprocess_only)) != 1:
        raise SystemExit("select exactly one mode")
    if args.preflight_only:
        return preflight()
    manifest_path = OUT / "h1b2_candidate_manifest.json"
    if not manifest_path.exists():
        raise SystemExit("HARD_GATE_H1B2_PRE_EXECUTION_MANIFEST_MISSING")
    manifest = read_json(manifest_path)
    if manifest.get("status") != "FROZEN_READY" or manifest.get("freeze_sha256") != sha256_obj({key: value for key, value in manifest.items() if key != "freeze_sha256"}):
        raise SystemExit("HARD_GATE_H1B2_FROZEN_MANIFEST_INVALID")
    current = current_head()
    ancestry = subprocess.run(["git", "merge-base", "--is-ancestor", str(manifest.get("head")), current], cwd=ROOT, capture_output=True)
    if current_branch() != TARGET_BRANCH or ancestry.returncode != 0:
        raise SystemExit("HARD_GATE_H1B2_HEAD_OR_BRANCH_DRIFT")
    if args.postprocess_only:
        return postprocess(manifest)
    return execute(manifest)


if __name__ == "__main__":
    raise SystemExit(main())
