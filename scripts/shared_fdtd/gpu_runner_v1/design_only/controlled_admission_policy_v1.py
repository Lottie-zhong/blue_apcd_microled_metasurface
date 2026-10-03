"""Design-only reference validator for controlled GPU Runner case admission.

This module is intentionally not imported by the production adapter or runner.
It validates manifests and synthetic/offline fixtures only; it never opens an
FSP with Lumerical and has no solver/dispatch entry point.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import Any, Iterable


class AdmissionError(ValueError):
    """A case setup violates the design-only admission contract."""


MANIFEST_SCHEMA = "APCD_GPU_RUNNER_CONTROLLED_CASE_SOURCE_MANIFEST_V1"
SETUP_SCHEMA = "APCD_GPU_RUNNER_RESOLVED_SETUP_CONTRACT_V1"
PREENTRY_LOAD_SCHEMA = "APCD_GPU_RUNNER_PREENTRY_SETUP_LOAD_ONLY_PROOF_V1"
GEOMETRY_SOURCE_SCHEMA = "APCD_GPU_RUNNER_K6_GEOMETRY_SOURCE_V1"
DIAGNOSTIC_SOURCE_SCHEMA = "APCD_GPU_RUNNER_DIAGNOSTIC_MONITOR_SOURCE_V1"
FINGERPRINT_SCHEMA = "APCD_GPU_RUNNER_RESOLVED_SETUP_FINGERPRINT_V1"

SAFE_ID = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,95}$")
SAFE_ATTEMPT = re.compile(r"^attempt_[0-9]{3}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AdmissionError("CANONICAL_JSON_INVALID") from exc


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AdmissionError("JSON_DUPLICATE_KEY:" + key)
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise AdmissionError("JSON_NONFINITE_NUMBER:" + value)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except AdmissionError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AdmissionError("JSON_READ_FAILED:" + path.name) from exc


def _exact_keys(value: Any, expected: set[str], error: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise AdmissionError(error)
    return value


def _safe_identity(case_id: Any, attempt_id: Any) -> None:
    if not isinstance(case_id, str) or not SAFE_ID.fullmatch(case_id):
        raise AdmissionError("CASE_ID_INVALID")
    if not isinstance(attempt_id, str) or not SAFE_ATTEMPT.fullmatch(attempt_id):
        raise AdmissionError("ATTEMPT_ID_INVALID")


def _check_sha(value: Any, error: str) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise AdmissionError(error)
    return value


def _resolve_file(
    raw_path: Any,
    *,
    relative_to: Path,
    allowed_roots: Iterable[Path],
    error_prefix: str,
) -> Path:
    if not isinstance(raw_path, str) or not raw_path:
        raise AdmissionError(error_prefix + "_PATH_INVALID")
    supplied = Path(raw_path)
    path = supplied if supplied.is_absolute() else relative_to / supplied
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise AdmissionError(error_prefix + "_PATH_MISSING") from exc
    if not resolved.is_file() or path.is_symlink():
        raise AdmissionError(error_prefix + "_PATH_NOT_REGULAR_FILE")
    lexical_absolute = Path(os.path.abspath(path))
    if os.path.normcase(str(resolved)) != os.path.normcase(str(lexical_absolute)):
        raise AdmissionError(error_prefix + "_PATH_SYMLINK_OR_REPARSE")
    contained = False
    for root in allowed_roots:
        try:
            resolved.relative_to(root.resolve(strict=True))
            contained = True
            break
        except (ValueError, OSError, RuntimeError):
            continue
    if not contained:
        raise AdmissionError(error_prefix + "_PATH_OUTSIDE_AUTHORITY")
    return resolved


def _verify_artifact(
    artifacts: dict[str, Any],
    name: str,
    *,
    case_dir: Path,
    allowed_roots: Iterable[Path] | None = None,
) -> tuple[Path, str]:
    record = _exact_keys(
        artifacts.get(name), {"path", "sha256"}, "ARTIFACT_RECORD_INVALID:" + name
    )
    expected_sha = _check_sha(record["sha256"], "ARTIFACT_SHA256_INVALID:" + name)
    roots = tuple(allowed_roots) if allowed_roots is not None else (case_dir,)
    path = _resolve_file(
        record["path"],
        relative_to=case_dir,
        allowed_roots=roots,
        error_prefix=name.upper(),
    )
    actual_sha = file_sha256(path)
    if actual_sha != expected_sha:
        raise AdmissionError("ARTIFACT_HASH_MISMATCH:" + name)
    return path, actual_sha


def setup_fingerprint(
    *,
    case_class: str,
    case_id: str,
    attempt_id: str,
    ordered_d_nm: list[float],
    physical_contract_sha256: str,
    physical_contract_semantic_sha256: str,
) -> str:
    return canonical_sha256(
        {
            "schema": FINGERPRINT_SCHEMA,
            "case_class": case_class,
            "case_id": case_id,
            "attempt_id": attempt_id,
            "ordered_D_nm": ordered_d_nm,
            "physical_contract_sha256": physical_contract_sha256,
            "physical_contract_semantic_sha256": physical_contract_semantic_sha256,
        }
    )


def _validate_geometry(value: Any) -> list[float]:
    if not isinstance(value, list) or len(value) != 6:
        raise AdmissionError("ORDERED_D_MUST_CONTAIN_D1_TO_D6")
    result: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise AdmissionError("ORDERED_D_VALUE_INVALID")
        number = float(item)
        if not math.isfinite(number) or number <= 0:
            raise AdmissionError("ORDERED_D_VALUE_INVALID")
        result.append(number)
    return result


def _monitor_contract_valid(
    base_contract: dict[str, Any],
    candidate_contract: dict[str, Any],
    expected_monitor: dict[str, Any],
) -> None:
    if set(base_contract) != set(candidate_contract):
        raise AdmissionError("DIAGNOSTIC_CONTRACT_FIELDS_CHANGED")
    for key in base_contract:
        if key == "monitors":
            continue
        if candidate_contract[key] != base_contract[key]:
            raise AdmissionError("DIAGNOSTIC_CONTRACT_FIELDS_CHANGED:" + key)
    base_monitors = base_contract.get("monitors")
    candidate_monitors = candidate_contract.get("monitors")
    if not isinstance(base_monitors, list) or not isinstance(candidate_monitors, list):
        raise AdmissionError("DIAGNOSTIC_MONITOR_LIST_INVALID")
    if (len(candidate_monitors) != len(base_monitors) + 1
            or candidate_monitors[:-1] != base_monitors
            or candidate_monitors[-1] != expected_monitor):
        raise AdmissionError("DIAGNOSTIC_OVERLAY_NOT_EXACT_SINGLE_MONITOR")


def validate_case_admission(
    policy: dict[str, Any],
    *,
    case_class: str,
    base_setup: dict[str, Any],
    authority_root: Path,
    manifest_path: Path,
    expected_manifest_sha256: str,
    trusted_provenance_roots: Iterable[Path] = (),
) -> dict[str, Any]:
    """Validate one offline admission pack; never dispatches or loads an FSP.

    `base_setup` has `ordered_D_nm`, `physical_contract`, and the byte-level
    `physical_contract_sha256` from an already authorized setup. `manifest_path`
    is the new case's source manifest and its digest is supplied independently
    by the immutable dispatch envelope.
    """
    if (not isinstance(policy, dict)
            or not {"schema", "status", "k6_geometry", "ext02_diagnostic"}.issubset(policy)):
        raise AdmissionError("POLICY_SCHEMA_INVALID")
    if policy["schema"] != "APCD_GPU_RUNNER_CONTROLLED_CASE_ADMISSION_POLICY_V1":
        raise AdmissionError("POLICY_SCHEMA_INVALID")
    if policy["status"] != "DESIGN_ONLY_REFERENCE_NOT_PRODUCTION_AUTHORITY":
        raise AdmissionError("POLICY_NOT_DESIGN_ONLY")
    _check_sha(expected_manifest_sha256, "SOURCE_MANIFEST_SHA256_INVALID")
    if not isinstance(base_setup, dict) or not isinstance(base_setup.get("physical_contract"), dict):
        raise AdmissionError("BASE_SETUP_INVALID")
    base_contract = base_setup["physical_contract"]
    base_contract_sha = _check_sha(
        base_setup.get("physical_contract_sha256"), "BASE_CONTRACT_SHA256_INVALID"
    )
    if not isinstance(authority_root, Path) or not authority_root.is_dir():
        raise AdmissionError("AUTHORITY_ROOT_MISSING")
    root = authority_root.resolve(strict=True)
    manifest_abs = _resolve_file(
        str(manifest_path),
        relative_to=root,
        allowed_roots=(root,),
        error_prefix="SOURCE_MANIFEST",
    )
    try:
        manifest_rel = manifest_abs.relative_to(root)
    except ValueError as exc:
        raise AdmissionError("SOURCE_MANIFEST_PATH_OUTSIDE_AUTHORITY") from exc
    if len(manifest_rel.parts) != 3 or manifest_rel.name != "source_manifest.json":
        raise AdmissionError("SOURCE_MANIFEST_PATH_INVALID")
    case_id, attempt_id = manifest_rel.parts[:2]
    _safe_identity(case_id, attempt_id)
    case_dir = root / case_id / attempt_id
    if manifest_abs != (case_dir / "source_manifest.json").resolve(strict=True):
        raise AdmissionError("SOURCE_MANIFEST_PATH_MISMATCH")
    if file_sha256(manifest_abs) != expected_manifest_sha256:
        raise AdmissionError("SOURCE_MANIFEST_HASH_MISMATCH")

    manifest = _read_json(manifest_abs)
    _exact_keys(
        manifest,
        {
            "schema", "case_class", "case_id", "attempt_id",
            "physical_contract_sha256", "physical_contract_semantic_sha256",
            "setup_contract_fingerprint_sha256", "artifacts",
        },
        "SOURCE_MANIFEST_SCHEMA_INVALID",
    )
    if manifest["schema"] != MANIFEST_SCHEMA:
        raise AdmissionError("SOURCE_MANIFEST_SCHEMA_INVALID")
    if (manifest["case_class"] != case_class or manifest["case_id"] != case_id
            or manifest["attempt_id"] != attempt_id):
        raise AdmissionError("CASE_AUTHORITY_IDENTITY_MISMATCH")
    artifacts = manifest["artifacts"]
    _exact_keys(
        artifacts,
        {
            "resolved_setup", "physical_contract", "source_fsp", "staged_fsp",
            "pre_entry_setup_load_proof", "case_provenance_source",
        },
        "SOURCE_MANIFEST_ARTIFACT_SET_INVALID",
    )

    setup_path, _ = _verify_artifact(artifacts, "resolved_setup", case_dir=case_dir)
    contract_path, contract_sha = _verify_artifact(
        artifacts, "physical_contract", case_dir=case_dir
    )
    source_fsp, source_sha = _verify_artifact(artifacts, "source_fsp", case_dir=case_dir)
    staged_fsp, staged_sha = _verify_artifact(artifacts, "staged_fsp", case_dir=case_dir)
    proof_path, proof_sha = _verify_artifact(
        artifacts, "pre_entry_setup_load_proof", case_dir=case_dir
    )
    provenance_roots = (case_dir, *tuple(trusted_provenance_roots))
    provenance_path, provenance_sha = _verify_artifact(
        artifacts,
        "case_provenance_source",
        case_dir=case_dir,
        allowed_roots=provenance_roots,
    )
    del proof_sha, provenance_sha
    if source_sha != staged_sha:
        raise AdmissionError("SOURCE_STAGED_FSP_HASH_MISMATCH")

    setup = _read_json(setup_path)
    _exact_keys(
        setup,
        {
            "schema", "case_id", "attempt_id", "ordered_D_nm",
            "physical_contract_sha256", "physical_contract_semantic_sha256",
            "setup_contract_fingerprint_sha256",
        },
        "RESOLVED_SETUP_SCHEMA_INVALID",
    )
    if (setup["schema"] != SETUP_SCHEMA or setup["case_id"] != case_id
            or setup["attempt_id"] != attempt_id):
        raise AdmissionError("RESOLVED_SETUP_IDENTITY_MISMATCH")
    ordered_d = _validate_geometry(setup["ordered_D_nm"])
    contract = _read_json(contract_path)
    if not isinstance(contract, dict):
        raise AdmissionError("PHYSICAL_CONTRACT_INVALID")
    contract_semantic_sha = canonical_sha256(contract)
    if (manifest["physical_contract_sha256"] != contract_sha
            or setup["physical_contract_sha256"] != contract_sha):
        raise AdmissionError("PHYSICAL_CONTRACT_FILE_HASH_MISMATCH")
    if (manifest["physical_contract_semantic_sha256"] != contract_semantic_sha
            or setup["physical_contract_semantic_sha256"] != contract_semantic_sha):
        raise AdmissionError("PHYSICAL_CONTRACT_SEMANTIC_HASH_MISMATCH")
    expected_setup_fp = setup_fingerprint(
        case_class=case_class,
        case_id=case_id,
        attempt_id=attempt_id,
        ordered_d_nm=ordered_d,
        physical_contract_sha256=contract_sha,
        physical_contract_semantic_sha256=contract_semantic_sha,
    )
    if (manifest["setup_contract_fingerprint_sha256"] != expected_setup_fp
            or setup["setup_contract_fingerprint_sha256"] != expected_setup_fp):
        raise AdmissionError("SETUP_CONTRACT_FINGERPRINT_MISMATCH")

    provenance = _read_json(provenance_path)
    if not isinstance(provenance, dict):
        raise AdmissionError("CASE_PROVENANCE_SOURCE_INVALID")
    if case_class == "K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1":
        route = policy["k6_geometry"]
        if case_id == "" or provenance.get("schema") != GEOMETRY_SOURCE_SCHEMA:
            raise AdmissionError("K6_GEOMETRY_SOURCE_SCHEMA_INVALID")
        if (provenance.get("eligible") is not True
                or provenance.get("case_id") != case_id
                or provenance.get("attempt_id") != attempt_id
                or provenance.get("ordered_D_nm") != ordered_d
                or provenance.get("expansion_manifest_sha256")
                    != route.get("geometry_source", {}).get(
                        "required_expansion_manifest_sha256")):
            raise AdmissionError("K6_GEOMETRY_NOT_AUTHORIZED_BY_SOURCE")
        if ordered_d == _validate_geometry(base_setup.get("ordered_D_nm")):
            raise AdmissionError("K6_GEOMETRY_CHANGE_REQUIRED")
        if (contract != base_contract or contract_sha != base_contract_sha):
            raise AdmissionError("K6_PHYSICAL_CONTRACT_CHANGED")
    elif case_class == "EXT02_DECLARED_EH_MONITOR_DIAGNOSTIC_V1":
        route = policy["ext02_diagnostic"]
        if case_id != route.get("case_id") or provenance.get("schema") != DIAGNOSTIC_SOURCE_SCHEMA:
            raise AdmissionError("EXT02_DIAGNOSTIC_SOURCE_SCHEMA_INVALID")
        if (provenance.get("case_id") != case_id
                or provenance.get("attempt_id") != attempt_id
                or provenance.get("proposal_sha256") != route.get("proposal_reference_sha256")
                or provenance.get("added_monitor") != route.get("added_monitor")):
            raise AdmissionError("EXT02_DIAGNOSTIC_SOURCE_MISMATCH")
        if ordered_d != _validate_geometry(base_setup.get("ordered_D_nm")):
            raise AdmissionError("EXT02_GEOMETRY_MUST_REMAIN_FIXED")
        _monitor_contract_valid(base_contract, contract, route.get("added_monitor"))
        if contract_sha == base_contract_sha:
            raise AdmissionError("EXT02_CONTRACT_HASH_REUSED_OR_UNCHANGED")
    else:
        raise AdmissionError("CASE_CLASS_NOT_AUTHORIZED")

    proof = _read_json(proof_path)
    if not isinstance(proof, dict) or proof.get("schema") != PREENTRY_LOAD_SCHEMA:
        raise AdmissionError("PREENTRY_LOAD_PROOF_SCHEMA_INVALID")
    if (proof.get("load_only_pass") is not True
            or proof.get("solver_run_called") is not False
            or proof.get("scientific_entry_count") != 0
            or proof.get("case_id") != case_id
            or proof.get("attempt_id") != attempt_id
            or proof.get("physical_contract_sha256") != contract_sha
            or proof.get("physical_contract_semantic_sha256") != contract_semantic_sha
            or proof.get("setup_contract_fingerprint_sha256") != expected_setup_fp
            or proof.get("source_fsp_sha256") != source_sha
            or proof.get("staged_fsp_sha256") != staged_sha):
        raise AdmissionError("PREENTRY_LOAD_PROOF_MISMATCH")
    readback = proof.get("setup_readback")
    if not isinstance(readback, dict) or readback.get("ordered_D_nm") != ordered_d:
        raise AdmissionError("PREENTRY_SETUP_READBACK_MISMATCH")
    if case_class == "EXT02_DECLARED_EH_MONITOR_DIAGNOSTIC_V1":
        monitors = readback.get("monitor_objects")
        expected_monitor = policy["ext02_diagnostic"]["added_monitor"]
        if not isinstance(monitors, list) or expected_monitor not in monitors:
            raise AdmissionError("PREENTRY_DIAGNOSTIC_MONITOR_NOT_READ_BACK")

    return {
        "accepted": True,
        "design_only": True,
        "case_id": case_id,
        "attempt_id": attempt_id,
        "case_class": case_class,
        "physical_contract_sha256": contract_sha,
        "physical_contract_semantic_sha256": contract_semantic_sha,
        "setup_contract_fingerprint_sha256": expected_setup_fp,
        "source_fsp_sha256": source_sha,
        "staged_fsp_sha256": staged_sha,
        "pre_entry_load_only_proof_sha256": file_sha256(proof_path),
        "solver_entry_performed": False,
        "post_entry_truth_recovery_required_for_admission": False,
    }
