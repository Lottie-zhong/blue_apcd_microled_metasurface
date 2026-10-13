import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from apcd_gpu_v2.diag2 import (
    BATCH_ID,
    DATASET_ID,
    DIAG2_CASES,
    DIAG2_ROLE,
    Pin,
    validate_diag2_admission,
    validate_diag2_contract,
)
from apcd_gpu_v2.ledger import Refused


COUPLING_ROOT = Path(
    os.environ.get(
        "APCD_TEST_COUPLING_ROOT",
        r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1",
    )
)
PREPARATION = (
    COUPLING_ROOT
    / "reports/coupling/APCD_COUPLING_DIAG2_V21_ADMISSION_PREPARATION_V1"
)
CONTRACT_PATH = (
    COUPLING_ROOT
    / "reports/coupling/APCD_COUPLING_V21_SCIENCE_CONTRACT_CLOSEOUT_V1"
    / "SCIENCE_CONTRACT_6PS.json"
)


def frozen_inputs():
    manifest_path = PREPARATION / "DIAG2_ADMISSION_CANDIDATE_MANIFEST.json"
    assert manifest_path.is_file(), "official candidate manifest missing"
    assert CONTRACT_PATH.is_file(), "official frozen 6 ps contract missing"
    manifest_raw = manifest_path.read_bytes()
    contract_raw = CONTRACT_PATH.read_bytes()
    manifest = json.loads(manifest_raw)
    contract = json.loads(contract_raw)
    contract_sha = hashlib.sha256(contract_raw).hexdigest()
    assert hashlib.sha256(
        json.dumps(contract, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest() == contract_sha
    assert manifest["official_frozen_contract"]["raw_sha256"] == contract_sha
    assert manifest["official_frozen_contract"]["canonical_sha256"] == contract_sha
    assert manifest["batch"]["batch_id"] == BATCH_ID
    assert manifest["batch"]["dataset_id"] == DATASET_ID
    assert manifest["batch"]["case_set_is_exactly_two_original_identities"] is True
    assert [row["case_id"] for row in manifest["batch"]["cases"]] == list(DIAG2_CASES)
    assert all(
        row["attempt_id"] == "attempt_001"
        and row["role"] == DIAG2_ROLE
        and row["mesh_nm"] == 5
        and row["simulation_time_s"] == 6e-12
        and row["auto_shutoff_min"] == 1e-6
        and row["max_entries"] == 1
        and row["entry_count"] == 0
        and row["replay_count"] == 0
        for row in manifest["batch"]["cases"]
    )
    assert manifest["science_budget"]["diag2_entered"] == 0
    assert manifest["science_budget"]["diag2_remaining"] == 2
    assert manifest["science_budget"]["doe56_unentered"] == 52
    assert manifest["science_budget"]["doe56_mutable"] is False
    return manifest_path, manifest_raw, manifest, CONTRACT_PATH, contract_raw, contract, contract_sha


def request_for(row, contract_path, contract_sha):
    return SimpleNamespace(
        physical_contract=Pin(path=str(contract_path), sha256=contract_sha),
        physical_contract_sha256=contract_sha,
        case_id=row["case_id"],
        attempt_id=row["attempt_id"],
        parent_anchor_case_id=row["anchor_case_id"],
        ordered_D_nm=tuple(row["ordered_D1_D6_nm"]),
        geometry_sha256=row["geometry_sha256"],
    )


@pytest.mark.parametrize("index", [0, 1], ids=["A1", "A2"])
def test_real_frozen_diag2_contract_compatibility_without_rewrite(index):
    manifest_path, manifest_raw, manifest, contract_path, contract_raw, contract, sha = frozen_inputs()
    row = manifest["batch"]["cases"][index]
    request = request_for(row, contract_path, sha)
    config = SimpleNamespace(physical_contract_sha256=sha)

    accepted = validate_diag2_contract(config, request)

    assert accepted == contract
    assert hashlib.sha256(manifest_path.read_bytes()).digest() == hashlib.sha256(manifest_raw).digest()
    assert hashlib.sha256(contract_path.read_bytes()).digest() == hashlib.sha256(contract_raw).digest()


def test_wrong_contract_sha_is_denied():
    _, _, manifest, contract_path, _, _, sha = frozen_inputs()
    request = request_for(manifest["batch"]["cases"][0], contract_path, sha)
    with pytest.raises(Refused, match="PHYSICAL_CONTRACT_CONFIG_MISMATCH"):
        validate_diag2_contract(SimpleNamespace(physical_contract_sha256="0" * 64), request)


def test_real_contract_case_or_geometry_mismatch_is_denied():
    _, _, manifest, contract_path, _, _, sha = frozen_inputs()
    row = manifest["batch"]["cases"][0]
    request = request_for(row, contract_path, sha)
    request.geometry_sha256 = "0" * 64
    with pytest.raises(Refused, match="FROZEN_CASE_BINDING_MISMATCH"):
        validate_diag2_contract(SimpleNamespace(physical_contract_sha256=sha), request)


def test_unissued_production_admission_remains_denied_after_contract_adapter():
    _, _, manifest, contract_path, _, _, sha = frozen_inputs()
    row = manifest["batch"]["cases"][0]
    root = Path("D:/apcd_runtime/coupling_v3_time_diag2_v1/candidate_setups").resolve()
    request = SimpleNamespace(
        schema_version="APCD_V2_DIAG2_REQUEST_V1",
        dataset_id=DATASET_ID,
        batch_id=BATCH_ID,
        config_sha256="request-config",
        pre_fsp=str(root / row["case_id"] / "attempt_001" / "pre.fsp"),
    )
    config = SimpleNamespace(
        schema_version="APCD_V2_DIAG2_SERIAL_V1",
        mode="PRODUCTION_GPU",
        dataset_id=DATASET_ID,
        batch_id=BATCH_ID,
        sha256="request-config",
        candidate_fsp_root=str(root),
        scientific_admission=SimpleNamespace(read=lambda: {"status": "NOT_ISSUED"}),
        physical_contract_sha256=sha,
    )
    with pytest.raises(Refused, match="SCIENTIFIC_ADMISSION_NOT_GRANTED"):
        validate_diag2_admission(config, request)
