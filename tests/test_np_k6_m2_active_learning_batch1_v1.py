import importlib.util
import json
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
VALIDATOR = ROOT / "scripts" / "validate_np_k6_m2_active_learning_batch1_v1.py"
OUT = ROOT / "outputs" / "np_k6_m2_active_learning_batch1_selection_v1"


def load_validator():
    spec = importlib.util.spec_from_file_location("m2_batch1_validator", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_m2_batch1_validator_passes():
    result = load_validator().validate()
    assert result["status"] == "PASS", result


def test_batch1_has_exactly_six_and_twelve():
    selected = list(__import__("csv").DictReader((OUT / "batch1_selected_geometries.csv").open(encoding="utf-8")))
    tasks = json.loads((OUT / "batch1_task_manifest.json").read_text(encoding="utf-8"))["tasks"]
    assert len(selected) == 6
    assert len(tasks) == 12


def test_batch1_tasks_are_planned_only():
    tasks = json.loads((OUT / "batch1_task_manifest.json").read_text(encoding="utf-8"))["tasks"]
    assert all(t["entered"] is False for t in tasks)
    assert all(t["run_invocation_count"] == 0 for t in tasks)
    assert all(t["solver_authorized"] is False for t in tasks)
    assert all(t["training_label"] is False for t in tasks)
    assert all(t["sealed"] is False for t in tasks)


def test_no_sealed_or_existing_formal_geometry_selected():
    pool = json.loads((OUT / "candidate_pool_audit.json").read_text(encoding="utf-8"))
    assert pool["sealed_access"] == 0
    assert pool["eligible_unlabeled_development"] == 45
    selected = list(__import__("csv").DictReader((OUT / "batch1_selected_geometries.csv").open(encoding="utf-8")))
    assert len({r["geometry_hash"] for r in selected}) == 6


def test_acquisition_committee_provenance():
    for name in ["cnn_ensemble_provenance.json", "mlp_ensemble_manifest.json"]:
        obj = json.loads((OUT / name).read_text(encoding="utf-8"))
        assert obj["purpose"] == "ACQUISITION_ONLY"
        assert obj["sealed_access"] == 0
        assert obj["solver_calls"] == 0
