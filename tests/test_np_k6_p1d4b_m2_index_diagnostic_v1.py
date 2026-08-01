from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parents[1]
def test_m2_index_diagnostic_evidence_contract():
 p=ROOT/"scripts"/"validate_np_k6_p1d4b_m2_index_diagnostic_v1.py";s=importlib.util.spec_from_file_location("m2v",p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.main()
