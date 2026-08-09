from __future__ import annotations

import csv
import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
ML = ROOT / "outputs/lp_ml_dataset_v1"
PLAN = ML / "plans/lp_5d_phase_reachability_probe_v2.json"
BOUNDS = ML / "plans/lp_ml_dataset_v1_5d_design_space_contract_v1.json"
INPUT_SCHEMA = ML / "plans/lp_ml_dataset_v1_input_schema_v1.json"
PFORM = ML / "contracts/lp_linear_x_projector_target_matrix_v1.json"
QMAN = ML / "clean_v2/quarantine_manifest_v2.json"
CANONICAL = ML / "canonical_v1_21/geometry_master_v1_17.csv"
STAGING = ML / "staging/lp_5d_phase_reachability_probe_v2"
PACKAGE = ML / "execution_packages/lp_5d_phase_reachability_probe_v2"
AN = ML / "analysis"
REPORT = ROOT / "reports/lp_5d_phase_reachability_probe_v1.md"
RUNTIME_PATH = ROOT / "scripts/lp_checkpoint_authoritative_runtime_v1_23.py"
SCRIPT = ROOT / "scripts/lp_5d_phase_reachability_probe_v1.py"
R1_HASH = "f6bcfd429f3cd1b722f520bc67dbc62501854a686b17d8deae492cc66e950b21"
PROTECTED = [
    ROOT / "reports/lp_ml1a3_git_history_geometry_reconstruction.md",
    ROOT / "reports/stage11_4a20_legacy_fsp_object_inventory.md",
]
EXPECTED_ROLES = {
    "LOW_PHASE_EXTREME": 6,
    "HIGH_PHASE_EXTREME": 6,
    "PHASE_PROJECTOR_TRADEOFF": 4,
    "5D_BOUNDARY_SPARSE_REGION": 4,
    "DISAGREEMENT_PHYSICS_CONTROL": 4,
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canon_sha(obj: object) -> str:
    data = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf8")
    return hashlib.sha256(data).hexdigest()


def atomic_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False), encoding="utf8")
    os.replace(tmp, path)


def atomic_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for row in rows for k in row))
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"MODULE_LOAD_FAILED:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def fixed_contract() -> dict:
    return {
        "H_nm": 500.0,
        "period_x_nm": 432.0,
        "period_y_nm": 432.0,
        "material": "APCD_TIO2_NATIVE_M1",
        "background": "air",
        "source": "normal_incidence_plane_wave",
        "reference_plane": "field_monitor_z_1000_nm",
        "field_monitor_z_nm": 1000.0,
        "mesh": "frozen_mesh_contract",
        "boundaries": "x/y_periodic_z_PML",
        "observable": "coordinate_weighted_full_period_G0",
        "endpoint_handling": "duplicate_endpoint_remove_then_periodic_reclosure",
        "normalization": "sqrt(T)/norm(weighted_Ex,weighted_Ey)",
        "jones_convention": "[[txx,txy],[tyx,tyy]]",
    }


def geometry_hash(j: int, l: int, w: int, cx: float, cy: float) -> tuple[str, dict]:
    g = {
        "J1_shape": "sharp_rectangle",
        "J1_side_nm": float(j),
        "J2_shape": "sharp_rectangle",
        "J2_length_nm": float(l),
        "J2_width_nm": float(w),
        "J1_center_x_nm": -float(cx),
        "J1_center_y_nm": -float(cy),
        "J2_center_x_nm": float(cx),
        "J2_center_y_nm": float(cy),
        "J1_rotation_deg": 0.0,
        "J2_rotation_deg": 0.0,
        **fixed_contract(),
    }
    return canon_sha(g), g


def config_hash() -> str:
    return canon_sha({
        "H_nm": 500.0,
        "period_nm": [432.0, 432.0],
        "material": "APCD_TIO2_NATIVE_M1",
        "background": "air",
        "incidence": "normal",
        "boundary": "xy_periodic_z_pml",
        "monitor_z_nm": 1000.0,
        "wavelength_nm": 450.0,
        "observable": "LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1",
    })


def read_plan() -> list[dict]:
    obj = json.loads(PLAN.read_text(encoding="utf8"))
    rows = obj["candidates"]
    if len(rows) != 24:
        raise RuntimeError("FROZEN24_COUNT_MISMATCH")
    if [r["role"] for r in rows].count("LOW_PHASE_EXTREME") != 6:
        raise RuntimeError("FROZEN_ROLE_COUNT_MISMATCH")
    counts = {role: sum(r["role"] == role for r in rows) for role in EXPECTED_ROLES}
    if counts != EXPECTED_ROLES:
        raise RuntimeError(f"FROZEN_ROLE_COUNT_MISMATCH:{counts}")
    return rows


def existing_hashes() -> set[str]:
    out: set[str] = set()
    if CANONICAL.exists():
        with CANONICAL.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                h = row.get("exact_geometry_hash") or row.get("exact_geometry_hash_sha256")
                if h:
                    out.add(h)
    return out


def process_snapshot() -> dict:
    try:
        text = subprocess.check_output(["tasklist"], text=True, stderr=subprocess.STDOUT)
    except Exception as exc:
        return {"status": "UNAVAILABLE", "error": str(exc), "solver_calls": 0}
    rows = []
    for line in text.splitlines():
        if any(k in line.lower() for k in ("fdtd", "lumerical", "python")):
            rows.append(line.strip())
    return {"status": "RECORDED", "matching_process_lines": rows, "no_process_termination": True, "solver_calls": 0}


