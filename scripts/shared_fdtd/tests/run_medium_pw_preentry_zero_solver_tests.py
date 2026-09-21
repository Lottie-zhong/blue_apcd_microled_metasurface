from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = ROOT / "contracts" / "coupling" / "medium_pw"
BUILDER = ROOT / "scripts" / "shared_fdtd" / "tools" / "build_medium_pw_setup_only_v1.py"
OUT = ROOT / "outputs" / "coupling_ml" / "FREEZE_V3_RESOURCE_HARDENING_AND_MEDIUM_PW_PREENTRY_V1"


def main():
    mesh = json.loads((CONTRACT / "MEDIUM_PW_MESH_CONTRACT_V1.json").read_text(encoding="utf-8"))
    temporal = json.loads((CONTRACT / "MEDIUM_PW_TEMPORAL_CONTRACT_V1.json").read_text(encoding="utf-8"))
    monitor = json.loads((CONTRACT / "MEDIUM_PW_MONITOR_CONTRACT_V1.json").read_text(encoding="utf-8"))
    schema = json.loads((CONTRACT / "MEDIUM_PW_VARIABLE_K_SCHEMA_V1.json").read_text(encoding="utf-8"))
    policy = json.loads((CONTRACT / "V3_RESOURCE_POLICY_FREEZE_V1.json").read_text(encoding="utf-8"))
    tests = {}
    tests["mesh_contract_exact"] = mesh["physics"]["Lambda_x_nm"] == 1740.0 and mesh["physics"]["Lambda_y_nm"] == 290.0 and len(mesh["mesh_overrides"]) == 12 and all(item["dx_nm"] in (5.0, 10.0, 15.0, 20.0) for item in mesh["mesh_overrides"])
    tests["no_full_domain_5nm_override"] = all(not (item["dx_nm"] == 5.0 and item["x_span_nm"] == 1740.0 and item["y_span_nm"] == 290.0 and item["z_span_nm"] > 100.0) for item in mesh["mesh_overrides"])
    tests["temporal_contract_exact"] = temporal["maximum_physical_simulation_time_s"] == 3e-12 and temporal["auto_shutoff_min"] == 1e-6 and temporal["validation_checkpoints_ps"] == [1.0, 2.0, 3.0]
    tests["monitor_contract_preserves_fields"] = all(name in monitor["essential_production"] for name in ("MON_PRENP", "MON_POSTNP", "MON_REFLECTION")) and monitor["essential_production"]["MON_PRENP"]["complex_fields"]
    tests["variable_k_schema"] = schema["current_case"]["K"] == len(schema["current_case"]["ordered_D_list_nm"]) and schema["validation"]["no_generic_interface_hardcodes_K6"]
    tests["resource_policy_frozen"] = policy["global_capacity"] == 3 and policy["branch_caps"] == {"traditional": 1, "coupling_ml": 2} and policy["pw_integrated_max_concurrent"] == 1
    tests["builder_has_no_solver_run"] = "fd.run(" not in BUILDER.read_text(encoding="utf-8")
    readback = OUT / "W2H_15294_MEDIUM_PW_SETUP_READBACK.json"
    tests["fresh_load_evidence"] = readback.is_file() and json.loads(readback.read_text(encoding="utf-8"))["load_only"] and not json.loads(readback.read_text(encoding="utf-8"))["run_called"]
    passed = sum(bool(value) for value in tests.values())
    result = {"status": "PASS" if passed == len(tests) else "FAIL", "passed": passed, "total": len(tests), "tests": tests, "solver_runs": 0, "scientific_solver_entries": 0}
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
