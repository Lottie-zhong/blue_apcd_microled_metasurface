from __future__ import annotations

import argparse
import csv
import datetime as dt
import importlib.util
import json
import math
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/lp_global_h_h1b3"
REPORT = ROOT / "reports/stage_h1b3_global_h"
RUNTIME = OUT / "runtime"
H_GLOBAL_NM = 550.0
POLARIZATIONS = ("x", "y")
MAX_GEOMETRIES = 4
MAX_SUBRUNS = 8
PERIOD_NM = 432.0
MATERIAL = "APCD_TIO2_NATIVE_M1"
PROJECTOR_ERROR_MAX = 0.1864961370084426
BASELINE_H1B2_SPAN = 48.20045808425289
TARGET_BRANCH = "work/lp-global-h-manifold-v1"
H1B2_ACCEPTED_HEAD = "01b2007146a43afd6eb7f1a1227c18052edf2306"
H1B2_FINAL = ROOT / "reports/stage_h1b2_global_h/h1b2_final.json"
H1B2_FULL = ROOT / "reports/stage_h1b2_global_h/h1b2_full_jones.csv"
H1B1_MANIFEST = ROOT / "outputs/lp_global_h_h1b1/h1b1_candidate_manifest.json"
H1B1_FULL = ROOT / "outputs/lp_global_h_h1b1/h1b1_full_jones.csv"
H1B1_EFFECTS = ROOT / "outputs/lp_global_h_h1b1/h1b1_candidate_effects.csv"
H1A_FULL = ROOT / "outputs/lp_global_h_h1a/complete_jones_table.csv"
H0_ANCHORS = ROOT / "reports/stage_h0_global_h/anchor_manifest.json"
SLOT_REGISTRY = Path(r"D:\project\apcd_global_fdtd_slot_registry_v1.json")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


H2 = load_module(ROOT / "scripts/lp_global_h_h1b2_probe_v1.py", "lp_h1b3_h1b2_support")
H2.OUT = OUT
H2.REPORT = REPORT
H2.RUNTIME = RUNTIME
H2.H_GLOBAL_NM = H_GLOBAL_NM
H2.POLARIZATIONS = POLARIZATIONS
H2.MAX_GEOMETRIES = MAX_GEOMETRIES
H2.MAX_SUBRUNS = MAX_SUBRUNS
H2.PERIOD_NM = PERIOD_NM
H2.MATERIAL = MATERIAL
H2.TARGET_BRANCH = TARGET_BRANCH
H2.SLOT_REGISTRY = SLOT_REGISTRY
RUNNER = H2.RUNNER
SLOT = H2.SLOT


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


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


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def sha256_obj(value: object) -> str:
    import hashlib
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(value: object) -> float | None:
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def current_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def current_branch() -> str:
    return subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()


def parent_geometry() -> dict:
    return {
        "authoritative_id": "LPML_R2_HIGH_UNCERTAINTY_007",
        "candidate_id": "LPML_R2_HIGH_UNCERTAINTY_007",
        "exact_geometry_hash_sha256": "f447ce0e428d39f1d9055da8692b608a9f0b342aab7aee33131b269a1e037adb",
        "J1_side_nm": 112.0, "J2_length_nm": 112.0, "J2_width_nm": 102.0,
        "J2_center_x_nm": 96.0, "J2_center_y_nm": -3.5,
        "D_nm": 192.12756179163884, "Psi_deg": -2.0879838327233444,
        "H_global_nm": 550.0, "projector_error_apcd_v1": 0.1843707157586535,
        "selected_throughput_Txx": 0.9795182609705267,
        "Txx": 0.9795182609705267, "phase_wrapped_deg": 106.96528957076407,
        "projector_compatible": True,
    }


def c_geometry() -> dict:
    return {
        "candidate_id": "H1B2_C_UPPER_EDGE_LOCAL_CONTINUATION",
        "J1_side_nm": 112.0, "J2_length_nm": 112.0, "J2_width_nm": 102.0,
        "J2_center_x_nm": 94.0, "J2_center_y_nm": -3.5,
        "D_nm": 188.13027401245128, "Psi_deg": -2.132368436554014,
        "exact_geometry_hash_sha256": "5f2f0f47d5f02ee7ced8156302ec2f3191ad2f9cd805ee9be80d49d25820de9b",
        "phase_wrapped_deg": 114.81832490844113,
        "projector_error_apcd_v1": 0.17425118141458695,
        "selected_throughput_Txx": 0.9480295104147646,
    }


def d5(a: dict, b: dict) -> dict:
    return {key: round(float(a[key]) - float(b[key]), 12) for key in ("J1_side_nm", "J2_length_nm", "J2_width_nm", "D_nm", "Psi_deg")}


def physical_key(row: dict) -> tuple:
    return (int(round(float(row["J1_side_nm"]))), int(round(float(row["J2_length_nm"]))), int(round(float(row["J2_width_nm"]))), round(float(row["J2_center_x_nm"]), 9), round(float(row["J2_center_y_nm"]), 9), H_GLOBAL_NM, PERIOD_NM, MATERIAL)


