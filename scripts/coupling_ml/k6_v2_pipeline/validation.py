"""Geometry-grouped OOF metrics for the frozen K6 V2 learning curves.

This module reports outer-fold validation only. It never chooses model settings
from outer-fold truth and never opens sealed confirmation responses.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

import numpy as np

from .contracts import CaseCollection
from .training import FitPlan, FitRun


def evaluate_learning_curve_oof(
    collection: CaseCollection,
    plan: FitPlan,
    runs: Sequence[FitRun],
    *,
    decoder=None,
) -> dict[str, Any]:
    """Join saved 32/64/128 curve predictions and apply the frozen H1 evaluator.

    Outer validation labels are read only here, after each fit is complete. The
    fixed 4-way geometry split yields 128 development OOF geometries. Every
    prediction bundle is joined by case ID; positional zip alignment is rejected.
    """
    if collection.purpose != "development":
        raise ValueError("learning_curve_evaluation_requires_development_collection")
    truth_by_id = {case.case_id: case for case in collection.training_cases()}
    if set(truth_by_id) != set(plan.development_case_ids):
        raise ValueError("development_collection_plan_case_id_mismatch")
    expected_outer_ids = set().union(*(set(v) for v in plan.outer_validation_ids.values()))
    if len(expected_outer_ids) != 128 or not expected_outer_ids.issubset(truth_by_id):
        raise ValueError("frozen_outer_validation_must_cover_exact_128_dev_geometries")

    templates = {t.task_id: t for t in plan.curve_templates}
    curve_runs = [r for r in runs if r.task.phase == "learning_curve"]
    if len(curve_runs) != len(templates) or {r.task.task_id for r in curve_runs} != set(templates):
        raise ValueError("learning_curve_fit_set_missing_duplicate_or_extra")

    by_key: dict[tuple[str, int, int, int | None], FitRun] = {}
    for run in curve_runs:
        task = run.task
        template = templates[task.task_id]
        if task.model_kind != template.model_kind or task.train_case_ids != template.train_case_ids:
            raise ValueError("learning_curve_training_manifest_mismatch:" + task.task_id)
        if task.training_geometry_count != template.training_geometry_count:
            raise ValueError("learning_curve_training_size_mismatch:" + task.task_id)
        outer = int(task.outer_fold)
        if task.config_source != f"outer_{outer}_inner_cv_min_mean_loss":
            raise ValueError("learning_curve_config_not_selected_inside_outer_train:" + task.task_id)
        if task.model_kind == "CARTESIAN_MLP":
            expected_updates = f"outer_{outer}_seed{task.seed}_floor_median_3_inner_best"
            if task.update_source != expected_updates:
                raise ValueError("learning_curve_updates_not_selected_inside_outer_train:" + task.task_id)
        val_ids = tuple(plan.outer_validation_ids[outer])
        if set(task.prediction_case_ids) != set(val_ids) or len(task.prediction_case_ids) != len(val_ids):
            raise ValueError("learning_curve_prediction_ids_not_fixed_outer_validation:" + task.task_id)
        if set(task.train_case_ids) & set(val_ids):
            raise ValueError("learning_curve_train_outer_validation_overlap:" + task.task_id)
        if run.predicted_c_hat is None or run.predicted_p_scale is None:
            raise ValueError("learning_curve_prediction_artifact_missing:" + task.task_id)
        c = np.asarray(run.predicted_c_hat, dtype=np.complex128)
        p = np.asarray(run.predicted_p_scale, dtype=np.float64)
        n = len(task.prediction_case_ids)
        if c.shape != (n, 21, 7, 2) or p.shape != (n, 21):
            raise ValueError("learning_curve_prediction_shape_invalid:" + task.task_id)
        if not (np.isfinite(c.real).all() and np.isfinite(c.imag).all()):
            raise ValueError("learning_curve_c_hat_prediction_nonfinite:" + task.task_id)
        if not np.isfinite(p).all() or (p <= 0.0).any():
            raise ValueError("learning_curve_p_scale_prediction_invalid:" + task.task_id)
        if task.model_kind == "RBF_KRR":
            key = ("RBF_KRR", outer, task.training_geometry_count, None)
        elif task.model_kind == "CARTESIAN_MLP":
            if task.seed not in (0, 1, 2):
                raise ValueError("learning_curve_mlp_seed_invalid:" + task.task_id)
            key = ("CARTESIAN_MLP", outer, task.training_geometry_count, int(task.seed))
        else:
            raise ValueError("learning_curve_candidate_not_frozen:" + task.model_kind)
        if key in by_key:
            raise ValueError("learning_curve_duplicate_prediction_run:" + task.task_id)
        by_key[key] = run

    from .h1 import evaluate_original_h1

    output: dict[str, Any] = {
        "schema": "COUPLING_ML_K6_V2_LEARNING_CURVE_OOF_EVALUATION_V1",
        "scope": "development_oof_only_not_confirmation_or_production_admission",
        "outer_validation_geometry_count": len(expected_outer_ids),
        "wavelengths_grouped_by_geometry": True,
        "outer_fold_ids": sorted(plan.outer_validation_ids),
        "training_sizes_are_actual_geometry_counts": [32, 64, 128],
        "confirmation_responses_opened": False,
        "production_admission": False,
        "results": {},
    }
    ordered_ids = tuple(sorted(expected_outer_ids))
    for model_kind in ("RBF_KRR", "CARTESIAN_MLP"):
        output["results"][model_kind] = {}
        seed_ids = (None,) if model_kind == "RBF_KRR" else (0, 1, 2)
        for size in (32, 64, 128):
            prediction_by_seed: dict[int | None, dict[str, tuple[np.ndarray, np.ndarray]]] = {
                seed: {} for seed in seed_ids
            }
            fit_diagnostics: list[dict[str, Any]] = []
            fold_summaries: dict[int, Any] = {}
            for outer in sorted(plan.outer_validation_ids):
                fold_ids = tuple(plan.outer_validation_ids[outer])
                for seed in seed_ids:
                    key = (model_kind, outer, size, seed)
                    if key not in by_key:
                        raise ValueError(f"learning_curve_expected_fit_missing:{key}")
                    run = by_key[key]
                    fit_diagnostics.append({
                        "task_id": run.task.task_id,
                        "outer_fold": outer,
                        "training_geometry_count": size,
                        "seed": seed,
                        "training_loss": float(run.training_loss),
                        "best_update": int(run.best_update),
                        "actual_updates": int(run.actual_updates),
                        "input_sha256": run.input_sha256,
                    })
                    loc = {cid: i for i, cid in enumerate(run.prediction_case_ids)}
                    for cid in fold_ids:
                        if cid not in loc:
                            raise ValueError("learning_curve_case_id_join_failed:" + cid)
                        i = loc[cid]
                        prediction_by_seed[seed][cid] = (
                            np.asarray(run.predicted_c_hat[i], dtype=np.complex128),
                            np.asarray(run.predicted_p_scale[i], dtype=np.float64),
                        )
                if model_kind == "RBF_KRR":
                    seed_fold = (None,)
                else:
                    seed_fold = (0, 1, 2)
                ctrue = np.asarray([truth_by_id[cid].c_hat for cid in fold_ids], dtype=np.complex128)
                ptrue = np.asarray([truth_by_id[cid].p_scale for cid in fold_ids], dtype=np.float64)
                etrue = np.asarray([truth_by_id[cid].eta for cid in fold_ids], dtype=np.float64)
                atrue = np.asarray([truth_by_id[cid].absolute_order for cid in fold_ids], dtype=np.float64)
                cp = np.stack([
                    np.stack([prediction_by_seed[s][cid][0] for cid in fold_ids], axis=0)
                    for s in seed_fold
                ], axis=0)
                pp = np.stack([
                    np.stack([prediction_by_seed[s][cid][1] for cid in fold_ids], axis=0)
                    for s in seed_fold
                ], axis=0)
                fold_summaries[outer] = evaluate_original_h1(
                    ctrue, cp, ptrue, pp, etrue, atrue, decoder=decoder
                )

            ctrue = np.asarray([truth_by_id[cid].c_hat for cid in ordered_ids], dtype=np.complex128)
            ptrue = np.asarray([truth_by_id[cid].p_scale for cid in ordered_ids], dtype=np.float64)
            etrue = np.asarray([truth_by_id[cid].eta for cid in ordered_ids], dtype=np.float64)
            atrue = np.asarray([truth_by_id[cid].absolute_order for cid in ordered_ids], dtype=np.float64)
            cp = np.stack([
                np.stack([prediction_by_seed[s][cid][0] for cid in ordered_ids], axis=0)
                for s in seed_ids
            ], axis=0)
            pp = np.stack([
                np.stack([prediction_by_seed[s][cid][1] for cid in ordered_ids], axis=0)
                for s in seed_ids
            ], axis=0)
            pooled = evaluate_original_h1(ctrue, cp, ptrue, pp, etrue, atrue, decoder=decoder)
            output["results"][model_kind][str(size)] = {
                "pooled_128_geometry_oof": pooled,
                "per_outer_fold": fold_summaries,
                "fit_diagnostics": fit_diagnostics,
                "training_case_ids_by_outer_fold": {
                    str(o): list(next(r.task.train_case_ids for r in curve_runs
                                      if r.task.model_kind == model_kind
                                      and r.task.outer_fold == o
                                      and r.task.training_geometry_count == size))
                    for o in sorted(plan.outer_validation_ids)
                },
            }
    return output
