from __future__ import annotations

from copy import deepcopy
from typing import Any

from .joint_case_schema import canonical_hash, validate_joint_case

def _positive(value: Any, name: str) -> float:
    result = float(value)
    if result <= 0:
        raise ValueError(f"{name} must be positive")
    return result

def build_joint_case(
    mdc_candidate: dict[str, Any],
    np_candidate: dict[str, Any],
    spacer_nm: float,
    wavelength_nm: float,
    polarization: str,
    kx_over_k0: float,
) -> dict[str, Any]:
    mdc = deepcopy(mdc_candidate)
    np = deepcopy(np_candidate)
    layers = list(mdc.get("layers", []))
    if not layers:
        raise ValueError("mdc candidate must provide ordered layers")
    mdc_total = sum(_positive(layer["thickness_nm"], "layer thickness") for layer in layers)
    if abs(mdc_total - float(mdc.get("total_thickness_nm", mdc_total))) > 1e-9:
        raise ValueError("MDC layer sum disagrees with candidate total thickness")
    pillars = list(np.get("pillars", []))
    if len(pillars) != int(np.get("K", len(pillars))):
        raise ValueError("NP pillar count disagrees with K")
    spacer = float(spacer_nm)
    if spacer < 0:
        raise ValueError("spacer_nm must be non-negative")
    pillar_bottom = mdc_total + spacer
    pillar_top = pillar_bottom + _positive(np["pillar_height_nm"], "pillar height")
    objects: list[dict[str, Any]] = []
    objects.append({"role": "gan_substrate", "material_id": "APCD_GAN_NATIVE_M1", "z_min_nm": -600.0, "z_max_nm": 0.0})
    z = 0.0
    for index, layer in enumerate(layers, start=1):
        thickness = _positive(layer["thickness_nm"], "layer thickness")
        objects.append({"role": "mdc_layer", "index": index, "material_id": layer["material_id"], "z_min_nm": z, "z_max_nm": z + thickness, "thickness_nm": thickness})
        z += thickness
    if spacer > 0:
        objects.append({"role": "extra_spacer", "material_id": "APCD_SIO2_NATIVE_M1", "z_min_nm": mdc_total, "z_max_nm": pillar_bottom, "thickness_nm": spacer})
    for index, pillar in enumerate(pillars):
        objects.append({"role": "np_pillar", "index": index, "x_nm": float(pillar["x_nm"]), "y_nm": float(pillar.get("y_nm", 0.0)), "diameter_nm": _positive(pillar["diameter_nm"], "pillar diameter"), "z_min_nm": pillar_bottom, "z_max_nm": pillar_top, "material_id": np["material_id"]})
    objects.append({"role": "air_superstrate", "material_id": "Air", "z_min_nm": pillar_top, "z_max_nm": pillar_top + 700.0})
    case = {
        "schema_version": "joint_case_schema_v1",
        "case_id": f"STAGE_A_{int(float(wavelength_nm))}NM_X_UX0_TEXTRA{int(spacer)}",
        "mdc_candidate": mdc,
        "np_candidate": np,
        "spacer_nm": spacer,
        "wavelength_nm": float(wavelength_nm),
        "polarization": polarization,
        "kx_over_k0": float(kx_over_k0),
        "objects": objects,
        "coordinates": {
            "plus_z": "GaN -> MDC -> NP -> Air",
            "plus_x": "RUN3A phase gradient",
            "positive_kx": "physical +x",
            "m_plus_1": "physical +x",
            "joint_z_zero_nm": 0.0,
            "mdc_top_nm": mdc_total,
            "np_pillar_bottom_nm": pillar_bottom,
            "np_pillar_top_nm": pillar_top,
            "reference_plane": "NP pillar bottom",
        },
        "material_contract_id": "MDC_NATIVE_M1",
        "coordinate_contract_id": "coordinate_convention_v1",
        "source_contract_id": "APCD_MDC_NP_COUPLING_V1_STAGE_A_DIRECT_FULLWAVE_BASELINE",
    }
    case["mdc_geometry_hash"] = canonical_hash({"candidate": mdc, "layers": layers})
    case["np_geometry_hash"] = canonical_hash({"candidate": np, "pillars": pillars})
    case["joint_geometry_hash"] = canonical_hash({"objects": objects, "coordinates": case["coordinates"]})
    return validate_joint_case(case)
