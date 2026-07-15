import csv
import json
import subprocess
from pathlib import Path

from scripts.audit_mdc_ml_inverse_design_spec_v1 import (
    STATIC_FILES,
    REQUIRED_IMMUTABLE_PAYLOAD,
    SPEC_FREEZE_ANCHOR_COMMIT,
    audit_repository_freeze_contract,
    baseline_roundtrip_audit,
    audit_schema_inventory,
    audit_spec,
    build_static_examples,
    hash_behavior_audit,
    git_payload_sha256,
    load_freeze_manifest,
    load_schema,
    load_spec,
    make_schema_dummy,
    make_schema_tolerance_child_dummy,
    objective_activation_audit,
    run_audit,
    validate_json_instance,
)
from scripts.mdc_ml_structure_grammar_v1 import decode_canonical_structure, generate_dummy_candidates, validate_bounds


EXPECTED_LF_ATTRIBUTE_PATHS = (
    ".gitattributes",
    *REQUIRED_IMMUTABLE_PAYLOAD,
    "configs/mdc_ml_spec_freeze_manifest_v1.json",
)


def _lf_attributes_text() -> str:
    return "".join(f"/{path} text eol=lf\n" for path in EXPECTED_LF_ATTRIBUTE_PATHS)


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
    assert result["repository_contract_status"] == "PASS"
    assert result["spec_freeze_anchor_commit"] == SPEC_FREEZE_ANCHOR_COMMIT
    assert result["freeze_anchor_exists"] is True
    assert result["anchor_is_ancestor"] is True
    assert result["immutable_payload_count"] == 6
    assert result["payload_drift_count"] == 0
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


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=root, text=True, encoding="utf-8"
    ).strip()


def _make_freeze_repo(root: Path) -> tuple[str, Path]:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "P0C Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "p0c@example.invalid"], cwd=root, check=True)
    for relative in REQUIRED_IMMUTABLE_PAYLOAD:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"frozen payload: {relative}\n", encoding="utf-8", newline="\n")
    (root / ".gitattributes").write_text(
        _lf_attributes_text(), encoding="utf-8", newline="\n"
    )
    subprocess.run(
        ["git", "add", ".gitattributes", *REQUIRED_IMMUTABLE_PAYLOAD],
        cwd=root,
        check=True,
    )
    subprocess.run(["git", "commit", "-q", "-m", "freeze anchor"], cwd=root, check=True)
    anchor = _git(root, "rev-parse", "HEAD")
    manifest_path = root / "configs" / "mdc_ml_spec_freeze_manifest_v1.json"
    manifest = {
        "manifest_version": "mdc_ml_spec_freeze_manifest_v1",
        "repository_contract_version": "mdc_ml_repository_freeze_contract_v1",
        "spec_freeze_anchor_commit": anchor,
        "head_policy": "descendant_or_equal",
        "immutable_payload": [
            {
                "path": relative,
                "role": f"test_role_{index}",
                "sha256": git_payload_sha256(anchor, relative, root),
                "immutable": True,
            }
            for index, relative in enumerate(REQUIRED_IMMUTABLE_PAYLOAD)
        ],
        "mutable_maintenance_files": [
            "scripts/audit_mdc_ml_inverse_design_spec_v1.py",
            "tests/test_mdc_ml_inverse_design_spec_v1.py",
            "tests/test_mdc_ml_structure_grammar_v1.py",
        ],
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return anchor, manifest_path


def test_freeze_anchor_itself_and_descendant_pass(tmp_path):
    anchor, manifest_path = _make_freeze_repo(tmp_path)
    at_anchor = audit_repository_freeze_contract(
        root=tmp_path, manifest_path=manifest_path, current_head=anchor, expected_anchor=anchor
    )
    assert at_anchor["status"] == "PASS"
    assert at_anchor["anchor_is_ancestor"] is True

    smoke = tmp_path / "configs" / "mdc_ml_f0_smoke_v1.yaml"
    smoke.write_text("smoke grid maintenance file\n", encoding="utf-8")
    subprocess.run(["git", "add", str(smoke.relative_to(tmp_path))], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "legal descendant"], cwd=tmp_path, check=True)
    descendant = _git(tmp_path, "rev-parse", "HEAD")
    result = audit_repository_freeze_contract(
        root=tmp_path, manifest_path=manifest_path, current_head=descendant, expected_anchor=anchor
    )
    assert descendant != anchor
    assert result["status"] == "PASS"
    assert result["anchor_is_ancestor"] is True
    assert result["payload_drift_count"] == 0
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["spec_freeze_anchor_commit"] == anchor


