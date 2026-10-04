import numpy as np
import pytest

from scripts.coupling_ml.k6_v2_pipeline.contracts import MODEL_OUTPUTS, pack_model_target
from scripts.coupling_ml.k6_v2_pipeline.models import (
    CartesianMLP, GeometryStandardizer, V2TargetNormalizer, mlp_parameter_count,
    unpack_prediction,
)
from scripts.coupling_ml.k6_v2_pipeline.training import (
    FitTask, SYNTHETIC_TEST_ONLY, _load_cached_fit, _save_fit_run, build_fit_plan,
    fit_arrays, floor_median_updates, reset_synthetic_test_fit_counts,
    seed_mean_predictions, synthetic_test_fit_counts,
)


def _synthetic_targets(n, seed=42):
    rng = np.random.default_rng(seed)
    c = rng.normal(size=(n, 21, 7, 2)) + 1j * rng.normal(size=(n, 21, 7, 2))
    p = np.exp(rng.normal(loc=-0.5, scale=0.25, size=(n, 21)))
    return np.concatenate([pack_model_target(c[i], p[i]) for i in range(n)], axis=0)


def test_frozen_mlp_shape_and_parameter_count():
    import torch
    model = CartesianMLP(seed=0)
    assert mlp_parameter_count() == 21377
    assert model.parameter_count() == 21377
    assert tuple(model(torch.zeros((4, 6), dtype=torch.float32)).shape) == (4, MODEL_OUTPUTS)


def test_train_only_normalizers_roundtrip_and_loss():
    train = _synthetic_targets(8)
    x = np.arange(48, dtype=float).reshape(8, 6)
    xs = GeometryStandardizer.fit(x)
    assert np.allclose(xs.mean, x.mean(axis=0))
    assert np.allclose(xs.scale, x.std(axis=0))
    scaler = V2TargetNormalizer.fit(train)
    normalized = scaler.transform(train)
    assert np.allclose(scaler.inverse_transform(normalized), train, rtol=1e-12, atol=1e-12)
    assert scaler.loss_components(normalized, normalized) == (0.0, 0.0, 0.0)
    # Held-out values are never an argument to fit and cannot alter train statistics.
    extreme_heldout = _synthetic_targets(1, seed=999) * 1e6
    scaler_again = V2TargetNormalizer.fit(train.copy())
    assert np.array_equal(scaler.c_mean, scaler_again.c_mean)
    assert scaler.log_p_mean == scaler_again.log_p_mean
    assert scaler.log_p_std == scaler_again.log_p_std
    assert extreme_heldout.shape == (1, MODEL_OUTPUTS)


def test_schedule_is_exact_281_fits_and_geometry_grouped():
    plan = build_fit_plan()
    assert len(plan.development_case_ids) == 160
    assert [len(ids) for ids in plan.outer_validation_ids.values()] == [32] * 4
    assert plan.counts.to_dict() == {
        "inner_krr": 108, "inner_mlp": 108,
        "learning_curve_krr": 12, "learning_curve_mlp": 36,
        "final_global": 4, "local_affine": 13, "total": 281,
    }
    assert plan.counts.total <= 284
    for outer in range(1, 5):
        assert {t.training_geometry_count for t in plan.curve_templates if t.outer_fold == outer} == {32, 64, 128}
        inner = [t for t in plan.inner_tasks if t.outer_fold == outer]
        assert len(inner) == 54
        assert all(not (set(t.train_case_ids) & set(t.prediction_case_ids)) for t in inner)
    assert plan.to_summary()["confirmation_responses_opened"] is False


def test_refit_update_rule_is_floor_median():
    assert floor_median_updates([11, 20, 30]) == 20
    assert floor_median_updates([11, 20, 31, 41]) == 25
    with pytest.raises(ValueError, match="invalid_inner_best_update_values"):
        floor_median_updates([0, 1001])


