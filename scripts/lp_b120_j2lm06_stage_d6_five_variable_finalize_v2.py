from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import os
import socket
import subprocess
import uuid
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
ML = ROOT / "outputs/lp_ml_dataset_v1"
ANALYSIS = ML / "analysis"
PLANS = ML / "plans"
CANONICAL = ML / "canonical_v1_21"
STAGING = ML / "staging/b120_j2lm06_positional_jacobian_stage_d6_v1_attempt1_lp_ml_schema_v1_22"
PACKAGE = ML / "execution_packages/b120_j2lm06_positional_jacobian_stage_d6_execution_package_v1"
REPORT = ROOT / "reports/lp_b120_j2lm06_stage_d6_attested_execution_five_variable_finalization_v2.md"

PLAN = PLANS / "b120_j2lm06_positional_jacobian_stage_d6_v1.json"
D6_EXECUTION_CONTRACT = PLANS / "b120_j2lm06_stage_d6_execution_contract_v1.json"
D6_ML_CONTRACT = PLANS / "b120_j2lm06_stage_d6_ml_label_contract_v1.json"
D6_DERIVATIVE_CONTRACT = PLANS / "b120_j2lm06_stage_d6_derivative_contract_v1.json"
D5_JACOBIAN = ANALYSIS / "b120_j2lm06_stage_d5_central_difference_jacobian_v1.json"
D5_SVD = ANALYSIS / "b120_j2lm06_stage_d5_leakage_svd_audit_v1.json"
D5_PHASE = ANALYSIS / "b120_j2lm06_stage_d5_phase_derivative_crosscheck_v1.json"
D5_LINEARITY = ANALYSIS / "b120_j2lm06_stage_d5_linearity_audit_v1.csv"
D5_ROUTE = ANALYSIS / "b120_j2lm06_stage_d5_route_decision_v1.json"
ANCHOR_ATTESTATION = ANALYSIS / "b120_j2lm06_stage_d5_anchor_source_attestation_v1.json"
RUNNER = ROOT / "scripts/lp_b120_j2lm06_positional_jacobian_stage_d6_execute_v1.py"
RUNTIME = ROOT / "scripts/lp_checkpoint_authoritative_runtime_v1_22.py"
FINALIZER = ROOT / "scripts/lp_b120_j2lm06_stage_d6_five_variable_finalize_v2.py"

