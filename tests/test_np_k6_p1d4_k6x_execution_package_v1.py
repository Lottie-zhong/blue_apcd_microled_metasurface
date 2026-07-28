import json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_execution_package_no_run():
 runpy.run_path(str(ROOT/'scripts'/'build_np_k6_p1d4_k6x_execution_package_v1.py'),run_name='__main__');runpy.run_path(str(ROOT/'scripts'/'validate_np_k6_p1d4_k6x_execution_package_v1.py'),run_name='__main__')
 p=ROOT/'outputs/np_k6_p1d4_k6x_execution_package_v1';assert json.loads((p/'solver_budget_contract.json').read_text())['max_entered_runs']==4;assert json.loads((p/'preflight_manifest.json').read_text())['solver_entered']==0