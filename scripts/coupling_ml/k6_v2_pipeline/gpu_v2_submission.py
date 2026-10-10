"""Read-only Coupling-side audit for the installed GPU V2 G027 request.

This module never dispatches a request, changes a ledger, enables a task, or alters
science release authority. The current valid result is the explicitly installed DENY.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any

RUNTIME = Path(r"D:\apcd_runtime\gpu_platform_v2_serial_production_v1")
COUPLING_ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
INSTALLATION_PATH = RUNTIME / "INSTALLATION.json"
INVENTORY_PATH = RUNTIME / "INSTALLED_CODE_SHA256.json"
CONFIG_PATH = RUNTIME / "serial_config.json"
REQUESTS_PATH = RUNTIME / "g027_requests.json"
RELEASE_PATH = RUNTIME / "SCIENCE_RELEASE_DENY.json"
LEDGER_PATH = COUPLING_ROOT / "reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1/QUEUE_EXECUTION_LEDGER_V1.json"


class HandoffAuditError(RuntimeError):
    pass


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise HandoffAuditError("DUPLICATE_JSON_KEY:" + key)
        result[key] = value
    return result


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=_unique_pairs)


def audit_g027_candidate() -> dict:
    """Check installed hashes, Coupling budget, candidate pins, and expected release denial."""
    for required in (INSTALLATION_PATH, INVENTORY_PATH, CONFIG_PATH, REQUESTS_PATH, RELEASE_PATH, LEDGER_PATH):
        if not required.is_file():
            raise HandoffAuditError("REQUIRED_AUTHORITY_MISSING:" + str(required))

    installation = _json(INSTALLATION_PATH)
    inventory_sha = sha256_file(INVENTORY_PATH)
    if inventory_sha != installation["code_inventory_sha256"]:
        raise HandoffAuditError("INSTALLED_CODE_INVENTORY_SHA_MISMATCH")
    inventory = _json(INVENTORY_PATH)
    release_root = Path(installation["code_release"]).resolve()
    if release_root.name != installation.get("code_head"):
        raise HandoffAuditError("INSTALLED_RELEASE_HEAD_PATH_MISMATCH")
    mismatches = []
    for relative, expected in inventory.items():
        path = release_root / Path(relative)
        if not path.is_file() or sha256_file(path) != expected:
            mismatches.append(relative)
    if mismatches:
        raise HandoffAuditError("INSTALLED_CODE_HASH_MISMATCH:" + ",".join(mismatches[:8]))

    config_raw_sha = sha256_file(CONFIG_PATH)
    requests_raw_sha = sha256_file(REQUESTS_PATH)
    release_raw_sha = sha256_file(RELEASE_PATH)
    if config_raw_sha != installation["configuration_sha256"]:
        raise HandoffAuditError("CONFIGURATION_RAW_SHA_MISMATCH")
    if requests_raw_sha != installation["request_sha256"]:
        raise HandoffAuditError("REQUEST_FILE_RAW_SHA_MISMATCH")
    if release_raw_sha != installation["release_sha256"]:
        raise HandoffAuditError("SCIENCE_RELEASE_RAW_SHA_MISMATCH")

    package_root = release_root / "platform_v2"
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    serial = importlib.import_module("apcd_gpu_v2.serial")
    config = serial.SerialConfig.model_validate_json(json.dumps(_json(CONFIG_PATH)))
    request_rows = _json(REQUESTS_PATH)
    if not isinstance(request_rows, list) or len(request_rows) != 1:
        raise HandoffAuditError("G027_REQUEST_FILE_NOT_SINGLE_CASE")
    request = serial.SerialRequest.model_validate_json(json.dumps(request_rows[0]))
    if request.case_id != "K6GDP2_DEV_G027" or request.attempt_id != "attempt_001":
        raise HandoffAuditError("G027_REQUEST_IDENTITY_MISMATCH")
    if config.sha256 != installation["configuration_digest"]:
        raise HandoffAuditError("CONFIGURATION_DIGEST_MISMATCH")
    if request.request_sha256 != installation["request_digest"]:
        raise HandoffAuditError("REQUEST_DIGEST_MISMATCH")
    if request.config_sha256 != config.sha256:
        raise HandoffAuditError("REQUEST_CONFIG_BINDING_MISMATCH")
    if Path(config.release.path).resolve() != RELEASE_PATH.resolve():
        raise HandoffAuditError("CONFIG_RELEASE_PATH_MISMATCH")

    ledger_before = sha256_file(LEDGER_PATH)
    budget = serial.CouplingBudget(config)
    try:
        ledger = budget.validate(request)
        budget_eligible, budget_reason = True, None
    except serial.Refused as exc:
        ledger = _json(LEDGER_PATH)
        budget_eligible, budget_reason = False, str(exc)
    ledger_after = sha256_file(LEDGER_PATH)
    if ledger_before != ledger_after:
        raise HandoffAuditError("READ_ONLY_AUDIT_MUTATED_COUPLING_LEDGER")

    release = _json(RELEASE_PATH)
    admission_reason = None
    admission_validated = False
    try:
        serial.validate_admission(config, request)
        admission_validated = True
    except serial.Refused as exc:
        admission_reason = str(exc)
    if release.get("science_authorized") is not False or release.get("requests") != []:
        raise HandoffAuditError("LIVE_RELEASE_IS_NOT_THE_EXPECTED_DENY")
    if admission_validated or admission_reason != "FORMAL_SCIENCE_RELEASE_MISSING_OR_UNBOUND":
        raise HandoffAuditError("LIVE_V2_ADMISSION_GATE_DID_NOT_FAIL_AT_EXPECTED_DENY:" + str(admission_reason))

    record = ledger.get("case_records", {}).get(request.case_id, {})
    counts = {
        "authorized": ledger.get("authorized_development_case_count"),
        "entered": ledger.get("entered_count"),
        "truth_valid": ledger.get("truth_valid_count"),
        "labels_valid": ledger.get("labels_valid_count"),
        "unentered": ledger.get("remaining_unentered_count"),
        "automatic_replay": ledger.get("automatic_replay_count"),
        "confirmation_response_access": ledger.get("confirmation_response_access_count"),
    }
    return {
        "schema": "COUPLING_GPU_V2_READ_ONLY_G027_AUDIT_V1",
        "status": "G027_SCIENCE_ADMISSION_BLOCKED",
        "installed_code_head": installation["code_head"],
        "installed_code_inventory_sha256": inventory_sha,
        "serial_py_sha256": inventory["platform_v2/apcd_gpu_v2/serial.py"],
        "serial_controller_py_sha256": inventory["platform_v2/tools/serial_controller.py"],
        "config_raw_sha256": config_raw_sha,
        "config_digest": config.sha256,
        "request_file_raw_sha256": requests_raw_sha,
        "request_sha256": request.request_sha256,
        "request_admission_sha256": request.admission_sha256,
        "release_sha256": release_raw_sha,
        "queue_sha256": config.queue.sha256,
        "source_manifest_sha256": request.source_manifest.sha256,
        "pre_fsp_sha256": request.pre_fsp_sha256,
        "physical_contract_sha256": request.physical_contract_sha256,
        "case_id": request.case_id,
        "attempt_id": request.attempt_id,
        "role": request.role,
        "ordered_D_nm": list(request.ordered_D_nm),
        "budget_eligible": budget_eligible,
        "budget_refusal": budget_reason,
        "case_record_phase": record.get("phase"),
        "entry_consumed": bool(record.get("entry_consumed")),
        "truth_available": bool(record.get("truth_available")),
        "counts": counts,
        "release_science_authorized": release.get("science_authorized"),
        "release_owner_clear": release.get("owner_clear"),
        "release_request_count": len(release.get("requests", [])),
        "admission_validated": admission_validated,
        "admission_refusal": admission_reason,
        "ledger_sha256_before": ledger_before,
        "ledger_sha256_after": ledger_after,
        "ledger_unchanged": ledger_before == ledger_after,
        "dispatch_performed": False,
        "solver_entry_performed": False,
    }


if __name__ == "__main__":
    print(json.dumps(audit_g027_candidate(), sort_keys=True, indent=2))
