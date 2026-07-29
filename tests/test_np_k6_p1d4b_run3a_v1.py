def test_run3a():
 import json
 from pathlib import Path
 o=Path(__file__).resolve().parents[1]/'outputs/np_k6_p1d4b_k6x_phase_candidate_run3a_freeze_v1'
 assert json.loads((o/'solver_budget_audit.json').read_text())['entered_runs']==1