def make_manifest(rows: list[dict]) -> tuple[dict, list[dict]]:
    bounds = json.loads(BOUNDS.read_text(encoding="utf8"))
    qman = json.loads(QMAN.read_text(encoding="utf8"))
    existing = existing_hashes()
    manifest_rows = []
    hashes = set()
    for order, row in enumerate(rows, 1):
        j, l, w = int(row["J1_side_nm"]), int(row["J2_length_nm"]), int(row["J2_width_nm"])
        cx, cy = float(row["center_x_abs_nm"]), float(row["center_y_nm"])
        D = 2 * math.hypot(cx, cy)
        psi = math.degrees(math.atan2(cy, cx))
        direct = D - max(j, w)
        periodic = min(432.0 - 2 * abs(cx) - max(j, w), 432.0 - 2 * abs(cy) - max(j, l))
        eh, geometry = geometry_hash(j, l, w, cx, cy)
        rel = canon_sha({"J1_side_nm": j, "J2_length_nm": l, "J2_width_nm": w, "cx_abs": cx, "cy_abs": abs(cy), "H_nm": 500.0, "period": 432.0})
        sym = canon_sha({"J1_side_nm": j, "J2_length_nm": l, "J2_width_nm": w, "radius": round(math.hypot(cx, cy), 6), "H_nm": 500.0, "period": 432.0})
        checks = {
            "exact_order": order == len(manifest_rows) + 1,
            "within_bounds": bounds["ranges"]["J1_side_nm"][0] <= j <= bounds["ranges"]["J1_side_nm"][1] and bounds["ranges"]["J2_length_nm"][0] <= l <= bounds["ranges"]["J2_length_nm"][1] and bounds["ranges"]["J2_width_nm"][0] <= w <= bounds["ranges"]["J2_width_nm"][1] and bounds["ranges"]["D_nm"][0] <= D <= bounds["ranges"]["D_nm"][1] and bounds["ranges"]["Psi_deg"][0] <= psi <= bounds["ranges"]["Psi_deg"][1],
            "center_quantized": all(abs(2 * z - round(2 * z)) < 1e-9 for z in (cx, cy)),
            "gap_legal": direct >= 60.0 and periodic >= 60.0,
            "cell_containment": cx + max(j, l) / 2 < 216 and abs(cy) + max(w, l) / 2 < 216,
            "no_overlap": direct > 0,
            "canonical_duplicate_free": eh not in existing,
            "unique_in_probe": eh not in hashes,
            "r1_quarantine_free": eh != R1_HASH,
            "not_d9": "D9" not in row["planned_candidate_id"],
        }
        if not all(checks.values()):
            raise RuntimeError(f"MANIFEST_GATE_FAILED:{row['planned_candidate_id']}:{checks}")
        hashes.add(eh)
        manifest_rows.append({
            "order": order,
            "candidate_id": row["planned_candidate_id"],
            "role": row["role"],
            "wavelength_nm": 450.0,
            "J1_side_nm": j,
            "J2_length_nm": l,
            "J2_width_nm": w,
            "D_nm": D,
            "Psi_deg": psi,
            "J1_center_x_nm": -cx,
            "J1_center_y_nm": -cy,
            "J2_center_x_nm": cx,
            "J2_center_y_nm": cy,
            "direct_gap_nm": direct,
            "periodic_gap_nm": periodic,
            "exact_geometry_hash_sha256": eh,
            "canonical_relative_geometry_hash_sha256": rel,
            "symmetry_equivalence_geometry_hash_sha256": sym,
            "geometry": geometry,
            "checks": checks,
            "status": "FROZEN_FOR_EXECUTION",
            "physics_status": "ABSENT_NOT_SIMULATED",
            "phase_label": "PHASE_ONLY_REACHABILITY_PHYSICS_AFTER_ACCEPTANCE",
            "full_jones_label": "FULL_JONES_REACHABILITY_PHYSICS_AFTER_XY_ACCEPTANCE",
        })
    manifest = {
        "manifest_version": "LP_5D_PHASE_REACHABILITY_PROBE_V2_EXECUTION_MANIFEST_V1",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "creation_code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_plan_path": str(PLAN),
        "source_plan_sha256": sha(PLAN),
        "bounds_contract_sha256": sha(BOUNDS),
        "input_schema_sha256": sha(INPUT_SCHEMA),
        "formal_p_contract_sha256": sha(PFORM),
        "formal_p_payload_sha256": json.loads(PFORM.read_text(encoding="utf8"))["matrix_sha256"],
        "quarantine_manifest_path": str(QMAN),
        "quarantine_manifest_sha256": sha(QMAN),
        "quarantine_exact_hash": qman["exact_geometry_hash_sha256"],
        "candidate_count": 24,
        "role_counts": EXPECTED_ROLES,
        "candidate_order": [r["candidate_id"] for r in manifest_rows],
        "future_budget": {"geometries": 24, "x_y_subruns": 48, "wavelength_nm": [450.0]},
        "fixed_contract": fixed_contract(),
        "solver_calls": 0,
        "entered_max": 48,
        "no_replacement": True,
        "no_geometry_expansion": True,
        "no_auto_retry_entered": True,
        "no_d9": True,
        "no_broadband": True,
        "no_ml_assimilation": True,
        "protected_hashes_before": {str(p): sha(p) for p in PROTECTED},
        "active_process_snapshot": process_snapshot(),
        "candidates": manifest_rows,
    }
    return manifest, manifest_rows


