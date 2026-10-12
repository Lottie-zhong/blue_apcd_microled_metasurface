"""Offline tests for the Owner-certified flat postprocess resolver."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "coupling_ml"))

from k6_v2_pipeline import generic_profile as G  # noqa: E402
from k6_v2_pipeline import ingest as I  # noqa: E402
from k6_v2_pipeline import postprocess_contract_resolver as R  # noqa: E402


TASK = ROOT / "reports" / "coupling" / "APCD_COUPLING_V21_SCIENCE_CONTRACT_CLOSEOUT_V1"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_authority(batch_dir: Path) -> dict:
    manifest_path = batch_dir / "BATCH_MANIFEST_TEST_FIXTURE_ONLY.json"
    admission_path = batch_dir / "SCIENCE_ADMISSION_TEST_FIXTURE_ONLY.json"
    certification_path = batch_dir / "SCIENCE_OWNER_PROFILE_CERTIFICATION_TEST_FIXTURE_ONLY.json"
    resolver_certification_path = TASK / "POSTPROCESS_CONTRACT_RESOLVER_CERTIFICATION_V1.json"
    return {
        "schema": G.AUTHORITY_SCHEMA,
        "profile_id": G.PROFILE_ID,
        "manifest": json.loads(manifest_path.read_text(encoding="utf-8")),
        "admission": json.loads(admission_path.read_text(encoding="utf-8")),
        "certification": json.loads(certification_path.read_text(encoding="utf-8")),
        "manifest_file_sha": _sha(manifest_path),
        "admission_file_sha": _sha(admission_path),
        "certification_file_sha": _sha(certification_path),
        "resolver_certification": json.loads(
            resolver_certification_path.read_text(encoding="utf-8")
        ),
        "resolver_certification_file_sha": _sha(resolver_certification_path),
    }


class ResolvedPostprocessContractTests(unittest.TestCase):
    def test_real_b_and_c_authorities_resolve_six_flat_fields(self):
        batches = (
            ("B_DIAG2_TEST_FIXTURE", (
                "K6V3_TIME_DIAG2_A1_5NM_6PS",
                "K6V3_TIME_DIAG2_A2_5NM_6PS",
            )),
            ("C_COUPLING_TEST_FIXTURE", ("K6COUPLING_OFFLINE_TEST_C001",)),
        )
        contract_path = TASK / "SCIENCE_CONTRACT_6PS.json"
        contract_sha = _sha(contract_path)
        expected_fields = json.loads(contract_path.read_text(encoding="utf-8"))[
            "parent_physical_contract_fields"
        ]
        expected_projection = {key: expected_fields[key] for key in R.FIELDS}
        projection_digest = I._canon({
            "schema": R.RESOLVED_CONTRACT_SCHEMA,
            "resolved_contract": expected_projection,
        })
        independent_digest = hashlib.sha256(json.dumps(
            {"schema": R.RESOLVED_CONTRACT_SCHEMA,
             "resolved_contract": expected_projection},
            sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        ).encode("utf-8")).hexdigest()
        self.assertEqual(projection_digest, independent_digest)
        self.assertEqual(
            projection_digest,
            "c13356f4b4f51aabce9a82db23fdb503e6b6e159388ce7055da8c09e9cf1b75b",
        )

        seen = 0
        for folder, case_ids in batches:
            authority = _load_authority(TASK / "fixtures" / folder)
            for case_id in case_ids:
                resolved = R.resolve_postprocess_contract(
                    authority, case_id, "attempt_001"
                )
                self.assertEqual(resolved["verdict"], "PASS")
                self.assertEqual(resolved["case_id"], case_id)
                self.assertEqual(resolved["physical_contract_sha256"], contract_sha)
                self.assertEqual(resolved["physical_contract_file_sha256"], contract_sha)
                self.assertEqual(resolved["source_contract_section"],
                                 "parent_physical_contract_fields")
                self.assertEqual(resolved["resolved_contract"], expected_projection)
                self.assertEqual(resolved["resolved_contract_sha256"], independent_digest)
                self.assertFalse(resolved["entry_authorization"])
                self.assertFalse(resolved["native_truth_validated"])
                self.assertEqual(resolved["solver_entry_count"], 0)
                seen += 1
        self.assertEqual(seen, 3)

    def test_case_identity_and_attempt_fail_closed(self):
        authority = _load_authority(TASK / "fixtures" / "B_DIAG2_TEST_FIXTURE")
        with self.assertRaisesRegex(ValueError, "profile_case_not_authorized"):
            R.resolve_postprocess_contract(
                authority, "UNKNOWN_CASE", "attempt_001"
            )
        with self.assertRaisesRegex(ValueError, "profile_attempt_mismatch"):
            R.resolve_postprocess_contract(
                authority, "K6V3_TIME_DIAG2_A1_5NM_6PS", "attempt_002"
            )

    def test_resolver_certification_pin_is_required(self):
        authority = _load_authority(TASK / "fixtures" / "B_DIAG2_TEST_FIXTURE")
        authority["resolver_certification_file_sha"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "resolver_certification_file_sha_mismatch"):
            R.resolve_postprocess_contract(
                authority, "K6V3_TIME_DIAG2_A1_5NM_6PS", "attempt_001"
            )

    def test_versioned_projection_rejects_missing_or_malformed_fields(self):
        contract = {
            "schema": R.SOURCE_CONTRACT_SCHEMA,
            "parent_physical_contract_fields": {
                "materials": {"mdc_tio2": "APCD_TIO2_NATIVE_M1"},
                "monitors": {"input": "MON_IN", "output": "MON_POSTNP", "pre": "MON_PRENP"},
                "references_nm": {"MON_IN": -50.0, "MON_POSTNP": 1722.0, "MON_PRENP": 1202.0},
                "samples_nm": {"MON_IN": -100.0, "MON_POSTNP": 1800.0, "MON_PRENP": 1150.0},
                "stack_layers": [["APCD_TIO2_NATIVE_M1", 44.0]],
                "wavelengths_nm": list(range(440, 461)),
            },
        }
        fields, section = R._source_fields(contract)
        R._validate_resolved_fields(fields)
        self.assertEqual(section, "parent_physical_contract_fields")
        del contract["parent_physical_contract_fields"]["samples_nm"]
        with self.assertRaisesRegex(ValueError, "resolver_required_fields_missing"):
            R._source_fields(contract)
        contract["parent_physical_contract_fields"]["samples_nm"] = {
            "MON_IN": -100.0, "MON_POSTNP": 1800.0
        }
        fields, _ = R._source_fields(contract)
        with self.assertRaisesRegex(ValueError, "resolver_reference_or_sample_planes_invalid"):
            R._validate_resolved_fields(fields)

    def test_optional_case_binding_checks_known_identity_but_allows_new_case(self):
        row = {
            "case_id": "CASE_A",
            "attempt_id": "attempt_001",
            "role": "DEVELOPMENT_GLOBAL",
            "ordered_D_nm": [120, 160, 165, 175, 160, 195],
        }
        contract = {
            "case_geometry_binding": {
                "cases": [{
                    "case_id": "CASE_A", "attempt_id": "attempt_001",
                    "role": "DEVELOPMENT_GLOBAL",
                    "ordered_D_nm": row["ordered_D_nm"],
                    "geometry_sha256": G.geometry_sha(row["ordered_D_nm"]),
                }]
            }
        }
        self.assertEqual(R._check_optional_geometry_binding(contract, row), "MATCHED")
        contract["case_geometry_binding"]["cases"][0]["ordered_D_nm"][0] = 125
        with self.assertRaisesRegex(ValueError, "resolver_case_geometry_binding_mismatch"):
            R._check_optional_geometry_binding(contract, row)
        row["case_id"] = "NEW_BATCH_CASE"
        self.assertEqual(R._check_optional_geometry_binding(contract, row),
                         "UNLISTED_SHARED_CONTRACT_CASE")

    def test_case_request_float_mesh_uses_frozen_canonicalizer(self):
        authority = _load_authority(TASK / "fixtures" / "B_DIAG2_TEST_FIXTURE")
        row = copy.deepcopy(authority["manifest"]["cases"][0])
        float_row = copy.deepcopy(row)
        float_row["mesh_nm"] = 5.0
        int_digest = G._case_request_digest(row)
        float_digest = G._case_request_digest(float_row)
        independent = hashlib.sha256(json.dumps(
            G._case_request_payload(float_row),
            sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        ).encode("utf-8")).hexdigest()
        self.assertNotEqual(int_digest, float_digest)
        self.assertEqual(int_digest,
                         "ca865c861563201bedcc638485e319cb4471a7b23a136ae4c326098398003385")
        self.assertEqual(float_digest,
                         "61fd93038102be83a381ad4f1271dac5ccdf689261c8edd9a7269ffb6b9b1bf2")
        self.assertEqual(float_digest, independent)
        self.assertEqual(float_row["mesh_nm"], 5.0)


if __name__ == "__main__":
    unittest.main()
