"""Deterministic zero-solver completeness checks for the MEDIUM MON_IN payload."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
from shared_fdtd.tools.pw_complex_floquet_state_v1 import _synthetic_raw, canonical_state_from_raw
CONTRACT_DIR = ROOT / "contracts" / "coupling" / "medium_pw"
OUT = ROOT / "outputs" / "coupling_ml" / "FREEZE_V3_RESOURCE_HARDENING_AND_MEDIUM_PW_PREENTRY_V1"
BUILDER = ROOT / "scripts" / "shared_fdtd" / "tools" / "build_medium_pw_setup_only_v1.py"
READBACK = OUT / "W2H_15294_MEDIUM_PW_SETUP_WITH_MON_IN_READBACK.json"
FSP = OUT / "W2H_15294_MEDIUM_PW_SETUP_ONLY_WITH_MON_IN.fsp"


def main() -> None:
    monitor_contract = json.loads((CONTRACT_DIR / "MEDIUM_PW_MONITOR_CONTRACT_V1.json").read_text(encoding="utf-8"))
    mesh = json.loads((CONTRACT_DIR / "MEDIUM_PW_MESH_CONTRACT_V1.json").read_text(encoding="utf-8"))
    readback = json.loads(READBACK.read_text(encoding="utf-8"))
    mon_in = monitor_contract["essential_production"]["MON_IN"]
    rb_monitors = readback["monitors"]
    builder_text = BUILDER.read_text(encoding="utf-8")
    tests = {
        "A_mon_in_exists": "MON_IN" in monitor_contract["essential_production"] and "MON_IN" in rb_monitors and FSP.is_file(),
        "B_z_exact_minus_100_nm": mon_in["z_nm"] == -100.0 and abs(float(rb_monitors["MON_IN"]["z"]) * 1e9 + 100.0) < 1e-6,
        "C_complete_supercell": mon_in["x_span_nm"] == 1740.0 and mon_in["y_span_nm"] == 290.0 and rb_monitors["MON_IN"]["x span"] == 1.74e-6 and rb_monitors["MON_IN"]["y span"] == 2.9e-7,
        "D_21_wavelengths": len(monitor_contract["canonical_state"]["wavelengths_nm"]) == 21 and monitor_contract["canonical_state"]["wavelengths_nm"] == list(range(440, 461)) and rb_monitors["MON_IN"]["frequency points"] == 21.0,
        "E_six_complex_fields": monitor_contract["essential_production"]["MON_IN"]["complex_fields"] == ["Ex", "Ey", "Ez", "Hx", "Hy", "Hz"],
        "F_local_medium_geometry": mesh["physics"]["z_coordinates_nm"]["gan_min"] <= -100.0 <= mesh["physics"]["z_coordinates_nm"]["gan_mdc_interface"] and mon_in["local_medium"] == mesh["physics"]["gan_material"],
        "G_frozen_schema_mapping": monitor_contract["canonical_state"]["monitors"] == {"input": "MON_IN", "pre": "MON_PRENP", "output": "MON_POSTNP"} and monitor_contract["canonical_state"]["state_schema"] == "PW_COMPLEX_FLOQUET_STATE_V1",
        "H_forward_backward_defined": False,
        "I_physics_contract_unchanged": all(abs(float(readback["solver"][key]) - expected) < 1e-15 for key, expected in (("x span", 1.74e-6), ("y span", 2.9e-7), ("z min", -600e-9), ("z max", 3000e-9))) and abs(float(readback["source"]["z"]) + 276e-9) < 1e-15 and readback["source"]["direction"] == "Forward",
        "J_no_solver_invocation": "fd.run(" not in builder_text,
        "K_existing_medium_preentry_pass": False,
        "L_existing_comparator_pass": False,
    }
    amplitudes = {(0, 0, 1, "TM"): 1.0 + 0.2j, (0, 0, -1, "TM"): 0.3 - 0.1j}
    synthetic_planes = {
        plane: _synthetic_raw(65, 17, z_nm * 1e-9, 1.7 + 0.002j, amplitudes)
        for plane, z_nm in (("IN", -100.0), ("PRENP", 1150.0), ("POSTNP", 1800.0))
    }
    synthetic_state = canonical_state_from_raw(synthetic_planes, {plane: [1.7 + 0.002j] for plane in synthetic_planes})
    incident_order = list(map(tuple, synthetic_state["orders"])).index((0, 0))
    in_coefficients = synthetic_state["coefficients"][0, 0, incident_order]
    tests["H_forward_backward_defined"] = set(rb_monitors) == {"MON_IN", "MON_PRENP", "MON_POSTNP", "MON_REFLECTION"} and all(abs(complex(in_coefficients[index])) > 1e-12 for index in ((0, 1), (1, 1)))
    for name, test_path in (("K_existing_medium_preentry_pass", ROOT / "scripts/shared_fdtd/tests/run_medium_pw_preentry_zero_solver_tests.py"), ("L_existing_comparator_pass", ROOT / "scripts/shared_fdtd/tests/run_pw_complex_floquet_state_zero_solver_tests.py")):
        result = subprocess.run([sys.executable, str(test_path)], cwd=str(ROOT), capture_output=True, text=True)
        tests[name] = result.returncode == 0
    tests["F_local_medium_geometry"] = bool(tests["F_local_medium_geometry"])
    assert all(tests.values()), tests
    print(json.dumps({"schema_version": "MEDIUM_PW_MON_IN_ZERO_SOLVER_TESTS_V1", "status": "PASS", "tests": tests, "solver_invocations": 0, "scientific_solver_entries": 0}, indent=2))


if __name__ == "__main__":
    main()