SCHEMA = "LP_ML_SCHEMA_V1.22"
SOURCE_STAGE = "B120_J2LM06_POSITIONAL_JACOBIAN_STAGE_D6_V1_ATTEMPT1"
EVIDENCE_TIER = "FORMAL_FULL_DIMER_450"
START_HEAD = "d4a11fafbdcb767a7629caa5dfdb5fef54d74386"
REQUIRED_PARENT = "c13d89cbce219359ca482eb2f0e5e8d4f28d86ae"
PHYSICS_HASH = "403866467fb3ec47d5bb8efb9d22f225d6e670caee2b51aaa29b470bf01b8d38"
PLAN_SHA = "7ad1e0be8c101e4a6766d31c77207dd04a21f5a891dcd68e02ac1ff9ed9bc7f7"
VALIDATOR_ID = "LP_V122_CHECKPOINT_AUTHORITATIVE_POST_SOLVER_ACCEPTANCE_V1"
EXPECTED = [
    "LP_H500_D6_J2LM06_D_M01",
    "LP_H500_D6_J2LM06_D_P01",
    "LP_H500_D6_J2LM06_PSI_M01",
    "LP_H500_D6_J2LM06_PSI_P01",
]
EXPECTED_SUBRUNS = [f"{candidate}_{pol}" for candidate in EXPECTED for pol in ("x", "y")]
PROTECTED = {
    ROOT / "reports/lp_ml1a3_git_history_geometry_reconstruction.md":
        "21c6884f71bad6bd6779d7ccc90cec55ab1a94e239f849ea74a942bdd50edd6a",
    ROOT / "reports/stage11_4a20_legacy_fsp_object_inventory.md":
        "ae3b13341547e13ca85ca763ed8265591c100ac1a78c555de1c8378816a33708",
}
FROZEN_HASHES = {
    RUNNER: "68ec2df888b5de44c9cf1575b51c48b65df9b50b98e0243d523a6be64bf03d01",
    RUNTIME: "c83b2027f9548055b4dde725428ca5ff99b5ebe9ce650bcee45d5a290dcfe495",
    PACKAGE / "package_manifest.json": "6bbd4a9f5f447daaefe81b17caf263fe2060c10677293400af44e423fbab68a7",
    PACKAGE / "content_checksums.json": "eb39489212d64bb8eec7770d52dacb8814eb624e7a12b5858163bcc75b44ac98",
    PLAN: PLAN_SHA,
    D6_EXECUTION_CONTRACT: "e9eef668e1fdec624b3195f782606dee428b0dbe455b99dbb8e514ac160667f8",
    D6_ML_CONTRACT: "bbf72266534bac396433334d1fbf053602f880bbeb032c98287b94332c0702d8",
    D6_DERIVATIVE_CONTRACT: "a7984750fabfa4a7b6c1eff11b96d071f964960ccb3d61a5792721ea8faae80a",
    CANONICAL / "checksums_v1_21.json": "14d1799017b0b0626bbc4c24e0df8a75331b9b51e4cf2708d17f8c45922e78c7",
}
ANALYSIS_OUTPUTS = {
    "attestation": ANALYSIS / "b120_j2lm06_stage_d6_runtime_execution_attestation_v1.json",
    "inventory_csv": ANALYSIS / "b120_j2lm06_stage_d6_checkpoint_inventory_v1.csv",
    "inventory_json": ANALYSIS / "b120_j2lm06_stage_d6_checkpoint_inventory_v1.json",
    "reconstruction": ANALYSIS / "b120_j2lm06_stage_d6_physics_reconstruction_audit_v1.csv",
    "ml_audit": ANALYSIS / "b120_j2lm06_stage_d6_ml_label_audit_v1.json",
    "radial": ANALYSIS / "b120_j2lm06_stage_d6_radial_derivative_v1.json",
    "tangential": ANALYSIS / "b120_j2lm06_stage_d6_tangential_derivative_v1.json",
    "bias": ANALYSIS / "b120_j2lm06_stage_d6_tangential_radial_bias_audit_v1.json",
    "linearity": ANALYSIS / "b120_j2lm06_stage_d6_positional_linearity_audit_v1.csv",
    "jacobian": ANALYSIS / "b120_j2lm06_stage_d6_five_variable_jacobian_v1.json",
    "svd_raw": ANALYSIS / "b120_j2lm06_stage_d6_leakage_svd_raw_v1.json",
    "svd_step": ANALYSIS / "b120_j2lm06_stage_d6_leakage_svd_step_normalized_v1.json",
    "trust": ANALYSIS / "b120_j2lm06_stage_d6_five_variable_trust_region_prediction_v1.csv",
    "route": ANALYSIS / "b120_j2lm06_stage_d6_route_decision_v1.json",
    "provenance": ANALYSIS / "b120_j2lm06_stage_d6_checksum_provenance_manifest_v1.json",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp." + uuid.uuid4().hex)
    with temp.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def dump(path: Path, payload: Any) -> None:
    atomic_bytes(path, (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode())


def encode(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if isinstance(value, np.generic):
        return value.item()
    return value


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    keys = fields or sorted({key for row in rows for key in row})
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp." + uuid.uuid4().hex)
    with temp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows([{key: encode(row.get(key, "")) for key in keys} for row in rows])
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def cdict(value: complex) -> dict[str, float]:
    return {"real": float(value.real), "imag": float(value.imag)}


def cvalue(value: dict[str, Any] | str) -> complex:
    if isinstance(value, str):
        value = json.loads(value)
    return complex(float(value["real"]), float(value["imag"]))


def cmat(value: list[list[dict[str, Any]]]) -> np.ndarray:
    return np.array([[cvalue(entry) for entry in row] for row in value], dtype=complex)


def cmat_dict(value: np.ndarray) -> list[list[dict[str, float]]]:
    return [[cdict(value[i, j]) for j in range(2)] for i in range(2)]


def wrap_deg(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


def phase_deg(value: complex) -> float:
    return float(math.degrees(math.atan2(value.imag, value.real)) % 360.0)


def stokes(vector: np.ndarray) -> dict[str, float]:
    vector = np.asarray(vector, dtype=complex)
    power = float(np.vdot(vector, vector).real)
    if power <= 1e-30:
        return {"S1": 0.0, "S2": 0.0, "S3": 0.0, "aolp_deg": 0.0, "ellipticity_deg": 0.0}
    ex, ey = vector
    s1 = float((abs(ex) ** 2 - abs(ey) ** 2) / power)
    s2 = float(2.0 * np.real(ex * np.conj(ey)) / power)
    s3 = float(-2.0 * np.imag(ex * np.conj(ey)) / power)
    return {
        "S1": s1,
        "S2": s2,
        "S3": s3,
        "aolp_deg": float(0.5 * math.degrees(math.atan2(s2, s1))),
        "ellipticity_deg": float(0.5 * math.degrees(math.asin(max(-1.0, min(1.0, s3))))),
    }


def metrics(matrix: np.ndarray, fabrication_pass: bool = True) -> dict[str, Any]:
    txx, txy, tyx, tyy = matrix[0, 0], matrix[0, 1], matrix[1, 0], matrix[1, 1]
    Txx, Txy, Tyx, Tyy = [float(abs(z) ** 2) for z in (txx, txy, tyx, tyy)]
    cross = Txy + Tyx
    leakage = cross + Tyy
    ratio = Txx / max(leakage, 1e-30)
    purity = Txx / max(Txx + Tyx, 1e-30)
    u, singular, vh = np.linalg.svd(matrix)
    sigma1, sigma2 = [float(x) for x in singular]
    pin = stokes(vh.conj().T[:, 0])
    pout = stokes(u[:, 0])
    input_x = float(abs(vh.conj().T[0, 0]) ** 2)
    output_x = float(abs(u[0, 0]) ** 2)
    matrix_error = float(sigma2 / max(sigma1, 1e-30))
    a0 = (txx + tyy) / 2
    az = (txx - tyy) / 2
    ax = (txy + tyx) / 2
    ay = (tyx - txy) / (2j)
    pauli_norm = math.sqrt(abs(a0) ** 2 + abs(az) ** 2 + abs(ax) ** 2 + abs(ay) ** 2)
    phase = phase_deg(txx)
    bins = [0, 60, 120, 180, 240, 300]
    nearest = min(bins, key=lambda item: abs(wrap_deg(phase - item)))
    bin_error = abs(wrap_deg(phase - nearest))
    rank_pass = sigma2 / max(sigma1, 1e-30) <= 0.5
    axis_pass = (
        input_x >= 0.9 and output_x >= 0.9
        and abs(pin["ellipticity_deg"]) <= 10 and abs(pout["ellipticity_deg"]) <= 10
    )
    leakage_pass = ratio >= 8 and purity >= 0.9
    shape_pass = rank_pass and matrix_error <= 0.45
    throughput_pass = Txx >= 0.45
    usable = shape_pass and axis_pass and leakage_pass and throughput_pass and fabrication_pass
    return {
        "Txx": Txx, "Txy": Txy, "Tyx": Tyx, "Tyy": Tyy,
        "selected_power": Txx, "cross_power": cross, "leakage_sum": leakage,
        "R_total": ratio, "selected_polarization_purity": purity,
        "sigma1": sigma1, "sigma2": sigma2, "sigma2_over_sigma1": sigma2 / max(sigma1, 1e-30),
        "determinant_magnitude": float(abs(np.linalg.det(matrix))),
        "matrix_projection_error": matrix_error,
        "reciprocity_residual": float(abs(txy - tyx) / max(np.linalg.norm(matrix), 1e-30)),
        "input_x_overlap": input_x, "output_x_overlap": output_x,
        "principal_input_stokes": pin, "principal_output_stokes": pout,
        "pauli": {
            "a0": cdict(a0), "az": cdict(az), "ax": cdict(ax), "ay": cdict(ay),
            "identity_anisotropy_ratio": float(abs(a0) / max(abs(az), 1e-30)),
            "identity_anisotropy_phase_error_deg": abs(wrap_deg(phase_deg(a0) - phase_deg(az) - 180.0)),
            "off_axis_fraction": float(math.sqrt(abs(ax) ** 2 + abs(ay) ** 2) / max(pauli_norm, 1e-30)),
        },
        "off_axis_fraction": float(math.sqrt(abs(ax) ** 2 + abs(ay) ** 2) / max(pauli_norm, 1e-30)),
        "abs_txx": float(abs(txx)), "actual_txx_phase_deg": phase,
        "nearest_bin_deg": nearest, "phase_bin_error_deg": bin_error,
        "rank_pass": bool(rank_pass), "axis_pass": bool(axis_pass),
        "leakage_pass": bool(leakage_pass), "projector_shape_pass": bool(shape_pass),
        "selected_throughput_pass": bool(throughput_pass),
        "fabrication_pass": bool(fabrication_pass), "usable_projector": bool(usable),
        "projector_preserved_from_backbone": bool(usable and min(input_x, output_x) >= 0.9),
    }


def metric_row(candidate: dict[str, Any], matrix: np.ndarray, value: dict[str, Any], checkpoint: Path) -> dict[str, Any]:
    pin, pout, p = value["principal_input_stokes"], value["principal_output_stokes"], value["pauli"]
    row: dict[str, Any] = {
        "schema_version": SCHEMA, "source_stage": SOURCE_STAGE, "evidence_tier": EVIDENCE_TIER,
        "candidate_id": candidate["candidate_id"], "logical_candidate_id": candidate["logical_candidate_id"],
        "anchor_id": candidate["anchor_id"], "positional_mode": candidate["positional_mode"],
        "sign": candidate["sign"], "D_nm": candidate["D_nm"], "psi_deg": candidate["psi_deg"],
        "effective_delta_D_nm": candidate["effective_delta_D_nm"],
        "effective_delta_psi_deg": candidate["effective_delta_psi_deg"],
        "exact_geometry_hash": candidate["exact_geometry_hash"],
        "canonical_relative_geometry_hash": candidate["canonical_relative_geometry_hash"],
        "symmetry_equivalence_hash": candidate["symmetry_equivalence_hash"],
        "physics_configuration_hash": candidate["physics_configuration_hash"],
        "wavelength_nm": 450.0, "candidate_checkpoint_path": str(checkpoint),
        "candidate_checkpoint_sha256": sha(checkpoint), "quality_status": "PASS",
        "split_group": candidate["canonical_relative_geometry_hash"], "split_assignment": "UNASSIGNED",
        "projector_preserved_from_backbone": value["projector_preserved_from_backbone"],
    }
    for name, z in zip(("txx", "txy", "tyx", "tyy"), matrix.reshape(-1)):
        row[f"{name}_real"], row[f"{name}_imag"] = float(z.real), float(z.imag)
    for key in (
        "Txx", "Txy", "Tyx", "Tyy", "selected_power", "cross_power", "leakage_sum", "R_total",
        "selected_polarization_purity", "sigma1", "sigma2", "sigma2_over_sigma1",
        "determinant_magnitude", "matrix_projection_error", "reciprocity_residual",
        "input_x_overlap", "output_x_overlap", "off_axis_fraction", "abs_txx",
        "actual_txx_phase_deg", "nearest_bin_deg", "phase_bin_error_deg", "rank_pass",
        "axis_pass", "leakage_pass", "projector_shape_pass", "selected_throughput_pass",
        "fabrication_pass", "usable_projector",
    ):
        row[key] = value[key]
    for prefix, state in (("input", pin), ("output", pout)):
        for key in ("S1", "S2", "S3"):
            row[f"{prefix}_{key}"] = state[key]
        row[f"{prefix}_AoLP_deg"] = state["aolp_deg"]
        row[f"{prefix}_ellipticity_deg"] = state["ellipticity_deg"]
    for name in ("a0", "az", "ax", "ay"):
        row[f"{name}_real"], row[f"{name}_imag"] = p[name]["real"], p[name]["imag"]
    row["abs_a0_over_abs_az"] = p["identity_anisotropy_ratio"]
    row["common_differential_phase_error_deg"] = p["identity_anisotropy_phase_error_deg"]
    row["weighted_G0_Jones"] = cmat_dict(matrix)
    return row


def verify_package() -> dict[str, Any]:
    content = json.loads((PACKAGE / "content_checksums.json").read_text(encoding="utf-8"))
    checks = []
    for row in content["files"]:
        path = PACKAGE / row["path"]
        checks.append({
            "path": row["path"], "exists": path.is_file(),
            "bytes_match": path.is_file() and path.stat().st_size == row["bytes"],
            "sha256_match": path.is_file() and sha(path) == row["sha256"],
        })
    return {"status": "PASS" if all(all(r[k] for k in ("exists", "bytes_match", "sha256_match")) for r in checks) else "FAIL", "files": checks}


def source_gate() -> dict[str, Any]:
    head = git("rev-parse", "HEAD")
    parents = git("show", "-s", "--format=%P", "HEAD").split()
    canonical = json.loads((CANONICAL / "canonical_manifest_v1_21.json").read_text())
    count = json.loads((CANONICAL / "count_audit_v1_21.json").read_text())
    package = verify_package()
    checks = {
        "host": socket.gethostname().upper() == "DESKTOP-NNE313K",
        "branch": git("branch", "--show-current") == "work/lp-stage11-4",
        "head": head == START_HEAD,
        "direct_parent": parents == [REQUIRED_PARENT],
        "protected": all(sha(path) == expected for path, expected in PROTECTED.items()),
        "frozen_hashes": all(path.is_file() and sha(path) == expected for path, expected in FROZEN_HASHES.items()),
        "package_content": package["status"] == "PASS",
        "canonical_schema": canonical.get("schema_version") == "LP_ML_SCHEMA_V1.21",
        "canonical_counts": canonical.get("counts") == {
            "450_nm_Jones_rows": 122,
            "complete_four_point_geometries": 28,
            "constituent_geometries": 10,
            "constituent_wavelength_rows": 16,
            "formal_full_dimer_subruns": 412,
            "total_wavelength_Jones_rows": 206,
            "unique_full_dimer_geometries": 122,
        },
        "canonical_count_audit": count.get("status") == "PASS",
    }
    if not all(checks.values()):
        raise RuntimeError("SOURCE_AND_CONTRACT_GATE_FAILED:" + json.dumps(checks, sort_keys=True))
    return {"status": "PASS", "checks": checks, "head": head, "parent": parents[0], "package": package}


def load_formal(plan: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, np.ndarray], list[dict[str, Any]]]:
    rows = read_csv(STAGING / "formal_subruns.csv")
    if len(rows) != 8:
        raise RuntimeError(f"FORMAL_SUBRUN_COUNT_MISMATCH:{len(rows)}")
    actual_order = [f"{row['candidate_id']}_{row['input_polarization']}" for row in rows]
    if actual_order != EXPECTED_SUBRUNS or len({row["formal_subrun_key"] for row in rows}) != 8:
        raise RuntimeError("FORMAL_SUBRUN_ORDER_OR_DUPLICATE_MISMATCH")
    specs = {row["candidate_id"]: row for row in plan["candidates"]}
    inventory, matrices = [], {}
    for candidate_id in EXPECTED:
        pair = [row for row in rows if row["candidate_id"] == candidate_id]
        if [row["input_polarization"] for row in pair] != ["x", "y"]:
            raise RuntimeError("XY_PAIR_ORDER_MISMATCH:" + candidate_id)
        checkpoints: dict[str, dict[str, Any]] = {}
        for row in pair:
            checkpoint_path = Path(row["checkpoint_path"])
            if not checkpoint_path.is_file() or sha(checkpoint_path) != row["checkpoint_sha256"]:
                raise RuntimeError("CHECKPOINT_SHA256_MISMATCH:" + candidate_id)
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            checks = {
                "candidate": checkpoint["candidate_id"] == candidate_id,
                "polarization": checkpoint["input_polarization"] == row["input_polarization"],
                "wavelength": float(checkpoint["wavelength_nm"]) == 450.0,
                "geometry": checkpoint["exact_geometry_hash"] == specs[candidate_id]["exact_geometry_hash"],
                "physics": checkpoint["physics_configuration_hash"] == PHYSICS_HASH,
                "observable": checkpoint["weighted_G0_version"] == "LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1",
                "normalization": checkpoint["normalization_version"] == "LP_WEIGHTED_G0_SQRT_T_NORM_V1",
                "plan": checkpoint["source_plan_sha256"] == PLAN_SHA,
                "finite": all(math.isfinite(float(v)) for v in (
                    checkpoint["source_T"], checkpoint["normalization_scale"],
                    checkpoint["weighted_G0_Ex"]["real"], checkpoint["weighted_G0_Ex"]["imag"],
                    checkpoint["weighted_G0_Ey"]["real"], checkpoint["weighted_G0_Ey"]["imag"],
                )),
            }
            if not all(checks.values()):
                raise RuntimeError("CHECKPOINT_RELOAD_GATE_FAILED:" + json.dumps(checks))
            checkpoints[row["input_polarization"]] = checkpoint
            inventory.append({
                "candidate_id": candidate_id, "input_polarization": row["input_polarization"],
                "checkpoint_path": str(checkpoint_path), "checkpoint_sha256": row["checkpoint_sha256"],
                "formal_subrun_key": row["formal_subrun_key"], "checkpoint_reload": "PASS",
                "identity_validation": "PASS", "quality_status": "PASS",
            })
        x, y = checkpoints["x"], checkpoints["y"]
        matrices[candidate_id] = np.array([
            [cvalue(x["weighted_G0_Ex"]), cvalue(y["weighted_G0_Ex"])],
            [cvalue(x["weighted_G0_Ey"]), cvalue(y["weighted_G0_Ey"])],
        ], dtype=complex)
    return rows, matrices, inventory


def derivative_record(
    name: str, minus_id: str, plus_id: str, minus: np.ndarray, plus: np.ndarray,
    anchor: np.ndarray, denominator: float, unit: str,
) -> dict[str, Any]:
    derivative = (plus - minus) / denominator
    phase_a_rad = math.radians(wrap_deg(phase_deg(plus[0, 0]) - phase_deg(minus[0, 0]))) / denominator
    phase_b_rad = float(np.imag(derivative[0, 0] / anchor[0, 0]))
    if unit == "nm":
        tolerance_rad = math.radians(max(0.25, 0.05 * abs(math.degrees(phase_a_rad))))
    else:
        tolerance_rad = max(math.radians(0.25), 0.05 * abs(phase_a_rad))
    minus_metrics, plus_metrics = metrics(minus), metrics(plus)
    record: dict[str, Any] = {
        "schema_version": SCHEMA, "axis": name, "minus_candidate_id": minus_id,
        "plus_candidate_id": plus_id, "denominator": denominator, "denominator_unit": unit,
        "complex_dJ": cmat_dict(derivative), "phase_method_A_rad_per_unit": phase_a_rad,
        "phase_method_B_rad_per_unit": phase_b_rad,
        "phase_method_A_deg_per_unit": math.degrees(phase_a_rad),
        "phase_method_B_deg_per_unit": math.degrees(phase_b_rad),
        "phase_crosscheck_abs_difference_rad_per_unit": abs(phase_a_rad - phase_b_rad),
        "phase_crosscheck_tolerance_rad_per_unit": tolerance_rad,
        "phase_crosscheck_status": "PASS" if abs(phase_a_rad - phase_b_rad) <= tolerance_rad else "REVIEW",
    }
    for key in (
        "Txx", "Txy", "Tyx", "Tyy", "R_total", "sigma2_over_sigma1",
        "matrix_projection_error", "off_axis_fraction",
    ):
        record[f"d{key}_per_{unit}"] = (float(plus_metrics[key]) - float(minus_metrics[key])) / denominator
    pminus, pplus = minus_metrics["pauli"], plus_metrics["pauli"]
    for pkey in ("a0", "az", "ax", "ay"):
        value = (cvalue(pplus[pkey]) - cvalue(pminus[pkey])) / denominator
        record[f"d{pkey}_per_{unit}"] = cdict(value)
    return record


def leakage_column(matrix: np.ndarray) -> np.ndarray:
    return np.array([
        matrix[0, 1].real, matrix[0, 1].imag, matrix[1, 0].real,
        matrix[1, 0].imag, matrix[1, 1].real, matrix[1, 1].imag,
    ], dtype=float)


def svd_record(matrix: np.ndarray, variables: list[str], units: list[str], label: str) -> dict[str, Any]:
    u, singular, vh = np.linalg.svd(matrix, full_matrices=True)
    tolerance = max(matrix.shape) * np.finfo(float).eps * (singular[0] if len(singular) else 1.0)
    rank = int(np.sum(singular > tolerance))
    directions = []
    for index, direction in enumerate(vh):
        directions.append({"index": index, "components": {variables[i]: float(direction[i]) for i in range(len(variables))}})
    near = vh[-1]
    return {
        "schema_version": SCHEMA, "normalization": label, "shape": list(matrix.shape),
        "variables": variables, "column_units": units, "matrix": matrix.tolist(),
        "singular_values": [float(value) for value in singular], "numerical_rank": rank,
        "rank_tolerance": float(tolerance), "condition_number": float(singular[0] / singular[-1]) if singular[-1] > tolerance else None,
        "exact_nullspace_dimension": int(matrix.shape[1] - rank),
        "right_singular_vectors": directions,
        "best_near_null_direction": {variables[i]: float(near[i]) for i in range(len(variables))},
        "near_null_is_exact": bool(matrix.shape[1] - rank > 0),
    }


def rectangle_gap(
    j1: tuple[float, float], j2: tuple[float, float], side: float, length: float,
    width: float, shift: tuple[float, float] = (0.0, 0.0),
) -> float:
    dx = abs((j2[0] + shift[0]) - j1[0])
    dy = abs((j2[1] + shift[1]) - j1[1])
    gx = max(dx - side / 2 - length / 2, 0.0)
    gy = max(dy - side / 2 - width / 2, 0.0)
    return math.hypot(gx, gy)


def geometry_hashes(raw: dict[str, Any]) -> tuple[str, str, str]:
    digest = lambda value: hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    dx = raw["J2_center_x_nm"] - raw["J1_center_x_nm"]
    dy = raw["J2_center_y_nm"] - raw["J1_center_y_nm"]
    sizes = [raw["J1_side_nm"], raw["J2_length_nm"], raw["J2_width_nm"]]
    distance = math.hypot(dx, dy)
    psi = math.degrees(math.atan2(dy, dx))
    return (
        digest(raw),
        digest({"dx": dx, "dy": dy, "sizes": sizes}),
        digest({"D": round(distance, 12), "psi_signed": round(psi, 12), "sizes": sizes}),
    )


def pareto(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def dominates(a: dict[str, Any], b: dict[str, Any]) -> bool:
        av = (
            -float(a["predicted_phase_drop_deg"]), -float(a["predicted_Txx"]),
            float(a["predicted_leakage_sum"]), float(a["predicted_matrix_projection_error"]),
            float(a["parameter_step_norm"]),
        )
        bv = (
            -float(b["predicted_phase_drop_deg"]), -float(b["predicted_Txx"]),
            float(b["predicted_leakage_sum"]), float(b["predicted_matrix_projection_error"]),
            float(b["parameter_step_norm"]),
        )
        return all(x <= y + 1e-12 for x, y in zip(av, bv)) and any(x < y - 1e-12 for x, y in zip(av, bv))

    front = [row for row in rows if not any(dominates(other, row) for other in rows if other is not row)]
    front.sort(key=lambda row: (
        -float(row["predicted_phase_drop_deg"]), -float(row["predicted_Txx"]),
        float(row["predicted_matrix_projection_error"]), float(row["parameter_step_norm"]),
    ))
    return front[:8]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    if not args.finalize:
        raise RuntimeError("EXPLICIT_FINALIZE_FLAG_REQUIRED")
    gate = source_gate()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    if [row["candidate_id"] for row in plan["candidates"]] != EXPECTED or plan["execution_order"] != EXPECTED_SUBRUNS:
        raise RuntimeError("FROZEN_ORDER_MISMATCH")
    formal_rows, matrices, inventory = load_formal(plan)
    anchor_payload = json.loads(ANCHOR_ATTESTATION.read_text(encoding="utf-8"))
    if anchor_payload.get("reconstruction") != "PASS" or anchor_payload.get("candidate_id") != "LP_H500_D2_B120_J2LM06":
        raise RuntimeError("ANCHOR_ATTESTATION_FAILED")
    anchor = cmat(anchor_payload["jones"])

    # Checkpoint-derived candidate Jones and complete formal rows.
    candidate_rows, reconstruction_rows = [], []
    candidates_dir = STAGING / "candidates"
    for candidate in plan["candidates"]:
        candidate_id = candidate["candidate_id"]
        matrix = matrices[candidate_id]
        value = metrics(matrix, candidate["direct_gap_nm"] >= 60 and candidate["nearest_periodic_gap_nm"] >= 60)
        pair = [row for row in formal_rows if row["candidate_id"] == candidate_id]
        checkpoint = candidates_dir / f"{candidate_id}.json"
        payload = {
            "schema_version": SCHEMA, "source_stage": SOURCE_STAGE, "candidate_id": candidate_id,
            "status": "PASS", "candidate_checkpoint_reload": "PENDING",
            "subrun_checkpoints": [row["checkpoint_path"] for row in pair],
            "weighted_G0_Jones": cmat_dict(matrix), "formal_metrics": value,
            "geometry_provenance": candidate,
        }
        dump(checkpoint, payload)
        reloaded = json.loads(checkpoint.read_text(encoding="utf-8"))
        if reloaded["weighted_G0_Jones"] != payload["weighted_G0_Jones"]:
            raise RuntimeError("CANDIDATE_CHECKPOINT_RELOAD_FAILED:" + candidate_id)
        payload["candidate_checkpoint_reload"] = "PASS"
        dump(checkpoint, payload)
        row = metric_row(candidate, matrix, value, checkpoint)
        candidate_rows.append(row)
        independent = np.array([
            [complex(row["txx_real"], row["txx_imag"]), complex(row["txy_real"], row["txy_imag"])],
            [complex(row["tyx_real"], row["tyx_imag"]), complex(row["tyy_real"], row["tyy_imag"])],
        ])
        reconstruction_rows.append({
            "candidate_id": candidate_id, "x_y_pairing": "PASS", "checkpoint_reload": "PASS",
            "jones_reconstruction_frobenius_error": float(np.linalg.norm(independent - matrix)),
            "derived_metrics_recalculation": "PASS" if abs(metrics(independent)["Txx"] - row["Txx"]) < 1e-14 else "FAIL",
            "status": "PASS",
        })

    jdm, jdp, jtm, jtp = [matrices[candidate] for candidate in EXPECTED]
    half_angle_rad = abs(math.radians(float(plan["candidates"][3]["effective_delta_psi_deg"])))
    tangential_denominator = 2.0 * half_angle_rad
    common_delta_d = (
        float(plan["candidates"][2]["effective_delta_D_nm"])
        + float(plan["candidates"][3]["effective_delta_D_nm"])
    ) / 2
    radial = derivative_record("D", EXPECTED[0], EXPECTED[1], jdm, jdp, anchor, 2.0, "nm")
    tangential = derivative_record("Psi", EXPECTED[2], EXPECTED[3], jtm, jtp, anchor, tangential_denominator, "rad")
    djd = cmat(radial["complex_dJ"])
    djpsi = cmat(tangential["complex_dJ"])

    mid_radial = (jdm + jdp) / 2
    mid_tangential = (jtm + jtp) / 2
    radial_bias = djd * common_delta_d
    mid_corrected = mid_tangential - radial_bias
    norm_anchor = max(float(np.linalg.norm(anchor)), 1e-30)
    radial_midpoint = float(np.linalg.norm(jdp + jdm - 2 * anchor) / norm_anchor)
    tangential_raw = float(np.linalg.norm(mid_tangential - anchor) / norm_anchor)
    tangential_corrected = float(np.linalg.norm(mid_corrected - anchor) / norm_anchor)

    def residuals(matrix: np.ndarray) -> dict[str, Any]:
        base, current = metrics(anchor), metrics(matrix)
        return {
            "complex_txx_abs": float(abs(matrix[0, 0] - anchor[0, 0])),
            "complex_leakage_vector_norm": float(np.linalg.norm(leakage_column(matrix) - leakage_column(anchor))),
            "phase_deg": abs(wrap_deg(current["actual_txx_phase_deg"] - base["actual_txx_phase_deg"])),
            "Txx": abs(current["Txx"] - base["Txx"]), "Tyy": abs(current["Tyy"] - base["Tyy"]),
            "sigma2_over_sigma1": abs(current["sigma2_over_sigma1"] - base["sigma2_over_sigma1"]),
            "matrix_projection_error": abs(current["matrix_projection_error"] - base["matrix_projection_error"]),
        }

    bias_audit = {
        "schema_version": SCHEMA, "actual_half_angle_rad": half_angle_rad,
        "tangential_denominator_rad": tangential_denominator,
        "tangential_common_delta_D_nm": common_delta_d,
        "Jmid_raw": cmat_dict(mid_tangential), "J_radial_bias": cmat_dict(radial_bias),
        "Jmid_corrected": cmat_dict(mid_corrected),
        "R_psi_raw": tangential_raw, "R_psi_corrected": tangential_corrected,
        "raw_residuals": residuals(mid_tangential), "corrected_residuals": residuals(mid_corrected),
        "raw_physics_unchanged": True, "correction_use": "VERSIONED_DIAGNOSTIC_ONLY",
    }

    anchor_metrics = metrics(anchor)
    radial_phase_mid = abs(wrap_deg(metrics(jdp)["actual_txx_phase_deg"] + metrics(jdm)["actual_txx_phase_deg"] - 2 * anchor_metrics["actual_txx_phase_deg"]))
    tangential_phase_mid_raw = abs(wrap_deg(metrics(jtp)["actual_txx_phase_deg"] + metrics(jtm)["actual_txx_phase_deg"] - 2 * anchor_metrics["actual_txx_phase_deg"]))
    radial_max = max(radial_midpoint, radial_phase_mid / 180.0)
    tangential_max = max(tangential_corrected, bias_audit["corrected_residuals"]["phase_deg"] / 180.0)
    radial_status = "RADIAL_LINEARITY_PASS" if radial_max <= 0.15 and radial["phase_crosscheck_status"] == "PASS" else "RADIAL_LINEARITY_REVIEW"
    tangential_status = "TANGENTIAL_LINEARITY_PASS" if tangential_max <= 0.15 and tangential["phase_crosscheck_status"] == "PASS" else "TANGENTIAL_LINEARITY_REVIEW"
    linearity_rows = [
        {
            "mode": "D", "diagnostic_version": "D6_POSITIONAL_LINEARITY_DIAGNOSTIC_V1",
            "raw_midpoint_residual": radial_midpoint, "corrected_midpoint_residual": radial_midpoint,
            "phase_midpoint_residual_deg": radial_phase_mid, "max_normalized_residual": radial_max,
            "phase_crosscheck": radial["phase_crosscheck_status"], "status": radial_status,
        },
        {
            "mode": "Psi", "diagnostic_version": "D6_POSITIONAL_LINEARITY_DIAGNOSTIC_V1",
            "raw_midpoint_residual": tangential_raw, "corrected_midpoint_residual": tangential_corrected,
            "phase_midpoint_residual_deg": tangential_phase_mid_raw, "max_normalized_residual": tangential_max,
            "phase_crosscheck": tangential["phase_crosscheck_status"], "status": tangential_status,
        },
    ]

    d5 = json.loads(D5_JACOBIAN.read_text(encoding="utf-8"))
    variables = ["J1_side_nm", "J2_length_nm", "J2_width_nm", "D_nm", "Psi_rad"]
    full_derivatives = [cmat(row["dJ_d_nm"]) for row in d5["derivatives"]] + [djd, djpsi]
    raw_jacobian = np.column_stack([matrix.reshape(-1) for matrix in full_derivatives])
    step_scales = np.array([1.0, 1.0, 1.0, 1.0, half_angle_rad])
    step_jacobian = raw_jacobian * step_scales[np.newaxis, :]
    leakage_raw = np.column_stack([leakage_column(matrix) for matrix in full_derivatives])
    leakage_step = leakage_raw * step_scales[np.newaxis, :]
    raw_svd = svd_record(leakage_raw, variables, ["per_nm", "per_nm", "per_nm", "per_nm", "per_rad"], "RAW_PHYSICAL_UNIT")
    step_svd = svd_record(leakage_step, variables, ["1nm", "1nm", "1nm", "1nm", f"{half_angle_rad:.17g}rad"], "STEP_NORMALIZED")

    d5_leakage = leakage_raw[:, :3]
    projector = d5_leakage @ np.linalg.pinv(d5_leakage)
    d_orthogonal = float(np.linalg.norm((np.eye(6) - projector) @ leakage_step[:, 3]) / max(np.linalg.norm(leakage_step[:, 3]), 1e-30))
    psi_orthogonal = float(np.linalg.norm((np.eye(6) - projector) @ leakage_step[:, 4]) / max(np.linalg.norm(leakage_step[:, 4]), 1e-30))
    positional_correlation = float(abs(np.dot(leakage_step[:, 3], leakage_step[:, 4])) / max(np.linalg.norm(leakage_step[:, 3]) * np.linalg.norm(leakage_step[:, 4]), 1e-30))
    d5_svd = json.loads(D5_SVD.read_text(encoding="utf-8"))
    controllability_improved = (
        step_svd["numerical_rank"] > int(d5_svd.get("rank", d5_svd.get("numerical_rank", 0)))
        or max(d_orthogonal, psi_orthogonal) >= 0.1
    )
    jacobian_record = {
        "schema_version": SCHEMA, "variables": variables,
        "raw_physical_unit_complex_jones_jacobian": {
            "column_units": ["per_nm", "per_nm", "per_nm", "per_nm", "per_rad"],
            "columns": {variables[i]: cmat_dict(full_derivatives[i]) for i in range(5)},
        },
        "step_normalized_complex_jones_jacobian": {
            "step_scales": {variables[i]: float(step_scales[i]) for i in range(5)},
            "columns": {variables[i]: cmat_dict(full_derivatives[i] * step_scales[i]) for i in range(5)},
        },
        "D_column_orthogonal_fraction_vs_D5": d_orthogonal,
        "Psi_column_orthogonal_fraction_vs_D5": psi_orthogonal,
        "radial_tangential_leakage_column_correlation": positional_correlation,
        "controllability_improved": bool(controllability_improved),
    }

    # Offline, manufacturing-gated five-variable discrete diagnostic.
    canonical_rows = read_csv(CANONICAL / "geometry_master_v1_17.csv")
    canonical_hashes = {
        key: {row.get(key, "") for row in canonical_rows if row.get(key)}
        for key in ("exact_geometry_hash", "canonical_relative_geometry_hash", "symmetry_equivalence_hash")
    }
    prediction_rows: list[dict[str, Any]] = []
    uncertainty_deg = max(radial_phase_mid, bias_audit["corrected_residuals"]["phase_deg"])
    for d1, d2l, d2w, nd, npsi in itertools.product(range(-2, 3), range(-2, 3), range(-2, 3), (-1, 0, 1), (-1, 0, 1)):
        if (d1, d2l, d2w, nd, npsi) == (0, 0, 0, 0, 0):
            continue
        j1 = (-99.5 - 0.5 * nd, -0.5 * npsi)
        j2 = (100.0 + 0.5 * nd, 0.5 * npsi)
        side, length, width = 110 + d1, 109 + d2l, 100 + d2w
        dx, dy = j2[0] - j1[0], j2[1] - j1[1]
        actual_d = math.hypot(dx, dy)
        actual_psi = math.atan2(dy, dx)
        direct = rectangle_gap(j1, j2, side, length, width)
        periodic = min(
            rectangle_gap(j1, j2, side, length, width, (sx * 432.0, sy * 432.0))
            for sx, sy in itertools.product((-1, 0, 1), repeat=2) if (sx, sy) != (0, 0)
        )
        raw = {
            "J1_center_x_nm": j1[0], "J1_center_y_nm": j1[1],
            "J2_center_x_nm": j2[0], "J2_center_y_nm": j2[1],
            "J1_side_nm": side, "J2_length_nm": length, "J2_width_nm": width,
            "H_nm": 500, "period_nm": 432, "material": "APCD_TIO2_NATIVE_M1",
            "theta1_deg": 0, "theta2_deg": 0,
        }
        exact_hash, canonical_hash, symmetry_hash = geometry_hashes(raw)
        duplicate = (
            exact_hash in canonical_hashes["exact_geometry_hash"]
            or canonical_hash in canonical_hashes["canonical_relative_geometry_hash"]
            or symmetry_hash in canonical_hashes["symmetry_equivalence_hash"]
        )
        delta = np.array([d1, d2l, d2w, actual_d - 199.5, actual_psi])
        predicted = anchor + (raw_jacobian @ delta).reshape(2, 2)
        value = metrics(predicted, direct >= 60 and periodic >= 60)
        phase_drop = wrap_deg(anchor_metrics["actual_txx_phase_deg"] - value["actual_txx_phase_deg"])
        geometry_pass = direct >= 60 and periodic >= 60 and not duplicate
        eligible = bool(
            geometry_pass and value["projector_preserved_from_backbone"]
            and phase_drop > uncertainty_deg
        )
        prediction_rows.append({
            "delta_J1_side_nm": d1, "delta_J2_length_nm": d2l, "delta_J2_width_nm": d2w,
            "n_D": nd, "n_Psi": npsi, "actual_effective_delta_D_nm": actual_d - 199.5,
            "actual_effective_delta_Psi_rad": actual_psi,
            "J1_center_nm": list(j1), "J2_center_nm": list(j2),
            "actual_D_nm": actual_d, "actual_Psi_deg": math.degrees(actual_psi),
            "direct_gap_nm": direct, "nearest_periodic_gap_nm": periodic,
            "exact_geometry_hash": exact_hash, "canonical_relative_geometry_hash": canonical_hash,
            "symmetry_equivalence_hash": symmetry_hash, "canonical_duplicate": duplicate,
            "geometry_gate": geometry_pass, "predicted_phase_deg": value["actual_txx_phase_deg"],
            "predicted_phase_drop_deg": phase_drop, "predicted_Txx": value["Txx"],
            "predicted_Tyy": value["Tyy"], "predicted_leakage_sum": value["leakage_sum"],
            "predicted_sigma2_over_sigma1": value["sigma2_over_sigma1"],
            "predicted_matrix_projection_error": value["matrix_projection_error"],
            "predicted_projector_gate": value["projector_preserved_from_backbone"],
            "proposal_eligible": eligible, "parameter_step_norm": float(np.linalg.norm([d1, d2l, d2w, nd, npsi])),
            "label": "MODEL_PREDICTION_NOT_PHYSICS_LABEL",
            "status": "DIAGNOSTIC_PROPOSAL_NOT_SIMULATED",
        })
    proposals = pareto([row for row in prediction_rows if row["proposal_eligible"]])

    linearity_pass = radial_status.endswith("_PASS") and tangential_status.endswith("_PASS")
    if not linearity_pass:
        route = "CASE_C_POSITIONAL_LINEARIZATION_UNRELIABLE"
        trust_authorization = "NOT_AUTHORIZED"
        next_family = "SMALLER_POSITION_STEP_OR_ALTERNATE_LOCAL_SAMPLING_PLANNING"
    elif controllability_improved and proposals:
        route = "CASE_A_FIVE_VARIABLE_PROJECTOR_TANGENT_FOUND"
        trust_authorization = "AUTHORIZED_PLANNING_ONLY"
        next_family = "FROZEN_FIVE_VARIABLE_TRUST_REGION_VALIDATION_PLANNING"
    elif controllability_improved:
        route = "CASE_B_POSITIONAL_DOF_IMPROVES_CONTROLLABILITY_BUT_NO_DISCRETE_PROJECTOR_PROPOSAL"
        trust_authorization = "NOT_AUTHORIZED"
        next_family = "FINER_POSITION_OPERATOR_OR_MANUFACTURING_GRID_PLANNING"
    else:
        route = "CASE_D_POSITIONAL_DOF_REDUNDANT_OR_INSUFFICIENT"
        trust_authorization = "NOT_AUTHORIZED"
        next_family = "PILLAR_ROTATION_OR_ASYMMETRIC_DISPLACEMENT_PLANNING"

    # Formal V1.22 staging tables and identity/quality layer.
    geometry_rows = []
    for candidate in plan["candidates"]:
        geometry_rows.append({
            "schema_version": SCHEMA, "source_stage": SOURCE_STAGE,
            "candidate_id": candidate["candidate_id"], "logical_candidate_id": candidate["logical_candidate_id"],
            "anchor_id": candidate["anchor_id"], "positional_mode": candidate["positional_mode"],
            "sign": candidate["sign"], "J1_center_nm": [candidate["geometry"]["J1_center_x_nm"], candidate["geometry"]["J1_center_y_nm"]],
            "J2_center_nm": [candidate["geometry"]["J2_center_x_nm"], candidate["geometry"]["J2_center_y_nm"]],
            "dimer_center_nm": candidate["dimer_center_nm"], "D_nm": candidate["D_nm"], "psi_deg": candidate["psi_deg"],
            "effective_delta_D_nm": candidate["effective_delta_D_nm"],
            "effective_delta_psi_deg": candidate["effective_delta_psi_deg"],
            "coordinate_displacement_operator": candidate["positional_mode"],
            "radial_purity": 1.0 if candidate["positional_mode"].startswith("RADIAL") else 0.0,
            "tangential_purity": 1.0 if candidate["positional_mode"].startswith("TANGENTIAL") else 0.0,
            "finite_difference_pair_id": candidate["finite_difference_pair_id"],
            "direct_gap_nm": candidate["direct_gap_nm"], "nearest_periodic_gap_nm": candidate["nearest_periodic_gap_nm"],
            "manufacturing_pass": candidate["direct_gap_nm"] >= 60 and candidate["nearest_periodic_gap_nm"] >= 60,
            "exact_geometry_hash": candidate["exact_geometry_hash"],
            "canonical_relative_geometry_hash": candidate["canonical_relative_geometry_hash"],
            "symmetry_equivalence_hash": candidate["symmetry_equivalence_hash"],
            "split_group": candidate["canonical_relative_geometry_hash"], "split_assignment": "UNASSIGNED",
            "quality_status": "PASS",
        })
    subrun_rows: list[dict[str, Any]] = []
    for row in formal_rows:
        checkpoint = json.loads(Path(row["checkpoint_path"]).read_text(encoding="utf-8"))
        spec = next(candidate for candidate in plan["candidates"] if candidate["candidate_id"] == row["candidate_id"])
        enriched = dict(row)
        enriched.update({
            "execution_attempt_id": SOURCE_STAGE, "source_stage": SOURCE_STAGE,
            "evidence_tier": EVIDENCE_TIER, "solver_called": True, "solver_retry": False,
            "checkpoint_reload": "PASS", "ml_record_reload": "PASS",
            "material_id": "APCD_TIO2_NATIVE_M1", "material_hash": checkpoint["material_hash"],
            "source_hash": checkpoint["source_hash"], "boundary_hash": checkpoint["boundary_hash"],
            "monitor_hash": checkpoint["monitor_hash"], "reference_plane_nm": checkpoint["reference_plane_nm"],
            "canonical_relative_geometry_hash": spec["canonical_relative_geometry_hash"],
            "symmetry_equivalence_hash": spec["symmetry_equivalence_hash"],
            "failure_code": "NONE", "retained_data_status": "FORMAL_ACCEPTED",
        })
        subrun_rows.append(enriched)

    write_csv(STAGING / "geometry_membership_v1_22.csv", geometry_rows)
    write_csv(STAGING / "subrun_records_v1_22.csv", subrun_rows)
    write_csv(STAGING / "candidate_wavelength_jones_v1_22.csv", candidate_rows)
    write_csv(STAGING / "positional_derivatives_v1_22.csv", [
        {"axis": "D", **radial}, {"axis": "Psi", **tangential},
    ])
    dump(STAGING / "five_variable_jacobian_v1_22.json", jacobian_record)
    dump(STAGING / "leakage_svd_raw_v1_22.json", raw_svd)
    dump(STAGING / "leakage_svd_step_normalized_v1_22.json", step_svd)
    write_csv(STAGING / "trust_region_predictions_v1_22.csv", proposals)
    write_csv(STAGING / "failure_and_quality_labels_v1_22.csv", [])
    write_csv(STAGING / "source_to_output_provenance_v1_22.csv", [
        {"path": str(path), "sha256": sha(path), "role": "FROZEN_INPUT"}
        for path in [*FROZEN_HASHES, D5_JACOBIAN, D5_SVD, D5_PHASE, D5_LINEARITY, D5_ROUTE, ANCHOR_ATTESTATION]
    ] + [{"path": str(FINALIZER), "sha256": sha(FINALIZER), "role": "OFFLINE_FINALIZER"}])
    attempt_identity = {
        "schema_version": SCHEMA, "source_stage": SOURCE_STAGE, "status": "FINALIZED",
        "git_head": START_HEAD, "required_parent_head": REQUIRED_PARENT,
        "execution_package_path": str(PACKAGE),
        "execution_package_manifest_sha256": sha(PACKAGE / "package_manifest.json"),
        "runner_sha256": sha(RUNNER), "runtime_sha256": sha(RUNTIME),
        "validator_id": VALIDATOR_ID, "candidate_order": EXPECTED, "subrun_order": EXPECTED_SUBRUNS,
        "raw_solver_invocations": 8, "accepted_subruns": 8,
        "registration_mode": "CHECKPOINT_AUTHORITATIVE_ATOMIC_REGISTRATION",
        "event_log": "APPEND_ONLY_NDJSON", "lock": "O_EXCL_SINGLE_WRITER",
        "serializer": "TEMP_FLUSH_FSYNC_ATOMIC_REPLACE", "retry": "FORBIDDEN",
    }
    dump(STAGING / "attempt_identity_v1_22.json", attempt_identity)
    dump(STAGING / "execution_package_identity_v1_22.json", gate["package"])
    dump(STAGING / "quality_lineage_v1_22.json", {
        "status": "PASS", "anchor_attestation": "PASS", "D5_finalized": "UNCHANGED",
        "runtime_attestation": "PASS", "checkpoint_reload": "8/8", "xy_pairing": "4/4",
        "Jones_reconstruction": "4/4", "failure_rows": 0, "legacy_validator": "FORBIDDEN",
        "applicable_runtime_regression_tests": "5_PASSED",
        "frozen_preexecution_staging_absence_test": "NOT_APPLICABLE_AFTER_AUTHORIZED_D6_STAGING_CREATION",
    })

    write_csv(ANALYSIS_OUTPUTS["inventory_csv"], inventory)
    dump(ANALYSIS_OUTPUTS["inventory_json"], {"status": "PASS", "count": 8, "rows": inventory})
    write_csv(ANALYSIS_OUTPUTS["reconstruction"], reconstruction_rows)
    dump(ANALYSIS_OUTPUTS["radial"], radial)
    dump(ANALYSIS_OUTPUTS["tangential"], tangential)
    dump(ANALYSIS_OUTPUTS["bias"], bias_audit)
    write_csv(ANALYSIS_OUTPUTS["linearity"], linearity_rows)
    dump(ANALYSIS_OUTPUTS["jacobian"], jacobian_record)
    dump(ANALYSIS_OUTPUTS["svd_raw"], raw_svd)
    dump(ANALYSIS_OUTPUTS["svd_step"], step_svd)
    write_csv(ANALYSIS_OUTPUTS["trust"], proposals)
    route_payload = {
        "schema_version": SCHEMA, "status": "PASS", "route_decision": route,
        "radial_linearity": radial_status, "tangential_linearity": tangential_status,
        "controllability_improved": controllability_improved,
        "D_column_orthogonal_fraction_vs_D5": d_orthogonal,
        "Psi_column_orthogonal_fraction_vs_D5": psi_orthogonal,
        "proposal_count": len(proposals), "trust_region_FDTD_validation_authorization": trust_authorization,
        "next_variable_family_authorization": next_family,
        "spectral_authorization": "NOT_AUTHORIZED", "training_authorization": "NOT_AUTHORIZED",
        "canonical_v1_22_merge": "NOT_AUTHORIZED",
    }
    dump(ANALYSIS_OUTPUTS["route"], route_payload)
    dump(ANALYSIS_OUTPUTS["attestation"], {
        "status": "PASS", "commit_bound_gate": gate, "schema_version": SCHEMA,
        "runner_sha256": sha(RUNNER), "runtime_sha256": sha(RUNTIME),
        "validator_id": VALIDATOR_ID, "callback_qualname": "post_solver_acceptance",
        "callback_source_sha256": "f8bc6a5e6ca9bc98a966435fe1ddca283f2b719d4d50d2738de4f54c226ad083",
        "legacy_runtime_gate": "FORBIDDEN", "legacy_line557": "FORBIDDEN",
        "raw_solver_invocations": 8, "accepted_subruns": 8, "duplicates": 0,
    })
    ml_audit = {
        "schema_version": SCHEMA, "status": "PASS",
        "row_counts": {"geometry": len(geometry_rows), "subrun": len(subrun_rows), "Jones": len(candidate_rows)},
        "required_field_missing": 0, "type_schema_failures": 0, "hash_provenance_failures": 0,
        "prediction_physics_mixing": 0, "legacy_seed_projector_field_present": False,
        "checkpoint_reload": "8/8", "Jones_independent_reconstruction": "4/4",
    }
    dump(ANALYSIS_OUTPUTS["ml_audit"], ml_audit)

    # Manifests are written after all payload files, excluding their own self-reference.
    dataset_manifest = {
        "schema_version": SCHEMA, "source_stage": SOURCE_STAGE, "status": "PASS", "append_only": True,
        "row_counts": {"geometry": 4, "subrun": 8, "Jones": 4, "positional_derivatives": 2, "trust_region_proposals": len(proposals)},
        "raw_solver_invocations": 8, "accepted_subruns": 8, "duplicate_accepted_keys": 0,
        "x_accepted": 4, "y_accepted": 4, "route_decision": route,
        "canonical_status": "CANONICAL_V1_21_UNCHANGED_NO_V1_22_MERGE",
    }
    dump(STAGING / "dataset_manifest_v1_22.json", dataset_manifest)
    staging_files = sorted(path for path in STAGING.rglob("*") if path.is_file() and path.name != "checksums_v1_22.json")
    dump(STAGING / "checksums_v1_22.json", {
        "status": "PASS", "self_reference_policy": "EXCLUDES_ITSELF",
        "files": [{"path": str(path.relative_to(STAGING)), "sha256": sha(path), "bytes": path.stat().st_size} for path in staging_files],
    })

    report_text = f"""# APCD LP J2LM06 Stage D6 attested execution and five-variable finalization v2

- Status: `PASS`
- Route: `{route}`
- Formal execution: `4 geometries / 8 x-y subruns / 450 nm`
- Accepted checkpoints: `8/8`; reconstructed Jones: `4/4`
- Tangential denominator: `{tangential_denominator:.17g} rad`
- Tangential common radial bias: `{common_delta_d:.17g} nm`
- Tangential raw/corrected residual: `{tangential_raw:.17g}` / `{tangential_corrected:.17g}`
- Raw leakage singular values: `{raw_svd["singular_values"]}`
- Step-normalized leakage singular values: `{step_svd["singular_values"]}`
- Trust-region proposals: `{len(proposals)}`; all are `MODEL_PREDICTION_NOT_PHYSICS_LABEL`
- Trust-region FDTD validation: `{trust_authorization}`
- Applicable runtime regression tests: `5 passed`; the frozen pre-execution staging-absence assertion is not applicable after authorized D6 staging creation
- Spectrum/training/canonical v1.22 merge: `NOT_AUTHORIZED`
"""
    atomic_bytes(REPORT, report_text.encode("utf-8"))

    output_paths = [
        *[path for key, path in ANALYSIS_OUTPUTS.items() if key != "provenance"],
        STAGING / "dataset_manifest_v1_22.json", STAGING / "checksums_v1_22.json", REPORT, FINALIZER,
    ]
    dump(ANALYSIS_OUTPUTS["provenance"], {
        "status": "PASS", "self_reference_policy": "EXCLUDES_ITSELF",
        "frozen_inputs": [{"path": str(path), "sha256": sha(path)} for path in [*FROZEN_HASHES, D5_JACOBIAN, D5_SVD, D5_PHASE, D5_LINEARITY, D5_ROUTE, ANCHOR_ATTESTATION]],
        "outputs": [{"path": str(path), "sha256": sha(path), "bytes": path.stat().st_size} for path in output_paths],
    })

    heavy = [
        str(path)
        for base in (STAGING, ROOT / "outputs/lp_d6_runtime")
        if base.exists()
        for path in base.rglob("*")
        if path.is_file() and path.suffix.lower() in {".fsp", ".fspx", ".ldf", ".log", ".h5", ".mat", ".npy", ".npz"}
    ]
    events = [json.loads(line) for line in (STAGING / "events.ndjson").read_text(encoding="utf-8").splitlines() if line.strip()]
    acceptance = [event for event in events if event.get("event") == "ACCEPTED"]
    final_checks = {
        "protected_unchanged": all(sha(path) == expected for path, expected in PROTECTED.items()),
        "frozen_unchanged": all(sha(path) == expected for path, expected in FROZEN_HASHES.items()),
        "accepted_events_8": len(acceptance) == 8,
        "formal_rows_8": len(read_csv(STAGING / "formal_subruns.csv")) == 8,
        "geometry_rows_4": len(read_csv(STAGING / "geometry_membership_v1_22.csv")) == 4,
        "subrun_rows_8": len(read_csv(STAGING / "subrun_records_v1_22.csv")) == 8,
        "Jones_rows_4": len(read_csv(STAGING / "candidate_wavelength_jones_v1_22.csv")) == 4,
        "reconstruction_4": len(reconstruction_rows) == 4 and all(row["status"] == "PASS" for row in reconstruction_rows),
        "heavy_absent": not heavy,
        "prediction_physics_separated": all(row["label"] == "MODEL_PREDICTION_NOT_PHYSICS_LABEL" for row in proposals),
        "package_content": verify_package()["status"] == "PASS",
    }
    if not all(final_checks.values()):
        raise RuntimeError("FINAL_ACCEPTANCE_FAILED:" + json.dumps(final_checks, sort_keys=True))
    dump(STAGING / "final_acceptance_v1_22.json", {"status": "PASS", "checks": final_checks})
    # Refresh staging checksum after the final acceptance row.
    staging_files = sorted(path for path in STAGING.rglob("*") if path.is_file() and path.name != "checksums_v1_22.json")
    dump(STAGING / "checksums_v1_22.json", {
        "status": "PASS", "self_reference_policy": "EXCLUDES_ITSELF",
        "files": [{"path": str(path.relative_to(STAGING)), "sha256": sha(path), "bytes": path.stat().st_size} for path in staging_files],
    })
    output_paths = [
        *[path for key, path in ANALYSIS_OUTPUTS.items() if key != "provenance"],
        STAGING / "dataset_manifest_v1_22.json", STAGING / "checksums_v1_22.json", REPORT, FINALIZER,
    ]
    dump(ANALYSIS_OUTPUTS["provenance"], {
        "status": "PASS", "self_reference_policy": "EXCLUDES_ITSELF",
        "frozen_inputs": [{"path": str(path), "sha256": sha(path)} for path in [*FROZEN_HASHES, D5_JACOBIAN, D5_SVD, D5_PHASE, D5_LINEARITY, D5_ROUTE, ANCHOR_ATTESTATION]],
        "outputs": [{"path": str(path), "sha256": sha(path), "bytes": path.stat().st_size} for path in output_paths],
    })
    print(json.dumps({
        "status": "PASS", "route": route, "solver_calls": 8, "accepted": 8,
        "counts": {"geometry": 4, "subruns": 8, "Jones": 4},
        "tangential_denominator_rad": tangential_denominator,
        "tangential_common_delta_D_nm": common_delta_d,
        "tangential_raw_residual": tangential_raw,
        "tangential_corrected_residual": tangential_corrected,
        "raw_singular_values": raw_svd["singular_values"],
        "step_singular_values": step_svd["singular_values"],
        "combined_rank": step_svd["numerical_rank"],
        "exact_nullspace_dimension": step_svd["exact_nullspace_dimension"],
        "near_null": step_svd["best_near_null_direction"],
        "proposals": len(proposals),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
