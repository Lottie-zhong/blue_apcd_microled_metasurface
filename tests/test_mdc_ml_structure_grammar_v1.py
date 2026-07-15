from copy import deepcopy

import pytest

from scripts.mdc_ml_structure_grammar_v1 import (
    DEFAULT_BOUNDS,
    GrammarError,
    MATERIAL_PROVENANCE,
    NOMINAL_PRIMARY_OBJECTIVES,
    ROBUST_PRIMARY_OBJECTIVES,
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


def test_dummy_candidates_cover_every_family_and_bounds():
    candidates = generate_dummy_candidates()
    canonicals = [validate_bounds(candidate) for candidate in candidates]
    assert len(candidates) == 12
    assert len(candidates) <= 100
    assert set(TOPOLOGY_FAMILIES) <= {item["topology_family"] for item in canonicals}
    assert min(layer["thickness_nm"] for item in canonicals for index, layer in enumerate(item["layers"]) if layer["material_token"] == "H" and index not in item["defect_indices"]) == DEFAULT_BOUNDS["H"][0]
    assert max(item["defect_thickness_nm"][0] for item in canonicals) == DEFAULT_BOUNDS["defect"][1]
    by_name = {candidate["sample_id"]: canonical for candidate, canonical in zip(candidates, canonicals)}
    assert (by_name["DUMMY_REACHABLE_MIN_9_LAYERS_500_NM"]["layer_count"], by_name["DUMMY_REACHABLE_MIN_9_LAYERS_500_NM"]["total_thickness_nm"]) == (9, 500)
    assert (by_name["DUMMY_REACHABLE_MAX_25_LAYERS_2200_NM"]["layer_count"], by_name["DUMMY_REACHABLE_MAX_25_LAYERS_2200_NM"]["total_thickness_nm"]) == (25, 2200)


def test_adjacent_materials_merge_and_defect_index_is_canonical():
    structure = {
        "sample_id": "MERGE",
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
    canonical = canonicalize_structure(structure)
    assert canonical["material_tokens"] == ["H", "L", "H", "L", "H"]
    assert canonical["thickness_nm"] == [45, 79, 210, 79, 45]
    assert canonical["defect_indices"] == [2]
    assert all(a != b for a, b in zip(canonical["material_tokens"], canonical["material_tokens"][1:]))


@pytest.mark.parametrize("bad_value", [45.5, True, 0, -1])
def test_integer_positive_nm_is_enforced(bad_value):
    structure = deepcopy(generate_dummy_candidates()[0])
    structure["left_mirror"][0]["thickness_nm"] = bad_value
    with pytest.raises(GrammarError):
        canonicalize_structure(structure)


def test_mirror_reversal_is_a_distinct_physical_hash():
    canonical = validate_bounds(generate_dummy_candidates()[1])
    assert canonical["layers"] != list(reversed(canonical["layers"]))
    assert canonical["canonical_geometry_hash"] != geometry_hash(reversed(canonical["layers"]))


def test_hashes_are_deterministic_and_ignore_sample_name():
    first = generate_dummy_candidates()[0]
    renamed = deepcopy(first)
    renamed["sample_id"] = "RENAMED_ONLY"
    assert canonicalize_structure(first)["sequence_hash"] == canonicalize_structure(renamed)["sequence_hash"]
    assert canonicalize_structure(first)["canonical_geometry_hash"] == canonicalize_structure(renamed)["canonical_geometry_hash"]


def test_roundtrip_preserves_physical_geometry_and_hash():
    canonical = validate_bounds(generate_dummy_candidates()[2])
    roundtrip = validate_bounds(decode_canonical_structure(canonical))
    assert roundtrip["layers"] == canonical["layers"]
    assert roundtrip["sequence_hash"] == canonical["sequence_hash"]
    assert roundtrip["canonical_geometry_hash"] == canonical["canonical_geometry_hash"]
    assert roundtrip["physical_configuration_hash"] == canonical["physical_configuration_hash"]
    assert roundtrip["split_group_hash"] == canonical["split_group_hash"]


def _simulation_hash(canonical, *, wavelength_grid_id="wl_A", angle_grid_id="angle_A", physical_hash=None):
    return simulation_provenance_hash(
        physical_configuration_hash_value=physical_hash or canonical["physical_configuration_hash"],
        wavelength_grid_id=wavelength_grid_id,
        angle_grid_id=angle_grid_id,
        angle_convention_id="air_side_far_field_conserved_real_kx_v1",
        solver_id="TMM_static_test",
        solver_version="not_executed_static_contract",
        polarization_contract_id="TE_TM_separate_unpolarized_arithmetic_mean_v1",
        numerical_settings_contract_id="F0_TMM_static_contract_v1",
    )


def test_grid_identity_changes_only_simulation_provenance_hash():
    canonical = validate_bounds(generate_dummy_candidates()[0])
    identities = (canonical["canonical_geometry_hash"], canonical["physical_configuration_hash"], canonical["split_group_hash"])
    base = _simulation_hash(canonical)
    assert _simulation_hash(canonical, wavelength_grid_id="wl_B") != base
    assert _simulation_hash(canonical, angle_grid_id="angle_B") != base
    assert identities == (canonical["canonical_geometry_hash"], canonical["physical_configuration_hash"], canonical["split_group_hash"])


def test_material_source_change_affects_physical_and_simulation_only():
    canonical = validate_bounds(generate_dummy_candidates()[0])
    changed = deepcopy(MATERIAL_PROVENANCE)
    changed["gan_raw_table_sha256"] = "0" * 64
    changed_physical = physical_configuration_hash(canonical["canonical_geometry_hash"], material_provenance=changed)
    assert changed_physical != canonical["physical_configuration_hash"]
    assert _simulation_hash(canonical, physical_hash=changed_physical) != _simulation_hash(canonical)
    assert split_group_hash(canonical["canonical_geometry_hash"]) == canonical["split_group_hash"]


def test_tolerance_child_changes_geometry_but_inherits_parent_split_group():
    parent = validate_bounds(generate_dummy_candidates()[0])
    child_input = decode_canonical_structure(parent)
    child_input["defect_region"][0]["thickness_nm"] += 3
    child = validate_bounds(child_input)
    assert child["canonical_geometry_hash"] != parent["canonical_geometry_hash"]
    assert child["physical_configuration_hash"] != parent["physical_configuration_hash"]
    assert split_group_hash(parent["canonical_geometry_hash"]) == parent["split_group_hash"]
    assert child["split_group_hash"] != parent["split_group_hash"]


def test_staged_objectives_reject_missing_robustness_label():
    nominal = resolve_primary_objectives(pareto_stage="nominal", robustness_label_available=False, robustness_evaluation_status="not_evaluated", tolerance_robustness_penalty_pm3=None)
    assert nominal == NOMINAL_PRIMARY_OBJECTIVES
    with pytest.raises(GrammarError, match="robust Pareto"):
        resolve_primary_objectives(pareto_stage="robust_shortlist", robustness_label_available=False, robustness_evaluation_status="not_evaluated", tolerance_robustness_penalty_pm3=None)
    robust = resolve_primary_objectives(pareto_stage="robust_shortlist", robustness_label_available=True, robustness_evaluation_status="complete", tolerance_robustness_penalty_pm3=0.0)
    assert robust == ROBUST_PRIMARY_OBJECTIVES


def test_bounds_reject_too_thin_defect():
    structure = deepcopy(generate_dummy_candidates()[0])
    structure["defect_region"][0]["thickness_nm"] = 119
    with pytest.raises(GrammarError, match="defect"):
        validate_bounds(structure)


def test_split_leakage_audit_detects_parent_and_geometry_crossing():
    records = [
        {"split_group_hash": "a" * 64, "structure_id": "S1", "parent_split_group_hash": "a" * 64, "split_name": "train"},
        {"split_group_hash": "a" * 64, "structure_id": "S2", "parent_split_group_hash": "a" * 64, "split_name": "validation"},
    ]
    findings = audit_split_leakage(records)
    assert any("split_group group" in finding for finding in findings)


def test_split_leakage_audit_passes_grouped_records():
    records = [
        {"split_group_hash": "a" * 64, "structure_id": "S1", "parent_split_group_hash": "a" * 64, "split_name": "train"},
        {"split_group_hash": "b" * 64, "structure_id": "S2", "parent_split_group_hash": "b" * 64, "split_name": "validation"},
    ]
    assert audit_split_leakage(records) == []