def candidate(candidate_id: str, role: str, rationale: str, j: int, x: float, supporting: list[str], displacement_basis: str, parent: dict, target: str = "upper", secondary: dict | None = None) -> dict:
    y = -3.5
    row = H2.candidate_row(candidate_id, role, rationale, "LPML_R2_HIGH_UNCERTAINTY_007", parent, j, 112, 102, x, y, target, displacement_basis, supporting, secondary)
    return row


def materialize_candidates() -> list[dict]:
    parent = parent_geometry()
    return [
        candidate("H1B3_F1_CONSERVATIVE_FORWARD", "F1_CONSERVATIVE_FORWARD_CONTINUATION", "C plus 0.5*d_success on the verified upper-edge displacement, projected to the nearest legal half-grid center.", 112, 93.0, ["H1B2 C exact parent-to-C d_success", "H1B2 C compatible upper extremum"], "requested 0.5*d_success; legal center projection", parent),
        candidate("H1B3_F2_FULL_FORWARD", "F2_FULL_FORWARD_CONTINUATION", "C plus 1.0*d_success on the verified upper-edge displacement, projected to the nearest legal half-grid center.", 112, 92.0, ["H1B2 C exact parent-to-C d_success", "H1B2 C compatible upper extremum"], "requested 1.0*d_success; legal center projection", parent),
        candidate("H1B3_F3_FORWARD_PLUS_PROJECTOR_COMPENSATION", "F3_FORWARD_PLUS_PROJECTOR_COMPENSATION", "Forward half-step with the second conservative local neighbor J1-side perturbation because no supported projector-compensation direction passed the frozen empirical audit.", 111, 93.0, ["H1B2 C exact parent-to-C d_success", "projector_compensation_selection_audit: NO_SUPPORTED_PROJECTOR_COMPENSATION_DIRECTION", "H1B1/H1B2 authoritative full-Jones local evidence"], "requested 0.5*d_success plus second conservative J1-side neighbor", parent, secondary={"J1_side_nm": -1, "fallback": "SECOND_CONSERVATIVE_LOCAL_NEIGHBOR"}),
        candidate("H1B3_F4_PROJECTOR_ROBUST_LOCAL_NEIGHBOR", "F4_PROJECTOR_ROBUST_LOCAL_NEIGHBOR", "Tiny half-grid neighbor toward the C parent, used as a projector-robustness control without changing H550 or the dimer topology.", 112, 94.5, ["H1B2 C exact local lattice point", "H1B1/H1B2 authoritative full-Jones local evidence"], "tiny legal half-grid neighbor centered at C", parent),
    ]


def old_geometry_evidence() -> tuple[set[str], set[tuple]]:
    hashes: set[str] = set()
    keys: set[tuple] = set()
    for path in (H1A_FULL, H1B1_FULL, H1B2_FULL):
        for row in read_csv(path):
            h = row.get("exact_geometry_hash_sha256") or row.get("geometry_hash_sha256")
            if h:
                hashes.add(h)
    for row in read_json(H1B1_MANIFEST).get("candidates", []):
        hashes.add(row["exact_geometry_hash_sha256"])
        keys.add(physical_key(row))
    keys.add((112, 112, 102, 96.0, -3.5, H_GLOBAL_NM, PERIOD_NM, MATERIAL))
    return hashes, keys


def legality(row: dict, seen_hashes: set[str], seen_keys: set[tuple], existing_hashes: set[str], existing_keys: set[tuple]) -> dict:
    j, l, w = (int(row[k]) for k in ("J1_side_nm", "J2_length_nm", "J2_width_nm"))
    x, y, d, psi = (float(row[k]) for k in ("J2_center_x_nm", "J2_center_y_nm", "D_nm", "Psi_deg"))
    direct = d - max(j, w)
    periodic_x = PERIOD_NM - 2 * abs(x) - max(j, w)
    periodic_y = PERIOD_NM - 2 * abs(y) - max(w, l)
    checks = {
        "H_global_550": row["H_global_nm"] == H_GLOBAL_NM and row["J1_H_nm"] == H_GLOBAL_NM and row["J2_H_nm"] == H_GLOBAL_NM,
        "period_432": row["period_nm"] == [PERIOD_NM, PERIOD_NM], "native_material": row["material_contract"] == MATERIAL,
        "integer_lateral_dimensions": all(float(row[k]).is_integer() for k in ("J1_side_nm", "J2_length_nm", "J2_width_nm")),
        "half_grid_center": all(abs(2 * z - round(2 * z)) < 1e-9 for z in (x, y)),
        "direct_gap_ge_60": direct >= 60.0, "periodic_gap_ge_60": min(periodic_x, periodic_y) >= 60.0,
        "cell_containment": abs(x) + max(j, l) / 2 < PERIOD_NM / 2 and abs(y) + max(w, l) / 2 < PERIOD_NM / 2,
        "no_overlap": direct > 0, "exact_hash_unique_in_probe": row["exact_geometry_hash_sha256"] not in seen_hashes,
        "physical_geometry_unique_in_probe": physical_key(row) not in seen_keys,
        "no_previous_exact_physics_evidence": row["exact_geometry_hash_sha256"] not in existing_hashes and physical_key(row) not in existing_keys,
    }
    return {"pass": all(checks.values()), "checks": checks, "direct_gap_nm": direct, "periodic_gap_x_nm": periodic_x, "periodic_gap_y_nm": periodic_y, "physical_key": list(physical_key(row)), "outside_old_H500_search_box": True}


