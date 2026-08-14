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
import socket
import subprocess
import time
import traceback
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/lp_global_h_h1b1"
REPORT = ROOT / "reports/stage_h1b1_global_h"
RUNTIME = OUT / "runtime"
H_GLOBAL_NM = 550.0
POLARIZATIONS = ("x", "y")
MAX_GEOMETRIES = 5
MAX_SUBRUNS = 10
PERIOD_NM = 432.0
MATERIAL = "APCD_TIO2_NATIVE_M1"
MANUFACTURING_GAP_NM = 60.0
BASELINE_COMPATIBLE_SPAN_DEG = 30.096722115614966
OLD_COMPATIBLE_ERROR_MAX = 0.1864961370084426
TARGET_BRANCH = "work/lp-global-h-manifold-v1"
ACCEPTED_H1B0_HEAD = "c7daf9350f72f44d69ac940b57278622c692eaf6"
PROPOSAL = ROOT / "reports/stage_h1b0_global_h/h1b0_proposed_next_probe.json"
HYPOTHESES = ROOT / "reports/stage_h1b0_global_h/h1b0_lateral_hypotheses.json"
H1B0_RANKING = ROOT / "reports/stage_h1b0_global_h/h1b0_fixed_h_ranking.csv"
H1B0_ANCHOR_RESPONSE = ROOT / "reports/stage_h1b0_global_h/h1b0_anchor_response.csv"
H1A_FINAL = ROOT / "reports/stage_h1a_global_h/stage_h1a_global_h_final.json"
H1A_FULL = ROOT / "outputs/lp_global_h_h1a/complete_jones_table.csv"
H0_ANCHORS = ROOT / "reports/stage_h0_global_h/anchor_manifest.json"
BOUNDS = ROOT / "outputs/lp_ml_dataset_v1/plans/lp_ml_dataset_v1_5d_design_space_contract_v1.json"
SLOT_REGISTRY = Path(r"D:\project\apcd_global_fdtd_slot_registry_v1.json")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


H1A = load_module(ROOT / "scripts/lp_global_h_h1a_probe_v1.py", "lp_h1b1_h1a_support")
RUNNER = H1A.RUNNER
SLOT = H1A.SLOT
H0 = H1A.H0


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


def integer(value: object) -> int:
    x = float(value)
    if not math.isfinite(x) or abs(x - round(x)) > 1e-9:
        raise ValueError(f"not an integer lateral dimension: {value!r}")
    return int(round(x))


def anchor_key(row: dict) -> tuple:
    d = float(row["D_nm"])
    psi = math.radians(float(row["Psi_deg"]))
    cx = round(d * math.cos(psi) / 2.0, 9)
    cy = round(d * math.sin(psi) / 2.0, 9)
    return (integer(row["J1_side_nm"]), integer(row["J2_length_nm"]), integer(row["J2_width_nm"]), cx, cy)


def geometry_identity(row: dict) -> dict:
    return {
        "schema": "LP_GLOBAL_H_H1B1_GEOMETRY_IDENTITY_V1",
        "H_global_nm": H_GLOBAL_NM,
        "J1_H_nm": H_GLOBAL_NM,
        "J2_H_nm": H_GLOBAL_NM,
        "bottom_plane_nm": 0.0,
        "period_nm": [PERIOD_NM, PERIOD_NM],
        "material_contract": MATERIAL,
        "J1_shape": "sharp_rectangle",
        "J2_shape": "sharp_rectangle",
        "J1_side_nm": integer(row["J1_side_nm"]),
        "J2_length_nm": integer(row["J2_length_nm"]),
        "J2_width_nm": integer(row["J2_width_nm"]),
        "J1_center_x_nm": float(row["J1_center_x_nm"]),
        "J1_center_y_nm": float(row["J1_center_y_nm"]),
        "J2_center_x_nm": float(row["J2_center_x_nm"]),
        "J2_center_y_nm": float(row["J2_center_y_nm"]),
        "J1_rotation_deg": 0.0,
        "J2_rotation_deg": float(row["Psi_deg"]),
        "source_z_nm": -250.0,
        "monitor_z_nm": 1000.0,
        "wavelength_nm": 450.0,
        "observable": "coordinate_weighted_full_period_complex_G0",
        "endpoint_convention": "deduplicate_periodic_endpoints_and_reclose_period",
        "normalization": "sqrt(T)/norm(weighted_Ex,weighted_Ey)",
        "phase_reference": "arg(txx)",
        "projector": [[1, 0], [0, 0]],
    }


