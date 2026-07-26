from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_mdc_ml_active_learning_merge_retrain_v1.py"
SPEC = importlib.util.spec_from_file_location("merge_builder", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def temporary_config(tmp_path: Path, output_root: Path) -> Path:
    config = json.loads((ROOT / "configs" / "mdc_ml_active_learning_merge_retrain_v1.yaml").read_text())
    config["output_root"] = str(output_root)
    path = tmp_path / "merge_retrain_test_config.json"
    path.write_text(json.dumps(config, sort_keys=True), encoding="utf-8")
    return path


def test_pretraining_promotion_contract_is_quantified_and_closed():
    cfg = json.loads((ROOT / "configs" / "mdc_ml_active_learning_merge_retrain_v1.yaml").read_text())
    contract = cfg["development_promotion_contract"]
    assert contract["promotion_contract_id"] == "mdc_ml_merge_retrain_development_promotion_v1"
    assert contract["bootstrap"] == {"method": "paired_group_bootstrap", "replicates": 2000, "seed": 20260723, "confidence_level": 0.80, "grouping_priority": ["parent_or_anchor", "canonical_source_group", "geometry_hash"]}
    assert contract["validation_non_degradation"] == {"roc_auc": {"direction": "higher", "minimum_delta": -0.020}, "pr_auc": {"direction": "higher", "minimum_delta": -0.020}, "balanced_accuracy": {"direction": "higher", "minimum_delta": -0.020}, "mean_spearman": {"direction": "higher", "minimum_delta": -0.030}, "brier": {"direction": "lower", "maximum_delta": 0.015}, "mean_iqr_nmae": {"direction": "lower", "maximum_delta": 0.050}}
    assert contract["required_improvement"] == {"pr_auc": {"direction": "higher", "minimum_delta": 0.030}, "brier": {"direction": "lower", "maximum_delta": -0.020}, "mean_spearman": {"direction": "higher", "minimum_delta": 0.040}, "mean_iqr_nmae": {"direction": "lower", "maximum_delta": -0.050}, "bootstrap_interval_must_be_favorable": True}
    assert contract["subgroup_guard"]["classification_minimum_n"] == 8
    assert contract["subgroup_guard"]["regression_minimum_n"] == 6
    assert contract["subgroup_guard"]["insufficient_support_status"] == "INSUFFICIENT_SUBGROUP_SUPPORT"
    assert {"validation_non_degradation", "one_required_improvement", "sealed_test_non_use", "fresh_process_artifact_roundtrip"} <= set(contract["mandatory_gates"])
    assert set(contract) == {"promotion_contract_id", "bootstrap", "validation_non_degradation", "required_improvement", "subgroup_guard", "calibration_conformal_guard", "mandatory_gates", "decision_order"}


def test_validate_only_is_pure_read_and_idempotent():
    cfg = ROOT / "configs" / "mdc_ml_active_learning_merge_retrain_v1.yaml"
    output_root = ROOT / json.loads(cfg.read_text())["output_root"]
    before = MODULE.output_tree(output_root)
    first = MODULE.validate_existing(cfg)
    middle = MODULE.output_tree(output_root)
    second = MODULE.validate_existing(cfg)
    after = MODULE.output_tree(output_root)
    assert first["status"] == second["status"] == "PASS"
    assert before == middle == after


def test_validate_only_missing_directory_fails_without_creating_it(tmp_path: Path):
    missing = tmp_path / "does-not-exist"
    with pytest.raises(RuntimeError, match="missing merged outputs"):
        MODULE.validate_existing(temporary_config(tmp_path, missing))
    assert not missing.exists()


@pytest.mark.parametrize("artifact, mutate", [
    ("merged_registry_v1.jsonl", lambda path: path.write_text("\n".join(path.read_text().splitlines()[:-1]) + "\n", encoding="utf-8")),
    ("adaptive_crossfit_audit_v1.json", lambda path: path.write_text(json.dumps({**json.loads(path.read_text()), "fold_signature": "drift"}), encoding="utf-8")),
    ("sealed_test_non_use_audit_v1.json", lambda path: path.write_text(json.dumps({**json.loads(path.read_text()), "sealed_test_targets_used": True}), encoding="utf-8")),
])
def test_validate_only_rejects_drift_without_repair(tmp_path: Path, artifact: str, mutate):
    source = ROOT / "outputs" / "mdc_ml_active_learning_merge_retrain_v1"
    copied = tmp_path / "copied-output"
    shutil.copytree(source, copied)
    mutate(copied / artifact)
    before = MODULE.output_tree(copied)
    with pytest.raises(RuntimeError, match="merged output validation failed"):
        MODULE.validate_existing(temporary_config(tmp_path, copied))
    assert MODULE.output_tree(copied) == before


def test_build_mode_smoke_uses_only_a_temporary_output_directory(tmp_path: Path):
    output_root = tmp_path / "build-output"
    cfg = temporary_config(tmp_path, output_root)
    assert MODULE.build(cfg)["status"] == "PASS"
    assert MODULE.validate_existing(cfg)["status"] == "PASS"
    assert MODULE.output_tree(output_root)["file_count"] == 10


def test_validate_only_path_does_not_call_build_function_or_serializers():
    source = SCRIPT.read_text()
    validate_source = source[source.index("def validate_existing"):source.index("def main")]
    assert "result = validate_existing(args.config) if args.validate_only else build(args.config)" in source
    assert "out.mkdir" not in validate_source
    assert "write_json" not in validate_source
    assert "write_jsonl" not in validate_source
    assert "write_csv" not in validate_source


def test_training_execution_contract_is_complete_and_frozen():
    cfg = ROOT / "configs" / "mdc_ml_active_learning_merge_retrain_v1.yaml"
    result = MODULE.validate_existing(cfg)
    assert result["status"] == "PASS"
    assert result["promotion_contract_sha256"] == "71b43c40035bb49a0a9647734b8aa4b42f7a089aa9c354de0b2a90f0c93def52"
    assert len(result["training_execution_contract_sha256"]) == 64
    assert all(result["checks"].values())


def test_execution_contract_source_references_and_candidates_are_closed():
    cfg = json.loads((ROOT / "configs" / "mdc_ml_active_learning_merge_retrain_v1.yaml").read_text())
    contract = MODULE.training_execution_contract(cfg)
    assert all(MODULE.validate_source_references(contract))
    allow = contract["model_candidate_allowlist"]
    bounded = contract["bounded_recompetition_candidate_set"]
    assert {"extra_trees_1"} <= set(bounded["classification_candidate_ids"])
    assert {"multitask_mlp_3seed"} <= set(bounded["regression_candidate_ids"])
    assert contract["fixed_v1_architecture_retrain"]["classification"]["candidate_id"] == "extra_trees_1"
    assert contract["fixed_v1_architecture_retrain"]["regression"]["candidate_id"] == "multitask_mlp_3seed"
    assert contract["training_seeds"]["regressor_ensemble_seeds"] == [20260720, 20260721, 20260722]
    assert contract["target_transforms"]["canonical_4d_targets"] == cfg["regression_targets"]
    assert not MODULE.has_unresolved_placeholder(contract)
    assert len(allow["classification"]) == len({item["candidate_id"] for item in allow["classification"]})
    assert len(allow["regression"]) == len({item["candidate_id"] for item in allow["regression"]})


def test_execution_contract_rejects_unknown_drift_and_unsafe_rules(tmp_path: Path):
    cfg = json.loads((ROOT / "configs" / "mdc_ml_active_learning_merge_retrain_v1.yaml").read_text())
    output = ROOT / cfg["output_root"]
    for mutate in (
        lambda value: value["bounded_recompetition_candidate_set"]["classification_candidate_ids"].append("unknown"),
        lambda value: value["model_candidate_allowlist"]["classification"][0]["hyperparameters"].update({"strategy": "most_frequent"}),
        lambda value: value["target_transforms"].update({"canonical_4d_targets": list(reversed(value["regression_targets"]))}),
        lambda value: value["training_seeds"].update({"regressor_ensemble_seeds": [20260720, 20260721]}),
        lambda value: value["early_stopping"].update({"validation_source": "original calibration"}),
        lambda value: value["contract_revision"].update({"first_training_started": True}),
    ):
        altered = json.loads(json.dumps(cfg)); mutate(altered)
        checks = MODULE.validate_training_execution_contract(altered, output)
        assert not all(checks.values())
    with pytest.raises(RuntimeError, match="unknown promotion decision"):
        MODULE.resolve_route_rules(cfg["route_rules"], "unknown")
    assert MODULE.resolve_route_rules(cfg["route_rules"], "RETAIN_V1_FOR_NEXT_PROPOSAL")["proposal_model"] == "v1"
    assert MODULE.resolve_route_rules(cfg["route_rules"], "PROMOTE_DEV_CHAMPION_V2")["proposal_model"] == "v2"
    assert MODULE.resolve_route_rules(cfg["route_rules"], "RETAIN_V1_FOR_NEXT_PROPOSAL", data_contract_failure=True)["routes"] == ["NEED_DATA_CONTRACT_REVIEW"]
