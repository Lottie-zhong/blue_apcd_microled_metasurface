from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shared_fdtd.tools.pw_scientific_launcher import (  # noqa: E402
    _contract,
    contract_resolution_provenance,
    validate_config,
)


REQUIRED = {
    "monitors": {"input": "MON_IN", "pre": "MON_PRENP", "output": "MON_POSTNP"},
    "samples_nm": {"MON_IN": -100.0, "MON_PRENP": 1150.0, "MON_POSTNP": 1800.0},
    "references_nm": {"MON_IN": -50.0, "MON_PRENP": 1202.0, "MON_POSTNP": 1722.0},
    "materials": {
        "substrate": "APCD_GAN_NATIVE_M1",
        "mdc_tio2": "APCD_TIO2_NATIVE_M1",
        "mdc_sio2": "APCD_SIO2_NATIVE_M1",
        "superstrate": "Air",
    },
    "stack_layers": [["APCD_TIO2_NATIVE_M1", 44.0]],
    "wavelengths_nm": list(range(440, 461)),
}


def config(contract):
    return {
        "db": "db",
        "runtime": "runtime",
        "attempt_root": "attempt",
        "pre_fsp": "pre.fsp",
        "pre_fsp_sha256": "a" * 64,
        "physical_contract_hash": "32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5",
        "branch": "coupling_ml",
        "case": "K6V1_SCHEMA_TEST",
        "attempt": "attempt_001",
        "task": "PW_K6_FIXED_MDC_12G_STAGE1_HF_EXECUTION_V1",
        "slot_id": "GLOBAL_SLOT_2",
        "lease_token": "token",
        "fencing_generation": 60,
        "scientific_launcher": "PW_PERIODIC_PLANAR",
        "pw_contract": contract,
        "run_fsp": "attempt/run.fsp",
    }


def expect_error(fn, token):
    try:
        fn()
    except Exception as exc:
        assert token in str(exc), (token, exc)
    else:
        raise AssertionError("expected " + token)


def main():
    checks = {}
    nested = {"contract": copy.deepcopy(REQUIRED), "contract_id": "APCD_PW_PERIODIC_PLANAR_5NM_GPU_PRODUCTION_V3"}
    cfg = config(nested)
    validate_config(cfg)
    assert _contract(cfg) == REQUIRED
    assert contract_resolution_provenance(cfg)["schema_path"] == "pw_contract.contract"
    checks["A_canonical_nested_production_schema"] = "PASS"

    missing = copy.deepcopy(nested)
    del missing["contract"]["materials"]
    expect_error(lambda: validate_config(config(missing)), "SCIENTIFIC_CONTRACT_FIELD_MISSING:materials")
    checks["B_required_field_missing"] = "PASS"

    identical = copy.deepcopy(nested)
    identical.update(copy.deepcopy(REQUIRED))
    validate_config(config(identical))
    assert contract_resolution_provenance(config(identical))["resolution"] == "canonical_nested_verified_against_legacy_overlap"
    checks["C_nested_and_legacy_identical"] = "PASS"

    conflict = copy.deepcopy(identical)
    conflict["samples_nm"]["MON_IN"] = -101.0
    expect_error(lambda: validate_config(config(conflict)), "PW_CONTRACT_SCHEMA_CONFLICT:samples_nm")
    checks["D_nested_and_legacy_conflict"] = "PASS"

    legacy = copy.deepcopy(REQUIRED)
    validate_config(config(legacy))
    assert contract_resolution_provenance(config(legacy))["schema_path"] == "pw_contract"
    checks["E_legacy_compatibility"] = "PASS"

    expect_error(lambda: validate_config(config({"contract": []})), "PW_CONTRACT_SCHEMA_PATH_ERROR:pw_contract.contract")
    checks["F_schema_path_error"] = "PASS"
    print(json.dumps({"status": "PASS", "solver_invocations": 0, "checks": checks}, indent=2))


if __name__ == "__main__":
    main()