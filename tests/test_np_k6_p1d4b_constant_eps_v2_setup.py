import json
from pathlib import Path

def test_constant_eps_v2_setup_only_contract():
    root=Path(__file__).resolve().parents[1]
    e=root/"outputs/np_k6_p1d4b_k6x_run3c_n1_material_representation_constant_eps_v2_setup_v1"
    m=json.loads((e/"setup_manifest.json").read_text())
    v=json.loads((e/"setup_validator_report.json").read_text())
    s=json.loads((e/"single_variable_contract_audit.json").read_text())
    assert m["setup_only"] and not m["entered"] and m["run_invocation_count"]==0
    assert v["pass"] and v["constant_445_449_455"] and v["sampled_data_absent"]
    assert s["pass"] and not s["unexpected_differences"]

def test_constant_builder_uses_scalar_dielectric_not_sampled_data():
    root=Path(__file__).resolve().parents[1]
    text=(root/"scripts/build_np_k6_p1d4b_constant_eps_v2_setup.py").read_text()
    assert 'addmaterial("Dielectric")' in text
    assert 'Sampled 3D data' not in text and 'sampled data' not in text

def test_n_squared_errors_and_old_supersession():
    root=Path(__file__).resolve().parents[1]
    e=root/"outputs/np_k6_p1d4b_k6x_run3c_n1_material_representation_constant_eps_v2_setup_v1"
    v=json.loads((e/"setup_validator_report.json").read_text())
    assert all(x["abs_error"] <= 1e-10 for x in v["n_squared_errors"].values())
    old=json.loads((e/"old_control_supersession.json").read_text())
    assert old["old_classification"]=="MATERIAL_REPRESENTATION_CONTROL_INVALID_WRONG_REPRESENTATION"
    assert old["solver_attempt_consumed"] and old["superseded_by"]=="RUN3C_N1_MATERIAL_REPRESENTATION_CONSTANT_EPS_V2_DIAGNOSTIC"
