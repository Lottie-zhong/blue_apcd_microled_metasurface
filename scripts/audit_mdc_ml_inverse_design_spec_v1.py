"""Audit and build deterministic static examples for MDC ML inverse-design v1."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

try:
    from scripts.mdc_ml_structure_grammar_v1 import (
        CANONICAL_GEOMETRY_HASH_VERSION,
        DEFAULT_BOUNDS,
        GrammarError,
        MATERIAL_PROVENANCE,
        NOMINAL_PRIMARY_OBJECTIVES,
        PHYSICAL_CONFIGURATION_HASH_VERSION,
        ROBUST_PRIMARY_OBJECTIVES,
        SIMULATION_PROVENANCE_HASH_VERSION,
        SPLIT_GROUP_HASH_VERSION,
        TOPOLOGY_FAMILIES,
        audit_split_leakage,
        canonicalize_structure,
        decode_canonical_structure,
        generate_dummy_candidates,
        geometry_hash,
        physical_configuration_hash,
        resolve_primary_objectives,
        simulation_provenance_hash,
        split_group_hash,
        validate_bounds,
    )
except ModuleNotFoundError:  # Direct execution from scripts/.
    from mdc_ml_structure_grammar_v1 import (  # type: ignore
        CANONICAL_GEOMETRY_HASH_VERSION,
        DEFAULT_BOUNDS,
        GrammarError,
        MATERIAL_PROVENANCE,
        NOMINAL_PRIMARY_OBJECTIVES,
        PHYSICAL_CONFIGURATION_HASH_VERSION,
        ROBUST_PRIMARY_OBJECTIVES,
        SIMULATION_PROVENANCE_HASH_VERSION,
        SPLIT_GROUP_HASH_VERSION,
        TOPOLOGY_FAMILIES,
        audit_split_leakage,
        canonicalize_structure,
        decode_canonical_structure,
        generate_dummy_candidates,
        geometry_hash,
        physical_configuration_hash,
        resolve_primary_objectives,
        simulation_provenance_hash,
        split_group_hash,
        validate_bounds,
    )

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "configs" / "mdc_ml_inverse_design_spec_v1.yaml"
SCHEMA_PATH = ROOT / "configs" / "mdc_ml_dataset_schema_v1.json"
FREEZE_MANIFEST_PATH = ROOT / "configs" / "mdc_ml_spec_freeze_manifest_v1.json"
OUTPUT_DIR = ROOT / "outputs" / "mdc_ml_inverse_design_spec_v1"
SPEC_FREEZE_ANCHOR_COMMIT = "ba361fa39a5c04cccbaa55ad1d89b328c5a8d91b"
SPEC_SOURCE_FROZEN_COMMIT = "40dedf4098fa0ca19e0e5f0e3395e73fb4949c53"
REPOSITORY_CONTRACT_VERSION = "mdc_ml_repository_freeze_contract_v1"
REQUIRED_IMMUTABLE_PAYLOAD = (
    "configs/mdc_ml_inverse_design_spec_v1.yaml",
    "configs/mdc_ml_dataset_schema_v1.json",
    "scripts/mdc_ml_structure_grammar_v1.py",
    "reports/mdc_ml_inverse_design_spec_v1.md",
    "reports/mdc_ml_inverse_design_spec_v1_p0_contract_audit.md",
    "reports/mdc_ml_inverse_design_spec_v1_p0b_hash_objective_audit.md",
)
BASELINE_ID = "P1_ZL1_ALTERNATIVE_G3_A3"
BASELINE_SOURCE = ROOT / "outputs" / "mdc_p1_asymmetric_scan_static_v1" / "p1_asymmetric_structures.csv"
MATERIAL_POLICY_SOURCE = ROOT / "configs" / "mdc_defect_450_material_policy.json"
STATIC_FILES = (
    "topology_examples.csv",
    "canonicalization_examples.csv",
    "invalid_structure_examples.csv",
    "objective_definition_table.csv",
    "schema_field_inventory.csv",
    "design_space_coverage_audit.json",
    "baseline_roundtrip_audit_v1.json",
    "p0_contract_audit_v1.json",
    "p0b_hash_objective_audit_v1.json",
    "validation.json",
)


def load_spec(path: Path = SPEC_PATH) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        import yaml

        value = yaml.safe_load(text)
        if not isinstance(value, dict):
            raise ValueError("spec root must be a mapping")
        return value


def load_schema(path: Path = SCHEMA_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("schema root must be an object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def git_head(root: Path = ROOT) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True, encoding="utf-8"
    ).strip()


def load_freeze_manifest(path: Path = FREEZE_MANIFEST_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("freeze manifest root must be an object")
    return value


def git_commit_exists(commit: str, root: Path = ROOT) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def git_is_ancestor(anchor: str, head: str, root: Path = ROOT) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", anchor, head],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def git_payload_sha256(anchor: str, path: str, root: Path = ROOT) -> str:
    payload = subprocess.check_output(["git", "show", f"{anchor}:{path}"], cwd=root)
    return hashlib.sha256(payload).hexdigest()


def git_index_entry(path: str, root: Path = ROOT) -> dict[str, str]:
    output = subprocess.check_output(
        ["git", "ls-files", "--stage", "--", path], cwd=root, text=True
    ).strip()
    entries = [line for line in output.splitlines() if line]
    if len(entries) != 1:
        raise ValueError(f"expected one index entry for {path}, got {len(entries)}")
    metadata, indexed_path = entries[0].split("\t", 1)
    mode, object_id, stage = metadata.split()
    if indexed_path != path or stage != "0":
        raise ValueError(f"invalid index entry for {path}: {entries[0]}")
    return {"mode": mode, "object_id": object_id, "stage": stage}


def git_index_payload_sha256(path: str, root: Path = ROOT) -> str:
    payload = subprocess.check_output(["git", "show", f":{path}"], cwd=root)
    return hashlib.sha256(payload).hexdigest()


def git_canonical_worktree_content(path: str, root: Path = ROOT) -> tuple[str, str]:
    payload = (root / path).read_bytes()
    result = subprocess.run(
        ["git", "hash-object", f"--path={path}", "--stdin"],
        cwd=root,
        input=payload,
        capture_output=True,
        check=True,
    )
    object_id = result.stdout.decode("ascii").strip()
    existing = subprocess.run(
        ["git", "cat-file", "blob", object_id],
        cwd=root,
        capture_output=True,
    )
    if existing.returncode == 0:
        return object_id, hashlib.sha256(existing.stdout).hexdigest()

    # A genuinely modified clean-filtered blob may not exist in the repository.
    # Materialize it only in a disposable object directory so the audit remains
    # read-only with respect to the repository's own object database.
    with tempfile.TemporaryDirectory(prefix="mdc_ml_p0d_git_objects_") as temp:
        object_directory = Path(temp) / "objects"
        object_directory.mkdir()
        environment = os.environ.copy()
        environment["GIT_OBJECT_DIRECTORY"] = str(object_directory)
        written = subprocess.run(
            ["git", "hash-object", "-w", f"--path={path}", "--stdin"],
            cwd=root,
            input=payload,
            capture_output=True,
            check=True,
            env=environment,
        )
        written_object_id = written.stdout.decode("ascii").strip()
        if written_object_id != object_id:
            raise RuntimeError(f"non-deterministic Git canonicalization for {path}")
        canonical = subprocess.check_output(
            ["git", "cat-file", "blob", object_id], cwd=root, env=environment
        )
    return object_id, hashlib.sha256(canonical).hexdigest()


def git_path_has_diff(path: str, root: Path = ROOT, *, cached: bool) -> bool:
    command = ["git", "diff", "--quiet"]
    if cached:
        command.append("--cached")
    command.extend(["--", path])
    result = subprocess.run(command, cwd=root, capture_output=True)
    if result.returncode not in (0, 1):
        stderr = result.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"git diff failed for {path}: {stderr}")
    return result.returncode == 1


def checkout_eol(payload: bytes) -> str:
    crlf_count = payload.count(b"\r\n")
    lf_count = payload.count(b"\n")
    if crlf_count and crlf_count == lf_count:
        return "crlf"
    if crlf_count and lf_count > crlf_count:
        return "mixed"
    if lf_count:
        return "lf"
    return "none"


def audit_repository_freeze_contract(
    *,
    root: Path = ROOT,
    manifest_path: Path | None = None,
    current_head: str | None = None,
    expected_anchor: str = SPEC_FREEZE_ANCHOR_COMMIT,
    commit_exists: Callable[[str, Path], bool] = git_commit_exists,
    ancestor_check: Callable[[str, str, Path], bool] = git_is_ancestor,
    anchor_payload_hash: Callable[[str, str, Path], str] = git_payload_sha256,
) -> dict[str, Any]:
    """Verify immutable payload identity using Git-canonical content semantics."""
    path = root / "configs" / "mdc_ml_spec_freeze_manifest_v1.json" if manifest_path is None else manifest_path
    errors: list[str] = []
    if not path.exists():
        return {
            "status": "FAIL", "repository_contract_version": REPOSITORY_CONTRACT_VERSION,
            "errors": [f"freeze manifest is unavailable: {path}"], "payloads": [],
            "payload_drift_count": 0, "immutable_payload_count": 0,
            "freeze_anchor_exists": False, "anchor_is_ancestor": False,
            "current_head": current_head,
        }
    try:
        manifest = load_freeze_manifest(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "status": "FAIL", "repository_contract_version": REPOSITORY_CONTRACT_VERSION,
            "errors": [f"invalid freeze manifest: {exc}"], "payloads": [],
            "payload_drift_count": 0, "immutable_payload_count": 0,
            "freeze_anchor_exists": False, "anchor_is_ancestor": False,
            "current_head": current_head,
        }

    anchor = str(manifest.get("spec_freeze_anchor_commit", ""))
    if manifest.get("manifest_version") != "mdc_ml_spec_freeze_manifest_v1":
        errors.append("freeze manifest version mismatch")
    if manifest.get("repository_contract_version") != REPOSITORY_CONTRACT_VERSION:
        errors.append("repository contract version mismatch")
    if manifest.get("head_policy") != "descendant_or_equal":
        errors.append("head policy must be descendant_or_equal")
    if anchor != expected_anchor:
        errors.append(f"freeze anchor is {anchor}, expected immutable anchor {expected_anchor}")
    try:
        head = git_head(root) if current_head is None else current_head
    except (OSError, subprocess.CalledProcessError) as exc:
        head = None
        errors.append(f"cannot resolve current HEAD: {exc}")
    anchor_exists = bool(anchor) and commit_exists(anchor, root)
    if not anchor_exists:
        errors.append(f"freeze anchor commit does not exist: {anchor}")
    anchor_is_ancestor = bool(anchor_exists and head and ancestor_check(anchor, head, root))
    if anchor_exists and head and not anchor_is_ancestor:
        errors.append(f"freeze anchor {anchor} is not an ancestor of HEAD {head}")

    entries = manifest.get("immutable_payload")
    if not isinstance(entries, list):
        entries = []
        errors.append("immutable_payload must be a list")
    entry_paths = [entry.get("path") for entry in entries if isinstance(entry, dict)]
    if tuple(entry_paths) != REQUIRED_IMMUTABLE_PAYLOAD:
        errors.append("immutable payload inventory/order differs from the frozen v1 contract")
    mutable = manifest.get("mutable_maintenance_files", [])
    if set(entry_paths) & set(mutable if isinstance(mutable, list) else []):
        errors.append("immutable payload overlaps mutable maintenance files")

    payloads: list[dict[str, Any]] = []
    drift_count = 0
    sha_pattern = re.compile(r"^[0-9a-f]{64}$")
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"immutable_payload[{index}] must be an object")
            drift_count += 1
            continue
        relative = str(entry.get("path", ""))
        expected = str(entry.get("sha256", ""))
        if entry.get("immutable") is not True:
            errors.append(f"payload is not marked immutable: {relative}")
        if not entry.get("role"):
            errors.append(f"payload role is missing: {relative}")
        if sha_pattern.fullmatch(expected) is None:
            errors.append(f"payload expected SHA-256 is invalid: {relative}")
        anchor_actual: str | None = None
        head_actual: str | None = None
        index_actual: str | None = None
        index_object_id: str | None = None
        index_mode: str | None = None
        canonical_object_id: str | None = None
        canonical_actual: str | None = None
        raw_actual: str | None = None
        raw_eol: str | None = None
        unstaged_diff: bool | None = None
        staged_diff: bool | None = None
        if anchor_exists and relative:
            try:
                anchor_actual = anchor_payload_hash(anchor, relative, root)
            except (OSError, subprocess.CalledProcessError) as exc:
                errors.append(f"cannot read payload from freeze anchor {relative}: {exc}")
        worktree_path = root / relative
        regular_file = bool(
            worktree_path.exists()
            and worktree_path.is_file()
            and not worktree_path.is_symlink()
        )
        if head and relative:
            try:
                head_actual = git_payload_sha256(head, relative, root)
            except (OSError, subprocess.CalledProcessError) as exc:
                errors.append(f"cannot read payload from current HEAD {relative}: {exc}")
        if relative:
            try:
                index_entry = git_index_entry(relative, root)
                index_mode = index_entry["mode"]
                index_object_id = index_entry["object_id"]
                index_actual = git_index_payload_sha256(relative, root)
            except (OSError, ValueError, subprocess.CalledProcessError) as exc:
                errors.append(f"cannot read payload from index {relative}: {exc}")
        if regular_file:
            raw_payload = worktree_path.read_bytes()
            raw_actual = hashlib.sha256(raw_payload).hexdigest()
            raw_eol = checkout_eol(raw_payload)
            try:
                canonical_object_id, canonical_actual = git_canonical_worktree_content(
                    relative, root
                )
                unstaged_diff = git_path_has_diff(relative, root, cached=False)
                staged_diff = git_path_has_diff(relative, root, cached=True)
            except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
                errors.append(f"cannot canonicalize working-tree payload {relative}: {exc}")
        anchor_matches_manifest = anchor_actual == expected
        head_matches_manifest = head_actual == expected
        index_matches_manifest = index_actual == expected
        canonical_matches_manifest = canonical_actual == expected
        index_type_ok = bool(index_mode and index_mode.startswith("100"))
        no_unstaged_diff = unstaged_diff is False
        no_staged_diff = staged_diff is False
        status = "PASS" if all((
            anchor_matches_manifest,
            head_matches_manifest,
            index_matches_manifest,
            canonical_matches_manifest,
            regular_file,
            index_type_ok,
            no_unstaged_diff,
            no_staged_diff,
        )) else "FAIL"
        if status != "PASS":
            drift_count += 1
            if not anchor_matches_manifest:
                errors.append(f"manifest SHA-256 does not match freeze anchor payload: {relative}")
            if not head_matches_manifest:
                errors.append(f"current HEAD immutable payload drift: {relative}")
            if not index_matches_manifest:
                errors.append(f"index immutable payload drift: {relative}")
            if not canonical_matches_manifest:
                errors.append(f"Git-canonical working-tree immutable payload drift: {relative}")
            if not regular_file:
                errors.append(f"immutable payload is missing or not a regular file: {relative}")
            if not index_type_ok:
                errors.append(f"immutable payload index type is not a regular file: {relative}")
            if not no_unstaged_diff:
                errors.append(f"unstaged semantic payload diff: {relative}")
            if not no_staged_diff:
                errors.append(f"staged payload diff: {relative}")
        payloads.append({
            "path": relative, "role": entry.get("role"), "immutable": entry.get("immutable"),
            "expected_sha256": expected, "anchor_sha256": anchor_actual,
            "head_sha256": head_actual, "index_sha256": index_actual,
            "canonical_worktree_sha256": canonical_actual,
            "raw_worktree_sha256": raw_actual,
            "raw_matches_anchor": raw_actual == anchor_actual,
            "checkout_eol": raw_eol,
            "eol_normalization_applied": bool(
                raw_actual != canonical_actual and canonical_matches_manifest
            ),
            "index_mode": index_mode, "index_object_id": index_object_id,
            "canonical_worktree_object_id": canonical_object_id,
            "git_canonical_matches_index": canonical_object_id == index_object_id,
            "regular_file": regular_file,
            "unstaged_semantic_diff": unstaged_diff, "staged_diff": staged_diff,
            "status": status,
        })
    passed = not errors
    return {
        "status": "PASS" if passed else "FAIL",
        "repository_contract_version": REPOSITORY_CONTRACT_VERSION,
        "manifest_path": path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path),
        "spec_freeze_anchor_commit": anchor, "head_policy": manifest.get("head_policy"),
        "freeze_anchor_exists": anchor_exists, "current_head": head,
        "anchor_is_ancestor": anchor_is_ancestor,
        "immutable_payload_count": len(entries), "payload_drift_count": drift_count,
        "payloads": payloads, "mutable_maintenance_files": mutable, "errors": errors,
    }


def _resolve_ref(root_schema: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise ValueError(f"external schema reference is not allowed: {reference}")
    value: Any = root_schema
    for part in reference[2:].split("/"):
        value = value[part.replace("~1", "/").replace("~0", "~")]
    if not isinstance(value, dict):
        raise ValueError(f"schema reference is not an object: {reference}")
    return value


def _matches_type(value: Any, type_name: str) -> bool:
    checks = {
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
        "boolean": lambda item: isinstance(item, bool),
        "null": lambda item: item is None,
    }
    return checks[type_name](value)


def validate_json_instance(
    instance: Any,
    schema: dict[str, Any],
    *,
    root_schema: dict[str, Any] | None = None,
    path: str = "$",
) -> list[str]:
    """Validate the JSON-Schema subset used by the v1 sample contract."""
    root_schema = schema if root_schema is None else root_schema
    if "$ref" in schema:
        return validate_json_instance(
            instance, _resolve_ref(root_schema, schema["$ref"]), root_schema=root_schema, path=path
        )
    errors: list[str] = []
    expected = schema.get("type")
    if expected is not None:
        choices = expected if isinstance(expected, list) else [expected]
        if not any(_matches_type(instance, choice) for choice in choices):
            return [f"{path}: expected type {choices}, got {type(instance).__name__}"]
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: value does not equal const")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value is outside enum")
    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            errors.append(f"{path}: string is shorter than minLength")
        if "pattern" in schema and re.fullmatch(schema["pattern"], instance) is None:
            errors.append(f"{path}: string does not match pattern")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: value is below minimum")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: value is above maximum")
    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            errors.append(f"{path}: array is shorter than minItems")
        if "items" in schema:
            for index, item in enumerate(instance):
                errors.extend(
                    validate_json_instance(
                        item, schema["items"], root_schema=root_schema, path=f"{path}[{index}]"
                    )
                )
    if isinstance(instance, dict):
        properties = schema.get("properties", {})
        for required in schema.get("required", []):
            if required not in instance:
                errors.append(f"{path}: missing required field {required}")
        if schema.get("additionalProperties") is False:
            for name in instance:
                if name not in properties:
                    errors.append(f"{path}: unexpected field {name}")
        for name, value in instance.items():
            if name in properties:
                errors.extend(
                    validate_json_instance(
                        value, properties[name], root_schema=root_schema, path=f"{path}.{name}"
                    )
                )
    return errors


def make_schema_dummy(canonical: dict[str, Any]) -> dict[str, Any]:
    wavelength_grid_id = "wl_420_480_coarse_0p5_v1"
    angle_grid_id = "angle_air_signed_m60_p60_coarse_2_v1"
    provenance_hash = simulation_provenance_hash(
        physical_configuration_hash_value=canonical["physical_configuration_hash"],
        wavelength_grid_id=wavelength_grid_id,
        angle_grid_id=angle_grid_id,
        angle_convention_id="air_side_far_field_conserved_real_kx_v1",
        solver_id="TMM_static_dummy",
        solver_version="not_executed_static_contract",
        polarization_contract_id="TE_TM_separate_unpolarized_arithmetic_mean_v1",
        numerical_settings_contract_id="F0_TMM_static_contract_v1",
    )
    proxy_quad = {
        "tmm_apcd_ready_cone5_integral_proxy": None,
        "tmm_apcd_ready_cone10_integral_proxy": None,
        "tmm_apcd_ready_cone5_fraction_proxy": None,
        "tmm_apcd_ready_cone10_fraction_proxy": None,
    }
    return {
        "identity": {
            "sample_id": "STATIC_SCHEMA_DUMMY",
            "structure_id": "STRUCTURE_" + canonical["canonical_geometry_hash"][:16],
            "canonical_geometry_hash": canonical["canonical_geometry_hash"],
            "canonical_geometry_hash_version": canonical["canonical_geometry_hash_version"],
            "physical_configuration_hash": canonical["physical_configuration_hash"],
            "physical_configuration_hash_version": canonical["physical_configuration_hash_version"],
            "sequence_hash": canonical["sequence_hash"],
            "topology_family": canonical["topology_family"],
            "fidelity": "F0",
            "parent_id": None,
            "legacy_geometry_hashes": [canonical["p0a_legacy_physical_hash"]],
            "hash_lineage_note": "P0-A material-bound hash retained for lineage; canonical geometry v3 excludes provenance",
        },
        "geometry": {
            "source_medium": canonical["source_medium"],
            "exit_medium": canonical["exit_medium"],
            "material_tokens": canonical["material_tokens"],
            "thickness_nm": canonical["thickness_nm"],
            "layer_count": canonical["layer_count"],
            "total_thickness_nm": canonical["total_thickness_nm"],
            "defect_indices": canonical["defect_indices"],
            "defect_material": canonical["defect_material"],
            "defect_thickness_nm": canonical["defect_thickness_nm"],
            "termination": canonical["termination"],
            "left_count": canonical["left_layer_count_input"],
            "right_count": canonical["right_layer_count_input"],
            "chirp_parameters": canonical["chirp_parameters"],
        },
        "simulation": {
            "material_ids": {
                "source_medium": "APCD_GAN_NATIVE_M1",
                "H": "APCD_TIO2_NATIVE_M1",
                "L": "APCD_SIO2_NATIVE_M1",
                "exit_medium": "AIR",
            },
            "material_policy_id": MATERIAL_PROVENANCE["material_policy_id"],
            "material_policy_version": MATERIAL_PROVENANCE["material_policy_version"],
            "source_fsp_sha256": MATERIAL_PROVENANCE["source_fsp_sha256"],
            "gan_raw_table_sha256": MATERIAL_PROVENANCE["gan_raw_table_sha256"],
            "angle_convention_id": "air_side_far_field_conserved_real_kx_v1",
            "wavelength_grid_id": wavelength_grid_id,
            "angle_grid_id": angle_grid_id,
            "solver": "TMM",
            "solver_version": "not_executed_static_contract",
            "polarization_contract_id": "TE_TM_separate_unpolarized_arithmetic_mean_v1",
            "numerical_settings_contract_id": "F0_TMM_static_contract_v1",
            "provenance_commit": SPEC_SOURCE_FROZEN_COMMIT,
            "simulation_provenance_hash": provenance_hash,
            "simulation_provenance_hash_version": SIMULATION_PROVENANCE_HASH_VERSION,
            "quality_flags": {
                "status": "static_dummy_no_solver",
                "response_complete": False,
                "power_balance_checked": False,
                "usable_for_training": False,
                "failure_reason": None,
            },
        },
        "response_artifact": {
            "response_artifact_path": None,
            "response_artifact_format": None,
            "response_artifact_sha256": None,
            "wavelength_grid_id": wavelength_grid_id,
            "angle_grid_id": angle_grid_id,
            "array_shape": [],
            "array_dtype": None,
            "field_inventory": [],
            "git_allowed": False,
        },
        "labels": {
            "scalar_spectral_metrics": {
                "spectral_fwhm_normal_nm": None,
                "peak_wavelength_nm": None,
                "T450": None,
                "tmm_band_transmission_448_453_normal_proxy": None,
            },
            "scalar_angular_metrics": {
                "angular_fwhm_450_deg": None,
                "peak_angle_deg": None,
                "sidelobe_power": None,
            },
            "tmm_apcd_ready_proxies": {
                "contract_id": "tmm_apcd_ready_in_plane_proxy_v1",
                "TE": deepcopy(proxy_quad),
                "TM": deepcopy(proxy_quad),
                "unpolarized_derived": deepcopy(proxy_quad),
                "quality_status": "static_dummy_no_grid",
            },
            "tolerance_metrics": {
                "tolerance_parent_geometry_hash": None,
                "tolerance_mode": "nominal",
                "tolerance_seed": None,
                "tolerance_scenario_id": "nominal",
                "correlated_bias_H_nm": 0,
                "correlated_bias_L_nm": 0,
                "correlated_bias_defect_nm": 0,
                "local_jitter_max_nm": None,
                "tolerance_robustness_penalty_pm3": None,
                "robustness_worst_case": None,
                "robustness_quantile": None,
                "minimum_stable_window_nm": None,
            },
            "failure_mechanism": None,
        },
        "objective_activation": {
            "objective_activation_stage": "nominal_search",
            "nominal_primary_objectives": list(NOMINAL_PRIMARY_OBJECTIVES),
            "robust_primary_objectives": list(ROBUST_PRIMARY_OBJECTIVES),
            "required_labels_by_stage": list(NOMINAL_PRIMARY_OBJECTIVES),
            "pareto_stage": "nominal",
            "robustness_label_available": False,
            "robustness_evaluation_status": "not_evaluated",
        },
        "split": {
            "split_name": "train",
            "split_group_hash": canonical["split_group_hash"],
            "parent_split_group_hash": None,
            "ood_category": None,
            "inherits_parent_split": False,
        },
    }


def make_schema_tolerance_child_dummy(
    parent: dict[str, Any], child: dict[str, Any]
) -> dict[str, Any]:
    record = make_schema_dummy(child)
    record["identity"]["sample_id"] = "STATIC_SCHEMA_TOLERANCE_CHILD"
    record["identity"]["parent_id"] = "STRUCTURE_" + parent["canonical_geometry_hash"][:16]
    tolerance = record["labels"]["tolerance_metrics"]
    tolerance.update({
        "tolerance_parent_geometry_hash": parent["canonical_geometry_hash"],
        "tolerance_mode": "layer_local_integer_jitter_pm3",
        "tolerance_seed": 42,
        "tolerance_scenario_id": "static_child_single_layer_plus3",
        "local_jitter_max_nm": 3,
        "tolerance_robustness_penalty_pm3": 0.25,
    })
    record["objective_activation"].update({
        "objective_activation_stage": "post_nominal_shortlist_pm3_complete",
        "required_labels_by_stage": list(ROBUST_PRIMARY_OBJECTIVES),
        "pareto_stage": "robust_shortlist",
        "robustness_label_available": True,
        "robustness_evaluation_status": "complete",
    })
    record["split"].update({
        "split_group_hash": parent["split_group_hash"],
        "parent_split_group_hash": parent["split_group_hash"],
        "inherits_parent_split": True,
    })
    return record


def audit_spec(spec: dict[str, Any]) -> list[str]:
    required = {
        "spec_version", "material_policy", "angle_convention", "topology_grammar",
        "variable_bounds", "manufacturing_constraints", "response_grids",
        "objective_definitions", "power_gates", "fidelity_levels", "go_no_go_rules",
        "split_policy", "model_candidates", "active_learning_policy", "hash_contracts",
        "tolerance_contract", "apcd_ready_proxy_contract", "storage_contract",
    }
    errors = [f"missing spec section {name}" for name in sorted(required - set(spec))]
    if spec.get("spec_version") != "MDC_ML_INVERSE_DESIGN_SPEC_V1":
        errors.append("unexpected spec_version")
    if spec.get("source_frozen_commit") != SPEC_SOURCE_FROZEN_COMMIT:
        errors.append("source_frozen_commit does not match the requested baseline")
    families = spec.get("topology_grammar", {}).get("topology_families", [])
    if tuple(families) != TOPOLOGY_FAMILIES:
        errors.append("topology family inventory differs from the grammar implementation")
    hashes = spec.get("hash_contracts", {})
    expected_hash_versions = {
        "canonical_geometry_hash": CANONICAL_GEOMETRY_HASH_VERSION,
        "physical_configuration_hash": PHYSICAL_CONFIGURATION_HASH_VERSION,
        "simulation_provenance_hash": SIMULATION_PROVENANCE_HASH_VERSION,
        "split_group_hash": SPLIT_GROUP_HASH_VERSION,
    }
    for name, version in expected_hash_versions.items():
        if hashes.get(name, {}).get("id") != version:
            errors.append(f"hash contract {name} must use {version}")
    geometry_excludes = set(hashes.get("canonical_geometry_hash", {}).get("excludes", []))
    if not {"source_fsp_sha256", "material_raw_table_hashes", "wavelength_grid", "angle_grid", "solver", "tolerance_seed"}.issubset(geometry_excludes):
        errors.append("canonical geometry hash exclusions are incomplete")
    lineage = hashes.get("legacy_lineage", {})
    if lineage.get("frozen_historical_geometry_hash") != "c38694d6f162c04322ae8a87def91622d4fd4f272e4ec286e85acc978f74d888":
        errors.append("frozen historical geometry hash lineage is missing")
    if lineage.get("p0a_material_bound_hash") != "878c4c625432d1d3bcfb990b7e40038f129289e4eee1187b73738d6a25f8a221":
        errors.append("P0-A material-bound hash lineage is missing")
    objectives = spec.get("objective_definitions", {})
    nominal_fields = tuple(item["field"] for item in objectives.get("nominal_search_primary", []))
    robust_fields = tuple(item["field"] for item in objectives.get("robust_shortlist_primary", []))
    unique_fields = set(robust_fields)
    unique_fields.update(item["field"] for item in objectives.get("hard_constraints_or_gates", []))
    unique_fields.update(item["field"] for item in objectives.get("diagnostics_only", []))
    if objectives.get("inventory_count") != 14 or len(unique_fields) != 14:
        errors.append(f"objective inventory must contain exactly 14 unique fields, got {len(unique_fields)}")
    if nominal_fields != NOMINAL_PRIMARY_OBJECTIVES:
        errors.append("nominal Pareto must be the frozen 4D objective tuple")
    if robust_fields != ROBUST_PRIMARY_OBJECTIVES:
        errors.append("robust shortlist Pareto must be the frozen 5D objective tuple")
    if objectives.get("aggregation_policy") != "staged_pareto_no_single_arbitrary_score":
        errors.append("objective aggregation must use staged Pareto without a single score")
    activation = objectives.get("objective_activation_contract", {})
    if activation.get("missing_robustness_label_behavior") != "ineligible_for_robust_pareto_never_zero_or_imputed":
        errors.append("missing robustness labels must make candidates ineligible for robust Pareto")
    if activation.get("first_nominal_surrogate_requires_robustness_prediction") is not False:
        errors.append("first nominal surrogate must not require a robustness label")
    serialized = json.dumps(spec, ensure_ascii=False).lower()
    if "significant" in serialized or "显著改善" in serialized:
        errors.append("ambiguous improvement language remains in the executable contract")
    tolerance = spec.get("tolerance_contract", {})
    expected_tolerance_fields = {
        "tolerance_parent_geometry_hash", "tolerance_mode", "tolerance_seed",
        "tolerance_scenario_id", "correlated_bias_H_nm", "correlated_bias_L_nm",
        "correlated_bias_defect_nm", "local_jitter_max_nm", "robustness_worst_case",
        "tolerance_robustness_penalty_pm3", "robustness_quantile", "minimum_stable_window_nm",
    }
    if set(tolerance.get("required_fields", [])) != expected_tolerance_fields:
        errors.append("tolerance required-field inventory is not exact")
    correlated = tolerance.get("correlated_material_deposition_bias", {})
    if any(correlated.get(name) != [-3, 0, 3] for name in ("delta_H_nm", "delta_L_nm", "delta_defect_nm")):
        errors.append("correlated +/-3 nm tolerance lattice is incomplete")
    local = tolerance.get("layer_local_integer_jitter", {})
    if local.get("local_jitter_max_nm") != 3 or local.get("fixed_seed_required") is not True:
        errors.append("local +/-3 nm tolerance mode must be integer and fixed-seed")
    if tolerance.get("strong_candidate_pm5", {}).get("scope") != "final_few_candidates_only_not_all_pilot":
        errors.append("+/-5 nm tolerance must remain final-candidate-only")
    proxy = spec.get("apcd_ready_proxy_contract", {})
    proxy_fields = {
        "tmm_apcd_ready_cone5_integral_proxy", "tmm_apcd_ready_cone10_integral_proxy",
        "tmm_apcd_ready_cone5_fraction_proxy", "tmm_apcd_ready_cone10_fraction_proxy",
    }
    if set(proxy.get("fields", [])) != proxy_fields:
        errors.append("APCD-ready proxy field inventory is incomplete")
    if proxy.get("angular_quadrature") != "composite_trapezoidal_after_degrees_to_radians":
        errors.append("APCD-ready angular quadrature must integrate radians")
    if "no_sin_theta" not in proxy.get("angular_weighting", ""):
        errors.append("in-plane angular weighting must explicitly reject a solid-angle claim")
    if "return_null" not in proxy.get("missing_grid_behavior", ""):
        errors.append("missing APCD-ready grid behavior must return null with a quality flag")
    storage = spec.get("storage_contract", {}).get("external_response_array_artifact", {})
    expected_artifact_fields = {
        "response_artifact_path", "response_artifact_format", "response_artifact_sha256",
        "wavelength_grid_id", "angle_grid_id", "array_shape", "array_dtype", "field_inventory",
    }
    if set(storage.get("required_fields", [])) != expected_artifact_fields:
        errors.append("external response artifact reference is incomplete")
    if set(storage.get("allowed_formats", [])) != {"NPZ", "HDF5"}:
        errors.append("external response arrays must use NPZ or HDF5")
    if storage.get("git_allowed") is not False or storage.get("inline_in_sample_json_allowed") is not False:
        errors.append("large/complete response arrays must remain external and outside Git")
    baseline_gate = spec.get("go_no_go_rules", {}).get("baseline_relative_threshold", {})
    if baseline_gate.get("status") != "pending_f0_baseline_recompute" or baseline_gate.get("executable_gate") is not False:
        errors.append("baseline-relative gate must remain non-executable until an F0 recompute")
    materials = spec.get("material_policy", {})
    material_field_map = {
        "material_policy_id": "policy_id",
        "material_policy_version": "policy_version",
        "source_material_id": "source_medium",
        "H_material_id": "H",
        "L_material_id": "L",
        "exit_material_id": "exit_medium",
    }
    for name, expected in MATERIAL_PROVENANCE.items():
        spec_name = material_field_map.get(name, name)
        if materials.get(spec_name) != expected:
            errors.append(f"material provenance mismatch for {spec_name}")
    gates = spec.get("power_gates", {})
    if [gates.get(name, {}).get("minimum") for name in ("exploratory", "viable", "strong")] != [0.2, 0.5, 0.7]:
        errors.append("power gate thresholds differ from 0.2/0.5/0.7")
    scope = spec.get("scope_guards", {})
    if any(scope.get(name) is not False for name in ("solver_runs_allowed", "model_training_allowed", "large_dataset_generation_allowed", "level_b_generation_allowed")):
        errors.append("v1 scope guard permits a forbidden action")
    return errors


def audit_schema_inventory(schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_groups = {"identity", "geometry", "simulation", "response_artifact", "labels", "objective_activation", "split"}
    if set(schema.get("required", [])) != required_groups:
        errors.append("schema top-level required groups are incomplete")
    required_fields = {
        "identity": {"sample_id", "structure_id", "canonical_geometry_hash", "canonical_geometry_hash_version", "physical_configuration_hash", "physical_configuration_hash_version", "sequence_hash", "topology_family", "fidelity", "parent_id", "legacy_geometry_hashes", "hash_lineage_note"},
        "geometry": {"source_medium", "exit_medium", "material_tokens", "thickness_nm", "layer_count", "total_thickness_nm", "defect_indices", "defect_material", "defect_thickness_nm", "termination", "left_count", "right_count", "chirp_parameters"},
        "simulation": {"material_ids", "material_policy_id", "material_policy_version", "source_fsp_sha256", "gan_raw_table_sha256", "angle_convention_id", "wavelength_grid_id", "angle_grid_id", "solver", "solver_version", "polarization_contract_id", "numerical_settings_contract_id", "provenance_commit", "simulation_provenance_hash", "simulation_provenance_hash_version", "quality_flags"},
        "response_artifact": {"response_artifact_path", "response_artifact_format", "response_artifact_sha256", "wavelength_grid_id", "angle_grid_id", "array_shape", "array_dtype", "field_inventory", "git_allowed"},
        "labels": {"scalar_spectral_metrics", "scalar_angular_metrics", "tmm_apcd_ready_proxies", "tolerance_metrics", "failure_mechanism"},
        "objective_activation": {"objective_activation_stage", "nominal_primary_objectives", "robust_primary_objectives", "required_labels_by_stage", "pareto_stage", "robustness_label_available", "robustness_evaluation_status"},
        "split": {"split_name", "split_group_hash", "parent_split_group_hash", "ood_category", "inherits_parent_split"},
    }
    for group, names in required_fields.items():
        actual = set(schema.get("properties", {}).get(group, {}).get("required", []))
        if not names.issubset(actual):
            errors.append(f"schema {group} missing required fields {sorted(names - actual)}")
    return errors


def baseline_roundtrip_audit() -> dict[str, Any]:
    searched = [
        str(BASELINE_SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "outputs/mdc_p1_asymmetric_scan_static_v1/p1_seed_resolution.json",
        "outputs/mdc_native_m1_zl1_alternative_tolerance/run_manifest.json",
    ]
    if not BASELINE_SOURCE.exists():
        return {"status": "BLOCKED", "blocker": "authoritative baseline row is unavailable", "searched_locations": searched}
    with BASELINE_SOURCE.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    row = next((item for item in rows if item.get("static_structure_id") == BASELINE_ID), None)
    if row is None:
        return {"status": "BLOCKED", "blocker": f"authoritative row {BASELINE_ID} is unavailable", "searched_locations": searched}
    tokens = []
    for item in row["sequence_GaN_to_Air"].split():
        match = re.fullmatch(r"([HL])(\d+)", item)
        if match is None:
            return {"status": "BLOCKED", "blocker": f"unparseable authoritative token {item}", "searched_locations": searched}
        tokens.append({"material_token": match.group(1), "thickness_nm": int(match.group(2))})
    defect_candidates = [index for index, layer in enumerate(tokens) if layer["material_token"] == "L" and layer["thickness_nm"] > DEFAULT_BOUNDS["L"][1]]
    if len(defect_candidates) != 1:
        return {"status": "BLOCKED", "blocker": f"expected one explicit defect token, found {len(defect_candidates)}", "searched_locations": searched}
    defect_index = defect_candidates[0]
    candidate = {
        "sample_id": BASELINE_ID,
        "topology_family": "off_center_defect",
        "left_mirror": tokens[:defect_index],
        "defect_region": [tokens[defect_index]],
        "right_mirror": tokens[defect_index + 1:],
        "parameters": {
            "source_topology_family": row["topology"],
            "defect_offset_layers": len(tokens[:defect_index]) - len(tokens[defect_index + 1:]),
        },
    }
    encoded = validate_bounds(candidate)
    decoded = decode_canonical_structure(encoded)
    reencoded = validate_bounds(decoded)
    source_pairs = [[item["material_token"], item["thickness_nm"]] for item in tokens]
    encoded_pairs = [[item["material_token"], item["thickness_nm"]] for item in encoded["layers"]]
    errors = []
    if source_pairs != encoded_pairs:
        errors.append("authoritative layer sequence differs after encoding")
    if encoded_pairs != [[item["material_token"], item["thickness_nm"]] for item in reencoded["layers"]]:
        errors.append("layer sequence differs after decode/re-encode")
    if encoded["canonical_geometry_hash"] != reencoded["canonical_geometry_hash"]:
        errors.append("canonical geometry hash differs after decode/re-encode")
    if encoded["physical_configuration_hash"] != reencoded["physical_configuration_hash"]:
        errors.append("physical configuration hash differs after decode/re-encode")
    if encoded["split_group_hash"] != reencoded["split_group_hash"]:
        errors.append("split group hash differs after decode/re-encode")
    if encoded["sequence_hash"] != reencoded["sequence_hash"]:
        errors.append("sequence hash differs after decode/re-encode")
    if encoded["layer_count"] != int(row["layer_count"]) or encoded["total_thickness_nm"] != int(row["total_thickness_nm"]):
        errors.append("authoritative layer count or total thickness differs")
    if encoded["p0a_legacy_physical_hash"] != "878c4c625432d1d3bcfb990b7e40038f129289e4eee1187b73738d6a25f8a221":
        errors.append("P0-A material-bound hash lineage is not reproducible")
    simulation_example_hash = simulation_provenance_hash(
        physical_configuration_hash_value=encoded["physical_configuration_hash"],
        wavelength_grid_id="wl_420_480_coarse_0p5_v1",
        angle_grid_id="angle_air_signed_m60_p60_coarse_2_v1",
        angle_convention_id="air_side_far_field_conserved_real_kx_v1",
        solver_id="TMM_static_identity_example",
        solver_version="not_executed_static_contract",
        polarization_contract_id="TE_TM_separate_unpolarized_arithmetic_mean_v1",
        numerical_settings_contract_id="F0_TMM_static_contract_v1",
    )
    return {
        "status": "PASS" if not errors else "FAIL",
        "blocker": None,
        "errors": errors,
        "authoritative_source": searched[0] + "#" + BASELINE_ID,
        "source_medium": "APCD_GAN_NATIVE_M1",
        "exit_medium": "AIR",
        "source_topology_family": row["topology"],
        "grammar_topology_family": encoded["topology_family"],
        "ordered_material_ids": [MATERIAL_PROVENANCE["H_material_id"] if item["material_token"] == "H" else MATERIAL_PROVENANCE["L_material_id"] for item in tokens],
        "ordered_thickness_nm": [item["thickness_nm"] for item in tokens],
        "layer_count": encoded["layer_count"],
        "total_thickness_nm": encoded["total_thickness_nm"],
        "defect_indices_zero_based": encoded["defect_indices"],
        "termination": encoded["termination"],
        "frozen_legacy_sequence_hash": row["canonical_sequence_hash"],
        "frozen_legacy_geometry_hash": row["geometry_hash"],
        "p0_sequence_hash": encoded["sequence_hash"],
        "p0a_material_bound_hash_contract": "mdc_physical_geometry_hash_v2",
        "p0a_material_bound_hash": encoded["p0a_legacy_physical_hash"],
        "canonical_geometry_hash_version": encoded["canonical_geometry_hash_version"],
        "canonical_geometry_hash": encoded["canonical_geometry_hash"],
        "physical_configuration_hash_version": encoded["physical_configuration_hash_version"],
        "physical_configuration_hash": encoded["physical_configuration_hash"],
        "simulation_provenance_hash_version": SIMULATION_PROVENANCE_HASH_VERSION,
        "simulation_provenance_example_hash": simulation_example_hash,
        "split_group_hash_version": SPLIT_GROUP_HASH_VERSION,
        "split_group_hash": encoded["split_group_hash"],
        "legacy_geometry_hashes": [
            row["geometry_hash"],
            encoded["p0a_legacy_physical_hash"],
        ],
        "hash_lineage_note": "c386 is the frozen historical geometry hash; 878c is the P0-A material-bound hash and is not the pure v3 geometry identity",
        "roundtrip_sequence_hash": reencoded["sequence_hash"],
        "roundtrip_canonical_geometry_hash": reencoded["canonical_geometry_hash"],
        "roundtrip_physical_configuration_hash": reencoded["physical_configuration_hash"],
        "roundtrip_split_group_hash": reencoded["split_group_hash"],
        "layer_by_layer_equality": source_pairs == encoded_pairs,
        "roundtrip_hash_equality": all((
            encoded["canonical_geometry_hash"] == reencoded["canonical_geometry_hash"],
            encoded["physical_configuration_hash"] == reencoded["physical_configuration_hash"],
            encoded["split_group_hash"] == reencoded["split_group_hash"],
        )),
        "searched_locations": searched,
    }


def _simulation_hash(
    physical_hash: str, *, wavelength_grid_id: str = "wl_A", angle_grid_id: str = "angle_A"
) -> str:
    return simulation_provenance_hash(
        physical_configuration_hash_value=physical_hash,
        wavelength_grid_id=wavelength_grid_id,
        angle_grid_id=angle_grid_id,
        angle_convention_id="air_side_far_field_conserved_real_kx_v1",
        solver_id="TMM_static_identity_test",
        solver_version="not_executed_static_contract",
        polarization_contract_id="TE_TM_separate_unpolarized_arithmetic_mean_v1",
        numerical_settings_contract_id="F0_TMM_static_contract_v1",
    )


def hash_behavior_audit(canonical: dict[str, Any]) -> dict[str, Any]:
    geometry = canonical["canonical_geometry_hash"]
    physical = canonical["physical_configuration_hash"]
    split_hash = canonical["split_group_hash"]
    base_simulation = _simulation_hash(physical)
    wavelength_simulation = _simulation_hash(physical, wavelength_grid_id="wl_B")
    angle_simulation = _simulation_hash(physical, angle_grid_id="angle_B")

    changed_material = deepcopy(MATERIAL_PROVENANCE)
    changed_material["gan_raw_table_sha256"] = "0" * 64
    changed_physical = physical_configuration_hash(
        geometry, material_provenance=changed_material
    )
    changed_material_simulation = _simulation_hash(changed_physical)

    child_input = decode_canonical_structure(canonical)
    child_input["defect_region"][0]["thickness_nm"] += 3
    child = validate_bounds(child_input)
    child_inherited_split = split_group_hash(geometry)
    mirror_reference = validate_bounds(generate_dummy_candidates()[1])
    reversed_geometry = geometry_hash(reversed(mirror_reference["layers"]))
    repeated = validate_bounds(decode_canonical_structure(canonical))

    cases = {
        "wavelength_grid_change": {
            "canonical_geometry_unchanged": canonical["canonical_geometry_hash"] == geometry,
            "physical_configuration_unchanged": canonical["physical_configuration_hash"] == physical,
            "simulation_provenance_changed": wavelength_simulation != base_simulation,
            "split_group_unchanged": canonical["split_group_hash"] == split_hash,
        },
        "angle_grid_change": {
            "canonical_geometry_unchanged": canonical["canonical_geometry_hash"] == geometry,
            "physical_configuration_unchanged": canonical["physical_configuration_hash"] == physical,
            "simulation_provenance_changed": angle_simulation != base_simulation,
            "split_group_unchanged": canonical["split_group_hash"] == split_hash,
        },
        "gan_raw_table_change": {
            "canonical_geometry_unchanged": canonical["canonical_geometry_hash"] == geometry,
            "physical_configuration_changed": changed_physical != physical,
            "simulation_provenance_changed": changed_material_simulation != base_simulation,
            "split_group_unchanged": split_group_hash(geometry) == split_hash,
        },
        "single_layer_pm3_tolerance_child": {
            "child_canonical_geometry_changed": child["canonical_geometry_hash"] != geometry,
            "child_physical_configuration_changed": child["physical_configuration_hash"] != physical,
            "child_split_group_inherits_parent": child_inherited_split == split_hash,
            "child_default_geometry_group_is_not_used": child["split_group_hash"] != split_hash,
        },
        "mirror_reversal": {
            "canonical_geometry_changed": reversed_geometry != mirror_reference["canonical_geometry_hash"],
            "identity_not_equal": reversed_geometry != mirror_reference["canonical_geometry_hash"],
        },
        "repeat_roundtrip": {
            "canonical_geometry_stable": repeated["canonical_geometry_hash"] == geometry,
            "physical_configuration_stable": repeated["physical_configuration_hash"] == physical,
            "split_group_stable": repeated["split_group_hash"] == split_hash,
            "layer_by_layer_equality": repeated["layers"] == canonical["layers"],
        },
    }
    errors = [
        f"{case}.{name} is false"
        for case, outcomes in cases.items()
        for name, passed in outcomes.items()
        if passed is not True
    ]
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "hash_versions": {
            "canonical_geometry_hash": CANONICAL_GEOMETRY_HASH_VERSION,
            "physical_configuration_hash": PHYSICAL_CONFIGURATION_HASH_VERSION,
            "simulation_provenance_hash": SIMULATION_PROVENANCE_HASH_VERSION,
            "split_group_hash": SPLIT_GROUP_HASH_VERSION,
        },
        "cases": cases,
    }


def objective_activation_audit() -> dict[str, Any]:
    errors: list[str] = []
    nominal = resolve_primary_objectives(
        pareto_stage="nominal",
        robustness_label_available=False,
        robustness_evaluation_status="not_evaluated",
        tolerance_robustness_penalty_pm3=None,
    )
    if nominal != NOMINAL_PRIMARY_OBJECTIVES:
        errors.append("nominal stage did not resolve to the 4D objective tuple")
    missing_robust_rejected = False
    try:
        resolve_primary_objectives(
            pareto_stage="robust_shortlist",
            robustness_label_available=False,
            robustness_evaluation_status="not_evaluated",
            tolerance_robustness_penalty_pm3=None,
        )
    except GrammarError:
        missing_robust_rejected = True
    if not missing_robust_rejected:
        errors.append("missing robustness label was admitted to robust Pareto")
    robust = resolve_primary_objectives(
        pareto_stage="robust_shortlist",
        robustness_label_available=True,
        robustness_evaluation_status="complete",
        tolerance_robustness_penalty_pm3=0.25,
    )
    if robust != ROBUST_PRIMARY_OBJECTIVES:
        errors.append("completed robust stage did not resolve to the 5D objective tuple")
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "nominal_pareto_dimension": len(nominal),
        "nominal_primary_objectives": list(nominal),
        "robust_pareto_dimension": len(robust),
        "robust_primary_objectives": list(robust),
        "missing_robustness_label_rejected": missing_robust_rejected,
        "first_nominal_surrogate_requires_robustness_prediction": False,
    }


def audit_material_and_hash_provenance(canonical: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not MATERIAL_POLICY_SOURCE.exists():
        return ["canonical material policy source is unavailable"]
    policy = json.loads(MATERIAL_POLICY_SOURCE.read_text(encoding="utf-8-sig"))
    serialized = json.dumps(policy, sort_keys=True)
    policy_owned_fields = (
        "material_policy_id", "material_policy_version", "source_material_id",
        "H_material_id", "L_material_id", "source_fsp_sha256", "gan_raw_table_sha256",
    )
    for expected in (MATERIAL_PROVENANCE[name] for name in policy_owned_fields):
        if str(expected) not in serialized:
            errors.append(f"canonical material policy does not contain {expected}")
    errors.extend(hash_behavior_audit(canonical)["errors"])
    return errors


def run_audit(
    *,
    verify_repository_contract: bool = True,
    verify_head: bool | None = None,
) -> dict[str, Any]:
    """Run the formal audit.

    ``verify_head`` is a compatibility alias for ``verify_repository_contract``.
    When true it means anchor ancestry plus immutable-payload verification; it
    never means exact equality between HEAD and a fixed commit.
    """
    if verify_head is not None:
        verify_repository_contract = verify_head
    spec = load_spec()
    schema = load_schema()
    candidates = generate_dummy_candidates()
    canonicals = [validate_bounds(candidate) for candidate in candidates]
    checks: list[dict[str, Any]] = []

    def add(name: str, errors: list[str]) -> None:
        checks.append({"name": name, "pass": not errors, "details": errors or ["PASS"]})

    add("spec_contract", audit_spec(spec))
    add("dataset_schema_inventory", audit_schema_inventory(schema))
    schema_errors = []
    for index, canonical in enumerate(canonicals):
        schema_errors.extend(f"dummy[{index}] {error}" for error in validate_json_instance(make_schema_dummy(canonical), schema))
    add("dataset_schema_all_dummy_instances", schema_errors)
    child_input = decode_canonical_structure(canonicals[0])
    child_input["defect_region"][0]["thickness_nm"] += 3
    tolerance_child = validate_bounds(child_input)
    add(
        "dataset_schema_tolerance_child_instance",
        validate_json_instance(
            make_schema_tolerance_child_dummy(canonicals[0], tolerance_child), schema
        ),
    )
    baseline = baseline_roundtrip_audit()
    add("authoritative_baseline_roundtrip", [] if baseline["status"] == "PASS" else baseline.get("errors", []) or [baseline.get("blocker", "baseline audit failed")])
    add(
        "topology_coverage",
        [] if set(TOPOLOGY_FAMILIES).issubset({item["topology_family"] for item in canonicals}) else ["one or more topology families are absent"],
    )
    add("dummy_structure_limit", [] if len(candidates) <= 100 else [f"generated {len(candidates)} structures"])
    by_id = {candidate["sample_id"]: canonical for candidate, canonical in zip(candidates, canonicals)}
    reachability_errors = []
    for sample_id, expected_count, expected_total in (
        ("DUMMY_REACHABLE_MIN_9_LAYERS_500_NM", 9, 500),
        ("DUMMY_REACHABLE_MAX_25_LAYERS_2200_NM", 25, 2200),
    ):
        item = by_id.get(sample_id)
        if item is None or item["layer_count"] != expected_count or item["total_thickness_nm"] != expected_total:
            reachability_errors.append(f"{sample_id} does not reach ({expected_count}, {expected_total})")
    add("exact_layer_and_total_boundary_reachability", reachability_errors)
    add("material_and_hash_provenance", audit_material_and_hash_provenance(canonicals[0]))
    activation_audit = objective_activation_audit()
    add("staged_objective_activation", activation_audit["errors"])
    split_records = [
        {
            "canonical_geometry_hash": item["canonical_geometry_hash"],
            "split_group_hash": item["split_group_hash"],
            "structure_id": "STRUCTURE_" + item["canonical_geometry_hash"][:16],
            "parent_split_group_hash": item["split_group_hash"],
            "split_name": "train",
        }
        for item in canonicals
    ]
    add("split_leakage_static_control", audit_split_leakage(split_records))
    repository_contract = (
        audit_repository_freeze_contract()
        if verify_repository_contract
        else {
            "status": "SKIPPED", "repository_contract_version": REPOSITORY_CONTRACT_VERSION,
            "spec_freeze_anchor_commit": SPEC_FREEZE_ANCHOR_COMMIT,
            "current_head": git_head(), "freeze_anchor_exists": None,
            "anchor_is_ancestor": None, "immutable_payload_count": 0,
            "payload_drift_count": 0, "payloads": [], "errors": [],
        }
    )
    if verify_repository_contract:
        add("repository_freeze_contract", repository_contract["errors"])
    passed = all(check["pass"] for check in checks)
    return {
        "status": "PASS" if passed else "FAIL",
        "spec_version": spec["spec_version"],
        "source_frozen_commit": spec["source_frozen_commit"],
        "checks": checks,
        "static_dummy_structure_count": len(candidates),
        "nominal_primary_objective_count": len(spec["objective_definitions"]["nominal_search_primary"]),
        "robust_primary_objective_count": len(spec["objective_definitions"]["robust_shortlist_primary"]),
        "hash_behavior_status": hash_behavior_audit(canonicals[0])["status"],
        "objective_activation_status": activation_audit["status"],
        "f0_pilot_contract_ready": passed,
        "authoritative_baseline_roundtrip_status": baseline["status"],
        "repository_contract": repository_contract,
        "repository_contract_status": repository_contract["status"],
        "spec_freeze_anchor_commit": repository_contract["spec_freeze_anchor_commit"],
        "current_head": repository_contract["current_head"],
        "freeze_anchor_exists": repository_contract["freeze_anchor_exists"],
        "anchor_is_ancestor": repository_contract["anchor_is_ancestor"],
        "immutable_payload_count": repository_contract["immutable_payload_count"],
        "payload_drift_count": repository_contract["payload_drift_count"],
        "solver_calls": 0,
        "model_training_runs": 0,
        "level_b_structures_generated": 0,
    }


def _topology_rows(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for candidate in candidates:
        canonical = validate_bounds(candidate)
        rows.append(
            {
                "sample_id": candidate["sample_id"],
                "structure_id": "STRUCTURE_" + canonical["canonical_geometry_hash"][:16],
                "topology_family": canonical["topology_family"],
                "material_tokens": json.dumps(canonical["material_tokens"], separators=(",", ":")),
                "thickness_nm": json.dumps(canonical["thickness_nm"], separators=(",", ":")),
                "layer_count": canonical["layer_count"],
                "total_thickness_nm": canonical["total_thickness_nm"],
                "defect_indices": json.dumps(canonical["defect_indices"], separators=(",", ":")),
                "defect_count": canonical["defect_count"],
                "gan_termination": canonical["termination"]["gan_side"],
                "air_termination": canonical["termination"]["air_side"],
                "left_count": canonical["left_layer_count_input"],
                "right_count": canonical["right_layer_count_input"],
                "chirp_parameters": json.dumps(canonical["chirp_parameters"], sort_keys=True, separators=(",", ":")),
                "sequence_hash": canonical["sequence_hash"],
                "canonical_geometry_hash": canonical["canonical_geometry_hash"],
                "canonical_geometry_hash_version": canonical["canonical_geometry_hash_version"],
                "physical_configuration_hash": canonical["physical_configuration_hash"],
                "physical_configuration_hash_version": canonical["physical_configuration_hash_version"],
                "split_group_hash": canonical["split_group_hash"],
                "validation_status": "PASS",
                "data_role": "static_dummy_no_solver",
            }
        )
    return rows


def _canonicalization_rows(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merge_case = {
        "sample_id": "CANON_MERGE_ACROSS_REGIONS",
        "topology_family": "symmetric_periodic",
        "left_mirror": [
            {"material_token": "H", "thickness_nm": 45},
            {"material_token": "L", "thickness_nm": 79},
            {"material_token": "H", "thickness_nm": 45},
        ],
        "defect_region": [{"material_token": "H", "thickness_nm": 120}],
        "right_mirror": [
            {"material_token": "H", "thickness_nm": 45},
            {"material_token": "L", "thickness_nm": 79},
            {"material_token": "H", "thickness_nm": 45},
        ],
        "parameters": {},
    }
    cases = [merge_case, candidates[0], candidates[5]]
    rows = []
    for case in cases:
        before = [
            [layer["material_token"], layer["thickness_nm"]]
            for region in ("left_mirror", "defect_region", "right_mirror")
            for layer in case[region]
        ]
        canonical = canonicalize_structure(case)
        after = [[layer["material_token"], layer["thickness_nm"]] for layer in canonical["layers"]]
        rows.append(
            {
                "example_id": case["sample_id"],
                "input_sequence": json.dumps(before, separators=(",", ":")),
                "canonical_sequence": json.dumps(after, separators=(",", ":")),
                "input_layer_count": len(before),
                "canonical_layer_count": canonical["layer_count"],
                "adjacent_merges": len(before) - canonical["layer_count"],
                "canonical_defect_indices": json.dumps(canonical["defect_indices"], separators=(",", ":")),
                "sequence_hash": canonical["sequence_hash"],
                "canonical_geometry_hash": canonical["canonical_geometry_hash"],
                "physical_configuration_hash": canonical["physical_configuration_hash"],
                "split_group_hash": canonical["split_group_hash"],
            }
        )
    return rows


def _invalid_rows(base: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[tuple[str, dict[str, Any], str]] = []

    def altered(name: str, edit: Any, expected: str) -> None:
        case = deepcopy(base)
        edit(case)
        cases.append((name, case, expected))

    altered("NON_INTEGER_NM", lambda c: c["left_mirror"][0].update(thickness_nm=45.5), "integer nm")
    altered("ZERO_THICKNESS", lambda c: c["left_mirror"][0].update(thickness_nm=0), "positive thickness")
    altered("ILLEGAL_TOKEN", lambda c: c["left_mirror"][0].update(material_token="X"), "H/L token")
    altered("REPEATED_MIRROR_TOKEN", lambda c: c["left_mirror"][1].update(material_token="H"), "mirror alternation")
    altered("DEFECT_TOO_THIN", lambda c: c["defect_region"][0].update(thickness_nm=119), "defect lower bound")
    altered("TOTAL_TOO_THICK", lambda c: c["defect_region"][0].update(thickness_nm=900), "total/defect upper bound")
    altered("LAYER_COUNT_TOO_LOW", lambda c: (c.update(left_mirror=c["left_mirror"][:2]), c.update(right_mirror=c["right_mirror"][-2:])), "layer count lower bound")
    altered("BAD_SYMMETRY", lambda c: c["right_mirror"][0].update(thickness_nm=80), "symmetric reversal rule")
    rows: list[dict[str, Any]] = []
    for name, case, expected in cases:
        message = "unexpectedly valid"
        try:
            validate_bounds(case)
        except (GrammarError, ValueError) as exc:
            message = str(exc)
        rows.append(
            {
                "example_id": name,
                "expected_failure": expected,
                "observed_error": message,
                "input_structure": json.dumps(case, sort_keys=True, separators=(",", ":")),
                "validation_status": "EXPECTED_FAIL" if message != "unexpectedly valid" else "UNEXPECTED_PASS",
            }
        )
    return rows


def _objective_rows(spec: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    categories = (
        "nominal_search_primary", "robust_shortlist_primary",
        "hard_constraints_or_gates", "diagnostics_only",
    )
    for category in categories:
        for order, objective in enumerate(spec["objective_definitions"][category], start=1):
            rows.append(
                {
                    "category": category,
                    "category_order": order,
                    "field": objective["field"],
                    "direction": objective.get("direction", "diagnostic_only"),
                    "unit": objective.get("unit", "defined_by_f0_screening_config"),
                    "threshold": objective.get("threshold", objective.get("threshold_status", "")),
                    "meaning": objective.get("meaning", ""),
                    "aggregation": "staged_Pareto" if category in {"nominal_search_primary", "robust_shortlist_primary"} else "not_aggregated_as_primary",
                }
            )
    return rows


def _schema_inventory_rows(schema: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for group in ("identity", "geometry", "simulation", "response_artifact", "labels", "objective_activation", "split"):
        group_schema = schema["properties"][group]
        required = set(group_schema.get("required", []))
        for field, field_schema in group_schema.get("properties", {}).items():
            rows.append(
                {
                    "group": group,
                    "field": field,
                    "required": str(field in required).lower(),
                    "type": json.dumps(field_schema.get("type", "$ref"), separators=(",", ":")),
                    "reference": field_schema.get("$ref", ""),
                    "description": field_schema.get("description", ""),
                }
            )
    return rows


def _coverage(canonicals: list[dict[str, Any]]) -> dict[str, Any]:
    regular_h = []
    regular_l = []
    defects = []
    for canonical in canonicals:
        defect_indices = set(canonical["defect_indices"])
        for index, layer in enumerate(canonical["layers"]):
            if index in defect_indices:
                defects.append(layer["thickness_nm"])
            elif layer["material_token"] == "H":
                regular_h.append(layer["thickness_nm"])
            else:
                regular_l.append(layer["thickness_nm"])
    observed = {
        "H": [min(regular_h), max(regular_h)],
        "L": [min(regular_l), max(regular_l)],
        "defect": [min(defects), max(defects)],
        "layer_count": [min(item["layer_count"] for item in canonicals), max(item["layer_count"] for item in canonicals)],
        "total_thickness_nm": [min(item["total_thickness_nm"] for item in canonicals), max(item["total_thickness_nm"] for item in canonicals)],
    }
    return {
        "audit_status": "PASS",
        "proposal_status": "v1_static_coverage_proposal_not_final_manufacturing_limits",
        "dummy_structure_count": len(canonicals),
        "dummy_structure_limit": 100,
        "topology_families_required": list(TOPOLOGY_FAMILIES),
        "topology_families_observed": sorted({item["topology_family"] for item in canonicals}),
        "bounds": {name: list(value) for name, value in DEFAULT_BOUNDS.items()},
        "observed_ranges": observed,
        "exact_boundary_hits": {
            name: observed[name] == list(DEFAULT_BOUNDS[name]) for name in DEFAULT_BOUNDS
        },
        "coverage_limitations": [
            "Static dummy examples prove grammar and boundary handling, not optical performance.",
            "Exact layer-count and total-thickness endpoints are reachable controls, not sampled distributions.",
            "Manufacturing limits remain proposals pending fabrication review."
        ],
        "solver_calls": 0,
        "level_b_structures_generated": 0,
    }


def _file_state(directory: Path) -> dict[str, str]:
    names = [*STATIC_FILES, "manifest.json"]
    return {name: sha256(directory / name) for name in names if (directory / name).exists()}


def build_static_examples(output_dir: Path = OUTPUT_DIR) -> dict[str, Any]:
    previous = _file_state(output_dir)
    audit = run_audit()
    if audit["status"] != "PASS":
        raise RuntimeError(json.dumps(audit, ensure_ascii=False))
    spec = load_spec()
    schema = load_schema()
    candidates = generate_dummy_candidates()
    canonicals = [validate_bounds(candidate) for candidate in candidates]
    topology_rows = _topology_rows(candidates)
    canonicalization_rows = _canonicalization_rows(candidates)
    invalid_rows = _invalid_rows(candidates[0])
    objective_rows = _objective_rows(spec)
    inventory_rows = _schema_inventory_rows(schema)
    baseline = baseline_roundtrip_audit()
    hash_audit = hash_behavior_audit(canonicals[0])
    activation_audit = objective_activation_audit()
    p0_contract = {
        "status": audit["status"],
        "spec_version": spec["spec_version"],
        "source_frozen_commit": spec["source_frozen_commit"],
        "authoritative_baseline_roundtrip_status": baseline["status"],
        "nominal_primary_objective_count": len(NOMINAL_PRIMARY_OBJECTIVES),
        "nominal_primary_objectives": list(NOMINAL_PRIMARY_OBJECTIVES),
        "robust_primary_objective_count": len(ROBUST_PRIMARY_OBJECTIVES),
        "robust_primary_objectives": list(ROBUST_PRIMARY_OBJECTIVES),
        "classified_objective_count": 14,
        "tolerance_modes": [
            spec["tolerance_contract"]["correlated_material_deposition_bias"]["mode"],
            spec["tolerance_contract"]["layer_local_integer_jitter"]["mode"],
            spec["tolerance_contract"]["strong_candidate_pm5"]["mode"],
        ],
        "apcd_ready_proxy_contract_id": spec["apcd_ready_proxy_contract"]["id"],
        "apcd_ready_proxy_fields": spec["apcd_ready_proxy_contract"]["fields"],
        "baseline_relative_go_gate_status": spec["go_no_go_rules"]["baseline_relative_threshold"]["status"],
        "exact_reachable_boundaries": {
            "minimum": {"sample_id": "DUMMY_REACHABLE_MIN_9_LAYERS_500_NM", "layer_count": 9, "total_thickness_nm": 500},
            "maximum": {"sample_id": "DUMMY_REACHABLE_MAX_25_LAYERS_2200_NM", "layer_count": 25, "total_thickness_nm": 2200},
        },
        "material_provenance": MATERIAL_PROVENANCE,
        "external_response_formats": spec["storage_contract"]["external_response_array_artifact"]["allowed_formats"],
        "f0_pilot_contract_ready": audit["f0_pilot_contract_ready"],
        "remaining_blockers": [],
        "pending_nonblocking_contract_actions": [
            "recompute the frozen alternative under the same F0 proxy contract before enabling a baseline-relative Go gate"
        ],
        "solver_calls": 0,
        "model_training_runs": 0,
        "level_b_structures_generated": 0,
    }
    p0b_contract = {
        "status": "PASS" if hash_audit["status"] == activation_audit["status"] == baseline["status"] == "PASS" else "FAIL",
        "spec_version": spec["spec_version"],
        "contract_revision": spec["contract_revision"],
        "source_frozen_commit": SPEC_SOURCE_FROZEN_COMMIT,
        "hash_identity_layers": spec["hash_contracts"],
        "baseline_hash_lineage": {
            "authoritative_source": baseline.get("authoritative_source"),
            "frozen_historical_geometry_hash": baseline.get("frozen_legacy_geometry_hash"),
            "p0a_material_bound_hash": baseline.get("p0a_material_bound_hash"),
            "canonical_geometry_hash": baseline.get("canonical_geometry_hash"),
            "physical_configuration_hash": baseline.get("physical_configuration_hash"),
            "simulation_provenance_example_hash": baseline.get("simulation_provenance_example_hash"),
            "split_group_hash": baseline.get("split_group_hash"),
            "roundtrip_status": baseline["status"],
        },
        "hash_behavior_tests": hash_audit,
        "staged_objectives": activation_audit,
        "solver_calls": 0,
        "model_training_runs": 0,
        "pilot_rows_generated": 0,
    }

    write_csv(
        output_dir / "topology_examples.csv",
        topology_rows,
        ["sample_id", "structure_id", "topology_family", "material_tokens", "thickness_nm", "layer_count", "total_thickness_nm", "defect_indices", "defect_count", "gan_termination", "air_termination", "left_count", "right_count", "chirp_parameters", "sequence_hash", "canonical_geometry_hash", "canonical_geometry_hash_version", "physical_configuration_hash", "physical_configuration_hash_version", "split_group_hash", "validation_status", "data_role"],
    )
    write_csv(
        output_dir / "canonicalization_examples.csv",
        canonicalization_rows,
        ["example_id", "input_sequence", "canonical_sequence", "input_layer_count", "canonical_layer_count", "adjacent_merges", "canonical_defect_indices", "sequence_hash", "canonical_geometry_hash", "physical_configuration_hash", "split_group_hash"],
    )
    write_csv(
        output_dir / "invalid_structure_examples.csv",
        invalid_rows,
        ["example_id", "expected_failure", "observed_error", "input_structure", "validation_status"],
    )
    write_csv(
        output_dir / "objective_definition_table.csv",
        objective_rows,
        ["category", "category_order", "field", "direction", "unit", "threshold", "meaning", "aggregation"],
    )
    write_csv(
        output_dir / "schema_field_inventory.csv",
        inventory_rows,
        ["group", "field", "required", "type", "reference", "description"],
    )
    write_json(output_dir / "design_space_coverage_audit.json", _coverage(canonicals))
    write_json(output_dir / "baseline_roundtrip_audit_v1.json", baseline)
    write_json(output_dir / "p0_contract_audit_v1.json", p0_contract)
    write_json(output_dir / "p0b_hash_objective_audit_v1.json", p0b_contract)
    write_json(output_dir / "validation.json", audit)

    file_inventory = {
        name: {"sha256": sha256(output_dir / name), "bytes": (output_dir / name).stat().st_size}
        for name in STATIC_FILES
    }
    manifest = {
        "spec_version": spec["spec_version"],
        "source_frozen_commit": SPEC_SOURCE_FROZEN_COMMIT,
        "generator": "scripts/audit_mdc_ml_inverse_design_spec_v1.py",
        "output_directory": "outputs/mdc_ml_inverse_design_spec_v1",
        "dummy_structure_count": len(candidates),
        "solver_calls": 0,
        "model_training_runs": 0,
        "large_dataset_rows_generated": 0,
        "level_b_structures_generated": 0,
        "files": file_inventory,
        "determinism": "sorted JSON keys, fixed row order, LF line endings, no timestamps",
    }
    write_json(output_dir / "manifest.json", manifest)
    current = _file_state(output_dir)
    return {
        "status": "PASS",
        "output_files": len(current),
        "dummy_structure_count": len(candidates),
        "byte_stable_against_previous": None if not previous else previous == current,
        "solver_calls": 0,
        "model_training_runs": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--audit-only", action="store_true")
    group.add_argument("--build-static-examples", action="store_true")
    args = parser.parse_args()
    result = run_audit() if args.audit_only else build_static_examples()
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