def candidate_row(candidate_id: str, role: str, rationale: str, sources: list[str], j: int, l: int, w: int, cx: float, cy: float) -> dict:
    psi = math.degrees(math.atan2(cy, cx))
    d = 2.0 * math.hypot(cx, cy)
    row = {
        "candidate_id": candidate_id,
        "role": role,
        "rationale": rationale,
        "source_anchor_ids": sources,
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
    identity = geometry_identity(row)
    row["geometry_identity"] = identity
    row["exact_geometry_hash_sha256"] = sha256_obj(identity)
    return row


def materialize_candidates() -> list[dict]:
    # H1B-0 supplied abstract directions, not coordinates.  This is a fixed,
    # non-optimizing materialization: five rows, ordered by the authorized
    # A-E roles, using only active bounds and half-grid centers.
    return [
        candidate_row(
            "H1B1_A_LOWER_COMPATIBLE_EDGE",
            "A_lower_compatible_phase_edge_extension",
            "Lower active-family endpoint from the low-phase/038 direction; no search or optimization.",
            ["LPML_R2_LOW_PHASE_AND_SIX_BIN_COVERAGE_024", "LPML_R1_GLOBAL_SOBOL_038"],
            108, 106, 98, 98.0, 1.0,
        ),
        candidate_row(
            "H1B1_B_UPPER_COMPATIBLE_EDGE",
            "B_upper_compatible_phase_edge_extension",
            "Upper active-family endpoint from the high-phase/boundary direction; center fixed on the half-grid.",
            ["LPML_R2_HIGH_UNCERTAINTY_007", "LPML_R2_BOUNDARY_AND_HIGH_GRADIENT_054"],
            112, 110, 102, 101.5, 1.5,
        ),
        candidate_row(
            "H1B1_C_J1_SIDE_CONTRAST",
            "C_J1_side_directed_contrast",
            "Keep the 038 center and J2 dimensions while changing J1_side to the lower legal contrast.",
            ["LPML_R1_GLOBAL_SOBOL_038"],
            108, 109, 100, 101.5, 1.0,
        ),
        candidate_row(
            "H1B1_D_D_PSI_CONTRAST",
            "D_D_Psi_directed_contrast",
            "Keep the 126 lateral family and move the center deterministically toward lower D and positive Psi.",
            ["LPML_R1_GLOBAL_SOBOL_126"],
            111, 110, 101, 99.5, 1.5,
        ),
        candidate_row(
            "H1B1_E_INTERIOR_PROJECTOR_CONTROL",
            "E_interior_projector_preserving_robustness_control",
            "Interior dimension midpoint between 038 and 126 at the 038 half-grid center.",
            ["LPML_R1_GLOBAL_SOBOL_038", "LPML_R1_GLOBAL_SOBOL_126"],
            111, 109, 101, 101.5, 1.0,
        ),
    ]


def legality(candidate: dict, bounds: dict, anchor_keys: set[tuple], seen: set[str]) -> dict:
    j = integer(candidate["J1_side_nm"])
    l = integer(candidate["J2_length_nm"])
    w = integer(candidate["J2_width_nm"])
    cx = float(candidate["J2_center_x_nm"])
    cy = float(candidate["J2_center_y_nm"])
    d = float(candidate["D_nm"])
    psi = float(candidate["Psi_deg"])
    direct = d - max(j, w)
    periodic_x = PERIOD_NM - 2.0 * abs(cx) - max(j, w)
    periodic_y = PERIOD_NM - 2.0 * abs(cy) - max(w, l)
    key = (j, l, w, round(cx, 9), round(cy, 9))
    checks = {
        "H_global_550": candidate["H_global_nm"] == H_GLOBAL_NM and candidate["J1_H_nm"] == H_GLOBAL_NM and candidate["J2_H_nm"] == H_GLOBAL_NM,
        "period_432": candidate["period_nm"] == [PERIOD_NM, PERIOD_NM],
        "native_material": candidate["material_contract"] == MATERIAL,
        "integer_lateral_dimensions": all(float(candidate[k]).is_integer() for k in ("J1_side_nm", "J2_length_nm", "J2_width_nm")),
        "half_grid_center": all(abs(2.0 * z - round(2.0 * z)) < 1e-9 for z in (cx, cy)),
        "within_active_bounds": (
            bounds["ranges"]["J1_side_nm"][0] <= j <= bounds["ranges"]["J1_side_nm"][1]
            and bounds["ranges"]["J2_length_nm"][0] <= l <= bounds["ranges"]["J2_length_nm"][1]
            and bounds["ranges"]["J2_width_nm"][0] <= w <= bounds["ranges"]["J2_width_nm"][1]
            and bounds["ranges"]["D_nm"][0] <= d <= bounds["ranges"]["D_nm"][1]
            and bounds["ranges"]["Psi_deg"][0] <= psi <= bounds["ranges"]["Psi_deg"][1]
        ),
        "direct_gap_ge_60": direct >= MANUFACTURING_GAP_NM,
        "periodic_gap_ge_60": min(periodic_x, periodic_y) >= MANUFACTURING_GAP_NM,
        "cell_containment": cx + max(j, l) / 2.0 < PERIOD_NM / 2.0 and abs(cy) + max(w, l) / 2.0 < PERIOD_NM / 2.0,
        "no_overlap": direct > 0.0,
        "exact_hash_unique_in_probe": candidate["exact_geometry_hash_sha256"] not in seen,
        "lateral_identity_not_anchor": key not in anchor_keys,
    }
    return {"pass": all(checks.values()), "checks": checks, "direct_gap_nm": direct, "periodic_gap_x_nm": periodic_x, "periodic_gap_y_nm": periodic_y, "identity_key": key}


def build_manifest() -> dict:
    if current_branch() != TARGET_BRANCH:
        raise RuntimeError(f"HARD_GATE_WRONG_BRANCH:{current_branch()}")
    head = current_head()
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ACCEPTED_H1B0_HEAD, head],
        cwd=ROOT,
        capture_output=True,
    )
    if ancestry.returncode != 0:
        raise RuntimeError(f"HARD_GATE_UNEXPECTED_H1B0_PROVENANCE:{head}")
    proposal = read_json(PROPOSAL)
    hypotheses = read_json(HYPOTHESES)
    h1a = read_json(H1A_FINAL)
    ranking = read_csv(H1B0_RANKING)
    h550 = next((r for r in ranking if float(r["H_global_nm"]) == H_GLOBAL_NM), None)
    if proposal.get("status") != "PROPOSED_ONLY" or proposal.get("solver_contract", {}).get("new_fdtd") != 0:
        raise RuntimeError("HARD_GATE_H1B0_PROPOSAL_STATUS")
    if proposal.get("proposed_budget", {}).get("full_dimer_geometry_cases") != MAX_GEOMETRIES or proposal.get("proposed_budget", {}).get("formal_x_y_subruns") != MAX_SUBRUNS:
        raise RuntimeError("HARD_GATE_H1B0_BUDGET_MISMATCH")
    if h1a.get("status") != "COMPLETE_ANALYSIS" or h1a.get("solver_subruns_entered") != 48 or h1a.get("solver_subruns_accepted") != 48 or h1a.get("solver_subruns_quarantined") != 0 or h1a.get("H500_scheduled") is not False:
        raise RuntimeError("HARD_GATE_H1A_AUTHORITATIVE_EVIDENCE")
    if h550 is None:
        raise RuntimeError("HARD_GATE_H1B0_H550_RANKING")
    anchors, _ = H1A.load_anchors()
    anchor_keys = {anchor_key(a) for a in anchors}
    bounds = read_json(BOUNDS)
    candidates = materialize_candidates()
    seen: set[str] = set()
    for candidate in candidates:
        audit = legality(candidate, bounds, anchor_keys, seen)
        candidate["legality"] = audit
        if not audit["pass"]:
            raise RuntimeError(f"HARD_STOP_PROPOSAL_CONFLICT:{candidate['candidate_id']}:{audit}")
        seen.add(candidate["exact_geometry_hash_sha256"])
    if len(candidates) != MAX_GEOMETRIES or len(seen) != MAX_GEOMETRIES:
        raise RuntimeError("HARD_GATE_EXACTLY_FIVE_CANDIDATES")
    contract = H1A.physical_contract(head)
    scheduler_path = ROOT / "scripts/apcd_global_fdtd_slot_v1.py"
    scheduler_log = subprocess.check_output(["git", "log", "-1", "--format=%H %s", "--", "scripts/apcd_global_fdtd_slot_v1.py"], cwd=ROOT, text=True).strip()
    live = SLOT.live_job_snapshot()
    payload = {
        "schema": "LP_GLOBAL_H_H1B1_CANDIDATE_MANIFEST_V1",
        "stage": "H1B-1",
        "status": "FROZEN_READY",
        "remote_host": socket.gethostname(),
        "worktree": str(ROOT),
        "branch": current_branch(),
        "head": head,
        "accepted_h1b0_head": ACCEPTED_H1B0_HEAD,
        "proposal_mode": "H1B0_ABSTRACT_DETERMINISTIC_MATERIALIZATION",
        "proposal_sha256": sha256_file(PROPOSAL),
        "hypotheses_sha256": sha256_file(HYPOTHESES),
        "h1b0_ranking_sha256": sha256_file(H1B0_RANKING),
        "h1b0_anchor_response_sha256": sha256_file(H1B0_ANCHOR_RESPONSE),
        "h1a_final_sha256": sha256_file(H1A_FINAL),
        "bounds_contract_sha256": sha256_file(BOUNDS),
        "scheduler_path": str(scheduler_path),
        "scheduler_sha256": sha256_file(scheduler_path),
        "scheduler_provenance_commit": scheduler_log,
        "solver_authorization": {"approved_new_geometries": MAX_GEOMETRIES, "approved_new_subruns": MAX_SUBRUNS, "H_global_nm_only": H_GLOBAL_NM, "polarizations": list(POLARIZATIONS), "H500_scheduled": False},
        "physical_contract": contract,
        "physical_contract_sha256": sha256_obj(contract),
        "baseline_H550": {"compatible_span_deg": BASELINE_COMPATIBLE_SPAN_DEG, "max_compatible_pair_deg": float(h550["max_projector_compatible_pairwise_separation_deg"]), "sector_gap_deg": float(h550["sector_gap_deg"]), "compatible_error_threshold": OLD_COMPATIBLE_ERROR_MAX},
        "pre_execution_live_snapshot": live,
        "global_capacity": SLOT.GLOBAL_CAPACITY,
        "max_active_fdtd_per_branch": SLOT.MAX_ACTIVE_FDTD_PER_BRANCH,
        "processes_per_job": SLOT.PROCESSES_PER_JOB,
        "threads_per_job": SLOT.THREADS_PER_JOB,
        "candidates": candidates,
    }
    payload["freeze_sha256"] = sha256_obj(payload)
    return payload


