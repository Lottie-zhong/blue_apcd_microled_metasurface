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
    *,
    interface_candidate: dict[str, Any] | None = None,
    case_id: str | None = None,
    control_group: str = "B3",
    incident_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mdc = deepcopy(mdc_candidate)
    np = deepcopy(np_candidate)
    interface = deepcopy(interface_candidate or {})
    layers = list(mdc.get("layers", []))
    support_layers = list(interface.get("layers", []))
    mdc_total = sum(_positive(layer["thickness_nm"], "layer thickness") for layer in layers)
    declared_mdc_total = float(mdc.get("total_thickness_nm", mdc_total))
    if abs(mdc_total - declared_mdc_total) > 1e-9:
        raise ValueError("MDC layer sum disagrees with candidate total thickness")
    support_total = sum(_positive(layer["thickness_nm"], "support thickness") for layer in support_layers)
    declared_support_total = float(interface.get("total_thickness_nm", support_total))
    if abs(support_total - declared_support_total) > 1e-9:
        raise ValueError("support layer sum disagrees with candidate total thickness")
    pillars = list(np.get("pillars", []))
    declared_k = int(np.get("K", len(pillars)))
    if len(pillars) != declared_k:
        raise ValueError("NP pillar count disagrees with K")
    spacer = float(spacer_nm)
    if spacer < 0:
        raise ValueError("spacer_nm must be non-negative")
    stack_top = mdc_total + support_total + spacer
    pillar_height = _positive(np["pillar_height_nm"], "pillar height") if pillars else 0.0
    pillar_top = stack_top + pillar_height
    objects: list[dict[str, Any]] = [{"role": "gan_substrate", "material_id": "APCD_GAN_NATIVE_M1", "z_min_nm": -600.0, "z_max_nm": 0.0}]
    z = 0.0
    for index, layer in enumerate(layers, start=1):
        thickness = _positive(layer["thickness_nm"], "layer thickness")
        objects.append({"role": "mdc_layer", "index": index, "material_id": layer["material_id"], "z_min_nm": z, "z_max_nm": z + thickness, "thickness_nm": thickness})
        z += thickness
    for index, layer in enumerate(support_layers, start=1):
        thickness = _positive(layer["thickness_nm"], "support thickness")
        objects.append({"role": "interface_support_layer", "index": index, "material_id": layer["material_id"], "z_min_nm": z, "z_max_nm": z + thickness, "thickness_nm": thickness})
        z += thickness
    if spacer > 0:
        objects.append({"role": "extra_spacer", "material_id": "APCD_SIO2_NATIVE_M1", "z_min_nm": z, "z_max_nm": z + spacer, "thickness_nm": spacer})
        z += spacer
    for index, pillar in enumerate(pillars):
        objects.append({"role": "np_pillar", "index": index, "x_nm": float(pillar["x_nm"]), "y_nm": float(pillar.get("y_nm", 0.0)), "diameter_nm": _positive(pillar["diameter_nm"], "pillar diameter"), "z_min_nm": stack_top, "z_max_nm": pillar_top, "material_id": np["material_id"]})
    objects.append({"role": "air_superstrate", "material_id": "Air", "z_min_nm": pillar_top, "z_max_nm": pillar_top + 700.0})
    case = {
        "schema_version": "joint_case_schema_v1",
        "case_id": case_id or f"STAGE_A_{int(float(wavelength_nm))}NM_X_UX0_TEXTRA{int(spacer)}",
        "control_group": control_group,
        "mdc_candidate": mdc,
        "interface_candidate": interface,
        "np_candidate": np,
        "spacer_nm": spacer,
        "wavelength_nm": float(wavelength_nm),
        "polarization": polarization,
        "kx_over_k0": float(kx_over_k0),
        "incident_state": deepcopy(incident_state) if incident_state is not None else None,
        "objects": objects,
        "coordinates": {
            "plus_z": "GaN -> MDC/support -> NP -> Air",
            "plus_x": "RUN3A phase gradient",
            "positive_kx": "physical +x",
            "m_plus_1": "physical +x",
            "joint_z_zero_nm": 0.0,
            "mdc_top_nm": mdc_total,
            "interface_top_nm": mdc_total + support_total,
            "stack_top_nm": stack_top,
            "np_pillar_bottom_nm": stack_top,
            "np_pillar_top_nm": pillar_top,
            "total_sio2_separation_nm": (float(layers[-1]["thickness_nm"]) if layers and layers[-1].get("material_id") == "APCD_SIO2_NATIVE_M1" else 0.0) + support_total + spacer,
            "same_material_spacer_continuity": bool(spacer == 0 or (layers and layers[-1].get("material_id") == "APCD_SIO2_NATIVE_M1")),
            "reference_plane": "NP pillar bottom" if pillars else "GaN/stack interface",
        },
        "material_contract_id": "MDC_NATIVE_M1",
        "coordinate_contract_id": "coordinate_convention_v1",
        "source_contract_id": "APCD_MDC_NP_COUPLING_V1_STAGE_A_DIRECT_FULLWAVE_BASELINE",
    }
    case["mdc_geometry_hash"] = canonical_hash({"candidate": mdc, "layers": layers})
    case["interface_geometry_hash"] = canonical_hash({"candidate": interface, "layers": support_layers})
    case["np_geometry_hash"] = canonical_hash({"candidate": np, "pillars": pillars})
    case["joint_geometry_hash"] = canonical_hash({"objects": objects, "coordinates": case["coordinates"]})
    case["incident_state_hash"] = canonical_hash(case["incident_state"]) if case["incident_state"] is not None else None
    return validate_joint_case(case)
