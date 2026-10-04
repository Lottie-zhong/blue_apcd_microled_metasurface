"""Versioned, fail-closed setup admission shared by the production adapter and tests."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import Any


ROUTE_VERSION = "APCD_GPU_RUNNER_VERSIONED_CONTROLLED_ADMISSION_V1"
POLICY_SCHEMA = "APCD_GPU_RUNNER_CONTROLLED_ADMISSION_POLICY_V1"
AUTHORITY_SCHEMA = "APCD_GPU_RUNNER_CONTROLLED_ADMISSION_AUTHORITY_V1"
SOURCE_MANIFEST_SCHEMA = "APCD_GPU_RUNNER_CONTROLLED_CASE_SOURCE_MANIFEST_V1"
SETUP_SCHEMA = "APCD_GPU_RUNNER_RESOLVED_SETUP_CONTRACT_V1"
PROOF_SCHEMA = "APCD_GPU_RUNNER_PREENTRY_SETUP_LOAD_PROOF_V1"
GEOMETRY_SOURCE_SCHEMA = "APCD_GPU_RUNNER_K6_GEOMETRY_SOURCE_V1"
DIAGNOSTIC_SOURCE_SCHEMA = "APCD_GPU_RUNNER_EXT02_DIAGNOSTIC_SOURCE_V1"
PREFLIGHT_ENVELOPE_SCHEMA = "APCD_GPU_RUNNER_CONTROLLED_SETUP_PREFLIGHT_ENVELOPE_V1"
LEGACY_CASE_IDS = (
    "K6V1_S21", "K6V1_S42", "K6V1_S36", "K6V1_S31",
    "K6V1_S45", "K6V1_S32", "K6V1_S47", "K6V1_S33",
    "K6V1_S37", "K6V1_S48", "K6V1_S35", "K6V1_S39",
)


class ControlledAdmissionError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ControlledAdmissionError("JSON_DUPLICATE_KEY:" + str(key))
        result[key] = value
    return result


def _reject_constant(value):
    raise ControlledAdmissionError("JSON_NONFINITE_CONSTANT:" + str(value))


def read_json(path: Path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"),
                          object_pairs_hook=_unique_object,
                          parse_constant=_reject_constant)
    except ControlledAdmissionError:
        raise
    except (OSError, UnicodeError, ValueError) as exc:
        raise ControlledAdmissionError("JSON_READ_FAILED:" + str(path)) from exc


def _exact_keys(value: Any, keys: set[str], error: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise ControlledAdmissionError(error)
    return value


def _sha(value: Any, error: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ControlledAdmissionError(error)
    return value


def _identity(case_id: Any, attempt_id: Any) -> None:
    for name, value in (("case_id", case_id), ("attempt_id", attempt_id)):
        if (not isinstance(value, str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", value)):
            raise ControlledAdmissionError("INVALID_" + name.upper())


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(os.path.abspath(str(left))) == os.path.normcase(os.path.abspath(str(right)))


def _under(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath((os.path.normcase(str(path)),
                                   os.path.normcase(str(root)))) == os.path.normcase(str(root))
    except ValueError:
        return False


def _case_artifact(case_dir: Path, record: Any, error: str) -> tuple[Path, str]:
    _exact_keys(record, {"path", "sha256"}, error + "_SCHEMA_INVALID")
    rel = record["path"]
    digest = _sha(record["sha256"], error + "_HASH_INVALID")
    if (not isinstance(rel, str) or not rel or Path(rel).is_absolute()
            or ".." in Path(rel).parts or "\\" in rel):
        raise ControlledAdmissionError(error + "_PATH_INVALID")
    path = case_dir.joinpath(*Path(rel).parts)
    resolved = path.resolve(strict=True)
    root = case_dir.resolve(strict=True)
    if not _under(resolved, root) or not resolved.is_file():
        raise ControlledAdmissionError(error + "_PATH_OUTSIDE_CASE")
    cursor = case_dir
    for part in Path(rel).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ControlledAdmissionError(error + "_SYMLINK_FORBIDDEN")
    if file_sha256(resolved) != digest:
        raise ControlledAdmissionError(error + "_HASH_MISMATCH")
    return resolved, digest


def setup_fingerprint(*, case_class: str, case_id: str, attempt_id: str,
                      ordered_D_nm: list[int], physical_contract_sha256: str,
                      physical_contract_semantic_sha256: str) -> str:
    return canonical_sha256({
        "schema": "APCD_GPU_RUNNER_RESOLVED_SETUP_FINGERPRINT_V1",
        "route_version": ROUTE_VERSION,
        "case_class": case_class,
        "case_id": case_id,
        "attempt_id": attempt_id,
        "ordered_D_nm": ordered_D_nm,
        "physical_contract_sha256": physical_contract_sha256,
        "physical_contract_semantic_sha256": physical_contract_semantic_sha256,
    })


def validate_geometry(values: Any, *, minimum_nm=100, maximum_nm=230) -> list[int]:
    if (not isinstance(values, list) or len(values) != 6
            or any(type(value) is not int or value < minimum_nm or value > maximum_nm
                   or value % 5 for value in values)):
        raise ControlledAdmissionError("K6_GEOMETRY_VECTOR_INVALID")
    return list(values)


def _expected_monitor(policy: dict) -> dict:
    ext = policy.get("case_classes", {}).get("EXT02_DECLARED_EH_MONITOR_DIAGNOSTIC_V1")
    if not isinstance(ext, dict):
        raise ControlledAdmissionError("POLICY_EXT02_MONITOR_MISSING")
    contract_entry = {
        "name": ext["monitor_name"],
        "type": "DFTMonitor",
        "monitor_type": ext["monitor_type"],
        "nominal_sample_z_nm": ext["nominal_sample_z_nm"],
        "reference_plane_nm": ext["reference_plane_nm"],
        "span_nm": ext["span_nm"],
        "components": ext["components"],
        "wavelengths_nm": ext["wavelengths_nm"],
        "sampling": ext["sampling"],
    }
    return {
        "contract_key": ext["monitor_contract_key"],
        "name": ext["monitor_name"],
        "monitor_type": ext["monitor_type"],
        "nominal_z_nm": ext["nominal_sample_z_nm"],
        "reference_plane_nm": ext["reference_plane_nm"],
        "span_nm": ext["span_nm"],
        "components": ext["components"],
        "wavelengths_nm": ext["wavelengths_nm"],
        "sampling": ext["sampling"],
        "actual_sampled_z_status": ext["actual_sampled_z_status"],
        "contract_entry": contract_entry,
        "protocol_sha256": ext["proposal_protocol_sha256"],
    }


def _compare_ext02_contract(base_contract: dict, actual_contract: dict,
                            policy: dict) -> None:
    monitor = _expected_monitor(policy)
    key = monitor["contract_key"]
    if not isinstance(base_contract.get("monitors"), dict):
        raise ControlledAdmissionError("BASE_MONITOR_CONTRACT_INVALID")
    expected = copy.deepcopy(base_contract)
    if key in expected["monitors"]:
        raise ControlledAdmissionError("BASE_ALREADY_HAS_CONTROLLED_MONITOR")
    expected["monitors"][key] = monitor["contract_entry"]
    if actual_contract != expected:
        raise ControlledAdmissionError("EXT02_UNDECLARED_PHYSICAL_CONTRACT_DELTA")


def _trusted_ext02_source(provenance: dict, authority: dict, case_id: str,
                          attempt_id: str) -> None:
    ext = authority["ext02"]
    if (provenance.get("schema") != DIAGNOSTIC_SOURCE_SCHEMA
            or provenance.get("case_id") != case_id
            or provenance.get("attempt_id") != attempt_id
            or provenance.get("proposal_sha256") != ext["protocol_sha256"]
            or provenance.get("base_setup_fsp_path") != ext["base_setup_fsp_path"]
            or provenance.get("base_setup_fsp_sha256") != ext["base_setup_fsp_sha256"]
            or provenance.get("geometry_source_manifest_path") != ext["geometry_source_manifest_path"]
            or provenance.get("geometry_source_manifest_sha256") != ext["geometry_source_manifest_sha256"]
            or provenance.get("ordered_D_nm") != ext["ordered_D_nm"]
            or provenance.get("geometry_hash_sha256") != ext["geometry_hash_sha256"]):
        raise ControlledAdmissionError("EXT02_DIAGNOSTIC_SOURCE_MISMATCH")
    for path_key, hash_key in (("base_setup_fsp_path", "base_setup_fsp_sha256"),
                               ("geometry_source_manifest_path", "geometry_source_manifest_sha256"),
                               ("protocol_path", "protocol_sha256")):
        trusted_path = Path(ext[path_key])
        if not trusted_path.is_file() or file_sha256(trusted_path) != ext[hash_key]:
            raise ControlledAdmissionError("EXT02_TRUSTED_SOURCE_CHANGED:" + path_key)
    geometry_source = read_json(Path(ext["geometry_source_manifest_path"]))
    if (geometry_source.get("case_id") != case_id
            or geometry_source.get("attempt_id") != attempt_id
            or geometry_source.get("ordered_D_nm") != ext["ordered_D_nm"]
            or geometry_source.get("geometry_hash_sha256") != ext["geometry_hash_sha256"]):
        raise ControlledAdmissionError("EXT02_GEOMETRY_SOURCE_IDENTITY_MISMATCH")


def _trusted_k6_geometry(provenance: dict, authority: dict, case_id: str,
                         attempt_id: str, geometry: list[int], *,
                         preflight: bool = True) -> dict:
    if provenance.get("schema") != GEOMETRY_SOURCE_SCHEMA:
        raise ControlledAdmissionError("K6_GEOMETRY_SOURCE_SCHEMA_INVALID")
    sources = authority.get("k6_geometry_authorities")
    if not isinstance(sources, list):
        raise ControlledAdmissionError("K6_GEOMETRY_AUTHORITY_INVALID")
    match = [row for row in sources if isinstance(row, dict)
             and row.get("case_id") == case_id and row.get("attempt_id") == attempt_id]
    if len(match) != 1:
        raise ControlledAdmissionError("K6_GEOMETRY_NOT_ENROLLED")
    row = match[0]
    if row.get("setup_admission_authorized") is not True:
        raise ControlledAdmissionError("K6_SETUP_ADMISSION_NOT_AUTHORIZED")
    solver_authorized = row.get("solver_entry_authorized")
    max_entries = row.get("max_solver_entries")
    if (not isinstance(solver_authorized, bool) or type(max_entries) is not int
            or max_entries < 0):
        raise ControlledAdmissionError("K6_SOLVER_ENTRY_AUTHORITY_INVALID")
    if not preflight and (solver_authorized is not True or max_entries < 1):
        raise ControlledAdmissionError("K6_SOLVER_ENTRY_NOT_AUTHORIZED")
    source_path = Path(row["path"])
    source_sha = _sha(row.get("sha256"), "K6_GEOMETRY_AUTHORITY_HASH_INVALID")
    if (not source_path.is_file() or file_sha256(source_path) != source_sha
            or provenance.get("authority_path") != str(source_path)
            or provenance.get("authority_sha256") != source_sha):
        raise ControlledAdmissionError("K6_GEOMETRY_AUTHORITY_HASH_MISMATCH")
    source = read_json(source_path)
    if (source.get("setup_admission_authorized") != row.get("setup_admission_authorized")
            or source.get("solver_entry_authorized") != row.get("solver_entry_authorized")
            or source.get("max_solver_entries") != row.get("max_solver_entries")):
        raise ControlledAdmissionError("K6_GEOMETRY_SOURCE_PERMISSION_MISMATCH")
    if (source.get("schema") != GEOMETRY_SOURCE_SCHEMA
            or source.get("eligible") is not True
            or source.get("case_id") != case_id
            or source.get("attempt_id") != attempt_id
            or source.get("ordered_D_nm") != geometry
            or source.get("geometry_hash_sha256") != provenance.get("geometry_hash_sha256")
            or provenance.get("ordered_D_nm") != geometry
            or source.get("expansion_manifest_sha256") != authority["expansion_manifest_sha256"]
            or provenance.get("expansion_manifest_sha256") != authority["expansion_manifest_sha256"]):
        raise ControlledAdmissionError("K6_GEOMETRY_NOT_AUTHORIZED_BY_SOURCE")
    base_path = Path(source.get("base_setup_fsp_path", ""))
    base_sha = _sha(source.get("base_setup_fsp_sha256"), "K6_BASE_SETUP_HASH_INVALID")
    if not base_path.is_file() or file_sha256(base_path) != base_sha:
        raise ControlledAdmissionError("K6_BASE_SETUP_SOURCE_CHANGED")
    return source


def validate_ext02_entry_budget(entry: dict, *, preflight: bool) -> int:
    """Fail closed on EXT02's per-attempt entry cap and replay policy."""
    if not isinstance(entry, dict):
        raise ControlledAdmissionError("EXT02_SOLVER_ENTRY_BUDGET_INVALID")
    authorized = entry.get("solver_entry_authorized")
    max_entries = entry.get("max_solver_entries")
    automatic_replays = entry.get("post_entry_automatic_replays")
    if (type(authorized) is not bool or type(max_entries) is not int
            or max_entries not in (0, 1) or authorized != (max_entries == 1)
            or type(automatic_replays) is not int or automatic_replays != 0):
        raise ControlledAdmissionError("EXT02_SOLVER_ENTRY_BUDGET_INVALID")
    if not preflight and max_entries != 1:
        raise ControlledAdmissionError("EXT02_SOLVER_ENTRY_NOT_AUTHORIZED")
    return max_entries


