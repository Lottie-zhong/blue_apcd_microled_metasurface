# -*- coding: utf-8 -*-
"""Synthetic tests for the pinned 128-case K6 V2 budget and locked registry guard."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import controlled_admission_v1 as controlled
import runner


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _h(value):
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return path


class K6V2SolverBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.base_fsp = self.root / "base.fsp"
        self.base_fsp.write_bytes(b"immutable base setup")
        self.expansion_sha = _h("frozen-expansion")
        self.first_id = "K6LDA1_DEV_D1_M05"
        self.first_geometry = [215, 195, 210, 150, 140, 210]
        self.first_geometry_sha = _h("first-geometry")
        self.first_source_path = self.root / "first_geometry_authority.json"
        self.first_source = {
            "schema": controlled.GEOMETRY_SOURCE_SCHEMA,
            "eligible": True,
            "case_id": self.first_id,
            "attempt_id": "attempt_001",
            "ordered_D_nm": self.first_geometry,
            "geometry_hash_sha256": self.first_geometry_sha,
            "expansion_manifest_sha256": self.expansion_sha,
            "base_setup_fsp_path": str(self.base_fsp),
            "base_setup_fsp_sha256": _sha(self.base_fsp),
            "setup_admission_authorized": True,
            "solver_entry_authorized": False,
            "max_solver_entries": 0,
        }
        _write_json(self.first_source_path, self.first_source)
        self.route_rows = []
        self.dev_rows = []
        self.sealed_rows = []
        for i in range(160):
            if i < 128:
                case_id = self.first_id if i == 0 else "K6V2_DEV_SYN_{:03d}".format(i + 1)
                role = "DEVELOPMENT_LOCAL_AXIS" if i < 12 else "DEVELOPMENT_GLOBAL"
                geometry = self.first_geometry if i == 0 else [100 + 5 * ((i + j) % 27) for j in range(6)]
                geometry_sha = self.first_geometry_sha if i == 0 else _h("geometry:" + case_id)
                source_path = self.first_source_path if i == 0 else self.root / ("source_" + case_id + ".json")
                source_sha = _sha(source_path) if i == 0 else _h("source:" + case_id)
            else:
                offset = i - 128
                case_id = "K6V2_SEALED_SYN_{:03d}".format(offset + 1)
                role = "SEALED_LOCAL_COMBINATION" if offset < 4 else "SEALED_CONFIRMATION_GLOBAL"
                geometry = [100 + 5 * ((i + j) % 27) for j in range(6)]
                geometry_sha = _h("geometry:" + case_id)
                source_path = self.root / ("source_" + case_id + ".json")
                source_sha = _h("source:" + case_id)
            row = {
                "case_id": case_id,
                "attempt_id": "attempt_001",
                "role": role,
                "ordered_D_nm": geometry,
                "geometry_hash_sha256": geometry_sha,
                "path": str(source_path),
                "sha256": source_sha,
                "setup_admission_authorized": True,
                "solver_entry_authorized": False,
                "max_solver_entries": 0,
                "training_authorized": False,
                "training_dataset_eligible": False,
            }
            self.route_rows.append(row)
            (self.dev_rows if i < 128 else self.sealed_rows).append(row)
        budget_cases = []
        for index, row in enumerate(self.dev_rows, start=1):
            budget_cases.append({
                "sequence_index": index,
                "case_id": row["case_id"],
                "attempt_id": row["attempt_id"],
                "role": row["role"],
                "ordered_D_nm": row["ordered_D_nm"],
                "geometry_hash_sha256": row["geometry_hash_sha256"],
                "geometry_authority_path": row["path"],
                "geometry_authority_sha256": row["sha256"],
                "setup_admission_authorized": True,
                "solver_entry_authorized": True,
                "max_solver_entries": 1,
                "post_entry_automatic_replays": 0,
                "training_dataset_eligible": False,
            })
        ids = [row["case_id"] for row in budget_cases]
        self.budget = {
            "schema": controlled.K6_V2_SOLVER_BUDGET_SCHEMA,
            "budget_id": "K6V2_SYNTHETIC_128_CASES",
            "route_version": controlled.ROUTE_VERSION,
            "status": "OWNER_APPROVED_ACTIVE",
            "authorization": {
                "task_id": "COUPLING_K6_V2_128_DEVELOPMENT_CASES_GENERATION_V1",
                "approval_kind": "DIRECT_USER_INSTRUCTION",
                "approval_scope": "128 development cases only",
                "cryptographic_signature_claimed": False,
            },
            "frozen_inputs": {
                "case_registration_package_sha256": _h("package"),
                "sha256_inventory_sha256": _h("inventory"),
                "development_case_allowlist_sha256": _h("allowlist"),
                "candidate_table_sha256": _h("candidate"),
                "amendment_01_sha256": _h("amendment"),
                "base_contract_sha256": _h("contract"),
                "expansion_manifest_sha256": self.expansion_sha,
                "coupling_source_head": "1" * 40,
            },
            "limits": {
                "max_total_entries": 128,
                "max_entries_per_case": 1,
                "post_entry_automatic_replays": 0,
            },
            "confirmation_controls": {
                "case_count": 32,
                "case_ids": [row["case_id"] for row in self.sealed_rows],
                "solver_entry_authorized": False,
                "max_solver_entries": 0,
                "response_access_authorized": False,
                "training_fit_authorized": False,
            },
            "development_case_order_sha256": hashlib.sha256("\n".join(ids).encode("ascii")).hexdigest(),
            "development_cases": budget_cases,
        }
        self.budget_path = self.root / "k6_v2_development_solver_budget_v1.json"
        _write_json(self.budget_path, self.budget)
        self.authority = {
            "expansion_manifest_sha256": self.expansion_sha,
            "base_contract_sha256": _h("contract"),
            "k6_geometry_authorities": self.route_rows,
            "k6_v2_development_solver_budget": {
                "path": str(self.budget_path),
                "sha256": _sha(self.budget_path),
            },
        }
        self.provenance = {
            "schema": controlled.GEOMETRY_SOURCE_SCHEMA,
            "authority_path": str(self.first_source_path),
            "authority_sha256": _sha(self.first_source_path),
            "ordered_D_nm": self.first_geometry,
            "geometry_hash_sha256": self.first_geometry_sha,
            "expansion_manifest_sha256": self.expansion_sha,
        }

    def tearDown(self):
        self.temp.cleanup()

    def _grant(self):
        selected = controlled._trusted_k6_geometry(
            self.provenance, self.authority, self.first_id, "attempt_001", self.first_geometry,
            preflight=False)
        self.assertFalse(selected["solver_entry_authorized"])
        self.assertEqual(selected["max_solver_entries"], 0)
        return selected["_controlled_solver_entry_budget"]

    def test_exact_dev_case_receives_one_budget_without_mutating_setup_authority(self):
        grant = self._grant()
        self.assertEqual(grant["case_id"], self.first_id)
        self.assertEqual(grant["max_entries_per_case"], 1)
        self.assertEqual(grant["max_total_entries"], 128)
        self.assertEqual(grant["post_entry_automatic_replays"], 0)
        self.assertEqual(len(grant["authorized_case_ids"]), 128)

    def test_sealed_confirmation_is_not_in_solver_budget(self):
        row = self.sealed_rows[0]
        with self.assertRaisesRegex(controlled.ControlledAdmissionError,
                                    "K6_SOLVER_ENTRY_NOT_AUTHORIZED"):
            controlled._trusted_k6_v2_solver_entry_budget(
                self.authority, self.route_rows, row["case_id"], row["attempt_id"], row["ordered_D_nm"])

    def test_budget_bytes_must_match_the_route_pinned_sha(self):
        changed = copy.deepcopy(self.budget)
        changed["status"] = "REVOKED"
        _write_json(self.budget_path, changed)
        with self.assertRaisesRegex(controlled.ControlledAdmissionError,
                                    "K6_V2_SOLVER_BUDGET_HASH_MISMATCH"):
            controlled._trusted_k6_v2_solver_entry_budget(
                self.authority, self.route_rows, self.first_id, "attempt_001", self.first_geometry)

    def test_changed_geometry_or_grant_cap_rejected(self):
        changed = copy.deepcopy(self.budget)
        changed["development_cases"][0]["ordered_D_nm"] = [220, 195, 210, 150, 140, 210]
        _write_json(self.budget_path, changed)
        self.authority["k6_v2_development_solver_budget"]["sha256"] = _sha(self.budget_path)
        with self.assertRaisesRegex(controlled.ControlledAdmissionError,
                                    "K6_V2_SOLVER_BUDGET_CASE_AUTHORITY_MISMATCH"):
            controlled._trusted_k6_v2_solver_entry_budget(
                self.authority, self.route_rows, self.first_id, "attempt_001", self.first_geometry)

    def test_registry_guard_allows_fresh_first_case_but_rejects_replay_and_total_exhaustion(self):
        grant = self._grant()
        fresh = {"schema": "APCD_GPU_RUNNER_REGISTRY_V1", "runs": [
            {"case_id": self.first_id, "attempt_id": "attempt_001", "state": "PRECHECK_PASS"},
        ]}
        result = controlled.validate_k6_v2_registry_entry_budget(
            fresh, grant=grant, case_id=self.first_id, attempt_id="attempt_001",
            entry_states=runner.ENTRY_STATES)
        self.assertEqual(result["total_entries_before"], 0)
        replayed = copy.deepcopy(fresh)
        replayed["runs"].append({"case_id": self.first_id, "attempt_id": "attempt_001",
                                 "state": "SOLVER_ENTERED"})
        with self.assertRaisesRegex(controlled.ControlledAdmissionError,
                                    "K6_CASE_ENTRY_BUDGET_EXHAUSTED"):
            controlled.validate_k6_v2_registry_entry_budget(
                replayed, grant=grant, case_id=self.first_id, attempt_id="attempt_001",
                entry_states=runner.ENTRY_STATES)
        full = {"schema": "APCD_GPU_RUNNER_REGISTRY_V1", "runs": [
            {"case_id": self.dev_rows[1]["case_id"], "attempt_id": "attempt_001", "state": "DONE"}
            for _ in range(128)
        ]}
        with self.assertRaisesRegex(controlled.ControlledAdmissionError,
                                    "K6_TOTAL_ENTRY_BUDGET_EXHAUSTED"):
            controlled.validate_k6_v2_registry_entry_budget(
                full, grant=grant, case_id=self.first_id, attempt_id="attempt_001",
                entry_states=runner.ENTRY_STATES)

    def test_registry_rejects_attempt_identity_conflict_and_unknown_state(self):
        grant = self._grant()
        for row, error in (
                ({"case_id": self.first_id, "attempt_id": "attempt_002", "state": "DONE"},
                 "K6_CASE_ENTRY_IDENTITY_CONFLICT"),
                ({"case_id": self.dev_rows[1]["case_id"], "attempt_id": "attempt_002", "state": "PENDING"},
                 "K6_CASE_ENTRY_IDENTITY_CONFLICT"),
                ({"case_id": self.first_id, "attempt_id": "attempt_001", "state": "MYSTERY"},
                 "K6_V2_RUNNER_REGISTRY_STATE_INVALID")):
            with self.subTest(error=error), self.assertRaisesRegex(
                    controlled.ControlledAdmissionError, error):
                controlled.validate_k6_v2_registry_entry_budget(
                    {"schema": "APCD_GPU_RUNNER_REGISTRY_V1", "runs": [row]},
                    grant=grant, case_id=self.first_id, attempt_id="attempt_001",
                    entry_states=runner.ENTRY_STATES)


if __name__ == "__main__":
    unittest.main()
