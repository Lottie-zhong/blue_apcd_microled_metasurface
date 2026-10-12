import json
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from apcd_gpu_v2.artifacts import sha256
from pydantic import ValidationError

from apcd_gpu_v2.diag2 import (BATCH_ID, DATASET_ID, DIAG2_CASES, DIAG2_ROLE, CASE_SPEC, Diag2Request)
from apcd_gpu_v2.ledger import Refused
from apcd_gpu_v2.serial import Diag2Budget
from apcd_gpu_v2 import serial


def _config(path):
    return SimpleNamespace(
        coupling_ledger=str(path),
        mode="PRODUCTION_EQUIVALENT",
        registry=SimpleNamespace(sha256="1" * 64),
        scientific_admission=SimpleNamespace(sha256="2" * 64),
        physical_contract_sha256="3" * 64,
        release=SimpleNamespace(sha256="4" * 64),
        sha256="5" * 64,
        importer_entrypoint="load_diag2_runner_case",
    )


def _ledger(config, *, status="OPEN"):
    records = {
        case_id: {
            "attempt_id": "attempt_001",
            "max_entry_count": 1,
            "entry_count": 0,
            "replay_count": 0,
            "phase": "UNENTERED",
        }
        for case_id in DIAG2_CASES
    }
    return {
        "schema": "APCD_COUPLING_DIAG2_ENTRY_LEDGER_V1",
        "status": status,
        "dataset_id": DATASET_ID,
        "batch_id": BATCH_ID,
        "case_ids": list(DIAG2_CASES),
        "max_new_entries": 2,
        "per_case_entry_limit": 1,
        "automatic_replays": 0,
        "registry_sha256": config.registry.sha256,
        "scientific_admission_sha256": config.scientific_admission.sha256,
        "physical_contract_sha256": config.physical_contract_sha256,
        "entry_count": 0,
        "remaining_count": 2,
        "truth_valid_count": 0,
        "labels_valid_count": 0,
        "entered_case_ids": [],
        "remaining_case_ids": list(DIAG2_CASES),
        "truth_valid_case_ids": [],
        "labels_valid_case_ids": [],
        "case_records": records,
    }


def _request(case_id=DIAG2_CASES[0], suffix="a"):
    return SimpleNamespace(
        dataset_id=DATASET_ID,
        batch_id=BATCH_ID,
        case_id=case_id,
        attempt_id="attempt_001",
        request_sha256=suffix * 64,
        admission_sha256=chr(ord(suffix) + 1) * 64,
        pre_fsp_sha256="c" * 64,
        source_setup_fsp_sha256="d" * 64,
        source_run_fsp_sha256="e" * 64,
        physical_contract_sha256="3" * 64,
    )


def _write_ledger(path, config, **kwargs):
    path.write_text(json.dumps(_ledger(config, **kwargs), sort_keys=True), encoding="utf-8")


def test_receipt_committed_before_ledger_crash_recovers_as_consumed(tmp_path):
    path = tmp_path / "diag2_entry_ledger.json"
    config = _config(path)
    _write_ledger(path, config)
    budget = Diag2Budget(config)
    req = _request()

    def crash(step):
        if step == "coupling_receipt_committed":
            raise RuntimeError("injected crash")

    with pytest.raises(RuntimeError, match="injected crash"):
        budget.prepare_entry(req, "owner-token-1", crash)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["entry_count"] == 0
    assert req.case_id in data["remaining_case_ids"]
    assert budget.receipt_path(req).is_file()

    reconciled = budget.reconcile_entry_evidence(req)
    assert reconciled == {"entered": True, "replay_allowed": False, "repaired": True}
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["entry_count"] == 1
    assert data["remaining_count"] == 1
    assert data["case_records"][req.case_id]["phase"] == "V2_ENTRY_UNCERTAIN"
    with pytest.raises(Refused, match="DIAG2_ENTRY_CONSUMED_OR_UNCERTAIN_NO_REPLAY"):
        budget.validate(req)


def test_exact_two_case_budget_and_duplicate_entry_are_enforced(tmp_path):
    path = tmp_path / "diag2_entry_ledger.json"
    config = _config(path)
    _write_ledger(path, config)
    budget = Diag2Budget(config)

    first, second = _request(DIAG2_CASES[0], "a"), _request(DIAG2_CASES[1], "c")
    budget.prepare_entry(first, "owner-token-1")
    budget.prepare_entry(second, "owner-token-2")

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["entry_count"] == 2
    assert data["remaining_count"] == 0
    assert set(data["entered_case_ids"]) == set(DIAG2_CASES)
    assert all(data["case_records"][cid]["replay_count"] == 0 for cid in DIAG2_CASES)
    with pytest.raises(Refused, match="DIAG2_ENTRY_CONSUMED_OR_UNCERTAIN_NO_REPLAY"):
        budget.validate(first)
    extra = _request("UNREGISTERED_CASE", "e")
    with pytest.raises(Refused, match="DIAG2_ENTRY_CONSUMED_OR_UNCERTAIN_NO_REPLAY"):
        budget.validate(extra)


