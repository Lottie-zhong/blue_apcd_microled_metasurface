"""Offline checks for the candidate generic profile adapter."""
from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "coupling_ml"))

from k6_v2_pipeline import contracts as C  # noqa: E402
from k6_v2_pipeline import generic_profile as G  # noqa: E402
from k6_v2_pipeline.ingest import load_old32_engineering_diagnostic  # noqa: E402


class GenericProfileContractTests(unittest.TestCase):
    def test_real_diag2_role_is_supported_but_requires_owner_admission(self):
        # Current DIAG2 A1 identity is a diagnostic sample only. The generic
        # adapter recognizes its role, but cannot grant admission without the
        # Science Owner authority envelope.
        self.assertIn("TIME_CONVERGENCE_DIAGNOSTIC_ONLY", G.KNOWN_ROLES)
        with self.assertRaisesRegex(ValueError, "authority_schema"):
            G.validate_profile_admission(
                authority={}, case_id="K6V3_TIME_DIAG2_A1_5NM_6PS",
                attempt_id="attempt_001"
            )

    def test_no_prepared_batch_authority_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "authority_schema"):
            G.validate_profile_admission(
                authority={}, case_id="unprepared_batch_case", attempt_id="attempt_001"
            )

    def test_parameterized_kernel_is_source_equivalent_to_frozen_extractor(self):
        frozen = inspect.getsource(__import__(
            "k6_v2_pipeline.ingest", fromlist=["_load_runner_truth"]
        )._load_runner_truth)
        signature = (
            "def _load_runner_truth(record,role_map,expected_roles,*,"
            "root=None,power_supplement=None):"
        )
        adapted_signature = (
            "def _load_authorized_runner_truth(record,role_map,expected_roles,*,"
            "contract_sha256,root=None,power_supplement=None):"
        )
        self.assertEqual(frozen.count("C.PHYSICAL_CONTRACT_SHA256"), 4)
        expected = frozen.replace(signature, adapted_signature, 1)
        expected = expected.replace("C.PHYSICAL_CONTRACT_SHA256", "contract_sha256")
        adapted = inspect.getsource(G._load_authorized_runner_truth)
        self.assertEqual(adapted, expected)
        self.assertNotIn("C.PHYSICAL_CONTRACT_SHA256", adapted)

    def test_physical_rule_evaluator_can_enforce_exact_six_ps_value(self):
        exact_six_ps = {"min": 6.0, "max": 6.0}
        self.assertTrue(G._rule_allows(6.0, exact_six_ps))
        self.assertFalse(G._rule_allows(3.0, exact_six_ps))

    def test_real_frozen_old32_values_reuse_609d_numeric_core(self):
        # Numeric compatibility only: this old32 case is not promoted into a
        # dynamic batch and no profile/solver admission is asserted.
        collection = load_old32_engineering_diagnostic(root=ROOT)
        case = collection.cases[0]
        result = G._validate_609d_numeric_payload(case)
        self.assertEqual(case.role, C.ROLE_OLD32)
        self.assertEqual(result["outputs"], 609)
        self.assertTrue(np.isfinite(result["h2_eta_max_abs_delta"]))


if __name__ == "__main__":
    unittest.main()
