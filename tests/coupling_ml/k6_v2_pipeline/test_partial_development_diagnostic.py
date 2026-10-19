import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from coupling_ml.k6_v2_pipeline import training as T


def _task(model_kind="RBF_KRR", **overrides):
    train = tuple(f"train_{i:02d}" for i in range(52))
    valid = tuple(f"valid_{i:02d}" for i in range(13))
    fields = dict(
        task_id="partial65_krr" if model_kind == "RBF_KRR" else "partial65_mlp_s0",
        phase="engineering_diagnostic",
        model_kind=model_kind,
        outer_fold=None,
        inner_fold=None,
        training_geometry_count=52,
        train_case_ids=train,
        prediction_case_ids=valid,
        gamma=1.0 / 3.0 if model_kind == "RBF_KRR" else None,
        ridge_alpha=1e-2 if model_kind == "RBF_KRR" else None,
        weight_decay=1e-4 if model_kind == "CARTESIAN_MLP" else None,
        seed=0 if model_kind == "CARTESIAN_MLP" else None,
        fixed_updates=None,
        config_source="PARTIAL_DIAGNOSTIC_CONFIG_V1.json",
        update_source="frozen_grid_midpoint_lowest_seed",
    )
    fields.update(overrides)
    return T.FitTask(**fields)


class PartialDevelopmentDiagnosticScopeTests(unittest.TestCase):
    def test_accepts_only_two_frozen_candidate_shapes(self):
        T._validate_partial_development_diagnostic_task(_task("RBF_KRR"))
        T._validate_partial_development_diagnostic_task(_task("CARTESIAN_MLP"))

    def test_rejects_changed_config_or_split(self):
        with self.assertRaisesRegex(ValueError, "config_mismatch"):
            T._validate_partial_development_diagnostic_task(_task("RBF_KRR", gamma=2.0))
        overlapped = list(_task().prediction_case_ids)
        overlapped[0] = _task().train_case_ids[0]
        with self.assertRaisesRegex(ValueError, "identity_mismatch"):
            T._validate_partial_development_diagnostic_task(
                _task("RBF_KRR", prediction_case_ids=tuple(overlapped))
            )
        with self.assertRaisesRegex(ValueError, "identity_mismatch"):
            T._validate_partial_development_diagnostic_task(
                _task("RBF_KRR", training_geometry_count=24)
            )


if __name__ == "__main__":
    unittest.main()