def test_production_entrypoints_reject_unadmitted_tasks_before_truth_access(tmp_path):
    from dataclasses import replace
    from types import SimpleNamespace
    from scripts.coupling_ml.k6_v2_pipeline.training import PRODUCTION, run_fit_task

    plan = build_fit_plan()
    task = plan.inner_tasks[0]
    X = np.zeros((task.training_geometry_count, 6), dtype=np.float64)
    Y = _synthetic_targets(task.training_geometry_count, seed=17)
    with pytest.raises(ValueError, match="public_array_fitting_is_synthetic_test_only"):
        fit_arrays(task, X, Y, run_purpose=PRODUCTION)

    tampered_task = replace(task, task_id=task.task_id + "_forged")
    with pytest.raises(ValueError, match="scheduled_inner_task_not_in_frozen_plan"):
        run_fit_task(tampered_task, {}, tmp_path)

    class MetadataOnlyCase:
        def __init__(self, case_id, role, geometry):
            self.case_id = case_id
            self.role = role
            self.ordered_D_nm = geometry

        @property
        def c_hat(self):
            raise AssertionError("truth_response_read_before_admission")

        @property
        def p_scale(self):
            raise AssertionError("truth_response_read_before_admission")

    fabricated_confirmation = MetadataOnlyCase(
        "SEALED_CONFIRMATION_FAKE", "SEALED_CONFIRMATION_GLOBAL", (100, 100, 100, 100, 100, 100)
    )
    with pytest.raises(ValueError, match="development_case_allowlist_mismatch"):
        run_fit_task(task, {fabricated_confirmation.case_id: fabricated_confirmation}, tmp_path)

    development_cases = {
        case_id: MetadataOnlyCase(
            case_id, plan.development_role_by_id[case_id], plan.geometry_by_id[case_id]
        )
        for case_id in plan.development_case_ids
    }
    first_id = plan.development_case_ids[0]
    development_cases[first_id].role = "SEALED_CONFIRMATION_GLOBAL"
    with pytest.raises(ValueError, match="development_case_role_mismatch"):
        run_fit_task(task, development_cases, tmp_path)

    development_cases[first_id].role = plan.development_role_by_id[first_id]
    development_cases[first_id].ordered_D_nm = (999, 999, 999, 999, 999, 999)
    with pytest.raises(ValueError, match="development_ordered_geometry_mismatch"):
        run_fit_task(task, development_cases, tmp_path)


def test_synthetic_only_fits_and_hash_checked_checkpoint(tmp_path):
    from scripts.coupling_ml.k6_v2_pipeline.models import RBFKRR
    rng = np.random.default_rng(7)
    X = rng.normal(size=(8, 6))
    Y = _synthetic_targets(8, seed=7)
    Xv = rng.normal(size=(2, 6))
    Yv = _synthetic_targets(2, seed=8)
    reset_synthetic_test_fit_counts()

    kt = FitTask(
        task_id="synthetic_krr", phase="inner", model_kind="RBF_KRR",
        outer_fold=1, inner_fold=1, training_geometry_count=8,
        train_case_ids=tuple(f"tr{i}" for i in range(8)),
        prediction_case_ids=("v0", "v1"), gamma=1.0/6.0, ridge_alpha=1e-2,
    )
    kr = fit_arrays(kt, X, Y, X_validation=Xv, Y_validation=Yv,
                    X_prediction=Xv, prediction_case_ids=("v0", "v1"),
                    run_purpose=SYNTHETIC_TEST_ONLY)
    assert kr.synthetic_test_only and kr.validation_loss is not None
    assert kr.predicted_c_hat.shape == (2, 21, 7, 2)
    assert kr.predicted_p_scale.shape == (2, 21)
    cache = tmp_path / "synthetic_checkpoint"
    _save_fit_run(kr, cache, kr.input_sha256)
    assert _load_cached_fit(kt, cache, kr.input_sha256) is not None
    with (cache / "predictions.npz").open("ab") as stream:
        stream.write(b"tamper")
    with pytest.raises(ValueError, match="fit_checkpoint_provenance_mismatch"):
        _load_cached_fit(kt, cache, kr.input_sha256)

    import torch
    mt = FitTask(
        task_id="synthetic_mlp_resume", phase="learning_curve", model_kind="CARTESIAN_MLP",
        outer_fold=1, inner_fold=None, training_geometry_count=8,
        train_case_ids=tuple(f"tr{i}" for i in range(8)),
        prediction_case_ids=("v0", "v1"), weight_decay=1e-4, seed=0, fixed_updates=5,
    )
    progress_path = tmp_path / "mlp-progress.pt"
    interrupted_updates = []

    def interrupt_after_three(step):
        interrupted_updates.append(step)
        if step == 3:
            raise RuntimeError("synthetic_interruption")

    with pytest.raises(RuntimeError, match="synthetic_interruption"):
        fit_arrays(
            mt, X, Y, X_prediction=Xv, prediction_case_ids=("v0", "v1"),
            run_purpose=SYNTHETIC_TEST_ONLY, checkpoint_path=progress_path,
            after_optimizer_update=interrupt_after_three,
        )
    assert interrupted_updates == [1, 2, 3]
    progress = torch.load(progress_path, map_location="cpu", weights_only=False)
    assert progress["completed_updates"] == 3
    assert [int(row["step"]) for row in progress["history"]] == [1, 2, 3]
    assert progress["task_sha256"] == mt.fingerprint()

    resumed = fit_arrays(
        mt, X, Y, X_prediction=Xv, prediction_case_ids=("v0", "v1"),
        run_purpose=SYNTHETIC_TEST_ONLY, checkpoint_path=progress_path,
    )
    reference = fit_arrays(
        mt, X, Y, X_prediction=Xv, prediction_case_ids=("v0", "v1"),
        run_purpose=SYNTHETIC_TEST_ONLY,
    )
    assert resumed.synthetic_test_only
    assert resumed.actual_updates == resumed.best_update == 5
    assert resumed.resumed_from_update == 3
    assert resumed.resume_count == 1
    assert resumed.optimizer_updates_this_invocation == 2
    assert resumed.replayed_optimizer_updates == 0
    assert [int(row["step"]) for row in resumed.history] == [1, 2, 3, 4, 5]
    assert resumed.predicted_c_hat.shape == (2, 21, 7, 2)
    assert resumed.predicted_p_scale.shape == (2, 21)
    assert all(torch.equal(resumed.model.state_dict()[k], reference.model.state_dict()[k])
               for k in resumed.model.state_dict())

    with pytest.raises(ValueError, match="mlp_progress_checkpoint_provenance_mismatch"):
        fit_arrays(
            mt, X, Y + 0.01, X_prediction=Xv,
            prediction_case_ids=("v0", "v1"), run_purpose=SYNTHETIC_TEST_ONLY,
            checkpoint_path=progress_path,
        )
    from dataclasses import replace
    with pytest.raises(ValueError, match="mlp_progress_checkpoint_provenance_mismatch"):
        fit_arrays(
            replace(mt, fixed_updates=4), X, Y, X_prediction=Xv,
            prediction_case_ids=("v0", "v1"), run_purpose=SYNTHETIC_TEST_ONLY,
            checkpoint_path=progress_path,
        )
    # One KRR fit, one interrupted/resumed MLP task (two calls), one reference
    # MLP fit, and two provenance-rejection invocations: no production fits.
    assert synthetic_test_fit_counts() == {"RBF_KRR": 1, "CARTESIAN_MLP": 5}
    # The resumable MLP task performed 3 + 2 optimizer calls; the independent
    # uninterrupted reference performed 5. The mismatch invocation did none.
    assert len(interrupted_updates) + resumed.optimizer_updates_this_invocation + reference.actual_updates == 10