def validate_case_pack(*, route_version: str, case_class: str, case_id: str,
                       attempt_id: str, geometry: list[int], expansion_sha256: str,
                       pre_fsp_path: str, pre_fsp_sha256: str,
                       physical_contract_path: str, physical_contract_sha256: str,
                       source_manifest_path: str, source_manifest_sha256: str,
                       policy: dict, authority: dict, policy_sha256: str,
                       authority_sha256: str, case_root: Path,
                       base_contract: dict, base_contract_sha256: str,
                        preflight: bool = True) -> dict:
    """Validate all immutable files and route authorization; does not open or run FDTD."""
    if route_version != ROUTE_VERSION:
        raise ControlledAdmissionError("CONTROLLED_ROUTE_VERSION_UNSUPPORTED")
    if policy.get("schema") != POLICY_SCHEMA or policy.get("route_version") != ROUTE_VERSION:
        raise ControlledAdmissionError("CONTROLLED_POLICY_SCHEMA_INVALID")
    if authority.get("schema") != AUTHORITY_SCHEMA or authority.get("route_version") != ROUTE_VERSION:
        raise ControlledAdmissionError("CONTROLLED_AUTHORITY_SCHEMA_INVALID")
    if authority.get("policy_sha256") != policy_sha256:
        raise ControlledAdmissionError("CONTROLLED_POLICY_AUTHORITY_HASH_MISMATCH")
    _identity(case_id, attempt_id)
    if case_id in LEGACY_CASE_IDS:
        raise ControlledAdmissionError("LEGACY_CASE_MUST_USE_ORIGINAL_ROUTE")
    geometry = validate_geometry(geometry)
    if expansion_sha256 != authority.get("expansion_manifest_sha256"):
        raise ControlledAdmissionError("CONTROLLED_EXPANSION_MANIFEST_MISMATCH")
    ext02_authority = None
    if case_class == "EXT02_DECLARED_EH_MONITOR_DIAGNOSTIC_V1":
        ext02_authority = authority.get("ext02", {})
        if (case_id != ext02_authority.get("case_id")
                or attempt_id != ext02_authority.get("attempt_id")
                or geometry != ext02_authority.get("ordered_D_nm")
                or ext02_authority.get("protocol_sha256") != _expected_monitor(policy)["protocol_sha256"]):
            raise ControlledAdmissionError("EXT02_CASE_NOT_AUTHORIZED")
        validate_ext02_entry_budget(ext02_authority, preflight=preflight)
    case_root = Path(case_root).resolve(strict=True)
    case_dir = case_root / case_id / attempt_id
    if not case_dir.is_dir() or case_dir.is_symlink():
        raise ControlledAdmissionError("CONTROLLED_CASE_DIRECTORY_MISSING_OR_UNSAFE")
    source_manifest = Path(source_manifest_path).resolve(strict=True)
    if (not _under(source_manifest, case_root)
            or not _same_path(source_manifest, case_dir / "source_manifest.json")):
        raise ControlledAdmissionError("CONTROLLED_SOURCE_MANIFEST_PATH_MISMATCH")
    source_manifest_sha256 = _sha(source_manifest_sha256, "SOURCE_MANIFEST_HASH_INVALID")
    if file_sha256(source_manifest) != source_manifest_sha256:
        raise ControlledAdmissionError("SOURCE_MANIFEST_HASH_MISMATCH")
    manifest = read_json(source_manifest)
    _exact_keys(manifest, {
        "schema", "route_version", "case_class", "case_id", "attempt_id",
        "route_policy_sha256", "route_authority_sha256",
        "physical_contract_sha256", "physical_contract_semantic_sha256",
        "setup_contract_fingerprint_sha256", "artifacts",
    }, "SOURCE_MANIFEST_KEYS_INVALID")
    if (manifest["schema"] != SOURCE_MANIFEST_SCHEMA
            or manifest["route_version"] != ROUTE_VERSION
            or manifest["case_class"] != case_class
            or manifest["case_id"] != case_id
            or manifest["attempt_id"] != attempt_id
            or manifest["route_policy_sha256"] != policy_sha256
            or manifest["route_authority_sha256"] != authority_sha256):
        raise ControlledAdmissionError("SOURCE_MANIFEST_IDENTITY_OR_ROUTE_MISMATCH")
    artifacts = manifest["artifacts"]
    artifact_names = {
        "resolved_setup", "physical_contract", "source_fsp", "staged_fsp",
        "pre_entry_setup_load_proof", "case_provenance_source", "five_nm_case_spec",
    }
    _exact_keys(artifacts, artifact_names, "SOURCE_MANIFEST_ARTIFACT_SET_INVALID")
    resolved_setup_path, resolved_setup_sha = _case_artifact(case_dir, artifacts["resolved_setup"], "RESOLVED_SETUP")
    contract_path, contract_sha = _case_artifact(case_dir, artifacts["physical_contract"], "PHYSICAL_CONTRACT")
    source_path, source_sha = _case_artifact(case_dir, artifacts["source_fsp"], "SOURCE_FSP")
    staged_path, staged_sha = _case_artifact(case_dir, artifacts["staged_fsp"], "STAGED_FSP")
    proof_path, proof_sha = _case_artifact(case_dir, artifacts["pre_entry_setup_load_proof"], "PREENTRY_LOAD_PROOF")
    provenance_path, provenance_sha = _case_artifact(case_dir, artifacts["case_provenance_source"], "CASE_PROVENANCE_SOURCE")
    case_spec_path, case_spec_sha = _case_artifact(case_dir, artifacts["five_nm_case_spec"], "FIVE_NM_CASE_SPEC")
    if source_sha != staged_sha:
        raise ControlledAdmissionError("SOURCE_STAGED_FSP_HASH_MISMATCH")
    if (not _same_path(Path(pre_fsp_path), staged_path)
            or _sha(pre_fsp_sha256, "PRE_FSP_HASH_INVALID") != staged_sha):
        raise ControlledAdmissionError("RUNNER_PRE_FSP_BINDING_MISMATCH")
    if (not _same_path(Path(physical_contract_path), contract_path)
            or _sha(physical_contract_sha256, "PHYSICAL_CONTRACT_HASH_INVALID") != contract_sha):
        raise ControlledAdmissionError("RUNNER_PHYSICAL_CONTRACT_BINDING_MISMATCH")

    contract = read_json(contract_path)
    if not isinstance(contract, dict):
        raise ControlledAdmissionError("PHYSICAL_CONTRACT_INVALID")
    semantic_sha = canonical_sha256(contract)
    if (manifest["physical_contract_sha256"] != contract_sha
            or manifest["physical_contract_semantic_sha256"] != semantic_sha):
        raise ControlledAdmissionError("PHYSICAL_CONTRACT_FINGERPRINT_MISMATCH")
    if file_sha256(Path(authority["base_contract_path"])) != base_contract_sha256:
        raise ControlledAdmissionError("PINNED_BASE_CONTRACT_CHANGED")
    if (base_contract_sha256 != authority["base_contract_sha256"]
            or not isinstance(base_contract, dict)):
        raise ControlledAdmissionError("PINNED_BASE_CONTRACT_AUTHORITY_MISMATCH")

    provenance = read_json(provenance_path)
    geometry_authority = None
    if case_class == "EXT02_DECLARED_EH_MONITOR_DIAGNOSTIC_V1":
        ext = ext02_authority
        if contract_sha == base_contract_sha256:
            raise ControlledAdmissionError("EXT02_CONTRACT_HASH_REUSED_OR_UNCHANGED")
        _compare_ext02_contract(base_contract, contract, policy)
        _trusted_ext02_source(provenance, authority, case_id, attempt_id)
        expected_provenance_schema = DIAGNOSTIC_SOURCE_SCHEMA
    elif case_class == "K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1":
        if contract != base_contract or contract_sha != base_contract_sha256:
            raise ControlledAdmissionError("K6_PHYSICAL_CONTRACT_CHANGED")
        geometry_authority = _trusted_k6_geometry(
            provenance, authority, case_id, attempt_id, geometry, preflight=preflight)
        expected_provenance_schema = GEOMETRY_SOURCE_SCHEMA
    else:
        raise ControlledAdmissionError("CASE_CLASS_NOT_AUTHORIZED")
    if provenance.get("schema") != expected_provenance_schema:
        raise ControlledAdmissionError("CASE_PROVENANCE_SCHEMA_INVALID")

    spec = read_json(case_spec_path)
    expected_case_geometry_hash = (
        authority.get("ext02", {}).get("geometry_hash_sha256")
        if case_class.startswith("EXT02_")
        else geometry_authority.get("geometry_hash_sha256")
    )
    if (not isinstance(spec, dict) or spec.get("case_id") != case_id
            or spec.get("attempt_id") != attempt_id
            or spec.get("ordered_D_nm") != geometry
            or spec.get("geometry_hash_sha256") != expected_case_geometry_hash
            or spec.get("physical_contract_hash") != base_contract_sha256
            or spec.get("extension_manifest_sha256") != authority.get("expansion_manifest_sha256")
            or spec.get("mesh_contract_sha256") != authority.get("mesh_contract_sha256")
            or spec.get("monitor_contract_sha256") != authority.get("monitor_contract_sha256")):
        raise ControlledAdmissionError("FIVE_NM_CASE_SPEC_MISMATCH")
    nested = spec.get("pw_contract", {}).get("contract", {})
    if (nested.get("monitors") != base_contract.get("monitors")
            or nested.get("samples_nm") != base_contract.get("samples_nm")
            or nested.get("references_nm") != base_contract.get("references_nm")
            or nested.get("materials") != base_contract.get("materials")
            or nested.get("stack_layers") != base_contract.get("stack_layers")
            or nested.get("wavelengths_nm") != base_contract.get("wavelengths_nm")):
        raise ControlledAdmissionError("FIVE_NM_CASE_SPEC_CONTRACT_MISMATCH")

    setup = read_json(resolved_setup_path)
    _exact_keys(setup, {
        "schema", "route_version", "case_class", "case_id", "attempt_id",
        "ordered_D_nm", "geometry_hash_sha256", "physical_contract_sha256",
        "physical_contract_semantic_sha256", "setup_contract_fingerprint_sha256",
        "base_setup_fsp_sha256", "five_nm_case_spec_sha256",
    }, "RESOLVED_SETUP_KEYS_INVALID")
    expected_geometry_hash = (authority.get("ext02", {}).get("geometry_hash_sha256")
                              if case_class.startswith("EXT02_")
                              else provenance.get("geometry_hash_sha256"))
    expected_fp = setup_fingerprint(
        case_class=case_class, case_id=case_id, attempt_id=attempt_id,
        ordered_D_nm=geometry, physical_contract_sha256=contract_sha,
        physical_contract_semantic_sha256=semantic_sha)
    if (setup.get("schema") != SETUP_SCHEMA or setup.get("route_version") != ROUTE_VERSION
            or setup.get("case_class") != case_class or setup.get("case_id") != case_id
            or setup.get("attempt_id") != attempt_id or setup.get("ordered_D_nm") != geometry
            or setup.get("geometry_hash_sha256") != expected_geometry_hash
            or setup.get("physical_contract_sha256") != contract_sha
            or setup.get("physical_contract_semantic_sha256") != semantic_sha
            or setup.get("setup_contract_fingerprint_sha256") != expected_fp
            or setup.get("base_setup_fsp_sha256") != (
                authority.get("ext02", {}).get("base_setup_fsp_sha256")
                if case_class.startswith("EXT02_")
                else geometry_authority.get("base_setup_fsp_sha256"))
            or setup.get("five_nm_case_spec_sha256") != case_spec_sha):
        raise ControlledAdmissionError("RESOLVED_SETUP_CONTRACT_MISMATCH")
    if (manifest["setup_contract_fingerprint_sha256"] != expected_fp):
        raise ControlledAdmissionError("SETUP_CONTRACT_FINGERPRINT_MISMATCH")

    proof = read_json(proof_path)
    if not isinstance(proof, dict) or proof.get("schema") != PROOF_SCHEMA:
        raise ControlledAdmissionError("PREENTRY_LOAD_PROOF_SCHEMA_INVALID")
    if (proof.get("result") != "PASS" or proof.get("load_only_pass") is not True
            or proof.get("solver_run_called") is not False
            or proof.get("scientific_entry_count") != 0
            or proof.get("post_entry_truth_proved") is not False
            or proof.get("post_entry_truth_required_after_solver") is not True
            or proof.get("route_version") != ROUTE_VERSION
            or proof.get("case_class") != case_class
            or proof.get("case_id") != case_id or proof.get("attempt_id") != attempt_id
            or proof.get("route_policy_sha256") != policy_sha256
            or proof.get("route_authority_sha256") != authority_sha256
            or proof.get("physical_contract_sha256") != contract_sha
            or proof.get("physical_contract_semantic_sha256") != semantic_sha
            or proof.get("setup_contract_fingerprint_sha256") != expected_fp
            or proof.get("source_fsp_sha256") != source_sha
            or proof.get("staged_fsp_sha256") != staged_sha):
        raise ControlledAdmissionError("PREENTRY_LOAD_PROOF_MISMATCH")
    readback = proof.get("setup_readback")
    if (not isinstance(readback, dict) or readback.get("five_nm_validator_status") != "PASS"
            or readback.get("source_staged_semantic_parity") != "PASS"
            or readback.get("ordered_D_nm") != geometry):
        raise ControlledAdmissionError("PREENTRY_SETUP_READBACK_MISMATCH")
    if case_class.startswith("EXT02_"):
        expected_monitor = _expected_monitor(policy)
        monitor_rb = readback.get("added_monitor")
        if (not isinstance(monitor_rb, dict)
                or monitor_rb.get("name") != expected_monitor["name"]
                or monitor_rb.get("type") != "DFTMonitor"
                or monitor_rb.get("monitor_type") != expected_monitor["monitor_type"]
                or monitor_rb.get("z_nm") != expected_monitor["nominal_z_nm"]
                or monitor_rb.get("actual_sampled_z_nm") is not None
                or monitor_rb.get("actual_sampled_z_status") != "UNAVAILABLE_BEFORE_SOLVER"):
            raise ControlledAdmissionError("PREENTRY_DIAGNOSTIC_MONITOR_READBACK_MISMATCH")
        existing = readback.get("existing_monitor_readbacks")
        if (not isinstance(existing, dict)
                or set(existing) != {"MON_IN", "MON_PRENP", "MON_POSTNP", "MON_REFLECTION"}
                or any(not isinstance(row, dict) or row.get("base") != row.get("staged")
                       or row.get("base") != row.get("source") for row in existing.values())):
            raise ControlledAdmissionError("PREENTRY_EXISTING_MONITOR_READBACK_MISMATCH")
    return {
        "accepted": True,
        "route_version": ROUTE_VERSION,
        "case_class": case_class,
        "case_id": case_id,
        "attempt_id": attempt_id,
        "route_policy_sha256": policy_sha256,
        "route_authority_sha256": authority_sha256,
        "source_manifest_path": str(source_manifest),
        "source_manifest_sha256": source_manifest_sha256,
        "physical_contract_path": str(contract_path),
        "physical_contract_sha256": contract_sha,
        "physical_contract_semantic_sha256": semantic_sha,
        "setup_contract_fingerprint_sha256": expected_fp,
        "source_fsp_path": str(source_path),
        "source_fsp_sha256": source_sha,
        "staged_fsp_path": str(staged_path),
        "staged_fsp_sha256": staged_sha,
        "resolved_setup_path": str(resolved_setup_path),
        "resolved_setup_sha256": resolved_setup_sha,
        "pre_entry_setup_load_proof_path": str(proof_path),
        "pre_entry_setup_load_proof_sha256": proof_sha,
        "case_provenance_source_path": str(provenance_path),
        "case_provenance_source_sha256": provenance_sha,
        "five_nm_case_spec_path": str(case_spec_path),
        "five_nm_case_spec_sha256": case_spec_sha,
        "base_setup_fsp_path": (authority.get("ext02", {}).get("base_setup_fsp_path")
                                 if case_class.startswith("EXT02_")
                                 else geometry_authority.get("base_setup_fsp_path")),
        "base_setup_fsp_sha256": (authority.get("ext02", {}).get("base_setup_fsp_sha256")
                                   if case_class.startswith("EXT02_")
                                   else geometry_authority.get("base_setup_fsp_sha256")),
        "solver_entry_performed": False,
        "post_entry_truth_proved": False,
        "post_entry_truth_required_after_solver": True,
    }


