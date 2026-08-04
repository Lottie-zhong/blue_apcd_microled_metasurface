import importlib.util
from pathlib import Path
p=Path(__file__).parents[1]/'scripts/validate_np_k6_p0_observable_convergence_adjudication_v2.py'
spec=importlib.util.spec_from_file_location('v',p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
def test_adjudication_v2_contract_passes():
 assert m.validate()==[]
def test_no_solver_this_round():
 assert m.read('solver_budget_audit_v2.json')['solver_calls_this_adjudication_round']==0
