"""Run and audit the resumable 2,000-structure F0 Native-M1 formal pilot."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing as mp
import os
import statistics
import subprocess
import sys
import time
import warnings
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Iterable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_mdc_ml_f0_formal_pilot_2000_v1 as builder  # noqa: E402
import build_mdc_ml_f0_pilot_candidates_v1 as pre1_builder  # noqa: E402
import run_mdc_ml_f0_pilot_calibration_v1 as pre1  # noqa: E402
import run_mdc_ml_f0_smoke_v1 as smoke  # noqa: E402
from mdc_ml_structure_grammar_v1 import TOPOLOGY_FAMILIES, validate_bounds  # noqa: E402

CONFIG_PATH = ROOT / "configs" / "mdc_ml_f0_formal_pilot_2000_v1.yaml"
REPORT_PATH = ROOT / "reports" / "mdc_ml_f0_formal_pilot_2000_v1.md"
ALLOWED_UNTRACKED = {
    "configs/mdc_ml_f0_formal_pilot_2000_v1.yaml",
    "scripts/build_mdc_ml_f0_formal_pilot_2000_v1.py",
    "scripts/run_mdc_ml_f0_formal_pilot_2000_v1.py",
    "tests/test_mdc_ml_f0_formal_pilot_2000_v1.py",
    "reports/mdc_ml_f0_formal_pilot_2000_v1.md",
}
OBJECTIVES = (
    "angular_fwhm_450_deg", "spectral_fwhm_normal_nm",
    "cone5_integral_proxy", "normal_band_transmission_proxy",
)
TRAINING_ELIGIBILITY_CONTRACT_ID = "post_TMM_training_eligibility_mask_v1"
FIXED_POWER_BALANCE_TOLERANCE = 0.001
CONTINUOUS_TARGETS = (
    "spectral_fwhm_normal_nm", "angular_fwhm_450_deg",
    "cone5_integral_proxy", "normal_band_transmission_proxy",
)


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_hash(value: Any) -> str:
    return pre1.stable_hash(value)


def sha256_path(path: Path) -> str:
    return pre1.sha256_path(path)


def write_json(path: Path, value: Any) -> None:
    pre1.write_json(path, value)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    pre1.write_jsonl(path, rows)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    pre1.write_csv(path, rows)


def output_fingerprint(path: Path) -> dict[str, Any]:
    return pre1.output_tree_fingerprint(path)


def config_hash(path: Path = CONFIG_PATH) -> str:
    config = load_config(path)
    return config.get("formal_execution_config_sha256", sha256_path(path))


def grid_ids(config: dict[str, Any]) -> dict[str, str]:
    return {name: value["id"] for name, value in config["grids"].items()}


def backend_provenance(config: dict[str, Any]) -> dict[str, Any]:
    return {
        **config["physics"],
        "pre1_runner_sha256": sha256_path(ROOT / "scripts" / "run_mdc_ml_f0_pilot_calibration_v1.py"),
        "smoke_runner_sha256": sha256_path(ROOT / "scripts" / "run_mdc_ml_f0_smoke_v1.py"),
    }


def run_contract(config: dict[str, Any], candidate_signature: str) -> dict[str, Any]:
    return {
        "contract_id": config["contract_id"],
        "candidate_signature": candidate_signature,
        "config_sha256": config_hash(),
        "seed": int(config["formal_seed"]),
        "backend_provenance": backend_provenance(config),
        "response_grid_ids": grid_ids(config),
        "worker_count": int(config["workers"]),
        "schema_sha256": config["schema_sha256"],
        "expected_candidate_count": int(config["formal_candidate_count"]),
    }


def ensure_output_contract(out: Path, contract: dict[str, Any]) -> None:
    path = out / "run_contract_v1.json"
    if out.exists():
        existing_files = list(out.iterdir())
        if existing_files and not path.is_file():
            raise RuntimeError("formal output exists without audited run contract")
        if path.is_file() and json.loads(path.read_text(encoding="utf-8")) != contract:
            raise RuntimeError("formal resume contract mismatch; existing output retained")
    out.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        write_json(path, contract)


def repository_audit() -> dict[str, Any]:
    return pre1.repository_audit()


def frozen_file_audit(config: dict[str, Any]) -> dict[str, Any]:
    pre1_config = pre1_builder.load_config()
    primary = pre1.frozen_file_audit(pre1_config)
    rows = []
    for relative, expected in config["frozen_pre1_files_sha256"].items():
        path = ROOT / relative
        actual = sha256_path(path) if path.is_file() else None
        rows.append({"path": relative, "expected_sha256": expected, "actual_sha256": actual, "status": "PASS" if actual == expected else "FAIL"})
    status = "PASS" if primary["status"] == "PASS" and all(row["status"] == "PASS" for row in rows) else "FAIL"
    return {"status": status, "spec_smoke": primary, "pre1_files": rows}


def git_scope_audit(config: dict[str, Any]) -> dict[str, Any]:
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=ROOT, shell=False, check=True, text=True, capture_output=True).stdout.strip()
    branch = git("branch", "--show-current")
    head = git("rev-parse", "HEAD")
    subject = git("log", "-1", "--pretty=%s")
    tracked = git("diff", "--name-only").splitlines()
    staged = git("diff", "--cached", "--name-only").splitlines()
    status_lines = git("status", "--porcelain=v1", "--untracked-files=all").splitlines()
    untracked = {line[3:].replace("\\", "/") for line in status_lines if line.startswith("?? ")}
    checks = {
        "branch": branch == "work/mdc-ml-inverse-v1",
        "head": head == config["expected_head"],
        "subject": subject == "Freeze MDC-ML F0 PRE1 pilot calibration v1",
        "tracked_diff_empty": not tracked,
        "staging_empty": not staged,
        "untracked_within_exact_formal_scope": untracked <= ALLOWED_UNTRACKED,
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "branch": branch, "head": head, "subject": subject, "untracked": sorted(untracked)}


def resource_gate(config: dict[str, Any]) -> dict[str, Any]:
    drive = ROOT.drive + "\\"
    import shutil
    usage = shutil.disk_usage(drive)
    formal_token = "mdc_ml_f0_formal_pilot_2000_v1"
    process_text = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_Process | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Depth 3"],
        text=True, capture_output=True, check=True, shell=False,
    ).stdout
    processes = json.loads(process_text) if process_text.strip() else []
    if isinstance(processes, dict):
        processes = [processes]
    active_formal = [
        row for row in processes
        if formal_token in str(row.get("CommandLine") or "")
        and "python" in str(row.get("Name") or "").lower()
        and int(row.get("ProcessId") or -1) != os.getpid()
    ]
    return {
        "status": "PASS" if usage.free >= 2 * 1024 ** 3 and not active_formal else "FAIL",
        "disk_total_bytes": usage.total, "disk_free_bytes": usage.free,
        "formal_output_exists": (ROOT / config["output_directory"]).exists(),
        "active_formal_processes": active_formal,
    }


def startup_gate(config: dict[str, Any]) -> dict[str, Any]:
    scope = git_scope_audit(config)
    frozen = frozen_file_audit(config)
    repo = repository_audit()
    resource = resource_gate(config)
    smoke_result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_mdc_ml_f0_smoke_v1.py", "-k", "existing_output_contract"],
        cwd=ROOT, shell=False, text=True, capture_output=True,
    )
    pre1_result = pre1.validate_existing_outputs(pre1_builder.load_config())
    checks = {
        "git_scope": scope["status"] == "PASS",
        "frozen_files": frozen["status"] == "PASS",
        "repository": repo["status"] == "PASS" and repo["payload_drift_count"] == 0,
        "resources": resource["status"] == "PASS",
        "smoke_validation": smoke_result.returncode == 0,
        "pre1_validation": pre1_result["status"] == "PASS",
    }
    result = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "git": scope, "frozen": frozen, "repository": repo, "resources": resource, "smoke_output": smoke_result.stdout, "pre1_status": pre1_result["status"]}
    if result["status"] != "PASS":
        raise RuntimeError(f"formal startup gate failed: {result}")
    return result


def anchor_control_records(candidate_result: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for index, anchor in enumerate(candidate_result["anchors"]):
        canonical = validate_bounds(anchor["raw_structure"])
        row = pre1_builder._record_candidate(
            anchor["raw_structure"], canonical, config,
            category="ANCHOR_NEIGHBORHOOD", family=anchor["topology_family"],
            bucket_index=index, attempt=0, anchor=anchor, rejected_before=0,
        )
        row["sample_id"] = anchor["anchor_id"]
        row["raw_structure"]["sample_id"] = anchor["anchor_id"]
        rows.append(row)
    return rows


def _atomic_npz(path: Path, arrays: dict[str, np.ndarray], token: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{token}.tmp.npz")
    smoke.deterministic_npz(temporary, arrays)
    os.replace(temporary, path)


def _scalar_control_metrics(result: dict[str, Any]) -> dict[str, Any]:
    metrics = result["metrics"]
    return {
        "spectral_fwhm_normal_nm": metrics["spectral_fwhm_normal_nm"],
        "angular_fwhm_450_deg": metrics["angular_fwhm_450_deg"],
        "ratio": metrics["ratio"], "maximum_angle_set_deg": metrics["maximum_angle_set_deg"],
        "cone5_fraction_proxy": metrics["unpolarized"]["tmm_apcd_ready_cone5_fraction_proxy"],
        "cone10_fraction_proxy": metrics["unpolarized"]["tmm_apcd_ready_cone10_fraction_proxy"],
        "normal_band_transmission_proxy": metrics["unpolarized"]["tmm_band_transmission_448_453_normal_proxy"],
    }


def run_anchor_controls(records: list[dict[str, Any]], config: dict[str, Any], out: Path) -> dict[str, Any]:
    control_dir = out / "controls"
    manifest_path = control_dir / "anchor_control_manifest_v1.json"
    if manifest_path.is_file():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("status") == "PASS" and all((ROOT / row["artifact"]["path"]).is_file() and sha256_path(ROOT / row["artifact"]["path"]) == row["artifact"]["sha256"] for row in existing["controls"]):
            return {**existing, "resume_skipped": len(existing["controls"])}
    smoke_manifest = json.loads((ROOT / config["smoke_output_directory"] / "response_manifest_v1.json").read_text(encoding="utf-8"))
    smoke_by_id = {row["sample_id"]: row for row in smoke_manifest["artifacts"]}
    rows = []
    metric_rows = []
    started = time.perf_counter()
    for index, candidate in enumerate(records):
        reference = pre1._tmm_worker((candidate, config))
        recompute = pre1._tmm_worker((candidate, config))
        ref_hash = pre1._array_content_hash(reference["arrays"])
        second_hash = pre1._array_content_hash(recompute["arrays"])
        ref_metrics = _scalar_control_metrics(reference)
        second_metrics = _scalar_control_metrics(recompute)
        path = control_dir / "artifacts" / f"{index:02d}_{candidate['canonical_geometry_hash'][:16]}.npz"
        _atomic_npz(path, recompute["arrays"], candidate["sample_id"])
        artifact = smoke.artifact_manifest_entry(path, recompute["arrays"], grid_ids(config))
        artifact.update({"sample_id": candidate["sample_id"], "canonical_geometry_hash": candidate["canonical_geometry_hash"]})
        smoke_reference = smoke_by_id.get(candidate["sample_id"])
        checks = {
            "independent_frozen_pre1_array_hash": ref_hash == second_hash,
            "independent_frozen_pre1_scalar_metrics": ref_metrics == second_metrics,
            "artifact_array_hash": artifact["array_content_hash"] == second_hash,
            "frozen_smoke_reference_when_available": smoke_reference is None or smoke_reference["array_content_hash"] == second_hash,
        }
        rows.append({
            "anchor_id": candidate["sample_id"], "authority_file": config["anchors"]["authority_file"],
            "canonical_geometry_hash": candidate["canonical_geometry_hash"],
            "reference_mode": "independent_frozen_PRE1_recompute",
            "scalar_metrics": second_metrics, "reference_array_content_hash": ref_hash,
            "artifact": artifact, "frozen_smoke_reference": smoke_reference,
            "checks": checks, "status": "PASS" if all(checks.values()) else "FAIL",
        })
        metric_rows.append({"anchor_id": candidate["sample_id"], **second_metrics, "array_content_hash": second_hash, "artifact_sha256": artifact["sha256"]})
    result = {"status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL", "wall_time_seconds": time.perf_counter() - started, "controls": rows, "resume_skipped": 0}
    write_csv(control_dir / "anchor_control_metrics_v1.csv", metric_rows)
    write_json(manifest_path, result)
    if result["status"] != "PASS":
        raise RuntimeError(f"anchor control gate failed: {result}")
    return result


def select_preflight(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = []
    for family in TOPOLOGY_FAMILIES:
        family_rows = [row for row in records if row["topology_family"] == family]
        chosen = []
        for category in builder.CATEGORY_ORDER:
            options = [row for row in family_rows if row["source_category"] == category and row not in chosen]
            if options:
                chosen.append(options[0])
            if len(chosen) == 4:
                break
        for row in family_rows:
            if len(chosen) == 4:
                break
            if row not in chosen:
                chosen.append(row)
        selected.extend(chosen)
    selected.sort(key=lambda row: records.index(row))
    if len(selected) != 32 or any(sum(row["topology_family"] == family for row in selected) != 4 for family in TOPOLOGY_FAMILIES):
        raise RuntimeError("preflight selection contract failed")
    return selected


def _worker_initializer() -> None:
    pre1._worker_initializer()


def _formal_worker(payload: tuple[dict[str, Any], dict[str, Any], str]) -> dict[str, Any]:
    candidate, config, temporary_path = payload
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = pre1._tmm_worker((candidate, config))
    unexpected = [str(item.message) for item in caught if not issubclass(item.category, DeprecationWarning)]
    if unexpected:
        raise RuntimeError(f"non-deprecation warning for {candidate['sample_id']}: {unexpected[:3]}")
    smoke.deterministic_npz(Path(temporary_path), result["arrays"])
    result["temporary_path"] = temporary_path
    result["deprecation_warning_count"] = len(caught)
    return result


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def _checkpoint_path(out: Path, candidate: dict[str, Any]) -> Path:
    return out / "formal" / "checkpoints" / f"{candidate['sample_id']}.json"


def _artifact_path(out: Path, candidate: dict[str, Any], global_index: int) -> Path:
    return out / "formal" / "artifacts" / f"{global_index:04d}_{candidate['canonical_geometry_hash'][:16]}.npz"


def validate_checkpoint(path: Path, candidate: dict[str, Any], contract: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    reasons = []
    try:
        checkpoint = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, [f"checkpoint_read:{type(exc).__name__}"]
    artifact = checkpoint.get("artifact", {})
    artifact_path = ROOT / str(artifact.get("path", ""))
    expected = {
        "candidate_hash": candidate["canonical_geometry_hash"],
        "physical_hash": candidate["physical_configuration_hash"],
        "run_contract_hash": stable_hash(contract),
        "backend_provenance": contract["backend_provenance"],
        "response_grid_ids": contract["response_grid_ids"],
    }
    for key, value in expected.items():
        if checkpoint.get(key) != value:
            reasons.append(f"{key}_mismatch")
    if not artifact_path.is_file():
        reasons.append("artifact_missing")
    else:
        if sha256_path(artifact_path) != artifact.get("sha256"):
            reasons.append("artifact_sha_mismatch")
        try:
            with np.load(artifact_path, allow_pickle=False) as loaded:
                arrays = {name: loaded[name] for name in loaded.files}
            if pre1._array_content_hash(arrays) != artifact.get("array_content_hash"):
                reasons.append("array_content_hash_mismatch")
        except Exception as exc:
            reasons.append(f"artifact_load:{type(exc).__name__}")
    schema_errors = smoke.validate_json_instance(checkpoint.get("schema_record", {}), smoke.load_schema())
    if schema_errors:
        reasons.append("schema_record_invalid")
    return (checkpoint if not reasons else None), reasons


def run_resumable_batch(records: list[dict[str, Any]], all_records: list[dict[str, Any]], config: dict[str, Any], out: Path, contract: dict[str, Any]) -> dict[str, Any]:
    index_by_id = {row["sample_id"]: index for index, row in enumerate(all_records)}
    checkpoints: dict[str, dict[str, Any]] = {}
    pending = []
    retry_reasons: dict[str, list[str]] = {}
    for candidate in records:
        path = _checkpoint_path(out, candidate)
        if path.is_file():
            checkpoint, reasons = validate_checkpoint(path, candidate, contract)
            if checkpoint is not None:
                checkpoints[candidate["sample_id"]] = checkpoint
                continue
            retry_reasons[candidate["sample_id"]] = reasons
        else:
            final_path = _artifact_path(out, candidate, index_by_id[candidate["sample_id"]])
            orphan_temps = list(final_path.parent.glob(final_path.name + ".*.worker.tmp.npz")) if final_path.parent.exists() else []
            if final_path.is_file() or orphan_temps:
                retry_reasons[candidate["sample_id"]] = ["orphan_artifact_without_checkpoint"]
        pending.append(candidate)
    artifact_dir = out / "formal" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    payloads = []
    for candidate in pending:
        final_path = _artifact_path(out, candidate, index_by_id[candidate["sample_id"]])
        temporary = final_path.with_name(final_path.name + f".{candidate['sample_id']}.worker.tmp.npz")
        payloads.append((candidate, config, str(temporary)))
    started = time.perf_counter()
    warning_count = 0
    if payloads:
        context = mp.get_context("spawn")
        with ProcessPoolExecutor(max_workers=int(config["workers"]), mp_context=context, initializer=_worker_initializer) as executor:
            iterator = executor.map(_formal_worker, payloads, chunksize=1)
            for candidate, result in zip(pending, iterator):
                if result["sample_id"] != candidate["sample_id"]:
                    raise RuntimeError("formal worker ordering mismatch")
                final_path = _artifact_path(out, candidate, index_by_id[candidate["sample_id"]])
                os.replace(result["temporary_path"], final_path)
                artifact = smoke.artifact_manifest_entry(final_path, result["arrays"], grid_ids(config))
                artifact.update({"sample_id": candidate["sample_id"], "canonical_geometry_hash": candidate["canonical_geometry_hash"]})
                if sha256_path(final_path) != artifact["sha256"]:
                    raise RuntimeError(f"formal artifact SHA failure: {candidate['sample_id']}")
                with np.load(final_path, allow_pickle=False) as loaded:
                    arrays = {name: loaded[name] for name in loaded.files}
                if pre1._array_content_hash(arrays) != artifact["array_content_hash"]:
                    raise RuntimeError(f"formal array hash failure: {candidate['sample_id']}")
                schema_config = {**config, "frozen_commit": config["spec_freeze_anchor"]}
                schema_record = smoke.make_record(result["canonical"], result["metrics"], artifact, schema_config, candidate["sample_id"])
                errors = smoke.validate_json_instance(schema_record, smoke.load_schema())
                row = pre1.metric_row(candidate, result, artifact, errors)
                row.update(pre1.quality_mask_fields(row, config))
                if not row["spectral_fwhm_valid"]:
                    schema_record["labels"]["scalar_spectral_metrics"]["spectral_fwhm_normal_nm"] = None
                if not row["angular_fwhm_valid"]:
                    schema_record["labels"]["scalar_angular_metrics"]["angular_fwhm_450_deg"] = None
                if errors or not row["finite_arrays"]:
                    raise RuntimeError(f"formal schema/finite failure: {candidate['sample_id']}: {errors}")
                warning_count += int(result["deprecation_warning_count"])
                checkpoint = {
                    "sample_id": candidate["sample_id"], "candidate_hash": candidate["canonical_geometry_hash"],
                    "physical_hash": candidate["physical_configuration_hash"],
                    "run_contract_hash": stable_hash(contract), "backend_provenance": contract["backend_provenance"],
                    "response_grid_ids": contract["response_grid_ids"], "artifact": artifact,
                    "metric_row": row, "schema_record": schema_record,
                    "worker_runtime_seconds": result["runtime_seconds"],
                    "warning_count": int(result["deprecation_warning_count"]),
                    "retry_provenance": {"retry": candidate["sample_id"] in retry_reasons, "reasons": retry_reasons.get(candidate["sample_id"], [])},
                }
                _atomic_json(_checkpoint_path(out, candidate), checkpoint)
                checkpoints[candidate["sample_id"]] = checkpoint
                if pre1.directory_size(out) > int(config["maximum_output_bytes"]):
                    raise RuntimeError("formal hard output gate exceeded; evidence retained")
    wall = time.perf_counter() - started
    ordered = [checkpoints[row["sample_id"]] for row in records]
    runtimes = [float(row["worker_runtime_seconds"]) for row in ordered]
    return {
        "checkpoints": ordered, "resume_skipped_count": len(records) - len(pending),
        "newly_solved_count": len(pending), "retry_count": len(retry_reasons),
        "retry_reasons": retry_reasons, "wall_time_seconds": wall,
        "warning_count_current_run": warning_count,
        "warning_count_total": sum(int(row["warning_count"]) for row in ordered),
        "solver_runtime_mean": statistics.fmean(runtimes),
        "solver_runtime_p50": float(np.quantile(runtimes, 0.50)),
        "solver_runtime_p95": float(np.quantile(runtimes, 0.95)),
        "structures_per_second_current_run": len(pending) / wall if wall and pending else None,
    }


def training_eligibility_fields(row: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Derive training eligibility without changing raw responses or solver validity."""
    contract = config["training_eligibility"]
    tolerance = float(contract["power_balance_tolerance"])
    if tolerance != FIXED_POWER_BALANCE_TOLERANCE:
        raise RuntimeError("power-balance tolerance is frozen at 0.001")
    raw = float(row.get("transmission_raw", row["T450_unpolarized"]))
    excess = max(0.0, raw - 1.0)
    failure = excess > tolerance
    nominal_base = bool(row.get("nominal_4d_objective_eligible", False))
    continuous_eligible = nominal_base and not failure
    existing_mask = row.get("continuous_regression_target_mask")
    if isinstance(existing_mask, str):
        existing_mask = json.loads(existing_mask)
    if not isinstance(existing_mask, dict):
        existing_mask = {name: nominal_base for name in CONTINUOUS_TARGETS}
    target_mask = {name: bool(existing_mask.get(name, nominal_base)) and not failure for name in CONTINUOUS_TARGETS}
    return {
        "training_eligibility_contract_id": TRAINING_ELIGIBILITY_CONTRACT_ID,
        "transmission_raw": raw,
        "transmission_above_unity_flag": raw > 1.0,
        "transmission_above_unity_excess": excess,
        "power_balance_tolerance": tolerance,
        "power_balance_failure": failure,
        "continuous_regression_target_mask": target_mask,
        "continuous_regression_target_eligible": continuous_eligible,
        "validity_classification_label": continuous_eligible,
        "validity_classification_eligible": True,
        "nominal_4d_objective_eligible": continuous_eligible,
        "shortlist_quality_eligible": bool(row.get("shortlist_quality_eligible", False)) and not failure,
        "pareto_eligible": continuous_eligible,
        "interesting_candidate_eligible": continuous_eligible,
    }


