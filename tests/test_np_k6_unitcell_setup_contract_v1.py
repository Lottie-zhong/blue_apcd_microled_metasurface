import ast, importlib.util, math
from pathlib import Path
import pytest, yaml

ROOT=Path(__file__).resolve().parents[1]
def mod(name,path):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
B=mod("np_builder",ROOT/"scripts"/"build_np_k6_unitcell_setup_v1.py")
E=mod("np_extractor",ROOT/"scripts"/"extract_np_k6_unitcell_complex_t_v1.py")

def test_yaml_contract():
    c=yaml.safe_load((ROOT/"configs"/"np_k6_unitcell_setup_v1.yaml").read_text(encoding="utf-8"))
    assert c["branch_id"]=="NP-K6-MDC-V1" and c["local_pitch_x_nm"]==c["period_y_nm"]==290
    assert c["extraction"]["weighted_G0"]=="forbidden"

def test_integer_and_fabrication_gates():
    assert B.parse_integer_nm("500")==500
    for value in ("500.0","1e2","nan"):
        with pytest.raises(Exception): B.parse_integer_nm(value)
    B.validate_geometry(500,160)
    for pair in ((299,160),(500,99),(700,100),(500,231)):
        with pytest.raises(ValueError): B.validate_geometry(*pair)

def test_blank_pillar_shared_contract():
    a=B.build_spec("blank",450,"x",500,160); b=B.build_spec("pillar",450,"x",500,160)
    assert a["layout_nm"]==b["layout_nm"] and a["source_monitor_reference_shared"] and b["source_monitor_reference_shared"]

def test_complex_normalization_and_crosspol():
    r=E.normalize_input(2+2j,1-1j,1+1j)
    assert r["copol"]["abs"]==pytest.approx(2.0) and r["phase_rel_rad"]==pytest.approx(0.0)
    assert r["crosspol"]["real"]==pytest.approx(0.0) and r["crosspol"]["imag"]==pytest.approx(-1.0)
    with pytest.raises(ValueError): E.normalize_input(1+0j,0j,0j)

def test_no_solver_run_call():
    for path in (ROOT/"scripts"/"build_np_k6_unitcell_setup_v1.py",ROOT/"scripts"/"extract_np_k6_unitcell_complex_t_v1.py"):
        tree=ast.parse(path.read_text(encoding="utf-8")); assert ".run(" not in path.read_text(encoding="utf-8")
        assert isinstance(tree,ast.Module)