import json
from pathlib import Path

def test_material_control_scope_is_explicitly_blocked_when_not_constant_epsilon():
    root=Path(__file__).resolve().parents[1]
    e=root/"outputs/np_k6_p1d4b_k6x_run3c_n1_material_representation_control_v1"
    c=json.loads((e/"material_control_classification.json").read_text())
    assert c["classification"]=="HARD_GATE_MATERIAL_CONTROL_NOT_SINGLE_VARIABLE"
    assert c["no_additional_solver"] is True
