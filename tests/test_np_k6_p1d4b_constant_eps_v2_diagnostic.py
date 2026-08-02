import json
from pathlib import Path

def test_constant_eps_v2_diagnostic_validator_contract():
    root=Path(__file__).resolve().parents[1]
    e=root/"outputs/np_k6_p1d4b_k6x_run3c_n1_material_representation_constant_eps_v2_diagnostic_v1"
    m=json.loads((e/"entered_ledger.json").read_text())
    assert m["entered"] and m["run_invocation_count"]==1
    assert m["engine_completed"] and m["post_saved"] and m["controller_returned"]
    assert json.loads((e/"actual_grid_comparison.json").read_text())["coordinate_grid_equal"]
    assert json.loads((e/"post_run_material_audit.json").read_text())["all_constant"]
    assert json.loads((e/"solver_budget_audit.json").read_text())["N2_run"] is False
