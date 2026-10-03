import importlib.util
import unittest
from pathlib import Path

import numpy as np

SCRIPT = Path(__file__).parents[2] / "scripts" / "coupling_ml" / "coupling_ml_32g_predicted_amplitude_phase_hybrid_audit_v1.py"
spec = importlib.util.spec_from_file_location("hybrid_audit", str(SCRIPT))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class HybridConstructionTests(unittest.TestCase):
    def test_phase_source_priority_and_magnitude_preservation(self):
        c0 = np.asarray([3 + 4j, 1e-10j, 1e-10j, 0j], dtype=np.complex128)
        c1 = np.asarray([-8 + 6j, 3 + 4j, 0j, 0 + 2j], dtype=np.complex128)
        hybrid, masks = audit.build_hybrid(c0, c1)
        np.testing.assert_allclose(np.abs(hybrid), np.abs(c1), rtol=0, atol=1e-14)
        self.assertAlmostEqual(np.angle(hybrid[0]), np.angle(c0[0]))
        self.assertAlmostEqual(np.angle(hybrid[1]), np.angle(c1[1]))
        self.assertEqual(hybrid[2], 0j)
        self.assertEqual(hybrid[3], 2j)
        self.assertEqual(int(masks["used_c1_phase"].sum()), 2)
        self.assertEqual(int(masks["used_fixed_unit_phase"].sum()), 1)

    def test_shape_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            audit.build_hybrid(np.ones(2, complex), np.ones(3, complex))

    def test_h2_power_is_invariant_for_paired_equal_magnitudes(self):
        c0 = np.ones((1, 1, 7, 2), dtype=np.complex128) * (1 + 2j)
        c1 = np.ones((1, 1, 7, 2), dtype=np.complex128) * (3 - 4j)
        hybrid, _ = audit.build_hybrid(c0, c1)
        factors = np.ones((1, 7, 2), dtype=float)
        pscale = np.asarray([[0.37]], dtype=float)
        r1 = audit.h2_reconstruct(c1, pscale, factors)
        rh = audit.h2_reconstruct(hybrid, pscale, factors)
        np.testing.assert_allclose(rh["order_power"], r1["order_power"], rtol=0, atol=1e-14)
        np.testing.assert_allclose(rh["eta"], r1["eta"], rtol=0, atol=1e-14)
        np.testing.assert_allclose(rh["scale"], r1["scale"], rtol=0, atol=1e-14)
        np.testing.assert_allclose(rh["total"], pscale, rtol=0, atol=1e-14)


if __name__ == "__main__":
    unittest.main()