def case_identity(candidate: dict, pol: str, head: str) -> dict:
    return {"candidate_id": candidate["candidate_id"], "exact_geometry_hash_sha256": candidate["exact_geometry_hash_sha256"], "geometry_identity": candidate["geometry_identity"], "H_global_nm": H_GLOBAL_NM, "polarization": pol, "material_contract": MATERIAL, "period_nm": [PERIOD_NM, PERIOD_NM], "builder_version": H1A.BUILDER_VERSION, "builder_commit": head, "formal_extraction_convention": H1A.EXTRACTION_CONVENTION}


def case_name(candidate: dict, pol: str) -> str:
    return f"H1B1_{candidate['candidate_id']}_H550_P{pol}"


def accounting_path() -> Path:
    return OUT / "h1b1_solver_accounting.json"


def load_accounting() -> dict:
    return read_json(accounting_path()) if accounting_path().exists() else {"solver_entries": [], "cases": []}


def write_accounting(payload: dict) -> None:
    atomic_json(accounting_path(), payload)


def initialize_accounting(manifest: dict) -> dict:
    old = load_accounting() if accounting_path().exists() else {}
    planned = [{"case_id": case_name(c, p), "candidate_id": c["candidate_id"], "geometry_hash_sha256": c["exact_geometry_hash_sha256"], "H_global_nm": H_GLOBAL_NM, "polarization": p, "planned": True, "attempted": False, "solver_entered": False, "accepted": False, "phase_only": False, "quarantined": False, "recovered": False, "unentered_infrastructure_failure": False} for c in manifest["candidates"] for p in POLARIZATIONS]
    if old.get("manifest_freeze_sha256") not in (None, manifest["freeze_sha256"]):
        if old.get("solver_entries"):
            raise RuntimeError("HARD_GATE_ACCOUNTING_MANIFEST_MISMATCH_AFTER_ENTRY")
    payload = {"schema": "LP_GLOBAL_H_H1B1_SOLVER_ACCOUNTING_V1", "stage": "H1B-1", "manifest_freeze_sha256": manifest["freeze_sha256"], "solver_budget_planned": MAX_SUBRUNS, "H_global_nm_only": H_GLOBAL_NM, "H500_scheduled": False, "cases": old.get("cases", planned), "solver_entries": old.get("solver_entries", []), "status": old.get("status", "PLANNED")}
    if len(payload["cases"]) != MAX_SUBRUNS:
        raise RuntimeError("HARD_GATE_ACCOUNTING_CASE_COUNT")
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