def _load_pinned_route_files(*, policy_path: Path, authority_path: Path,
                             expected_policy_sha256: str,
                             expected_authority_sha256: str):
    policy_path = Path(policy_path).resolve(strict=True)
    authority_path = Path(authority_path).resolve(strict=True)
    if file_sha256(policy_path) != expected_policy_sha256:
        raise ControlledAdmissionError("CONTROLLED_POLICY_PIN_MISMATCH")
    if file_sha256(authority_path) != expected_authority_sha256:
        raise ControlledAdmissionError("CONTROLLED_AUTHORITY_PIN_MISMATCH")
    policy = read_json(policy_path)
    authority = read_json(authority_path)
    if (not isinstance(policy, dict) or policy.get("schema") != POLICY_SCHEMA
            or not isinstance(authority, dict) or authority.get("schema") != AUTHORITY_SCHEMA
            or authority.get("policy_sha256") != expected_policy_sha256):
        raise ControlledAdmissionError("CONTROLLED_ROUTE_CONFIGURATION_INVALID")
    return policy, authority


def validate_controlled_envelope(envelope: dict, *, manifest_keys: set[str],
                                  preflight: bool, policy_path: Path,
                                  authority_path: Path,
                                  expected_policy_sha256: str,
                                  expected_authority_sha256: str):
    """Validate a controlled run or setup-preflight envelope without any dispatch."""
    policy, authority = _load_pinned_route_files(
        policy_path=policy_path, authority_path=authority_path,
        expected_policy_sha256=expected_policy_sha256,
        expected_authority_sha256=expected_authority_sha256)
    route_keys = {"route_version", "case_class", "authority_path", "authority_sha256",
                  "source_manifest_path", "source_manifest_sha256"}
    if preflight:
        expected_keys = {
            "schema", "route_version", "case_class", "case_id", "attempt_id",
            "geometry", "expansion_manifest_sha256", "physical_contract_sha256",
            "physical_contract_path", "pre_fsp_path", "pre_fsp_sha256",
            "controlled_admission",
        }
        if (not isinstance(envelope, dict) or set(envelope) != expected_keys
                or envelope.get("schema") != PREFLIGHT_ENVELOPE_SCHEMA):
            raise ControlledAdmissionError("CONTROLLED_PREFLIGHT_ENVELOPE_INVALID")
        core = {key: envelope[key] for key in (
            "case_id", "attempt_id", "geometry", "expansion_manifest_sha256",
            "physical_contract_sha256", "pre_fsp_path", "pre_fsp_sha256")}
    else:
        expected_keys = set(manifest_keys) | {"physical_contract_path", "controlled_admission"}
        if not isinstance(envelope, dict) or set(envelope) != expected_keys:
            raise ControlledAdmissionError("CONTROLLED_RUN_ENVELOPE_KEYS_INVALID")
        core = {key: envelope[key] for key in manifest_keys}
        if not isinstance(core.get("run_id"), str) or core["run_id"].startswith("PREFLIGHT_ONLY_"):
            raise ControlledAdmissionError("CONTROLLED_RUN_ID_INVALID")
    route = _exact_keys(envelope.get("controlled_admission"), route_keys,
                        "CONTROLLED_ROUTE_BINDING_INVALID")
    if route["route_version"] != ROUTE_VERSION or envelope.get("route_version", ROUTE_VERSION) != ROUTE_VERSION:
        raise ControlledAdmissionError("CONTROLLED_ROUTE_VERSION_UNSUPPORTED")
    if route["case_class"] != envelope.get("case_class", route["case_class"]):
        raise ControlledAdmissionError("CONTROLLED_CASE_CLASS_MISMATCH")
    if (not _same_path(Path(route["authority_path"]), Path(authority_path))
            or _sha(route["authority_sha256"], "CONTROLLED_AUTHORITY_HASH_INVALID")
            != expected_authority_sha256):
        raise ControlledAdmissionError("CONTROLLED_AUTHORITY_BINDING_MISMATCH")
    if preflight:
        physical_contract_path = envelope["physical_contract_path"]
    else:
        physical_contract_path = envelope["physical_contract_path"]
    case_root = Path(authority["setup_root"]).resolve(strict=True)
    base_contract_path = Path(authority["base_contract_path"]).resolve(strict=True)
    base_contract_sha = file_sha256(base_contract_path)
    if base_contract_sha != authority["base_contract_sha256"]:
        raise ControlledAdmissionError("PINNED_BASE_CONTRACT_CHANGED")
    context = validate_case_pack(
        route_version=route["route_version"], case_class=route["case_class"],
        case_id=core["case_id"], attempt_id=core["attempt_id"],
        geometry=core["geometry"], expansion_sha256=core["expansion_manifest_sha256"],
        pre_fsp_path=core["pre_fsp_path"], pre_fsp_sha256=core["pre_fsp_sha256"],
        physical_contract_path=physical_contract_path,
        physical_contract_sha256=core["physical_contract_sha256"],
        source_manifest_path=route["source_manifest_path"],
        source_manifest_sha256=route["source_manifest_sha256"],
        policy=policy, authority=authority,
        policy_sha256=expected_policy_sha256,
        authority_sha256=expected_authority_sha256,
        case_root=case_root, base_contract=read_json(base_contract_path),
        base_contract_sha256=base_contract_sha, preflight=preflight)
    context["policy"] = policy
    context["authority"] = authority
    context["policy_path"] = str(Path(policy_path).resolve())
    context["authority_path"] = str(Path(authority_path).resolve())
    context["physical_contract_path"] = str(Path(physical_contract_path).resolve(strict=True))
    context["preflight_only"] = bool(preflight)
    return core, Path(physical_contract_path).resolve(strict=True), context