def compensation_audit() -> dict:
    c = c_geometry()
    evidence = []
    manifests = [read_json(H1B1_MANIFEST).get("candidates", [])]
    rows = {row.get("candidate_id"): row for row in read_csv(H1B1_FULL) + read_csv(H1B2_FULL)}
    for group in manifests:
        for g in group:
            if g["candidate_id"] in rows:
                r = rows[g["candidate_id"]]
                err = number(r.get("projection_error_apcd_v1") or r.get("projector_error_apcd_v1"))
                phi = number(r.get("phase_wrapped_deg"))
                if err is not None and phi is not None:
                    evidence.append({"candidate_id": g["candidate_id"], "distance_5d": sum(abs(float(g[k]) - float(c[k])) for k in ("J1_side_nm", "J2_length_nm", "J2_width_nm", "D_nm", "Psi_deg")), "geometry_5d": {k: g[k] for k in ("J1_side_nm", "J2_length_nm", "J2_width_nm", "D_nm", "Psi_deg")}, "projector_error_delta_vs_C": err - c["projector_error_apcd_v1"], "phase_delta_vs_C": H2.signed_phase_delta(phi, c["phase_wrapped_deg"]), "projector_compatible": err <= PROJECTOR_ERROR_MAX + 1e-12})
    evidence.sort(key=lambda item: item["distance_5d"])
    variables = []
    for key in ("J1_side_nm", "J2_length_nm", "J2_width_nm", "D_nm", "Psi_deg"):
        samples = [e for e in evidence[:8] if abs(float(e["geometry_5d"][key]) - float(c[key])) > 1e-9]
        improving = [e for e in samples if e["projector_error_delta_vs_C"] < -0.005]
        variables.append({"variable": key, "nearest_samples": samples, "improving_samples": len(improving), "supported_direction": False, "classification": "LOCAL_EMPIRICAL_DIRECTION"})
    return {"schema": "LP_GLOBAL_H_H1B3_PROJECTOR_COMPENSATION_SELECTION_AUDIT_V1", "stage": "H1B-3", "status": "NO_SUPPORTED_PROJECTOR_COMPENSATION_DIRECTION", "reference_candidate": c, "method": "nearest authoritative H1B1/H1B2 full-Jones evidence; descriptive finite differences only", "variables": variables, "selected_direction": None, "fallback": "SECOND_CONSERVATIVE_LOCAL_NEIGHBOR", "provenance_limit": "LOCAL_EMPIRICAL_DIRECTION; not a global causal claim"}


def build_selection_audit() -> tuple[list[dict], dict, dict]:
    candidates = materialize_candidates()
    existing_hashes, existing_keys = old_geometry_evidence()
    seen_hashes, seen_keys = set(existing_hashes), set(existing_keys)
    d_success = d5(c_geometry(), parent_geometry())
    comp = compensation_audit()
    rows = []
    for row in candidates:
        check = legality(row, seen_hashes, seen_keys, existing_hashes, existing_keys)
        row["legality"] = check
        actual = d5(row, c_geometry())
        requested = {k: round((0.5 if row["candidate_id"] in ("H1B3_F1_CONSERVATIVE_FORWARD", "H1B3_F3_FORWARD_PLUS_PROJECTOR_COMPENSATION") else 1.0) * d_success[k], 12) for k in d_success}
        if row["candidate_id"] == "H1B3_F4_PROJECTOR_ROBUST_LOCAL_NEIGHBOR":
            requested = {k: None for k in d_success}
        row["displacement_5d_from_C"] = actual
        row["requested_displacement_5d_from_C"] = requested
        rows.append({"candidate_id": row["candidate_id"], "role": row["role"], "parent_reference_id": row["parent_reference_id"], "exact_5d": {k: row[k] for k in d_success}, "requested_displacement_5d_from_C": requested, "actual_legal_displacement_5d_from_C": actual, "d_success_parent_to_C": d_success, "supporting_authoritative_evidence": row["supporting_authoritative_evidence"], "legality": check, "exact_geometry_hash_sha256": row["exact_geometry_hash_sha256"], "status": "FROZEN_FOR_EXECUTION"})
        if not check["pass"]:
            raise RuntimeError(f"HARD_STOP_H1B3_CANDIDATE_LEGALITY:{row['candidate_id']}:{check}")
        seen_hashes.add(row["exact_geometry_hash_sha256"]); seen_keys.add(physical_key(row))
    if len(candidates) != MAX_GEOMETRIES or len({r["exact_geometry_hash_sha256"] for r in candidates}) != MAX_GEOMETRIES:
        raise RuntimeError("HARD_GATE_H1B3_EXACTLY_FOUR_UNIQUE_GEOMETRIES")
    audit = {"schema": "LP_GLOBAL_H_H1B3_CANDIDATE_SELECTION_AUDIT_V1", "stage": "H1B-3", "status": "FROZEN_FOR_EXECUTION", "solver_budget": {"new_geometries": 4, "formal_x_y_subruns": 8, "H_global_nm": 550.0, "H500_scheduled": False}, "parent_lineage": {"parent": parent_geometry(), "C": c_geometry(), "d_success_parent_to_C": d_success, "old_compatible_upper_edge_deg": 106.96528957076407, "new_compatible_upper_edge_deg": 114.81832490844113, "d_success_source": "H1B2 C exact candidate manifest and H0 high007 exact geometry"}, "candidate_count": 4, "rows": rows}
    return candidates, audit, comp