def resource_and_setup_gate(fdtd, candidate: dict, pol: str) -> tuple[dict, dict]:
    resource = H1A.resource_gate(fdtd)
    gate = H1A.setup_gate(fdtd, candidate, pol, H_GLOBAL_NM)
    return resource, gate


def next_attempt(case_dir: Path, case_id: str) -> tuple[str, Path, Path]:
    old = sorted(case_dir.glob("attempt_provenance*.json"))
    nums = []
    for p in old:
        m = re.search(r"_attempt_(\d{3})\.json$", p.name)
        nums.append(int(m.group(1)) if m else 1)
    n = max(nums, default=0) + 1
    aid = f"{case_id}_attempt_{n:03d}"
    prov = case_dir / ("attempt_provenance.json" if n == 1 else f"attempt_provenance_attempt_{n:03d}.json")
    return aid, prov, case_dir / f"{aid}_pre.fsp"


def run_case(runtime, candidate: dict, pol: str, manifest: dict, scheduler, entered: list[dict]) -> dict:
    head = manifest["head"]
    identity = case_identity(candidate, pol, head)
    identity_hash = sha256_obj(identity)
    cid = case_name(candidate, pol)
    case_dir = RUNTIME / "cases" / cid
    case_dir.mkdir(parents=True, exist_ok=True)
    recovered = checkpoint_result(case_dir, identity)
    if recovered:
        update_case(cid, {"attempted": True, "solver_entered": True, "accepted": True, "recovered": True, "status": "ACCEPTED"})
        return recovered
    if any(x.get("case_id") == cid and x.get("solver_entered") is True for x in entered):
        result = {"status": "QUARANTINED_ENTERED_NO_RECOVERY", "solver_entered": True, "case_id": cid, "candidate_id": candidate["candidate_id"], "geometry_hash_sha256": candidate["exact_geometry_hash_sha256"], "error": "entered=true exact H1B1 case has no accepted checkpoint; replay forbidden"}
        update_case(cid, {"attempted": True, "solver_entered": True, "quarantined": True, "status": result["status"]})
        return result
    attempt_id, provenance_path, pre_fsp = next_attempt(case_dir, cid)
    record = {"schema": "LP_GLOBAL_H_H1B1_ATTEMPT_PROVENANCE_V1", "case_id": cid, "attempt_id": attempt_id, "candidate_id": candidate["candidate_id"], "case_identity": identity, "case_identity_sha256": identity_hash, "branch": current_branch(), "worktree": str(ROOT), "H_global_nm": H_GLOBAL_NM, "polarization": pol, "solver_entered": False, "entered_solver": False, "slot_acquired": False, "processes": SLOT.PROCESSES_PER_JOB, "threads": SLOT.THREADS_PER_JOB, "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "physical_contract_sha256": manifest["physical_contract_sha256"]}
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
        lease = scheduler.acquire_wait(branch=TARGET_BRANCH, worktree=str(ROOT), task_id="H1B1_TARGETED_EXPANSION", case_uid=cid, pid=os.getpid(), metadata={"task_class": "H1B1_FORMAL_FDTD", "attempt_id": attempt_id, "polarization": pol, "H_global_nm": H_GLOBAL_NM}, timeout_s=21600.0, poll_s=15.0)
        record.update({"slot_acquired": True, "slot_id": lease.slot_id, "slot_acquire_time": lease.record.get("slot_acquire_time"), "concurrent_peer_branch": lease.record.get("concurrent_peer_branch", []), "admission_snapshot": lease.record.get("admission_snapshot"), "status": "SLOT_ACQUIRED"})
        lease.start_heartbeat()
        atomic_json(provenance_path, record)
        f = runtime.lumapi.FDTD(hide=getattr(runtime, "hide_gui", True))
        f.load(str(pre_fsp))
        resource, gate = resource_and_setup_gate(f, candidate, pol)
        record.update({"resource_gate": resource, "configuration_gate": gate, "status": "PREFLIGHT_GATED"})
        atomic_json(provenance_path, record)
        if not resource.get("pass") or not gate.get("pass"):
            record.update({"status": "QUARANTINED_PREFLIGHT_GATE", "quarantined": True, "error": "resource or configuration gate failed"})
            update_case(cid, {"status": record["status"], "quarantined": True})
            return record
        if len({x.get("case_id") for x in entered}) >= MAX_SUBRUNS:
            raise RuntimeError("HARD_GATE_H1B1_ENTERED_BUDGET")
        entered_utc = dt.datetime.now(dt.timezone.utc).isoformat()
        lease.mark_solver_entered(entered_utc)
        entry = {"case_id": cid, "attempt_id": attempt_id, "candidate_id": candidate["candidate_id"], "geometry_hash_sha256": candidate["exact_geometry_hash_sha256"], "case_identity_sha256": identity_hash, "H_global_nm": H_GLOBAL_NM, "polarization": pol, "solver_entered": True, "entered_solver": True, "entered_utc": entered_utc, "slot_id": lease.slot_id, "pre_fsp_sha256": record["pre_fsp_sha256"], "physical_contract_sha256": manifest["physical_contract_sha256"], "pid": os.getpid()}
        entered.append(entry)
        record.update({"solver_entered": True, "entered_solver": True, "entered_utc": entered_utc, "solver_start": entered_utc, "status": "ENTERED"})
        update_case(cid, {"solver_entered": True, "status": "ENTERED", "slot_id": lease.slot_id}, entry)
        atomic_json(provenance_path, record)
        f.run()
        solver_completed = True
        completed = dt.datetime.now(dt.timezone.utc).isoformat()
        lease.release("SOLVER_COMPLETED", completed)
        lease = None
        record.update({"solver_complete": completed, "slot_release_time": dt.datetime.now(dt.timezone.utc).isoformat(), "status": "SOLVER_COMPLETED"})
        rows, grid = RUNNER.extract_broadband(f)
        checkpoint = {"schema": "LP_GLOBAL_H_H1B1_CHECKPOINT_V1", "status": "ACCEPTED", "case_id": cid, "candidate_id": candidate["candidate_id"], "polarization": pol, "case_identity": identity, "case_identity_sha256": identity_hash, "geometry": candidate, "H_global_nm": H_GLOBAL_NM, "physical_contract_sha256": manifest["physical_contract_sha256"], "setup": setup, "resource_gate": resource, "configuration_gate": gate, "rows": rows, "grid_audit": grid}
        atomic_json(case_dir / "checkpoint.json", checkpoint)
        record.update({"status": "ACCEPTED", "rows": rows, "grid_audit": grid, "checkpoint_path": str(case_dir / "checkpoint.json"), "checkpoint_sha256": sha256_file(case_dir / "checkpoint.json")})
        update_case(cid, {"status": "ACCEPTED", "accepted": True}, None)
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
    J = np.array([[complex_value(x["rows"][0], "weighted_Ex_real", "weighted_Ex_imag"), complex_value(y["rows"][0], "weighted_Ex_real", "weighted_Ex_imag")], [complex_value(x["rows"][0], "weighted_Ey_real", "weighted_Ey_imag"), complex_value(y["rows"][0], "weighted_Ey_real", "weighted_Ey_imag")]])
    return {"source_class": "H1B1_NEW_SOLVER_XY_FORMAL", "physics_scope": "FULL_JONES_H1B1_PHYSICS", "Jones_complete": True, "candidate_id": candidate["candidate_id"], "authoritative_id": candidate["candidate_id"], "anchor_role": candidate["role"], "geometry_hash_sha256": candidate["exact_geometry_hash_sha256"], "H_global_nm": H_GLOBAL_NM, "J1_side_nm": candidate["J1_side_nm"], "J2_length_nm": candidate["J2_length_nm"], "J2_width_nm": candidate["J2_width_nm"], "D_nm": candidate["D_nm"], "Psi_deg": candidate["Psi_deg"], "x_case_id": x.get("case_id"), "y_case_id": y.get("case_id"), "x_checkpoint_sha256": x.get("checkpoint_sha256"), "y_checkpoint_sha256": y.get("checkpoint_sha256"), **RUNNER.metrics(J)}


def phase_only_row(candidate: dict, x: dict) -> dict:
    txx = complex_value(x["rows"][0], "weighted_Ex_real", "weighted_Ex_imag")
    return {"source_class": "H1B1_X_FORMAL_ONLY", "physics_scope": "PHASE_ONLY_H1B1_PHYSICS", "Jones_complete": False, "projector_eligible": False, "candidate_id": candidate["candidate_id"], "authoritative_id": candidate["candidate_id"], "anchor_role": candidate["role"], "geometry_hash_sha256": candidate["exact_geometry_hash_sha256"], "H_global_nm": H_GLOBAL_NM, "phase_wrapped_deg": float(np.degrees(np.angle(txx)) % 360.0), "Txx": abs(txx) ** 2, "selected_throughput_Txx": abs(txx) ** 2, "txx_real": txx.real, "txx_imag": txx.imag, "x_case_id": x.get("case_id"), "x_checkpoint_sha256": x.get("checkpoint_sha256")}


def old_h550_rows() -> list[dict]:
    rows = []
    for row in read_csv(H1A_FULL):
        if number(row.get("H_global_nm")) != H_GLOBAL_NM or str(row.get("Jones_complete", "")).upper() not in {"TRUE", "1"}:
            continue
        q = dict(row)
        q.update({"source_class": "H1A_EXISTING_AUTHORITATIVE", "candidate_id": row.get("authoritative_id"), "physics_scope": "FULL_JONES_H1A_PHYSICS", "phase_wrapped_deg": number(row.get("phase_wrapped_deg")), "projector_error_apcd_v1": number(row.get("projection_error_apcd_v1") or row.get("projector_error_apcd_v1")), "selected_throughput_Txx": number(row.get("Txx"))})
        q["projector_compatible"] = q["projector_error_apcd_v1"] is not None and q["projector_error_apcd_v1"] <= OLD_COMPATIBLE_ERROR_MAX + 1e-12
        rows.append(q)
    if len(rows) != 6:
        raise RuntimeError(f"HARD_GATE_H1A_H550_MERGE_COUNT:{len(rows)}")
    return rows


def phase_span(values: list[float]) -> dict:
    return H0.circular_phase_span([float(x) for x in values]) if values else {"circular_coverage_deg": 0.0, "raw_min_deg": None, "raw_max_deg": None}


def max_pairs(rows: list[dict]) -> tuple[float, list[str] | None]:
    best = (0.0, None)
    for a, b in itertools.combinations(rows, 2):
        sep = abs(H1A.circ_diff(float(a["phase_wrapped_deg"]) % 360.0, float(b["phase_wrapped_deg"]) % 360.0))
        if sep > best[0]:
            best = (sep, [str(a.get("candidate_id") or a.get("authoritative_id")), str(b.get("candidate_id") or b.get("authoritative_id"))])
    return best


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
    old = old_h550_rows()
    merged = old + full_new
    compatible = [r for r in merged if bool(r.get("projector_compatible")) or (number(r.get("projector_error_apcd_v1")) is not None and number(r.get("projector_error_apcd_v1")) <= OLD_COMPATIBLE_ERROR_MAX + 1e-12)]
    for row in merged:
        error = number(row.get("projection_error_apcd_v1") or row.get("projector_error_apcd_v1"))
        row["projector_error_apcd_v1"] = error
        row["projector_compatible"] = error is not None and error <= OLD_COMPATIBLE_ERROR_MAX + 1e-12
    compatible = [r for r in merged if r["projector_compatible"]]
    raw = phase_span([float(r["phase_wrapped_deg"]) % 360.0 for r in merged])
    comp_span = phase_span([float(r["phase_wrapped_deg"]) % 360.0 for r in compatible])
    max_pair, pair_ids = max_pairs(compatible)
    old_compatible = [r for r in old if r["projector_compatible"]]
    old_phases = [float(r["phase_wrapped_deg"]) % 360.0 for r in old_compatible]
    old_min, old_max = min(old_phases), max(old_phases)
    effects = []
    for row in full_new:
        phi = float(row["phase_wrapped_deg"]) % 360.0
        to_old = [abs(H1A.circ_diff(phi, p)) for p in old_phases]
        effect = dict(next(c for c in manifest["candidates"] if c["candidate_id"] == row["candidate_id"]))
        effects.append({"candidate_id": row["candidate_id"], "role": row["anchor_role"], "geometry_hash_sha256": row["geometry_hash_sha256"], "phi_deg": phi, "projector_error_apcd_v1": row["projector_error_apcd_v1"], "selected_throughput_Txx": row.get("Txx"), "projector_compatible": row["projector_compatible"], "extends_lower_edge_vs_old_compatible": phi < old_min, "extends_upper_edge_vs_old_compatible": phi > old_max, "max_pair_separation_to_old_compatible_deg": max(to_old, default=0.0), "exact_5d": {k: effect[k] for k in ("J1_side_nm", "J2_length_nm", "J2_width_nm", "D_nm", "Psi_deg")}, "legality": effect["legality"]})
    delta = float(comp_span.get("circular_coverage_deg", 0.0)) - BASELINE_COMPATIBLE_SPAN_DEG
    flag60 = max_pair >= 60.0
    flag120 = float(comp_span.get("circular_coverage_deg", 0.0)) >= 120.0
    if len(full_new) < MAX_GEOMETRIES:
        verdict = "H1B1_INCONCLUSIVE"
        route = "INSUFFICIENT_ACCEPTED_FULL_JONES_EVIDENCE"
    elif flag60:
        verdict = "H1B1_TARGETED_EXPANSION_REACHED_60_SECTOR"
        route = "SYSTEMATIC_FIXED_H550_MANIFOLD_MAPPING"
    elif delta > 0.0:
        verdict = "H1B1_TARGETED_EXPANSION_IMPROVED_BUT_BELOW_60"
        route = "MINIMAL_FULL_DIMER_REFINEMENT_OR_CONSTITUENT_DIAGNOSTIC"
    else:
        verdict = "H1B1_TARGETED_EXPANSION_NO_USEFUL_GAIN"
        route = "TARGETED_CONSTITUENT_RECONNAISSANCE"
    span = {"baseline_H1A_H550_compatible_span_deg": BASELINE_COMPATIBLE_SPAN_DEG, "new_merged_H550_raw_span_deg": raw.get("circular_coverage_deg", 0.0), "new_merged_H550_projector_compatible_count": len(compatible), "new_merged_H550_projector_compatible_span_deg": comp_span.get("circular_coverage_deg", 0.0), "delta_compatible_span_deg": delta, "max_compatible_pair_separation_deg": max_pair, "new_sector_gap_deg": 60.0 - max_pair, "max_compatible_pair_ids": pair_ids, "old_H1A_H550_count": len(old), "new_H1B1_full_jones_count": len(full_new), "merged_H550_count": len(merged), "FLAG_60_SECTOR": flag60, "FLAG_120_ML_RESTART": flag120}
    return {"full_new": full_new, "phase_new": phase_new, "merged": merged, "effects": effects, "span": span, "verdict": verdict, "route": route}


def write_analysis(manifest: dict, accounting: dict, results: dict[str, dict], analysis: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "h1b1_full_jones.csv", analysis["full_new"])
    write_csv(OUT / "h1b1_phase_only.csv", analysis["phase_new"])
    write_csv(OUT / "h1b1_h550_merged_manifold.csv", analysis["merged"])
    write_csv(OUT / "h1b1_candidate_effects.csv", analysis["effects"])
    atomic_json(OUT / "h1b1_span_comparison.json", analysis["span"])
    h500 = read_csv(H1A_FULL)
    h500_rows = [r for r in h500 if number(r.get("H_global_nm")) == 500.0]
    accounting["status"] = "COMPLETE_ANALYSIS"
    accounting["solver_subruns_entered"] = len(accounting.get("solver_entries", []))
    accounting["solver_subruns_accepted"] = sum(1 for r in accounting.get("cases", []) if r.get("accepted"))
    accounting["solver_subruns_quarantined"] = sum(1 for r in accounting.get("cases", []) if r.get("quarantined"))
    accounting["phase_only_cases"] = sum(1 for r in accounting.get("cases", []) if r.get("phase_only"))
    accounting["recovered_cases"] = sum(1 for r in accounting.get("cases", []) if r.get("recovered"))
    accounting["unentered_infrastructure_failures"] = sum(1 for r in accounting.get("cases", []) if r.get("unentered_infrastructure_failure"))
    accounting["H500_replay_check"] = {"scheduled": False, "authoritative_rows": len(h500_rows)}
    write_accounting(accounting)
    final = {"schema": "LP_GLOBAL_H_H1B1_FINAL_V1", "stage": "H1B-1", "status": "COMPLETE_ANALYSIS", "branch": current_branch(), "head": current_head(), "manifest_freeze_sha256": manifest["freeze_sha256"], "solver_accounting": accounting, "verdict": analysis["verdict"], "recommended_next_route": analysis["route"], "span_comparison": analysis["span"], "candidate_effects": analysis["effects"], "flags": {"FLAG_60_SECTOR": analysis["span"]["FLAG_60_SECTOR"], "FLAG_120_ML_RESTART": analysis["span"]["FLAG_120_ML_RESTART"]}, "H500_replay_check": {"scheduled": False, "authoritative_rows": len(h500_rows)}, "artifacts": {"candidate_manifest": str(OUT / "h1b1_candidate_manifest.json"), "solver_accounting": str(OUT / "h1b1_solver_accounting.json"), "full_jones": str(OUT / "h1b1_full_jones.csv"), "phase_only": str(OUT / "h1b1_phase_only.csv"), "merged_manifold": str(OUT / "h1b1_h550_merged_manifold.csv"), "candidate_effects": str(OUT / "h1b1_candidate_effects.csv"), "span_comparison": str(OUT / "h1b1_span_comparison.json"), "final": str(OUT / "h1b1_final.json"), "summary": str(OUT / "h1b1_summary.md")}}
    atomic_json(OUT / "h1b1_final.json", final)
    lines = ["# Stage H1B-1 Targeted Full-Dimer Expansion", "", f"- Status: `{final['status']}`", f"- Verdict: `{analysis['verdict']}`", f"- Route recommendation: `{analysis['route']}`", f"- Branch / HEAD: `{final['branch']}` / `{final['head']}`", f"- Planned / entered / accepted: `{MAX_SUBRUNS}` / `{accounting.get('solver_subruns_entered', 0)}` / `{accounting.get('solver_subruns_accepted', 0)}`", "", "## Frozen contract", "", "- H_global = J1_H = J2_H = 550 nm; x+y only; period 432 nm; native material APCD_TIO2_NATIVE_M1.", "- H500 is authoritative control only and was not scheduled.", "- Full Jones uses the existing weighted full-period complex G0 extraction and does not assume txy=tyx.", "", "## H550 comparison", "", f"- Old H1A compatible span: `{BASELINE_COMPATIBLE_SPAN_DEG:.12f}` deg", f"- Merged raw span: `{analysis['span']['new_merged_H550_raw_span_deg']:.12f}` deg", f"- Merged compatible count / span: `{analysis['span']['new_merged_H550_projector_compatible_count']}` / `{analysis['span']['new_merged_H550_projector_compatible_span_deg']:.12f}` deg", f"- Delta compatible span: `{analysis['span']['delta_compatible_span_deg']:.12f}` deg", f"- Max compatible pair / sector gap: `{analysis['span']['max_compatible_pair_separation_deg']:.12f}` / `{analysis['span']['new_sector_gap_deg']:.12f}` deg", "", "## Flags", "", f"- FLAG_60_SECTOR: `{analysis['span']['FLAG_60_SECTOR']}`", f"- FLAG_120_ML_RESTART: `{analysis['span']['FLAG_120_ML_RESTART']}`; not an automatic ML start.", "", "## Candidate effects", ""]
    lines += [f"- {r['candidate_id']}: phi={r['phi_deg']:.9f} deg, projector_error={r['projector_error_apcd_v1']}, compatible={r['projector_compatible']}, lower_extension={r['extends_lower_edge_vs_old_compatible']}, upper_extension={r['extends_upper_edge_vs_old_compatible']}" for r in analysis["effects"]]
    lines += ["", "## Artifacts", ""] + [f"- {k}: `{v}`" for k, v in final["artifacts"].items()]
    (OUT / "h1b1_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (REPORT / "h1b1_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    atomic_json(REPORT / "h1b1_final.json", final)


def make_runtime():
    config = RUNNER.load_runtime_config(str(ROOT / "configs/runtime.yaml"))
    lumapi = RUNNER.import_lumapi(config)
    return type("RuntimeProxy", (), {"lumapi": lumapi, "hide_gui": getattr(config, "hide_gui", True)})()


def execute(manifest: dict) -> int:
    accounting = initialize_accounting(manifest)
    OUT.mkdir(parents=True, exist_ok=True)
    runtime = make_runtime()
    scheduler = SLOT.GlobalSlotScheduler(SLOT_REGISTRY)
    entered = list(accounting.get("solver_entries", []))
    results: dict[str, dict] = {}
    for candidate in manifest["candidates"]:
        for pol in POLARIZATIONS:
            result = run_case(runtime, candidate, pol, manifest, scheduler, entered)
            results[case_name(candidate, pol)] = result
    analysis = analyze(manifest, results)
    write_analysis(manifest, load_accounting(), results, analysis)
    print(json.dumps({"status": "COMPLETE_ANALYSIS", "verdict": analysis["verdict"], "entered": len(entered), "accepted_full_jones": len(analysis["full_new"]), "span": analysis["span"]}, indent=2, ensure_ascii=False, default=str))
    return 0


def preflight() -> int:
    manifest = build_manifest()
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    path = OUT / "h1b1_candidate_manifest.json"
    if path.exists():
        old = read_json(path)
        if old.get("freeze_sha256") != manifest["freeze_sha256"]:
            old_accounting = load_accounting()
            if old_accounting.get("solver_entries"):
                raise RuntimeError("HARD_GATE_EXISTING_FROZEN_MANIFEST_MISMATCH_AFTER_ENTRY")
            # The first preflight may be invalidated by a production
            # scheduler provenance fix.  Before any solver entry, refreshing
            # the freeze is safe and leaves the old manifest in Git-untracked
            # runtime history only.
    atomic_json(path, manifest)
    initialize_accounting(manifest)
    atomic_json(REPORT / "h1b1_pre_execution_audit.json", {"status": "PASS", "manifest_freeze_sha256": manifest["freeze_sha256"], "candidate_count": len(manifest["candidates"]), "formal_subrun_count": MAX_SUBRUNS, "H_global_nm": H_GLOBAL_NM, "H500_scheduled": False, "live_snapshot": manifest["pre_execution_live_snapshot"], "scheduler_provenance": {"path": manifest["scheduler_path"], "sha256": manifest["scheduler_sha256"], "commit": manifest["scheduler_provenance_commit"]}})
    print(json.dumps({"status": "FROZEN_READY", "freeze_sha256": manifest["freeze_sha256"], "candidates": [{"candidate_id": c["candidate_id"], "geometry_hash_sha256": c["exact_geometry_hash_sha256"], "role": c["role"], "D_nm": c["D_nm"], "Psi_deg": c["Psi_deg"], "legality": c["legality"]} for c in manifest["candidates"]], "live_snapshot": manifest["pre_execution_live_snapshot"]}, indent=2, ensure_ascii=False, default=str))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if bool(args.preflight_only) == bool(args.execute):
        raise SystemExit("select exactly one mode")
    if args.preflight_only:
        return preflight()
    manifest_path = OUT / "h1b1_candidate_manifest.json"
    if not manifest_path.exists():
        raise SystemExit("HARD_GATE_PRE_EXECUTION_MANIFEST_MISSING")
    manifest = read_json(manifest_path)
    if manifest.get("status") != "FROZEN_READY" or manifest.get("freeze_sha256") != sha256_obj({k: v for k, v in manifest.items() if k != "freeze_sha256"}):
        raise SystemExit("HARD_GATE_FROZEN_MANIFEST_INVALID")
    return execute(manifest)


if __name__ == "__main__":
    raise SystemExit(main())