def _without_declared_k6_geometry_delta(row: dict) -> dict:
    """Keep validator-required identity keys while masking only enrolled D1-D6."""
    value = copy.deepcopy(row)
    for name in ("NP_D{}".format(i) for i in range(1, 7)):
        if name in value.get("geometry", {}):
            value["geometry"][name].pop("diameter_nm", None)
    # The official semantic projection indexes these fields directly. Identical
    # sentinels neutralize only their declared variation without dropping schema.
    value["ordered_D_nm"] = ["DECLARED_D1_D6_VARIANT"] * 6
    value["geometry_hash_sha256"] = "DECLARED_D1_D6_VARIANT"
    value.pop("mesh_coverage", None)
    return value


def validate_real_readback(context: dict, *, case_authority: dict,
                           source_fsp: Path, staged_fsp: Path,
                           manifest: dict, setup_validator,
                           monitor_readback) -> dict:
    """Fresh LOAD-only verification using the pinned 5 nm inspector; never calls run()."""
    source_fsp = Path(source_fsp).resolve(strict=True)
    staged_fsp = Path(staged_fsp).resolve(strict=True)
    expected_pre = Path(manifest["pre_fsp_path"]).resolve(strict=True)
    if not _same_path(expected_pre, Path(context["staged_fsp_path"])):
        raise ControlledAdmissionError("RUNNER_PRE_FSP_PATH_MISMATCH")
    if file_sha256(source_fsp) != context["staged_fsp_sha256"]:
        raise ControlledAdmissionError("RUNNER_SOURCE_FSP_HASH_MISMATCH")
    if file_sha256(staged_fsp) != context["staged_fsp_sha256"]:
        raise ControlledAdmissionError("RUNNER_STAGED_FSP_HASH_MISMATCH")
    authority = case_authority["authority"]
    policy = case_authority["policy"]
    base_path = Path(context["base_setup_fsp_path"]).resolve(strict=True)
    spec = read_json(Path(context["five_nm_case_spec_path"]))
    case_class = context["case_class"]

    baseline = setup_validator.inspect_fsp(base_path, spec)
    baseline_validation = setup_validator.validate_expected(baseline, spec)
    source_row = setup_validator.inspect_fsp(source_fsp, spec)
    source_validation = setup_validator.validate_expected(source_row, spec)
    staged_row = setup_validator.inspect_fsp(staged_fsp, spec)
    staged_validation = setup_validator.validate_expected(staged_row, spec)
    for name, result in (("BASE", baseline_validation), ("SOURCE", source_validation),
                         ("STAGED", staged_validation)):
        if not isinstance(result, dict) or result.get("status") != "PASS" or result.get("errors"):
            raise ControlledAdmissionError("FIVE_NM_BASE_VALIDATOR_" + name + "_FAILED")

    if case_class == "K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1":
        base_to_source = setup_validator.compare_semantics(
            _without_declared_k6_geometry_delta(baseline), _without_declared_k6_geometry_delta(source_row))
        source_to_staged = setup_validator.compare_semantics(
            _without_declared_k6_geometry_delta(source_row), _without_declared_k6_geometry_delta(staged_row))
        if (not isinstance(base_to_source, dict) or base_to_source.get("status") != "PASS"
                or not isinstance(source_to_staged, dict) or source_to_staged.get("status") != "PASS"):
            raise ControlledAdmissionError("K6_UNDECLARED_NON_GEOMETRY_SETUP_DELTA")
        if set(source_row["object_names"]) != set(baseline["object_names"]):
            raise ControlledAdmissionError("K6_GEOMETRY_OBJECT_INVENTORY_CHANGED")
        proof = read_json(Path(context["pre_entry_setup_load_proof_path"]))
        proof_row = proof.get("setup_readback", {}).get("staged_fsp_readback")
        if not isinstance(proof_row, dict):
            raise ControlledAdmissionError("FRESH_LOAD_PROOF_READBACK_MISSING")
        proof_parity = setup_validator.compare_semantics(
            _without_declared_k6_geometry_delta(proof_row), _without_declared_k6_geometry_delta(staged_row))
        if not isinstance(proof_parity, dict) or proof_parity.get("status") != "PASS":
            raise ControlledAdmissionError("FRESH_LOAD_PROOF_SEMANTIC_PARITY_FAILED")
        return {
            "schema": "APCD_GPU_RUNNER_V1_CONTROLLED_SETUP_STRUCTURAL_VALIDATION_V1",
            "result": "PASS", "route_version": ROUTE_VERSION,
            "case_class": case_class, "case_id": manifest["case_id"],
            "attempt_id": manifest["attempt_id"],
            "route_policy_sha256": context["route_policy_sha256"],
            "route_authority_sha256": context["route_authority_sha256"],
            "source_manifest_sha256": context["source_manifest_sha256"],
            "physical_contract_sha256": context["physical_contract_sha256"],
            "physical_contract_semantic_sha256": context["physical_contract_semantic_sha256"],
            "setup_contract_fingerprint_sha256": context["setup_contract_fingerprint_sha256"],
            "source_pre_fsp_sha256": context["staged_fsp_sha256"],
            "staged_pre_fsp_sha256": file_sha256(staged_fsp),
            "base_setup_fsp_sha256": context["base_setup_fsp_sha256"],
            "solver_run_called": False, "solver_invocations": 0,
            "scientific_entry_performed": False, "post_entry_truth_proved": False,
            "post_entry_truth_required_after_solver": True,
            "five_nm_validator": {"base": baseline_validation, "source": source_validation,
                                  "staged": staged_validation},
            "base_to_source_semantic_parity": base_to_source,
            "source_to_staged_semantic_parity": source_to_staged,
            "proof_to_fresh_load_semantic_parity": proof_parity,
            "setup_readback": {"ordered_D_nm": staged_row["ordered_D_nm"],
                               "geometry_hash_sha256": staged_row["geometry_hash_sha256"],
                               "fdtd": staged_row["fdtd"], "stack": staged_row["stack"],
                               "sources": staged_row["sources"], "monitors": staged_row["monitors"],
                               "meshes": staged_row["meshes"], "materials": staged_row["materials"]},
        }

    monitor_policy = _expected_monitor(policy)

    def without_diagnostic(row):
        value = copy.deepcopy(row)
        diagnostic_name = monitor_policy["name"]
        value["object_names"] = [name for name in value["object_names"] if name != diagnostic_name]
        value["object_types"].pop(diagnostic_name, None)
        return value

    base_to_source = setup_validator.compare_semantics(baseline, without_diagnostic(source_row))
    source_to_staged = setup_validator.compare_semantics(without_diagnostic(source_row),
                                                         without_diagnostic(staged_row))
    if (not isinstance(base_to_source, dict) or base_to_source.get("status") != "PASS"
            or not isinstance(source_to_staged, dict) or source_to_staged.get("status") != "PASS"):
        raise ControlledAdmissionError("UNDECLARED_BASE_SETUP_DELTA")
    names_added = sorted(set(source_row["object_names"]) - set(baseline["object_names"]))
    names_removed = sorted(set(baseline["object_names"]) - set(source_row["object_names"]))
    if names_added != [monitor_policy["name"]] or names_removed:
        raise ControlledAdmissionError("EXT02_SETUP_OBJECT_DELTA_INVALID")
    monitor = monitor_readback(staged_fsp, monitor_policy)
    monitor_source = monitor_readback(source_fsp, monitor_policy)
    if monitor != monitor_source:
        raise ControlledAdmissionError("SOURCE_STAGED_MONITOR_READBACK_MISMATCH")
    expected_monitor = monitor_policy
    if (monitor.get("name") != expected_monitor["name"]
            or monitor.get("monitor_type") != expected_monitor["monitor_type"]
            or not math.isclose(float(monitor.get("z_nm", -1)), float(expected_monitor["nominal_z_nm"]), abs_tol=1e-9)
            or not math.isclose(float(monitor.get("x_span_nm", -1)), float(expected_monitor["span_nm"]["x"]), abs_tol=1e-9)
            or not math.isclose(float(monitor.get("y_span_nm", -1)), float(expected_monitor["span_nm"]["y"]), abs_tol=1e-9)
            or monitor.get("frequency_points") != expected_monitor["wavelengths_nm"]["points"]
            or monitor.get("components") != expected_monitor["components"]
            or monitor.get("spatial_interpolation") != expected_monitor["sampling"]["spatial_interpolation"]
            or monitor.get("down_sample") != expected_monitor["sampling"]["down_sample"]):
        raise ControlledAdmissionError("EXT02_DIAGNOSTIC_MONITOR_SETTINGS_MISMATCH")
    existing_monitor_readbacks = {}
    for name in ("MON_IN", "MON_PRENP", "MON_POSTNP", "MON_REFLECTION"):
        values = {
            "base": monitor_readback(base_path, {"name": name}),
            "source": monitor_readback(source_fsp, {"name": name}),
            "staged": monitor_readback(staged_fsp, {"name": name}),
        }
        if values["base"] != values["source"] or values["base"] != values["staged"]:
            raise ControlledAdmissionError("EXISTING_MONITOR_CHANGED:" + name)
        existing_monitor_readbacks[name] = values

    proof = read_json(Path(context["pre_entry_setup_load_proof_path"]))
    proof_readback = proof.get("setup_readback", {})
    if proof_readback.get("added_monitor") != monitor:
        raise ControlledAdmissionError("FRESH_LOAD_MONITOR_DIFFERS_FROM_PROOF")
    proof_staged = proof_readback.get("staged_fsp_readback")
    if not isinstance(proof_staged, dict):
        raise ControlledAdmissionError("FRESH_LOAD_PROOF_READBACK_MISSING")
    proof_parity = setup_validator.compare_semantics(without_diagnostic(proof_staged),
                                                    without_diagnostic(staged_row))
    if not isinstance(proof_parity, dict) or proof_parity.get("status") != "PASS":
        raise ControlledAdmissionError("FRESH_LOAD_PROOF_SEMANTIC_PARITY_FAILED")
    if staged_row.get("ordered_D_nm") != manifest.get("geometry"):
        raise ControlledAdmissionError("FRESH_LOAD_GEOMETRY_MISMATCH")

    return {
        "schema": "APCD_GPU_RUNNER_V1_CONTROLLED_SETUP_STRUCTURAL_VALIDATION_V1",
        "result": "PASS",
        "route_version": ROUTE_VERSION,
        "case_class": case_class,
        "case_id": manifest["case_id"],
        "attempt_id": manifest["attempt_id"],
        "route_policy_sha256": context["route_policy_sha256"],
        "route_authority_sha256": context["route_authority_sha256"],
        "source_manifest_sha256": context["source_manifest_sha256"],
        "physical_contract_sha256": context["physical_contract_sha256"],
        "physical_contract_semantic_sha256": context["physical_contract_semantic_sha256"],
        "setup_contract_fingerprint_sha256": context["setup_contract_fingerprint_sha256"],
        "source_pre_fsp_sha256": context["staged_fsp_sha256"],
        "staged_pre_fsp_sha256": file_sha256(staged_fsp),
        "base_setup_fsp_sha256": context["base_setup_fsp_sha256"],
        "solver_run_called": False,
        "solver_invocations": 0,
        "scientific_entry_performed": False,
        "post_entry_truth_proved": False,
        "post_entry_truth_required_after_solver": True,
        "five_nm_validator": {"base": baseline_validation, "source": source_validation,
                              "staged": staged_validation},
        "base_to_overlay_semantic_parity": base_to_source,
        "source_to_staged_semantic_parity": source_to_staged,
        "proof_to_fresh_load_semantic_parity": proof_parity,
        "setup_readback": {
            "ordered_D_nm": staged_row["ordered_D_nm"],
            "geometry_hash_sha256": staged_row["geometry_hash_sha256"],
            "fdtd": staged_row["fdtd"],
            "stack": staged_row["stack"],
            "sources": staged_row["sources"],
            "monitors": staged_row["monitors"],
            "meshes": staged_row["meshes"],
            "materials": staged_row["materials"],
            "added_monitor": monitor,
            "existing_monitor_readbacks": existing_monitor_readbacks,
            "base_object_delta": {"added": names_added, "removed": names_removed},
        },
    }
