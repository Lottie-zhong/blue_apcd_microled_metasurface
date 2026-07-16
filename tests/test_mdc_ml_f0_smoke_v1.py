from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mdc_ml_structure_grammar_v1 import TOPOLOGY_FAMILIES

SPEC = importlib.util.spec_from_file_location("f0_smoke", SCRIPTS / "run_mdc_ml_f0_smoke_v1.py")
assert SPEC and SPEC.loader
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


class F0SmokeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = smoke.load_config()

    def test_exact_deterministic_17_structure_set(self) -> None:
        first = smoke.build_smoke_candidates(self.config)
        second = smoke.build_smoke_candidates(self.config)
        first_canonical = [smoke.canonical_roundtrip(item) for item in first]
        second_canonical = [smoke.canonical_roundtrip(item) for item in second]
        self.assertEqual(len(first), 17)
        self.assertEqual(
            [item["canonical_geometry_hash"] for item in first_canonical],
            [item["canonical_geometry_hash"] for item in second_canonical],
        )
        self.assertEqual(len({item["canonical_geometry_hash"] for item in first_canonical}), 17)

    def test_two_nonbaseline_per_topology_family(self) -> None:
        candidates = smoke.build_smoke_candidates(self.config)
        counts = {
            family: sum(item["topology_family"] == family for item in candidates[1:])
            for family in TOPOLOGY_FAMILIES
        }
        self.assertEqual(counts, {family: 2 for family in TOPOLOGY_FAMILIES})

    def test_frozen_baseline_identity_and_roundtrip(self) -> None:
        canonical = smoke.canonical_roundtrip(smoke.baseline_candidate(self.config))
        baseline = self.config["baseline"]
        self.assertEqual(canonical["canonical_geometry_hash"], baseline["canonical_geometry_hash"])
        self.assertEqual(canonical["physical_configuration_hash"], baseline["physical_configuration_hash"])
        self.assertEqual(canonical["layer_count"], 12)
        self.assertEqual(canonical["total_thickness_nm"], 975)
        self.assertEqual(canonical["defect_indices"], [5])

    def test_peak_set_uses_frozen_symmetric_tie_semantics(self) -> None:
        angles = np.arange(-2.0, 3.0)
        center = smoke.peak_set(angles, np.array([0.1, 0.4, 1.0, 0.4, 0.1]))
        pair = smoke.peak_set(angles, np.array([0.1, 1.0, 0.5, 1.0, 0.1]))
        self.assertEqual(center["maximum_angle_set_deg"], [0.0])
        self.assertTrue(center["center_is_global_max"])
        self.assertEqual(pair["maximum_angle_set_deg"], [-1.0, 1.0])
        self.assertTrue(pair["symmetric_peak_pair"])

    def test_apcd_integral_uses_radians_and_normalized_spectrum(self) -> None:
        wavelengths = np.arange(448.0, 453.1, 0.5)
        angles = np.arange(-60.0, 61.0, 1.0)
        transmission = np.ones((len(wavelengths), len(angles)))
        self.assertAlmostEqual(smoke.integrate_apcd(wavelengths, angles, transmission, 5.0), np.deg2rad(10.0), places=14)
        self.assertAlmostEqual(
            smoke.integrate_apcd(wavelengths, angles, transmission, 5.0)
            / smoke.integrate_apcd(wavelengths, angles, transmission, 60.0),
            1.0 / 12.0,
            places=14,
        )

    def test_deterministic_npz_bytes(self) -> None:
        arrays = {"b": np.array([1 + 2j]), "a": np.arange(3, dtype=float)}
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.npz"
            second = Path(directory) / "second.npz"
            smoke.deterministic_npz(first, arrays)
            smoke.deterministic_npz(second, dict(reversed(list(arrays.items()))))
            self.assertEqual(smoke.sha256_path(first), smoke.sha256_path(second))
            with np.load(first, allow_pickle=False) as loaded:
                self.assertEqual(sorted(loaded.files), ["a", "b"])

    def test_existing_output_contract_when_present(self) -> None:
        out = ROOT / self.config["output_directory"]
        validation = out / "validation_v1.json"
        if not validation.exists():
            self.skipTest("full smoke output has not been generated")
        result = json.loads(validation.read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["schema_validation"], "PASS")
        self.assertEqual(result["artifact_sha_validation"], "PASS")
        self.assertEqual(result["nan_inf_audit"], "PASS")
        self.assertEqual(result["duplicate_geometry_audit"], "PASS")
        self.assertEqual(result["topology_coverage_audit"], "PASS")


if __name__ == "__main__":
    unittest.main()
