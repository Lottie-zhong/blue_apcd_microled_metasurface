import importlib.util, json
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[1]; P=R/"scripts"/"run_np_k6_p1d2b_broadband_pillar_x_v1.py"
S=importlib.util.spec_from_file_location("p",P); m=importlib.util.module_from_spec(S); S.loader.exec_module(m)
def test_d115_only_allowlisted_geometry():
 m.configure(115); s=m.spec("NP_P1D2_BROADBAND_PILLAR_H500_D115_X",115)
 assert (s["diameter_nm"],s["radius_nm"],s["gap_nm"],s["aspect_ratio"])==(115,57.5,175,500/115)
 with pytest.raises(ValueError):m.configure(120)
def test_d110_d115_pair_and_four_point_schema():
 rows=json.loads((R/"outputs/np_k6_p1d2b2_broadband_d110_x_v1/results.json").read_text())["rows"]; m.configure(115)
 assert len(m.pair_dispersion(rows,110,115)["rows"])==11
 assert m.partial_four_diameter_line(rows)["provisional_four_diameter_broadband_line"]
def test_d115_post_artifacts_if_present():
 out=R/"outputs/np_k6_p1d2b3_broadband_d115_x_v1"
 if not (out/"results.json").exists():pytest.skip("post-run not available during preflight")
 assert len(json.loads((out/"results.json").read_text())["rows"])==11
 assert json.loads((out/"partial_line_d100_d105_d110_d115.json").read_text())["provisional_four_diameter_broadband_line"]