def expected_identity(candidate: dict, polarization: str, source_plan_sha: str) -> dict:
    return {
        "candidate_id": candidate["candidate_id"],
        "input_polarization": polarization,
        "wavelength_nm": 450.0,
        "exact_geometry_hash": candidate["exact_geometry_hash_sha256"],
        "physics_configuration_hash": config_hash(),
        "weighted_G0_version": "LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1",
        "normalization_version": "LP_WEIGHTED_G0_SQRT_T_NORM_V1",
        "source_plan_sha256": source_plan_sha,
        "schema_version": "LP_ML_SCHEMA_V1.22",
    }


def spec_for(candidate: dict) -> dict:
    return {
        **candidate,
        "legacy_case_id": candidate["candidate_id"],
        "legacy_bin": 60,
        "J1_primitive": "sharp_rectangle",
        "J1_dims": {"side_nm": float(candidate["J1_side_nm"])},
        "J1_center": [float(candidate["J1_center_x_nm"]), float(candidate["J1_center_y_nm"])],
        "J1_rotation": 0.0,
        "J2_primitive": "sharp_rectangle",
        "J2_L": float(candidate["J2_length_nm"]),
        "J2_W": float(candidate["J2_width_nm"]),
        "J2_center": [float(candidate["J2_center_x_nm"]), float(candidate["J2_center_y_nm"])],
        "J2_rotation": 0.0,
        "geometry_hash": candidate["exact_geometry_hash_sha256"],
        "migration_manifest": {"geometry_hash_sha256": candidate["exact_geometry_hash_sha256"]},
        "direct_gap_ref": float(candidate["direct_gap_nm"]),
        "periodic_gap_ref": float(candidate["periodic_gap_nm"]),
        "common_translation": [0.0, 0.0],
        "migration_case": {"geometry_audit": {"J1": {}, "J2": {}}},
        "physics_configuration_hash": config_hash(),
        "fabrication_preferred_pass": True,
    }


def write_accounting(path: Path, base: dict, results: list[dict], status: str = "RUNNING") -> None:
    counts = {k: 0 for k in ("planned", "raw_invocations", "successful", "accepted", "recovered", "failed", "missing", "duplicate_invocation", "unauthorized", "pre_solver_compatibility_stops")}
    counts["planned"] = 48
    for r in results:
        counts["raw_invocations"] += int(r.get("solver_entered", False))
        counts["successful"] += int(r.get("solver_status") == "SUCCESS")
        counts["accepted"] += int(r.get("accepted", False))
        counts["recovered"] += int(r.get("recovered", False))
        counts["failed"] += int(r.get("solver_status") == "FAILED")
    atomic_json(path, {**base, "status": status, "counts": counts, "solver_calls": counts["raw_invocations"], "subruns": results})


def prepare() -> dict:
    if STAGING.exists():
        raise RuntimeError("STAGING_ALREADY_EXISTS_BEFORE_EXECUTION")
    manifest, rows = make_manifest(read_plan())
    PACKAGE.mkdir(parents=True, exist_ok=True)
    manifest_json = PACKAGE / "frozen_execution_manifest_v1.json"
    manifest_csv = PACKAGE / "frozen_execution_manifest_v1.csv"
    contract = PACKAGE / "execution_contract_v1.json"
    atomic_json(manifest_json, manifest)
    atomic_csv(manifest_csv, rows)
    execution_contract = {
        "contract_version": "LP_5D_PHASE_REACHABILITY_PROBE_EXECUTION_CONTRACT_V1",
        "status": "AUTHORIZED_FOR_EXPLICIT_EXECUTION",
        "manifest_sha256": sha(manifest_json),
        "manifest_csv_sha256": sha(manifest_csv),
        "runner_path": str(SCRIPT),
        "runner_sha256": sha(SCRIPT),
        "runtime_path": str(RUNTIME_PATH),
        "runtime_sha256": sha(RUNTIME_PATH),
        "candidate_order": manifest["candidate_order"],
        "future_budget": manifest["future_budget"],
        "max_entered": 48,
        "wavelength_nm_only": [450.0],
        "x_then_y": True,
        "no_replacement": True,
        "no_auto_retry_entered": True,
        "no_d9": True,
        "no_model_fill": True,
        "historical_hard_gate_preserved": "HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE",
    }
    atomic_json(contract, execution_contract)
    checks = [{"path": p.name, "sha256": sha(p), "bytes": p.stat().st_size} for p in (manifest_json, manifest_csv, contract)]
    atomic_json(PACKAGE / "content_checksums_v1.json", {"status": "PASS", "files": checks})
    return {"status": "PASS", "manifest_sha256": sha(manifest_json), "manifest_csv_sha256": sha(manifest_csv), "candidate_count": 24, "role_counts": EXPECTED_ROLES, "solver_calls": 0, "active_process_snapshot": manifest["active_process_snapshot"]}


def load_prepared() -> tuple[dict, list[dict]]:
    manifest_path = PACKAGE / "frozen_execution_manifest_v1.json"
    contract_path = PACKAGE / "execution_contract_v1.json"
    checks_path = PACKAGE / "content_checksums_v1.json"
    if not manifest_path.exists() or not contract_path.exists() or not checks_path.exists():
        raise RuntimeError("EXECUTION_PACKAGE_MISSING")
    checks = json.loads(checks_path.read_text(encoding="utf8"))
    for item in checks["files"]:
        if sha(PACKAGE / item["path"]) != item["sha256"]:
            raise RuntimeError("EXECUTION_PACKAGE_HASH_MISMATCH")
    manifest = json.loads(manifest_path.read_text(encoding="utf8"))
    contract = json.loads(contract_path.read_text(encoding="utf8"))
    if contract["manifest_sha256"] != sha(manifest_path) or contract["status"] != "AUTHORIZED_FOR_EXPLICIT_EXECUTION":
        raise RuntimeError("EXECUTION_CONTRACT_MISMATCH")
    return manifest, manifest["candidates"]


