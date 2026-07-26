from __future__ import annotations

from pathlib import Path

from mdc_ml.merge_retrain_v1.artifacts import ArtifactPolicy, AtomicArtifactStore
from mdc_ml.merge_retrain_v1.classification import (
    CLASSIFICATION_TARGETS, build_classification_crossfit_plan,
    load_classification_metadata, synthetic_classification_fixture,
)
from mdc_ml.merge_retrain_v1.contracts import ROOT, load_frozen_contract


def test_metadata_plan_is_pure_and_exact_once():
    contract=load_frozen_contract(); meta=load_classification_metadata(contract); plans=build_classification_crossfit_plan(meta,contract)
    assert CLASSIFICATION_TARGETS == contract.targets.classification_targets
    assert meta.counts["merged_classification"] == 2640 and meta.counts["round1_classification"] == 128
    assert len(plans)==4 and sum(len(p.held_out_indices) for p in plans)==128
    assert not any(set(p.train_indices)&set(p.held_out_indices) for p in plans)
    assert all(p.feature_signature==contract.feature_signature for p in plans)


def test_synthetic_fixture_executes_full_classification_path(tmp_path: Path):
    # tmp_path is permitted fixture-only storage, outside the worktree.
    contract=load_frozen_contract()
    result=synthetic_classification_fixture(contract,tmp_path,"pytest-classification")
    audit=result["audit"]
    assert result["status"]=="PASS"
    assert audit["synthetic_classification_fit_calls"]>0 and audit["synthetic_calibrator_fit_calls"]>0
    assert audit["formal_classification_fit_calls"]==audit["regression_fit_calls"]==audit["MLP_fit_calls"]==0
    assert audit["exact_once"] and audit["fresh_process_result"]=="PASS"