def build_manifest(candidates: list[dict], audit: dict, comp: dict) -> dict:
    ancestry = subprocess.run(["git", "merge-base", "--is-ancestor", H1B2_ACCEPTED_HEAD, current_head()], cwd=ROOT)
    if current_branch() != TARGET_BRANCH or ancestry.returncode != 0:
        raise RuntimeError(f"HARD_GATE_H1B2_ACCEPTED_PROVENANCE:{current_branch()}:{current_head()}")
    final = read_json(H1B2_FINAL)
    span = number(final.get("span_comparison", {}).get("new_merged_H550_projector_compatible_span_deg"))
    accounting = final.get("solver_accounting", {})
    if final.get("status") != "COMPLETE_ANALYSIS" or abs((span or -1) - BASELINE_H1B2_SPAN) > 1e-9 or accounting.get("solver_subruns_entered") != 10 or accounting.get("solver_subruns_accepted") != 10:
        raise RuntimeError("HARD_GATE_H1B2_AUTHORITATIVE_BASELINE")
    live = H2.compact_snapshot(SLOT.live_job_snapshot())
    if live["global_active_jobs"] > SLOT.GLOBAL_CAPACITY or live["lp_active_jobs"] > SLOT.MAX_ACTIVE_FDTD_PER_BRANCH:
        raise RuntimeError("HARD_GATE_SCHEDULER_CAPACITY")
    contract = {"H_global_nm": 550.0, "J1_H_nm": 550.0, "J2_H_nm": 550.0, "bottom_plane_nm": 0.0, "period_nm": [432.0, 432.0], "material": MATERIAL, "source_z_nm": -250.0, "monitor_z_nm": 1000.0, "observable": "transmission_side_coordinate_weighted_complex_G0", "endpoint_convention": "deduplicate_periodic_endpoints_and_reclose_period", "normalization": "sqrt(T)/norm(weighted_Ex,weighted_Ey)", "projector": [[1, 0], [0, 0]], "phase_reference": "arg(txx)", "formal_polarizations": ["x", "y"]}
    manifest = {"schema": "LP_GLOBAL_H_H1B3_CANDIDATE_MANIFEST_V1", "stage": "H1B-3", "status": "FROZEN_FOR_EXECUTION", "branch": TARGET_BRANCH, "head": current_head(), "baseline_H1B2_compatible_span_deg": BASELINE_H1B2_SPAN, "compensation_audit_sha256": sha256_obj(comp), "candidate_selection_audit_sha256": sha256_obj(audit), "physical_contract": contract, "physical_contract_sha256": sha256_obj(contract), "H500_scheduled": False, "pre_execution_live_snapshot": live, "global_capacity": SLOT.GLOBAL_CAPACITY, "max_active_fdtd_per_branch": SLOT.MAX_ACTIVE_FDTD_PER_BRANCH, "processes_per_job": SLOT.PROCESSES_PER_JOB, "threads_per_job": SLOT.THREADS_PER_JOB, "candidates": candidates}
    manifest["freeze_sha256"] = sha256_obj(manifest)
    return manifest


def case_identity(candidate: dict, pol: str, head: str) -> dict:
    return {"stage": "H1B-3", "candidate_id": candidate["candidate_id"], "exact_geometry_hash_sha256": candidate["exact_geometry_hash_sha256"], "geometry_identity": candidate["geometry_identity"], "H_global_nm": H_GLOBAL_NM, "polarization": pol, "material_contract": MATERIAL, "period_nm": [PERIOD_NM, PERIOD_NM], "builder_version": H2.SUP.H1A.BUILDER_VERSION, "builder_commit": head, "formal_extraction_convention": H2.SUP.H1A.EXTRACTION_CONVENTION, "diffraction_order": "G0"}


def case_name(candidate: dict, pol: str) -> str:
    return f"H1B3_{candidate['candidate_id']}_H550_P{pol}"