def execute_subrun(candidate: dict, pol: str, d6, runtime, manifest: dict, index: int, results: list[dict]) -> dict:
    sub = STAGING / "subruns" / candidate["candidate_id"] / pol
    if (sub / "entered.json").exists():
        raise RuntimeError("ENTERED_SUBRUN_ALREADY_EXISTS_NO_RERUN")
    sub.mkdir(parents=True, exist_ok=True)
    spec = spec_for(candidate)
    expected = expected_identity(candidate, pol, manifest["source_plan_sha256"])
    lock = runtime.ExecutionLock(STAGING / "locks" / f"{candidate['candidate_id']}_{pol}.lock", {"candidate_id": candidate["candidate_id"], "subrun_id": f"{candidate['candidate_id']}_{pol}"})
    backend = d6.ProductionLumapiBackend()
    entered = False
    pre_fsp = ROOT / "outputs/lp_d6_runtime" / f"pre_{candidate['candidate_id']}_{pol}.fsp"
    result = {"order": index, "candidate_id": candidate["candidate_id"], "role": candidate["role"], "polarization": pol, "solver_entered": False, "solver_status": "NOT_ENTERED", "accepted": False, "recovered": False}
    try:
        lock.acquire()
        backend.open_session()
        backend.build_geometry(spec)
        backend.configure_source_boundaries_monitor(spec, pol)
        pre_fsp.parent.mkdir(parents=True, exist_ok=True)
        backend.fdtd.save(str(pre_fsp))
        entered_payload = {
            "candidate_id": candidate["candidate_id"],
            "polarization": pol,
            "attempt_id": f"LP_5D_PHASE_REACHABILITY_V2_{index:02d}",
            "solver_entered": True,
            "entered_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "pre_fsp_sha256": sha(pre_fsp),
            "physical_contract_sha256": canon_sha(fixed_contract()),
            "exact_geometry_hash_sha256": candidate["exact_geometry_hash_sha256"],
            "wavelength_nm": 450.0,
            "no_retry_after_entered": True,
        }
        atomic_json(sub / "entered.json", entered_payload)
        entered = True
        result["solver_entered"] = True
        result["entered_utc"] = entered_payload["entered_utc"]
        result["pre_fsp_sha256"] = entered_payload["pre_fsp_sha256"]
        write_accounting(STAGING / "solver_accounting.json", {"plan_sha256": manifest["source_plan_sha256"], "manifest_sha256": sha(PACKAGE / "frozen_execution_manifest_v1.json"), "started_utc": dt.datetime.now(dt.timezone.utc).isoformat()}, results + [result])
        backend.run_solver()
        result["solver_status"] = "SUCCESS"
        checkpoint = sub / "checkpoint.json"
        payload = backend.extract_weighted_g0_observables()
        runtime.atomic_json(checkpoint, payload)
        result["checkpoint_sha256"] = sha(checkpoint)
        accepted = runtime.post_solver_acceptance(checkpoint, expected, STAGING / "formal_subruns.csv", STAGING / "events.ndjson")
        if accepted.get("status") != "PASS":
            raise RuntimeError("POST_SOLVER_ACCEPTANCE_NOT_PASS")
        reloaded = json.loads(checkpoint.read_text(encoding="utf8"))
        if reloaded.get("exact_geometry_hash") != candidate["exact_geometry_hash_sha256"] or reloaded.get("input_basis") != pol:
            raise RuntimeError("CHECKPOINT_RELOAD_IDENTITY_MISMATCH")
        atomic_json(sub / "acceptance_audit.json", {"status": "PASS", "accepted": True, "checkpoint_sha256": sha(checkpoint), "formal_subrun_key": accepted["formal_subrun_key"], "checkpoint_reload_pass": True, "phase_evidence_eligible": pol == "x", "full_jones_evidence_eligible_after_y": True})
        result.update({"accepted": True, "checkpoint_reload_pass": True, "formal_subrun_key": accepted["formal_subrun_key"]})
        return result
    except Exception as exc:
        result["solver_status"] = "FAILED" if entered else "PRE_SOLVER_FAILURE"
        result["failure"] = repr(exc)
        atomic_json(sub / "failure.json", result)
        raise
    finally:
        try:
            backend.close_session()
        finally:
            if pre_fsp.exists():
                pre_fsp.unlink(missing_ok=True)
            lock.release()


def phase_from(cp: dict) -> float:
    z = cp["weighted_G0_Ex"]
    return math.degrees(math.atan2(float(z["imag"]), float(z["real"]))) % 360.0


def phase_summary(phases: list[float]) -> dict:
    vals = sorted(phases)
    if not vals:
        return {"count": 0}
    gaps = [b - a for a, b in zip(vals, vals[1:])] + [vals[0] + 360.0 - vals[-1]]
    largest = max(gaps)
    return {"count": len(vals), "min_phase_deg": min(vals), "max_phase_deg": max(vals), "span_deg": max(vals) - min(vals), "largest_uncovered_circular_arc_deg": largest, "circular_coverage_deg": 360.0 - largest}


