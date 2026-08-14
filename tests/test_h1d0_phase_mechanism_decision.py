import importlib.util
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("h1d0", ROOT / "scripts/lp_h1d0_phase_mechanism_decision.py")
H1D0 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(H1D0)


class H1D0OfflineTests(unittest.TestCase):
    def test_zero_solver_contract_constants(self):
        self.assertEqual(H1D0.K, 6)
        self.assertEqual(H1D0.M, 1)
        self.assertAlmostEqual(H1D0.PERIOD_NM, 2591.446716, places=9)

    def test_detour_sign_and_modulo_offsets(self):
        rows = H1D0.ideal_detour_offsets()
        self.assertEqual([round(r["ideal_relative_offset_nm"], 6) for r in rows], [0.0, 2159.53893, 1727.631144, 1295.723358, 863.815572, 431.907786])
        for row in rows:
            self.assertAlmostEqual(row["phase_recovered_deg"] % 360.0, row["target_phase_deg"] % 360.0, places=8)

    def test_common_translation_invariance(self):
        rows = H1D0.ideal_detour_offsets()
        common_translation = 137.25
        phases_a = [H1D0.phase_factor(row["phase_recovered_deg"]) for row in rows]
        phases_b = [H1D0.phase_factor(-(2.0 * math.pi * H1D0.M * (row["ideal_relative_offset_nm"] + common_translation) / H1D0.PERIOD_NM) * 180.0 / math.pi) for row in rows]
        self.assertAlmostEqual(abs(phases_a[1] / phases_a[0] - phases_b[1] / phases_b[0]), 0.0, places=12)

    def test_strict_bank_identity(self):
        bank = H1D0.strict_bank()
        self.assertEqual(len(bank), 7)
        self.assertEqual(len({g["exact_hash"] for g in bank}), 7)
        for geometry in bank:
            self.assertEqual(len(geometry["trajectory"]), 9)

    def test_registry_contract(self):
        audit = H1D0.dataset_audit(H1D0.strict_bank())
        self.assertEqual(audit["row_count"], 488)
        self.assertTrue(audit["all_full_jones_accepted"])
        self.assertTrue(audit["all_ml_eligible"])
        self.assertTrue(audit["all_ml_admitted_false"])
        self.assertTrue(audit["all_split_unassigned"])

    def test_pure_layout_is_legal_offline(self):
        parent = max(H1D0.strict_bank(), key=lambda g: float(g["minimum_throughput"]))
        assignments, _ = H1D0.pure_assignments(parent)
        audit = H1D0.layout_geometry(assignments)
        self.assertTrue(audit["geometry_legal"])
        self.assertGreaterEqual(audit["min_clearance_nm"], H1D0.MIN_CLEARANCE_NM)

    def test_no_full_wave_claim_in_phase_model(self):
        self.assertEqual(H1D0.M, 1)
        self.assertNotIn("FDTD", H1D0.phase_factor.__doc__ or "")


if __name__ == "__main__":
    unittest.main()