def test_entry_and_launch_markers_use_one_writer_lock(tmp_path, monkeypatch):
    path = tmp_path / "diag2_entry_ledger.json"
    config = _config(path)
    _write_ledger(path, config)
    budget = Diag2Budget(config)
    req = _request()
    locks = []
    real_exclusive = serial.exclusive

    @contextmanager
    def observe_lock(lock_path):
        locks.append(Path(lock_path))
        with real_exclusive(lock_path):
            yield

    monkeypatch.setattr(serial, "exclusive", observe_lock)
    budget.prepare_entry(req, "owner-token-1")
    budget.mark_launch_request(req, "owner-token-1")
    assert len(locks) == 2
    assert locks[0] == locks[1] == path.with_suffix(".v2_writer.lock")
    with pytest.raises(Refused, match="COUPLING_LAUNCH_ALREADY_REQUESTED_NO_REPLAY"):
        budget.mark_launch_request(req, "owner-token-1")


def test_terminal_label_publication_is_sha_pinned_and_idempotent(tmp_path):
    path = tmp_path / "diag2_entry_ledger.json"
    config = _config(path)
    _write_ledger(path, config)
    budget = Diag2Budget(config)
    req = _request()
    budget.prepare_entry(req, "owner-token-1")

    labels = tmp_path / "candidate_labels.npz"
    c_hat = np.arange(21 * 7 * 2, dtype=np.float64).reshape(21, 7, 2).astype(np.complex128)
    np.savez(labels, C_hat_real=c_hat.real, C_hat_imag=c_hat.imag, P_scale=np.ones(21))
    evidence = {
        "bundle": {"path": str(tmp_path / "native_pair"), "files": {"run.fsp": {"sha256": "a" * 64}}},
        "validation": {
            "verdict": "PASS",
            "outputs": 609,
            "fresh_load_verified": True,
            "actual_importer": "load_diag2_runner_case",
            "labels_artifact": {"path": str(labels), "sha256": sha256(labels)},
            "time_convergence": {"status": "TIME_CONVERGENCE_UNRESOLVED"},
            "time_convergence_artifact": {"sha256": "b" * 64},
        },
    }
    budget.finish_truth(req, evidence)
    data = json.loads(path.read_text(encoding="utf-8"))
    row = data["case_records"][req.case_id]
    assert row["phase"] == "V2_TRUTH_VALID"
    assert data["truth_valid_count"] == data["labels_valid_count"] == 1
    target = Path(row["evidence"]["validation"]["labels_artifact"]["path"])
    published = path.parent / "DIAG2_LABELS" / f"{req.case_id}__attempt_001.npz"
    assert published.is_file()
    original_sha = sha256(published)
    receipt = Path(row["terminal_receipt"])
    receipt_sha = sha256(receipt)

    budget.finish_truth(req, evidence)
    assert sha256(published) == original_sha
    assert sha256(receipt) == receipt_sha
    after = json.loads(path.read_text(encoding="utf-8"))
    assert after["entry_count"] == 1
    assert after["truth_valid_count"] == after["labels_valid_count"] == 1


def _typed_request_doc(case_id):
    spec = CASE_SPEC[case_id]
    source_setup = r"D:\apcd_runtime\gpu_v3_interface_audit_20261011_v1\source_setup"
    cid = case_id
    return {
        "schema_version": "APCD_V2_DIAG2_REQUEST_V1",
        "dataset_id": DATASET_ID,
        "batch_id": BATCH_ID,
        "case_id": case_id,
        "attempt_id": "attempt_001",
        "role": DIAG2_ROLE,
        "source_case_id": spec["source_case_id"],
        "parent_anchor_case_id": spec["parent_anchor_case_id"],
        "ordered_D_nm": list(spec["ordered_D_nm"]),
        "geometry_sha256": spec["geometry_sha256"],
        "source_run_fsp_sha256": spec["source_run_fsp_sha256"],
        "source_setup_fsp_sha256": spec["source_setup_fsp_sha256"],
        "pre_fsp": rf"D:\apcd_runtime\coupling_v3_time_diag2_v1\candidate_setups\{cid}\attempt_001\pre.fsp",
        "pre_fsp_sha256": spec["pre_fsp_sha256"],
        "source_manifest": {
            "path": rf"{source_setup}\{spec['source_case_id']}\attempt_001\source_manifest.json",
            "sha256": "1" * 64,
        },
        "physical_contract": {
            "path": r"D:\candidate\physical_contract.json",
            "sha256": "2" * 64,
        },
        "physical_contract_sha256": "3" * 64,
        "simulation_time_s": 6e-12,
        "auto_shutoff_min": 1e-6,
        "config_sha256": "4" * 64,
    }


@pytest.mark.parametrize("case_id", DIAG2_CASES)
def test_diag2_request_identity_accepts_only_pinned_setup_fsp(case_id):
    request = Diag2Request.model_validate_json(json.dumps(_typed_request_doc(case_id)))
    assert request.case_id == case_id
    assert request.attempt_id == "attempt_001"
    assert request.pre_fsp_sha256 == CASE_SPEC[case_id]["pre_fsp_sha256"]


def test_diag2_request_rejects_wrong_setup_fsp_and_replay_attempt():
    document = _typed_request_doc(DIAG2_CASES[0])
    document["pre_fsp_sha256"] = "0" * 64
    with pytest.raises(ValidationError, match="DIAG2 frozen case binding mismatch"):
        Diag2Request.model_validate_json(json.dumps(document))
    document = _typed_request_doc(DIAG2_CASES[1])
    document["attempt_id"] = "attempt_002"
    with pytest.raises(ValidationError):
        Diag2Request.model_validate_json(json.dumps(document))