def test_pscale_invalid_values_fail_closed():
    c = np.zeros((21, 7, 2), dtype=np.complex128)
    p = np.ones(21, dtype=np.float64)
    p[3] = 0.0
    with pytest.raises(ValueError, match="p_scale_truth_must_be_finite_positive"):
        pack_model_target(c, p)
    raw = np.zeros((1, MODEL_OUTPUTS), dtype=np.float64)
    raw[:, 588:] = 1000.0
    with pytest.raises(ValueError, match="predicted_p_scale_exp_nonfinite"):
        unpack_prediction(raw)


def test_seed_mean_uses_physical_pscale_arithmetic_mean():
    c1 = np.ones((21, 7, 2), dtype=np.complex128) * (1 + 2j)
    c2 = np.ones((21, 7, 2), dtype=np.complex128) * (3 + 4j)
    p1 = np.ones(21, dtype=np.float64)
    p2 = np.ones(21, dtype=np.float64) * 9.0
    cmean, pmean = seed_mean_predictions(((c1, p1), (c2, p2)))
    assert np.all(cmean == 2 + 3j)
    assert np.all(pmean == 5.0)
    assert not np.allclose(pmean, np.exp((np.log(p1) + np.log(p2)) / 2.0))


def test_real32_diagnostic_fit_authority_is_scoped():
    from dataclasses import replace
    from scripts.coupling_ml.k6_v2_pipeline.real32_diagnostic import _task
    from scripts.coupling_ml.k6_v2_pipeline.training import (
        ENGINEERING_DIAGNOSTIC, _ENGINEERING_DIAGNOSTIC_AUTHORITY,
        _fit_arrays_impl, _validate_engineering_diagnostic_task,
    )
    task = _task("RBF_KRR")
    _validate_engineering_diagnostic_task(task)
    X = np.zeros((24, 6), dtype=np.float64)
    Y = np.zeros((24, 609), dtype=np.float64)
    with pytest.raises(ValueError, match="public_array_fitting_is_synthetic_test_only"):
        fit_arrays(task, X, Y, run_purpose=ENGINEERING_DIAGNOSTIC)
    with pytest.raises(ValueError, match="scoped_authority"):
        _fit_arrays_impl(task, X, Y, run_purpose=ENGINEERING_DIAGNOSTIC)
    forged = replace(task, task_id="unapproved_real32_candidate")
    with pytest.raises(ValueError, match="config_mismatch"):
        _fit_arrays_impl(
            forged, X, Y, run_purpose=ENGINEERING_DIAGNOSTIC,
            _engineering_diagnostic_authority=_ENGINEERING_DIAGNOSTIC_AUTHORITY,
        )
