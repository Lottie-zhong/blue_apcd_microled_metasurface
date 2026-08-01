from pathlib import Path
import importlib.util
def test_boundary_diagnostic():
 p=Path(__file__).resolve().parents[1]/'scripts/validate_np_k6_p1d4b_n1_minimal_boundary_diagnostic_v1.py'; s=importlib.util.spec_from_file_location('v',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.main()
