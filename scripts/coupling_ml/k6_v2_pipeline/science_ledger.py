"""Offline validator for the external APCD_COUPLING_BATCH_ENTRY_LEDGER_V1 protocol.

This module never opens or writes a production ledger. Callers pass isolated JSON objects.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

SCHEMA = "APCD_COUPLING_BATCH_ENTRY_LEDGER_V1"
ADMISSION_SCHEMA = "APCD_GPU_V21_SCIENCE_ADMISSION_V1"
SCIENCE_OWNER_ID = "APCD_COUPLING_ML_SCIENCE_OWNER_V1"


class LedgerError(ValueError):
    pass


def _need(ok: bool, code: str) -> None:
    if not ok:
        raise LedgerError(code)


def _unique(values: Any, code: str) -> list[str]:
    _need(isinstance(values, list) and all(isinstance(x, str) and x for x in values), code)
    _need(len(values) == len(set(values)), code)
    return values


def initial_ledger(admission: Mapping[str, Any], admission_sha256: str,
                   *, expected_science_owner: str) -> dict[str, Any]:
    """Build an in-memory ledger view from an independently authenticated admission."""
    _need(expected_science_owner == SCIENCE_OWNER_ID, "trusted_science_owner_pin")
    _need(admission.get("schema_version") == ADMISSION_SCHEMA, "admission_schema")
    _need(admission.get("science_owner") == SCIENCE_OWNER_ID, "admission_owner")
    _need(admission.get("scientific_admission") == "PASS", "admission_science_not_pass")
    _need(admission.get("no_replay") is True and admission.get("revoked") is False, "admission_policy")
    ids = _unique(admission.get("approved_case_set"), "admission_case_set")
    budget = admission.get("approved_entry_budget")
    _need(isinstance(budget, int) and not isinstance(budget, bool) and budget == len(ids), "admission_budget")
    _need(isinstance(admission_sha256, str) and len(admission_sha256) == 64, "admission_sha")
    out = {
        "schema": SCHEMA, "batch_id": admission.get("batch_id"),
        "admission_sha256": admission_sha256, "authorized_entry_budget": budget,
        "no_replay": True, "replay_count": 0,
        "entered_case_ids": [], "entered_count": 0,
        "remaining_unentered_case_ids": list(ids), "remaining_unentered_count": budget,
        "truth_valid_case_ids": [], "truth_valid_count": 0,
        "labels_valid_case_ids": [], "labels_valid_count": 0,
        "case_records": {},
    }
    validate_ledger(out, expected_batch_id=out["batch_id"],
                    expected_admission_sha256=admission_sha256,
                    expected_case_ids=ids, expected_budget=budget)
    return out


def validate_ledger(data: Mapping[str, Any], *, expected_batch_id: str,
                    expected_admission_sha256: str, expected_case_ids: list[str],
                    expected_budget: int) -> None:
    _need(data.get("schema") == SCHEMA, "ledger_schema")
    _need(data.get("batch_id") == expected_batch_id, "ledger_batch_id")
    _need(data.get("admission_sha256") == expected_admission_sha256, "ledger_admission_sha")
    _need(data.get("authorized_entry_budget") == expected_budget == len(expected_case_ids), "ledger_budget")
    _need(data.get("no_replay") is True and data.get("replay_count") == 0, "ledger_replay_policy")
    entered = _unique(data.get("entered_case_ids"), "ledger_entered")
    remaining = _unique(data.get("remaining_unentered_case_ids"), "ledger_remaining")
    truth = _unique(data.get("truth_valid_case_ids"), "ledger_truth")
    labels = _unique(data.get("labels_valid_case_ids"), "ledger_labels")
    _need(not set(entered) & set(remaining), "ledger_entered_remaining_overlap")
    _need(set(entered) | set(remaining) == set(expected_case_ids), "ledger_case_set")
    _need(set(labels) <= set(truth) <= set(entered), "ledger_truth_subset")
    for ids, count_key in (
        (entered, "entered_count"), (remaining, "remaining_unentered_count"),
        (truth, "truth_valid_count"), (labels, "labels_valid_count"),
    ):
        _need(data.get(count_key) == len(ids), "ledger_count:" + count_key)
    _need(len(entered) + len(remaining) == expected_budget, "ledger_total")
    records = data.get("case_records")
    _need(isinstance(records, Mapping) and set(records) <= set(expected_case_ids), "ledger_records")
    for cid, row in records.items():
        _need(isinstance(row, Mapping), "ledger_record_shape")
        _need(row.get("attempt_id") == "attempt_001", "ledger_attempt")
        _need(row.get("entry_count") in (0, 1) and row.get("replay_count") == 0, "ledger_record_count")
        _need(bool(row.get("truth_valid")) == (cid in truth), "ledger_record_truth")
        _need(bool(row.get("labels_valid")) == (cid in labels), "ledger_record_labels")
        if cid in entered:
            _need(row.get("entry_count") == 1, "ledger_record_entry")
        else:
            _need(row.get("entry_count") == 0, "ledger_record_unentered")


def reconcile_offline_receipt(data: Mapping[str, Any], admission: Mapping[str, Any],
                              receipt: Mapping[str, Any], *, admission_sha256: str,
                              expected_science_owner: str, test_fixture_only: bool) -> dict[str, Any]:
    """Reconcile a synthetic offline receipt into a copied ledger object."""
    _need(test_fixture_only is True, "offline_fixture_marker_required")
    _need(expected_science_owner == SCIENCE_OWNER_ID, "trusted_science_owner_pin")
    _need(admission.get("science_owner") == SCIENCE_OWNER_ID, "admission_owner")
    _need(admission.get("batch_id") == data.get("batch_id"), "reconcile_batch")
    _need(admission_sha256 == data.get("admission_sha256"), "reconcile_admission_sha")
    _need(receipt.get("schema") == "APCD_COUPLING_SCIENCE_VALIDITY_RECEIPT_V1"
          and receipt.get("verdict") == "PASS" and receipt.get("scientific_validated") is True
          and receipt.get("outputs") == 609, "receipt_not_scientifically_valid")
    _need(receipt.get("batch_id") == data.get("batch_id")
          and receipt.get("admission_file_sha256") == admission_sha256, "receipt_authority_binding")
    cid = receipt.get("case_id")
    ids = list(admission.get("approved_case_set", []))
    _need(cid in ids and cid in data.get("remaining_unentered_case_ids", []), "case_not_unentered")
    _need(receipt.get("attempt_id") == "attempt_001", "receipt_attempt")
    _need(isinstance(receipt.get("science_receipt_sha256"), str)
          and len(receipt["science_receipt_sha256"]) == 64, "receipt_sha")
    out = deepcopy(data)
    out["entered_case_ids"].append(cid)
    out["entered_count"] += 1
    out["remaining_unentered_case_ids"].remove(cid)
    out["remaining_unentered_count"] -= 1
    out["truth_valid_case_ids"].append(cid)
    out["truth_valid_count"] += 1
    out["labels_valid_case_ids"].append(cid)
    out["labels_valid_count"] += 1
    out["case_records"][cid] = {
        "attempt_id": "attempt_001", "phase": "OFFLINE_FIXTURE_VALIDATED",
        "entry_count": 1, "replay_count": 0, "truth_valid": True, "labels_valid": True,
        "solver_entered": False, "fixture_only": True,
        "science_receipt_sha256": receipt["science_receipt_sha256"],
    }
    validate_ledger(out, expected_batch_id=out["batch_id"],
                    expected_admission_sha256=admission_sha256,
                    expected_case_ids=ids, expected_budget=out["authorized_entry_budget"])
    return out