def test_missing_anchor_and_unrelated_head_fail(tmp_path):
    anchor, manifest_path = _make_freeze_repo(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    missing = "0" * 40
    manifest["spec_freeze_anchor_commit"] = missing
    missing_manifest = tmp_path / "missing_manifest.json"
    missing_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    missing_result = audit_repository_freeze_contract(
        root=tmp_path, manifest_path=missing_manifest, expected_anchor=missing
    )
    assert missing_result["status"] == "FAIL"
    assert missing_result["freeze_anchor_exists"] is False

    tree = _git(tmp_path, "rev-parse", "HEAD^{tree}")
    unrelated = _git(tmp_path, "commit-tree", tree, "-m", "unrelated root")
    unrelated_result = audit_repository_freeze_contract(
        root=tmp_path, manifest_path=manifest_path, current_head=unrelated, expected_anchor=anchor
    )
    assert unrelated_result["status"] == "FAIL"
    assert unrelated_result["freeze_anchor_exists"] is True
    assert unrelated_result["anchor_is_ancestor"] is False


def test_payload_drift_is_detected_and_extra_smoke_file_is_excluded(tmp_path):
    anchor, manifest_path = _make_freeze_repo(tmp_path)
    extra = tmp_path / "wavelength_grid_and_smoke.yaml"
    extra.write_text("not immutable spec payload\n", encoding="utf-8")
    clean = audit_repository_freeze_contract(
        root=tmp_path, manifest_path=manifest_path, expected_anchor=anchor
    )
    assert clean["status"] == "PASS"
    assert clean["payload_drift_count"] == 0

    changed = tmp_path / REQUIRED_IMMUTABLE_PAYLOAD[1]
    changed.write_bytes(changed.read_bytes() + b"drift\n")
    drift = audit_repository_freeze_contract(
        root=tmp_path, manifest_path=manifest_path, expected_anchor=anchor
    )
    assert drift["status"] == "FAIL"
    assert drift["payload_drift_count"] == 1
    failed = [row for row in drift["payloads"] if row["status"] == "FAIL"]
    assert [row["path"] for row in failed] == [REQUIRED_IMMUTABLE_PAYLOAD[1]]


def test_crlf_checkout_bytes_are_diagnostic_when_git_canonical_content_matches(tmp_path):
    anchor, manifest_path = _make_freeze_repo(tmp_path)
    relative = REQUIRED_IMMUTABLE_PAYLOAD[0]
    payload = tmp_path / relative
    payload.write_bytes(payload.read_bytes().replace(b"\n", b"\r\n"))

    result = audit_repository_freeze_contract(
        root=tmp_path, manifest_path=manifest_path, expected_anchor=anchor
    )
    row = next(item for item in result["payloads"] if item["path"] == relative)
    assert result["status"] == "PASS"
    assert row["raw_matches_anchor"] is False
    assert row["checkout_eol"] == "crlf"
    assert row["eol_normalization_applied"] is True
    assert row["git_canonical_matches_index"] is True
    assert row["unstaged_semantic_diff"] is False


def test_staged_payload_mutation_is_detected(tmp_path):
    anchor, manifest_path = _make_freeze_repo(tmp_path)
    relative = REQUIRED_IMMUTABLE_PAYLOAD[2]
    payload = tmp_path / relative
    payload.write_bytes(payload.read_bytes() + b"semantic drift\n")
    subprocess.run(["git", "add", "--", relative], cwd=tmp_path, check=True)

    result = audit_repository_freeze_contract(
        root=tmp_path, manifest_path=manifest_path, expected_anchor=anchor
    )
    row = next(item for item in result["payloads"] if item["path"] == relative)
    assert result["status"] == "FAIL"
    assert row["staged_diff"] is True
    assert row["index_sha256"] != row["expected_sha256"]


def test_descendant_commit_may_not_change_payload(tmp_path):
    anchor, manifest_path = _make_freeze_repo(tmp_path)
    relative = REQUIRED_IMMUTABLE_PAYLOAD[3]
    payload = tmp_path / relative
    payload.write_bytes(payload.read_bytes() + b"committed drift\n")
    subprocess.run(["git", "add", "--", relative], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "illegal payload drift"], cwd=tmp_path, check=True)

    result = audit_repository_freeze_contract(
        root=tmp_path, manifest_path=manifest_path, expected_anchor=anchor
    )
    row = next(item for item in result["payloads"] if item["path"] == relative)
    assert result["anchor_is_ancestor"] is True
    assert result["status"] == "FAIL"
    assert row["head_sha256"] != row["expected_sha256"]