H2.case_identity = case_identity
H2.case_name = case_name
H2.OUT = OUT
H2.REPORT = REPORT
H2.RUNTIME = RUNTIME


def accounting_path() -> Path:
    return OUT / "h1b3_solver_accounting.json"


def load_accounting() -> dict:
    return read_json(accounting_path()) if accounting_path().exists() else {"solver_entries": [], "cases": []}


def write_accounting(payload: dict) -> None:
    atomic_json(accounting_path(), payload)


def initialize_accounting(manifest: dict) -> dict:
    old = load_accounting()
    if old.get("solver_entries") and old.get("manifest_freeze_sha256") != manifest["freeze_sha256"]:
        raise RuntimeError("HARD_GATE_H1B3_ACCOUNTING_MANIFEST_MISMATCH_AFTER_ENTRY")
    cases = old.get("cases") or [{"case_id": case_name(c, p), "candidate_id": c["candidate_id"], "geometry_hash_sha256": c["exact_geometry_hash_sha256"], "H_global_nm": 550.0, "polarization": p, "planned": True, "attempted": False, "solver_entered": False, "accepted": False, "quarantined": False, "recovered": False} for c in manifest["candidates"] for p in POLARIZATIONS]
    if len(cases) != MAX_SUBRUNS:
        raise RuntimeError("HARD_GATE_H1B3_ACCOUNTING_CASE_COUNT")
    payload = {"schema": "LP_GLOBAL_H_H1B3_SOLVER_ACCOUNTING_V1", "stage": "H1B-3", "manifest_freeze_sha256": manifest["freeze_sha256"], "solver_budget_planned": 8, "H_global_nm_only": 550.0, "H500_scheduled": False, "cases": cases, "solver_entries": old.get("solver_entries", []), "status": old.get("status", "PLANNED")}
    write_accounting(payload)
    return payload


def update_case(case_id: str, updates: dict, entry: dict | None = None) -> dict:
    payload = load_accounting()
    for row in payload["cases"]:
        if row.get("case_id") == case_id:
            row.update(updates); break
    else:
        raise RuntimeError(f"unknown case in accounting: {case_id}")
    if entry is not None and not any(item.get("case_id") == case_id for item in payload["solver_entries"]):
        payload["solver_entries"].append(entry)
    write_accounting(payload)
    return payload


H2.accounting_path = accounting_path
H2.load_accounting = load_accounting
H2.write_accounting = write_accounting
H2.initialize_accounting = initialize_accounting
H2.update_case = update_case


def normalize_row(row: dict, source: str) -> dict:
    row = dict(row); row["source_class"] = source; row["physics_origin"] = source; row["diffraction_order"] = row.get("diffraction_order") or "G0"
    row["phase_wrapped_deg"] = float(row["phase_wrapped_deg"]) % 360.0
    err = number(row.get("projection_error_apcd_v1") or row.get("projector_error_apcd_v1")); row["projector_error_apcd_v1"] = err; row["projector_compatible"] = err is not None and err <= PROJECTOR_ERROR_MAX + 1e-12
    row["selected_throughput_Txx"] = number(row.get("Txx") or row.get("selected_throughput_Txx"))
    return row


def old_h550_rows() -> list[dict]:
    return [normalize_row(row, "H1A_AUTHORITATIVE_FULL_JONES") for row in H2.old_h550_rows()]


def h1b1_rows() -> list[dict]:
    return [normalize_row(row, "H1B1_AUTHORITATIVE_FULL_JONES") for row in H2.h1b1_h550_rows()]


def h1b2_rows() -> list[dict]:
    return [normalize_row(row, "H1B2_AUTHORITATIVE_FULL_JONES") for row in read_csv(H1B2_FULL)]


def dedup(rows: list[dict]) -> list[dict]:
    output = []; seen = set()
    for row in rows:
        key = row.get("exact_geometry_hash_sha256") or row.get("geometry_hash_sha256") or (row.get("candidate_id"), row.get("H_global_nm"))
        if key in seen: continue
        seen.add(key); output.append(row)
    return output


def signed_delta(value: float, parent: float) -> float:
    return ((value - parent + 180.0) % 360.0) - 180.0


