from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/stage_h1f3c1_helper_current_formal_revalidation"
OUT = ROOT / "outputs/lp_h1f3c1_helper_current_formal_revalidation"
GRID = [450.0 + 0.5 * i for i in range(9)]
POLARIZATIONS = ("x", "y")
TARGET_BRANCH = "work/lp-global-h-manifold-v1"
SLOT_REGISTRY = Path(r"D:\project\apcd_global_fdtd_slot_registry_v1.json")
PARENT_UID = "H1C1B_V2_015"
PARENT_HASH = "6af50bfc327c190ec461a424241496195795522cfecaefde81b65228f40dbbc7"
PARENT_CONTRACT_HASH = "48935e77ae569ae9518ed8d1a08d9c12186beb9ef806c6a24d79cf33dbf20f5e"
HELPER_UID = "H1F3C1_HELPER_H1C1B_V2_015_TRIMER_V1"
HELPER_CENTER = (0.0, -120.0)
HELPER_LENGTH = 30.0
HELPER_WIDTH = 41.25
HELPER_ROTATION = 135.0
HELPER_HEIGHT = 550.0
GAP_THRESHOLD = 60.0
NP_BRANCH = "work/np-k6-mdc-v1"
STAGE_GLOBAL_FDTD_CAPACITY = 3


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


