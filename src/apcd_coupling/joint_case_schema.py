from __future__ import annotations

import hashlib
import json
import math
from typing import Any

NATIVE_MATERIALS = {"APCD_GAN_NATIVE_M1", "APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1"}

def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def _number(value: Any, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result

def validate_joint_case(case: dict[str, Any]) -> dict[str, Any]:
    required = {"case_id", "control_group", "mdc_candidate", "interface_candidate", "np_candidate", "spacer_nm", "wavelength_nm", "polarization", "kx_over_k0", "objects", "coordinates"}
    missing = sorted(required - set(case))
    if missing:
        raise ValueError(f"joint case missing fields: {missing}")
    if _number(case["spacer_nm"], "spacer_nm") < 0 or _number(case["wavelength_nm"], "wavelength_nm") <= 0:
        raise ValueError("invalid spacer or wavelength")
    if case["polarization"] not in {"x", "y"}:
        raise ValueError("polarization must be x or y")
    if _number(case["kx_over_k0"], "kx_over_k0") != 0:
        raise ValueError("Stage-A builder supports only normal incidence kx_over_k0=0")
    materials = {obj.get("material_id") for obj in case["objects"] if obj.get("material_id")}
    if not materials.issubset(NATIVE_MATERIALS | {"Air"}):
        raise ValueError(f"non-canonical material in joint case: {sorted(materials - NATIVE_MATERIALS - {'Air'})}")
    if case["spacer_nm"] == 0 and any(obj.get("role") == "extra_spacer" for obj in case["objects"]):
        raise ValueError("t_extra=0 must not create an extra spacer object")
    if case["coordinates"]["np_pillar_bottom_nm"] != case["coordinates"]["stack_top_nm"]:
        raise ValueError("NP pillar bottom is not at stack top")
    roles = [obj.get("role") for obj in case["objects"]]
    if case["control_group"] == "B0" and any(role in roles for role in ("mdc_layer", "interface_support_layer", "np_pillar", "extra_spacer")):
        raise ValueError("B0 must be bare GaN/Air")
    if case["control_group"] == "B1" and ("np_pillar" in roles or "interface_support_layer" in roles or "extra_spacer" in roles):
        raise ValueError("B1 must contain MDC only")
    if case["control_group"] == "B2" and ("mdc_layer" in roles or len([r for r in roles if r == "interface_support_layer"]) != 1):
        raise ValueError("B2 must contain only the 79 nm interface support plus NP")
    return case
