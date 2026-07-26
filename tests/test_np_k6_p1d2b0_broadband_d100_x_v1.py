import importlib.util
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[1];P=R/"scripts"/"run_np_k6_p1d2b_broadband_pillar_x_v1.py"
S=importlib.util.spec_from_file_location("d100",P);m=importlib.util.module_from_spec(S);S.loader.exec_module(m)
def test_only_d100_x_allowed():
 assert m.spec()["diameter_nm"]==100
 for d in (99,105):
  with pytest.raises(ValueError):m.spec(diameter_nm=d)
def test_geometry_and_axis_contract():
 s=m.spec();assert(s["radius_nm"],s["gap_nm"],s["aspect_ratio"])==(50,190,5.0);assert s["target_wavelength_grid_nm"]==list(range(445,456));assert len(s["monitor_mapping"])*3==33
def test_blank_pillar_diff_is_limited_without_solver():
 a={"simulation_time_s":1e-12,"auto_shutoff_min":1e-5};d=m.compare_contract(m.spec(),a);assert d["equivalence_gate"] and sorted(d["actual_differences"])==d["allowed_contract_differences"]
def test_post_artifacts_if_present():
 p=R/"outputs"/"np_k6_p1d2b0_broadband_d100_x_v1"/"results.json"
 if not p.exists():pytest.skip("post-run not available during preflight")
 x=__import__("json").loads(p.read_text());assert len(x["rows"])==11 and all("txy" not in r and "tyy" not in r for r in x["rows"])