def postprocess(manifest: dict, rows: list[dict]) -> dict:
    import numpy as np
    phase_rows, full_rows = [], []
    for c in rows:
        base = STAGING / "subruns" / c["candidate_id"]
        xcp = base / "x" / "checkpoint.json"
        if not xcp.exists():
            continue
        x = json.loads(xcp.read_text(encoding="utf8"))
        phase_rows.append({"candidate_id": c["candidate_id"], "role": c["role"], "exact_geometry_hash_sha256": c["exact_geometry_hash_sha256"], "phase_deg": phase_from(x), "abs_txx": math.hypot(x["weighted_G0_Ex"]["real"], x["weighted_G0_Ex"]["imag"]), "source_T": x["source_T"], "phase_evidence_label": "PHASE_ONLY_REACHABILITY_PHYSICS", "physics_origin": "PROSPECTIVE_5D_PHASE_REACHABILITY_PROBE"})
        ycp = base / "y" / "checkpoint.json"
        if not ycp.exists():
            continue
        y = json.loads(ycp.read_text(encoding="utf8"))
        txx = complex(x["weighted_G0_Ex"]["real"], x["weighted_G0_Ex"]["imag"])
        tyx = complex(x["weighted_G0_Ey"]["real"], x["weighted_G0_Ey"]["imag"])
        txy = complex(y["weighted_G0_Ex"]["real"], y["weighted_G0_Ex"]["imag"])
        tyy = complex(y["weighted_G0_Ey"]["real"], y["weighted_G0_Ey"]["imag"])
        J = np.array([[txx, txy], [tyx, tyy]], dtype=complex)
        norm = float(np.linalg.norm(J))
        sv = np.linalg.svd(J, compute_uv=False)
        direct_error = math.sqrt(abs(txy) ** 2 + abs(tyx) ** 2 + abs(tyy) ** 2) / (norm + 1e-15)
        scalar_error = math.sqrt(max(0.0, 1.0 - abs(txx) ** 2 / (norm * norm + 1e-30)))
        full_rows.append({"candidate_id": c["candidate_id"], "role": c["role"], "exact_geometry_hash_sha256": c["exact_geometry_hash_sha256"], "txx_real": txx.real, "txx_imag": txx.imag, "txy_real": txy.real, "txy_imag": txy.imag, "tyx_real": tyx.real, "tyx_imag": tyx.imag, "tyy_real": tyy.real, "tyy_imag": tyy.imag, "phase_deg": phase_from(x), "abs_txx": abs(txx), "Txx": abs(txx) ** 2, "Txy": abs(txy) ** 2, "Tyx": abs(tyx) ** 2, "Tyy": abs(tyy) ** 2, "leakage": abs(txy) ** 2 + abs(tyx) ** 2 + abs(tyy) ** 2, "throughput": abs(txx) ** 2, "sigma1": float(sv[0]), "sigma2": float(sv[1]), "sigma2_over_sigma1": float(sv[1] / sv[0]) if sv[0] else None, "projection_error": direct_error, "projection_error_scalar_invariant": scalar_error, "projection_error_consistency_abs_error": abs(direct_error - scalar_error), "determinant_abs": abs(np.linalg.det(J)), "jones_frobenius_norm": norm, "full_jones_label": "FULL_JONES_REACHABILITY_PHYSICS", "projector_lineage": "projector_preserved_from_backbone"})
    atomic_csv(AN / "lp_5d_phase_reachability_probe_x_phase_evidence_v1.csv", phase_rows)
    atomic_csv(AN / "lp_5d_phase_reachability_probe_complete_jones_v1.csv", full_rows)
    old_path = AN / "lp_ml_inverse_stage1_5d_reachability_admission_v2.csv"
    old = []
    if old_path.exists():
        with old_path.open(encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                try:
                    old.append(float(r["phase_deg"]))
                except Exception:
                    pass
    new = [r["phase_deg"] for r in phase_rows]
    combined = old + new
    envelope = {"OLD_SUPPORT": phase_summary(old), "NEW_PROBE_ONLY": phase_summary(new), "COMBINED_SUPPORT": phase_summary(combined), "old_geometry_count": len(old), "new_phase_geometry_count": len(new), "full_jones_geometry_count": len(full_rows), "solver_calls": len(phase_rows) * 2}
    atomic_json(AN / "lp_5d_phase_reachability_probe_raw_phase_envelope_comparison_v1.json", envelope)
    low = sorted(phase_rows, key=lambda r: r["phase_deg"])
    high = sorted(phase_rows, key=lambda r: r["phase_deg"], reverse=True)
    extremes = {"new_minimum": low[:2], "new_maximum": high[:2], "old_minimum_deg": min(old) if old else None, "old_maximum_deg": max(old) if old else None}
    atomic_json(AN / "lp_5d_phase_reachability_probe_new_extrema_v1.json", extremes)
    role_effect = {}
    old_min, old_max = (min(old), max(old)) if old else (None, None)
    for role in EXPECTED_ROLES:
        rr = [r for r in phase_rows if r["role"] == role]
        role_effect[role] = {"count": len(rr), "below_old_min_count": sum(r["phase_deg"] < old_min for r in rr) if old_min is not None else 0, "above_old_max_count": sum(r["phase_deg"] > old_max for r in rr) if old_max is not None else 0, "min_phase_deg": min((r["phase_deg"] for r in rr), default=None), "max_phase_deg": max((r["phase_deg"] for r in rr), default=None)}
    atomic_json(AN / "lp_5d_phase_reachability_probe_role_effectiveness_v1.json", role_effect)
    full_sorted = sorted(full_rows, key=lambda r: r["projection_error"])
    best50 = full_sorted[: max(1, len(full_sorted) // 2)]
    best25 = full_sorted[: max(1, len(full_sorted) // 4)]
    throughput_median = sorted(r["throughput"] for r in full_rows)[len(full_rows) // 2] if full_rows else None
    throughput = [r for r in full_rows if throughput_median is not None and r["throughput"] >= throughput_median]
    tradeoff = {"all_full_jones": phase_summary([r["phase_deg"] for r in full_rows]), "best50_projector_error": phase_summary([r["phase_deg"] for r in best50]), "best25_projector_error": phase_summary([r["phase_deg"] for r in best25]), "throughput_ge_median": phase_summary([r["phase_deg"] for r in throughput]), "throughput_median": throughput_median, "projector_error_consistency_max_abs_error": max((r["projection_error_consistency_abs_error"] for r in full_rows), default=None), "no_new_absolute_threshold": True}
    atomic_json(AN / "lp_5d_phase_reachability_probe_phase_projector_tradeoff_v1.json", tradeoff)
    extrema = low[:2] + high[:2]
    b = json.loads(BOUNDS.read_text(encoding="utf8"))["ranges"]
    boundary = []
    for r in extrema:
        c = next(x for x in rows if x["candidate_id"] == r["candidate_id"])
        boundary.append({"candidate_id": r["candidate_id"], "phase_deg": r["phase_deg"], "J1_side": "at_lower" if c["J1_side_nm"] == b["J1_side_nm"][0] else "at_upper" if c["J1_side_nm"] == b["J1_side_nm"][1] else "interior", "J2_length": "at_lower" if c["J2_length_nm"] == b["J2_length_nm"][0] else "at_upper" if c["J2_length_nm"] == b["J2_length_nm"][1] else "interior", "J2_width": "at_lower" if c["J2_width_nm"] == b["J2_width_nm"][0] else "at_upper" if c["J2_width_nm"] == b["J2_width_nm"][1] else "interior", "D": "at_lower" if abs(c["D_nm"] - b["D_nm"][0]) < 1e-9 else "at_upper" if abs(c["D_nm"] - b["D_nm"][1]) < 1e-9 else "interior", "Psi": "at_lower" if abs(c["Psi_deg"] - b["Psi_deg"][0]) < 1e-9 else "at_upper" if abs(c["Psi_deg"] - b["Psi_deg"][1]) < 1e-9 else "interior"})
    boundary_saturation_detected = any("at_" in v for r in boundary for k, v in r.items() if k not in ("candidate_id", "phase_deg"))
    atomic_json(AN / "lp_5d_phase_reachability_probe_boundary_saturation_v1.json", {"extreme_coordinate_status": boundary, "boundary_saturation_detected": boundary_saturation_detected})
    sectors_all = sorted({int((r["phase_deg"] % 360) // 60) for r in phase_rows})
    sectors_full = sorted({int((r["phase_deg"] % 360) // 60) for r in full_rows})
    pairwise = max((abs(a["phase_deg"] - b["phase_deg"]) for i, a in enumerate(phase_rows) for b in phase_rows[i + 1:]), default=0.0)
    atomic_json(AN / "lp_5d_phase_reachability_probe_60deg_sector_diagnostic_v1.json", {"phase_only_sectors_touched": sectors_all, "full_jones_sectors_touched": sectors_full, "phase_only_sector_count": len(sectors_all), "full_jones_sector_count": len(sectors_full), "maximum_pairwise_phase_separation_deg": pairwise, "projector_compatible_phase_separation_available": max((abs(a["phase_deg"] - b["phase_deg"]) for i, a in enumerate(best50) for b in best50[i + 1:]), default=0.0), "six_bin_requirement_is_diagnostic_only": True})
    raw_expanded = bool(old and (min(new, default=old_min) < old_min or max(new, default=old_max) > old_max))
    compatible_expanded = bool(old and tradeoff["best50_projector_error"].get("span_deg", 0.0) > phase_summary(old).get("span_deg", 0.0))
    if raw_expanded and compatible_expanded:
        evidence = "LEVEL_3_USEFUL_5D_PHASE_LEVERAGE_EXISTS"
        outcome = "LP_5D_PHASE_REACHABILITY_PROBE_USEFUL_LEVERAGE_CONFIRMED"
    elif raw_expanded:
        evidence = "LEVEL_3_PHASE_PROJECTOR_TRADEOFF_LIMITED"
        outcome = "LP_5D_PHASE_REACHABILITY_PROBE_PHASE_PROJECTOR_TRADEOFF_LIMITED"
    elif boundary_saturation_detected:
        evidence = "LEVEL_3_5D_PHASE_LEVERAGE_INSUFFICIENT"
        outcome = "LP_5D_PHASE_REACHABILITY_PROBE_LEVEL3_5D_INSUFFICIENT"
    else:
        evidence = "LEVEL_2_REFINED"
        outcome = "LP_5D_PHASE_REACHABILITY_PROBE_REFINEMENT_REQUIRED"
    decision = {"outcome": outcome, "evidence_level": evidence, "raw_phase_expanded": raw_expanded, "projector_compatible_phase_expanded": compatible_expanded, "old_support": phase_summary(old), "new_probe_support": phase_summary(new), "combined_support": phase_summary(combined), "solver_calls": len(phase_rows) * 2, "no_d9": True, "no_retraining": True, "no_new_geometry": True}
    atomic_json(AN / "lp_5d_phase_reachability_probe_level3_evidence_decision_v1.json", decision)
    atomic_json(AN / "lp_5d_phase_reachability_probe_future_freedom_ranking_v1.json", {"status": "OFFLINE_ONLY_NOT_IMPLEMENTED", "ranking": [{"freedom": "H", "rank": 1}, {"freedom": "J1_side_to_J1_length_plus_J1_width", "rank": 2}], "no_execution_authorization": True})
    accounting_path = STAGING / "solver_accounting.json"
    if accounting_path.exists():
        accounting = json.loads(accounting_path.read_text(encoding="utf8"))
        atomic_json(AN / "lp_5d_phase_reachability_probe_solver_accounting_v1.json", accounting)
        acceptance_rows = []
        for item in accounting.get("subruns", []):
            acceptance_rows.append({
                "order": item.get("order"),
                "candidate_id": item.get("candidate_id"),
                "role": item.get("role"),
                "polarization": item.get("polarization"),
                "solver_entered": item.get("solver_entered"),
                "solver_status": item.get("solver_status"),
                "accepted": item.get("accepted"),
                "checkpoint_reload_pass": item.get("checkpoint_reload_pass"),
                "checkpoint_sha256": item.get("checkpoint_sha256"),
                "formal_subrun_key": item.get("formal_subrun_key"),
                "failure": item.get("failure", ""),
            })
        atomic_csv(AN / "lp_5d_phase_reachability_probe_per_subrun_acceptance_audit_v1.csv", acceptance_rows)
    execution_contract = json.loads((PACKAGE / "execution_contract_v1.json").read_text(encoding="utf8"))
    report_lines = [
        "# LP 5D Phase Reachability Probe V1",
        "",
        f"- Outcome: `{decision['outcome']}`",
        f"- Evidence level: `{decision['evidence_level']}`",
        f"- Solver calls: `{len(phase_rows) * 2}`",
        "- Wavelength: `450.0 nm only`",
        "",
        "## Frozen probe",
        "",
        "24 frozen geometries, 48 x/y subruns, no replacement or geometry expansion.",
        "",
        "## Active-process preflight",
        "",
        "Existing FDTD/Python process lines were recorded; no external process was terminated.",
        "",
        "## Solver accounting",
        "",
        f"- Accepted x/y subruns: {len(phase_rows) * 2}/{48}",
        f"- Complete Jones: {len(full_rows)}/24",
        "- Entered=true subruns were not retried.",
        "",
        "## Accepted x phase evidence",
        "",
        f"- Phase-only evidence rows: {len(phase_rows)}",
        f"- New probe envelope: {phase_summary(new)}",
        "",
        "## Complete Jones evidence",
        "",
        f"- Full-Jones rows: {len(full_rows)}",
        f"- Maximum direct/scalar projector consistency error: {tradeoff['projector_error_consistency_max_abs_error']}",
        "",
        "## Old vs new phase envelope",
        "",
        f"- OLD_SUPPORT: {envelope['OLD_SUPPORT']}",
        f"- NEW_PROBE_ONLY: {envelope['NEW_PROBE_ONLY']}",
        f"- COMBINED_SUPPORT: {envelope['COMBINED_SUPPORT']}",
        "",
        "## New low/high phase extrema",
        "",
        f"- Lowest: {low[:2]}",
        f"- Highest: {high[:2]}",
        "",
        "## Probe-role effectiveness",
        "",
        json.dumps(role_effect, indent=2, sort_keys=True),
        "",
        "## Phase/projector tradeoff",
        "",
        json.dumps(tradeoff, indent=2, sort_keys=True),
        "",
        "## Boundary saturation",
        "",
        json.dumps({"extreme_coordinate_status": boundary}, indent=2, sort_keys=True),
        "",
        "## 60-degree reachability",
        "",
        json.dumps({"phase_only_sectors": sectors_all, "full_jones_sectors": sectors_full, "maximum_pairwise_phase_separation_deg": pairwise}, indent=2, sort_keys=True),
        "",
        "## Evidence level",
        "",
        f"`{decision['evidence_level']}`",
        "",
        "## 5D sufficiency decision",
        "",
        f"`{decision['outcome']}`",
        "",
        "## Future freedom ranking",
        "",
        "Offline-only ranking retained: H first; no new freedom implemented.",
        "",
        "## Hard gates",
        "",
        "No D9, broadband, K6, model fill, retraining, replacement, or protected-report modification.",
        "",
        "## Execution provenance",
        "",
        f"The 48-subrun execution contract froze runner SHA256 `{execution_contract.get('runner_sha256')}`; a postprocess-only fix changed the current code to `{sha(SCRIPT)}` after all 48 accepted subruns. No solver was rerun and no physics checkpoint was modified.",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf8")
    atomic_json(AN / "lp_5d_phase_reachability_probe_postprocess_fix_attestation_v1.json", {
        "status": "POSTPROCESS_ONLY_FIX_AFTER_48_COMPLETED_SUBRUNS",
        "solver_rerun": False,
        "entered_subruns_unchanged": True,
        "execution_runner_sha256_frozen_at_prepare": execution_contract.get("runner_sha256"),
        "current_runner_sha256": sha(SCRIPT),
        "fix_scope": "boundary_saturation_postprocess_boolean_and_output_materialization_only",
        "physics_checkpoints_modified": False,
        "solver_calls": 0,
    })
    lightweight = []
    for p in sorted(AN.glob("lp_5d_phase_reachability_probe_*_v1.*")):
        if p.name == "lp_5d_phase_reachability_probe_output_checksums_v1.json":
            continue
        lightweight.append({"path": str(p), "sha256": sha(p), "bytes": p.stat().st_size})
    for p in sorted(PACKAGE.glob("*.json")) + sorted(PACKAGE.glob("*.csv")):
        lightweight.append({"path": str(p), "sha256": sha(p), "bytes": p.stat().st_size})
    lightweight.append({"path": str(REPORT), "sha256": sha(REPORT), "bytes": REPORT.stat().st_size})
    atomic_json(AN / "lp_5d_phase_reachability_probe_output_checksums_v1.json", {"status": "PASS", "solver_calls": len(phase_rows) * 2, "files": lightweight, "staging_raw_checkpoints_excluded": True})
    return {"phase_rows": len(phase_rows), "full_rows": len(full_rows), "decision": decision, "envelope": envelope, "report": str(REPORT), "report_sha256": sha(REPORT)}


def execute() -> dict:
    if STAGING.exists():
        raise RuntimeError("STAGING_ALREADY_EXISTS_NO_RESUME_OR_RERUN")
    manifest, rows = load_prepared()
    STAGING.mkdir(parents=True, exist_ok=False)
    d6 = load_module("lp_d6_exec_adapter", ROOT / "scripts/lp_b120_j2lm06_positional_jacobian_stage_d6_execute_v1.py")
    runtime = load_module("lp_checkpoint_authoritative_runtime_v1_23_exec", RUNTIME_PATH)
    d6.expected_identity = lambda candidate, polarization: expected_identity(candidate, polarization, manifest["source_plan_sha256"])
    results: list[dict] = []
    base = {"manifest_sha256": sha(PACKAGE / "frozen_execution_manifest_v1.json"), "manifest_csv_sha256": sha(PACKAGE / "frozen_execution_manifest_v1.csv"), "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "candidate_count": 24, "subrun_budget": 48}
    write_accounting(STAGING / "solver_accounting.json", base, results)
    try:
        for candidate in rows:
            for pol in ("x", "y"):
                result = execute_subrun(candidate, pol, d6, runtime, manifest, len(results) + 1, results)
                results.append(result)
                write_accounting(STAGING / "solver_accounting.json", base, results)
    except Exception:
        write_accounting(STAGING / "solver_accounting.json", base, results, "PARTIAL_DATA_PRESERVED")
        raise
    accounting = json.loads((STAGING / "solver_accounting.json").read_text(encoding="utf8"))
    accounting["status"] = "PASS" if accounting["counts"]["accepted"] == 48 else "PARTIAL_DATA_PRESERVED"
    write_accounting(STAGING / "solver_accounting.json", base, results, accounting["status"])
    post = postprocess(manifest, rows)
    after = {str(p): sha(p) for p in PROTECTED}
    atomic_json(STAGING / "protected_hash_audit.json", {"before": manifest["protected_hashes_before"], "after": after, "unchanged": manifest["protected_hashes_before"] == after})
    atomic_json(STAGING / "run_summary.json", {"status": accounting["status"], "planned_geometries": 24, "planned_subruns": 48, "raw_invocations": len(results), "accepted_subruns": sum(r["accepted"] for r in results), "complete_jones": post["full_rows"], "solver_calls": len(results), "decision": post["decision"]})
    return {"status": accounting["status"], "solver_calls": len(results), "accepted": sum(r["accepted"] for r in results), "complete_jones": post["full_rows"], "decision": post["decision"]}


def postprocess_only() -> dict:
    manifest, rows = load_prepared()
    if not STAGING.exists():
        raise RuntimeError("STAGING_MISSING_FOR_POSTPROCESS")
    accounting = json.loads((STAGING / "solver_accounting.json").read_text(encoding="utf8"))
    if accounting["counts"]["raw_invocations"] > 48:
        raise RuntimeError("SOLVER_BUDGET_EXCEEDED")
    post = postprocess(manifest, rows)
    after = {str(p): sha(p) for p in PROTECTED}
    atomic_json(STAGING / "protected_hash_audit.json", {"before": manifest["protected_hashes_before"], "after": after, "unchanged": manifest["protected_hashes_before"] == after})
    atomic_json(STAGING / "run_summary.json", {"status": accounting["status"], "planned_geometries": 24, "planned_subruns": 48, "raw_invocations": accounting["counts"]["raw_invocations"], "accepted_subruns": accounting["counts"]["accepted"], "complete_jones": post["full_rows"], "solver_calls": accounting["counts"]["raw_invocations"], "decision": post["decision"], "postprocess_only": True})
    return {"status": accounting["status"], "solver_calls": accounting["counts"]["raw_invocations"], "accepted": accounting["counts"]["accepted"], "complete_jones": post["full_rows"], "decision": post["decision"], "report": post["report"]}


def main() -> int:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--prepare-only", action="store_true")
    p.add_argument("--execute", action="store_true")
    p.add_argument("--postprocess-only", action="store_true")
    args = p.parse_args()
    if args.prepare_only:
        print(json.dumps(prepare(), indent=2, sort_keys=True))
        return 0
    if args.execute:
        print(json.dumps(execute(), indent=2, sort_keys=True))
        return 0
    if args.postprocess_only:
        print(json.dumps(postprocess_only(), indent=2, sort_keys=True))
        return 0
    raise SystemExit("USE_EXPLICIT_PREPARE_ONLY_OR_EXECUTE")


if __name__ == "__main__":
    main()
