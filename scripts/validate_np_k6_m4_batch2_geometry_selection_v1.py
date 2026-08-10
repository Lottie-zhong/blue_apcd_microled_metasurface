"""Independent validator for the zero-solver NP K6 M4 selection evidence."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any


ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / r"outputs\np_k6_m4_batch2_geometry_selection_v1"
FOUNDATION = ROOT / r"outputs\np_k6_ml_d0_database_foundation_v1"
M3 = ROOT / r"outputs\np_k6_m3_pilot_retraining_v1"
M2 = ROOT / r"outputs\np_k6_m2_active_learning_batch1_selection_v1"
WAVELENGTHS = set(range(445, 456))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_diameters(geometry_id: str) -> list[float]:
    values = [float(x) for x in re.findall(r"D(\d+)", geometry_id)]
    if len(values) != 6:
        raise ValueError(f"geometry id does not contain six diameters: {geometry_id}")
    return values


def finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def refresh_checksum_manifest() -> None:
    files = []
    for path in sorted(OUT.iterdir()):
        if path.is_file() and path.name != "m4_checksum_manifest.json":
            files.append({"path": path.name, "sha256": sha256(path), "size_bytes": path.stat().st_size, "git_candidate": path.stat().st_size < 2_000_000})
    write_json(OUT / "m4_checksum_manifest.json", {
        "schema_version": "np_k6_m4_checksum_manifest_v1",
        "files": files,
        "runtime_checkpoints_excluded": True,
        "solver_run_invocations": 0,
        "sealed_target_reads": 0,
    })


def main() -> int:
    checks: dict[str, bool] = {}
    errors: list[str] = []
    required = {
        "m4_authority_audit.json", "m4_candidate_prediction_profiles_long.csv",
        "m4_candidate_selection_long.csv", "m4_checksum_manifest.json",
        "m4_decision.json", "m4_geometry_coverage_audit.json",
        "m4_geometry_coverage_summary.csv", "m4_geometry_feature_space.csv",
        "m4_provenance_manifest.json", "m4_selection_manifest.json",
        "m4_selection_policy.json", "m4_solver_cost_decision_package.json",
        "m4_solver_zero_audit.json", "m4_validator_report.json",
    }
    missing = sorted(name for name in required if not (OUT / name).is_file())
    checks["required_evidence_present"] = not missing
    if missing:
        errors.append("missing:" + ",".join(missing))
        report = {"schema_version": "np_k6_m4_standalone_validator_v1", "status": "FAIL", "checks": checks, "errors": errors}
        OUT.mkdir(parents=True, exist_ok=True)
        write_json(OUT / "m4_standalone_validator_report.json", report)
        return 1

    authority = read_json(OUT / "m4_authority_audit.json")
    selection = read_json(OUT / "m4_selection_manifest.json")
    policy = read_json(OUT / "m4_selection_policy.json")
    decision = read_json(OUT / "m4_decision.json")
    zero = read_json(OUT / "m4_solver_zero_audit.json")
    generated = read_json(OUT / "m4_validator_report.json")
    coverage = read_json(OUT / "m4_geometry_coverage_audit.json")
    cost = read_json(OUT / "m4_solver_cost_decision_package.json")
    profiles = read_csv(OUT / "m4_candidate_prediction_profiles_long.csv")
    selected_rows = read_csv(OUT / "m4_candidate_selection_long.csv")
    manifest = read_json(FOUNDATION / "k6_hf_pilot_geometry_manifest.json")
    dev_rows = [row for row in manifest["rows"] if row["pilot_role"] == "development_pilot"]
    sealed_rows = [row for row in manifest["rows"] if row["pilot_role"] == "sealed_test_pilot"]
    dev_hashes = {row["geometry_hash"] for row in dev_rows}
    sealed_hashes = {row["geometry_hash"] for row in sealed_rows}
    hf_hashes = {row["geometry_hash"] for row in read_csv(M3 / "development_hf_v2_training_view.csv")}

    policy_body = {key: value for key, value in policy.items() if key != "policy_hash"}
    policy_hash = hashlib.sha256(json.dumps(policy_body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    checks["policy_hash_recomputes"] = policy_hash == policy.get("policy_hash") == selection.get("policy_hash") == decision.get("policy_hash")
    if not checks["policy_hash_recomputes"]:
        errors.append("policy_hash_mismatch")
    checks["authority_counts"] = (
        authority.get("development_universe_count") == 48
        and authority.get("candidate_pool_count") == 45
        and authority.get("effective_candidate_count") == 39
        and authority.get("existing_hf9_count") == 9
        and authority.get("sealed_universe_count") == 12
    )
    checks["candidate_source_hf_overlap_is_explicitly_excluded"] = authority.get("candidate_existing_hf_overlap_count") == 6
    checks["authority_zero_overlap"] = all(authority.get(key) == 0 for key in (
        "candidate_sealed_overlap_count", "effective_existing_hf_overlap_count",
        "effective_sealed_overlap_count", "duplicate_candidate_hashes",
        "sealed_target_reads", "solver_run_invocations"))
    checks["m3_validator_pass"] = generated.get("status") == "PASS" and all(generated.get("checks", {}).values())
    checks["selection_status_ready"] = selection.get("status") == "NP_K6_M4_BATCH2_GEOMETRY_SELECTION_READY_FOR_SOLVER_AUTHORIZATION" and decision.get("solver_started") is False

    primary = selection.get("primary4", [])
    backups = selection.get("backups_ranked", [])
    first6 = selection.get("first6_additions", [])
    first8 = selection.get("first8_additions", [])
    primary_ids = [row.get("geometry_id") for row in primary]
    backup_ids = [row.get("geometry_id") for row in backups]
    checks["primary4_and_backup_contract"] = (
        len(primary) == 4 and len(set(primary_ids)) == 4 and len(backups) >= 8
        and len(first6) == 2 and len(first8) == 2
        and not set(primary_ids) & set(backup_ids)
        and [row.get("rank") for row in backups] == list(range(1, len(backups) + 1))
    )
    selected_all = primary + backups
    selected_hashes = {row.get("geometry_hash") for row in selected_all}
    selected_ids = {row.get("geometry_id") for row in selected_all}
    checks["selected_development_only"] = (
        len(selected_hashes) == len(selected_all)
        and all(row.get("geometry_hash") in dev_hashes for row in selected_all)
        and not selected_hashes & sealed_hashes
        and not selected_hashes & hf_hashes
    )
    source_rows = read_csv(M2 / "candidate_acquisition_features.csv")
    effective_source_hashes = {row["geometry_hash"] for row in source_rows if row["geometry_hash"] not in hf_hashes and row["geometry_hash"] not in sealed_hashes}
    checks["selection_rows_cover_effective_pool"] = len(selected_rows) == 39 and {row.get("geometry_hash") for row in selected_rows} == effective_source_hashes
    malformed = []
    for row in selected_rows:
        try:
            values = parse_diameters(row["geometry_id"])
            if values != [float(row[f"D{i}"]) for i in range(6)]:
                malformed.append(row["geometry_id"])
            if row["geometry_hash"] not in dev_hashes:
                malformed.append(row["geometry_id"] + ":outside_dev")
        except (KeyError, ValueError):
            malformed.append(row.get("geometry_id", "<missing>"))
        if row.get("policy_hash") != policy_hash:
            malformed.append(row.get("geometry_id", "<missing>") + ":policy")
    checks["physical_d0_d5_order_preserved"] = not malformed
    if malformed:
        errors.append("malformed_selection_rows:" + ",".join(malformed[:8]))

    expected_keys = {(row["geometry_id"], int(row["wavelength_nm"]), row["polarization"]) for row in profiles}
    expected_ids = {row["geometry_id"] for row in selected_rows if row.get("geometry_hash") not in hf_hashes}
    expected_complete = {(gid, wl, pol) for gid in expected_ids for wl in range(445, 456) for pol in ("p", "s")}
    checks["profile_858_complete"] = len(profiles) == 39 * 11 * 2 and expected_keys == expected_complete and all(finite(value) for row in profiles for value in row.values() if value not in {row.get("geometry_id"), row.get("geometry_hash"), row.get("polarization")} and value != "")
    checks["profile_no_duplicates"] = len(expected_keys) == len(profiles)
    checks["coverage_audit_complete"] = set(coverage.get("comparisons", {})) >= {"current_hf9", "hf9_plus_primary4", "hf9_plus_first6", "hf9_plus_first8"} and coverage.get("solver_run_invocations") == 0 and coverage.get("sealed_target_reads") == 0
    checks["cost_package_complete"] = (
        cost.get("solver_authorization") is False and cost.get("solver_run_invocations") == 0
        and cost.get("sealed_target_reads") == 0
        and {row.get("batch") for row in cost.get("batches", [])} == {"primary4", "first6", "first8"}
        and {row.get("paired_ps_case_count") for row in cost.get("batches", [])} == {8, 12, 16}
    )
    checks["zero_solver_and_sealed_reads"] = (
        zero.get("fdtd_run_invocations") == 0 and zero.get("lumapi_run_invocations") == 0
        and zero.get("sealed_target_reads") == 0 and zero.get("batch2_started") is False
        and zero.get("lumerical_imported") is False
    )
    checks["no_large_or_solver_artifacts"] = not any(path.suffix.lower() in {".fsp", ".pt", ".npz"} for path in OUT.iterdir() if path.is_file())

    # Write a deterministic report, then refresh the manifest so every lightweight
    # artifact (including this report) is covered while the manifest excludes itself.
    report = {
        "schema_version": "np_k6_m4_standalone_validator_v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "errors": errors,
        "policy_hash": policy_hash,
        "primary4_geometry_ids": primary_ids,
        "backup_count": len(backups),
        "profile_row_count": len(profiles),
        "solver_run_invocations": 0,
        "sealed_target_reads": 0,
    }
    write_json(OUT / "m4_standalone_validator_report.json", report)
    refresh_checksum_manifest()
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
