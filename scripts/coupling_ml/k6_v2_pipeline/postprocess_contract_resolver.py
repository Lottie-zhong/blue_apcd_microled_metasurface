"""Owner-controlled, read-only postprocess-contract resolution for coupling_609d_v1.

This module projects only the six frozen postprocess fields. It does not write
files, issue scientific entry authorization, access native truth, or run solvers.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from math import isfinite
from pathlib import Path
from typing import Any

from . import generic_profile as G
from . import ingest as I

RESOLVER_SCHEMA = "APCD_COUPLING_POSTPROCESS_CONTRACT_RESOLVER_V1"
RESOLVED_CONTRACT_SCHEMA = "APCD_COUPLING_RESOLVED_POSTPROCESS_CONTRACT_V1"
SOURCE_CONTRACT_SCHEMA = "APCD_COUPLING_PHYSICS_CONTRACT_V2"
FIELDS = (
    "materials",
    "monitors",
    "references_nm",
    "samples_nm",
    "stack_layers",
    "wavelengths_nm",
)


def _need(ok: bool, reason: str) -> None:
    if not ok:
        raise I.DataAccessError(reason)


def _verify_resolver_certificate(authority: Mapping[str, Any]) -> tuple[Mapping[str, Any], str]:
    cert = G._map(authority.get("resolver_certification"),
                  "resolver_certification")
    cert_sha = G._sha(authority.get("resolver_certification_file_sha"),
                      "resolver_certification_file")
    _need(I._canon(cert) == cert_sha,
          "resolver_certification_file_sha_mismatch")
    _need(cert.get("schema") == "APCD_COUPLING_POSTPROCESS_CONTRACT_RESOLVER_CERTIFICATION_V1"
          and cert.get("verdict") == "PASS"
          and cert.get("science_owner") == G.SCIENCE_OWNER_ID
          and cert.get("profile_id") == G.PROFILE_ID
          and cert.get("resolver_schema") == RESOLVER_SCHEMA
          and cert.get("resolved_contract_schema") == RESOLVED_CONTRACT_SCHEMA
          and cert.get("resolver_module") == "k6_v2_pipeline.postprocess_contract_resolver"
          and cert.get("resolver_entrypoint") == "resolve_postprocess_contract"
          and cert.get("fields") == list(FIELDS)
          and cert.get("projection_digest_rule") ==
              "ingest._canon({schema:resolved_contract_schema,resolved_contract:exact_six_fields})",
          "resolver_certification_contract")
    _need(cert.get("resolver_module_sha256") == I.sha256_file(Path(__file__))
          and cert.get("generic_profile_sha256") == I.sha256_file(Path(G.__file__))
          and cert.get("canonicalizer_module_sha256") == I.sha256_file(Path(I.__file__)),
          "resolver_certification_toolchain_sha")
    return cert, cert_sha


def _finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(float(value))
    )


def _source_fields(contract: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    """Select only a named, versioned source section; never infer key aliases."""
    _need(contract.get("schema") == SOURCE_CONTRACT_SCHEMA,
          "resolver_source_contract_schema")
    parent_fields = contract.get("parent_physical_contract_fields")
    _need(isinstance(parent_fields, Mapping),
          "resolver_parent_physical_contract_fields")
    missing = [key for key in FIELDS if key not in parent_fields]
    _need(not missing, "resolver_required_fields_missing:" + ",".join(missing))
    return {key: deepcopy(parent_fields[key]) for key in FIELDS}, \
        "parent_physical_contract_fields"


def _validate_resolved_fields(fields: Mapping[str, Any]) -> None:
    """Structural checks only; preserve every certified source value verbatim."""
    materials = fields.get("materials")
    monitors = fields.get("monitors")
    references = fields.get("references_nm")
    samples = fields.get("samples_nm")
    stack = fields.get("stack_layers")
    wavelengths = fields.get("wavelengths_nm")

    _need(isinstance(materials, Mapping) and bool(materials)
          and all(isinstance(v, str) and v for v in materials.values()),
          "resolver_materials_invalid")
    _need(isinstance(monitors, Mapping)
          and {"input", "output", "pre"} <= set(monitors)
          and all(isinstance(v, str) and v for v in monitors.values()),
          "resolver_monitors_invalid")
    monitor_names = set(monitors.values())
    _need(isinstance(references, Mapping) and isinstance(samples, Mapping)
          and set(references) == monitor_names
          and set(samples) == monitor_names
          and all(_finite_number(v) for v in references.values())
          and all(_finite_number(v) for v in samples.values()),
          "resolver_reference_or_sample_planes_invalid")
    _need(isinstance(stack, list) and bool(stack), "resolver_stack_layers_invalid")
    allowed_materials = set(materials.values())
    for layer in stack:
        _need(isinstance(layer, (list, tuple)) and len(layer) == 2
              and isinstance(layer[0], str) and layer[0] in allowed_materials
              and _finite_number(layer[1]) and float(layer[1]) > 0,
              "resolver_stack_layer_invalid")
    _need(isinstance(wavelengths, list) and len(wavelengths) == 21
          and all(_finite_number(v) for v in wavelengths)
          and all(float(a) < float(b) for a, b in zip(wavelengths, wavelengths[1:])),
          "resolver_wavelengths_invalid")


def _check_optional_geometry_binding(
    contract: Mapping[str, Any], row: Mapping[str, Any]
) -> str:
    """Check listed case bindings; shared contracts may serve new authorized cases."""
    binding = contract.get("case_geometry_binding")
    if not isinstance(binding, Mapping):
        return "SHARED_CONTRACT_NO_CASE_BINDING"
    rows = binding.get("cases")
    _need(isinstance(rows, list), "resolver_case_geometry_binding_invalid")
    matches = [item for item in rows
               if isinstance(item, Mapping) and item.get("case_id") == row.get("case_id")]
    _need(len(matches) <= 1, "resolver_case_geometry_binding_duplicate")
    if not matches:
        return "UNLISTED_SHARED_CONTRACT_CASE"
    bound = matches[0]
    ordered = list(row.get("ordered_D_nm", ()))
    _need(bound.get("attempt_id") == row.get("attempt_id")
          and bound.get("ordered_D_nm") == ordered
          and bound.get("role") == row.get("role")
          and bound.get("geometry_sha256") == G.geometry_sha(ordered),
          "resolver_case_geometry_binding_mismatch")
    return "MATCHED"


def resolve_postprocess_contract(
    authority: Mapping[str, Any], case_id: str, attempt_id: str
) -> dict[str, Any]:
    """Resolve an authorized case's flat postprocess mapping from its pinned contract.

    Caller must independently pin this module and the generic_profile importer.
    Returned resolved_contract has exactly the six direct fields expected by
    the frozen postprocessor. resolved_contract_sha256 uses ingest._canon over
    the versioned projection envelope.
    """
    manifest, _admission, _cert = G._verified_authority(authority)
    resolver_cert, resolver_cert_sha = _verify_resolver_certificate(authority)
    decision = G.validate_profile_admission(
        authority=authority, case_id=case_id, attempt_id=attempt_id
    )
    row = G._case_row(manifest, case_id, attempt_id)

    declared_request_sha = G._sha(row.get("case_request_sha256"), "case_request")
    request_sha = G._case_request_digest(row)
    _need(request_sha == declared_request_sha, "resolver_case_request_digest")
    acceptance_sha = G._verify_source_acceptance(row, request_sha)

    contract_pin = G._map(row.get("physics_contract"), "case_physics_contract")
    contract_sha = G._sha(row.get("physics_contract_sha"), "case_physics_contract")
    contract_path = Path(contract_pin["path"])
    _need(contract_pin.get("sha256") == contract_sha
          and contract_path.is_file()
          and I.sha256_file(contract_path) == contract_sha,
          "resolver_physics_contract_file_sha_mismatch")
    contract = I._json(contract_path)
    _need(isinstance(contract, Mapping), "resolver_physics_contract_invalid")
    _need(I._canon(contract) == contract_sha,
          "resolver_physics_contract_canonical_sha_mismatch")
    _need(resolver_cert.get("source_contract_schema") == contract.get("schema")
          and resolver_cert.get("source_contract_sha256") == contract_sha
          and resolver_cert.get("source_contract_section") ==
              "parent_physical_contract_fields",
          "resolver_certification_source_contract_binding")

    stop = contract.get("temporal_stop")
    if isinstance(stop, Mapping):
        if "fdtd_simulation_maximum_time_s" in stop:
            _need(row.get("simulation_time_s") == stop["fdtd_simulation_maximum_time_s"],
                  "resolver_simulation_time_contract_mismatch")
        if "fdtd_auto_shutoff_min" in stop:
            _need(row.get("auto_shutoff_min") == stop["fdtd_auto_shutoff_min"],
                  "resolver_auto_shutoff_contract_mismatch")

    fields, source_section = _source_fields(contract)
    _validate_resolved_fields(fields)
    geometry_binding = _check_optional_geometry_binding(contract, row)
    projection_digest = I._canon({
        "schema": RESOLVED_CONTRACT_SCHEMA,
        "resolved_contract": fields,
    })

    return {
        "schema": RESOLVER_SCHEMA,
        "verdict": "PASS",
        "profile_id": G.PROFILE_ID,
        "batch_id": manifest["batch_id"],
        "case_id": case_id,
        "attempt_id": attempt_id,
        "role": row["role"],
        "case_request_sha256": declared_request_sha,
        "source_acceptance_file_sha256": acceptance_sha,
        "resolver_certification_file_sha256": resolver_cert_sha,
        "physical_contract_sha256": contract_sha,
        "physical_contract_file_sha256": contract_pin["sha256"],
        "source_contract_schema": contract["schema"],
        "source_contract_section": source_section,
        "case_geometry_binding": geometry_binding,
        "resolved_contract_schema": RESOLVED_CONTRACT_SCHEMA,
        "resolved_contract_sha256": projection_digest,
        "resolved_contract": fields,
        "entry_authorization": False,
        "native_truth_validated": False,
        "solver_entry_count": 0,
        "decision_scope": decision["verdict"],
    }