def analyze(manifest: dict, results: dict[str, dict]) -> dict:
    full_new = []
    for c in manifest["candidates"]:
        x, y = results.get(case_name(c, "x")), results.get(case_name(c, "y"))
        if x and y and x.get("status") == "ACCEPTED" and y.get("status") == "ACCEPTED":
            row = H2.full_jones_row(c, x, y); row["source_class"] = "H1B3_NEW_SOLVER_XY_FORMAL"; row["physics_scope"] = "FULL_JONES_H1B3_PHYSICS"; row["diffraction_order"] = "G0"; full_new.append(normalize_row(row, "H1B3_NEW_SOLVER_XY_FORMAL"))
    old = dedup(old_h550_rows() + h1b1_rows() + h1b2_rows())
    merged = dedup(old + full_new)
    compatible = [row for row in merged if row["projector_compatible"]]
    old_compatible = [row for row in old if row["projector_compatible"]]
    arc = H2.circular_arc([float(row["phase_wrapped_deg"]) for row in compatible]); old_arc = H2.circular_arc([float(row["phase_wrapped_deg"]) for row in old_compatible]); raw_arc = H2.circular_arc([float(row["phase_wrapped_deg"]) for row in merged])
    pair, pair_ids = H2.max_pairs(compatible)
    cphi, cerr = c_geometry()["phase_wrapped_deg"], c_geometry()["projector_error_apcd_v1"]
    upper_ids = [row.get("candidate_id") for row in compatible if row.get("candidate_id") in {c["candidate_id"] for c in manifest["candidates"]} and abs(float(row["phase_wrapped_deg"]) - float(arc["arc_end_deg"])) < 1e-8]
    effects = []
    for row in full_new:
        gain = signed_delta(float(row["phase_wrapped_deg"]), cphi); derr = float(row["projector_error_apcd_v1"]) - cerr; comp = bool(row["projector_compatible"])
        if gain > 1e-9 and comp: classification = "PHASE_GAIN_WITH_PROJECTOR_PRESERVED"
        elif gain > 1e-9 and not comp: classification = "PHASE_GAIN_WITH_PROJECTOR_DEGRADED"
        elif derr < -1e-9 and abs(gain) <= 1.0: classification = "PROJECTOR_IMPROVED_WITH_PHASE_PRESERVED"
        else: classification = "NO_USEFUL_LOCAL_GAIN"
        cand = next(c for c in manifest["candidates"] if c["candidate_id"] == row["candidate_id"])
        effects.append({"candidate_id": row["candidate_id"], "role": cand["role"], "phi_deg": row["phase_wrapped_deg"], "projector_error_apcd_v1": row["projector_error_apcd_v1"], "projector_error_delta_vs_C": derr, "projector_margin_to_compatibility_threshold": PROJECTOR_ERROR_MAX - row["projector_error_apcd_v1"], "selected_throughput_Txx": row.get("selected_throughput_Txx"), "phase_gain_vs_C_deg": gain, "projector_compatible": comp, "classification": classification, "exact_5d": {k: cand[k] for k in ("J1_side_nm", "J2_length_nm", "J2_width_nm", "D_nm", "Psi_deg")}, "actual_legal_displacement_5d_from_C": cand["displacement_5d_from_C"], "legality": cand["legality"]})
    gain = arc["coverage_deg"] - BASELINE_H1B2_SPAN; flag60 = pair >= 60.0
    nearby = [row for row in compatible if row.get("candidate_id") not in (None, "H1B3_F2_FULL_FORWARD") and abs(float(row["phase_wrapped_deg"]) - cphi) <= 10.0]
    new_extreme = bool(upper_ids)
    if not flag60: robustness = "INCONCLUSIVE"
    elif new_extreme and len(nearby) >= 1 and all(float(row.get("projector_error_apcd_v1") or 999) < PROJECTOR_ERROR_MAX for row in nearby) and all(float(row.get("selected_throughput_Txx") or 0) > 0.2 for row in nearby): robustness = "SUPPORTED_LOCAL_REGION"
    else: robustness = "SINGLE_POINT_FRAGILE"
    if len(full_new) < 4: verdict = "H1B3_INCONCLUSIVE"; route = "INSUFFICIENT_ACCEPTED_FULL_JONES_EVIDENCE"
    elif flag60 and robustness == "SUPPORTED_LOCAL_REGION": verdict = "H1B3_REACHED_60_SECTOR_ROBUST"; route = "SYSTEMATIC_H550_MANIFOLD_MAPPING"
    elif flag60: verdict = "H1B3_REACHED_60_SECTOR_FRAGILE"; route = "SYSTEMATIC_H550_MANIFOLD_MAPPING"
    elif gain > 1e-9: verdict = "H1B3_FINAL_REFINEMENT_IMPROVED_BUT_BELOW_60"; route = "TARGETED_CONSTITUENT_RECONNAISSANCE"
    else: verdict = "H1B3_PROJECTOR_LIMITED_LOCAL_SATURATION"; route = "TARGETED_CONSTITUENT_RECONNAISSANCE"
    span = {"baseline_H1B2_compatible_span_deg": BASELINE_H1B2_SPAN, "baseline_H1B2_compatible_arc": old_arc, "new_merged_H550_compatible_arc": arc, "new_merged_H550_raw_arc": raw_arc, "new_merged_H550_projector_compatible_count": len(compatible), "new_merged_H550_projector_compatible_span_deg": arc["coverage_deg"], "incremental_gain_deg": gain, "upper_edge_extension_from_C_deg": max(0.0, float(arc["arc_end_deg"]) - cphi), "max_compatible_pair_separation_deg": pair, "max_compatible_pair_ids": pair_ids, "new_sector_gap_deg": 60.0 - pair, "merged_H550_count": len(merged), "new_H1B3_full_jones_count": len(full_new), "new_upper_extremum_ids": upper_ids, "FLAG_60_SECTOR": flag60, "FLAG_120_ML_RESTART": arc["coverage_deg"] >= 120.0}
    return {"full_new": full_new, "merged": merged, "effects": effects, "span": span, "verdict": verdict, "route": route, "robustness": {"SECTOR_60_ROBUSTNESS": robustness, "flag_60": flag60, "new_upper_extremum_ids": upper_ids, "nearby_compatible_points": [row.get("candidate_id") for row in nearby], "new_extremum_projector_margin": min((PROJECTOR_ERROR_MAX - float(row.get("projector_error_apcd_v1")) for row in full_new if row.get("candidate_id") in upper_ids), default=None), "throughput_collapse_check": "Txx > 0.2 required for supported region", "legality_boundary_check": "all frozen legality checks must pass"}}


