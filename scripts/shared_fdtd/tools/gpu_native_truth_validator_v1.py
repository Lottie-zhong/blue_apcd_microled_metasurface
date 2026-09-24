from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

WAVELENGTHS_NM = list(range(440, 461))
FIELDS = ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz")
MONITOR_ROLES = {
    "MON_IN": {"sample_z_nm": -100.0, "required_fields": FIELDS},
    "MON_PRENP": {"sample_z_nm": 1150.0, "reference_z_nm": 1202.0, "required_fields": FIELDS},
    "MON_POSTNP": {"sample_z_nm": 1800.0, "reference_z_nm": 1722.0, "required_fields": FIELDS},
    "MON_REFLECTION": {"sample_z_nm": -400.0, "required_fields": ()},
}


def _finite_sequence(value: Any) -> bool:
    if isinstance(value, (str, bytes)) or value is None:
        return False
    if not isinstance(value, Sequence):
        return math.isfinite(float(value))
    return bool(value) and all(_finite_sequence(item) for item in value)


def validate_monitor(name: str, payload: Mapping[str, Any], wavelengths_nm: Sequence[int] = WAVELENGTHS_NM) -> dict[str, Any]:
    errors: list[str] = []
    role = MONITOR_ROLES.get(name)
    if role is None:
        return {"pass": False, "errors": [f"unknown_monitor:{name}"]}
    if not payload.get("present", False):
        errors.append("monitor_missing")
    if list(payload.get("wavelengths_nm", [])) != list(wavelengths_nm):
        errors.append("wavelength_grid_mismatch")
    if payload.get("type") != "2D Z-normal":
        errors.append("type_mismatch")
    if abs(float(payload.get("z_nm", 1e99)) - role["sample_z_nm"]) > 1e-9:
        errors.append("z_mismatch")
    if abs(float(payload.get("x_span_nm", -1.0)) - 1740.0) > 1e-9:
        errors.append("x_span_mismatch")
    if abs(float(payload.get("y_span_nm", -1.0)) - 290.0) > 1e-9:
        errors.append("y_span_mismatch")
    fields = payload.get("fields", {})
    field_names = set(fields if isinstance(fields, Sequence) and not isinstance(fields, Mapping) else fields.keys())
    for field in role["required_fields"]:
        if field not in field_names:
            errors.append(f"missing_field:{field}")
    if name == "MON_REFLECTION":
        if not _finite_sequence(payload.get("signed_poynting")):
            errors.append("missing_or_invalid_signed_poynting")
        if not _finite_sequence(payload.get("R")):
            errors.append("missing_or_invalid_R")
    return {"pass": not errors, "errors": errors, "name": name, "role": "R_ONLY" if name == "MON_REFLECTION" else "COMPLEX_EH"}


def validate_truth_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    results = {name: validate_monitor(name, bundle.get("monitors", {}).get(name, {})) for name in MONITOR_ROLES}
    errors = [f"{name}:{error}" for name, result in results.items() for error in result["errors"]]
    required_paths = set(bundle.get("required_relative_paths", []))
    present_paths = set(bundle.get("present_relative_paths", []))
    errors.extend(f"missing_bundle_file:{path}" for path in sorted(required_paths - present_paths))
    if bundle.get("archive_restore_pass") is False:
        errors.append("archive_restore_failed")
    return {"pass": not errors, "errors": errors, "monitors": results}