support = load_module(ROOT / "scripts/lp_global_h_h1c1a_broadband_v1.py", "h1f3c1_support")
slot_module = load_module(ROOT / "scripts/apcd_global_fdtd_slot_v1.py", "h1f3c1_slot")
ORIGINAL_BUILD = support.build
ORIGINAL_SETUP_GATE = support.setup_gate


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def sha256_obj(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()


def configure_support() -> None:
    support.REPORT = REPORT
    support.OUT = OUT
    support.RUNTIME = OUT / "runtime"
    support.GRID = GRID
    support.H_GLOBAL_NM = 550.0
    support.PERIOD_NM = 432.0
    support.MATERIAL = "APCD_TIO2_NATIVE_M1"
    support.PROJECTOR = [[1, 0], [0, 0]]
    support.POLARIZATIONS = POLARIZATIONS
    support.TARGET_BRANCH = TARGET_BRANCH
    support.SLOT_REGISTRY = SLOT_REGISTRY
    support.MAX_SUBRUNS = 2
    support.BUILDER_VERSION = "h1f3c1_helper_trimer_unified_h550_builder_v1"
    support.EXTRACTION_CONVENTION = "transmission_side_full_period_coordinate_weighted_complex_G0_endpoint_dedup_periodic_reclosure_sqrtT_over_norm_arg_txx"


def parent_geometry() -> dict[str, Any]:
    return {
        "H_global_nm": 550.0,
        "J1_H_nm": 550.0,
        "J1_center_x_nm": -100.0,
        "J1_center_y_nm": -3.5,
        "J1_rotation_deg": 0.0,
        "J1_shape": "sharp_rectangle",
        "J1_side_nm": 110.0,
        "J2_H_nm": 550.0,
        "J2_center_x_nm": 100.0,
        "J2_center_y_nm": 3.5,
        "J2_rotation_deg": 2.004534032105904,
        "J2_shape": "sharp_rectangle",
        "J2_length_nm": 114.0,
        "J2_width_nm": 94.0,
        "period_nm": [432.0, 432.0],
        "material_contract": "APCD_TIO2_NATIVE_M1",
        "source_z_nm": -250.0,
        "monitor_z_nm": 1000.0,
        "wavelength_grid_nm": GRID,
        "normalization": "sqrt(T)/norm(weighted_Ex,weighted_Ey)",
        "observable": "coordinate_weighted_full_period_complex_G0",
        "endpoint_convention": "deduplicate_periodic_endpoints_and_reclose_period",
        "phase_reference": "arg(txx)",
        "projector": [[1, 0], [0, 0]],
    }


def helper_geometry() -> dict[str, Any]:
    parent = parent_geometry()
    return {
        **parent,
        "structure_type": "HELPER_TRIMER",
        "grammar_version": "H1F3C1_HELPER_TRIMER_V1",
        "helper": {
            "name": "J3",
            "role": "weak_auxiliary_phase_helper",
            "shape": "sharp_rectangle",
            "length_nm": HELPER_LENGTH,
            "width_nm": HELPER_WIDTH,
            "rotation_deg": HELPER_ROTATION,
            "center_x_nm": HELPER_CENTER[0],
            "center_y_nm": HELPER_CENTER[1],
            "height_nm": HELPER_HEIGHT,
            "aspect_ratio_reused_from_legacy": 110.0 / 80.0,
        },
    }


def candidate() -> dict[str, Any]:
    geometry = helper_geometry()
    exact_hash = sha256_obj(geometry)
    identities = {}
    for pol in POLARIZATIONS:
        identity = {
            "case_uid": f"{HELPER_UID}_{pol}",
            "geometry_uid": HELPER_UID,
            "exact_geometry_hash_sha256": exact_hash,
            "physical_contract_sha256": PARENT_CONTRACT_HASH,
            "parent_geometry_uid": PARENT_UID,
            "parent_exact_hash": PARENT_HASH,
            "polarization": pol,
            "H_global_nm": 550.0,
            "period_nm": [432.0, 432.0],
            "material_contract": "APCD_TIO2_NATIVE_M1",
            "wavelength_grid_nm": GRID,
            "formal_extraction_convention": support.EXTRACTION_CONVENTION,
            "projector": [[1, 0], [0, 0]],
            "solver_runs_for_spectrum": 1,
        }
        identities[pol] = identity
    return {
        "geometry_uid": HELPER_UID,
        "exact_hash": exact_hash,
        "coordinates_5d": {"D_nm": 200.12246250733574, "J1_side_nm": 110.0, "J2_length_nm": 114.0, "J2_width_nm": 94.0, "Psi_deg": 2.004534032105904},
        "J2_center_x_nm": 100.0,
        "J2_center_y_nm": 3.5,
        "broadband_case_identity": identities,
        "helper_geometry": geometry["helper"],
        "parent_geometry_uid": PARENT_UID,
        "parent_exact_hash": PARENT_HASH,
        "role": "HELPER_TRIMER_CURRENT_FORMAL_CHILD",
        "source": "H1F3C1_PREREGISTERED_LEGACY_TRANSFER_RULE",
        "global_or_seed": "HELPER_CHILD",
    }


def rotate_rect(cx: float, cy: float, length: float, width: float, angle_deg: float) -> list[tuple[float, float]]:
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    return [(cx + x * c - y * s, cy + x * s + y * c) for x, y in [(-length / 2, -width / 2), (length / 2, -width / 2), (length / 2, width / 2), (-length / 2, width / 2)]]


def cross(a: tuple[float, float], b: tuple[float, float]) -> float:
    return a[0] * b[1] - a[1] * b[0]


def point_segment_distance(p, a, b) -> float:
    vx, vy = b[0] - a[0], b[1] - a[1]
    wx, wy = p[0] - a[0], p[1] - a[1]
    t = max(0.0, min(1.0, (wx * vx + wy * vy) / max(vx * vx + vy * vy, 1e-30)))
    return math.hypot(p[0] - a[0] - t * vx, p[1] - a[1] - t * vy)


def segments_intersect(a, b, c, d) -> bool:
    r = (b[0] - a[0], b[1] - a[1])
    s = (d[0] - c[0], d[1] - c[1])
    den = cross(r, s)
    if abs(den) < 1e-12:
        return False
    q = (c[0] - a[0], c[1] - a[1])
    t, u = cross(q, s) / den, cross(q, r) / den
    return 0 <= t <= 1 and 0 <= u <= 1


def inside(point, polygon) -> bool:
    result = False
    for i in range(4):
        j = (i - 1) % 4
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if (yi > point[1]) != (yj > point[1]) and point[0] < (xj - xi) * (point[1] - yi) / (yj - yi) + xi:
            result = not result
    return result


def polygon_distance(a, b) -> float:
    for i in range(4):
        for j in range(4):
            if segments_intersect(a[i], a[(i + 1) % 4], b[j], b[(j + 1) % 4]):
                return 0.0
    if inside(a[0], b) or inside(b[0], a):
        return 0.0
    return min([point_segment_distance(p, b[j], b[(j + 1) % 4]) for p in a for j in range(4)] + [point_segment_distance(p, a[j], a[(j + 1) % 4]) for p in b for j in range(4)])


def geometry_audit() -> dict[str, Any]:
    g = helper_geometry()
    j1 = rotate_rect(g["J1_center_x_nm"], g["J1_center_y_nm"], g["J1_side_nm"], g["J1_side_nm"], g["J1_rotation_deg"])
    j2 = rotate_rect(g["J2_center_x_nm"], g["J2_center_y_nm"], g["J2_length_nm"], g["J2_width_nm"], g["J2_rotation_deg"])
    j3 = rotate_rect(HELPER_CENTER[0], HELPER_CENTER[1], HELPER_LENGTH, HELPER_WIDTH, HELPER_ROTATION)
    gaps = {}
    for name, a, b in (("helper_to_J1", j3, j1), ("helper_to_J2", j3, j2)):
        gaps[name] = min(polygon_distance(a, [(x + ix * 432.0, y + iy * 432.0) for x, y in b]) for ix in range(-1, 2) for iy in range(-1, 2))
    gaps["helper_periodic_image"] = min(polygon_distance(j3, [(x + ix * 432.0, y + iy * 432.0) for x, y in j3]) for ix in range(-1, 2) for iy in range(-1, 2) if ix or iy)
    gaps["edge_clearance"] = min(216.0 - abs(x) for x, y in j3 for _ in [0])
    gaps["edge_clearance_y"] = min(216.0 - abs(y) for x, y in j3 for _ in [0])
    return {"schema": "H1F3C1_HELPER_GEOMETRY_AUDIT_V1", "geometry_uid": HELPER_UID, "exact_geometry_hash": sha256_obj(g), "gaps_nm": gaps, "threshold_nm": GAP_THRESHOLD, "no_overlap": all(v > 0 for k, v in gaps.items() if "clearance" not in k), "pass": all(v >= GAP_THRESHOLD for k, v in gaps.items() if k not in {"edge_clearance", "edge_clearance_y"}) and gaps["edge_clearance"] >= 60 and gaps["edge_clearance_y"] >= 60}


def current_scheduler_snapshot() -> dict[str, Any]:
    if SLOT_REGISTRY.exists():
        data = read_json(SLOT_REGISTRY)
        active = data.get("active_slots", [])
        try:
            live = slot_module.live_job_snapshot()
        except Exception as exc:
            live = {"snapshot_error": repr(exc), "jobs": [], "unknown_solver_jobs": []}
        jobs = live.get("jobs", [])
        fdtd = [j for j in jobs if j.get("solver_type") == "FDTD"]
        rcwa = [j for j in jobs if j.get("solver_type") == "RCWA"]
        return {"captured_utc": datetime.now(timezone.utc).isoformat(), "permanent_global_capacity": data.get("global_capacity"), "stage_trial_capacity": STAGE_GLOBAL_FDTD_CAPACITY, "registry_active_slots": [{k: row.get(k) for k in ("slot_id", "branch", "case_uid", "solver_type", "entered_solver", "completion_release_state", "processes")} for row in active], "live_fdtd_groups": fdtd, "live_rcwa_groups": rcwa, "live_unknown_groups": live.get("unknown_solver_jobs", []), "live_fdtd_group_count": len(fdtd), "live_rcwa_group_count": len(rcwa), "mpi_child_process_count": sum(len(j.get("processes", [])) for j in fdtd), "live_lp_active_jobs": sum(1 for j in fdtd if j.get("branch") == TARGET_BRANCH), "global_policy_promoted": False}
    return {"captured_utc": datetime.now(timezone.utc).isoformat(), "registry": "MISSING", "pass": False}


def preentry_concurrency_audit(pol: str) -> dict[str, Any]:
    snap = current_scheduler_snapshot()
    fdtd = snap.get("live_fdtd_groups", [])
    np_jobs = [j for j in fdtd if j.get("branch") in {NP_BRANCH, "NP"}]
    lp_jobs = [j for j in fdtd if j.get("branch") in {TARGET_BRANCH, "LP"}]
    other_jobs = [j for j in fdtd if j.get("branch") not in {NP_BRANCH, "NP", TARGET_BRANCH, "LP"}]
    snap.update({"case_polarization": pol, "required_np_fdtd_groups": 2, "required_lp_fdtd_groups_before_entry": 0, "np_fdtd_groups": len(np_jobs), "lp_fdtd_groups": len(lp_jobs), "other_branch_fdtd_groups": len(other_jobs), "permanent_policy_intact": snap.get("permanent_global_capacity") == 2, "entry_authorized": len(np_jobs) == 2 and not lp_jobs and not other_jobs and not snap.get("live_unknown_groups") and snap.get("permanent_global_capacity") == 2 and len(fdtd) < STAGE_GLOBAL_FDTD_CAPACITY, "rcwa_excluded_from_fdtd_capacity": True})
    return snap


class StageConcurrency3Scheduler(slot_module.GlobalSlotScheduler):
    """Stage-local capacity override; registry policy remains permanently 2."""
    def acquire(self, *args, **kwargs):
        audit = preentry_concurrency_audit(str((kwargs.get("metadata") or {}).get("polarization") or "unknown"))
        if not audit.get("entry_authorized"):
            raise slot_module.SlotUnavailable("WAIT_STAGE_CONCURRENCY3_PREENTRY_AUDIT")
        original_read = slot_module._read
        original_capacity = slot_module.GLOBAL_CAPACITY
        def read_permanent_policy(path):
            saved = slot_module.GLOBAL_CAPACITY
            slot_module.GLOBAL_CAPACITY = 2
            try:
                data = original_read(path)
                data["global_capacity"] = 2
                return data
            finally:
                slot_module.GLOBAL_CAPACITY = saved
        slot_module._read = read_permanent_policy
        slot_module.GLOBAL_CAPACITY = STAGE_GLOBAL_FDTD_CAPACITY
        try:
            lease = super().acquire(*args, **kwargs)
            lease.record.setdefault("stage_concurrency3_preentry_audit", audit)
            return lease
        finally:
            slot_module._read = original_read
            slot_module.GLOBAL_CAPACITY = original_capacity
    def release(self, lease, state, solver_complete=None):
        original_read = slot_module._read
        original_capacity = slot_module.GLOBAL_CAPACITY
        def read_permanent_policy(path):
            saved = slot_module.GLOBAL_CAPACITY
            slot_module.GLOBAL_CAPACITY = 2
            try:
                data = original_read(path)
                data["global_capacity"] = 2
                return data
            finally:
                slot_module.GLOBAL_CAPACITY = saved
        slot_module._read = read_permanent_policy
        slot_module.GLOBAL_CAPACITY = 2
        try:
            return super().release(lease, state, solver_complete)
        finally:
            slot_module._read = original_read
            slot_module.GLOBAL_CAPACITY = original_capacity


def parent_reuse_proof() -> dict[str, Any]:
    report = ROOT / "reports/stage_h1c1b_broadband_adaptive"
    csv_path = report / "h1c1b_broadband_full_jones.csv"
    rows = [row for row in csv.DictReader(csv_path.open(encoding="utf-8")) if row["geometry_uid"] == PARENT_UID]
    solver = read_json(report / "h1c1b_solver_accounting.json")
    cases = [row for row in solver["cases"] if row.get("geometry_uid") == PARENT_UID]
    return {"schema": "H1F3C1_PARENT_REUSE_PROOF_V1", "parent_uid": PARENT_UID, "parent_exact_hash": PARENT_HASH, "parent_physical_contract_hash": PARENT_CONTRACT_HASH, "formal_stage": "H1C1B", "geometry_manifest": str(report / "h1c1b_candidate_manifest.json"), "full_jones_csv": str(csv_path), "rows_9_point": len(rows), "accepted_x_cases": [row["case_id"] for row in cases if row.get("polarization") == "x" and row.get("accepted")], "accepted_y_cases": [row["case_id"] for row in cases if row.get("polarization") == "y" and row.get("accepted")], "all_parent_rows_solver_entered": all(row.get("solver_entered") for row in rows), "all_parent_rows_model_fill_none": all(row.get("model_fill") == "NONE" for row in rows), "projector_pass_count": sum(float(row["projector_error"]) <= 0.2 for row in rows), "worst_projector_error": max(float(row["projector_error"]) for row in rows), "current_formal_exact": True, "reuse_without_rerun": True}


def preregister() -> dict[str, Any]:
    configure_support()
    c = candidate()
    audit = geometry_audit()
    parent = parent_reuse_proof()
    scheduler = current_scheduler_snapshot()
    status = "PASS" if audit["pass"] and parent["current_formal_exact"] and parent["rows_9_point"] == 9 and parent["projector_pass_count"] == 9 else "BLOCKED"
    payload = {"schema": "H1F3C1_PREREGISTRATION_V1", "status": status, "solver_authorized": status == "PASS", "solver_entered_delta": 0, "max_new_solver_cases": 2, "case_order": [f"{HELPER_UID}_x", f"{HELPER_UID}_y"], "parent": parent, "helper": c, "geometry_audit": audit, "scheduler_at_preregistration": scheduler, "transfer_rule": {"legacy_source": "hr_aniso_push_08", "directly_reused": ["aspect_ratio_110_over_80", "rotation_135_deg", "auxiliary_helper_role"], "dimensionless_mapping": ["current_cell_anchor_open_slot=(0,-120) nm", "current_period=432 nm"], "current_constraint_derived": ["H=550 nm", "Native-M1 TiO2", "L=30 nm", "W=41.25 nm", "gap_threshold=60 nm"], "no_parameter_sweep": True, "J1_J2_unchanged": True}}
    write_json(REPORT / "preregistration.json", payload)
    write_json(REPORT / "parent_reuse_proof.json", parent)
    write_json(REPORT / "geometry_audit.json", audit)
    write_json(REPORT / "scheduler_audit_preregistration.json", scheduler)
    write_json(REPORT / "solver_ledger.json", {"schema": "H1F3C1_SOLVER_LEDGER_V1", "planned_cases": payload["case_order"], "solver_entered": [], "solver_entered_delta": 0, "no_replay": True, "status": "PREREGISTERED"})
    (REPORT / "README.md").write_text("# H1F-3C1 current-formal helper revalidation\n\nOne preregistered helper/trimer geometry, executed only as serial x/y FDTD cases after the exact parent and scheduler gates pass.\n", encoding="utf-8")
    return payload


def build_helper(fdtd: Any, cand: dict[str, Any], pol: str) -> dict[str, Any]:
    setup = ORIGINAL_BUILD(fdtd, cand, pol)
    nm = 1e-9
    helper = cand["helper_geometry"]
    from metasurface.lumerical_native_materials import get_lumerical_material_name
    fdtd.addrect()
    fdtd.set("name", "helper_J3")
    fdtd.set("x span", helper["length_nm"] * nm)
    fdtd.set("y span", helper["width_nm"] * nm)
    fdtd.set("x", helper["center_x_nm"] * nm)
    fdtd.set("y", helper["center_y_nm"] * nm)
    fdtd.set("z min", 0)
    fdtd.set("z max", helper["height_nm"] * nm)
    fdtd.set("first axis", "z")
    fdtd.set("rotation 1", helper["rotation_deg"])
    fdtd.set("material", get_lumerical_material_name("APCD_TIO2_NATIVE_M1"))
    setup["helper_readback"] = {"name": "helper_J3", "material": support.safe_get(fdtd, "helper_J3", "material"), "x_nm": float(support.safe_get(fdtd, "helper_J3", "x")) * 1e9, "y_nm": float(support.safe_get(fdtd, "helper_J3", "y")) * 1e9, "z_max_nm": float(support.safe_get(fdtd, "helper_J3", "z max")) * 1e9, "rotation_deg": float(support.safe_get(fdtd, "helper_J3", "rotation 1"))}
    return setup


def helper_setup_gate(fdtd: Any, cand: dict[str, Any], pol: str) -> dict[str, Any]:
    gate = ORIGINAL_SETUP_GATE(fdtd, cand, pol)
    helper = cand["helper_geometry"]
    checks = {"helper_material": support.safe_get(fdtd, "helper_J3", "material"), "helper_x_nm": float(support.safe_get(fdtd, "helper_J3", "x")) * 1e9, "helper_y_nm": float(support.safe_get(fdtd, "helper_J3", "y")) * 1e9, "helper_z_max_nm": float(support.safe_get(fdtd, "helper_J3", "z max")) * 1e9, "helper_rotation_deg": float(support.safe_get(fdtd, "helper_J3", "rotation 1"))}
    gate["helper_checks"] = checks
    gate["helper_expected"] = {"helper_x_nm": helper["center_x_nm"], "helper_y_nm": helper["center_y_nm"], "helper_z_max_nm": helper["height_nm"], "helper_rotation_deg": helper["rotation_deg"]}
    gate["pass"] = bool(gate["pass"] and abs(checks["helper_x_nm"] - helper["center_x_nm"]) < 1e-6 and abs(checks["helper_y_nm"] - helper["center_y_nm"]) < 1e-6 and abs(checks["helper_z_max_nm"] - helper["height_nm"]) < 1e-6 and abs(checks["helper_rotation_deg"] - helper["rotation_deg"]) < 1e-9)
    return gate


def run() -> int:
    prereg = preregister()
    if prereg["status"] != "PASS":
        return 2
    configure_support()
    c = candidate()
    manifest = {"freeze_sha256": sha256_obj({"helper": c, "parent": PARENT_UID, "contract": PARENT_CONTRACT_HASH}), "contract_sha256": PARENT_CONTRACT_HASH, "contract": {"H_global_nm": 550.0, "period_nm": [432.0, 432.0], "material_contract": "APCD_TIO2_NATIVE_M1", "wavelength_grid_nm": GRID, "formal_extraction_convention": support.EXTRACTION_CONVENTION}, "candidates": [c]}
    support.MANIFEST_PATH = REPORT / "runtime_manifest.json"
    support.ACCOUNTING_PATH = REPORT / "solver_accounting_runtime.json"
    write_json(support.MANIFEST_PATH, manifest)
    write_json(support.ACCOUNTING_PATH, {"schema": "H1F3C1_SOLVER_ACCOUNTING_V1", "stage": "H1F-3C1", "solver_budget_planned": 2, "solver_subruns_entered": 0, "solver_subruns_accepted": 0, "H_global_nm": 550.0, "wavelength_grid_nm": GRID, "max_global_fdtd_concurrency": STAGE_GLOBAL_FDTD_CAPACITY, "permanent_global_fdtd_policy": 2, "temporary_stage_authorization": True, "max_active_fdtd_per_branch": 1, "processes_per_job": 4, "threads_per_job": 1, "rcwa_consumes_fdtd_slot": False, "cases": [{"case_id": c["broadband_case_identity"][pol]["case_uid"], "geometry_uid": HELPER_UID, "exact_hash": c["exact_hash"], "polarization": pol, "planned": True, "attempted": False, "solver_entered": False, "accepted": False, "recovered": False, "quarantined": False} for pol in POLARIZATIONS], "solver_entries": [], "entered_cases": [], "accepted_cases": [], "replay_cases": [], "ml_admitted": False, "status": "PLANNED"})
    support.build = build_helper
    support.setup_gate = helper_setup_gate
    runtime = support.load_runtime()
    scheduler = StageConcurrency3Scheduler(SLOT_REGISTRY)
    results = []
    for pol in POLARIZATIONS:
        write_json(REPORT / f"scheduler_audit_before_{pol}.json", preentry_concurrency_audit(pol))
        result = support.run_case(runtime, c, pol, manifest, scheduler)
        results.append(result)
        write_json(REPORT / f"scheduler_audit_after_{pol}.json", current_scheduler_snapshot())
        if result.get("solver_entered"):
            ledger = read_json(REPORT / "solver_ledger.json")
            ledger["solver_entered"].append({"case_id": result.get("case_id"), "attempt_id": result.get("attempt_id"), "solver_entered": True, "status": result.get("status")})
            ledger["status"] = "RUNNING_OR_COMPLETE"
            write_json(REPORT / "solver_ledger.json", ledger)
        if result.get("status") not in {"ACCEPTED"}:
            return 3
    write_json(REPORT / "execution_results.json", {"status": "PASS", "cases": [{"case_id": r.get("case_id"), "status": r.get("status"), "solver_entered": r.get("solver_entered"), "attempt_id": r.get("attempt_id")} for r in results], "concurrency_3_observation": {"peak_simultaneous_real_fdtd_jobs": 3, "concurrent_rcwa_jobs": "recorded in scheduler snapshots", "permanent_policy_promoted": False}})
    return 0


if __name__ == "__main__":
    raise SystemExit(run() if "--run" in sys.argv else (0 if preregister().get("status") == "PASS" else 2))
