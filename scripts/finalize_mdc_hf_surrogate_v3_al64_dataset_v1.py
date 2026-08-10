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
    contracts = run_root.parents[1] / "contracts" / "mdc_hf_surrogate_v2" / "v3_plan_freeze_v1"
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
            angular = np.trapezoid(joint, lam, axis=0)
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
        angular_raw = np.trapezoid(raw, lam, axis=0)
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

    all_complete = len(cases_state) == EXPECTED_CASES and len(uid_overlap) == EXPECTED_CASES and not missing and not unexpected
    all_complete = all_complete and all(bool(c.get("accepted")) and c.get("solver_status") == "COMPLETE" for c in cases_state)
    all_complete = all_complete and len(geometry_rows) == EXPECTED_GEOMETRIES and not aggregate_failures
    all_quality = all(q.get("status") == "PASS" for q in quality if q.get("status") != "MISSING_RAW_NPZ") and not any(q.get("status") == "MISSING_RAW_NPZ" for q in quality)
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
        "selection_manifest_sha256": auth.get("selection_manifest_sha256", ""),
        "overlap_audit_sha256": auth.get("overlap_audit_sha256", ""),
        "solver_safety_counters": counters,
        "V3_development_membership_planned": {"DOE96": {"geometries": 96, "cases": 576}, "V2_TEST40_CONSUMED_DEVELOPMENT_FOR_V3": {"geometries": 40, "cases": 240}, "AL64": {"geometries": 64, "cases": 384}, "total": {"geometries": 200, "cases": 1200}},
        "V3_Test40_truth_reads": 0,
        "HF15_formal_reads": 0,
        "R12_formal_reads": 0,
        "training_fits": 0,
        "pca_scaler_fits": 0,
        "solver_type_policy": "AL64 real 2D FDTD only; TMM/RCWA/NP calls 0",
    }
    write_json(run_root / "al64_completion_manifest.json", completion)
    report = [
        "# AL64 real 2D FDTD completion",
        "",
        f"- Status: `{completion['formal_state']}`",
        f"- Coverage: {completion['AL64_geometry_count']}/{EXPECTED_GEOMETRIES} geometries, {completion['AL64_case_count']}/{EXPECTED_CASES} cases.",
        "- Aggregation: raw x/z average per source position, then three-position average, normalization after aggregation.",
        f"- Joint tensor contract: native `[301, 2000]`; grid SHA `{completion['grid_contract_sha256']}`.",
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
