import csv
import json

from scripts.audit_mdc_ml_inverse_design_spec_v1 import (
    STATIC_FILES,
    baseline_roundtrip_audit,
    audit_schema_inventory,
    audit_spec,
    build_static_examples,
    hash_behavior_audit,
    load_schema,
    load_spec,
    make_schema_dummy,
    make_schema_tolerance_child_dummy,
    objective_activation_audit,
    run_audit,
    validate_json_instance,
)
from scripts.mdc_ml_structure_grammar_v1 import decode_canonical_structure, generate_dummy_candidates, validate_bounds


def test_spec_contract_contains_required_policies():
    spec = load_spec()
    assert audit_spec(spec) == []
    assert spec["objective_definitions"]["aggregation_policy"] == "staged_pareto_no_single_arbitrary_score"
    assert spec["objective_definitions"]["inventory_count"] == 14
    assert len(spec["objective_definitions"]["nominal_search_primary"]) == 4
    assert len(spec["objective_definitions"]["robust_shortlist_primary"]) == 5
    assert "significant" not in json.dumps(spec, ensure_ascii=False).lower()
    assert "显著改善" not in json.dumps(spec, ensure_ascii=False)
    assert spec["design_levels"]["level_b"]["schema_only_in_v1"] is True
    assert spec["design_levels"]["level_b"]["enabled"] is False
    assert spec["sampling_policy"]["generated_in_v1"] is False
    assert spec["power_gates"]["viable"]["minimum"] == 0.5


def test_dataset_schema_and_static_dummy_validate():
    schema = load_schema()
    assert audit_schema_inventory(schema) == []
    for canonical in map(validate_bounds, generate_dummy_candidates()):
        assert validate_json_instance(make_schema_dummy(canonical), schema) == []
    parent = validate_bounds(generate_dummy_candidates()[0])
    child_input = decode_canonical_structure(parent)
    child_input["defect_region"][0]["thickness_nm"] += 3
    child = validate_bounds(child_input)
    record = make_schema_tolerance_child_dummy(parent, child)
    assert validate_json_instance(record, schema) == []
    assert record["split"]["split_group_hash"] == parent["split_group_hash"]
    assert record["split"]["inherits_parent_split"] is True


def test_authoritative_baseline_roundtrip_passes():
    result = baseline_roundtrip_audit()
    assert result["status"] == "PASS"
    assert result["layer_by_layer_equality"] is True
    assert result["roundtrip_hash_equality"] is True
    assert result["p0a_material_bound_hash"] == "878c4c625432d1d3bcfb990b7e40038f129289e4eee1187b73738d6a25f8a221"
    assert result["canonical_geometry_hash"] != result["physical_configuration_hash"]


def test_hash_behavior_and_objective_activation_audits_pass():
    canonical = validate_bounds(generate_dummy_candidates()[0])
    assert hash_behavior_audit(canonical)["status"] == "PASS"
    activation = objective_activation_audit()
    assert activation["status"] == "PASS"
    assert activation["nominal_pareto_dimension"] == 4
    assert activation["robust_pareto_dimension"] == 5
    assert activation["missing_robustness_label_rejected"] is True


def test_audit_passes_without_solver_or_training():
    result = run_audit()
    assert result["status"] == "PASS"
    assert result["solver_calls"] == 0
    assert result["model_training_runs"] == 0
    assert result["level_b_structures_generated"] == 0
    assert result["nominal_primary_objective_count"] == 4
    assert result["robust_primary_objective_count"] == 5
    assert result["hash_behavior_status"] == "PASS"
    assert result["objective_activation_status"] == "PASS"
    assert result["authoritative_baseline_roundtrip_status"] == "PASS"
    assert result["f0_pilot_contract_ready"] is True


def test_static_builder_is_byte_stable_and_bounded(tmp_path):
    first = build_static_examples(tmp_path)
    second = build_static_examples(tmp_path)
    assert first["status"] == "PASS"
    assert first["dummy_structure_count"] <= 100
    assert second["byte_stable_against_previous"] is True
    assert {path.name for path in tmp_path.iterdir()} == {*STATIC_FILES, "manifest.json"}

    with (tmp_path / "topology_examples.csv").open(encoding="utf-8", newline="") as handle:
        topology = list(csv.DictReader(handle))
    with (tmp_path / "invalid_structure_examples.csv").open(encoding="utf-8", newline="") as handle:
        invalid = list(csv.DictReader(handle))
    assert len(topology) == 12
    assert all(row["validation_status"] == "PASS" for row in topology)
    assert all(row["validation_status"] == "EXPECTED_FAIL" for row in invalid)

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["solver_calls"] == 0
    assert manifest["model_training_runs"] == 0
    assert manifest["large_dataset_rows_generated"] == 0
    contract = json.loads((tmp_path / "p0_contract_audit_v1.json").read_text(encoding="utf-8"))
    assert contract["classified_objective_count"] == 14
    assert contract["f0_pilot_contract_ready"] is True
    p0b = json.loads((tmp_path / "p0b_hash_objective_audit_v1.json").read_text(encoding="utf-8"))
    assert p0b["status"] == "PASS"
    assert p0b["staged_objectives"]["nominal_pareto_dimension"] == 4
    assert p0b["staged_objectives"]["robust_pareto_dimension"] == 5
