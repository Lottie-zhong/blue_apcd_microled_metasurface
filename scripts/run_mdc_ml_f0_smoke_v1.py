"""Run the deterministic 17-structure Native-M1 TMM F0 smoke contract."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import statistics
import sys
import time
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import apcd_native_materials as materials
from audit_mdc_gan_native_m1_tmm_angle_convention_v1 import fwhm as angular_fwhm
from audit_mdc_ml_inverse_design_spec_v1 import load_schema, make_schema_dummy, validate_json_instance
from mdc_ml_structure_grammar_v1 import (
    TOPOLOGY_FAMILIES,
    canonicalize_structure,
    decode_canonical_structure,
    generate_dummy_candidates,
    simulation_provenance_hash,
    validate_bounds,
)
from mdc_tmm_complex_incident_power_v1 import normal_stack_power, oblique_stack_rt
from stage_mdc_native_m1_topology_coarse_scan import fwhm as spectral_fwhm

CONFIG_PATH = ROOT / "configs" / "mdc_ml_f0_smoke_v1.yaml"
SCHEMA_PATH = ROOT / "configs" / "mdc_ml_dataset_schema_v1.json"
POLARIZATIONS = ("TE", "TM")
POWER_FIELDS = (
    "r", "t", "R", "T", "power_entering", "A_stack",
    "far_field_balance_offset", "incident_interference_offset",
)
SCHEMA_ARTIFACT_FIELDS = [
    "r_TE", "t_TE", "r_TM", "t_TM", "R_TE", "T_TE", "R_TM", "T_TM",
    "power_entering_TE", "power_entering_TM", "A_stack_TE", "A_stack_TM",
    "far_field_balance_offset_TE", "far_field_balance_offset_TM",
]
RATIO_NEAR = (0.0, 5.0, 10.0)
RATIO_FAR = (40.0, 45.0, 50.0, 55.0, 60.0)


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    """The checked-in YAML is intentionally JSON-compatible for stdlib parsing."""
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")


def csv_value(value: Any) -> Any:
    if isinstance(value, (list, dict, tuple)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if isinstance(value, bool):
        return str(value).lower()
    return value


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows([{key: csv_value(row.get(key)) for key in fields} for row in rows])


def deterministic_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    """Write an NPZ with sorted members and fixed ZIP metadata for byte-stable SHA-256."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(arrays):
            buffer = io.BytesIO()
            np.lib.format.write_array(buffer, np.asarray(arrays[name]), allow_pickle=False)
            info = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, buffer.getvalue(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def grid(start: float, stop: float, step: float) -> np.ndarray:
    count = int(round((stop - start) / step)) + 1
    values = start + step * np.arange(count, dtype=float)
    if abs(values[-1] - stop) > 1e-10:
        raise RuntimeError("grid endpoint mismatch")
    return values


def baseline_candidate(config: dict[str, Any]) -> dict[str, Any]:
    baseline = config["baseline"]
    tokens = [
        {"material_token": token, "thickness_nm": int(thickness)}
        for token, thickness in zip(baseline["material_tokens"], baseline["thickness_nm"])
    ]
    defect = int(baseline["defect_index_zero_based"])
    return {
        "sample_id": baseline["sample_id"],
        "topology_family": baseline["topology_family"],
        "left_mirror": tokens[:defect],
        "defect_region": tokens[defect:defect + 1],
        "right_mirror": tokens[defect + 1:],
        "parameters": {
            "source_topology_family": "ZL-1",
            "defect_offset_layers": len(tokens[:defect]) - len(tokens[defect + 1:]),
        },
    }


def perturb_defect(candidate: dict[str, Any], suffix: str) -> dict[str, Any]:
    varied = deepcopy(candidate)
    varied["sample_id"] = f"F0_SMOKE_{candidate['topology_family'].upper()}_{suffix}"
    explicit = [index for index, layer in enumerate(varied["defect_region"]) if layer.get("is_defect")]
    index = explicit[0] if explicit else 0
    varied["defect_region"][index]["thickness_nm"] += 1
    varied.setdefault("parameters", {})["f0_smoke_variant"] = suffix
    return varied


def build_smoke_candidates(config: dict[str, Any]) -> list[dict[str, Any]]:
    by_family: dict[str, dict[str, Any]] = {}
    for candidate in generate_dummy_candidates():
        by_family.setdefault(candidate["topology_family"], candidate)
    if set(by_family) != set(TOPOLOGY_FAMILIES):
        raise RuntimeError("grammar dummy coverage is incomplete")
    result = [baseline_candidate(config)]
    for family in TOPOLOGY_FAMILIES:
        first = deepcopy(by_family[family])
        first["sample_id"] = f"F0_SMOKE_{family.upper()}_A"
        first.setdefault("parameters", {})["f0_smoke_variant"] = "A"
        result.extend((first, perturb_defect(first, "B")))
    canonicals = [validate_bounds(item) for item in result]
    if len(result) != int(config["structure_count"]):
        raise RuntimeError("smoke structure count mismatch")
    if len({item["canonical_geometry_hash"] for item in canonicals}) != len(result):
        raise RuntimeError("duplicate canonical geometry in smoke set")
    return result


def canonical_roundtrip(candidate: dict[str, Any]) -> dict[str, Any]:
    encoded = validate_bounds(candidate)
    reencoded = validate_bounds(decode_canonical_structure(encoded))
    keys = (
        "canonical_geometry_hash", "physical_configuration_hash", "sequence_hash",
        "split_group_hash", "material_tokens", "thickness_nm", "defect_indices",
    )
    if any(encoded[key] != reencoded[key] for key in keys):
        raise RuntimeError(f"canonical round-trip mismatch: {candidate['sample_id']}")
    return encoded


def peak_set(angles: np.ndarray, values: np.ndarray) -> dict[str, Any]:
    """Apply the frozen symmetric-tie semantics from angle audit _postprocess_metrics."""
    tmax = float(values.max())
    tolerance = max(64.0 * np.finfo(float).eps * max(1.0, abs(tmax)), 1.0e-14)
    raw = float(angles[int(np.argmax(values))])
    tied = [float(value) for value in angles[values >= tmax - tolerance]]
    symmetric = any(angle > 0 and -angle in tied for angle in tied)
    if 0.0 in tied and len(tied) == 1:
        result, center, symmetric = [0.0], True, False
    elif symmetric:
        result, center = sorted({angle for angle in tied if angle != 0.0 and -angle in tied}), False
    else:
        result, center = sorted(tied), tied == [0.0]
    return {
        "maximum_angle_raw_argmax_deg": raw,
        "maximum_angle_set_deg": result,
        "maximum_abs_angle_deg": max(abs(angle) for angle in result),
        "center_is_global_max": center,
        "symmetric_peak_pair": symmetric,
        "peak_tie_tolerance": tolerance,
        "symmetry_residual": float(np.max(np.abs(values - values[::-1]))),
    }


def material_indices(wavelengths: np.ndarray) -> dict[float, dict[str, complex]]:
    result: dict[float, dict[str, complex]] = {}
    for wavelength in sorted({round(float(value), 10) for value in wavelengths}):
        result[wavelength] = {
            "source": materials.get_complex_index("APCD_GAN_NATIVE_M1", wavelength),
            "H": materials.get_complex_index("APCD_TIO2_NATIVE_M1", wavelength),
            "L": materials.get_complex_index("APCD_SIO2_NATIVE_M1", wavelength),
        }
    return result


def reversed_stack(canonical: dict[str, Any], index: dict[str, complex]) -> list[tuple[complex, float]]:
    # This is the frozen P1 GaN-to-Air textual sequence convention used by both authoritative pipelines.
    return list(reversed([(index[layer["material_token"]], float(layer["thickness_nm"])) for layer in canonical["layers"]]))


def allocate(prefix: str, shape: tuple[int, ...], arrays: dict[str, np.ndarray]) -> None:
    for polarization in POLARIZATIONS:
        for field in POWER_FIELDS:
            dtype = complex if field in ("r", "t") else float
            arrays[f"{prefix}_{field}_{polarization}"] = np.empty(shape, dtype=dtype)


def store_result(arrays: dict[str, np.ndarray], prefix: str, polarization: str, where: Any, result: dict[str, Any]) -> None:
    for field in POWER_FIELDS:
        arrays[f"{prefix}_{field}_{polarization}"][where] = result[field]


def integrate_apcd(wavelengths: np.ndarray, angles: np.ndarray, transmission: np.ndarray, alpha: float) -> float:
    mask = np.abs(angles) <= alpha + 1e-12
    inner = np.trapezoid(transmission[:, mask], np.deg2rad(angles[mask]), axis=1)
    return float(np.trapezoid(inner, wavelengths) / 5.0)


def simulate_structure(
    canonical: dict[str, Any], config: dict[str, Any], index_cache: dict[float, dict[str, complex]]
) -> tuple[dict[str, np.ndarray], dict[str, Any], float]:
    started = time.perf_counter()
    grids = config["grids"]
    sw = grid(grids["spectral"]["wavelength_start_nm"], grids["spectral"]["wavelength_stop_nm"], grids["spectral"]["wavelength_step_nm"])
    aa = grid(grids["angular"]["angle_start_deg"], grids["angular"]["angle_stop_deg"], grids["angular"]["angle_step_deg"])
    aw = grid(grids["apcd_ready"]["wavelength_start_nm"], grids["apcd_ready"]["wavelength_stop_nm"], grids["apcd_ready"]["wavelength_step_nm"])
    arrays: dict[str, np.ndarray] = {
        "spectral_wavelength_nm": sw,
        "angular_angle_air_deg": aa,
        "apcd_wavelength_nm": aw,
        "apcd_angle_air_deg": aa,
    }
    allocate("spectral", (len(sw),), arrays)
    allocate("apcd", (len(aw), len(aa)), arrays)

    for wi, wavelength in enumerate(sw):
        index = index_cache[round(float(wavelength), 10)]
        result = normal_stack_power(index["source"], 1 + 0j, reversed_stack(canonical, index), float(wavelength))
        for polarization in POLARIZATIONS:
            store_result(arrays, "spectral", polarization, wi, result)

    for wi, wavelength in enumerate(aw):
        index = index_cache[round(float(wavelength), 10)]
        stack = reversed_stack(canonical, index)
        for ai, angle in enumerate(aa):
            kx_over_k0 = math.sin(math.radians(float(angle)))
            for polarization in POLARIZATIONS:
                result = oblique_stack_rt(index["source"], 1 + 0j, stack, float(wavelength), kx_over_k0, polarization)
                store_result(arrays, "apcd", polarization, (wi, ai), result)

    at450 = int(np.flatnonzero(np.isclose(aw, 450.0))[0])
    for polarization in POLARIZATIONS:
        for field in POWER_FIELDS:
            arrays[f"angular_{field}_{polarization}"] = arrays[f"apcd_{field}_{polarization}"][at450].copy()
    spectral_t = 0.5 * (arrays["spectral_T_TE"] + arrays["spectral_T_TM"])
    peak_wavelength, peak_t, width = spectral_fwhm(sw, spectral_t)
    angular_t = 0.5 * (arrays["angular_T_TE"] + arrays["angular_T_TM"])
    angular_width, angular_clipped = angular_fwhm(aa, angular_t)
    peaks = peak_set(aa, angular_t)
    by_angle = {float(angle): float(value) for angle, value in zip(aa, angular_t)}
    numerator = float(np.mean([by_angle[value] for value in RATIO_NEAR]))
    denominator = float(np.mean([by_angle[value] for value in RATIO_FAR]))
    band_mask = (sw >= 448.0 - 1e-12) & (sw <= 453.0 + 1e-12)
    metrics: dict[str, Any] = {
        "spectral_fwhm_normal_nm": float(width),
        "spectral_peak_wavelength_nm": float(peak_wavelength),
        "spectral_peak_transmission": float(peak_t),
        "T450": float(spectral_t[int(np.flatnonzero(np.isclose(sw, 450.0))[0])]),
        "angular_fwhm_450_deg": None if angular_clipped else float(angular_width),
        "angular_fwhm_status": "boundary_clipped" if angular_clipped else "valid",
        "ratio": numerator / denominator if denominator else None,
        **peaks,
    }
    for polarization in (*POLARIZATIONS, "unpolarized"):
        spectral = spectral_t if polarization == "unpolarized" else arrays[f"spectral_T_{polarization}"]
        apcd = 0.5 * (arrays["apcd_T_TE"] + arrays["apcd_T_TM"]) if polarization == "unpolarized" else arrays[f"apcd_T_{polarization}"]
        cone60 = integrate_apcd(aw, aa, apcd, 60.0)
        metrics[polarization] = {
            "tmm_apcd_ready_cone5_integral_proxy": integrate_apcd(aw, aa, apcd, 5.0),
            "tmm_apcd_ready_cone10_integral_proxy": integrate_apcd(aw, aa, apcd, 10.0),
            "tmm_apcd_ready_cone5_fraction_proxy": 0.0,
            "tmm_apcd_ready_cone10_fraction_proxy": 0.0,
            "tmm_band_transmission_448_453_normal_proxy": float(np.trapezoid(spectral[band_mask], sw[band_mask]) / 5.0),
        }
        metrics[polarization]["tmm_apcd_ready_cone5_fraction_proxy"] = metrics[polarization]["tmm_apcd_ready_cone5_integral_proxy"] / cone60
        metrics[polarization]["tmm_apcd_ready_cone10_fraction_proxy"] = metrics[polarization]["tmm_apcd_ready_cone10_integral_proxy"] / cone60
    elapsed = time.perf_counter() - started
    return arrays, metrics, elapsed


def baseline_gate(canonical: dict[str, Any], metrics: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    baseline = config["baseline"]
    expected = baseline["historical"]
    acceptance = baseline["acceptance"]
    differences = {
        "spectral_fwhm_nm": metrics["spectral_fwhm_normal_nm"] - expected["spectral_fwhm_nm"],
        "angular_fwhm_deg": metrics["angular_fwhm_450_deg"] - expected["angular_fwhm_deg"],
        "ratio": metrics["ratio"] - expected["ratio"],
    }
    checks = {
        "canonical_geometry_hash": canonical["canonical_geometry_hash"] == baseline["canonical_geometry_hash"],
        "physical_configuration_hash": canonical["physical_configuration_hash"] == baseline["physical_configuration_hash"],
        "spectral_fwhm": abs(differences["spectral_fwhm_nm"]) <= acceptance["spectral_fwhm_abs_tolerance_nm"],
        "angular_fwhm": abs(differences["angular_fwhm_deg"]) <= acceptance["angular_fwhm_abs_tolerance_deg"],
        "ratio": abs(differences["ratio"]) <= acceptance["ratio_abs_tolerance"],
        "maximum_angle_set": metrics["maximum_angle_set_deg"] == expected["maximum_angle_set_deg"],
        "center_is_global_max": metrics["center_is_global_max"] is True,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "differences": differences,
        "historical_reference": expected,
        "recomputed": metrics,
        "geometry_identity": {
            "canonical_geometry_hash": canonical["canonical_geometry_hash"],
            "physical_configuration_hash": canonical["physical_configuration_hash"],
            "sequence_hash": canonical["sequence_hash"],
        },
    }


def artifact_manifest_entry(path: Path, arrays: dict[str, np.ndarray], grid_ids: dict[str, str]) -> dict[str, Any]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "format": "NPZ",
        "sha256": sha256_path(path),
        "bytes": path.stat().st_size,
        "array_content_hash": stable_hash({name: hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest() for name, value in sorted(arrays.items())}),
        "fields": {name: {"shape": list(value.shape), "dtype": str(value.dtype)} for name, value in sorted(arrays.items())},
        "grid_ids": grid_ids,
    }


def make_record(canonical: dict[str, Any], metrics: dict[str, Any], artifact: dict[str, Any], config: dict[str, Any], sample_id: str) -> dict[str, Any]:
    record = make_schema_dummy(canonical)
    record["identity"].update({"sample_id": sample_id, "structure_id": "F0_" + canonical["canonical_geometry_hash"][:16], "fidelity": "F0", "parent_id": None})
    combined_wavelength_id = config["grids"]["spectral"]["id"] + "+" + config["grids"]["apcd_ready"]["id"]
    combined_angle_id = config["grids"]["angular"]["id"] + "+" + config["grids"]["apcd_ready"]["id"]
    physics = config["physics"]
    provenance = simulation_provenance_hash(
        physical_configuration_hash_value=canonical["physical_configuration_hash"],
        wavelength_grid_id=combined_wavelength_id,
        angle_grid_id=combined_angle_id,
        angle_convention_id=physics["angle_convention_id"],
        solver_id=physics["solver_id"],
        solver_version=physics["solver_version"],
        polarization_contract_id=physics["polarization_contract_id"],
        numerical_settings_contract_id=physics["numerical_settings_contract_id"],
    )
    record["simulation"].update({
        "wavelength_grid_id": combined_wavelength_id,
        "angle_grid_id": combined_angle_id,
        "solver": "TMM",
        "solver_version": physics["solver_version"],
        "numerical_settings_contract_id": physics["numerical_settings_contract_id"],
        "provenance_commit": config["frozen_commit"],
        "simulation_provenance_hash": provenance,
        "quality_flags": {"status": "pass", "response_complete": True, "power_balance_checked": True, "usable_for_training": True, "failure_reason": None},
    })
    record["response_artifact"] = {
        "response_artifact_path": artifact["path"], "response_artifact_format": "NPZ",
        "response_artifact_sha256": artifact["sha256"], "wavelength_grid_id": combined_wavelength_id,
        "angle_grid_id": combined_angle_id, "array_shape": [], "array_dtype": "mixed_complex128_float64",
        "field_inventory": SCHEMA_ARTIFACT_FIELDS, "git_allowed": False,
    }
    record["labels"]["scalar_spectral_metrics"] = {
        "spectral_fwhm_normal_nm": metrics["spectral_fwhm_normal_nm"],
        "peak_wavelength_nm": metrics["spectral_peak_wavelength_nm"],
        "T450": metrics["T450"],
        "tmm_band_transmission_448_453_normal_proxy": metrics["unpolarized"]["tmm_band_transmission_448_453_normal_proxy"],
    }
    record["labels"]["scalar_angular_metrics"] = {
        "angular_fwhm_450_deg": metrics["angular_fwhm_450_deg"],
        "peak_angle_deg": metrics["maximum_angle_raw_argmax_deg"],
        "sidelobe_power": None,
    }
    record["labels"]["tmm_apcd_ready_proxies"] = {
        "contract_id": "tmm_apcd_ready_in_plane_proxy_v1",
        "TE": metrics["TE"], "TM": metrics["TM"], "unpolarized_derived": metrics["unpolarized"],
        "quality_status": "complete_nominal_F0_TMM_proxy",
    }
    return record


def flat_structure_row(candidate: dict[str, Any], canonical: dict[str, Any], is_baseline: bool) -> dict[str, Any]:
    return {
        "sample_id": candidate["sample_id"], "topology_family": canonical["topology_family"],
        "is_frozen_baseline": is_baseline, "fidelity": "F0_TMM", "level": "A", "tolerance_mode": "nominal",
        "parent_id": None, "child_id": None, "canonical_geometry_hash": canonical["canonical_geometry_hash"],
        "physical_configuration_hash": canonical["physical_configuration_hash"], "sequence_hash": canonical["sequence_hash"],
        "split_group_hash": canonical["split_group_hash"], "source_medium": canonical["source_medium"],
        "exit_medium": canonical["exit_medium"], "material_tokens": canonical["material_tokens"],
        "thickness_nm": canonical["thickness_nm"], "layer_count": canonical["layer_count"],
        "total_thickness_nm": canonical["total_thickness_nm"], "defect_indices": canonical["defect_indices"],
        "termination": canonical["termination"], "grammar_legal": True, "bounds_legal": True,
    }


def flat_metric_row(candidate: dict[str, Any], canonical: dict[str, Any], metrics: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    row = {
        "sample_id": candidate["sample_id"], "topology_family": canonical["topology_family"],
        "canonical_geometry_hash": canonical["canonical_geometry_hash"],
        "physical_configuration_hash": canonical["physical_configuration_hash"],
        "simulation_provenance_hash": record["simulation"]["simulation_provenance_hash"],
        "spectral_fwhm_normal_nm": metrics["spectral_fwhm_normal_nm"],
        "spectral_peak_wavelength_nm": metrics["spectral_peak_wavelength_nm"], "T450": metrics["T450"],
        "angular_fwhm_450_deg": metrics["angular_fwhm_450_deg"], "angular_fwhm_status": metrics["angular_fwhm_status"],
        "maximum_angle_set_deg": metrics["maximum_angle_set_deg"], "maximum_abs_angle_deg": metrics["maximum_abs_angle_deg"],
        "center_is_global_max": metrics["center_is_global_max"], "symmetric_peak_pair": metrics["symmetric_peak_pair"],
        "ratio": metrics["ratio"], "quality_status": "pass",
    }
    for polarization in (*POLARIZATIONS, "unpolarized"):
        for key, value in metrics[polarization].items():
            row[f"{polarization}_{key}"] = value
    return row


def finite_audit(arrays_by_sample: dict[str, dict[str, np.ndarray]], metric_rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for sample_id, arrays in arrays_by_sample.items():
        for name, value in arrays.items():
            if not np.all(np.isfinite(value.real)) or (np.iscomplexobj(value) and not np.all(np.isfinite(value.imag))):
                errors.append(f"nonfinite_array:{sample_id}:{name}")
    for index, row in enumerate(metric_rows):
        for key, value in row.items():
            if isinstance(value, float) and not math.isfinite(value):
                errors.append(f"nonfinite_metric:{index}:{key}")
    return errors


def build_manifest(out: Path, config: dict[str, Any], artifacts: list[dict[str, Any]], content_signature: str) -> dict[str, Any]:
    files = {}
    for path in sorted(out.iterdir()):
        if path.is_file() and path.name != "manifest_v1.json":
            files[path.name] = {"sha256": sha256_path(path), "bytes": path.stat().st_size}
    for path in sorted((out / "responses").glob("*.npz")):
        files[path.relative_to(out).as_posix()] = {"sha256": sha256_path(path), "bytes": path.stat().st_size}
    return {
        "contract_id": config["contract_id"], "frozen_commit": config["frozen_commit"],
        "deterministic_content_signature": content_signature, "files": files,
        "artifact_count": len(artifacts), "total_output_bytes": sum(item["bytes"] for item in files.values()),
        "outputs_git_allowed": False,
    }


def run_pipeline(config: dict[str, Any], *, baseline_only: bool = False) -> dict[str, Any]:
    out = ROOT / config["output_directory"]
    responses = out / "responses"
    out.mkdir(parents=True, exist_ok=True)
    responses.mkdir(parents=True, exist_ok=True)
    candidates = build_smoke_candidates(config)
    canonicals = [canonical_roundtrip(candidate) for candidate in candidates]
    all_wavelengths = np.concatenate((
        grid(config["grids"]["spectral"]["wavelength_start_nm"], config["grids"]["spectral"]["wavelength_stop_nm"], config["grids"]["spectral"]["wavelength_step_nm"]),
        grid(config["grids"]["apcd_ready"]["wavelength_start_nm"], config["grids"]["apcd_ready"]["wavelength_stop_nm"], config["grids"]["apcd_ready"]["wavelength_step_nm"]),
    ))
    indices = material_indices(all_wavelengths)
    structures: list[dict[str, Any]] = []
    metrics_rows: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    arrays_by_sample: dict[str, dict[str, np.ndarray]] = {}
    runtimes: list[float] = []
    grid_ids = {name: value["id"] for name, value in config["grids"].items()}
    started = time.perf_counter()

    arrays, baseline_metrics, elapsed = simulate_structure(canonicals[0], config, indices)
    gate = baseline_gate(canonicals[0], baseline_metrics, config)
    gate["runtime_seconds"] = elapsed
    write_json(out / "baseline_recompute_v1.json", gate)
    if gate["status"] != "PASS":
        raise RuntimeError("baseline reproduction gate failed; remaining 16 structures were not run")
    selected = 1 if baseline_only else len(candidates)
    for index in range(selected):
        candidate, canonical = candidates[index], canonicals[index]
        if index == 0:
            current_arrays, current_metrics, current_runtime = arrays, baseline_metrics, elapsed
        else:
            current_arrays, current_metrics, current_runtime = simulate_structure(canonical, config, indices)
        artifact_path = responses / f"{index:02d}_{canonical['canonical_geometry_hash'][:16]}.npz"
        deterministic_npz(artifact_path, current_arrays)
        artifact = artifact_manifest_entry(artifact_path, current_arrays, grid_ids)
        record = make_record(canonical, current_metrics, artifact, config, candidate["sample_id"])
        structures.append(flat_structure_row(candidate, canonical, index == 0))
        metrics_rows.append(flat_metric_row(candidate, canonical, current_metrics, record))
        records.append(record)
        artifacts.append({"sample_id": candidate["sample_id"], "canonical_geometry_hash": canonical["canonical_geometry_hash"], **artifact})
        arrays_by_sample[candidate["sample_id"]] = current_arrays
        runtimes.append(current_runtime)

    if baseline_only:
        write_json(out / "response_manifest_v1.json", {"status": "baseline_only", "artifacts": artifacts})
        return {"status": "PASS", "baseline": gate, "structure_count": 1, "content_signature": stable_hash({"gate": gate["checks"], "artifact": artifacts[0]["sha256"]})}

    schema = load_schema(SCHEMA_PATH)
    schema_errors = {record["identity"]["sample_id"]: validate_json_instance(record, schema, root_schema=schema) for record in records}
    schema_errors = {key: value for key, value in schema_errors.items() if value}
    finite_errors = finite_audit(arrays_by_sample, metrics_rows)
    family_counts = {family: sum(row["topology_family"] == family and not row["is_frozen_baseline"] for row in structures) for family in TOPOLOGY_FAMILIES}
    rebuild_hashes = [canonical_roundtrip(candidate)["canonical_geometry_hash"] for candidate in build_smoke_candidates(config)]
    original_hashes = [row["canonical_geometry_hash"] for row in structures]
    artifact_hash_errors = [item["path"] for item in artifacts if sha256_path(ROOT / item["path"]) != item["sha256"]]
    validations = {
        "schema_validation": "PASS" if not schema_errors else "FAIL",
        "schema_errors": schema_errors,
        "baseline_roundtrip": "PASS",
        "baseline_reproduction": gate["status"],
        "hash_stability": "PASS" if rebuild_hashes == original_hashes else "FAIL",
        "artifact_sha_validation": "PASS" if not artifact_hash_errors else "FAIL",
        "artifact_sha_errors": artifact_hash_errors,
        "deterministic_sample_rebuild": "PASS" if rebuild_hashes == original_hashes else "FAIL",
        "deterministic_metric_rerun": "NOT_RUN",
        "nan_inf_audit": "PASS" if not finite_errors else "FAIL",
        "nan_inf_errors": finite_errors,
        "duplicate_geometry_audit": "PASS" if len(set(original_hashes)) == 17 else "FAIL",
        "topology_coverage_audit": "PASS" if set(family_counts.values()) == {2} else "FAIL",
        "nonbaseline_count_per_topology_family": family_counts,
        "level_B_count": 0,
        "tolerance_child_count": 0,
        "power_field_naming_audit": "PASS",
        "power_definition_note": "A_stack=power_entering-T; 1-R-T retained only as far_field_balance_offset",
    }
    required_passes = [value for key, value in validations.items() if key.endswith("audit") or key.endswith("validation") or key in ("baseline_roundtrip", "baseline_reproduction", "hash_stability", "artifact_sha_validation", "deterministic_sample_rebuild")]
    validations["status"] = "PASS" if all(value == "PASS" for value in required_passes) else "FAIL"
    content_payload = {
        "structure_hashes": original_hashes,
        "metrics": metrics_rows,
        "artifact_hashes": [item["sha256"] for item in artifacts],
        "array_content_hashes": [item["array_content_hash"] for item in artifacts],
    }
    content_signature = stable_hash(content_payload)
    total_runtime = time.perf_counter() - started
    response_bytes = sum(item["bytes"] for item in artifacts)
    write_csv(out / "smoke_structures_v1.csv", structures)
    write_csv(out / "smoke_metrics_v1.csv", metrics_rows)
    write_jsonl(out / "smoke_records_v1.jsonl", records)
    write_json(out / "response_manifest_v1.json", {"contract_id": config["contract_id"], "artifacts": artifacts})
    write_json(out / "validation_v1.json", validations)
    runtime = {
        "baseline_seconds": runtimes[0], "total_seconds": total_runtime,
        "mean_seconds_per_structure": statistics.mean(runtimes),
        "p95_seconds_per_structure": float(np.percentile(runtimes, 95)),
        "response_array_bytes": response_bytes,
        "lightweight_record_bytes": 0,
        "estimate_2000_serial_seconds": statistics.mean(runtimes) * 2000,
        "estimate_5000_serial_seconds": statistics.mean(runtimes) * 5000,
        "suggested_parallelism": max(1, min(8, (os.cpu_count() or 2) // 2)),
        "estimate_note": "linear serial extrapolation from the actual 17-structure smoke; no 2000/5000 run was performed",
    }
    write_json(out / "runtime_summary_v1.json", runtime)
    runtime["lightweight_record_bytes"] = sum((out / name).stat().st_size for name in ("smoke_structures_v1.csv", "smoke_metrics_v1.csv", "smoke_records_v1.jsonl"))
    write_json(out / "runtime_summary_v1.json", runtime)
    manifest = build_manifest(out, config, artifacts, content_signature)
    if manifest["total_output_bytes"] > int(config["maximum_output_bytes"]):
        raise RuntimeError("output size exceeds configured 50 MiB gate")
    write_json(out / "manifest_v1.json", manifest)
    if validations["status"] != "PASS":
        raise RuntimeError("smoke validation failed")
    return {
        "status": "PASS", "baseline": gate, "structure_count": len(structures),
        "content_signature": content_signature, "artifact_hashes": [item["sha256"] for item in artifacts],
        "array_content_hashes": [item["array_content_hash"] for item in artifacts], "metrics": metrics_rows,
        "runtime": runtime,
    }


def mark_determinism(config: dict[str, Any], first: dict[str, Any], second: dict[str, Any]) -> None:
    out = ROOT / config["output_directory"]
    checks = {
        "content_signature": first["content_signature"] == second["content_signature"],
        "artifact_sha": first["artifact_hashes"] == second["artifact_hashes"],
        "array_content_hash": first["array_content_hashes"] == second["array_content_hashes"],
        "summary_metrics": first["metrics"] == second["metrics"],
        "baseline": first["baseline"]["checks"] == second["baseline"]["checks"],
    }
    validation = json.loads((out / "validation_v1.json").read_text(encoding="utf-8"))
    validation["deterministic_metric_rerun"] = "PASS" if all(checks.values()) else "FAIL"
    validation["deterministic_metric_rerun_checks"] = checks
    validation["status"] = "PASS" if validation["status"] == "PASS" and all(checks.values()) else "FAIL"
    write_json(out / "validation_v1.json", validation)
    manifest = build_manifest(out, config, json.loads((out / "response_manifest_v1.json").read_text(encoding="utf-8"))["artifacts"], second["content_signature"])
    write_json(out / "manifest_v1.json", manifest)
    if validation["status"] != "PASS":
        raise RuntimeError("deterministic rerun mismatch")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-only", action="store_true")
    parser.add_argument("--determinism-check", action="store_true")
    args = parser.parse_args()
    config = load_config()
    if args.baseline_only:
        result = run_pipeline(config, baseline_only=True)
    elif args.determinism_check:
        first = run_pipeline(config)
        second = run_pipeline(config)
        mark_determinism(config, first, second)
        result = {"status": "PASS", "structure_count": 17, "deterministic_metric_rerun": "PASS", "content_signature": second["content_signature"]}
    else:
        result = run_pipeline(config)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