def test_deleted_payload_is_detected(tmp_path):
    anchor, manifest_path = _make_freeze_repo(tmp_path)
    relative = REQUIRED_IMMUTABLE_PAYLOAD[4]
    (tmp_path / relative).unlink()

    result = audit_repository_freeze_contract(
        root=tmp_path, manifest_path=manifest_path, expected_anchor=anchor
    )
    row = next(item for item in result["payloads"] if item["path"] == relative)
    assert result["status"] == "FAIL"
    assert row["regular_file"] is False


def test_directory_replacement_is_detected_as_type_change(tmp_path):
    anchor, manifest_path = _make_freeze_repo(tmp_path)
    relative = REQUIRED_IMMUTABLE_PAYLOAD[5]
    payload = tmp_path / relative
    payload.unlink()
    payload.mkdir()

    result = audit_repository_freeze_contract(
        root=tmp_path, manifest_path=manifest_path, expected_anchor=anchor
    )
    row = next(item for item in result["payloads"] if item["path"] == relative)
    assert result["status"] == "FAIL"
    assert row["regular_file"] is False


def test_manifest_expected_sha_mutation_is_detected(tmp_path):
    anchor, manifest_path = _make_freeze_repo(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["immutable_payload"][0]["sha256"] = "f" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8", newline="\n")

    result = audit_repository_freeze_contract(
        root=tmp_path, manifest_path=manifest_path, expected_anchor=anchor
    )
    assert result["status"] == "FAIL"
    assert result["payload_drift_count"] == 1
    assert "manifest SHA-256 does not match freeze anchor payload" in "\n".join(
        result["errors"]
    )


def test_exact_lf_attributes_cover_only_contract_files():
    root = Path(__file__).resolve().parents[1]
    attributes = (root / ".gitattributes").read_text(encoding="utf-8")
    assert attributes == _lf_attributes_text()
    for relative in EXPECTED_LF_ATTRIBUTE_PATHS:
        result = _git(root, "check-attr", "text", "eol", "--", relative)
        assert f"{relative}: text: set" in result
        assert f"{relative}: eol: lf" in result


def test_core_autocrlf_true_clone_checks_out_contract_payloads_as_lf(tmp_path):
    source = tmp_path / "source"
    clone = tmp_path / "clone"
    source.mkdir()
    anchor, manifest_path = _make_freeze_repo(source)
    subprocess.run(
        ["git", "-c", "core.autocrlf=true", "clone", "-q", str(source), str(clone)],
        check=True,
    )
    clone_manifest = clone / manifest_path.relative_to(source)
    clone_manifest.write_bytes(manifest_path.read_bytes())
    result = audit_repository_freeze_contract(
        root=clone, manifest_path=clone_manifest, expected_anchor=anchor
    )
    assert result["status"] == "PASS"
    eol_inventory = _git(clone, "ls-files", "--eol", "--", *REQUIRED_IMMUTABLE_PAYLOAD)
    assert len(eol_inventory.splitlines()) == len(REQUIRED_IMMUTABLE_PAYLOAD)
    assert all("w/lf" in line for line in eol_inventory.splitlines())


def test_manifest_hashes_are_anchor_derived_and_not_current_head_derived():
    manifest = load_freeze_manifest()
    assert manifest["spec_freeze_anchor_commit"] == SPEC_FREEZE_ANCHOR_COMMIT
    assert tuple(row["path"] for row in manifest["immutable_payload"]) == REQUIRED_IMMUTABLE_PAYLOAD
    roles = (
        "inverse_design_specification",
        "dataset_schema",
        "structure_grammar_and_identity_contract",
        "frozen_specification_report",
        "p0_physics_and_data_contract_audit_report",
        "p0b_hash_and_objective_audit_report",
    )
    rebuilt = [
        {
            "path": path,
            "role": role,
            "sha256": git_payload_sha256(SPEC_FREEZE_ANCHOR_COMMIT, path),
            "immutable": True,
        }
        for path, role in zip(REQUIRED_IMMUTABLE_PAYLOAD, roles)
    ]
    assert rebuilt == manifest["immutable_payload"]
    for row in rebuilt:
        assert len(row["sha256"]) == 64
        int(row["sha256"], 16)


def test_legacy_verify_head_true_means_repository_contract_not_exact_equality():
    result = run_audit(verify_head=True)
    assert result["status"] == "PASS"
    assert result["repository_contract_status"] == "PASS"
    assert result["repository_contract"]["head_policy"] == "descendant_or_equal"
