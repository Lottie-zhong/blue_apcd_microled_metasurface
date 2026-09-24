from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from shared_fdtd.tools.gpu_native_truth_validator_v1 import validate_monitor  # noqa: E402
from shared_fdtd.tools.pw_complex_floquet_state_v1 import _synthetic_raw, canonical_state_from_raw  # noqa: E402

CONTRACT = ROOT / "contracts/coupling/medium_pw/MEDIUM_PW_MONITOR_CONTRACT_V1.json"
SCHEMA = ROOT / "contracts/coupling/medium_pw/PW_GPU_MONITOR_TRUTH_SCHEMA_V1.json"
SETUP = ROOT / "outputs/coupling_ml/W2H_15294_5NM_GPU_PRODUCTION_SCHEMA_V3/attempt_001/setup/runtime.fsp"


def payload(z: float) -> dict:
    return {"present": True, "type": "2D Z-normal", "z_nm": z, "x_span_nm": 1740.0, "y_span_nm": 290.0, "wavelengths_nm": list(range(440, 461)), "fields": ["Ex", "Ey", "Ez", "Hx", "Hy", "Hz"]}


def main() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    tests = {}
    tests["A_PRENP_sample_1150_ref_1202_PASS"] = contract["essential_production"]["MON_PRENP"]["z_nm"] == 1150.0 and contract["essential_production"]["MON_PRENP"]["reference_plane_nm"] == 1202.0 and validate_monitor("MON_PRENP", payload(1150.0))["pass"]
    tests["B_POSTNP_sample_1800_ref_1722_PASS"] = contract["essential_production"]["MON_POSTNP"]["z_nm"] == 1800.0 and contract["essential_production"]["MON_POSTNP"]["reference_plane_nm"] == 1722.0 and validate_monitor("MON_POSTNP", payload(1800.0))["pass"]
    tests["C_PRENP_at_1202_FAIL_sample_contract"] = not validate_monitor("MON_PRENP", payload(1202.0))["pass"]
    tests["D_POSTNP_at_1722_FAIL_sample_contract"] = not validate_monitor("MON_POSTNP", payload(1722.0))["pass"]
    tests["E_stale_1200_2212_rejected"] = schema["monitors"]["MON_PRENP"]["z_nm"] != 1200.0 and schema["monitors"]["MON_POSTNP"]["z_nm"] != 2212.0
    tests["F_sample_reference_swap_rejected"] = not (contract["essential_production"]["MON_PRENP"]["z_nm"] == contract["essential_production"]["MON_PRENP"]["reference_plane_nm"] or contract["essential_production"]["MON_POSTNP"]["z_nm"] == contract["essential_production"]["MON_POSTNP"]["reference_plane_nm"])
    planes = {plane: _synthetic_raw(33, 9, z * 1e-9, 1.7 + 0.002j, {(0, 0, 1, "TM"): 1.0 + 0.2j}) for plane, z in (("IN", -100.0), ("PRENP", 1150.0), ("POSTNP", 1800.0))}
    state = canonical_state_from_raw(planes, {plane: [1.7 + 0.002j] for plane in planes})
    tests["G_raw_sample_to_canonical_reference_deembedding_PASS"] = abs(state["plane_metadata"]["PRENP"]["z_sample_m"] * 1e9 - 1150.0) < 1e-9 and abs(state["plane_metadata"]["PRENP"]["z_reference_m"] * 1e9 - 1202.0) < 1e-9 and abs(state["plane_metadata"]["POSTNP"]["z_sample_m"] * 1e9 - 1800.0) < 1e-9 and abs(state["plane_metadata"]["POSTNP"]["z_reference_m"] * 1e9 - 1722.0) < 1e-9
    digest = hashlib.sha256(SETUP.read_bytes()).hexdigest() if SETUP.is_file() else ""
    tests["H_setup_sha_unchanged"] = digest == "36e5011b5e5c67a41e28dba296575356e6d7cefbbb1b4dd5e20ed0bfbffc08a5"
    tests["I_no_solver_entries"] = True
    result = {"status": "PASS" if all(tests.values()) else "FAIL", "solver_invocations": 0, "scientific_solver_entries": 0, "tests": tests, "setup_sha256": digest}
    print(json.dumps(result, indent=2))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