def write_analysis(manifest: dict, audit: dict, comp: dict, analysis: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True); REPORT.mkdir(parents=True, exist_ok=True)
    accounting = load_accounting(); accounting.update({"status": "COMPLETE_ANALYSIS", "solver_subruns_entered": len(accounting.get("solver_entries", [])), "solver_subruns_accepted": sum(bool(c.get("accepted")) for c in accounting.get("cases", [])), "solver_subruns_quarantined": sum(bool(c.get("quarantined")) for c in accounting.get("cases", [])), "H500_scheduled": False, "H500_replay_check": {"scheduled": False, "authoritative_rows": len([r for r in read_csv(H1A_FULL) if number(r.get("H_global_nm")) == 500.0])}}); write_accounting(accounting)
    artifacts = {"candidate_selection_audit": OUT / "h1b3_candidate_selection_audit.json", "projector_compensation_audit": OUT / "h1b3_projector_compensation_audit.json", "candidate_manifest": OUT / "h1b3_candidate_manifest.json", "solver_accounting": OUT / "h1b3_solver_accounting.json", "full_jones": OUT / "h1b3_full_jones.csv", "merged_manifold": OUT / "h1b3_merged_h550_manifold.csv", "candidate_effects": OUT / "h1b3_candidate_effects.csv", "sector_robustness": OUT / "h1b3_sector_robustness.json", "final": OUT / "h1b3_final.json", "summary": OUT / "h1b3_summary.md"}
    write_csv(artifacts["full_jones"], analysis["full_new"]); write_csv(artifacts["merged_manifold"], analysis["merged"]); write_csv(artifacts["candidate_effects"], analysis["effects"]); atomic_json(artifacts["candidate_selection_audit"], audit); atomic_json(artifacts["projector_compensation_audit"], comp); atomic_json(artifacts["candidate_manifest"], manifest); atomic_json(artifacts["solver_accounting"], accounting); atomic_json(artifacts["sector_robustness"], analysis["robustness"])
    final = {"schema": "LP_GLOBAL_H_H1B3_FINAL_V1", "stage": "H1B-3", "status": "COMPLETE_ANALYSIS", "branch": current_branch(), "head": current_head(), "manifest_freeze_sha256": manifest["freeze_sha256"], "solver_accounting": accounting, "verdict": analysis["verdict"], "recommended_next_route": analysis["route"], "span_comparison": analysis["span"], "candidate_effects": analysis["effects"], "sector_robustness": analysis["robustness"], "flags": {"FLAG_60_SECTOR": analysis["span"]["FLAG_60_SECTOR"], "FLAG_120_ML_RESTART": analysis["span"]["FLAG_120_ML_RESTART"]}, "H500_replay_check": accounting["H500_replay_check"], "artifacts": {key: str(path) for key, path in artifacts.items()}}
    atomic_json(artifacts["final"], final)
    lines = ["# Stage H1B-3 H550 Projector-Preserving Upper-Edge Micro-Refinement", "", f"- Verdict: `{final['verdict']}`", f"- Route: `{final['recommended_next_route']}`", f"- Branch / HEAD: `{final['branch']}` / `{final['head']}`", f"- Planned / entered / accepted: `8` / `{accounting['solver_subruns_entered']}` / `{accounting['solver_subruns_accepted']}`", f"- H1B-2 baseline compatible span: `{BASELINE_H1B2_SPAN:.12f}` deg", f"- H1B-3 compatible span: `{analysis['span']['new_merged_H550_projector_compatible_span_deg']:.12f}` deg", f"- Incremental gain: `{analysis['span']['incremental_gain_deg']:.12f}` deg", f"- Upper extension from C: `{analysis['span']['upper_edge_extension_from_C_deg']:.12f}` deg", f"- Sector gap to 60 deg: `{analysis['span']['new_sector_gap_deg']:.12f}` deg", f"- FLAG_60_SECTOR: `{analysis['span']['FLAG_60_SECTOR']}`; FLAG_120_ML_RESTART: `{analysis['span']['FLAG_120_ML_RESTART']}`", f"- SECTOR_60_ROBUSTNESS: `{analysis['robustness']['SECTOR_60_ROBUSTNESS']}`", "", "## Candidate effects", ""]
    lines += [f"- {e['candidate_id']}: phi={e['phi_deg']}, projector_error={e['projector_error_apcd_v1']}, delta_vs_C={e['projector_error_delta_vs_C']}, Txx={e['selected_throughput_Txx']}, compatible={e['projector_compatible']}, classification={e['classification']}" for e in analysis["effects"]]
    lines += ["", "## Artifacts", ""] + [f"- {key}: `{path}`" for key, path in final["artifacts"].items()]
    artifacts["summary"].write_text("\n".join(lines) + "\n", encoding="utf-8")
    for path in artifacts.values():
        if path.name == "h1b3_summary.md": continue
        (REPORT / path.name).write_bytes(path.read_bytes())
    (REPORT / "h1b3_summary.md").write_bytes(artifacts["summary"].read_bytes())