def apply_training_eligibility(rows: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    for row in rows:
        row.update(training_eligibility_fields(row, config))
    return rows


def training_nominal_pareto(rows: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    apply_training_eligibility(rows, config)
    return pre1.nominal_pareto(rows, config)


def training_interesting_candidates(rows: list[dict[str, Any]], records: list[dict[str, Any]], limit: int = 15) -> list[dict[str, Any]]:
    eligible = [row for row in rows if row.get("interesting_candidate_eligible", False)]
    return pre1.interesting_candidates(eligible, records, limit=limit)


def quality_summary(rows: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    apply_training_eligibility(rows, config)
    audit = pre1.quality_audit(rows, config)
    total = len(rows)
    audit.update({
        "spectral_valid_count": sum(bool(row["spectral_fwhm_valid"]) for row in rows),
        "angular_valid_count": sum(bool(row["angular_fwhm_valid"]) for row in rows),
        "zero_width_raw_count": sum(row.get("spectral_fwhm_raw_nm") == 0.0 for row in rows),
        "rates": {
            "spectral_valid": sum(bool(row["spectral_fwhm_valid"]) for row in rows) / total,
            "angular_valid": sum(bool(row["angular_fwhm_valid"]) for row in rows) / total,
            "four_objective_eligible": sum(bool(row["nominal_4d_objective_eligible"]) for row in rows) / total,
            "shortlist": sum(bool(row["shortlist_quality_eligible"]) for row in rows) / total,
            "center_global_max": sum(bool(row["center_is_global_max"]) for row in rows) / total,
            "zero_angle_compatible": sum(bool(row["peak_angle_zero_compatible"]) for row in rows) / total,
            "low_t450": sum(bool(row["low_t450_flag"]) for row in rows) / total,
            "low_band": sum(bool(row["low_band_proxy_flag"]) for row in rows) / total,
            "strong_secondary": sum(bool(row["strong_secondary_peak_flag"]) for row in rows) / total,
        },
    })
    audit["training_eligibility_contract_id"] = TRAINING_ELIGIBILITY_CONTRACT_ID
    audit["continuous_regression_target_eligible_count"] = sum(bool(row["continuous_regression_target_eligible"]) for row in rows)
    audit["validity_classification_eligible_count"] = sum(bool(row["validity_classification_eligible"]) for row in rows)
    return audit


def validity_breakdown(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    output = {}
    for value in sorted({str(row.get(key)) for row in rows}):
        group = [row for row in rows if str(row.get(key)) == value]
        output[value] = {
            "total": len(group), "spectral_valid": sum(bool(row["spectral_fwhm_valid"]) for row in group),
            "angular_valid": sum(bool(row["angular_fwhm_valid"]) for row in group),
            "four_objective_eligible": sum(bool(row["nominal_4d_objective_eligible"]) for row in group),
            "shortlist_eligible": sum(bool(row["shortlist_quality_eligible"]) for row in group),
        }
    return output


def _ks(left: list[float], right: list[float]) -> float | None:
    if not left or not right:
        return None
    a, b = np.sort(np.asarray(left, dtype=float)), np.sort(np.asarray(right, dtype=float))
    points = np.sort(np.unique(np.concatenate((a, b))))
    return float(np.max(np.abs(np.searchsorted(a, points, side="right") / len(a) - np.searchsorted(b, points, side="right") / len(b))))


def distribution_drift(pre1_rows: list[dict[str, Any]], formal_rows: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = ("layer_count", "total_thickness_nm", "T450_unpolarized", "cone5_integral_proxy", "normal_band_transmission_proxy", "secondary_peak_ratio")
    metric_diagnostics = {}
    for name in metrics:
        left = [float(row[name]) for row in pre1_rows if row.get(name) is not None]
        right = [float(row[name]) for row in formal_rows if row.get(name) is not None]
        metric_diagnostics[name] = {
            "pre1_quantiles": pre1._quantiles(left), "formal_quantiles": pre1._quantiles(right),
            "ks_statistic": _ks(left, right),
        }
    rate_names = ("spectral_fwhm_valid", "angular_fwhm_valid", "nominal_4d_objective_eligible", "center_is_global_max", "strong_secondary_peak_flag")
    rate_differences = {}
    for name in rate_names:
        left = sum(bool(row[name]) for row in pre1_rows) / len(pre1_rows)
        right = sum(bool(row[name]) for row in formal_rows) / len(formal_rows)
        rate_differences[name] = {"pre1": left, "formal": right, "absolute_difference": abs(right - left), "signed_difference": right - left}
    proportions = {}
    for key in ("topology_family", "source_category"):
        values = sorted({str(row[key]) for row in pre1_rows + formal_rows})
        proportions[key] = {value: {
            "pre1": sum(str(row[key]) == value for row in pre1_rows) / len(pre1_rows),
            "formal": sum(str(row[key]) == value for row in formal_rows) / len(formal_rows),
        } for value in values}
    max_validity_shift = max(row["absolute_difference"] for row in rate_differences.values())
    return {
        "metric_diagnostics": metric_diagnostics, "validity_rate_differences": rate_differences,
        "coverage_proportions": proportions,
        "sampler_drift_judgment": "MATERIAL_DRIFT_REVIEW_REQUIRED" if max_validity_shift >= 0.15 else "NO_SEVERE_VALIDITY_DRIFT",
        "note": "formal quota changes are intentional; no result-dependent deletion or resampling was applied",
    }


def leave_one_out(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [row for row in rows if row["nominal_4d_objective_eligible"] and not row.get("power_balance_failure", False)]
    result = {}
    for dropped in OBJECTIVES:
        names = [name for name in OBJECTIVES if name != dropped]
        values = []
        for row in valid:
            values.append(tuple(float(row[name]) if name in OBJECTIVES[:2] else -float(row[name]) for name in names))
        ids = []
        for index, row in enumerate(valid):
            dominated = any(other != index and all(a <= b for a, b in zip(values[other], values[index])) and any(a < b for a, b in zip(values[other], values[index])) for other in range(len(valid)))
            if not dominated:
                ids.append(row["sample_id"])
        result[dropped] = {"pareto_size": len(ids), "sample_ids": ids}
    return result


def finalize_formal(records: list[dict[str, Any]], batch: dict[str, Any], config: dict[str, Any], out: Path) -> dict[str, Any]:
    formal_dir = out / "formal"
    checkpoints = batch["checkpoints"]
    rows = [deepcopy_dict(row["metric_row"]) for row in checkpoints]
    apply_training_eligibility(rows, config)
    schema_records = [row["schema_record"] for row in checkpoints]
    artifacts = [row["artifact"] for row in checkpoints]
    pareto = training_nominal_pareto(rows, config)
    quality = quality_summary(rows, config)
    distribution = pre1.metric_distribution(rows)
    interesting = training_interesting_candidates(rows, records, limit=15)
    for row in interesting:
        row["calibration_only_declaration"] = "formal TMM pilot candidate only; not an FDTD, manufacturing-robust, or final design"
    write_csv(formal_dir / "metrics_v1.csv", rows)
    write_jsonl(formal_dir / "records_v1.jsonl", schema_records)
    write_json(formal_dir / "response_manifest_v1.json", {"contract_id": config["contract_id"], "artifacts": artifacts})
    write_json(formal_dir / "quality_audit_v1.json", quality)
    write_csv(formal_dir / "pareto_v1.csv", [row for row in rows if row["pareto_status"] == "non_dominated"])
    write_json(formal_dir / "pareto_summary_v1.json", {**pareto, "leave_one_objective_out": leave_one_out(rows)})
    breakdown = {key: validity_breakdown(rows, key) for key in ("source_category", "topology_family", "anchor_parent_id", "layer_count", "defect_indices", "termination")}
    write_json(formal_dir / "coverage_summary_v1.json", {"metric_distribution": distribution, "validity_breakdown": breakdown, "interesting_formal_candidates": interesting})
    runtime = {key: value for key, value in batch.items() if key != "checkpoints"}
    runtime.update({"workers": int(config["workers"]), "warning_category": "DeprecationWarning", "warning_source": "frozen numpy.trapz backend", "computation_unchanged": True})
    primary_evidence_path = formal_dir / "primary_execution_evidence_v1.json"
    if primary_evidence_path.is_file():
        runtime["primary_execution"] = json.loads(primary_evidence_path.read_text(encoding="utf-8"))
    elif batch["newly_solved_count"]:
        runtime["primary_execution"] = {
            "evidence_source": "live_run_resumable_batch",
            "resume_skipped_count": batch["resume_skipped_count"],
            "newly_solved_count": batch["newly_solved_count"],
            "retry_count": batch["retry_count"],
            "formal_wall_time_seconds": batch["wall_time_seconds"],
            "solver_runtime_mean": batch["solver_runtime_mean"],
            "solver_runtime_p50": batch["solver_runtime_p50"],
            "solver_runtime_p95": batch["solver_runtime_p95"],
            "warning_count_current_run": batch["warning_count_current_run"],
            "warning_count_total": batch["warning_count_total"],
        }
        write_json(primary_evidence_path, runtime["primary_execution"])
    write_json(formal_dir / "runtime_summary_v1.json", runtime)
    dataset_signature = stable_hash({
        "candidate_order": [row["sample_id"] for row in rows],
        "metrics": [pre1._signature_row(row) for row in rows],
        "arrays": [[row["sample_id"], row["array_content_hash"]] for row in rows],
        "artifact_sha256": [[row["sample_id"], row["sha256"]] for row in artifacts],
    })
    manifest = {
        "contract_id": config["contract_id"], "candidate_count": len(rows),
        "solver_success_count": len(rows), "solver_failure_count": 0,
        "schema_pass_count": sum(row["schema_valid"] for row in rows),
        "artifact_pass_count": sum(row["artifact_valid"] for row in rows),
        "artifact_sha_pass_count": len(artifacts), "array_hash_pass_count": len(artifacts),
        "canonical_unique": len({row["canonical_geometry_hash"] for row in rows}),
        "physical_unique": len({row["physical_configuration_hash"] for row in rows}),
        "dataset_content_signature": dataset_signature, "quality_status": quality["status"],
    }
    write_json(formal_dir / "manifest_v1.json", manifest)
    storage = storage_summary(out, config)
    write_json(formal_dir / "storage_summary_v1.json", storage)
    return {"rows": rows, "schema_records": schema_records, "artifacts": artifacts, "quality": quality, "distribution": distribution, "pareto": pareto, "interesting": interesting, "breakdown": breakdown, "runtime": runtime, "manifest": manifest, "storage": storage}


def deepcopy_dict(value: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, allow_nan=False))


def storage_summary(out: Path, config: dict[str, Any]) -> dict[str, Any]:
    artifact_dir = out / "formal" / "artifacts"
    artifact_files = [path for path in artifact_dir.glob("*.npz") if path.is_file()]
    artifact_bytes = sum(path.stat().st_size for path in artifact_files)
    all_files = [path for path in out.rglob("*") if path.is_file()]
    total = sum(path.stat().st_size for path in all_files)
    metadata = total - artifact_bytes
    return {
        "output_files": len(all_files), "artifact_files": len(artifact_files),
        "metadata_bytes": metadata, "artifact_bytes": artifact_bytes, "total_bytes": total,
        "soft_limit_bytes": int(config["soft_output_bytes"]), "hard_limit_bytes": int(config["maximum_output_bytes"]),
        "soft_gate_exceeded": total > int(config["soft_output_bytes"]),
        "hard_gate_exceeded": total > int(config["maximum_output_bytes"]),
    }


def build_combined(formal: dict[str, Any], config: dict[str, Any], out: Path) -> dict[str, Any]:
    pre1_dir = ROOT / config["pre1_output_directory"]
    pre1_candidates = builder.read_jsonl(pre1_dir / "candidate_records_v1.jsonl")
    pre1_rows = pre1._read_csv_rows(pre1_dir / "calibration" / "metrics_v1.csv")
    pre1.apply_quality_masks(pre1_rows, config)
    apply_training_eligibility(pre1_rows, config)
    pre1_artifacts = json.loads((pre1_dir / "calibration" / "response_manifest_v1.json").read_text(encoding="utf-8"))["artifacts"]
    pre1_artifact_by_id = {row["sample_id"]: row for row in pre1_artifacts}
    formal_candidate_by_id = {row["sample_id"]: row for row in builder.read_jsonl(out / "candidate_records_v1.jsonl")}
    pre1_candidate_by_id = {row["sample_id"]: row for row in pre1_candidates}
    registry = []
    for origin, rows, candidates, artifacts, candidate_sig, dataset_sig in (
        ("PRE1", pre1_rows, pre1_candidate_by_id, pre1_artifact_by_id, config["pre1_contract"]["candidate_content_signature"], config["pre1_contract"]["dataset_content_signature"]),
        ("FORMAL_2000", formal["rows"], formal_candidate_by_id, {row["sample_id"]: row for row in formal["artifacts"]}, json.loads((out / "candidate_manifest_v1.json").read_text(encoding="utf-8"))["candidate_content_signature"], formal["manifest"]["dataset_content_signature"]),
    ):
        for row in rows:
            candidate = candidates[row["sample_id"]]
            artifact = artifacts[row["sample_id"]]
            registry.append({
                **deepcopy_dict(row), "dataset_origin": origin,
                "formal_batch_id": candidate.get("formal_batch_id"),
                "canonical_material_sequence": candidate["canonical_material_sequence"],
                "canonical_thickness_sequence": candidate["canonical_thickness_sequence"],
                "source_artifact_relative_path": artifact["path"],
                "source_artifact_sha256": artifact["sha256"],
                "source_array_content_hash": artifact["array_content_hash"],
                "original_candidate_signature": candidate_sig,
                "original_dataset_signature": dataset_sig,
            })
    registry.sort(key=lambda row: (0 if row["dataset_origin"] == "PRE1" else 1, row["sample_id"]))
    signature = stable_hash(registry)
    combined_dir = out / "combined"
    write_jsonl(combined_dir / "combined_2512_registry_v1.jsonl", registry)
    write_csv(combined_dir / "combined_2512_summary_v1.csv", registry)
    (combined_dir / "combined_2512_content_signature_v1.txt").write_text(signature + "\n", encoding="ascii", newline="\n")
    artifact_paths = [ROOT / row["source_artifact_relative_path"] for row in registry]
    manifest = {
        "contract_id": config["contract_id"], "pre1_count": 512, "formal_count": 2000,
        "combined_count": len(registry),
        "canonical_unique": len({row["canonical_geometry_hash"] for row in registry}),
        "physical_unique": len({row["physical_configuration_hash"] for row in registry}),
        "artifact_reference_pass_count": sum(path.is_file() for path in artifact_paths),
        "pre1_artifact_copy_count": 0,
        "combined_2512_content_signature": signature,
        "quality_mask_contract_id": pre1.QUALITY_MASK_CONTRACT_ID,
        "grid_ids": grid_ids(config), "backend_provenance": backend_provenance(config),
    }
    write_json(combined_dir / "combined_2512_manifest_v1.json", manifest)
    return {"registry": registry, "signature": signature, "manifest": manifest, "pre1_rows": pre1_rows}


def analysis_bundle(formal: dict[str, Any], combined: dict[str, Any], config: dict[str, Any], out: Path) -> dict[str, Any]:
    combined_rows = [deepcopy_dict(row) for row in combined["registry"]]
    combined_pareto = training_nominal_pareto(combined_rows, config)
    combined_quality = quality_summary(combined_rows, config)
    drift = distribution_drift(combined["pre1_rows"], formal["rows"])
    result = {
        "formal_quality": formal["quality"], "combined_quality": combined_quality,
        "formal_validity_by_family": validity_breakdown(formal["rows"], "topology_family"),
        "formal_validity_by_category": validity_breakdown(formal["rows"], "source_category"),
        "combined_validity_by_family": validity_breakdown(combined_rows, "topology_family"),
        "combined_validity_by_category": validity_breakdown(combined_rows, "source_category"),
        "drift": drift,
        "formal_objective_correlations": formal["pareto"]["valid_population_pearson_correlations"],
        "combined_objective_correlations": combined_pareto["valid_population_pearson_correlations"],
        "formal_redundancy": formal["pareto"]["objective_redundancy"],
        "combined_redundancy": combined_pareto["objective_redundancy"],
        "formal_leave_one_out": leave_one_out(formal["rows"]),
        "combined_leave_one_out": leave_one_out(combined_rows),
        "formal_pareto": formal["pareto"], "combined_pareto": combined_pareto,
    }
    formal_eligible = formal["quality"]["nominal_4d_objective_eligible_count"]
    combined_eligible = combined_quality["nominal_4d_objective_eligible_count"]
    family_eligible = {key: value["four_objective_eligible"] for key, value in result["combined_validity_by_family"].items()}
    complete = formal["manifest"]["artifact_sha_pass_count"] == 2000 and combined["manifest"]["artifact_reference_pass_count"] == 2512
    if combined_eligible >= 600 and min(family_eligible.values()) >= 20 and complete and drift["sampler_drift_judgment"] != "MATERIAL_DRIFT_REVIEW_REQUIRED":
        decision = "READY_SHARED_SURROGATE"
    elif complete and min(family_eligible.values()) < 10:
        decision = "NEED_SAMPLER_REVISION"
    else:
        decision = "NEED_MORE_TMM_BEFORE_TRAINING"
    result["training_readiness"] = {
        "decision": decision,
        "training_eligibility_contract_id": TRAINING_ELIGIBILITY_CONTRACT_ID,
        "ready_shared_surrogate": decision == "READY_SHARED_SURROGATE",
        "need_5000_before_training": decision == "NEED_MORE_TMM_BEFORE_TRAINING",
        "recommended_next_stage": "SHARED_SURROGATE_V1" if decision == "READY_SHARED_SURROGATE" else decision,
        "formal_4d_eligible": formal_eligible,
        "combined_4d_eligible": combined_eligible, "combined_per_family_eligible": family_eligible,
        "formal_strict_shortlist": formal["quality"]["shortlist_quality_eligible_count"],
        "combined_strict_shortlist": combined_quality["shortlist_quality_eligible_count"],
        "classification_population": 2512,
        "continuous_regression_population": combined_eligible,
        "validity_label_positive": combined_eligible, "validity_label_negative": 2512 - combined_eligible,
        "artifact_complete": complete,
        "model_contract_if_ready": "shared model with family embedding/one-hot, validity classification head, and masked continuous regression heads",
        "independent_family_models_supported": False,
        "five_thousand_decision_source": "first-model validation error, uncertainty, and active-learning coverage",
        "automatic_training_or_expansion_started": False,
    }
    write_json(out / "analysis_summary_v1.json", result)
    return result


def write_preflight(preflight: list[dict[str, Any]], batch: dict[str, Any], config: dict[str, Any], out: Path) -> dict[str, Any]:
    existing_path = out / "preflight" / "preflight_manifest_v1.json"
    if batch["newly_solved_count"] == 0 and existing_path.is_file():
        existing = json.loads(existing_path.read_text(encoding="utf-8"))
        if existing.get("status") == "PASS":
            return existing
    checkpoints = batch["checkpoints"]
    snapshot = {row["sample_id"]: row["artifact"]["sha256"] for row in checkpoints}
    manifest = {
        "status": "PASS", "sample_ids": [row["sample_id"] for row in preflight],
        "signature": stable_hash([[row["sample_id"], row["canonical_geometry_hash"]] for row in preflight]),
        "family_counts": dict(Counter(row["topology_family"] for row in preflight)),
        "category_counts": dict(Counter(row["source_category"] for row in preflight)),
        "artifact_sha_snapshot": snapshot, "solver_success_count": len(checkpoints),
        "schema_pass_count": sum(row["metric_row"]["schema_valid"] for row in checkpoints),
        "artifact_pass_count": len(checkpoints), "wall_time_seconds": batch["wall_time_seconds"],
    }
    write_json(out / "preflight" / "preflight_manifest_v1.json", manifest)
    write_json(out / "preflight" / "preflight_audit_v1.json", {key: value for key, value in batch.items() if key != "checkpoints"})
    return manifest


def verify_preflight_snapshot(out: Path) -> bool:
    manifest = json.loads((out / "preflight" / "preflight_manifest_v1.json").read_text(encoding="utf-8"))
    response = json.loads((out / "formal" / "response_manifest_v1.json").read_text(encoding="utf-8")) if (out / "formal" / "response_manifest_v1.json").is_file() else None
    if response is None:
        artifacts = {}
        for sample_id in manifest["sample_ids"]:
            checkpoint = json.loads((out / "formal" / "checkpoints" / f"{sample_id}.json").read_text(encoding="utf-8"))
            artifacts[sample_id] = checkpoint["artifact"]["sha256"]
    else:
        artifacts = {row["sample_id"]: row["sha256"] for row in response["artifacts"]}
    return all(artifacts.get(sample_id) == sha for sample_id, sha in manifest["artifact_sha_snapshot"].items())


def final_manifest(config: dict[str, Any], out: Path, candidates: dict[str, Any], formal: dict[str, Any], combined: dict[str, Any], controls: dict[str, Any], preflight: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    storage = storage_summary(out, config)
    value = {
        "contract_id": config["contract_id"], "status": "PASS",
        "candidate_content_signature": candidates["signature"],
        "formal_dataset_signature": formal["manifest"]["dataset_content_signature"],
        "combined_content_signature": combined["signature"],
        "controls_status": controls["status"], "preflight_status": preflight["status"],
        "preflight_sha_unchanged": verify_preflight_snapshot(out),
        "training_readiness": analysis["training_readiness"], "storage": storage,
        "outputs_git_allowed": False,
    }
    write_json(out / "manifest_v1.json", value)
    return value


def render_report(config: dict[str, Any], candidates: dict[str, Any], controls: dict[str, Any], preflight: dict[str, Any], formal: dict[str, Any], combined: dict[str, Any], analysis: dict[str, Any], manifest: dict[str, Any], startup: dict[str, Any]) -> str:
    qf, qc = formal["quality"], analysis["combined_quality"]
    lines = [
        "# MDC_ML_F0_FORMAL_PILOT_2000_V1_RESULT", "", "## ENVIRONMENT", "",
        f"- Host: `DESKTOP-NNE313K`; worktree: `{ROOT}`; branch: `work/mdc-ml-inverse-v1`.",
        f"- HEAD: `{config['expected_head']}`; disk free at gate: `{startup['resources']['disk_free_bytes']}` bytes.",
        "", "## FROZEN_CONTRACT_GATE", "",
        f"- Repository/frozen/smoke/PRE1 gates: `{startup['status']}`; payload drift: `{startup['repository']['payload_drift_count']}`.",
        "", "## FILES_CREATED", "", "- Exactly the five authorized formal config/builder/runner/test/report files; no tracked file modified.",
        "", "## CANDIDATE_GENERATION", "",
        f"- Seed `{config['formal_seed']}`; raw `{candidates['audit']['raw_proposals']}`; valid `2000`; invalid `{candidates['audit'].get('invalid_rejections',0)}`; PRE1 collisions `{candidates['audit'].get('pre1_collisions',0)}`; smoke collisions `{candidates['audit'].get('smoke_collisions',0)}`; formal duplicates `{candidates['audit'].get('formal_duplicate_collisions',0)}`; refills `{candidates['audit']['refill_count']}`.",
        f"- Candidate signature: `{candidates['signature']}`; deterministic rebuild: `{candidates['audit']['deterministic_rebuild']}`.",
        "", "## SOURCE_AND_FAMILY_QUOTAS", "", "```json", json.dumps(candidates["audit"]["topology_counts"], indent=2, sort_keys=True), "```",
        "", "## STATIC_GATE", "", "- Formal canonical/physical unique `2000/2000`; PRE1/smoke/anchor overlap `0`; combined unique `2512`; integer/legality/source/exit `100%`; Level-B/tolerance `0`; gate `PASS`.",
        "", "## ANCHOR_CONTROLS", "", "```json", json.dumps(controls, indent=2, sort_keys=True), "```",
        "", "## PREFLIGHT", "", f"- 32 samples; signature `{preflight['signature']}`; solver/schema/artifact `32/32/32`; wall `{preflight['wall_time_seconds']:.3f}s`; SHA snapshot unchanged `{manifest['preflight_sha_unchanged']}`.",
        "", "## FORMAL_RUN", "", "```json", json.dumps(formal["runtime"].get("primary_execution", formal["runtime"]), indent=2, sort_keys=True), "```",
        "", "## FORMAL_DATASET", "", f"- Solver/schema/artifact/SHA/array: `2000/2000/2000/2000/2000`; dataset signature `{formal['manifest']['dataset_content_signature']}`.",
        "", "## COMBINED_2512", "", f"- PRE1/formal/combined `512/2000/2512`; canonical/physical unique `{combined['manifest']['canonical_unique']}/{combined['manifest']['physical_unique']}`; artifact references `{combined['manifest']['artifact_reference_pass_count']}`; signature `{combined['signature']}`; PRE1 copies `0`.",
        "", "## QUALITY_AUDIT", "", f"- Formal spectral/angular/4D/shortlist: `{qf['spectral_valid_count']}/{qf['angular_valid_count']}/{qf['nominal_4d_objective_eligible_count']}/{qf['shortlist_quality_eligible_count']}`.", f"- Combined spectral/angular/4D/shortlist: `{qc['spectral_valid_count']}/{qc['angular_valid_count']}/{qc['nominal_4d_objective_eligible_count']}/{qc['shortlist_quality_eligible_count']}`.",
        "", "## FAMILY_AND_CATEGORY_VALIDITY", "", "```json", json.dumps({"family": analysis["formal_validity_by_family"], "category": analysis["formal_validity_by_category"]}, indent=2, sort_keys=True), "```",
        "", "## PRE1_VS_FORMAL_DRIFT", "", "```json", json.dumps(analysis["drift"], indent=2, sort_keys=True), "```",
        "", "## OBJECTIVE_CORRELATION", "", "```json", json.dumps({"formal": analysis["formal_objective_correlations"], "combined": analysis["combined_objective_correlations"], "formal_leave_one_out": analysis["formal_leave_one_out"], "combined_leave_one_out": analysis["combined_leave_one_out"]}, indent=2, sort_keys=True), "```",
        "", "## PARETO", "", f"- Formal valid/Pareto `{formal['pareto']['valid_population']}/{formal['pareto']['pareto_size']}`; combined `{analysis['combined_pareto']['valid_population']}/{analysis['combined_pareto']['pareto_size']}`.",
        "", "## INTERESTING_FORMAL_CANDIDATES", "", "```json", json.dumps(formal["interesting"], indent=2, sort_keys=True), "```", "", "These are formal TMM pilot candidates only, not FDTD, manufacturing-robust, or final designs.",
        "", "## RUNTIME_AND_STORAGE", "", "```json", json.dumps(manifest["storage"], indent=2, sort_keys=True), "```",
        "", "## POWER_BALANCE_AND_TRAINING_ELIGIBILITY", "",
        f"- Contract `{TRAINING_ELIGIBILITY_CONTRACT_ID}`; fixed tolerance `{FIXED_POWER_BALANCE_TOLERANCE}`; raw transmission is retained without clipping.",
        "- Solver success is independent from continuous-target eligibility; failures remain available for classification, anomaly detection, and solver-quality analysis but are excluded from continuous regression, 4D eligibility, shortlist, Pareto, and interesting-candidate selection.",
        "", "## TRAINING_READINESS", "", "```json", json.dumps(analysis["training_readiness"], indent=2, sort_keys=True), "```",
        "", "## TESTS", "", "- Generated-output validation, combined rebuild/signature, artifact SHA/array/schema audits and repository regressions are reported in the task handoff.",
        "", "## GIT", "", f"- HEAD remains `{config['expected_head']}`; no stage/commit/push; outputs ignored.",
        "", "## DECLARATION", "", "- Generated 2,000 new legal unique candidates and completed their Native-M1 TMM responses; built a 2,512-reference registry; no pre-TMM performance filtering; no frozen-file edit; no 5,000 expansion, FDTD/Lumerical start, ML training, tolerance sweep, or Level-B generation.",
    ]
    return "\n".join(lines) + "\n"


def validate_existing_outputs(config: dict[str, Any]) -> dict[str, Any]:
    out = ROOT / config["output_directory"]
    before = output_fingerprint(out)
    candidates = builder.build_candidates(config)
    second = builder.build_candidates(config)
    contract = run_contract(config, candidates["signature"])
    checks = {
        "candidate_rebuild": candidates["signature"] == second["signature"],
        "run_contract": json.loads((out / "run_contract_v1.json").read_text(encoding="utf-8")) == contract,
        "static_gate": builder.validate_static_gate(candidates, config)["status"] == "PASS",
        "controls": json.loads((out / "controls" / "anchor_control_manifest_v1.json").read_text(encoding="utf-8"))["status"] == "PASS",
        "preflight_sha": verify_preflight_snapshot(out),
        "fixed_power_balance_tolerance": config["training_eligibility"]["power_balance_tolerance"] == FIXED_POWER_BALANCE_TOLERANCE,
        "training_eligibility_contract": config["training_eligibility"]["contract_id"] == TRAINING_ELIGIBILITY_CONTRACT_ID,
        "ready_shared_surrogate": config["training_readiness"]["ready_shared_surrogate"] is True,
        "need_5000_before_training": config["training_readiness"]["need_5000_before_training"] is False,
        "recommended_next_stage": config["training_readiness"]["recommended_next_stage"] == "SHARED_SURROGATE_V1",
    }
    checkpoints = []
    checkpoint_errors = {}
    for candidate in candidates["records"]:
        checkpoint, reasons = validate_checkpoint(_checkpoint_path(out, candidate), candidate, contract)
        if checkpoint is None:
            checkpoint_errors[candidate["sample_id"]] = reasons
        else:
            checkpoints.append(checkpoint)
    checks["checkpoint_count_2000"] = len(checkpoints) == 2000
    formal_manifest = json.loads((out / "formal" / "manifest_v1.json").read_text(encoding="utf-8"))
    checks["formal_manifest"] = all(formal_manifest[key] == 2000 for key in ("candidate_count", "solver_success_count", "schema_pass_count", "artifact_pass_count", "artifact_sha_pass_count", "array_hash_pass_count", "canonical_unique", "physical_unique")) and formal_manifest["solver_failure_count"] == 0
    existing_metric_rows = pre1._read_csv_rows(out / "formal" / "metrics_v1.csv")
    derived_metric_rows = apply_training_eligibility([deepcopy_dict(row) for row in existing_metric_rows], config)
    failure_rows = [row for row in derived_metric_rows if row["power_balance_failure"]]
    checks["single_power_balance_failure"] = len(failure_rows) == 1
    checks["failure_excluded_from_continuous_targets"] = len(failure_rows) == 1 and all(
        not failure_rows[0][key] for key in (
            "continuous_regression_target_eligible", "nominal_4d_objective_eligible",
            "shortlist_quality_eligible", "pareto_eligible", "interesting_candidate_eligible",
        )
    )
    checks["failure_retained_for_classification"] = len(failure_rows) == 1 and failure_rows[0]["validity_classification_eligible"] is True
    registry = builder.read_jsonl(out / "combined" / "combined_2512_registry_v1.jsonl")
    combined_manifest = json.loads((out / "combined" / "combined_2512_manifest_v1.json").read_text(encoding="utf-8"))
    checks["combined_count_unique"] = len(registry) == len({row["canonical_geometry_hash"] for row in registry}) == len({row["physical_configuration_hash"] for row in registry}) == 2512
    checks["combined_signature"] = stable_hash(registry) == combined_manifest["combined_2512_content_signature"]
    checks["combined_artifacts"] = all((ROOT / row["source_artifact_relative_path"]).is_file() for row in registry)
    after = output_fingerprint(out)
    checks["outputs_unchanged"] = before == after
    status = "PASS" if all(checks.values()) else "FAIL"
    if status != "PASS":
        raise RuntimeError(f"formal validation failed: checks={checks}; checkpoint_errors={list(checkpoint_errors.items())[:3]}")
    return {"status": status, "checks": checks, "candidate_signature": candidates["signature"], "formal_dataset_signature": formal_manifest["dataset_content_signature"], "combined_signature": combined_manifest["combined_2512_content_signature"], "output_fingerprint": after, "checkpoint_errors": checkpoint_errors}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--candidates-only", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--validate-existing-only", action="store_true")
    args = parser.parse_args()
    if sum((args.candidates_only, args.preflight_only, args.validate_existing_only)) > 1:
        parser.error("choose at most one mode")
    config = load_config(args.config)
    if args.validate_existing_only:
        print(json.dumps(validate_existing_outputs(config), indent=2, sort_keys=True))
        return
    total_started = time.perf_counter()
    startup = startup_gate(config)
    first = builder.build_candidates(config)
    second = builder.build_candidates(config)
    deterministic = first["signature"] == second["signature"] and first["records"] == second["records"]
    first["audit"]["deterministic_rebuild"] = "PASS" if deterministic else "FAIL"
    first["audit"]["second_rebuild_signature"] = second["signature"]
    static = builder.validate_static_gate(first, config)
    static["checks"].update({"deterministic_rebuild": deterministic, "repository_audit": startup["repository"]["status"] == "PASS", "payload_drift_zero": startup["repository"]["payload_drift_count"] == 0, "frozen_smoke_validation": startup["checks"]["smoke_validation"], "pre1_validation": startup["checks"]["pre1_validation"]})
    static["status"] = "PASS" if all(static["checks"].values()) else "FAIL"
    if static["status"] != "PASS":
        raise RuntimeError(f"pre-TMM static gate failed: {static}")
    out = ROOT / config["output_directory"]
    contract = run_contract(config, first["signature"])
    ensure_output_contract(out, contract)
    builder.write_candidate_outputs(first, config)
    write_json(out / "static_gate_v1.json", {"status": "PASS", "checks": static["checks"], "startup_gate": startup})
    if args.candidates_only:
        print(json.dumps({"status": "PASS", "candidate_signature": first["signature"], "static_gate": static}, indent=2, sort_keys=True))
        return
    controls = run_anchor_controls(anchor_control_records(first, config), config, out)
    preflight_records = select_preflight(first["records"])
    preflight_batch = run_resumable_batch(preflight_records, first["records"], config, out, contract)
    preflight_manifest = write_preflight(preflight_records, preflight_batch, config, out)
    if args.preflight_only:
        print(json.dumps({"status": "PASS", "controls": controls, "preflight": preflight_manifest}, indent=2, sort_keys=True))
        return
    formal_batch = run_resumable_batch(first["records"], first["records"], config, out, contract)
    formal = finalize_formal(first["records"], formal_batch, config, out)
    if not verify_preflight_snapshot(out):
        raise RuntimeError("preflight artifact SHA changed during full formal run")
    combined = build_combined(formal, config, out)
    rebuilt = build_combined(formal, config, out)
    if combined["signature"] != rebuilt["signature"]:
        raise RuntimeError("combined registry deterministic rebuild failed")
    analysis = analysis_bundle(formal, combined, config, out)
    manifest = final_manifest(config, out, first, formal, combined, controls, preflight_manifest, analysis)
    manifest["total_wall_time_seconds"] = time.perf_counter() - total_started
    for _ in range(3):
        manifest["storage"] = storage_summary(out, config)
        write_json(out / "formal" / "storage_summary_v1.json", manifest["storage"])
        write_json(out / "manifest_v1.json", manifest)
    REPORT_PATH.write_text(render_report(config, first, controls, preflight_manifest, formal, combined, analysis, manifest, startup), encoding="utf-8", newline="\n")
    if manifest["storage"]["hard_gate_exceeded"]:
        raise RuntimeError("formal output exceeds 800 MiB hard gate; analysis stopped and evidence retained")
    print(json.dumps({"status": "PASS", "candidate_signature": first["signature"], "controls": controls, "preflight": preflight_manifest, "formal_manifest": formal["manifest"], "formal_quality": formal["quality"], "combined_manifest": combined["manifest"], "combined_quality": analysis["combined_quality"], "training_readiness": analysis["training_readiness"], "storage": manifest["storage"], "total_wall_time_seconds": manifest["total_wall_time_seconds"]}, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    mp.freeze_support()
    main()
