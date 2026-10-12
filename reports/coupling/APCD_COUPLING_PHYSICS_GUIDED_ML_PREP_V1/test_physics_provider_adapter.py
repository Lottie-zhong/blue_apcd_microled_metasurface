"""Synthetic, offline-only tests for the Coupling ML physics adapter."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts" / "coupling_ml"))

from physics_provider_adapter import (  # noqa: E402
    IllConditionedCascadeError,
    ModeKey,
    ProviderUnavailableError,
    ProviderStatus,
    cascade_transmission_synthetic,
    require_full_complex_state,
    validate_mode_axis,
    validate_p_scale,
    validate_scattering_matrix,
)


class ProviderContractTests(unittest.TestCase):
    def test_full_complex_requires_validated_status_and_complete_mask(self):
        values = np.ones((21, 7, 2), dtype=np.complex128)
        mask = np.ones(values.shape, dtype=bool)
        accepted = require_full_complex_state(
            values, ProviderStatus.VALIDATED_COMPLEX, mask
        )
        self.assertEqual(accepted.shape, (21, 7, 2))
        with self.assertRaisesRegex(ValueError, "provider_status_not_full"):
            require_full_complex_state(values, ProviderStatus.POWER_ONLY, mask)
        with self.assertRaisesRegex(ValueError, "all_frozen"):
            bad_mask = mask.copy()
            bad_mask[0, 0, 0] = False
            require_full_complex_state(values, ProviderStatus.VALIDATED_COMPLEX, bad_mask)

    def test_unavailable_provider_never_becomes_zero_state(self):
        with self.assertRaises(ProviderUnavailableError):
            require_full_complex_state(None, ProviderStatus.UNAVAILABLE, None)

    def test_propagating_mask_requires_boolean_dtype(self):
        values = np.ones((21, 7, 2), dtype=np.complex128)
        with self.assertRaisesRegex(TypeError, "mask_must_be_boolean"):
            require_full_complex_state(
                values, ProviderStatus.VALIDATED_COMPLEX, np.ones(values.shape, dtype=int)
            )

    def test_partial_and_unverified_provider_statuses_are_rejected(self):
        values = np.ones((21, 7, 2), dtype=np.complex128)
        mask = np.ones(values.shape, dtype=bool)
        for status in (ProviderStatus.PARTIAL_COMPLEX, ProviderStatus.UNVERIFIED):
            with self.subTest(status=status):
                with self.assertRaisesRegex(ValueError, "provider_status_not_full"):
                    require_full_complex_state(values, status, mask)

    def test_power_scale_is_separate_finite_and_positive(self):
        scale = np.full((21,), 0.25)
        self.assertTrue(np.array_equal(validate_p_scale(scale), scale))
        with self.assertRaisesRegex(ValueError, "finite_positive"):
            validate_p_scale(np.r_[np.ones(20), 0.0])

    def test_smatrix_axes_are_explicit_and_dimension_driven(self):
        inputs = (
            ModeKey("M_left", 0, 0, "TM", "+z", "propagating"),
            ModeKey("M_left", 1, 0, "TE", "+z", "evanescent"),
        )
        outputs = (ModeKey("N_right", 0, 0, "TM", "+z", "propagating"),)
        matrix = np.ones((1, 2), dtype=np.complex128)
        self.assertEqual(validate_scattering_matrix(matrix, inputs, outputs).shape, (1, 2))
        with self.assertRaisesRegex(ValueError, "axis_shape"):
            validate_scattering_matrix(np.ones((2, 2), complex), inputs, outputs)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_mode_axis((inputs[0], inputs[0]))
        bad_direction = (ModeKey("M_left", 0, 0, "TM", "sideways", "propagating"),)
        with self.assertRaisesRegex(ValueError, "propagation_direction"):
            validate_mode_axis(bad_direction)
        bad_order = (ModeKey("M_left", 0.5, 0, "TM", "+z", "propagating"),)
        with self.assertRaisesRegex(ValueError, "mode_order_integer"):
            validate_mode_axis(bad_order)

    def test_synthetic_cascade_uses_linear_solve_with_known_scalar_result(self):
        eye = np.eye(2, dtype=np.complex128)
        t_n = eye
        propagation = 0.5 * eye
        r_m = 0.2 * eye
        r_n = 0.1 * eye
        t_m = eye
        result = cascade_transmission_synthetic(t_n, propagation, r_m, r_n, t_m)
        expected = (0.5 / (1.0 - 0.2 * 0.5 * 0.1 * 0.5)) * eye
        np.testing.assert_allclose(result.coefficients, expected, rtol=1e-13, atol=1e-13)
        self.assertLess(float(np.max(result.condition_number)), 2.0)

    def test_synthetic_cascade_supports_batch_and_wavelength_axes(self):
        eye = np.eye(2, dtype=np.complex128)
        result = cascade_transmission_synthetic(
            np.broadcast_to(eye, (2, 1, 2, 2)),
            np.broadcast_to(0.4 * eye, (1, 3, 2, 2)),
            np.broadcast_to(0.1 * eye, (1, 3, 2, 2)),
            np.broadcast_to(0.2 * eye, (1, 3, 2, 2)),
            np.broadcast_to(eye[..., :1], (2, 3, 2, 1)),
        )
        self.assertEqual(result.coefficients.shape, (2, 3, 2, 1))
        self.assertEqual(result.condition_number.shape, (2, 3))

    def test_ill_conditioned_feedback_is_rejected(self):
        eye = np.eye(2, dtype=np.complex128)
        r_n = np.diag([0.0, 1.0 - 1.0e-14]).astype(np.complex128)
        with self.assertRaises(IllConditionedCascadeError):
            cascade_transmission_synthetic(
                eye, eye, eye, r_n, eye, condition_limit=1.0e10
            )


class FrozenOutputCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from k6_v2_pipeline.contracts import pack_model_target, unpack_model_target
        from k6_v2_pipeline.h1 import load_h2_decoder, reconstruct_h2

        cls.pack = staticmethod(pack_model_target)
        cls.unpack = staticmethod(unpack_model_target)
        cls.load_h2_decoder = staticmethod(load_h2_decoder)
        cls.reconstruct_h2 = staticmethod(reconstruct_h2)

    def test_frozen_609_target_round_trip_and_h2_decoding(self):
        rng = np.random.default_rng(1722)
        c_hat = (
            rng.normal(size=(21, 7, 2)) + 1j * rng.normal(size=(21, 7, 2))
        ).astype(np.complex128)
        p_scale = rng.uniform(0.1, 0.9, size=(21,))
        packed = self.pack(c_hat, p_scale)
        self.assertEqual(packed.shape, (1, 609))
        c_round, p_round = self.unpack(packed)
        np.testing.assert_allclose(c_round[0], c_hat, rtol=0.0, atol=0.0)
        np.testing.assert_allclose(p_round[0], p_scale, rtol=1e-14, atol=1e-14)

        decoded = self.reconstruct_h2(c_hat, p_scale, self.load_h2_decoder())
        np.testing.assert_allclose(decoded["eta"].sum(axis=-1), 1.0, atol=1e-14)
        np.testing.assert_allclose(decoded["total_power"][0], p_scale, atol=0.0)
        np.testing.assert_allclose(
            decoded["absolute_order"],
            decoded["eta"] * p_scale[None, :, None],
            rtol=0.0,
            atol=1e-14,
        )


if __name__ == "__main__":
    unittest.main()
