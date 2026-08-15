import importlib.util
import json
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "lp_h1e3c_j2_decoupling_probe.py"
spec = importlib.util.spec_from_file_location("h1e3c", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


class H1E3CProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = mod.read(mod.MANIFEST)
        cls.children = cls.manifest["candidates"]

    def test_exact_parent_selection_and_manifest_size(self):
        self.assertEqual(self.manifest["stage"], "H1E-3C")
        self.assertEqual(len(self.children), 8)
        self.assertEqual({c["role"] for c in self.children}, {"A", "B", "C"})
        self.assertEqual(sum(c["role"] == "A" for c in self.children), 4)
        self.assertEqual(sum(c["role"] == "B" for c in self.children), 2)
        self.assertEqual(sum(c["role"] == "C" for c in self.children), 2)
        expected = {
            "H1C1B_V2_010": "3f1dc26c576ffc1bc4c074f90d1c58ade24eb09b6926603aa8208ee52da19611",
            "GLOBAL_006": "58cb7c6aebab655f9f14af16d5a2ec1d0182037e8543fca5a31e7a08ebfcd176",
            "H1C1B_V2_009": "955c293def3063f64969c25743e14ce122e7ed0364b12be0b9f75cdb350cb800",
        }
        for role, uid in (("A", "H1C1B_V2_010"), ("B", "GLOBAL_006"), ("C", "H1C1B_V2_009")):
            self.assertEqual(self.manifest["parents"][uid]["exact_hash"], expected[uid])

    def test_geometry_semantics_and_pairs(self):
        self.assertEqual(len({c["exact_hash"] for c in self.children}), 8)
        for c in self.children:
            self.assertEqual(c["Psi_position_deg"], c["Psi0_deg"] + (1.0 if "PLUS" in c["mode"] else -1.0))
            if "TIED" in c["mode"]:
                self.assertEqual(c["theta_J2_deg"], c["Psi_position_deg"])
                self.assertEqual(c["delta_theta_J2_deg"], 0.0)
            else:
                self.assertEqual(c["theta_J2_deg"], c["theta0_deg"])
                self.assertEqual(c["delta_theta_J2_deg"], -1.0 if "PLUS" in c["mode"] else 1.0)
            self.assertTrue(c["legality"]["pass"])
            self.assertEqual(c["geometry_identity"]["wavelength_grid_nm"], mod.GRID)

    def test_old_grammar_regression(self):
        report = mod.read(mod.REPORT / "h1e3c_builder_regression.json")
        self.assertTrue(report["old_default_equals_explicit_zero_delta"])
        self.assertTrue(report["old_default_theta_equals_position"])
        self.assertTrue(report["legacy_semantics_preserved"])
        self.assertEqual(report["legacy_semantics_hash"], report["new_default_semantics_hash"])

    def test_control_reuse_and_budget(self):
        reuse = mod.read(mod.REPORT / "h1e3c_historical_control_reuse.json")
        self.assertFalse(reuse["historical_exact_control_reused"])
        self.assertEqual(reuse["new_geometry_count_if_prepared"], 8)
        self.assertEqual(self.manifest["solver_authorization"]["formal_x_y_subruns"], 16)
        accounting = mod.read(mod.ACCOUNTING)
        self.assertEqual(accounting["entered_formal_subruns"], 16)
        self.assertEqual(accounting["accepted_formal_subruns"], 16)
        self.assertEqual(accounting["quarantined_formal_subruns"], 0)
        self.assertEqual(len(accounting["solver_entries"]), 16)
        self.assertTrue(all(c.get("solver_entered", False) for c in accounting["cases"]))
        self.assertTrue(all(not c.get("solver_replay", False) for c in accounting["cases"]))

    def test_registry_and_policy_flags(self):
        self.assertEqual(self.manifest["contract"]["wavelength_grid_nm"], mod.GRID)
        self.assertEqual(self.manifest["contract"]["projector"], [[1, 0], [0, 0]])
        self.assertTrue(self.manifest["solver_authorization"]["entered_no_replay"])


if __name__ == "__main__":
    unittest.main()
