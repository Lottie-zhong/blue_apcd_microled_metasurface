"""Static Level-A MDC grammar utilities. No optical solver is imported or called."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Iterable

SPEC_VERSION = "MDC_ML_INVERSE_DESIGN_SPEC_V1"
TOKENS = {"H": "APCD_TIO2_NATIVE_M1", "L": "APCD_SIO2_NATIVE_M1"}
CANONICAL_GEOMETRY_HASH_VERSION = "mdc_canonical_geometry_hash_v3"
PHYSICAL_CONFIGURATION_HASH_VERSION = "mdc_physical_configuration_hash_v1"
SIMULATION_PROVENANCE_HASH_VERSION = "mdc_simulation_provenance_hash_v2"
SPLIT_GROUP_HASH_VERSION = "mdc_split_group_hash_v1"
P0A_LEGACY_PHYSICAL_HASH_VERSION = "mdc_physical_geometry_hash_v2"
MATERIAL_PROVENANCE = {
    "material_policy_id": "MDC_NATIVE_M1",
    "material_policy_version": 5,
    "source_material_id": "APCD_GAN_NATIVE_M1",
    "H_material_id": "APCD_TIO2_NATIVE_M1",
    "L_material_id": "APCD_SIO2_NATIVE_M1",
    "exit_material_id": "AIR",
    "source_material_name": "GaN",
    "H_source_material_name": "tio22",
    "L_source_material_name": "sio222",
    "source_fsp_sha256": "d7511bb92154152d5050d7ae664cb5b281ad3794a280129008359353b357e26f",
    "gan_raw_table_sha256": "906f2983665a51b748aa85ef85cd095550bb64a8ef77b8796e36a0b765407ef0",
}
TOPOLOGY_FAMILIES = (
    "symmetric_periodic",
    "asymmetric_pair_count",
    "off_center_defect",
    "grouped_chirped",
    "dual_defect",
    "termination_reversed",
    "locally_aperiodic",
    "hybrid_periodic_aperiodic",
)
DEFAULT_BOUNDS = {
    "H": (25, 100),
    "L": (40, 180),
    "defect": (120, 500),
    "layer_count": (9, 25),
    "total_thickness_nm": (500, 2200),
}


class GrammarError(ValueError):
    """Raised when a structure does not obey the Level-A grammar."""


def _layer_signature(layer: dict[str, Any]) -> tuple[str, int]:
    return str(layer["material_token"]), int(layer["thickness_nm"])


def _validate_layer(layer: Any, location: str) -> None:
    if not isinstance(layer, dict):
        raise GrammarError(f"{location}: layer must be an object")
    token = layer.get("material_token")
    if token not in TOKENS:
        raise GrammarError(f"{location}: material_token must be H or L")
    thickness = layer.get("thickness_nm")
    if isinstance(thickness, bool) or not isinstance(thickness, int):
        raise GrammarError(f"{location}: thickness_nm must be an integer nm value")
    if thickness <= 0:
        raise GrammarError(f"{location}: thickness_nm must be positive")
    if "is_defect" in layer and not isinstance(layer["is_defect"], bool):
        raise GrammarError(f"{location}: is_defect must be boolean")


def _is_alternating(layers: list[dict[str, Any]]) -> bool:
    return all(
        layers[index - 1]["material_token"] != layer["material_token"]
        for index, layer in enumerate(layers[1:], start=1)
    )


def validate_grammar(structure: Any) -> None:
    """Validate the constrained left-mirror + defect + right-mirror grammar."""
    if not isinstance(structure, dict):
        raise GrammarError("structure must be an object")
    family = structure.get("topology_family")
    if family not in TOPOLOGY_FAMILIES:
        raise GrammarError(f"unsupported topology_family: {family!r}")

    regions: dict[str, list[dict[str, Any]]] = {}
    for region in ("left_mirror", "defect_region", "right_mirror"):
        value = structure.get(region)
        if not isinstance(value, list) or not value:
            raise GrammarError(f"{region} must be a non-empty layer list")
        for index, layer in enumerate(value):
            _validate_layer(layer, f"{region}[{index}]")
        regions[region] = value

    if len(regions["left_mirror"]) < 2 or len(regions["right_mirror"]) < 2:
        raise GrammarError("each mirror must contain at least two layers")
    if not _is_alternating(regions["left_mirror"]):
        raise GrammarError("left_mirror must alternate H/L before canonicalization")
    if not _is_alternating(regions["right_mirror"]):
        raise GrammarError("right_mirror must alternate H/L before canonicalization")

    parameters = structure.get("parameters", {})
    if not isinstance(parameters, dict):
        raise GrammarError("parameters must be an object")

    if family == "symmetric_periodic":
        left = [_layer_signature(layer) for layer in regions["left_mirror"]]
        right = [_layer_signature(layer) for layer in regions["right_mirror"]]
        if left != list(reversed(right)):
            raise GrammarError("symmetric_periodic mirrors must be exact reversals")
    elif family == "asymmetric_pair_count":
        if len(regions["left_mirror"]) == len(regions["right_mirror"]):
            raise GrammarError("asymmetric_pair_count requires unequal mirror counts")
    elif family == "off_center_defect":
        if not isinstance(parameters.get("defect_offset_layers"), int) or parameters.get(
            "defect_offset_layers"
        ) == 0:
            raise GrammarError("off_center_defect requires non-zero defect_offset_layers")
    elif family == "grouped_chirped":
        chirp = parameters.get("chirp_parameters")
        if not isinstance(chirp, dict) or not chirp.get("groups"):
            raise GrammarError("grouped_chirped requires chirp_parameters.groups")
    elif family == "dual_defect":
        defect_count = sum(bool(layer.get("is_defect")) for layer in regions["defect_region"])
        if defect_count != 2:
            raise GrammarError("dual_defect requires exactly two explicitly marked defects")
    elif family == "termination_reversed":
        if parameters.get("termination_reversed") is not True:
            raise GrammarError("termination_reversed requires its explicit topology flag")
    elif family == "locally_aperiodic":
        if not parameters.get("local_aperiodic_indices"):
            raise GrammarError("locally_aperiodic requires local_aperiodic_indices")
    elif family == "hybrid_periodic_aperiodic":
        components = parameters.get("hybrid_components")
        if not isinstance(components, list) or not {
            "periodic",
            "locally_aperiodic",
        }.issubset(components):
            raise GrammarError("hybrid topology must declare periodic and locally_aperiodic")


def sequence_hash(layers: Iterable[dict[str, Any]]) -> str:
    """Hash only the normalized ordered token/thickness sequence."""
    payload = [[str(layer["material_token"]), int(layer["thickness_nm"])] for layer in layers]
    encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _hash_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def geometry_hash(layers: Iterable[dict[str, Any]]) -> str:
    """Hash canonical material IDs and integer-nm layers, never material provenance."""
    payload = {
        "contract": CANONICAL_GEOMETRY_HASH_VERSION,
        "canonicalization_contract": "left_defect_right_merge_adjacent_integer_nm_v1",
        "direction": "GaN_to_Air",
        "source_medium": "APCD_GAN_NATIVE_M1",
        "exit_medium": "AIR",
        "layers": [
            [
                str(layer.get("material_id", TOKENS[str(layer["material_token"])])),
                int(layer["thickness_nm"]),
            ]
            for layer in layers
        ],
    }
    return _hash_payload(payload)


def p0a_legacy_physical_hash(layers: Iterable[dict[str, Any]]) -> str:
    """Reproduce the P0-A 878c... material-bound hash for lineage only."""
    payload = {
        "contract": P0A_LEGACY_PHYSICAL_HASH_VERSION,
        "direction": "GaN_to_Air",
        "source_medium": "APCD_GAN_NATIVE_M1",
        "exit_medium": "AIR",
        "layers": [
            [str(layer["material_token"]), int(layer["thickness_nm"])] for layer in layers
        ],
        "material_ids": TOKENS,
        "material_policy": {
            name: MATERIAL_PROVENANCE[name]
            for name in (
                "material_policy_id", "material_policy_version", "source_material_id",
                "H_material_id", "L_material_id", "exit_material_id",
                "source_fsp_sha256", "gan_raw_table_sha256",
            )
        },
    }
    return _hash_payload(payload)


def physical_configuration_hash(
    canonical_geometry_hash_value: str,
    *,
    material_provenance: dict[str, Any] | None = None,
) -> str:
    """Bind a pure canonical geometry to one concrete material-model configuration."""
    provenance = MATERIAL_PROVENANCE if material_provenance is None else material_provenance
    payload = {
        "contract": PHYSICAL_CONFIGURATION_HASH_VERSION,
        "canonical_geometry_hash": canonical_geometry_hash_value,
        "material_policy_id": provenance["material_policy_id"],
        "material_policy_version": provenance["material_policy_version"],
        "source_fsp_sha256": provenance["source_fsp_sha256"],
        "material_models": {
            provenance["source_material_id"]: {
                "source_material_name": provenance["source_material_name"],
                "raw_table_sha256": provenance["gan_raw_table_sha256"],
            },
            provenance["H_material_id"]: {
                "source_material_name": provenance["H_source_material_name"],
                "version_contract": f"{provenance['material_policy_id']}_v{provenance['material_policy_version']}",
            },
            provenance["L_material_id"]: {
                "source_material_name": provenance["L_source_material_name"],
                "version_contract": f"{provenance['material_policy_id']}_v{provenance['material_policy_version']}",
            },
        },
    }
    return _hash_payload(payload)


def simulation_provenance_hash(
    *,
    physical_configuration_hash_value: str,
    wavelength_grid_id: str,
    angle_grid_id: str,
    angle_convention_id: str,
    solver_id: str,
    solver_version: str,
    polarization_contract_id: str,
    numerical_settings_contract_id: str,
) -> str:
    """Bind a physical configuration to a complete numerical provenance contract."""
    payload = {
        "contract": SIMULATION_PROVENANCE_HASH_VERSION,
        "physical_configuration_hash": physical_configuration_hash_value,
        "wavelength_grid_id": wavelength_grid_id,
        "angle_grid_id": angle_grid_id,
        "angle_convention_id": angle_convention_id,
        "solver_id": solver_id,
        "solver_version": solver_version,
        "polarization_contract_id": polarization_contract_id,
        "numerical_settings_contract_id": numerical_settings_contract_id,
    }
    return _hash_payload(payload)


def split_group_hash(parent_canonical_geometry_hash: str) -> str:
    """Group nominal geometry and every tolerance child by the nominal parent geometry."""
    return _hash_payload({
        "contract": SPLIT_GROUP_HASH_VERSION,
        "parent_canonical_geometry_hash": parent_canonical_geometry_hash,
    })


NOMINAL_PRIMARY_OBJECTIVES = (
    "angular_fwhm_450",
    "spectral_fwhm_normal",
    "tmm_apcd_ready_cone5_integral_proxy",
    "tmm_band_transmission_448_453_normal_proxy",
)
ROBUST_PRIMARY_OBJECTIVES = (*NOMINAL_PRIMARY_OBJECTIVES, "tolerance_robustness_penalty_pm3")


def resolve_primary_objectives(
    *,
    pareto_stage: str,
    robustness_label_available: bool,
    robustness_evaluation_status: str,
    tolerance_robustness_penalty_pm3: float | None,
) -> tuple[str, ...]:
    """Return executable objectives without fabricating a missing robustness label."""
    if pareto_stage == "nominal":
        return NOMINAL_PRIMARY_OBJECTIVES
    if pareto_stage != "robust_shortlist":
        raise GrammarError(f"unsupported pareto_stage: {pareto_stage!r}")
    if not robustness_label_available or robustness_evaluation_status != "complete":
        raise GrammarError("robust Pareto requires a completed +/-3 nm tolerance evaluation")
    if tolerance_robustness_penalty_pm3 is None:
        raise GrammarError("robust Pareto cannot use a missing or fabricated robustness label")
    return ROBUST_PRIMARY_OBJECTIVES


def canonicalize_structure(structure: dict[str, Any]) -> dict[str, Any]:
    """Merge adjacent identical materials and derive normalized defect indices."""
    validate_grammar(structure)
    flat: list[dict[str, Any]] = []
    defect_region = structure["defect_region"]
    for section in ("left_mirror", "defect_region", "right_mirror"):
        for layer in structure[section]:
            is_defect = bool(layer.get("is_defect"))
            if section == "defect_region" and len(defect_region) == 1:
                is_defect = True
            flat.append(
                {
                    "material_token": layer["material_token"],
                    "thickness_nm": layer["thickness_nm"],
                    "is_defect": is_defect,
                    "source_sections": [section],
                }
            )

    merged: list[dict[str, Any]] = []
    for layer in flat:
        if merged and merged[-1]["material_token"] == layer["material_token"]:
            merged[-1]["thickness_nm"] += layer["thickness_nm"]
            merged[-1]["is_defect"] = merged[-1]["is_defect"] or layer["is_defect"]
            merged[-1]["source_sections"].extend(layer["source_sections"])
        else:
            merged.append(deepcopy(layer))

    defect_indices = [index for index, layer in enumerate(merged) if layer["is_defect"]]
    public_layers = [
        {
            "material_token": layer["material_token"],
            "material_id": TOKENS[layer["material_token"]],
            "thickness_nm": layer["thickness_nm"],
        }
        for layer in merged
    ]
    result = {
        "topology_family": structure["topology_family"],
        "direction": "GaN_to_Air",
        "source_medium": "APCD_GAN_NATIVE_M1",
        "exit_medium": "AIR",
        "layers": public_layers,
        "material_tokens": [layer["material_token"] for layer in public_layers],
        "thickness_nm": [layer["thickness_nm"] for layer in public_layers],
        "layer_count": len(public_layers),
        "total_thickness_nm": sum(layer["thickness_nm"] for layer in public_layers),
        "defect_indices": defect_indices,
        "defect_count": len(defect_indices),
        "defect_material": [public_layers[index]["material_id"] for index in defect_indices],
        "defect_thickness_nm": [public_layers[index]["thickness_nm"] for index in defect_indices],
        "termination": {
            "gan_side": public_layers[0]["material_token"],
            "air_side": public_layers[-1]["material_token"],
        },
        "left_layer_count_input": len(structure["left_mirror"]),
        "right_layer_count_input": len(structure["right_mirror"]),
        "chirp_parameters": structure.get("parameters", {}).get("chirp_parameters", {}),
        "parameters": deepcopy(structure.get("parameters", {})),
    }
    result["sequence_hash"] = sequence_hash(public_layers)
    result["canonical_geometry_hash_version"] = CANONICAL_GEOMETRY_HASH_VERSION
    result["canonical_geometry_hash"] = geometry_hash(public_layers)
    result["physical_configuration_hash_version"] = PHYSICAL_CONFIGURATION_HASH_VERSION
    result["physical_configuration_hash"] = physical_configuration_hash(
        result["canonical_geometry_hash"]
    )
    result["split_group_hash_version"] = SPLIT_GROUP_HASH_VERSION
    result["split_group_hash"] = split_group_hash(result["canonical_geometry_hash"])
    result["p0a_legacy_physical_hash"] = p0a_legacy_physical_hash(public_layers)
    return result


def decode_canonical_structure(canonical: dict[str, Any]) -> dict[str, Any]:
    """Decode a canonical physical sequence back into the constrained grammar."""
    layers = [
        {"material_token": layer["material_token"], "thickness_nm": layer["thickness_nm"]}
        for layer in canonical["layers"]
    ]
    defect_indices = list(canonical["defect_indices"])
    if not defect_indices:
        raise GrammarError("canonical structure has no defect index")
    first, last = min(defect_indices), max(defect_indices)
    if first == 0 or last == len(layers) - 1:
        raise GrammarError("canonical defect cannot consume a terminal mirror layer")
    defect_region = deepcopy(layers[first : last + 1])
    if len(defect_indices) > 1:
        for offset, layer in enumerate(defect_region, start=first):
            layer["is_defect"] = offset in defect_indices
    return {
        "sample_id": "DECODED_" + canonical["canonical_geometry_hash"][:16],
        "topology_family": canonical["topology_family"],
        "left_mirror": deepcopy(layers[:first]),
        "defect_region": defect_region,
        "right_mirror": deepcopy(layers[last + 1 :]),
        "parameters": deepcopy(canonical.get("parameters", {})),
    }


def validate_bounds(
    structure: dict[str, Any], bounds: dict[str, tuple[int, int]] | None = None
) -> dict[str, Any]:
    """Return the canonical structure or raise when proposed v1 bounds are violated."""
    active = DEFAULT_BOUNDS if bounds is None else bounds
    canonical = canonicalize_structure(structure)
    errors: list[str] = []

    def check(name: str, value: int) -> None:
        low, high = active[name]
        if value < low or value > high:
            errors.append(f"{name}={value} outside [{low}, {high}]")

    check("layer_count", canonical["layer_count"])
    check("total_thickness_nm", canonical["total_thickness_nm"])
    defect_indices = set(canonical["defect_indices"])
    for index, layer in enumerate(canonical["layers"]):
        check("defect" if index in defect_indices else layer["material_token"], layer["thickness_nm"])
    if not 1 <= canonical["defect_count"] <= 2:
        errors.append("canonical defect_count must be 1 or 2")
    if canonical["topology_family"] == "dual_defect" and canonical["defect_count"] != 2:
        errors.append("dual_defect must retain two separated defects after canonicalization")
    if errors:
        raise GrammarError("; ".join(errors))
    return canonical


def _layer(token: str, thickness: int, *, defect: bool = False) -> dict[str, Any]:
    layer: dict[str, Any] = {"material_token": token, "thickness_nm": thickness}
    if defect:
        layer["is_defect"] = True
    return layer


def _periodic_left(pairs: int, h_nm: int, l_nm: int) -> list[dict[str, Any]]:
    return [_layer(token, h_nm if token == "H" else l_nm) for _ in range(pairs) for token in ("H", "L")]


def _reverse_layers(layers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [deepcopy(layer) for layer in reversed(layers)]


def generate_dummy_candidates() -> list[dict[str, Any]]:
    """Generate twelve deterministic, solver-free Level-A examples (well below 100)."""
    left = _periodic_left(3, 45, 79)
    right = _reverse_layers(left)
    candidates: list[dict[str, Any]] = [
        {
            "sample_id": "DUMMY_SYMMETRIC_BASE",
            "topology_family": "symmetric_periodic",
            "left_mirror": left,
            "defect_region": [_layer("H", 180)],
            "right_mirror": right,
            "parameters": {},
        },
        {
            "sample_id": "DUMMY_ASYMMETRIC_COUNTS",
            "topology_family": "asymmetric_pair_count",
            "left_mirror": _periodic_left(2, 45, 79),
            "defect_region": [_layer("H", 180)],
            "right_mirror": _reverse_layers(_periodic_left(4, 45, 79)),
            "parameters": {},
        },
        {
            "sample_id": "DUMMY_OFF_CENTER",
            "topology_family": "off_center_defect",
            "left_mirror": _periodic_left(2, 47, 77),
            "defect_region": [_layer("H", 190)],
            "right_mirror": _reverse_layers(_periodic_left(4, 47, 77)),
            "parameters": {"defect_offset_layers": -2},
        },
        {
            "sample_id": "DUMMY_GROUPED_CHIRP",
            "topology_family": "grouped_chirped",
            "left_mirror": [_layer("H", 42), _layer("L", 75), _layer("H", 45), _layer("L", 79), _layer("H", 48), _layer("L", 83)],
            "defect_region": [_layer("H", 200)],
            "right_mirror": [_layer("L", 83), _layer("H", 48), _layer("L", 79), _layer("H", 45), _layer("L", 75), _layer("H", 42)],
            "parameters": {"chirp_parameters": {"groups": ["outer", "middle", "inner"], "offset_nm": [-4, 0, 4]}},
        },
        {
            "sample_id": "DUMMY_DUAL_DEFECT",
            "topology_family": "dual_defect",
            "left_mirror": left,
            "defect_region": [_layer("H", 160, defect=True), _layer("L", 79), _layer("H", 160, defect=True)],
            "right_mirror": right,
            "parameters": {"defect_spacing_layers": 1},
        },
        {
            "sample_id": "DUMMY_TERMINATION_REVERSED",
            "topology_family": "termination_reversed",
            "left_mirror": [_layer("L", 79), _layer("H", 45), _layer("L", 79), _layer("H", 45), _layer("L", 79)],
            "defect_region": [_layer("H", 180)],
            "right_mirror": right,
            "parameters": {"termination_reversed": True},
        },
        {
            "sample_id": "DUMMY_LOCAL_APERIODIC",
            "topology_family": "locally_aperiodic",
            "left_mirror": [_layer("H", 45), _layer("L", 79), _layer("H", 52), _layer("L", 74), _layer("H", 45), _layer("L", 79)],
            "defect_region": [_layer("H", 185)],
            "right_mirror": right,
            "parameters": {"local_aperiodic_indices": [2, 3]},
        },
        {
            "sample_id": "DUMMY_HYBRID",
            "topology_family": "hybrid_periodic_aperiodic",
            "left_mirror": [_layer("H", 43), _layer("L", 76), _layer("H", 45), _layer("L", 79), _layer("H", 51), _layer("L", 84)],
            "defect_region": [_layer("H", 205)],
            "right_mirror": right,
            "parameters": {"hybrid_components": ["periodic", "locally_aperiodic"], "local_aperiodic_indices": [4, 5]},
        },
    ]
    for name, h_nm, l_nm, defect_nm in (
        ("DUMMY_BOUNDARY_LOW", 25, 40, 120),
        ("DUMMY_BOUNDARY_HIGH", 100, 180, 500),
    ):
        boundary_left = _periodic_left(3, h_nm, l_nm)
        candidates.append(
            {
                "sample_id": name,
                "topology_family": "symmetric_periodic",
                "left_mirror": boundary_left,
                "defect_region": [_layer("H", defect_nm)],
                "right_mirror": _reverse_layers(boundary_left),
                "parameters": {"boundary_control": True},
            }
        )
    for name, pairs, h_nm, l_nm, defect_nm in (
        ("DUMMY_REACHABLE_MIN_9_LAYERS_500_NM", 2, 45, 50, 120),
        ("DUMMY_REACHABLE_MAX_25_LAYERS_2200_NM", 6, 100, 50, 400),
    ):
        boundary_left = _periodic_left(pairs, h_nm, l_nm)
        candidates.append(
            {
                "sample_id": name,
                "topology_family": "symmetric_periodic",
                "left_mirror": boundary_left,
                "defect_region": [_layer("H", defect_nm)],
                "right_mirror": _reverse_layers(boundary_left),
                "parameters": {"declared_design_boundary_control": True},
            }
        )
    for candidate in candidates:
        validate_bounds(candidate)
    return candidates


def audit_split_leakage(records: Iterable[dict[str, Any]]) -> list[str]:
    """Return group leakage findings; an empty list means the split contract passes."""
    groups: dict[tuple[str, str], set[str]] = {}
    for index, record in enumerate(records):
        split_name = record.get("split_name")
        if not split_name:
            return [f"record[{index}] missing split_name"]
        keys = {
            ("split_group", str(record.get("split_group_hash", ""))),
            ("structure", str(record.get("structure_id", ""))),
        }
        parent = record.get("parent_split_group_hash") or record.get("parent_id") or record.get("parent_seed")
        if parent:
            keys.add(("parent", str(parent)))
        for kind, value in keys:
            if value:
                groups.setdefault((kind, value), set()).add(str(split_name))
    return [
        f"{kind} group {value} crosses splits {sorted(splits)}"
        for (kind, value), splits in sorted(groups.items())
        if len(splits) > 1
    ]


__all__ = [
    "CANONICAL_GEOMETRY_HASH_VERSION",
    "DEFAULT_BOUNDS",
    "GrammarError",
    "MATERIAL_PROVENANCE",
    "NOMINAL_PRIMARY_OBJECTIVES",
    "P0A_LEGACY_PHYSICAL_HASH_VERSION",
    "PHYSICAL_CONFIGURATION_HASH_VERSION",
    "ROBUST_PRIMARY_OBJECTIVES",
    "SIMULATION_PROVENANCE_HASH_VERSION",
    "SPLIT_GROUP_HASH_VERSION",
    "SPEC_VERSION",
    "TOKENS",
    "TOPOLOGY_FAMILIES",
    "audit_split_leakage",
    "canonicalize_structure",
    "decode_canonical_structure",
    "generate_dummy_candidates",
    "geometry_hash",
    "p0a_legacy_physical_hash",
    "physical_configuration_hash",
    "resolve_primary_objectives",
    "sequence_hash",
    "simulation_provenance_hash",
    "split_group_hash",
    "validate_bounds",
    "validate_grammar",
]
