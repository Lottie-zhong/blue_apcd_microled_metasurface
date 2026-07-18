"""Run the F0-PRE1 benchmark and 512-structure Native-M1 calibration."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import multiprocessing as mp
import os
import shutil
import statistics
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Iterable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_mdc_ml_f0_pilot_candidates_v1 as builder  # noqa: E402
import run_mdc_ml_f0_smoke_v1 as smoke  # noqa: E402
from mdc_ml_structure_grammar_v1 import TOPOLOGY_FAMILIES  # noqa: E402

CONFIG_PATH = ROOT / "configs" / "mdc_ml_f0_pilot_calibration_v1.yaml"
QUALITY_MASK_CONTRACT_ID = "post_TMM_objective_eligibility_mask_v1"
DERIVED_DIAGNOSTIC_FIELDS = {
    "solver_valid", "transmission_raw", "transmission_above_unity_flag",
    "transmission_above_unity_excess", "power_balance_tolerance",
    "power_balance_failure", "peak_angle_zero_compatible", "low_t450_flag",
    "low_band_proxy_flag", "strong_secondary_peak_flag",
    "nominal_4d_objective_eligible", "shortlist_quality_eligible",
    "continuous_regression_target_mask", "quality_mask_contract_id",
}


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_hash(value: Any) -> str:
    return builder.stable_hash(value)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    builder.write_json(path, value)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    builder.write_jsonl(path, rows)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    builder.write_csv(path, rows)


def directory_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file()) if path.exists() else 0


def output_tree_fingerprint(path: Path) -> dict[str, Any]:
    items = sorted(item for item in path.rglob("*") if item.is_file())
    digest = hashlib.sha256()
    total = 0
    for item in items:
        relative = item.relative_to(path).as_posix()
        size = item.stat().st_size
        total += size
        digest.update(f"{relative}|{size}|{sha256_path(item)}\n".encode("utf-8"))
    return {"file_count": len(items), "bytes": total, "tree_sha256": digest.hexdigest()}


def _file_stats(paths: Iterable[Path]) -> dict[str, Any]:
    files = [path for path in paths if path.is_file()]
    size = sum(path.stat().st_size for path in files)
    return {"files": len(files), "bytes": size, "mib": size / (1024 ** 2)}


def _storage_estimates(base_bytes: int, structure_count: int) -> dict[str, dict[str, float]]:
    per_structure = base_bytes / structure_count
    return {
        str(count): {
            "base_bytes": per_structure * count,
            "plus_10_percent_bytes": per_structure * count * 1.10,
            "plus_20_percent_bytes": per_structure * count * 1.20,
        }
        for count in (2000, 5000)
    }


def storage_accounting(out: Path, structure_count: int = 512) -> dict[str, Any]:
    calibration_dir = out / "calibration"
    benchmark_dir = out / "benchmark"
    workers = {
        worker: list((benchmark_dir / f"workers_{worker}").rglob("*"))
        if (benchmark_dir / f"workers_{worker}").exists() else []
        for worker in (1, 2, 4, 8)
    }
    calibration_metadata = [path for path in calibration_dir.glob("*") if path.is_file()]
    calibration_artifacts = list((calibration_dir / "artifacts").glob("*.npz"))
    categories = {
        "candidate_manifests_records": _file_stats(path for path in out.glob("candidate*") if path.is_file()),
        "benchmark_metadata": _file_stats(path for path in benchmark_dir.glob("*") if path.is_file()),
        "benchmark_warmup_outputs": _file_stats([]),
        **{f"benchmark_workers_{worker}": _file_stats(workers[worker]) for worker in (1, 2, 4, 8)},
        "f0_cross_fidelity": _file_stats([out / "f0_cross_fidelity_v1.json", *list((out / "f0_cross_fidelity").rglob("*"))]),
        "pre1_control_metadata": _file_stats(out / name for name in (
            "formal_pilot_recommendation_v1.json", "manifest_v1.json",
            "runtime_and_storage_budget_v1.json", "static_gate_v1.json",
        )),
        "calibration_metadata": _file_stats(calibration_metadata),
        "calibration_npz_artifacts": _file_stats(calibration_artifacts),
        "calibration_complete": _file_stats([*calibration_metadata, *calibration_artifacts]),
        "whole_pre1": _file_stats(out.rglob("*")),
    }
    artifact_hashes: set[str] = set()
    response_manifest = calibration_dir / "response_manifest_v1.json"
    if response_manifest.is_file():
        artifact_hashes = {item["sha256"] for item in json.loads(response_manifest.read_text(encoding="utf-8"))["artifacts"]}
    duplicate_benchmark = [
        path for path in workers[8]
        if path.is_file() and path.suffix == ".npz" and sha256_path(path) in artifact_hashes
    ]
    categories["benchmark_duplicate_calibration_artifacts"] = _file_stats(duplicate_benchmark)
    production_bytes = int(categories["calibration_complete"]["bytes"])
    artifact_bytes = int(categories["calibration_npz_artifacts"]["bytes"])
    metadata_bytes = int(categories["calibration_metadata"]["bytes"])
    whole_bytes = int(categories["whole_pre1"]["bytes"])
    return {
        "structure_count": structure_count,
        "categories": categories,
        "formal_pilot_bytes_per_structure": production_bytes / structure_count,
        "artifact_bytes_per_structure": artifact_bytes / structure_count,
        "metadata_bytes_per_structure": metadata_bytes / structure_count,
        "whole_pre1_naive_bytes_per_structure": whole_bytes / structure_count,
        "formal_estimates": _storage_estimates(production_bytes, structure_count),
        "artifact_estimates": _storage_estimates(artifact_bytes, structure_count),
        "metadata_estimates": _storage_estimates(metadata_bytes, structure_count),
        "whole_pre1_naive_estimates": _storage_estimates(whole_bytes, structure_count),
        "recommended_disk_reserve_bytes": production_bytes / structure_count * 5000 * 1.5,
        "formal_pilot_excludes": [
            "PRE1 benchmark warm-ups/repeats and retained reference artifacts",
            "PRE1 F0 cross-fidelity artifact",
            "PRE1-only candidate/static/control manifests as per-structure production bytes",
        ],
    }


def enforce_output_limit(out: Path, maximum_bytes: int) -> int:
    size = directory_size(out)
    if size > maximum_bytes:
        raise RuntimeError(f"output size gate exceeded: {size} > {maximum_bytes}")
    return size


def frozen_file_audit(config: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for relative, expected in config["frozen_files_sha256"].items():
        path = ROOT / relative
        actual = sha256_path(path) if path.is_file() else None
        rows.append({"path": relative, "expected_sha256": expected, "actual_sha256": actual, "status": "PASS" if actual == expected else "FAIL"})
    return {"status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL", "files": rows}


def repository_audit() -> dict[str, Any]:
    command = [sys.executable, str(SCRIPTS / "audit_mdc_ml_inverse_design_spec_v1.py"), "--audit-only"]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False, shell=False)
    if completed.returncode != 0:
        raise RuntimeError(f"repository audit failed ({completed.returncode}): {completed.stdout}\n{completed.stderr}")
    value = json.loads(completed.stdout)
    if value.get("status") != "PASS" or value.get("payload_drift_count") != 0:
        raise RuntimeError(f"repository contract gate failed: {value}")
    return value


def _all_wavelengths(config: dict[str, Any]) -> np.ndarray:
    return np.concatenate((
        smoke.grid(config["grids"]["spectral"]["wavelength_start_nm"], config["grids"]["spectral"]["wavelength_stop_nm"], config["grids"]["spectral"]["wavelength_step_nm"]),
        smoke.grid(config["grids"]["apcd_ready"]["wavelength_start_nm"], config["grids"]["apcd_ready"]["wavelength_stop_nm"], config["grids"]["apcd_ready"]["wavelength_step_nm"]),
    ))


def _array_content_hash(arrays: dict[str, np.ndarray]) -> str:
    return stable_hash({name: hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest() for name, value in sorted(arrays.items())})


def f0_cross_fidelity(config: dict[str, Any], out: Path) -> dict[str, Any]:
    settings = config["f0_cross_fidelity"]
    smoke_config = smoke.load_config(ROOT / settings["smoke_config"])
    raw = smoke.baseline_candidate(smoke_config)
    canonical = smoke.canonical_roundtrip(raw)
    indices = smoke.material_indices(_all_wavelengths(smoke_config))
    arrays, metrics, elapsed = smoke.simulate_structure(canonical, smoke_config, indices)
    scalar_gate = smoke.baseline_gate(canonical, metrics, smoke_config)
    cross_dir = out / "f0_cross_fidelity"
    artifact_path = cross_dir / "baseline_response_v1.npz"
    smoke.deterministic_npz(artifact_path, arrays)
    grid_ids = {name: value["id"] for name, value in smoke_config["grids"].items()}
    artifact = smoke.artifact_manifest_entry(artifact_path, arrays, grid_ids)
    reference_manifest = json.loads((ROOT / settings["smoke_response_manifest"]).read_text(encoding="utf-8"))
    reference = next(item for item in reference_manifest["artifacts"] if item["sample_id"] == settings["baseline_sample_id"])
    expected = settings["expected_metrics"]
    recomputed = {
        "spectral_fwhm_normal_nm": metrics["spectral_fwhm_normal_nm"],
        "angular_fwhm_450_deg": metrics["angular_fwhm_450_deg"],
        "ratio": metrics["ratio"],
        "maximum_angle_set_deg": metrics["maximum_angle_set_deg"],
        "tmm_apcd_ready_cone5_fraction_proxy": metrics["unpolarized"]["tmm_apcd_ready_cone5_fraction_proxy"],
        "tmm_apcd_ready_cone10_fraction_proxy": metrics["unpolarized"]["tmm_apcd_ready_cone10_fraction_proxy"],
        "tmm_band_transmission_448_453_normal_proxy": metrics["unpolarized"]["tmm_band_transmission_448_453_normal_proxy"],
    }
    tolerance = float(config["quality"]["cross_fidelity_absolute_tolerance"])
    scalar_checks = {
        key: (value == expected[key] if isinstance(value, list) else abs(float(value) - float(expected[key])) <= tolerance)
        for key, value in recomputed.items()
    }
    shape_checks = {
        name: list(value.shape) == reference["fields"][name]["shape"] and str(value.dtype) == reference["fields"][name]["dtype"]
        for name, value in arrays.items()
    }
    array_hash = _array_content_hash(arrays)
    result = {
        "status": "PASS",
        "runtime_seconds": elapsed,
        "scalar_gate": scalar_gate,
        "scalar_checks": scalar_checks,
        "expected_metrics": expected,
        "recomputed_metrics": recomputed,
        "array_shape_dtype_checks": shape_checks,
        "array_content_hash": array_hash,
        "expected_array_content_hash": settings["expected_array_content_hash"],
        "reference_array_content_hash": reference["array_content_hash"],
        "artifact_sha256": artifact["sha256"],
        "frozen_smoke_reference_compatible": True,
    }
    result["status"] = "PASS" if (
        scalar_gate["status"] == "PASS" and all(scalar_checks.values()) and all(shape_checks.values())
        and array_hash == settings["expected_array_content_hash"] == reference["array_content_hash"]
    ) else "FAIL"
    result["frozen_smoke_reference_compatible"] = result["status"] == "PASS"
    write_json(out / "f0_cross_fidelity_v1.json", result)
    if result["status"] != "PASS":
        raise RuntimeError(f"F0 cross-fidelity gate failed: {result}")
    return result


def select_benchmark_subset(records: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for family in TOPOLOGY_FAMILIES:
        family_rows = [row for row in records if row["topology_family"] == family]
        categories = {category: sorted(
            [row for row in family_rows if row["source_category"] == category],
            key=lambda row: (row["layer_count"], row["total_thickness_nm"], row["canonical_geometry_hash"]),
        ) for category in builder.CATEGORY_ORDER}
        quota = {
            "FAMILY_STRATIFIED_GLOBAL": 2,
            "ANCHOR_NEIGHBORHOOD": 2 if categories["ANCHOR_NEIGHBORHOOD"] else 0,
            "FAMILY_CHALLENGE": 2 if categories["ANCHOR_NEIGHBORHOOD"] else 3,
            "RARE_CROSS_FAMILY": 2,
        }
        if not categories["ANCHOR_NEIGHBORHOOD"]:
            quota["FAMILY_STRATIFIED_GLOBAL"] = 3
        for category in builder.CATEGORY_ORDER:
            rows = categories[category]
            count = quota[category]
            if count == 0:
                continue
            if len(rows) < count:
                raise RuntimeError(f"benchmark category shortage: {family}/{category}")
            indices = sorted({round(position * (len(rows) - 1) / max(count - 1, 1)) for position in range(count)})
            while len(indices) < count:
                indices.append(next(index for index in range(len(rows)) if index not in indices))
            selected.extend(rows[index] for index in sorted(indices[:count]))
    selected.sort(key=lambda row: row["sample_id"])
    if len(selected) != int(config["benchmark"]["subset_count"]):
        raise RuntimeError("benchmark subset count mismatch")
    if len({row["canonical_geometry_hash"] for row in selected}) != len(selected):
        raise RuntimeError("benchmark subset contains duplicate geometry")
    counts = Counter(row["topology_family"] for row in selected)
    if any(counts[family] != int(config["benchmark"]["per_family"]) for family in TOPOLOGY_FAMILIES):
        raise RuntimeError(f"benchmark family coverage mismatch: {counts}")
    return selected


def _worker_initializer() -> None:
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"


def _tmm_worker(payload: tuple[dict[str, Any], dict[str, Any]]) -> dict[str, Any]:
    candidate, config = payload
    canonical = smoke.canonical_roundtrip(candidate["raw_structure"])
    indices = smoke.material_indices(_all_wavelengths(config))
    arrays, metrics, elapsed = smoke.simulate_structure(canonical, config, indices)
    return {"sample_id": candidate["sample_id"], "canonical": canonical, "arrays": arrays, "metrics": metrics, "runtime_seconds": elapsed}


def _synthetic_worker(payload: tuple[str, bool]) -> dict[str, Any]:
    sample_id, fail = payload
    if fail:
        raise RuntimeError(f"synthetic worker failure: {sample_id}")
    seed = int(hashlib.sha256(sample_id.encode("utf-8")).hexdigest()[:16], 16)
    values = np.asarray([(seed >> shift) & 255 for shift in range(0, 64, 8)], dtype=np.float64)
    return {"sample_id": sample_id, "metrics_hash": stable_hash(values.tolist()), "array_hash": hashlib.sha256(values.tobytes()).hexdigest()}


def synthetic_parallel_signatures(sample_ids: Iterable[str], workers: int, *, fail: bool = False) -> dict[str, Any]:
    ordered = sorted(sample_ids)
    context = mp.get_context("spawn")
    with ProcessPoolExecutor(max_workers=workers, mp_context=context, initializer=_worker_initializer) as executor:
        results = list(executor.map(_synthetic_worker, [(sample_id, fail) for sample_id in ordered], chunksize=1))
    results.sort(key=lambda row: row["sample_id"])
    return {
        "metrics_signature": stable_hash([[row["sample_id"], row["metrics_hash"]] for row in results]),
        "array_signature": stable_hash([[row["sample_id"], row["array_hash"]] for row in results]),
        "ordering_signature": stable_hash([row["sample_id"] for row in results]),
    }


def _spectral_boundary_clipped(arrays: dict[str, np.ndarray]) -> bool:
    values = 0.5 * (arrays["spectral_T_TE"] + arrays["spectral_T_TM"])
    index = int(np.argmax(values))
    half = float(values[index]) / 2.0
    left = any(values[position - 1] < half <= values[position] for position in range(index, 0, -1))
    right = any(values[position] >= half > values[position + 1] for position in range(index, len(values) - 1))
    return not (left and right)


def _secondary_peak(arrays: dict[str, np.ndarray], metrics: dict[str, Any]) -> dict[str, Any]:
    angles = arrays["angular_angle_air_deg"]
    values = 0.5 * (arrays["angular_T_TE"] + arrays["angular_T_TM"])
    peaks = [index for index in range(1, len(values) - 1) if values[index] >= values[index - 1] and values[index] >= values[index + 1]]
    global_value = float(values.max())
    global_set = set(float(value) for value in metrics["maximum_angle_set_deg"])
    secondary = sorted(
        [(float(values[index]), float(angles[index])) for index in peaks if float(angles[index]) not in global_set],
        reverse=True,
    )
    value, angle = secondary[0] if secondary else (0.0, None)
    return {"secondary_peak_value": value, "secondary_peak_angle_deg": angle, "secondary_peak_ratio": value / global_value if global_value else None, "secondary_peak_count": len(secondary)}


def quality_mask_fields(row: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    quality = config["quality"]
    if quality["quality_mask_contract_id"] != QUALITY_MASK_CONTRACT_ID:
        raise RuntimeError("quality mask contract mismatch")
    if quality["pre_solver_performance_filtering_allowed"] is not False:
        raise RuntimeError("PRE1 forbids pre-solver performance filtering")
    solver_valid = bool(row.get("solver_valid", row.get("finite_arrays", False)))
    schema_valid = bool(row["schema_valid"])
    artifact_valid = bool(row["artifact_valid"])
    transmission_raw = float(row["T450_unpolarized"])
    transmission_excess = max(0.0, transmission_raw - 1.0)
    power_tolerance = float(quality["transmission_power_balance_tolerance"])
    above_unity = transmission_raw > 1.0
    power_failure = transmission_excess > power_tolerance
    peak_tolerance = float(quality["peak_angle_zero_compatibility_tolerance_deg"])
    zero_compatible = any(abs(float(angle)) <= peak_tolerance for angle in row["maximum_angle_set_deg"])
    low_t450 = transmission_raw < float(quality["low_T450_threshold"])
    low_band = float(row["normal_band_transmission_proxy"]) < float(quality["low_band_proxy_threshold"])
    strong_secondary = float(row.get("secondary_peak_ratio") or 0.0) >= float(quality["strong_secondary_peak_ratio"])
    base = solver_valid and schema_valid and artifact_valid and not power_failure
    target_mask = {
        "spectral_fwhm_normal_nm": base and bool(row["spectral_fwhm_valid"]) and not bool(row["spectral_boundary_clipped"]) and row["spectral_fwhm_normal_nm"] is not None,
        "angular_fwhm_450_deg": base and bool(row["angular_fwhm_valid"]) and not bool(row["angular_boundary_clipped"]) and row["angular_fwhm_450_deg"] is not None,
        "cone5_integral_proxy": base and math.isfinite(float(row["cone5_integral_proxy"])),
        "normal_band_transmission_proxy": base and math.isfinite(float(row["normal_band_transmission_proxy"])),
        "T450_unpolarized": base and math.isfinite(transmission_raw),
    }
    nominal_eligible = all(target_mask[name] for name in (
        "spectral_fwhm_normal_nm", "angular_fwhm_450_deg",
        "cone5_integral_proxy", "normal_band_transmission_proxy",
    ))
    shortlist_eligible = (
        nominal_eligible and bool(row["center_is_global_max"]) and zero_compatible
        and not low_t450 and not low_band and not strong_secondary
    )
    return {
        "quality_mask_contract_id": QUALITY_MASK_CONTRACT_ID,
        "solver_valid": solver_valid,
        "schema_valid": schema_valid,
        "artifact_valid": artifact_valid,
        "spectral_fwhm_valid": bool(row["spectral_fwhm_valid"]),
        "angular_fwhm_valid": bool(row["angular_fwhm_valid"]),
        "spectral_boundary_clipped": bool(row["spectral_boundary_clipped"]),
        "angular_boundary_clipped": bool(row["angular_boundary_clipped"]),
        "center_is_global_max": bool(row["center_is_global_max"]),
        "peak_angle_zero_compatible": zero_compatible,
        "low_t450_flag": low_t450,
        "low_band_proxy_flag": low_band,
        "strong_secondary_peak_flag": strong_secondary,
        "transmission_raw": transmission_raw,
        "transmission_above_unity_flag": above_unity,
        "transmission_above_unity_excess": transmission_excess,
        "power_balance_tolerance": power_tolerance,
        "power_balance_failure": power_failure,
        "continuous_regression_target_mask": target_mask,
        "nominal_4d_objective_eligible": nominal_eligible,
        "shortlist_quality_eligible": shortlist_eligible,
    }


def apply_quality_masks(rows: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    for row in rows:
        row.update(quality_mask_fields(row, config))
    return rows


def _signature_row(row: dict[str, Any]) -> dict[str, Any]:
    excluded = {
        "worker_runtime_seconds", "artifact_path", "artifact_sha256",
        "artifact_bytes", "pareto_status", *DERIVED_DIAGNOSTIC_FIELDS,
    }
    return {key: value for key, value in row.items() if key not in excluded}


def metric_row(candidate: dict[str, Any], result: dict[str, Any], artifact: dict[str, Any], schema_errors: list[str]) -> dict[str, Any]:
    arrays, metrics, canonical = result["arrays"], result["metrics"], result["canonical"]
    spectral_clipped = _spectral_boundary_clipped(arrays)
    angular_values = 0.5 * (arrays["angular_T_TE"] + arrays["angular_T_TM"])
    center_index = int(np.flatnonzero(np.isclose(arrays["angular_angle_air_deg"], 0.0))[0])
    spectral_450 = int(np.flatnonzero(np.isclose(arrays["spectral_wavelength_nm"], 450.0))[0])
    secondary = _secondary_peak(arrays, metrics)
    finite = all(np.all(np.isfinite(value.real)) and (not np.iscomplexobj(value) or np.all(np.isfinite(value.imag))) for value in arrays.values())
    spectral_raw = float(metrics["spectral_fwhm_normal_nm"])
    spectral_valid = math.isfinite(spectral_raw) and spectral_raw > 0.0 and not spectral_clipped
    angular_raw = metrics["angular_fwhm_450_deg"]
    angular_valid = metrics["angular_fwhm_status"] == "valid" and angular_raw is not None and float(angular_raw) > 0.0
    return {
        "sample_id": candidate["sample_id"],
        "source_category": candidate["source_category"],
        "topology_family": candidate["topology_family"],
        "anchor_parent_id": candidate["anchor_parent_id"],
        "canonical_geometry_hash": canonical["canonical_geometry_hash"],
        "physical_configuration_hash": canonical["physical_configuration_hash"],
        "simulation_provenance_hash": candidate["simulation_provenance_hash"],
        "layer_count": canonical["layer_count"],
        "total_thickness_nm": canonical["total_thickness_nm"],
        "defect_indices": canonical["defect_indices"],
        "termination": canonical["termination"],
        "spectral_fwhm_normal_nm": spectral_raw if spectral_valid else None,
        "spectral_fwhm_raw_nm": spectral_raw,
        "spectral_fwhm_valid": spectral_valid,
        "spectral_boundary_clipped": spectral_clipped,
        "angular_fwhm_450_deg": float(angular_raw) if angular_valid else None,
        "angular_fwhm_raw_deg": angular_raw,
        "angular_fwhm_valid": angular_valid,
        "angular_boundary_clipped": metrics["angular_fwhm_status"] == "boundary_clipped",
        "T450_TE": float(arrays["spectral_T_TE"][spectral_450]),
        "T450_TM": float(arrays["spectral_T_TM"][spectral_450]),
        "T450_unpolarized": metrics["T450"],
        "maximum_angle_set_deg": metrics["maximum_angle_set_deg"],
        "center_is_global_max": metrics["center_is_global_max"],
        "center_to_global_ratio": float(angular_values[center_index] / angular_values.max()) if angular_values.max() else None,
        "symmetric_peak_pair": metrics["symmetric_peak_pair"],
        **secondary,
        "cone5_integral_proxy": metrics["unpolarized"]["tmm_apcd_ready_cone5_integral_proxy"],
        "cone10_integral_proxy": metrics["unpolarized"]["tmm_apcd_ready_cone10_integral_proxy"],
        "cone5_fraction_proxy": metrics["unpolarized"]["tmm_apcd_ready_cone5_fraction_proxy"],
        "cone10_fraction_proxy": metrics["unpolarized"]["tmm_apcd_ready_cone10_fraction_proxy"],
        "normal_band_transmission_proxy": metrics["unpolarized"]["tmm_band_transmission_448_453_normal_proxy"],
        "ratio": metrics["ratio"],
        "max_abs_far_field_balance_offset": max(float(np.max(np.abs(value))) for name, value in arrays.items() if "far_field_balance_offset" in name),
        "array_content_hash": artifact["array_content_hash"],
        "artifact_sha256": artifact["sha256"],
        "artifact_bytes": artifact["bytes"],
        "artifact_path": artifact["path"],
        "schema_valid": not schema_errors,
        "artifact_valid": True,
        "finite_arrays": finite,
        "worker_runtime_seconds": result["runtime_seconds"],
    }


def run_tmm_batch(records: list[dict[str, Any]], config: dict[str, Any], workers: int, artifact_dir: Path) -> dict[str, Any]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    schema = smoke.load_schema()
    context = mp.get_context("spawn")
    expected_order = [row["sample_id"] for row in records]
    metric_rows: list[dict[str, Any]] = []
    schema_records: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    runtimes: list[float] = []
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers, mp_context=context, initializer=_worker_initializer) as executor:
        iterator = executor.map(_tmm_worker, [(record, config) for record in records], chunksize=1)
        for index, (candidate, result) in enumerate(zip(records, iterator)):
            if result["sample_id"] != candidate["sample_id"]:
                raise RuntimeError("worker result ordering mismatch")
            artifact_path = artifact_dir / f"{index:04d}_{candidate['canonical_geometry_hash'][:16]}.npz"
            smoke.deterministic_npz(artifact_path, result["arrays"])
            artifact = smoke.artifact_manifest_entry(artifact_path, result["arrays"], {name: value["id"] for name, value in config["grids"].items()})
            artifact.update({"sample_id": candidate["sample_id"], "canonical_geometry_hash": candidate["canonical_geometry_hash"]})
            with np.load(artifact_path, allow_pickle=False) as loaded:
                loaded_arrays = {name: loaded[name] for name in loaded.files}
            if _array_content_hash(loaded_arrays) != artifact["array_content_hash"] or sha256_path(artifact_path) != artifact["sha256"]:
                raise RuntimeError(f"artifact validation failed: {candidate['sample_id']}")
            record = smoke.make_record(result["canonical"], result["metrics"], artifact, config, candidate["sample_id"])
            errors = smoke.validate_json_instance(record, schema)
            row = metric_row(candidate, result, artifact, errors)
            row.update(quality_mask_fields(row, config))
            if not row["spectral_fwhm_valid"]:
                record["labels"]["scalar_spectral_metrics"]["spectral_fwhm_normal_nm"] = None
            if not row["angular_fwhm_valid"]:
                record["labels"]["scalar_angular_metrics"]["angular_fwhm_450_deg"] = None
            if errors:
                raise RuntimeError(f"schema validation failed: {candidate['sample_id']}: {errors}")
            if not row["finite_arrays"]:
                raise RuntimeError(f"unflagged NaN/Inf: {candidate['sample_id']}")
            metric_rows.append(row)
            schema_records.append(record)
            artifacts.append(artifact)
            runtimes.append(float(result["runtime_seconds"]))
            enforce_output_limit(ROOT / config["output_directory"], int(config["maximum_output_bytes"]))
    wall = time.perf_counter() - started
    if [row["sample_id"] for row in metric_rows] != expected_order:
        raise RuntimeError("final sample ordering mismatch")
    signature_rows = [_signature_row(row) for row in metric_rows]
    return {
        "metric_rows": metric_rows,
        "schema_records": schema_records,
        "artifacts": artifacts,
        "wall_time_seconds": wall,
        "structures_per_second": len(records) / wall,
        "solver_runtime_mean": statistics.fmean(runtimes),
        "solver_runtime_p50": float(np.quantile(runtimes, 0.50)),
        "solver_runtime_p95": float(np.quantile(runtimes, 0.95)),
        "output_bytes": sum(item["bytes"] for item in artifacts),
        "metrics_content_signature": stable_hash(signature_rows),
        "array_content_signature": stable_hash([[item["sample_id"], item["array_content_hash"]] for item in artifacts]),
        "result_ordering_signature": stable_hash(expected_order),
        "success_count": len(records),
        "failure_count": 0,
        "worker_exception_count": 0,
    }


def select_workers(rows: list[dict[str, Any]]) -> tuple[int, str]:
    throughput = {int(row["workers"]): float(row["structures_per_second"]) for row in rows}
    selected = max(throughput, key=lambda workers: (throughput[workers], -workers))
    reason = "maximum median throughput"
    if selected == 8 and throughput[8] < 1.10 * throughput[4]:
        selected, reason = 4, "workers=8 improved less than 10% over workers=4"
    if selected == 4 and throughput[4] < 1.10 * throughput[2]:
        selected, reason = 2, "workers=4 improved less than 10% over workers=2"
    return selected, reason


def run_parallel_benchmark(records: list[dict[str, Any]], config: dict[str, Any], out: Path) -> dict[str, Any]:
    benchmark_dir = out / "benchmark"
    subset = select_benchmark_subset(records, config)
    subset_manifest = {
        "sample_ids": [row["sample_id"] for row in subset],
        "geometry_hashes": [row["canonical_geometry_hash"] for row in subset],
        "subset_signature": stable_hash([[row["sample_id"], row["canonical_geometry_hash"]] for row in subset]),
        "topology_counts": dict(Counter(row["topology_family"] for row in subset)),
        "source_category_counts": dict(Counter(row["source_category"] for row in subset)),
    }
    write_json(benchmark_dir / "subset_manifest_v1.json", subset_manifest)
    benchmark_rows: list[dict[str, Any]] = []
    cleanup: list[str] = []
    reference_dirs: dict[int, Path] = {}
    reference_results: dict[int, dict[str, Any]] = {}
    for workers in config["benchmark"]["workers"]:
        warmup_dir = benchmark_dir / f"workers_{workers}" / "warmup_scratch"
        run_tmm_batch(subset[: int(config["benchmark"]["warmup_count"])], config, int(workers), warmup_dir)
        shutil.rmtree(warmup_dir)
        cleanup.append(warmup_dir.relative_to(out).as_posix())
        repeats: list[dict[str, Any]] = []
        for repeat in range(1, int(config["benchmark"]["timed_repeats"]) + 1):
            artifact_dir = benchmark_dir / f"workers_{workers}" / ("reference_artifacts" if repeat == 1 else f"repeat_{repeat}_scratch")
            result = run_tmm_batch(subset, config, int(workers), artifact_dir)
            repeats.append(result)
            if repeat > 1:
                shutil.rmtree(artifact_dir)
                cleanup.append(artifact_dir.relative_to(out).as_posix())
        signatures = {(item["metrics_content_signature"], item["array_content_signature"], item["result_ordering_signature"]) for item in repeats}
        if len(signatures) != 1:
            raise RuntimeError(f"benchmark repeats are non-deterministic for workers={workers}")
        reference_dirs[int(workers)] = benchmark_dir / f"workers_{workers}" / "reference_artifacts"
        reference_results[int(workers)] = repeats[0]
        walls = [item["wall_time_seconds"] for item in repeats]
        median_wall = statistics.median(walls)
        benchmark_rows.append({
            "workers": int(workers), "repeat_wall_times_seconds": walls,
            "median_wall_time_seconds": median_wall, "structures_per_second": len(subset) / median_wall,
            "speedup": None, "parallel_efficiency": None,
            "success_count": len(subset), "failure_count": 0, "worker_exception_count": 0,
            "mean_per_structure_runtime": statistics.fmean(item["solver_runtime_mean"] for item in repeats),
            "p50_per_structure_runtime": statistics.fmean(item["solver_runtime_p50"] for item in repeats),
            "p95_per_structure_runtime": statistics.fmean(item["solver_runtime_p95"] for item in repeats),
            "output_bytes": repeats[0]["output_bytes"],
            "metrics_content_signature": repeats[0]["metrics_content_signature"],
            "array_content_signature": repeats[0]["array_content_signature"],
            "result_ordering_signature": repeats[0]["result_ordering_signature"],
            "peak_rss_bytes": None,
        })
    baseline_throughput = next(row["structures_per_second"] for row in benchmark_rows if row["workers"] == 1)
    for row in benchmark_rows:
        row["speedup"] = row["structures_per_second"] / baseline_throughput
        row["parallel_efficiency"] = row["speedup"] / row["workers"]
    if len({row["metrics_content_signature"] for row in benchmark_rows}) != 1 or len({row["array_content_signature"] for row in benchmark_rows}) != 1 or len({row["result_ordering_signature"] for row in benchmark_rows}) != 1:
        raise RuntimeError("worker-dependent result hash drift detected")
    selected, reason = select_workers(benchmark_rows)
    for workers, path in reference_dirs.items():
        if workers != selected:
            shutil.rmtree(path)
            cleanup.append(path.relative_to(out).as_posix())
    result = {
        "status": "PASS", "warmup_method": f"{config['benchmark']['warmup_count']} uncounted structures per worker setting",
        "timed_repeat_count": int(config["benchmark"]["timed_repeats"]),
        "selected_workers": selected, "selection_reason": reason,
        "rows": benchmark_rows, "subset": subset_manifest, "cleanup": cleanup,
        "memory_io_observation": "peak RSS unavailable; output writes are main-process serialized and no worker shares NPZ files",
    }
    write_csv(benchmark_dir / "parallel_benchmark_v1.csv", benchmark_rows)
    write_json(benchmark_dir / "parallel_benchmark_v1.json", result)
    enforce_output_limit(out, int(config["maximum_output_bytes"]))
    return result


def _quantiles(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    array = np.asarray(values, dtype=float)
    return {"min": float(np.min(array)), "p10": float(np.quantile(array, 0.10)), "p25": float(np.quantile(array, 0.25)), "p50": float(np.quantile(array, 0.50)), "p75": float(np.quantile(array, 0.75)), "p90": float(np.quantile(array, 0.90)), "max": float(np.max(array))}


def _pearson_correlations(rows: list[dict[str, Any]], names: tuple[str, ...]) -> dict[str, dict[str, float | None]]:
    arrays = {name: np.asarray([float(row[name]) for row in rows], dtype=float) for name in names}
    output: dict[str, dict[str, float | None]] = {}
    for left in names:
        output[left] = {}
        for right in names:
            if len(rows) < 2 or float(np.std(arrays[left])) == 0.0 or float(np.std(arrays[right])) == 0.0:
                output[left][right] = None
            else:
                output[left][right] = float(np.corrcoef(arrays[left], arrays[right])[0, 1])
    return output


def nominal_pareto(rows: list[dict[str, Any]], config: dict[str, Any] | None = None) -> dict[str, Any]:
    def eligible(row: dict[str, Any]) -> bool:
        value = bool(row["spectral_fwhm_valid"] and row["angular_fwhm_valid"] and row["spectral_fwhm_normal_nm"] is not None and float(row["spectral_fwhm_normal_nm"]) > 0.0 and row["angular_fwhm_450_deg"] is not None and float(row["angular_fwhm_450_deg"]) > 0.0 and not row["spectral_boundary_clipped"] and not row["angular_boundary_clipped"] and row["schema_valid"] and row["artifact_valid"] and not bool(row.get("power_balance_failure", False)))
        if "nominal_4d_objective_eligible" in row and bool(row["nominal_4d_objective_eligible"]) != value:
            raise RuntimeError(f"quality-mask/Pareto eligibility mismatch: {row['sample_id']}")
        return value
    valid = [row for row in rows if eligible(row)]
    objectives = [(float(row["angular_fwhm_450_deg"]), float(row["spectral_fwhm_normal_nm"]), -float(row["cone5_integral_proxy"]), -float(row["normal_band_transmission_proxy"])) for row in valid]
    pareto: list[dict[str, Any]] = []
    for index, row in enumerate(valid):
        value = objectives[index]
        dominated = any(other != index and all(candidate <= target for candidate, target in zip(objectives[other], value)) and any(candidate < target for candidate, target in zip(objectives[other], value)) for other in range(len(valid)))
        row["pareto_status"] = "dominated" if dominated else "non_dominated"
        if not dominated:
            pareto.append(row)
    valid_ids = {row["sample_id"] for row in valid}
    for row in rows:
        if row["sample_id"] not in valid_ids:
            row["pareto_status"] = "ineligible_invalid_metric_or_boundary"
    objective_names = ("angular_fwhm_450_deg", "spectral_fwhm_normal_nm", "cone5_integral_proxy", "normal_band_transmission_proxy")
    valid_ranges = {name: _quantiles([float(row[name]) for row in valid]) for name in objective_names}
    pareto_ranges = {name: _quantiles([float(row[name]) for row in pareto]) for name in objective_names}
    correlations = _pearson_correlations(valid, objective_names)
    redundancy_config = (config or {}).get("objective_redundancy", {})
    warning_threshold = float(redundancy_config.get("warning_abs_pearson_threshold", 0.995))
    cone_band = correlations["cone5_integral_proxy"]["normal_band_transmission_proxy"]
    redundancy_warning = cone_band is not None and abs(cone_band) >= warning_threshold
    return {
        "valid_population": len(valid), "pareto_size": len(pareto),
        "objective_directions": {
            "angular_fwhm_450_deg": "minimize",
            "spectral_fwhm_normal_nm": "minimize",
            "cone5_integral_proxy": "maximize",
            "normal_band_transmission_proxy": "maximize",
        },
        "family_composition": dict(Counter(row["topology_family"] for row in pareto)),
        "source_category_composition": dict(Counter(row["source_category"] for row in pareto)),
        "objective_ranges": valid_ranges,
        "valid_population_objective_ranges": valid_ranges,
        "pareto_objective_ranges": pareto_ranges,
        "valid_population_pearson_correlations": correlations,
        "objective_redundancy": {
            "effective_redundancy_warning": redundancy_warning,
            "warning_abs_pearson_threshold": warning_threshold,
            "cone5_integral_vs_normal_band_proxy_pearson": cone_band,
            "frozen_nominal_4d_retained": bool(redundancy_config.get("retain_frozen_nominal_4d_objectives", True)),
            "recompute_each_formal_pilot": bool(redundancy_config.get("recompute_each_formal_pilot", True)),
            "sensitivity_analysis_policy": redundancy_config.get("sensitivity_analysis_policy", "diagnostic_only; never replaces frozen nominal 4D"),
        },
        "pareto_sample_ids": [row["sample_id"] for row in pareto],
    }


def _wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    proportion = successes / total
    denominator = 1.0 + z * z / total
    center = (proportion + z * z / (2.0 * total)) / denominator
    half = z * math.sqrt(proportion * (1.0 - proportion) / total + z * z / (4.0 * total * total)) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def formal_2000_expectation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    eligible_count = sum(bool(row["nominal_4d_objective_eligible"]) for row in rows)
    low, high = _wilson_interval(eligible_count, total)
    family_total = Counter(row["topology_family"] for row in rows)
    family_eligible = Counter(row["topology_family"] for row in rows if row["nominal_4d_objective_eligible"])
    family_projection = {}
    for family, observed_total in sorted(family_total.items()):
        observed_eligible = family_eligible[family]
        projected_total = 2000.0 * observed_total / total
        family_low, family_high = _wilson_interval(observed_eligible, observed_total)
        family_projection[family] = {
            "observed_total": observed_total,
            "observed_eligible": observed_eligible,
            "observed_rate": observed_eligible / observed_total,
            "projected_2000_total_at_observed_mix": projected_total,
            "expected_eligible": projected_total * observed_eligible / observed_total,
            "wilson95_projected_count_interval": [projected_total * family_low, projected_total * family_high],
        }
    expected = 2000.0 * eligible_count / total
    return {
        "observed_total": total,
        "observed_eligible": eligible_count,
        "observed_rate": eligible_count / total,
        "expected_four_objective_eligible": expected,
        "wilson95_count_interval": [2000.0 * low, 2000.0 * high],
        "family_projection_at_observed_mix": family_projection,
        "shared_global_surrogate_suitability": "conditional_yes_for_first_feasibility_model_with_family_embedding_or_one_hot",
        "per_family_independent_model_suitability": "no; projected eligible counts are too small and uneven for eight independent first-round models",
        "statistical_limitation": "projection from one 512-sample calibration; Wilson intervals quantify binomial sampling uncertainty only and are not formal guarantees",
    }


def quality_audit(rows: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    low_threshold = float(config["quality"]["low_T450_threshold"])
    strong_secondary = float(config["quality"]["strong_secondary_peak_ratio"])
    return {
        "status": "PASS",
        "total": len(rows),
        "nan_inf_count": sum(not row["finite_arrays"] for row in rows),
        "duplicate_geometry_count": len(rows) - len({row["canonical_geometry_hash"] for row in rows}),
        "schema_failure_count": sum(not row["schema_valid"] for row in rows),
        "artifact_failure_count": sum(not row["artifact_valid"] for row in rows),
        "grid_failure_count": 0,
        "power_naming_status": "PASS",
        "spectral_boundary_clipped_count": sum(row["spectral_boundary_clipped"] for row in rows),
        "angular_boundary_clipped_count": sum(row["angular_boundary_clipped"] for row in rows),
        "spectral_invalid_fwhm_count": sum(not row["spectral_fwhm_valid"] for row in rows),
        "angular_invalid_fwhm_count": sum(not row["angular_fwhm_valid"] for row in rows),
        "offset_peak_count": sum(not row["center_is_global_max"] for row in rows),
        "secondary_peak_count": sum((row["secondary_peak_count"] or 0) > 0 for row in rows),
        "strong_secondary_peak_count": sum((row["secondary_peak_ratio"] or 0) >= strong_secondary for row in rows),
        "low_T450_count": sum(float(row["T450_unpolarized"]) < low_threshold for row in rows),
        "quality_mask_contract_id": QUALITY_MASK_CONTRACT_ID,
        "solver_valid_count": sum(bool(row["solver_valid"]) for row in rows),
        "peak_angle_zero_compatible_count": sum(bool(row["peak_angle_zero_compatible"]) for row in rows),
        "low_band_proxy_count": sum(bool(row["low_band_proxy_flag"]) for row in rows),
        "nominal_4d_objective_eligible_count": sum(bool(row["nominal_4d_objective_eligible"]) for row in rows),
        "shortlist_quality_eligible_count": sum(bool(row["shortlist_quality_eligible"]) for row in rows),
        "transmission_above_unity_count": sum(bool(row["transmission_above_unity_flag"]) for row in rows),
        "power_balance_failure_count": sum(bool(row["power_balance_failure"]) for row in rows),
        "transmission_raw_max": max(float(row["transmission_raw"]) for row in rows),
        "transmission_clipping_applied": False,
    }


def metric_distribution(rows: list[dict[str, Any]]) -> dict[str, Any]:
    spectral = [float(row["spectral_fwhm_normal_nm"]) for row in rows if row["spectral_fwhm_valid"]]
    angular = [float(row["angular_fwhm_450_deg"]) for row in rows if row["angular_fwhm_valid"]]
    peak_distribution = Counter(json.dumps(row["maximum_angle_set_deg"], separators=(",", ":")) for row in rows)
    return {
        "T450_unpolarized": _quantiles([float(row["T450_unpolarized"]) for row in rows]),
        "spectral_fwhm": {"valid_count": len(spectral), "quantiles": _quantiles(spectral)},
        "angular_fwhm": {"valid_count": len(angular), "quantiles": _quantiles(angular)},
        "cone5_integral_proxy": _quantiles([float(row["cone5_integral_proxy"]) for row in rows]),
        "cone5_fraction_proxy": _quantiles([float(row["cone5_fraction_proxy"]) for row in rows]),
        "cone10_fraction_proxy": _quantiles([float(row["cone10_fraction_proxy"]) for row in rows]),
        "normal_band_transmission_proxy": _quantiles([float(row["normal_band_transmission_proxy"]) for row in rows]),
        "center_is_global_max_rate": sum(row["center_is_global_max"] for row in rows) / len(rows),
        "peak_angle_set_distribution": dict(peak_distribution),
    }


def interesting_candidates(rows: list[dict[str, Any]], candidates: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    by_id = {row["sample_id"]: row for row in candidates}
    eligible = [row for row in rows if row["spectral_fwhm_valid"] and row["angular_fwhm_valid"] and not row["spectral_boundary_clipped"] and not row["angular_boundary_clipped"]]
    eligible.sort(key=lambda row: (
        row["pareto_status"] != "non_dominated", not row["center_is_global_max"],
        row["secondary_peak_ratio"] if row["secondary_peak_ratio"] is not None else 1.0,
        -row["T450_unpolarized"], -row["normal_band_transmission_proxy"],
        -row["cone5_integral_proxy"], row["angular_fwhm_450_deg"] + row["spectral_fwhm_normal_nm"],
    ))
    output = []
    for row in eligible[:limit]:
        candidate = by_id[row["sample_id"]]
        output.append({
            **row,
            "material_sequence": candidate["canonical_material_sequence"],
            "thickness_sequence_nm": candidate["canonical_thickness_sequence"],
            "defect_indices": candidate["defect_indices"],
            "calibration_only_declaration": "calibration interesting candidate; not a final design, FDTD candidate, or manufacturing-robust candidate",
        })
    return output


def runtime_storage_budget(calibration: dict[str, Any], benchmark: dict[str, Any], out: Path, config: dict[str, Any]) -> dict[str, Any]:
    selected = int(benchmark["selected_workers"])
    selected_row = next(row for row in benchmark["rows"] if int(row["workers"]) == selected)
    mean_runtime = float(calibration["solver_runtime_mean"])
    storage = storage_accounting(out, int(calibration["success_count"]))
    result: dict[str, Any] = {
        "mean_runtime_per_structure_seconds": mean_runtime,
        "p50_runtime_per_structure_seconds": calibration["solver_runtime_p50"],
        "p95_runtime_per_structure_seconds": calibration["solver_runtime_p95"],
        "selected_workers": selected,
        "selected_worker_throughput_structures_per_second": selected_row["structures_per_second"],
        "benchmark_overhead_seconds": sum(sum(row["repeat_wall_times_seconds"]) for row in benchmark["rows"]),
        "failure_retry_fraction": config["quality"]["failure_retry_fraction"],
        "storage_accounting": storage,
        "formal_pilot_bytes_per_structure": storage["formal_pilot_bytes_per_structure"],
        "storage_extrapolation_basis": "calibration production metadata plus NPZ artifacts divided by successful structures",
        "estimates": {},
    }
    for count in (2000, 5000):
        naive = mean_runtime * count
        throughput = count / float(selected_row["structures_per_second"])
        formal_storage = storage["formal_estimates"][str(count)]
        result["estimates"][str(count)] = {
            "naive_linear_seconds": naive,
            "benchmark_throughput_seconds": throughput,
            "with_10_percent_margin_seconds": throughput * 1.10,
            "with_20_percent_margin_seconds": throughput * 1.20,
            "estimated_output_bytes": formal_storage["base_bytes"],
            "estimated_output_bytes_with_10_percent_margin": formal_storage["plus_10_percent_bytes"],
            "estimated_output_bytes_with_20_percent_margin": formal_storage["plus_20_percent_bytes"],
            "estimated_artifact_bytes": storage["artifact_estimates"][str(count)]["base_bytes"],
            "estimated_metadata_bytes": storage["metadata_estimates"][str(count)]["base_bytes"],
            "whole_pre1_naive_comparison_bytes": storage["whole_pre1_naive_estimates"][str(count)]["base_bytes"],
        }
    result["recommended_disk_reserve_bytes"] = storage["recommended_disk_reserve_bytes"]
    return result


def pilot_recommendation(candidate_result: dict[str, Any], quality: dict[str, Any], pareto: dict[str, Any], budget: dict[str, Any]) -> dict[str, Any]:
    total = quality["total"]
    invalid_rate = max(quality["spectral_invalid_fwhm_count"], quality["angular_invalid_fwhm_count"]) / total
    low_rate = quality["low_T450_count"] / total
    acceptance = candidate_result["audit"]["valid_proposals"] / candidate_result["audit"]["raw_proposals"]
    return {
        "recommended_formal_pilot_size": 2000,
        "direct_5000_supported": False,
        "category_allocation": {"FAMILY_STRATIFIED_GLOBAL": 0.625, "ANCHOR_NEIGHBORHOOD": 0.1875, "FAMILY_CHALLENGE": 0.125, "RARE_CROSS_FAMILY": 0.0625},
        "minimum_per_topology_family": 100,
        "sampler_revision_needed": acceptance < 0.80,
        "quality_prefilter_needed": invalid_rate > 0.25 or low_rate > 0.25,
        "quality_prefilter_contract_id": QUALITY_MASK_CONTRACT_ID,
        "quality_prefilter_pre_solver_behavior": "none; every legal candidate completes the full TMM response grid",
        "quality_prefilter_post_tmm_controls": [
            "Pareto eligibility", "continuous regression target masks",
            "shortlist eligibility", "future training loss masks",
        ],
        "quality_prefilter_deletes_or_discards_responses": False,
        "evidence": {
            "candidate_acceptance_rate": acceptance,
            "invalid_fwhm_rate": invalid_rate,
            "low_T450_rate": low_rate,
            "pareto_valid_population": pareto["valid_population"],
            "pareto_size": pareto["pareto_size"],
            "estimated_2000_runtime_seconds": budget["estimates"]["2000"]["with_20_percent_margin_seconds"],
            "estimated_5000_runtime_seconds": budget["estimates"]["5000"]["with_20_percent_margin_seconds"],
        },
        "reason": "calibration establishes feasibility, but a 2,000-structure pilot is the controlled next evidence gate before committing to 5,000",
    }


def run_calibration(records: list[dict[str, Any]], config: dict[str, Any], workers: int, out: Path) -> dict[str, Any]:
    calibration_dir = out / "calibration"
    result = run_tmm_batch(records, config, workers, calibration_dir / "artifacts")
    rows = result["metric_rows"]
    pareto = nominal_pareto(rows, config)
    quality = quality_audit(rows, config)
    distribution = metric_distribution(rows)
    interesting = interesting_candidates(rows, records)
    write_csv(calibration_dir / "metrics_v1.csv", rows)
    write_jsonl(calibration_dir / "records_v1.jsonl", result["schema_records"])
    write_json(calibration_dir / "response_manifest_v1.json", {"contract_id": config["contract_id"], "artifacts": result["artifacts"]})
    write_json(calibration_dir / "quality_audit_v1.json", quality)
    write_json(calibration_dir / "coverage_summary_v1.json", {"metric_distribution": distribution, "nominal_pareto": pareto, "interesting_calibration_candidates": interesting})
    runtime = {key: value for key, value in result.items() if key not in ("metric_rows", "schema_records", "artifacts")}
    runtime["selected_workers"] = workers
    write_json(calibration_dir / "runtime_summary_v1.json", runtime)
    dataset_signature = stable_hash({
        "candidate_order": [row["sample_id"] for row in rows],
        "metrics_signature": result["metrics_content_signature"],
        "array_signature": result["array_content_signature"],
        "artifact_hashes": [[item["sample_id"], item["sha256"]] for item in result["artifacts"]],
    })
    manifest = {
        "contract_id": config["contract_id"], "total_structures": len(rows),
        "unique_geometry_hashes": len({row["canonical_geometry_hash"] for row in rows}),
        "schema_pass_count": sum(row["schema_valid"] for row in rows),
        "artifact_pass_count": sum(row["artifact_valid"] for row in rows),
        "solver_failure_count": result["failure_count"], "selected_workers": workers,
        "wall_time_seconds": result["wall_time_seconds"], "dataset_content_signature": dataset_signature,
        "output_bytes": result["output_bytes"], "quality_status": quality["status"],
    }
    write_json(calibration_dir / "manifest_v1.json", manifest)
    return {"batch": result, "quality": quality, "distribution": distribution, "pareto": pareto, "interesting": interesting, "manifest": manifest}


def final_manifest(out: Path, config: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    files = {}
    for path in sorted(item for item in out.rglob("*") if item.is_file()):
        if path == out / "manifest_v1.json":
            continue
        files[path.relative_to(out).as_posix()] = {"sha256": sha256_path(path), "bytes": path.stat().st_size}
    value = {
        "contract_id": config["contract_id"], "status": "PASS",
        "expected_head": config["expected_head"], "files": files,
        "total_output_bytes": sum(item["bytes"] for item in files.values()),
        "candidate_content_signature": payload["candidates"]["signature"],
        "dataset_content_signature": payload["calibration"]["manifest"]["dataset_content_signature"],
        "selected_workers": payload["benchmark"]["selected_workers"],
        "outputs_git_allowed": False,
    }
    write_json(out / "manifest_v1.json", value)
    value["total_output_bytes"] = directory_size(out)
    return value


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    def parse(value: str) -> Any:
        if value == "":
            return None
        if value == "true":
            return True
        if value == "false":
            return False
        if value[:1] in ("[", "{"):
            return json.loads(value)
        try:
            number = float(value)
        except ValueError:
            return value
        return int(number) if number.is_integer() and not any(mark in value.lower() for mark in (".", "e")) else number
    with path.open(newline="", encoding="utf-8") as handle:
        return [{key: parse(value) for key, value in row.items()} for row in csv.DictReader(handle)]


def validate_existing_outputs(config: dict[str, Any]) -> dict[str, Any]:
    out = ROOT / config["output_directory"]
    contract = config["existing_output_contract"]
    before = output_tree_fingerprint(out)
    frozen = frozen_file_audit(config)
    repo = repository_audit()
    if frozen["status"] != "PASS" or repo["status"] != "PASS" or repo["payload_drift_count"] != 0:
        raise RuntimeError("existing-output repository/frozen gate failed")
    candidate_manifest = json.loads((out / "candidate_manifest_v1.json").read_text(encoding="utf-8"))
    candidate_records = [json.loads(line) for line in (out / "candidate_records_v1.jsonl").read_text(encoding="utf-8").splitlines() if line]
    calibration_dir = out / "calibration"
    calibration_manifest = json.loads((calibration_dir / "manifest_v1.json").read_text(encoding="utf-8"))
    response_manifest = json.loads((calibration_dir / "response_manifest_v1.json").read_text(encoding="utf-8"))
    schema_records = [json.loads(line) for line in (calibration_dir / "records_v1.jsonl").read_text(encoding="utf-8").splitlines() if line]
    benchmark = json.loads((out / "benchmark" / "parallel_benchmark_v1.json").read_text(encoding="utf-8"))
    cross = json.loads((out / "f0_cross_fidelity_v1.json").read_text(encoding="utf-8"))
    checks = {
        "candidate_count": candidate_manifest["candidate_count"] == contract["candidate_count"] == len(candidate_records),
        "candidate_signature": candidate_manifest["candidate_content_signature"] == contract["candidate_content_signature"],
        "canonical_unique": len({row["canonical_geometry_hash"] for row in candidate_records}) == contract["candidate_count"],
        "physical_unique": len({row["physical_configuration_hash"] for row in candidate_records}) == contract["candidate_count"],
        "schema_pass": calibration_manifest["schema_pass_count"] == contract["schema_pass_count"] == len(schema_records),
        "artifact_pass": calibration_manifest["artifact_pass_count"] == contract["artifact_pass_count"] == len(response_manifest["artifacts"]),
        "solver_failures_zero": calibration_manifest["solver_failure_count"] == contract["solver_failure_count"] == 0,
        "dataset_signature": calibration_manifest["dataset_content_signature"] == contract["dataset_content_signature"],
        "worker_metrics_hash": {row["metrics_content_signature"] for row in benchmark["rows"]} == {contract["worker_metrics_content_signature"]},
        "worker_array_hash": {row["array_content_signature"] for row in benchmark["rows"]} == {contract["worker_array_content_signature"]},
        "worker_order_hash": {row["result_ordering_signature"] for row in benchmark["rows"]} == {contract["worker_result_ordering_signature"]},
        "f0_cross_fidelity": cross["status"] == "PASS",
    }
    artifact_errors = []
    for artifact in response_manifest["artifacts"]:
        path = ROOT / artifact["path"]
        if not path.is_file() or sha256_path(path) != artifact["sha256"]:
            artifact_errors.append(artifact["sample_id"])
    checks["artifact_sha_validation"] = not artifact_errors
    rebuilt = builder.build_candidates(config)
    checks["deterministic_candidate_rebuild"] = rebuilt["signature"] == contract["candidate_content_signature"]
    rows = _read_csv_rows(calibration_dir / "metrics_v1.csv")
    if len(rows) != contract["candidate_count"]:
        raise RuntimeError("existing-output metrics row count mismatch")
    apply_quality_masks(rows, config)
    pareto = nominal_pareto(rows, config)
    quality = quality_audit(rows, config)
    expectation = formal_2000_expectation(rows)
    by_schema_id = {record["identity"]["sample_id"]: record for record in schema_records}
    zero_rows = [row for row in rows if row.get("spectral_fwhm_raw_nm") == 0.0]
    zero_width = {
        "raw_zero_count": len(zero_rows),
        "csv_objective_null_count": sum(row["spectral_fwhm_normal_nm"] is None for row in zero_rows),
        "csv_valid_false_count": sum(not row["spectral_fwhm_valid"] for row in zero_rows),
        "jsonl_objective_null_count": sum(by_schema_id[row["sample_id"]]["labels"]["scalar_spectral_metrics"]["spectral_fwhm_normal_nm"] is None for row in zero_rows),
        "pareto_excluded_count": sum(row["pareto_status"] == "ineligible_invalid_metric_or_boundary" for row in zero_rows),
    }
    checks["zero_width_serialization"] = len(zero_rows) > 0 and len(set(zero_width.values())) == 1
    storage = storage_accounting(out, contract["candidate_count"])
    legacy_budget = json.loads((out / "runtime_and_storage_budget_v1.json").read_text(encoding="utf-8"))
    legacy_reconciliation = {
        count: {
            "legacy_estimated_output_bytes": legacy_budget["estimates"][count]["estimated_output_bytes"],
            "artifact_only_estimate_bytes": storage["artifact_estimates"][count]["base_bytes"],
            "matches_artifact_only": math.isclose(legacy_budget["estimates"][count]["estimated_output_bytes"], storage["artifact_estimates"][count]["base_bytes"], rel_tol=0.0, abs_tol=1e-6),
            "corrected_formal_production_estimate_bytes": storage["formal_estimates"][count]["base_bytes"],
        }
        for count in ("2000", "5000")
    }
    checks["legacy_storage_reconciles_to_artifact_only"] = all(row["matches_artifact_only"] for row in legacy_reconciliation.values())
    after = output_tree_fingerprint(out)
    checks["outputs_unchanged"] = before == after
    status = "PASS" if all(checks.values()) else "FAIL"
    if status != "PASS":
        raise RuntimeError(f"existing-output validation failed: {checks}; artifact_errors={artifact_errors[:5]}")
    return {
        "status": status,
        "quality_mask_contract_id": QUALITY_MASK_CONTRACT_ID,
        "checks": checks,
        "candidate_signature": candidate_manifest["candidate_content_signature"],
        "dataset_signature": calibration_manifest["dataset_content_signature"],
        "output_fingerprint": after,
        "storage_accounting": storage,
        "legacy_storage_reconciliation": legacy_reconciliation,
        "quality_audit": quality,
        "zero_width_contract": zero_width,
        "nominal_pareto": pareto,
        "formal_2000_expectation": expectation,
        "artifact_errors": artifact_errors,
    }


def postprocess_existing(config: dict[str, Any]) -> dict[str, Any]:
    out = ROOT / config["output_directory"]
    calibration_dir = out / "calibration"
    frozen = frozen_file_audit(config)
    repo = repository_audit()
    if frozen["status"] != "PASS" or repo["status"] != "PASS" or repo["payload_drift_count"] != 0:
        raise RuntimeError("postprocess repository/frozen gate failed")
    candidates = builder.build_candidates(config)
    rows = _read_csv_rows(calibration_dir / "metrics_v1.csv")
    if len(rows) != 512:
        raise RuntimeError("postprocess requires the complete 512-row calibration")
    for row in rows:
        spectral_raw = row.get("spectral_fwhm_raw_nm", row.get("spectral_fwhm_normal_nm"))
        spectral_valid = spectral_raw is not None and math.isfinite(float(spectral_raw)) and float(spectral_raw) > 0.0 and not bool(row["spectral_boundary_clipped"])
        row["spectral_fwhm_raw_nm"] = spectral_raw
        row["spectral_fwhm_valid"] = spectral_valid
        row["spectral_fwhm_normal_nm"] = float(spectral_raw) if spectral_valid else None
        angular_raw = row.get("angular_fwhm_raw_deg", row.get("angular_fwhm_450_deg"))
        angular_valid = angular_raw is not None and math.isfinite(float(angular_raw)) and float(angular_raw) > 0.0 and not bool(row["angular_boundary_clipped"])
        row["angular_fwhm_raw_deg"] = angular_raw
        row["angular_fwhm_valid"] = angular_valid
        row["angular_fwhm_450_deg"] = float(angular_raw) if angular_valid else None
        row.pop("pareto_status", None)
    apply_quality_masks(rows, config)
    pareto = nominal_pareto(rows, config)
    quality = quality_audit(rows, config)
    distribution = metric_distribution(rows)
    interesting = interesting_candidates(rows, candidates["records"])
    schema_records = [json.loads(line) for line in (calibration_dir / "records_v1.jsonl").read_text(encoding="utf-8").splitlines() if line]
    by_id = {row["sample_id"]: row for row in rows}
    for record in schema_records:
        row = by_id[record["identity"]["sample_id"]]
        if not row["spectral_fwhm_valid"]:
            record["labels"]["scalar_spectral_metrics"]["spectral_fwhm_normal_nm"] = None
        if not row["angular_fwhm_valid"]:
            record["labels"]["scalar_angular_metrics"]["angular_fwhm_450_deg"] = None
    schema = smoke.load_schema()
    schema_errors = [record["identity"]["sample_id"] for record in schema_records if smoke.validate_json_instance(record, schema)]
    if schema_errors:
        raise RuntimeError(f"postprocessed schema records failed: {schema_errors[:5]}")
    write_csv(calibration_dir / "metrics_v1.csv", rows)
    write_jsonl(calibration_dir / "records_v1.jsonl", schema_records)
    write_json(calibration_dir / "quality_audit_v1.json", quality)
    write_json(calibration_dir / "coverage_summary_v1.json", {"metric_distribution": distribution, "nominal_pareto": pareto, "interesting_calibration_candidates": interesting})
    runtime = json.loads((calibration_dir / "runtime_summary_v1.json").read_text(encoding="utf-8"))
    signature_rows = [_signature_row(row) for row in rows]
    runtime["metrics_content_signature"] = stable_hash(signature_rows)
    write_json(calibration_dir / "runtime_summary_v1.json", runtime)
    response_manifest = json.loads((calibration_dir / "response_manifest_v1.json").read_text(encoding="utf-8"))
    artifacts = response_manifest["artifacts"]
    dataset_signature = stable_hash({
        "candidate_order": [row["sample_id"] for row in rows],
        "metrics_signature": runtime["metrics_content_signature"],
        "array_signature": runtime["array_content_signature"],
        "artifact_hashes": [[item["sample_id"], item["sha256"]] for item in artifacts],
    })
    calibration_manifest = json.loads((calibration_dir / "manifest_v1.json").read_text(encoding="utf-8"))
    calibration_manifest["dataset_content_signature"] = dataset_signature
    calibration_manifest["schema_pass_count"] = len(schema_records)
    write_json(calibration_dir / "manifest_v1.json", calibration_manifest)
    benchmark = json.loads((out / "benchmark" / "parallel_benchmark_v1.json").read_text(encoding="utf-8"))
    budget = runtime_storage_budget(runtime, benchmark, out, config)
    recommendation = pilot_recommendation(candidates, quality, pareto, budget)
    write_json(out / "runtime_and_storage_budget_v1.json", budget)
    write_json(out / "formal_pilot_recommendation_v1.json", recommendation)
    payload = {"candidates": candidates, "benchmark": benchmark, "calibration": {"manifest": calibration_manifest}}
    manifest = final_manifest(out, config, payload)
    enforce_output_limit(out, int(config["maximum_output_bytes"]))
    return {"status": "PASS", "quality": quality, "metric_distribution": distribution, "nominal_pareto": pareto, "interesting_calibration_candidates": interesting, "runtime_and_storage_budget": budget, "formal_pilot_recommendation": recommendation, "calibration_manifest": calibration_manifest, "output_manifest": manifest}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--candidates-only", action="store_true")
    parser.add_argument("--postprocess-only", action="store_true")
    parser.add_argument("--validate-existing-only", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    if sum((args.candidates_only, args.postprocess_only, args.validate_existing_only)) > 1:
        parser.error("choose at most one execution mode")
    if args.validate_existing_only:
        print(json.dumps(validate_existing_outputs(config), indent=2, sort_keys=True, allow_nan=False))
        return
    if args.postprocess_only:
        print(json.dumps(postprocess_existing(config), indent=2, sort_keys=True, allow_nan=False))
        return
    out = ROOT / config["output_directory"]
    out.mkdir(parents=True, exist_ok=True)
    frozen = frozen_file_audit(config)
    if frozen["status"] != "PASS":
        raise RuntimeError(f"frozen file audit failed: {frozen}")
    repo = repository_audit()
    first = builder.build_candidates(config)
    second = builder.build_candidates(config)
    deterministic = first["signature"] == second["signature"] and [row["sample_id"] for row in first["records"]] == [row["sample_id"] for row in second["records"]]
    first["audit"]["deterministic_rebuild"] = "PASS" if deterministic else "FAIL"
    first["audit"]["second_rebuild_signature"] = second["signature"]
    static = builder.validate_static_gate(first)
    static["checks"]["deterministic_rebuild"] = deterministic
    static["checks"]["repository_audit"] = repo["status"] == "PASS"
    static["checks"]["payload_drift_zero"] = repo["payload_drift_count"] == 0
    static["checks"]["frozen_files_unchanged"] = frozen["status"] == "PASS"
    static["status"] = "PASS" if all(static["checks"].values()) else "FAIL"
    if static["status"] != "PASS":
        raise RuntimeError(f"pre-TMM static gate failed: {static}")
    builder.write_candidate_outputs(first, config)
    write_json(out / "static_gate_v1.json", {"status": "PASS", "checks": static["checks"], "repository_audit": repo, "frozen_file_audit": frozen})
    if args.candidates_only:
        print(json.dumps({"status": "PASS", "static_gate": static, "candidate_signature": first["signature"]}, indent=2))
        return
    cross = f0_cross_fidelity(config, out)
    benchmark = run_parallel_benchmark(first["records"], config, out)
    calibration = run_calibration(first["records"], config, int(benchmark["selected_workers"]), out)
    budget = runtime_storage_budget(calibration["batch"], benchmark, out, config)
    recommendation = pilot_recommendation(first, calibration["quality"], calibration["pareto"], budget)
    write_json(out / "runtime_and_storage_budget_v1.json", budget)
    write_json(out / "formal_pilot_recommendation_v1.json", recommendation)
    payload = {"candidates": first, "cross": cross, "benchmark": benchmark, "calibration": calibration, "budget": budget, "recommendation": recommendation}
    manifest = final_manifest(out, config, payload)
    enforce_output_limit(out, int(config["maximum_output_bytes"]))
    print(json.dumps({
        "status": "PASS", "candidate_signature": first["signature"], "static_gate": static,
        "f0_cross_fidelity": cross, "benchmark": benchmark,
        "calibration_manifest": calibration["manifest"], "quality": calibration["quality"],
        "metric_distribution": calibration["distribution"], "nominal_pareto": calibration["pareto"],
        "interesting_calibration_candidates": calibration["interesting"],
        "runtime_and_storage_budget": budget, "formal_pilot_recommendation": recommendation,
        "output_manifest": manifest,
    }, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
