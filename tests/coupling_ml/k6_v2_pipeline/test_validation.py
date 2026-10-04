from dataclasses import replace

import numpy as np
import pytest

from scripts.coupling_ml.k6_v2_pipeline import h1 as h1_module
from scripts.coupling_ml.k6_v2_pipeline.contracts import (
    CaseCollection, CaseTruth, ROLE_GLOBAL_DEV, ROLE_OLD32,
)
from scripts.coupling_ml.k6_v2_pipeline.training import FitCounts, FitPlan, FitRun, FitTask
from scripts.coupling_ml.k6_v2_pipeline.validation import evaluate_learning_curve_oof


def _fixture():
    ids = tuple([f"OLD{i:02d}" for i in range(32)] + [f"NEW{i:03d}" for i in range(128)])
    roles = {cid: (ROLE_OLD32 if cid.startswith("OLD") else ROLE_GLOBAL_DEV) for cid in ids}
    geometry = {cid: (100 + (i % 27), 105 + (i % 23), 110 + (i % 19),
                      115 + (i % 17), 120 + (i % 13), 125 + (i % 11))
                for i, cid in enumerate(ids)}
    cases = []
    for cid in ids:
        eta = np.full((21, 7), 1.0 / 7.0)
        p = np.ones(21)
        cases.append(CaseTruth(cid, "attempt_001", roles[cid], geometry[cid],
                               np.full((21, 7, 2), 1e-3 + 0j), p, eta,
                               eta.copy(), {"synthetic_test_only": True}))
    collection = CaseCollection("development", tuple(cases), "fixture", {"synthetic_test_only": True})

    outer = {f: tuple(f"NEW{i:03d}" for i in range((f - 1) * 32, f * 32))
             for f in range(1, 5)}
    templates, runs = [], []
    for fold in range(1, 5):
        validation_ids = outer[fold]
        train_pool = tuple(cid for cid in ids if cid not in set(validation_ids))
        old = tuple(cid for cid in train_pool if cid.startswith("OLD"))
        new_train = tuple(cid for cid in train_pool if cid.startswith("NEW"))
        for size in (32, 64, 128):
            train_ids = old if size == 32 else old + new_train[:32] if size == 64 else train_pool
            assert len(train_ids) == size
            for model_kind, seeds in (("RBF_KRR", (None,)), ("CARTESIAN_MLP", (0, 1, 2))):
                for seed in seeds:
                    task_id = (f"curve_o{fold}_n{size}_krr" if seed is None
                               else f"curve_o{fold}_n{size}_mlp_s{seed}")
                    task = FitTask(
                        task_id=task_id, phase="learning_curve", model_kind=model_kind,
                        outer_fold=fold, inner_fold=None,
                        training_geometry_count=size, train_case_ids=train_ids,
                        prediction_case_ids=validation_ids, gamma=1.0/6 if seed is None else None,
                        ridge_alpha=1e-2 if seed is None else None,
                        weight_decay=None if seed is None else 1e-4, seed=seed,
                        fixed_updates=None if seed is None else 5,
                        config_source=f"outer_{fold}_inner_cv_min_mean_loss",
                        update_source=None if seed is None else f"outer_{fold}_seed{seed}_floor_median_3_inner_best")
                    templates.append(task)
                    n = len(validation_ids)
                    runs.append(FitRun(
                        task=task, model=None, x_scaler=None, target_scaler=None,
                        input_sha256="0" * 64, training_loss=0.0, validation_loss=None,
                        best_update=0 if seed is None else 5, actual_updates=0 if seed is None else 5,
                        prediction_case_ids=validation_ids,
                        predicted_c_hat=np.full((n, 21, 7, 2), 1e-3 + 0j),
                        predicted_p_scale=np.ones((n, 21))))
    plan = FitPlan(
        repository_root="fixture", development_case_ids=ids,
        development_role_by_id=roles, geometry_by_id=geometry,
        outer_validation_ids=outer, inner_tasks=(), curve_templates=tuple(templates),
        final_templates=(), local_tasks=(), counts=FitCounts(0, 0, 0, 0, 0, 0, 0),
        source_hashes={"fixture": "0" * 64})
    return collection, plan, runs


def test_learning_curve_oof_joins_exact_geometry_ids_and_reports_both_candidates(monkeypatch):
    collection, plan, runs = _fixture()
    calls = []
    def fake_h1(*args, decoder=None):
        calls.append((args[0].shape[0], args[1].shape[0]))
        return {"synthetic_test_only": True, "gates": {"state": False}}
    monkeypatch.setattr(h1_module, "evaluate_original_h1", fake_h1)
    report = evaluate_learning_curve_oof(collection, plan, runs)
    assert report["outer_validation_geometry_count"] == 128
    assert report["confirmation_responses_opened"] is False
    assert set(report["results"]) == {"RBF_KRR", "CARTESIAN_MLP"}
    assert set(report["results"]["RBF_KRR"]) == {"32", "64", "128"}
    assert set(report["results"]["CARTESIAN_MLP"]) == {"32", "64", "128"}
    assert len(calls) == 30  # 6 candidate/size groups x (4 folds + pooled)


def test_learning_curve_oof_rejects_outer_selected_configuration(monkeypatch):
    collection, plan, runs = _fixture()
    task = runs[0].task
    runs[0].task = replace(task, config_source="selected_from_outer_validation")
    monkeypatch.setattr(h1_module, "evaluate_original_h1",
                        lambda *args, **kwargs: {"synthetic_test_only": True})
    with pytest.raises(ValueError, match="config_not_selected_inside_outer_train"):
        evaluate_learning_curve_oof(collection, plan, runs)
