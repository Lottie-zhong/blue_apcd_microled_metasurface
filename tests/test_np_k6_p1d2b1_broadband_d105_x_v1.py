import importlib.util, json
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[1];P=R/"scripts"/"run_np_k6_p1d2b_broadband_pillar_x_v1.py"
S=importlib.util.spec_from_file_location("p",P);m=importlib.util.module_from_spec(S);S.loader.exec_module(m)
def test_d105_only_task_case():
 m.configure(105);s=m.spec("NP_P1D2_BROADBAND_PILLAR_H500_D105_X",105)
 assert(s["diameter_nm"],s["radius_nm"],s["gap_nm"])==(105,52.5,185)
 m.configure(110)
 with pytest.raises(ValueError):m.configure(115)
def test_pair_math_and_thresholds():
 m.configure(105)
 r100=json.loads((R/"outputs/np_k6_p1d2b0_broadband_d100_x_v1/results.json").read_text())["rows"]
 rows=[]
 for x in r100:
  y=dict(x);y["txx"]=dict(x["txx"]);y["txx"]["phase_rad_wrapped"]+=0.01;y["txx"]["amplitude"]*=1.01;y["T"]+=.001;rows.append(y)
 p=m.pair_dispersion(rows,100,105)
 assert len(p["rows"])==11 and p["summary"]["pair_relative_phase_stability"]=="stable"
def test_d105_post_artifacts_if_present():
 p=R/"outputs/np_k6_p1d2b1_broadband_d105_x_v1/results.json"
 if not p.exists():pytest.skip("post-run not available during preflight")
 x=json.loads(p.read_text());assert len(x["rows"])==11