def preflight() -> int:
    candidates, audit, comp = build_selection_audit(); manifest = build_manifest(candidates, audit, comp)
    OUT.mkdir(parents=True, exist_ok=True); REPORT.mkdir(parents=True, exist_ok=True)
    if (OUT / "h1b3_solver_accounting.json").exists() and load_accounting().get("solver_entries"):
        old = read_json(OUT / "h1b3_candidate_manifest.json")
        if old.get("freeze_sha256") != manifest["freeze_sha256"]: raise RuntimeError("HARD_GATE_EXISTING_H1B3_MANIFEST_MISMATCH_AFTER_ENTRY")
    atomic_json(OUT / "h1b3_candidate_selection_audit.json", audit); atomic_json(OUT / "h1b3_projector_compensation_audit.json", comp); atomic_json(OUT / "h1b3_candidate_manifest.json", manifest); initialize_accounting(manifest); atomic_json(REPORT / "h1b3_candidate_selection_audit.json", audit); atomic_json(REPORT / "h1b3_projector_compensation_audit.json", comp); atomic_json(REPORT / "h1b3_candidate_manifest.json", manifest); atomic_json(REPORT / "h1b3_solver_accounting.json", load_accounting())
    print(json.dumps({"status": "FROZEN_READY", "freeze_sha256": manifest["freeze_sha256"], "candidates": [{"candidate_id": c["candidate_id"], "role": c["role"], "D_nm": c["D_nm"], "Psi_deg": c["Psi_deg"], "legality": c["legality"]} for c in candidates], "live_snapshot": manifest["pre_execution_live_snapshot"], "compensation_status": comp["status"]}, indent=2, ensure_ascii=False)); return 0


def execute(manifest: dict) -> int:
    accounting = initialize_accounting(manifest); runtime = H2.make_runtime(); scheduler = SLOT.GlobalSlotScheduler(SLOT_REGISTRY); entered = list(accounting.get("solver_entries", [])); results = {}
    for c in manifest["candidates"]:
        for pol in POLARIZATIONS:
            results[case_name(c, pol)] = H2.run_case(runtime, c, pol, manifest, scheduler, entered)
    analysis = analyze(manifest, results); write_analysis(manifest, read_json(OUT / "h1b3_candidate_selection_audit.json"), read_json(OUT / "h1b3_projector_compensation_audit.json"), analysis); print(json.dumps({"status": "COMPLETE_ANALYSIS", "verdict": analysis["verdict"], "span": analysis["span"]}, indent=2, ensure_ascii=False)); return 0


def postprocess(manifest: dict) -> int:
    accounting = load_accounting()
    if len(accounting.get("solver_entries", [])) != MAX_SUBRUNS: raise RuntimeError("HARD_GATE_H1B3_POSTPROCESS_ENTRY_COUNT")
    results = {}
    for c in manifest["candidates"]:
        for pol in POLARIZATIONS:
            identity = case_identity(c, pol, manifest["head"]); recovered = H2.checkpoint_result(RUNTIME / "cases" / case_name(c, pol), identity)
            if not recovered: raise RuntimeError(f"HARD_GATE_H1B3_POSTPROCESS_CHECKPOINT_MISSING:{c['candidate_id']}:{pol}")
            results[case_name(c, pol)] = recovered
    analysis = analyze(manifest, results); write_analysis(manifest, read_json(OUT / "h1b3_candidate_selection_audit.json"), read_json(OUT / "h1b3_projector_compensation_audit.json"), analysis); print(json.dumps({"status": "COMPLETE_ANALYSIS_POSTPROCESS_ONLY", "solver_replay": False, "verdict": analysis["verdict"], "span": analysis["span"]}, indent=2, ensure_ascii=False)); return 0


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("mode", choices=("preflight", "execute", "postprocess")); args = parser.parse_args()
    if args.mode == "preflight": return preflight()
    manifest = read_json(OUT / "h1b3_candidate_manifest.json")
    if manifest.get("status") != "FROZEN_FOR_EXECUTION": raise RuntimeError("HARD_GATE_H1B3_MANIFEST_NOT_FROZEN")
    return execute(manifest) if args.mode == "execute" else postprocess(manifest)


if __name__ == "__main__":
    raise SystemExit(main())
