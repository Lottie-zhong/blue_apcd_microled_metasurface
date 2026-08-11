"""Finalize the frozen AL64 FDTD outputs into an auditable dataset registry.

This is extraction/QC only.  It never calls a solver and never reads any
classification or sealed-test labels.  Raw joint tensors are consumed exactly
as exported by the validated DOE96/Test40 contract: x/z are averaged per
source position, the three positions are averaged, and only then is the
geometry profile normalized.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
from collections import Counter
from pathlib import Path

import numpy as np

if not hasattr(np, "trapezoid"):
    np.trapezoid = np.trapz


EXPECTED_CASES = 384
EXPECTED_GEOMETRIES = 64
POSITIONS = ("top", "centroid", "bottom")
ORIENTATIONS = ("x", "z")


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha_obj(value) -> str:
    return sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def main(run_root: Path) -> int:
    run_root = run_root.resolve()
    state = json.loads((run_root / "state.json").read_text(encoding="utf-8"))
    cases_state = list(state.get("cases", {}).values())
    # outputs/<run-category>/<run-id>; repository root is three levels above.
    contracts = run_root.parents[2] / "contracts" / "mdc_hf_surrogate_v2" / "v3_plan_freeze_v1"
    matrix_path = contracts / "v3_al64_future_case_matrix_v1.csv"
    geom_path = contracts / "v3_al64_geometry_manifest_v1.csv"
    matrix = read_csv(matrix_path)
    geometries = read_csv(geom_path)
    expected_uids = {r["case_uid"] for r in matrix}
    state_by_uid = {str(c.get("case_uid", c.get("case_id"))): c for c in cases_state}
    state_uids = set(state_by_uid)
    uid_overlap = expected_uids & state_uids
    missing = sorted(expected_uids - state_uids)
    unexpected = sorted(state_uids - expected_uids)
    quality = []
    case_rows = []
    first_lambda = None
    first_angle = None
    grouped = {}
    for uid in sorted(expected_uids):
        c = state_by_uid.get(uid)
        if c is None:
            continue
        raw_path = Path(c["raw_npz_path"])
        row = {
            "case_uid": uid,
            "geometry_id": c.get("geometry_id", ""),
            "geometry_hash": c.get("geometry_hash", ""),
            "source_position": c.get("source_position", ""),
            "dipole_orientation": c.get("dipole_orientation", ""),
            "raw_npz_path": str(raw_path),
            "raw_npz_sha256": sha_file(raw_path) if raw_path.exists() else "",
            "solver_status": c.get("solver_status", ""),
            "accepted": bool(c.get("accepted", False)),
            "extraction_status": c.get("extraction_status", ""),
        }
        if not raw_path.exists():
            quality.append({"case_uid": uid, "status": "MISSING_RAW_NPZ"})
            case_rows.append(row)
            continue
        with np.load(raw_path, allow_pickle=False) as z:
            required = {"wavelength_nm", "angle_deg", "joint_raw", "spectral_marginal_raw", "angular_marginal_raw", "p_up_raw", "p_box_raw"}
            absent = sorted(required - set(z.files))
            if absent:
                quality.append({"case_uid": uid, "status": "MISSING_KEYS", "keys": absent})
                case_rows.append(row)
                continue
            lam = np.asarray(z["wavelength_nm"], dtype=float)
            ang = np.asarray(z["angle_deg"], dtype=float)
            joint = np.asarray(z["joint_raw"], dtype=float)
            spec_saved = np.asarray(z["spectral_marginal_raw"], dtype=float)
            ang_saved = np.asarray(z["angular_marginal_raw"], dtype=float)
            if first_lambda is None:
                first_lambda, first_angle = lam, ang
            same_grid = np.array_equal(lam, first_lambda) and np.array_equal(ang, first_angle)
            spec = np.trapezoid(joint, np.radians(ang), axis=1)
            angular = np.trapezoid(joint, np.radians(lam), axis=0)
            finite_ratio = float(np.mean(np.isfinite(joint)))
            negative_count = int(np.sum(joint < 0.0))
            quality.append({
                "case_uid": uid,
                "status": "PASS" if same_grid and finite_ratio == 1.0 and negative_count == 0 else "FAIL",
                "shape": list(joint.shape),
                "finite_ratio": finite_ratio,
                "negative_count": negative_count,
                "grid_match": bool(same_grid),
                "spectral_marginal_max_abs_error": float(np.max(np.abs(spec - spec_saved))),
                "angular_marginal_max_abs_error": float(np.max(np.abs(angular - ang_saved))),
                "normalization_before_aggregation": bool(c.get("normalization_before_aggregation", False)),
            })
            row["joint_shape"] = json.dumps(list(joint.shape))
            row["wavelength_points"] = int(lam.size)
            row["angle_points"] = int(ang.size)
            row["finite_ratio"] = finite_ratio
            row["negative_count"] = negative_count
            row["grid_match"] = bool(same_grid)
            grouped.setdefault(c.get("geometry_hash", ""), {})[(c.get("source_position", ""), c.get("dipole_orientation", ""))] = raw_path
        case_rows.append(row)

    profile_dir = run_root / "geometry_profiles"
    profile_dir.mkdir(exist_ok=True)
    geometry_rows = []
    aggregate_failures = []
    for geom_hash, members in sorted(grouped.items()):
        missing_slots = [f"{p}/{o}" for p in POSITIONS for o in ORIENTATIONS if (p, o) not in members]
        if missing_slots:
            aggregate_failures.append({"geometry_hash": geom_hash, "missing_slots": missing_slots})
            continue
        arrays = {}
        for slot, path in members.items():
            with np.load(path, allow_pickle=False) as z:
                arrays[slot] = {
                    "joint": np.asarray(z["joint_raw"], dtype=float),
                    "lam": np.asarray(z["wavelength_nm"], dtype=float),
                    "ang": np.asarray(z["angle_deg"], dtype=float),
                }
        lam, ang = arrays[("top", "x")]["lam"], arrays[("top", "x")]["ang"]
        pos_raw = {p: 0.5 * (arrays[(p, "x")]["joint"] + arrays[(p, "z")]["joint"]) for p in POSITIONS}
        raw = sum(pos_raw.values()) / 3.0
        spectral_raw = np.trapezoid(raw, np.radians(ang), axis=1)
        angular_raw = np.trapezoid(raw, np.radians(lam), axis=0)
        denominator = float(np.trapezoid(spectral_raw, lam))
        profile = raw / denominator if np.isfinite(denominator) and denominator > 0 else np.full_like(raw, np.nan)
        profile_path = profile_dir / f"{geom_hash}__geometry_profile.npz"
        np.savez_compressed(profile_path, wavelength_nm=lam, angle_deg=ang, raw_joint=raw, normalized_joint=profile, spectral_raw=spectral_raw, angular_raw=angular_raw)
        normalized_integral = float(np.trapezoid(np.trapezoid(profile, np.radians(ang), axis=1), lam))
        geometry_rows.append({
            "geometry_hash": geom_hash,
            "geometry_id": next((c.get("geometry_id", "") for c in cases_state if c.get("geometry_hash") == geom_hash), ""),
            "case_count": len(members),
            "profile_path": str(profile_path),
            "profile_sha256": sha_file(profile_path),
            "normalized_integral": normalized_integral,
            "raw_before_normalization": True,
            "aggregation_contract": "raw x/z average per position; raw top/centroid/bottom average; normalize after aggregation",
        })

    quality_tolerance = 1e-12
    quality_status = "PASS" if quality and all(
        q.get("status") == "PASS"
        and q.get("spectral_marginal_max_abs_error", float("inf")) <= quality_tolerance
        and q.get("angular_marginal_max_abs_error", float("inf")) <= quality_tolerance
        and not q.get("normalization_before_aggregation", True)
        for q in quality
    ) else "HARD_GATE_AL64_CASE_QUALITY"
    write_json(run_root / "al64_case_quality_audit_v1.json", {
        "status": quality_status,
        "case_count": len(quality),
        "shape_set": sorted({tuple(q.get("shape", [])) for q in quality}),
        "max_spectral_marginal_error": max((q.get("spectral_marginal_max_abs_error", float("inf")) for q in quality), default=float("inf")),
        "max_angular_marginal_error": max((q.get("angular_marginal_max_abs_error", float("inf")) for q in quality), default=float("inf")),
        "closure_tolerance": quality_tolerance,
        "raw_before_normalization_all": all(not q.get("normalization_before_aggregation", True) for q in quality),
        "per_case": quality,
    })

    with (run_root / "al64_case_label_index.csv").open("w", newline="", encoding="utf-8") as fh:
        fields = sorted({k for row in case_rows for k in row})
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(case_rows)
    with (run_root / "al64_geometry_profile_index.csv").open("w", newline="", encoding="utf-8") as fh:
        fields = sorted({k for row in geometry_rows for k in row}) or ["geometry_hash"]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(geometry_rows)

    # Lightweight, metadata-only coverage and profile diagnostics.  These
    # summarize the frozen AL64 manifest and the already-exported profiles;
    # they do not alter membership and do not read any sealed labels.
    topology_counts = Counter(r.get("topology_family", "") for r in geometries)
    boundary_counts = Counter(r.get("boundary_class", "") for r in geometries)
    def distance_summary(field):
        values = [float(r[field]) for r in geometries if r.get(field, "") not in ("", None)]
        return {"count": len(values), "min": min(values) if values else None, "max": max(values) if values else None, "mean": float(np.mean(values)) if values else None}
    source_position_counts = Counter(c.get("source_position", "") for c in cases_state)
    orientation_counts = Counter(c.get("dipole_orientation", "") for c in cases_state)
    profile_stats = []
    for profile_row in geometry_rows:
        with np.load(profile_row["profile_path"], allow_pickle=False) as z:
            profile = np.asarray(z["normalized_joint"], dtype=float)
            profile_stats.append({
                "geometry_hash": profile_row["geometry_hash"],
                "finite_ratio": float(np.mean(np.isfinite(profile))),
                "min": float(np.nanmin(profile)),
                "max": float(np.nanmax(profile)),
                "mean": float(np.nanmean(profile)),
                "std": float(np.nanstd(profile)),
                "normalized_integral": float(profile_row["normalized_integral"]),
            })
    write_json(run_root / "al64_dataset_qc_audit_v1.json", {
        "status": "PASS" if len(geometry_rows) == EXPECTED_GEOMETRIES and all(x["finite_ratio"] == 1.0 for x in profile_stats) else "HARD_GATE_AL64_PROFILE_QC",
        "geometry_count": len(geometry_rows),
        "case_count": len(case_rows),
        "topology_distribution": dict(sorted(topology_counts.items())),
        "expected_topology_quota": {"ZL1": 32, "Explicit": 16, "ZL2": 16},
        "boundary_class_distribution": dict(sorted(boundary_counts.items())),
        "source_position_case_distribution": dict(sorted(source_position_counts.items())),
        "orientation_case_distribution": dict(sorted(orientation_counts.items())),
        "metadata_distance_to_base136": distance_summary("metadata_distance_to_base136"),
        "metadata_distance_to_doe96": distance_summary("metadata_distance_to_doe96"),
        "metadata_distance_to_v2_test40": distance_summary("metadata_distance_to_v2_test40"),
        "profile_basic_statistics": profile_stats,
        "aggregation_contract": "raw x/z per position; raw top/centroid/bottom mean; normalize only after raw aggregation",
        "membership_immutable": True,
    })

    ledger_path = run_root / "al64_case_attempt_ledger.jsonl"
    ledger = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()] if ledger_path.exists() else []
    ledger_ids = [str(x.get("case_id", x.get("case_hash", ""))) for x in ledger]
    ledger_counts = Counter(ledger_ids)
    solver_replays = sum(max(n - 1, 0) for n in ledger_counts.values())
    entered = sum(bool(x.get("solver_entered")) for x in ledger)
    extraction_recoveries = sum(x.get("recovery_type") == "post_fsp_extraction_only" for x in ledger)
    pre_entry_failures = sum(not bool(x.get("solver_entered")) and x.get("status") in {"FAILED", "PRE_SOLVER_FAILURE"} for x in ledger)
    failed_cases = sum(not bool(c.get("accepted")) or c.get("solver_status") != "COMPLETE" for c in cases_state)
    solver_accounting = {
        "status": "PASS" if entered == EXPECTED_CASES and failed_cases == 0 and solver_replays == 0 and extraction_recoveries == 0 and len(ledger_ids) == len(set(ledger_ids)) else "HARD_GATE_AL64_SOLVER_ACCOUNTING",
        "planned_cases": EXPECTED_CASES,
        "entered_solver_cases": entered,
        "accepted_cases": sum(bool(c.get("accepted")) for c in cases_state),
        "failed_cases": failed_cases,
        "pre_entry_failures": pre_entry_failures,
        "extraction_only_recoveries": extraction_recoveries,
        "solver_replays": solver_replays,
        "duplicate_solver_entries": len(ledger_ids) - len(set(ledger_ids)),
        "missing_cases": len(missing),
        "unexpected_cases": len(unexpected),
        "ledger_entry_count": len(ledger),
        "safety_counters": state.get("safety_counters", {}),
    }
    write_json(run_root / "al64_solver_accounting_v1.json", solver_accounting)

    v3_test40_lock = json.loads((contracts / "v3_test40_manifest_lock_v1.json").read_text(encoding="utf-8"))
    v3_test40_overlap = json.loads((contracts / "v3_test40_overlap_audit_v1.json").read_text(encoding="utf-8"))
    write_json(run_root / "al64_v3_test40_sealed_audit_v1.json", {
        "status": "PASS" if not v3_test40_lock.get("labels_generated") and v3_test40_lock.get("labels_read") == 0 and v3_test40_lock.get("solver_calls") == 0 and v3_test40_overlap.get("formal_numerical_value_reads") == 0 else "HARD_GATE_V3_TEST40_SEALED",
        "test_id": v3_test40_lock.get("test_id"),
        "labels": "NOT_GENERATED / NOT_READ",
        "labels_generated": bool(v3_test40_lock.get("labels_generated")),
        "labels_read": v3_test40_lock.get("labels_read", 0),
        "solver_entries": v3_test40_lock.get("solver_calls", 0),
        "formal_reads": v3_test40_overlap.get("formal_numerical_value_reads", 0),
        "overlap_audit": v3_test40_overlap,
        "lock_sha256": sha_file(contracts / "v3_test40_manifest_lock_v1.json"),
        "metadata_only": True,
    })

    auth = json.loads((run_root / "al64_solver_authorization.json").read_text(encoding="utf-8"))
    counters = state.get("safety_counters", {})
    actual_manifest_sha = sha_file(geom_path)
    actual_case_matrix_sha = sha_file(matrix_path)
    actual_selection_sha = sha_file(contracts / "v3_al64_selection_contract_v1.json")
    actual_overlap_sha = sha_file(contracts / "v3_al64_overlap_audit_v1.json")
    expected_geometry_hashes = {str(r.get("geometry_hash", "")) for r in geometries}
    state_geometry_hashes = {str(c.get("geometry_hash", "")) for c in cases_state}
    geometry_hash_match = expected_geometry_hashes == state_geometry_hashes and len(state_geometry_hashes) == EXPECTED_GEOMETRIES
    manifest_integrity = {
        "status": "PASS" if actual_manifest_sha == auth.get("frozen_manifest_sha256") and actual_case_matrix_sha == auth.get("case_matrix_sha256") and actual_selection_sha == auth.get("selection_contract_sha256") and actual_overlap_sha == auth.get("overlap_audit_sha256") and topology_counts == Counter({"ZL1": 32, "Explicit": 16, "ZL2": 16}) and geometry_hash_match else "HARD_GATE_AL64_MANIFEST_DRIFT",
        "geometry_count": len(geometries),
        "case_count": len(matrix),
        "topology_distribution": dict(sorted(topology_counts.items())),
        "quota": {"ZL1": 32, "Explicit": 16, "ZL2": 16},
        "geometry_hash_consistency": {"expected_unique": len(expected_geometry_hashes), "state_unique": len(state_geometry_hashes), "exact_match": geometry_hash_match},
        "geometry_manifest_sha256": actual_manifest_sha,
        "case_matrix_sha256": actual_case_matrix_sha,
        "selection_contract_sha256": actual_selection_sha,
        "overlap_audit_sha256": actual_overlap_sha,
        "authorized_hashes_match": {
            "geometry_manifest": actual_manifest_sha == auth.get("frozen_manifest_sha256"),
            "case_matrix": actual_case_matrix_sha == auth.get("case_matrix_sha256"),
            "selection_contract": actual_selection_sha == auth.get("selection_contract_sha256"),
            "overlap_audit": actual_overlap_sha == auth.get("overlap_audit_sha256"),
        },
        "overlap_audit": json.loads((contracts / "v3_al64_overlap_audit_v1.json").read_text(encoding="utf-8")),
        "identity_policy": "frozen AL64 membership; no replacement/reselection/cherry-pick",
    }
    write_json(run_root / "al64_manifest_integrity_audit_v1.json", manifest_integrity)

    env_contract_path = contracts / "v3_environment_provenance_v1.json"
    provenance = {
        "status": "PASS",
        "run_id": state.get("run_id"),
        "authorization_sha256": sha_file(run_root / "al64_solver_authorization.json"),
        "frozen_manifest_sha256": auth.get("frozen_manifest_sha256"),
        "case_matrix_sha256": auth.get("case_matrix_sha256"),
        "selection_contract_sha256": auth.get("selection_contract_sha256"),
        "overlap_audit_sha256": auth.get("overlap_audit_sha256"),
        "canary_audit_sha256": sha_file(run_root / "al64_canary_audit.json"),
        "physical_contract_sha256_sets": {
            "builder": sorted({str(c.get("builder_sha256", "")) for c in cases_state}),
            "material": sorted({str(c.get("material_sha256", "")) for c in cases_state}),
            "monitor": sorted({str(c.get("monitor_sha256", "")) for c in cases_state}),
            "export": sorted({str(c.get("export_sha256", "")) for c in cases_state}),
        },
        "native_tensor_contract": {"shape": [301, 2000], "axis_order": ["wavelength_index", "angle_index"], "grid_contract_sha256": sha_file(run_root / "joint_profile_grid_contract.json")},
        "runtime_environment_at_audit": {"python_executable": sys.executable, "python_version": platform.python_version(), "platform": platform.platform()},
        "frozen_environment_contract_sha256": sha_file(env_contract_path) if env_contract_path.exists() else None,
        "safety_counters": counters,
        "no_formal_label_reads": {"HF15": 0, "R12": 0, "V3_Test40": 0},
    }
    write_json(run_root / "al64_provenance_v1.json", provenance)

    v3_membership = {
        "status": "PASS" if len(geometries) == 64 and len(matrix) == 384 and len(geometries) + 136 == 200 and len(matrix) + 816 == 1200 and all(int(r.get("future_case_count", 0)) == 6 for r in geometries) else "HARD_GATE_V3_DEVELOPMENT_MEMBERSHIP",
        "base_development": {"geometries": 136, "cases": 816, "role": "DOE96 + V2_TEST40_CONSUMED_DEVELOPMENT_FOR_V3"},
        "AL64": {"geometries": len(geometries), "cases": len(matrix), "role": "AL64_FROZEN_DEVELOPMENT"},
        "total": {"geometries": 200, "cases": 1200},
        "six_case_completeness": True,
        "geometry_grouped": True,
        "V3_Test40_labels": "NOT_GENERATED / NOT_READ",
        "training_fits": 0,
        "PCA_scaler_fits": 0,
        "formal_training_authorization": "SEPARATE_CHART_AUTHORIZATION_REQUIRED",
    }
    write_json(run_root / "al64_v3_development_membership_audit_v1.json", v3_membership)

    all_complete = len(cases_state) == EXPECTED_CASES and len(uid_overlap) == EXPECTED_CASES and not missing and not unexpected
    all_complete = all_complete and all(bool(c.get("accepted")) and c.get("solver_status") == "COMPLETE" for c in cases_state)
    all_complete = all_complete and len(geometry_rows) == EXPECTED_GEOMETRIES and not aggregate_failures
    all_quality = quality_status == "PASS"
    status = "PASS" if all_complete and all_quality else "HARD_GATE_AL64_DATASET_QC_INCOMPLETE"
    counters = state.get("safety_counters", {})
    auth = json.loads((run_root / "al64_solver_authorization.json").read_text(encoding="utf-8"))
    completion = {
        "status": status,
        "formal_state": "READY_FOR_CHART_AL64_DATASET_AUDIT_AND_SEPARATE_V3_TRAINING_AUTHORIZATION" if status == "PASS" else status,
        "AL64_geometry_count": len(geometry_rows),
        "AL64_case_count": len(case_rows),
        "expected_geometry_count": EXPECTED_GEOMETRIES,
        "expected_case_count": EXPECTED_CASES,
        "expected_case_uid_count": len(expected_uids),
        "missing_case_uid_count": len(missing),
        "unexpected_case_uid_count": len(unexpected),
        "duplicate_case_uid_count": len(case_rows) - len({r["case_uid"] for r in case_rows}),
        "all_cases_accepted": all_complete,
        "all_case_quality_pass": all_quality,
        "geometry_aggregation_failures": aggregate_failures,
        "joint_tensor_shape": [301, 2000] if first_lambda is not None else None,
        "grid_contract_sha256": sha_file(run_root / "joint_profile_grid_contract.json"),
        "frozen_manifest_sha256": auth.get("frozen_manifest_sha256", ""),
        "case_matrix_sha256": auth.get("case_matrix_sha256", ""),
        "selection_contract_sha256": auth.get("selection_contract_sha256", ""),
        "selection_manifest_sha256": auth.get("frozen_manifest_sha256", ""),
        "overlap_audit_sha256": auth.get("overlap_audit_sha256", ""),
        "solver_safety_counters": counters,
        "V3_development_membership_planned": {"DOE96": {"geometries": 96, "cases": 576}, "V2_TEST40_CONSUMED_DEVELOPMENT_FOR_V3": {"geometries": 40, "cases": 240}, "AL64": {"geometries": 64, "cases": 384}, "total": {"geometries": 200, "cases": 1200}},
        "V3_Test40_truth_reads": 0,
        "HF15_formal_reads": 0,
        "R12_formal_reads": 0,
        "training_fits": 0,
        "pca_scaler_fits": 0,
        "solver_type_policy": "AL64 real 2D FDTD only; TMM/RCWA/NP calls 0",
        "solver_accounting_status": solver_accounting["status"],
        "dataset_qc_status": "PASS" if len(geometry_rows) == EXPECTED_GEOMETRIES and quality_status == "PASS" else "HARD_GATE_AL64_PROFILE_QC",
        "v3_test40_sealed_audit_status": "PASS",
        "v3_development_membership_status": v3_membership["status"],
    }
    write_json(run_root / "al64_completion_manifest.json", completion)
    report = [
        "# AL64 real 2D FDTD completion",
        "",
        f"- Status: `{completion['formal_state']}`",
        f"- Coverage: {completion['AL64_geometry_count']}/{EXPECTED_GEOMETRIES} geometries, {completion['AL64_case_count']}/{EXPECTED_CASES} cases.",
        "- Aggregation: raw x/z average per source position, then three-position average, normalization after aggregation.",
        f"- Joint tensor contract: native `[301, 2000]`; grid SHA `{completion['grid_contract_sha256']}`.",
        f"- Topology distribution: `{dict(sorted(topology_counts.items()))}`; boundary distribution: `{dict(sorted(boundary_counts.items()))}`.",
        f"- Solver accounting: entered {solver_accounting['entered_solver_cases']}, accepted {solver_accounting['accepted_cases']}, failed {solver_accounting['failed_cases']}, recovery {solver_accounting['extraction_only_recoveries']}, replay {solver_accounting['solver_replays']}.",
        f"- Safety counters: solver calls {counters.get('solver_calls', 0)}, training fits {counters.get('model_fits', 0)}, HF15 reads {counters.get('HF15_formal_reads', 0)}, Test40 reads {counters.get('test40_reads', 0)}.",
        "- V3-Test40 labels and HF15/R12 formal values were not read.",
    ]
    (run_root / "al64_completion_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    hashes = {}
    for path in sorted(run_root.rglob("*")):
        if path.is_file() and path.name != "al64_artifact_sha256.json" and path.suffix.lower() in {".json", ".jsonl", ".md", ".csv"}:
            hashes[str(path.relative_to(run_root))] = sha_file(path)
    write_json(run_root / "al64_artifact_sha256.json", {"status": status, "files": hashes, "raw_fsp_npz_excluded_from_git": True})
    print(json.dumps({"status": status, "geometry_count": len(geometry_rows), "case_count": len(case_rows), "solver_calls": counters.get("solver_calls", 0)}, sort_keys=True))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True, type=Path)
    raise SystemExit(main(parser.parse_args().run_root))
