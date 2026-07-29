def test_audit():
 from pathlib import Path
 import json
 o=Path(__file__).resolve().parents[1]/'outputs/np_k6_p1d4b_k6x_phase_candidate_run3a_audit_v1'
 assert json.loads((o/'solver_zero_audit.json').read_text())['new_solver_entered']==0
