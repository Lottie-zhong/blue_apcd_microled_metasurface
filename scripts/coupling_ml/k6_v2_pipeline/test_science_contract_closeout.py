"""Offline contract and ledger protocol checks; no solver or production ledger."""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "coupling_ml"))

from k6_v2_pipeline import generic_profile as G  # noqa: E402
from k6_v2_pipeline import science_ledger as L  # noqa: E402


class CloseoutContractTests(unittest.TestCase):
    def test_versioned_request_canonicalization_independent_vector(self):
        row = {
            "case_id": "K6COUPLING_CANON_VECTOR_C001",
            "attempt_id": "attempt_001",
            "role": "DEVELOPMENT_GLOBAL",
            "ordered_D_nm": [120, 160, 165, 175, 160, 195],
            "physics_contract_sha": "a" * 64,
            "physics_contract": {"path": r"D:\fixture\contract.json", "sha256": "a" * 64},
            "simulation_time_s": 6e-12,
            "mesh_nm": 5,
            "auto_shutoff_min": 1e-6,
            "source_fsp": {"path": r"D:\fixture\source.fsp", "sha256": "b" * 64},
            "source_manifest": {"path": r"D:\fixture\source_manifest.json", "sha256": "c" * 64},
            "source_acceptance": {"path": r"D:\fixture\source_acceptance.json", "sha256": "d" * 64},
            "case_request_sha256": "",
        }
        projection = {
            "schema": "APCD_COUPLING_CASE_REQUEST_CANON_V1",
            "case_request": {k: v for k, v in row.items()
                             if k not in ("case_request_sha256", "source_acceptance")},
            "source_acceptance_path": row["source_acceptance"]["path"],
        }
        expected = "94ed521d572ce8676c3d5aea99ac91ce2dcf907bdbe08ab4a7cfcd2799fe51a3"
        independent = hashlib.sha256(
            json.dumps(projection, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            .encode("utf-8")
        ).hexdigest()
        self.assertEqual(independent, expected)
        self.assertEqual(G._case_request_digest(row), expected)
        changed_file_pin = dict(row)
        changed_file_pin["source_acceptance"] = {
            "path": row["source_acceptance"]["path"], "sha256": "e" * 64
        }
        self.assertEqual(G._case_request_digest(changed_file_pin), expected)
        changed_path = dict(row)
        changed_path["source_acceptance"] = {
            "path": r"D:\fixture\other_acceptance.json", "sha256": "d" * 64
        }
        self.assertNotEqual(G._case_request_digest(changed_path), expected)

    def test_b_and_c_ledgers_have_independent_budgets_and_no_replay(self):
        b_ids = ["K6V3_TIME_DIAG2_A1_5NM_6PS", "K6V3_TIME_DIAG2_A2_5NM_6PS"]
        c_ids = ["K6COUPLING_OFFLINE_TEST_C001"]
        b_adm = admission("B_DIAG2_TEST_FIXTURE", b_ids)
        c_adm = admission("C_COUPLING_TEST_FIXTURE", c_ids)
        b_sha = "1" * 64
        c_sha = "2" * 64
        b = L.initial_ledger(b_adm, b_sha, expected_science_owner=L.SCIENCE_OWNER_ID)
        c = L.initial_ledger(c_adm, c_sha, expected_science_owner=L.SCIENCE_OWNER_ID)
        b = L.reconcile_offline_receipt(
            b, b_adm, receipt(b_adm, b_ids[0], b_sha), admission_sha256=b_sha,
            expected_science_owner=L.SCIENCE_OWNER_ID, test_fixture_only=True,
        )
        c = L.reconcile_offline_receipt(
            c, c_adm, receipt(c_adm, c_ids[0], c_sha), admission_sha256=c_sha,
            expected_science_owner=L.SCIENCE_OWNER_ID, test_fixture_only=True,
        )
        self.assertEqual((b["authorized_entry_budget"], b["entered_count"],
                          b["remaining_unentered_count"]), (2, 1, 1))
        self.assertEqual((c["authorized_entry_budget"], c["entered_count"],
                          c["remaining_unentered_count"]), (1, 1, 0))
        self.assertEqual(b["batch_id"], "B_DIAG2_TEST_FIXTURE")
        self.assertEqual(c["batch_id"], "C_COUPLING_TEST_FIXTURE")
        self.assertNotIn(c_ids[0], b["case_records"])
        self.assertNotIn(b_ids[0], c["case_records"])
        with self.assertRaisesRegex(L.LedgerError, "case_not_unentered"):
            L.reconcile_offline_receipt(
                b, b_adm, receipt(b_adm, b_ids[0], b_sha), admission_sha256=b_sha,
                expected_science_owner=L.SCIENCE_OWNER_ID, test_fixture_only=True,
            )

    def test_consumer_cannot_supply_science_owner_identity(self):
        adm = admission("B_DIAG2_TEST_FIXTURE", ["CASE_1"])
        with self.assertRaisesRegex(L.LedgerError, "trusted_science_owner_pin"):
            L.initial_ledger(adm, "3" * 64, expected_science_owner="CONSUMER")
        adm["science_owner"] = "CONSUMER"
        with self.assertRaisesRegex(L.LedgerError, "admission_owner"):
            L.initial_ledger(adm, "3" * 64, expected_science_owner=L.SCIENCE_OWNER_ID)

    def test_ledger_rejects_overbudget_and_unmarked_fixtures(self):
        adm = admission("C_COUPLING_TEST_FIXTURE", ["CASE_1"])
        adm["approved_entry_budget"] = 2
        with self.assertRaisesRegex(L.LedgerError, "admission_budget"):
            L.initial_ledger(adm, "4" * 64, expected_science_owner=L.SCIENCE_OWNER_ID)
        adm = admission("C_COUPLING_TEST_FIXTURE", ["CASE_1"])
        state = L.initial_ledger(adm, "5" * 64, expected_science_owner=L.SCIENCE_OWNER_ID)
        with self.assertRaisesRegex(L.LedgerError, "offline_fixture_marker_required"):
            L.reconcile_offline_receipt(
                state, adm, receipt(adm, "CASE_1", "5" * 64), admission_sha256="5" * 64,
                expected_science_owner=L.SCIENCE_OWNER_ID, test_fixture_only=False,
            )


def admission(batch, ids):
    return {
        "schema_version": L.ADMISSION_SCHEMA,
        "batch_id": batch,
        "science_owner": L.SCIENCE_OWNER_ID,
        "scientific_admission": "PASS",
        "approved_case_set": list(ids),
        "approved_entry_budget": len(ids),
        "no_replay": True,
        "revoked": False,
    }


def receipt(adm, case_id, admission_sha):
    return {
        "schema": "APCD_COUPLING_SCIENCE_VALIDITY_RECEIPT_V1",
        "verdict": "PASS",
        "outputs": 609,
        "scientific_validated": True,
        "batch_id": adm["batch_id"],
        "case_id": case_id,
        "attempt_id": "attempt_001",
        "admission_file_sha256": admission_sha,
        "science_receipt_sha256": hashlib.sha256(
            (adm["batch_id"] + case_id).encode("utf-8")
        ).hexdigest(),
    }


if __name__ == "__main__":
    unittest.main()
