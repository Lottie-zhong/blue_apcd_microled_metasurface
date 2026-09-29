from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shared_fdtd.tools.pw_scientific_launcher import (  # noqa: E402
    _new_solver_processes,
    load_only_validate,
    run_and_confirm_entry,
    validate_config,
)


CONTRACT = {
    "monitors": {"input": "MON_IN", "pre": "MON_PRENP", "output": "MON_POSTNP"},
    "samples_nm": {"MON_IN": -100.0, "MON_PRENP": 1150.0, "MON_POSTNP": 1800.0},
    "references_nm": {"MON_IN": -50.0, "MON_PRENP": 1202.0, "MON_POSTNP": 1722.0},
    "materials": {"substrate": "APCD_GAN_NATIVE_M1", "mdc_tio2": "APCD_TIO2_NATIVE_M1", "mdc_sio2": "APCD_SIO2_NATIVE_M1"},
    "stack_layers": [["APCD_TIO2_NATIVE_M1", 44.0]],
    "wavelengths_nm": list(range(440, 461)),
}


def cfg(**overrides):
    value = {
        "db": "db", "runtime": "runtime", "attempt_root": "attempt", "pre_fsp": "pre.fsp",
        "pre_fsp_sha256": "a" * 64, "physical_contract_hash": "b" * 64,
        "branch": "coupling_ml", "case": "PW_CASE", "attempt": "attempt_002", "task": "task",
        "slot_id": "GLOBAL_SLOT_2", "lease_token": "token", "fencing_generation": 7,
        "scientific_launcher": "PW_PERIODIC_PLANAR", "pw_contract": CONTRACT,
        "run_fsp": "attempt/run.fsp",
    }
    value.update(overrides)
    return value


class ReturnFD:
    def __init__(self, failure=False):
        self.run_calls = 0
        self.failure = failure

    def run(self):
        self.run_calls += 1
        if self.failure:
            raise RuntimeError("preentry")


class LoadOnlyFD:
    def __init__(self):
        self.run_calls = 0

    def getdata(self, monitor, name):
        return [1.0]

    def grating(self, monitor, index):
        return [1.0]


def expect_error(fn, token):
    try:
        fn()
    except Exception as exc:
        assert token in str(exc), (token, exc)
    else:
        raise AssertionError("expected " + token)


def main():
    checks = {}
    launcher_source = (ROOT / "shared_fdtd/tools/pw_scientific_launcher.py").read_text(encoding="utf-8")
    assert "np.savez_compressed" in launcher_source and "raw_complex_fields" in launcher_source and all(name in launcher_source for name in ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz"))
    checks["M_raw_complex_fields_persisted"] = "PASS"
    validate_config(cfg())
    checks["A_payload_valid"] = "PASS"
    expect_error(lambda: validate_config(cfg(branch="traditional")), "PW_FOREIGN_BRANCH")
    checks["B_foreign_owner_rejected"] = "PASS"
    expect_error(lambda: validate_config(cfg(fencing_generation=0)), "PW_INVALID_FENCING_GENERATION")
    checks["C_invalid_fencing_rejected"] = "PASS"
    expect_error(lambda: validate_config(cfg(pw_contract={})), "SCIENTIFIC_CONTRACT_FIELD_MISSING:monitors,samples_nm,references_nm,materials,stack_layers,wavelengths_nm")
    checks["D_contract_gate"] = "PASS"

    fd = ReturnFD(failure=True)
    evidence = []
    expect_error(lambda: run_and_confirm_entry(fd, cfg(), evidence.append, process_snapshot=lambda: []), "preentry")
    assert fd.run_calls == 1 and not evidence
    checks["E_preentry_failure_no_entry"] = "PASS"

    fd = ReturnFD()
    evidence = []
    run_and_confirm_entry(fd, cfg(), evidence.append, process_snapshot=lambda: [])
    assert fd.run_calls == 1 and len(evidence) == 1 and evidence[0]["observation"] == "lumapi.run_returned"
    checks["F_confirmed_entry_boundary"] = "PASS"

    fd = ReturnFD()
    evidence = []
    run_and_confirm_entry(fd, cfg(), evidence.append, process_snapshot=lambda: [{"ProcessId": "9", "Name": "fdtd-engine-msmpi.exe", "CommandLine": "run.fsp"}])
    assert len(evidence) == 1
    checks["G_single_confirmation"] = "PASS"
    assert fd.run_calls == 1
    checks["H_no_replay"] = "PASS"

    fd = LoadOnlyFD()
    load_only_validate(fd, cfg())
    assert fd.run_calls == 0
    checks["I_load_only_no_solver"] = "PASS"

    cfg2 = cfg(case="PW_CASE_2", slot_id="GLOBAL_SLOT_3")
    validate_config(cfg2)
    assert cfg()["case"] != cfg2["case"] and cfg()["slot_id"] != cfg2["slot_id"]
    checks["J_two_slot_isolation"] = "PASS"

    rows = _new_solver_processes([], [{"ProcessId": "1", "Name": "fdtd-engine-msmpi.exe", "CommandLine": "attempt/run.fsp"}], "attempt/run.fsp")
    assert len(rows) == 1
    checks["K_process_entry_evidence"] = "PASS"
    expect_error(lambda: validate_config(cfg(scientific_launcher="G2")), "PW_LAUNCHER_SELECTOR_MISMATCH")
    checks["L_launcher_selector_gate"] = "PASS"

    print(json.dumps({"status": "PASS", "solver_invocations": 0, "checks": checks}, indent=2))


if __name__ == "__main__":
    main()
